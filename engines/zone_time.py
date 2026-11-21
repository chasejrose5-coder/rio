# zone_time.py — time in each heart-rate zone from a Strava stream.

"""Each sample is counted by the heart rate at that second. Cardiac drift
is not adjusted. A run with no stream has no breakdown.

When the workout had a target zone and more time was spent above that zone
than inside it, the note tells the runner to slow down or stop next time.
"""

from __future__ import annotations

from datetime import date, timedelta

WARNING = (
    "You were above Zone {zone} for much of this run. Next time, slow down or stop "
    "until your heart rate is back in the zone."
)


def parse_hr_stream(payload: object) -> dict | None:
    """Parallel time and heart-rate samples, or None when Strava sent no stream."""
    if not isinstance(payload, dict):
        return None
    heart = payload.get("heartrate")
    clock = payload.get("time")
    if not isinstance(heart, dict) or not isinstance(clock, dict):
        return None
    rates = heart.get("data")
    times = clock.get("data")
    if not isinstance(rates, list) or not isinstance(times, list):
        return None
    count = min(len(rates), len(times), 20000)
    if count < 2:
        return None
    kept_time: list[int] = []
    kept_hr: list[int] = []
    for index in range(count):
        moment = _whole(times[index])
        bpm = _whole(rates[index])
        if moment is None or bpm is None or bpm <= 0:
            continue
        if kept_time and moment < kept_time[-1]:
            continue
        kept_time.append(moment)
        kept_hr.append(bpm)
    if len(kept_time) < 2:
        return None
    return {"time": kept_time, "hr": kept_hr}


def zone_report(stream: object, zones: object, target_zone: int | None) -> dict | None:
    """Seconds in each of the five zones. None when the stream or the zones are missing."""
    if not isinstance(stream, dict):
        return None
    bands = _bands(zones)
    if bands is None:
        return None
    times = stream.get("time")
    rates = stream.get("hr")
    if not isinstance(times, list) or not isinstance(rates, list):
        return None
    seconds = [0, 0, 0, 0, 0]
    above = 0
    counted = 0
    target_seconds = 0
    limit = min(len(times), len(rates))
    for index in range(limit - 1):
        start = _whole(times[index])
        end = _whole(times[index + 1])
        bpm = _whole(rates[index])
        if start is None or end is None or bpm is None or end <= start:
            continue
        span = end - start
        if span > 30:
            span = 30
        slot = _slot(bpm, bands)
        counted += span
        if slot is None:
            if bpm > bands[-1][2]:
                above += span
            continue
        seconds[slot] += span
        if target_zone is not None and slot + 1 == target_zone:
            target_seconds += span
        if target_zone is not None and slot + 1 > target_zone:
            above += span
    if counted <= 0:
        return None
    rows = []
    for index, (_number, name, _low, _high) in enumerate(bands):
        rows.append({"zone": index + 1, "name": name, "seconds": seconds[index]})
    warning = ""
    if isinstance(target_zone, int) and 1 <= target_zone <= 5 and above > target_seconds and above >= 60:
        warning = WARNING.format(zone=target_zone)
    return {
        "zones": rows,
        "above_seconds": above,
        "target_zone": target_zone if isinstance(target_zone, int) else None,
        "warning": warning,
    }


def season_week(start: object, day: object, length: object) -> int | None:
    """Plan week for a calendar day. Week 1 starts the Sunday on or before the start date."""
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        return None
    if not isinstance(start, date) or not isinstance(day, date):
        return None
    sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    if day < sunday:
        return None
    week = ((day - sunday).days // 7) + 1
    if week > length:
        return None
    return week


def sum_zone_reports(reports: object) -> dict | None:
    """Add the seconds in each zone. None when no report has a counted second.

    Names come from the first report that names that zone. A missing zone
    stays at 0 so the five zones still line up.
    """
    if not isinstance(reports, list):
        return None
    seconds = [0, 0, 0, 0, 0]
    names = ["", "", "", "", ""]
    counted = False
    for report in reports:
        if not isinstance(report, dict):
            continue
        rows = report.get("zones")
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            zone = row.get("zone")
            span = row.get("seconds")
            if isinstance(zone, bool) or not isinstance(zone, int) or zone not in range(1, 6):
                continue
            if isinstance(span, bool) or not isinstance(span, int) or span < 0:
                continue
            seconds[zone - 1] += span
            if span > 0:
                counted = True
            name = row.get("name")
            if isinstance(name, str) and name and not names[zone - 1]:
                names[zone - 1] = name
    if not counted:
        return None
    return {
        "zones": [
            {"zone": index + 1, "name": names[index], "seconds": seconds[index]}
            for index in range(5)
        ]
    }


def _bands(zones: object) -> list[tuple[int, str, int, int]] | None:
    if not isinstance(zones, list) or len(zones) < 5:
        return None
    found: dict[int, tuple[str, int, int]] = {}
    for row in zones:
        if not isinstance(row, dict):
            return None
        number = row.get("zone")
        name = row.get("name")
        low = row.get("low_bpm")
        high = row.get("high_bpm")
        if not isinstance(number, int) or isinstance(number, bool) or number not in range(1, 6):
            return None
        if not isinstance(name, str) or not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
            return None
        if isinstance(low, bool) or isinstance(high, bool) or int(low) >= int(high):
            return None
        found[number] = (name, int(low), int(high))
    if set(found) != {1, 2, 3, 4, 5}:
        return None
    return [(number, found[number][0], found[number][1], found[number][2]) for number in range(1, 6)]


def _slot(bpm: int, bands: list[tuple[int, str, int, int]]) -> int | None:
    for index, (_number, _name, low, high) in enumerate(bands):
        if low <= bpm <= high:
            return index
    return None


def _whole(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)
