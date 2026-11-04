-- Lock profiles.email. Safe to run more than once.
-- Authenticated users cannot change email. The service role still can.
-- Admin is decided from the confirmed auth user, not from this column.
-- Run this in the Supabase SQL editor. The app does not apply it.

create or replace function public.lock_profile_email()
returns trigger
language plpgsql
as $$
declare
  jwt_email text;
begin
  if coalesce(auth.role(), '') = 'service_role'
     or current_user in ('service_role', 'postgres', 'supabase_admin') then
    return new;
  end if;
  jwt_email := nullif(auth.jwt() ->> 'email', '');
  if tg_op = 'INSERT' then
    if jwt_email is not null then
      new.email := jwt_email;
    end if;
    return new;
  end if;
  new.email := old.email;
  return new;
end;
$$;

drop trigger if exists profiles_lock_email on public.profiles;
create trigger profiles_lock_email
  before insert or update on public.profiles
  for each row
  execute function public.lock_profile_email();

revoke update on table public.profiles from authenticated;
grant update (display_name) on table public.profiles to authenticated;
