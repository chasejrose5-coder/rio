# activity_data.py — one matched Intervals activity, in the v0.1 field groups.

"""Show the four groups from the Intervals data page.

The header and the Intervals table follow the locked field map: date and
start, title, distance, elapsed time, average heart rate, then lap distance,
elapsed time, and pace. The HR summary is average heart rate, max heart rate,
HR zones, and decoupling. Streams are listed only when the activity has them.

The adapter stores the date, the start, the title, and the average heart
rate. Distance, elapsed time, the interval rows, the rest of the heart-rate
summary, and stream samples are not stored. Each of those says "not pulled."
An activity that records an empty stream list has no streams, so that group
stays off the page. A missing stream list was not pulled.

The rows are matched activities already stored. This file does not call
Intervals.icu. No model. No spend. No scores.
"""

from __future__ import annotations

import re

from ui.last_session import heart_rate_text
from ui.settings import format_date

# Shown wherever the adapter has no stored value for that field.
NOT_PULLED = "not pulled."

# Header labels from the field map. Distance and elapsed time are the
# activity totals. WORK distance and WORK rep times are not those fields.
_HEADER = (
    ("Date / start time", "when"),
    ("Title", "title"),
    ("Distance", "gap"),
    ("Elapsed Time", "gap"),
    ("Avg HR", "hr"),
)

# Intervals table. The stored reps list is not this table.
_INTERVALS = ("Distance", "Elapsed Time", "Pace")

# Heart-rate summary on the activity. Only the average is stored.
_HR = (
    ("Avg HR", "hr"),
    ("Max HR", "gap"),
    ("HR zones", "gap"),
    ("Decoupling", "gap"),
)

_STREAM_LABELS = {
    "heartrate": "Heart rate",
    "velocity_smooth": "Pace",
    "pace": "Pace",
    "altitude": "Altitude",
    "cadence": "Cadence",
    "watts": "Power",
    "distance": "Distance",
    "time": "Time",
    "latlng": "Position",
    "temp": "Temperature",
    "grade_smooth": "Grade",
    "grade": "Grade",
    "moving": "Moving",
}

_SYNTHETIC = re.compile(r"(?<![A-Za-z])synthetic(?![A-Za-z])", re.IGNORECASE)


def matched_activities(activities: object) -> list[dict]:
    """Matched rows only, newest start first. An extra session stays out."""
    rows = []
    for row in activities or []:
        if not isinstance(row, dict) or row.get("matched") is not True:
            continue
        if _ident(row.get("id")) is None:
            continue
        rows.append(row)
    rows.sort(
        key=lambda row: (
            str(row.get("date") or ""),
            str(row.get("start") or ""),
            _ident(row.get("id")) or "",
        ),
        reverse=True,
    )
    return rows


def choice_labels(rows: list[dict]) -> list[str]:
    """Date and title. The same label twice keeps the activity id on each."""
    base = [_choice_label(row) for row in rows]
    counts: dict[str, int] = {}
    for label in base:
        counts[label] = counts.get(label, 0) + 1
    labels = []
    for row, label in zip(rows, base):
        if counts[label] > 1:
            labels.append(f"{label} · {_ident(row.get('id'))}")
        else:
            labels.append(label)
    return labels


def activity_banner(row: object) -> str | None:
    """SYNTHETIC / FIXTURE when the stored name or id says synthetic."""
    if not isinstance(row, dict):
        return None
    blob = f"{row.get('name') or ''} {row.get('id') or ''}"
    if _SYNTHETIC.search(blob):
        return "SYNTHETIC / FIXTURE"
    return None


def activity_view(activity: object, *, date_format: str = "iso") -> dict:
    """The four groups. A field the adapter does not store is not pulled.

    A missing streams list was not pulled, so the group says so. An empty
    list means the activity has no streams and the group is omitted. Named
    streams still say not pulled, because the samples are not stored.
    """
    row = activity if isinstance(activity, dict) else {}
    values = {
        "when": _when(row, date_format),
        "title": _title(row),
        "hr": _hr(row),
        "gap": NOT_PULLED,
    }
    return {
        "header": [(label, values[kind]) for label, kind in _HEADER],
        "intervals": [{column: NOT_PULLED for column in _INTERVALS}],
        "hr": [(label, values[kind]) for label, kind in _HR],
        "streams": _streams(row),
    }


def _choice_label(row: dict) -> str:
    day = str(row.get("date") or "").strip() or "—"
    name = row.get("name")
    title = name.strip() if isinstance(name, str) else ""
    if not title:
        title = _ident(row.get("id")) or "Activity"
    return f"{day} · {title}"


def _ident(value: object) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _when(row: dict, date_format: str) -> str:
    start = row.get("start")
    if isinstance(start, str) and start.strip():
        text = start.strip()
        day = text[:10]
        shown = format_date(day, date_format)
        clock = _clock(text)
        if clock and shown and shown != "—":
            return f"{shown}, {clock}"
        if shown and shown != "—":
            return shown
    day = row.get("date")
    if isinstance(day, str) and day.strip():
        shown = format_date(day.strip(), date_format)
        if shown and shown != "—":
            return shown
    return "—"


def _clock(text: str) -> str:
    if "T" not in text:
        return ""
    clock = text.split("T", 1)[1].replace("Z", "")
    for mark in ("+", "-"):
        index = clock.find(mark)
        if index > 0:
            clock = clock[:index]
            break
    parts = clock.split(":")
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return ""
    return f"{int(parts[0]):02d}:{int(parts[1]):02d}"


def _title(row: dict) -> str:
    name = row.get("name")
    if not isinstance(name, str) or not name.strip():
        return "—"
    return name.strip()


def _hr(row: dict) -> str:
    if "heart_rate" not in row or row.get("heart_rate") is None:
        return "—"
    text = heart_rate_text({"average_heartrate": row.get("heart_rate")})
    return text if text else "—"


def _streams(row: dict) -> list[tuple[str, str]] | str | None:
    """Named streams, not pulled, or omitted when the activity has none.

    A missing list was not stored. An empty list is an activity with no streams.
    """
    if "streams" not in row:
        return NOT_PULLED
    names = _stream_names(row.get("streams"))
    if not names:
        return None
    return [(_STREAM_LABELS.get(name, name), NOT_PULLED) for name in names]


def _stream_names(raw: object) -> list[str]:
    if isinstance(raw, dict):
        names = []
        for key, value in raw.items():
            if _empty_stream(value):
                continue
            text = str(key).strip()
            if text:
                names.append(text)
        return names
    if isinstance(raw, list):
        names = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                names.append(item.strip())
        return names
    return []


def _empty_stream(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple, dict, str)) and len(value) == 0:
        return True
    return False
