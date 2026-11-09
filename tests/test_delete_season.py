# test_delete_season.py — a past season can be deleted. The current one cannot.

from __future__ import annotations

import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.accounts import (
    AccountError,
    create_account,
    delete_past_season,
    read_record,
    record_keys,
    write_record,
)
from ui.cloud_store import CloudAuthError, SupabaseDirectory, reset_memory_directory
from ui.past_seasons import confirm_deletes, season_summary
from ui.plan_store import dump_record, storage_key
from ui.profile import dump_goal, profile_key

PAST = ("2:10.0", "2025-01-04", "2:00.0", "2025-06-01")
OTHER = ("2:08.0", "2024-01-06", "1:59.0", "2024-05-01")
ACTIVE = ("2:02.9", "2026-04-19", "1:55.0", "2027-03-19")
TODAY = date(2026, 11, 9)


def _fresh_file():
    directory = Path(tempfile.mkdtemp(prefix="rio-delete-season-"))
    return directory, directory / "accounts.json"


def _body() -> str:
    return dump_record(
        {1: "on_track"},
        {
            "2025-02-01": {
                "completed": True,
                "numbers": [121.4],
                "template_id": "rr_800_r0_x1",
                "text": "2:01.4",
            },
            "2025-02-08": {
                "completed": True,
                "numbers": [118.2],
                "template_id": "rr_800_r0_x1",
                "text": "1:58.2",
            },
            "2025-03-01": {
                "completed": False,
                "numbers": [],
                "template_id": "aer_4000_r0_x1",
                "text": "",
            },
        },
        [
            {"date": "2025-02-01", "distance": 6400, "id": "a", "matched": True, "name": "Easy"},
            {"date": "2025-02-08", "distance": 800, "id": "b", "matched": True, "name": "Race"},
        ],
    )


def test_summary_uses_only_stored_facts() -> None:
    """Dates and the goal time are shown. A missing fact is left out."""
    bare = season_summary(PAST, None)
    if bare != [("Season", "2025-01-04 – 2025-06-01"), ("Goal time", "2:00.0")]:
        raise AssertionError(bare)
    if any(label == "Event" or label == "Workouts logged" for label, _value in bare):
        raise AssertionError(bare)
    stored = {
        "event": "800m",
        "actuals": {
            "2025-02-01": {
                "completed": True,
                "numbers": [118.2],
                "template_id": "rr_800_r0_x1",
                "text": "1:58.2",
            },
            "2025-02-08": {
                "completed": True,
                "numbers": [121.4],
                "template_id": "rr_800_r0_x1",
                "text": "2:01.4",
            },
            "2025-03-01": {
                "missed": True,
                "numbers": [],
                "template_id": "aer_4000_r0_x1",
                "text": "",
            },
            "2025-03-08": {
                "mark": "on_track",
                "numbers": [48.0, 47.5],
                "template_id": "ap_800_r90_x5",
                "text": "48.0",
            },
        },
        "activities": [
            {"distance": 6400},
            {"distance": 800},
            {"name": "no distance"},
        ],
        "plan": {
            "sessions": [
                {"date": "2025-02-01", "reason_codes": ["phase_1"]},
                {"date": "2025-02-08", "reason_codes": ["phase_1"]},
                {"date": "2025-03-01", "reason_codes": ["phase_2"]},
            ]
        },
        "notes": ["felt smooth"],
    }
    rows = dict(season_summary(PAST, stored))
    if rows["Event"] != "800m" or rows["Goal time"] != "2:00.0":
        raise AssertionError(rows)
    if rows["Workouts logged"] != "4" or rows["Workouts completed"] != "2":
        raise AssertionError(rows)
    if rows["Distance logged"] != "7200 m":
        raise AssertionError(rows)
    if rows["Best 800"] != "1:58.2" or rows["Last 800"] != "2:01.4":
        raise AssertionError(rows)
    if rows["Phases completed"] != "1" or rows["Notes"] != "1":
        raise AssertionError(rows)
    if "Insights" in rows or "Adaptations" in rows:
        raise AssertionError(rows)
    if "48.0" in rows.values():
        raise AssertionError("a rep split was shown as an 800")


def test_confirm_does_not_delete_and_the_current_season_cannot() -> None:
    """The panel opening is not a delete. A current season never confirms."""
    if confirm_deletes(PAST, False, TODAY):
        raise AssertionError("an unconfirmed season was deleted")
    if confirm_deletes(PAST, None, TODAY):
        raise AssertionError("a missing press was treated as confirm")
    if not confirm_deletes(PAST, True, TODAY):
        raise AssertionError("a confirmed past season was refused")
    if confirm_deletes(ACTIVE, True, TODAY):
        raise AssertionError("the current season confirmed")
    if confirm_deletes(ACTIVE, False, TODAY):
        raise AssertionError("the current season confirmed")


def test_local_delete_removes_one_past_season() -> None:
    """The past season and its profile go. The other season and the account stay."""
    directory, path = _fresh_file()
    try:
        email, secret = create_account(path, "ada@example.com", "correct-horse", "Ada")
        other_email, other_secret = create_account(path, "bea@example.com", "other-password", "Bea")
        write_record(path, email, secret, storage_key(PAST), _body())
        write_record(path, email, secret, profile_key(PAST), dump_goal("1:59.0"))
        write_record(path, email, secret, storage_key(OTHER), dump_record({}, {}, []))
        write_record(path, email, secret, profile_key(OTHER), dump_goal("1:59.0"))
        write_record(path, email, secret, storage_key(ACTIVE), dump_record({2: "on_track"}, {}, []))
        write_record(path, email, secret, "rio.note.v1\nkeep", "keep this")
        write_record(path, other_email, other_secret, storage_key(PAST), _body())
        try:
            delete_past_season(path, email, secret, ACTIVE, TODAY)
        except AccountError as exc:
            if "can't be deleted" not in str(exc):
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("the current season was deleted")
        if read_record(path, email, secret, storage_key(ACTIVE)) == "":
            raise AssertionError("the current season was removed")
        delete_past_season(path, email, secret, PAST, TODAY)
        if read_record(path, email, secret, storage_key(PAST)) != "":
            raise AssertionError("the past season stayed")
        if read_record(path, email, secret, profile_key(PAST)) != "":
            raise AssertionError("the past season profile stayed")
        if read_record(path, email, secret, storage_key(OTHER)) == "":
            raise AssertionError("another past season was removed")
        if read_record(path, email, secret, profile_key(OTHER)) == "":
            raise AssertionError("another season profile was removed")
        if read_record(path, email, secret, "rio.note.v1\nkeep") != "keep this":
            raise AssertionError("a note that is not the season was removed")
        if read_record(path, other_email, other_secret, storage_key(PAST)) == "":
            raise AssertionError("another athlete's season was removed")
        left = record_keys(path, email, secret, "rio.plan.v1\n")
        if set(left) != {storage_key(OTHER), storage_key(ACTIVE)}:
            raise AssertionError(left)
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def _plan(inputs, actuals=None, plan=None):
    return {
        "current_time": inputs[0],
        "start_date": inputs[1],
        "goal_time": inputs[2],
        "goal_date": inputs[3],
        "plan": plan or {"sessions": []},
        "marks": {},
        "actuals": actuals or {},
    }


def test_hosted_memory_delete_is_scoped() -> None:
    """One athlete's past season goes. The current season and the other athlete stay."""
    directory = reset_memory_directory()
    ada = directory.sign_up("ada@example.com", "password-one", "Ada")
    bea = directory.sign_up("bea@example.com", "password-two", "Bea")
    past_actuals = {
        "2025-02-01": {"completed": True, "template_id": "rr_800_r0_x1", "text": "2:01.4", "numbers": [121.4]},
        "2025-02-08": {"completed": True, "template_id": "aer_4000_r0_x1", "text": "", "numbers": []},
    }
    other_actuals = {
        "2025-02-01": {"completed": True, "template_id": "rr_800_r0_x1", "text": "2:05.0", "numbers": [125]},
    }
    directory.save_bundle(
        ada["access_token"],
        {
            "goal": {"event": "800m", "goal_time": "1:55.0", "goal_date": "2027-03-19", "current_mark": "2:02.9"},
            "plans": [
                _plan(PAST, past_actuals),
                _plan(OTHER, {"2024-02-01": {"completed": True, "template_id": "aer_4000_r0_x1", "text": "", "numbers": []}}),
                _plan(ACTIVE, {"2026-05-01": {"completed": True, "template_id": "aer_4000_r0_x1", "text": "", "numbers": []}}),
            ],
            "results": [
                {
                    "id": "tied-payload",
                    "logged_on": "2025-04-01",
                    "template_id": "rr_800_r0_x1",
                    "payload": {
                        "current_time": PAST[0],
                        "start_date": PAST[1],
                        "goal_time": PAST[2],
                        "goal_date": PAST[3],
                    },
                },
                {
                    "id": "tied-day",
                    "logged_on": "2025-02-08",
                    "template_id": "aer_4000_r0_x1",
                    "payload": {"numbers": [1200]},
                },
                {
                    "id": "range-only",
                    "logged_on": "2025-03-01",
                    "template_id": "aer_4000_r0_x1",
                    "payload": {"numbers": [1200]},
                },
                {
                    "id": "shared-day",
                    "logged_on": "2025-02-01",
                    "template_id": "rr_800_r0_x1",
                    "payload": {"numbers": [125]},
                },
            ],
        },
    )
    # The shared day is also on the other past season, so that result stays.
    ada_plans = directory.plans[ada["user_id"]]
    for row in ada_plans:
        if row["start_date"] == OTHER[1]:
            row["actuals"] = other_actuals
    directory.save_bundle(
        bea["access_token"],
        {
            "goal": {"goal_time": "2:00"},
            "plans": [_plan(PAST, past_actuals)],
            "results": [{"id": "bea-result", "logged_on": "2025-02-01", "template_id": "rr_800_r0_x1", "payload": {}}],
        },
    )
    try:
        directory.delete_season(ada["access_token"], ACTIVE, TODAY)
    except CloudAuthError as exc:
        if "can't be deleted" not in str(exc):
            raise AssertionError(exc) from exc
    else:
        raise AssertionError("the current season was deleted")
    if len(directory.plans[ada["user_id"]]) != 3:
        raise AssertionError(directory.plans[ada["user_id"]])
    directory.delete_season(ada["access_token"], PAST, TODAY)
    left = [
        (row["start_date"], row["goal_date"])
        for row in directory.plans[ada["user_id"]]
    ]
    if left != [(OTHER[1], OTHER[3]), (ACTIVE[1], ACTIVE[3])]:
        raise AssertionError(left)
    if directory.plans[ada["user_id"]][1]["actuals"].get("2026-05-01") is None:
        raise AssertionError("the current season's workout was removed")
    kept_ids = [row["id"] for row in directory.results[ada["user_id"]]]
    if kept_ids != ["range-only", "shared-day"]:
        raise AssertionError(kept_ids)
    if directory.goals[ada["user_id"]]["goal_time"] != "1:55.0":
        raise AssertionError("the account goal was removed")
    if directory.plans[bea["user_id"]][0]["start_date"] != PAST[1]:
        raise AssertionError("another athlete's season was removed")
    if directory.results[bea["user_id"]][0]["id"] != "bea-result":
        raise AssertionError("another athlete's result was removed")


class _Store:
    def __init__(self) -> None:
        self.tables = {
            "plans": [],
            "results": [],
            "goals": [{"user_id": "ada", "goal_time": "1:55.0"}],
            "profiles": [{"id": "ada", "email": "ada@example.com"}],
        }
        self.tokens = {"token-ada": "ada", "token-bea": "bea"}
        self.keys: list[str] = []
        self.touched: list[str] = []
        self.rpc_missing = True
        self.rpc_calls: list[dict] = []


class _Query:
    def __init__(self, store: _Store, name: str) -> None:
        self.store = store
        self.name = name
        self.op = "select"
        self.filters: list[tuple[str, str]] = []

    def select(self, *_args, **_kwargs):
        self.op = "select"
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, column, value):
        self.filters.append((column, str(value)))
        return self

    def execute(self):
        rows = self.store.tables.setdefault(self.name, [])

        def match(row: dict) -> bool:
            for column, value in self.filters:
                if str(row.get(column) or "") != value:
                    return False
            return True

        if self.op == "select":
            return SimpleNamespace(data=[dict(row) for row in rows if match(row)])
        if self.op == "delete":
            self.store.tables[self.name] = [row for row in rows if not match(row)]
            return SimpleNamespace(data=[])
        raise AssertionError(self.op)


class _Rpc:
    def __init__(self, store: _Store, name: str, params: dict) -> None:
        self.store = store
        self.name = name
        self.params = params

    def execute(self):
        self.store.rpc_calls.append(self.params)
        if self.store.rpc_missing:
            raise RuntimeError("42883 delete_past_season does not exist")
        return SimpleNamespace(data=[])


class _Client:
    def __init__(self, store: _Store, key: str) -> None:
        self.store = store
        self.key = key
        self.token = ""
        self.auth = self
        self.postgrest = SimpleNamespace(auth=self._auth)
        store.keys.append(key)

    def _auth(self, token: str) -> None:
        self.token = token

    def get_user(self, jwt=None):
        found = self.store.tokens.get(jwt or self.token)
        if not found:
            raise RuntimeError("bad token")
        return SimpleNamespace(user=SimpleNamespace(id=found))

    def table(self, name: str) -> _Query:
        self.store.touched.append(name)
        return _Query(self.store, name)

    def rpc(self, name: str, params: dict) -> _Rpc:
        return _Rpc(self.store, name, params)


def _hosted(store: _Store) -> SupabaseDirectory:
    directory = SupabaseDirectory("https://example.supabase.co", "anon-key", "service-key")
    directory._client = lambda key: _Client(store, key)  # type: ignore[method-assign]
    return directory


def test_hosted_client_deletes_only_that_season() -> None:
    """The signed-in key deletes one season. The service key is not used."""
    store = _Store()
    store.tables["plans"] = [
        {
            "id": "past",
            "user_id": "ada",
            "current_time": PAST[0],
            "start_date": PAST[1],
            "goal_time": PAST[2],
            "goal_date": PAST[3],
            "actuals": {
                "2025-02-01": {"template_id": "rr_800_r0_x1", "completed": True},
            },
        },
        {
            "id": "other",
            "user_id": "ada",
            "current_time": OTHER[0],
            "start_date": OTHER[1],
            "goal_time": OTHER[2],
            "goal_date": OTHER[3],
            "actuals": {"2024-02-01": {"template_id": "aer_4000_r0_x1", "completed": True}},
        },
        {
            "id": "active",
            "user_id": "ada",
            "current_time": ACTIVE[0],
            "start_date": ACTIVE[1],
            "goal_time": ACTIVE[2],
            "goal_date": ACTIVE[3],
            "actuals": {},
        },
        {
            "id": "bea",
            "user_id": "bea",
            "current_time": PAST[0],
            "start_date": PAST[1],
            "goal_time": PAST[2],
            "goal_date": PAST[3],
            "actuals": {"2025-02-01": {"template_id": "rr_800_r0_x1", "completed": True}},
        },
    ]
    store.tables["results"] = [
        {
            "id": "tied",
            "user_id": "ada",
            "logged_on": "2025-02-01",
            "template_id": "rr_800_r0_x1",
            "payload": {},
        },
        {
            "id": "loose",
            "user_id": "ada",
            "logged_on": "2025-03-01",
            "template_id": "aer_4000_r0_x1",
            "payload": {"numbers": [1]},
        },
        {
            "id": "bea-row",
            "user_id": "bea",
            "logged_on": "2025-02-01",
            "template_id": "rr_800_r0_x1",
            "payload": {},
        },
    ]
    directory = _hosted(store)
    try:
        directory.delete_season("token-ada", ACTIVE, TODAY)
    except CloudAuthError:
        pass
    else:
        raise AssertionError("the current season was deleted")
    if store.keys:
        raise AssertionError("a refused delete still called the server")
    directory.delete_season("token-ada", PAST, TODAY)
    if "service-key" in store.keys or store.keys != ["anon-key"]:
        raise AssertionError(store.keys)
    if "goals" in store.touched or "profiles" in store.touched:
        raise AssertionError(store.touched)
    plan_ids = [row["id"] for row in store.tables["plans"]]
    if plan_ids != ["other", "active", "bea"]:
        raise AssertionError(plan_ids)
    result_ids = [row["id"] for row in store.tables["results"]]
    if result_ids != ["loose", "bea-row"]:
        raise AssertionError(result_ids)
    if store.tables["goals"][0]["goal_time"] != "1:55.0":
        raise AssertionError("the goal row was removed")


def test_hosted_rpc_is_one_call_when_the_function_exists() -> None:
    """A present database function is the delete. The row deletes are not repeated."""
    store = _Store()
    store.rpc_missing = False
    store.tables["plans"] = [
        {
            "id": "past",
            "user_id": "ada",
            "current_time": PAST[0],
            "start_date": PAST[1],
            "goal_time": PAST[2],
            "goal_date": PAST[3],
            "actuals": {},
        }
    ]
    directory = _hosted(store)
    directory.delete_season("token-ada", PAST, TODAY)
    if store.touched:
        raise AssertionError(store.touched)
    if store.rpc_calls != [
        {
            "p_current_time": PAST[0],
            "p_start_date": PAST[1],
            "p_goal_time": PAST[2],
            "p_goal_date": PAST[3],
            "p_today": TODAY.isoformat(),
        }
    ]:
        raise AssertionError(store.rpc_calls)
    if store.tables["plans"][0]["id"] != "past":
        raise AssertionError("the fallback also deleted the row")


def test_page_asks_before_it_deletes_and_hides_the_current_season() -> None:
    """Delete season opens the panel. Delete permanently is the only delete."""
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    css = (ROOT / "ui" / "static" / "app.css").read_text(encoding="utf-8")
    entry = app[app.index("def _past_entry(") : app.index("def page_past_seasons(")]
    confirm = app[app.index("def _past_confirm(") : app.index("def _past_entry(")]
    page = app[app.index("def page_past_seasons(") : app.index("\ndef _auth_screen(")]
    if entry.index("is_past_season(") > entry.index("Delete season"):
        raise AssertionError("delete is offered before the past check")
    if "delete_season(" in entry or "delete_past_season(" in entry:
        raise AssertionError("the row button deletes")
    if "Delete permanently" not in confirm or "Cancel" not in confirm:
        raise AssertionError("the confirm panel is missing a button")
    if "can't be undone" not in app:
        raise AssertionError("the warning does not say it can't be undone")
    if confirm.index("confirm_deletes(") > confirm.index("_commit_past_delete("):
        raise AssertionError("delete runs before confirm")
    if "season_summary(" not in app or "rio_past_deleted" not in page:
        raise AssertionError("the panel or the confirmation is missing")
    if "Season deleted." not in app:
        raise AssertionError("there is no confirmation after delete")
    if 'background: #C2461F' not in css or "#E25A32" not in css:
        raise AssertionError("the delete control lost the brand colors")
    about = (ROOT / "ui" / "about.py").read_text(encoding="utf-8")
    if "delete_past_season" in about or "Delete season" in about:
        raise AssertionError("about changed")
    sql = (ROOT / "supabase" / "migrations" / "008_delete_past_season.sql").read_text(encoding="utf-8")
    if "auth.uid()" not in sql or "delete_past_season" not in sql:
        raise AssertionError("the migration is not scoped to the signed-in athlete")
    if "information_schema" in sql:
        raise AssertionError("the migration uses the wrong catalog")


def main() -> None:
    test_summary_uses_only_stored_facts()
    test_confirm_does_not_delete_and_the_current_season_cannot()
    test_local_delete_removes_one_past_season()
    test_hosted_memory_delete_is_scoped()
    test_hosted_client_deletes_only_that_season()
    test_hosted_rpc_is_one_call_when_the_function_exists()
    test_page_asks_before_it_deletes_and_hides_the_current_season()
    print("delete season ok")


if __name__ == "__main__":
    main()
