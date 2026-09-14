# Level 1 — backend, not frontend

Contents:
1. Why frontend keys are always public
2. Recognition patterns in code
3. The migration recipe (frontend call → backend route)
4. Special case: legitimately public keys
5. Special case: Supabase (publishable vs secret, RLS)
6. Securing the own route (auth, origin, CORS)
7. Verification: is the key really gone?

---

## 1. Why frontend keys are always public

Every build step that inlines an environment variable into the client bundle replaces the
placeholder with the **plaintext**. Minification renames variables; it encrypts nothing. After
that it takes:

- DevTools → Network → look at the request headers
- `Ctrl+F` in the loaded JS bundle
- `curl` on the `.js` file and `grep`

The key is therefore not "hard to find", it is published. Treat it as compromised from that
moment: **rotate**, do not merely move it.

The frameworks even mark this explicitly — the prefixes are a warning, not a permission:

| Framework | Prefix that ends up in the bundle |
|---|---|
| Next.js | `NEXT_PUBLIC_` |
| Vite (incl. TanStack Start) | `VITE_` |
| Create React App | `REACT_APP_` |
| Nuxt | `public:` in `runtimeConfig` |
| Expo | `EXPO_PUBLIC_` |

Rule of thumb: *if the name contains "public", the value is public. If no prefix was needed
because the key is hard-coded, it is public all the more.*

## 2. Recognition patterns in code

CRITICAL as soon as one of these appears in a file with `"use client"`, in a React component, a
hook, or anywhere on the browser path:

```ts
// ❌ key literal in the client
const KEY = "sk-proj-abc123...";

// ❌ key pulled into the bundle through a public env prefix
const KEY = process.env.NEXT_PUBLIC_OPENAI_API_KEY;
const KEY = import.meta.env.VITE_STRIPE_SECRET;

// ❌ SDK deliberately run in the browser
const client = new Anthropic({ apiKey: KEY, dangerouslyAllowBrowser: true });

// ❌ direct fetch against a paid third-party service from the component
await fetch("https://api.some-paid-service.com/v1/generate", {
  headers: { Authorization: `Bearer ${KEY}` },
});
```

The parameter name `dangerouslyAllowBrowser` is to be taken literally — it exists for local
prototypes, not for deployments.

## 3. Migration recipe

Always the same five steps:

**Step 1 — rotate the key.** Create a new key at the provider, revoke the old one immediately.
The old value was public, no matter for how short a time.

**Step 2 — keep the key server-side only.** Remove the prefix
(`NEXT_PUBLIC_OPENAI_API_KEY` → `OPENAI_API_KEY`), set it in `.env.local` and in the deployment
secrets (e.g. Vercel Project Settings → Environment Variables, scope: Server; Cloudflare:
`wrangler secret put`). Check that `.env*` is in `.gitignore`.

**Step 3 — create a server route** that wraps the third-party service. The client only receives
the result, never the key.

```ts
// app/api/generate/route.ts   (Next.js App Router, runs server-side)
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const Body = z.object({
  prompt: z.string().min(1).max(2000), // size limit = cost limit
});

export async function POST(req: NextRequest) {
  // 1. Auth first — never let strangers burn the budget
  const user = await getUserFromSession(req);
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  // 2. Validation including size limit
  const parsed = Body.safeParse(await req.json());
  if (!parsed.success) {
    return NextResponse.json({ error: "invalid_body" }, { status: 400 });
  }

  // 3. Rate limit / quota  → see rate-limiting.md
  const gate = await checkLimit(user.id);
  if (!gate.ok) {
    return NextResponse.json(
      { error: "rate_limited" },
      { status: 429, headers: { "Retry-After": String(gate.retryAfter) } },
    );
  }

  // 4. Only now the expensive call — with a timeout
  const upstream = await fetch("https://api.some-paid-service.com/v1/generate", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.SERVICE_API_KEY}`, // stays on the server
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ prompt: parsed.data.prompt, max_tokens: 500 }),
    signal: AbortSignal.timeout(15_000),
  });

  if (!upstream.ok) {
    // do not pass third-party error details through 1:1
    return NextResponse.json({ error: "upstream_failed" }, { status: 502 });
  }

  const data = await upstream.json();
  return NextResponse.json({ result: data.output });
}
```

**Step 4 — switch the client.** It calls only its own route now:

```ts
// ✅ the client knows no key any more
const res = await fetch("/api/generate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ prompt }),
});
if (res.status === 429) {
  const wait = res.headers.get("Retry-After");
  showToast(`Zu viele Anfragen. Bitte in ${wait}s erneut versuchen.`); // product copy stays German
  return;
}
```

**Step 5 — verify** (see section 7).

## 4. Special case: legitimately public keys

Some keys belong in the frontend — the provider designed them for it and secures them through
origin / domain restrictions. Typical:

- Stripe **publishable** key (`pk_...`) — yes. Stripe **secret** key (`sk_...`) — never.
- Google Maps JS API key — yes, **but** only with an HTTP referrer restriction and an active
  budget alert, otherwise someone else drives around on your map bill.
- Analytics / feature-flag client keys — usually yes, write-only.
- Supabase publishable key (`sb_publishable_...`, legacy `anon`) — yes, but only with RLS
  (section 5).

Test question: *can this key read, write or bill anything the owner of the browser is not
allowed to do anyway?* If yes → backend.

Even for legitimately public keys: set the domain restriction and configure a usage limit in the
provider dashboard. Otherwise the key is placed correctly but is still a cost risk.

## 5. Special case: Supabase

Supabase has two key formats. Verified against the Supabase API-keys docs on 2026-09-14:

| Key | Format | Placement | Condition |
|---|---|---|---|
| Publishable | `sb_publishable_...` (legacy JWT `anon`) | Client allowed | **Only** with RLS enabled on every table |
| Secret | `sb_secret_...` (legacy JWT `service_role`) | Server only | Bypasses **every** RLS policy — in the client it is full database access for every visitor |

The legacy `anon` / `service_role` JWT keys are deprecated; Supabase plans to retire them by the
end of 2026. Both systems work side by side until the old keys are disabled in the dashboard.
Audit rule: treat `anon` exactly like a publishable key and `service_role` exactly like a secret
key — the placement rules do not change with the format.

```ts
// ❌ immediate total loss of access control
const supabase = createClient(url, process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY!);

// ✅ client: publishable key, protection comes from RLS
const supabase = createClient(url, process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!);

// ✅ server route: secret key only here, never exported
const admin = createClient(url, process.env.SUPABASE_SECRET_KEY!);
```

RLS without policies means "nothing visible" — RLS disabled means "everything visible". A
publishable key on a table without RLS equals a public database. In the audit always check both
together: key placement **and** RLS status.

## 6. Securing the own route

The own route is now the attack surface — it is exactly as public as the page itself. Moving the
call only protects the key, not the budget.

- **Auth before the expensive part.** Session check as the first line of the handler.
- **Rate limit and quota.** See `rate-limiting.md`. Without it the route is merely a free proxy
  in front of your paid service.
- **No open CORS.** `Access-Control-Allow-Origin: *` on a route that costs money invites foreign
  sites to share it. Allow only your own origins.
- **Origin / Referer check** as an additional hurdle against simple scripts — not real protection
  (headers can be forged), but cheap. Server Actions in Next.js and server functions in TanStack
  Start do this for their own POSTs; a plain Route Handler does not.
- **No pass-through parameters.** If the client may freely choose model, `max_tokens`, target
  size or even the target URL, it also chooses your cost. The server sets the expensive
  parameters; the client picks from an allowlist at most.

```ts
// ❌ the client determines the cost
const { model, maxTokens } = await req.json();

// ✅ the server determines, the client chooses from an allowlist
const TIERS = { fast:    { model: "small", maxTokens: 300 },
                precise: { model: "large", maxTokens: 1200 } } as const;
const tier = TIERS[parsed.data.tier] ?? TIERS.fast;
```

## 7. Verification

After the migration, prove that the key is really no longer shipped:

```bash
# build, then search the bundle for the key prefix
npm run build
grep -r "sk-" .next/static dist 2>/dev/null | head
grep -r "SERVICE_ROLE\|sb_secret_" .next/static dist 2>/dev/null | head
```

No hit = the key stayed server-side. Additionally in the browser: open the Network tab, trigger
the feature, check that only the own route appears and no `Authorization` header with a real
secret goes out.

This check belongs to Agent 3 (Test/QA) — it is the only proof that does not rely on trust.
