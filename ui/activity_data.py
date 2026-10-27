# activity_data.py — matched Intervals workouts. Display only.

"""Completed work and average heart rate for matched Intervals workouts.

One row is one matched session: the date, the template or the activity
label, WORK meters, and average heart rate. Weekly meters sum that work.
Warm-up and cool-down stay out. Template meters are not used. A day with
no stored match and no Intervals file is left out. A matched activity
with no work meters and no heart rate is left out, so an empty record
draws no line and no dot.

A second list is every stored activity that has an activity distance or
an average heart rate. Each row shows the date, the activity name, that
distance, and the heart rate. An unmatched activity is labeled extra.
An activity with no distance and no heart rate is left out. WORK meters
are not that distance.

The field groups remain for a stored activity whose samples were not
pulled. The header and the Intervals table follow the locked field map.
Distance, elapsed time, the interval rows, the rest of the heart-rate
summary, and stream samples say "not pulled." An empty stream list means
the activity has no streams, so that group stays off.

This file does not call Intervals.icu. No model. No spend. No scores.
"""

from __future__ import annotations

import math
import re
from datetime import date, timedelta

from ui.calendar import session_label
from ui.last_session import activity_by_ref, activity_heart_rate, heart_rate_text
from ui.progress import week_sunday
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


def all_activities(activities: object, *, date_format: str = "iso") -> list[dict]:
    """Every stored activity with a distance or an average heart rate.

    Newest start first. The name is the activity name. Distance is the
    activity distance, not WORK meters. An unmatched activity is labeled
    extra. An activity with no distance and no heart rate is left out.
    """
    rows = []
    for activity in activities or []:
        if not isinstance(activity, dict):
            continue
        ident = _ident(activity.get("id"))
        if ident is None:
            continue
        meters = _whole_meters(activity.get("distance"))
        if meters == 0:
            meters = None
        bpm = _bpm(activity.get("heart_rate"))
        if meters is None and bpm is None:
            continue
        day = activity.get("date") if isinstance(activity.get("date"), str) else ""
        name = activity.get("name")
        title = name.strip() if isinstance(name, str) and name.strip() else "—"
        shown = format_date(day, date_format) if day else "—"
        if not shown:
            shown = "—"
        rows.append(
            {
                "date": day,
                "shown_date": shown,
                "name": title,
                "meters": meters,
                "distance": _work_text(meters),
                "heart_rate": bpm,
                "hr": _hr_text(bpm),
                "extra": activity.get("matched") is not True,
                "id": ident,
                "start": str(activity.get("start") or ""),
            }
        )
    rows.sort(key=lambda row: (row["date"], row["start"], row["id"]), reverse=True)
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


def file_heart_rates(
    sessions: list,
    actuals: dict | None,
    directory=None,
) -> dict[str, float]:
    """Average heart rate from a stored Intervals file on a planned day.

    The ref has to belong to that day's template. A missing file is left
    out. Lap heart rates stay on the laps. The read stays on disk.
    """
    if not isinstance(actuals, dict):
        return {}
    templates = _planned_templates(sessions)
    found: dict[str, float] = {}
    for day, row in actuals.items():
        if not isinstance(day, str) or not isinstance(row, dict):
            continue
        if templates.get(day) != row.get("template_id"):
            continue
        text = _ref_text(row.get("intervals"))
        if not text:
            continue
        bpm = _bpm(activity_heart_rate(activity_by_ref(text, directory)))
        if bpm is None:
            continue
        found[day] = bpm
    return found


def session_rows(
    activities: object,
    sessions: object,
    *,
    file_distances: dict | None = None,
    file_heart_rates: dict | None = None,
    date_format: str = "iso",
) -> list[dict]:
    """One row per matched session, newest date first.

    The label is the plan template when that day is in the stored plan,
    otherwise the activity name. Work meters are the matched activity's
    WORK distance. A loaded file fills a planned day that has no matched
    work meters. Warm-up, cool-down, activity totals, and template meters
    are not used. A day with neither a match nor a file is left out.
    A matched activity with no work meters and no heart rate is left out.
    """
    planned = _planned(sessions)
    distances = file_distances if isinstance(file_distances, dict) else {}
    rates = file_heart_rates if isinstance(file_heart_rates, dict) else {}
    rows: list[dict] = []
    covered: set[str] = set()
    for activity in matched_activities(activities):
        day = activity.get("date") if isinstance(activity.get("date"), str) else ""
        if day:
            covered.add(day)
        template_id, codes = _template(planned.get(day), activity)
        meters = _whole_meters(activity.get("work_m"))
        if meters is None and day:
            meters = _whole_meters(distances.get(day))
        bpm = _bpm(activity.get("heart_rate"))
        if bpm is None and day:
            bpm = _bpm(rates.get(day))
        if meters is None and bpm is None:
            continue
        rows.append(
            _session_row(
                day,
                template_id,
                codes,
                activity.get("name"),
                meters,
                bpm,
                date_format,
                _ident(activity.get("id")) or "",
                str(activity.get("start") or ""),
            )
        )
    extras = []
    for day in set(distances) | set(rates):
        if not isinstance(day, str) or day in covered or day not in planned:
            continue
        meters = _whole_meters(distances.get(day))
        bpm = _bpm(rates.get(day))
        if meters is None and bpm is None:
            continue
        extras.append(day)
    for day in extras:
        session = planned[day]
        template_id = session.get("template_id")
        template = template_id.strip() if isinstance(template_id, str) else ""
        codes = session.get("reason_codes")
        rows.append(
            _session_row(
                day,
                template,
                codes if isinstance(codes, list) else [],
                "",
                _whole_meters(distances.get(day)),
                _bpm(rates.get(day)),
                date_format,
                "",
                "",
            )
        )
    rows.sort(key=lambda row: (row["date"], row["start"], row["id"]), reverse=True)
    return rows


def heart_rate_points(rows: list) -> list[dict]:
    """One point per matched row that has an average heart rate."""
    points = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        day = row.get("date")
        bpm = _bpm(row.get("heart_rate"))
        if not isinstance(day, str) or not day or bpm is None:
            continue
        points.append({"date": day, "bpm": bpm})
    return points


def weekly_completed_meters(rows: list, *, start: date, length: int) -> list[int]:
    """Completed WORK meters for each plan week.

    A week with no matched work is 0 when some other week has work meters.
    No work meters at all returns an empty list, so the page draws no line.
    A date outside the season is left out. Template meters are not read.
    """
    if type(start) is not date:
        return []
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        return []
    origin = week_sunday(start, 1)
    close = origin + timedelta(days=length * 7)
    totals = [0] * length
    found = False
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        meters = row.get("meters")
        if isinstance(meters, bool) or not isinstance(meters, int) or meters < 0:
            continue
        day = _iso_day(row.get("date"))
        if day is None or day < origin or day >= close:
            continue
        index = (day - origin).days // 7
        if index < 0 or index >= length:
            continue
        totals[index] += meters
        found = True
    if not found:
        return []
    return totals


def _planned(sessions: object) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        day = session.get("date")
        if isinstance(day, str) and day:
            found[day] = session
    return found


def _planned_templates(sessions: list) -> dict[str, str]:
    found: dict[str, str] = {}
    for day, session in _planned(sessions).items():
        template_id = session.get("template_id")
        if isinstance(template_id, str) and template_id:
            found[day] = template_id
    return found


def _ref_text(value: object) -> str:
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return ""


def _template(session: dict | None, activity: dict) -> tuple[str, list]:
    """The stored plan's template for this day. The activity template is the fallback."""
    if isinstance(session, dict):
        template_id = session.get("template_id")
        if isinstance(template_id, str) and template_id.strip():
            codes = session.get("reason_codes")
            return template_id.strip(), codes if isinstance(codes, list) else []
    template_id = activity.get("template_id")
    if isinstance(template_id, str) and template_id.strip():
        return template_id.strip(), []
    return "", []


def _session_row(
    day: str,
    template_id: str,
    codes: list,
    name: object,
    meters: int | None,
    bpm: float | None,
    date_format: str,
    ident: str,
    start: str,
) -> dict:
    shown = format_date(day, date_format) if day else "—"
    if not shown:
        shown = "—"
    return {
        "date": day,
        "shown_date": shown,
        "label": _workout_label(template_id, codes, name),
        "template_id": template_id,
        "meters": meters,
        "work": _work_text(meters),
        "heart_rate": bpm,
        "hr": _hr_text(bpm),
        "id": ident,
        "start": start,
    }


def _workout_label(template_id: str, codes: list, name: object) -> str:
    label = session_label(template_id, codes)
    if label:
        return label
    if isinstance(name, str) and name.strip():
        return name.strip()
    if template_id:
        return template_id
    return "—"


def _work_text(meters: int | None) -> str:
    if meters is None:
        return "—"
    return f"{meters:,} m"


def _hr_text(bpm: float | None) -> str:
    if bpm is None:
        return "—"
    text = heart_rate_text({"average_heartrate": bpm})
    return text if text else "—"


def _whole_meters(value: object) -> int | None:
    number = _meters(value)
    if number is None:
        return None
    return int(number + 0.5)


def _meters(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _bpm(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def _iso_day(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None
