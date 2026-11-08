# test_easy_pace.py — saved easy pace drives easy and long runs. Quality fractions stay.

from __future__ import annotations

import sys
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.pace import (
    FAMILY_FRACTION,
    METERS_PER_MILE,
    PaceLog,
    canonical_easy_pace,
    display_workout,
    easy_pace_phrase,
    parse_easy_pace,
    workout_times,
)
from ui.accounts import create_account, read_local, write_easy_pace, write_local
from ui.cloud_store import reset_memory_directory

START = date(2026, 1, 1)
GOAL_DAY = date(2026, 1, 11)
MID = date(2026, 1, 6)
CURRENT = "2:00.0"
GOAL = "1:50.0"
QUALITY = (
    "mv_60_r120_x10",
    "spd_150_r150_x8",
    "rr_800_r0_x1",
    "se_py_200to400_r90_x5",
    "an_600_r180_x3",
    "an_dn_800to400_r180_x3",
    "ap_800_r90_x5",
    "thr_up_800to1600_r60_x3",
    "thr_5000_r0_x1",
)


def _workout(template: str, on: date = START, **extra):
    return workout_times(
        template,
        current_mark=CURRENT,
        goal_mark=GOAL,
        start=START,
        goal_date=GOAL_DAY,
        on=on,
        **extra,
    )


def test_the_family_table_is_unchanged() -> None:
    """Quality marks stay put. The aer fraction is still the unset fallback."""
    if FAMILY_FRACTION != {
        "mv": Decimal("0.82"),
        "spd": Decimal("0.96"),
        "rr": Decimal("1.00"),
        "se": Decimal("1.03"),
        "an": Decimal("1.06"),
        "ap": Decimal("1.12"),
        "thr": Decimal("1.18"),
        "aer": Decimal("1.55"),
    }:
        raise AssertionError(FAMILY_FRACTION)


def test_a_saved_easy_pace_replaces_only_continuous_aer() -> None:
    """7:25 per mile is the easy and long target. Quality reps do not move."""
    if parse_easy_pace("7:25") != Decimal(445):
        raise AssertionError(parse_easy_pace("7:25"))
    if canonical_easy_pace(" 7:25.0 ") != "7:25":
        raise AssertionError(canonical_easy_pace(" 7:25.0 "))
    if easy_pace_phrase("7:25", "mi") != "7:25 per mile":
        raise AssertionError(easy_pace_phrase("7:25", "mi"))
    if easy_pace_phrase("4:36", "km") != "4:36 per kilometer":
        raise AssertionError(easy_pace_phrase("4:36", "km"))
    for bad in ("", "7:5", "0:30", "31:00", "7:60", "fast", None, 445):
        if parse_easy_pace(bad) is not None or canonical_easy_pace(bad) is not None:
            raise AssertionError(bad)
        if easy_pace_phrase(bad, "mi"):
            raise AssertionError(bad)
    untouched = _workout("aer_4000_r0_x1")
    if untouched is None or untouched["line"] != "1 × 4000 m @ 15:30.0":
        raise AssertionError(untouched)
    if "easy_pace" in untouched or untouched.get("easy_unset"):
        raise AssertionError("a missing pace was treated as saved")
    easy = _workout("aer_5000_r0_x1", easy_pace="7:25", easy_unit="mi")
    long_run = _workout("aer_12000_r0_x1", easy_pace="7:25", easy_unit="mi")
    if easy is None or long_run is None:
        raise AssertionError("an easy run was dropped")
    if easy["line"] != "7:25 per mile" or long_run["line"] != "7:25 per mile":
        raise AssertionError((easy["line"], long_run["line"]))
    if easy.get("easy_pace") != "7:25 per mile":
        raise AssertionError(easy)
    for row in (easy, long_run):
        if "m @" in row["line"] or "15:30" in row["line"] or "6:14" in row["line"]:
            raise AssertionError(row["line"])
    expected = (Decimal(445) * Decimal(5000) / METERS_PER_MILE).quantize(Decimal("0.1"))
    if easy["reps"][0]["seconds"] != expected:
        raise AssertionError(easy["reps"][0]["seconds"])
    metric = _workout("aer_5000_r0_x1", easy_pace="4:36", easy_unit="km")
    if metric is None or metric["line"] != "4:36 per kilometer":
        raise AssertionError(metric)
    if metric["reps"][0]["seconds"] != Decimal("1380.0"):
        raise AssertionError(metric["reps"][0])
    for template in QUALITY:
        plain = _workout(template)
        paced = _workout(template, easy_pace="7:25", easy_unit="mi")
        if plain != paced:
            raise AssertionError(template)
        if plain is None or "easy_pace" in plain:
            raise AssertionError(template)
    blank = _workout("aer_10000_r0_x1", easy_pace="", easy_unit="mi")
    if blank is None or blank.get("easy_unset") is not True or blank["line"] != "":
        raise AssertionError(blank)
    if "6:14" in str(blank["line"]) or "m @" in blank["line"]:
        raise AssertionError(blank["line"])
    shown = display_workout(
        easy,
        {"template_id": "aer_5000_r0_x1", "distance_m": 5000, "moving_seconds": 1500},
        "mi",
    )
    if shown["planned"] != "7:25 per mile" or "Run at 7:25 per mile" not in shown["detail"]:
        raise AssertionError(shown)
    if "15:30" in shown["detail"] or "6:14" in shown["detail"] or "m @" in shown["detail"]:
        raise AssertionError(shown["detail"])
    hidden = display_workout(
        blank,
        {"template_id": "aer_10000_r0_x1"},
        "mi",
    )
    if "6:14" in hidden["detail"] or "15:30" in hidden["detail"] or "/mi" in hidden["detail"]:
        raise AssertionError(hidden)
    if hidden["planned"] != "Set your easy pace":
        raise AssertionError(hidden)
    speed = display_workout(
        _workout("spd_150_r150_x8", easy_pace="7:25", easy_unit="mi"),
        {"template_id": "spd_150_r150_x8"},
        "mi",
    )
    if "21.6 s" not in speed["detail"] or "/mi" in speed["detail"] or "7:25" in speed["detail"]:
        raise AssertionError(speed["detail"])


def test_an_easy_log_at_that_pace_does_not_move_quality() -> None:
    """Running the saved easy pace is not a miss against 1.55."""
    prescribed = _workout("aer_4000_r0_x1", date(2026, 1, 3), easy_pace="7:25", easy_unit="mi")
    if prescribed is None:
        raise AssertionError("the easy run had no target")
    log = PaceLog(date(2026, 1, 3), float(prescribed["reps"][0]["seconds"]), "aer_4000_r0_x1")
    held = _workout("spd_150_r150_x8", MID, logs=[log], easy_pace="7:25", easy_unit="mi")
    plain = _workout("spd_150_r150_x8", MID)
    if held is None or plain is None or held["factor"] != 1 or held["reps"] != plain["reps"]:
        raise AssertionError(held)
    shifted = _workout("spd_150_r150_x8", MID, logs=[log])
    if shifted is None or shifted["factor"] != Decimal("1.01"):
        raise AssertionError(shifted)
    if shifted["reps"] == plain["reps"]:
        raise AssertionError("the 1.55 target did not treat the easy run as slow")


def test_the_pace_stays_on_the_athlete() -> None:
    """Local and hosted profiles keep the pace. Another athlete does not."""
    directory = Path(tempfile.mkdtemp(prefix="rio-easy-"))
    path = directory / "accounts.json"
    email, secret = create_account(path, "jay@example.com", "correct-horse", "Jay")
    other_email, other_secret = create_account(path, "ada@example.com", "correct-horse", "Ada")
    if read_local(path, email).get("easy_pace"):
        raise AssertionError("a new account already had an easy pace")
    saved = write_easy_pace(path, email, secret, "7:25", "mi")
    if saved["easy_pace"] != "7:25" or saved["easy_pace_unit"] != "mi":
        raise AssertionError(saved)
    renamed = write_local(path, email, secret, "Jay", "JR", "UTC", {"reminders": True})
    if renamed["easy_pace"] != "7:25" or renamed["preferred"] != "JR":
        raise AssertionError(renamed)
    if read_local(path, other_email).get("easy_pace"):
        raise AssertionError("the other account took the pace")
    try:
        write_easy_pace(path, other_email, other_secret, "0:30", "mi")
    except ValueError:
        pass
    else:
        raise AssertionError("a pace under a minute was stored")
    if read_local(path, other_email).get("easy_pace"):
        raise AssertionError("a refused pace was stored")
    hosted = reset_memory_directory()
    jay = hosted.sign_up("jay@example.com", "correct-horse", "Jay")
    ada = hosted.sign_up("ada@example.com", "correct-horse", "Ada")
    if hosted.load_bundle(jay["access_token"])["profile"].get("easy_pace"):
        raise AssertionError("a new hosted account already had an easy pace")
    hosted.save_easy_pace(jay["access_token"], "7:25.0", "km")
    kept = hosted.load_bundle(jay["access_token"])["profile"]
    ada_profile = hosted.load_bundle(ada["access_token"])["profile"]
    if kept.get("easy_pace") != "7:25" or kept.get("easy_pace_unit") != "km":
        raise AssertionError(kept)
    if ada_profile.get("easy_pace") or ada_profile.get("easy_pace_unit"):
        raise AssertionError(ada_profile)
    hosted.save_pace_units(jay["access_token"], "mi")
    again = hosted.load_bundle(jay["access_token"])["profile"]
    if again.get("easy_pace") != "7:25" or again.get("pace_units") != "mi":
        raise AssertionError(again)
    try:
        hosted.save_easy_pace(jay["access_token"], "nope", "mi")
    except ValueError:
        pass
    else:
        raise AssertionError("a bad pace was saved")
    migrations = list((ROOT / "supabase" / "migrations").glob("*.sql"))
    for migration in migrations:
        body = migration.read_text(encoding="utf-8")
        if "easy_pace" in body:
            raise AssertionError(migration.name)


def test_the_screen_is_the_gate_and_profile_can_edit_it() -> None:
    """New and existing athletes hit this screen. Settings is not the only door."""
    screen = (ROOT / "ui" / "easy_pace.py").read_text(encoding="utf-8")
    for label in ("Your easy pace", "7:25", "per mile", "per kilometer", "Save easy pace", "Minutes and seconds"):
        if label not in screen:
            raise AssertionError(label)
    for banned in ("Current 800", "Goal 800", "goal_time", "current_time", "1.55"):
        if banned in screen:
            raise AssertionError(banned)
    if ACCENT_MISSING(screen):
        raise AssertionError("the brand accent is missing")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    wrapped = app[app.index("def _with_plan(") : app.index("def _fresh_value(")]
    if "_easy_pace_gate()" not in wrapped or "_intro_gate()" not in wrapped:
        raise AssertionError("the screen is not in front of the pages")
    if wrapped.index("_easy_pace_gate()") > wrapped.index("page()"):
        raise AssertionError("the page draws before the pace is saved")
    page = app[app.index("def page_profile(") : app.index("\ndef page_about(")]
    if page.count("_easy_pace_section()") < 2:
        raise AssertionError("Profile cannot change the pace without a season")
    split = app[app.index("def _split_html(") : app.index("def recipe_continuous(")]
    continuous = split.split("found = _pace_bundle", 1)[0]
    if "Run at" not in continuous or "Set your easy pace before this run." not in continuous:
        raise AssertionError(continuous)
    if "format_pace(" in continuous:
        raise AssertionError("an easy run still prints the guessed pace")
    if "1.55" in continuous:
        raise AssertionError(continuous)


def ACCENT_MISSING(screen: str) -> bool:
    theme = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    return "ACCENT" not in screen or 'ACCENT = "#E25A32"' not in theme


def main() -> None:
    test_the_family_table_is_unchanged()
    test_a_saved_easy_pace_replaces_only_continuous_aer()
    test_an_easy_log_at_that_pace_does_not_move_quality()
    test_the_pace_stays_on_the_athlete()
    test_the_screen_is_the_gate_and_profile_can_edit_it()
    print("easy pace ok")


if __name__ == "__main__":
    main()
