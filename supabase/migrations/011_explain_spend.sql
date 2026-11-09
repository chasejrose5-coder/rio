-- One explain spend counter for Streamlit and the API. Safe to run more than once.
-- The $25 cap stays in the app (SPEND_CAP_MICRO_USD). This row only stores
-- the microdollars already reserved. The service role is the only role
-- granted the table and the two functions. A signed-in athlete is not.
-- Run this in the SQL editor. The app does not apply it.
-- Until it has been run, both apps keep the JSON file
-- (RIO_EXPLAIN_SPEND_PATH, otherwise data/explain_spend.json).
-- After it has been run, a process that is not pinned to that file uses this row.

create table if not exists public.explain_spend (
  id text primary key,
  micro_usd bigint not null default 0,
  updated_at timestamptz not null default now(),
  constraint explain_spend_one check (id = 'global'),
  constraint explain_spend_nonnegative check (micro_usd >= 0)
);

insert into public.explain_spend (id, micro_usd)
values ('global', 0)
on conflict (id) do nothing;

alter table public.explain_spend enable row level security;

revoke all on table public.explain_spend from public;
revoke all on table public.explain_spend from anon;
revoke all on table public.explain_spend from authenticated;
grant all on table public.explain_spend to service_role;

create or replace function public.touch_explain_spend_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists explain_spend_touch_updated_at on public.explain_spend;
create trigger explain_spend_touch_updated_at
  before insert or update on public.explain_spend
  for each row
  execute function public.touch_explain_spend_updated_at();

create or replace function public.reserve_explain_spend(p_worst bigint, p_cap bigint)
returns boolean
language plpgsql
security definer
set search_path = public
as $$
declare
  current_micro bigint;
begin
  if p_worst is null or p_worst < 0 or p_cap is null or p_cap < 0 then
    return false;
  end if;
  insert into public.explain_spend (id, micro_usd)
  values ('global', 0)
  on conflict (id) do nothing;
  select micro_usd into current_micro
  from public.explain_spend
  where id = 'global'
  for update;
  if current_micro is null or current_micro >= p_cap then
    return false;
  end if;
  if p_worst = 0 then
    return true;
  end if;
  if current_micro + p_worst > p_cap then
    return false;
  end if;
  update public.explain_spend
  set micro_usd = current_micro + p_worst
  where id = 'global';
  return true;
end;
$$;

create or replace function public.settle_explain_spend(p_reserved bigint, p_actual bigint)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  current_micro bigint;
  next_micro bigint;
begin
  if p_reserved is null or p_reserved < 0 then
    p_reserved := 0;
  end if;
  if p_actual is null or p_actual < 0 then
    p_actual := p_reserved;
  end if;
  insert into public.explain_spend (id, micro_usd)
  values ('global', 0)
  on conflict (id) do nothing;
  select micro_usd into current_micro
  from public.explain_spend
  where id = 'global'
  for update;
  next_micro := coalesce(current_micro, 0) - p_reserved + p_actual;
  if next_micro < 0 then
    next_micro := 0;
  end if;
  update public.explain_spend
  set micro_usd = next_micro
  where id = 'global';
end;
$$;

revoke all on function public.reserve_explain_spend(bigint, bigint) from public;
revoke all on function public.reserve_explain_spend(bigint, bigint) from anon;
revoke all on function public.reserve_explain_spend(bigint, bigint) from authenticated;
grant execute on function public.reserve_explain_spend(bigint, bigint) to service_role;

create or replace function public.adopt_explain_spend(p_micro bigint)
returns bigint
language plpgsql
security definer
set search_path = public
as $$
declare
  current_micro bigint;
begin
  if p_micro is null or p_micro < 0 then
    p_micro := 0;
  end if;
  insert into public.explain_spend (id, micro_usd)
  values ('global', 0)
  on conflict (id) do nothing;
  select micro_usd into current_micro
  from public.explain_spend
  where id = 'global'
  for update;
  if current_micro is null or current_micro < p_micro then
    update public.explain_spend
    set micro_usd = p_micro
    where id = 'global';
    current_micro := p_micro;
  end if;
  return current_micro;
end;
$$;

revoke all on function public.adopt_explain_spend(bigint) from public;
revoke all on function public.adopt_explain_spend(bigint) from anon;
revoke all on function public.adopt_explain_spend(bigint) from authenticated;
grant execute on function public.adopt_explain_spend(bigint) to service_role;

revoke all on function public.settle_explain_spend(bigint, bigint) from public;
revoke all on function public.settle_explain_spend(bigint, bigint) from anon;
revoke all on function public.settle_explain_spend(bigint, bigint) from authenticated;
grant execute on function public.settle_explain_spend(bigint, bigint) to service_role;
