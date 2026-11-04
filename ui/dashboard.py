# dashboard.py — the next workout and this week, from a plan Start already stored.

"""Display fields for the home page. The plan is the one Start stored.

The next workout is the first session on or after today. Distance, pace,
rest, and reps for that session are read from the frozen id and the plain
description already written for it. The phase and the one-line focus belong
to the week that contains today. The last mark is the latest week mark, when
one was stored. Days until the goal count from today.

The focus line is fixed words for reason codes and primary templates already
on that week. No model. No spend. No scores.
"""

from __future__ import annotations

import re
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


# Frozen ids: se_400_r90_x6, aer_10000_r0_x1, thr_up_800to1600_r60_x3.
_ID_FACTS = re.compile(
    r"(?:^|_)(?:py_|up_)?(\d+)(?:to(\d+))?_r(\d+)_x(\d+)$"
)

# Pace words already written on the card. First match wins. Display only.
_PACE = (
    ("800 m race", "Race"),
    ("at or faster than goal 800", "Goal 800 or faster"),
    ("near goal 800", "Near goal 800"),
    ("at goal 800", "Goal 800"),
    ("clearly slower than goal 800", "Slower than goal 800"),
    ("slower than goal 800", "Slower than goal 800"),
    ("comfortably hard", "Comfortably hard"),
    ("not goal 800", "Not 800 pace"),
    ("not 800 pace", "Not 800 pace"),
    ("zone 2", "Easy"),
    ("talkable", "Easy"),
    ("very easy", "Easy"),
    ("easy", "Easy"),
    ("strong", "Strong"),
    ("fast", "Fast"),
    ("hard", "Hard"),
)


MARK_LABEL = {
    "on_track": "On track",
    "not_hitting": "Not hitting",
    "smashing": "Smashing",
}


def mark_label(mark: object) -> str:
    """The words for a stored mark. The stored value stays the raw code."""
    text = str(mark or "").strip()
    if not text:
        return "—"
    return MARK_LABEL.get(text, text.replace("_", " "))


def plain_marks(text: object) -> str:
    """Replace raw mark codes in a sentence that is about to be shown."""
    shown = str(text or "")
    for raw, label in MARK_LABEL.items():
        shown = shown.replace(raw, label)
    return shown


def session_facts(template_id: object, description: object = "") -> dict:
    """Distance, pace, rest, and reps for the home track.

    Distance, rest, and reps come from the frozen id. Pace comes from the
    plain description already written for that id. An id that does not
    name them stays blank. No new plan.
    """
    blank = {"distance": "—", "pace": "—", "rest": "—", "reps": "—"}
    text = str(template_id or "").strip()
    found = _ID_FACTS.search(text)
    if found is None:
        return blank
    start = int(found.group(1))
    end = found.group(2)
    rest = int(found.group(3))
    reps = int(found.group(4))
    if start <= 0 or rest < 0 or reps <= 0:
        return blank
    if end is None:
        distance = f"{start} m"
    else:
        finish = int(end)
        if finish <= start:
            return blank
        distance = f"{start}–{finish} m"
    return {
        "distance": distance,
        "pace": _pace_label(description),
        "rest": _rest_text(rest),
        "reps": str(reps),
    }


def _pace_label(description: object) -> str:
    text = str(description or "").strip().lower()
    if not text:
        return "—"
    for needle, label in _PACE:
        if needle in text:
            return label
    return "—"


def _rest_text(seconds: int) -> str:
    if seconds <= 0:
        return "—"
    if seconds >= 120 and seconds % 60 == 0:
        return f"{seconds // 60} min"
    return f"{seconds} s"


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
