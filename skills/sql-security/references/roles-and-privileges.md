# Roles and Privileges

Contents:
1. Understanding roles (there are no "users")
2. Role attributes — who may create, who may drop
3. Ownership — the strongest permission
4. GRANT and REVOKE in detail
5. Default privileges
6. The Supabase roles in practice
7. App accounts vs. database roles
8. Audit queries

---

## 1. Understanding roles

Postgres only has **roles**. Whether a role is a "user" or a "group" depends solely on the
`LOGIN` attribute:

```sql
create role app_readonly nologin;                    -- group
create role reporting login password '…';            -- account
grant app_readonly to reporting;                     -- account joins the group
```

The pattern worth using in every project:

```
Group roles (carry privileges)         Login roles (are the accounts)
──────────────────────────────         ───────────────────────────────
app_readonly    ← select               reporting_service
app_readwrite   ← select/insert/…      app_backend
app_admin       ← + ddl                (migrations only, not the running app)
```

Why: when a service is retired or an account must be locked out, you revoke a membership
rather than unwinding twenty individual grants and forgetting one.

```sql
revoke app_readwrite from app_backend;    -- access gone immediately
drop role reporting_service;              -- remove the account (reassign objects first!)
```

Source: https://www.postgresql.org/docs/current/database-roles.html

---

## 2. Role attributes

Attributes belong to the role itself, not to an object:

| Attribute | Meaning | Give it to |
|-----------|---------|------------|
| `LOGIN` | may connect | real accounts only |
| `SUPERUSER` | ignores **all** permission checks including RLS | practically never; unavailable to Supabase customers |
| `CREATEDB` | may create databases | administrators |
| `CREATEROLE` | may create and alter roles | administrators. Careful: it can escalate its own privileges |
| `BYPASSRLS` | ignores row level security | only `service_role` / the secret key |
| `NOINHERIT` | does not inherit group privileges automatically, only via `set role` | useful for sensitive admin roles |
| `CONNECTION LIMIT n` | maximum concurrent connections | useful for service accounts |
| `VALID UNTIL` | password expiry | temporary access |

```sql
create role import_job login password '…'
  connection limit 5
  valid until '2026-12-31';

alter role import_job set statement_timeout = '30s';
```

`alter role ... set` applies per-role defaults, which is a very effective guard against one
service running away with long queries.

Source: https://www.postgresql.org/docs/current/role-attributes.html

---

## 3. Ownership — the strongest permission

The owner of an object may **always** alter and drop it, regardless of grants. Grants cannot
replace ownership and cannot prevent it.

| Action | Who may do it |
|--------|---------------|
| `DROP TABLE` | owner or superuser. `GRANT ALL PRIVILEGES` is **not** sufficient |
| `ALTER TABLE` (columns, constraints) | owner only |
| `ENABLE/DISABLE ROW LEVEL SECURITY` | owner only |
| `CREATE POLICY` / `DROP POLICY` | owner only |
| `TRUNCATE` | owner, or via `grant truncate` |
| `DROP DATABASE` | the database owner or a superuser, and only with no open connections |
| `CREATE DATABASE` | a role with `CREATEDB` |

The practical consequence for an application:

> The role the application runs as must **never** own the tables.

Otherwise a compromised application account could turn RLS off
(`alter table … disable row level security`) and then read everything. So migrations run under
a separate role with DDL rights, while the running application uses a role with plain DML
grants.

```sql
-- Check ownership
select tablename, tableowner from pg_tables where schemaname = 'public';

-- Transfer ownership (e.g. before dropping a role)
alter table orders owner to app_admin;
reassign owned by old_role to app_admin;
drop owned by old_role;    -- removes remaining privileges
drop role old_role;
```

`drop role` fails while the role still owns objects or holds privileges, which is why
`reassign owned` and `drop owned` always come first.

Sources:
- https://www.postgresql.org/docs/current/ddl-priv.html
- https://www.postgresql.org/docs/current/sql-dropdatabase.html
- https://www.postgresql.org/docs/current/sql-droprole.html

---

## 4. GRANT and REVOKE

Privileges always apply to a specific object.

```sql
-- The schema must be enterable first, or table privileges are useless
grant usage on schema public to app_readonly;

-- Table privileges
grant select on orders to app_readonly;
grant select, insert, update, delete on orders to app_readwrite;

-- Column level (e.g. excluding salary)
grant select (id, name, department) on employees to app_readonly;
grant update (status) on orders to app_readwrite;

-- Sequences: without usage, any insert with a generated number fails
grant usage on all sequences in schema public to app_readwrite;

-- Functions
grant execute on function complete_order(uuid, numeric) to authenticated;

-- Taking privileges back
revoke insert, update, delete on orders from anon;
revoke all on schema public from public;    -- the pseudo-role "public" = everyone
```

Important details:

- **`public` is a role**, not a synonym for "publicly readable". Privileges granted to `public`
  apply to every existing and future role. That is rarely what anyone wants.
- **`grant … on all tables in schema`** only affects tables that exist at that moment. Future
  tables need default privileges (section 5).
- **`with grant option`** lets the target role pass the privilege on. Almost never appropriate.
- A missing grant produces error **42501 "permission denied"**. A non-matching RLS policy
  produces an **empty result**. Knowing this difference saves a lot of debugging time.

### Grant matrix template

| Role | Internal tables | Public tables (e.g. price list) | Functions |
|------|-----------------|----------------------------------|-----------|
| `anon` | nothing | `select` | only deliberately exposed ones |
| `authenticated` | `select, insert, update, delete` (plus RLS!) | `select` | business RPCs |
| `service_role` | everything (bypasses RLS) | everything | everything |
| `app_readonly` | `select` | `select` | none |

Grants are the coarse gate ("may this role perform the operation at all"), RLS is the fine one
("on which rows"). Both are required.

Source: https://www.postgresql.org/docs/current/sql-grant.html

---

## 5. Default privileges

```sql
-- Applies to everything app_admin creates in public from now on:
alter default privileges for role app_admin in schema public
  grant select, insert, update, delete on tables to authenticated;

alter default privileges for role app_admin in schema public
  revoke all on tables from anon;

alter default privileges for role app_admin in schema public
  grant usage on sequences to authenticated;
```

This prevents the single most common mistake: a new table is created, the grants are
forgotten, and it is either unusable for everyone or open to `anon`.

In existing Supabase projects, new tables in `public` automatically receive grants for `anon`,
`authenticated` and `service_role`. Policies do **not** take those grants back. Supabase is
changing the platform default so that these automatic grants are revoked and exposure becomes
opt-in — until then, clean up manually.

Sources:
- https://www.postgresql.org/docs/current/sql-alterdefaultprivileges.html
- https://supabase.com/docs/guides/api/securing-your-api

---

## 6. The Supabase roles in practice

| Role | Who uses it | RLS |
|------|-------------|-----|
| `anon` | visitors who are not signed in (publishable key) | applies |
| `authenticated` | signed-in users (publishable key + session JWT) | applies |
| `service_role` | servers using the secret key | **bypassed** (`BYPASSRLS`) |
| `postgres` | dashboard, migrations | limited admin, not a true superuser |
| `supabase_admin` and others | internal services | not for your own use |

Worth internalising: the publishable key does not make the user anonymous. The *application*
authenticates with the key; the *user* authenticates separately through Supabase Auth with
their own JWT. That JWT is what lifts the role from `anon` to `authenticated`.

Policies are written for `anon` and `authenticated`. They never apply to the secret key.

### A dedicated schema for the API

```sql
create schema api;
grant usage on schema api to anon, authenticated;
-- internal tables stay in public and are not reachable through the API
```

A dedicated schema makes the exposed surface explicit and easy to audit: whatever is not in
`api` is not exposed.

Source: https://supabase.com/docs/guides/api/using-custom-schemas

---

## 7. App accounts vs. database roles

Do not conflate these:

| Layer | What it is | Example |
|-------|------------|---------|
| Database roles | Postgres roles: few, static | `anon`, `authenticated`, `app_readonly` |
| App accounts | rows in `auth.users`: many, dynamic | the 40 employees using the app |
| App roles | business roles in your own table | `manager`, `dispatcher`, `driver` |

Creating a Postgres role per user does not scale and is not done. Business roles belong in a
table:

```sql
create table user_roles (
  user_id uuid not null references auth.users(id) on delete cascade,
  role    text not null check (role in ('manager','dispatcher','driver')),
  primary key (user_id, role)
);
alter table user_roles enable row level security;
create index on user_roles (user_id);
```

RLS policies then query this table. Users may read it but must not write to it, otherwise they
will promote themselves:

```sql
revoke insert, update, delete on user_roles from authenticated;
```

Role changes go exclusively through a server route using the secret key, or a
`security definer` function with an explicit check. The matching policy patterns are in
`rls-security/references/policy-patterns.md`.

---

## 8. Audit queries

### Who holds which privileges on which table

```sql
select grantee, table_name, string_agg(privilege_type, ', ' order by privilege_type) as privileges
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon','authenticated','service_role')
group by grantee, table_name
order by table_name, grantee;
```

Justify every row where `grantee = 'anon'` on an internal table, individually.

### Tables without RLS

```sql
select tablename
from pg_tables t
where schemaname = 'public'
  and not exists (
    select 1 from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where c.relname = t.tablename and n.nspname = 'public' and c.relrowsecurity
  );
```

Every row in the result is reachable through the API as soon as a grant exists.

### Roles and their attributes

```sql
select rolname, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls, rolcanlogin, rolconnlimit
from pg_roles
where rolname not like 'pg\_%'
order by rolname;
```

### Memberships

```sql
select r.rolname as role, m.rolname as member
from pg_auth_members am
join pg_roles r on r.oid = am.roleid
join pg_roles m on m.oid = am.member
order by 1, 2;
```

### Spot-check a role's privileges

```sql
select has_table_privilege('anon', 'orders', 'select');   -- true here would be suspicious
select has_table_privilege('authenticated', 'orders', 'insert');
```

These make good assertions in automated tests: they check the privilege situation without
reading any actual data.

In addition, the Supabase dashboard under **Advisors → Security** and `supabase db lint` will
flag missing RLS, exposed tables, and `security definer` functions without a fixed
`search_path`.
