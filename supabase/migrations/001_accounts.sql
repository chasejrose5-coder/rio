-- Round 1 accounts. Run this in the Supabase SQL editor.
-- New tables are not exposed until these grants exist.
-- Row level security is on. Each person can read and write only their own rows.

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text not null,
  display_name text not null default '',
  role text not null default 'athlete' check (role in ('athlete', 'coach', 'admin')),
  created_at timestamptz not null default now()
);

create table if not exists public.goals (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  event text not null default '800m',
  goal_time text not null default '',
  goal_date text not null default '',
  current_mark text not null default '',
  updated_at timestamptz not null default now()
);

create table if not exists public.plans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  -- current_time is reserved in Postgres. The quotes keep that column name.
  "current_time" text not null default '',
  start_date text not null default '',
  goal_time text not null default '',
  goal_date text not null default '',
  plan jsonb not null default '{}'::jsonb,
  marks jsonb not null default '{}'::jsonb,
  actuals jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.results (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  logged_on text not null default '',
  template_id text not null default '',
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.goals enable row level security;
alter table public.plans enable row level security;
alter table public.results enable row level security;

grant usage on schema public to authenticated, service_role;

grant select, insert, update, delete on table public.profiles to authenticated;
grant select, insert, update, delete on table public.goals to authenticated;
grant select, insert, update, delete on table public.plans to authenticated;
grant select, insert, update, delete on table public.results to authenticated;

grant all on table public.profiles to service_role;
grant all on table public.goals to service_role;
grant all on table public.plans to service_role;
grant all on table public.results to service_role;

drop policy if exists profiles_own on public.profiles;
create policy profiles_own on public.profiles
  for all to authenticated
  using (auth.uid() = id)
  with check (auth.uid() = id);

drop policy if exists goals_own on public.goals;
create policy goals_own on public.goals
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists plans_own on public.plans;
create policy plans_own on public.plans
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists results_own on public.results;
create policy results_own on public.results
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
