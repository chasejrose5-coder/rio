# test_no_watch.py — Done finishes a workout. A blank time stays blank.

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.accounts import create_account, read_local, write_local
from ui.cloud_store import no_watch_value, reset_memory_directory
from ui.no_watch import (
    finish_session,
    missed_session,
    next_open_workout,
    quality_day,
    session_completed,
    timed_mark,
)
from ui.plan_store import dump_record, load_record
from ui.recap import recap_view
from ui.settings import DEFAULTS, normalize

EASY = {
    "date": "2026-11-09",
    "day_of_week": "Monday",
    "template_id": "aer_5000_r0_x1",
    "week_number": 1,
}
LONG = {
    "date": "2026-11-14",
    "day_of_week": "Saturday",
    "template_id": "aer_12000_r0_x1",
    "week_number": 1,
}
HARD = {
    "date": "2026-11-10",
    "day_of_week": "Tuesday",
    "template_id": "se_400_r90_x6",
    "week_number": 1,
}
RECOVERY = {
    "date": "2026-11-10",
    "day_of_week": "Tuesday",
    "template_id": "aer_5000_r0_x1",
    "week_number": 1,
}
TODAY = date(2026, 11, 9)


def _function(source: str, name: str) -> str:
    start = source.index(f"def {name}(")
    rest = source[start + 1 :]
    nxt = rest.find("\ndef ")
    if nxt < 0:
        return source[start:]
    return source[start : start + 1 + nxt]


def test_the_toggle_is_off_until_someone_turns_it_on() -> None:
    """A new account does not get Done-only logging. A bad value stays off."""
    if DEFAULTS["no_watch"] is not False:
        raise AssertionError(DEFAULTS["no_watch"])
    clean = normalize(None)
    if clean["no_watch"] is not False or clean != DEFAULTS:
        raise AssertionError(clean)
    if normalize({"no_watch": "yes"})["no_watch"] is not False:
        raise AssertionError("a word turned the toggle on")
    if normalize({"no_watch": 1})["no_watch"] is not False:
        raise AssertionError("a number turned the toggle on")
    if normalize({"no_watch": True})["no_watch"] is not True:
        raise AssertionError("an explicit on was dropped")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    page = _function(app, "page_settings")
    for label in (
        "Logging",
        "I don't use a watch",
        "Complete workouts with Done instead of entering splits.",
        "settings-no-watch",
    ):
        if label not in page:
            raise AssertionError(label)
    if "_save_hosted_no_watch(" not in page:
        raise AssertionError("a hosted account does not keep the toggle")


def test_done_stays_off_the_session_until_the_toggle_is_on() -> None:
    """With the toggle off, the session still logs through the result boxes."""
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    page = _function(app, "page_session")
    watch = page.index("if _no_watch():")
    done = page.index("_render_watchless(")
    quality = page.index("elif _quality_day(session):")
    result = page.index("_render_result(")
    if not (watch < done < quality < result):
        raise AssertionError("Done replaced the result boxes")
    home = _function(app, "page_dashboard")
    if home.index("if _no_watch():") > home.index("_render_watchless("):
        raise AssertionError("Home shows Done before the toggle is read")
    if "next_open_workout(" not in home or "_athlete_today()" not in home:
        raise AssertionError("Home does not move past a finished day")
    if "date.today()" in home:
        raise AssertionError("Home left the saved time zone")


def test_easy_and_long_done_do_not_invent_a_time() -> None:
    """Done completes the day. Behind, on target, and ahead stay off. No splits."""
    if quality_day(EASY) or quality_day(LONG) or quality_day(RECOVERY):
        raise AssertionError("an easy or long run was treated as hard")
    for session in (EASY, LONG, RECOVERY):
        result = finish_session(session, "ahead", "")
        if not result["ok"] or not isinstance(result["row"], dict):
            raise AssertionError(result)
        row = result["row"]
        if row.get("completed") is not True or row.get("numbers") != [] or row.get("text") != "":
            raise AssertionError(row)
        if "mark" in row or "slots" in row or "pace" in row:
            raise AssertionError(row)
        if timed_mark(row) is not None:
            raise AssertionError("a blank Done became a timed effort")
    missed = missed_session(EASY)
    if missed is None or missed.get("missed") is not True or missed.get("completed") is True:
        raise AssertionError(missed)
    if missed.get("numbers") != [] or "mark" in missed:
        raise AssertionError(missed)
    bad = finish_session(EASY, None, "6 x 72")
    if bad["ok"] or bad["row"] is not None:
        raise AssertionError("rep splits were accepted")
    if finish_session(EASY, None, "400 m")["ok"]:
        raise AssertionError("a distance was stored as a time")


def test_a_hard_day_needs_one_of_the_three_choices() -> None:
    """Behind, on target, and ahead reuse the stored quality marks."""
    if not quality_day(HARD):
        raise AssertionError("Tuesday work was not a hard day")
    missing = finish_session(HARD, None, "")
    if missing["ok"] or missing["row"] is not None:
        raise AssertionError("a hard day finished with no choice")
    if "behind" not in missing["error"] or "on target" not in missing["error"]:
        raise AssertionError(missing["error"])
    expected = {
        "Behind": "not_hitting",
        "behind": "not_hitting",
        "On target": "on_track",
        "on_track": "on_track",
        "Ahead": "smashing",
        "ahead": "smashing",
    }
    for choice, mark in expected.items():
        result = finish_session(HARD, choice, "  ")
        row = result["row"]
        if not result["ok"] or row is None:
            raise AssertionError((choice, result))
        if row.get("mark") != mark or row.get("numbers") != [] or row.get("completed") is not True:
            raise AssertionError(row)
        if timed_mark(row) is not None:
            raise AssertionError("the choice alone became a timed effort")
        if row.get("mark") not in ("on_track", "not_hitting", "smashing"):
            raise AssertionError("the choice was not the stored quality mark")


def test_an_optional_time_is_stored_and_a_blank_one_is_not() -> None:
    """One clock time is kept. It does not become a list of splits."""
    blank = finish_session(HARD, "on target", "")
    if blank["row"]["numbers"] != [] or blank["row"]["text"] != "":
        raise AssertionError(blank["row"])
    typed = finish_session(HARD, "Ahead", "1:12.4")
    row = typed["row"]
    if row["numbers"] != [72.4] or row["text"] != "1:12.4" or row["mark"] != "smashing":
        raise AssertionError(row)
    if timed_mark(row) != "smashing":
        raise AssertionError("a typed hard day did not count as a timed effort")
    easy = finish_session(EASY, None, "25:00")
    if easy["row"]["numbers"] != [1500] or "mark" in easy["row"]:
        raise AssertionError(easy["row"])
    if finish_session(HARD, "Behind", "1:10, 1:11")["ok"]:
        raise AssertionError("two times were stored")
    if len(easy["row"]["numbers"]) != 1:
        raise AssertionError("one field became more than one time")


def test_done_moves_the_plan_and_a_miss_does_not() -> None:
    """A finished day is no longer the next workout. Couldn't finish leaves it."""
    sessions = [EASY, HARD, LONG]
    if next_open_workout(sessions, TODAY, {})["date"] != EASY["date"]:
        raise AssertionError("today was skipped before it was finished")
    done = finish_session(EASY, None, "")["row"]
    actuals = {EASY["date"]: done}
    nxt = next_open_workout(sessions, TODAY, actuals)
    if nxt is None or nxt["date"] != HARD["date"]:
        raise AssertionError(nxt)
    missed = missed_session(EASY)
    if session_completed(EASY, {EASY["date"]: missed}):
        raise AssertionError("a miss counted as complete")
    if next_open_workout(sessions, TODAY, {EASY["date"]: missed})["date"] != EASY["date"]:
        raise AssertionError("a miss moved the plan forward")
    logged = {
        "template_id": HARD["template_id"],
        "numbers": [70],
        "mark": "on_track",
        "text": "70",
    }
    if not session_completed(HARD, {HARD["date"]: logged}):
        raise AssertionError("a logged time was not finished")
    view = recap_view(
        week=1,
        sessions=sessions,
        actuals={
            EASY["date"]: done,
            HARD["date"]: finish_session(HARD, "Behind", "")["row"],
            LONG["date"]: missed_session(LONG),
        },
        marks={},
    )
    if view["completed"] != "2 of 3":
        raise AssertionError(view["completed"])
    if view["marks"] != "Tuesday not_hitting":
        raise AssertionError(view["marks"])


def test_a_completion_without_a_time_survives_the_record() -> None:
    """The account keeps Done with no numbers. An older empty result still drops."""
    easy = finish_session(EASY, None, "")["row"]
    hard = finish_session(HARD, "On target", "75")["row"]
    missed = missed_session(LONG)
    raw = dump_record(
        {},
        {
            EASY["date"]: easy,
            HARD["date"]: hard,
            LONG["date"]: missed,
            "2026-04-23": {
                "text": "70",
                "numbers": [],
                "mark": "on_track",
                "template_id": "se_400_r90_x6",
            },
        },
    )
    _marks, actuals, _activities = load_record(raw)
    if set(actuals) != {EASY["date"], HARD["date"], LONG["date"]}:
        raise AssertionError(actuals)
    if actuals[EASY["date"]] != {
        "completed": True,
        "numbers": [],
        "template_id": EASY["template_id"],
        "text": "",
    }:
        raise AssertionError(actuals[EASY["date"]])
    if actuals[HARD["date"]].get("numbers") != [75] or actuals[HARD["date"]].get("mark") != "on_track":
        raise AssertionError(actuals[HARD["date"]])
    if actuals[LONG["date"]].get("missed") is not True or actuals[LONG["date"]].get("numbers") != []:
        raise AssertionError(actuals[LONG["date"]])
    if "probability" in raw or "readiness" in raw:
        raise AssertionError("a score was stored")


def test_the_preference_stays_on_a_hosted_account_and_a_local_one() -> None:
    """Pace units and the time zone live on the athlete. This toggle does too."""
    if no_watch_value({"user_metadata": {}}) is not None:
        raise AssertionError("a missing flag was invented")
    if no_watch_value({"user_metadata": {"no_watch": True}}) is not True:
        raise AssertionError("metadata lost the flag")
    if no_watch_value({"user_metadata": {"no_watch": False}}) is not False:
        raise AssertionError("an explicit off became on")
    if no_watch_value({"user_metadata": {"no_watch": "yes"}}) is not False:
        raise AssertionError("a word was stored as on")
    directory = reset_memory_directory()
    jay = directory.sign_up("jay@example.com", "correct-horse", "Jay")
    ada = directory.sign_up("ada@example.com", "correct-horse", "Ada")
    if "no_watch" in directory.load_bundle(jay["access_token"])["profile"]:
        raise AssertionError("a new hosted account already logged without a watch")
    directory.save_no_watch(jay["access_token"], True)
    again = directory.sign_in("jay@example.com", "correct-horse")
    kept = directory.load_bundle(again["access_token"])["profile"]
    if kept.get("no_watch") is not True:
        raise AssertionError(kept)
    other = directory.load_bundle(ada["access_token"])["profile"]
    if "no_watch" in other:
        raise AssertionError(other)
    directory.save_pace_units(jay["access_token"], "km")
    directory.save_timezone(jay["access_token"], "America/Los_Angeles")
    both = directory.load_bundle(again["access_token"])["profile"]
    if both.get("no_watch") is not True or both.get("pace_units") != "km":
        raise AssertionError(both)
    if both.get("timezone") != "America/Los_Angeles":
        raise AssertionError(both)
    directory.save_no_watch(jay["access_token"], False)
    if directory.load_bundle(again["access_token"])["profile"].get("no_watch") is not False:
        raise AssertionError("turning the toggle off did not stick")
    folder = Path(tempfile.mkdtemp(prefix="rio-nowatch-"))
    path = folder / "accounts.json"
    email, secret = create_account(path, "jay@example.com", "correct-horse", "Jay")
    write_local(path, email, secret, "Jay", "", "America/Los_Angeles", {"no_watch": True})
    local = read_local(path, email)
    if local is None or local["settings"].get("no_watch") is not True:
        raise AssertionError(local)
    if normalize(local["settings"])["no_watch"] is not True:
        raise AssertionError("the local profile dropped the toggle")
    app = (ROOT / "ui" / "cloud_ui.py").read_text(encoding="utf-8")
    if 'settings["no_watch"]' not in _function(app, "_apply_bundle"):
        raise AssertionError("a hosted sign-in does not restore the toggle")
    store = (ROOT / "ui" / "cloud_store.py").read_text(encoding="utf-8")
    if 'profile["no_watch"] = watch' not in _function(store, "_load_bundle"):
        raise AssertionError("the hosted bundle dropped the toggle")
    for migration in (ROOT / "supabase" / "migrations").glob("*.sql"):
        if "no_watch" in migration.read_text(encoding="utf-8"):
            raise AssertionError(migration.name)


def main() -> None:
    test_the_toggle_is_off_until_someone_turns_it_on()
    test_done_stays_off_the_session_until_the_toggle_is_on()
    test_easy_and_long_done_do_not_invent_a_time()
    test_a_hard_day_needs_one_of_the_three_choices()
    test_an_optional_time_is_stored_and_a_blank_one_is_not()
    test_done_moves_the_plan_and_a_miss_does_not()
    test_a_completion_without_a_time_survives_the_record()
    test_the_preference_stays_on_a_hosted_account_and_a_local_one()
    print("no watch ok")


if __name__ == "__main__":
    main()
