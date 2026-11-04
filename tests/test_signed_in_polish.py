# test_signed_in_polish.py — signed-in pages stay readable.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.past_seasons import keys_from_inputs, season_entries
from ui.plan_store import storage_key

INPUTS = ("2:05.0", "2026-11-04", "1:59.0", "2027-04-04")


def test_cloud_seasons_do_not_need_the_local_seal() -> None:
    keys = keys_from_inputs([INPUTS, list(INPUTS), ("bad",), None])
    if keys != [storage_key(INPUTS)]:
        raise AssertionError(keys)
    if season_entries(keys) != [INPUTS]:
        raise AssertionError(season_entries(keys))
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    page = app[app.index("def page_past_seasons(") : app.index("\ndef _auth_screen(")]
    if page.index('_open("Past seasons")') > page.index("_stored_season_keys("):
        raise AssertionError("the page still stops before the nav")
    if "st.stop()" in page:
        raise AssertionError("a missed read still blanks the page")
    if "This account's seasons could not be read." not in page:
        raise AssertionError("a failed read has no message")
    if 'who[1] == "cloud"' not in app:
        raise AssertionError("a cloud login still uses the local seal")
    pull = app[app.index("def _pull_for(") : app.index("\ndef _with_plan(")]
    if 'page_name == "page_past_seasons"' not in pull:
        raise AssertionError("past seasons still waits on a pull")


def test_home_plan_library_and_creators_copy() -> None:
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    if "01  /  Next workout" not in app or "02  /  Next 3 days" not in app:
        raise AssertionError("home numbering still starts at 02")
    if "04  /  Open" in app:
        raise AssertionError("the old open number is still on home")
    if "Rest day" not in app or "No mark yet" not in app or "No rest" not in app:
        raise AssertionError("an empty home value is still a bare dash")
    if "No runs logged" not in app:
        raise AssertionError("a week with no file still prints zero miles")
    if "Bio coming soon." not in app:
        raise AssertionError("creators still show the placeholder as the bio")
    if "cursor: default" not in app:
        raise AssertionError("library rows still look clickable")
    if "First name is enough. Saved on this machine." not in app:
        raise AssertionError("the name note was removed")
    settings = app[app.index("def page_settings(") : app.index("\ndef page_plan(")]
    name_at = settings.index('st.text_input("Name"')
    note_at = settings.index("First name is enough. Saved on this machine.")
    zone_at = settings.index('st.selectbox("Time zone"')
    if not (name_at < note_at < zone_at):
        raise AssertionError("the name note is not under Name")
    if "rio-after-hero" not in app or "Refresh from Strava" not in app:
        raise AssertionError("plan or activity spacing copy is missing")
    if 'st.button("Refresh", key="activity-refresh")' not in app:
        raise AssertionError("the refresh control was renamed")


def test_audit_medium_and_low_items() -> None:
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    cloud = (ROOT / "ui" / "cloud_ui.py").read_text(encoding="utf-8")
    theme = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    if 'autocomplete="current-password"' not in app or 'autocomplete="email"' not in app:
        raise AssertionError("local login is missing autocomplete")
    if 'autocomplete="current-password"' not in cloud or 'autocomplete="name"' not in cloud:
        raise AssertionError("cloud login is missing autocomplete")
    if "line-height: 1.02" not in theme or "min-height: 44px" not in theme:
        raise AssertionError("the auth heading or touch size was not updated")
    if "background-color: #2A1B1B" not in theme:
        raise AssertionError("the photo pages have no dark fallback")
    if 'page_title="RIO · Runner Intelligence Owned"' not in app or 'page_icon="🏃"' not in app:
        raise AssertionError("the tab title was not set")
    if 'st.query_params.get("skip") != "1"' not in app or 'st.query_params["skip"] = "1"' not in app:
        raise AssertionError("a reload does not skip the splash")
    if "min-width: 44px" not in app:
        raise AssertionError("the password eye is still a small target")
    startup = (ROOT / "ui" / "startup.py").read_text(encoding="utf-8")
    if "data-placeholder" not in startup or 'aria-hidden="true"' not in startup:
        raise AssertionError("the startup placeholder block was removed")


def main() -> None:
    test_cloud_seasons_do_not_need_the_local_seal()
    test_home_plan_library_and_creators_copy()
    test_audit_medium_and_low_items()
    print("signed in polish ok")


if __name__ == "__main__":
    main()
