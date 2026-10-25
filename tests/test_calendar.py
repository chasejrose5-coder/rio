# test_calendar.py — a month of the plan Start already stored.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.season import sequence
from ui.calendar import (
    RACE_ID,
    month_title,
    month_weeks,
    opening_month,
    plan_months,
    session_label,
)

START = date(2026, 4, 19)
GOAL_DAY = date(2027, 3, 19)
TODAY = date(2026, 10, 24)

_LABELS = {
    "Easy",
    "Speed",
    "Long",
    "Race readiness",
    "Race",
    "Threshold",
    "Aerobic power",
    "Speed endurance",
    "Anaerobic",
}


def _no_score(value: dict) -> None:
    if "probability" in value or "readiness" in value or "readiness_score" in value:
        raise AssertionError("a score was added")
    text = str(value).lower()
    if "probability" in text or "readiness_score" in text:
        raise AssertionError("a score was named")


def test_labels_follow_the_stored_session() -> None:
    """Race is only the 800. A long run is Long. Easy aerobic stays Easy."""
    if session_label(RACE_ID) != "Race":
        raise AssertionError("the 800 race was not Race")
    if session_label("rr_400_r240_x2") != "Race readiness":
        raise AssertionError("a race-readiness day was called Race")
    if session_label("rr_800_r240_x2") != "Race readiness":
        raise AssertionError("another 800 id was treated as the race")
    if session_label("aer_8000_r0_x1") != "Long":
        raise AssertionError("the 8 km long run was not Long")
    if session_label("aer_12000_r0_x1") != "Long":
        raise AssertionError("the 12 km long run was not Long")
    if session_label("aer_10000_r0_x1", ["weekly_aerobic_long_run"]) != "Long":
        raise AssertionError("the weekly long-run code was ignored")
    if session_label("aer_10000_r0_x1") != "Easy":
        raise AssertionError("a 10 km easy day was not Easy")
    if session_label("aer_5000_r0_x1") != "Easy" or session_label("aer_4000_r0_x1") != "Easy":
        raise AssertionError("an easy day was not Easy")
    if session_label("spd_150_r150_x8") != "Speed" or session_label("mv_60_r120_x10") != "Speed":
        raise AssertionError("short fast work was not Speed")
    if session_label("thr_1200_r60_x4") != "Threshold":
        raise AssertionError("threshold was labeled Speed")
    if session_label("ap_600_r75_x6") != "Aerobic power":
        raise AssertionError("aerobic power lost its name")
    if session_label("se_400_r90_x6") != "Speed endurance":
        raise AssertionError("speed endurance was collapsed into Speed")
    if session_label("an_600_r180_x3") != "Anaerobic":
        raise AssertionError("anaerobic work lost its name")
    if session_label("") != "" or session_label(None) != "":
        raise AssertionError("a blank session grew a label")


def test_october_opens_on_sunday() -> None:
    """1 Oct 2026 is a Thursday, so the grid leads with four days of September."""
    if date(2026, 10, 1).weekday() != 3 or date(2026, 10, 24).weekday() != 5:
        raise AssertionError("October 2026 did not fall where the grid expects")
    weeks = month_weeks(2026, 10, [], today=TODAY)
    if len(weeks) != 5 or any(len(week) != 7 for week in weeks):
        raise AssertionError("October was not five Sunday–Saturday weeks")
    first = weeks[0][0]
    opening = weeks[0][4]
    if first["date"] != "2026-09-27" or first["in_month"] or first["label"] or first["day"]:
        raise AssertionError("the grid did not start on the Sunday before the month")
    if opening["date"] != "2026-10-01" or not opening["in_month"] or opening["day"] != 1:
        raise AssertionError("1 October was not the Thursday cell")
    saturday = weeks[3][6]
    if saturday["date"] != "2026-10-24" or not saturday["today"]:
        raise AssertionError("24 October was not marked as today")
    if weeks[-1][-1]["date"] != "2026-10-31" or not weeks[-1][-1]["in_month"]:
        raise AssertionError("31 October was not the last cell")
    if month_weeks(2026, 13, []) or month_weeks(True, 10, []):
        raise AssertionError("a bad month produced a grid")


def test_a_stored_plan_fills_the_month() -> None:
    """Calendar reads sequence() output. It does not build another plan."""
    plan = sequence("2:02.9", START, "1:55.0", GOAL_DAY)
    sessions = plan["sessions"]
    months = plan_months(sessions)
    if months[0] != date(2026, 4, 1) or months[-1] != date(2027, 3, 1):
        raise AssertionError(f"the season months were {months[0]} … {months[-1]}")
    if opening_month(months, TODAY) != date(2026, 10, 1):
        raise AssertionError("today did not open October")
    if opening_month(months, date(2026, 1, 1)) != months[0]:
        raise AssertionError("a day before the plan did not open the first month")
    if opening_month(months, date(2027, 6, 1)) != months[-1]:
        raise AssertionError("a day after the plan did not open the last month")
    if month_title(date(2026, 10, 1)) != "October 2026":
        raise AssertionError("the month title changed")
    labeled = {}
    races = 0
    for session in sessions:
        _no_score(session)
        label = session_label(session["template_id"], session["reason_codes"])
        if label not in _LABELS:
            raise AssertionError(f"{session['template_id']} labeled {label!r}")
        if label == "Race":
            races += 1
            if session["template_id"] != RACE_ID:
                raise AssertionError("Race was used for a day that is not the 800")
        labeled[session["date"]] = (label, session["template_id"])
    if races != 1:
        raise AssertionError(f"the plan had {races} race days")
    weeks = month_weeks(2026, 10, sessions, today=TODAY)
    seen = {}
    for week in weeks:
        for cell in week:
            _no_score(cell)
            if not cell["in_month"]:
                if cell["label"] or cell["template_id"]:
                    raise AssertionError("a day outside October kept a session")
                continue
            if cell["date"] in labeled:
                label, template = labeled[cell["date"]]
                if cell["label"] != label or cell["template_id"] != template:
                    raise AssertionError(f"{cell['date']} did not keep its session")
                seen[cell["date"]] = label
            elif cell["label"] or cell["template_id"]:
                raise AssertionError(f"{cell['date']} invented a session")
    october = [day for day in labeled if day.startswith("2026-10-")]
    if set(seen) != set(october) or not october:
        raise AssertionError("October did not show every stored session")
    if seen.get("2026-10-24") != "Long":
        raise AssertionError(f"24 October was {seen.get('2026-10-24')}")
    source = (ROOT / "ui" / "calendar.py").read_text(encoding="utf-8")
    if "engines" in source or "explain(" in source:
        raise AssertionError("calendar called an engine")


if __name__ == "__main__":
    test_labels_follow_the_stored_session()
    test_october_opens_on_sunday()
    test_a_stored_plan_fills_the_month()
    print("calendar ok")
