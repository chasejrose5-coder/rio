-- Lock profiles.role. Safe to run more than once.
-- Authenticated users cannot change role. New rows stay athlete.
-- The service role may still set role, which is how Admin is recorded.

create or replace function public.lock_profile_role()
returns trigger
language plpgsql
as $$
begin
  if coalesce(auth.role(), '') = 'service_role'
     or current_user in ('service_role', 'postgres', 'supabase_admin') then
    return new;
  end if;
  if tg_op = 'INSERT' then
    new.role := 'athlete';
    return new;
  end if;
  new.role := old.role;
  return new;
end;
$$;

drop trigger if exists profiles_lock_role on public.profiles;
create trigger profiles_lock_role
  before insert or update on public.profiles
  for each row
  execute function public.lock_profile_role();

revoke update on table public.profiles from authenticated;
grant update (email, display_name) on table public.profiles to authenticated;
