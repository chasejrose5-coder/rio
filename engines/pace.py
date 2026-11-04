# pace.py — 800m split targets from the goal and the logs. Rules only.

"""Exact rep times for a prescribed workout.

The formulas are fixed. The same inputs always return the same times.
Nothing here is random, learned, or fetched. This is not a classification,
and it does not store a score.

Scheduled 800
    The season starts at the current 800 and ends at the goal 800.
    On the start date the scheduled time is the current mark.
    On the goal date, and after it, the scheduled time is the goal.
    Between those dates the time moves in a straight line by calendar day:

        span = goal_date - start_date, in days
        elapsed = on - start_date, in days
        scheduled = current + (goal - current) * (elapsed / span)

    If the goal date is on or before the start date, the scheduled time
    is the goal on every date.

Pace fractions
    A rep time is the scheduled 800 pace, scaled by a fraction for the
    workout family. The fraction is seconds relative to 800 pace, so 1.00
    is race pace, a smaller number is faster, and a larger number is slower.

        mv   0.82   max velocity, clearly faster than 800 pace
        spd  0.96   at or faster than 800 pace
        rr   1.00   race pace, including the 800 race itself
        se   1.03   near 800 pace
        an   1.06   hard, a little slower than race pace
        ap   1.12   strong, clearly slower than 800 pace
        thr  1.18   comfortably hard, not 800 pace
        aer  1.55   easy running

        seconds = meters * (scheduled_800 / 800) * fraction

    The family is the first piece of the frozen template id.

Distances
    A flat id repeats one distance.
    An up id (a ladder) steps evenly from the first distance to the last,
    one step per rep.
    A py id (a pyramid) climbs to the long rep at the middle, then comes
    back down by the same step. Five reps from 200 to 400 are
    200, 300, 400, 300, 200.

Rounding
    Each rep is rounded to a tenth of a second, half up, after the raw
    seconds are rounded to six decimals. The block time uses those tenths,
    plus the rest between reps. Rest after the last rep is not included.

Tolerance
    Each rep has a window of half a percent of its time, and at least
    0.2 seconds. A 21.4 second rep is 21.2-21.6.

Logged results
    A log is a race or a workout result: the day, the seconds that were
    run, and either an explicit target or the template that was prescribed.
    A log changes dates after it. It does not change its own day.
    The error is (actual - target) / target. Faster than the target is a
    negative error and tightens later targets. Slower eases them.
    Each ISO week can move the factor by at most 1 percent in total.
    A larger error is cut to the room left in that week, so one result
    cannot jump the times. The factor starts at 1. Later targets use

        effective_800 = scheduled_800 * factor

    With no logs the factor stays 1, which is on track.
    A factor below 1 is ahead. A factor above 1 is behind.
    After the goal date the schedule stays on the goal, and logs still
    correct it under the same weekly cap.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

# One week of logs may shift targets by at most this share of the 800.
WEEKLY_CAP = Decimal("0.01")
# Half a percent, and never tighter than two tenths on a short rep.
TOLERANCE_SHARE = Decimal("0.005")
TOLERANCE_FLOOR = Decimal("0.2")

# Seconds relative to 800 pace. 1 is race pace.
FAMILY_FRACTION = {
    "mv": Decimal("0.82"),
    "spd": Decimal("0.96"),
    "rr": Decimal("1.00"),
    "se": Decimal("1.03"),
    "an": Decimal("1.06"),
    "ap": Decimal("1.12"),
    "thr": Decimal("1.18"),
    "aer": Decimal("1.55"),
}

STATUS_ON_TRACK = "on track"
STATUS_AHEAD = "ahead"
STATUS_BEHIND = "behind"

_MARK = re.compile(r"^(\d+):(\d{2}(?:\.\d+)?)$")
_ID = re.compile(
    r"^(?P<family>[a-z]+)_(?:(?P<shape>py|up)_)?(?P<start>\d+)"
    r"(?:to(?P<end>\d+))?_r(?P<rest>\d+)_x(?P<reps>\d+)$"
)
_ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SIX = Decimal("0.000001")
_TENTH = Decimal("0.1")
_METERS = Decimal(800)


@dataclass(frozen=True)
class PaceLog:
    """One logged race or workout. Dates after this log use the correction.

    actual_seconds is the time that was run. For a single race it is the
    race time. For a rep workout it is the average rep time.
    target_seconds, when set, is the target those seconds are compared with.
    Otherwise template_id is prescribed and the target is computed.
    """

    on: date
    actual_seconds: float
    template_id: str = ""
    target_seconds: float | None = None


def parse_mark(mark: object) -> Decimal:
    """Seconds in an 800 time such as 1:55.0 or 2:02.9."""
    if not isinstance(mark, str):
        raise ValueError("800 time is not a mark")
    found = _MARK.fullmatch(mark.strip())
    if found is None:
        raise ValueError("800 time is not a mark")
    seconds = Decimal(found.group(1)) * 60 + Decimal(found.group(2))
    if seconds <= 0:
        raise ValueError("800 time is not a mark")
    return seconds


def scheduled_seconds(
    current: Decimal,
    goal: Decimal,
    start: date,
    goal_day: date,
    on: date,
) -> Decimal:
    """The 800 the calendar calls for on this date, before any log."""
    span = (goal_day - start).days
    if span <= 0 or on >= goal_day:
        return goal
    if on <= start:
        return current
    elapsed = Decimal((on - start).days)
    return current + (goal - current) * (elapsed / Decimal(span))


def correction_factor(
    current: Decimal,
    goal: Decimal,
    start: date,
    goal_day: date,
    on: date,
    logs: list[PaceLog] | tuple[PaceLog, ...] | None,
) -> Decimal:
    """Share applied to the scheduled 800. 1 means the logs have not moved it.

    Only logs dated before `on` count. Each ISO week spends at most WEEKLY_CAP.
    """
    factor = Decimal(1)
    spent: dict[tuple[int, int], Decimal] = {}
    ordered = _ordered_logs(logs)
    for entry in ordered:
        if entry.on >= on:
            continue
        target = _log_target(entry, current, goal, start, goal_day, factor)
        if target is None or target <= 0:
            continue
        actual = _decimal(entry.actual_seconds)
        if actual is None or actual <= 0:
            continue
        error = (actual - target) / target
        week = entry.on.isocalendar()[:2]
        used = spent.get(week, Decimal(0))
        room = WEEKLY_CAP - used
        if room < 0:
            room = Decimal(0)
        applied = error
        if applied > room:
            applied = room
        if applied < -room:
            applied = -room
        factor = factor * (Decimal(1) + applied)
        spent[week] = used + abs(applied)
    return factor


def status_for(factor: Decimal) -> str:
    """ahead when logs have tightened the 800, behind when they have eased it."""
    if factor < 1:
        return STATUS_AHEAD
    if factor > 1:
        return STATUS_BEHIND
    return STATUS_ON_TRACK


def workout_times(
    template_id: object,
    *,
    current_mark: object,
    goal_mark: object,
    start: date,
    goal_date: date,
    on: date,
    logs: list[PaceLog] | tuple[PaceLog, ...] | None = None,
) -> dict | None:
    """The line, the tolerance, and the block for one prescribed workout.

    None when the id is not a frozen rep recipe. The dict is plain numbers
    and strings so a page can print it without another rule.
    """
    parsed = _parse_id(template_id)
    if parsed is None:
        return None
    current = parse_mark(current_mark)
    goal = parse_mark(goal_mark)
    start_day = _as_date(start)
    goal_day = _as_date(goal_date)
    day = _as_date(on)
    factor = correction_factor(current, goal, start_day, goal_day, day, logs)
    scheduled = scheduled_seconds(current, goal, start_day, goal_day, day)
    effective = scheduled * factor
    family, shape, first, last, rest, reps = parsed
    distances = _distances(shape, first, last, reps)
    fraction = FAMILY_FRACTION[family]
    rows = []
    for meters in distances:
        raw = (Decimal(meters) * effective / _METERS) * fraction
        seconds = _tenths(raw)
        half = _tolerance_half(seconds)
        rows.append(
            {
                "meters": meters,
                "seconds": seconds,
                "low": seconds - half,
                "high": seconds + half,
            }
        )
    block = _block(rows, rest)
    return {
        "line": _line(rows, rest),
        "tolerance": _tolerance_text(rows),
        "block": _clock(block),
        "block_seconds": block,
        "rest_seconds": rest,
        "reps": rows,
        "scheduled_seconds": scheduled,
        "effective_seconds": effective,
        "factor": factor,
        "status": status_for(factor),
    }


def project_800(
    *,
    current_mark: object,
    goal_mark: object,
    start: date,
    goal_date: date,
    on: date,
    logs: list[PaceLog] | tuple[PaceLog, ...] | None = None,
) -> dict:
    """Scheduled 800, the log-corrected 800, and on track / ahead / behind."""
    current = parse_mark(current_mark)
    goal = parse_mark(goal_mark)
    start_day = _as_date(start)
    goal_day = _as_date(goal_date)
    day = _as_date(on)
    factor = correction_factor(current, goal, start_day, goal_day, day, logs)
    scheduled = scheduled_seconds(current, goal, start_day, goal_day, day)
    return {
        "scheduled_seconds": scheduled,
        "effective_seconds": scheduled * factor,
        "factor": factor,
        "status": status_for(factor),
    }


def _log_target(
    entry: PaceLog,
    current: Decimal,
    goal: Decimal,
    start: date,
    goal_day: date,
    factor: Decimal,
) -> Decimal | None:
    """The target this log is judged against, before the log is applied."""
    if entry.target_seconds is not None:
        return _decimal(entry.target_seconds)
    parsed = _parse_id(entry.template_id)
    if parsed is None:
        return None
    family, shape, first, last, _rest, reps = parsed
    scheduled = scheduled_seconds(current, goal, start, goal_day, entry.on)
    effective = scheduled * factor
    distances = _distances(shape, first, last, reps)
    fraction = FAMILY_FRACTION[family]
    total = Decimal(0)
    for meters in distances:
        total += (Decimal(meters) * effective / _METERS) * fraction
    return total / Decimal(len(distances))


def _ordered_logs(
    logs: list[PaceLog] | tuple[PaceLog, ...] | None,
) -> list[PaceLog]:
    if not logs:
        return []
    paired = []
    for index, entry in enumerate(logs):
        if not isinstance(entry, PaceLog):
            continue
        paired.append((entry.on, index, entry))
    paired.sort(key=lambda item: (item[0], item[1]))
    return [entry for _day, _index, entry in paired]


def _parse_id(template_id: object) -> tuple[str, str, int, int, int, int] | None:
    if not isinstance(template_id, str):
        return None
    found = _ID.fullmatch(template_id.strip())
    if found is None:
        return None
    family = found.group("family")
    if family not in FAMILY_FRACTION:
        return None
    first = int(found.group("start"))
    end = found.group("end")
    last = first if end is None else int(end)
    rest = int(found.group("rest"))
    reps = int(found.group("reps"))
    if first <= 0 or last < first or rest < 0 or reps <= 0:
        return None
    shape = found.group("shape") or ""
    if shape and end is None:
        return None
    return family, shape, first, last, rest, reps


def _distances(shape: str, first: int, last: int, reps: int) -> list[int]:
    if shape == "up":
        return _ladder(first, last, reps)
    if shape == "py":
        return _pyramid(first, last, reps)
    return [first] * reps


def _ladder(first: int, last: int, reps: int) -> list[int]:
    if reps <= 1:
        return [first]
    span = Decimal(last - first)
    steps = Decimal(reps - 1)
    return [int(_whole(Decimal(first) + span * Decimal(index) / steps)) for index in range(reps)]


def _pyramid(first: int, last: int, reps: int) -> list[int]:
    peak = reps // 2
    if peak <= 0:
        return [first]
    step = Decimal(last - first) / Decimal(peak)
    rows = []
    for index in range(reps):
        rise = peak - abs(index - peak)
        rows.append(int(_whole(Decimal(first) + step * Decimal(rise))))
    return rows


def _line(rows: list[dict], rest: int) -> str:
    same = len({row["meters"] for row in rows}) == 1 and len({row["seconds"] for row in rows}) == 1
    if same:
        row = rows[0]
        body = f"{len(rows)} × {row['meters']} m @ {_rep_time_text(row['seconds'])}"
    else:
        parts = [
            f"{row['meters']} m @ {_rep_time_text(row['seconds'])}" for row in rows
        ]
        body = ", ".join(parts)
    if rest <= 0:
        return body
    return f"{body}, {rest} s rest"


def _rep_time_text(seconds: Decimal) -> str:
    """A short rep stays in seconds. A long rep is a clock time."""
    if seconds >= 60:
        return _clock(seconds)
    return f"{_seconds_text(seconds)} s"


def _tolerance_text(rows: list[dict]) -> str:
    same = len({(row["low"], row["high"]) for row in rows}) == 1
    if same:
        row = rows[0]
        return f"{_seconds_text(row['low'])}-{_seconds_text(row['high'])} s"
    parts = []
    seen: set[int] = set()
    for row in rows:
        meters = row["meters"]
        if meters in seen:
            continue
        seen.add(meters)
        parts.append(
            f"{meters} m {_seconds_text(row['low'])}-{_seconds_text(row['high'])} s"
        )
    return "; ".join(parts)


def _block(rows: list[dict], rest: int) -> Decimal:
    total = sum((row["seconds"] for row in rows), Decimal(0))
    if len(rows) > 1 and rest > 0:
        total += Decimal(rest) * Decimal(len(rows) - 1)
    return total


def _tolerance_half(seconds: Decimal) -> Decimal:
    half = seconds * TOLERANCE_SHARE
    if half < TOLERANCE_FLOOR:
        half = TOLERANCE_FLOOR
    return _tenths(half)


def _tenths(value: Decimal) -> Decimal:
    quiet = value.quantize(_SIX, rounding=ROUND_HALF_UP)
    return quiet.quantize(_TENTH, rounding=ROUND_HALF_UP)


def _whole(value: Decimal) -> Decimal:
    return value.quantize(Decimal(1), rounding=ROUND_HALF_UP)


def _seconds_text(value: Decimal) -> str:
    return f"{value:.1f}"


def _clock(seconds: Decimal) -> str:
    if seconds < 60:
        return f"{_seconds_text(seconds)} s"
    whole = int(seconds)
    fraction = seconds - Decimal(whole)
    # The tenths already on the block stay visible when they are not zero.
    minutes = whole // 60
    remain = Decimal(whole % 60) + fraction
    return f"{minutes}:{remain:04.1f}"


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return None
    try:
        number = Decimal(str(value))
    except (ArithmeticError, ValueError):
        return None
    if not number.is_finite():
        return None
    return number


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if _ISO_DAY.fullmatch(text):
            return date.fromisoformat(text)
    raise ValueError("date is not a calendar date")
