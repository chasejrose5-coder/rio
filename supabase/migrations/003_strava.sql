-- Strava tokens and activities. Safe to run more than once.
-- Tokens are not granted to the signed-in role. The service role reads them.
-- Activities are granted like the other per-user tables.

create table if not exists public.strava_tokens (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  athlete_id bigint,
  athlete_name text not null default '',
  access_token text not null default '',
  refresh_token text not null default '',
  expires_at bigint,
  last_sync_at bigint,
  scope text not null default '',
  updated_at timestamptz not null default now()
);

create table if not exists public.strava_activities (
  user_id uuid not null references public.profiles (id) on delete cascade,
  activity_id text not null,
  name text not null default '',
  sport_type text not null default '',
  start_local text not null default '',
  distance_m double precision,
  moving_seconds integer,
  elapsed_seconds integer,
  pace_s_per_km double precision,
  average_hr integer,
  max_hr integer,
  laps jsonb not null default '[]'::jsonb,
  template_id text not null default '',
  matched boolean not null default false,
  primary key (user_id, activity_id)
);

alter table public.strava_tokens enable row level security;
alter table public.strava_activities enable row level security;

grant usage on schema public to authenticated, service_role;

grant select, insert, update, delete on table public.strava_activities to authenticated;
grant all on table public.strava_tokens to service_role;
grant all on table public.strava_activities to service_role;

drop policy if exists strava_activities_own on public.strava_activities;
create policy strava_activities_own on public.strava_activities
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
