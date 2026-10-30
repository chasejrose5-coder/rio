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

from adapters.intervals_icu import IntervalsIcuError
from engines.explain import SPEND_CAP_MICRO_USD
from ui.activities import (
    HISTORY_START,
    MAX_FETCH,
    WINDOW_DAYS,
    PullError,
    activity_history,
    activity_window,
    extras_between,
    load_local_env,
    match_activities,
    merge_activities,
    sync_all,
    sync_recent,
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
    nxt = source.index("\ndef ", start + len(marker))
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


def test_pull_all_lists_every_activity_and_matches_by_date() -> None:
    """The list is the whole history. An older planned day still matches.

    WORK distance and the activity heart rate are kept. Warm-up and the
    activity total stay out. A day with no planned session stays extra.
    """
    planned = [
        {"date": "2024-06-02", "template_id": "se_400_r90_x6", "day_of_week": "Sunday"},
        {"date": "2026-10-20", "template_id": "aer_8000_r0_x1", "day_of_week": "Tuesday"},
    ]
    seen = {"env": False, "listed": None, "fetched": []}

    def load_env() -> None:
        seen["env"] = True

    def list_fn(oldest: str, newest: str) -> list[dict]:
        if seen["env"] is not True:
            raise AssertionError("the list ran before the local key was loaded")
        seen["listed"] = (oldest, newest)
        return [
            {"id": "old", "start_date_local": "2024-06-02T08:00:00"},
            {"id": "extra", "start_date_local": "2024-06-03T08:00:00"},
            {"id": "new", "start_date_local": "2026-10-20T08:00:00"},
        ]

    def fetch_fn(activity_id: object) -> dict:
        seen["fetched"].append(activity_id)
        days = {"old": "2024-06-02", "extra": "2024-06-03", "new": "2026-10-20"}
        return _run(days[str(activity_id)], activity_id, "08:00:00")

    rows = sync_all(planned, [], TODAY, list_fn=list_fn, fetch_fn=fetch_fn, load_env=load_env)
    if seen["listed"] != activity_history(TODAY):
        raise AssertionError(seen["listed"])
    if seen["listed"] == activity_window(TODAY):
        raise AssertionError("the list was the last 14 days")
    if sorted(seen["fetched"]) != ["extra", "new", "old"]:
        raise AssertionError(seen["fetched"])
    by_id = {row["id"]: row for row in rows}
    matched = by_id["old"]
    if matched["matched"] is not True or matched["date"] != "2024-06-02":
        raise AssertionError(matched)
    if matched["template_id"] != "se_400_r90_x6" or matched["work_m"] != 800:
        raise AssertionError(matched)
    if matched["heart_rate"] != 148 or matched["work_m"] == 99999:
        raise AssertionError("warm-up or the activity total replaced WORK distance")
    if matched.get("distance") != 99999 or by_id["extra"].get("distance") != 99999:
        raise AssertionError("the activity distance was not stored")
    if by_id["extra"]["matched"] is not False or "template_id" in by_id["extra"]:
        raise AssertionError(by_id["extra"])
    if by_id["new"]["matched"] is not True or by_id["new"]["work_m"] != 800:
        raise AssertionError(by_id["new"])


def test_pull_all_fetches_every_listed_activity() -> None:
    """The 14-day cap does not drop an older activity."""
    fetched = []
    count = MAX_FETCH + 3

    def list_fn(oldest: str, newest: str) -> list[dict]:
        if (oldest, newest) != activity_history(TODAY):
            raise AssertionError((oldest, newest))
        return [
            {
                "id": f"id-{number:02d}",
                "start_date_local": f"2020-01-01T00:{number % 60:02d}:00",
                "type": "Run",
            }
            for number in range(count)
        ]

    def fetch_fn(activity_id: object) -> dict:
        fetched.append(activity_id)
        return {
            "id": activity_id,
            "name": str(activity_id),
            "start_date_local": "2020-01-01T08:00:00",
            "type": "Run",
        }

    sync_all([], [], TODAY, list_fn=list_fn, fetch_fn=fetch_fn, load_env=lambda: None)
    if len(fetched) != count:
        raise AssertionError(len(fetched))
    if "id-00" not in fetched:
        raise AssertionError("an older activity was left out")


def test_a_failed_history_list_keeps_stored_matches() -> None:
    """A list failure leaves the stored matches in place. The message has no key."""
    stored = match_activities(PLANNED, [_run("2026-10-20", "44521", "08:00:00")])
    secret = "local-athlete-key"

    def list_fn(oldest: str, newest: str) -> list[dict]:
        raise IntervalsIcuError("Intervals.icu returned 401 Unauthorized. Check RIO_INTERVALS_API_KEY.")

    try:
        sync_all(PLANNED, stored, TODAY, list_fn=list_fn, load_env=lambda: None)
    except PullError as exc:
        message = str(exc)
    else:
        raise AssertionError("a failed list still returned rows")
    if secret in message:
        raise AssertionError("the failure included a key")
    oldest, newest = activity_history(TODAY)
    kept = merge_activities(stored, [], "2026-10-26", "2026-10-26")
    if kept != stored:
        raise AssertionError("a day after today was treated as part of the history")
    replaced = merge_activities(stored, [], oldest, newest)
    if replaced:
        raise AssertionError("a successful empty history pull did not replace the stored day")


def test_pull_lists_the_window_and_fetches_each_activity() -> None:
    """The list call is the last 14 days. Each id is fetched. The local env is read first."""
    seen = {"env": False, "listed": None, "fetched": []}

    def load_env() -> None:
        seen["env"] = True

    def list_fn(oldest: str, newest: str) -> list[dict]:
        if seen["env"] is not True:
            raise AssertionError("the list ran before the local key was loaded")
        seen["listed"] = (oldest, newest)
        return [
            {"id": "a", "start_date_local": "2026-10-20T08:00:00"},
            {"id": "b", "start_date_local": "2026-10-21T08:00:00"},
        ]

    def fetch_fn(activity_id: object) -> dict:
        seen["fetched"].append(activity_id)
        day = "2026-10-20" if activity_id == "a" else "2026-10-21"
        return _run(day, activity_id, "08:00:00")

    rows = sync_recent(PLANNED, [], TODAY, list_fn=list_fn, fetch_fn=fetch_fn, load_env=load_env)
    if seen["listed"] != activity_window(TODAY):
        raise AssertionError(seen["listed"])
    if seen["fetched"] != ["b", "a"] and sorted(seen["fetched"]) != ["a", "b"]:
        raise AssertionError(seen["fetched"])
    matched = [row for row in rows if row["id"] == "a"][0]
    if matched["matched"] is not True or matched["work_m"] != 800:
        raise AssertionError(matched)


def test_a_failed_detail_keeps_the_listed_row() -> None:
    """One activity that will not open still occupies its day. The others are kept."""

    def list_fn(oldest: str, newest: str) -> list[dict]:
        return [
            {"id": "good", "name": "Good", "start_date_local": "2026-10-20T08:00:00", "type": "Run"},
            {"id": "bad", "name": "Bad", "start_date_local": "2026-10-21T08:00:00", "type": "Run"},
        ]

    def fetch_fn(activity_id: object) -> dict:
        if activity_id == "bad":
            raise IntervalsIcuError("Intervals.icu returned 404 Not Found.")
        return _run("2026-10-20", "good", "08:00:00")

    rows = sync_recent(
        PLANNED,
        [],
        TODAY,
        list_fn=list_fn,
        fetch_fn=fetch_fn,
        load_env=lambda: None,
    )
    by_id = {row["id"]: row for row in rows}
    if "reps" in by_id["bad"] or by_id["bad"]["matched"] is not False:
        raise AssertionError(by_id["bad"])
    if by_id["good"]["reps"] != [57.5, 58]:
        raise AssertionError(by_id["good"])


def test_fetch_stops_after_the_newest_forty() -> None:
    """A long list does not fetch every id. The newest days are the ones kept."""
    fetched = []

    def list_fn(oldest: str, newest: str) -> list[dict]:
        rows = []
        for number in range(MAX_FETCH + 1):
            rows.append(
                {
                    "id": f"id-{number:02d}",
                    "start_date_local": f"2026-10-01T00:{number:02d}:00" if number < 60 else "2026-09-01T00:00:00",
                    "type": "Run",
                }
            )
        return rows

    def fetch_fn(activity_id: object) -> dict:
        fetched.append(activity_id)
        return {
            "id": activity_id,
            "name": str(activity_id),
            "start_date_local": "2026-10-21T08:00:00",
            "type": "Run",
        }

    sync_recent([], [], TODAY, list_fn=list_fn, fetch_fn=fetch_fn, load_env=lambda: None)
    if len(fetched) != MAX_FETCH:
        raise AssertionError(len(fetched))
    if "id-00" in fetched:
        raise AssertionError("the oldest activity was fetched past the cap")


def test_reload_keeps_matches_outside_a_failed_pull() -> None:
    """A list failure leaves the stored matches in place. The message has no key."""
    stored = match_activities(PLANNED, [_run("2026-10-20", "44521", "08:00:00")])
    secret = "local-athlete-key"

    def list_fn(oldest: str, newest: str) -> list[dict]:
        raise IntervalsIcuError("Intervals.icu returned 401 Unauthorized. Check RIO_INTERVALS_API_KEY.")

    try:
        sync_recent(PLANNED, stored, TODAY, list_fn=list_fn, load_env=lambda: None)
    except PullError as exc:
        message = str(exc)
    else:
        raise AssertionError("a failed list still returned rows")
    if secret in message or "local-athlete-key" in message:
        raise AssertionError("the failure included a key")
    if "401" not in message:
        raise AssertionError(message)
    oldest, newest = activity_window(TODAY)
    kept = merge_activities(stored, [], "2026-10-01", "2026-10-01")
    if kept != stored:
        raise AssertionError("a range that misses the stored day dropped it")
    replaced = merge_activities(stored, [], oldest, newest)
    if replaced:
        raise AssertionError("the window was not the part a successful empty pull replaces")
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


def test_local_env_keeps_an_existing_key_and_reads_the_athlete() -> None:
    """A key already in the environment wins. An unset athlete id comes from that file."""
    previous = {
        "RIO_INTERVALS_API_KEY": os.environ.get("RIO_INTERVALS_API_KEY"),
        "RIO_INTERVALS_ATHLETE_ID": os.environ.get("RIO_INTERVALS_ATHLETE_ID"),
    }
    os.environ["RIO_INTERVALS_API_KEY"] = "already-set"
    os.environ.pop("RIO_INTERVALS_ATHLETE_ID", None)
    try:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "\n".join(
                    [
                        "# comment",
                        "export RIO_INTERVALS_API_KEY=\"from-file\"",
                        "RIO_INTERVALS_ATHLETE_ID='athlete-9'",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            load_local_env([path])
        if os.environ.get("RIO_INTERVALS_API_KEY") != "already-set":
            raise AssertionError("an existing key was replaced")
        if os.environ.get("RIO_INTERVALS_ATHLETE_ID") != "athlete-9":
            raise AssertionError(os.environ.get("RIO_INTERVALS_ATHLETE_ID"))
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def test_unprefixed_env_names_fill_the_rio_names() -> None:
    """INTERVALS_API_KEY in .env is the local key when the RIO_ name is unset."""
    names = (
        "RIO_INTERVALS_API_KEY",
        "RIO_INTERVALS_ATHLETE_ID",
        "INTERVALS_API_KEY",
        "INTERVALS_ATHLETE_ID",
    )
    previous = {name: os.environ.get(name) for name in names}
    for name in names:
        os.environ.pop(name, None)
    try:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "INTERVALS_API_KEY=alias-key\nINTERVALS_ATHLETE_ID=athlete-4\n",
                encoding="utf-8",
            )
            load_local_env([path])
        if os.environ.get("RIO_INTERVALS_API_KEY") != "alias-key":
            raise AssertionError("the local key was not read")
        if os.environ.get("RIO_INTERVALS_ATHLETE_ID") != "athlete-4":
            raise AssertionError("the local athlete id was not read")
        os.environ["RIO_INTERVALS_API_KEY"] = "already-set"
        os.environ["INTERVALS_API_KEY"] = "other-key"
        load_local_env([path])
        if os.environ.get("RIO_INTERVALS_API_KEY") != "already-set":
            raise AssertionError("an existing key was replaced")
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def test_pull_uses_the_adapter_and_does_not_spend() -> None:
    """The app asks for the last 14 days when a live page opens.

    Dashboard, Weekly, Session, Progress, and Activity data use that pull.
    Refresh on Activity data lists every activity. The page functions stay
    off the network. Engines are not used for the match. Prose spend stays
    capped at $25.
    """
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    source = (ROOT / "ui" / "activities.py").read_text(encoding="utf-8")
    pull = _function(source, "_pull")
    recent = _function(source, "pull_recent")
    history = _function(source, "pull_all")
    if "list_activities(oldest, newest)" not in pull:
        raise AssertionError("the pull does not call list_activities")
    if "fetch_activity(activity_id)" not in pull:
        raise AssertionError("the pull does not read the activity")
    if "load_local_env" not in pull:
        raise AssertionError("the pull does not load the local key")
    if "activity_window(today)" not in recent or "limit=MAX_FETCH" not in recent:
        raise AssertionError("the 14-day pull changed")
    if "activity_history(today)" not in history or "limit=None" not in history:
        raise AssertionError("activity data does not ask for every activity")
    if "MAX_FETCH" in history or "activity_window" in history:
        raise AssertionError("activity data still uses the 14-day window")
    if "from engines" in source or "explain(" in source or "print(" in source:
        raise AssertionError("the pull started prose spend or printed a value")
    if "athlete_id" in pull or "api_key" in pull:
        raise AssertionError("the pull picks an athlete or a key of its own")
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
    pull_for = _function(app, "_pull_for")
    if 'st.session_state.get("activity-refresh") is True' not in pull_for:
        raise AssertionError("refresh does not read activities again")
    branches = pull_for.split("if refresh:", 1)[1]
    history, recent = branches.split("else:", 1)
    if "sync_all(" not in history or "sync_recent(" in history:
        raise AssertionError("refresh does not read every activity")
    if "sync_recent(" not in recent:
        raise AssertionError("opening a live page does not read the last 14 days")
    if "_pull_for(" not in wrapper or "sync_recent(" not in pull_for:
        raise AssertionError("opening a page does not pull")
    if wrapper.index("_pull_for(") > wrapper.index("_sync_browser_store("):
        raise AssertionError("matches are written before the pull")
    if '"load"' not in pull_for:
        raise AssertionError("the first page does not pull")
    restore = _function(app, "_restore_record")
    store = _function(app, "_sync_browser_store")
    if "season_activities" not in restore or "season_activities" not in store:
        raise AssertionError("a reload drops the matches")
    if "list_activities" in app or "fetch_activity" in app or "urlopen" in app:
        raise AssertionError("the page calls the live API directly")
    if "https://intervals.icu" in app or "SPEND_CAP" in app or "explain(" in pull_for:
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
    if "heart_rate_text(" not in session or "Avg HR" not in session:
        raise AssertionError("a matched day does not show heart rate")
    if "Reps" not in session or "Volume" not in session or "_render_logged_activity(" not in session:
        raise AssertionError("a matched day does not show reps, volume, or an extra")
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
    test_pull_all_lists_every_activity_and_matches_by_date()
    test_pull_all_fetches_every_listed_activity()
    test_a_failed_history_list_keeps_stored_matches()
    test_pull_lists_the_window_and_fetches_each_activity()
    test_a_failed_detail_keeps_the_listed_row()
    test_fetch_stops_after_the_newest_forty()
    test_reload_keeps_matches_outside_a_failed_pull()
    test_matched_distance_fills_completed_volume()
    test_local_env_keeps_an_existing_key_and_reads_the_athlete()
    test_unprefixed_env_names_fill_the_rio_names()
    test_pull_uses_the_adapter_and_does_not_spend()
    print("activities ok")


if __name__ == "__main__":
    main()
