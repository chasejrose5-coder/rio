# test_moved.py — the old Streamlit app opens on the moved screen and stops.

from __future__ import annotations

import sys
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.moved import (
    ACCOUNT,
    COPY,
    FASTER,
    HEADLINE,
    NEW_HOME,
    moved_css,
    moved_html,
)


def _boot(source: str) -> str:
    return source[source.index("\nst.set_page_config(") :]


def test_the_screen_is_an_address_to_copy() -> None:
    """The copy and the brand colors. The address is text, not a control."""
    html = moved_html()
    css = moved_css()
    text = unescape(html)
    for piece in (HEADLINE, FASTER, ACCOUNT, COPY, NEW_HOME, "RIO"):
        if piece not in text:
            raise AssertionError(piece)
    if "faster" not in FASTER.lower() or "more features" not in FASTER.lower():
        raise AssertionError(FASTER)
    if "same email and password" not in ACCOUNT:
        raise AssertionError(ACCOUNT)
    lowered = COPY.lower()
    if "copy" not in lowered or "paste" not in lowered or "address bar" not in lowered:
        raise AssertionError(COPY)
    url = html[html.index('class="rio-moved-url"') : html.index("</p>", html.index('class="rio-moved-url"'))]
    if f">{NEW_HOME}" not in url:
        raise AssertionError("the address is not its own selectable line")
    source = (ROOT / "ui" / "moved.py").read_text(encoding="utf-8")
    blob = "\n".join((html, css, source))
    for forbidden in (
        "Open the new RIO",
        'target="_blank"',
        'target="_self"',
        'target="_top"',
        "target=",
        "window.open",
        "window.location",
        "window.top",
        "onclick",
        "<form",
        "<iframe",
        "<script",
        "<button",
        "<a ",
        "href=",
        "st.iframe",
        "st.html(",
        "st.link_button",
        "components.v1",
        "components.v2",
    ):
        if forbidden in blob:
            raise AssertionError(forbidden)
    render = source[source.index("def render_moved") :]
    if "st.markdown(moved_html(), unsafe_allow_html=True, anchors=False)" not in render:
        raise AssertionError("the address is not in the app frame")
    if "st.markdown(moved_css(), unsafe_allow_html=True)" not in render:
        raise AssertionError("the page style is missing")
    if "reconnect" in html.lower() or "strava" in html.lower():
        raise AssertionError("the screen claims a Strava step it does not need")
    mark = css[css.index(".rio-moved-mark") : css.index(".rio-moved-owned")]
    if "#E25A32" not in mark:
        raise AssertionError("the wordmark is not the brand orange")
    if "#FFFFFF" in mark or "#C2461F" in mark:
        raise AssertionError("the wordmark uses the button orange")
    if "#C2461F" in css or "#C2461F" in html:
        raise AssertionError("the button orange is a fill on a page with no button")
    if "background: #E25A32" in css or "background-color: #E25A32" in css:
        raise AssertionError("the brand orange is behind type")
    if "#F4F1EC" not in css:
        raise AssertionError("the page is not paper")
    url_css = css[css.index(".rio-moved-url {") : css.index(".rio-moved-url::selection")]
    if "user-select: text" not in url_css:
        raise AssertionError("the address is not selectable")


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
    test_the_screen_is_an_address_to_copy()
    test_the_old_app_is_still_there_and_does_not_run()
    print("moved screen ok")


if __name__ == "__main__":
    main()
