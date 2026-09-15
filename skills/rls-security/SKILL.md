---
name: rls-security
description: >
  Row Level Security (RLS) in Postgres/Supabase — who may see, create, change and delete an
  individual ROW. Explains policies from the ground up (USING vs. WITH CHECK, one policy per
  operation, auth.uid(), auth.jwt()), gives ready-made patterns for owner, team and role based
  access, shows the performance traps (missing indexes, recursive policies) and the negative
  tests that make a policy proven rather than merely claimed.
  ALWAYS use this skill when: a table holding user data is created or changed; the user mentions
  "RLS", "policy", "row level security", "who can see what", "tenant", "team", "user sees
  someone else's data", "auth.uid", "unrestricted" or "security hole"; a query unexpectedly
  returns an empty result; data is read directly from the frontend; one user could see another
  user's data. Also trigger when multi-user data is only implicit — for example any table with a
  user_id, employee_id or team_id column.
---

# RLS Security — Securing Rows

RLS answers exactly one question: **which rows may this request touch?**

Technically, Postgres appends an extra condition to every query automatically:

```sql
-- Policy
create policy "read own orders" on orders
  for select to authenticated
  using ( (select auth.uid()) = created_by );

-- Client asks:       select * from orders
-- Postgres runs:     select * from orders where auth.uid() = created_by
```

The client cannot bypass, omit or override that condition. This is the reason a browser is
allowed to talk to the database directly at all.

Sources: [Supabase — Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security),
[Postgres — Row security policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

---

## The order that always applies

```
1. enable row level security      ← otherwise the table is wide open
2. set/revoke grants              ← otherwise the policy never even runs (→ sql-security)
3. one policy per operation       ← select / insert / update / delete, separately
4. write a negative test          ← otherwise the protection is only a claim
```

Without step 1, the table is readable by anyone holding the public key. Tables created through
the SQL editor or a migration do **not** have RLS on by default — only those created in the
dashboard's table editor do.

```sql
alter table orders enable row level security;
```

---

## USING and WITH CHECK

This is the most commonly misunderstood detail:

| Clause | Applies to | Question |
|--------|-----------|----------|
| `using (…)` | **existing** rows | which rows may I see or touch? |
| `with check (…)` | **new or modified** rows | what may the result look like? |

| Operation | Needs |
|-----------|-------|
| `select` | `using` |
| `insert` | `with check` |
| `update` | `using` **and** `with check` |
| `delete` | `using` |

If `update` has no `with check`, a user can take their own row and reassign it to someone else
(setting `created_by` to a foreign ID). The row then becomes invisible to them — but the data
has still been moved.

---

## The base pattern (owner)

Four separate policies, the shape almost every table needs:

```sql
alter table orders enable row level security;

create policy "orders_select_own"
  on orders for select to authenticated
  using ( (select auth.uid()) = created_by );

create policy "orders_insert_own"
  on orders for insert to authenticated
  with check ( (select auth.uid()) = created_by );

create policy "orders_update_own"
  on orders for update to authenticated
  using      ( (select auth.uid()) = created_by )
  with check ( (select auth.uid()) = created_by );

create policy "orders_delete_own"
  on orders for delete to authenticated
  using ( (select auth.uid()) = created_by );

-- Required, otherwise the policy is slow:
create index idx_orders_created_by on orders (created_by);
```

Three details that are not cosmetic:

1. **`(select auth.uid())` rather than `auth.uid()`** — the wrapped form is evaluated once per
   query instead of once per row. On a large table the difference is dramatic.
2. **`to authenticated`** — restricts the policy to signed-in users. Without it, the policy is
   also evaluated for `anon`, where it can never match.
3. **An index on every policy column** — the condition runs on every single query.

More patterns (team/tenant, roles, publicly readable, soft delete, storage):
`references/policy-patterns.md`

---

## Avoid `for all`

```sql
-- ❌ obscures which rule was meant for which operation
create policy "everything" on orders for all to authenticated
  using ( auth.uid() = created_by );
```

With `for all`, the `using` expression also acts as `with check`. Sometimes that is right and
often it is an accident. Four explicit policies are longer and in exchange reviewable: you can
see at a glance whether every operation is covered.

---

## The five most common mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| RLS not enabled | everyone sees everything; "Unrestricted" warning in the dashboard | `enable row level security` |
| grant for `anon` left in place | a write path exists despite policies | `revoke all … from anon` (→ sql-security) |
| `with check` missing on `update` | rows can be reassigned to strangers | set both clauses |
| policy checks a column the client sets | the client sends a foreign `user_id` | `default auth.uid()` plus `with check` |
| policy reads the table it protects | infinite recursion, error 42P17 | use a `security definer` helper function |

### Recursion — the classic

```sql
-- ❌ a policy on team_members queries team_members → recursion
create policy "see team" on team_members for select to authenticated
  using ( team_id in (select team_id from team_members where user_id = auth.uid()) );
```

The fix is to move the lookup into a `security definer` function, which bypasses RLS and
therefore does not trigger the policy again:

```sql
create function my_team_ids() returns setof uuid
language sql security definer set search_path = '' stable
as $$ select team_id from public.team_members where user_id = auth.uid(); $$;

create policy "see team" on team_members for select to authenticated
  using ( team_id in (select my_team_ids()) );
```

In full, including how to grant such functions: `references/policy-patterns.md`

---

## What RLS does not do

- **It does not protect against the secret key.** `service_role` has `BYPASSRLS` and ignores
  every policy. That is why the key never belongs in the client (→ sql-security).
- **It does not protect against the table owner.** The owner bypasses RLS by default. Where
  that is not wanted: `alter table … force row level security`.
- **It is not rate limiting.** Someone who is authorised is authorised any number of times
  (→ sql-security).
- **It is not column security.** RLS filters rows, not columns. For "nobody may see salary",
  use column grants or a view without that column.

---

## Testing — an untested policy counts as broken

```sql
-- act as user A (simulated)
select set_config('request.jwt.claims', '{"sub":"<uuid-a>","role":"authenticated"}', true);
set local role authenticated;

select count(*) from orders;    -- expected: only their own
```

The test that matters is always the **negative test**: user B must **not** see and **not**
change user A's row. A test that only proves you can see your own data proves nothing about the
protection.

The full procedure with pgTAP and `supabase test db`: `references/rls-testing.md`. For a first
static pass over the migration files (RLS enabled? four policies? `with check` on update?
unwrapped `auth.uid()`?), run the `sql-king` skill's `scripts/sql_scan.py`.

---

## Performance in brief

Policies run on every query. Three levers:

1. Index every column that appears in a policy.
2. Use `(select auth.uid())` rather than `auth.uid()` — evaluated once per query, not per row.
3. Add `to authenticated` so the policy is not evaluated for `anon` at all.

Measure with `explain (analyze)` as a real user, not as an admin — as an admin the policy is
not evaluated at all. Details: `references/rls-performance.md`

---

## Agent integration

- **Agent 1 (Research)**: establish the access model before any policy is written — who are the
  roles, what is the boundary (user? team? tenant?), which table holds that mapping.
- **Agent 2 (Code)**: enable RLS, write four policies per table, add indexes and helper
  functions.
- **Agent 3 (Test/QA)**: negative tests with at least two test users; also check whether a new
  table slipped through without a policy (`supabase db lint`, Security Advisor).

---

## Reference files

- `references/policy-patterns.md` — ready-made policies for owner, team/tenant, roles, publicly
  readable, soft delete and storage buckets; plus helper functions against recursion.
  Read when writing a policy.
- `references/rls-performance.md` — why policies get slow, measuring with EXPLAIN, index
  strategy, rewriting slow policies. Read when a query with RLS is slow.
- `references/rls-testing.md` — manual tests, pgTAP, `supabase test db`, the test case
  checklist. Read before declaring a table finished.

---

## Self-reflection (MANDATORY)

At the end of every RLS task, check:

- Is RLS enabled on **every** new table?
- Is there a policy for select, insert, update and delete — or was an operation quietly left open?
- Does every `update` policy have both `using` and `with check`?
- Is every policy column indexed and is `auth.uid()` wrapped in `(select …)`?
- Is there a negative test with a second user that actually fails?
- Were grants checked separately (→ sql-security)? RLS alone is not enough.
