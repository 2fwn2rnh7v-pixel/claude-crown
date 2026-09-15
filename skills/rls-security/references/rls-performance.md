# RLS Performance

A policy is a condition that runs on **every** query. Whatever is in it may be evaluated per
row. That makes policies the most common reason for "the app was fast until the table grew".

Contents:
1. Measuring correctly
2. Lever 1 — indexes
3. Lever 2 — wrapping function calls
4. Lever 3 — restricting the role
5. Lever 4 — rewriting subqueries
6. Lever 5 — repeating the filter in the client
7. The order to optimise in

---

## 1. Measuring correctly

Timings measured as a database administrator are worthless: the table owner bypasses RLS, so
the policy is never evaluated. Always measure in the role of a real user.

```sql
begin;
  select set_config('request.jwt.claims',
                    '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}',
                    true);
  set local role authenticated;

  explain (analyze, buffers)
  select id, title from orders order by created_at desc limit 20;
rollback;
```

What to look for:

| Observation | Meaning |
|-------------|---------|
| `Seq Scan` on a large table | an index on the policy column is missing |
| `SubPlan` per row | a function or subquery is being executed row by row |
| `Rows Removed by Filter: 250000` | the policy filters afterwards instead of using an index |
| `Function Scan` with a high row count | the `security definer` function is `volatile` instead of `stable` |

A single `InitPlan` at the top of the plan is good — that is the desired outcome of
`(select auth.uid())`.

---

## 2. Lever 1 — indexes

Columns appearing in `using` and `with check` need an index. Without one, Postgres must check
visibility for every row individually.

```sql
create index idx_orders_team on orders (team_id);
create index idx_notes_user  on notes  (user_id);
```

When the policy runs alongside a typical sort, a composite index in the order "policy column,
then sort column" pays off:

```sql
-- Policy: team_id in (...)   Query: order by created_at desc
create index idx_orders_team_created on orders (team_id, created_at desc);
```

For policies with an extra condition, use a partial index:

```sql
-- Policy: team_id in (...) and deleted_at is null
create index idx_orders_team_active on orders (team_id) where deleted_at is null;
```

Put this into the migration straight away, not later. The index costs nothing while the table
is small — and it is guaranteed to be missing exactly when the table has grown.

---

## 3. Lever 2 — wrapping function calls

```sql
using ( auth.uid() = user_id )          -- ❌ one call per row
using ( (select auth.uid()) = user_id ) -- ✅ one call per query
```

The wrapper turns the function call into an `InitPlan` that Postgres evaluates once and caches.
On a table with 100,000 rows, that is the difference between one call and a hundred thousand.

The same applies to `auth.jwt()` and to your own helper functions:

```sql
using ( team_id in (select my_team_ids()) )      -- ✅
using ( my_team_ids() @> array[team_id] )        -- ❌ may be evaluated per row
```

Mark your own functions `stable` as well — `volatile` (the default) forbids Postgres from
caching anything:

```sql
create function my_team_ids() returns setof uuid
language sql security definer set search_path = '' stable    -- ← important
as $$ … $$;
```

---

## 4. Lever 3 — restricting the role

```sql
create policy "…" on orders for select to authenticated using ( … );
--                                     ^^^^^^^^^^^^^^^^
```

Without `to authenticated`, Postgres also evaluates the policy for `anon` requests, where it
can never match. With several policies per table, that adds up.

Likewise: do not create more policies than necessary. Every `permissive` policy for the same
operation is another condition checked with OR.

---

## 5. Lever 4 — rewriting subqueries

```sql
-- slower on many rows: the subquery materialises a list
using ( order_id in (select id from orders where team_id in (select my_team_ids())) )

-- faster: exists stops at the first match
using ( exists (
  select 1 from orders o
  where o.id = order_line_items.order_id
    and o.team_id in (select my_team_ids())
) )
```

If that is still not enough, **denormalisation** is the next step: carry `team_id` in the child
table, keep it in sync with a trigger, and write the policy without a join.

```sql
alter table order_line_items add column team_id uuid not null references teams(id);
create index on order_line_items (team_id);

create policy "line_items_select" on order_line_items for select to authenticated
  using ( team_id in (select my_team_ids()) );
```

This is deliberately redundant. The price is a trigger and some storage; the gain is a policy
without a subquery.

---

## 6. Lever 5 — repeating the filter in the client

Even though the policy already restricts the rows, passing the same filter explicitly helps:

```ts
// The policy already filters on team_id — pass it anyway
const { data } = await supabase
  .from('orders')
  .select('id, title')
  .eq('team_id', currentTeam)
  .order('created_at', { ascending: false })
  .limit(50)
```

The reason: the planner then sees a concrete constant and can use the index directly instead of
first resolving the policy condition. Nothing changes security-wise — the policy remains the
binding constraint, the client filter is only a hint to the planner.

And always set a `limit`. A query without an upper bound eventually gets expensive no matter
how good the indexes are.

---

## 7. The order to optimise in

```
1. Measure in a real user role (explain analyze)
2. Check for an index on every policy column     → fixes most cases
3. Wrap auth.uid() / helpers in (select …)       → fixes most of the rest
4. Mark functions as stable
5. Add to authenticated
6. Rewrite in (…) as exists
7. Only then: denormalise
```

Do not start at step 7. In practice, steps 2 and 3 together handle the large majority of
problems.

---

## Sources

- Supabase — RLS performance and best practices:
  https://supabase.com/docs/guides/database/postgres/row-level-security
- Postgres — Using EXPLAIN: https://www.postgresql.org/docs/current/using-explain.html
- Postgres — Function volatility categories:
  https://www.postgresql.org/docs/current/xfunc-volatility.html
- Postgres — Row security policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
