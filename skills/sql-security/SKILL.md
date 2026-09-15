---
name: sql-security
description: >
  Securing the database layer of a TypeScript app on Postgres/Supabase — everything outside the
  row level. Covers separating and hiding API keys (publishable vs. secret, .env, key rotation
  after a leak), real account and role management (CREATE ROLE, group and login roles),
  granting privileges with GRANT/REVOKE and default privileges, who may create and drop tables
  and databases, rate limiting, and SQL injection prevention.
  ALWAYS use this skill when: keys, tokens, .env files or secrets appear; the user mentions
  "privileges", "roles", "permission", "GRANT", "access", "admin", "service_role", "anon key",
  "rate limit", "abuse", "injection", "DROP" or "who is allowed to"; an endpoint, edge function
  or server script touches the database; a key ended up in client code or the frontend; a new
  table needs grants. Also trigger when client code talks to the database directly, even if
  security was never mentioned.
---

# SQL Security — Keys, Roles, Privileges, Limits

This skill protects the layers **before** and **around** row level security. Row level security
itself — which user may see which row — lives in `rls-security`.

The governing sentence:

> **The client must never be able to do more than the worst imaginable user should be able to do.**
> Anything that reaches the browser is public: code, keys, network traffic.

---

## Four areas

| Area | Core question | Reference |
|------|---------------|-----------|
| Keys and secrets | Which key is allowed where? | `references/keys-and-secrets.md` |
| Roles and privileges | Who may perform which operation on which object? | `references/roles-and-privileges.md` |
| Rate limiting | How often may they do it? | `references/rate-limiting.md` |
| Injection | Can input become code? | `references/injection.md` |

---

## 1. Keys — the one rule

There are exactly two classes of key:

| Class | Supabase format | Legacy (until end of 2026) | Belongs in |
|-------|-----------------|----------------------------|------------|
| **Public** | `sb_publishable_…` | `anon` | browser, app, repo, CI — may be visible |
| **Secret** | `sb_secret_…` | `service_role` | servers, edge functions, workers only |

The secret key carries the Postgres attribute `BYPASSRLS`. It ignores **every** policy. An
`sb_secret_…` in a frontend bundle means full read and write access to the entire database for
every visitor.

**Check this for every key in the code:**

```
Does this file end up in the browser bundle?
  ├─ yes → publishable/anon only. Anything else is an incident.
  └─ no  → secret is allowed, but from process.env, never in source.
```

In Next.js, anything prefixed `NEXT_PUBLIC_` is compiled into the bundle. So
`NEXT_PUBLIC_SUPABASE_SECRET_KEY` is always wrong, no matter how plausible it looks.

Legacy `anon`/`service_role` keys are being switched off by the end of 2026, and new projects
no longer receive them. Build new work directly on `sb_publishable_…` / `sb_secret_…`.

Sources: [Supabase — API keys](https://supabase.com/docs/guides/getting-started/api-keys),
[Migrating to new API keys](https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys)

**Key leaked?** The emergency steps and their order are in `references/keys-and-secrets.md`.
The key point up front: reverting the commit is not enough — the key stays valid until it is
rotated.

---

## 2. Roles and privileges — least privilege

Postgres has no separate concept of "users" and "groups", only **roles**. A role with `LOGIN`
behaves like an account, one without behaves like a group.

```sql
-- Group role (no login) — carries the privileges
create role app_readonly nologin;
grant usage on schema public to app_readonly;
grant select on all tables in schema public to app_readonly;

-- Login role — an actual account that inherits the group's privileges
create role reporting_service login password '…';
grant app_readonly to reporting_service;
```

Always attach privileges to the **group role**, never directly to the account. When a service
or a person goes away, you revoke one membership instead of unwinding a dozen grants and
missing one.

### Who may destroy what

| Action | Who is allowed |
|--------|----------------|
| `DROP TABLE` | only the table **owner** (or a superuser). `GRANT ALL` is **not** enough |
| `ALTER TABLE`, enabling/disabling RLS, creating policies | only the owner |
| `DROP DATABASE` | the database owner or a superuser, and only with no open connections |
| `CREATE DATABASE` | roles with the `CREATEDB` attribute |
| Creating and altering roles | roles with the `CREATEROLE` attribute |
| Everything | `SUPERUSER` — not available to customers on managed platforms like Supabase |

The consequence: **ownership outranks grants.** An application role must never own the tables,
otherwise it can change the schema and its own policies.

Sources: [Postgres — Database roles](https://www.postgresql.org/docs/current/database-roles.html),
[Role attributes](https://www.postgresql.org/docs/current/role-attributes.html),
[DROP DATABASE](https://www.postgresql.org/docs/current/sql-dropdatabase.html)

### Grants for every new table

In existing Supabase projects, new tables in the `public` schema automatically receive
`select, insert, update, delete` for `anon`, `authenticated` and `service_role`. Those grants
do **not** go away when policies are added. So clean them up explicitly:

```sql
revoke all on my_table from anon;
grant select, insert, update, delete on my_table to authenticated;
```

Default rule of thumb: `anon` gets nothing, unless the table is deliberately public
(a price list, say) — and then only `select`.

The full grant matrix, `ALTER DEFAULT PRIVILEGES` and audit queries:
`references/roles-and-privileges.md`

Source: [Supabase — Securing your API](https://supabase.com/docs/guides/api/securing-your-api)

---

## 3. Rate limiting — three layers

Without limits, a single script can blow up the bill or saturate the database. RLS does **not**
help here: someone who is authorised is authorised any number of times.

| Layer | What it limits | Where to configure |
|-------|----------------|--------------------|
| Auth | logins, OTP, emails, token refresh | Supabase dashboard → Authentication → Rate Limits |
| API / application | requests per user or IP on your own endpoints | middleware, edge function, Upstash Redis |
| Database | connections, query runtime, result size | pool size, `statement_timeout`, `LIMIT` |

Supabase Auth uses a token bucket per IP address with a capacity of roughly 30 requests and
answers with **429 Too Many Requests** when exceeded. The REST layer (PostgREST) has **no**
built-in per-table limit — that one has to be built.

Concrete implementations (middleware, edge function plus Redis, `statement_timeout`,
pre-request function): `references/rate-limiting.md`

Sources: [Supabase — Rate limits](https://supabase.com/docs/guides/auth/rate-limits),
[Rate limiting edge functions](https://supabase.com/docs/guides/functions/examples/rate-limiting)

---

## 4. Injection — the core in three lines

```ts
// dangerous: input becomes part of the command
const sql = `select * from customers where name = '${input}'`

// safe: input stays a value
const { data } = await supabase.from('customers').select('*').eq('name', input)
```

The Supabase client parameterises automatically. In an app like this, injection mostly appears
in three places: dynamic SQL inside `plpgsql` functions, `SECURITY DEFINER` without a fixed
`search_path`, and hand-built filter strings. All three, with countermeasures:
`references/injection.md`

Source: [OWASP — SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)

---

## Quick audit (10 points)

Run through this before every release:

```
[ ]  1. No sb_secret_ / service_role key in client code, in a NEXT_PUBLIC_ variable, or in the repo
[ ]  2. .env* is in .gitignore; .env.example contains only placeholders
[ ]  3. Every table in public has RLS enabled (check the Supabase Security Advisor)
[ ]  4. anon holds no grants on any internal table
[ ]  5. No application role owns the tables
[ ]  6. Every SECURITY DEFINER function has set search_path = ''
[ ]  7. Auth rate limits configured; your own endpoints have a limit
[ ]  8. statement_timeout set for the application role
[ ]  9. No string-concatenated SQL in code or in functions
[ ] 10. Key rotation is documented and has been rehearsed at least once
```

Points 3 and 4 can be checked automatically in Supabase: dashboard → Advisors → Security, or
`supabase db lint`. Points 1, 3, 4, 6 and 9 are also covered statically by the `sql-king` skill's
`scripts/sql_scan.py` — run it on the repository before the release checklist.

---

## Agent integration

- **Agent 1 (Research)**: build an inventory — which keys exist, where they are used, which
  role owns which table, which grants are in place.
- **Agent 2 (Code)**: write the grants and revokes into the migration, wrap key access in
  `process.env`, add rate limiting.
- **Agent 3 (Test/QA)**: use the publishable key to attempt forbidden operations. The test
  passes when the attempt **fails**.

---

## Reference files

- `references/keys-and-secrets.md` — key types, `.env` layout, client/server separation in
  TypeScript, leak response plan, rotation. Read for anything involving keys.
- `references/roles-and-privileges.md` — creating roles, the grant matrix, ownership, default
  privileges, audit queries, app accounts vs. database roles. Read for every new table and any
  privilege question.
- `references/rate-limiting.md` — auth limits, middleware, edge function with Redis, timeouts,
  pool sizes, cost protection. Read for public or expensive endpoints.
- `references/injection.md` — parameterisation, dynamic SQL, `format()`, `SECURITY DEFINER`,
  input validation with Zod. Read when writing functions or dynamic filters.

---

## Self-reflection (MANDATORY)

At the end of every task, check:

- Could an attacker with the public key do more than a normal user should?
- Are grants explicitly set **and** unneeded ones revoked, or was RLS alone trusted?
- Does an application role own objects it could drop?
- Is there a limit on frequency, runtime and result size?
- Was every input treated as a value rather than as code?
- Is the leak response plan executable without taking the app down for long?
