# test_profile.py — Profile shows the four Start values and can save a goal time.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import SPEND_CAP_MICRO_USD
from engines.season import _parse_time
from ui.plan_store import storage_key
from ui.profile import (
    clean_goal,
    dump_goal,
    load_goal,
    profile_fields,
    profile_key,
    shown_goal,
)

INPUTS = ("2:02.9", "2026-04-19", "1:55.0", "2027-03-19")


def test_fields_are_the_four_start_values() -> None:
    """Current time, start date, goal time, and goal date, in that order."""
    rows = profile_fields("2:02.9", "2026-04-19", "1:55.0", "2027-03-19")
    if rows != [
        ("Current 800 time", "2:02.9"),
        ("Start date", "2026-04-19"),
        ("Goal 800 time", "1:55.0"),
        ("Goal date", "2027-03-19"),
    ]:
        raise AssertionError(rows)
    blank = profile_fields("  ", "", None, "  ")
    if [value for _label, value in blank] != ["—", "—", "—", "—"]:
        raise AssertionError(blank)
    if shown_goal("1:55.0", None) != "1:55.0":
        raise AssertionError("the Start goal was dropped")
    if shown_goal("1:55.0", " 1:52.0 ") != "1:52.0":
        raise AssertionError("a saved goal did not replace the display")
    if shown_goal("1:55.0", "nope") != "1:55.0":
        raise AssertionError("a bad save replaced the Start goal")


def test_goal_time_matches_start_and_stays_in_this_browser() -> None:
    """The saved string is an 800 time. The plan record is a different key."""
    accepted = ("1:55.0", "2:02.9", "1:55", "0:01", "12:00.50", "1:75", " 1:55.0 ")
    for sample in accepted:
        if clean_goal(sample) != _parse_time(sample, "goal_time"):
            raise AssertionError(sample)
    for sample in ("", "155", "1:5", "0:00", "0:00.0", "1:55.0s", "1:55.0\nno"):
        if clean_goal(sample) is not None:
            raise AssertionError(sample)
        try:
            _parse_time(sample, "goal_time")
        except ValueError:
            pass
        else:
            raise AssertionError(f"Start accepted {sample}")
    for sample in (None, 115, 1.55):
        if clean_goal(sample) is not None:
            raise AssertionError(sample)
    raw = dump_goal(" 1:52.0 ")
    if raw != '{"goal_time":"1:52.0"}':
        raise AssertionError(raw)
    if load_goal(raw) != "1:52.0":
        raise AssertionError(load_goal(raw))
    mixed = load_goal(
        '{"core":1,"goal_time":"1:50.5","probability":0.2,"readiness_score":9,"strength":1}'
    )
    if mixed != "1:50.5":
        raise AssertionError(mixed)
    for junk in ("", "  ", "{", "[]", '{"goal_time":"nope"}', None, 1):
        if load_goal(junk) is not None:
            raise AssertionError(junk)
    key = profile_key(INPUTS)
    if not key.startswith("rio.profile.v1\n"):
        raise AssertionError(key)
    if key == storage_key(INPUTS):
        raise AssertionError("the profile record uses the plan key")
    if profile_key(("2:02.9", "2026-04-19", "1:52.0", "2027-03-19")) == key:
        raise AssertionError("a different Start goal shared the key")
    if profile_key(("2:03.0", INPUTS[1], INPUTS[2], INPUTS[3])) == key:
        raise AssertionError("a different current time shared the key")
    try:
        dump_goal("nope")
    except ValueError as exc:
        if str(exc) != "goal_time is not an 800 time":
            raise AssertionError(exc) from exc
    else:
        raise AssertionError("a bad goal was stored")


def test_profile_is_in_the_nav_and_does_not_rebuild() -> None:
    """Profile is a top-nav page. Saving does not rebuild the season or spend."""
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    source = (ROOT / "ui" / "profile.py").read_text(encoding="utf-8")
    for token in (
        "engines",
        "sequence(",
        "adapt(",
        "explain(",
        "classify(",
        "prescribe(",
        "urlopen",
        "open(",
        "Path(",
        "probability",
        "readiness",
        "strength",
        "core",
    ):
        if token in source:
            raise AssertionError(token)
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    line = '("Profile", st.Page(_with_plan(page_profile), title="Profile", url_path="profile"))'
    if line not in app:
        raise AssertionError("Profile is not in the nav")
    if "window.__rioProfileToken" not in app or "localStorage.setItem" not in app:
        raise AssertionError("the goal is not saved in this browser")
    plan_js = app[app.index("_PLAN_STORE_JS") : app.index("_PROFILE_STORE_JS")]
    profile_js = app[app.index("_PROFILE_STORE_JS") : app.index("def _profile_component(")]
    if "__rioProfileToken" in plan_js or "__rioPlanStoreToken" in profile_js:
        raise AssertionError("the browser records share one token")
    if "localStorage.setItem" not in profile_js:
        raise AssertionError("the goal is not written to this browser")
    bridge = app[app.index("def _profile_component(") : app.index("def page_profile(")]
    page = app[app.index("def page_profile(") : app.index("\ndef page_about(")]
    if "profile_fields(" not in page or '_open("Profile")' not in page or "Save" not in page:
        raise AssertionError("the page does not show the four values or a save")
    if "_date_text(inputs[1])" not in page or "_date_text(inputs[3])" not in page:
        raise AssertionError("the dates are not the stored ones")
    if "clean_goal(" not in page or "_write_profile(" not in page:
        raise AssertionError("save does not keep the goal time")
    for blob in (bridge, page):
        for token in (
            "sequence(",
            "adapt(",
            "explain(",
            "classify(",
            "prescribe(",
            "_publish_inputs(",
            "_generate_season(",
            "_store_plan(",
            "_ensure_linked_plan(",
            "urlopen",
            "fetch_activity",
            "list_activities",
            "SPEND_CAP",
            "probability",
            "readiness_score",
            "strength",
            "core",
        ):
            if token in blob:
                raise AssertionError(token)
    for path in (ROOT / "engines").glob("*.py"):
        body = path.read_text(encoding="utf-8")
        if "ui.profile" in body or "page_profile" in body:
            raise AssertionError(f"{path.name} was changed for Profile")


def main() -> None:
    test_fields_are_the_four_start_values()
    test_goal_time_matches_start_and_stays_in_this_browser()
    test_profile_is_in_the_nav_and_does_not_rebuild()
    print("profile ok")


if __name__ == "__main__":
    main()
