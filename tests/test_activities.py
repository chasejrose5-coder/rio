# test_activities.py — recent activities match a planned day and stay in the browser.

from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import SPEND_CAP_MICRO_USD
from ui.activities import (
    HISTORY_START,
    NOT_CONNECTED_NOTICE,
    WINDOW_DAYS,
    activity_history,
    activity_window,
    extras_between,
    load_local_env,
    match_activities,
    merge_activities,
    with_matched_distances,
)
from ui.plan_store import dump_record, load_record

TODAY = date(2026, 10, 25)
PLANNED = [
    {"date": "2026-10-20", "template_id": "se_400_r90_x6", "day_of_week": "Tuesday"},
    {"date": "2026-10-22", "template_id": "aer_8000_r0_x1", "day_of_week": "Thursday"},
]


def _function(source: str, name: str) -> str:
    marker = f"def {name}("
    start = source.index(marker)
    nxt = source.find("\ndef ", start + len(marker))
    if nxt < 0:
        return source[start:]
    return source[start:nxt]


def _run(day: str, ident: object, start: str, *, kind: str = "Run", heart: float = 148) -> dict:
    return {
        "id": ident,
        "name": f"{kind} {ident}",
        "start_date_local": f"{day}T{start}",
        "type": kind,
        "distance": 99999,
        "average_heartrate": heart,
        "icu_intervals": [
            {"type": "WARMUP", "distance": 1600, "elapsed_time": 600, "average_heartrate": 180},
            {"type": "WORK", "distance": 400, "elapsed_time": 57.5, "average_heartrate": 176},
            {"type": "RECOVERY", "distance": 0, "elapsed_time": 90, "average_heartrate": 140},
            {"type": "WORK", "distance": 400, "elapsed_time": 58, "average_heartrate": 176},
            {"type": "COOLDOWN", "distance": 1600, "elapsed_time": 600, "average_heartrate": 130},
        ],
    }


def test_window_is_fourteen_days() -> None:
    """Today and the thirteen days before it. Both ends are included."""
    if WINDOW_DAYS != 14:
        raise AssertionError(WINDOW_DAYS)
    oldest, newest = activity_window(TODAY)
    if (oldest, newest) != ("2026-10-12", "2026-10-25"):
        raise AssertionError((oldest, newest))
    if (date.fromisoformat(newest) - date.fromisoformat(oldest)).days != 13:
        raise AssertionError("the window is not 14 days")


def test_a_run_on_a_planned_day_supplies_reps_volume_and_heart_rate() -> None:
    """The planned day uses WORK times, WORK distance, and the activity heart rate.

    Warm-up and the activity total stay out. A later activity that day is extra.
    A day with no planned session is extra. The earliest run wins over an earlier ride.
    """
    ride = _run("2026-10-20", "ride-1", "06:00:00", kind="Ride", heart=110)
    run = _run("2026-10-20", 44521, "08:00:00", heart=151)
    later = _run("2026-10-20", "later", "18:00:00", heart=160)
    easy = _run("2026-10-21", "easy", "07:00:00", heart=132)
    rows = match_activities(PLANNED, [later, ride, run, easy])
    by_id = {row["id"]: row for row in rows}
    matched = by_id["44521"]
    if matched["matched"] is not True or matched["date"] != "2026-10-20":
        raise AssertionError(matched)
    if matched["template_id"] != "se_400_r90_x6":
        raise AssertionError(matched)
    if matched["reps"] != [57.5, 58]:
        raise AssertionError(matched["reps"])
    if matched["work_m"] != 800:
        raise AssertionError(matched["work_m"])
    if matched["heart_rate"] != 151:
        raise AssertionError(matched["heart_rate"])
    if matched.get("distance") != 99999:
        raise AssertionError("the activity distance was not stored")
    if matched["work_m"] == 99999 or 180 in (matched["heart_rate"],):
        raise AssertionError("activity total or a lap heart rate was used")
    if by_id["ride-1"]["matched"] is not False or by_id["later"]["matched"] is not False:
        raise AssertionError("another activity on that day was treated as the session")
    if "template_id" in by_id["ride-1"] or by_id["easy"]["matched"] is not False:
        raise AssertionError("an unmatched activity was given the planned template")
    if {row["id"] for row in rows if row["date"] == "2026-10-22"}:
        raise AssertionError("a planned day with no activity invented a match")
    if by_id["easy"].get("distance") != 99999:
        raise AssertionError("an extra activity dropped its distance")
    zero = _run("2026-10-21", "zero", "07:30:00")
    zero["distance"] = 0
    zero["average_heartrate"] = None
    zeroed = match_activities(PLANNED, [zero])
    if len(zeroed) != 1 or "distance" in zeroed[0] or "heart_rate" in zeroed[0]:
        raise AssertionError(zeroed[0])
    if zeroed[0]["work_m"] == 0:
        raise AssertionError("a zero activity distance became the WORK distance")


def test_only_a_ride_still_matches_the_day() -> None:
    """A planned date with no run uses the earliest activity."""
    early = _run("2026-10-22", "early", "06:00:00", kind="Ride")
    late = _run("2026-10-22", "late", "09:00:00", kind="Ride")
    rows = match_activities(PLANNED, [late, early])
    matched = [row for row in rows if row["matched"]]
    if len(matched) != 1 or matched[0]["id"] != "early":
        raise AssertionError(rows)


def test_history_covers_every_activity_through_today() -> None:
    """Activity data asks from 1970-01-01 through today. Both ends are included."""
    if HISTORY_START != date(1970, 1, 1):
        raise AssertionError(HISTORY_START)
    oldest, newest = activity_history(TODAY)
    if (oldest, newest) != ("1970-01-01", "2026-10-25"):
        raise AssertionError((oldest, newest))
    if oldest == activity_window(TODAY)[0]:
        raise AssertionError("activity data still uses the 14-day window")


def test_a_stored_match_survives_a_reload_and_a_window_merge() -> None:
    """Rows outside a window stay. A reload keeps reps, work, and distance."""
    stored = match_activities(PLANNED, [_run("2026-10-20", "44521", "08:00:00")])
    oldest, newest = activity_window(TODAY)
    kept = merge_activities(stored, [], "2026-10-01", "2026-10-01")
    if kept != stored:
        raise AssertionError("a range that misses the stored day dropped it")
    replaced = merge_activities(stored, [], oldest, newest)
    if replaced:
        raise AssertionError("the window was not the part an empty pull replaces")
    raw = dump_record({}, {}, stored)
    _marks, _actuals, activities = load_record(raw)
    if activities != load_record(dump_record({}, {}, activities))[2]:
        raise AssertionError("a reload did not keep the match")
    if activities[0]["reps"] != [57.5, 58] or activities[0]["work_m"] != 800:
        raise AssertionError(activities[0])
    if activities[0].get("distance") != 99999:
        raise AssertionError("a reload dropped the activity distance")
    if "probability" in raw or "readiness" in raw:
        raise AssertionError("a score was stored with the match")


def test_matched_distance_fills_completed_volume() -> None:
    """A matched day uses the activity. A file distance remains on a day with no match."""
    activities = [
        {"id": "1", "date": "2026-10-20", "matched": True, "work_m": 800, "name": ""},
        {"id": "2", "date": "2026-10-21", "matched": False, "work_m": 5000, "name": ""},
    ]
    distances = with_matched_distances({"2026-10-20": 100, "2026-10-22": 4000}, activities)
    if distances != {"2026-10-20": 800, "2026-10-22": 4000}:
        raise AssertionError(distances)
    extras = extras_between(activities, "2026-10-12", "2026-10-25")
    if [row["id"] for row in extras] != ["2"]:
        raise AssertionError(extras)


def test_local_env_keeps_an_existing_value() -> None:
    """A value already in the environment wins over the same name in a file."""
    name = "RIO_TEST_ENV_SAMPLE"
    previous = os.environ.get(name)
    os.environ[name] = "already-set"
    try:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(f'export {name}="from-file"\n', encoding="utf-8")
            load_local_env([path])
            if os.environ.get(name) != "already-set":
                raise AssertionError("an existing value was replaced")
            os.environ.pop(name, None)
            load_local_env([path])
            if os.environ.get(name) != "from-file":
                raise AssertionError(os.environ.get(name))
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def test_pages_do_not_fetch_another_activity_source() -> None:
    """Opening a page restores stored runs. It does not call another service."""
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    if NOT_CONNECTED_NOTICE != "Strava is not configured.":
        raise AssertionError(NOT_CONNECTED_NOTICE)
    source = (ROOT / "ui" / "activities.py").read_text(encoding="utf-8")
    if "list_activities" in source or "fetch_activity" in source or "sync_recent" in source or "sync_all" in source:
        raise AssertionError("activities.py still fetches from another source")
    if "from engines" in source or "explain(" in source or "print(" in source:
        raise AssertionError("the match started prose spend or printed a value")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    block = app[app.index("_PULL_PAGES"):app.index("def _pull_for(")]
    for name in (
        "page_dashboard",
        "page_weekly",
        "page_session",
        "page_progress",
        "page_activity",
    ):
        if name not in block:
            raise AssertionError(f"{name} does not open a pull")
    wrapper = _function(app, "_with_plan")
    pull_shell = _function(app, "_pull_for")
    pull_for = _function(
        (ROOT / "services" / "activity_pull.py").read_text(encoding="utf-8"),
        "run_activity_pull",
    )
    if 'st.session_state.get("activity-refresh") is True' not in pull_shell:
        raise AssertionError("refresh does not read activities again")
    if "sync_recent(" in pull_for or "sync_all(" in pull_for:
        raise AssertionError("opening a page still syncs another source")
    if "NOT_CONNECTED_NOTICE" not in pull_for:
        raise AssertionError("a disconnected account does not say Strava is missing")
    if "_pull_for(" not in wrapper or "run_activity_pull(" not in pull_shell:
        raise AssertionError("opening a page does not restore runs")
    if wrapper.index("_pull_for(") > wrapper.index("_sync_browser_store("):
        raise AssertionError("matches are written before the pull")
    if '"load"' not in pull_for:
        raise AssertionError("the first page does not pull")
    restore = _function(app, "_restore_record")
    store = _function(app, "_sync_browser_store")
    local = (ROOT / "services" / "season_store.py").read_text(encoding="utf-8")
    if "season_activities" not in restore or "season_activities" not in store:
        raise AssertionError("a reload drops the matches")
    if "read_record(" not in local or "write_record(" not in local:
        raise AssertionError("a reload drops the matches")
    if "list_activities" in app or "fetch_activity" in app or "urlopen" in app:
        raise AssertionError("the page calls the live API directly")
    if ("https://intervals" + ".icu") in app or "SPEND_CAP" in app or "explain(" in pull_for:
        raise AssertionError("the pull started spending")
    weekly = app[app.index("def page_weekly(") : app.index("\ndef page_season(")]
    progress = app[app.index("def page_progress(") : app.index("\ndef page_weekly(")]
    session = _function(app, "page_session")
    if "with_matched_distances(" not in weekly or "loaded_distances(" not in weekly:
        raise AssertionError("weekly volume ignores a matched activity")
    if "_render_extras(" not in weekly or "_activities_notice(" not in weekly:
        raise AssertionError("weekly hides extra sessions")
    if "with_matched_distances(" not in progress or "loaded_distances(" not in progress:
        raise AssertionError("progress volume ignores a matched activity")
    if "fetch_activity" in weekly or "urlopen" in weekly or "explain(" in weekly:
        raise AssertionError("weekly calls the network or the model")
    if "fetch_activity" in progress or "urlopen" in progress or "explain(" in progress:
        raise AssertionError("progress calls the network or the model")
    supplied = _function(app, "_supplied_html")
    if "_supplied_html(" not in session or "rio-session-split" not in session:
        raise AssertionError("matched data is not beside the template")
    if "heart_rate_text(" not in session or "Avg HR" not in session:
        raise AssertionError("a matched day does not show heart rate")
    if "Reps" not in supplied or "Work" not in supplied or "Avg HR" not in supplied:
        raise AssertionError("a matched day does not show reps, work, or heart rate")
    if 'match.get("reps")' not in supplied or 'match.get("work_m")' not in supplied:
        raise AssertionError("the session page does not read the matched activity")
    if 'match.get("distance")' in supplied or "activity_distance(" in supplied:
        raise AssertionError("completed work uses the activity total")
    if "_render_logged_activity(" not in session:
        raise AssertionError("an extra session is hidden")
    if "disabled" in _function(app, "_time_box"):
        raise AssertionError("the time boxes are locked")
    if "fetch_activity" in session or "urlopen" in session or "explain(" in session:
        raise AssertionError("the session page calls the network or spends")
    engines = ROOT / "engines"
    for path in engines.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "list_activities" in text or "sync_recent" in text or "sync_all" in text:
            raise AssertionError(f"{path.name} was changed for the pull")


def main() -> None:
    test_window_is_fourteen_days()
    test_history_covers_every_activity_through_today()
    test_a_run_on_a_planned_day_supplies_reps_volume_and_heart_rate()
    test_only_a_ride_still_matches_the_day()
    test_a_stored_match_survives_a_reload_and_a_window_merge()
    test_matched_distance_fills_completed_volume()
    test_local_env_keeps_an_existing_value()
    test_pages_do_not_fetch_another_activity_source()
    print("activities ok")


if __name__ == "__main__":
    main()
