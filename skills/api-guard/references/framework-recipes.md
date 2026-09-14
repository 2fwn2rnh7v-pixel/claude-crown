# Framework recipes — where the guard sits in a concrete stack

Contents:
1. Next.js 16 App Router (Route Handler, Server Action, middleware, `'use cache'`)
2. TanStack Start on Cloudflare Workers (server functions, middleware, rate-limit binding)
3. Spring Boot REST service (Java)
4. Supabase (keys, RLS, counters, Edge Functions)
5. Stack-independent checklist

APIs below were verified against the vendor docs on 2026-09-14 (Next.js 16.3.5 docs, TanStack
Start middleware guide, Cloudflare Workers rate-limit binding, Supabase API keys). When a
project pins an older major, re-check before quoting — the names moved in 2025/26.

---

## 1. Next.js 16 App Router

### Route Handler — the four-step order

```ts
// app/api/analyse/route.ts
export async function POST(req: NextRequest) {
  const user = await getUser();                       // 1. auth
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const body = Body.safeParse(await req.json());      // 2. validation + size limit
  if (!body.success) return NextResponse.json({ error: "invalid_body" }, { status: 400 });

  const gate = await checkLimit(`u:${user.id}`, estimateCost(body.data)); // 3. limit + quota
  if (!gate.ok) return NextResponse.json({ error: "rate_limited" },
    { status: 429, headers: { "Retry-After": String(gate.retryAfter) } });

  return NextResponse.json(await callUpstream(body.data)); // 4. paid call, with timeout
}
```

### Server Action — same order, different entry

Server Actions are POST endpoints too; anyone can call them with the action ID. Next.js checks
`Origin` against `Host` for them and rejects mismatches — that stops naive cross-site scripts,
not `curl`. Auth and limit stay mandatory:

```ts
"use server";
export async function analyseText(input: string) {
  const user = await requireUser();                   // throws → 401 equivalent
  const text = TextSchema.parse(input);               // size limit
  const gate = await checkLimit(`u:${user.id}`);
  if (!gate.ok) return { error: "rate_limited", retryAfter: gate.retryAfter };
  return { result: await callUpstream(text) };
}
```

Never read `model`, `max_tokens` or a target URL from the action argument — the server decides.

### Middleware — coarse brake in front of everything

```ts
// middleware.ts
export async function middleware(req: NextRequest) {
  if (!req.nextUrl.pathname.startsWith("/api/")) return NextResponse.next();
  const ip = req.headers.get("x-real-ip") ?? req.headers.get("x-forwarded-for")?.split(",")[0] ?? "unknown";
  const { success, reset } = await ipLimit.limit(`ip:${ip}`);
  if (!success) return new NextResponse("rate_limited", { status: 429,
    headers: { "Retry-After": String(Math.ceil((reset - Date.now()) / 1000)) } });
  return NextResponse.next();
}
export const config = { matcher: "/api/:path*" };
```

Runs before the function invocation is billed. Keep it to IP-level burst protection; the
per-user limit and the daily quota belong in the handler where the user is known.

### Caching — `'use cache'` (Cache Components)

Enable with `cacheComponents: true` in `next.config.ts`. Then:

```ts
import { cacheLife, cacheTag } from "next/cache";

export async function getForecast(lat: number, lon: number) {
  "use cache";
  cacheLife("hours");            // always set explicitly; default profile revalidates at 15 min
  cacheTag("forecast");
  return fetchForecast(lat, lon); // the paid call — now once per (lat, lon) per hour
}
```

Invalidate after a mutation with `updateTag("forecast")` (in a Server Action) or
`revalidateTag`. Rules that bite in audits:

- Cached functions cannot read `cookies()`, `headers()` or `searchParams` — read outside, pass
  as arguments. Every argument and captured variable becomes part of the cache key, so a
  `userId` argument correctly separates users; a global cache of user data is a bug.
- The default in-memory handler does not persist across serverless instances or deployments.
  For a paid upstream that must not be re-hit after every deploy, use `'use cache: remote'` with
  a cache handler (Redis / KV) or the persistent `input_hash` table from
  `efficiency-and-cost.md`.
- `unstable_cache` still exists for data that must survive deploys without a remote handler.

Next.js also deduplicates identical `fetch()` calls within one render pass — no promise map
needed on the server for that case.

## 2. TanStack Start on Cloudflare Workers

The landing-page stack: TanStack Start, SSR in a Worker (`wrangler.jsonc`), Vite. Secrets go in
with `wrangler secret put NAME`, never through `VITE_*`.

### Server function with middleware

```ts
import { createServerFn, createMiddleware } from "@tanstack/react-start";

const rateLimited = createMiddleware({ type: "function" }).server(async ({ next, context }) => {
  const key = context.user ? `u:${context.user.id}` : `ip:${context.ip}`;
  const { success } = await context.env.API_LIMITER.limit({ key });
  if (!success) throw new Response("rate_limited", { status: 429, headers: { "Retry-After": "60" } });
  return next();
});

export const analyse = createServerFn({ method: "POST" })
  .middleware([authMiddleware, rateLimited])   // auth first, then limit
  .inputValidator(TextSchema)                  // size limit
  .handler(async ({ data }) => callUpstream(data));
```

Register coarse protection once for every request via `createStart` in `src/start.ts`
(`requestMiddleware: [ipLimitMiddleware]`); function middleware handles the per-user limit.
Server functions are called by the client through a generated endpoint — they are as public as
a route and need the same four steps.

### Cloudflare rate-limit binding

```jsonc
// wrangler.jsonc
{ "ratelimits": [{ "name": "API_LIMITER", "namespace_id": "1001", "simple": { "limit": 60, "period": 60 } }] }
```

`period` is 10 or 60 seconds only; the count is per Cloudflare location and eventually
consistent. Use it as the burst brake; keep the daily quota in KV / D1 / a Durable Object /
Upstash. Take the client IP from `cf-connecting-ip` — set by Cloudflare, not forgeable by the
client.

### Static site, no server function?

Then there is nothing to protect on the Worker — every third-party call from the page runs in
the browser, and Level 1 applies in full: only publishable keys with domain restrictions, no
paid API called directly. If a paid call is needed, it becomes a server function.

## 3. Spring Boot REST service (Java)

The Phoenix API (`site/phoenix-api`, Java 21, Spring Boot) logs into Postgres as the
`authenticated` role and lets RLS decide — so auth is the database's job, but limits and quotas
are still the service's. The established library is Bucket4j (token bucket) behind a
`OncePerRequestFilter` or `HandlerInterceptor`; in a multi-instance deployment back it with
Redis (`bucket4j-redis`) instead of a `ConcurrentHashMap`, for the same reason as the in-memory
caveat in `rate-limiting.md`. Verify the current Bucket4j artifact coordinates before quoting
them — they changed between major versions. Answer with `429` and `Retry-After`; keep the
filter ahead of any controller that calls a paid upstream. Expensive Java upstream calls need a
`java.net.http.HttpClient` with `.timeout(Duration)` on the request — the client default is no
timeout.

## 4. Supabase

- **Keys**: publishable `sb_publishable_*` (legacy `anon`) in the client only with RLS on every
  table; secret `sb_secret_*` (legacy `service_role`) server-only — it bypasses all RLS. Legacy
  JWT keys are deprecated, retirement planned by end of 2026. Details in `backend-vs-frontend.md`
  section 5.
- **Counters in Postgres**: the atomic upsert from `rate-limiting.md` section 5 must run inside a
  `security definer` function, otherwise a client with the publishable key can read or reset
  other users' counters through the table.
- **Edge Functions** are the natural home for a paid upstream call: the secret key and the
  third-party key live in the function's secrets, the client calls the function with its
  session JWT, the function verifies the user, checks the limit, then calls out.
- **RLS status is part of the finding**: a publishable key on a table without RLS is a public
  database, regardless of any rate limit.

## 5. Stack-independent checklist

| Question | Where to look |
|---|---|
| Does the paid call run on the server? | Level 1, `backend-vs-frontend.md` |
| Is auth the first line of the handler? | Route handler / action / server function body |
| Is the input size bounded before the call? | Zod / validator schema |
| Is the limit server-side and shared across instances? | Redis / KV / Postgres, not a `Map` |
| Is there a daily quota besides the burst limit? | Second limiter or counter table |
| Does the response carry `429` + `Retry-After`? | Handler return |
| Does the upstream fetch have a timeout? | `AbortSignal.timeout`, `HttpClient.timeout` |
| Is the key absent from the built bundle? | `quick-scan.md` post-build check |
