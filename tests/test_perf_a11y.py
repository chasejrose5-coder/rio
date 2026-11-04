# test_perf_a11y.py — photos and fonts are files. Primary buttons are darker.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.startup import startup_css
from ui.theme import ACCENT, BUTTON, BUTTON_ACTIVE, BUTTON_HOVER, asset_uri, font_css

STATIC = ROOT / "ui" / "static"
PHOTOS = {
    "startup-track.jpg": 250_000,
    "startup-track-800.jpg": 120_000,
    "login.jpg": 120_000,
    "login-800.jpg": 50_000,
    "start.jpg": 750_000,
    "start-800.jpg": 200_000,
    "about.jpg": 500_000,
    "about-800.jpg": 180_000,
}
FONTS = (
    "inter-latin-400-normal.woff2",
    "inter-latin-500-normal.woff2",
    "inter-latin-600-normal.woff2",
    "manrope-latin-700-normal.woff2",
    "manrope-latin-800-normal.woff2",
)


def test_startup_css_serves_files_instead_of_embedding_them() -> None:
    css = startup_css()
    if len(css.encode()) > 80_000:
        raise AssertionError(len(css.encode()))
    if "/app/static/photos/startup-track.jpg" not in css:
        raise AssertionError("the track photo is not a static file")
    if "startup-track-800.jpg" not in css:
        raise AssertionError("the mobile photo is missing")
    if "data:font/woff2;base64," in css:
        raise AssertionError("a font is still embedded")
    if "data:image/jpeg;base64," not in css:
        raise AssertionError("the test token for the old photo URI is missing")
    if css.count("data:image/jpeg;base64,") != 1 or len(css) > 80_000:
        raise AssertionError("the photo itself is still in the stylesheet")
    faces = font_css()
    for name in FONTS:
        if f"/app/static/fonts/{name}" not in faces:
            raise AssertionError(name)
    if asset_uri("login_floodlights.jpg") != "/app/static/photos/login.jpg":
        raise AssertionError(asset_uri("login_floodlights.jpg"))
    if asset_uri("start_line.jpg") != "/app/static/photos/start.jpg":
        raise AssertionError(asset_uri("start_line.jpg"))
    if asset_uri("about_stadium.jpg") != "/app/static/photos/about.jpg":
        raise AssertionError(asset_uri("about_stadium.jpg"))


def test_static_files_are_smaller_copies() -> None:
    for name, limit in PHOTOS.items():
        file = STATIC / "photos" / name
        if not file.is_file():
            raise AssertionError(name)
        if file.stat().st_size > limit:
            raise AssertionError((name, file.stat().st_size))
    for name in FONTS:
        file = STATIC / "fonts" / name
        if not file.is_file() or file.stat().st_size > 40_000:
            raise AssertionError(name)
    config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    if "enableStaticServing = true" not in config:
        raise AssertionError("static serving is off")
    if 'primaryColor = "#E25A32"' not in config:
        raise AssertionError("the brand color changed in config")
    pinned = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    if "streamlit==1.66.1" not in pinned:
        raise AssertionError(pinned)


def test_primary_buttons_use_the_darker_orange_and_keyboard_focus_is_visible() -> None:
    if ACCENT != "#E25A32" or BUTTON != "#C2461F":
        raise AssertionError((ACCENT, BUTTON))
    if BUTTON_HOVER != "#A63C1A" or BUTTON_ACTIVE != "#8C3216":
        raise AssertionError((BUTTON_HOVER, BUTTON_ACTIVE))
    css = startup_css()
    if "#C2461F" not in css or ":focus-visible" not in css:
        raise AssertionError("Continue is missing the darker fill or the focus ring")
    theme = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    if "outline: 2px solid #E25A32" not in theme:
        raise AssertionError("the focus ring is not the brand orange")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    if 'background: #C2461F !important;' not in app:
        raise AssertionError("a page button still uses the brand orange as its fill")
    # Brand orange remains for non-button marks.
    if 'accent-color: #e25a32' not in app:
        raise AssertionError("a control accent lost the brand color")


def main() -> None:
    test_startup_css_serves_files_instead_of_embedding_them()
    test_static_files_are_smaller_copies()
    test_primary_buttons_use_the_darker_orange_and_keyboard_focus_is_visible()
    print("perf a11y ok")


if __name__ == "__main__":
    main()
