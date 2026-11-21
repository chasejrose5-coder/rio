-- Core-circuit done marks for the signed-in athlete.
-- The exercise text stays in the app. A row is the day the runner marked the circuit done.
-- A signed-in athlete can read and write only their own rows. auth.uid() is the scope.
-- The service role bypasses row level security. The app uses the signed-in key.
-- Safe to run more than once. Run this in the SQL editor. The app does not apply it.
-- Until it has been run, a hosted account cannot save a core done mark.

create table if not exists public.core_completions (
  user_id uuid not null references public.profiles (id) on delete cascade,
  done_on date not null,
  created_at timestamptz not null default now(),
  primary key (user_id, done_on)
);

alter table public.core_completions enable row level security;

revoke all on table public.core_completions from public;
revoke all on table public.core_completions from anon;
grant select, insert, update, delete on table public.core_completions to authenticated;
grant all on table public.core_completions to service_role;

drop policy if exists core_completions_own on public.core_completions;
create policy core_completions_own on public.core_completions
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
