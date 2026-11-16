# test_stretch.py — Done marks and sore spots stay on the signed-in athlete.

"""No network. No production Supabase. Today follows the Settings time zone.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from ui.accounts import create_account, last_key
from ui.cloud_store import MemoryDirectory
from ui.settings import local_today

ORIGIN = "http://localhost:3000"


def _client(directory=None, accounts: Path | None = None) -> TestClient:
    app = create_app(directory=directory, accounts=accounts, frontend_origin=ORIGIN, load_env=False)
    return TestClient(app, base_url="https://testserver")


def _sign_up(directory: MemoryDirectory, email: str = "ada@example.com") -> TestClient:
    directory.sign_up(email, "correct-horse", "Ada")
    client = _client(directory)
    response = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if response.status_code != 200:
        raise AssertionError(response.text)
    return client


def test_migration_014_is_the_next_stretch_file_and_scopes_rows_to_auth_uid() -> None:
    names = sorted(path.name for path in (ROOT / "supabase" / "migrations").glob("*.sql"))
    numbers = [int(name.split("_", 1)[0]) for name in names]
    if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
        raise AssertionError(names)
    if 14 not in numbers or max(numbers) != 14:
        raise AssertionError(names)
    sql = (ROOT / "supabase" / "migrations" / "014_stretch.sql").read_text(encoding="utf-8").lower()
    if "information_schema.statistics" in sql:
        raise AssertionError("verification must not use information_schema.statistics")
    for table in ("stretch_completions", "sore_spots"):
        if f"create table if not exists public.{table}" not in sql:
            raise AssertionError(table)
        if f"alter table public.{table} enable row level security" not in sql:
            raise AssertionError(table)
    if sql.count("auth.uid() = user_id") < 4:
        raise AssertionError("both tables need using and with check on auth.uid()")
    if "grant select, insert, update, delete on table public.stretch_completions to authenticated" not in sql:
        raise AssertionError("completions are not granted to the signed-in role")
    if "from anon" not in sql or "revoke all on table public.sore_spots from anon" not in sql:
        raise AssertionError("anon can still read sore spots")
    readme = (ROOT / "supabase" / "migrations" / "README.md").read_text(encoding="utf-8")
    if "014_stretch.sql" not in readme:
        raise AssertionError("the migration note is missing")


def test_today_follows_the_saved_zone_and_another_athlete_cannot_see_the_rows() -> None:
    directory = MemoryDirectory()
    ada = _sign_up(directory)
    token = next(iter(directory.sessions))
    directory.save_timezone(token, "Pacific/Auckland")
    today = local_today("Pacific/Auckland")
    opened = ada.get("/stretch")
    if opened.status_code != 200 or opened.json()["today"] != today.isoformat():
        raise AssertionError(opened.text)
    if opened.json()["completions"] != [] or opened.json()["spots"] != []:
        raise AssertionError(opened.json())
    saved = ada.post("/stretch/spots", json={"region": "calves", "severity": "moderate"})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    spot = saved.json()["spots"][0]
    if spot["region"] != "calves" or spot["severity"] != "moderate" or spot["cleared"] is not False:
        raise AssertionError(spot)
    if spot["started_on"] != today.isoformat() or spot["check_in_on"] != (today + timedelta(days=7)).isoformat():
        raise AssertionError(spot)
    sharp = ada.post("/stretch/spots", json={"region": "neck", "severity": "sharp"})
    if sharp.status_code != 200 or {row["region"] for row in sharp.json()["spots"]} != {"calves", "neck"}:
        raise AssertionError(sharp.text)
    done = ada.post("/stretch/completions", json={"routine_id": "pre-run"})
    if done.status_code != 200 or done.json()["completions"] != [{"date": today.isoformat(), "routine_id": "pre-run"}]:
        raise AssertionError(done.text)
    again = ada.post("/stretch/completions", json={"routine_id": "pre-run"})
    if again.status_code != 200 or again.json()["completions"] != []:
        raise AssertionError(again.text)
    refused = ada.post("/stretch/spots", json={"region": "toes", "severity": "mild"})
    if refused.status_code != 400:
        raise AssertionError(refused.text)

    bob = _sign_up(directory, "bob@example.com")
    theirs = bob.get("/stretch")
    if theirs.status_code != 200 or theirs.json()["spots"] != [] or theirs.json()["completions"] != []:
        raise AssertionError(theirs.text)
    ada_again = ada.get("/stretch")
    if {row["region"] for row in ada_again.json()["spots"]} != {"calves", "neck"}:
        raise AssertionError(ada_again.text)


def test_a_check_in_extends_or_clears_and_a_local_plan_key_stays_last(tmp_path: Path) -> None:
    directory = MemoryDirectory()
    ada = _sign_up(directory)
    token = next(iter(directory.sessions))
    directory.save_timezone(token, "America/Los_Angeles")
    today = local_today("America/Los_Angeles")
    ada.post("/stretch/spots", json={"region": "quads", "severity": "mild"})
    kept = ada.post("/stretch/spots/quads/check-in", json={"still": True})
    if kept.status_code != 200:
        raise AssertionError(kept.text)
    spot = kept.json()["spots"][0]
    if spot["started_on"] != today.isoformat() or spot["check_in_on"] != (today + timedelta(days=7)).isoformat():
        raise AssertionError(spot)
    cleared = ada.post("/stretch/spots/quads/check-in", json={"still": False})
    if cleared.status_code != 200 or cleared.json()["spots"][0]["cleared"] is not True:
        raise AssertionError(cleared.text)
    missing = ada.delete("/stretch/spots/feet")
    if missing.status_code != 404:
        raise AssertionError(missing.text)

    path = tmp_path / "accounts.json"
    email, seal = create_account(path, "local@example.com", "correct-horse", "Local")
    client = _client(None, accounts=path)
    signed = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    generated = client.post(
        "/seasons",
        json={
            "current_time": "2:05.0",
            "start_date": "2026-04-19",
            "goal_time": "1:55.0",
            "goal_date": "2027-03-19",
        },
    )
    if generated.status_code != 200:
        raise AssertionError(generated.text)
    before = last_key(path, email, seal)
    if not isinstance(before, str) or not before.startswith("rio.plan.v1"):
        raise AssertionError(before)
    marked = client.post("/stretch/spots", json={"region": "glutes", "severity": "moderate"})
    if marked.status_code != 200 or marked.json()["spots"][0]["region"] != "glutes":
        raise AssertionError(marked.text)
    if last_key(path, email, seal) != before:
        raise AssertionError("the stretch record became the plan key")
    if client.get("/stretch").json()["spots"][0]["region"] != "glutes":
        raise AssertionError("the local sore spot was not saved")
