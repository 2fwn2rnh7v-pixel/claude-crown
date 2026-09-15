---
name: sql-king
description: >
  Foundation skill for everything involving a cloud database (Postgres / Supabase) in a
  TypeScript app. Teaches clean query writing, table and index design, migrations instead of
  dashboard clicks, performance analysis with EXPLAIN, and the mandatory "definition of done"
  checklist for every new table. Also the entry point (router) to the sibling skills
  sql-security (keys, roles, privileges, rate limiting) and rls-security (row level security).
  ALWAYS use this skill when: a table, column, view or migration is created or changed;
  a SELECT/INSERT/UPDATE/DELETE query or a Supabase client call is written; the user mentions
  "database", "DB", "SQL", "query", "table", "schema", "migration", "Supabase", "Postgres",
  "slow", "index" or "data model"; data is read or written from the frontend; data modelling
  is being discussed. Also trigger when database work is only implicit — for example a new
  feature that stores anything.
---

# SQL King — Foundation

This skill is the base layer for database work in a TypeScript + Postgres/Supabase app.
The goal is queries that are **correct, fast and safe** — in that order.

The sentence that holds the whole skill set together:

> **A table is finished when grants, policies and a test exist.**
> Not when `CREATE TABLE` ran without an error.

---

## Three questions before every query

Answer these first. They prevent most problems later:

1. **Who is running this query?** The browser (role `anon` / `authenticated`) or a server
   (role `service_role`, which bypasses RLS)? This decides the security layer.
2. **How many rows can come back in the worst case?** If the answer is "unlimited", a `LIMIT`
   and pagination are missing.
3. **Which column is being filtered on?** That column almost always needs an index.

---

## Which skill to use when

| Situation | Skill |
|-----------|-------|
| Writing a query, designing a schema, adding an index, writing a migration | **sql-king** (this one) |
| Keys, `.env`, roles, GRANT/REVOKE, who may DROP, rate limiting, injection | **sql-security** |
| Who may see or change which **row**? Policies, `auth.uid()`, tenant isolation | **rls-security** |

A new table needs **all three**. Order: schema (sql-king) → privileges (sql-security) →
policies (rls-security).

---

## The two-layer model (the most important concept here)

Postgres checks **two** separate things on every access:

```
Request
   │
   ▼
[1] GRANT      → May this role perform this operation on this table at all?
   │              Missing grant: error 42501 "permission denied"
   ▼
[2] RLS POLICY → Which ROWS may it touch while doing so?
   │              No matching policy: empty result, NO error
   ▼
Result
```

This gives the single most useful debugging rule in the whole skill set:

- **"permission denied" error** → a grant is missing → sql-security
- **Empty result although the data exists** → a policy is filtering → rls-security

Protecting a table with policies alone is not enough. As long as the grant for `anon` is still
in place, a write path exists. Always set both.

Sources: [Supabase — Understanding RLS](https://supabase.com/docs/guides/database/postgres/row-level-security),
[Postgres — Privileges](https://www.postgresql.org/docs/current/ddl-priv.html)

---

## Checklist: new table (definition of done)

Work through this for **every** new table. No item is optional.

```
[ ]  1. Table created in a migration file (not clicked together in the dashboard)
[ ]  2. Primary key present (uuid default gen_random_uuid())
[ ]  3. Foreign keys declared with references ... on delete <rule>
[ ]  4. created_at / updated_at timestamptz default now()
[ ]  5. NOT NULL wherever it makes sense, CHECK constraints for value ranges
[ ]  6. Index on every column used for filtering or joining (including policy columns!)
[ ]  7. RLS enabled: alter table ... enable row level security      → rls-security
[ ]  8. Grants explicitly set and revoked for anon + authenticated  → sql-security
[ ]  9. One policy each for select / insert / update / delete       → rls-security
[ ] 10. Test written: another user does NOT see the row             → rls-security
```

Item 10 matters most. Without a negative test, the protection is only a claim.

---

## Query basics

### Never `select *` against the database

```ts
// bad — fetches every column, breaks types on any schema change
const { data } = await supabase.from('orders').select('*')

// good — only what is needed, plus a limit
const { data } = await supabase
  .from('orders')
  .select('id, title, status, customer_id, created_at')
  .eq('status', 'open')
  .order('created_at', { ascending: false })
  .limit(50)
```

Fewer columns means fewer bytes on the wire and a real chance of an index-only scan.

### Filtering belongs in the database, not in TypeScript

```ts
// bad — loads 40,000 rows into the browser and throws 39,950 away
const all = await supabase.from('orders').select('*')
const open = all.data.filter(o => o.status === 'open')

// good
const open = await supabase.from('orders').select('id, title').eq('status', 'open')
```

This is not only slow, it is a data leak: everything the client loads is readable in the
network tab, even if the UI filters it out afterwards.

### Avoid N+1

```ts
// bad — 1 query for orders plus 1 per order = 51 round trips
const orders = await supabase.from('orders').select('id, customer_id').limit(50)
for (const o of orders.data) {
  const c = await supabase.from('customers').select('name').eq('id', o.customer_id).single()
}

// good — one round trip with an embedded join
const { data } = await supabase
  .from('orders')
  .select('id, title, customers ( id, name )')
  .limit(50)
```

Source: [Supabase — Joins and nesting](https://supabase.com/docs/guides/database/joins-and-nesting)

### Pagination always with a stable sort

```ts
.order('created_at', { ascending: false })
.order('id', { ascending: false })   // tiebreaker, otherwise rows jump between pages
.range(0, 49)
```

On large tables, keyset pagination (`where created_at < :lastValue`) is much faster than
`offset`, because Postgres still walks 10,000 rows to satisfy `offset 10000`.

---

## Indexes — five rules

1. Every **foreign key** needs an index. Postgres does *not* create one automatically.
2. Every column used in an **RLS policy** needs an index — the policy runs on every query.
3. In composite indexes, put the **equality column first, the sort column second**
   (`create index on orders (customer_id, created_at desc)`).
4. Indexes cost time on every INSERT and UPDATE. Do not index everything blindly.
5. In production always `create index concurrently`, otherwise the table is locked for writes.

Details, index types (btree/gin/partial) and examples: `references/schema-and-indexes.md`

---

## Measure performance instead of guessing

```sql
explain (analyze, buffers)
select id, title from orders where customer_id = '…' order by created_at desc limit 20;
```

What to look for:

- `Seq Scan` on a large table → an index is missing
- planned `rows=1000` vs. `actual rows=250000` → stale statistics, run `analyze <table>`
- execution time grows linearly with row count → missing index or missing limit

Source: [Postgres — Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)

Ready-made diagnostic queries (slowest queries, unused indexes, unindexed foreign keys) are in
`references/query-patterns.md`.

---

## Quick start on existing code

Before judging an existing project, scan it — then verify each lead at the element:

```bash
python scripts/sql_scan.py <project-root> [--sql-dirs supabase/migrations] [--src-dirs src app] [--json] [--fail-on HIGH]
```

Stdlib only. Migrations: tables without `enable row level security`, RLS tables missing a
policy per operation, `update`/`insert` policies without `with check`, `for all` policies,
unwrapped `auth.uid()`, `security definer` without `set search_path`, foreign keys without an
index, tables without an explicit `revoke … from anon`. Client code: secret keys on the client
path, `select('*')`, query chains without a limit, `.from(<variable>)`, `.or()` strings built
from input. Prints the counts per category plus every hit with file and line. The remaining
proof is a run of `supabase db lint` and the negative tests — the scanner reads files, it does
not see grants that live only in the database.

---

## Migrations instead of dashboard clicks

Every schema change belongs in the repository as a file. Changes clicked in the dashboard do
not exist locally, cannot be reviewed and cannot be rolled back.

```bash
supabase migration new orders_status_index   # creates a timestamped file
# write the SQL into that file, then:
supabase db reset      # rebuild locally from scratch and verify
supabase db push       # only then push to remote
```

Rules, ordering inside the file and rollback strategy: `references/migrations.md`

Source: [Supabase — Local development](https://supabase.com/docs/guides/local-development/overview)

---

## Agent integration

- **Agent 1 (Research)**: inventory the existing schema, indexes and policies before building
  anything new — start with `scripts/sql_scan.py`. Check whether a table already holds similar data.
- **Agent 2 (Code)**: implement the migration, the query and the TypeScript types, working
  through the 10-point checklist.
- **Agent 3 (Test/QA)**: run `explain analyze` on the new queries, plus the RLS negative tests
  from rls-security.

---

## Reference files

- `references/query-patterns.md` — query building blocks, joins, aggregation, upsert,
  transactions, diagnostics. Read when writing or optimising a concrete query.
- `references/schema-and-indexes.md` — data types, constraints, naming, index types.
  Read when designing or changing a table.
- `references/migrations.md` — migration workflow, safe DDL changes, rollback.
  Read when writing a migration.
- `references/sources.md` — all official documentation links, grouped by topic.
- `scripts/sql_scan.py` — static scan of migrations and client code (see Quick start). Run it
  first on any existing project; fixtures under `evals/fixtures/` show what it flags.

---

## Self-reflection (MANDATORY)

At the end of every database task, check:

- Was the 10-point checklist completed, including grants, policies and a test?
- Was the query checked for `select *`, a missing limit and client-side filtering?
- Is every filtered column and every policy column indexed?
- Is the change a migration file in the repository, not just a dashboard edit?
- Were sql-security and rls-security consulted where privileges or row visibility are involved?
