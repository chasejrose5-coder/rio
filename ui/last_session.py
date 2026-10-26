# last_session.py — open one local Intervals JSON file. Display input only.

"""Read one JSON file from tests/fixtures/intervals.

to_normalize_input builds the lap payload. The page then runs normalize,
classify, and explain on that payload and shows the same fields as a fixture.
quality_fill reads the same file for a quality session: WORK elapsed times,
and the activity id or the filename. Activity distance and average heart
rate are read from the same local file for display. Volume distance is
the sum of WORK interval distances in that file. Warm-up and cool-down
stay out. This file does not call the network.

No scores. Prose spend stays capped at $25 where explain already records it.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date
from pathlib import Path

from adapters.intervals_icu import to_normalize_input

ROOT = Path(__file__).resolve().parent.parent
INTERVALS_DIR = ROOT / "tests" / "fixtures" / "intervals"

_DAY = re.compile(r"^(\d{4}-\d{2}-\d{2})")
# Underscore is a word character, so a filename such as synthetic_se still counts.
_SYNTHETIC_WORD = re.compile(r"(?<![A-Za-z])synthetic(?![A-Za-z])", re.IGNORECASE)
_TEXT_KEYS = ("note", "name", "description", "source")
# The browser record keeps an activity id or a filename at this length.
_SOURCE_LIMIT = 120


class IntervalsFileError(ValueError):
    """A local Intervals JSON file could not be opened. No network."""


def intervals_json_paths(directory: Path | None = None) -> list[Path]:
    """JSON files in tests/fixtures/intervals, by name. Missing dir is empty."""
    folder = INTERVALS_DIR if directory is None else Path(directory)
    if not folder.is_dir():
        return []
    return sorted(
        (path for path in folder.glob("*.json") if path.is_file()),
        key=lambda path: path.name,
    )


def open_intervals(path: Path) -> tuple[dict, str | None]:
    """Return the normalize payload and the banner. The read stays on disk.

    The payload is to_normalize_input plus the activity date when it has one.
    A file that says it is synthetic gets SYNTHETIC / FIXTURE.
    """
    file = Path(path)
    activity = _load_activity(file)
    try:
        payload = _session_payload(activity)
    except (TypeError, ValueError) as exc:
        message = str(exc).strip() or f"{file.name} could not be read."
        raise IntervalsFileError(message) from exc
    banner = "SYNTHETIC / FIXTURE" if _says_synthetic(file, activity) else None
    return payload, banner


def quality_fill(path: Path) -> tuple[list[float | None], str]:
    """WORK elapsed times, and the activity id or the filename.

    The file is read from disk. Nothing is requested from Intervals.icu.
    """
    file = Path(path)
    activity = _load_activity(file)
    try:
        times = work_elapsed(activity)
    except (TypeError, ValueError) as exc:
        message = str(exc).strip() or f"{file.name} could not be read."
        raise IntervalsFileError(message) from exc
    return times, intervals_source(file, activity)


def work_elapsed(activity: dict) -> list[float | None]:
    """Elapsed seconds for each WORK interval, in order.

    Warm-up, recovery, and cool-down stay out. A WORK interval with no
    elapsed time is an empty slot, so the next rep stays in its own box.
    moving_time is not a stand-in for elapsed time.
    """
    payload = to_normalize_input(activity)
    times: list[float | None] = []
    for step in payload["intervals"]:
        if not isinstance(step, dict) or step.get("role") != "work":
            continue
        times.append(_elapsed(step.get("seconds")))
    return times


def intervals_source(path: Path, activity: dict) -> str:
    """Activity id when the file has one. Otherwise the filename."""
    found = _source_text(activity.get("id")) if isinstance(activity, dict) else None
    if found:
        return found
    name = _source_text(Path(path).name)
    if name:
        return name
    trimmed = Path(path).name.strip()[:_SOURCE_LIMIT]
    return trimmed or "intervals"


def fit_slots(times: object, count: int) -> list[float | None]:
    """One value per existing box. Extra WORK intervals are left out."""
    size = count if isinstance(count, int) and not isinstance(count, bool) and count > 0 else 1
    slots: list[float | None] = [None] * size
    if not isinstance(times, list):
        return slots
    for index, value in enumerate(times[:size]):
        slots[index] = _elapsed(value)
    return slots


def activity_distance(activity: object) -> float | None:
    """Activity distance in meters. A missing distance stays unset."""
    if not isinstance(activity, dict) or "distance" not in activity:
        return None
    return _meters(activity.get("distance"))


def work_distance(activity: object) -> float | None:
    """Meters of WORK intervals. Warm-up, recovery, and cool-down stay out.

    The activity distance is not used. A file with no WORK distance is unset.
    """
    if not isinstance(activity, dict):
        return None
    try:
        payload = to_normalize_input(activity)
    except (TypeError, ValueError):
        return None
    intervals = payload.get("intervals")
    if not isinstance(intervals, list):
        return None
    total = 0.0
    found = False
    for step in intervals:
        if not isinstance(step, dict) or step.get("role") != "work":
            continue
        meters = _meters(step.get("distance_m"))
        if meters is None:
            continue
        total += meters
        found = True
    if not found:
        return None
    return total


def activity_heart_rate(activity: object) -> float | None:
    """average_heartrate on the activity. Lap heart rates stay on the laps."""
    if not isinstance(activity, dict) or "average_heartrate" not in activity:
        return None
    bpm = _finite(activity.get("average_heartrate"))
    if bpm is None or bpm <= 0:
        return None
    return bpm


def heart_rate_text(activity: object) -> str | None:
    """Avg HR as shown. None when the activity JSON has no average heart rate."""
    bpm = activity_heart_rate(activity)
    if bpm is None:
        return None
    shown = str(int(bpm)) if bpm.is_integer() else f"{bpm:.1f}"
    return f"{shown} bpm"


def activity_by_ref(ref: object, directory: Path | None = None) -> dict | None:
    """The local activity named by an id or a filename. No network."""
    if isinstance(ref, bool):
        return None
    if isinstance(ref, int):
        text = str(ref)
    elif isinstance(ref, str):
        text = ref.strip()
    else:
        return None
    if not text:
        return None
    return _activity_index(directory).get(text)


def loaded_distances(
    sessions: list,
    actuals: dict | None,
    directory: Path | None = None,
) -> dict[str, float]:
    """Session date to WORK interval distance for a stored Intervals file.

    The ref has to belong to that day's template. Warm-up and cool-down
    stay out. A missing file or a file with no WORK distance is left out.
    The read stays on disk. Template meters are not used.
    """
    if not isinstance(actuals, dict):
        return {}
    templates: dict[str, str] = {}
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        day = session.get("date")
        template_id = session.get("template_id")
        if isinstance(day, str) and isinstance(template_id, str) and template_id:
            templates[day] = template_id
    index = _activity_index(directory)
    found: dict[str, float] = {}
    for day, row in actuals.items():
        if not isinstance(day, str) or not isinstance(row, dict):
            continue
        if templates.get(day) != row.get("template_id"):
            continue
        ref = row.get("intervals")
        if isinstance(ref, bool):
            continue
        if isinstance(ref, int):
            text = str(ref)
        elif isinstance(ref, str):
            text = ref.strip()
        else:
            continue
        if not text:
            continue
        meters = work_distance(index.get(text))
        if meters is None:
            continue
        found[day] = meters
    return found


def file_just_opened(previous: object, source: object) -> bool:
    """True on the run a file is chosen. The same file leaves an edit in place."""
    if not isinstance(source, str) or source.strip() == "":
        return False
    return source != previous


def _load_activity(path: Path) -> dict:
    name = path.name
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise IntervalsFileError(f"Could not read {name}.") from exc
    try:
        activity = json.loads(text)
    except json.JSONDecodeError as exc:
        raise IntervalsFileError(f"{name} is not JSON.") from exc
    if not isinstance(activity, dict):
        raise IntervalsFileError(f"{name} must be a JSON object.")
    return activity


def _session_payload(activity: dict) -> dict:
    payload = to_normalize_input(activity)
    day = _activity_day(activity)
    if day:
        payload["date"] = day
    return payload


def _activity_day(activity: dict) -> str:
    for key in ("start_date_local", "start_date", "date", "started_at"):
        value = activity.get(key)
        if value is None:
            continue
        text = str(value).strip()
        found = _DAY.match(text)
        if found is None:
            continue
        year, month, day = (int(part) for part in found.group(1).split("-"))
        try:
            date(year, month, day)
        except ValueError:
            continue
        return found.group(1)
    return ""


def _activity_index(directory: Path | None) -> dict[str, dict]:
    """Filename and activity id to the activity object. Unreadable files are skipped."""
    found: dict[str, dict] = {}
    for path in intervals_json_paths(directory):
        try:
            activity = _load_activity(path)
        except IntervalsFileError:
            continue
        _keep(found, path.name, activity)
        _keep(found, intervals_source(path, activity), activity)
    return found


def _keep(found: dict[str, dict], key: object, activity: dict) -> None:
    if not isinstance(key, str):
        return
    text = key.strip()
    if not text or text in found:
        return
    found[text] = activity


def _meters(value: object) -> float | None:
    number = _finite(value)
    if number is None or number < 0:
        return None
    return number


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _elapsed(value: object) -> float | None:
    number = _finite(value)
    if number is None or number <= 0:
        return None
    return round(number, 2)


def _source_text(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if not text or len(text) > _SOURCE_LIMIT:
        return None
    if any(ord(char) < 32 for char in text):
        return None
    return text


def _says_synthetic(path: Path, activity: dict) -> bool:
    """True when the file name or the activity text says synthetic."""
    if _SYNTHETIC_WORD.search(path.stem):
        return True
    flag = activity.get("synthetic")
    if flag is True:
        return True
    if isinstance(flag, str) and flag.strip().lower() in {"true", "yes", "synthetic"}:
        return True
    for key in _TEXT_KEYS:
        value = activity.get(key)
        if isinstance(value, str) and _SYNTHETIC_WORD.search(value):
            return True
    return False

