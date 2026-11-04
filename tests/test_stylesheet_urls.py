# test_stylesheet_urls.py — urls in app.css resolve from the stylesheet file.

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_URL = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""")


def test_stylesheet_urls_stay_next_to_the_css_file() -> None:
    css_path = ROOT / "ui" / "static" / "app.css"
    static = css_path.parent.resolve()
    live = re.sub(r"/\*.*?\*/", "", css_path.read_text(encoding="utf-8"), flags=re.S)
    urls = [match.group(2).strip() for match in _URL.finditer(live)]
    if not urls:
        raise AssertionError("app.css has no urls")
    for url in urls:
        if url.startswith("app/static/") or url.startswith("/"):
            raise AssertionError(url)
        rel = url.split("?", 1)[0].split("#", 1)[0]
        target = (static / rel).resolve()
        if static not in target.parents and target != static:
            raise AssertionError(url)
        if not target.is_file():
            raise AssertionError(url)


def main() -> None:
    test_stylesheet_urls_stay_next_to_the_css_file()
    print("stylesheet urls ok")


if __name__ == "__main__":
    main()
