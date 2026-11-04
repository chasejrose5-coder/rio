-- One row per season, and reloads read the newest. Safe to run more than once.
-- updated_at already exists. This adds the unique key and keeps the newest duplicate.
-- Older copies of the same season (same user, dates, and times) are removed.
-- A different season is kept. Run this in the SQL editor. The app does not apply it.

delete from public.plans older
where exists (
  select 1
  from public.plans newer
  where newer.user_id = older.user_id
    and newer.start_date = older.start_date
    and newer.goal_date = older.goal_date
    and newer."current_time" = older."current_time"
    and newer.goal_time = older.goal_time
    and (
      newer.updated_at > older.updated_at
      or (newer.updated_at = older.updated_at and newer.ctid > older.ctid)
    )
);

create unique index if not exists plans_season_key
  on public.plans (user_id, start_date, goal_date, "current_time", goal_time);

create or replace function public.touch_plan_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists plans_touch_updated_at on public.plans;
create trigger plans_touch_updated_at
  before insert or update on public.plans
  for each row
  execute function public.touch_plan_updated_at();
