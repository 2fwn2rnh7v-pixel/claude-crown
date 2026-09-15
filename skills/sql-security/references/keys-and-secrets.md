# Keys and Secrets

Contents:
1. Which keys exist
2. Where each key belongs
3. .env layout
4. Separating client and server clients (TypeScript)
5. Deployment
6. Leak — response plan
7. Rotation as routine

---

## 1. Which keys exist

| Key | Format | Privileges | May be visible? |
|-----|--------|-----------|-----------------|
| Publishable key | `sb_publishable_…` | low, RLS applies | **yes**, belongs in the frontend |
| Secret key | `sb_secret_…` | full, **bypasses RLS** | no, never |
| anon (legacy) | JWT | same as publishable | yes |
| service_role (legacy) | JWT | same as secret | no |
| Postgres password | string | direct database access | no |
| Management API token | `sbp_…` | project administration | no |
| JWT signing key | key pair | allows forging tokens | no |

Legacy `anon` and `service_role` are being retired by the end of 2026. Projects created from
November 2025 onward no longer have them. Build new work on the new keys; on existing projects
both work in parallel, so clients can be migrated one at a time.

One advantage of the new keys: a project can have several secret keys — for example one per
backend component. That way a single key can be rotated without taking everything else down.

Sources:
- https://supabase.com/docs/guides/getting-started/api-keys
- https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys
- https://github.com/orgs/supabase/discussions/29260

---

## 2. Where each key belongs

```
Browser / React component / mobile app
  └─ publishable key             ✅  (RLS protects the data)

Next.js server component / route handler / API route
  └─ publishable key + user session   ✅  preferred
  └─ secret key                       ⚠️  only where RLS must deliberately be bypassed

Edge function / cron / worker / migration script
  └─ secret key                  ✅

Git repository, CI logs, screenshots, chat messages
  └─ nothing secret              ✅
```

Note that even on the server the secret key is not the default choice. Working server-side with
the user's token keeps RLS protection intact. The secret key is for work that deliberately runs
outside user permissions: cron jobs, admin tooling, data imports.

Every use of the secret key should carry a comment explaining why. An uncommented secret-key
client is a review finding.

---

## 3. .env layout

```bash
# .env.local — NOT in the repository
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_...

# server-side only (no NEXT_PUBLIC_ prefix!)
SUPABASE_SECRET_KEY=sb_secret_...
DATABASE_URL=postgresql://...
```

```bash
# .env.example — IN the repository, placeholders only
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
SUPABASE_SECRET_KEY=
```

```gitignore
# .gitignore
.env
.env.*
!.env.example
```

The prefix rule is absolute: anything with `NEXT_PUBLIC_` (or `VITE_` in Vite, `EXPO_PUBLIC_`
in Expo) is written into the JavaScript bundle at build time and readable in the browser. No
server setup and no build trick changes that.

### Verify that nothing secret is in the bundle

```bash
npm run build
grep -r "sb_secret" .next/ 2>/dev/null && echo "MATCH — ROTATE IMMEDIATELY"
grep -rn "service_role" src/ app/ components/
git log -p --all -S 'sb_secret' | head        # was one ever committed?
```

The first command belongs in CI. A match should fail the build.

---

## 4. Separating client and server clients

The most reliable protection is structural: two files, one of which the client physically
cannot import.

```ts
// src/lib/supabase/client.ts   — for browser components
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
  )
}
```

```ts
// src/lib/supabase/admin.ts    — SERVER ONLY
import 'server-only'                    // build fails if a client component imports this
import { createClient } from '@supabase/supabase-js'

export function createAdminClient() {
  const key = process.env.SUPABASE_SECRET_KEY
  if (!key) throw new Error('SUPABASE_SECRET_KEY is missing')

  // WARNING: bypasses RLS completely.
  // Only for: cron jobs, admin panel, data import. Justify every use.
  return createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  })
}
```

The `server-only` package produces a build error as soon as this file reaches a client
component. That is far more effective than a convention or a review comment.

### Validate environment variables once, centrally

```ts
// src/lib/env.ts
import { z } from 'zod'

const schema = z.object({
  NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
  NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: z.string().startsWith('sb_publishable_'),
  SUPABASE_SECRET_KEY: z.string().startsWith('sb_secret_').optional(),
})

export const env = schema.parse(process.env)
```

The `startsWith` check catches exactly the mistake where the secret key was pasted into the
public variable — at startup, not in production.

---

## 5. Deployment

- Store secrets in the platform (Vercel → Project Settings → Environment Variables), separated
  by Production / Preview / Development.
- Preview deployments must **not** get production secrets. Otherwise every feature-branch URL
  is wired to the real database.
- For Supabase edge functions: `supabase secrets set NAME=value`, read with `Deno.env.get()`.
  Never hardcode them in the function, which lives in the repository.
- Never print secrets into build logs. `console.log(process.env)` is a leak.

```bash
supabase secrets set RESEND_API_KEY=…
supabase secrets list      # shows names, not values
```

---

## 6. Leak — response plan

Once a secret key has been exposed (commit, screenshot, log, chat message), treat it as
compromised. Git history remains readable even after a revert. Order matters:

```
1. Create a NEW key (dashboard → Settings → API Keys)
2. Deploy the new key to all environments
3. Only THEN deactivate the old key
4. Check the logs: was there unfamiliar access since the leak?
5. If the window is unclear or access is visible:
   invalidate user sessions, review the affected data, clarify any reporting obligations
6. Remove the secret from git history (git filter-repo / BFG) — as the LAST step, not the
   first. Removing it does not invalidate the key.
7. Fix the cause: pre-commit hook (gitleaks), CI check, review .gitignore
```

Doing step 3 before step 2 is the most common mistake — the app goes down immediately. With
the new keys the old and new key can run side by side, which removes that window entirely.

For legacy keys: regenerating the JWT secret invalidates **all** existing tokens instantly and
severs all connections. That is a planned outage, not a side effect — another reason to move
to the new keys.

Source: https://supabase.com/docs/guides/troubleshooting/rotating-anon-service-and-jwt-secrets-1Jq6yd

---

## 7. Rotation as routine

- Rehearse rotation once while nothing is on fire.
- One secret key per backend component, so each can be rotated independently.
- Put it in the calendar (twice a year, say) instead of "when something happens".
- Anyone who leaves the project retains whatever they have seen until it is rotated.

### Add secret scanning

```bash
# pre-commit hook or CI
gitleaks detect --no-banner --redact
```

A hit blocks the commit. Ten minutes of setup prevents the most expensive class of mistake in
this whole skill.
