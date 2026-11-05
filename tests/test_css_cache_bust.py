# test_css_cache_bust.py — the stylesheet URL changes when the file changes.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.css_href import app_css_href, cached_app_css_href


def test_the_stylesheet_href_is_relative_and_hashed() -> None:
    href = cached_app_css_href()
    if not href.startswith("app/static/app.css?v=") or href.startswith("/"):
        raise AssertionError(href)
    again = app_css_href(b"different bytes")
    if again == href or not again.startswith("app/static/app.css?v="):
        raise AssertionError(again)


def main() -> None:
    test_the_stylesheet_href_is_relative_and_hashed()
    print("css cache bust ok")


if __name__ == "__main__":
    main()
