# dashboard.py — the next workout and this week, from a plan Start already stored.

"""Display fields for the home page. The plan is the one Start stored.

The next workout is the first session on or after today. The phase and the
one-line focus belong to the week that contains today. The last mark is the
latest week mark, when one was stored. Days until the goal count from today.

The focus line is fixed words for reason codes and primary templates already
on that week. No model. No spend. No scores.
"""

from __future__ import annotations

from datetime import date

from ui.progress import MARKS, days_label, days_remaining, phase_label, week_status

# Primary template families, in the order a week is read. Display copy only.
_FOCUS_PREFIX = (
    ("se_", "Speed endurance"),
    ("ap_", "Aerobic power"),
    ("an_", "Anaerobic capacity"),
    ("thr_", "Threshold"),
    ("rr_", "Race pace"),
    ("mv_", "Max velocity"),
    ("spd_", "Speed"),
    ("aer_", "Easy running"),
)


def current_week(*, start: date, length: int, today: date) -> int | None:
    """The plan week that contains today. None when today is outside the season."""
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        return None
    for number in range(1, length + 1):
        status = week_status(
            start=start,
            week_number=number,
            today=today,
            marked=False,
        )
        if status == "current":
            return number
    return None


def next_workout(sessions: list, today: date) -> dict | None:
    """The first session on or after today. A past session is not next.

    Dates are unique in a stored plan. The row keeps the day, the date, and
    the template id. The page turns that id into the plain description.
    """
    chosen = None
    chosen_day = None
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        text = session.get("date")
        if not isinstance(text, str):
            continue
        try:
            day = date.fromisoformat(text)
        except ValueError:
            continue
        if day < today:
            continue
        if chosen_day is not None and day >= chosen_day:
            continue
        chosen_day = day
        chosen = session
    if chosen is None or chosen_day is None:
        return None
    day_name = str(chosen.get("day_of_week") or "").strip()
    return {
        "day_of_week": day_name or "—",
        "date": chosen_day.isoformat(),
        "template_id": str(chosen.get("template_id") or "").strip(),
    }


def last_mark(marks: dict | None) -> dict | None:
    """The latest stored week mark. None when no week has one.

    Latest is the highest week number. A value outside the three marks is
    ignored.
    """
    if not isinstance(marks, dict):
        return None
    found = None
    for week, mark in marks.items():
        if isinstance(week, bool) or not isinstance(week, int) or week < 1:
            continue
        if mark not in MARKS:
            continue
        if found is None or week > found["week"]:
            found = {"week": week, "mark": mark}
    return found


def week_focus(sessions: list) -> str:
    """One line for this week, from codes and primary templates already stored.

    An easy week says so. Otherwise the line names the primary work in the
    order the days fall. A taper with no primary work says it stays fresh.
    """
    rows = [session for session in sessions or [] if isinstance(session, dict)]
    codes: list[str] = []
    for session in rows:
        found = session.get("reason_codes") or []
        if not isinstance(found, list):
            continue
        for code in found:
            text = str(code)
            if text not in codes:
                codes.append(text)
    if "extra_easy_week" in codes:
        return "Easy week"
    labels: list[str] = []
    ordered = sorted(rows, key=lambda item: str(item.get("date") or ""))
    for session in ordered:
        found = session.get("reason_codes") or []
        if not isinstance(found, list) or "phase_primary" not in found:
            continue
        label = _focus_label(session.get("template_id"))
        if label and label not in labels:
            labels.append(label)
    if labels:
        return _join_focus(labels)
    if "phase_8_freshness" in codes:
        return "The taper stays fresh"
    return "—"


def dashboard_view(
    *,
    start: date,
    goal: date,
    length: int,
    sessions: list,
    marks: dict | None,
    today: date,
) -> dict:
    """Next workout, days to the goal, phase, last mark, and this week's focus.

    Phase and focus are blank when today falls outside the season. Days stop
    at zero once the goal date has passed.
    """
    phase = "—"
    focus = "—"
    week = current_week(start=start, length=length, today=today)
    if week is not None:
        rows = [
            session
            for session in sessions or []
            if isinstance(session, dict) and session.get("week_number") == week
        ]
        phase = phase_label(rows)
        focus = week_focus(rows)
    remaining = days_remaining(goal, today)
    return {
        "next": next_workout(sessions, today),
        "days_remaining": remaining,
        "days_label": days_label(remaining),
        "phase": phase,
        "mark": last_mark(marks),
        "focus": focus,
    }


def _focus_label(template_id: object) -> str:
    text = str(template_id or "").strip()
    for prefix, label in _FOCUS_PREFIX:
        if text.startswith(prefix):
            return label
    return ""


def _join_focus(labels: list[str]) -> str:
    """One sentence. The first name stays capitalized. The rest continue it."""
    words = [labels[0]]
    for label in labels[1:]:
        words.append(label[:1].lower() + label[1:] if label else label)
    if len(words) == 1:
        return words[0]
    if len(words) == 2:
        return f"{words[0]} and {words[1]}"
    return ", ".join(words[:-1]) + f", and {words[-1]}"
