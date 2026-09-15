# Testing RLS

A policy that is not tested is a claim. The test that matters is the **negative test**: user B
must not see and must not change user A's data.

Contents:
1. The test matrix
2. Quick test in the SQL editor
3. Automated with pgTAP
4. Testing from the application
5. Automatic checks (advisor, lint)
6. Checklist

---

## 1. The test matrix

For each table, cover at least these cases, using two test users (A and B) plus a guest:

| # | Who | Action | Expectation |
|---|-----|--------|-------------|
| 1 | A | read own row | visible |
| 2 | **B** | **read A's row** | **not visible** |
| 3 | Guest (anon) | read anything | nothing visible |
| 4 | A | change own row | allowed |
| 5 | **B** | **change A's row** | **0 rows affected** |
| 6 | **B** | **delete A's row** | **0 rows affected** |
| 7 | A | insert a row with a foreign user_id | rejected |
| 8 | **A** | **reassign own row to B (update user_id)** | **rejected** |
| 9 | Guest | insert a row | rejected |

The bold cases are the actual security tests. Case 8 fails without `with check` on `update` —
and it is the one almost always forgotten.

Note that a denied `update` or `delete` raises **no error**. It simply affects zero rows. So
the test must assert on the row count rather than wait for an exception.

---

## 2. Quick test in the SQL editor

```sql
-- Setup: the row belongs to user A
insert into notes (id, user_id, body)
values ('aaaa1111-0000-0000-0000-000000000001',
        '11111111-1111-1111-1111-111111111111', 'A secret');

-- Now act as user B
begin;
  select set_config('request.jwt.claims',
    '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
  set local role authenticated;

  -- Case 2: can B see A's note?
  select count(*) from notes
   where id = 'aaaa1111-0000-0000-0000-000000000001';   -- expected: 0

  -- Case 5: can B change it?
  update notes set body = 'hijacked'
   where id = 'aaaa1111-0000-0000-0000-000000000001';   -- expected: UPDATE 0
rollback;
```

End with `rollback` so the test leaves no trace. `set local role` only lasts until the end of
the transaction, which is exactly what you want.

These tests only work when the current connection is not the table owner. In the Supabase SQL
editor you run as a privileged role, which is precisely why `set local role authenticated`
is needed.

---

## 3. Automated with pgTAP

Supabase ships pgTAP. Tests live in `supabase/tests/` and run with `supabase test db` —
ideally in CI on every pull request.

```sql
-- supabase/tests/notes_rls_test.sql
begin;
select plan(6);

-- Setup
insert into auth.users (id, email) values
  ('11111111-1111-1111-1111-111111111111', 'a@test.com'),
  ('22222222-2222-2222-2222-222222222222', 'b@test.com');

insert into notes (id, user_id, body) values
  ('aaaa1111-0000-0000-0000-000000000001',
   '11111111-1111-1111-1111-111111111111', 'From A');

-- Is RLS on at all?
select ok(
  (select relrowsecurity from pg_class where relname = 'notes'),
  'RLS is enabled on notes'
);

-- As user A
select set_config('request.jwt.claims',
  '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}', true);
set local role authenticated;

select is( (select count(*)::int from notes), 1, 'A sees their own note' );

-- As user B
reset role;
select set_config('request.jwt.claims',
  '{"sub":"22222222-2222-2222-2222-222222222222","role":"authenticated"}', true);
set local role authenticated;

select is( (select count(*)::int from notes), 0, 'B does NOT see the note from A' );

-- B tries to change it
with changed as (
  update notes set body = 'hijacked'
   where id = 'aaaa1111-0000-0000-0000-000000000001'
  returning 1
)
select is( (select count(*)::int from changed), 0, 'B cannot change the note from A' );

-- B tries to delete it
with removed as (
  delete from notes
   where id = 'aaaa1111-0000-0000-0000-000000000001'
  returning 1
)
select is( (select count(*)::int from removed), 0, 'B cannot delete the note from A' );

-- B tries to insert on behalf of A
select throws_ok(
  $$ insert into notes (user_id, body)
     values ('11111111-1111-1111-1111-111111111111', 'forged') $$,
  '42501',
  null,
  'B cannot create a note on behalf of A'
);

select * from finish();
rollback;
```

```bash
supabase test db
```

Useful pgTAP assertions: `ok()`, `is()`, `throws_ok()`, `results_eq()`, `has_index()`, and
`policies_are()`, which checks that exactly the expected policies exist.

```sql
select policies_are('public', 'notes', array[
  'notes_select', 'notes_insert', 'notes_update', 'notes_delete'
]);
```

That single assertion catches the case where someone later drops a policy or leaves an
operation unprotected.

---

## 4. Testing from the application

Worth adding, because it exercises the real path through the API including grants and PostgREST:

```ts
import { createClient } from '@supabase/supabase-js'

const url = process.env.NEXT_PUBLIC_SUPABASE_URL!
const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!

test('B does not see notes belonging to A', async () => {
  const clientB = createClient(url, key)
  await clientB.auth.signInWithPassword({ email: 'b@test.com', password: '…' })

  const { data } = await clientB.from('notes').select('*')
  expect(data?.some(n => n.user_id === USER_A_ID)).toBe(false)
})

test('B cannot change a note belonging to A', async () => {
  const clientB = createClient(url, key)
  await clientB.auth.signInWithPassword({ email: 'b@test.com', password: '…' })

  const { data } = await clientB
    .from('notes')
    .update({ body: 'hijacked' })
    .eq('id', NOTE_FROM_A)
    .select()

  expect(data).toHaveLength(0)      // no error, but also no effect
})
```

Run these against the **local** database, not against production.

---

## 5. Automatic checks

```bash
supabase db lint
```

The dashboard offers the same under **Advisors → Security**. Among the things it reports:

- tables in `public` without RLS ("Unrestricted")
- tables with RLS but no policy at all (unusable for everyone — usually an oversight)
- `security definer` functions without a fixed `search_path`
- views running with the creator's privileges and therefore bypassing RLS

This check belongs in CI. It takes seconds and catches exactly the mistakes that happen when a
new table is created in a hurry.

---

## 6. Checklist

```
[ ] RLS enabled (verified in pg_class.relrowsecurity, not just assumed)
[ ] One policy each for select / insert / update / delete
[ ] update has both using AND with check
[ ] Two test users exist, negative tests run and fail correctly
[ ] Test: inserting with a foreign user_id is rejected
[ ] Test: reassigning your own row to another user is rejected
[ ] Test: anon sees nothing
[ ] Grants checked (anon has nothing) → sql-security
[ ] supabase db lint / Security Advisor clean
[ ] Tests run in CI, not just once by hand
```

As long as a single negative test is missing, the table is not finished.
