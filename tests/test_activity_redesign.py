# test_activity_redesign.py — pace units, plain names, one list, a fixed heart chart.

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.pace import (
    METERS_PER_MILE,
    display_workout,
    effort_pace,
    format_pace,
    format_span,
    pace_seconds,
    pace_unit,
    rep_time_text,
    workout_recipe,
    workout_times,
)
from ui.activity_board import (
    build_cards,
    card_html,
    group_weeks,
    heart_axis_chart,
    heart_points,
    summary_html,
    visible_text,
    week_summary,
    weekly_meters,
)
from ui.cloud_store import reset_memory_directory
from ui.sample_season import build_test_season
from ui.settings import DEFAULTS, normalize
from ui.strava import to_stored_activity

TODAY = date(2026, 11, 4)
START = date(2026, 1, 1)
GOAL_DAY = date(2026, 1, 11)


def test_a_mile_is_exact_and_pace_rounds_half_up() -> None:
    """1 mi = 1609.344 m. The same inputs always print the same pace."""
    if METERS_PER_MILE != Decimal("1609.344"):
        raise AssertionError(METERS_PER_MILE)
    if pace_unit("km") != "km" or pace_unit("per km") != "km":
        raise AssertionError("kilometers were not accepted")
    if pace_unit(None) != "mi" or pace_unit("yards") != "mi":
        raise AssertionError("the default pace is not per mile")
    mile = pace_seconds(Decimal("1609.344"), Decimal("360"), "mi")
    if mile != Decimal("360"):
        raise AssertionError(mile)
    again = pace_seconds(Decimal("1609.344"), Decimal("360"), "mi")
    if again != mile or format_pace(Decimal("1609.344"), Decimal("360"), "mi") != "6:00 /mi":
        raise AssertionError(again)
    per_km = format_pace(Decimal("1609.344"), Decimal("360"), "km")
    if per_km != "3:44 /km":
        raise AssertionError(per_km)
    if format_pace(Decimal("5000"), Decimal("1162.5"), "km") != "3:53 /km":
        raise AssertionError("half a second did not round up")
    if format_pace(Decimal("5000"), Decimal("1162.5"), "mi") != "6:14 /mi":
        raise AssertionError(format_pace(Decimal("5000"), Decimal("1162.5"), "mi"))
    if format_span(0, "mi") != "0.0 mi" or format_span(Decimal("1609.344"), "km") != "1.6 km":
        raise AssertionError(format_span(Decimal("1609.344"), "km"))
    if rep_time_text(Decimal("22.5")) != "22.5 s":
        raise AssertionError(rep_time_text(Decimal("22.5")))


def test_continuous_runs_are_pace_and_reps_keep_the_target() -> None:
    """An easy run is never a total time. A speed rep stays in seconds, plus rest."""
    easy = workout_recipe("aer_5000_r0_x1")
    speed = workout_recipe("spd_150_r150_x8")
    fly = workout_recipe("mv_60_r120_x10")
    if not easy or not easy["continuous"] or easy["speed"]:
        raise AssertionError(easy)
    if not speed or speed["continuous"] or not speed["speed"]:
        raise AssertionError(speed)
    if not fly or fly["reps"] != 10 or fly["distances"] != [60] * 10:
        raise AssertionError(fly)
    prescribed = workout_times(
        "aer_5000_r0_x1",
        current_mark="2:00.0",
        goal_mark="1:50.0",
        start=START,
        goal_date=GOAL_DAY,
        on=START,
    )
    run = {
        "template_id": "aer_5000_r0_x1",
        "distance_m": 5000,
        "moving_seconds": 1200,
        "laps": [{"distance_m": 5000, "moving_seconds": 1200}],
    }
    shown = display_workout(prescribed, run, "mi")
    if "/mi" not in shown["detail"] or "Target " not in shown["detail"] or "Actual " not in shown["detail"]:
        raise AssertionError(shown)
    if " m @" in shown["detail"] or shown["detail"].startswith("20:") or "15:30" in shown["detail"]:
        raise AssertionError("a continuous run was shown as a total time")
    metric = display_workout(prescribed, run, "km")
    if "/km" not in metric["detail"] or "/mi" in metric["detail"]:
        raise AssertionError(metric)
    if shown["detail"] == metric["detail"]:
        raise AssertionError("the unit did not change the pace")
    reps = workout_times(
        "spd_150_r150_x8",
        current_mark="2:00.0",
        goal_mark="1:50.0",
        start=START,
        goal_date=GOAL_DAY,
        on=START,
    )
    logged = {
        "template_id": "spd_150_r150_x8",
        "distance_m": 1200,
        "laps": [{"distance_m": 150, "moving_seconds": 21} for _ in range(8)],
    }
    speed_line = display_workout(reps, logged, "mi")
    if "21.6 s" not in speed_line["detail"] or "150 s rest" not in speed_line["detail"]:
        raise AssertionError(speed_line["detail"])
    if "/mi" in speed_line["detail"] or "/km" in speed_line["detail"]:
        raise AssertionError("a rep was shown as pace")
    if len(speed_line["laps"]) != 8:
        raise AssertionError(speed_line["laps"])
    first = speed_line["laps"][0]
    if first["rep"] != 1 or first["target"] != "21.6 s" or first["actual"] != "21.0 s":
        raise AssertionError(first)
    if first["rest"] != "150 s" or speed_line["laps"][-1]["rest"] != "—":
        raise AssertionError(speed_line["laps"][-1])
    if effort_pace({"distance_m": 1000, "moving_seconds": 300}, "km") != "5:00 /km":
        raise AssertionError(effort_pace({"distance_m": 1000, "moving_seconds": 300}, "km"))
    integer = effort_pace({"distance_m": 1000, "elapsed_seconds": 300}, "mi")
    if not integer or integer == "—":
        raise AssertionError("an integer distance dropped the pace")


def test_the_test_season_is_one_list_of_plain_cards() -> None:
    """Raw codes stay hidden. Weeks are newest first. This week has the four counts."""
    built = build_test_season()
    runs = built["runs"]
    activities = [to_stored_activity(run) for run in runs]
    start = date.fromisoformat(built["inputs"][1])
    goal_day = date.fromisoformat(built["inputs"][3])
    cards = build_cards(
        runs,
        activities,
        built["plan"]["sessions"],
        current=built["inputs"][0],
        goal=built["inputs"][2],
        start=start,
        goal_day=goal_day,
        unit="mi",
        date_format="short",
    )
    if len(cards) != len(runs):
        raise AssertionError((len(cards), len(runs)))
    ids = [card["id"] for card in cards]
    if len(ids) != len(set(ids)):
        raise AssertionError("a run was listed twice")
    markup = "".join(card_html(card) for card in cards)
    visible = visible_text(markup)
    for code in ("aer_5000_r0_x1", "spd_150_r150_x8", "mv_60_r120_x10"):
        if code in visible:
            raise AssertionError(f"{code} is on the page")
        if code not in markup:
            raise AssertionError(f"{code} was dropped from the markup")
    if "Easy 5 km" not in visible or "Long 12 km" not in visible:
        raise AssertionError(visible[:500])
    if "8 × 150 m" not in visible or "10 × 60 m" not in visible:
        raise AssertionError("a speed workout kept its code")
    easy = next(card for card in cards if card["template_id"] == "aer_5000_r0_x1")
    if "/mi" not in easy["detail"] or "Target " not in easy["detail"]:
        raise AssertionError(easy)
    if ":" in easy["detail"].split("Actual", 1)[-1] and "/mi" not in easy["detail"].split("Actual", 1)[-1]:
        raise AssertionError(easy["detail"])
    if any(token in easy["detail"] for token in (" m @", "Block")):
        raise AssertionError(easy["detail"])
    speed = next(card for card in cards if card["template_id"] == "spd_150_r150_x8")
    if not speed["laps"] or "Actual" not in card_html(speed):
        raise AssertionError(speed)
    table = card_html(speed)
    if "<th>Rep</th>" not in table or "<th>Target</th>" not in table or "<th>Rest</th>" not in table:
        raise AssertionError(table)
    summary = week_summary(cards, TODAY, "mi")
    if summary["runs"] != sum(summary["counts"].values()):
        raise AssertionError(summary)
    if summary["runs"] <= 0 or not summary["distance"].endswith(" mi"):
        raise AssertionError(summary)
    counted = "".join(summary_html(summary))
    for label in ("Distance", "Runs", "On track", "Ahead", "Behind", "Extra"):
        if label not in counted:
            raise AssertionError(label)
    groups = group_weeks(cards, TODAY)
    starts = [group["start"] for group in groups]
    if starts != sorted(starts, reverse=True):
        raise AssertionError(starts)
    opened = [group for group in groups if group["open"]]
    if len(opened) != 1 or opened[0]["start"] != date(2026, 11, 1):
        raise AssertionError(opened)
    for group in groups:
        days = [card["date"] for card in group["cards"]]
        if days != sorted(days, reverse=True):
            raise AssertionError(days)
    metric = build_cards(
        runs,
        [],
        built["plan"]["sessions"],
        current=built["inputs"][0],
        goal=built["inputs"][2],
        start=start,
        goal_day=goal_day,
        unit="km",
    )
    metric_easy = next(card for card in metric if card["template_id"] == "aer_5000_r0_x1")
    if "/km" not in metric_easy["detail"] or "/mi" in metric_easy["detail"]:
        raise AssertionError(metric_easy["detail"])
    if week_summary(metric, TODAY, "km")["distance"].endswith(" mi"):
        raise AssertionError("kilometers were drawn as miles")
    length = built["plan"]["season_length_weeks"]
    meters = weekly_meters(cards, start, length)
    if len(meters) != length or sum(meters) <= 0:
        raise AssertionError(meters)
    points = heart_points(cards)
    if len(points) < 8:
        raise AssertionError(len(points))
    svg = heart_axis_chart(points)
    if 'viewBox="0 0 640 220"' not in svg:
        raise AssertionError("the heart chart grew with the dates")
    if 'stroke="#6B6B6B"' not in svg or ">Heart rate" not in svg and "Heart rate · bpm" not in svg:
        raise AssertionError("the heart chart has no axis title")
    if svg.count("<text ") > 12:
        raise AssertionError("date labels were not thinned")
    if svg.count("<circle ") != len(points):
        raise AssertionError("a heart rate was dropped")
    if "aer_" in visible_text(svg):
        raise AssertionError(svg)


def test_pace_units_default_to_miles_and_stay_on_the_account() -> None:
    """The preference is per mile until someone picks per km. Another login is not changed."""
    if DEFAULTS["pace_units"] != "mi":
        raise AssertionError(DEFAULTS)
    clean = normalize(None)
    if clean["pace_units"] != "mi" or clean["units"] != "km":
        raise AssertionError(clean)
    if normalize({"pace_units": "km"})["pace_units"] != "km":
        raise AssertionError("per km was dropped")
    if normalize({"pace_units": "yards"})["pace_units"] != "mi":
        raise AssertionError("a bad pace unit stuck")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    page = app[app.index("def page_settings(") : app.index("\ndef page_plan(")]
    for label in ("Pace units", "per mile", "per km"):
        if label not in page:
            raise AssertionError(label)
    activity = app[app.index("def page_activity(") : app.index("\ndef ", app.index("def page_activity(") + 1)]
    if "No matched activities." not in activity or "_activity_table(" not in activity:
        raise AssertionError("the matched table was removed")
    tail = activity[activity.index("No matched activities.") :]
    if "return" in tail or "_all_activities_table(" not in tail:
        raise AssertionError("an empty list hides the other activities")
    if "heart_axis_chart(" not in activity or "week_summary(" not in activity:
        raise AssertionError("the activity page did not grow the new list")
    directory = reset_memory_directory()
    ada = directory.sign_up("ada@example.com", "password-one", "Ada")
    beau = directory.sign_up("beau@example.com", "password-two", "Beau")
    directory.save_pace_units(ada["access_token"], "km")
    kept = directory.load_bundle(ada["access_token"])
    if kept["profile"].get("pace_units") != "km":
        raise AssertionError(kept["profile"])
    other = directory.load_bundle(beau["access_token"])
    if other["profile"].get("pace_units") not in (None, "mi") or "pace_units" in other["profile"]:
        raise AssertionError(other["profile"])
    migrations = list((ROOT / "supabase" / "migrations").glob("004_*.sql"))
    if migrations:
        raise AssertionError("pace units required a new table")


def main() -> None:
    test_a_mile_is_exact_and_pace_rounds_half_up()
    test_continuous_runs_are_pace_and_reps_keep_the_target()
    test_the_test_season_is_one_list_of_plain_cards()
    test_pace_units_default_to_miles_and_stay_on_the_account()
    print("activity redesign ok")


if __name__ == "__main__":
    main()
