-- Stretching completions and sore spots for the signed-in athlete.
-- Exercise text stays in the app. These rows are only what the runner marked.
-- A signed-in athlete can read and write only their own rows. auth.uid() is the scope.
-- The service role bypasses row level security. The app uses the signed-in key.
-- Safe to run more than once. Run this in the SQL editor. The app does not apply it.
-- Until it has been run, the Stretching tab cannot save Done or a sore spot.

create table if not exists public.stretch_completions (
  user_id uuid not null references public.profiles (id) on delete cascade,
  done_on date not null,
  routine_id text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, done_on, routine_id),
  constraint stretch_completions_routine_id check (routine_id <> '')
);

create table if not exists public.sore_spots (
  user_id uuid not null references public.profiles (id) on delete cascade,
  region text not null,
  severity text not null,
  started_on date not null,
  check_in_on date not null,
  cleared boolean not null default false,
  updated_at timestamptz not null default now(),
  primary key (user_id, region),
  constraint sore_spots_region check (region <> ''),
  constraint sore_spots_severity check (severity in ('mild', 'moderate', 'sharp'))
);

alter table public.stretch_completions enable row level security;
alter table public.sore_spots enable row level security;

revoke all on table public.stretch_completions from public;
revoke all on table public.stretch_completions from anon;
grant select, insert, update, delete on table public.stretch_completions to authenticated;
grant all on table public.stretch_completions to service_role;

revoke all on table public.sore_spots from public;
revoke all on table public.sore_spots from anon;
grant select, insert, update, delete on table public.sore_spots to authenticated;
grant all on table public.sore_spots to service_role;

drop policy if exists stretch_completions_own on public.stretch_completions;
create policy stretch_completions_own on public.stretch_completions
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists sore_spots_own on public.sore_spots;
create policy sore_spots_own on public.sore_spots
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create or replace function public.touch_sore_spots_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists sore_spots_touch_updated_at on public.sore_spots;
create trigger sore_spots_touch_updated_at
  before insert or update on public.sore_spots
  for each row
  execute function public.touch_sore_spots_updated_at();
