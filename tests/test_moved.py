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


def test_the_screen_links_to_the_new_home() -> None:
    """The address is a link to the live site. The page does not redirect."""
    if NEW_HOME != "https://www.riorunning.com":
        raise AssertionError(NEW_HOME)
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
    if "open the new site" not in COPY.lower():
        raise AssertionError(COPY)
    if html.count("<a ") != 1:
        raise AssertionError("the address is not a single link")
    link = html[html.index("<a ") : html.index("</a>")]
    if f'href="{NEW_HOME}"' not in link or f">{NEW_HOME}</a>" not in html:
        raise AssertionError("the address is not the link")
    if 'target="_blank"' not in link or "noopener" not in link:
        raise AssertionError(link)
    if "rio-one-mocha.vercel.app" in html or "rio-rio-44fa.vercel.app" in html:
        raise AssertionError("the link still points at an old host")
    source = (ROOT / "ui" / "moved.py").read_text(encoding="utf-8")
    blob = "\n".join((html, css, source))
    for forbidden in (
        "window.open",
        "window.location",
        "window.top",
        "location.href",
        "location.replace",
        "onclick",
        "<form",
        "<iframe",
        "<script",
        "<meta",
        "http-equiv",
        'target="_top"',
        'target="_self"',
        "st.iframe",
        "st.html(",
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
    if "background: #E25A32" in css or "background-color: #E25A32" in css:
        raise AssertionError("the brand orange is behind type")
    if "#F4F1EC" not in css:
        raise AssertionError("the page is not paper")
    url_css = css[css.index("a.rio-moved-url {") : css.index("a.rio-moved-url:hover")]
    if "user-select: text" not in url_css or "cursor: pointer" not in url_css:
        raise AssertionError("the address is not a selectable link")
    if "#C2461F" not in url_css or "#FFFFFF" not in url_css:
        raise AssertionError("the link is not a button")


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
    test_the_screen_links_to_the_new_home()
    test_the_old_app_is_still_there_and_does_not_run()
    print("moved screen ok")


if __name__ == "__main__":
    main()
