-- Quality bases and workout notes for one season. Safe to run more than once.
-- The plan, marks, and actuals stay on public.plans. This table holds the two
-- fields the Streamlit session used to drop: the plan from before each week's
-- adapt, and the post-workout note.
-- A signed-in athlete can read and write only their own rows. The service role
-- bypasses row level security. Run this in the SQL editor. The app does not apply it.
-- Until it has been run, the API rebuilds a missing base from the stored marks,
-- earliest week first, starting from sequence() rather than the saved plan.

create table if not exists public.season_state (
  user_id uuid not null references public.profiles (id) on delete cascade,
  "current_time" text not null default '',
  start_date text not null default '',
  goal_time text not null default '',
  goal_date text not null default '',
  quality_base jsonb not null default '{}'::jsonb,
  workout_notes jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  primary key (user_id, start_date, goal_date, "current_time", goal_time)
);

alter table public.season_state enable row level security;

revoke all on table public.season_state from public;
revoke all on table public.season_state from anon;
grant select, insert, update, delete on table public.season_state to authenticated;
grant all on table public.season_state to service_role;

drop policy if exists season_state_own on public.season_state;
create policy season_state_own on public.season_state
  for all to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create or replace function public.touch_season_state_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

drop trigger if exists season_state_touch_updated_at on public.season_state;
create trigger season_state_touch_updated_at
  before insert or update on public.season_state
  for each row
  execute function public.touch_season_state_updated_at();

-- The past-season delete also removes this row. The plans and results deletes
-- are the same ones 008 already runs. A goal date of today or later is refused.
create or replace function public.delete_past_season(
  p_current_time text,
  p_start_date text,
  p_goal_time text,
  p_goal_date text,
  p_today text
) returns void
language plpgsql
security invoker
set search_path = public
as $$
begin
  if auth.uid() is null then
    raise exception 'not allowed';
  end if;
  if p_goal_date !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
     or p_today !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
     or p_goal_date >= p_today then
    raise exception 'current season';
  end if;

  delete from public.results r
  where r.user_id = auth.uid()
    and (
      (
        coalesce(r.payload ->> 'current_time', '') = p_current_time
        and coalesce(r.payload ->> 'start_date', '') = p_start_date
        and coalesce(r.payload ->> 'goal_time', '') = p_goal_time
        and coalesce(r.payload ->> 'goal_date', '') = p_goal_date
        and p_start_date <> ''
      )
      or (
        r.logged_on <> ''
        and exists (
          select 1
          from public.plans p
          where p.user_id = auth.uid()
            and p.start_date = p_start_date
            and p.goal_date = p_goal_date
            and p."current_time" = p_current_time
            and p.goal_time = p_goal_time
            and p.actuals ? r.logged_on
            and (
              coalesce(r.template_id, '') = ''
              or r.template_id = coalesce(p.actuals -> r.logged_on ->> 'template_id', '')
            )
        )
        and not exists (
          select 1
          from public.plans other
          where other.user_id = auth.uid()
            and other.actuals ? r.logged_on
            and not (
              other.start_date = p_start_date
              and other.goal_date = p_goal_date
              and other."current_time" = p_current_time
              and other.goal_time = p_goal_time
            )
        )
      )
    );

  delete from public.season_state
  where user_id = auth.uid()
    and start_date = p_start_date
    and goal_date = p_goal_date
    and "current_time" = p_current_time
    and goal_time = p_goal_time;

  delete from public.plans
  where user_id = auth.uid()
    and start_date = p_start_date
    and goal_date = p_goal_date
    and "current_time" = p_current_time
    and goal_time = p_goal_time;
end;
$$;

revoke all on function public.delete_past_season(text, text, text, text, text) from public;
revoke all on function public.delete_past_season(text, text, text, text, text) from anon;
grant execute on function public.delete_past_season(text, text, text, text, text) to authenticated;
