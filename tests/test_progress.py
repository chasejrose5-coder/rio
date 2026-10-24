# test_progress.py — a season week is done, current, or upcoming.

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.season import sequence
from ui.progress import (
    days_label,
    days_remaining,
    phase_label,
    progress_weeks,
    week_status,
    week_sunday,
)

START = date(2026, 4, 19)
GOAL_DAY = date(2027, 3, 19)
TODAY = date(2026, 10, 22)


def test_current_wins_over_a_mark() -> None:
    """The week that contains today stays current after a mark."""
    if date(2026, 4, 19).weekday() != 6:
        raise AssertionError("19 Apr 2026 is not a Sunday")
    if week_status(start=START, week_number=1, today=date(2026, 4, 19), marked=False) != "current":
        raise AssertionError("the opening Sunday is not current")
    if week_status(start=START, week_number=1, today=date(2026, 4, 25), marked=True) != "current":
        raise AssertionError("a marked Saturday left the current week")
    if week_status(start=START, week_number=2, today=date(2026, 4, 19), marked=False) != "upcoming":
        raise AssertionError("the next week is not upcoming")
    if week_status(start=START, week_number=2, today=date(2026, 4, 19), marked=True) != "done":
        raise AssertionError("a mark on a later week is not done")
    if week_status(start=START, week_number=1, today=date(2026, 4, 26), marked=True) != "done":
        raise AssertionError("a marked week before today is not done")
    if week_status(start=START, week_number=1, today=date(2026, 4, 26), marked=False) is not None:
        raise AssertionError("an unmarked past week was given a status")


def test_a_midweek_start_uses_the_sunday() -> None:
    """Week 1 is the Sunday–Saturday week that contains the start date."""
    start = date(2026, 4, 22)
    if week_status(start=start, week_number=1, today=date(2026, 4, 19), marked=False) != "current":
        raise AssertionError("the Sunday before a Wednesday start is outside week 1")
    if week_status(start=start, week_number=1, today=date(2026, 4, 18), marked=False) != "upcoming":
        raise AssertionError("the day before that Sunday was not upcoming")


def test_days_remaining_stop_at_the_goal() -> None:
    span = (GOAL_DAY - TODAY).days
    if days_remaining(GOAL_DAY, TODAY) != span or span <= 0:
        raise AssertionError("days remaining are not the days until the goal")
    if days_remaining(TODAY, TODAY) != 0 or days_remaining(date(2026, 10, 21), TODAY) != 0:
        raise AssertionError("a reached goal still had days remaining")
    if days_label(1) != "1 day to goal" or days_label(span) != f"{span} days to goal":
        raise AssertionError("the countdown label changed")
    if days_label(0) != "0 days to goal":
        raise AssertionError("zero days was not plural")
    if days_label(None) != "—":
        raise AssertionError("a blank countdown was not an em dash")


def test_rows_keep_season_order() -> None:
    """Marks, today, and phase come from the stored plan. The count is shared."""
    sessions = [
        {"week_number": 1, "reason_codes": ["phase_1", "phase_primary"]},
        {"week_number": 2, "reason_codes": ["phase_4", "phase_2"]},
        {"week_number": True, "reason_codes": ["phase_8"]},
    ]
    rows = progress_weeks(
        start=START,
        goal=date(2026, 5, 17),
        length=3,
        sessions=sessions,
        marks={1: "on_track", 3: "smashing", 4: "not_hitting"},
        today=date(2026, 4, 26),
    )
    if [row["week"] for row in rows] != [1, 2, 3]:
        raise AssertionError("weeks were not 1..length in order")
    if [row["status"] for row in rows] != ["done", "current", "done"]:
        raise AssertionError(f"statuses were {[row['status'] for row in rows]}")
    if [row["phase"] for row in rows] != ["1", "4, 2", "—"]:
        raise AssertionError(f"phases were {[row['phase'] for row in rows]}")
    if [row["days_remaining"] for row in rows] != [None, 21, None]:
        raise AssertionError(
            f"days remaining were {[row['days_remaining'] for row in rows]}"
        )
    if phase_label([{"reason_codes": ["phase_8"]}]) != "8":
        raise AssertionError("phase 8 was not read")
    blank = progress_weeks(
        start=START,
        goal=GOAL_DAY,
        length=2,
        sessions=[],
        marks=None,
        today=date(2026, 4, 10),
    )
    if [row["status"] for row in blank] != ["upcoming", "upcoming"]:
        raise AssertionError("a season before today was not upcoming")
    opening = days_remaining(GOAL_DAY, week_sunday(START, 1) + timedelta(days=6))
    if blank[0]["days_remaining"] != opening or blank[1]["days_remaining"] != opening - 7:
        raise AssertionError("upcoming weeks did not count down from each Saturday")
    if progress_weeks(
        start=START,
        goal=GOAL_DAY,
        length=0,
        sessions=sessions,
        marks={},
        today=TODAY,
    ):
        raise AssertionError("an empty season produced weeks")


def test_a_stored_plan_has_one_current_week() -> None:
    """Progress reads sequence() output. It does not build another plan."""
    plan = sequence("2:02.9", START, "1:55.0", GOAL_DAY)
    rows = progress_weeks(
        start=START,
        goal=GOAL_DAY,
        length=plan["season_length_weeks"],
        sessions=plan["sessions"],
        marks={1: "not_hitting"},
        today=TODAY,
    )
    if len(rows) != plan["season_length_weeks"] or len(rows) < 3:
        raise AssertionError("the stored season length was not kept")
    current = [row for row in rows if row["status"] == "current"]
    if len(current) != 1:
        raise AssertionError(f"{len(current)} weeks were current")
    number = current[0]["week"]
    if rows[0]["status"] != "done" or number == 1:
        raise AssertionError("the marked opening week was not done")
    previous = None
    live = current[0]["days_remaining"]
    for row in rows:
        if row["week"] < number and row["week"] != 1 and row["status"] is not None:
            raise AssertionError("an unmarked past week gained a status")
        if row["week"] > number and row["status"] != "upcoming":
            raise AssertionError("a later week was not upcoming")
        remaining = row["days_remaining"]
        if row["status"] == "current":
            if remaining != days_remaining(GOAL_DAY, TODAY):
                raise AssertionError("the current week was not the days to the goal")
        elif row["status"] == "upcoming":
            saturday = week_sunday(START, row["week"]) + timedelta(days=6)
            if remaining != days_remaining(GOAL_DAY, saturday):
                raise AssertionError("an upcoming week did not count from its Saturday")
            if previous is None and remaining >= live:
                raise AssertionError("the next week did not have fewer days than today")
            if previous is not None and remaining != max(0, previous - 7):
                raise AssertionError("upcoming days did not decrease by a week")
            previous = remaining
        elif remaining is not None:
            raise AssertionError("a finished week still had days remaining")
        if row["phase"] not in "12345678":
            raise AssertionError(f"week {row['week']} phase was {row['phase']}")
        if "probability" in row or "readiness" in row:
            raise AssertionError("a score was added to a week")


if __name__ == "__main__":
    test_current_wins_over_a_mark()
    test_a_midweek_start_uses_the_sunday()
    test_days_remaining_stop_at_the_goal()
    test_rows_keep_season_order()
    test_a_stored_plan_has_one_current_week()
    print("progress ok")
