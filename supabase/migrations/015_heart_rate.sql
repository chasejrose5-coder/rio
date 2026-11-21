-- Resting heart rate, max heart rate, and any zone boundaries the runner edited.
-- Zones are calculated in the app with the Karvonen method. This table stores the inputs.
-- A signed-in athlete can read and write only their own row. auth.uid() is the scope.
-- The service role bypasses row level security. The app uses the signed-in key.
-- Safe to run more than once. Run this in the SQL editor. The app does not apply it.
-- Until it has been run, a hosted account cannot save heart rate.
-- 004 was never added. 005 runs after 003. This file is 015 so the numbers do not collide.

create table if not exists public.heart_rate (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  resting_hr numeric(5,1),
  max_hr numeric(5,1),
  no_monitor boolean not null default false,
  zones jsonb,
  updated_at timestamptz not null default now(),
  constraint heart_rate_resting check (resting_hr is null or (resting_hr >= 30 and resting_hr <= 100)),
  constraint heart_rate_max check (max_hr is null or (max_hr >= 140 and max_hr <= 230)),
  constraint heart_rate_order check (resting_hr is null or max_hr is null or max_hr > resting_hr),
  constraint heart_rate_pair check (
    (resting_hr is null and max_hr is null) or (resting_hr is not null and max_hr is not null)
  ),
  constraint heart_rate_zones_array check (zones is null or jsonb_typeof(zones) = 'array')
);

alter table public.heart_rate enable row level security;

revoke all on table public.heart_rate from public;
revoke all on table public.heart_rate from anon;
grant select, insert, update, delete on table public.heart_rate to authenticated;
grant all on table public.heart_rate to service_role;

drop policy if exists heart_rate_own on public.heart_rate;
create policy heart_rate_own on public.heart_rate
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create or replace function public.touch_heart_rate_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists heart_rate_touch_updated_at on public.heart_rate;
create trigger heart_rate_touch_updated_at
  before insert or update on public.heart_rate
  for each row
  execute function public.touch_heart_rate_updated_at();
