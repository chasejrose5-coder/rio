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
    COPY_LABEL,
    FASTER,
    HEADLINE,
    NEW_HOME,
    moved_css,
    moved_html,
)


def _boot(source: str) -> str:
    return source[source.index("\nst.set_page_config(") :]


def test_the_screen_names_the_new_site_and_opens_a_new_tab() -> None:
    """The copy and colors stay. The click lives in a nested iframe."""
    html = moved_html()
    css = moved_css()
    for piece in (HEADLINE, FASTER, ACCOUNT, BUTTON_LABEL, COPY_LABEL, NEW_HOME, "RIO"):
        if piece not in html:
            raise AssertionError(piece)
    if "faster" not in FASTER.lower() or "more features" not in FASTER.lower():
        raise AssertionError(FASTER)
    if "same email and password" not in ACCOUNT:
        raise AssertionError(ACCOUNT)
    if f'action="{NEW_HOME}"' not in html or 'method="GET"' not in html:
        raise AssertionError("the button is not a GET form")
    if f'href="{NEW_HOME}"' not in html:
        raise AssertionError("the printed address is not a link")
    if html.count('target="_blank"') != 2:
        raise AssertionError("the form and the address do not both ask for a new tab")
    if html.count('rel="noopener noreferrer"') != 2:
        raise AssertionError("the new-tab controls are missing rel")
    if ">Copy link<" not in html:
        raise AssertionError("there is no copy control")
    script = html.split("<script>", 1)[1].split("</script>", 1)[0]
    if script.count("window.open(") != 1:
        raise AssertionError(script.count("window.open("))
    if script.index('addEventListener("submit"') > script.index("window.open("):
        raise AssertionError("window.open runs before the submit gesture")
    opened = script[script.index("window.open(") : script.index("window.open(") + 40]
    if "noopener" in opened:
        raise AssertionError("noopener makes Chrome return null and the form opens a second tab")
    if "event.preventDefault()" not in script:
        raise AssertionError("a successful popup also submits the form")
    if "window.parent.innerWidth" not in script:
        raise AssertionError("type size uses the iframe width")
    if "navigator.clipboard" not in script or 'execCommand("copy")' not in script:
        raise AssertionError("copy has no fallback")
    if "window.top" in html or "window.location" in html:
        raise AssertionError("the frame tries to navigate its parent")
    source = (ROOT / "ui" / "moved.py").read_text(encoding="utf-8")
    for forbidden in ('target="_self"', 'target="_top"'):
        if forbidden in html or forbidden in css or forbidden in source:
            raise AssertionError(forbidden)
    render = source[source.index("def render_moved") :]
    if "st.iframe(" not in render or "moved_html()" not in render:
        raise AssertionError("the control is not in a nested iframe")
    if 'height="content"' not in render:
        raise AssertionError("the iframe is a fixed box")
    if "st.markdown(moved_html()" in source:
        raise AssertionError("the links are in the app document")
    if "st.html(" in render or "st.link_button" in render:
        raise AssertionError("the control is still in the app document")
    if "onclick" in html.lower():
        raise AssertionError("the control uses an inline handler")
    if "reconnect" in html.lower() or "strava" in html.lower():
        raise AssertionError("the screen claims a Strava step it does not need")
    style = html[html.index("<style>") : html.index("</style>")]
    button = style[style.index("button.rio-moved-go") : style.index(".rio-moved-url")]
    if "#C2461F" not in button or "#FFFFFF" not in button:
        raise AssertionError("white type is not on the darker orange")
    mark = style[style.index(".rio-moved-mark") : style.index(".rio-moved-owned")]
    if "#E25A32" not in mark:
        raise AssertionError("the wordmark is not the brand orange")
    if "#FFFFFF" in mark or "#C2461F" in mark:
        raise AssertionError("the wordmark uses the button orange")
    if "background: #E25A32" in html or "background-color: #E25A32" in html:
        raise AssertionError("the brand orange is behind type")
    if "background: #E25A32" in css or "background-color: #E25A32" in css:
        raise AssertionError("the brand orange is behind type")
    if "#F4F1EC" not in css:
        raise AssertionError("the page is not paper")


def test_component_iframe_sandbox_allows_a_new_tab() -> None:
    """The installed 1.66.1 iframe sandbox includes popup escape, not top navigation."""
    import streamlit

    root = Path(streamlit.__file__).resolve().parent / "static" / "static" / "js"
    found = sorted(root.glob("IFrameUtil.*.js"))
    if len(found) != 1:
        raise AssertionError([path.name for path in found])
    text = found[0].read_text(encoding="utf-8")
    for flag in (
        "allow-forms",
        "allow-modals",
        "allow-popups",
        "allow-popups-to-escape-sandbox",
        "allow-same-origin",
        "allow-scripts",
        "allow-downloads",
    ):
        if f"`{flag}`" not in text:
            raise AssertionError(flag)
    for blocked in ("allow-top-navigation", "allow-top-navigation-by-user-activation"):
        if f"`{blocked}`" in text:
            raise AssertionError(blocked)
    frames = [
        path
        for path in root.glob("IFrame.*.js")
        if path.name != found[0].name and "Resizer" not in path.name
    ]
    if len(frames) != 1:
        raise AssertionError([path.name for path in frames])
    frame = frames[0].read_text(encoding="utf-8")
    if "IFrameUtil" not in frame or "sandbox:" not in frame:
        raise AssertionError("st.iframe does not use the component sandbox")


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
    test_the_screen_names_the_new_site_and_opens_a_new_tab()
    test_component_iframe_sandbox_allows_a_new_tab()
    test_the_old_app_is_still_there_and_does_not_run()
    print("moved screen ok")


if __name__ == "__main__":
    main()
