# test_dashboard.py — home page fields from a plan Start already stored.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import SPEND_CAP_MICRO_USD
from engines.season import sequence
from ui.dashboard import (
    current_week,
    dashboard_view,
    last_mark,
    next_workout,
    session_facts,
    week_focus,
)
from ui.progress import days_label, days_remaining

START = date(2026, 4, 19)
GOAL_DAY = date(2027, 3, 19)
TODAY = date(2026, 10, 24)


def _no_score(view: dict) -> None:
    if "probability" in view or "readiness" in view or "readiness_score" in view:
        raise AssertionError("a score was added")
    for value in view.values():
        text = str(value).lower()
        if "probability" in text or "readiness" in text:
            raise AssertionError("a score was named")


def test_next_workout_is_today_or_later() -> None:
    """A session today is next. Yesterday is not. The earlier future day wins."""
    sessions = [
        {"date": "2026-10-22", "day_of_week": "Thursday", "template_id": "se_400_r90_x6"},
        {"date": "2026-10-24", "day_of_week": "Saturday", "template_id": "aer_10000_r0_x1"},
        {"date": "2026-10-27", "day_of_week": "Tuesday", "template_id": "ap_800_r90_x5"},
        {"date": "not-a-date", "day_of_week": "Monday", "template_id": "aer_8000_r0_x1"},
        "skip",
    ]
    today = date(2026, 10, 24)
    found = next_workout(sessions, today)
    if found != {
        "day_of_week": "Saturday",
        "date": "2026-10-24",
        "template_id": "aer_10000_r0_x1",
    }:
        raise AssertionError(f"today was not the next workout: {found}")
    later = next_workout(sessions, date(2026, 10, 25))
    if later is None or later["date"] != "2026-10-27":
        raise AssertionError(f"the following Tuesday was not next: {later}")
    if next_workout(sessions, date(2026, 10, 28)) is not None:
        raise AssertionError("a finished plan still had a next workout")
    if next_workout([], today) is not None:
        raise AssertionError("an empty plan had a next workout")


def test_last_mark_is_the_latest_week() -> None:
    """A later week wins. Anything that is not a mark is ignored."""
    found = last_mark(
        {
            2: "on_track",
            5: "not_hitting",
            9: "smashing",
            4: "faster",
            True: "on_track",
            "3": "on_track",
            0: "on_track",
        }
    )
    if found != {"week": 9, "mark": "smashing"}:
        raise AssertionError(f"the latest mark was {found}")
    if last_mark(None) is not None or last_mark({}) is not None:
        raise AssertionError("a missing mark was invented")
    if last_mark({1: "ready"}) is not None:
        raise AssertionError("an unknown mark was kept")


def test_focus_names_primary_work_in_day_order() -> None:
    """Secondary work and the long run stay out. An easy week says so."""
    sessions = [
        {
            "date": "2026-10-22",
            "template_id": "ap_800_r90_x5",
            "reason_codes": ["phase_5", "phase_primary", "priority_aerobic_power"],
        },
        {
            "date": "2026-10-20",
            "template_id": "se_400_r90_x6",
            "reason_codes": ["phase_5", "phase_primary", "priority_speed_endurance"],
        },
        {
            "date": "2026-10-24",
            "template_id": "aer_10000_r0_x1",
            "reason_codes": ["phase_5", "weekly_aerobic_long_run"],
        },
        {
            "date": "2026-10-18",
            "template_id": "spd_150_r150_x8",
            "reason_codes": ["phase_5", "phase_secondary"],
        },
    ]
    if week_focus(sessions) != "Speed endurance and aerobic power":
        raise AssertionError(f"focus was {week_focus(sessions)}")
    easy = [
        {
            "date": "2026-10-20",
            "template_id": "se_300_r75_x8",
            "reason_codes": ["phase_5", "phase_primary", "extra_easy_week"],
        }
    ]
    if week_focus(easy) != "Easy week":
        raise AssertionError("an easy week kept the quality focus")
    taper = [
        {
            "date": "2026-10-20",
            "template_id": "rr_300_r180_x3",
            "reason_codes": ["phase_8", "phase_primary", "phase_8_freshness"],
        },
        {
            "date": "2026-10-22",
            "template_id": "mv_60_r120_x10",
            "reason_codes": ["phase_8", "phase_primary", "phase_8_freshness"],
        },
    ]
    if week_focus(taper) != "Race pace and max velocity":
        raise AssertionError(f"taper focus was {week_focus(taper)}")
    fresh = [
        {
            "date": "2026-10-20",
            "template_id": "aer_5000_r0_x1",
            "reason_codes": ["phase_8", "phase_8_freshness"],
        }
    ]
    if week_focus(fresh) != "The taper stays fresh":
        raise AssertionError("a fresh taper with no primary work was not named")
    if week_focus([]) != "—":
        raise AssertionError("an empty week grew a focus")
    three = week_focus(
        [
            {"date": "2026-10-20", "template_id": "se_400_r90_x6", "reason_codes": ["phase_primary"]},
            {"date": "2026-10-21", "template_id": "ap_700_r90_x5", "reason_codes": ["phase_primary"]},
            {"date": "2026-10-22", "template_id": "thr_1000_r60_x5", "reason_codes": ["phase_primary"]},
        ]
    )
    if three != "Speed endurance, aerobic power, and threshold":
        raise AssertionError(f"three-part focus was {three}")


def test_view_uses_the_current_week_only() -> None:
    """Days, phase, and focus come from today. A past week is not current."""
    sessions = [
        {
            "week_number": 1,
            "day_of_week": "Tuesday",
            "date": "2026-04-21",
            "template_id": "se_400_r90_x6",
            "reason_codes": ["phase_4", "phase_primary"],
        },
        {
            "week_number": 2,
            "day_of_week": "Tuesday",
            "date": "2026-04-28",
            "template_id": "thr_1200_r60_x4",
            "reason_codes": ["phase_3", "phase_primary"],
        },
    ]
    today = date(2026, 4, 28)
    view = dashboard_view(
        start=START,
        goal=GOAL_DAY,
        length=2,
        sessions=sessions,
        marks={1: "on_track"},
        today=today,
    )
    _no_score(view)
    if current_week(start=START, length=2, today=today) != 2:
        raise AssertionError("the week containing today was not current")
    if view["phase"] != "3":
        raise AssertionError(f"phase was {view['phase']}")
    if view["focus"] != "Threshold":
        raise AssertionError(f"focus followed the wrong week: {view['focus']}")
    if view["next"] != {
        "day_of_week": "Tuesday",
        "date": "2026-04-28",
        "template_id": "thr_1200_r60_x4",
    }:
        raise AssertionError(f"next workout was {view['next']}")
    if view["mark"] != {"week": 1, "mark": "on_track"}:
        raise AssertionError(f"last mark was {view['mark']}")
    remaining = days_remaining(GOAL_DAY, today)
    if view["days_remaining"] != remaining or view["days_label"] != days_label(remaining):
        raise AssertionError("days until the goal changed")
    before = dashboard_view(
        start=START,
        goal=GOAL_DAY,
        length=2,
        sessions=sessions,
        marks=None,
        today=date(2026, 4, 1),
    )
    if before["phase"] != "—" or before["focus"] != "—":
        raise AssertionError("a season that has not started had a current phase")
    if before["next"] is None or before["next"]["date"] != "2026-04-21":
        raise AssertionError("the first session was not next before the season")
    if before["mark"] is not None:
        raise AssertionError("a missing mark was filled in")
    after = dashboard_view(
        start=START,
        goal=date(2026, 5, 1),
        length=2,
        sessions=sessions,
        marks={2: "not_hitting"},
        today=date(2026, 5, 20),
    )
    if after["next"] is not None or after["phase"] != "—" or after["days_remaining"] != 0:
        raise AssertionError("a finished season still counted a workout or days")
    if after["mark"] != {"week": 2, "mark": "not_hitting"}:
        raise AssertionError("the last mark was dropped after the season")
    if dashboard_view(
        start=START,
        goal=GOAL_DAY,
        length=0,
        sessions=sessions,
        marks={},
        today=today,
    )["phase"] != "—":
        raise AssertionError("an empty season had a current phase")


def test_a_stored_plan_fills_the_home_page() -> None:
    """Dashboard reads sequence() output. It does not build another plan."""
    plan = sequence("2:02.9", START, "1:55.0", GOAL_DAY)
    view = dashboard_view(
        start=START,
        goal=GOAL_DAY,
        length=plan["season_length_weeks"],
        sessions=plan["sessions"],
        marks={1: "not_hitting", 4: "on_track"},
        today=TODAY,
    )
    _no_score(view)
    upcoming = [
        session
        for session in plan["sessions"]
        if date.fromisoformat(session["date"]) >= TODAY
    ]
    upcoming.sort(key=lambda session: session["date"])
    if not upcoming:
        raise AssertionError("the stored plan had no session on or after today")
    nxt = upcoming[0]
    if view["next"] != {
        "day_of_week": nxt["day_of_week"],
        "date": nxt["date"],
        "template_id": nxt["template_id"],
    }:
        raise AssertionError("the next workout was not the stored session")
    week = current_week(start=START, length=plan["season_length_weeks"], today=TODAY)
    if week is None or view["phase"] not in "12345678":
        raise AssertionError(f"current phase was {view['phase']}")
    if nxt["week_number"] < week:
        raise AssertionError("the next workout sat in a week before today")
    if view["focus"] in ("", "—") or "_" in view["focus"]:
        raise AssertionError(f"this week's focus was {view['focus']}")
    if view["days_remaining"] != (GOAL_DAY - TODAY).days:
        raise AssertionError("days until the goal were not the calendar span")
    if view["mark"] != {"week": 4, "mark": "on_track"}:
        raise AssertionError("an earlier mark was treated as the last mark")
    source = (ROOT / "ui" / "dashboard.py").read_text(encoding="utf-8")
    if "engines" in source or "explain(" in source:
        raise AssertionError("dashboard called an engine")


def test_session_facts_read_the_frozen_id() -> None:
    """Distance, rest, and reps are the id. Pace is the written sentence."""
    found = session_facts(
        "se_400_r90_x6",
        "6 × 400 m near goal 800 pace, 90 s rest",
    )
    if found != {
        "distance": "400 m",
        "pace": "Near goal 800",
        "rest": "90 s",
        "reps": "6",
    }:
        raise AssertionError(f"400s were {found}")
    easy = session_facts("aer_10000_r0_x1", "10 km easy, Zone 2, talkable")
    if easy["distance"] != "10000 m" or easy["rest"] != "—" or easy["reps"] != "1":
        raise AssertionError(f"an easy run was {easy}")
    if easy["pace"] != "Easy":
        raise AssertionError(f"easy pace was {easy['pace']}")
    minutes = session_facts("se_500_r120_x4", "4 × 500 m near goal 800 pace, 2 min rest")
    if minutes["rest"] != "2 min" or minutes["reps"] != "4":
        raise AssertionError(f"two-minute rest was {minutes}")
    ladder = session_facts("thr_up_800to1600_r60_x3", "comfortably hard")
    if ladder["distance"] != "800–1600 m" or ladder["rest"] != "60 s" or ladder["reps"] != "3":
        raise AssertionError(f"a ladder was {ladder}")
    if ladder["pace"] != "Comfortably hard":
        raise AssertionError(f"ladder pace was {ladder['pace']}")
    pyramid = session_facts("se_py_200to400_r90_x5", "near goal 800 pace")
    if pyramid["distance"] != "200–400 m" or pyramid["pace"] != "Near goal 800":
        raise AssertionError(f"a pyramid was {pyramid}")
    race = session_facts("rr_800_r0_x1", "800 m race")
    if race["pace"] != "Race" or race["rest"] != "—" or race["distance"] != "800 m":
        raise AssertionError(f"a race was {race}")
    slower = session_facts(
        "ap_800_r90_x5",
        "5 × 800 m strong, clearly slower than goal 800 pace, 90 s rest",
    )
    if slower["pace"] != "Slower than goal 800":
        raise AssertionError(f"slower pace was {slower['pace']}")
    blank = session_facts("not-a-session", "near goal 800 pace")
    if blank != {"distance": "—", "pace": "—", "rest": "—", "reps": "—"}:
        raise AssertionError(f"an unknown id grew facts: {blank}")
    if session_facts("", "")["distance"] != "—":
        raise AssertionError("a blank id grew a distance")


def test_home_track_does_not_spend() -> None:
    """The home page draws the track from stored fields. It does not call a model.

    A missing Intervals key is not shown here. Prose spend stays capped at $25.
    """
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    start = app.index("def page_dashboard(")
    page = app[start : app.index("\ndef ", start + 1)]
    if "_track_hero(" not in page or "_track_stage(" not in page or "_track_meta(" not in page:
        raise AssertionError("the track is not the home page")
    if "_activities_notice(" in page or "RIO_INTERVALS_API_KEY" in page:
        raise AssertionError("the home page shows the Intervals key warning")
    if "explain(" in page or "probability" in page.lower() or "readiness" in page.lower():
        raise AssertionError("home started prose or a score")
    source = (ROOT / "ui" / "dashboard.py").read_text(encoding="utf-8")
    if "engines" in source or "explain(" in source:
        raise AssertionError("session facts called an engine")
    if "session_facts(" not in app[app.index("def _track_stage(") : app.index("def _track_hero(")]:
        raise AssertionError("the track does not read the session facts")


if __name__ == "__main__":
    test_next_workout_is_today_or_later()
    test_last_mark_is_the_latest_week()
    test_focus_names_primary_work_in_day_order()
    test_view_uses_the_current_week_only()
    test_a_stored_plan_fills_the_home_page()
    test_session_facts_read_the_frozen_id()
    test_home_track_does_not_spend()
    print("dashboard ok")
