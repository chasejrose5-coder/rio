# test_review_cleanup.py — the review pass keeps the pages the older tests require.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_hidden_routes_stay_because_older_tests_read_them() -> None:
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    for name in ("page_last_session", "page_next", "page_decisions", "page_ledger", "page_goal"):
        if f"def {name}(" not in app:
            raise AssertionError(name)
    if "st.cache_resource" in app:
        raise AssertionError("a shared resource was cached")


def test_design_rules_are_in_the_stylesheet() -> None:
    css = (ROOT / "ui" / "static" / "app.css").read_text(encoding="utf-8")
    if ".rio-index::before" not in css or "#E25A32" not in css:
        raise AssertionError("the orange accent rule is missing")
    if "font-size: 0.75rem !important" not in css:
        raise AssertionError("the type floor is missing")
    if "#B42318" not in css:
        raise AssertionError("the danger style is missing")
    for url in ("app/static/",):
        if url in css.split(".rio-index::before", 1)[-1] and 'url("app/static/' in css.split(".rio-index::before", 1)[-1]:
            raise AssertionError("a new stylesheet url is not relative to the file")


def main() -> None:
    test_hidden_routes_stay_because_older_tests_read_them()
    test_design_rules_are_in_the_stylesheet()
    print("review cleanup ok")


if __name__ == "__main__":
    main()
