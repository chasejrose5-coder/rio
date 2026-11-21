-- Easy-day bike swaps for the signed-in athlete.
-- A row means that plan day is a bike instead of the easy run.
-- Minutes, distance, heart rate, and zone seconds are filled when the ride is logged.
-- A signed-in athlete can read and write only their own rows. auth.uid() is the scope.
-- The service role bypasses row level security. The app uses the signed-in key.
-- Safe to run more than once. Run this in the SQL editor. The app does not apply it.
-- Until it has been run, a hosted account cannot save a bike swap.

create table if not exists public.bike_sessions (
  user_id uuid not null references public.profiles (id) on delete cascade,
  done_on date not null,
  minutes integer,
  distance_m integer,
  avg_hr integer,
  strava_id text,
  zone_seconds jsonb,
  updated_at timestamptz not null default now(),
  primary key (user_id, done_on),
  constraint bike_sessions_minutes check (minutes is null or minutes > 0),
  constraint bike_sessions_distance check (distance_m is null or distance_m >= 0),
  constraint bike_sessions_hr check (avg_hr is null or (avg_hr >= 30 and avg_hr <= 230)),
  constraint bike_sessions_zones check (zone_seconds is null or jsonb_typeof(zone_seconds) = 'array')
);

alter table public.bike_sessions enable row level security;

revoke all on table public.bike_sessions from public;
revoke all on table public.bike_sessions from anon;
grant select, insert, update, delete on table public.bike_sessions to authenticated;
grant all on table public.bike_sessions to service_role;

drop policy if exists bike_sessions_own on public.bike_sessions;
create policy bike_sessions_own on public.bike_sessions
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create or replace function public.touch_bike_sessions_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists bike_sessions_touch_updated_at on public.bike_sessions;
create trigger bike_sessions_touch_updated_at
  before insert or update on public.bike_sessions
  for each row
  execute function public.touch_bike_sessions_updated_at();
