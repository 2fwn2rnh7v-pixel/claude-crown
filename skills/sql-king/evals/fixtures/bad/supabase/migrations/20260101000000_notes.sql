-- bad: no RLS, FK without index, for all policy, unwrapped auth.uid(), definer without search_path
create table notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  team_id uuid references teams(id),
  body text not null,
  created_at timestamptz not null default now()
);

create table teams (
  id uuid primary key default gen_random_uuid(),
  name text not null
);
alter table teams enable row level security;

create policy "teams_all" on teams for all
  using ( auth.uid() is not null );

create policy "teams_update" on teams for update to authenticated
  using ( id in (select my_team_ids()) );

create or replace function my_team_ids() returns setof uuid
language sql security definer stable
as $$ select team_id from public.team_members where user_id = auth.uid(); $$;
