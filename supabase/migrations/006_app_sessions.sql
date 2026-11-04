-- Hosted session tokens. Safe to run more than once.
-- The browser cookie stores only an id. This table stores the tokens.
-- No policy is granted to signed-in users. The service role bypasses RLS.
-- Run this in the Supabase SQL editor. The app does not apply it.

create table if not exists public.app_sessions (
  sid_hash text primary key,
  -- No foreign key: a Google sign-in can store a session before the profile row exists.
  -- delete_user removes these rows. They also expire after a day.
  user_id uuid not null,
  access_token text not null default '',
  refresh_token text not null default '',
  email text not null default '',
  display_name text not null default '',
  issued_at bigint not null,
  expires_at timestamptz not null
);

alter table public.app_sessions enable row level security;

revoke all on table public.app_sessions from public;
revoke all on table public.app_sessions from anon;
revoke all on table public.app_sessions from authenticated;
grant all on table public.app_sessions to service_role;
