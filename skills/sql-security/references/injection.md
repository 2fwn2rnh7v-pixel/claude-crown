# Preventing SQL Injection

Contents:
1. The underlying principle
2. The Supabase client
3. Direct SQL access
4. Dynamic SQL in Postgres functions
5. SECURITY DEFINER and search_path
6. Input validation with Zod
7. Test cases

---

## 1. The underlying principle

Injection always has the same cause: **input becomes part of the command** instead of staying a
value inside the command.

```
command and data kept apart   → safe      (parameters, placeholders)
command built from data       → unsafe    (string concatenation)
```

Hand-rolled escaping is not a solution. There are too many edge cases (encodings, Unicode,
nested quotes). Separating command from data is the solution.

Source: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html

---

## 2. The Supabase client

The JS client parameterises automatically. These calls are safe even when `input` comes
straight from a form:

```ts
await supabase.from('customers').select('id, name').eq('name', input)
await supabase.from('customers').select('*').ilike('name', `%${input}%`)   // a value, not code
await supabase.rpc('search_customers', { p_term: input })
```

Two places need care:

```ts
// table and column names are NOT parameters
await supabase.from(tableFromInput).select('*')        // ❌ never from user input
await supabase.from('customers').select(colsFromInput) // ❌

// correct: whitelist
const ALLOWED_SORTS = ['created_at', 'name', 'amount'] as const
type SortKey = typeof ALLOWED_SORTS[number]

function checkSort(value: string): SortKey {
  if ((ALLOWED_SORTS as readonly string[]).includes(value)) return value as SortKey
  return 'created_at'
}

await supabase.from('orders').select('*').order(checkSort(input))
```

Rule: **parameterise values, whitelist identifiers.** There is no parameterisation for
identifiers — not here and not in Postgres itself.

Also delicate: `.or()` and `.filter()` take a string in PostgREST syntax. Building unchecked
input into that string lets an attacker bend the filter logic. It is not classic SQL injection,
but it grants access to more rows than intended.

```ts
// ❌ input shapes the filter expression
.or(`name.ilike.%${input}%`)

// ✅ strip the characters that are syntax here
const safe = input.replace(/[,()\\.*]/g, '')
.or(`name.ilike.%${safe}%,city.ilike.%${safe}%`)
```

---

## 3. Direct SQL access

With `postgres.js`, `node-postgres` or Drizzle, the same principle applies:

```ts
// node-postgres — placeholders
await client.query('select id, name from customers where name = $1 and active = $2', [name, true])

// postgres.js — the template tag parameterises automatically
const rows = await sql`select id, name from customers where name = ${name}`

// ❌ never
await client.query(`select * from customers where name = '${name}'`)
```

With the `postgres.js` template tag, understand what `${}` does: it becomes a parameter.
Injecting a whole SQL fragment requires `sql.unsafe()` — that name is a warning, and it must
never receive user input.

---

## 4. Dynamic SQL in Postgres functions

This is where injection most often appears in Supabase projects, because `plpgsql` makes string
building so convenient.

```sql
-- ❌ vulnerable
create function search(p_column text, p_value text) returns setof customers
language plpgsql as $$
begin
  return query execute 'select * from customers where ' || p_column || ' = ''' || p_value || '''';
end; $$;
```

Calling it with `p_value = ''' or ''1''=''1` returns every row.

```sql
-- ✅ safe: format() with %I for identifiers, using for values
create function search(p_column text, p_value text) returns setof customers
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if p_column not in ('name', 'city', 'customer_number') then
    raise exception 'Invalid column: %', p_column;
  end if;

  return query execute
    format('select * from public.customers where %I = $1', p_column)
    using p_value;
end; $$;
```

The three building blocks:

| Building block | Purpose |
|----------------|---------|
| `format(..., %I, ...)` | quotes an **identifier** correctly |
| `format(..., %L, ...)` | quotes a **literal** correctly |
| `execute ... using $1` | passes the value as a **parameter** — the best option |
| `if ... not in (...)` | whitelist for identifiers, in addition to `%I` |

Better still: avoid dynamic SQL entirely. Most of the time the same thing can be written
statically:

```sql
select * from public.customers
where (p_column = 'name' and name = p_value)
   or (p_column = 'city' and city = p_value);
```

Source: https://www.postgresql.org/docs/current/plpgsql-statements.html#PLPGSQL-STATEMENTS-EXECUTING-DYN

---

## 5. SECURITY DEFINER and search_path

A `security definer` function runs with its creator's privileges and therefore bypasses RLS.
Without a fixed `search_path`, an attacker can place their own table or function in a schema
that is searched earlier and get the function to use it instead.

```sql
create function is_admin() returns boolean
language sql
security definer
set search_path = ''          -- required
stable
as $$
  select exists (
    select 1 from public.user_roles
    where user_id = auth.uid() and role = 'manager'
  );
$$;
```

Rules for `security definer`:

1. Always `set search_path = ''` (or an explicit, minimal path).
2. Fully qualify every object inside: `public.table`, not `table`.
3. Do only what is necessary — no generic "run whatever I say" functions.
4. `revoke execute ... from public` and grant it specifically to the role that needs it.
5. Check inside the body whether the caller is allowed to do this. The function will not check
   on its own.

```sql
revoke execute on function is_admin() from public;
grant execute on function is_admin() to authenticated;
```

`supabase db lint` and the Security Advisor report `security definer` functions without a fixed
`search_path`. Do not dismiss those warnings.

Source: https://www.postgresql.org/docs/current/sql-createfunction.html

---

## 6. Input validation with Zod

Parameterisation prevents injection. Validation prevents nonsense. Both are needed.

```ts
import { z } from 'zod'

const OrderSchema = z.object({
  title:       z.string().trim().min(1).max(200),
  customer_id: z.string().uuid(),
  amount_net:  z.number().nonnegative().max(1_000_000),
  status:      z.enum(['open', 'in_progress', 'done', 'cancelled']),
})

export async function POST(req: Request) {
  const result = OrderSchema.safeParse(await req.json())
  if (!result.success) {
    return Response.json({ error: result.error.flatten() }, { status: 400 })
  }
  // result.data is now typed and checked
}
```

Validation belongs on the **server**. Client-side checking is a convenience for the user, not a
security control — an attacker sends the request directly.

Ideally the Zod schemas mirror the table's CHECK constraints. The database is the last line:
even if some code path skips validation, the constraint rejects the row.

---

## 7. Test cases

These inputs belong in the tests of every endpoint that accepts text:

```
'
' OR '1'='1
'; drop table orders; --
%' --
\u0000
<script>alert(1)</script>
../../etc/passwd
{"$ne": null}
a 10,000 character string
```

Expected behaviour: **400 Bad Request** or an empty result — never a server error containing SQL
details, and never more rows than intended.

Never pass raw error messages to the client:

```ts
// ❌ leaks table names, constraints, structure
return Response.json({ error: dbError.message }, { status: 500 })

// ✅
console.error('DB error in create_order', dbError)
return Response.json({ error: 'The order could not be saved' }, { status: 500 })
```
