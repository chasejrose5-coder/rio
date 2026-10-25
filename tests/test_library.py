# test_library.py — the frozen menu as a searchable list.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.prescribe import load_menu
from ui.library import filter_workouts, library_rows, phases_for

MENU_DIR = ROOT / "rio" / "templates" / "800m"


def _no_score(row: dict) -> None:
    if "probability" in row or "readiness" in row or "readiness_score" in row:
        raise AssertionError("a score was added")
    text = str(row).lower()
    if "probability" in text or "readiness_score" in text:
        raise AssertionError("a score was named")


def test_every_frozen_template_is_listed_once() -> None:
    """The library is the menu. It does not invent a template."""
    menu = load_menu()
    files = sorted(MENU_DIR.glob("*.yml"))
    rows = library_rows(menu)
    if len(rows) != len(menu) or len(rows) != len(files) or len(rows) < 8:
        raise AssertionError(f"{len(rows)} rows for {len(files)} templates")
    ids = [row["id"] for row in rows]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise AssertionError("template ids were repeated or reordered")
    by_id = {item["id"]: item for item in menu}
    for row in rows:
        _no_score(row)
        source = by_id[row["id"]]
        if row["description"] != source["name"]:
            raise AssertionError(f"{row['id']} description was not the menu name")
        if row["family"] != source["family"]:
            raise AssertionError(f"{row['id']} family changed")
        if not row["capacity"] or row["capacity"] == "—":
            raise AssertionError(f"{row['id']} has no capacity")
    race = next(row for row in rows if row["id"] == "rr_800_r0_x1")
    if race["description"] != "800 m race" or race["capacity"] != "Race readiness":
        raise AssertionError(f"the race row was {race}")
    if 8 not in race["phases"] or 1 in race["phases"]:
        raise AssertionError(f"the race phases were {race['phases']}")


def test_search_and_filters_use_stored_fields() -> None:
    """Capacity is exact. Phase is the phases that already list the id."""
    rows = library_rows(load_menu())
    found = filter_workouts(rows, query="rr_800")
    if [row["id"] for row in found] != ["rr_800_r0_x1"]:
        raise AssertionError(f"search returned {[row['id'] for row in found]}")
    aerobic = filter_workouts(rows, family="aerobic")
    if not aerobic or any(row["family"] != "aerobic" for row in aerobic):
        raise AssertionError("the aerobic filter kept another capacity")
    if filter_workouts(rows, family="aerobic", query="12 km")[0]["id"] != "aer_12000_r0_x1":
        raise AssertionError("search did not narrow a capacity")
    phase_8 = filter_workouts(rows, phase=8)
    phase_ids = {row["id"] for row in phase_8}
    if "rr_800_r0_x1" not in phase_ids or "mv_60_r120_x10" not in phase_ids:
        raise AssertionError("phase 8 dropped a template it lists")
    if "aer_12000_r0_x1" in phase_ids or "aer_8000_r0_x1" in phase_ids:
        raise AssertionError("phase 8 kept a long run")
    if "aer_5000_r0_x1" not in phase_ids:
        raise AssertionError("phase 8 dropped the easy day")
    phase_1 = {row["id"] for row in filter_workouts(rows, phase=1)}
    if "aer_8000_r0_x1" not in phase_1 or "spd_150_r150_x8" not in phase_1:
        raise AssertionError("phase 1 dropped a listed template")
    if "aer_12000_r0_x1" not in phase_1 or "aer_5000_r0_x1" not in phase_1:
        raise AssertionError("phase 1 dropped the long run or the easy day")
    pyramid = "spd_py_150to300_r150_x5"
    if phases_for(pyramid):
        raise AssertionError("a template outside the phase lists gained a phase")
    if pyramid not in {row["id"] for row in rows}:
        raise AssertionError("a frozen template was left off the list")
    if filter_workouts(rows, phase=8, query=pyramid):
        raise AssertionError("phase 8 showed a template it does not list")
    if filter_workouts(rows, query="no-such-workout"):
        raise AssertionError("an unknown search returned rows")
    if filter_workouts(rows, phase=True):
        raise AssertionError("a boolean phase matched a row")
    if len(filter_workouts(rows)) != len(rows):
        raise AssertionError("an empty filter dropped a template")
    source = (ROOT / "ui" / "library.py").read_text(encoding="utf-8")
    if "explain(" in source or "MENU_DIR" in source:
        raise AssertionError("library wrote or rewrote the menu")


if __name__ == "__main__":
    test_every_frozen_template_is_listed_once()
    test_search_and_filters_use_stored_fields()
    print("library ok")
