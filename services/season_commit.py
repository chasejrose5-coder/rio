# season_commit.py — judge, adapt, and store one result or week mark.

"""The transaction behind a saved result, a week mark, and an activity match.

The caller's actuals dict and quality-base dict are updated in place, the
same way the shell used to update them. The plan dict that was passed in
is not modified. A failed adapt puts the day's previous actual back and
returns the error text. It does not roll the quality base back: the base
is recorded before adapt() runs.

No Streamlit. No session. No model. No score.
"""

from __future__ import annotations

from dataclasses import dataclass

from engines.season import adapt
from ui.auto_adapt import auto_adapt
from ui.no_watch import timed_mark
from ui.plan_store import MARKS
from ui.result import judge

PLAN_KEYS = (
    "week_number",
    "day_of_week",
    "date",
    "template_id",
    "reason_codes",
    "target_outcome",
)


@dataclass
class CommitOutcome:
    """What the shell writes after one result or one week mark."""

    committed: bool = False
    plan: dict | None = None
    marks: dict | None = None
    error: str | None = None
    note_mark: str | None = None
    note_detail: str | None = None


@dataclass
class ActivityMarkOutcome:
    """What the shell writes after a pull judges unmarked quality days."""

    applied: bool = False
    plan: dict | None = None
    marks: dict | None = None
    actuals: dict | None = None
    notice: str | None = None


def quality_day(session: dict) -> bool:
    """Tuesday and Thursday work. Recovery and the long run stay closed."""
    if str(session.get("day_of_week")) not in ("Tuesday", "Thursday"):
        return False
    template_id = str(session.get("template_id") or "")
    return bool(template_id) and not template_id.startswith("aer_")


def plan_for_adapt(plan: dict) -> dict:
    """The six session fields adapt() checks. Result numbers stay off this copy."""
    sessions = []
    for session in plan["sessions"]:
        row = {}
        for key in PLAN_KEYS:
            value = session[key]
            row[key] = list(value) if key == "reason_codes" else value
        sessions.append(row)
    return {
        "ontology_version": plan.get("ontology_version"),
        "season_length_weeks": plan.get("season_length_weeks"),
        "start_date": plan.get("start_date"),
        "sessions": sessions,
    }


def stored_slot(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = round(float(value), 2)
    if number <= 0:
        return None
    return number


def intervals_ref(value: object) -> str | None:
    """Activity id or filename kept with the actual. The record allows 120 characters."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > 120:
        return None
    return text


def attach_actuals(plan: dict, actuals: dict) -> None:
    """Write stored numbers onto sessions that still use that template."""
    by_date = {session["date"]: session for session in plan["sessions"]}
    for day in list(actuals):
        saved = actuals[day]
        session = by_date.get(day)
        if (
            not isinstance(saved, dict)
            or session is None
            or session.get("template_id") != saved.get("template_id")
        ):
            actuals.pop(day, None)
            continue
        numbers = saved.get("numbers")
        if isinstance(numbers, list) and numbers:
            session["actual"] = list(numbers)


def week_mark(plan: dict, week: int, actuals: dict) -> str | None:
    """not_hitting wins, then smashing. Same order adapt() uses for a list.

    A Done choice with no clock time is not a timed effort.
    """
    found = []
    for session in plan["sessions"]:
        if session.get("week_number") != week or not quality_day(session):
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


def adapt_from_result(plan: dict, week: int, outcome: str, bases: dict, actuals: dict) -> dict:
    """One adapt for this week, from the plan before this week's results."""
    if week not in bases:
        bases[week] = plan_for_adapt(plan)
    for later in list(bases):
        if later > week:
            del bases[later]
    updated = adapt(bases[week], week, outcome)
    attach_actuals(updated, actuals)
    return updated


def _marks_copy(marks: object) -> dict:
    return dict(marks or {})


def _restore_day(actuals: dict, day: str, previous: object) -> None:
    if previous is None:
        actuals.pop(day, None)
    else:
        actuals[day] = previous


def commit_result(
    plan: dict,
    session: dict,
    text: str,
    slots: list | None,
    intervals: str | None,
    actuals: dict,
    marks: object,
    bases: dict,
    goal_seconds: float | None,
) -> CommitOutcome:
    """Store the numbers and call adapt once. Empty or invalid text does nothing."""
    if not text:
        return CommitOutcome()
    judged = judge(session.get("template_id"), text, goal_seconds)
    if judged is None:
        return CommitOutcome()
    day = str(session["date"])
    week = session["week_number"]
    previous = actuals.get(day)
    row = {
        "text": text,
        "numbers": list(judged["numbers"]),
        "mark": judged["mark"],
        "template_id": session.get("template_id"),
    }
    if isinstance(slots, list):
        row["slots"] = [stored_slot(item) for item in slots]
    ref = intervals_ref(intervals)
    if ref is not None:
        row["intervals"] = ref
    actuals[day] = row
    mark = week_mark(plan, week, actuals)
    if mark is None:
        _restore_day(actuals, day, previous)
        return CommitOutcome()
    try:
        updated = adapt_from_result(plan, week, mark, bases, actuals)
    except ValueError as exc:
        _restore_day(actuals, day, previous)
        return CommitOutcome(error=str(exc))
    stored = _marks_copy(marks)
    stored[week] = mark
    return CommitOutcome(
        committed=True,
        plan=updated,
        marks=stored,
        note_mark=str(row["mark"]),
        note_detail=text,
    )


def commit_watchless_mark(
    plan: dict,
    session: dict,
    row: dict,
    actuals: dict,
    marks: object,
    bases: dict,
) -> CommitOutcome:
    """Store a typed quality time and adapt, the same way a result does."""
    day = str(session["date"])
    week = session["week_number"]
    previous = actuals.get(day)
    actuals[day] = row
    mark = week_mark(plan, week, actuals)
    if mark is None:
        _restore_day(actuals, day, previous)
        return CommitOutcome()
    try:
        updated = adapt_from_result(plan, week, mark, bases, actuals)
    except ValueError as exc:
        _restore_day(actuals, day, previous)
        return CommitOutcome(error=str(exc))
    stored = _marks_copy(marks)
    stored[week] = mark
    return CommitOutcome(
        committed=True,
        plan=updated,
        marks=stored,
        note_mark=str(row.get("mark") or mark),
        note_detail=str(row.get("text") or ""),
    )


def commit_mark(
    plan: dict,
    week_number: int,
    choice: str,
    actuals: dict,
    marks: object,
    bases: dict,
) -> CommitOutcome:
    """One mark for this week. Later weeks are what adapt() returns."""
    try:
        updated = adapt_from_result(plan, week_number, choice, bases, actuals)
    except ValueError as exc:
        return CommitOutcome(error=str(exc))
    stored = _marks_copy(marks)
    stored[week_number] = choice
    return CommitOutcome(committed=True, plan=updated, marks=stored)


def apply_activity_marks(
    plan: dict,
    activities: object,
    actuals: dict,
    goal_seconds: float | None,
    bases: dict,
    marks: object,
) -> ActivityMarkOutcome:
    """Store a matched quality day's mark, then adapt later weeks.

    A day that already has a mark is left as stored. Nothing is sent to a model.
    """
    try:
        updated, new_actuals, week_marks = auto_adapt(
            plan,
            activities,
            actuals,
            goal_seconds,
            bases,
        )
    except ValueError as exc:
        return ActivityMarkOutcome(notice=str(exc))
    if not week_marks:
        return ActivityMarkOutcome()
    stored = _marks_copy(marks)
    stored.update(week_marks)
    return ActivityMarkOutcome(
        applied=True,
        plan=updated,
        marks=stored,
        actuals=new_actuals,
    )
