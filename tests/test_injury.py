# test_injury.py — rebuilding areas stay on the signed-in athlete.

"""No network. No production Supabase. Today follows the Settings time zone.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from engines.injury import AREAS, level_index, level_name
from ui.cloud_store import MemoryDirectory

ORIGIN = "http://localhost:3000"


def _client(directory=None) -> TestClient:
    app = create_app(directory=directory, frontend_origin=ORIGIN, load_env=False)
    return TestClient(app, base_url="https://testserver")


def _sign_up(directory: MemoryDirectory, email: str = "ada@example.com") -> TestClient:
    directory.sign_up(email, "correct-horse", "Ada")
    client = _client(directory)
    response = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if response.status_code != 200:
        raise AssertionError(response.text)
    return client


def test_level_moves_one_step_every_14_days_and_not_before() -> None:
    anchor = date(2026, 11, 1)
    if level_index(0, anchor, date(2026, 11, 14)) != 0:
        raise AssertionError("day 13 is still easy")
    if level_name(0, anchor, date(2026, 11, 15)) != "medium":
        raise AssertionError("day 14 is medium")
    if level_name(0, anchor, date(2026, 11, 29)) != "hard":
        raise AssertionError("day 28 is hard")
    if level_index(2, anchor, date(2026, 12, 31)) != 2:
        raise AssertionError("hard stays hard")
    if level_index(1, date(2026, 12, 1), date(2026, 11, 1)) != 1:
        raise AssertionError("a future anchor does not move")


def test_migration_017_scopes_injury_rows_to_auth_uid() -> None:
    names = sorted(path.name for path in (ROOT / "supabase" / "migrations").glob("*.sql"))
    numbers = [int(name.split("_", 1)[0]) for name in names]
    if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
        raise AssertionError(names)
    if 17 not in numbers:
        raise AssertionError(names)
    sql = (ROOT / "supabase" / "migrations" / "017_injury_prevention.sql").read_text(encoding="utf-8").lower()
    if "information_schema.statistics" in sql:
        raise AssertionError("verification must not use information_schema.statistics")
    for table in ("injury_areas", "injury_completions"):
        if f"create table if not exists public.{table}" not in sql:
            raise AssertionError(table)
        if f"alter table public.{table} enable row level security" not in sql:
            raise AssertionError(table)
        if f"revoke all on table public.{table} from anon" not in sql:
            raise AssertionError(table)
    if sql.count("auth.uid() = user_id") < 4:
        raise AssertionError("both tables need using and with check on auth.uid()")
    if "level between 0 and 2" not in sql:
        raise AssertionError("level is not limited")
    readme = (ROOT / "supabase" / "migrations" / "README.md").read_text(encoding="utf-8")
    if "017_injury_prevention.sql" not in readme:
        raise AssertionError("the migration note is missing")
    if "bone-stress" not in AREAS or "general" in AREAS:
        raise AssertionError(AREAS)


def test_select_step_back_and_done_stay_on_one_athlete() -> None:
    directory = MemoryDirectory()
    ada = _sign_up(directory)
    opened = ada.get("/injury")
    if opened.status_code != 200 or opened.json()["areas"] != [] or opened.json()["completions"] != []:
        raise AssertionError(opened.text)
    saved = ada.post("/injury/areas", json={"area_id": "achilles"})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    area = saved.json()["areas"][0]
    if area["area_id"] != "achilles" or area["level"] != 0 or area["level_name"] != "easy":
        raise AssertionError(area)
    again = ada.post("/injury/areas", json={"area_id": "achilles"})
    if again.status_code != 200 or again.json()["areas"] != saved.json()["areas"]:
        raise AssertionError(again.text)
    early = ada.post("/injury/areas/achilles/step-back")
    if early.status_code != 400:
        raise AssertionError(early.text)
    refused = ada.post("/injury/areas", json={"area_id": "toes"})
    if refused.status_code != 400:
        raise AssertionError(refused.text)
    done = ada.post("/injury/completions", json={"block_id": "general", "done": True})
    if done.status_code != 200 or done.json()["completions"] != [{"date": opened.json()["today"], "block_id": "general"}]:
        raise AssertionError(done.text)
    still = ada.post("/injury/completions", json={"block_id": "general", "done": True})
    if still.json()["completions"] != done.json()["completions"]:
        raise AssertionError(still.text)
    cleared = ada.post("/injury/completions", json={"block_id": "general", "done": False})
    if cleared.json()["completions"] != []:
        raise AssertionError(cleared.text)
    today = opened.json()["today"]
    counted = ada.get(f"/injury/summary?start={today}&end={today}")
    if counted.status_code != 200 or counted.json() != {"tracked": True, "done": 0, "label": "Injury prevention"}:
        raise AssertionError(counted.text)
    bob = _sign_up(directory, "bob@example.com")
    theirs = bob.get("/injury")
    if theirs.status_code != 200 or theirs.json()["areas"] != []:
        raise AssertionError(theirs.text)
    removed = ada.delete("/injury/areas/achilles")
    if removed.status_code != 200 or removed.json()["areas"] != []:
        raise AssertionError(removed.text)
