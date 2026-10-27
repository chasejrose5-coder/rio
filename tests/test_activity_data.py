# test_activity_data.py — matched workouts, work meters, heart rate, no invented file.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import SPEND_CAP_MICRO_USD
from ui.activity_data import (
    NOT_PULLED,
    activity_banner,
    activity_view,
    choice_labels,
    file_heart_rates,
    heart_rate_points,
    matched_activities,
    session_rows,
    weekly_completed_meters,
)
from ui.last_session import loaded_distances
from ui.progress import heart_rate_chart

STORED = {
    "date": "2026-10-20",
    "id": "44521",
    "matched": True,
    "name": "Long Z2 Test",
    "start": "2026-10-20T08:12:00",
    "template_id": "aer_8000_r0_x1",
    "heart_rate": 151,
    "work_m": 123456,
    "reps": [57.5, 58],
    "distance": 5600,
    "elapsed_time": 2025,
    "max_heartrate": 176,
    "icu_intervals": [
        {"type": "WORK", "distance": 400, "elapsed_time": 57.5},
    ],
}


def _values(pairs: list[tuple[str, str]]) -> dict[str, str]:
    return {label: value for label, value in pairs}


def _flat(view: dict) -> str:
    parts = [f"{label}={value}" for label, value in view["header"]]
    parts.extend(f"{label}={value}" for label, value in view["hr"])
    for row in view["intervals"]:
        parts.extend(f"{key}={value}" for key, value in row.items())
    streams = view["streams"]
    if isinstance(streams, list):
        for label, value in streams:
            parts.append(f"{label}={value}")
    elif streams:
        parts.append(str(streams))
    return "\n".join(parts)


def test_only_matched_activities_are_listed_newest_first() -> None:
    """An extra session stays out. The latest start is the first choice."""
    early = {"id": "early", "matched": True, "date": "2026-10-18", "start": "2026-10-18T07:00:00", "name": "Early"}
    late = {"id": 99, "matched": True, "date": "2026-10-22", "start": "2026-10-22T18:00:00", "name": "Late"}
    same_day = {"id": "noon", "matched": True, "date": "2026-10-22", "start": "2026-10-22T12:00:00", "name": "Noon"}
    extra = {"id": "extra", "matched": False, "date": "2026-10-25", "name": "Extra"}
    blank = {"id": "", "matched": True, "date": "2026-10-25", "name": "Blank"}
    rows = matched_activities([extra, early, same_day, late, blank, "nope"])
    if [row["id"] for row in rows] != [99, "noon", "early"]:
        raise AssertionError([row["id"] for row in rows])
    labels = choice_labels(rows)
    if labels != ["2026-10-22 · Late", "2026-10-22 · Noon", "2026-10-18 · Early"]:
        raise AssertionError(labels)


def test_a_repeated_label_keeps_the_id() -> None:
    """Two activities with one date and title stay distinct in the drop-down."""
    first = {"id": "a", "matched": True, "date": "2026-10-20", "name": "Run"}
    second = {"id": "b", "matched": True, "date": "2026-10-20", "name": "Run"}
    labels = choice_labels(matched_activities([first, second]))
    if labels != ["2026-10-20 · Run · b", "2026-10-20 · Run · a"]:
        raise AssertionError(labels)
    nameless = choice_labels([{"id": "only", "date": "", "name": ""}])
    if nameless != ["— · only"]:
        raise AssertionError(nameless)


def test_stored_header_and_hr_show_and_the_rest_is_not_pulled() -> None:
    """Date, title, and average heart rate are stored. The other fields are not.

    Activity distance, elapsed time, and the interval rows stay not pulled
    even when a raw payload still carries them. WORK distance is not the header.
    """
    view = activity_view(STORED, date_format="iso")
    header = _values(view["header"])
    if header["Date / start time"] != "2026-10-20, 08:12":
        raise AssertionError(header)
    if header["Title"] != "Long Z2 Test":
        raise AssertionError(header)
    if header["Distance"] != NOT_PULLED or header["Elapsed Time"] != NOT_PULLED:
        raise AssertionError(header)
    if header["Avg HR"] != "151 bpm":
        raise AssertionError(header)
    hr = _values(view["hr"])
    if hr != {
        "Avg HR": "151 bpm",
        "Max HR": NOT_PULLED,
        "HR zones": NOT_PULLED,
        "Decoupling": NOT_PULLED,
    }:
        raise AssertionError(hr)
    if view["intervals"] != [
        {"Distance": NOT_PULLED, "Elapsed Time": NOT_PULLED, "Pace": NOT_PULLED}
    ]:
        raise AssertionError(view["intervals"])
    if view["streams"] != NOT_PULLED:
        raise AssertionError(view["streams"])
    shown = _flat(view)
    if "123456" in shown or "57.5" in shown or "5600" in shown or "2025" in shown:
        raise AssertionError(shown)
    if "176" in shown:
        raise AssertionError("max heart rate was treated as stored")
    short = activity_view({"date": "2026-10-20", "id": "x", "matched": True, "name": "  "}, date_format="short")
    if _values(short["header"])["Date / start time"] != "Oct 20, 2026":
        raise AssertionError(short["header"])
    if _values(short["header"])["Title"] != "—" or _values(short["hr"])["Avg HR"] != "—":
        raise AssertionError(short)


def test_streams_show_only_when_present_and_stay_not_pulled() -> None:
    """A missing stream list is not pulled. An empty list stays off the page.

    A named stream has no samples stored.
    """
    missing = activity_view({"id": "x"})
    if missing["streams"] != NOT_PULLED:
        raise AssertionError(missing["streams"])
    absent = activity_view({"id": "x", "streams": []})
    if absent["streams"] is not None:
        raise AssertionError(absent["streams"])
    blank = activity_view({"id": "x", "streams": {"heartrate": [], "altitude": None}})
    if blank["streams"] is not None:
        raise AssertionError(blank["streams"])
    recorded = {
        "id": "x",
        "name": "synthetic-se",
        "streams": {"heartrate": [140, 141], "velocity_smooth": [3.1], "cadence": [170]},
    }
    present = activity_view(recorded)
    if present["streams"] != [
        ("Heart rate", NOT_PULLED),
        ("Pace", NOT_PULLED),
        ("Cadence", NOT_PULLED),
    ]:
        raise AssertionError(present["streams"])
    named = activity_view({"id": "x", "streams": ["latlng", "temp"]})
    if named["streams"] != [("Position", NOT_PULLED), ("Temperature", NOT_PULLED)]:
        raise AssertionError(named["streams"])
    if activity_banner({"name": "Synthetic 6 x 400", "id": "1"}) != "SYNTHETIC / FIXTURE":
        raise AssertionError("a synthetic name was not marked")
    if activity_banner({"name": "Long Z2 Test", "id": "44521"}) is not None:
        raise AssertionError("a real activity was marked synthetic")
    if activity_banner(recorded) != "SYNTHETIC / FIXTURE":
        raise AssertionError("the name word synthetic was missed")


PLAN = [
    {
        "week_number": 1,
        "date": "2026-04-21",
        "template_id": "se_400_r90_x6",
        "reason_codes": ["phase_1"],
    },
    {
        "week_number": 1,
        "date": "2026-04-23",
        "template_id": "aer_8000_r0_x1",
        "reason_codes": ["phase_1", "weekly_aerobic_long_run"],
    },
    {
        "week_number": 2,
        "date": "2026-04-28",
        "template_id": "se_400_r90_x6",
        "reason_codes": ["phase_2"],
    },
]


def test_a_row_is_one_matched_session() -> None:
    """Date, template or label, work meters, and average heart rate.

    An unmatched activity stays out. Warm-up and the activity total stay out.
    The plan template is the label. Template meters are not used.
    """
    activities = [
        {
            "id": "a",
            "matched": True,
            "date": "2026-04-21",
            "start": "2026-04-21T08:00:00",
            "template_id": "se_400_r90_x6",
            "name": "Synthetic 6 x 400",
            "work_m": 800,
            "heart_rate": 151,
            "distance": 5600,
        },
        {
            "id": "long",
            "matched": True,
            "date": "2026-04-23",
            "start": "2026-04-23T09:00:00",
            "name": "Long Z2 Test",
            "work_m": 7500,
            "heart_rate": 142,
            "distance": 9000,
        },
        {
            "id": "extra",
            "matched": False,
            "date": "2026-04-28",
            "work_m": 8000,
            "heart_rate": 170,
            "name": "Extra",
        },
        {
            "id": "later",
            "matched": True,
            "date": "2026-06-01",
            "name": "Outside",
            "work_m": 5000,
            "heart_rate": 140,
        },
    ]
    rows = session_rows(activities, PLAN)
    if [row["date"] for row in rows] != ["2026-06-01", "2026-04-23", "2026-04-21"]:
        raise AssertionError([row["date"] for row in rows])
    speed = rows[2]
    if speed["label"] != "Speed endurance" or speed["work"] != "800 m" or speed["hr"] != "151 bpm":
        raise AssertionError(speed)
    if speed["meters"] != 800 or "5600" in speed["work"] or speed["meters"] == 2400:
        raise AssertionError("template meters or the activity total replaced WORK distance")
    long = rows[1]
    if long["label"] != "Long" or long["meters"] != 7500 or long["hr"] != "142 bpm":
        raise AssertionError(long)
    if any(row["id"] == "extra" for row in rows):
        raise AssertionError("an unmatched activity was listed")
    short = session_rows(
        [{"id": "a", "matched": True, "date": "2026-04-21", "name": "Long Z2 Test"}],
        [],
        date_format="short",
    )
    if short[0]["shown_date"] != "Apr 21, 2026" or short[0]["label"] != "Long Z2 Test":
        raise AssertionError(short[0])
    if short[0]["work"] != "—" or short[0]["hr"] != "—" or short[0]["meters"] is not None:
        raise AssertionError("a missing file invented work or heart rate")
    named = session_rows(
        [{"id": "a", "matched": True, "date": "2026-04-21", "template_id": "custom_thing", "name": ""}],
        [],
    )
    if named[0]["label"] != "custom_thing":
        raise AssertionError(named[0]["label"])


def test_weekly_work_is_matched_distance_only() -> None:
    """Each plan week sums WORK meters. A week with no match is 0.

    A date outside the season is left out. No match and no file draws nothing.
    A mark does not add template meters.
    """
    activities = [
        {"id": "a", "matched": True, "date": "2026-04-21", "work_m": 800, "heart_rate": 151},
        {"id": "b", "matched": True, "date": "2026-04-23", "work_m": 1000, "heart_rate": 142},
        {"id": "extra", "matched": False, "date": "2026-04-28", "work_m": 8000, "heart_rate": 170},
        {"id": "out", "matched": True, "date": "2026-06-01", "work_m": 5000, "heart_rate": 140},
    ]
    rows = session_rows(activities, PLAN, file_distances={"2026-04-21": 9999, "1999-01-01": 50})
    if rows[2]["meters"] != 800:
        raise AssertionError("a file distance was added on top of the matched work")
    meters = weekly_completed_meters(rows, start=date(2026, 4, 19), length=3)
    if meters != [1800, 0, 0]:
        raise AssertionError(meters)
    if 2400 in meters or 8000 in meters or 5000 in meters or 9999 in meters:
        raise AssertionError("template meters or an unmatched day were counted")
    empty = session_rows([], PLAN)
    if empty:
        raise AssertionError(empty)
    if weekly_completed_meters(empty, start=date(2026, 4, 19), length=8):
        raise AssertionError("a season with no Intervals file drew a line")
    points = heart_rate_points(rows)
    if [point["date"] for point in points] != ["2026-06-01", "2026-04-23", "2026-04-21"]:
        raise AssertionError(points)
    if any(point["bpm"] == 170 for point in points):
        raise AssertionError("an unmatched heart rate was plotted")
    blank = heart_rate_points(session_rows(
        [{"id": "a", "matched": True, "date": "2026-04-21", "heart_rate": None}],
        PLAN,
    ))
    if blank:
        raise AssertionError(blank)


def test_a_loaded_file_supplies_work_and_heart_rate() -> None:
    """A planned day with an Intervals file uses WORK distance and average HR.

    Warm-up, cool-down, and lap heart rate stay out. A missing file adds nothing.
    """
    day = "2026-04-21"
    sessions = [PLAN[0]]
    actuals = {day: {"template_id": "se_400_r90_x6", "intervals": "synthetic-se-400-with-recovery"}}
    wrong = {day: {"template_id": "aer_5000_r0_x1", "intervals": "synthetic-se-400-with-recovery"}}
    missing = {day: {"template_id": "se_400_r90_x6", "intervals": "no-such-intervals-file"}}
    with patch("urllib.request.urlopen", side_effect=AssertionError("live API")):
        distances = loaded_distances(sessions, actuals)
        rates = file_heart_rates(sessions, actuals)
        skipped = loaded_distances(sessions, wrong)
        absent = file_heart_rates(sessions, missing)
    if distances != {day: 2400.0} or rates != {day: 148.0}:
        raise AssertionError((distances, rates))
    if skipped or absent:
        raise AssertionError((skipped, absent))
    rows = session_rows([], sessions, file_distances=distances, file_heart_rates=rates)
    if len(rows) != 1:
        raise AssertionError(rows)
    row = rows[0]
    if row["label"] != "Speed endurance" or row["meters"] != 2400 or row["hr"] != "148 bpm":
        raise AssertionError(row)
    if row["meters"] == 5600 or row["heart_rate"] == 176:
        raise AssertionError("warm-up distance or a lap heart rate was used")
    filled = session_rows(
        [{"id": "a", "matched": True, "date": day, "work_m": None, "heart_rate": None, "distance": 5600}],
        sessions,
        file_distances=distances,
        file_heart_rates=rates,
    )
    if filled[0]["meters"] != 2400 or filled[0]["hr"] != "148 bpm":
        raise AssertionError(filled[0])
    owned = session_rows(
        [{"id": "a", "matched": True, "date": day, "work_m": 800, "heart_rate": 151, "distance": 5600}],
        sessions,
        file_distances=distances,
        file_heart_rates=rates,
    )
    if owned[0]["meters"] != 800 or owned[0]["hr"] != "151 bpm":
        raise AssertionError(owned[0])


def test_heart_rate_dots_are_labeled_with_the_date() -> None:
    """One dot per matched workout. The visible label is the date."""
    points = [
        {"date": "2026-04-21", "bpm": 151},
        {"date": "2026-05-05", "bpm": 141.5},
    ]
    svg = heart_rate_chart(
        points,
        start=date(2026, 4, 19),
        weeks=4,
        captions={"2026-04-21": "2026-04-21", "2026-05-05": "2026-05-05"},
    )
    if svg.count('class="rio-heart-dot"') != 2:
        raise AssertionError("a matched workout did not get its own dot")
    if "2026-04-21" not in svg or "2026-05-05" not in svg:
        raise AssertionError(svg)
    if "Tue 4/21 · 151" in svg or "Tue 5/5 · 141.5" in svg:
        raise AssertionError("the date label was replaced with the weekday line")
    if "2026-04-21 · 151 bpm" not in svg or "<polyline" in svg:
        raise AssertionError(svg)
    if "probability" in svg or "readiness" in svg or "mileage" in svg.lower():
        raise AssertionError(svg)


def test_the_page_lists_matched_activities_and_does_not_spend() -> None:
    """Activity data is in the nav. It does not classify, score, or call the model.

    Prose spend stays capped at $25. Season and classification stay untouched.
    """
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    if NOT_PULLED != "not pulled.":
        raise AssertionError(NOT_PULLED)
    source = (ROOT / "ui" / "activity_data.py").read_text(encoding="utf-8")
    if "from engines" in source or "explain(" in source or "classify(" in source:
        raise AssertionError("the view calls an engine")
    if "urlopen" in source or "fetch_activity" in source or "list_activities" in source:
        raise AssertionError("the view calls Intervals.icu")
    if "probability" in source.lower() or "readiness" in source.lower():
        raise AssertionError("the view adds a score")
    if "work_meters" in source:
        raise AssertionError("the view uses template meters")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    if '("Activity data", st.Page(' not in app or 'url_path="activity"' not in app:
        raise AssertionError("Activity data is not in the nav")
    table = app[app.index("def _activity_table(") : app.index("\ndef page_activity(")]
    for heading in ("Date", "Workout", "Work", "Avg HR"):
        if heading not in table:
            raise AssertionError(f"the table omits {heading}")
    start = app.index("def page_activity(")
    page = app[start : app.index("\ndef ", start + 1)]
    for call in (
        "session_rows(",
        "weekly_completed_meters(",
        "heart_rate_chart(",
        "heart_rate_points(",
        "loaded_distances(",
        "file_heart_rates(",
        "_stored_season(",
        "_activity_table(",
        "volume_chart(",
    ):
        if call not in page:
            raise AssertionError(f"the page omits {call}")
    if "No matched activities." not in page:
        raise AssertionError("an empty record does not say so")
    if "explain(" in page or "classify(" in page or "sequence(" in page or "adapt(" in page:
        raise AssertionError("the page spends or classifies")
    if "fetch_activity" in page or "urlopen" in page or "list_activities" in page:
        raise AssertionError("the page calls the live API")
    if "work_meters" in page:
        raise AssertionError("the page uses template meters")
    if "probability" in page.lower() or "readiness" in page.lower():
        raise AssertionError("the page adds a score")
    season = (ROOT / "engines" / "season.py").read_text(encoding="utf-8")
    if "activity_view" in season or "page_activity" in season or "session_rows" in season:
        raise AssertionError("season.py was changed for this page")
    classify = (ROOT / "engines" / "classify.py").read_text(encoding="utf-8")
    if "activity_view" in classify or "not pulled" in classify or "session_rows" in classify:
        raise AssertionError("classification was changed for this page")


def main() -> None:
    test_only_matched_activities_are_listed_newest_first()
    test_a_repeated_label_keeps_the_id()
    test_stored_header_and_hr_show_and_the_rest_is_not_pulled()
    test_streams_show_only_when_present_and_stay_not_pulled()
    test_a_row_is_one_matched_session()
    test_weekly_work_is_matched_distance_only()
    test_a_loaded_file_supplies_work_and_heart_rate()
    test_heart_rate_dots_are_labeled_with_the_date()
    test_the_page_lists_matched_activities_and_does_not_spend()
    print("activity data ok")


if __name__ == "__main__":
    main()
