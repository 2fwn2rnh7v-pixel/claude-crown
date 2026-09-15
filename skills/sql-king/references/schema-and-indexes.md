# Schema and Indexes

Contents:
1. Naming conventions
2. Choosing data types
3. Constraints
4. Foreign keys and delete rules
5. Index types and when to use which
6. Template for a new table

---

## 1. Naming conventions

Postgres folds unquoted identifiers to lowercase. `CamelCase` forces double quotes everywhere,
so use `snake_case` consistently.

| Object | Convention | Example |
|--------|-----------|---------|
| Table | plural, snake_case | `orders`, `customers`, `time_entries` |
| Column | singular, snake_case | `customer_id`, `created_at`, `amount_net` |
| Foreign key | `<target_singular>_id` | `customer_id` references `customers.id` |
| Index | `idx_<table>_<columns>` | `idx_orders_customer_id_created_at` |
| Constraint | `chk_` / `uq_` / `fk_` | `chk_orders_amount_positive` |
| View | `v_<purpose>` | `v_customer_revenue` |
| Function | verb phrase | `complete_order` |

Avoid non-ASCII characters in identifiers. They work technically but cause friction with
tooling, exports and generated TypeScript types.

---

## 2. Data types

| Purpose | Type | Why |
|---------|------|-----|
| Primary key | `uuid default gen_random_uuid()` | the client can generate the ID before insert, and IDs are not guessable |
| Point in time | `timestamptz` | stores UTC plus zone. **Never** plain `timestamp` |
| Date without time | `date` | e.g. invoice date, harvest day |
| Money | `numeric(12,2)` | `float`/`double` rounds wrong — 0.1 + 0.2 ≠ 0.3 |
| Quantity / area | `numeric(10,3)` | hectares, litres, hours |
| Text | `text` | no slower than `varchar(n)` in Postgres; bound the length with a CHECK |
| Yes/no | `boolean not null default false` | never `0/1` as an integer |
| Fixed choice list | `text` + CHECK **or** `enum` | see below |
| Free-form structure | `jsonb` | not `json`. Only when the shape is genuinely variable |
| Coordinates | `double precision` (lat/lng) or PostGIS `geography` | use PostGIS for areas and radius search |

### Enum or CHECK?

```sql
-- Option A: CHECK — flexible, values change with a simple migration
status text not null default 'open'
  check (status in ('open','in_progress','done','cancelled'))

-- Option B: real enum type — type safe, but removing a value is painful
create type order_status as enum ('open','in_progress','done','cancelled');
```

For an app under active development, **option A** is the better default. Adding a value means
replacing a constraint; removing a value from an enum type is a multi-step rebuild.

---

## 3. Constraints

Constraints are rules the database enforces itself. They hold even when a script, an import or
the SQL editor writes around the application — unlike validation in TypeScript.

```sql
create table orders (
  id          uuid primary key default gen_random_uuid(),
  customer_id uuid not null references customers(id) on delete restrict,
  title       text not null check (length(trim(title)) between 1 and 200),
  status      text not null default 'open'
                check (status in ('open','in_progress','done','cancelled')),
  amount_net  numeric(12,2) check (amount_net >= 0),
  starts_on   date,
  ends_on     date,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),

  constraint chk_orders_period check (ends_on is null or ends_on >= starts_on)
);
```

- `not null` is the cheapest error prevention available. When in doubt, set it.
- A `check` spanning several columns (like `chk_orders_period`) catches logic errors that a
  single-column check cannot see.
- Use `unique` for business uniqueness, e.g. `unique (employee_id, entry_date)` for time entries.

### Keep updated_at current automatically

```sql
create or replace function set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end; $$;

create trigger trg_orders_updated_at
  before update on orders
  for each row execute function set_updated_at();
```

Without a trigger, some code path will eventually forget the field.

---

## 4. Foreign keys and delete rules

```sql
customer_id uuid not null references customers(id) on delete restrict
```

| Rule | Behaviour when the parent row is deleted | When to use |
|------|------------------------------------------|-------------|
| `on delete restrict` | the delete is refused | **the default choice**; prevents accidental data loss |
| `on delete cascade` | child rows are deleted too | only for genuine ownership (order line items belonging to an order) |
| `on delete set null` | the child column becomes `null` | optional links, e.g. an assigned employee |
| `on delete no action` | like restrict, but checked at the end of the transaction | rarely needed |

`cascade` is convenient and dangerous: deleting one customer can silently take thousands of
orders, time entries and credits with it. Set cascades deliberately and document them — and
index **every** foreign key, otherwise each delete check becomes a full table scan.

---

## 5. Index types

| Type | How to create | Good for |
|------|---------------|----------|
| btree (default) | `create index on t (col)` | `=`, `<`, `>`, `between`, `order by` |
| Composite | `create index on t (a, b desc)` | filter on `a` **and** sort by `b` |
| Partial | `create index on t (customer_id) where deleted_at is null` | when nearly every query shares the same extra filter — smaller and faster |
| Unique | `create unique index on t (a, b)` | enforces uniqueness, enables `upsert onConflict` |
| gin | `create index on t using gin (tags)` | arrays, `jsonb`, full text |
| trigram | `create extension pg_trgm; create index on t using gin (name gin_trgm_ops)` | `ilike '%text%'` search |
| BRIN | `create index on t using brin (created_at)` | very large tables ordered by time (logs, sensor readings) |

### Column order in composite indexes

```sql
-- Query: where customer_id = X order by created_at desc limit 20
create index idx_orders_customer_created on orders (customer_id, created_at desc);
```

Rule: **equality filter first, sort column second.** An index on `(created_at, customer_id)`
barely helps this query.

An index on `(a, b)` can also serve queries that only filter on `a` — but not queries that
only filter on `b`.

### Always concurrently in production

```sql
create index concurrently idx_orders_status on orders (status);
```

Without `concurrently`, Postgres locks the table against writes until the index is built.
Note that `concurrently` cannot run inside a transaction, so in Supabase migrations it needs
its own migration file.

---

## 6. Template for a new table

Everything in **one** migration file, in this order:

```sql
-- 1) Table
create table time_entries (
  id          uuid primary key default gen_random_uuid(),
  employee_id uuid not null references employees(id) on delete restrict,
  order_id    uuid not null references orders(id)    on delete cascade,
  entry_date  date not null,
  hours       numeric(5,2) not null check (hours > 0 and hours <= 24),
  note        text check (length(note) <= 1000),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (employee_id, order_id, entry_date)
);

-- 2) Indexes (every FK + every policy column + every filter column)
create index idx_time_entries_employee on time_entries (employee_id);
create index idx_time_entries_order    on time_entries (order_id);
create index idx_time_entries_date     on time_entries (entry_date desc);

-- 3) Trigger
create trigger trg_time_entries_updated_at
  before update on time_entries
  for each row execute function set_updated_at();

-- 4) Enable RLS   → details in rls-security
alter table time_entries enable row level security;

-- 5) Grants       → details in sql-security
revoke all on time_entries from anon;
grant select, insert, update, delete on time_entries to authenticated;

-- 6) Policies     → details in rls-security
--    one each for select / insert / update / delete
```

Then run `supabase db reset` locally and write the negative tests.

---

## Sources

- Postgres — Data types: https://www.postgresql.org/docs/current/datatype.html
- Postgres — Constraints: https://www.postgresql.org/docs/current/ddl-constraints.html
- Postgres — Indexes: https://www.postgresql.org/docs/current/indexes.html
- Postgres — CREATE INDEX (incl. CONCURRENTLY): https://www.postgresql.org/docs/current/sql-createindex.html
- Supabase — Tables and data types: https://supabase.com/docs/guides/database/tables
