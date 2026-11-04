# test_audit_cleanup.py — plain labels, one pace unit, and hidden fixture pages.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.about import about_sections
from ui.dashboard import mark_label, plain_marks
from ui.settings import normalize
from ui.startup import HEADLINE, startup_html


def _function(source: str, name: str) -> str:
    marker = f"def {name}("
    start = source.index(marker)
    nxt = source.find("\ndef ", start + len(marker))
    if nxt < 0:
        return source[start:]
    return source[start:nxt]


def test_blank_preferences_follow_pace_and_a_short_date() -> None:
    """A new account starts on per mile and a short date. A bad value does not."""
    clean = normalize(None)
    if clean["pace_units"] != "mi" or clean["units"] != "km":
        raise AssertionError(clean)
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    prefs = _function(app, "_prefs")
    if 'prefs["units"] = "km" if prefs.get("pace_units") == "km" else "miles"' not in prefs:
        raise AssertionError("distances do not follow the pace unit")
    if clean["date_format"] != "short":
        raise AssertionError(clean["date_format"])
    rejected = normalize({"units": "yards", "date_format": "long", "pace_units": "yards"})
    if rejected["units"] != "km" or rejected["date_format"] != "iso":
        raise AssertionError(rejected)
    if rejected["pace_units"] != "mi":
        raise AssertionError(rejected["pace_units"])
    if normalize({"pace_units": "km", "units": "miles"})["pace_units"] != "km":
        raise AssertionError("per km was dropped")


def test_marks_and_reasons_use_plain_words() -> None:
    """Stored codes stay stored. The words on the page are plain."""
    if mark_label("on_track") != "On track":
        raise AssertionError(mark_label("on_track"))
    if mark_label("not_hitting") != "Not hitting" or mark_label("smashing") != "Smashing":
        raise AssertionError("a mark label changed")
    if plain_marks("Tuesday on_track · Thursday smashing") != "Tuesday On track · Thursday Smashing":
        raise AssertionError(plain_marks("Tuesday on_track · Thursday smashing"))
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    render = _function(app, "_render_mark")
    if "mark_label(mark)" not in render:
        raise AssertionError("the mark button still prints the raw code")
    season = _function(app, "_render_schedule")
    if "_plain_reasons(" not in season or 'expander("Reasons"' not in season:
        raise AssertionError("reason codes are still the raw list")
    if "phase_1" in season:
        raise AssertionError("a raw phase code is written into the season list")


def test_about_shows_athlete_language_and_keeps_the_old_lines() -> None:
    """The visible lines skip the developer words. The older lines stay on the section."""
    sections = {section["title"]: section for section in about_sections()}
    shown = "\n".join(sections["Classification"]["shown"] + sections["Hard days"]["shown"])
    for banned in ("ontology", "$25", "Last Session", "on_track", "not_hitting"):
        if banned in shown:
            raise AssertionError(banned)
    if "rules" not in shown.lower() or "on track" not in shown:
        raise AssertionError(shown)
    older = "\n".join(sections["Classification"]["paragraphs"] + sections["Hard days"]["paragraphs"])
    if "ontology version" not in older or "on_track" not in older or "$25" not in older:
        raise AssertionError("the older explanation was deleted")


def test_fixture_pages_and_the_startup_line() -> None:
    """Athletes are sent home. The clipped startup line stays for the existing check."""
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    for name in ("page_last_session", "page_next", "page_decisions", "page_ledger", "page_goal"):
        body = _function(app, name)
        if "_fixture_allowed()" not in body or "_open_home()" not in body:
            raise AssertionError(name)
    choice = _function(app, "_intervals_choice")
    result = _function(app, "_render_result")
    if "Intervals file" not in choice:
        raise AssertionError("the file picker function was removed")
    if "_fixture_allowed()" not in result:
        raise AssertionError("every athlete still sees the file picker")
    notice = _function(app, "_activities_notice")
    if "Strava isn't connected" not in notice or "Open Settings" not in notice:
        raise AssertionError(notice)
    if "Intervals.icu" in notice:
        raise AssertionError("the activity notice still names Intervals")
    if HEADLINE != "RIO headline goes here":
        raise AssertionError(HEADLINE)
    html = startup_html()
    if 'aria-hidden="true"' not in html or "Every rep has a reason" not in html:
        raise AssertionError("the screen reader still gets the placeholder headline")
    settings = app[app.index("def page_settings(") : app.index("\ndef page_plan(")]
    if 'st.toggle("Show template ids"' not in settings or "viewer_is_admin(" not in settings:
        raise AssertionError("template ids are not limited to an admin")
    pace = _function(app, "_split_html")
    if 'recipe.get("speed")' not in pace:
        raise AssertionError("a speed day still prints the block clock")


def main() -> None:
    test_blank_preferences_follow_pace_and_a_short_date()
    test_marks_and_reasons_use_plain_words()
    test_about_shows_athlete_language_and_keeps_the_old_lines()
    test_fixture_pages_and_the_startup_line()
    print("audit cleanup ok")


if __name__ == "__main__":
    main()
