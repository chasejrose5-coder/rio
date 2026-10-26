# test_progress.py — a season week is done, current, or upcoming.

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.season import sequence
from engines.explain import SPEND_CAP_MICRO_USD
from ui.progress import (
    days_label,
    days_remaining,
    phase_label,
    progress_weeks,
    volume_chart,
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


def test_volume_uses_loaded_distance() -> None:
    """A loaded day contributes that distance. A day with no file contributes 0.

    A week with no file shows 0 m. Template meters are not used.
    """
    sessions = [
        {
            "week_number": 1,
            "date": "2026-04-21",
            "template_id": "se_400_r90_x6",
            "reason_codes": ["phase_1"],
        },
        {
            "week_number": 1,
            "date": "2026-04-23",
            "template_id": "se_400_r90_x6",
            "reason_codes": ["phase_1"],
        },
        {
            "week_number": 2,
            "date": "2026-04-28",
            "template_id": "se_400_r90_x6",
            "reason_codes": ["phase_2"],
        },
    ]
    plain = progress_weeks(
        start=START,
        goal=GOAL_DAY,
        length=2,
        sessions=sessions,
        marks={},
        today=date(2026, 4, 10),
    )
    if plain[0]["volume"] != "0 m" or plain[1]["volume"] != "0 m":
        raise AssertionError((plain[0]["volume"], plain[1]["volume"]))
    if plain[0]["meters"] != 0 or plain[1]["meters"] != 0:
        raise AssertionError((plain[0]["meters"], plain[1]["meters"]))
    loaded = progress_weeks(
        start=START,
        goal=GOAL_DAY,
        length=2,
        sessions=sessions,
        marks={},
        today=date(2026, 4, 10),
        distances={"2026-04-21": 5600, "2026-04-23": 1000, "1999-01-01": 9},
    )
    if loaded[0]["volume"] != "6,600 m" or loaded[1]["volume"] != "0 m":
        raise AssertionError((loaded[0]["volume"], loaded[1]["volume"]))
    if loaded[0]["meters"] != 6600 or loaded[1]["meters"] != 0:
        raise AssertionError((loaded[0]["meters"], loaded[1]["meters"]))
    partial = progress_weeks(
        start=START,
        goal=GOAL_DAY,
        length=2,
        sessions=sessions,
        marks={},
        today=date(2026, 4, 10),
        distances={"2026-04-21": 5600, "2026-04-23": None, "1999-01-01": 9},
    )
    if partial[0]["volume"] != "5,600 m" or partial[1]["volume"] != "0 m":
        raise AssertionError((partial[0]["volume"], partial[1]["volume"]))
    broken = [
        {
            "week_number": 1,
            "date": "2026-04-21",
            "template_id": "se_400_r90_x6",
        },
        {
            "week_number": 1,
            "date": "2026-04-23",
            "template_id": "no_distance",
        },
    ]
    cleared = progress_weeks(
        start=START,
        goal=GOAL_DAY,
        length=1,
        sessions=broken,
        marks={},
        today=date(2026, 4, 10),
    )
    if cleared[0]["volume"] != "0 m":
        raise AssertionError(cleared[0]["volume"])
    one_file = progress_weeks(
        start=START,
        goal=GOAL_DAY,
        length=1,
        sessions=broken,
        marks={},
        today=date(2026, 4, 10),
        distances={"2026-04-23": 1000},
    )
    if one_file[0]["volume"] != "1,000 m":
        raise AssertionError(one_file[0]["volume"])
    still_open = progress_weeks(
        start=START,
        goal=GOAL_DAY,
        length=1,
        sessions=broken,
        marks={},
        today=date(2026, 4, 10),
        distances={"2026-04-21": 1000},
    )
    if still_open[0]["volume"] != "1,000 m":
        raise AssertionError(still_open[0]["volume"])
    if "probability" in loaded[0] or "readiness" in loaded[0]:
        raise AssertionError("a score was added to a week")
    source = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    start = source.index("def page_progress(")
    end = source.index("\ndef page_weekly(")
    page = source[start:end]
    if "loaded_distances(" not in page or "distances=" not in page:
        raise AssertionError("progress ignores loaded Intervals files")
    if "rio-progress-volume" not in source:
        raise AssertionError("progress does not show the distance")
    if "urlopen" in page or "fetch_activity" in page or "explain(" in page:
        raise AssertionError("progress calls the network or the model")
    progress_source = (ROOT / "ui" / "progress.py").read_text(encoding="utf-8")
    if "work_meters" in progress_source or "from engines" in progress_source:
        raise AssertionError("volume uses template meters")


def _polyline(svg: str) -> list[tuple[float, float]]:
    start = svg.index('points="') + len('points="')
    end = svg.index('"', start)
    points = []
    for pair in svg[start:end].split():
        x, y = pair.split(",")
        points.append((float(x), float(y)))
    return points


def test_the_line_is_weekly_completed_distance() -> None:
    """Every week is a point. A week with no file sits on zero.

    The line uses the completed meters already on the row. It does not
    score, and it does not spend.
    """
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    sessions = [
        {"week_number": 1, "date": "2026-04-21", "template_id": "se_400_r90_x6"},
        {"week_number": 2, "date": "2026-04-28", "template_id": "se_400_r90_x6"},
        {"week_number": 3, "date": "2026-05-05", "template_id": "se_400_r90_x6"},
    ]
    rows = progress_weeks(
        start=START,
        goal=GOAL_DAY,
        length=3,
        sessions=sessions,
        marks={},
        today=date(2026, 4, 10),
        distances={"2026-04-21": 5600, "2026-05-05": 1000},
    )
    if [row["meters"] for row in rows] != [5600, 0, 1000]:
        raise AssertionError([row["meters"] for row in rows])
    svg = volume_chart(
        [row["meters"] for row in rows],
        "km",
        [row["volume"] for row in rows],
    )
    points = _polyline(svg)
    if len(points) != 3:
        raise AssertionError(points)
    if not (points[0][1] < points[2][1] < points[1][1]):
        raise AssertionError("a week with no file did not sit on zero")
    if "Volume · km" not in svg or "mileage" in svg.lower():
        raise AssertionError(svg)
    if "probability" in svg or "readiness" in svg:
        raise AssertionError("a score was drawn on the line")
    if "Week 2 · 0 m" not in svg or "Week 1 · 5,600 m" not in svg:
        raise AssertionError("a week caption was dropped")
    flat = volume_chart([0, 0, 0], "km")
    flat_points = _polyline(flat)
    if len(flat_points) != 3 or len({point[1] for point in flat_points}) != 1:
        raise AssertionError("a season with no files was not a zero line")
    if "Volume · m" not in flat or "km" in flat:
        raise AssertionError(flat)
    miles = volume_chart([1609, 0], "miles")
    if "Volume · mi" not in miles or "km" in miles or "mileage" in miles.lower():
        raise AssertionError(miles)
    if ">1</text>" not in miles or ">2</text>" not in miles:
        raise AssertionError("week numbers were dropped")
    one = volume_chart([0], "km")
    if 'points="' in one or "<circle" not in one:
        raise AssertionError("a single week with no file was not drawn at zero")
    if volume_chart([], "km") != "":
        raise AssertionError("an empty season drew a line")
    long = volume_chart([0] * 47 + [5000], "km")
    long_points = _polyline(long)
    if len(long_points) != 48 or long_points[-1][1] >= long_points[0][1]:
        raise AssertionError("a later file did not rise off zero")
    if ">1</text>" not in long or ">48</text>" not in long or ">2</text>" in long:
        raise AssertionError("week labels were not the ends of a long season")
    broken = volume_chart([1000, None, -5, True], "km")
    broken_points = _polyline(broken)
    if len(broken_points) != 4 or broken_points[0][1] >= broken_points[1][1]:
        raise AssertionError(broken_points)
    if broken_points[1][1] != broken_points[2][1] or broken_points[2][1] != broken_points[3][1]:
        raise AssertionError("an unusable week was not zero")
    page = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    start = page.index("def page_progress(")
    end = page.index("\ndef page_weekly(")
    body = page[start:end]
    if "volume_chart(" not in body or 'row["meters"]' not in body:
        raise AssertionError("progress does not plot the weekly distance")
    progress_source = (ROOT / "ui" / "progress.py").read_text(encoding="utf-8")
    if "from engines" in progress_source or "explain(" in progress_source:
        raise AssertionError("the line started spending")
    for path in (ROOT / "engines").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "volume_chart" in text:
            raise AssertionError(f"{path.name} was changed for the line")


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
    test_volume_uses_loaded_distance()
    test_the_line_is_weekly_completed_distance()
    test_a_stored_plan_has_one_current_week()
    print("progress ok")
