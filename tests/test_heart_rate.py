# test_heart_rate.py — Karvonen zones, the heart-rate API, and migration 015.

"""No network. No production Supabase. Workout lines are not changed.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from engines.heart_rate import (
    METHOD_SENTENCE,
    SAFETY_NOTE,
    anchors_from_strava,
    anchors_in_order,
    karvonen_bpm,
    max_hr_from_age,
    require_anchors,
    zones_for,
)
from ui.accounts import create_account, last_key
from ui.cloud_session import new_hosted_sid
from ui.cloud_store import CloudAuthError, MemoryDirectory
from decimal import Decimal

ORIGIN = "http://localhost:3000"
MIGRATIONS = ROOT / "supabase" / "migrations"


def _client(directory=None, accounts: Path | None = None) -> TestClient:
    app = create_app(directory=directory, accounts=accounts, frontend_origin=ORIGIN, load_env=False)
    return TestClient(app, base_url="https://testserver")


def _local(path: Path) -> TestClient:
    create_account(path, "ada@example.com", "correct-horse", "Ada")
    client = _client(accounts=path)
    signed = client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    return client


def _sign_up(directory: MemoryDirectory, email: str, name: str = "Ada") -> TestClient:
    directory.sign_up(email, "correct-horse", name)
    client = _client(directory)
    signed = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    return client


def _bpm(zones: list, number: int) -> tuple[int, int]:
    row = next(item for item in zones if item["zone"] == number)
    return row["low_bpm"], row["high_bpm"]


def test_karvonen_rounds_half_up_and_refuses_a_bad_pair() -> None:
    if max_hr_from_age(30) is not None or max_hr_from_age("30") is not None or max_hr_from_age(None) is not None:
        raise AssertionError("age must not estimate max heart rate yet")
    basic = zones_for(60, 180)
    if basic["method"] != "karvonen" or basic["method_sentence"] != METHOD_SENTENCE:
        raise AssertionError(basic)
    if basic["safety"] != SAFETY_NOTE or basic["custom"] is not False:
        raise AssertionError(basic)
    expected = [(120, 132), (132, 144), (144, 156), (156, 168), (168, 180)]
    if [_bpm(basic["zones"], index + 1) for index in range(5)] != expected:
        raise AssertionError(basic["zones"])
    names = [row["name"] for row in basic["zones"]]
    if names != ["Recovery", "Easy / long", "Tempo", "Threshold", "VO2max / race"]:
        raise AssertionError(names)
    percents = [(row["low_percent"], row["high_percent"]) for row in basic["zones"]]
    if percents != [(50, 60), (60, 70), (70, 80), (80, 90), (90, 100)]:
        raise AssertionError(percents)
    wide = zones_for(Decimal("50"), Decimal("200"))
    if [_bpm(wide["zones"], index + 1) for index in range(5)] != [
        (125, 140),
        (140, 155),
        (155, 170),
        (170, 185),
        (185, 200),
    ]:
        raise AssertionError(wide["zones"])
    fractional = zones_for("62.5", 190)
    if fractional["resting_hr"] != 62.5 or fractional["max_hr"] != 190:
        raise AssertionError(fractional)
    if [_bpm(fractional["zones"], index + 1) for index in range(5)] != [
        (126, 139),
        (139, 152),
        (152, 165),
        (165, 177),
        (177, 190),
    ]:
        raise AssertionError(fractional["zones"])
    if karvonen_bpm(Decimal("62.5"), Decimal("190"), 50) != 126:
        raise AssertionError("half up")
    edges = zones_for(30, 140)
    if edges["zones"][0]["low_bpm"] != 85 or edges["zones"][-1]["high_bpm"] != 140:
        raise AssertionError(edges["zones"])
    top = zones_for(100, 230)
    if top["zones"][-1]["high_bpm"] != 230 or not anchors_in_order(Decimal(100), Decimal(230)):
        raise AssertionError(top)
    if anchors_in_order(Decimal(80), Decimal(80)) or anchors_in_order(Decimal(90), Decimal(80)):
        raise AssertionError("max has to be above resting")
    for resting, maximum, sentence in (
        (29, 180, "Enter a resting heart rate between 30 and 100."),
        (101, 180, "Enter a resting heart rate between 30 and 100."),
        (True, 180, "Enter a resting heart rate between 30 and 100."),
        ("slow", 180, "Enter a resting heart rate between 30 and 100."),
        (60, 139, "Enter a max heart rate between 140 and 230."),
        (60, 231, "Enter a max heart rate between 140 and 230."),
        (60, float("nan"), "Enter a max heart rate between 140 and 230."),
    ):
        try:
            require_anchors(resting, maximum)
        except ValueError as exc:
            if str(exc) != sentence:
                raise AssertionError((resting, maximum, str(exc))) from exc
        else:
            raise AssertionError((resting, maximum))


def test_custom_bounds_reset_to_karvonen_and_strava_zones_do_not_guess() -> None:
    edited = [
        {"zone": 1, "low_bpm": 118, "high_bpm": 130},
        {"zone": 2, "low_bpm": 130, "high_bpm": 144},
        {"zone": 3, "low_bpm": 144, "high_bpm": 156},
        {"zone": 4, "low_bpm": 156, "high_bpm": 168},
        {"zone": 5, "low_bpm": 168, "high_bpm": 180},
    ]
    custom = zones_for(60, 180, edited)
    if custom["custom"] is not True or _bpm(custom["zones"], 1) != (118, 130):
        raise AssertionError(custom)
    same = zones_for(60, 180, zones_for(60, 180)["zones"])
    if same["custom"] is not True and same["zones"] != zones_for(60, 180)["zones"]:
        raise AssertionError(same)
    if same["custom"] is not False:
        raise AssertionError("defaults must not be stored as custom")
    for bounds in (
        edited[:4],
        [{**row, "high_bpm": row["low_bpm"]} for row in edited],
        [{**edited[0], "low_bpm": 20}, *edited[1:]],
        [{**row, "zone": row["zone"] + 1} for row in edited],
    ):
        try:
            zones_for(60, 180, bounds)
        except ValueError as exc:
            if "Zone boundaries" not in str(exc) and "between 30 and 230" not in str(exc):
                raise AssertionError(str(exc)) from exc
        else:
            raise AssertionError(bounds)
    standard = {
        "heart_rate": {
            "custom_zones": False,
            "zones": [
                {"min": 0, "max": 115},
                {"min": 115, "max": 145},
                {"min": 145, "max": 163},
                {"min": 163, "max": 180},
                {"min": 180, "max": -1},
            ],
        }
    }
    if anchors_from_strava(standard) != (None, None):
        raise AssertionError(anchors_from_strava(standard))
    if anchors_from_strava({"resting_heartrate": 48, "max_heartrate": 192}) != (48, 192):
        raise AssertionError("explicit Strava anchors")
    nested = anchors_from_strava({"heart_rate": {"resting_hr": 55, "max_hr": 90}})
    if nested != (55, None):
        raise AssertionError(nested)
    if anchors_from_strava({"resting_hr": 120, "max_hr": 180}) != (None, 180):
        raise AssertionError("resting out of range")
    if anchors_from_strava([]) != (None, None):
        raise AssertionError("a list is not athlete zones")


def test_migration_015_is_the_only_new_number_and_scopes_the_row() -> None:
    names = sorted(path.name for path in MIGRATIONS.glob("*.sql"))
    numbers = [int(name.split("_", 1)[0]) for name in names]
    if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
        raise AssertionError(names)
    if 4 in numbers:
        raise AssertionError("004 was left unused; do not revive it")
    if numbers.count(15) != 1 or 15 not in numbers:
        raise AssertionError(names)
    sql = (MIGRATIONS / "015_heart_rate.sql").read_text(encoding="utf-8").lower()
    if "information_schema.statistics" in sql:
        raise AssertionError("verification must not use information_schema.statistics")
    if "create table if not exists public.heart_rate" not in sql:
        raise AssertionError("table")
    if "alter table public.heart_rate enable row level security" not in sql:
        raise AssertionError("rls")
    if sql.count("auth.uid() = user_id") < 2:
        raise AssertionError("policy needs using and with check")
    if "grant select, insert, update, delete on table public.heart_rate to authenticated" not in sql:
        raise AssertionError("authenticated grant")
    if "revoke all on table public.heart_rate from anon" not in sql:
        raise AssertionError("anon")
    if "heart_rate_own" not in sql or "heart_rate_touch_updated_at" not in sql:
        raise AssertionError("policy or trigger name")
    readme = (MIGRATIONS / "README.md").read_text(encoding="utf-8")
    if "015_heart_rate.sql" not in readme:
        raise AssertionError("the migration note is missing")
    prescribe = (ROOT / "engines" / "prescribe.py").read_text(encoding="utf-8")
    pace = (ROOT / "engines" / "pace.py").read_text(encoding="utf-8")
    if "zones_for" in prescribe or "karvonen" in pace.lower():
        raise AssertionError("prescriptions must stay unchanged in this phase")


def test_put_saves_zones_for_one_athlete_and_refuses_a_bad_value(tmp_path: Path) -> None:
    client = _local(tmp_path / "accounts.json")
    opened = client.get("/heart-rate")
    if opened.status_code != 200 or opened.json()["resting_hr"] is not None or opened.json()["zones"] != []:
        raise AssertionError(opened.text)
    if opened.json()["strava_prefill"]["available"] is not False or "profile:read_all" not in opened.json()["strava_prefill"]["note"]:
        raise AssertionError(opened.json()["strava_prefill"])
    empty = client.put("/heart-rate", json={})
    if empty.status_code != 400 or empty.json()["detail"] != "Nothing to save.":
        raise AssertionError(empty.text)
    low = client.put("/heart-rate", json={"resting_hr": 20, "max_hr": 180})
    if low.status_code != 400 or low.json()["detail"] != "Enter a resting heart rate between 30 and 100.":
        raise AssertionError(low.text)
    high = client.put("/heart-rate", json={"resting_hr": 60, "max_hr": 120})
    if high.status_code != 400 or "140 and 230" not in high.json()["detail"]:
        raise AssertionError(high.text)
    if client.get("/heart-rate").json()["resting_hr"] is not None:
        raise AssertionError("a refused value was stored")
    saved = client.put("/heart-rate", json={"resting_hr": 60, "max_hr": 180})
    if saved.status_code != 200 or saved.json()["custom"] is not False:
        raise AssertionError(saved.text)
    if _bpm(saved.json()["zones"], 2) != (132, 144) or saved.json()["method_sentence"] != METHOD_SENTENCE:
        raise AssertionError(saved.json())
    moved = client.put(
        "/heart-rate",
        json={
            "zones": [
                {"zone": 1, "low_bpm": 118, "high_bpm": 130},
                {"zone": 2, "low_bpm": 130, "high_bpm": 144},
                {"zone": 3, "low_bpm": 144, "high_bpm": 156},
                {"zone": 4, "low_bpm": 156, "high_bpm": 168},
                {"zone": 5, "low_bpm": 168, "high_bpm": 182},
            ]
        },
    )
    if moved.status_code != 200 or moved.json()["custom"] is not True or _bpm(moved.json()["zones"], 5) != (168, 182):
        raise AssertionError(moved.text)
    again = client.get("/heart-rate")
    if again.json()["custom"] is not True or again.json()["resting_hr"] != 60:
        raise AssertionError(again.text)
    reset = client.put("/heart-rate", json={"reset": True})
    if reset.status_code != 200 or reset.json()["custom"] is not False or _bpm(reset.json()["zones"], 1) != (120, 132):
        raise AssertionError(reset.text)
    recalc = client.put("/heart-rate", json={"resting_hr": 50, "max_hr": 200})
    if recalc.status_code != 200 or recalc.json()["custom"] is not False or _bpm(recalc.json()["zones"], 1) != (125, 140):
        raise AssertionError(recalc.text)
    skipped = client.put("/heart-rate", json={"no_monitor": True})
    if skipped.status_code != 200 or skipped.json()["no_monitor"] is not True or skipped.json()["max_hr"] != 200:
        raise AssertionError(skipped.text)


def test_another_athlete_cannot_see_the_saved_zones() -> None:
    directory = MemoryDirectory()
    ada = _sign_up(directory, "ada@example.com", "Ada")
    ada.put("/heart-rate", json={"resting_hr": 58, "max_hr": 176})
    bea = _sign_up(directory, "bea@example.com", "Bea")
    opened = bea.get("/heart-rate")
    if opened.status_code != 200 or opened.json()["resting_hr"] is not None:
        raise AssertionError(opened.text)
    bea.put("/heart-rate", json={"no_monitor": True})
    if ada.get("/heart-rate").json()["resting_hr"] != 58 or ada.get("/heart-rate").json()["no_monitor"] is not False:
        raise AssertionError("Bea's toggle changed Ada")
    if bea.get("/heart-rate").json()["no_monitor"] is not True:
        raise AssertionError("Bea's toggle was not saved")


def test_saving_heart_rate_leaves_the_season_templates(tmp_path: Path) -> None:
    from tests.test_api import _generate

    path = tmp_path / "accounts.json"
    email, seal = create_account(path, "ada@example.com", "correct-horse", "Ada")
    client = _client(accounts=path)
    signed = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    paced = client.patch("/settings", json={"easy_pace": "7:25", "easy_pace_unit": "mi"})
    if paced.status_code != 200:
        raise AssertionError(paced.text)
    first = _generate(client)
    before_ids = [row.get("template_id") for row in first["plan"]["sessions"]]
    if not before_ids:
        raise AssertionError("the season has no sessions")
    plan_key = last_key(path, email, seal)
    if not isinstance(plan_key, str) or not plan_key.startswith("rio.plan.v1"):
        raise AssertionError(plan_key)
    saved = client.put("/heart-rate", json={"resting_hr": 55, "max_hr": 188})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    if last_key(path, email, seal) != plan_key:
        raise AssertionError("the heart-rate record became the plan key")
    again = client.get("/seasons/current")
    if again.status_code != 200:
        raise AssertionError(again.text)
    after_ids = [row.get("template_id") for row in again.json()["plan"]["sessions"]]
    if before_ids != after_ids:
        raise AssertionError("heart rate changed the prescribed templates")


class _Result:
    def __init__(self, data: list) -> None:
        self.data = data


class _Query:
    def __init__(self, table: "_Table", op: str, payload: dict | None = None) -> None:
        self.table = table
        self.op = op
        self.payload = payload
        self.filters: list[tuple[str, object]] = []

    def eq(self, key: str, value: object) -> "_Query":
        self.filters.append((key, value))
        return self

    def execute(self) -> _Result:
        if self.table.fail:
            raise RuntimeError("relation heart_rate does not exist")
        if self.op == "select":
            return _Result([dict(row) for row in self.table.rows if self._match(row)])
        row = dict(self.payload or {})
        self.table.rows[:] = [existing for existing in self.table.rows if existing.get("user_id") != row.get("user_id")]
        self.table.rows.append(row)
        return _Result([row])

    def _match(self, row: dict) -> bool:
        return all(row.get(key) == value for key, value in self.filters)


class _Table:
    def __init__(self, rows: list, fail: bool = False) -> None:
        self.rows = rows
        self.fail = fail

    def select(self, _columns: str) -> _Query:
        return _Query(self, "select")

    def upsert(self, payload: dict, on_conflict: str = "") -> _Query:
        if on_conflict != "user_id":
            raise AssertionError(on_conflict)
        return _Query(self, "upsert", payload)


class _HostedClient:
    def __init__(self, rows: list, fail: bool = False) -> None:
        self.rows = rows
        self.fail = fail

    def table(self, name: str) -> _Table:
        if name != "heart_rate":
            raise AssertionError(name)
        return _Table(self.rows, self.fail)


class _HostedDirectory:
    def __init__(self, fail: bool = False) -> None:
        self.rows: list[dict] = [
            {"user_id": "someone-else", "resting_hr": 40, "max_hr": 160, "no_monitor": False, "zones": None}
        ]
        self.fail = fail
        self.sessions: dict[str, dict] = {}

    def sign_in(self, email: object, password: object) -> dict:
        if password != "correct-horse":
            raise CloudAuthError("Email or password does not match.")
        return {
            "access_token": "token-ada",
            "refresh_token": "refresh-ada",
            "user_id": "athlete-1",
            "email": str(email),
            "display_name": "Ada",
            "role": "athlete",
        }

    def save_hosted_session(self, record: object) -> str:
        sid = new_hosted_sid()
        self.sessions[sid] = dict(record) if isinstance(record, dict) else {}
        return sid

    def load_hosted_session(self, sid: object) -> dict | None:
        row = self.sessions.get(sid) if isinstance(sid, str) else None
        return dict(row) if isinstance(row, dict) else None

    def user_id(self, access_token: object) -> str:
        if access_token != "token-ada":
            raise CloudAuthError("Sign in again.")
        return "athlete-1"

    def load_bundle(self, access_token: object) -> dict:
        self.user_id(access_token)
        return {"profile": {"timezone": "America/Los_Angeles", "display_name": "Ada", "email": "ada@example.com"}}

    def _user_client(self, token: object):
        self.user_id(token)
        return _HostedClient(self.rows, self.fail)

    def _token_user(self, _client, access_token: str) -> str:
        return self.user_id(access_token)


def test_hosted_rows_stay_on_the_signed_in_athlete_and_a_missing_table_is_503() -> None:
    directory = _HostedDirectory()
    client = _client(directory)
    signed = client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    if signed.status_code != 200 or signed.json().get("kind") != "hosted":
        raise AssertionError(signed.text)
    opened = client.get("/heart-rate")
    if opened.status_code != 200 or opened.json()["resting_hr"] is not None:
        raise AssertionError(opened.text)
    saved = client.put("/heart-rate", json={"resting_hr": 62.5, "max_hr": 190})
    if saved.status_code != 200 or saved.json()["resting_hr"] != 62.5 or _bpm(saved.json()["zones"], 3) != (152, 165):
        raise AssertionError(saved.text)
    mine = [row for row in directory.rows if row.get("user_id") == "athlete-1"]
    if len(mine) != 1 or len(directory.rows) != 2:
        raise AssertionError(directory.rows)
    broken = _HostedDirectory(fail=True)
    failed = _client(broken)
    failed.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    missing = failed.get("/heart-rate")
    if missing.status_code != 503 or "migration 015" not in missing.json()["detail"]:
        raise AssertionError(missing.text)
