# test_past_seasons.py — Past seasons lists stored plans and opens one.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import SPEND_CAP_MICRO_USD
from ui.past_seasons import KEY_PREFIX, entry_fields, inputs_from_key, season_entries
from ui.plan_store import storage_key
from ui.profile import profile_key

INPUTS = ("2:02.9", "2026-04-19", "1:55.0", "2027-03-19")
OLDER = ("2:10.0", "2025-01-04", "2:00.0", "2025-06-01")


def test_rows_are_stored_seasons_only() -> None:
    """A plan key becomes one row. Other records and junk stay off the list."""
    if not storage_key(INPUTS).startswith(KEY_PREFIX):
        raise AssertionError("the list prefix is not the plan key")
    if profile_key(INPUTS).startswith(KEY_PREFIX):
        raise AssertionError("a profile record was treated as a season")
    if inputs_from_key(storage_key(INPUTS)) != INPUTS:
        raise AssertionError("a stored plan key was dropped")
    if inputs_from_key(profile_key(INPUTS)) is not None:
        raise AssertionError("a profile key was listed")
    rows = season_entries(
        [
            storage_key(INPUTS),
            storage_key(OLDER),
            storage_key(INPUTS),
            profile_key(INPUTS),
            "rio.plan.v1\n2:02.9\n2026-04-19\n1:55.0",
            "rio.plan.v1\nnope\n2026-02-31\n1:55.0\n2027-03-19",
            "rio.plan.v10\n2:02.9\n2026-04-19\n1:55.0\n2027-03-19",
            "",
            None,
            4,
        ]
    )
    if rows != [OLDER, INPUTS]:
        raise AssertionError(rows)
    if season_entries("not-a-list") or season_entries(None):
        raise AssertionError("a missing list invented a season")
    if entry_fields(INPUTS) != [
        ("Start date", "2026-04-19"),
        ("Goal date", "2027-03-19"),
        ("Goal time", "1:55.0"),
    ]:
        raise AssertionError(entry_fields(INPUTS))
    same_day = season_entries(
        [
            storage_key(("2:05.0", "2026-04-19", "1:50.0", "2027-03-19")),
            storage_key(("2:02.9", "2026-04-19", "1:55.0", "2027-03-19")),
            storage_key(("2:02.9", "2026-04-19", "1:55.0", "2027-04-01")),
        ]
    )
    if [item[2] for item in same_day[:2]] != ["1:50.0", "1:55.0"]:
        raise AssertionError(same_day)
    if same_day[2][3] != "2027-04-01":
        raise AssertionError(same_day)


def test_page_lists_stored_inputs_and_does_not_build() -> None:
    """Past seasons is a top-nav page. It reads keys and does not build a plan."""
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    source = (ROOT / "ui" / "past_seasons.py").read_text(encoding="utf-8")
    for token in (
        "engines",
        "sequence(",
        "adapt(",
        "explain(",
        "classify(",
        "prescribe(",
        "urlopen",
        "open(",
        "Path(",
        "probability",
        "readiness",
        "strength",
        "core",
    ):
        if token in source:
            raise AssertionError(token)
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    line = (
        '("Past seasons", st.Page(_with_plan(page_past_seasons), '
        'title="Past seasons", url_path="past-seasons"))'
    )
    if line not in app:
        raise AssertionError("Past seasons is not in the nav")
    if "window.__rioPastSeasonsToken" not in app or "localStorage.key" not in app:
        raise AssertionError("stored seasons are not read from this browser")
    past_js = app[app.index("_PAST_SEASONS_JS") : app.index("def _past_component(")]
    plan_js = app[app.index("_PLAN_STORE_JS") : app.index("_PROFILE_STORE_JS")]
    profile_js = app[app.index("_PROFILE_STORE_JS") : app.index("def _profile_component(")]
    if "__rioPastSeasonsToken" in plan_js or "__rioPastSeasonsToken" in profile_js:
        raise AssertionError("the season list shares a browser token")
    if "__rioPlanStoreToken" in past_js or "__rioProfileToken" in past_js:
        raise AssertionError("the season list shares a browser token")
    if "localStorage.setItem" in past_js or "localStorage.getItem" in past_js:
        raise AssertionError("the list writes or reads a plan body")
    bridge = app[app.index("def _past_component(") : app.index("def _past_row(")]
    shown = app.index("def _past_row(")
    page = app[shown : app.index("\nst.set_page_config(", shown)]
    if "season_entries(" not in page or "entry_fields(" not in page:
        raise AssertionError("the page does not list stored seasons")
    if '_open("Past seasons")' not in page or "query_values(" not in page:
        raise AssertionError("a row does not open the stored season")
    if '_nav_page("Plan")' not in page or "st.page_link(" not in page:
        raise AssertionError("a row does not open the plan page")
    if "_date_text(" not in page:
        raise AssertionError("the dates are not the stored ones")
    for blob in (bridge, page):
        for token in (
            "sequence(",
            "adapt(",
            "explain(",
            "classify(",
            "prescribe(",
            "_publish_inputs(",
            "_generate_season(",
            "_store_plan(",
            "_ensure_linked_plan(",
            "urlopen",
            "fetch_activity",
            "list_activities",
            "SPEND_CAP",
            "probability",
            "readiness_score",
            "strength",
            "core",
        ):
            if token in blob:
                raise AssertionError(token)
    for path in (ROOT / "engines").glob("*.py"):
        body = path.read_text(encoding="utf-8")
        if "ui.past_seasons" in body or "page_past_seasons" in body:
            raise AssertionError(f"{path.name} was changed for Past seasons")


def main() -> None:
    test_rows_are_stored_seasons_only()
    test_page_lists_stored_inputs_and_does_not_build()
    print("past seasons ok")


if __name__ == "__main__":
    main()
