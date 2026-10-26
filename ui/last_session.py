# last_session.py — open one local Intervals JSON file. Display input only.

"""Read one JSON file from tests/fixtures/intervals.

to_normalize_input builds the lap payload. The page then runs normalize,
classify, and explain on that payload and shows the same fields as a fixture.
This file does not call the network.

No scores. Prose spend stays capped at $25 where explain already records it.
"""

from __future__ import annotations

import json
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
    name = file.name
    try:
        text = file.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise IntervalsFileError(f"Could not read {name}.") from exc
    try:
        activity = json.loads(text)
    except json.JSONDecodeError as exc:
        raise IntervalsFileError(f"{name} is not JSON.") from exc
    if not isinstance(activity, dict):
        raise IntervalsFileError(f"{name} must be a JSON object.")
    try:
        payload = _session_payload(activity)
    except (TypeError, ValueError) as exc:
        message = str(exc).strip() or f"{name} could not be read."
        raise IntervalsFileError(message) from exc
    banner = "SYNTHETIC / FIXTURE" if _says_synthetic(file, activity) else None
    return payload, banner


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
