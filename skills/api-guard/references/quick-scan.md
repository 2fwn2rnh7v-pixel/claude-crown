# Quick scan — first look at existing code

Goal: know within minutes where the problems are, instead of guessing file by file. All
commands are read-only. Keep the order — Level 1 first, because that is where the critical hits
are.

`scripts/api_scan.py` runs every static pattern below in one go (pure Python, no ripgrep needed)
and prints the summary block at the end of this file. Use the commands here when a single
pattern needs refining, or when only ripgrep is at hand. If `rg` is missing, the patterns also
work with `grep -rn`.

---

## Level 1 — secrets in the client path

```bash
# public env prefixes with suspicious names
rg -n "(NEXT_PUBLIC|VITE|REACT_APP|EXPO_PUBLIC)_[A-Z_]*(KEY|SECRET|TOKEN|PASSWORD|SERVICE_ROLE)" src app

# SDKs deliberately run in the browser
rg -n "dangerouslyAllowBrowser" src app

# key-like literals in source
rg -n "['\"](sk-|sk_live|rk_live|sb_secret_|xoxb-|ghp_|AIza)" src app

# direct third-party calls from client components
rg -ln '"use client"' src app | xargs rg -n "fetch\(\s*['\"]https?://" 2>/dev/null

# service_role / secret key outside server directories
rg -n "service_role|SERVICE_ROLE|sb_secret_" src app --glob '!**/api/**' --glob '!**/server/**'
```

**Cross-check after the build** — this is the only reliable proof:

```bash
npm run build
rg -n "sk-|SERVICE_ROLE|sb_secret_|sk_live" .next/static dist build 2>/dev/null | head -20
```

Every hit here is CRITICAL: the key is shipped and must be rotated.

## Level 2 — endpoints without limit

```bash
# list all route handlers / server actions / server functions
rg -l "export async function (GET|POST|PUT|PATCH|DELETE)|\"use server\"|createServerFn" app src

# handlers in which no limit occurs
rg -L "ratelimit|rateLimit|checkLimit|Ratelimit|throttle|\.limit\(" \
   --glob '**/api/**/route.ts' --glob '**/api/**/*.ts' app src

# handlers without a recognisable auth check
rg -L "getUser|getSession|auth\(|requireUser|getServerSession|getClaims" \
   --glob '**/api/**/route.ts' app src
```

Cross-reference: which of these routes call a paid service? Exactly those are HIGH or CRITICAL.

## Level 3 — abuse and cost risks

```bash
# fetches without timeout / AbortSignal
rg -n "fetch\(" app src -A 4 | rg -B 2 -v "signal|AbortSignal" | rg "fetch\("

# polling loops
rg -n "setInterval\(" app src

# useEffect without a dependency array (fires on every render)
rg -n "useEffect\(\s*\(\s*\)\s*=>\s*\{[\s\S]*?\}\s*\)\s*;" -U app src

# retry logic — present, but without backoff?
rg -n "retry|retries|maxRetries" app src

# the client determines expensive parameters
rg -n "(model|maxTokens|max_tokens|quality|resolution)\s*[:=]\s*(body|req|params|searchParams)" app src
```

## Level 4 — efficiency

```bash
# await inside loops → N+1 suspicion
rg -n "for\s*\(.*\)\s*\{" app src -A 6 | rg "await "
rg -n "\.map\(async" app src

# search fields without debounce
rg -ln "onChange" app src | xargs rg -L "debounce|useDeferredValue|throttle" 2>/dev/null

# is there any caching at all?
rg -n "revalidate|Cache-Control|stale-while-revalidate|unstable_cache|cacheTag|cacheLife|use cache" app src
```

## Runtime check

Complementary to the static scan, often more revealing:

1. Browser DevTools → Network → filter `Fetch/XHR`, use the app normally. Count: how many
   requests for a single user action? Does the same request repeat?
2. Open the provider dashboard: consumption by endpoint and time of day. Even load around the
   clock points to polling or cron jobs, not to users.
3. Divide consumption by active users. If the value is clearly above what a human can trigger,
   something runs automatically.

## Summarise the result

After the scan, note briefly before starting the assessment:

```
Scanned: <directories>
Level 1: X hits (Y of them confirmed in the built bundle)
Level 2: X routes total, Y without limit, Z of those with a paid upstream call
Level 3: X polling sites, Y fetches without timeout, Z retry sites without backoff
Level 4: X N+1 suspects, Y search fields without debounce, caching: present / absent
```

Only then write out the individual findings — with this overview the prioritisation is already
settled.
