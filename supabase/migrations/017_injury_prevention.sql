-- Injury-prevention areas and done marks for the signed-in athlete.
-- Exercise text stays in the app. These rows are only what the runner marked.
-- A signed-in athlete can read and write only their own rows. auth.uid() is the scope.
-- The service role bypasses row level security. The app uses the signed-in key.
-- Safe to run more than once. Run this in the SQL editor. The app does not apply it.
-- Until it has been run, a hosted account cannot save a rebuilding area or a done mark.

create table if not exists public.injury_areas (
  user_id uuid not null references public.profiles (id) on delete cascade,
  area_id text not null,
  anchor_on date not null,
  level smallint not null default 0,
  updated_at timestamptz not null default now(),
  primary key (user_id, area_id),
  constraint injury_areas_id check (area_id <> ''),
  constraint injury_areas_level check (level between 0 and 2)
);

create table if not exists public.injury_completions (
  user_id uuid not null references public.profiles (id) on delete cascade,
  done_on date not null,
  block_id text not null,
  created_at timestamptz not null default now(),
  primary key (user_id, done_on, block_id),
  constraint injury_completions_block check (block_id <> '')
);

alter table public.injury_areas enable row level security;
alter table public.injury_completions enable row level security;

revoke all on table public.injury_areas from public;
revoke all on table public.injury_areas from anon;
grant select, insert, update, delete on table public.injury_areas to authenticated;
grant all on table public.injury_areas to service_role;

revoke all on table public.injury_completions from public;
revoke all on table public.injury_completions from anon;
grant select, insert, update, delete on table public.injury_completions to authenticated;
grant all on table public.injury_completions to service_role;

drop policy if exists injury_areas_own on public.injury_areas;
create policy injury_areas_own on public.injury_areas
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists injury_completions_own on public.injury_completions;
create policy injury_completions_own on public.injury_completions
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create or replace function public.touch_injury_areas_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists injury_areas_touch_updated_at on public.injury_areas;
create trigger injury_areas_touch_updated_at
  before insert or update on public.injury_areas
  for each row
  execute function public.touch_injury_areas_updated_at();
