# Migrations

Contents:
1. Why migration files
2. The workflow
3. Structure of a migration file
4. Making dangerous changes safe
5. Rollback
6. Keeping environments apart

---

## 1. Why migration files

A column clicked together in the dashboard exists only on the production server. It is not in
the git history, cannot be reviewed, cannot be reproduced locally, and disappears on the next
`supabase db reset`. The moment a second environment or a second person appears, this becomes
a real problem.

Rule: **every schema change is a file in the repository.** The dashboard is for looking, not
for changing.

Exception: exploratory work in the local database. Afterwards, turn it into a migration with
`supabase db diff -f <name>`.

---

## 2. The workflow

```bash
# 1. Create an empty migration (the filename gets a timestamp)
supabase migration new create_time_entries

# 2. Write the SQL into supabase/migrations/<timestamp>_create_time_entries.sql

# 3. Rebuild locally from scratch — this tests the migration from zero
supabase db reset

# 4. Regenerate types
supabase gen types typescript --local > src/types/database.ts

# 5. Run the tests (including the RLS negative tests)
supabase test db

# 6. Only when everything is green: push to remote
supabase db push
```

`supabase db reset` replays **all** migrations from the beginning. If that succeeds, the
migration chain is internally consistent — which is exactly what the production environment
will check later.

To capture changes someone made in the dashboard anyway:

```bash
supabase db pull      # generates a migration from the remote state
```

---

## 3. Structure of a migration file

A fixed order, so nothing is forgotten:

```sql
-- Migration: create time_entries
-- Purpose: hour tracking per employee and order
-- Date: 2026-09-14

-- 1) Schema
create table ...;

-- 2) Indexes
create index ...;

-- 3) Triggers / functions
create trigger ...;

-- 4) Enable RLS
alter table time_entries enable row level security;

-- 5) Grants
revoke all on time_entries from anon;
grant select, insert, update, delete on time_entries to authenticated;

-- 6) Policies
create policy "read own time entries" on time_entries
  for select to authenticated
  using ( (select auth.uid()) = employee_id );
-- ... insert / update / delete
```

One migration equals one logical change. Do not put three unrelated things in one file —
rolling back then forces all of them back together.

**Never edit a migration file after it has been pushed.** The server has already applied that
state; editing it afterwards makes local and remote drift apart. Write a new migration that
corrects the problem instead.

---

## 4. Making dangerous changes safe

Some DDL statements take an `ACCESS EXCLUSIVE` lock on the table. While that lock is held, the
app is stalled. On small tables this is unnoticeable; on large ones it is an outage.

| Change | Risk | Safe approach |
|--------|------|---------------|
| `add column` without default | low | do it directly |
| `add column ... not null default ...` | low since PG 11 | do it directly |
| `create index` | write lock | `create index concurrently` (in its own migration file) |
| `alter column ... type ...` | rewrites the table | new column + backfill + switch + drop old |
| `add constraint check` | full scan under lock | `add constraint ... not valid;` then `validate constraint ...;` |
| `drop column` | data gone, old code breaks | first deploy code that no longer uses it; drop in a later migration |
| `rename column` | old code breaks immediately | avoid. Add a new column, dual-write, migrate, drop the old one |

### Example: making a column non-nullable without locking the table

```sql
-- Step 1
alter table orders
  add constraint chk_title_nn check (title is not null) not valid;

-- Step 2 (takes only a weak lock)
alter table orders validate constraint chk_title_nn;
```

### Expand / contract

For anything risky, use this pattern:

```
Expand   → add the new thing (column/table), write to both
Migrate  → move existing data in batches
Contract → switch the code to the new thing, then remove the old one
```

Three deployments instead of one, in exchange for zero downtime and the ability to abort at
any point.

---

## 5. Rollback

Postgres has no automatic "undo migration". So:

- **Wrap DDL in a transaction** where possible. Postgres can roll back `create table`,
  `alter table` and `drop` transactionally — if step 3 fails, steps 1 and 2 are undone too.
  (Not possible with `create index concurrently`.)
- **Fix forward** rather than backward: write a new migration that repairs the mistake.
- **Before destructive changes** (`drop column`, `drop table`, a large `update`), take a backup
  or restore point and note the timestamp.

```sql
begin;
  alter table orders add column priority int not null default 0;
  create index idx_orders_priority on orders (priority);
commit;
```

Backups: Supabase takes automatic backups, and point-in-time recovery depends on the plan.
Before a risky migration, check which restore point actually exists — not afterwards.

---

## 6. Keeping environments apart

```
local (supabase start)  →  staging project  →  production
```

- The production service/secret key never belongs in a local `.env`.
- Never copy production data into test environments without anonymising personal data.
- `supabase link --project-ref <ref>` determines which project the CLI talks to. Check before
  every `db push` — pushing to the wrong project is the most expensive common mistake.

```bash
supabase projects list     # which project is which
supabase status            # what am I currently linked to
```

---

## Sources

- Supabase — Local development and CLI: https://supabase.com/docs/guides/local-development/overview
- Supabase — Database migrations: https://supabase.com/docs/guides/deployment/database-migrations
- Supabase — Backups: https://supabase.com/docs/guides/platform/backups
- Postgres — ALTER TABLE (locking behaviour): https://www.postgresql.org/docs/current/sql-altertable.html
- Postgres — Explicit locking: https://www.postgresql.org/docs/current/explicit-locking.html
