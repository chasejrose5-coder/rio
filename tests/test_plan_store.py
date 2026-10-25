# test_plan_store.py — the URL is the plan, the browser keeps marks and actuals.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.plan_store import (
    dump_record,
    inputs_ok,
    load_record,
    plan_inputs,
    query_values,
    storage_key,
)

PARAMS = {
    "current_time": "2:02.9",
    "start_date": "2026-04-19",
    "goal_time": "1:55.0",
    "goal_date": "2027-03-19",
    "date": "2026-04-21",
}
INPUTS = ("2:02.9", "2026-04-19", "1:55.0", "2027-03-19")


def _no_score(value: object) -> None:
    text = str(value).lower()
    if "probability" in text or "readiness" in text:
        raise AssertionError("a score was stored")


def test_url_keeps_the_four_inputs() -> None:
    """A link needs all four. A session date is not part of the plan."""
    found = plan_inputs(PARAMS)
    if found != INPUTS:
        raise AssertionError(found)
    if not inputs_ok(found):
        raise AssertionError("the parsed inputs were rejected")
    written = query_values(found)
    if written != {
        "current_time": "2:02.9",
        "start_date": "2026-04-19",
        "goal_time": "1:55.0",
        "goal_date": "2027-03-19",
    }:
        raise AssertionError(written)
    if "date" in written:
        raise AssertionError("a session date was written into the plan")
    partial = dict(PARAMS)
    del partial["goal_time"]
    if plan_inputs(partial) is not None:
        raise AssertionError("a partial URL built a plan")
    blank = dict(PARAMS)
    blank["current_time"] = "  "
    if plan_inputs(blank) is not None:
        raise AssertionError("a blank time built a plan")
    impossible = dict(PARAMS)
    impossible["start_date"] = "2026-02-31"
    if plan_inputs(impossible) is not None:
        raise AssertionError("an impossible day was kept")
    listed = dict(PARAMS)
    listed["goal_time"] = ["1:50.0", "1:55.0"]
    if plan_inputs(listed) != INPUTS:
        raise AssertionError(plan_inputs(listed))
    if plan_inputs(None) is not None or inputs_ok(("2:02.9",)) or inputs_ok(INPUTS + ("x",)):
        raise AssertionError("a bad shape was accepted")


def test_storage_key_follows_the_inputs() -> None:
    """The same four inputs share a key. Any change gets its own."""
    key = storage_key(INPUTS)
    if storage_key(INPUTS) != key:
        raise AssertionError("the key moved")
    changed = (
        ("2:03.0", "2026-04-19", "1:55.0", "2027-03-19"),
        ("2:02.9", "2026-04-20", "1:55.0", "2027-03-19"),
        ("2:02.9", "2026-04-19", "1:50.0", "2027-03-19"),
        ("2:02.9", "2026-04-19", "1:55.0", "2027-03-20"),
    )
    for other in changed:
        if storage_key(other) == key:
            raise AssertionError(other)


def test_marks_and_actuals_round_trip() -> None:
    """The record keeps the three marks and the result fields. Scores do not."""
    raw = dump_record(
        {2: "smashing", True: "on_track", 4: "faster", "3": "not_hitting"},
        {
            "2026-04-21": {
                "text": " 75.0 ",
                "numbers": [75, 76.5],
                "mark": "on_track",
                "template_id": "se_400_r90_x6",
                "slots": [75, None],
                "probability": 0.9,
                "readiness": 1,
            },
            "not-a-day": {
                "text": "70",
                "numbers": [70],
                "mark": "on_track",
                "template_id": "se_400_r90_x6",
            },
            "2026-04-23": {
                "text": "70",
                "numbers": [],
                "mark": "on_track",
                "template_id": "se_400_r90_x6",
            },
        },
    )
    again = dump_record(
        {"3": "not_hitting", 2: "smashing"},
        {
            "2026-04-21": {
                "template_id": "se_400_r90_x6",
                "mark": "on_track",
                "numbers": [75, 76.5],
                "text": "75.0",
                "slots": [75, None],
            }
        },
    )
    if raw != again:
        raise AssertionError(raw)
    marks, actuals = load_record(raw)
    _no_score(marks)
    _no_score(actuals)
    if marks != {2: "smashing", 3: "not_hitting"}:
        raise AssertionError(marks)
    row = actuals.get("2026-04-21")
    if row != {
        "mark": "on_track",
        "numbers": [75, 76.5],
        "slots": [75, None],
        "template_id": "se_400_r90_x6",
        "text": "75.0",
    }:
        raise AssertionError(row)
    if set(actuals) != {"2026-04-21"}:
        raise AssertionError(actuals)
    if load_record("") != ({}, {}) or load_record("nope") != ({}, {}) or load_record(None) != ({}, {}):
        raise AssertionError("junk became a record")


def test_store_does_not_leave_the_browser() -> None:
    """No engine, no model, no file. The app writes the record to localStorage."""
    source = Path(ROOT / "ui" / "plan_store.py").read_text(encoding="utf-8")
    if "engines" in source or "explain(" in source or "open(" in source or "Path(" in source:
        raise AssertionError("the record reached a file or an engine")
    app = Path(ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    if "localStorage" not in app or "plan_inputs(" not in app or "dump_record(" not in app:
        raise AssertionError("the app does not keep the browser record")
    if "SPEND_CAP" in app:
        raise AssertionError("plan persistence started spending")


def main() -> None:
    test_url_keeps_the_four_inputs()
    test_storage_key_follows_the_inputs()
    test_marks_and_actuals_round_trip()
    test_store_does_not_leave_the_browser()
    print("plan store ok")


if __name__ == "__main__":
    main()
