# test_api_usual_long.py — usual long run on settings, and the season snapshot.

"""The distance is stored in meters. An open season keeps the rung it started with.

No network. No production Supabase client.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from engines.season import long_run_start_meters
from ui.accounts import create_account
from ui.cloud_store import MemoryDirectory

INPUTS = {
    "current_time": "2:02.9",
    "start_date": "2026-04-19",
    "goal_time": "1:55.0",
    "goal_date": "2027-03-19",
}
EIGHT_MILES = round(8 * 1609.344)


def _client(directory=None, accounts: Path | None = None) -> TestClient:
    app = create_app(
        directory=directory,
        accounts=accounts,
        frontend_origin="http://localhost:3000",
        load_env=False,
    )
    return TestClient(app, base_url="https://testserver")


def _local(path: Path) -> TestClient:
    create_account(path, "ada@example.com", "correct-horse", "Ada")
    client = _client(accounts=path)
    signed = client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    return client


def _hosted() -> tuple[MemoryDirectory, TestClient]:
    directory = MemoryDirectory()
    directory.sign_up("ada@example.com", "correct-horse", "Ada")
    client = _client(directory)
    signed = client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    return directory, client


def _saturday(plan: dict, week: int = 1) -> str:
    for session in plan["sessions"]:
        if session["week_number"] == week and session["day_of_week"] == "Saturday":
            return session["template_id"]
    raise AssertionError(f"week {week} has no Saturday")


def test_a_local_usual_long_run_is_saved_in_meters_and_checked(tmp_path: Path) -> None:
    client = _local(tmp_path / "accounts.json")
    saved = client.patch("/settings", json={"usual_long_m": EIGHT_MILES})
    if saved.status_code != 200 or saved.json()["prefs"]["usual_long_m"] != EIGHT_MILES:
        raise AssertionError(saved.text)
    if saved.json()["prefs"]["usual_long_note"]:
        raise AssertionError(saved.json()["prefs"]["usual_long_note"])
    again = client.get("/auth/me")
    if again.json()["prefs"]["usual_long_m"] != EIGHT_MILES:
        raise AssertionError(again.text)
    short = client.patch("/settings", json={"usual_long_m": 1000})
    if short.status_code != 400 or "3.2 and 26 mi" not in short.json()["detail"]:
        raise AssertionError(short.text)
    client.patch("/settings", json={"pace_units": "km"})
    low = client.patch("/settings", json={"usual_long_m": 4900, "pace_units": "km"})
    if low.status_code != 400 or low.json()["detail"] != "Enter a distance between 5 and 42 km.":
        raise AssertionError(low.text)
    if client.get("/auth/me").json()["prefs"]["usual_long_m"] != EIGHT_MILES:
        raise AssertionError("a rejected distance replaced the saved one")


def test_generate_snapshots_the_rung_and_an_open_season_rejects_a_change(tmp_path: Path) -> None:
    client = _local(tmp_path / "accounts.json")
    made = client.post("/seasons", json={**INPUTS, "usual_long_m": 12000})
    if made.status_code != 200:
        raise AssertionError(made.text)
    plan = made.json()["plan"]
    if plan["long_run_start_m"] != 10000 or _saturday(plan) != "aer_10000_r0_x1":
        raise AssertionError((plan.get("long_run_start_m"), _saturday(plan)))
    if client.get("/auth/me").json()["prefs"]["usual_long_m"] != 12000:
        raise AssertionError("generate did not save the usual long run")
    profile = client.get("/profile")
    if profile.status_code != 200 or profile.json()["usual_long_locked"] is not True:
        raise AssertionError(profile.text)
    if profile.json()["usual_long_m"] != 12000:
        raise AssertionError(profile.json())
    locked = client.patch("/settings", json={"usual_long_m": 15000})
    if locked.status_code != 400 or "next season" not in locked.json()["detail"]:
        raise AssertionError(locked.text)
    same = client.patch("/settings", json={"usual_long_m": 12000, "theme": "dark"})
    if same.status_code != 200 or same.json()["prefs"]["theme"] != "dark":
        raise AssertionError(same.text)
    if same.json()["prefs"]["usual_long_m"] != 12000:
        raise AssertionError(same.json()["prefs"])
    cleared = client.post("/seasons/current/clear", json={"confirm": True})
    if cleared.status_code != 200 or cleared.json()["plan"]["long_run_start_m"] != 10000:
        raise AssertionError(cleared.text)
    if _saturday(cleared.json()["plan"]) != "aer_10000_r0_x1":
        raise AssertionError("clearing marks rebuilt Saturday from a new usual")


def test_a_hosted_usual_is_on_the_account_and_a_short_usual_is_flagged() -> None:
    _directory, client = _hosted()
    five = round(5 * 1609.344)
    saved = client.patch("/settings", json={"usual_long_m": five})
    if saved.status_code != 200 or saved.json()["prefs"]["usual_long_m"] != five:
        raise AssertionError(saved.text)
    if saved.json()["prefs"]["usual_long_note"]:
        raise AssertionError(saved.json()["prefs"])
    if long_run_start_meters(five) != 8000:
        raise AssertionError(long_run_start_meters(five))
    made = client.post("/seasons", json=INPUTS)
    if made.status_code != 200 or made.json()["plan"]["long_run_start_m"] != 8000:
        raise AssertionError(made.text)
    if _saturday(made.json()["plan"]) != "aer_8000_r0_x1":
        raise AssertionError(_saturday(made.json()["plan"]))
    removed = client.request("DELETE", "/seasons/past", json={**INPUTS, "confirm": True})
    if removed.status_code != 200:
        raise AssertionError(removed.text)
    cleared = client.patch("/settings", json={"usual_long_m": None})
    if cleared.status_code != 200 or cleared.json()["prefs"]["usual_long_m"] is not None:
        raise AssertionError(cleared.text)
    fresh = client.post("/seasons", json=INPUTS)
    if fresh.status_code != 200 or fresh.json()["plan"]["long_run_start_m"] != 9500:
        raise AssertionError(fresh.text)
