# no_watch.py — finish a workout without a watch. No invented times.

"""Done completes the session. A hard day also stores an existing mark.

Easy and long runs do not ask for behind, on target, or ahead.
A typed clock time is stored as one number. A blank time stays blank.
Last timed effort uses timed_mark(), which ignores a completion that
has no time. Pace formulas are not in this file.

No model. No spend. No scores.
"""

from __future__ import annotations

import re
from datetime import date

from ui.plan_store import MARKS
from ui.result import parse_result

# The words on the buttons, and the mark a quality result already stores.
CHOICES = (
    ("Behind", "not_hitting"),
    ("On target", "on_track"),
    ("Ahead", "smashing"),
)
OUTCOME_LABEL = {mark: label for label, mark in CHOICES}
_ALIAS = {
    "behind": "not_hitting",
    "not_hitting": "not_hitting",
    "not hitting": "not_hitting",
    "on target": "on_track",
    "on_target": "on_track",
    "on track": "on_track",
    "on_track": "on_track",
    "ahead": "smashing",
    "smashing": "smashing",
}
_REP_MARK = re.compile(r"×|(?<![A-Za-z])x", re.IGNORECASE)


def quality_day(session: object) -> bool:
    """Tuesday and Thursday work. Recovery and the long run stay closed.

    The same rule as the session page. An easy run on those days is not hard.
    """
    if not isinstance(session, dict):
        return False
    if str(session.get("day_of_week") or "") not in ("Tuesday", "Thursday"):
        return False
    template_id = session.get("template_id")
    if not isinstance(template_id, str) or not template_id or template_id.startswith("aer_"):
        return False
    return True


def outcome_mark(choice: object) -> str | None:
    """The stored mark for a button. Anything else is not a choice."""
    if not isinstance(choice, str):
        return None
    return _ALIAS.get(choice.strip().casefold().replace("_", " ").replace("-", " "))


def one_time(text: object) -> list[int | float] | None:
    """One clock time, in seconds. [] when blank. None when it is not one time.

    A rep list, a distance, and a pace are not stored as a time.
    """
    if text is None:
        return []
    if not isinstance(text, str):
        return None
    raw = text.strip()
    if not raw:
        return []
    if _REP_MARK.search(raw):
        return None
    parsed = parse_result(raw)
    if not isinstance(parsed, dict) or parsed.get("kind") != "pace":
        return None
    times = parsed.get("times")
    if not isinstance(times, list) or len(times) != 1:
        return None
    value = times[0]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number <= 0:
        return None
    if float(number).is_integer():
        return [int(number)]
    return [round(number, 2)]


def _template(session: object) -> str | None:
    if not isinstance(session, dict):
        return None
    template_id = session.get("template_id")
    if not isinstance(template_id, str):
        return None
    text = template_id.strip()
    if not text or len(text) > 80:
        return None
    return text


def finish_session(session: object, outcome: object, time_text: object) -> dict:
    """The completion row, or an error. A blank time is left empty.

    A hard day needs behind, on target, or ahead. That choice is the
    existing on_track, not_hitting, or smashing mark. Easy and long runs
    do not store a mark. Nothing here fills in a pace or a split.
    """
    template_id = _template(session)
    if template_id is None:
        return {"ok": False, "error": "That workout is not in this plan.", "row": None}
    hard = quality_day(session)
    mark = outcome_mark(outcome) if hard else None
    if hard and mark not in MARKS:
        return {
            "ok": False,
            "error": "Choose behind, on target, or ahead.",
            "row": None,
        }
    seconds = one_time(time_text)
    if seconds is None:
        return {
            "ok": False,
            "error": "Enter one time, like 1:12.4, or leave it blank.",
            "row": None,
        }
    text = ""
    if seconds and isinstance(time_text, str):
        text = time_text.strip()
    row: dict = {
        "template_id": template_id,
        "completed": True,
        "numbers": list(seconds),
        "text": text,
    }
    if mark is not None:
        row["mark"] = mark
    return {"ok": True, "error": "", "row": row}


def missed_session(session: object) -> dict | None:
    """Couldn't finish. No time, no mark, and not a completed workout."""
    template_id = _template(session)
    if template_id is None:
        return None
    return {
        "template_id": template_id,
        "missed": True,
        "numbers": [],
        "text": "",
    }


def timed_mark(row: object) -> str | None:
    """A quality mark that was stored with a time.

    Done without a time keeps the choice on the session and does not
    move last timed effort. A positive number is the typed clock time.
    """
    if not isinstance(row, dict):
        return None
    mark = row.get("mark")
    if mark not in MARKS:
        return None
    numbers = row.get("numbers")
    if not isinstance(numbers, list):
        return None
    for item in numbers:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            continue
        if float(item) > 0:
            return str(mark)
    return None


def session_completed(session: object, actuals: object) -> bool:
    """True when this day was finished. A miss is not finished.

    A logged result that already has a time counts, so the next workout
    can move past it. A different template on that date does not.
    """
    if not isinstance(session, dict) or not isinstance(actuals, dict):
        return False
    row = actuals.get(session.get("date"))
    if not isinstance(row, dict) or row.get("template_id") != session.get("template_id"):
        return False
    if row.get("missed") is True and row.get("completed") is not True:
        return False
    if row.get("completed") is True:
        return True
    numbers = row.get("numbers")
    if not isinstance(numbers, list):
        return False
    for item in numbers:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            continue
        if float(item) > 0:
            return True
    return False


def next_open_workout(sessions: object, today: date, actuals: object) -> dict | None:
    """The first session on or after today that is not already complete.

    The shape matches the home page's next workout. A finished day is
    skipped so the plan shows the next one.
    """
    if not isinstance(today, date):
        return None
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
        if day < today or session_completed(session, actuals):
            continue
        if chosen_day is not None and day >= chosen_day:
            continue
        chosen_day = day
        chosen = session
    if chosen is None or chosen_day is None:
        return None
    name = str(chosen.get("day_of_week") or "").strip()
    return {
        "day_of_week": name or "—",
        "date": chosen_day.isoformat(),
        "template_id": str(chosen.get("template_id") or "").strip(),
    }
