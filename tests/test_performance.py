# test_performance.py — one stylesheet, one plan view, splash text paints now.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.theme import surface_css


def test_the_big_stylesheet_is_a_static_file() -> None:
    css = (ROOT / "ui" / "static" / "app.css").read_text(encoding="utf-8")
    if "url(\"/app/static" in css or "url('/app/static" in css or "url(/app/static" in css:
        raise AssertionError("the stylesheet uses a root-absolute path")
    if "app/static/" not in css:
        raise AssertionError("the stylesheet dropped its static files")
    body = surface_css().replace("<style>", "").replace("</style>", "").strip()
    if body not in css:
        raise AssertionError("surface rules are not in the cached file")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    gate = app[app.index("def _css(") : app.index("def _date_text(")]
    if "@import url" not in gate or "_CSS_SENT" not in gate:
        raise AssertionError("the stylesheet is still inlined on every call")
    if "surface_css()" in gate:
        raise AssertionError("surface css is sent again over the websocket")
    plan = app[app.index("def page_plan(") : app.index("def page_more(")]
    if "st.tabs(" in plan or "segmented_control(" not in plan:
        raise AssertionError("plan still builds every tab")
    if plan.count("_nest(") != 3:
        raise AssertionError("a plan view was removed")


def test_splash_quote_does_not_wait_on_a_fade() -> None:
    startup = (ROOT / "ui" / "startup.py").read_text(encoding="utf-8")
    if "animation: none !important;" not in startup or ".rio-founder-words" not in startup:
        raise AssertionError("the splash quote still fades in")
    theme = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    if "Cache-Control" not in theme:
        raise AssertionError("the static cache limit was not recorded")


def main() -> None:
    test_the_big_stylesheet_is_a_static_file()
    test_splash_quote_does_not_wait_on_a_fade()
    print("performance ok")


if __name__ == "__main__":
    main()
