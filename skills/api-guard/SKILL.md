---
name: api-guard
description: >
  Audits and hardens API usage in TypeScript web apps: rate limiting and quotas, API keys and
  paid calls in the backend instead of the frontend, protection against cost explosions, and
  lowering API consumption for the same result (caching, batching, debouncing, payload trimming,
  model routing). Script-backed quick scan of existing code. Use ALWAYS when: an API call,
  fetch(), axios or an SDK client is written; an endpoint, route, Server Action, server function
  or Edge Function is created; API keys, secrets, tokens, .env, NEXT_PUBLIC_/VITE_ variables
  appear; an external service is connected (LLM, weather, maps, payment, Supabase, Cloudflare);
  the user says "Rate Limit", "Quota", "Kosten", "teuer", "Rechnung", "Verbrauch", "zu viele
  Requests", "429", "API-Key", "Missbrauch", "cost", "usage", "throttle", "caching" or "prüf mal
  meine API-Nutzung". Also trigger implicitly — when the frontend calls an external service
  directly, or a search, autocomplete or polling loop is built without anyone mentioning cost.
---

# API Guard

Audit and harden API usage in TypeScript web applications for **security**, **abuse resistance**
and **cost**. Always deliver concrete code corrections (before/after), never only problem
descriptions.

This skill complements `security-review`. Overlaps (auth, injection, input validation) belong
there. Here the only questions are: **who may call what, how often, from where — and what does
it cost?**

## Three guiding rules

1. **Everything in the frontend is public.** Minification, obfuscation, Base64 or "nobody will
   look" are not protection. Any key that reaches the browser is a published key — DevTools →
   Network is enough.
2. **Without a limit, every endpoint is an open cost centre.** An unthrottled endpoint that calls
   a paid service is an invoice a stranger is allowed to write for you.
3. **The cheapest request is the one that never leaves.** Before optimising anything, ask: does
   this call have to happen at all, now, at this size?

## Two modes

**Mode A — full API audit.** The user asks for a review explicitly ("prüf mal meine API-Nutzung",
"warum ist meine Rechnung so hoch", "is this safe"). Run all four levels, prioritise the findings,
close with the summary block. For existing code, start with `scripts/api_scan.py` (see Quick
start) — scan first, judge second.

**Mode B — accompanying.** Code is being written or changed without an explicit audit request.
Check only the affected levels, report only findings of MEDIUM and above, append the compact
block at the end. Do not interrupt the user's flow.

## The four levels

### Level 1 — placement: backend, not frontend

The most important question of all: *does the secret key ever leave the server?*

CRITICAL immediately when client code (React component, `"use client"`, browser bundle) contains:
- an API key, token or secret as a literal, or read from `NEXT_PUBLIC_*` / `VITE_*`
- an SDK instantiated with `dangerouslyAllowBrowser: true` or an equivalent
- a Supabase `service_role` or `sb_secret_*` key (instead of publishable key + RLS)
- a direct fetch against a paid third-party API

The correction always has the same shape: move the call into a server route / Server Action /
server function / Edge Function, the frontend calls only its own route, the key lives only in the
server environment. Details, the migration recipe and the special cases (publishable keys, RLS,
CORS, origin checks) are in `references/backend-vs-frontend.md`. Read it for every Level 1 finding.

### Level 2 — rate limiting

Check for every endpoint that costs money or writes data:

- Does a limit exist at all? (Most common answer: no.)
- What is the limit keyed on — user ID, IP, API key, session? IP alone is weak (NAT, mobile
  carriers, proxies); user ID alone is useless when registration is free.
- Is the limit **server-side**? A debounce in the frontend is UX, not a limit.
- Does it survive multiple instances? In-memory counters break as soon as the app scales.
- Does it answer with a clean `429` plus `Retry-After`, and does the client cope with that?
- Is there also a **daily / monthly quota**, not only a per-second limit? A rate limit brakes
  bursts, a quota caps cost. Both are needed.

Algorithms, concrete TypeScript implementations (Next.js route handler, Upstash/Redis,
Supabase-backed, Cloudflare binding) and recommended limit values: `references/rate-limiting.md`.
Framework-specific placement (Next.js 16, TanStack Start, Spring Boot): `references/framework-recipes.md`.

### Level 3 — abuse and cost risks

These gaps are not "insecure" in the classic sense, but they cost money or availability:

| Pattern | Why it hurts |
|---|---|
| Unbounded input length sent to an LLM / OCR / translation API | Cost scales with input — 1 MB of text per request is possible |
| Retry without backoff / retry storm | An outage triples the cost instead of lowering it |
| Polling every second | 86,400 requests per tab per day for data that changes hourly |
| `useEffect` without a dependency guard / StrictMode double mount | Every render fires a paid call |
| Autocomplete without debounce | One search term = one request per keystroke |
| Missing timeout | Hanging connections block workers and still land on the bill |
| No cost alert / no kill switch | The damage becomes visible only with the invoice |
| Missing idempotency on write calls | Double click = double payment / booking |
| Unbounded upload to a processing API | The largest cost lever of all |
| Expensive calls before the auth check | Strangers who are not logged in burn your budget |

Rule: the order inside a handler is always **auth → validation (incl. size limit) → rate limit /
quota → expensive call**. Anything checked after the expensive call protects nothing.

### Level 4 — same result, less consumption

Nothing is dropped here; the same output is produced more cheaply. Check in this order — the
early items yield the most:

1. **Do not call** — result already present? Has the input changed since the last call?
   Deduplicate identical in-flight requests.
2. **Cache** — response cache with TTL, `stale-while-revalidate`, ETag / `If-None-Match`,
   persistent cache for stable data (geocoding, master data, weather history).
3. **Batch** — n single calls into one batch call; resolve N+1 patterns in lists.
4. **Request less** — field selection, pagination, lower resolution, `max_tokens`, deltas
   instead of full pulls.
5. **Request later** — debounce, throttle, lazy loading, replace polling with webhook / SSE.
6. **Request cheaper** — smaller model for simple tasks, prompt caching for constant system
   prompts, batch tiers.

Concrete before/after examples for every item, the LLM-specific levers with verified price
multipliers, and a method to measure the effect: `references/efficiency-and-cost.md`.

## Quick start on existing code

When a whole project is to be audited and it is unclear where to begin:

```bash
python scripts/api_scan.py <project-root> [--dirs app src server lib] [--json] [--fail-on HIGH]
```

The script implements the ripgrep patterns from `references/quick-scan.md` in pure Python
(stdlib, no ripgrep needed): secrets in the client path, routes without limit or auth, polling
loops, fetches without timeout, N+1 suspects, search fields without debounce, caching presence.
It prints the summary block from `quick-scan.md` plus every hit with file and line. A hit is a
lead, not a verdict — verify each one at the element before it becomes a finding. Then run the
build-bundle check from `quick-scan.md`; that is the only proof that does not rely on trust.

## Finding format (Mode A)

```
### [SEVERITY] Short description

File: path/to/file.ts, lines X-Y
Level: [1-4] name
Problem: what exactly is wrong and why.
Abuse scenario: what a stranger (or a bug) does with it — with a rough number where possible:
"1 script, 10 req/s → ~X requests and ~Y € per hour".
Correction: code example before/after.
```

Severity levels:
- **CRITICAL** — secret in the client, unbounded paid call without auth
- **HIGH** — no rate limit on a paid / writing endpoint, no quota cap
- **MEDIUM** — avoidable repeated calls, missing caching, missing timeout
- **LOW** — polish: payload size, cache TTL, header hygiene

## Summary (Mode A)

```
## API audit summary

Scope: [what]
Overall rating: CRITICAL / HIGH / MEDIUM / LOW / CLEAN
Findings: X CRITICAL, X HIGH, X MEDIUM, X LOW

Estimated saving: [e.g. "~70% fewer calls through debounce + cache"]

Top 3 priorities:
1. [finding + action]
2. [finding + action]
3. [finding + action]

Positive: [what is done well]
```

## Compact format (Mode B)

```
--- API notes ---
1. [HIGH] description -> concrete correction
2. [MEDIUM] description -> concrete correction
```

## Agent integration

- **Agent 1 (Research)** — inventory of all outgoing calls: which service, which price per unit,
  which volume, which trigger. Without this inventory every cost statement is a guess.
- **Agent 2 (Code)** — Mode B alongside: when writing every new endpoint, set up the handler
  order (auth → validation → limit → call) correctly from the start.
- **Agent 3 (Test/QA)** — limit tests: does exceeding the limit really return 429? Does the
  quota bite? Does the kill switch work? Is the key really gone from the built bundle
  (`grep` in the `dist/` folder)?

## Reference files

- `references/backend-vs-frontend.md` — key placement, proxy/BFF pattern, migration recipe,
  Supabase keys and RLS, CORS and origin checks. Read for every Level 1 finding.
- `references/rate-limiting.md` — algorithms, limit keys, TypeScript implementations, header
  conventions (IETF draft), reference values. Read for every Level 2 finding.
- `references/efficiency-and-cost.md` — before/after patterns for reducing consumption,
  LLM-specific levers, measurement method. Read for Level 3 and Level 4 findings.
- `references/framework-recipes.md` — where the guard sits in Next.js 16 (Route Handler, Server
  Action, `'use cache'`), TanStack Start (server functions, middleware, Cloudflare Workers
  rate-limit binding), Spring Boot, Supabase. Read when placing the fix in a concrete stack.
- `references/quick-scan.md` — ripgrep commands for the first look at existing code, the
  post-build bundle check, and the runtime check.

## Self-reflection (MANDATORY)

At the end of every piece of work, check: all four levels considered? Is there really no secret
left in the client path? Is the handler order auth → validation → limit → call kept? Are the
limits server-side and multi-instance safe? Is there a cost cap besides the rate limit? Was the
saving potential quantified with concrete numbers or at least an order of magnitude? Are all
corrections formulated as runnable TypeScript instead of general advice? Were the findings
prioritised and the top 3 named?
