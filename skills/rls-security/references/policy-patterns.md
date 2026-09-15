# Policy Patterns

Contents:
1. Pattern 1 — owner
2. Pattern 2 — team / tenant
3. Pattern 3 — business roles
4. Pattern 4 — publicly readable, internally writable
5. Pattern 5 — soft delete
6. Pattern 6 — access derived from the parent table
7. Pattern 7 — storage buckets
8. Helper functions against recursion
9. Using JWT claims

Every pattern assumes RLS is enabled and grants are in place:

```sql
alter table <table> enable row level security;
revoke all on <table> from anon;
grant select, insert, update, delete on <table> to authenticated;
```

---

## 1. Owner

Everyone sees only what they created themselves. The default case.

```sql
create table notes (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid not null references auth.users(id) on delete cascade
             default auth.uid(),                      -- the client cannot forge this
  body       text not null,
  created_at timestamptz not null default now()
);
create index idx_notes_user on notes (user_id);
alter table notes enable row level security;

create policy "notes_select" on notes for select to authenticated
  using ( (select auth.uid()) = user_id );

create policy "notes_insert" on notes for insert to authenticated
  with check ( (select auth.uid()) = user_id );

create policy "notes_update" on notes for update to authenticated
  using      ( (select auth.uid()) = user_id )
  with check ( (select auth.uid()) = user_id );

create policy "notes_delete" on notes for delete to authenticated
  using ( (select auth.uid()) = user_id );
```

The combination of `default auth.uid()` and `with check` matters: even if the client sends a
foreign `user_id`, the policy rejects the insert.

---

## 2. Team / tenant

All members of an organisation see the same data. This is the common case for business apps
where orders, customers and time entries belong to the company rather than to one person.

```sql
create table team_members (
  team_id uuid not null references teams(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role    text not null default 'member' check (role in ('owner','dispatcher','member')),
  primary key (team_id, user_id)
);
create index idx_team_members_user on team_members (user_id);

-- Helper function: bypasses RLS and therefore prevents recursion
create or replace function my_team_ids()
returns setof uuid
language sql
security definer
set search_path = ''
stable
as $$
  select team_id from public.team_members where user_id = auth.uid();
$$;

revoke execute on function my_team_ids() from public;
grant execute on function my_team_ids() to authenticated;
```

```sql
-- The data table
create index idx_orders_team on orders (team_id);
alter table orders enable row level security;

create policy "orders_select_team" on orders for select to authenticated
  using ( team_id in (select my_team_ids()) );

create policy "orders_insert_team" on orders for insert to authenticated
  with check ( team_id in (select my_team_ids()) );

create policy "orders_update_team" on orders for update to authenticated
  using      ( team_id in (select my_team_ids()) )
  with check ( team_id in (select my_team_ids()) );

create policy "orders_delete_team" on orders for delete to authenticated
  using ( team_id in (select my_team_ids()) );
```

The policies on `team_members` itself:

```sql
alter table team_members enable row level security;

create policy "see own memberships" on team_members for select to authenticated
  using ( user_id = (select auth.uid()) or team_id in (select my_team_ids()) );

-- Nobody changes memberships through the client
revoke insert, update, delete on team_members from authenticated;
```

Invitations and role changes go through a server route using the secret key, or a
`security definer` function that first checks whether the caller is an owner. Otherwise any
member can promote themselves.

---

## 3. Business roles

```sql
create or replace function has_role(p_role text)
returns boolean
language sql security definer set search_path = '' stable
as $$
  select exists (
    select 1 from public.team_members
    where user_id = auth.uid() and role = p_role
  );
$$;
grant execute on function has_role(text) to authenticated;
```

```sql
-- Everyone in the team reads, only dispatchers write
create policy "orders_select_team" on orders for select to authenticated
  using ( team_id in (select my_team_ids()) );

create policy "orders_insert_dispatcher" on orders for insert to authenticated
  with check ( team_id in (select my_team_ids())
               and (has_role('dispatcher') or has_role('owner')) );

-- Only owners may delete
create policy "orders_delete_owner" on orders for delete to authenticated
  using ( team_id in (select my_team_ids()) and has_role('owner') );
```

Important: the role table must be read-only for users (see pattern 2), otherwise the whole
construction is worthless.

### Several policies for the same operation

Multiple `permissive` policies (the default) are combined with **OR** — one match is enough.
That is handy for "own rows OR team rows":

```sql
create policy "see own"      on time_entries for select to authenticated
  using ( employee_id = (select auth.uid()) );

create policy "owner sees all" on time_entries for select to authenticated
  using ( has_role('owner') and team_id in (select my_team_ids()) );
```

To enforce a condition that must **always** hold, use `as restrictive` — those are combined
with **AND**:

```sql
create policy "active tenant only" on orders as restrictive for select to authenticated
  using ( team_id in (select my_team_ids()) );
```

Rule of thumb: `permissive` for ways in, `restrictive` for boundaries that must never fall.

---

## 4. Publicly readable, internally writable

```sql
alter table price_list enable row level security;

grant select on price_list to anon, authenticated;
revoke insert, update, delete on price_list from anon, authenticated;

create policy "price_list_public_read" on price_list for select
  to anon, authenticated
  using ( published = true );
```

Changes happen exclusively server-side with the secret key. No insert or update policy is
needed — with no policy, the operation is simply impossible for those roles.

---

## 5. Soft delete

```sql
create policy "orders_select_active" on orders for select to authenticated
  using ( team_id in (select my_team_ids()) and deleted_at is null );

-- Matching partial index
create index idx_orders_team_active on orders (team_id) where deleted_at is null;
```

"Deleting" is then an `update` on `deleted_at`. The update policy must permit that while
preventing a deleted record from reappearing, depending on the business rule.

---

## 6. Access derived from the parent table

Order line items have no `team_id` of their own; they inherit access from the order:

```sql
create policy "line_items_select" on order_line_items for select to authenticated
  using (
    exists (
      select 1 from orders o
      where o.id = order_line_items.order_id
        and o.team_id in (select my_team_ids())
    )
  );
```

`exists` is faster than `in (select …)` here because Postgres stops at the first match. An
index on `order_line_items.order_id` is mandatory.

For very large tables, the alternative is to **denormalise**: carry `team_id` in the child
table and keep it consistent with a trigger. It costs storage and saves a join inside the
policy on every query.

---

## 7. Storage buckets

Storage uses the same mechanism through the `storage.objects` table. Without a policy, no
upload is possible.

```sql
-- Each user only in their own folder: <user_id>/filename.jpg
create policy "read own files" on storage.objects for select to authenticated
  using (
    bucket_id = 'receipts'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

create policy "upload own files" on storage.objects for insert to authenticated
  with check (
    bucket_id = 'receipts'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );
```

Keep the bucket private and serve files through signed URLs with a short expiry — a public
bucket bypasses these policies for reads.

Source: https://supabase.com/docs/guides/storage/security/access-control

---

## 8. Helper functions against recursion

Whenever a policy queries the very table it protects, recursion occurs (error 42P17). Moving
the lookup into a `security definer` function solves it, because that function bypasses RLS.

Rules for such functions:

```sql
create or replace function my_team_ids()
returns setof uuid
language sql
security definer          -- bypasses RLS → no recursion
set search_path = ''      -- required, otherwise hijacking is possible
stable                    -- lets Postgres cache the result per query
as $$
  select team_id from public.team_members where user_id = auth.uid();
$$;

revoke execute on function my_team_ids() from public;
grant execute on function my_team_ids() to authenticated;
```

- Mark it `stable`, not `volatile`, otherwise it is re-executed per row.
- Fully qualify objects (`public.team_members`), because `search_path` is empty.
- Return nothing the caller is not allowed to see. This function is a deliberate hole in the
  protection and must be as narrow as possible.
- Always filter on `where user_id = auth.uid()` — never accept a parameter that would let
  someone query other people's memberships.

---

## 9. Using JWT claims

```sql
-- Role straight from the token instead of from a table
create policy "admins only" on audit_log for select to authenticated
  using ( ((select auth.jwt()) -> 'app_metadata' ->> 'role') = 'admin' );
```

Important: **use `app_metadata` only, never `user_metadata`.** Users can change
`user_metadata` themselves through the auth API, so a policy based on it is worthless.
`app_metadata` can only be set server-side with the secret key.

The downside compared with a table: revoking a role only takes effect once the token is
refreshed. For security-critical roles, prefer the table approach (pattern 3).

Source: https://supabase.com/docs/guides/database/postgres/row-level-security
