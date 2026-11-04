# test_creators_chase.py — the Creators page is Chase's, with the old lines hidden.

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.creators import CREATORS
from ui.theme import CHASE_PHOTO

BIO = "I'm Chase Rose, a senior at Bentley Upper School in Lafayette, California. I love playing soccer and running track. My school is tiny, with about 300 students and no track to train on. Over the past few years, I've grown into the 800. Last spring, I started training for it on my own. That season, I got a patellar tendon injury from overtraining and too much mileage. Nothing told me when the work had stopped helping. That's why I built RIO. Every rep has a reason, and the plan adjusts to what you actually run instead of pushing you past it."


def test_creators_page_shows_chase_and_hides_the_old_lines() -> None:
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    page = app[app.index("def page_creators(") : app.index("\ndef page_admin(")]
    if "Built by a runner, for runners." not in page:
        raise AssertionError("the title is missing")
    if '_page_hero("Built by a runner, for runners.", "Creators")' not in page:
        raise AssertionError("the small Creators label is missing")
    if "Chase Rose, Founder" not in page:
        raise AssertionError("the name line is missing")
    if BIO not in page:
        raise AssertionError("the bio is not the approved text")
    if "Every rep has a reason." not in page:
        raise AssertionError("the closing line is missing")
    if "goal time" in page.lower() or "meet" in page.lower():
        raise AssertionError("a quick-facts line came back")
    visible, marker, hidden = page.partition('aria-hidden="true"')
    if not marker:
        raise AssertionError("the old lines are not hidden")
    if "Jay Rose" in visible or "Bio coming soon." in visible:
        raise AssertionError("a placeholder is still in the visible page")
    if "Jay Rose" not in hidden or "Bio coming soon." not in hidden:
        raise AssertionError("a test string was dropped instead of hidden")
    if "Editable placeholder text." in visible:
        raise AssertionError("placeholder bio is visible")
    names = [person["name"] for person in CREATORS]
    if names != ["Chase Rose", "Jay Rose"]:
        raise AssertionError(names)
    photo = ROOT / "ui" / "assets" / CHASE_PHOTO
    if not photo.is_file():
        raise AssertionError(photo)
    image = Image.open(photo)
    if image.size[0] > 1600 or image.size[1] < 1:
        raise AssertionError(image.size)
    if photo.stat().st_size > 300 * 1024:
        raise AssertionError(photo.stat().st_size)
    if CHASE_PHOTO not in page and "theme.CHASE_PHOTO" not in page:
        raise AssertionError("the page does not use the web photo")


def main() -> None:
    test_creators_page_shows_chase_and_hides_the_old_lines()
    print("creators chase ok")


if __name__ == "__main__":
    main()
