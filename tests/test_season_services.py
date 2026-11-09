# test_season_services.py — commit, pull, and season save without Streamlit.

"""Local accounts use a temp file. Hosted accounts use a fake directory.

Nothing here constructs a Supabase client or reads a service-role key.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.activity_pull import PULL_PAGES, run_activity_pull
from services.season_commit import (
    apply_activity_marks,
    commit_mark,
    commit_result,
    commit_watchless_mark,
)
from services.season_store import (
    LocalSeasonError,
    delete_local_plans,
    filter_plan_rows,
    filter_saved_inputs,
    load_hosted_season,
    load_local_season,
    remove_past_season,
    same_season,
    save_cleared_marks,
    save_hosted_season,
    save_local_season,
)
from ui.accounts import AccountError, create_account, read_record
from ui.activities import PullError
from ui.cloud_store import CloudAuthError, MemoryDirectory
from ui.plan_store import storage_key
from ui.result import goal_seconds
from engines.season import adapt, sequence

INPUTS = ("2:02.9", "2026-04-19", "1:55.0", "2027-03-19")
PAST = ("2:05.0", "2020-01-06", "1:59.0", "2020-06-01")
ACTIVE = ("2:05.0", "2026-01-05", "1:59.0", "2027-06-01")
TODAY = date(2026, 11, 9)


def _plan() -> dict:
    return sequence(*INPUTS)


def _tuesday(plan: dict) -> dict:
    for session in plan["sessions"]:
        if session["week_number"] == 1 and session["day_of_week"] == "Tuesday":
            return session
    raise AssertionError("week 1 has no Tuesday")


def _ids(plan: dict, week: int) -> list[str]:
    return [
        session["template_id"]
        for session in plan["sessions"]
        if session["week_number"] == week
    ]


def test_services_do_not_import_streamlit() -> None:
    """The extracted modules stay free of the shell."""
    for path in sorted((ROOT / "services").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "streamlit" in text or "session_state" in text:
            raise AssertionError(path.name)
        if "import supabase" in text or "from supabase" in text:
            raise AssertionError(path.name)
        if "RIO_SUPABASE" in text or "SERVICE_ROLE" in text:
            raise AssertionError(path.name)


def test_pull_pages_match_the_shell() -> None:
    """The shell tuple and the service tuple name the same pages."""
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    block = app[app.index("_PULL_PAGES = (") : app.index("def _pull_for(")]
    names = tuple(re.findall(r'"(page_[a-z_]+)"', block))
    if names != PULL_PAGES:
        raise AssertionError((names, PULL_PAGES))


def test_commit_result_adapts_once_from_the_quality_base() -> None:
    """A fast rep stores the mark and moves later weeks. A second save uses the base."""
    plan = _plan()
    session = _tuesday(plan)
    actuals: dict = {}
    marks: dict = {}
    bases: dict = {}
    first = commit_result(
        plan,
        session,
        "20",
        [None, 20, None],
        "44521",
        actuals,
        marks,
        bases,
        goal_seconds("1:55.0"),
    )
    if not first.committed or first.plan is None or first.marks != {1: "smashing"}:
        raise AssertionError(first)
    if first.note_mark != "smashing" or first.note_detail != "20":
        raise AssertionError((first.note_mark, first.note_detail))
    saved = actuals[session["date"]]
    if saved["mark"] != "smashing" or saved["numbers"] != [20] or saved["intervals"] != "44521":
        raise AssertionError(saved)
    if saved["slots"] != [None, 20.0, None]:
        raise AssertionError(saved["slots"])
    if _ids(first.plan, 1) != _ids(plan, 1):
        raise AssertionError("the judged week moved")

    def _templates(body: dict) -> list[tuple]:
        return [
            (row["week_number"], row["day_of_week"], row["template_id"])
            for row in body["sessions"]
        ]

    expected = _templates(adapt(plan, 1, "smashing"))
    if _templates(first.plan) != expected:
        raise AssertionError("later weeks did not follow adapt()")
    if expected == _templates(plan):
        raise AssertionError("smashing left the season unchanged")
    if list(bases) != [1]:
        raise AssertionError(bases)
    held = [session["template_id"] for session in plan["sessions"]]
    second = commit_result(
        first.plan,
        session,
        "20",
        [20],
        "44521",
        actuals,
        first.marks,
        bases,
        goal_seconds("1:55.0"),
    )
    if not second.committed or second.plan is None:
        raise AssertionError(second)
    if _templates(second.plan) != _templates(first.plan):
        raise AssertionError("a second result adapted the already adapted week")
    if [session["template_id"] for session in plan["sessions"]] != held:
        raise AssertionError("commit changed the caller's plan")
    if "probability" in saved or "readiness_score" in saved:
        raise AssertionError(saved)


def test_empty_or_invalid_text_does_not_store_a_result() -> None:
    plan = _plan()
    session = _tuesday(plan)
    actuals: dict = {}
    for text in ("", "nope", "   "):
        outcome = commit_result(
            plan, session, text, None, None, actuals, {}, {}, goal_seconds("1:55.0")
        )
        if outcome.committed or outcome.error or actuals:
            raise AssertionError((text, outcome, actuals))


def test_a_bad_mark_returns_the_error_and_keeps_the_plan() -> None:
    plan = _plan()
    actuals: dict = {"2026-04-21": {"mark": "on_track"}}
    outcome = commit_mark(plan, 1, "nope", actuals, {3: "on_track"}, {})
    if outcome.committed or outcome.plan is not None:
        raise AssertionError(outcome)
    if outcome.error is None or "outcome" not in outcome.error:
        raise AssertionError(outcome.error)
    if actuals != {"2026-04-21": {"mark": "on_track"}}:
        raise AssertionError(actuals)


def test_watchless_mark_uses_the_same_adapt() -> None:
    plan = _plan()
    session = _tuesday(plan)
    actuals: dict = {}
    row = {
        "text": "54",
        "numbers": [54],
        "mark": "smashing",
        "template_id": session["template_id"],
        "completed": True,
    }
    outcome = commit_watchless_mark(plan, session, row, actuals, {}, {})
    if not outcome.committed or outcome.marks != {1: "smashing"}:
        raise AssertionError(outcome)
    if actuals[session["date"]] is not row:
        raise AssertionError(actuals)
    if outcome.note_detail != "54":
        raise AssertionError(outcome.note_detail)


def test_activity_marks_store_the_pull_and_skip_a_second_pass() -> None:
    plan = _plan()
    session = _tuesday(plan)
    bases: dict = {}
    activity = {
        "id": "run-1",
        "date": session["date"],
        "matched": True,
        "name": "Run",
        "reps": [20],
        "template_id": session["template_id"],
    }
    first = apply_activity_marks(plan, [activity], {}, goal_seconds("1:55.0"), bases, {})
    if not first.applied or first.marks != {1: "smashing"} or first.actuals is None:
        raise AssertionError(first)
    if first.plan is None or _ids(first.plan, 1) != _ids(plan, 1):
        raise AssertionError("the judged week moved")
    second = apply_activity_marks(
        first.plan,
        [activity],
        first.actuals,
        goal_seconds("1:55.0"),
        bases,
        first.marks,
    )
    if second.applied or second.notice:
        raise AssertionError(second)


class _FakeDirectory:
    """Records the bundle. It does not open a socket."""

    def __init__(self) -> None:
        self.bundles: dict[str, dict] = {}
        self.deleted: list[tuple] = []

    def save_bundle(self, token: object, bundle: object) -> None:
        if not isinstance(token, str) or not isinstance(bundle, dict):
            raise CloudAuthError("This account could not be saved.")
        self.bundles[token] = json.loads(json.dumps(bundle))

    def load_bundle(self, token: object) -> dict:
        if not isinstance(token, str) or token not in self.bundles:
            raise CloudAuthError("Sign in again.")
        return json.loads(json.dumps(self.bundles[token]))

    def delete_season(self, token: object, inputs: object, today: object) -> None:
        self.deleted.append((token, inputs, today))
        bundle = self.bundles.get(token if isinstance(token, str) else "")
        if bundle is None:
            raise CloudAuthError("Sign in again.")
        kept = []
        for row in bundle.get("plans") or []:
            ident = (
                row.get("current_time"),
                row.get("start_date"),
                row.get("goal_time"),
                row.get("goal_date"),
            )
            if ident == inputs:
                continue
            kept.append(row)
        bundle["plans"] = kept


def _bundle_plan(plan: dict, marks: dict, actuals: dict) -> dict:
    return {
        "current_time": INPUTS[0],
        "start_date": INPUTS[1],
        "goal_time": INPUTS[2],
        "goal_date": INPUTS[3],
        "plan": plan,
        "marks": marks,
        "actuals": actuals,
    }


def test_hosted_save_skips_an_unchanged_digest_and_omits_hidden_state() -> None:
    """A fake directory receives the plan, not the quality base or the note."""
    directory = _FakeDirectory()
    plan = {"ontology_version": "v0.1", "sessions": [], "season_length_weeks": 0}
    digest = save_hosted_season(
        directory,
        "token-ada",
        inputs=INPUTS,
        plan=plan,
        marks={1: "on_track"},
        actuals={"2026-04-21": {"mark": "on_track", "text": "57.5"}},
        display_name="Ada",
        saved_hash=None,
    )
    if not isinstance(digest, str) or not digest:
        raise AssertionError(digest)
    again = save_hosted_season(
        directory,
        "token-ada",
        inputs=INPUTS,
        plan=plan,
        marks={1: "on_track"},
        actuals={"2026-04-21": {"mark": "on_track", "text": "57.5"}},
        display_name="Ada",
        saved_hash=digest,
    )
    if again is not None:
        raise AssertionError("an unchanged season was written again")
    saved = directory.bundles["token-ada"]
    text = json.dumps(saved)
    if "season_quality_base" in text or "rio_workout_notes" in text or "probability" in text:
        raise AssertionError(saved)
    if saved["plans"][0]["marks"] != {"1": "on_track"}:
        raise AssertionError(saved["plans"])
    if saved["goal"]["event"] != "800m" or saved["profile"]["display_name"] != "Ada":
        raise AssertionError(saved)
    loaded = load_hosted_season(directory, "token-ada")
    if loaded["plans"][0]["plan"] != plan:
        raise AssertionError(loaded)
    if save_hosted_season(None, "token-ada", inputs=INPUTS, plan=plan, marks={}, actuals={}, display_name="", saved_hash=None) is not None:
        raise AssertionError("a missing directory was written")


def test_memory_directory_round_trip_and_past_delete() -> None:
    """The in-memory hosted store keeps one athlete's season and deletes a past one."""
    directory = MemoryDirectory()
    ada = directory.sign_up("ada-service@example.com", "password-one", "Ada")
    beau = directory.sign_up("beau-service@example.com", "password-two", "Beau")
    plan = {"ontology_version": "v0.1", "sessions": [{"date": PAST[1]}], "season_length_weeks": 1}
    other = {"ontology_version": "v0.1", "sessions": [{"date": ACTIVE[1]}], "season_length_weeks": 1}
    save_hosted_season(
        directory,
        ada["access_token"],
        inputs=PAST,
        plan=plan,
        marks={1: "on_track"},
        actuals={},
        display_name="Ada",
        saved_hash=None,
    )
    loaded = load_hosted_season(directory, ada["access_token"])
    if loaded["plans"][0]["goal_date"] != PAST[3] or loaded["plans"][0]["marks"] != {1: "on_track"}:
        raise AssertionError(loaded["plans"])
    if loaded["profile"]["display_name"] != "Ada":
        raise AssertionError(loaded["profile"])
    # The memory stand-in stores the bundle's plan list as given. Seed both
    # seasons the way a hosted row set already would, then delete the past one.
    directory.plans[ada["user_id"]] = [
        {
            "current_time": PAST[0],
            "start_date": PAST[1],
            "goal_time": PAST[2],
            "goal_date": PAST[3],
            "plan": plan,
            "marks": {1: "on_track"},
            "actuals": {},
        },
        {
            "current_time": ACTIVE[0],
            "start_date": ACTIVE[1],
            "goal_time": ACTIVE[2],
            "goal_date": ACTIVE[3],
            "plan": other,
            "marks": {},
            "actuals": {"2026-01-06": {"mark": "on_track"}},
        },
    ]
    save_hosted_season(
        directory,
        beau["access_token"],
        inputs=PAST,
        plan=plan,
        marks={2: "smashing"},
        actuals={},
        display_name="Beau",
        saved_hash=None,
    )
    remove_past_season(
        hosted=True,
        directory=directory,
        token=ada["access_token"],
        path=None,
        email=None,
        secret=None,
        inputs=PAST,
        today=TODAY,
    )
    after = load_hosted_season(directory, ada["access_token"])
    dates = [row["goal_date"] for row in after["plans"]]
    if dates != [ACTIVE[3]]:
        raise AssertionError(dates)
    beau_dates = [row["goal_date"] for row in load_hosted_season(directory, beau["access_token"])["plans"]]
    if beau_dates != [PAST[3]] or load_hosted_season(directory, beau["access_token"])["plans"][0]["marks"] != {2: "smashing"}:
        raise AssertionError(beau_dates)
    try:
        remove_past_season(
            hosted=True,
            directory=directory,
            token=ada["access_token"],
            path=None,
            email=None,
            secret=None,
            inputs=ACTIVE,
            today=TODAY,
        )
    except CloudAuthError as exc:
        message = str(exc)
    else:
        raise AssertionError("the current season was deleted")
    if "can't be deleted" not in message:
        raise AssertionError(message)


def _account_file() -> tuple[Path, Path]:
    directory = Path(tempfile.mkdtemp(prefix="rio-services-"))
    return directory, directory / "accounts.json"


def test_local_save_load_and_delete_stay_on_that_account() -> None:
    """One athlete's sealed record does not open for the other athlete."""
    folder, path = _account_file()
    try:
        email, secret = create_account(path, "ada@example.com", "password-one", "Ada")
        other_email, other_secret = create_account(path, "beau@example.com", "password-two", "Beau")
        key = storage_key(PAST)
        save_local_season(
            path,
            email,
            secret,
            key,
            {1: "on_track"},
            {"2020-01-07": {"text": "60", "numbers": [60], "mark": "on_track", "template_id": "se_400_r90_x6"}},
            [{"id": "local-run", "date": "2020-01-07", "matched": True, "name": "Run"}],
        )
        save_local_season(path, email, secret, storage_key(ACTIVE), {2: "smashing"}, {}, [])
        save_local_season(path, other_email, other_secret, key, {4: "not_hitting"}, {}, [])
        marks, actuals, activities = load_local_season(path, email, secret, key)
        if marks != {1: "on_track"} or activities[0]["id"] != "local-run":
            raise AssertionError((marks, activities))
        if "2020-01-07" not in actuals:
            raise AssertionError(actuals)
        other_marks = load_local_season(path, other_email, other_secret, key)[0]
        if other_marks != {4: "not_hitting"}:
            raise AssertionError(other_marks)
        raw = read_record(path, email, secret, key)
        if not isinstance(raw, str) or "season_quality_base" in raw or "rio_workout_notes" in raw:
            raise AssertionError(raw)
        remove_past_season(
            hosted=False,
            directory=None,
            token=None,
            path=path,
            email=email,
            secret=secret,
            inputs=PAST,
            today=TODAY,
        )
        if load_local_season(path, email, secret, key) != ({}, {}, []):
            raise AssertionError("the past season was still stored")
        if load_local_season(path, email, secret, storage_key(ACTIVE))[0] != {2: "smashing"}:
            raise AssertionError("the current season was deleted")
        if load_local_season(path, other_email, other_secret, key)[0] != {4: "not_hitting"}:
            raise AssertionError("the other account was deleted")
        try:
            remove_past_season(
                hosted=False,
                directory=None,
                token=None,
                path=path,
                email=email,
                secret=secret,
                inputs=ACTIVE,
                today=TODAY,
            )
        except AccountError as exc:
            message = str(exc)
        else:
            raise AssertionError("the current local season was deleted")
        if "can't be deleted" not in message:
            raise AssertionError(message)
        save_cleared_marks(path, email, secret, ACTIVE)
        if load_local_season(path, email, secret, storage_key(ACTIVE)) != ({}, {}, []):
            raise AssertionError("clear left a mark")
        delete_local_plans(path, email, secret)
        if read_record(path, email, secret, storage_key(ACTIVE)) != "":
            raise AssertionError("reset left a plan")
        try:
            load_local_season(path, email, "not-the-secret", key)
        except LocalSeasonError as exc:
            if "could not be opened" not in str(exc):
                raise AssertionError(str(exc))
        else:
            raise AssertionError("a bad seal opened the record")
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def test_deleted_season_lists_drop_only_that_season() -> None:
    rows = filter_plan_rows(
        [
            {"current_time": PAST[0], "start_date": PAST[1], "goal_time": PAST[2], "goal_date": PAST[3]},
            {"current_time": ACTIVE[0], "start_date": ACTIVE[1], "goal_time": ACTIVE[2], "goal_date": ACTIVE[3]},
            "skip",
        ],
        PAST,
    )
    if rows != [
        {"current_time": ACTIVE[0], "start_date": ACTIVE[1], "goal_time": ACTIVE[2], "goal_date": ACTIVE[3]}
    ]:
        raise AssertionError(rows)
    if filter_plan_rows(None, PAST) is not None:
        raise AssertionError("a missing list was replaced")
    kept = filter_saved_inputs([PAST, ACTIVE, "nope"], PAST)
    if kept != [ACTIVE, "nope"]:
        raise AssertionError(kept)
    if not same_season(list(PAST), PAST) or same_season(ACTIVE, PAST):
        raise AssertionError("the open season was not recognized")


def test_pull_branches() -> None:
    """Refresh, a live page, Strava, and a failed pull keep the shell's order."""

    def _run(**overrides):
        calls = {"sync_all": 0, "sync_recent": 0, "restore": 0, "judge": 0, "today": 0, "connected": 0}
        notices = []
        stored = []
        loaded = []

        def sync_all(sessions, activities, today):
            calls["sync_all"] += 1
            if activities != ["old"] or today != TODAY:
                raise AssertionError((activities, today))
            return ["all"]

        def sync_recent(sessions, activities, today):
            calls["sync_recent"] += 1
            if overrides.get("explode"):
                raise PullError("intervals down")
            return ["recent"]

        values = {
            "page_name": "page_dashboard",
            "test_preview": False,
            "refresh": False,
            "already_pulled": False,
            "activities_loaded": None,
            "activities_trigger": None,
            "plan": {"sessions": [{"date": "2026-04-21"}]},
            "activities": lambda: ["old"],
            "today": lambda: calls.__setitem__("today", calls["today"] + 1) or TODAY,
            "strava_connected": lambda: calls.__setitem__("connected", calls["connected"] + 1) or False,
            "strava_gate_pending": lambda: False,
            "sync_all": sync_all,
            "sync_recent": sync_recent,
            "restore_rows": lambda: calls.__setitem__("restore", calls["restore"] + 1),
            "on_notice": notices.append,
            "clear_notice": lambda: notices.append("clear"),
            "on_activities": stored.append,
            "apply_marks": lambda plan: calls.__setitem__("judge", calls["judge"] + 1),
            "on_loaded": loaded.append,
        }
        values.update(overrides)
        apply_marks = values.pop("apply_marks")
        explode = values.pop("explode", False)
        run_activity_pull(_apply_activity_marks=apply_marks, **values)
        return calls, notices, stored, loaded, explode

    calls, notices, stored, loaded, _ = _run(test_preview=True)
    if any(calls.values()) or notices or stored or loaded:
        raise AssertionError("a preview pulled")
    calls, notices, stored, loaded, _ = _run(page_name="page_past_seasons")
    if any(calls.values()) or loaded:
        raise AssertionError("past seasons pulled")
    calls, notices, stored, loaded, _ = _run(plan=None)
    if calls["sync_recent"] or calls["connected"]:
        raise AssertionError("a missing plan pulled")
    calls, notices, stored, loaded, _ = _run(already_pulled=True)
    if calls["restore"] != 1 or calls["sync_recent"] or loaded:
        raise AssertionError(calls)
    calls, notices, stored, loaded, _ = _run()
    if calls["sync_recent"] != 1 or calls["sync_all"] or stored != [["recent"]] or loaded != ["page_dashboard"]:
        raise AssertionError((calls, stored, loaded))
    if calls["judge"] != 1 or notices != ["clear"]:
        raise AssertionError((calls, notices))
    calls, notices, stored, loaded, _ = _run(page_name="page_activity", refresh=True, already_pulled=True)
    if calls["sync_all"] != 1 or calls["sync_recent"] or stored != [["all"]] or calls["judge"] != 1:
        raise AssertionError((calls, stored))
    if loaded != ["page_activity"]:
        raise AssertionError(loaded)
    calls, notices, stored, loaded, _ = _run(page_name="page_library")
    if calls["judge"] or loaded != ["load"] or stored != [["recent"]]:
        raise AssertionError((calls, loaded, stored))
    calls, notices, stored, loaded, _ = _run(
        page_name="page_library",
        activities_trigger="load",
        already_pulled=False,
    )
    if calls["sync_recent"] or loaded:
        raise AssertionError("the same load pulled twice")
    calls, notices, stored, loaded, _ = _run(strava_connected=lambda: True)
    if calls["sync_recent"] or calls["sync_all"] or calls["judge"] or calls["restore"] != 1:
        raise AssertionError(calls)
    if loaded != ["page_dashboard"]:
        raise AssertionError(loaded)
    calls, notices, stored, loaded, _ = _run(strava_gate_pending=lambda: True)
    if calls["connected"] or calls["sync_recent"] or calls["restore"] or loaded:
        raise AssertionError(calls)
    calls, notices, stored, loaded, _ = _run(explode=True)
    if notices != ["intervals down"] or stored or calls["judge"] or loaded != ["page_dashboard"]:
        raise AssertionError((notices, stored, loaded, calls))
    if calls["restore"] != 1:
        raise AssertionError("a failed pull dropped the restore")


def main() -> None:
    test_services_do_not_import_streamlit()
    test_pull_pages_match_the_shell()
    test_commit_result_adapts_once_from_the_quality_base()
    test_empty_or_invalid_text_does_not_store_a_result()
    test_a_bad_mark_returns_the_error_and_keeps_the_plan()
    test_watchless_mark_uses_the_same_adapt()
    test_activity_marks_store_the_pull_and_skip_a_second_pass()
    test_hosted_save_skips_an_unchanged_digest_and_omits_hidden_state()
    test_memory_directory_round_trip_and_past_delete()
    test_local_save_load_and_delete_stay_on_that_account()
    test_deleted_season_lists_drop_only_that_season()
    test_pull_branches()
    print("season services ok")


if __name__ == "__main__":
    main()
