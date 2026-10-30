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

A dot marks each matched activity that has an average heart rate. The
dot is labeled with the day and that value. A day with no heart rate is
left blank.

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
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="#f4f4f4" />'
        )
    return (
        f'<polyline points="{drawn}" fill="none" stroke="#f4f4f4" '
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
            'dominant-baseline="middle" fill="#8f8f8f" font-size="10">'
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
            'fill="#8f8f8f" font-size="10">'
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


_HR_W = 640
_HR_FONT = 12
_HR_PAD_X = 24
_HR_TOP = 18
_HR_ROW = 30
_HR_BAND = 20
_HR_PLOT = 136
_HR_BOTTOM = 22
_HR_GAP = 18
_SHORT_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def matched_heart_rates(activities: object) -> list[dict]:
    """Matched activities that have an average heart rate, oldest first.

    An unmatched activity is left out. A matched day with no heart rate is
    left out. The value is the activity average, already stored.
    """
    found = []
    for row in activities or []:
        if not isinstance(row, dict) or row.get("matched") is not True:
            continue
        day = _chart_day(row.get("date"))
        bpm = _bpm(row.get("heart_rate"))
        if day is None or bpm is None:
            continue
        found.append({"date": day.isoformat(), "bpm": bpm})
    found.sort(key=lambda item: (item["date"], item["bpm"]))
    return found


def heart_rate_chart(
    points: list,
    *,
    start: date,
    weeks: int,
    captions: dict | None = None,
) -> str:
    """Dots for matched heart rates on this season. A day with none is blank.

    points come from matched_heart_rates(). A date outside the season is
    left out. captions replaces the visible label for that ISO date. The
    value stays on the dot. Dates sit above the dots, on another row when
    they would collide. Display only. No scores.
    """
    if isinstance(weeks, bool) or not isinstance(weeks, int) or weeks <= 0:
        return ""
    if type(start) is not date:
        return ""
    dots = _heart_dots(points, start, weeks, captions)
    if not dots:
        return ""
    height = _place_heart_labels(dots)
    parts = [
        '<div class="rio-heart">',
        '<p class="rio-mark-label">Heart rate · bpm</p>',
        (
            f'<svg class="rio-heart-line" viewBox="0 0 {_HR_W} {height}" '
            'role="img" aria-label="Average heart rate" '
            'xmlns="http://www.w3.org/2000/svg" '
            "style=\"font-family: 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif; font-variant-numeric: tabular-nums\">"
        ),
        "<title>Average heart rate</title>",
        *_heart_marks(dots),
        "</svg></div>",
    ]
    return "".join(parts)


def _chart_day(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _bpm(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def _bpm_text(bpm: float) -> str:
    if float(bpm).is_integer():
        return str(int(bpm))
    return f"{bpm:.1f}"


def _heart_dots(
    points: list,
    start: date,
    weeks: int,
    captions: dict | None = None,
) -> list[dict]:
    origin = week_sunday(start, 1)
    close = origin + timedelta(days=weeks * 7 - 1)
    chosen = []
    for point in points or []:
        if not isinstance(point, dict):
            continue
        day = _chart_day(point.get("date"))
        bpm = _bpm(point.get("bpm"))
        if day is None or bpm is None or day < origin or day > close:
            continue
        chosen.append({"date": day, "bpm": bpm})
    if not chosen:
        return []
    chosen.sort(key=lambda item: (item["date"], item["bpm"]))
    months = {item["date"].month for item in chosen}
    first = chosen[0]["date"]
    last = chosen[-1]["date"]
    span = (last - first).days
    low = min(item["bpm"] for item in chosen)
    high = max(item["bpm"] for item in chosen)
    if high == low:
        floor = low - 8
        peak = high + 8
    else:
        pad = max(4.0, (high - low) * 0.18)
        floor = low - pad
        peak = high + pad
    width = _HR_W - _HR_PAD_X * 2
    dots = []
    for item in chosen:
        if span == 0:
            x = _HR_W / 2
        else:
            x = _HR_PAD_X + width * (item["date"] - first).days / span
        t = 1 - (item["bpm"] - floor) / (peak - floor)
        dots.append(
            {
                "x": x,
                "t": t,
                "bpm": item["bpm"],
                "label": _heart_caption(
                    item["date"],
                    item["bpm"],
                    len(months) > 1,
                    captions,
                ),
                "title": f"{item['date'].isoformat()} · {_bpm_text(item['bpm'])} bpm",
            }
        )
    return dots


def _heart_caption(
    day: date,
    bpm: float,
    with_month: bool,
    captions: dict | None,
) -> str:
    """The visible label. A date caption replaces the weekday line."""
    if isinstance(captions, dict):
        found = captions.get(day.isoformat())
        if isinstance(found, str) and found.strip() and found.strip() != "—":
            return found.strip()
    return _heart_label(day, bpm, with_month)


def _heart_label(day: date, bpm: float, with_month: bool) -> str:
    when = f"{day.month}/{day.day}" if with_month else str(day.day)
    return f"{_SHORT_DAYS[day.weekday()]} {when} · {_bpm_text(bpm)}"


def _heart_marks(dots: list[dict]) -> list[str]:
    marks = []
    for dot in dots:
        marks.append(
            f'<text class="rio-heart-label" x="{dot["label_x"]:.1f}" y="{dot["label_y"]:.1f}" '
            f'text-anchor="{dot["anchor"]}" fill="#f4f4f4" font-size="{_HR_FONT}" font-weight="500">'
            f'{_esc(dot["label"])}</text>'
        )
    for dot in dots:
        marks.append(
            f'<circle class="rio-heart-dot" cx="{dot["x"]:.1f}" cy="{dot["y"]:.1f}" '
            'r="5" fill="#6db892">'
            f'<title>{_esc(dot["title"])}</title></circle>'
        )
    return marks


def _place_heart_labels(dots: list[dict]) -> int:
    """Put each date above its dot. A colliding date takes the next row.

    The plot stays under the dates, so a label does not cover a dot.
    """
    rows: list[list[tuple[float, float]]] = []
    ordered = sorted(dots, key=lambda item: (item["x"], item["bpm"]))
    for dot in ordered:
        width = _heart_label_width(dot["label"])
        anchor = _heart_anchor(dot["x"], width)
        box = _heart_span(dot["x"], width, anchor)
        row_index = 0
        while row_index < len(rows) and _heart_span_hit(box, rows[row_index]):
            row_index += 1
        if row_index == len(rows):
            rows.append([])
        rows[row_index].append(box)
        dot["anchor"] = anchor
        dot["row"] = row_index
        dot["label_x"] = dot["x"]
    row_count = len(rows)
    plot_top = _HR_TOP + row_count * _HR_ROW + _HR_BAND
    for dot in dots:
        dot["label_y"] = _HR_TOP + dot["row"] * _HR_ROW + 14
        dot["y"] = plot_top + dot["t"] * _HR_PLOT
    return plot_top + _HR_PLOT + _HR_BOTTOM


def _heart_label_width(text: str) -> float:
    """Width of a 12px label, a little wide so two dates do not touch."""
    width = 0.0
    for char in text:
        if char == " ":
            width += 3.2
        elif char in ".,'":
            width += 3.2
        elif char in "-/":
            width += 4.0
        elif char == "·":
            width += 4.5
        elif char.isdigit():
            width += 6.6
        elif char.isupper():
            width += 7.2
        else:
            width += 5.6
    return width + 8.0


def _heart_anchor(x: float, width: float) -> str:
    if x - width / 2 < 6:
        return "start"
    if x + width / 2 > _HR_W - 6:
        return "end"
    return "middle"


def _heart_span(x: float, width: float, anchor: str) -> tuple[float, float]:
    if anchor == "start":
        return (x, x + width)
    if anchor == "end":
        return (x - width, x)
    return (x - width / 2, x + width / 2)


def _heart_span_hit(box: tuple[float, float], occupied: list[tuple[float, float]]) -> bool:
    left, right = box
    for other in occupied:
        if right + _HR_GAP <= other[0] or other[1] + _HR_GAP <= left:
            continue
        return True
    return False
