# test_clarity.py — plain labels, no pace verdict before a run, one Strava empty state.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.intro import guide_html


def test_the_intro_matches_the_start_button() -> None:
    html = guide_html()
    if "Generate season plan" not in html:
        raise AssertionError(html)
    if "Generate Season Plan" not in html:
        raise AssertionError("the older label was dropped from the guide markup")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    start = app[app.index("def page_start(") : app.index("def _session_activity(")]
    if 'st.button("Generate season plan"' not in start:
        raise AssertionError("the start button does not match the intro")
    if 'placeholder="2:05.0"' not in start or 'placeholder="1:58.0"' not in start:
        raise AssertionError("the time fields have no format hint")
    if "Your 800 m time today" not in start or "800 m time you're aiming for" not in start:
        raise AssertionError("the 800 labels are still unexplained")


def test_pace_status_waits_for_a_run_and_copy_branches() -> None:
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    status = app[app.index("def _pace_status_label(") : app.index("def _pace_unit(")]
    if 'return "No runs yet"' not in status or 'return "Not enough data"' not in status:
        raise AssertionError(status)
    if 'return "On track"' in status:
        raise AssertionError("a missing log still says on track")
    if "Training block" not in app or "Last timed effort" not in app:
        raise AssertionError("home still uses unexplained tiles")
    if '"What it trains"' not in app:
        raise AssertionError("library still says only capacity")
    activity = app[app.index("def page_activity(") : app.index("\ndef ", app.index("def page_activity(") + 1)]
    if "strava_connected()" not in activity or 'st.button("Refresh", key="activity-refresh")' not in activity:
        raise AssertionError("refresh is not limited to a connected Strava account")
    if "Saved to your RIO account." not in app or "Your season stays in your account." not in app:
        raise AssertionError("hosted settings still say the account is only on this machine")


def main() -> None:
    test_the_intro_matches_the_start_button()
    test_pace_status_waits_for_a_run_and_copy_branches()
    print("clarity ok")


if __name__ == "__main__":
    main()
