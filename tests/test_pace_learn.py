# test_pace_learn.py — pace ranges from time spent in a zone.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.heart_rate import zones_for
from engines.heart_targets import CREATING_NOTE, heart_overlay
from engines.pace import workout_times
from engines.pace_learn import learn_ranges

def _run(bpm: int, meters: float, seconds: int) -> dict:
    return {
        "distance_m": meters,
        "moving_seconds": seconds,
        "stream": {"time": [0, seconds], "hr": [bpm, bpm]},
    }


def _zones(resting: int = 60, maximum: int = 180) -> list:
    return zones_for(resting, maximum)["zones"]


def test_six_zone_2_runs_become_a_pace_range_and_five_do_not() -> None:
    zones = _zones()
    # 138 bpm is Zone 2 for 60/180. Pace changes with the distance.
    short = [_run(138, 2000, 560 + index * 10) for index in range(5)]
    early = learn_ranges(short, zones, "mi")
    if early[2]["ready"] or early[2]["count"] != 5 or early[3]["count"] or early[4]["count"]:
        raise AssertionError(early)
    six = short + [_run(138, 2000, 620)]
    ready = learn_ranges(six, zones, "mi")
    if not ready[2]["ready"] or ready[2]["count"] != 6:
        raise AssertionError(ready)
    if ready[2]["low"] >= ready[2]["high"]:
        raise AssertionError(ready[2])
    # A run with no stream does not count, and a fast run is not Zone 2.
    mixed = six + [{"distance_m": 2000, "moving_seconds": 500}, _run(170, 2000, 400)]
    again = learn_ranges(mixed, zones, "mi")
    if again[2]["count"] != 6 or again[4]["count"] != 0:
        raise AssertionError(again)
    # 170 is Zone 5 for this profile (168–180), so it teaches no pace zone.
    tempo = learn_ranges([_run(150, 2000, 500)] * 6, zones, "mi")
    if tempo[3]["count"] != 6 or tempo[2]["count"]:
        raise AssertionError(tempo)


def test_new_zones_recount_the_same_samples() -> None:
    sample = [_run(138, 2000, 600)] * 6
    first = learn_ranges(sample, _zones(60, 180), "mi")
    # A much lower max pulls 138 bpm out of Zone 2.
    second = learn_ranges(sample, _zones(40, 150), "mi")
    if not first[2]["ready"] or second[2]["ready"] or second[2]["count"] == 6:
        raise AssertionError((first[2], second[2]))


def test_a_trusted_range_replaces_the_provisional_easy_pace() -> None:
    profile = zones_for(60, 180)
    profile["no_monitor"] = False
    times = workout_times(
        "aer_8000_r0_x1",
        current_mark="2:05.0",
        goal_mark="1:55.0",
        start=date(2026, 11, 1),
        goal_date=date(2027, 4, 1),
        on=date(2026, 11, 21),
        easy_pace="7:25",
        easy_unit="mi",
    )
    creating = heart_overlay("aer_8000_r0_x1", times, profile, "mi")
    if creating is None or creating["pace_note"] != CREATING_NOTE:
        raise AssertionError(creating)
    learned = {2: {"count": 6, "ready": True, "low": 430, "high": 470}}
    trusted = heart_overlay("aer_8000_r0_x1", times, profile, "mi", learned)
    if trusted is None or trusted["estimate"] != "ready":
        raise AssertionError(trusted)
    if trusted["pace_line"] != "7:10\u20137:50 per mile":
        raise AssertionError(trusted["pace_line"])
    if trusted["pace_note"] != "Learned from 6 Zone 2 runs.":
        raise AssertionError(trusted["pace_note"])
    partial = {2: {"count": 4, "ready": False, "low": None, "high": None}}
    still = heart_overlay("aer_8000_r0_x1", times, profile, "mi", partial)
    if still is None or not still["pace_note"].startswith(CREATING_NOTE) or "4 of 6" not in still["pace_note"]:
        raise AssertionError(still)
