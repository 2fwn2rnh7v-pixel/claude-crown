# Rate Limiting

Contents:
1. Why RLS is not enough
2. Layer 1 — Auth
3. Layer 2 — your own endpoints
4. Layer 3 — the database
5. Cost protection
6. What the frontend should do on a 429

---

## 1. Why RLS is not enough

Row level security answers "**may** this user touch this row". It does not answer "**how
often**". A signed-in user with a valid token can query their own data ten thousand times a
minute — entirely within the rules, and still a problem:

- database load and connection exhaustion
- egress and compute cost
- scraping of the data the user is allowed to see
- brute force against logins and OTP codes

Hence three layers that work independently of each other.

---

## 2. Layer 1 — Auth

Supabase Auth limits its own endpoints using a token bucket per IP address. Typical capacity is
around 30 requests; short bursts are tolerated, sustained excess is answered with
**429 Too Many Requests**.

Configurable under **Dashboard → Authentication → Rate Limits** or via the Management API:

```bash
curl -X PATCH "https://api.supabase.com/v1/projects/$PROJECT_REF/config/auth" \
  -H "Authorization: Bearer $SUPABASE_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "rate_limit_email_sent": 10,
        "rate_limit_sms_sent": 10,
        "rate_limit_verify": 10,
        "rate_limit_token_refresh": 10,
        "rate_limit_otp": 10,
        "rate_limit_anonymous_users": 10,
        "rate_limit_web3": 10
      }'
```

Two practical notes:

- If a server or proxy sits in front of Supabase, every request arrives from **one** IP, so
  Supabase ends up rate limiting the whole app. In that case forward the real user IP via the
  `Sb-Forwarded-For` header. That only works with a secret key and must be enabled for the
  project.
- Keep email and SMS limits low. Every SMS costs money, and that path is a favourite abuse
  target.

Also worth enabling: **Authentication → Attack Protection** (CAPTCHA, leaked-password
protection).

Source: https://supabase.com/docs/guides/auth/rate-limits

---

## 3. Layer 2 — your own endpoints

The REST layer (PostgREST) has **no** built-in limit per table or per user. If you need one,
build it in one of the following places.

### a) Middleware (simple, per instance)

Good enough for small deployments and as an immediate measure. Note that in serverless
environments each instance has its own memory, so the limit is only approximate.

```ts
// src/lib/rate-limit.ts
const hits = new Map<string, { count: number; reset: number }>()

export function checkLimit(key: string, max = 20, windowMs = 60_000) {
  const now = Date.now()
  const entry = hits.get(key)

  if (!entry || now > entry.reset) {
    hits.set(key, { count: 1, reset: now + windowMs })
    return { allowed: true, remaining: max - 1 }
  }
  if (entry.count >= max) {
    return { allowed: false, remaining: 0, retryAfter: Math.ceil((entry.reset - now) / 1000) }
  }
  entry.count++
  return { allowed: true, remaining: max - entry.count }
}
```

```ts
// app/api/orders/route.ts
export async function POST(req: Request) {
  const { data: { user } } = await supabase.auth.getUser()
  const key = user?.id ?? req.headers.get('x-forwarded-for') ?? 'unknown'

  const limit = checkLimit(`create-order:${key}`, 10, 60_000)
  if (!limit.allowed) {
    return new Response('Too many requests', {
      status: 429,
      headers: { 'Retry-After': String(limit.retryAfter) },
    })
  }
  // … actual work
}
```

Limit by user ID wherever possible; use IP only as a fallback, since shared networks and mobile
carriers put many people behind one address.

### b) Distributed limit with Redis (production grade)

```ts
import { Ratelimit } from '@upstash/ratelimit'
import { Redis } from '@upstash/redis'

const limiter = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(10, '60 s'),
  prefix: 'myapp',
})

const { success, reset } = await limiter.limit(`export:${user.id}`)
if (!success) return new Response('Rate limit reached', { status: 429 })
```

This holds across all instances and works the same way inside Supabase edge functions.

Source: https://supabase.com/docs/guides/functions/examples/rate-limiting

### c) Pre-request function in the database

Supabase can run a Postgres function before every Data API request (registered through the
`pgrst.db_pre_request` setting; it applies to the Data API / PostgREST only — not to Realtime or
Storage). That allows enforcing a
limit inside the database itself, which is useful for writes that come straight from the client
and have no route of their own.

The shape: a counter table keyed by user and time window; the function checks it and raises an
exception when the limit is exceeded. Important: this function runs on **every** request, so it
must be very fast and the counter table needs an index.

Source: https://supabase.com/docs/guides/api/securing-your-api

---

## 4. Layer 3 — the database

### Cap query runtime

```sql
alter role authenticated set statement_timeout = '8s';
alter role anon          set statement_timeout = '5s';
alter role app_backend   set statement_timeout = '30s';
```

Otherwise a single runaway query can block connections indefinitely. This timeout is the
cheapest insurance available.

Also useful:

```sql
alter role authenticated set idle_in_transaction_session_timeout = '30s';
```

Open transactions hold locks and prevent cleanup of old row versions.

### Cap connections

```sql
alter role import_job connection limit 5;
```

In serverless environments, always connect through the pooler (Supavisor/PgBouncer) rather than
directly. Every function instance holding its own direct connection exhausts the pool fast.
Rule of thumb: do not push the pool size past about 40 % of max connections when the Data API
is heavily used — Auth, Storage and PostgREST need connections too.

Source: https://supabase.com/docs/guides/database/connecting-to-postgres/pooling-and-limits

### Cap result size

Supabase lets you configure a maximum number of rows per request (Settings → API → Max rows).
That stops a `select` without a `limit` from accidentally transferring an entire table. In
addition, always set `.limit()` or `.range()` in the client.

---

## 5. Cost protection

Rate limiting is also cost control. On top of it:

- Enable the spend cap and budget alerts on the Supabase project.
- Limit expensive operations (exports, PDF generation, bulk email, AI calls) **individually**,
  independently of the general limit.
- Serve images and files through Storage with transformation limits rather than pushing base64
  through the database.
- Use signed URLs with short expiry instead of public buckets.

---

## 6. What the frontend should do on a 429

A limit helps little if the client retries immediately on rejection.

```ts
async function withBackoff<T>(fn: () => Promise<T>, attempts = 3): Promise<T> {
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn()
    } catch (e: any) {
      if (e?.status !== 429 || i === attempts - 1) throw e
      const wait = Math.min(2 ** i * 1000 + Math.random() * 300, 8000)
      await new Promise(r => setTimeout(r, wait))
    }
  }
  throw new Error('unreachable')
}
```

Three rules:

1. Back off exponentially, with some jitter — otherwise every client returns at the same moment.
2. Respect `Retry-After` from the response when present.
3. Show the user a comprehensible message ("too many requests, please wait a moment"), not a
   raw status code. Disable buttons while a request is in flight — repeated clicking is the most
   common cause of self-inflicted rate limits.
