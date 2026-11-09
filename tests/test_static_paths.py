# test_static_paths.py — static files resolve under a path prefix.

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.startup import startup_css
from ui.theme import font_css, static_mobile_url, static_url, surface_css

HOST = "https://riotraining.streamlit.app/~/+/"
PAGES = (
    "",
    "home",
    "plan",
    "activity",
    "library",
    "session",
    "admin",
    "more",
    "past-seasons",
    "profile",
    "settings",
    "about",
    "creators",
    "last-session",
    "next",
    "decisions",
    "ledger",
    "goal",
)


def _live(css: str) -> str:
    """Drop comments. Those hold strings an older test still reads."""
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _joined(page: str, href: str) -> str:
    base = HOST if not page else HOST + page
    return urljoin(base, href)


def test_served_urls_are_relative_and_survive_a_prefix() -> None:
    photos = {
        "startup_track.jpg": "app/static/photos/startup-track.jpg",
        "login_floodlights.jpg": "app/static/photos/login.jpg",
        "start_line.jpg": "app/static/photos/start.jpg",
        "about_stadium.jpg": "app/static/photos/about.jpg",
        "chase_blocks.jpg": "app/static/photos/chase-blocks.jpg",
        "home_aerial.jpg": "app/static/photos/home-aerial.jpg",
        "plan_curve.jpg": "app/static/photos/plan-curve.jpg",
    }
    for name, href in photos.items():
        if static_url(name) != href or static_url(name).startswith("/"):
            raise AssertionError(static_url(name))
        mobile = href[:-4] + "-800.jpg"
        if name == "chase_blocks.jpg":
            continue
        if static_mobile_url(name) != mobile or static_mobile_url(name).startswith("/"):
            raise AssertionError(static_mobile_url(name))
        for page in PAGES:
            joined = _joined(page, href)
            if joined != HOST + href:
                raise AssertionError((page, joined))
            if "/~/+/app/static/" not in joined:
                raise AssertionError(joined)
    chase = ROOT / "ui" / "static" / "photos" / "chase-blocks.jpg"
    if not chase.is_file() or chase.stat().st_size > 300 * 1024:
        raise AssertionError(chase.stat().st_size if chase.is_file() else "missing")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    if "static_url(theme.CHASE_PHOTO)" not in app:
        raise AssertionError("the creators photo is not a static file")
    if "asset_uri(" in app:
        raise AssertionError("a page still requests the absolute static path")
    for css in (startup_css(), font_css(), surface_css()):
        live = _live(css)
        if "/app/static" in live:
            raise AssertionError("a stylesheet still requests a root-absolute file")
        if "app/static/" not in live:
            raise AssertionError("a stylesheet dropped its static files")


def main() -> None:
    test_served_urls_are_relative_and_survive_a_prefix()
    print("static paths ok")


if __name__ == "__main__":
    main()
