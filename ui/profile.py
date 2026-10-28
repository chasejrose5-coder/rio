# profile.py — the four Start values. A goal time can stay in this browser.

"""Profile reads the plan Start already stored.

The current 800 time, the start date, the goal 800 time, and the goal date
are shown as stored. A saved goal time replaces the displayed goal on this
browser only. Nothing here builds a season.

No model. No spend.
"""

from __future__ import annotations

import json
import re

# Same shape Start already accepts: m:ss or m:ss.s. A zero time is not a time.
_TIME = re.compile(r"^(\d+):(\d{2})(\.\d+)?$")
_PREFIX = "rio.profile.v1"


def profile_fields(
    current_time: object,
    start_date: object,
    goal_time: object,
    goal_date: object,
) -> list[tuple[str, str]]:
    """The four stored values, in Start order."""
    return [
        ("Current 800 time", _text(current_time)),
        ("Start date", _text(start_date)),
        ("Goal 800 time", _text(goal_time)),
        ("Goal date", _text(goal_date)),
    ]


def shown_goal(start_goal: object, saved: object) -> str:
    """The saved goal when this browser has one. Otherwise the Start value."""
    text = clean_goal(saved)
    if text is not None:
        return text
    if isinstance(start_goal, str) and start_goal.strip():
        return start_goal.strip()
    return "—"


def clean_goal(value: object) -> str | None:
    """An 800 time, or None. Blank and zero are not times."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    match = _TIME.fullmatch(text)
    if match is None:
        return None
    seconds = int(match.group(1)) * 60 + int(match.group(2))
    if match.group(3):
        seconds += float(match.group(3))
    if seconds <= 0:
        return None
    return text


def profile_key(inputs: tuple[str, str, str, str]) -> str:
    """One browser key for this plan. The saved goal is not part of the key."""
    return _PREFIX + "\n" + "\n".join(inputs)


def dump_goal(goal_time: str) -> str:
    """The goal time only. Anything else stays off this browser's record."""
    text = clean_goal(goal_time)
    if text is None:
        raise ValueError("goal_time is not an 800 time")
    return json.dumps({"goal_time": text}, separators=(",", ":"), sort_keys=True)


def load_goal(raw: object) -> str | None:
    """The saved goal time, or None when this browser has none."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return clean_goal(parsed.get("goal_time"))


def _text(value: object) -> str:
    if not isinstance(value, str):
        return "—"
    text = value.strip()
    return text or "—"
