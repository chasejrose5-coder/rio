# test_startup_page.py — the track page renders first. Continue opens Log in.

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image

from ui.startup import (
    CONTINUE_LABEL,
    CREATOR_STATEMENT,
    HEADLINE,
    PHOTO_CREDIT,
    PHOTO_PATH,
    SEEN_KEY,
    acknowledge_startup,
    startup_css,
    startup_html,
    startup_pending,
)


class _Token:
    """The browser bridge, with no saved login."""

    def __init__(self) -> None:
        self.record = {"body": ""}


class _Bridge:
    def __call__(self, *args: object, **kwargs: object) -> _Token:
        return _Token()


def _bridge(*args: object, **kwargs: object) -> _Bridge:
    return _Bridge()


def _mean(image: Image.Image, y0: int, y1: int) -> tuple[int, int, int]:
    pixel = image.load()
    if pixel is None:
        raise AssertionError("the track photo could not be read")
    red = green = blue = count = 0
    width, _height = image.size
    for y in range(y0, y1, 2):
        for x in range(0, width, 8):
            r, g, b = pixel[x, y]
            red += r
            green += g
            blue += b
            count += 1
    return red // count, green // count, blue // count


def _page_text(at: object) -> str:
    parts: list[str] = []
    for block in getattr(at, "markdown"):
        parts.append(block.value)
    return "\n".join(parts)


def _labels(items: object) -> list[str]:
    return [item.label for item in items]


def _failure(at: object) -> str:
    found = getattr(at, "exception", None)
    if not found:
        return ""
    item = found[0]
    trace = getattr(item, "stack_trace", None) or []
    if trace:
        return "\n".join(trace[-12:])
    return str(item)


def test_the_photo_is_the_track_without_the_infield() -> None:
    """16:9, the red track, and no green infield along the top."""
    if not PHOTO_PATH.is_file():
        raise AssertionError(PHOTO_PATH)
    if PHOTO_PATH.stat().st_size >= 1_000_000:
        raise AssertionError(PHOTO_PATH.stat().st_size)
    image = Image.open(PHOTO_PATH)
    width, height = image.size
    if width < 1920 or width * 9 != height * 16:
        raise AssertionError((width, height))
    top = _mean(image, 0, 24)
    middle = _mean(image, height // 3, height // 3 + 40)
    if top[0] <= top[1] or top[1] > top[0] - 15:
        raise AssertionError(top)
    if middle[0] < 140 or middle[0] <= middle[1] + 40:
        raise AssertionError(middle)


def test_startup_page_renders_and_leads_to_login() -> None:
    """The track page is still in the file, ahead of login.

    A visit now stops on the moved screen, so Continue is not what opens.
    """
    if HEADLINE != "RIO headline goes here":
        raise AssertionError(HEADLINE)
    if CREATOR_STATEMENT != "Personal creator statement goes here.":
        raise AssertionError(CREATOR_STATEMENT)
    if PHOTO_CREDIT != "Photo by Giant Asparagus on Pexels":
        raise AssertionError(PHOTO_CREDIT)
    source = (ROOT / "ui" / "startup.py").read_text(encoding="utf-8")
    if "Photo by Giant Asparagus on Pexels" not in source:
        raise AssertionError("the photo credit is missing")
    if "pexels.com/photo/aerial-view-of-empty-athletic-track-and-field-35678275" not in source:
        raise AssertionError("the photo source is missing")
    for token in (
        "engines",
        "explain(",
        "urlopen",
        "localStorage",
        "probability",
        "readiness",
        "intervals",
    ):
        if token in source:
            raise AssertionError(token)
    html = startup_html()
    css = startup_css()
    for piece in (
        HEADLINE,
        CREATOR_STATEMENT,
        PHOTO_CREDIT,
        "Placeholder",
        "Personal creator statement",
        'data-placeholder="personal-creator-statement"',
        "rio-startup-shade",
        "rio-startup-statement",
    ):
        if piece not in html and piece not in css:
            raise AssertionError(piece)
    if "data:image/jpeg;base64," not in css or "background-size: cover" not in css:
        raise AssertionError("the photo is not the full-screen background")
    if "rgba(0, 0, 0, 0.64)" not in css:
        raise AssertionError("the dark overlay is missing")
    fresh: dict[str, object] = {}
    if not startup_pending(fresh):
        raise AssertionError("a new session skipped the startup page")
    acknowledge_startup(fresh)
    if startup_pending(fresh) or fresh.get(SEEN_KEY) is not True:
        raise AssertionError("Continue did not leave the startup page")
    if not startup_pending({}):
        raise AssertionError("another session stayed on the far side of Continue")

    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    boot = app[app.index("\nst.set_page_config(") :]
    gate_at = boot.index("if _account_identity() is None:")
    head = boot[:gate_at]
    if "startup_pending(st.session_state)" not in head or "render_startup()" not in head:
        raise AssertionError("startup is not before login")
    if "acknowledge_startup(st.session_state)" not in head or "st.stop()" not in head:
        raise AssertionError("Continue does not leave the startup page")
    if head.index("render_startup()") > head.index("_restore_session()"):
        raise AssertionError("startup is after the session restore")
    if head.index("_open_restored_session(") < head.index("_restore_session()"):
        raise AssertionError("a reload routes before the token is restored")
    login_gate = boot[gate_at : boot.index("st.navigation(")]
    if "_render_login()" not in login_gate or "st.stop()" not in login_gate:
        raise AssertionError("Continue does not lead to login")
    if "localStorage" in (ROOT / "ui" / "startup.py").read_text(encoding="utf-8"):
        raise AssertionError("startup is stored in this browser")

    from ui.moved import ACCOUNT, BUTTON_LABEL, FASTER, NEW_HOME
    from ui.moved import HEADLINE as MOVED_HEADLINE
    from streamlit.testing.v1 import AppTest

    script = ROOT / "ui" / "streamlit_app.py"
    with patch("streamlit.components.v2.component", _bridge):
        at = AppTest.from_file(str(script), default_timeout=60).run(timeout=60)
        if _failure(at):
            raise AssertionError(_failure(at))
        shown = _page_text(at) + "\n" + "\n".join(block.value for block in at.html)
        if MOVED_HEADLINE not in shown or FASTER not in shown or ACCOUNT not in shown:
            raise AssertionError("the moved screen did not render")
        if NEW_HOME not in shown or BUTTON_LABEL not in shown:
            raise AssertionError("the new site link is missing")
        if 'target="_blank"' in shown:
            raise AssertionError("the link opens a new tab")
        if HEADLINE in shown or CREATOR_STATEMENT in shown or "rio-startup-shade" in shown:
            raise AssertionError("the startup page rendered")
        if CONTINUE_LABEL in _labels(at.button) or "Log in" in _labels(at.button):
            raise AssertionError(_labels(at.button))
        if at.text_input:
            raise AssertionError("Log in showed on the moved screen")


def main() -> None:
    test_the_photo_is_the_track_without_the_infield()
    test_startup_page_renders_and_leads_to_login()
    print("startup page ok")


if __name__ == "__main__":
    main()
