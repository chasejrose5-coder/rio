# test_moved.py — the old Streamlit app opens on the moved screen and stops.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.moved import (
    ACCOUNT,
    BUTTON_LABEL,
    FASTER,
    HEADLINE,
    NEW_HOME,
    moved_css,
    moved_html,
)


def _boot(source: str) -> str:
    return source[source.index("\nst.set_page_config(") :]


def test_the_screen_names_the_new_site_and_keeps_the_same_tab() -> None:
    """The copy, the brand colors, and a same-tab link. No new window."""
    html = moved_html()
    css = moved_css()
    for piece in (HEADLINE, FASTER, ACCOUNT, BUTTON_LABEL, NEW_HOME, "RIO"):
        if piece not in html:
            raise AssertionError(piece)
    if "faster" not in FASTER.lower() or "more features" not in FASTER.lower():
        raise AssertionError(FASTER)
    if "same email and password" not in ACCOUNT:
        raise AssertionError(ACCOUNT)
    if html.count(f'href="{NEW_HOME}"') != 2:
        raise AssertionError("the button and the address are not both links")
    if 'target="_blank"' in html or 'target="_blank"' in css:
        raise AssertionError("the link opens a new tab")
    if 'target="_self"' not in html:
        raise AssertionError("the link does not stay in this tab")
    if "reconnect" in html.lower() or "strava" in html.lower():
        raise AssertionError("the screen claims a Strava step it does not need")
    button = css[css.index("a.rio-moved-go") : css.index(".rio-moved-url")]
    if "#C2461F" not in button or "#FFFFFF" not in button:
        raise AssertionError("white type is not on the darker orange")
    mark = css[css.index(".rio-moved-mark") : css.index(".rio-moved-owned")]
    if "#E25A32" not in mark:
        raise AssertionError("the wordmark is not the brand orange")
    if "#FFFFFF" in mark or "#C2461F" in mark:
        raise AssertionError("the wordmark uses the button orange")
    if "background: #E25A32" in css or "background-color: #E25A32" in css:
        raise AssertionError("the brand orange is behind type")


def test_the_old_app_is_still_there_and_does_not_run() -> None:
    """The stop is first. Login, startup, and Strava stay in the file."""
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    boot = _boot(app)
    stop = boot.index("\nst.stop()")
    head = boot[:stop]
    if "render_moved()" not in head:
        raise AssertionError("the moved screen is not first")
    for later in (
        "load_local_env()",
        "_boot_bridge()",
        "render_startup()",
        "_restore_session()",
        "boot_strava()",
        "_render_login()",
        "st.navigation(",
    ):
        if later in head:
            raise AssertionError(later)
    kept = boot[stop:]
    for later in (
        "load_local_env()",
        "render_startup()",
        "_render_login()",
        "st.navigation(",
        "boot_strava()",
    ):
        if later not in kept:
            raise AssertionError(later + " was removed")


def main() -> None:
    test_the_screen_names_the_new_site_and_keeps_the_same_tab()
    test_the_old_app_is_still_there_and_does_not_run()
    print("moved screen ok")


if __name__ == "__main__":
    main()
