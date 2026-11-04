# test_test_season.py — the TEST athlete stays off the signed-in account.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.pace import workout_times
from ui.cloud_store import reset_memory_directory
from ui.strava import earlier_logs, planned_vs_actual
from ui.strava_store import reset_memory_strava
from ui.sample_season import (
    CUTOFF,
    START,
    TEST_EMAIL,
    TEST_NAME,
    TestSeasonError,
    build_test_season,
    delete_test_season,
    load_test_season,
    read_test_bundle,
)

KEY = "server-key"


def test_the_season_is_fixed() -> None:
    """Same inputs build the same plan and the same runs. Nothing is fetched."""
    source = (ROOT / "ui" / "sample_season.py").read_text(encoding="utf-8")
    if "urlopen" in source or "openai" in source or "anthropic" in source:
        raise AssertionError("the test season calls out")
    first = build_test_season()
    second = build_test_season()
    if first != second:
        raise AssertionError("the test season changed between calls")
    if first["email"] != TEST_EMAIL or first["name"] != TEST_NAME:
        raise AssertionError(first["name"])
    if not TEST_EMAIL.endswith(".invalid"):
        raise AssertionError("the test address must not be deliverable")
    plan = first["plan"]
    if plan.get("ontology_version") != "v0.1":
        raise AssertionError(plan.get("ontology_version"))
    if not isinstance(plan.get("season_length_weeks"), int) or plan["season_length_weeks"] < 20:
        raise AssertionError(plan.get("season_length_weeks"))
    if first["goal"]["event"] != "800m" or first["goal"]["goal_time"] != "1:59.0":
        raise AssertionError(first["goal"])
    runs = first["runs"]
    if not 30 <= len(runs) <= 80:
        raise AssertionError(len(runs))
    days = sorted(date.fromisoformat(run["date"]) for run in runs)
    span = (days[-1] - days[0]).days
    if days[0] != date.fromisoformat(START) or days[-1] != CUTOFF or not 49 <= span <= 63:
        raise AssertionError((days[0], days[-1], span))
    matched = [run for run in runs if run["matched"] is True]
    extra = [run for run in runs if run["matched"] is False]
    if not matched or not extra:
        raise AssertionError((len(matched), len(extra)))
    quiet = [run for run in runs if run.get("average_hr") is None]
    if not quiet or len(quiet) >= len(runs) // 2:
        raise AssertionError(len(quiet))
    if any(not run.get("laps") for run in runs):
        raise AssertionError("a run has no laps")
    fast = slow = False
    start = date.fromisoformat(START)
    goal_day = date.fromisoformat(first["goal"]["goal_date"])
    for run in matched:
        prescribed = workout_times(
            run["template_id"],
            current_mark=first["goal"]["current_mark"],
            goal_mark=first["goal"]["goal_time"],
            start=start,
            goal_date=goal_day,
            on=date.fromisoformat(run["date"]),
            logs=[],
        )
        if not isinstance(prescribed, dict) or not prescribed.get("reps"):
            raise AssertionError(run["template_id"])
        target = float(prescribed["reps"][0]["seconds"])
        actual = run["laps"][0]["moving_seconds"]
        if actual < target:
            fast = True
        if actual > target:
            slow = True
    if not fast or not slow:
        raise AssertionError((fast, slow))
    statuses = set()
    for run in runs:
        on = date.fromisoformat(run["date"])
        row = planned_vs_actual(
            run,
            current=first["inputs"][0],
            goal=first["inputs"][2],
            start=start,
            goal_day=goal_day,
            on=on,
            logs=earlier_logs(runs, on),
        )
        if run["matched"] is not True:
            row["status"] = "Extra"
        statuses.add(row["status"])
    if not {"Ahead", "Behind", "Extra"} <= statuses:
        raise AssertionError(statuses)


def test_load_replaces_and_leaves_the_other_account() -> None:
    """Two loads keep one TEST athlete. The signed-in rows and token stay."""
    directory = reset_memory_directory()
    store = reset_memory_strava()
    admin = directory.sign_up("coach@example.com", "long-password", "Coach")
    directory.save_bundle(
        admin["access_token"],
        {
            "goal": {
                "event": "800m",
                "goal_time": "1:55.0",
                "goal_date": "2027-06-01",
                "current_mark": "2:02.0",
            },
            "plans": [{"current_time": "2:02.0", "plan": {"sessions": [{"date": "2026-09-01"}]}}],
        },
    )
    store.put_token(admin["user_id"], {"access_token": "admin-token", "refresh_token": "admin-refresh"}, KEY)
    store.put_activities(admin["user_id"], [{"id": "real-run", "name": "Real", "date": "2026-10-01"}])
    goal_before = directory.goals[admin["user_id"]]
    plan_before = directory.plans[admin["user_id"]]
    first = load_test_season(
        directory,
        store,
        KEY,
        caller_id=admin["user_id"],
        caller_email=admin["email"],
    )
    test_id = first["user_id"]
    if test_id == admin["user_id"]:
        raise AssertionError("the test athlete reused this login")
    password = directory.users[test_id]["password"]
    store.activities[test_id].append({"id": "poison", "name": "Poison", "date": "2026-10-02"})
    second = load_test_season(
        directory,
        store,
        KEY,
        caller_id=admin["user_id"],
        caller_email=admin["email"],
    )
    if second["user_id"] != test_id or second["created"] is not False:
        raise AssertionError(second)
    if directory.users[test_id]["password"] != password:
        raise AssertionError("a second load replaced the test login")
    if directory.users[test_id]["display_name"] != TEST_NAME:
        raise AssertionError(directory.users[test_id]["display_name"])
    if directory.users[test_id]["role"] != "athlete":
        raise AssertionError(directory.users[test_id]["role"])
    ids = [row.get("id") for row in store.get_activities(test_id)]
    built = build_test_season()
    if len(ids) != len(built["runs"]) or "poison" in ids:
        raise AssertionError(ids)
    if store.get_token(test_id, KEY) is not None:
        raise AssertionError("the test athlete was given a token")
    if directory.goals[admin["user_id"]] != goal_before or directory.plans[admin["user_id"]] != plan_before:
        raise AssertionError("this login's season changed")
    token = store.get_token(admin["user_id"], KEY)
    if token is None or token.get("access_token") != "admin-token":
        raise AssertionError(token)
    admin_ids = [row.get("id") for row in store.get_activities(admin["user_id"])]
    if admin_ids != ["real-run"]:
        raise AssertionError(admin_ids)
    if len(directory.users) != 2:
        raise AssertionError(len(directory.users))
    bundle = read_test_bundle(directory, store, KEY)
    if bundle is None or bundle["name"] != TEST_NAME or len(bundle["activities"]) != len(built["runs"]):
        raise AssertionError(bundle)
    extras = [row for row in bundle["activities"] if row.get("matched") is not True]
    if not extras:
        raise AssertionError("extras were dropped")
    try:
        load_test_season(directory, store, KEY, caller_id=test_id, caller_email="coach@example.com")
    except TestSeasonError as exc:
        if "unchanged" not in str(exc):
            raise AssertionError(str(exc)) from None
    else:
        raise AssertionError("the test athlete was written as if it were this login")
    if not delete_test_season(
        directory,
        store,
        KEY,
        caller_id=admin["user_id"],
        caller_email=admin["email"],
    ):
        raise AssertionError("delete did not remove the test athlete")
    if directory.find_user_by_email(TEST_EMAIL, KEY) is not None:
        raise AssertionError("the test profile remained")
    if store.get_activities(test_id):
        raise AssertionError("test runs remained")
    if delete_test_season(
        directory,
        store,
        KEY,
        caller_id=admin["user_id"],
        caller_email=admin["email"],
    ):
        raise AssertionError("a second delete removed something")
    if admin["user_id"] not in directory.users:
        raise AssertionError("this login was removed")
    if directory.goals[admin["user_id"]] != goal_before:
        raise AssertionError("delete changed this login")
    if store.get_token(admin["user_id"], KEY).get("access_token") != "admin-token":
        raise AssertionError("delete cleared this login's token")
    try:
        load_test_season(directory, store, "", caller_id=admin["user_id"], caller_email=admin["email"])
    except TestSeasonError:
        pass
    else:
        raise AssertionError("an empty server key was accepted")


def test_admin_page_keeps_the_gate() -> None:
    """The buttons sit behind the admin check, and the preview does not save."""
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    admin = app[app.index("def page_admin(") : app.index("\ndef ", app.index("def page_admin(") + 1)]
    if "@" in admin:
        raise AssertionError("an email was written into the admin gate")
    if admin.index("viewer_is_admin(") > admin.index("render_test_season("):
        raise AssertionError("the test season is not behind the admin check")
    if "Load test season" in admin or "Delete test season" in admin:
        raise AssertionError("the button label should stay out of the admin slice")
    ui = (ROOT / "ui" / "sample_season_ui.py").read_text(encoding="utf-8")
    for label in ("Load test season", "Delete test season", "View test Home", "View test Plan", "View test Activity"):
        if label not in ui:
            raise AssertionError(label)
    pull = app[app.index("def _pull_for(") : app.index("\ndef ", app.index("def _pull_for(") + 1)]
    if "rio_test_preview" not in pull:
        raise AssertionError("a preview still pulls")
    store = app[app.index("def _sync_browser_store(") : app.index("def _load_shared_plan(")]
    if "rio_test_preview" not in store or "write_record(" not in store:
        raise AssertionError("a preview still saves")
    cloud = (ROOT / "ui" / "cloud_ui.py").read_text(encoding="utf-8")
    persist = cloud[cloud.index("def persist_cloud_season(") : cloud.index("\ndef ", cloud.index("def persist_cloud_season(") + 1)]
    if "rio_test_preview" not in persist:
        raise AssertionError("a preview still writes this login")
    sync = (ROOT / "ui" / "strava_ui.py").read_text(encoding="utf-8")
    once = sync[sync.index("def sync_once(") : sync.index("\ndef ", sync.index("def sync_once(") + 1)]
    if "rio_test_preview" not in once:
        raise AssertionError("a preview still imports")
    hosted = (ROOT / "ui" / "cloud_store.py").read_text(encoding="utf-8")
    create = hosted[hosted.rindex("def create_confirmed_user(") : hosted.index("\n    def ", hosted.rindex("def create_confirmed_user(") + 1)]
    if "email_confirm" not in create or "sign_up" in create or "invite" in create.lower():
        raise AssertionError("the test athlete is not created with the server key")


def main() -> None:
    test_the_season_is_fixed()
    test_load_replaces_and_leaves_the_other_account()
    test_admin_page_keeps_the_gate()
    print("test season ok")


if __name__ == "__main__":
    main()
