# progress.py — season weeks as done, current, or upcoming. Display only.

"""One row per week of a plan Start already stored.

The week that contains today is current, even when it already has a mark.
Any other week with a mark is done. A week after today with no mark is
upcoming. A past week with no mark is unmarked. A done or unmarked week
has no countdown. The current week counts from today to the goal. An
upcoming week counts from the Saturday that closes it, so the number
steps down by a week each row.

Each week shows completed work distance. A day with a loaded Intervals
file contributes that file's WORK distance. A day with no file contributes
0. A week with no file shows 0 m. The same weekly totals are a line, and
a week with no file stays at 0. Template meters are not used.

No model. No spend. No scores.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from html import escape

# The three marks adapt() already stores. Anything else is not a mark.
MARKS = ("on_track", "not_hitting", "smashing")


def week_sunday(start: date, week_number: int) -> date:
    """Sunday that opens this plan week. Week 1 contains the start date."""
    anchor = start - timedelta(days=(start.weekday() + 1) % 7)
    return anchor + timedelta(days=(week_number - 1) * 7)


def days_remaining(goal: date, today: date) -> int:
    """Days from today until the goal date. A reached goal stays at zero."""
    remaining = (goal - today).days
    if remaining < 0:
        return 0
    return remaining


def days_label(days: int | None) -> str:
    """The countdown as written on a row. A blank countdown is an em dash."""
    if days is None:
        return "—"
    noun = "day" if days == 1 else "days"
    return f"{days} {noun} to goal"


def _row_days(
    status: str | None,
    *,
    start: date,
    week_number: int,
    goal: date,
    today: date,
) -> int | None:
    """Days left on this row. Done and unmarked weeks have none.

    The current week counts from today. An upcoming week counts from the
    Saturday that closes it, which is later each week, so the countdown
    falls by seven days a row until the goal.
    """
    if status == "current":
        return days_remaining(goal, today)
    if status == "upcoming":
        saturday = week_sunday(start, week_number) + timedelta(days=6)
        return days_remaining(goal, saturday)
    return None


def week_status(*, start: date, week_number: int, today: date, marked: bool) -> str | None:
    """done, current, upcoming, or None when a past week has no mark.

    Current wins when the week contains today, so the row you are in stays
    current after a mark. A mark on any other week is done, including a
    week that has not started. An unmarked week that starts after today
    is upcoming.
    """
    sunday = week_sunday(start, week_number)
    saturday = sunday + timedelta(days=6)
    if sunday <= today <= saturday:
        return "current"
    if marked:
        return "done"
    if today < sunday:
        return "upcoming"
    return None


def week_meters(sessions: list, distances: dict | None = None) -> int:
    """Completed WORK meters for this week.

    A day with a loaded distance contributes that distance. A day with no
    file contributes 0. A week with no loaded file is 0. Template meters
    are not used. The loaded number is already WORK distance.
    """
    total = sum(_loaded_meters(sessions, distances).values())
    if not math.isfinite(total) or total < 0:
        return 0
    return int(total + 0.5)


def week_volume(sessions: list, distances: dict | None = None) -> str:
    """Completed distance for this week, as a label. A week with no file is 0 m."""
    return _meter_text(week_meters(sessions, distances))


def _loaded_meters(sessions: list, distances: dict | None) -> dict[str, float]:
    """Dates in this week that have a loaded Intervals distance."""
    if not isinstance(distances, dict) or not sessions:
        return {}
    found: dict[str, float] = {}
    for session in sessions:
        if not isinstance(session, dict):
            continue
        day = session.get("date")
        if not isinstance(day, str) or day not in distances:
            continue
        meters = _distance_number(distances.get(day))
        if meters is None:
            continue
        found[day] = meters
    return found


def _distance_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _meter_text(meters: int | float | None) -> str:
    if isinstance(meters, bool) or not isinstance(meters, (int, float)):
        return "—"
    if isinstance(meters, float):
        if not math.isfinite(meters) or meters < 0:
            return "—"
        meters = int(meters + 0.5)
    if meters < 0:
        return "—"
    return f"{meters:,} m"


def phase_label(sessions: list) -> str:
    """The phase digits already stored on the week's sessions."""
    found: list[str] = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        codes = session.get("reason_codes") or []
        if not isinstance(codes, list):
            continue
        for code in codes:
            text = str(code)
            if len(text) == 7 and text.startswith("phase_") and text[6] in "12345678":
                number = text[6]
                if number not in found:
                    found.append(number)
    if len(found) == 1:
        return found[0]
    if not found:
        return "—"
    return ", ".join(found)


def _marked(marks: dict, week: int) -> bool:
    return marks.get(week) in MARKS


def progress_weeks(
    *,
    start: date,
    goal: date,
    length: int,
    sessions: list,
    marks: dict | None,
    today: date,
    distances: dict | None = None,
) -> list[dict]:
    """Week number, phase, status, days remaining, and volume, in season order.

    A done or unmarked week has no countdown. The current week counts from
    today. An upcoming week counts from the Saturday that closes it.
    Volume is loaded WORK distance. A day with no file contributes 0.
    A week with no file shows 0 m. meters is that same total as a number,
    0 when the week has no file. Template meters are not used.
    """
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        return []
    grouped: dict[int, list] = {}
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        number = session.get("week_number")
        if isinstance(number, bool) or not isinstance(number, int):
            continue
        grouped.setdefault(number, []).append(session)
    stored = marks if isinstance(marks, dict) else {}
    rows = []
    for number in range(1, length + 1):
        status = week_status(
            start=start,
            week_number=number,
            today=today,
            marked=_marked(stored, number),
        )
        meters = week_meters(grouped.get(number, []), distances)
        rows.append(
            {
                "week": number,
                "phase": phase_label(grouped.get(number, [])),
                "status": status,
                "days_remaining": _row_days(
                    status,
                    start=start,
                    week_number=number,
                    goal=goal,
                    today=today,
                ),
                "meters": meters,
                "volume": _meter_text(meters),
            }
        )
    return rows


# Chart box. The page scales it to the card width.
_CHART_W = 640
_CHART_H = 152
_CHART_LEFT = 42
_CHART_RIGHT = 12
_CHART_TOP = 14
_CHART_BOTTOM = 24
_M_TO_MI = 1 / 1609.344


def volume_chart(meters: list, units: str = "km", captions: list | None = None) -> str:
    """A line of weekly completed distance. A week with no file is a point at 0.

    units is the settings choice, km or miles. A metric week of at least
    1 km uses km. A shorter week stays in m. Miles uses mi. The word
    mileage is not used. Display only. No scores.
    """
    values = _chart_meters(meters)
    if not values:
        return ""
    unit = _chart_unit(max(values), units)
    points = _chart_points(values)
    labels = captions if isinstance(captions, list) else None
    parts = [
        '<div class="rio-volume">',
        f'<p class="rio-mark-label">Volume · {_esc(unit)}</p>',
        (
            f'<svg class="rio-volume-line" viewBox="0 0 {_CHART_W} {_CHART_H}" '
            'role="img" aria-label="Weekly completed distance" '
            'xmlns="http://www.w3.org/2000/svg" '
            "style=\"font-family: 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif\">"
        ),
        "<title>Weekly completed distance</title>",
        _baseline(points),
        _series(points),
        *_y_labels(values, unit, points),
        *_x_labels(len(values), points),
        *_hover(values, points, unit, labels),
        "</svg></div>",
    ]
    return "".join(parts)


def _chart_meters(values: list) -> list[int]:
    found = []
    for value in values or []:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            found.append(0)
            continue
        number = float(value)
        if not math.isfinite(number) or number < 0:
            found.append(0)
            continue
        found.append(int(number + 0.5))
    return found


def _chart_unit(peak: int, units: str) -> str:
    if units == "miles":
        return "mi"
    if peak >= 1000:
        return "km"
    return "m"


def _chart_points(values: list[int]) -> list[tuple[float, float]]:
    """Plot coordinates. y grows downward, so 0 sits on the baseline."""
    count = len(values)
    peak = max(values) if values else 0
    width = _CHART_W - _CHART_LEFT - _CHART_RIGHT
    height = _CHART_H - _CHART_TOP - _CHART_BOTTOM
    baseline = _CHART_TOP + height
    points = []
    for index, meters in enumerate(values):
        if count == 1:
            x = _CHART_LEFT + width / 2
        else:
            x = _CHART_LEFT + width * index / (count - 1)
        if peak <= 0:
            y = baseline
        else:
            y = baseline - height * (meters / peak)
        points.append((x, y))
    return points


def _format_amount(meters: float, unit: str) -> str:
    if meters <= 0:
        return "0"
    if unit == "m":
        return f"{int(meters + 0.5):,}"
    if unit == "km":
        km = meters / 1000.0
        if abs(km - round(km)) < 1e-9:
            return str(int(round(km)))
        return f"{km:.1f}"
    miles = meters * _M_TO_MI
    if miles < 0.1:
        return f"{miles:.2f}"
    return f"{miles:.1f}"


def _baseline(points: list[tuple[float, float]]) -> str:
    floor = max(point[1] for point in points)
    x1 = _CHART_LEFT
    x2 = _CHART_W - _CHART_RIGHT
    return (
        f'<line x1="{x1:.1f}" y1="{floor:.1f}" x2="{x2:.1f}" y2="{floor:.1f}" '
        'stroke="#2a2a2a" stroke-width="1" vector-effect="non-scaling-stroke" />'
    )


def _series(points: list[tuple[float, float]]) -> str:
    drawn = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    if len(points) == 1:
        x, y = points[0]
        return (
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="#d5d5d5" />'
        )
    return (
        f'<polyline points="{drawn}" fill="none" stroke="#d5d5d5" '
        'stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" '
        'vector-effect="non-scaling-stroke" />'
    )


def _y_labels(values: list[int], unit: str, points: list[tuple[float, float]]) -> list[str]:
    peak = max(values) if values else 0
    floor = max(point[1] for point in points)
    top = min(point[1] for point in points)
    ticks = [(0.0, floor)]
    if peak > 0:
        ticks.append((float(peak), top))
        mid = peak / 2
        if _format_amount(mid, unit) not in (_format_amount(0, unit), _format_amount(peak, unit)):
            ticks.append((mid, (top + floor) / 2))
    labels = []
    for amount, y in ticks:
        text = _esc(_format_amount(amount, unit))
        labels.append(
            f'<text x="{_CHART_LEFT - 8:.1f}" y="{y:.1f}" text-anchor="end" '
            'dominant-baseline="middle" fill="#6f6f6f" font-size="10">'
            f"{text}</text>"
        )
    return labels


def _x_labels(count: int, points: list[tuple[float, float]]) -> list[str]:
    width = _CHART_W - _CHART_LEFT - _CHART_RIGHT
    gap = width if count <= 1 else width / (count - 1)
    step = 1
    while count > 1 and step < count and step * gap < 36:
        step += 1
    indexes = [0] if count <= 1 else list(range(0, count, step))
    last = count - 1
    if indexes[-1] != last:
        if (last - indexes[-1]) * gap < 28 and len(indexes) > 1:
            indexes[-1] = last
        else:
            indexes.append(last)
    y = _CHART_H - 8
    labels = []
    for index in indexes:
        x = points[index][0]
        if index == 0 and count > 1:
            anchor = "start"
        elif index == last and count > 1:
            anchor = "end"
        else:
            anchor = "middle"
        labels.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            'fill="#6f6f6f" font-size="10">'
            f"{index + 1}</text>"
        )
    return labels


def _hover(
    values: list[int],
    points: list[tuple[float, float]],
    unit: str,
    captions: list | None,
) -> list[str]:
    marks = []
    for index, (meters, (x, y)) in enumerate(zip(values, points)):
        shown = _point_caption(index, meters, unit, captions)
        marks.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="transparent">'
            f"<title>{_esc(shown)}</title></circle>"
        )
    return marks


def _point_caption(index: int, meters: int, unit: str, captions: list | None) -> str:
    shown = ""
    if captions is not None and index < len(captions) and isinstance(captions[index], str):
        shown = captions[index].strip()
    if not shown:
        shown = f"{_format_amount(meters, unit)} {unit}"
    return f"Week {index + 1} · {shown}"


def _esc(value: object) -> str:
    return escape(str(value), quote=True)
