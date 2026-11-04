# test_pace.py — split math and the weekly correction. New tests only.

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.pace import (
    FAMILY_FRACTION,
    WEEKLY_CAP,
    PaceLog,
    parse_mark,
    project_800,
    workout_times,
)

START = date(2026, 1, 1)
GOAL_DAY = date(2026, 1, 11)
MID = date(2026, 1, 6)
CURRENT = "2:00.0"
GOAL = "1:50.0"


def _project(on: date, logs=None):
    return project_800(
        current_mark=CURRENT,
        goal_mark=GOAL,
        start=START,
        goal_date=GOAL_DAY,
        on=on,
        logs=logs,
    )


def _workout(template: str, on: date, logs=None):
    return workout_times(
        template,
        current_mark=CURRENT,
        goal_mark=GOAL,
        start=START,
        goal_date=GOAL_DAY,
        on=on,
        logs=logs,
    )


def test_marks_and_a_straight_line_with_no_logs() -> None:
    """No logs stay on the line from the current 800 to the goal."""
    if parse_mark("2:02.9") != Decimal("122.9"):
        raise AssertionError(parse_mark("2:02.9"))
    if parse_mark("1:55.0") != Decimal("115.0"):
        raise AssertionError(parse_mark("1:55.0"))
    if parse_mark("1:55") != Decimal("115"):
        raise AssertionError(parse_mark("1:55"))
    for bad in ("", "fast", "1:5", None, "0:00.0"):
        try:
            parse_mark(bad)
        except ValueError:
            continue
        raise AssertionError(bad)
    at_start = _project(START)
    if at_start["scheduled_seconds"] != Decimal("120") or at_start["status"] != "on track":
        raise AssertionError(at_start)
    if at_start["factor"] != 1 or at_start["effective_seconds"] != Decimal("120"):
        raise AssertionError(at_start)
    before = _project(date(2025, 12, 1))
    if before["scheduled_seconds"] != Decimal("120"):
        raise AssertionError(before)
    mid = _project(MID)
    if mid["scheduled_seconds"] != Decimal("115") or mid["status"] != "on track":
        raise AssertionError(mid)
    if mid["effective_seconds"] != Decimal("115"):
        raise AssertionError(mid)
    again = _project(MID)
    if again != mid:
        raise AssertionError("the same inputs did not match")
    if _project(MID, None) != mid:
        raise AssertionError("missing logs were not the same as no logs")


def test_the_goal_date_and_after_it_stay_on_the_goal() -> None:
    """Once the goal date has arrived, the schedule does not keep stepping."""
    on_goal = _project(GOAL_DAY)
    if on_goal["scheduled_seconds"] != Decimal("110") or on_goal["status"] != "on track":
        raise AssertionError(on_goal)
    later = _project(date(2026, 2, 1))
    if later["scheduled_seconds"] != Decimal("110") or later["factor"] != 1:
        raise AssertionError(later)
    if later["status"] != "on track":
        raise AssertionError(later)
    same_day = project_800(
        current_mark=GOAL,
        goal_mark=GOAL,
        start=GOAL_DAY,
        goal_date=START,
        on=date(2026, 3, 1),
    )
    if same_day["scheduled_seconds"] != Decimal("110") or same_day["status"] != "on track":
        raise AssertionError(same_day)


def test_a_faster_log_tightens_and_a_slower_log_eases() -> None:
    """Each ISO week can move the 800 by at most one percent."""
    if WEEKLY_CAP != Decimal("0.01"):
        raise AssertionError(WEEKLY_CAP)
    fast = PaceLog(date(2026, 1, 3), 10, target_seconds=20)
    ahead = _project(MID, [fast])
    if ahead["factor"] != Decimal("0.99") or ahead["status"] != "ahead":
        raise AssertionError(ahead)
    if ahead["effective_seconds"] != Decimal("115") * Decimal("0.99"):
        raise AssertionError(ahead["effective_seconds"])
    if ahead["effective_seconds"] >= ahead["scheduled_seconds"]:
        raise AssertionError("a fast log did not tighten the 800")
    slow = PaceLog(date(2026, 1, 3), 40, target_seconds=20)
    behind = _project(MID, [slow])
    if behind["factor"] != Decimal("1.01") or behind["status"] != "behind":
        raise AssertionError(behind)
    if behind["effective_seconds"] != Decimal("115") * Decimal("1.01"):
        raise AssertionError(behind)
    # A second result in that same week does not stack another percent.
    stacked = _project(
        MID,
        [fast, PaceLog(date(2026, 1, 4), 10, target_seconds=20)],
    )
    if stacked["factor"] != Decimal("0.99"):
        raise AssertionError(stacked["factor"])
    # The next week has a fresh one percent.
    two = _project(
        date(2026, 1, 13),
        [fast, PaceLog(date(2026, 1, 12), 10, target_seconds=20)],
    )
    if two["factor"] != Decimal("0.99") * Decimal("0.99") or two["status"] != "ahead":
        raise AssertionError(two)
    # A result does not change the day it was logged.
    same = _project(date(2026, 1, 3), [fast])
    if same["factor"] != 1 or same["status"] != "on track":
        raise AssertionError(same)
    # Order does not matter. A blank or useless log is ignored.
    flipped = _project(
        MID,
        [
            PaceLog(date(2026, 1, 4), 0, target_seconds=20),
            PaceLog(date(2026, 1, 3), 10, target_seconds=20),
            PaceLog(date(2026, 1, 2), -1, template_id="not-a-session"),
        ],
    )
    if flipped["factor"] != ahead["factor"]:
        raise AssertionError(flipped)


def test_a_fast_log_still_applies_after_the_goal_date() -> None:
    """Past the goal date the schedule is the goal, then the logs correct it."""
    log = PaceLog(date(2026, 1, 20), 40, target_seconds=20)
    found = _project(date(2026, 2, 1), [log])
    if found["scheduled_seconds"] != Decimal("110"):
        raise AssertionError(found)
    if found["factor"] != Decimal("1.01") or found["status"] != "behind":
        raise AssertionError(found)
    if found["effective_seconds"] != Decimal("110") * Decimal("1.01"):
        raise AssertionError(found)


def test_rep_splits_tolerance_and_block() -> None:
    """Flat reps, a pyramid, a ladder, and one block time."""
    if FAMILY_FRACTION["spd"] != Decimal("0.96"):
        raise AssertionError(FAMILY_FRACTION["spd"])
    speed = _workout("spd_150_r150_x8", START)
    if speed is None:
        raise AssertionError("150s were not a workout")
    if speed["line"] != "8 × 150 m @ 21.6 s, 150 s rest":
        raise AssertionError(speed["line"])
    if speed["tolerance"] != "21.4-21.8 s":
        raise AssertionError(speed["tolerance"])
    if speed["block"] != "20:22.8" or speed["block_seconds"] != Decimal("1222.8"):
        raise AssertionError((speed["block"], speed["block_seconds"]))
    if speed["status"] != "on track":
        raise AssertionError(speed["status"])
    again = _workout("spd_150_r150_x8", START)
    if again != speed:
        raise AssertionError("the rep times were not stable")
    tightened = _workout(
        "spd_150_r150_x8",
        MID,
        [PaceLog(date(2026, 1, 3), 10, target_seconds=20)],
    )
    if tightened is None or tightened["status"] != "ahead":
        raise AssertionError(tightened)
    if Decimal(tightened["reps"][0]["seconds"]) >= Decimal(speed["reps"][0]["seconds"]):
        raise AssertionError("a fast log did not tighten the rep")
    pyramid = _workout("se_py_200to400_r90_x5", START)
    if pyramid is None:
        raise AssertionError("the pyramid was dropped")
    meters = [row["meters"] for row in pyramid["reps"]]
    if meters != [200, 300, 400, 300, 200]:
        raise AssertionError(meters)
    if "90 s rest" not in pyramid["line"] or "200 m @ 30.9 s" not in pyramid["line"]:
        raise AssertionError(pyramid["line"])
    ladder = _workout("thr_up_800to1600_r60_x3", START)
    if ladder is None or [row["meters"] for row in ladder["reps"]] != [800, 1200, 1600]:
        raise AssertionError(ladder)
    easy = _workout("aer_4000_r0_x1", START)
    if easy is None or easy["line"] != "1 × 4000 m @ 15:30.0":
        raise AssertionError(easy)
    if "rest" in easy["line"]:
        raise AssertionError(easy["line"])
    if workout_times(
        "not-a-session",
        current_mark=CURRENT,
        goal_mark=GOAL,
        start=START,
        goal_date=GOAL_DAY,
        on=START,
    ) is not None:
        raise AssertionError("an unknown id grew a time")


def main() -> None:
    test_marks_and_a_straight_line_with_no_logs()
    test_the_goal_date_and_after_it_stay_on_the_goal()
    test_a_faster_log_tightens_and_a_slower_log_eases()
    test_a_fast_log_still_applies_after_the_goal_date()
    test_rep_splits_tolerance_and_block()
    print("pace ok")


if __name__ == "__main__":
    main()
