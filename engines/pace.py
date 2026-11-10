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
    A dn id (a descending ladder) steps evenly from the first distance
    down to the last, one step per rep. Three reps from 800 to 400 are
    800, 600, 400.
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

Pace display
    A continuous easy, aerobic, or long run is shown as pace, never as a
    total clock time. One mile is 1609.344 meters. The same distance and
    time always format the same way. Rep workouts keep the per-rep target.

Athlete easy pace
    When an easy pace is supplied, a continuous aer run uses that pace
    for its target. The line is the pace they entered, such as
    7:25 per mile, not a finish time and not 1.55 times the 800.
    Quality families ignore it and keep their fractions. A call that
    does not supply an easy pace still uses the aer fraction. That
    fraction is not the athlete's pace.
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

# Statute mile. Pace conversion uses this exact length.
METERS_PER_MILE = Decimal("1609.344")
METERS_PER_KM = Decimal(1000)
PACE_MILE = "mi"
PACE_KM = "km"
# Easy, aerobic, and long runs are one effort. Other families are reps.
CONTINUOUS_FAMILIES = frozenset({"aer"})
SPEED_FAMILIES = frozenset({"spd", "mv"})

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
_EASY = re.compile(r"^(\d{1,2}):([0-5]\d)$")
_EASY_TRAIL = re.compile(r"^\d{1,2}:[0-5]\d\.0+$")
_ID = re.compile(
    r"^(?P<family>[a-z]+)_(?:(?P<shape>py|up|dn)_)?(?P<start>\d+)"
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
    easy_pace: object = None,
    easy_unit: object = None,
) -> Decimal:
    """Share applied to the scheduled 800. 1 means the logs have not moved it.

    Only logs dated before `on` count. Each ISO week spends at most WEEKLY_CAP.
    A saved easy pace is the target for a continuous aer log. Other families
    stay on their fractions.
    """
    factor = Decimal(1)
    spent: dict[tuple[int, int], Decimal] = {}
    ordered = _ordered_logs(logs)
    for entry in ordered:
        if entry.on >= on:
            continue
        target = _log_target(
            entry,
            current,
            goal,
            start,
            goal_day,
            factor,
            easy_pace=easy_pace,
            easy_unit=easy_unit,
        )
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
    easy_pace: object = None,
    easy_unit: object = None,
) -> dict | None:
    """The line, the tolerance, and the block for one prescribed workout.

    None when the id is not a frozen rep recipe. The dict is plain numbers
    and strings so a page can print it without another rule.

    easy_pace, when it is a pace such as 7:25, replaces the aer fraction
    for a continuous easy or long run. The line is that pace. Quality
    families keep their fractions. An empty pace marks that continuous
    run unset so the aer fraction is not presented as the athlete's pace.
    """
    parsed = _parse_id(template_id)
    if parsed is None:
        return None
    current = parse_mark(current_mark)
    goal = parse_mark(goal_mark)
    start_day = _as_date(start)
    goal_day = _as_date(goal_date)
    day = _as_date(on)
    factor = correction_factor(
        current,
        goal,
        start_day,
        goal_day,
        day,
        logs,
        easy_pace=easy_pace,
        easy_unit=easy_unit,
    )
    scheduled = scheduled_seconds(current, goal, start_day, goal_day, day)
    effective = scheduled * factor
    family, shape, first, last, rest, reps = parsed
    distances = _distances(shape, first, last, reps)
    fraction = FAMILY_FRACTION[family]
    rate = _easy_rate(family, shape, reps, easy_pace, easy_unit)
    unset = (
        easy_pace is not None
        and family in CONTINUOUS_FAMILIES
        and shape == ""
        and reps == 1
        and rate is None
    )
    span = _easy_span(easy_unit)
    rows = []
    for meters in distances:
        if rate is not None:
            raw = Decimal(meters) * rate / span
        else:
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
    result = {
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
    if rate is not None:
        phrase = easy_pace_phrase(easy_pace, easy_unit)
        result["easy_pace"] = phrase
        result["line"] = phrase
    elif unset:
        result["easy_unset"] = True
        result["line"] = ""
    return result


def project_800(
    *,
    current_mark: object,
    goal_mark: object,
    start: date,
    goal_date: date,
    on: date,
    logs: list[PaceLog] | tuple[PaceLog, ...] | None = None,
    easy_pace: object = None,
    easy_unit: object = None,
) -> dict:
    """Scheduled 800, the log-corrected 800, and on track / ahead / behind."""
    current = parse_mark(current_mark)
    goal = parse_mark(goal_mark)
    start_day = _as_date(start)
    goal_day = _as_date(goal_date)
    day = _as_date(on)
    factor = correction_factor(
        current,
        goal,
        start_day,
        goal_day,
        day,
        logs,
        easy_pace=easy_pace,
        easy_unit=easy_unit,
    )
    scheduled = scheduled_seconds(current, goal, start_day, goal_day, day)
    return {
        "scheduled_seconds": scheduled,
        "effective_seconds": scheduled * factor,
        "factor": factor,
        "status": status_for(factor),
    }


def pace_unit(value: object) -> str:
    """mi or km. Anything else is per mile."""
    if isinstance(value, str):
        text = value.strip().lower().replace("_", " ")
        if text in ("km", "per km", "kilometer", "kilometre", "/km", "per kilometer"):
            return PACE_KM
    return PACE_MILE


def parse_easy_pace(value: object) -> Decimal | None:
    """Seconds in an easy pace such as 7:25. None when it is not one.

    Minutes and seconds. A trailing .0 is ignored. Faster than 1:00 or
    slower than 30:00 is not a pace this screen stores.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if _EASY_TRAIL.fullmatch(text):
        text = text.split(".", 1)[0]
    found = _EASY.fullmatch(text)
    if found is None:
        return None
    minutes = int(found.group(1))
    seconds = int(found.group(2))
    total = minutes * 60 + seconds
    if total < 60 or total > 30 * 60:
        return None
    return Decimal(total)


def canonical_easy_pace(value: object) -> str | None:
    """7:25, or None when parse_easy_pace would refuse it."""
    seconds = parse_easy_pace(value)
    if seconds is None:
        return None
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def easy_pace_phrase(pace: object, unit: object = PACE_MILE) -> str:
    """7:25 per mile, or 4:36 per kilometer. Blank when the pace is not saved."""
    text = canonical_easy_pace(pace)
    if text is None:
        return ""
    label = "per mile" if pace_unit(unit) == PACE_MILE else "per kilometer"
    return f"{text} {label}"


def workout_recipe(template_id: object) -> dict | None:
    """Distances, rest, and whether this id is one continuous run.

    None when the id is not a frozen rep recipe. The same id always
    returns the same recipe.
    """
    parsed = _parse_id(template_id)
    if parsed is None:
        return None
    family, shape, first, last, rest, reps = parsed
    distances = _distances(shape, first, last, reps)
    continuous = family in CONTINUOUS_FAMILIES and shape == "" and reps == 1
    return {
        "family": family,
        "shape": shape,
        "rest_seconds": rest,
        "reps": reps,
        "distances": distances,
        "continuous": continuous,
        "speed": family in SPEED_FAMILIES,
        "template_id": template_id.strip() if isinstance(template_id, str) else "",
    }


def pace_seconds(meters: object, seconds: object, unit: object = PACE_MILE) -> Decimal | None:
    """Seconds per mile or per kilometer. None when the effort is unusable.

    Per mile multiplies by 1609.344 / meters. The division is exact Decimal.
    """
    distance = _decimal(meters)
    elapsed = _decimal(seconds)
    if distance is None or elapsed is None or distance <= 0 or elapsed <= 0:
        return None
    span = METERS_PER_MILE if pace_unit(unit) == PACE_MILE else METERS_PER_KM
    return elapsed * span / distance


def format_pace(meters: object, seconds: object, unit: object = PACE_MILE) -> str:
    """A pace such as 6:34 /mi. Blank when the effort is unusable.

    Rounded to the nearest second, half up.
    """
    found = pace_seconds(meters, seconds, unit)
    if found is None:
        return ""
    return _pace_clock(found, pace_unit(unit))


def effort_pace(run: object, unit: object = PACE_MILE) -> str:
    """Pace for one logged run. Blank when the run has no distance and time."""
    if not isinstance(run, dict):
        return ""
    meters, seconds = _effort(run)
    if meters is None or seconds is None:
        return ""
    return format_pace(meters, seconds, unit)


def format_span(meters: object, unit: object = PACE_MILE) -> str:
    """A distance in the pace unit, to one tenth. 0 stays 0.0."""
    amount = _decimal(meters)
    chosen = pace_unit(unit)
    if amount is None or amount < 0:
        amount = Decimal(0)
    span = METERS_PER_MILE if chosen == PACE_MILE else METERS_PER_KM
    shown = (amount / span).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{shown} {chosen}"


def rep_time_text(seconds: object) -> str:
    """A rep time to a tenth of a second, or a clock when it is a minute or more."""
    number = _decimal(seconds)
    if number is None or number <= 0:
        return ""
    return _rep_time_text(_tenths(number))


def display_workout(bundle: dict | None, run: object, unit: object = PACE_MILE) -> dict:
    """Planned and actual lines for one run.

    A continuous run is pace in the chosen unit. A rep workout keeps the
    per-rep target and the rest. Actual rep times come from the laps when
    those laps are the prescribed reps. The same inputs always match.
    """
    chosen = pace_unit(unit)
    template = ""
    if isinstance(run, dict):
        template = str(run.get("template_id") or "")
    recipe = workout_recipe(template)
    continuous = bool(recipe and recipe["continuous"])
    speed = bool(recipe and recipe["speed"])
    if isinstance(bundle, dict) and bundle.get("reps") and continuous:
        return _continuous_display(bundle, run if isinstance(run, dict) else {}, chosen)
    if isinstance(bundle, dict) and bundle.get("reps"):
        return _rep_display(bundle, run if isinstance(run, dict) else {}, speed)
    actual = format_pace(*_effort(run if isinstance(run, dict) else {}), chosen)
    detail = f"Actual {actual}" if actual else "Actual —"
    return {
        "planned": "—",
        "actual": actual or "—",
        "detail": detail,
        "laps": [],
        "continuous": False,
        "speed": False,
    }


def _continuous_display(bundle: dict, run: dict, unit: str) -> dict:
    meters, seconds = _effort(run)
    actual = format_pace(meters, seconds, unit) if meters is not None else ""
    if bundle.get("easy_unset") is True:
        detail = "Set your easy pace before this run."
        if actual:
            detail = f"{detail} Actual {actual}"
        return {
            "planned": "Set your easy pace",
            "actual": actual or "—",
            "detail": detail,
            "laps": [],
            "continuous": True,
            "speed": False,
        }
    phrase = bundle.get("easy_pace")
    if isinstance(phrase, str) and phrase.strip():
        detail = f"Run at {phrase}"
        if actual:
            detail = f"{detail} · Actual {actual}"
        return {
            "planned": phrase,
            "actual": actual or "—",
            "detail": detail,
            "laps": [],
            "continuous": True,
            "speed": False,
        }
    row = bundle["reps"][0]
    target = format_pace(row["meters"], row["seconds"], unit)
    if not target:
        target = "—"
    detail = f"Target {target} · Actual {actual or '—'}"
    return {
        "planned": target,
        "actual": actual or "—",
        "detail": detail,
        "laps": [],
        "continuous": True,
        "speed": False,
    }


def _rep_display(bundle: dict, run: dict, speed: bool) -> dict:
    reps = bundle["reps"]
    rest = int(bundle.get("rest_seconds") or 0)
    distances = [int(row["meters"]) for row in reps]
    times = _lap_seconds(run, distances)
    same = len({row["seconds"] for row in reps}) == 1 and len(set(distances)) == 1
    if same:
        planned = f"Target {rep_time_text(reps[0]['seconds'])}"
        if rest > 0:
            planned = f"{planned} · {rest} s rest"
    else:
        planned = str(bundle.get("line") or "—")
    actuals = [rep_time_text(item) for item in times]
    actuals = [item for item in actuals if item]
    actual = ", ".join(actuals) if actuals else "—"
    detail = planned if not actuals else f"{planned} · Actual {actual}"
    laps = []
    if speed and actuals:
        laps = _speed_laps(reps, times, rest)
    return {
        "planned": planned,
        "actual": actual,
        "detail": detail,
        "laps": laps,
        "continuous": False,
        "speed": speed,
    }


def _speed_laps(reps: list, times: list, rest: int) -> list[dict]:
    rows = []
    count = max(len(reps), len(times))
    for index in range(count):
        target = rep_time_text(reps[index]["seconds"]) if index < len(reps) else "—"
        actual = rep_time_text(times[index]) if index < len(times) else "—"
        between = index < count - 1 and rest > 0
        rows.append(
            {
                "rep": index + 1,
                "target": target or "—",
                "actual": actual or "—",
                "rest": f"{rest} s" if between else "—",
            }
        )
    return rows


def _effort(run: dict) -> tuple[Decimal | None, Decimal | None]:
    """Total meters and seconds. Laps win. A stored pace fills a missing time."""
    laps = run.get("laps") if isinstance(run.get("laps"), list) else []
    meters = Decimal(0)
    seconds = Decimal(0)
    used = False
    for lap in laps:
        if not isinstance(lap, dict):
            continue
        distance = _lap_meters(lap)
        elapsed = _lap_elapsed(lap)
        if distance is None or elapsed is None or distance <= 0 or elapsed <= 0:
            continue
        meters += distance
        seconds += elapsed
        used = True
    if used:
        return meters, seconds
    distance = _decimal(run.get("distance_m"))
    if distance is None:
        distance = _decimal(run.get("distance"))
    elapsed = _decimal(run.get("elapsed_seconds"))
    if elapsed is None or elapsed <= 0:
        elapsed = _decimal(run.get("moving_seconds"))
    pace = _decimal(run.get("pace_s_per_km"))
    if pace is not None and pace > 0 and distance is not None and distance > 0:
        elapsed = pace * distance / METERS_PER_KM
    if distance is None or elapsed is None or distance <= 0 or elapsed <= 0:
        return None, None
    return distance, elapsed


def _lap_seconds(run: dict, distances: list[int]) -> list[Decimal]:
    """One time per prescribed rep. A warm-up lap is left out when it does not match."""
    laps = run.get("laps") if isinstance(run.get("laps"), list) else []
    parsed: list[tuple[Decimal | None, Decimal]] = []
    for lap in laps:
        if not isinstance(lap, dict):
            continue
        elapsed = _lap_elapsed(lap)
        if elapsed is None or elapsed <= 0:
            continue
        parsed.append((_lap_meters(lap), elapsed))
    if not parsed:
        reps = run.get("reps")
        if isinstance(reps, list):
            for item in reps:
                number = _decimal(item)
                if number is not None and number > 0:
                    parsed.append((None, number))
    if not parsed:
        return []
    if len(parsed) == len(distances):
        return [elapsed for _meters, elapsed in parsed]
    if len(distances) == 1 and len(parsed) == 1:
        return [parsed[0][1]]
    chosen: list[Decimal] = []
    cursor = 0
    for target in distances:
        goal = Decimal(target)
        matched = None
        while cursor < len(parsed):
            distance, elapsed = parsed[cursor]
            cursor += 1
            if distance is None or goal <= 0:
                matched = elapsed
                break
            gap = abs(distance - goal) / goal
            if gap <= Decimal("0.2"):
                matched = elapsed
                break
        if matched is None:
            break
        chosen.append(matched)
    if len(chosen) == len(distances):
        return chosen
    if not distances:
        return [elapsed for _meters, elapsed in parsed]
    return []


def _lap_meters(lap: dict) -> Decimal | None:
    for key in ("distance_m", "distance"):
        number = _decimal(lap.get(key))
        if number is not None:
            return number
    return None


def _lap_elapsed(lap: dict) -> Decimal | None:
    for key in ("moving_seconds", "moving_time", "elapsed_seconds", "elapsed_time"):
        number = _decimal(lap.get(key))
        if number is not None and number > 0:
            return number
    return None


def _pace_clock(seconds: Decimal, unit: str) -> str:
    whole = seconds.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    total = int(whole)
    if total < 0:
        total = 0
    return f"{total // 60}:{total % 60:02d} /{unit}"


def _easy_rate(
    family: str,
    shape: str,
    reps: int,
    easy_pace: object,
    easy_unit: object,
) -> Decimal | None:
    """Seconds per mile or per kilometer for a continuous aer run.

    None for every quality family, and when the athlete has not saved a pace.
    """
    if family not in CONTINUOUS_FAMILIES or shape != "" or reps != 1:
        return None
    return parse_easy_pace(easy_pace)


def _easy_span(unit: object) -> Decimal:
    return METERS_PER_MILE if pace_unit(unit) == PACE_MILE else METERS_PER_KM


def _log_target(
    entry: PaceLog,
    current: Decimal,
    goal: Decimal,
    start: date,
    goal_day: date,
    factor: Decimal,
    easy_pace: object = None,
    easy_unit: object = None,
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
    rate = _easy_rate(family, shape, reps, easy_pace, easy_unit)
    if rate is not None:
        span = _easy_span(easy_unit)
        total = sum(
            (_tenths(Decimal(meters) * rate / span) for meters in distances),
            Decimal(0),
        )
        return total / Decimal(len(distances))
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
    shape = found.group("shape") or ""
    if first <= 0 or rest < 0 or reps <= 0:
        return None
    if shape and end is None:
        return None
    if shape == "dn":
        if last >= first:
            return None
    elif last < first:
        return None
    return family, shape, first, last, rest, reps


def _distances(shape: str, first: int, last: int, reps: int) -> list[int]:
    if shape in ("up", "dn"):
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


def average_rep_text(reps: object) -> str:
    """The mean of the prescribed rep times. Blank when there are none.

    The seconds come from workout_times. This does not pick a new fraction.
    """
    if not isinstance(reps, list) or not reps:
        return ""
    total = Decimal(0)
    count = 0
    for row in reps:
        if not isinstance(row, dict):
            continue
        seconds = row.get("seconds")
        number = seconds if isinstance(seconds, Decimal) else _decimal(seconds)
        if number is None or number <= 0:
            continue
        total += number
        count += 1
    if count == 0:
        return ""
    return _rep_time_text(_tenths(total / Decimal(count)))


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
