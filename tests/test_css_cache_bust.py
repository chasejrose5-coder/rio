# test_css_cache_bust.py — the stylesheet URL changes when the file changes.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.css_href import app_css_href, cached_app_css_href


def test_the_stylesheet_href_is_relative_and_versioned() -> None:
    href = cached_app_css_href()
    if href.startswith("/") or not href.startswith("app/static/app.css?v="):
        raise AssertionError(href)
    version = href.split("?v=", 1)[1]
    if len(version) != 10 or any(char not in "0123456789abcdef" for char in version):
        raise AssertionError(version)
    raw = (ROOT / "ui" / "static" / "app.css").read_bytes()
    if href != app_css_href(raw):
        raise AssertionError("the cached href is not the file's hash")
    if app_css_href(b"a") == app_css_href(b"b"):
        raise AssertionError("a different stylesheet kept the same URL")
    if not app_css_href(b"a").startswith("app/static/app.css?v="):
        raise AssertionError(app_css_href(b"a"))


def main() -> None:
    test_the_stylesheet_href_is_relative_and_versioned()
    print("css cache bust ok")


if __name__ == "__main__":
    main()
