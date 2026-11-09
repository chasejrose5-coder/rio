# auto_adapt.py — judge a matched quality day and adapt later weeks.

"""A matched Tuesday or Thursday uses that activity's WORK elapsed times.

Those times go through the same ±3% judge as a hand-entered result.
The mark and the raw numbers are stored on the session. adapt() then
runs for that week, and only later weeks change. A day that already
has a mark is left as stored. Recovery days, long runs, and extra
activities are skipped. Empty and missing rep times are ignored.

This file does not call Intervals.icu. No model. No spend. No scores.
"""

from __future__ import annotations

from engines.season import adapt
from ui.last_session import fit_slots
from ui.no_watch import timed_mark
from ui.plan_store import MARKS
from ui.result import filled_times, goal_seconds, judge, result_box_count

_PLAN_KEYS = (
    "week_number",
    "day_of_week",
    "date",
    "template_id",
    "reason_codes",
    "target_outcome",
)


def auto_adapt(
    plan: dict,
    activities: object,
    actuals: object,
    goal: object,
    bases: dict | None = None,
) -> tuple[dict, dict, dict]:
    """Return the plan, the actuals, and the week marks just applied.

    The caller's plan and actuals are not changed. `bases` keeps the plan
    from before a week's results, so a later mark for that week does not
    adapt the already adapted plan. Days that already have a mark stay.
    """
    stored = actuals if isinstance(actuals, dict) else {}
    if not isinstance(plan, dict) or not isinstance(plan.get("sessions"), list):
        return plan, stored, {}
    seconds = _goal(goal)
    pending = _pending(plan, activities, stored, seconds)
    if not pending:
        return plan, stored, {}
    working_actuals = _copy_actuals(stored)
    working = plan
    applied: dict[int, str] = {}
    remembered = bases if isinstance(bases, dict) else {}
    for week in sorted({item["week"] for item in pending}):
        ready = _still_open(working, working_actuals, pending, week)
        if not ready:
            continue
        for item in ready:
            working_actuals[item["date"]] = item["row"]
        outcome = _week_outcome(working, working_actuals, week)
        if outcome is None:
            for item in ready:
                working_actuals.pop(item["date"], None)
            continue
        if week not in remembered:
            remembered[week] = _strip(working)
        for later in list(remembered):
            if isinstance(later, int) and not isinstance(later, bool) and later > week:
                del remembered[later]
        try:
            working = adapt(_strip(remembered[week]), week, outcome)
        except ValueError:
            for item in ready:
                working_actuals.pop(item["date"], None)
            raise
        applied[week] = outcome
    if not applied:
        return plan, stored, {}
    return working, working_actuals, applied


def _pending(plan: dict, activities: object, actuals: dict, goal: float | None) -> list[dict]:
    """Quality days that can take a mark. The first matched activity on a day wins."""
    by_date: dict[str, dict] = {}
    for session in plan["sessions"]:
        if isinstance(session, dict) and isinstance(session.get("date"), str):
            by_date[session["date"]] = session
    found: list[dict] = []
    seen: set[str] = set()
    for activity in activities or []:
        if not isinstance(activity, dict) or activity.get("matched") is not True:
            continue
        day = activity.get("date")
        if not isinstance(day, str) or day in seen:
            continue
        session = by_date.get(day)
        if not isinstance(session, dict) or not _quality_day(session):
            continue
        seen.add(day)
        saved = actuals.get(day)
        if isinstance(saved, dict) and saved.get("mark") in MARKS:
            continue
        template_id = session.get("template_id")
        named = activity.get("template_id")
        if isinstance(named, str) and named.strip() and named.strip() != template_id:
            continue
        week = session.get("week_number")
        if isinstance(week, bool) or not isinstance(week, int):
            continue
        row = _result_row(template_id, activity, goal)
        if row is None:
            continue
        found.append(
            {
                "week": week,
                "date": day,
                "template_id": template_id,
                "row": row,
            }
        )
    return found


def _still_open(plan: dict, actuals: dict, pending: list[dict], week: int) -> list[dict]:
    """Drop a day whose workout changed, or that gained a mark, before adapt."""
    by_date = {
        session.get("date"): session
        for session in plan["sessions"]
        if isinstance(session, dict)
    }
    ready = []
    for item in pending:
        if item["week"] != week:
            continue
        session = by_date.get(item["date"])
        if (
            not isinstance(session, dict)
            or session.get("week_number") != week
            or session.get("template_id") != item["template_id"]
            or not _quality_day(session)
        ):
            continue
        saved = actuals.get(item["date"])
        if isinstance(saved, dict) and saved.get("mark") in MARKS:
            continue
        ready.append(item)
    return ready


def _result_row(template_id: object, activity: dict, goal: float | None) -> dict | None:
    """The actual a hand-entered result would store. Empty reps are left out."""
    slots = fit_slots(activity.get("reps"), result_box_count(template_id))
    text = filled_times(slots)
    if not text:
        return None
    judged = judge(template_id, text, goal)
    if not isinstance(judged, dict) or judged.get("mark") not in MARKS:
        return None
    numbers = judged.get("numbers")
    if not isinstance(numbers, list) or not numbers:
        return None
    row = {
        "text": text,
        "numbers": list(numbers),
        "mark": judged["mark"],
        "template_id": template_id,
        "slots": list(slots),
    }
    ref = _ref(activity.get("id"))
    if ref is not None:
        row["intervals"] = ref
    return row


def _quality_day(session: dict) -> bool:
    """Tuesday and Thursday work. Recovery and the long run stay closed."""
    if str(session.get("day_of_week")) not in ("Tuesday", "Thursday"):
        return False
    template_id = session.get("template_id")
    if not isinstance(template_id, str) or not template_id or template_id.startswith("aer_"):
        return False
    return True


def _week_outcome(plan: dict, actuals: dict, week: int) -> str | None:
    """not_hitting wins, then smashing. Same order adapt() uses for a list."""
    found = []
    for session in plan["sessions"]:
        if session.get("week_number") != week or not _quality_day(session):
            continue
        saved = actuals.get(session.get("date"))
        if not isinstance(saved, dict) or saved.get("template_id") != session.get("template_id"):
            continue
        mark = timed_mark(saved)
        if mark in MARKS:
            found.append(mark)
    if not found:
        return None
    if "not_hitting" in found:
        return "not_hitting"
    if "smashing" in found:
        return "smashing"
    return "on_track"


def _goal(value: object) -> float | None:
    if isinstance(value, str):
        return goal_seconds(value)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number <= 0:
        return None
    return number


def _strip(plan: dict) -> dict:
    """The six session fields adapt() checks. Result numbers stay off this copy."""
    sessions = []
    for session in plan["sessions"]:
        if not isinstance(session, dict):
            raise ValueError("session fields are not the season fields")
        row = {}
        for key in _PLAN_KEYS:
            if key not in session:
                raise ValueError("session fields are not the season fields")
            value = session[key]
            row[key] = list(value) if key == "reason_codes" else value
        sessions.append(row)
    return {
        "ontology_version": plan.get("ontology_version"),
        "season_length_weeks": plan.get("season_length_weeks"),
        "start_date": plan.get("start_date"),
        "sessions": sessions,
    }


def _copy_actuals(actuals: dict) -> dict:
    copied = {}
    for day, row in actuals.items():
        if not isinstance(row, dict):
            copied[day] = row
            continue
        item = dict(row)
        if isinstance(item.get("numbers"), list):
            item["numbers"] = list(item["numbers"])
        if isinstance(item.get("slots"), list):
            item["slots"] = list(item["slots"])
        copied[day] = item
    return copied


def _ref(value: object) -> str | None:
    """Activity id stored with the actual. The record allows 120 characters."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if not text or len(text) > 120:
        return None
    if any(ord(char) < 32 for char in text):
        return None
    return text
