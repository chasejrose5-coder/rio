# test_data_nav.py — one row per season, and a deep link stays on that page.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.cloud_session import load_is_app_root
from ui.cloud_store import PLAN_CONFLICT, _missing_plan_key, _plan_row, _save_plan


class _Query:
    def __init__(self, table, op, row=None, conflict="") -> None:
        self.table = table
        self.op = op
        self.row = row
        self.conflict = conflict

    def execute(self):
        if self.op == "fail":
            raise RuntimeError("there is no unique or exclusion constraint matching the ON CONFLICT")
        self.table.calls.append((self.op, self.conflict, dict(self.row or {})))
        return self


class _Table:
    def __init__(self, fail_conflict: bool = False) -> None:
        self.fail_conflict = fail_conflict
        self.calls = []

    def upsert(self, row, on_conflict=""):
        if on_conflict and self.fail_conflict:
            return _Query(self, "fail", row, on_conflict)
        return _Query(self, "upsert", row, on_conflict)


class _Client:
    def __init__(self, table) -> None:
        self.table_obj = table

    def table(self, _name):
        return self.table_obj


def test_a_second_save_targets_the_same_season() -> None:
    first = _plan_row(
        {"id": "old", "current_time": "2:05", "start_date": "2026-09-01", "goal_time": "1:59", "goal_date": "2027-03-01", "plan": {"sessions": [1]}},
        "user-1",
    )
    second = _plan_row(
        {"current_time": "2:05", "start_date": "2026-09-01", "goal_time": "1:59", "goal_date": "2027-03-01", "plan": {"sessions": [2]}},
        "user-1",
    )
    if "id" in first or first["user_id"] != "user-1":
        raise AssertionError(first)
    if (first["current_time"], first["start_date"], first["goal_date"], first["goal_time"]) != (
        second["current_time"],
        second["start_date"],
        second["goal_date"],
        second["goal_time"],
    ):
        raise AssertionError("the season key changed")
    table = _Table()
    _save_plan(_Client(table), first)
    _save_plan(_Client(table), second)
    if len(table.calls) != 2 or table.calls[0][1] != PLAN_CONFLICT or table.calls[1][1] != PLAN_CONFLICT:
        raise AssertionError(table.calls)
    if table.calls[1][2]["plan"] != {"sessions": [2]}:
        raise AssertionError("the second save did not replace the season")


def test_a_missing_season_key_still_saves() -> None:
    table = _Table(fail_conflict=True)
    row = _plan_row({"current_time": "2:05", "start_date": "2026-09-01", "goal_time": "1:59", "goal_date": "2027-03-01"}, "user-1")
    _save_plan(_Client(table), row)
    if not _missing_plan_key(RuntimeError("42P10 there is no unique or exclusion constraint")):
        raise AssertionError("the missing index was not recognized")
    if len(table.calls) != 1 or table.calls[0][0] != "upsert" or table.calls[0][1]:
        raise AssertionError(table.calls)


def test_a_deep_link_is_not_the_app_root() -> None:
    root = "https://riotraining.streamlit.app/~/+/"
    plan = "https://riotraining.streamlit.app/~/+/plan"
    settings = "http://localhost:8501/settings?x=1"
    home = "http://localhost:8501/home"
    if not load_is_app_root(root) or not load_is_app_root("http://localhost:8501/"):
        raise AssertionError("the root was treated as a page")
    if load_is_app_root(plan) or load_is_app_root(settings):
        raise AssertionError("a deep link was sent home")
    if not load_is_app_root(home) or not load_is_app_root(""):
        raise AssertionError("home should still choose Home or Start")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    opened = app[app.index("def _open_restored_session(") : app.index("def _route_after_login(")]
    if '["rio_enter"]' not in opened or "load_is_app_root(" not in opened:
        raise AssertionError("a reload no longer chooses a page from the root")
    sql = (ROOT / "supabase" / "migrations" / "007_plans_season_key.sql").read_text(encoding="utf-8")
    if "plans_season_key" not in sql or 'newer."current_time" = older."current_time"' not in sql:
        raise AssertionError(sql)
    if "004_" in sql:
        raise AssertionError("the season key used the reserved migration number")


def main() -> None:
    test_a_second_save_targets_the_same_season()
    test_a_missing_season_key_still_saves()
    test_a_deep_link_is_not_the_app_root()
    print("data nav ok")


if __name__ == "__main__":
    main()
