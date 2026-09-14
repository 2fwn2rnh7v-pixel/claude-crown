# Level 2 — rate limiting

Contents:
1. Why rate limiting is not optional
2. Rate limit vs quota vs concurrency
3. Choosing the right limit key
4. Algorithms compared
5. Implementations (in-memory, Redis/Upstash, Supabase, Cloudflare binding, edge middleware)
6. Correct 429 response and client behaviour
7. Reference values for limits
8. Cost cap and kill switch
9. Testing

---

## 1. Why rate limiting is not optional

An endpoint without a limit lets a single script send as many requests in a few minutes as your
whole user base does in a month. Three concrete consequences:

- **Cost.** At €0.01 per call, 20 requests/second means roughly €720 per hour. Not theory —
  this is exactly how the invoices people are surprised by come about.
- **Availability.** Your own quota at the provider is exhausted, real users get errors.
  Self-inflicted denial of service.
- **Data leakage.** An unthrottled read endpoint with pagination is an invitation to pull the
  entire data set. Rate limiting is scraping protection here.

Frontend debouncing or a disabled button are **not** a limit. They improve UX for cooperative
users. Whoever calls the route directly with `curl` sees none of it.

## 2. Rate limit vs quota vs concurrency

Three different protection mechanisms that do not replace each other:

| Mechanism | Question | Protects against |
|---|---|---|
| **Rate limit** | How many requests per time window? | Bursts, brute force, scraping speed |
| **Quota** | How much in total per day / month? | Slowly creeping cost explosion |
| **Concurrency limit** | How many open at the same time? | Resource exhaustion on slow calls |

Typical mistake: setting only the rate limit. 10 requests/minute sounds harmless — but that is
14,400 requests per day and user. On a paid service that is still an open cost centre.
**Always set both.**

## 3. Choosing the right limit key

What the limit hangs on decides its effectiveness:

| Key | Strength | Weakness |
|---|---|---|
| User ID / session | Fair, precise | Useless with free registration without verification |
| IP | Also catches anonymous callers | NAT / mobile carriers share IPs (collateral damage); rotating proxies bypass it |
| API key | Clearly attributable | Only for machine clients |
| Combination | Best practice | A bit more effort |

Recommendation: limit in **tiers**. Logged-in users by user ID, anonymous requests by IP with a
much stricter limit, plus a global limit per endpoint as an emergency brake.

```ts
function limitKey(req: Request, user?: { id: string }) {
  if (user) return `u:${user.id}`;
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  return `ip:${ip}`;
}
```

With `x-forwarded-for` take only the first entry behind your own trusted proxy — otherwise the
header is freely forgeable and a naive read makes the limit trivially bypassable. On Cloudflare
prefer `cf-connecting-ip`, on Vercel `x-real-ip`; both are set by the platform, not the client.

## 4. Algorithms compared

| Algorithm | How it works | Assessment |
|---|---|---|
| **Fixed window** | Counter per fixed time window | Simplest entry. Weakness: double the limit is possible at the window boundary |
| **Sliding window** | Rolling window, weighted count | Good default, prevents the boundary effect |
| **Token bucket** | Tokens refill steadily, a request consumes tokens | Allows short bursts, limits the average — ideal for UI-driven load |
| **Leaky bucket** | Requests drain at a constant rate | Good for smooth forwarding to a slow upstream API |

For most web apps: **sliding window** for protection, **token bucket** when short bursts are
desired (e.g. the user clicks three times quickly but must not hammer permanently).

Additional concept **cost weighting**: not every request costs the same. A call with 4,000 input
tokens should draw more from the bucket than one with 100. Limit LLM APIs by estimated cost, not
by request count. Upstash supports this directly: `limit(key, { rate: cost })` subtracts `cost`
tokens instead of one (verified against the Upstash Ratelimit docs, 2026-09-14).

## 5. Implementations

### In-memory (local development / single instance only)

```ts
// lib/limit-memory.ts
type Entry = { count: number; resetAt: number };
const store = new Map<string, Entry>();

export function checkLimitMemory(key: string, max: number, windowMs: number) {
  const now = Date.now();
  const entry = store.get(key);
  if (!entry || entry.resetAt <= now) {
    store.set(key, { count: 1, resetAt: now + windowMs });
    return { ok: true, remaining: max - 1, retryAfter: 0 };
  }
  if (entry.count >= max) {
    return { ok: false, remaining: 0, retryAfter: Math.ceil((entry.resetAt - now) / 1000) };
  }
  entry.count++;
  return { ok: true, remaining: max - entry.count, retryAfter: 0 };
}
```

**Name the limits clearly:** with several serverless instances each has its own counter — the
effective limit is `max × instances`. After a cold start the counter is empty. Not sufficient for
production on Vercel / edge / Workers.

### Redis / Upstash (production standard, serverless-capable)

```ts
// lib/limit.ts
import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";

const redis = Redis.fromEnv();

// short-term protection against bursts
export const burstLimit = new Ratelimit({
  redis,
  limiter: Ratelimit.slidingWindow(10, "60 s"),
  prefix: "rl:burst",
  analytics: true,
});

// daily cap against creeping cost
export const dailyQuota = new Ratelimit({
  redis,
  limiter: Ratelimit.fixedWindow(200, "24 h"),
  prefix: "rl:daily",
});

export async function checkLimit(key: string, cost = 1) {
  const burst = await burstLimit.limit(key, { rate: cost });
  if (!burst.success) {
    return { ok: false, retryAfter: Math.ceil((burst.reset - Date.now()) / 1000) };
  }
  const day = await dailyQuota.limit(key, { rate: cost });
  if (!day.success) {
    return { ok: false, retryAfter: Math.ceil((day.reset - Date.now()) / 1000) };
  }
  return { ok: true, remaining: burst.remaining, pending: burst.pending };
}
```

`limit()` returns `{ success, limit, remaining, reset, pending }`. `pending` is a promise for
background work (analytics, multi-region sync); in serverless handlers hand it to the platform's
`waitUntil` so the function is not frozen before it finishes.

### Supabase / Postgres as the limit store (when no Redis exists)

If Postgres is there anyway, a table plus an atomic upsert is enough. What matters is that
counting and checking happen in **one** statement — otherwise there is a race condition through
which parallel requests slip past the limit.

```sql
create table api_usage (
  limit_key    text        not null,
  window_start timestamptz not null,
  count        int         not null default 0,
  primary key (limit_key, window_start)
);

-- count atomically and return the current value
insert into api_usage (limit_key, window_start, count)
values ($1, date_trunc('minute', now()), 1)
on conflict (limit_key, window_start)
  do update set count = api_usage.count + 1
returning count;
```

Then check in the handler whether `count` exceeds the limit. Clean up old rows via cron or
`pg_cron`, otherwise the table grows without bound. With RLS-protected tables run this through a
`security definer` function so the publishable key cannot reset counters.

### Cloudflare Workers rate-limit binding (TanStack Start on Workers)

GA, configured in `wrangler.jsonc`, no external store (verified 2026-09-14):

```jsonc
{
  "ratelimits": [
    { "name": "API_LIMITER", "namespace_id": "1001", "simple": { "limit": 100, "period": 60 } }
  ]
}
```

```ts
const { success } = await env.API_LIMITER.limit({ key: limitKey(request, user) });
if (!success) return new Response("rate_limited", { status: 429, headers: { "Retry-After": "60" } });
```

Constraints: `period` is only `10` or `60` seconds; the limit is **per Cloudflare location**, not
global, and eventually consistent — Cloudflare calls it "intentionally designed to not be used as
an accurate accounting system". Good as a burst brake in front of a Worker; the daily quota still
needs a real store (KV / D1 / Durable Object / Upstash).

### Edge middleware (globally in front)

A limit in middleware (Next.js `middleware.ts`, TanStack Start global request middleware) bites
before function invocations are counted — so it also protects the hosting bill, not only the
third-party API. Useful as a coarse emergency brake per IP over all `/api/*` routes, in addition
to the finer limit in the handler.

## 6. Correct 429 response and client behaviour

Server-side. `Retry-After` (RFC 9110) is the one header every client understands. The informative
rate-limit headers are still an IETF draft: draft-ietf-httpapi-ratelimit-headers-11 (2026-05)
defines two structured fields, `RateLimit` and `RateLimit-Policy`, and **not** the older
`RateLimit-Limit` / `RateLimit-Remaining` / `RateLimit-Reset` triple many libraries still emit.
Send the draft form; accept that clients mostly ignore it and rely on `Retry-After`.

```ts
return new Response(JSON.stringify({ error: "rate_limited" }), {
  status: 429,
  headers: {
    "Content-Type": "application/json",
    "Retry-After": String(retryAfter),                       // seconds — the header that matters
    "RateLimit-Policy": `"burst";q=${max};w=${windowSeconds}`, // IETF draft-11 structured fields
    "RateLimit": `"burst";r=${remaining};t=${retryAfter}`,
  },
});
```

Client-side — respect `Retry-After` and use **exponential backoff plus jitter**. Without jitter
all waiting clients restart simultaneously and create exactly the storm the limit was meant to
prevent:

```ts
async function fetchWithBackoff(url: string, init: RequestInit, attempts = 3) {
  for (let i = 0; i < attempts; i++) {
    const res = await fetch(url, init);
    if (res.status !== 429 && res.status < 500) return res;

    const header = Number(res.headers.get("Retry-After"));
    const base = Number.isFinite(header) && header > 0 ? header * 1000 : 2 ** i * 500;
    const jitter = Math.random() * 300;
    await new Promise((r) => setTimeout(r, base + jitter));
  }
  throw new Error("rate_limited_after_retries");
}
```

Never retry without bound, and never retry a `4xx` other than `429` — a `400` does not get
better on the second attempt, but costs again.

In the UI: make the remaining quota visible ("noch 12 Anfragen heute"). That lowers support
effort and often works better than any technical brake.

## 7. Reference values for limits

Starting points, then adjust based on real usage:

| Endpoint type | Burst | Daily quota (per user) |
|---|---|---|
| Login / password reset | 5 / 15 min per IP+account | — |
| Registration | 3 / hour per IP | — |
| Search / autocomplete | 20 / min | 2,000 |
| Expensive LLM or image call | 5 / min | 50–200 |
| File upload for processing | 3 / min | 20 |
| Standard write operation | 30 / min | — |
| Anonymous request (not logged in) | one tenth of the user limit | very low |

Approach: start generous, **measure**, then lower. The 99th percentile of real usage is a good
anchor — above it is almost always abuse or a bug.

## 8. Cost cap and kill switch

Rate limits are per user. A global boundary is needed on top:

- **Budget alert at the provider** (e.g. at 50% and 80% of the monthly budget). First and
  cheapest measure, takes five minutes.
- **Hard cap in the provider dashboard**, where available — also stops what your code does
  not catch.
- **Global daily counter in the app** across all users. On overrun the app degrades gracefully
  ("Funktion heute nicht verfügbar") instead of paying on.
- **Kill switch via feature flag** that switches the expensive path off without a deployment.
  Valuable exactly when it has to be fast.
- **Anomaly alarm**: today's consumption against the average of the last seven days. A factor
  of 10 is almost never organic growth.

## 9. Testing

Belongs to Agent 3 (Test/QA) and is quick:

```bash
# does the limit bite? 30 parallel requests, count status codes
seq 30 | xargs -P 30 -I{} curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://localhost:3000/api/generate \
  -H "Content-Type: application/json" -d '{"prompt":"test"}' | sort | uniq -c
```

Expectation: a small number of `200`, the rest `429`. If 30× `200` come back, the limit does not
bite — most common causes: limit checked only after the expensive call, in-memory store with
several instances, or a race condition through non-atomic counting.

Further test cases: exceeding the quota returns 429 with a sensible `Retry-After`; two different
users do not affect each other; after the window expires access works again; the client aborts
cleanly after a bounded number of retries.
