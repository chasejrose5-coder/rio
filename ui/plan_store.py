# plan_store.py — the four inputs in the URL. The account keeps marks and actuals.

"""Share a plan by its four inputs. Marks, actuals, and activity matches are one record.

The URL carries current_time, start_date, goal_time, and goal_date. The
record is keyed by those same four strings. This file only shapes that
record. The app stores it on the signed-in account. A pulled activity is
stored with that record, so a reload keeps the match.

No file. No model. No spend. No scores.
An actual may keep the Intervals filename or activity id that filled it.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date

# The three marks adapt() already stores. Anything else is not a mark.
MARKS = ("on_track", "not_hitting", "smashing")
INPUTS = ("current_time", "start_date", "goal_time", "goal_date")

# The key is the identity. Activities are optional, so an older record still
# opens. Bump the prefix only when marks or actuals can no longer be read.
_PREFIX = "rio.plan.v1"
_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FIELD_LIMIT = 40
_TEXT_LIMIT = 400
_ID_LIMIT = 80
_LIST_LIMIT = 32
# Activity id or filename stored with a result. Longer than a template id.
_REF_LIMIT = 120
_NAME_LIMIT = 120
_ACTIVITY_LIMIT = 80


def plan_inputs(params: object) -> tuple[str, str, str, str] | None:
    """The four inputs, or None when any one of them is missing or unusable."""
    if not hasattr(params, "get"):
        return None
    found = []
    for name in INPUTS:
        text = _text(params.get(name))
        if text is None:
            return None
        found.append(text)
    start = _day(found[1])
    goal_day = _day(found[3])
    if start is None or goal_day is None:
        return None
    return (found[0], start, found[2], goal_day)


def inputs_ok(value: object) -> bool:
    """True when this is the tuple plan_inputs() would return."""
    if not isinstance(value, tuple) or len(value) != 4:
        return False
    if not all(isinstance(item, str) for item in value):
        return False
    return plan_inputs(dict(zip(INPUTS, value))) == value


def query_values(inputs: tuple[str, str, str, str]) -> dict[str, str]:
    """The four URL fields. A session date is not one of them."""
    return {
        "current_time": inputs[0],
        "start_date": inputs[1],
        "goal_time": inputs[2],
        "goal_date": inputs[3],
    }


def storage_key(inputs: tuple[str, str, str, str]) -> str:
    """One browser key for this plan. A different input is a different key."""
    return _PREFIX + "\n" + "\n".join(inputs)


def dump_record(marks: object, actuals: object, activities: object = None) -> str:
    """Marks, actuals, and pulled activities, in a stable order.

    Unknown fields are left out. An empty activity list is left out so a
    record with only marks and actuals keeps its shape.
    """
    payload = {"actuals": _clean_actuals(actuals), "marks": _clean_marks(marks)}
    cleaned = _clean_activities(activities)
    if cleaned:
        payload["activities"] = cleaned
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def load_record(raw: object) -> tuple[dict, dict, list]:
    """Marks keyed by week number, actuals keyed by date, and pulled activities.

    Junk is empty. A record written before activities existed loads an empty list.
    """
    if not isinstance(raw, str) or not raw.strip():
        return {}, {}, []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}, {}, []
    if not isinstance(parsed, dict):
        return {}, {}, []
    marks = {}
    for key, value in _clean_marks(parsed.get("marks")).items():
        marks[int(key)] = value
    return marks, _clean_actuals(parsed.get("actuals")), _clean_activities(parsed.get("activities"))


def _text(value: object) -> str | None:
    if isinstance(value, (list, tuple)):
        value = value[-1] if value else None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > _FIELD_LIMIT:
        return None
    return text


def _day(value: str) -> str | None:
    if _DAY.fullmatch(value) is None:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _week(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        week = value
    elif isinstance(value, str) and value.strip().isdigit():
        week = int(value.strip())
    else:
        return None
    if week < 1 or week > 9999:
        return None
    return week


def _number(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        if value.is_integer():
            return int(value)
    return value


def _clean_marks(marks: object) -> dict[str, str]:
    if not isinstance(marks, dict):
        return {}
    cleaned = {}
    for key, value in marks.items():
        week = _week(key)
        if week is None or value not in MARKS:
            continue
        cleaned[str(week)] = value
    return cleaned


def _clean_actuals(actuals: object) -> dict[str, dict]:
    if not isinstance(actuals, dict):
        return {}
    cleaned = {}
    for key, value in actuals.items():
        day = _text(key)
        day = _day(day) if day is not None else None
        row = _clean_actual(value)
        if day is None or row is None:
            continue
        cleaned[day] = row
    return cleaned


def _clean_actual(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    template_id = value.get("template_id")
    if not isinstance(template_id, str):
        return None
    template_id = template_id.strip()
    if not template_id or len(template_id) > _ID_LIMIT:
        return None
    mark = value.get("mark")
    if mark not in MARKS:
        return None
    numbers = _number_list(value.get("numbers"))
    if not numbers:
        return None
    text = value.get("text")
    if not isinstance(text, str):
        text = ""
    row = {
        "mark": mark,
        "numbers": numbers,
        "template_id": template_id,
        "text": text.strip()[:_TEXT_LIMIT],
    }
    slots = _slots(value.get("slots"))
    if slots is not None:
        row["slots"] = slots
    intervals = _intervals_ref(value.get("intervals"))
    if intervals is not None:
        row["intervals"] = intervals
    return row


def _number_list(value: object) -> list[int | float] | None:
    if not isinstance(value, list) or len(value) > _LIST_LIMIT:
        return None
    numbers = []
    for item in value:
        number = _number(item)
        if number is None:
            return None
        numbers.append(number)
    return numbers


def _intervals_ref(value: object) -> str | None:
    """The activity id or filename. Anything else stays off the record."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if not text or len(text) > _REF_LIMIT:
        return None
    if any(ord(char) < 32 for char in text):
        return None
    return text


def _slots(value: object) -> list | None:
    if not isinstance(value, list) or len(value) > _LIST_LIMIT:
        return None
    slots = []
    for item in value:
        if item is None:
            slots.append(None)
            continue
        number = _number(item)
        if number is None:
            return None
        slots.append(number)
    return slots


def _clean_activities(activities: object) -> list[dict]:
    """Pulled activities, one per id. Scores and unknown fields stay out."""
    if not isinstance(activities, list):
        return []
    found: dict[str, dict] = {}
    for item in activities[:200]:
        row = _clean_activity(item)
        if row is None:
            continue
        found[row["id"]] = row
    rows = list(found.values())
    rows.sort(key=lambda row: (row["date"], row.get("start") or "", row["id"]))
    return rows[:_ACTIVITY_LIMIT]


def _clean_activity(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    ident = _intervals_ref(value.get("id"))
    day_text = _text(value.get("date"))
    day = _day(day_text) if day_text is not None else None
    matched = value.get("matched")
    if ident is None or day is None or matched not in (True, False):
        return None
    name = value.get("name")
    if not isinstance(name, str):
        name = ""
    row = {
        "date": day,
        "id": ident,
        "matched": matched,
        "name": name.strip()[:_NAME_LIMIT],
    }
    start = _plain_token(value.get("start"), _FIELD_LIMIT)
    if start is not None:
        row["start"] = start
    if matched:
        template = value.get("template_id")
        if isinstance(template, str):
            template = template.strip()
            if template and len(template) <= _ID_LIMIT:
                row["template_id"] = template
    heart = _positive(value.get("heart_rate"))
    if heart is not None:
        row["heart_rate"] = heart
    distance = _meters(value.get("distance"))
    if distance is not None and distance > 0:
        row["distance"] = distance
    meters = _meters(value.get("work_m"))
    if meters is not None:
        row["work_m"] = meters
    reps = _rep_list(value.get("reps"))
    if reps is not None:
        row["reps"] = reps
    return row


def _plain_token(value: object, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > limit:
        return None
    if any(ord(char) < 32 for char in text):
        return None
    return text


def _positive(value: object) -> int | float | None:
    number = _number(value)
    if number is None or number <= 0:
        return None
    return number


def _meters(value: object) -> int | float | None:
    number = _number(value)
    if number is None or number < 0:
        return None
    return number


def _rep_list(value: object) -> list | None:
    """WORK times, with a gap left empty. A list with no time is left out."""
    if not isinstance(value, list) or len(value) > _LIST_LIMIT:
        return None
    reps = []
    for item in value:
        if item is None:
            reps.append(None)
            continue
        number = _number(item)
        if number is None:
            return None
        if number <= 0:
            reps.append(None)
            continue
        reps.append(number)
    if not any(item is not None for item in reps):
        return None
    return reps
