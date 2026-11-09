-- Delete one past season for the signed-in athlete, in one transaction.
-- Results are removed only when they name this season or match one of its
-- logged days and that day is not stored on another of this athlete's seasons.
-- The current season (goal date today or later) is refused. Other athletes
-- stay behind row level security and auth.uid(). Safe to run more than once.
-- Run this in the SQL editor. Until it has been run, the app deletes the
-- same rows one by one with the signed-in key.

create index if not exists results_user_logged
  on public.results (user_id, logged_on);

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
