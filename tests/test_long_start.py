# test_long_start.py — usual long run, the 20 km ladder, and Saturday's build.

"""Week 1 uses Chase's start rule. Later Saturdays step 500 m up to 20 km.

The 10% distance cap counts easy and long running. A Saturday drops only
on an easy week. The same inputs build the same plan twice.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.season import (
    _LONG_FLOOR,
    _LONG_MAX,
    _MILE_M,
    _SIX_MILES_M,
    adapt,
    long_run_start_meters,
    sequence,
    usual_long_clamp,
    work_meters,
)
from services.season_commit import plan_for_adapt
from ui.auto_adapt import _strip

START = date(2026, 12, 6)


def _weeks(plan: dict) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}
    for session in plan["sessions"]:
        grouped.setdefault(session["week_number"], []).append(session)
    return grouped


def _phase(week: list[dict]) -> int:
    for session in week:
        for code in session["reason_codes"]:
            if code.startswith("phase_") and code[-1].isdigit():
                return int(code[-1])
    raise AssertionError("a week has no phase")


def _saturday_meters(week: list[dict]) -> int | None:
    for session in week:
        if session["day_of_week"] != "Saturday":
            continue
        template = session["template_id"]
        if template.startswith("aer_"):
            return work_meters(template)
        return None
    return None


def _assert_saturdays(plan: dict) -> None:
    previous = None
    for number in range(1, plan["season_length_weeks"] + 1):
        week = _weeks(plan).get(number, [])
        if not week:
            continue
        phase = _phase(week)
        meters = _saturday_meters(week)
        easy = any("extra_easy_week" in session["reason_codes"] for session in week)
        if phase == 8:
            if meters is not None:
                raise AssertionError(f"taper week {number} kept a long run")
            continue
        if meters is None:
            raise AssertionError(f"week {number} has no Saturday long run")
        if meters < _LONG_FLOOR or meters > _LONG_MAX or (meters - _LONG_FLOOR) % 500:
            raise AssertionError(f"week {number} Saturday is {meters} m")
        if previous is not None:
            if easy:
                if meters not in (previous, previous - 500) or meters < _LONG_FLOOR:
                    raise AssertionError(f"easy week {number} moved from {previous} to {meters}")
            elif meters < previous:
                raise AssertionError(f"week {number} Saturday dropped from {previous} to {meters}")
            elif meters > previous + 500:
                raise AssertionError(f"week {number} Saturday jumped from {previous} to {meters}")
            elif previous < _LONG_MAX and meters != previous + 500:
                raise AssertionError(f"week {number} held at {meters} before 20 km")
        previous = meters


def test_chase_start_rung() -> None:
    """Six miles or more starts a mile shorter. Under that, it starts at the usual."""
    if long_run_start_meters(None) != 9500 or usual_long_clamp(None) is not None:
        raise AssertionError("a missing usual did not start at 9.5 km")
    cases = (
        (5000, 5000, None),
        (5400, 5000, None),
        (8000, 8000, None),
        (9000, 9000, None),
        (9500, 9500, None),
        (9655, 9500, None),
        (_SIX_MILES_M, 8000, None),
        (10_000, 8000, None),
        (11_109, 9500, None),
        (12_000, 10_000, None),
        (15_000, 13_000, None),
        (20_000, 18_000, None),
        (21_609, 20_000, None),
        (25_000, 20_000, "high"),
    )
    for usual, rung, clamp in cases:
        found = long_run_start_meters(usual)
        target = usual - _MILE_M if usual >= _SIX_MILES_M else usual
        if found != rung or usual_long_clamp(usual) != clamp:
            raise AssertionError(f"{usual} m -> {found} clamp {usual_long_clamp(usual)}")
        if found > target:
            raise AssertionError(f"{usual} m rung {found} exceeds the target {target}")


def test_week_one_uses_the_rung_including_a_midweek_start() -> None:
    goal = START + timedelta(days=21 * 7)
    plan = sequence("2:10.0", START, "2:00.0", goal, long_start_m=12000)
    if plan["long_run_start_m"] != 12000:
        raise AssertionError(plan["long_run_start_m"])
    opener = _weeks(plan)[1]
    if _saturday_meters(opener) != 12000:
        raise AssertionError(_saturday_meters(opener))
    wednesday = date(2026, 12, 9)
    partial = sequence("2:10.0", wednesday, "2:00.0", goal, long_start_m=12000)
    if _saturday_meters(_weeks(partial)[1]) != 12000:
        raise AssertionError("a mid-week start changed the first Saturday")
    _assert_saturdays(plan)
    _assert_saturdays(partial)


def test_saturday_never_drops_outside_an_easy_week() -> None:
    """Season lengths 1–52, every start weekday, and several usual long runs."""
    usuals = (None, 5000, 6000, 8000, 9000, 9500, 12000, 15000, 18000, 20000)
    for weeks in range(1, 53):
        for weekday in range(7):
            start = START + timedelta(days=weekday)
            goal = start + timedelta(days=weeks * 7)
            for usual in usuals:
                rung = long_run_start_meters(usual)
                plan = sequence("2:10.0", start, "2:00.0", goal, long_start_m=rung)
                if plan["long_run_start_m"] != rung:
                    raise AssertionError((weeks, weekday, usual, plan["long_run_start_m"]))
                _assert_saturdays(plan)
                again = json.dumps(plan, sort_keys=True)
                if again != json.dumps(
                    sequence("2:10.0", start, "2:00.0", goal, long_start_m=rung),
                    sort_keys=True,
                ):
                    raise AssertionError("the same inputs built two plans")


def test_an_easy_week_may_drop_one_rung() -> None:
    """Repeated not-hitting reaches an easy week. That Saturday may step down once."""
    goal = START + timedelta(days=12 * 7)
    plan = sequence("2:10.0", START, "2:00.0", goal, long_start_m=13000)
    easy = None
    for _turn in range(8):
        plan = adapt(plan, 1, "not_hitting")
        for number, week in _weeks(plan).items():
            if any("extra_easy_week" in session["reason_codes"] for session in week):
                easy = number
                break
        if easy is not None:
            break
    if easy is None:
        raise AssertionError("no easy week was planned")
    _assert_saturdays(plan)
    if plan["long_run_start_m"] != 13000:
        raise AssertionError("adapt dropped the stored start rung")


def test_adapt_strip_and_replay_keep_the_start_rung() -> None:
    goal = START + timedelta(days=16 * 7)
    plan = sequence("2:10.0", START, "2:00.0", goal, long_start_m=15000)
    moved = adapt(plan, 2, "not_hitting")
    if moved["long_run_start_m"] != 15000:
        raise AssertionError(moved.get("long_run_start_m"))
    if plan_for_adapt(plan)["long_run_start_m"] != 15000:
        raise AssertionError("plan_for_adapt dropped the start rung")
    if _strip(plan)["long_run_start_m"] != 15000:
        raise AssertionError("_strip dropped the start rung")
    held = adapt(plan, 2, "on_track")
    if held["long_run_start_m"] != 15000 or held["sessions"] != plan["sessions"]:
        raise AssertionError("on track changed the stored start")
    replay = sequence("2:10.0", START, "2:00.0", goal, long_start_m=plan["long_run_start_m"])
    if replay["sessions"] != plan["sessions"]:
        raise AssertionError("replay did not rebuild the same plan")
