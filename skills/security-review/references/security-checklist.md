# Security checklist — 10 categories, TypeScript patterns

Read for every Mode A review. Each category: what to check, the attacker's move, the
TypeScript correction. Severity anchors are given per category; adjust to the data at stake.
OWASP Top 10:2025 mapping noted per category (verified 2026-09-14 against top10.owasp.org).

Order inside every handler, regardless of category: **authenticate → authorise → validate →
rate-limit → do the work → encode the output**. Anything checked after the work protects nothing.

---

## 1. Input validation & output encoding (OWASP A05 Injection, A06 Insecure Design)

Check:
- Is every external input (body, query, params, headers, cookies, file names, webhooks, URL
  fragments, `postMessage`) validated against a schema **before** use?
- Are types, lengths, ranges, enums and formats enforced, not only presence?
- Is validation server-side? Client-side validation is UX, not security.
- Is output encoded for its context (HTML, attribute, URL, JS, SQL)?
- Are unknown keys rejected (`.strict()`) so mass assignment cannot smuggle `role: "admin"`?

Attacker: sends `{"amount": -500}`, a 10 MB string, `{"role": "admin"}`, or `<img onerror>` in a
name field.

```ts
// ❌ trusting the body
const { email, amount, role } = await req.json();
await db.user.update({ where: { email }, data: { amount, role } });

// ✅ schema first, allowlist of fields, bounded values
import { z } from "zod";
const Body = z.object({
  email: z.string().email().max(254),
  amount: z.number().int().min(0).max(1_000_000),
}).strict();                                   // unknown keys → 400, no mass assignment
const parsed = Body.safeParse(await req.json());
if (!parsed.success) return json({ error: "invalid_body" }, 400);
```

Output encoding: React escapes text children by default; the escape hatches are
`dangerouslySetInnerHTML`, `href={userValue}` (allow only `http(s):` — `javascript:` URLs are
XSS), and building HTML strings server-side. For rich text sanitise with DOMPurify (or
`isomorphic-dompurify` on the server) with an explicit allowlist.

Severity anchors: unvalidated write path → HIGH; missing length limit on a paid or stored
field → MEDIUM; missing `.strict()` on a model with privileged fields → HIGH.

## 2. Authentication & sessions (OWASP A07 Authentication Failures)

Check:
- Password hashing with Argon2id (preferred) or bcrypt with a work factor ≥ 12; never MD5/SHA
  alone, never a home-made scheme.
- Login and password reset rate-limited per IP **and** per account; generic error messages
  (no "user not found" vs "wrong password").
- Sessions: `HttpOnly`, `Secure`, `SameSite=Lax` or `Strict` cookies; session ID rotated on
  login and privilege change; server-side invalidation on logout.
- JWTs: algorithm pinned (`alg` from the token is never trusted), short expiry, `aud`/`iss`
  verified, secret ≥ 256 bit, refresh tokens rotated and revocable.
- Reset tokens: random (≥ 128 bit), single-use, expiring, compared in constant time.
- MFA or step-up for admin actions where the product allows.

Attacker: credential stuffing against `/login` without limit; replays a reset link; forges a
JWT with `alg: none`; steals a cookie without `HttpOnly` via XSS.

```ts
// ❌
const ok = user.passwordHash === sha256(password);
const token = jwt.sign({ id: user.id }, "secret");

// ✅
import { hash, verify } from "@node-rs/argon2";           // Argon2id defaults
const ok = await verify(user.passwordHash, password);
const token = await new SignJWT({ sub: user.id })        // jose
  .setProtectedHeader({ alg: "HS256" })
  .setIssuer("app").setAudience("app").setExpirationTime("15m")
  .sign(secretKey);
// verify with jwtVerify(token, secretKey, { algorithms: ["HS256"], issuer: "app", audience: "app" })
```

Supabase Auth / NextAuth / Clerk / Lucia already implement most of this — the review then checks
that the library is used as documented (session read on the server, not trusted from the client).

Severity anchors: weak hashing or unpinned JWT alg → CRITICAL; no login rate limit → HIGH;
cookie flags missing → MEDIUM.

## 3. Authorisation & access control (OWASP A01 Broken Access Control)

Check:
- Every read and write checks **who** may touch **this** record, not only whether someone is
  logged in. IDOR: `GET /invoices/123` must verify the invoice belongs to the caller's tenant.
- Role checks happen on the server, per request, from the session — never from a client-sent
  `role` field or a hidden form input.
- Privilege escalation paths: can a user edit their own `role`, `tenant_id`, `owner_id`?
- Multi-tenant: is the tenant taken from the session, never from the URL or body? With
  Postgres RLS: is RLS enabled on **every** table, and does the service/secret key stay
  server-only?
- Server Actions and server functions are endpoints: same checks as routes.

Attacker: changes the ID in the URL; posts `tenant_id` of another company; calls an admin
Server Action directly by its ID.

```ts
// ❌ authenticated ≠ authorised
export async function deleteInvoice(id: string) {
  "use server";
  const user = await requireUser();
  await db.invoice.delete({ where: { id } });
}

// ✅ scope every query to the caller
export async function deleteInvoice(id: string) {
  "use server";
  const { user, tenantId } = await requireTenant();      // from the session
  requirePermission(user, "invoices.delete");
  const result = await db.invoice.deleteMany({ where: { id, tenantId } });
  if (result.count === 0) throw new NotFoundError();      // no leak whether it exists elsewhere
}
```

Severity anchors: IDOR on any personal or financial record → CRITICAL; missing role check on an
admin action → CRITICAL; tenant from the URL → CRITICAL.

## 4. Injection risks (OWASP A05 Injection)

Check:
- SQL: parameterised queries / tagged templates only; no string concatenation into `raw` /
  `executeRaw`; ORM `where` built from validated fields, never from a spread of user JSON.
- Command: `execFile` with an argument array, never `exec` with a string; no user input in
  shell commands at all if avoidable.
- Template / SSTI: no user input into template engines' code paths.
- XSS: see category 1; also `innerHTML`, `document.write`, `eval`, `new Function`.
- NoSQL / query operators: reject objects where strings are expected (`{ $gt: "" }`).
- Path and header injection: newlines in headers, user input in `Location`.
- LLM prompts: user text goes into the user turn, never concatenated into the system prompt;
  tool results are data.

Attacker: `' OR 1=1 --`, `; rm -rf /`, `{"$ne": null}`, a `<script>` in a comment.

```ts
// ❌
await prisma.$queryRawUnsafe(`SELECT * FROM users WHERE email = '${email}'`);
exec(`convert ${fileName} out.png`);

// ✅
await prisma.$queryRaw`SELECT * FROM users WHERE email = ${email}`;   // parameterised
execFile("convert", [safeName, "out.png"], { timeout: 10_000 });      // no shell
```

Severity anchors: any SQL / command injection reachable from a request → CRITICAL; stored XSS →
HIGH; reflected XSS → MEDIUM/HIGH.

## 5. Error handling & logging (OWASP A10 Mishandling of Exceptional Conditions, A09 Logging and Alerting Failures)

Check:
- No stack traces, SQL text, file paths or upstream error bodies reach the client.
- Failures fail **closed**: an exception in the auth check must not fall through to the work.
- Every `catch` either handles or rethrows — no swallowed errors that leave a half-written state.
- Security events are logged with context: login failures, permission denials, rate-limit hits,
  admin actions, key rotation. Not logged: passwords, tokens, full card numbers, session IDs.
- Logs are structured and searchable; an alert exists for spikes in 401/403/429.

Attacker: reads the stack trace to learn the ORM, table names and file layout; triggers an
exception to bypass a check that only ran in the `try`.

```ts
// ❌ leaks internals, fails open
try { await authorise(user); } catch {}
try { ... } catch (e) { return json({ error: String(e) }, 500); }

// ✅ fail closed, generic outward, detailed inward
const authz = await authorise(user).catch(() => null);
if (!authz) return json({ error: "forbidden" }, 403);
try { ... } catch (e) {
  logger.error({ evt: "invoice.create.failed", userId: user.id, err: serialiseSafely(e) });
  return json({ error: "internal" }, 500);
}
```

Severity anchors: fail-open auth → CRITICAL; stack trace to client → MEDIUM; no logging of
auth failures → MEDIUM.

## 6. Configuration, secrets & cryptography (OWASP A02 Security Misconfiguration, A04 Cryptographic Failures)

Check:
- No secrets in source, in `NEXT_PUBLIC_*` / `VITE_*`, in client bundles, in logs, in git
  history (`git log -p | grep -i secret` once). `.env*` ignored. Secrets rotated after any leak.
- Debug modes, default credentials, verbose errors, directory listings off in production.
- Security headers present: `Content-Security-Policy` (nonce-based for inline scripts),
  `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`,
  `Permissions-Policy`; CORS restricted to own origins, never `*` with credentials.
- Cryptography: `crypto.randomBytes` / `crypto.randomUUID` for tokens, never `Math.random`;
  AES-GCM or libsodium for encryption; SHA-256+ for integrity; Argon2id/bcrypt for passwords;
  constant-time comparison (`crypto.timingSafeEqual`) for secrets; TLS everywhere.
- Keys have an owner, a rotation path and a scope (least privilege per key).

Attacker: finds `sk_live_…` in the JS bundle; guesses a `Math.random` reset token; downgrades to
HTTP where HSTS is missing.

```ts
// ❌
const token = Math.random().toString(36).slice(2);
if (provided === stored) { ... }

// ✅
const token = crypto.randomBytes(32).toString("base64url");
const a = Buffer.from(provided), b = Buffer.from(stored);
if (a.length === b.length && crypto.timingSafeEqual(a, b)) { ... }
```

Key placement (frontend vs backend) in depth: the `api-guard` skill, `references/backend-vs-frontend.md`.

Severity anchors: secret in client or repo → CRITICAL; `Math.random` for a security token →
HIGH; missing CSP / HSTS → MEDIUM.

## 7. File access & paths (OWASP A01, A05)

Check:
- Path traversal: user-supplied names are never joined into a path without normalising and
  verifying the result stays inside the intended directory.
- Uploads: size limit before reading the body, MIME type checked by content (magic bytes), not
  by extension or the client's `Content-Type`; file name replaced by a generated one; stored
  outside the web root or in object storage with private ACL; images re-encoded; SVG treated as
  active content.
- Downloads: `Content-Disposition: attachment` for user files; no execution of uploaded content.
- Temp files cleaned up; archives extracted with a size and path check (zip slip).

Attacker: uploads `../../.env` as a file name; a 5 GB file; an SVG with a script; a zip that
extracts over `/etc/passwd`.

```ts
// ❌
const target = path.join(UPLOAD_DIR, req.query.name);

// ✅
const base = path.resolve(UPLOAD_DIR);
const target = path.resolve(base, path.basename(String(req.query.name)));
if (!target.startsWith(base + path.sep)) return json({ error: "invalid_path" }, 400);
```

Severity anchors: traversal reachable from a request → CRITICAL; unbounded upload → HIGH;
extension-only type check → MEDIUM.

## 8. Dependencies (OWASP A03 Software Supply Chain Failures, A08 Software or Data Integrity Failures)

Check:
- Lockfile committed and used in CI (`npm ci` / `bun install --frozen-lockfile`).
- `npm audit` / `bun audit` / Dependabot or Renovate active; known CVEs triaged, not ignored.
- No unmaintained packages on the security path (auth, crypto, parsing, sanitising).
- Install scripts and postinstall hooks reviewed; scoped registry tokens; `--ignore-scripts` in
  CI where possible.
- Integrity: subresource integrity for third-party scripts, signed releases / provenance where
  the ecosystem offers it, no `curl | sh` in build steps.
- Version pinning for build tooling in CI images.

Attacker: publishes a typosquat or hijacks a maintainer account; a postinstall script exfiltrates
the CI token.

Severity anchors: known critical CVE in a reachable package → HIGH/CRITICAL; no lockfile in CI →
MEDIUM; unpinned third-party script without SRI → MEDIUM.

## 9. Business logic & abuse (OWASP A06 Insecure Design)

Check:
- Can steps be skipped or reordered (pay → confirm → ship; verify e-mail → activate)?
- Are prices, quantities, discounts, totals computed server-side from server data — never
  accepted from the client?
- Idempotency on payments and bookings (double submit, retries).
- Race conditions on balance, stock, vouchers: atomic updates or row locks, not
  read-then-write.
- Rate limits and quotas on anything that costs money, sends messages, or enumerates data —
  the `api-guard` skill covers this level in depth.
- Enumeration: user IDs, invoice numbers, e-mail existence via timing or messages.
- Money in floats: never; integer minor units or a decimal type.

Attacker: replays the "apply voucher" request 50 times; posts `price: 0.01`; fires two
withdrawals in parallel.

```ts
// ❌ read-then-write race
const acc = await db.account.findUnique({ where: { id } });
if (acc.balance >= amount) await db.account.update({ where: { id }, data: { balance: acc.balance - amount } });

// ✅ atomic, conditional
const r = await db.account.updateMany({
  where: { id, balance: { gte: amount } },
  data: { balance: { decrement: amount } },
});
if (r.count === 0) throw new InsufficientFundsError();
```

Severity anchors: client-controlled price / total → CRITICAL; race on money or stock → HIGH;
missing idempotency on payment → HIGH.

## 10. Security tests

Check:
- Negative tests exist for every guard: wrong user, wrong tenant, missing role, expired token,
  oversized input, malformed JSON — each must return the right 4xx and not perform the action.
- Injection payloads in the test data for every free-text field.
- Rate-limit test: N parallel requests → expected count of 429.
- Authorisation matrix test: roles × actions, generated, not hand-picked.
- Static checks in CI: type-check, lint with security rules, dependency audit, secret scanning
  (gitleaks or the platform's scanner), a bundle grep for key prefixes after build.
- Tests run against the same RLS policies / middleware as production, not a mocked auth layer
  that always says yes.

```ts
test("other tenant cannot delete invoice", async () => {
  const res = await asUser(tenantB.user).post("/api/invoices/delete", { id: tenantA.invoice.id });
  expect(res.status).toBe(404);                              // not 403: existence not leaked
  expect(await db.invoice.findUnique({ where: { id: tenantA.invoice.id } })).not.toBeNull();
});
```

Severity anchors: no negative test on an auth/authz guard that a finding touched → MEDIUM;
auth mocked away in the test suite → HIGH (false sense of coverage).

---

## Quick self-check before the summary

- Every finding has file + line, an attack scenario and a before/after code block.
- CRITICAL findings are reachable from a request without special preconditions — otherwise
  downgrade and say why.
- Positive observations named: a review that lists only problems is incomplete.
- Cross-references used instead of duplicated: rate limiting, quotas and key placement →
  `api-guard`; both skills share the Mode A/B contract and the severity scale.
