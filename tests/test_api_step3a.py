# test_api_step3a.py — the Home card says the workout, including the clock.

"""The Next.js Home reads these fields. The stored plan is not rewritten.

No network. No production Supabase client. The model is not called.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from ui.accounts import create_account

INPUTS = {
    "current_time": "2:02.9",
    "start_date": "2026-04-19",
    "goal_time": "1:55.0",
    "goal_date": "2027-03-19",
}


def test_home_workout_states_the_rep_time(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    create_account(path, "ada@example.com", "correct-horse", "Ada")
    app = create_app(
        directory=None,
        accounts=path,
        frontend_origin="http://localhost:3000",
        load_env=False,
    )
    client = TestClient(app, base_url="https://testserver")
    signed = client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    generated = client.post("/seasons", json=INPUTS)
    if generated.status_code != 200:
        raise AssertionError(generated.text)
    home = client.get("/home")
    if home.status_code != 200:
        raise AssertionError(home.text)
    season = home.json()["season"]
    if not isinstance(season, dict):
        raise AssertionError(home.text)
    nxt = season.get("next")
    if not isinstance(nxt, dict) or not nxt.get("label") or not isinstance(nxt.get("facts"), dict):
        raise AssertionError(nxt)
    line = ""
    prescription = nxt.get("prescription")
    if isinstance(prescription, dict):
        line = str(prescription.get("line") or "")
    if "m @" not in line and "Set your easy pace" not in line and "per " not in line:
        raise AssertionError(nxt)
    days = season.get("next_days")
    if not isinstance(days, list) or len(days) != 3:
        raise AssertionError(days)
    if season.get("pace_status") != "No runs yet":
        raise AssertionError(season.get("pace_status"))
    sessions = generated.json()["plan"]["sessions"]
    if sessions and "label" in sessions[0]:
        raise AssertionError("the stored plan grew a display field")


def test_generate_names_the_bad_field_and_stores_nothing(tmp_path: Path) -> None:
    """POST /seasons returns sequence()'s sentence. A rejected plan is not current."""
    path = tmp_path / "accounts.json"
    create_account(path, "bea@example.com", "correct-horse", "Bea")
    app = create_app(directory=None, accounts=path, frontend_origin="http://localhost:3000", load_env=False)
    client = TestClient(app, base_url="https://testserver")
    signed = client.post("/auth/sign-in", json={"email": "bea@example.com", "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    cases = (
        ({**INPUTS, "current_time": "nope"}, "current_time is not an 800 time"),
        ({**INPUTS, "goal_time": "nope"}, "goal_time is not an 800 time"),
        ({**INPUTS, "goal_date": "2026-04-01"}, "goal_date is before start_date"),
        ({**INPUTS, "start_date": "not-a-date"}, "start_date is not a calendar date"),
        ({**INPUTS, "goal_date": "not-a-date"}, "goal_date is not a calendar date"),
        ({**INPUTS, "start_date": "2026-02-31"}, "start_date is not a calendar date"),
    )
    for body, sentence in cases:
        response = client.post("/seasons", json=body)
        if response.status_code != 400 or response.json().get("detail") != sentence:
            raise AssertionError((sentence, response.status_code, response.text))
    current = client.get("/seasons/current")
    if current.status_code != 404:
        raise AssertionError(current.text)
