# test_core.py — a core done mark stays on the signed-in athlete.

"""No network. No production Supabase. Today follows the Settings time zone.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
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


def test_migration_018_scopes_core_rows_to_auth_uid() -> None:
    names = sorted(path.name for path in (ROOT / "supabase" / "migrations").glob("*.sql"))
    numbers = [int(name.split("_", 1)[0]) for name in names]
    if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
        raise AssertionError(names)
    if 18 not in numbers:
        raise AssertionError(names)
    sql = (ROOT / "supabase" / "migrations" / "018_core_completions.sql").read_text(encoding="utf-8").lower()
    if "information_schema.statistics" in sql:
        raise AssertionError("verification must not use information_schema.statistics")
    if "create table if not exists public.core_completions" not in sql:
        raise AssertionError(sql)
    if "enable row level security" not in sql or "revoke all on table public.core_completions from anon" not in sql:
        raise AssertionError(sql)
    if sql.count("auth.uid() = user_id") < 2:
        raise AssertionError("core completions need using and with check on auth.uid()")
    readme = (ROOT / "supabase" / "migrations" / "README.md").read_text(encoding="utf-8")
    if "018_core_completions.sql" not in readme:
        raise AssertionError("the migration note is missing")


def test_done_stays_on_one_athlete_and_the_week_can_count_it() -> None:
    directory = MemoryDirectory()
    ada = _sign_up(directory)
    opened = ada.get("/core")
    if opened.status_code != 200 or opened.json()["completions"] != []:
        raise AssertionError(opened.text)
    today = opened.json()["today"]
    saved = ada.post("/core/completions", json={"done": True})
    if saved.status_code != 200 or saved.json()["completions"] != [{"date": today}]:
        raise AssertionError(saved.text)
    again = ada.post("/core/completions", json={"done": True})
    if again.json()["completions"] != [{"date": today}]:
        raise AssertionError(again.text)
    counted = ada.get(f"/core/summary?start={today}&end={today}")
    if counted.status_code != 200 or counted.json() != {"tracked": True, "done": 1, "label": "Core"}:
        raise AssertionError(counted.text)
    bob = _sign_up(directory, "bob@example.com")
    if bob.get("/core").json()["completions"] != []:
        raise AssertionError(bob.get("/core").text)
    cleared = ada.post("/core/completions", json={"done": False})
    if cleared.json()["completions"] != []:
        raise AssertionError(cleared.text)
