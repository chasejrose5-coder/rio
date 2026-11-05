# test_link_safety.py — a signed-in link cannot wipe a saved season.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.plan_store import hosted_link_action, row_for_inputs

OWN = ("2:02", "2026-01-01", "1:55", "2026-06-01")
OTHER = ("2:10", "2026-02-01", "1:58", "2026-07-01")


def test_a_known_link_opens_the_saved_marks() -> None:
    row = {
        "current_time": OWN[0],
        "start_date": OWN[1],
        "goal_time": OWN[2],
        "goal_date": OWN[3],
        "plan": {"sessions": [{"date": "2026-01-02"}]},
        "marks": {"1": "on_track"},
        "actuals": {"1": {"reps": ["70"]}},
    }
    if hosted_link_action(OWN, [OWN], None) != "open":
        raise AssertionError("a saved season was treated as new")
    found = row_for_inputs([row], OWN)
    if not isinstance(found, dict) or found["marks"] != {"1": "on_track"}:
        raise AssertionError(found)
    if found["actuals"] != {"1": {"reps": ["70"]}}:
        raise AssertionError("the logged result was dropped")


def test_a_foreign_link_stays_a_preview() -> None:
    if hosted_link_action(OTHER, [OWN], OWN) != "preview":
        raise AssertionError("a foreign link was opened as this account's season")
    if row_for_inputs([], OTHER) is not None:
        raise AssertionError("a missing season invented a row")
    if hosted_link_action(OWN, [OWN], OWN) != "same":
        raise AssertionError("the open season was rebuilt")


def test_the_hosted_path_returns_before_a_save() -> None:
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    start = app.index("def _ensure_linked_plan(")
    body = app[start : app.index("\ndef ", start + 1)]
    if "hosted_link_action(" not in body or "season_link_preview" not in body:
        raise AssertionError("a signed-in link still builds a season")
    if body.index("hosted_link_action(") > body.index("_store_plan("):
        raise AssertionError("the save runs before the signed-in check")
    links = app[app.index("def _link_params(") : app.index("def _inputs_from_form(")]
    if "not _hosted_account()" not in links:
        raise AssertionError("signed-in links still carry the four times")


def main() -> None:
    test_a_known_link_opens_the_saved_marks()
    test_a_foreign_link_stays_a_preview()
    test_the_hosted_path_returns_before_a_save()
    print("link safety ok")


if __name__ == "__main__":
    main()
