# progress.py — season weeks as done, current, or upcoming. Display only.

"""One row per week of a plan Start already stored.

The week that contains today is current, even when it already has a mark.
Any other week with a mark is done. A week after today with no mark is
upcoming. A past week with no mark is unmarked. A done or unmarked week
has no countdown. The current week counts from today to the goal. An
upcoming week counts from the Saturday that closes it, so the number
steps down by a week each row.

No model. No spend. No scores.
"""

from __future__ import annotations

from datetime import date, timedelta

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
) -> list[dict]:
    """Week number, phase, status, and days remaining, in season order.

    A done or unmarked week has no countdown. The current week counts from
    today. An upcoming week counts from the Saturday that closes it.
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
            }
        )
    return rows
