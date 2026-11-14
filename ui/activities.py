# activities.py — match stored activities by date, and load a local .env.

"""Attach an activity record to the planned day it landed on.

Strava is the only activity source. When it is not connected, pages use
NOT_CONNECTED_NOTICE and do not fetch runs. The earliest run on a planned
date fills that session. Any other activity is an extra session.

A matched day keeps that activity's WORK elapsed times, WORK distance, and
average heart rate. Warm-up and cool-down stay out of the WORK distance.
The activity distance is stored beside that and is not the volume.

No model. No spend. No scores. Engines are not used.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

from ui.last_session import (
    activity_distance,
    activity_heart_rate,
    work_distance,
    work_elapsed,
)

ROOT = Path(__file__).resolve().parent.parent

# Shown when Strava is not connected. The web card looks for "not configured".
NOT_CONNECTED_NOTICE = "Strava is not configured."

# Today and the 13 days before it. oldest and newest are both included.
WINDOW_DAYS = 14
# A full history asks from this day through today. Both ends are included.
HISTORY_START = date(1970, 1, 1)
_ID_LIMIT = 120
_NAME_LIMIT = 120
_START_LIMIT = 40


class PullError(Exception):
    """A readable activity pull failure. The message never includes the API key."""


def activity_window(today: date) -> tuple[str, str]:
    """Oldest and newest day, YYYY-MM-DD, covering the last 14 days."""
    if type(today) is not date:
        raise TypeError("today must be a date")
    oldest = today - timedelta(days=WINDOW_DAYS - 1)
    return oldest.isoformat(), today.isoformat()


def activity_history(today: date) -> tuple[str, str]:
    """Oldest and newest day, YYYY-MM-DD, covering every activity through today."""
    if type(today) is not date:
        raise TypeError("today must be a date")
    oldest = HISTORY_START if today >= HISTORY_START else today
    return oldest.isoformat(), today.isoformat()


def load_local_env(paths: list[Path] | None = None) -> None:
    """Load KEY=VALUE lines from .env. Existing environment values win.

    The values are never printed. A missing file is skipped. Pass paths to
    read those files instead of the working directory and the project root.
    """
    if paths is None:
        candidates = [Path.cwd() / ".env", ROOT / ".env"]
    else:
        candidates = list(paths)
    seen: set[Path] = set()
    for path in candidates:
        file = Path(path)
        try:
            resolved = file.resolve()
        except OSError:
            continue
        if resolved in seen or not file.is_file():
            seen.add(resolved)
            continue
        seen.add(resolved)
        _apply_env_file(file)


def match_activities(sessions: list, activities: list) -> list[dict]:
    """One planned date takes the earliest run. Every other activity is extra.

    A date with no run takes the earliest activity. A date with no planned
    session is extra. WORK times, WORK distance, and average heart rate are
    copied off the activity. The activity distance is stored on its own and
    is not used as the WORK distance.
    """
    planned: dict[str, str] = {}
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        day = session.get("date")
        template = session.get("template_id")
        if not isinstance(day, str) or day in planned:
            continue
        if not isinstance(template, str) or not template.strip():
            continue
        planned[day] = template.strip()
    grouped: dict[str, list[dict]] = {}
    for activity in activities or []:
        if not isinstance(activity, dict):
            continue
        if _id_text(activity.get("id")) is None or not activity_day(activity):
            continue
        grouped.setdefault(activity_day(activity), []).append(activity)
    rows = []
    for day, group in grouped.items():
        ordered = sorted(group, key=_oldest_key)
        chosen = _choose(ordered)
        template = planned.get(day)
        for activity in ordered:
            matched = template is not None and activity is chosen
            record = _record(
                activity,
                matched=matched,
                template_id=template if matched else None,
            )
            if record is not None:
                rows.append(record)
    rows.sort(key=lambda row: (row["date"], row.get("start") or "", row["id"]))
    return rows


def merge_activities(stored: object, pulled: list, oldest: str, newest: str) -> list[dict]:
    """Keep stored rows outside the window. Pulled rows replace the window."""
    kept: list[dict] = []
    for row in stored or []:
        if not isinstance(row, dict):
            continue
        day = row.get("date")
        if isinstance(day, str) and oldest <= day <= newest:
            continue
        kept.append(row)
    by_id: dict[str, dict] = {}
    for row in kept + list(pulled or []):
        if not isinstance(row, dict):
            continue
        ident = row.get("id")
        if isinstance(ident, str) and ident:
            by_id[ident] = row
    rows = list(by_id.values())
    rows.sort(key=lambda row: (str(row.get("date") or ""), str(row.get("start") or ""), str(row.get("id") or "")))
    return rows


def matched_on(activities: object, day: object) -> dict | None:
    """The activity matched to this planned date, if one was stored."""
    if not isinstance(day, str):
        return None
    for row in activities or []:
        if isinstance(row, dict) and row.get("matched") is True and row.get("date") == day:
            return row
    return None


def activity_by_id(activities: object, ident: object) -> dict | None:
    """The stored activity with this id."""
    if not isinstance(ident, str) or not ident.strip():
        return None
    text = ident.strip()
    for row in activities or []:
        if isinstance(row, dict) and row.get("id") == text:
            return row
    return None


def extras_between(activities: object, start: date | str, end: date | str) -> list[dict]:
    """Unmatched activities whose date falls inside the inclusive range."""
    oldest = start.isoformat() if isinstance(start, date) else str(start)
    newest = end.isoformat() if isinstance(end, date) else str(end)
    rows = []
    for row in activities or []:
        if not isinstance(row, dict) or row.get("matched") is not False:
            continue
        day = row.get("date")
        if isinstance(day, str) and oldest <= day <= newest:
            rows.append(row)
    return rows


def with_matched_distances(distances: object, activities: object) -> dict[str, float]:
    """File distances, then a matched day's WORK distance over that date.

    Days with no match keep the file distance. A matched day uses the activity.
    """
    found: dict[str, float] = {}
    if isinstance(distances, dict):
        for day, meters in distances.items():
            number = _meters_value(meters)
            if isinstance(day, str) and number is not None:
                found[day] = number
    for row in activities or []:
        if not isinstance(row, dict) or row.get("matched") is not True:
            continue
        day = row.get("date")
        number = _meters_value(row.get("work_m"))
        if isinstance(day, str) and number is not None:
            found[day] = number
    return found


def meters_text(value: object) -> str:
    """Whole meters for a label. An unusable distance is blank."""
    number = _meters_value(value)
    if number is None:
        return ""
    return f"{int(number + 0.5):,} m"


def weekday_name(day: object) -> str:
    """English weekday for a YYYY-MM-DD date. Anything else is blank."""
    if not isinstance(day, str):
        return ""
    try:
        when = date.fromisoformat(day)
    except ValueError:
        return ""
    return ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[when.weekday()]


def activity_day(activity: object) -> str:
    """The calendar date on start_date_local, or blank when it has none."""
    if not isinstance(activity, dict):
        return ""
    for key in ("start_date_local", "start_date", "date"):
        value = activity.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if len(text) < 10:
            continue
        found = text[:10]
        if found[4] != "-" or found[7] != "-":
            continue
        try:
            date.fromisoformat(found)
        except ValueError:
            continue
        return found
    return ""


def _apply_env_file(path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise OSError(f"Could not read .env: {path}") from exc
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if name and name not in os.environ:
            os.environ[name] = value


def _oldest_key(activity: dict) -> tuple:
    start = _start_text(activity.get("start_date_local"))
    return (start == "", start, _ident(activity))


def _ident(activity: dict) -> str:
    value = activity.get("id")
    if value is None:
        return ""
    return str(value)


def _choose(ordered: list[dict]) -> dict:
    """Earliest run. A day with no run uses the earliest activity."""
    for activity in ordered:
        if _is_run(activity):
            return activity
    return ordered[0]


def _is_run(activity: dict) -> bool:
    return str(activity.get("type") or "").strip().lower() == "run"


def _record(activity: dict, *, matched: bool, template_id: str | None) -> dict | None:
    day = activity_day(activity)
    ident = _id_text(activity.get("id"))
    if not day or ident is None:
        return None
    name = activity.get("name")
    if not isinstance(name, str):
        name = ""
    row = {
        "date": day,
        "id": ident,
        "matched": matched,
        "name": name.strip()[:_NAME_LIMIT],
    }
    start = _start_text(activity.get("start_date_local"))
    if start:
        row["start"] = start[:_START_LIMIT]
    if matched and isinstance(template_id, str) and template_id.strip():
        row["template_id"] = template_id.strip()[:80]
    heart = activity_heart_rate(activity)
    if heart is not None:
        row["heart_rate"] = _whole(heart)
    # Activity distance stays off the WORK total.
    total = activity_distance(activity)
    if total is not None and total > 0:
        row["distance"] = _whole(total)
    try:
        meters = work_distance(activity)
    except (TypeError, ValueError):
        meters = None
    if meters is not None:
        row["work_m"] = _whole(meters)
    try:
        times = work_elapsed(activity)
    except (TypeError, ValueError):
        times = []
    reps = [_whole(item) if item is not None else None for item in times[:32]]
    if any(item is not None for item in reps):
        row["reps"] = reps
    return row


def _id_text(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if not text or len(text) > _ID_LIMIT:
        return None
    if any(ord(char) < 32 for char in text):
        return None
    return text


def _start_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text or any(ord(char) < 32 for char in text):
        return ""
    return text


def _meters_value(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number < 0 or number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _whole(number: float) -> int | float:
    if float(number).is_integer():
        return int(number)
    return number
