-- Coach teams. Safe to run more than once.
-- New tables are not exposed until these grants exist.
-- A coach can read an athlete's rows. A coach cannot write them.

create table if not exists public.teams (
  id uuid primary key default gen_random_uuid(),
  coach_id uuid not null unique references public.profiles (id) on delete cascade,
  code text not null unique,
  created_at timestamptz not null default now()
);

create table if not exists public.team_members (
  athlete_id uuid primary key references public.profiles (id) on delete cascade,
  team_id uuid not null references public.teams (id) on delete cascade,
  joined_at timestamptz not null default now()
);

alter table public.teams enable row level security;
alter table public.team_members enable row level security;

grant usage on schema public to authenticated, service_role;

grant select, insert, update on table public.teams to authenticated;
grant select, delete on table public.team_members to authenticated;

grant all on table public.teams to service_role;
grant all on table public.team_members to service_role;

create or replace function public.caller_is_coach()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.profiles
    where id = auth.uid()
      and role in ('coach', 'admin')
  );
$$;

create or replace function public.coach_of(athlete uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.team_members as members
    join public.teams as teams on teams.id = members.team_id
    where teams.coach_id = auth.uid()
      and members.athlete_id = athlete
  );
$$;

revoke all on function public.caller_is_coach() from public;
revoke all on function public.coach_of(uuid) from public;
grant execute on function public.caller_is_coach() to authenticated;
grant execute on function public.coach_of(uuid) to authenticated;

drop policy if exists teams_select on public.teams;
create policy teams_select on public.teams
  for select to authenticated
  using (
    coach_id = auth.uid()
    or id in (
      select members.team_id
      from public.team_members as members
      where members.athlete_id = auth.uid()
    )
  );

drop policy if exists teams_insert on public.teams;
create policy teams_insert on public.teams
  for insert to authenticated
  with check (coach_id = auth.uid() and public.caller_is_coach());

drop policy if exists teams_update on public.teams;
create policy teams_update on public.teams
  for update to authenticated
  using (coach_id = auth.uid() and public.caller_is_coach())
  with check (coach_id = auth.uid() and public.caller_is_coach());

drop policy if exists members_select on public.team_members;
create policy members_select on public.team_members
  for select to authenticated
  using (
    athlete_id = auth.uid()
    or public.coach_of(athlete_id)
  );

drop policy if exists members_delete on public.team_members;
create policy members_delete on public.team_members
  for delete to authenticated
  using (athlete_id = auth.uid());

drop policy if exists profiles_team_read on public.profiles;
create policy profiles_team_read on public.profiles
  for select to authenticated
  using (
    public.coach_of(id)
    or id in (
      select teams.coach_id
      from public.teams as teams
      join public.team_members as members on members.team_id = teams.id
      where members.athlete_id = auth.uid()
    )
  );

drop policy if exists goals_coach_read on public.goals;
create policy goals_coach_read on public.goals
  for select to authenticated
  using (public.coach_of(user_id));

drop policy if exists plans_coach_read on public.plans;
create policy plans_coach_read on public.plans
  for select to authenticated
  using (public.coach_of(user_id));

drop policy if exists results_coach_read on public.results;
create policy results_coach_read on public.results
  for select to authenticated
  using (public.coach_of(user_id));

create or replace function public.join_team(join_code text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  found uuid;
  me uuid;
begin
  me := auth.uid();
  if me is null then
    raise exception 'Sign in again.';
  end if;
  if join_code is null or length(trim(join_code)) < 6 or length(trim(join_code)) > 8 then
    raise exception 'That code is not a team.';
  end if;
  select id into found
  from public.teams
  where code = upper(trim(join_code));
  if found is null then
    raise exception 'That code is not a team.';
  end if;
  if exists (
    select 1 from public.teams
    where id = found and coach_id = me
  ) then
    raise exception 'That code is your own team.';
  end if;
  if exists (
    select 1 from public.team_members
    where athlete_id = me
  ) then
    raise exception 'Leave your team before joining another.';
  end if;
  insert into public.team_members (team_id, athlete_id)
  values (found, me);
end;
$$;

revoke all on function public.join_team(text) from public;
grant execute on function public.join_team(text) to authenticated;
