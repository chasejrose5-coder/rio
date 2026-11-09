# test_activity_data.py — matched workouts, work meters, heart rate, no invented file.

from __future__ import annotations

import sys
from datetime import date, timedelta
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
    all_activities,
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
        [{"id": "a", "matched": True, "date": "2026-04-21", "name": "Long Z2 Test", "heart_rate": 151}],
        [],
        date_format="short",
    )
    if short[0]["shown_date"] != "Apr 21, 2026" or short[0]["label"] != "Long Z2 Test":
        raise AssertionError(short[0])
    if short[0]["work"] != "—" or short[0]["hr"] != "151 bpm" or short[0]["meters"] is not None:
        raise AssertionError("a missing file invented work")
    empty = session_rows(
        [{"id": "empty", "matched": True, "date": "2026-04-22", "name": "Empty"}],
        PLAN,
    )
    if empty:
        raise AssertionError("an empty activity was listed")
    named = session_rows(
        [{"id": "a", "matched": True, "date": "2026-04-21", "template_id": "custom_thing", "name": "", "work_m": 400}],
        [],
    )
    if named[0]["label"] != "custom_thing":
        raise AssertionError(named[0]["label"])


def test_every_activity_is_listed_and_an_unmatched_row_is_extra() -> None:
    """Date, name, activity distance, and average heart rate.

    The matched table still lists only a planned day with work or heart
    rate. WORK meters are not the activity distance. An activity with no
    distance and no heart rate stays off both lists.
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
            "start": "2026-04-28T07:00:00",
            "name": "Easy",
            "work_m": 8000,
            "heart_rate": 170,
            "distance": 8200,
        },
        {
            "id": "hr-only",
            "matched": False,
            "date": "2026-04-22",
            "name": "Spin",
            "heart_rate": 132,
            "work_m": 400,
        },
        {
            "id": "distance-only",
            "matched": True,
            "date": "2026-04-20",
            "name": "  Walk  ",
            "distance": 3000,
        },
        {
            "id": "work-only",
            "matched": True,
            "date": "2026-04-19",
            "name": "Intervals",
            "work_m": 800,
        },
        {
            "id": "empty",
            "matched": False,
            "date": "2026-04-18",
            "name": "Empty",
            "distance": 0,
        },
        {
            "id": "",
            "matched": False,
            "date": "2026-04-30",
            "name": "Blank",
            "distance": 1000,
            "heart_rate": 140,
        },
        "nope",
    ]
    rows = all_activities(activities)
    if [row["id"] for row in rows] != ["extra", "long", "hr-only", "a", "distance-only"]:
        raise AssertionError([row["id"] for row in rows])
    easy = rows[0]
    if easy["name"] != "Easy" or easy["extra"] is not True or easy["distance"] != "8,200 m":
        raise AssertionError(easy)
    if easy["hr"] != "170 bpm" or easy["meters"] != 8200 or easy["meters"] == 8000:
        raise AssertionError("WORK meters replaced the activity distance")
    speed = next(row for row in rows if row["id"] == "a")
    if speed["extra"] is not False or speed["name"] != "Synthetic 6 x 400":
        raise AssertionError(speed)
    if speed["distance"] != "5,600 m" or speed["meters"] != 5600 or speed["hr"] != "151 bpm":
        raise AssertionError(speed)
    if speed["meters"] == 800:
        raise AssertionError("WORK meters replaced the activity distance")
    spin = next(row for row in rows if row["id"] == "hr-only")
    if spin["extra"] is not True or spin["distance"] != "—" or spin["hr"] != "132 bpm":
        raise AssertionError(spin)
    if spin["meters"] is not None:
        raise AssertionError("WORK meters were shown as the activity distance")
    walk = next(row for row in rows if row["id"] == "distance-only")
    if walk["name"] != "Walk" or walk["hr"] != "—" or walk["meters"] != 3000 or walk["extra"] is not False:
        raise AssertionError(walk)
    if any(row["id"] in {"work-only", "empty"} for row in rows):
        raise AssertionError("an empty activity was listed")
    if any("probability" in row or "readiness" in row for row in rows):
        raise AssertionError("a score was added")
    short = all_activities(
        [{"id": "a", "matched": False, "date": "2026-04-21", "name": "", "heart_rate": 151}],
        date_format="short",
    )
    if short[0]["shown_date"] != "Apr 21, 2026" or short[0]["name"] != "—":
        raise AssertionError(short[0])
    if short[0]["extra"] is not True or short[0]["distance"] != "—":
        raise AssertionError(short[0])
    matched = session_rows(activities, PLAN)
    if [row["id"] for row in matched] != ["long", "a", "work-only"]:
        raise AssertionError([row["id"] for row in matched])
    if matched[1]["meters"] != 800 or matched[1]["label"] != "Speed endurance":
        raise AssertionError(matched[1])
    if "5,600" in matched[1]["work"] or matched[1]["meters"] == 5600:
        raise AssertionError("the activity distance replaced WORK meters")


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
    if 'fill="#f4f4f4"' not in svg or 'font-size="12"' not in svg:
        raise AssertionError("the date is still faint")
    if 'r="5"' not in svg or 'fill="#ff7a45"' not in svg:
        raise AssertionError("the dot is still faint")
    _assert_dates_clear_the_dots(svg)


def test_close_dates_stay_on_separate_rows() -> None:
    """Workouts a day apart keep their own date, off the other dates and the dot."""
    points = []
    captions = {}
    for index in range(6):
        day = date(2026, 4, 21) + timedelta(days=index)
        iso = day.isoformat()
        points.append({"date": iso, "bpm": 142 + index * 3})
        captions[iso] = iso
    svg = heart_rate_chart(
        points,
        start=date(2026, 4, 19),
        weeks=3,
        captions=captions,
    )
    if svg.count('class="rio-heart-dot"') != 6:
        raise AssertionError("a matched workout did not get its own dot")
    if "<polyline" in svg or "<line " in svg:
        raise AssertionError("close dates were connected")
    _assert_dates_clear_the_dots(svg)


def _assert_dates_clear_the_dots(svg: str) -> None:
    labels = _heart_labels(svg)
    dots = _heart_dot_points(svg)
    if not labels or len(labels) != len(dots):
        raise AssertionError("a dot has no date")
    if max(label[1] for label in labels) >= min(dot[1] for dot in dots):
        raise AssertionError("a date sits on its dot")
    for index, label in enumerate(labels):
        for other in labels[index + 1 :]:
            if abs(label[1] - other[1]) > 8:
                continue
            if label[2] + 8 <= other[0] or other[2] + 8 <= label[0]:
                continue
            raise AssertionError("two dates share a row")


def _heart_labels(svg: str) -> list[tuple[float, float, float]]:
    needle = 'class="rio-heart-label"'
    found = []
    start = 0
    while True:
        at = svg.find(needle, start)
        if at < 0:
            break
        tag_end = svg.find(">", at)
        tag = svg[svg.rfind("<text", 0, at) : tag_end]
        text_end = svg.find("</text>", tag_end)
        text = svg[tag_end + 1 : text_end]
        x = float(tag.split('x="')[1].split('"')[0])
        y = float(tag.split('y="')[1].split('"')[0])
        anchor = tag.split('text-anchor="')[1].split('"')[0]
        width = len(text) * 6.2
        if anchor == "start":
            left = x
        elif anchor == "end":
            left = x - width
        else:
            left = x - width / 2
        found.append((left, y, left + width))
        start = text_end
    return found


def _heart_dot_points(svg: str) -> list[tuple[float, float]]:
    needle = 'class="rio-heart-dot"'
    found = []
    start = 0
    while True:
        at = svg.find(needle, start)
        if at < 0:
            break
        tag_start = svg.rfind("<circle", 0, at)
        tag_end = svg.find(">", at)
        tag = svg[tag_start:tag_end]
        found.append(
            (
                float(tag.split('cx="')[1].split('"')[0]),
                float(tag.split('cy="')[1].split('"')[0]),
            )
        )
        start = tag_end
    return found


def test_the_page_lists_matched_activities_and_does_not_spend() -> None:
    """Activity data is in the nav. Opening it reads the last 14 days.

    Refresh reads every activity. The page does not classify, score, or call
    the model. The adapter is the only reader. Prose spend stays capped at
    $25. Season and classification stay untouched.
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
    if '("Activity", st.Page(' not in app or 'url_path="activity"' not in app:
        raise AssertionError("Activity is not in the nav")
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
    if 'st.button("Refresh", key="activity-refresh")' not in page:
        raise AssertionError("Activity data has no refresh")
    if "_activities_notice(" not in page:
        raise AssertionError("a failed pull is hidden")
    block = app[app.index("_PULL_PAGES") : app.index("def _pull_for(")]
    for name in (
        "page_dashboard",
        "page_weekly",
        "page_session",
        "page_progress",
        "page_activity",
    ):
        if name not in block:
            raise AssertionError(f"{name} does not pull on open")
    pull_shell = app[app.index("def _pull_for(") : app.index("\ndef _with_plan(")]
    pull_for = (ROOT / "services" / "activity_pull.py").read_text(encoding="utf-8")
    pull_for = pull_for[pull_for.index("def run_activity_pull(") :]
    if 'st.session_state.get("activity-refresh") is True' not in pull_shell:
        raise AssertionError("refresh does not read activities again")
    branches = pull_for.split("if refresh:", 1)[1]
    history, recent = branches.split("else:", 1)
    if "sync_all(" not in history or "sync_recent(" in history:
        raise AssertionError("refresh does not read every activity")
    if "sync_recent(" not in recent:
        raise AssertionError("opening Activity data does not read the last 14 days")
    if "explain(" in page or "classify(" in page or "sequence(" in page or "adapt(" in page:
        raise AssertionError("the page spends or classifies")
    if "fetch_activity" in page or "urlopen" in page or "list_activities" in page:
        raise AssertionError("the page calls the live API directly")
    if "work_meters" in page:
        raise AssertionError("the page uses template meters")
    if "probability" in page.lower() or "readiness" in page.lower():
        raise AssertionError("the page adds a score")
    season = (ROOT / "engines" / "season.py").read_text(encoding="utf-8")
    if "all_activities" in season or "activity_view" in season or "page_activity" in season:
        raise AssertionError("season.py was changed for this page")
    if "session_rows" in season:
        raise AssertionError("season.py was changed for this page")
    classify = (ROOT / "engines" / "classify.py").read_text(encoding="utf-8")
    if "all_activities" in classify or "activity_view" in classify or "not pulled" in classify:
        raise AssertionError("classification was changed for this page")
    if "session_rows" in classify:
        raise AssertionError("classification was changed for this page")
    listed = source[source.index("def all_activities(") : source.index("\ndef choice_labels(")]
    if 'get("distance")' not in listed or 'get("work_m")' in listed:
        raise AssertionError("the all-activities list uses WORK meters")
    if 'activity.get("matched") is not True' not in listed:
        raise AssertionError("an unmatched activity is not marked extra")
    all_table = app[app.index("def _all_activities_table(") : app.index("\ndef _activity_table(")]
    for heading in ("Date", "Activity", "Distance", "Avg HR"):
        if heading not in all_table:
            raise AssertionError(f"the all-activities table omits {heading}")
    if 'label = "extra"' not in all_table:
        raise AssertionError("an unmatched row is not labeled extra")
    if "Workout" in all_table:
        raise AssertionError("the all-activities table uses the matched workout label")
    if "all_activities(" not in page or "_all_activities_table(" not in page or "All activities" not in page:
        raise AssertionError("the page does not list every activity")
    tail = page[page.index("No matched activities.") :]
    if "return" in tail:
        raise AssertionError("an empty matched list hides the other activities")
    if "_activity_table(" not in tail or "_all_activities_table(" not in tail:
        raise AssertionError("one of the activity tables was removed")


def main() -> None:
    test_only_matched_activities_are_listed_newest_first()
    test_a_repeated_label_keeps_the_id()
    test_stored_header_and_hr_show_and_the_rest_is_not_pulled()
    test_streams_show_only_when_present_and_stay_not_pulled()
    test_a_row_is_one_matched_session()
    test_every_activity_is_listed_and_an_unmatched_row_is_extra()
    test_weekly_work_is_matched_distance_only()
    test_a_loaded_file_supplies_work_and_heart_rate()
    test_heart_rate_dots_are_labeled_with_the_date()
    test_close_dates_stay_on_separate_rows()
    test_the_page_lists_matched_activities_and_does_not_spend()
    print("activity data ok")


if __name__ == "__main__":
    main()
