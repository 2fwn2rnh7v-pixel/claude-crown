create table notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  body text not null check (length(body) <= 10000),
  created_at timestamptz not null default now()
);
create index idx_notes_user on notes (user_id);

alter table notes enable row level security;
revoke all on notes from anon;
grant select, insert, update, delete on notes to authenticated;

create policy "notes_select" on notes for select to authenticated
  using ( (select auth.uid()) = user_id );
create policy "notes_insert" on notes for insert to authenticated
  with check ( (select auth.uid()) = user_id );
create policy "notes_update" on notes for update to authenticated
  using ( (select auth.uid()) = user_id )
  with check ( (select auth.uid()) = user_id );
create policy "notes_delete" on notes for delete to authenticated
  using ( (select auth.uid()) = user_id );

create or replace function my_team_ids() returns setof uuid
language sql security definer set search_path = '' stable
as $$ select team_id from public.team_members where user_id = auth.uid(); $$;
