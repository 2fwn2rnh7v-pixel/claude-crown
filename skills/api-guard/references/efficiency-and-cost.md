# Levels 3 & 4 — lower consumption, same result

Contents:
1. Measure first
2. Stage 1 — do not call at all
3. Stage 2 — cache
4. Stage 3 — batch (resolve N+1)
5. Stage 4 — request less
6. Stage 5 — request later
7. Stage 6 — request cheaper (LLM-specific)
8. The silent cost eaters
9. Prove the effect

---

## 1. Measure first

Without numbers every optimisation is a guess. Before anything is changed: one log point per
outgoing call.

```ts
// lib/api-metrics.ts
export async function tracked<T>(
  name: string,
  fn: () => Promise<T>,
  meta: { userId?: string; inputSize?: number } = {},
): Promise<T> {
  const start = performance.now();
  try {
    const result = await fn();
    console.info(JSON.stringify({
      evt: "api_call", name, ok: true,
      ms: Math.round(performance.now() - start), ...meta,
    }));
    return result;
  } catch (err) {
    console.warn(JSON.stringify({ evt: "api_call", name, ok: false, ...meta }));
    throw err;
  }
}
```

Then answer: which call is the most frequent? Which the most expensive per call? How many calls
fall on the same input? Experience says the answer to the third question is the biggest lever —
often 30–60% of all calls are repetitions.

## 2. Stage 1 — do not call at all

**Deduplicate in-flight requests.** Three components need the same data and fire three calls. A
promise map solves that:

```ts
const inFlight = new Map<string, Promise<unknown>>();

export function dedupe<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const running = inFlight.get(key);
  if (running) return running as Promise<T>;

  const p = fn().finally(() => inFlight.delete(key));
  inFlight.set(key, p);
  return p;
}
```

Data-fetching libraries (TanStack Query, SWR) do this automatically for the same query key — one
reason to prefer them over manual `useEffect` fetching. Next.js deduplicates identical `fetch`
calls within one render pass on the server as well.

**Detect unchanged input.** If the user did not touch the text, the analysis need not run again:

```ts
const hash = await sha256(input);
if (hash === lastHash) return lastResult; // call saved
```

**`useEffect` traps.** A missing dependency array, unstable object dependencies and the StrictMode
double mount produce calls nobody ordered:

```ts
// ❌ runs on every render
useEffect(() => { void loadData(); });

// ❌ filter is a new object on every render → always runs
useEffect(() => { void loadData(filter); }, [filter]);

// ✅ stable, primitive dependencies
useEffect(() => { void loadData({ year, region }); }, [year, region]);
```

## 3. Stage 2 — cache

Caching pays for everything that changes less often than it is requested.

```ts
// simple TTL cache for server modules
type Entry<T> = { value: T; until: number };
const cache = new Map<string, Entry<unknown>>();

export async function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>) {
  const hit = cache.get(key);
  if (hit && hit.until > Date.now()) return hit.value as T;

  const value = await fn();
  cache.set(key, { value, until: Date.now() + ttlMs });
  return value;
}
```

Choose the TTL by change rate, not by feeling:

| Data type | TTL |
|---|---|
| Geocoding, master data, translations | Days to unbounded (persistent, not only in RAM) |
| Weather forecast | 30–60 minutes |
| Prices, availabilities | 30–60 seconds |
| User-owned data | Never cache globally — the key must contain the user ID |

**`stale-while-revalidate`** returns the old value immediately and refreshes in the background —
the user never waits, and the request count stays capped:

```ts
return NextResponse.json(data, {
  headers: { "Cache-Control": "public, s-maxage=300, stale-while-revalidate=3600" },
});
```

In Next.js 16 the same idea lives in the framework: `'use cache'` + `cacheLife('hours')` on the
data function, `cacheTag` + `updateTag` after the mutation. See `framework-recipes.md`.

**ETag / `If-None-Match`**: if the third-party API answers `304 Not Modified`, the transfer is
gone and with many providers part of the cost too. Always check whether the provider supports it.

**Persistent cache** for expensive, stable results — a table with `input_hash` as the primary
key. Survives deployments and cold starts, unlike the map cache. Almost always the right choice
for expensive LLM or image processing.

## 4. Stage 3 — batch

The N+1 pattern is the most common consumption driver in list views:

```ts
// ❌ 1 + N calls
const fields = await api.getFields();
for (const field of fields) {
  field.weather = await api.getWeather(field.lat, field.lon); // N calls
}

// ✅ 1 + 1 calls
const fields = await api.getFields();
const coords = fields.map((f) => ({ lat: f.lat, lon: f.lon }));
const weather = await api.getWeatherBatch(coords);
fields.forEach((f, i) => (f.weather = weather[i]));
```

If the provider offers no batch endpoint, a **micro-batcher** helps: collect requests within a
short time window and send them together.

```ts
let buffer: string[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;
const waiting = new Map<string, (v: unknown) => void>();

export function request(id: string) {
  return new Promise((resolve) => {
    waiting.set(id, resolve);
    buffer.push(id);
    timer ??= setTimeout(async () => {
      const ids = buffer; buffer = []; timer = null;
      const results = await api.getMany(ids);     // one call instead of ids.length
      ids.forEach((i) => waiting.get(i)?.(results[i]));
    }, 20);
  });
}
```

Same principle for parallelism: `Promise.all` is faster than a loop with `await`, but does not
reduce the number of calls — and can blow the provider's rate limit. With many elements work with
bounded concurrency (e.g. 5 at a time) instead of sending everything at once.

## 5. Stage 4 — request less

With many APIs the price scales with data volume, not request count.

- **Field selection**: `?fields=id,name,status` instead of the full object. With GraphQL request
  only what is rendered.
- **Pagination**: `limit=20` instead of 10,000 rows of which 20 are visible.
- **Delta instead of full pull**: `?since=<timestamp>` — fetch only changes.
- **Lower the resolution**: thumbnails in the list, full size only in the detail view.
- **Trim the input**: before sending to a text API remove whitespace, boilerplate and irrelevant
  sections. Same result, less volume.
- **Filter server-side**: do not fetch 1,000 records and discard 990 in the client.

## 6. Stage 5 — request later

**Debounce** on search input — by far the largest single win for autocomplete:

```ts
// ❌ one request per keystroke: "traktor" = 7 requests
onChange={(e) => search(e.target.value)}

// ✅ one request after the typing pause
const debounced = useMemo(() => debounce(search, 300), []);
onChange={(e) => debounced(e.target.value)}
```

In addition: search only from 3 characters, abort running requests on new input via
`AbortController`. React 19's `useDeferredValue` is an alternative when the search runs against
local state.

**Replace polling with push.** A 5-second poll produces 17,280 requests per day and open tab.
Alternatives in this order: webhook, Server-Sent Events, WebSocket. If polling is unavoidable:

```ts
// grow the interval while nothing changes; pause when the tab is in the background
let interval = 5_000;
async function poll() {
  if (document.hidden) return schedule(30_000);
  const { changed } = await check();
  interval = changed ? 5_000 : Math.min(interval * 2, 300_000);
  schedule(interval);
}
```

**Lazy loading**: load the data for a tab only when the tab is opened. In many dashboards calls
are paid for panels nobody ever looks at.

## 7. Stage 6 — request cheaper (LLM-specific)

Multipliers below are Anthropic's, verified 2026-09-14 via the `claude-api` reference; other
providers have their own sheets — look them up, do not assume.

- **Model routing.** Classification, extraction, formatting, short rewrites do not need a large
  model. Small model as the default, large only for tasks that measurably fail on it. Most common
  single lever on LLM bills. Measure the cheaper alternative first: the newest model at lower
  `effort` often beats an older model at high effort, and one model means one cache namespace.
- **Prompt caching.** If the system prompt or a document stays constant across many requests,
  put the constant part first and let it cache. Cache reads cost ~0.1× the base input price
  (0.025× on Claude Fable 5.1), writes 1.25× (5-minute TTL) or 2× (1-hour TTL) — break-even at
  two requests. Prefixes below the model's minimum (512–4096 tokens depending on model) silently
  do not cache: verify with `usage.cache_read_input_tokens`, a zero across repeats means a silent
  invalidator (timestamp in the system prompt, unsorted JSON, varying tool list).
- **Set `max_tokens`.** Without an upper bound you pay for digressions nobody reads. Prescribe
  the format explicitly ("answer in at most 3 bullet points").
- **Trim the context.** Do not send the entire chat history — the last n messages plus a summary
  are almost always enough. Server-side compaction exists for long conversations.
- **Structured output instead of follow-ups.** Request all needed fields in one call as JSON
  instead of three calls for three fields.
- **Semantic cache.** Map similar questions to the same cached answer entry (embedding +
  threshold). Pays off with FAQ-like traffic.
- **Batch processing.** For non-interactive tasks (nightly evaluations, mass classification) the
  Message Batches API costs 50% — on every token, including cache reads and writes; the discounts
  stack.
- **Streaming** does not lower the cost, but the perceived wait — and prevents impatient users
  from aborting and triggering the call again.

## 8. The silent cost eaters

- **Missing timeouts.** Without `AbortSignal.timeout()` a request can hang for minutes, block
  resources and still be billed.
- **Retry storm.** Retry without backoff turns a short outage into a cost spike. Retry only on
  `429` and `5xx`, with backoff and jitter, at most 2–3 attempts. On persistent failure a
  **circuit breaker** kicks in: after n consecutive errors do not call at all for a while. SDK
  clients (Anthropic, Stripe, …) already retry 2× by default — do not stack a second retry loop
  on top, or one failure becomes nine calls.
- **Missing idempotency.** A double click or retry creates two bookings. On write calls send an
  `Idempotency-Key` or check for duplicates server-side.
- **Development against production.** Hot reload fires real calls on every save. Work locally
  with mock responses or a file cache.
- **Forgotten cron jobs and CI tests** that hit paid endpoints. Mock in CI as a rule.
- **Requests not aborted.** If the user leaves the page, the call keeps running.
  `AbortController` in the effect cleanup.

## 9. Prove the effect

Close every optimisation with a number — before/after, measured or cleanly estimated:

```
Field-search autocomplete
  before:  1 request per keystroke  ≈ 7 calls per search
  after:   debounce 300 ms + from 3 characters + 5-min cache
           ≈ 1 call per search, of which ~40% cache hits
  result:  ~92% fewer calls, identical search result
```

This is the part that convinces in the audit — and shows that the functionality stayed
untouched. If the output has changed, it is not an optimisation but a change, and it must be
named as such.
