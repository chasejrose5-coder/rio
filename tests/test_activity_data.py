# test_activity_data.py — matched activities, four groups, unstored fields say not pulled.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import SPEND_CAP_MICRO_USD
from ui.activity_data import (
    NOT_PULLED,
    activity_banner,
    activity_view,
    choice_labels,
    matched_activities,
)

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
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    if '("Activity data", st.Page(' not in app or 'url_path="activity"' not in app:
        raise AssertionError("Activity data is not in the nav")
    start = app.index("def page_activity(")
    page = app[start : app.index("\ndef ", start + 1)]
    for heading in ("Activity header", "Intervals", "HR summary", "Streams"):
        if heading not in page:
            raise AssertionError(f"the page omits {heading}")
    if 'st.selectbox("Activity"' not in page or "matched_activities(" not in page:
        raise AssertionError("the page has no matched-activity drop-down")
    if "activity_view(" not in page:
        raise AssertionError("the page does not use the four groups")
    if "explain(" in page or "classify(" in page or "sequence(" in page or "adapt(" in page:
        raise AssertionError("the page spends or classifies")
    if "fetch_activity" in page or "urlopen" in page or "list_activities" in page:
        raise AssertionError("the page calls the live API")
    if "probability" in page.lower() or "readiness" in page.lower():
        raise AssertionError("the page adds a score")
    season = (ROOT / "engines" / "season.py").read_text(encoding="utf-8")
    if "activity_view" in season or "page_activity" in season:
        raise AssertionError("season.py was changed for this page")
    classify = (ROOT / "engines" / "classify.py").read_text(encoding="utf-8")
    if "activity_view" in classify or "not pulled" in classify:
        raise AssertionError("classification was changed for this page")


def main() -> None:
    test_only_matched_activities_are_listed_newest_first()
    test_a_repeated_label_keeps_the_id()
    test_stored_header_and_hr_show_and_the_rest_is_not_pulled()
    test_streams_show_only_when_present_and_stay_not_pulled()
    test_the_page_lists_matched_activities_and_does_not_spend()
    print("activity data ok")


if __name__ == "__main__":
    main()
