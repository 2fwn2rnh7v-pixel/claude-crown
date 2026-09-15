# Query Patterns

Contents:
1. Reading (filters, joins, aggregation)
2. Writing (insert, upsert, update, delete)
3. Transactions and RPC
4. Typing in TypeScript
5. Diagnostic queries

---

## 1. Reading

### Filter operators (Supabase client → SQL)

| Client | SQL | Note |
|--------|-----|------|
| `.eq('status','open')` | `= 'open'` | uses an index |
| `.neq(...)` | `<> ...` | usually cannot use an index |
| `.gt/.gte/.lt/.lte` | `> >= < <=` | uses a btree index |
| `.in('status',['a','b'])` | `in (...)` | uses an index |
| `.like('name','%Smith%')` | `like` | a leading `%` defeats a btree index → needs gin/trigram |
| `.ilike(...)` | `ilike` | same limitation |
| `.is('deleted_at', null)` | `is null` | for soft delete; a partial index helps |
| `.contains('tags',['organic'])` | `@>` | needs a gin index |

### Embedded joins

```ts
// one-to-many — a customer with their orders
const { data } = await supabase
  .from('customers')
  .select('id, name, orders ( id, title, status )')
  .eq('id', customerId)
  .single()

// many-to-one — an order with the customer name
.select('id, title, customers ( name )')

// filtering on the embedded table
.select('id, name, orders!inner ( id, status )')
.eq('orders.status', 'open')     // !inner turns this into an INNER JOIN
```

Without `!inner`, Supabase still returns the customer when no order matches — the embedded
array is simply empty. This is a frequent source of confusion.

### Aggregation

```sql
select
  c.id,
  c.name,
  count(o.id)                                    as order_count,
  count(o.id) filter (where o.status = 'open')   as open_orders,
  coalesce(sum(o.amount), 0)                     as revenue
from customers c
left join orders o on o.customer_id = c.id
where c.active = true
group by c.id, c.name
having count(o.id) > 0
order by revenue desc
limit 20;
```

`filter (where ...)` is cleaner and faster than `sum(case when ... then 1 else 0 end)`.

If the same aggregation is needed repeatedly, put it in a **view** so the logic does not get
duplicated across three frontend files. A view only inherits the RLS policies of its underlying
tables when it is created with `security_invoker = true` — otherwise it runs with the
privileges of whoever created it, which silently bypasses RLS.

```sql
create view v_customer_revenue with (security_invoker = true) as
select ... ;
```

---

## 2. Writing

### Insert with return value

```ts
const { data, error } = await supabase
  .from('orders')
  .insert({ title, customer_id: customerId, status: 'open' })
  .select('id, created_at')
  .single()
```

Never send `user_id` or `tenant_id` from the frontend. Set them server-side instead:

```sql
alter table orders
  alter column created_by set default auth.uid();
```

Now the client cannot forge the field even if it sends one — provided the INSERT policy also
checks `with check (created_by = (select auth.uid()))`.

### Upsert

```ts
await supabase
  .from('time_entries')
  .upsert(
    { employee_id, entry_date, hours: 8 },
    { onConflict: 'employee_id,entry_date' }   // requires a matching UNIQUE index
  )
```

Without a unique constraint on exactly those columns, the upsert fails.

### Update and delete: always with a filter

```ts
// dangerous — without .eq() this hits every visible row
await supabase.from('orders').update({ status: 'done' })

// correct
await supabase.from('orders').update({ status: 'done' }).eq('id', orderId)
```

RLS limits the damage to the user's own rows, but it does not prevent it. Direct SQL access
(psql, SQL editor) has no such safety net — there, run the same statement as a `select` first
and check the row count before running the `update` or `delete`.

### Soft delete instead of a real DELETE

```sql
alter table orders add column deleted_at timestamptz;
create index on orders (customer_id) where deleted_at is null;
```

Upside: recoverable, foreign keys stay intact. Downside: every query now needs
`.is('deleted_at', null)` — which is a good reason to put a view on top.

---

## 3. Transactions and RPC

The Supabase JS client **cannot** hold a transaction across multiple statements. As soon as
two writes must succeed or fail together, write a Postgres function and call it via `rpc()`.

```sql
create or replace function complete_order(p_order_id uuid, p_hours numeric)
returns void
language plpgsql
security invoker          -- runs with the caller's privileges, so RLS still applies
set search_path = public  -- prevents search_path hijacking
as $$
begin
  update orders set status = 'done', completed_at = now()
   where id = p_order_id;

  insert into time_entries (order_id, hours, recorded_by)
  values (p_order_id, p_hours, auth.uid());
end;
$$;
```

```ts
const { error } = await supabase.rpc('complete_order', {
  p_order_id: orderId,
  p_hours: 4.5,
})
```

Both statements in one function means one transaction. A failure in step 2 rolls back step 1.

**`security invoker` vs `security definer`:** `invoker` is the default and the safe choice.
`definer` bypasses RLS and is only needed when the function is deliberately allowed to do more
than the caller — and then it requires `set search_path` and an explicit privilege check in the
body. See sql-security.

---

## 4. Typing

```bash
supabase gen types typescript --linked > src/types/database.ts
```

```ts
import type { Database } from '@/types/database'
const supabase = createClient<Database>(url, key)
```

This types table names, columns and return values. Re-run it after **every** migration,
otherwise TypeScript describes a schema that no longer exists.

Never ignore errors:

```ts
const { data, error } = await supabase.from('orders').select('id')
if (error) throw new Error(`Loading orders failed: ${error.message}`)
```

The client does not throw on its own. An unchecked `error` looks exactly like "no data" in the
UI and hides privilege and policy problems.

---

## 5. Diagnostic queries

### Slowest queries

```sql
create extension if not exists pg_stat_statements;

select
  round(mean_exec_time::numeric, 2) as avg_ms,
  calls,
  round(total_exec_time::numeric)   as total_ms,
  left(query, 120)                  as query
from pg_stat_statements
order by total_exec_time desc
limit 20;
```

Sort by `total_exec_time`, not `mean_exec_time`. A 20 ms query that runs 50,000 times costs
more than a 2 s query that runs once.

### Foreign keys without an index

```sql
select c.conrelid::regclass as table_name, a.attname as column_name
from pg_constraint c
join pg_attribute a on a.attrelid = c.conrelid and a.attnum = c.conkey[1]
where c.contype = 'f'
  and not exists (
    select 1 from pg_index i
    where i.indrelid = c.conrelid and i.indkey[0] = c.conkey[1]
  );
```

Every row in the result is a potential full table scan on joins and on `on delete cascade`.

### Unused indexes

```sql
select relname as table_name, indexrelname as index_name, idx_scan as scans,
       pg_size_pretty(pg_relation_size(indexrelid)) as size
from pg_stat_user_indexes
where idx_scan = 0
order by pg_relation_size(indexrelid) desc;
```

`idx_scan = 0` over a meaningful production window means the index is a deletion candidate.
Keep unique indexes anyway — they enforce a rule.

### Table sizes

```sql
select relname, pg_size_pretty(pg_total_relation_size(relid)) as total
from pg_catalog.pg_statio_user_tables
order by pg_total_relation_size(relid) desc
limit 15;
```

---

## Sources

- Supabase — Joins and nesting: https://supabase.com/docs/guides/database/joins-and-nesting
- Supabase — Database functions: https://supabase.com/docs/guides/database/functions
- Supabase — Generating TypeScript types: https://supabase.com/docs/guides/api/rest/generating-types
- Postgres — Aggregate functions: https://www.postgresql.org/docs/current/functions-aggregate.html
- Postgres — pg_stat_statements: https://www.postgresql.org/docs/current/pgstatstatements.html
