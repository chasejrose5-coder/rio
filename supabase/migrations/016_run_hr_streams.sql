-- Heart-rate samples for one Strava run, so time-in-zone can be counted again
-- when resting or max heart rate changes. The activity list does not store this.
-- A signed-in athlete can read and write only their own rows. auth.uid() is the scope.
-- The service role bypasses row level security. The app uses the signed-in key.
-- Safe to run more than once. Run this in the SQL editor. The app does not apply it.
-- Until it has been run, a hosted account cannot save a heart-rate stream.
-- activity:read_all already allows these activity streams. No new Strava scope.

create table if not exists public.run_hr_streams (
  user_id uuid not null references public.profiles (id) on delete cascade,
  activity_id text not null,
  sample_time jsonb not null,
  sample_hr jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (user_id, activity_id),
  constraint run_hr_streams_activity check (activity_id <> ''),
  constraint run_hr_streams_time_array check (jsonb_typeof(sample_time) = 'array'),
  constraint run_hr_streams_hr_array check (jsonb_typeof(sample_hr) = 'array')
);

alter table public.run_hr_streams enable row level security;

revoke all on table public.run_hr_streams from public;
revoke all on table public.run_hr_streams from anon;
grant select, insert, update, delete on table public.run_hr_streams to authenticated;
grant all on table public.run_hr_streams to service_role;

drop policy if exists run_hr_streams_own on public.run_hr_streams;
create policy run_hr_streams_own on public.run_hr_streams
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create or replace function public.touch_run_hr_streams_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists run_hr_streams_touch_updated_at on public.run_hr_streams;
create trigger run_hr_streams_touch_updated_at
  before insert or update on public.run_hr_streams
  for each row
  execute function public.touch_run_hr_streams_updated_at();
