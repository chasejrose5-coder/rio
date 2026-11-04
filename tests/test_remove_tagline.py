# test_remove_tagline.py — the front page no longer shows that line.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.startup import startup_html

TAGLINE = "Understand the work behind your goal"


def test_the_front_page_drops_the_tagline() -> None:
    html = startup_html()
    source = (ROOT / "ui" / "startup.py").read_text(encoding="utf-8")
    if TAGLINE in html or TAGLINE in source:
        raise AssertionError("the tagline is still on the front page")
    for piece in (
        "RIO",
        "Your Race, Your Plan, Your Result",
        "Every rep has a reason",
        "Chase Rose, Founder",
        "Most plans tell you what to run",
    ):
        if piece not in html:
            raise AssertionError(piece)


def main() -> None:
    test_the_front_page_drops_the_tagline()
    print("tagline ok")


if __name__ == "__main__":
    main()
