-- Strava OAuth nonce. Safe to run more than once.
-- The browser tab does not store this. The service role writes it, the same
-- way it writes strava_tokens. A signed-in athlete is not granted the table.
-- Run this in the SQL editor. The app does not apply it.
-- Until it has been run, the API cannot start a hosted Strava connect.
-- The Streamlit app does not read this table. Its callback is unchanged.

create table if not exists public.strava_oauth (
  user_id uuid primary key references public.profiles (id) on delete cascade,
  nonce text not null,
  state text not null,
  redirect_uri text not null default '',
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.strava_oauth enable row level security;

revoke all on table public.strava_oauth from public;
revoke all on table public.strava_oauth from anon;
revoke all on table public.strava_oauth from authenticated;
grant all on table public.strava_oauth to service_role;

create index if not exists strava_oauth_expires_at on public.strava_oauth (expires_at);

create or replace function public.touch_strava_oauth_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists strava_oauth_touch_updated_at on public.strava_oauth;
create trigger strava_oauth_touch_updated_at
  before insert or update on public.strava_oauth
  for each row
  execute function public.touch_strava_oauth_updated_at();
