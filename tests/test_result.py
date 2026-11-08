# test_result.py — quality-day result within 3% of pace or distance.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.season import adapt, sequence
from ui.result import filled_times, goal_seconds, judge, parse_result, rep_count, result_box_count

START = date(2026, 4, 19)
GOAL_DAY = date(2027, 3, 19)
GOAL = goal_seconds("1:55.0")
REP = "se_400_r90_x6"


def test_band() -> None:
    """57.5s is 400 m at 1:55.0. The 3% line is still on track."""
    if GOAL != 115:
        raise AssertionError(f"goal seconds are {GOAL}")
    target = 115 / 800 * 400
    if judge(REP, str(target), GOAL)["mark"] != "on_track":
        raise AssertionError("the target time is not on track")
    if judge(REP, str(target * 1.03), GOAL)["mark"] != "on_track":
        raise AssertionError("3% slow is outside on track")
    if judge(REP, str(target * 0.97), GOAL)["mark"] != "on_track":
        raise AssertionError("3% fast is outside on track")
    slow = judge(REP, "60, 60, 60", GOAL)
    fast = judge(REP, "54", GOAL)
    if slow["mark"] != "not_hitting" or fast["mark"] != "smashing":
        raise AssertionError(f"times mapped to {slow['mark']} and {fast['mark']}")
    if slow["numbers"] != [60, 60, 60] or fast["numbers"] != [54]:
        raise AssertionError("raw times were not kept")
    average = judge(REP, "avg 57.5", GOAL)
    if average["mark"] != "on_track" or average["numbers"] != [57.5]:
        raise AssertionError("an average was not a single time")
    clock = judge(REP, "0:57.5, 1:00", GOAL)
    if clock["numbers"] != [57.5, 60] or clock["mark"] != "on_track":
        raise AssertionError(f"clock times became {clock}")


def test_distance() -> None:
    same = judge(REP, "400m", GOAL)
    short = judge(REP, "380 m", GOAL)
    long = judge(REP, "1.2km", None)
    edge = judge(REP, "412m", GOAL)
    if same["mark"] != "on_track" or same["numbers"] != [400]:
        raise AssertionError("the rep distance is not on track")
    if short["mark"] != "not_hitting":
        raise AssertionError("a short rep is not not_hitting")
    if edge["mark"] != "on_track":
        raise AssertionError("3% long is outside on track")
    if long["mark"] != "smashing" or long["numbers"] != [1200]:
        raise AssertionError("a longer distance was not smashing")
    paired = judge(REP, "400m in 54", GOAL)
    if paired["numbers"] != [400, 54] or paired["mark"] != "smashing":
        raise AssertionError(f"distance and time became {paired}")
    counted = judge(REP, "6 x 57.5, 58", GOAL)
    if counted["numbers"] != [57.5, 58] or counted["mark"] != "on_track":
        raise AssertionError(f"a rep count stayed in the times: {counted}")


def test_ignored() -> None:
    for text in ("", "   ", "fast", "0", "-5", "400m 500m", "about 57", "21some"):
        if parse_result(text) is not None or judge(REP, text, GOAL) is not None:
            raise AssertionError(f"{text!r} was not ignored")
    if judge("not-a-template", "57.5", GOAL) is not None:
        raise AssertionError("a template without a rep length was judged")
    if judge(REP, "57.5", None) is not None:
        raise AssertionError("pace was judged without a goal time")
    if judge(REP, "400 meters", None)["mark"] != "on_track":
        raise AssertionError("distance still needs a goal time")


def test_rep_boxes() -> None:
    """The id's rep count is the box count. A continuous effort stays one."""
    if rep_count(REP) != 6 or result_box_count(REP) != 6:
        raise AssertionError("6 × 400 did not ask for six boxes")
    if rep_count("mv_60_r120_x10") != 10 or result_box_count("an_400_r45_x6") != 6:
        raise AssertionError("the rep count was not read from the id")
    if rep_count("rr_800_r0_x1") != 1 or result_box_count("rr_800_r0_x1") != 1:
        raise AssertionError("the race did not stay one box")
    if result_box_count("aer_12000_r0_x1") != 1 or result_box_count("not-a-template") != 1:
        raise AssertionError("continuous work did not stay one box")
    if rep_count(None) is not None or rep_count("se_py_200to400_r90_x5") is not None:
        raise AssertionError("an id without a rep count was counted")


def test_empty_boxes_are_ignored() -> None:
    """Only filled times reach the ±3% rule. The band itself stays put."""
    entered = filled_times([60, None, 60, "", 0])
    direct = judge(REP, "60, 60", GOAL)
    from_boxes = judge(REP, entered, GOAL)
    if entered != "60, 60" or from_boxes != direct:
        raise AssertionError(f"empty boxes changed the mark: {entered} {from_boxes}")
    if filled_times([None, None]) != "" or judge(REP, filled_times([]), GOAL) is not None:
        raise AssertionError("an empty set was judged")
    one = filled_times([54.0])
    if one != "54" or judge(REP, one, GOAL)["mark"] != "smashing":
        raise AssertionError("one filled rep was not mapped")


def test_two_results_adapt_once() -> None:
    """The week is judged once. A second call on the shifted plan would move again."""
    plan = sequence("2:02.9", START, "1:55.0", GOAL_DAY)
    once = adapt(plan, 1, "smashing")
    twice = adapt(once, 1, "smashing")
    # Week 2 cannot become phase 3 yet: the 9.5 km floor is still more than
    # 10% above week 1. A later week advances once the long run can support it.
    if _ids(once, 2) != _ids(twice, 2):
        raise AssertionError("week 2 advanced through the 10% rule")
    if not any(_ids(once, week) != _ids(twice, week) for week in range(3, 48)):
        raise AssertionError("a second adapt on the same week did not move again")
    if _ids(once, 1) != _ids(plan, 1):
        raise AssertionError("adapt changed the judged week")
    held = adapt(plan, 1, "not_hitting")
    combined = adapt(plan, 1, ["not_hitting", "smashing"])
    if _ids(combined, 11) != _ids(held, 11) or _ids(combined, 2) != _ids(plan, 2):
        raise AssertionError("not_hitting did not win over smashing")
    same = adapt(plan, 1, "on_track")
    if _ids(same, 2) != _ids(plan, 2):
        raise AssertionError("on_track changed a future week")


def _ids(plan: dict, week: int) -> list[str]:
    return [
        session["template_id"]
        for session in plan["sessions"]
        if session["week_number"] == week
    ]


if __name__ == "__main__":
    test_band()
    test_distance()
    test_ignored()
    test_rep_boxes()
    test_empty_boxes_are_ignored()
    test_two_results_adapt_once()
    print("result ok")
