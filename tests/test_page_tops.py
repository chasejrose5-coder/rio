# test_page_tops.py — photo heroes stay full. Other pages sit halfway.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.startup import startup_css, startup_html
from ui.theme import editorial_css, photo_page_css


def test_photo_pages_keep_the_earlier_hero_and_other_pages_sit_between() -> None:
    html = startup_html()
    if "Understand the work behind your goal" in html:
        raise AssertionError("the tagline came back")
    css = startup_css()
    for piece in (
        "14vh 6vw 5rem",
        "clamp(88px, 18vw, 176px)",
        "clamp(36px, 5.4vw, 72px)",
        "rgba(0, 0, 0, 0.64)",
    ):
        if piece not in css:
            raise AssertionError(piece)
    plain = editorial_css()
    if "clamp(2.6rem, 6.05vw, 5.55rem)" not in plain:
        raise AssertionError("the halfway title is missing")
    if "clamp(1.7rem, 3.1vw, 2.35rem)" not in plain:
        raise AssertionError("the earlier compact size was dropped")
    if "78vh" in plain or "140px" in plain or "4.5rem 5vw 3.6rem" in plain:
        raise AssertionError("a photo hero size landed on every page")
    photos = photo_page_css()
    for piece in ("78vh", "min-height: 24rem", "clamp(56px, 9vw, 140px)", "4.75rem", "1rem 5vw 0.9rem"):
        if piece not in photos:
            raise AssertionError(piece)
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    gate = app[app.index("def _css(") : app.index("def _date_text(")]
    if "photo_page_css()" not in gate or '"About"' not in gate or '"Start"' not in gate:
        raise AssertionError("photo pages do not restore the hero")


def main() -> None:
    test_photo_pages_keep_the_earlier_hero_and_other_pages_sit_between()
    print("page tops ok")


if __name__ == "__main__":
    main()
