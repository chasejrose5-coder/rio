# progress.py — season weeks as done, current, or upcoming. Display only.

"""One row per week of a plan Start already stored.

The week that contains today is current, even when it already has a mark.
Any other week with a mark is done. A week after today with no mark is
upcoming. A past week with no mark is unmarked. A done or unmarked week
has no countdown. The current week counts from today to the goal. An
upcoming week counts from the Saturday that closes it, so the number
steps down by a week each row.

Each week shows a distance. A day with a loaded Intervals distance uses
that distance. Any other day uses the work distance written in its
template id. A week with no loaded file uses the template total.

No model. No spend. No scores.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

from engines.season import work_meters

# The three marks adapt() already stores. Anything else is not a mark.
MARKS = ("on_track", "not_hitting", "smashing")


def week_sunday(start: date, week_number: int) -> date:
    """Sunday that opens this plan week. Week 1 contains the start date."""
    anchor = start - timedelta(days=(start.weekday() + 1) % 7)
    return anchor + timedelta(days=(week_number - 1) * 7)


def days_remaining(goal: date, today: date) -> int:
    """Days from today until the goal date. A reached goal stays at zero."""
    remaining = (goal - today).days
    if remaining < 0:
        return 0
    return remaining


def days_label(days: int | None) -> str:
    """The countdown as written on a row. A blank countdown is an em dash."""
    if days is None:
        return "—"
    noun = "day" if days == 1 else "days"
    return f"{days} {noun} to goal"


def _row_days(
    status: str | None,
    *,
    start: date,
    week_number: int,
    goal: date,
    today: date,
) -> int | None:
    """Days left on this row. Done and unmarked weeks have none.

    The current week counts from today. An upcoming week counts from the
    Saturday that closes it, which is later each week, so the countdown
    falls by seven days a row until the goal.
    """
    if status == "current":
        return days_remaining(goal, today)
    if status == "upcoming":
        saturday = week_sunday(start, week_number) + timedelta(days=6)
        return days_remaining(goal, saturday)
    return None


def week_status(*, start: date, week_number: int, today: date, marked: bool) -> str | None:
    """done, current, upcoming, or None when a past week has no mark.

    Current wins when the week contains today, so the row you are in stays
    current after a mark. A mark on any other week is done, including a
    week that has not started. An unmarked week that starts after today
    is upcoming.
    """
    sunday = week_sunday(start, week_number)
    saturday = sunday + timedelta(days=6)
    if sunday <= today <= saturday:
        return "current"
    if marked:
        return "done"
    if today < sunday:
        return "upcoming"
    return None


def week_volume(sessions: list, distances: dict | None = None) -> str:
    """This week's distance.

    A day with a loaded Intervals distance uses that distance. Any other
    day uses its template meters. A week with no loaded file uses the
    template total.
    """
    loaded = _loaded_meters(sessions, distances)
    if not loaded:
        return _meter_text(_template_meters(sessions))
    return _meter_text(_mixed_meters(sessions, loaded))


def _loaded_meters(sessions: list, distances: dict | None) -> dict[str, float]:
    """Dates in this week that have a loaded Intervals distance."""
    if not isinstance(distances, dict) or not sessions:
        return {}
    found: dict[str, float] = {}
    for session in sessions:
        if not isinstance(session, dict):
            continue
        day = session.get("date")
        if not isinstance(day, str) or day not in distances:
            continue
        meters = _distance_number(distances.get(day))
        if meters is None:
            continue
        found[day] = meters
    return found


def _mixed_meters(sessions: list, loaded: dict[str, float]) -> float | None:
    """Loaded distance where a day has one, otherwise that day's template meters."""
    if not sessions:
        return None
    total = 0.0
    for session in sessions:
        if not isinstance(session, dict):
            return None
        day = session.get("date")
        if isinstance(day, str) and day in loaded:
            total += loaded[day]
            continue
        meters = _session_template(session)
        if meters is None:
            return None
        total += meters
    return total


def _session_template(session: object) -> int | None:
    """Work distance written in this session's template id."""
    if not isinstance(session, dict):
        return None
    template_id = session.get("template_id")
    if not isinstance(template_id, str) or not template_id:
        return None
    try:
        return work_meters(template_id)
    except ValueError:
        return None


def _template_meters(sessions: list) -> int | None:
    """Work distance written in the template ids. One unreadable id clears the week."""
    if not sessions:
        return None
    total = 0
    for session in sessions:
        meters = _session_template(session)
        if meters is None:
            return None
        total += meters
    return total


def _distance_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _meter_text(meters: int | float | None) -> str:
    if isinstance(meters, bool) or not isinstance(meters, (int, float)):
        return "—"
    if isinstance(meters, float):
        if not math.isfinite(meters) or meters < 0:
            return "—"
        meters = int(meters + 0.5)
    if meters < 0:
        return "—"
    return f"{meters:,} m"


def phase_label(sessions: list) -> str:
    """The phase digits already stored on the week's sessions."""
    found: list[str] = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        codes = session.get("reason_codes") or []
        if not isinstance(codes, list):
            continue
        for code in codes:
            text = str(code)
            if len(text) == 7 and text.startswith("phase_") and text[6] in "12345678":
                number = text[6]
                if number not in found:
                    found.append(number)
    if len(found) == 1:
        return found[0]
    if not found:
        return "—"
    return ", ".join(found)


def _marked(marks: dict, week: int) -> bool:
    return marks.get(week) in MARKS


def progress_weeks(
    *,
    start: date,
    goal: date,
    length: int,
    sessions: list,
    marks: dict | None,
    today: date,
    distances: dict | None = None,
) -> list[dict]:
    """Week number, phase, status, days remaining, and volume, in season order.

    A done or unmarked week has no countdown. The current week counts from
    today. An upcoming week counts from the Saturday that closes it.
    A day with a loaded Intervals distance uses that distance. Any other
    day uses its template meters. A week with no loaded file uses the
    template total.
    """
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        return []
    grouped: dict[int, list] = {}
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        number = session.get("week_number")
        if isinstance(number, bool) or not isinstance(number, int):
            continue
        grouped.setdefault(number, []).append(session)
    stored = marks if isinstance(marks, dict) else {}
    rows = []
    for number in range(1, length + 1):
        status = week_status(
            start=start,
            week_number=number,
            today=today,
            marked=_marked(stored, number),
        )
        rows.append(
            {
                "week": number,
                "phase": phase_label(grouped.get(number, [])),
                "status": status,
                "days_remaining": _row_days(
                    status,
                    start=start,
                    week_number=number,
                    goal=goal,
                    today=today,
                ),
                "volume": week_volume(grouped.get(number, []), distances),
            }
        )
    return rows
