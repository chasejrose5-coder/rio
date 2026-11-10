# test_api_step3_activity.py — Activity figures, Strava callback base, and the lap table.

"""No network. No production Supabase. The model is not called.

The callback base is an origin. The path stays /strava/callback.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from api.strava_flow import redirect_for_api
from engines.classify import classify
from engines.explain import explain
from engines.normalize import normalize
from ui.accounts import create_account
from ui.last_session import open_intervals
from ui.settings import local_today
from ui.strava import redirect_uri

FILE = ROOT / "tests" / "fixtures" / "intervals" / "synthetic_se_400_with_recovery.json"
INPUTS = {
    "current_time": "2:02.9",
    "start_date": "2026-04-19",
    "goal_time": "1:55.0",
    "goal_date": "2027-03-19",
}


def _client(path: Path) -> TestClient:
    app = create_app(directory=None, accounts=path, frontend_origin="http://localhost:3000", load_env=False)
    return TestClient(app, base_url="https://testserver")


def _signed(path: Path, email: str = "ada@example.com") -> TestClient:
    create_account(path, email, "correct-horse", "Ada")
    client = _client(path)
    signed = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    return client


def test_callback_base_is_configurable_and_streamlit_keeps_its_root(monkeypatch) -> None:
    monkeypatch.setenv("RIO_APP_URL", "https://riotraining.streamlit.app")
    monkeypatch.delenv("RIO_STRAVA_REDIRECT_URI", raising=False)
    monkeypatch.delenv("RIO_CALLBACK_BASE_URL", raising=False)
    if redirect_uri() != "https://riotraining.streamlit.app/":
        raise AssertionError(redirect_uri())
    if redirect_for_api() != "https://riotraining.streamlit.app/":
        raise AssertionError(redirect_for_api())
    monkeypatch.setenv("RIO_CALLBACK_BASE_URL", "https://rio.example/")
    if redirect_for_api() != "https://rio.example/strava/callback":
        raise AssertionError(redirect_for_api())
    monkeypatch.setenv("RIO_STRAVA_REDIRECT_URI", "https://override.example/custom")
    if redirect_for_api() != "https://override.example/custom":
        raise AssertionError("a full redirect did not win")
    if redirect_uri() != "https://riotraining.streamlit.app/":
        raise AssertionError("Streamlit's own redirect changed")


def test_activity_uses_the_settings_zone_and_keeps_rows(tmp_path: Path) -> None:
    client = _signed(tmp_path / "accounts.json")
    saved = client.patch("/settings", json={"timezone": "America/Los_Angeles", "date_format": "short"})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    missing = client.get("/activities")
    if missing.status_code != 404:
        raise AssertionError(missing.text)
    generated = client.post("/seasons", json=INPUTS)
    if generated.status_code != 200:
        raise AssertionError(generated.text)
    found = client.get("/activities")
    if found.status_code != 200:
        raise AssertionError(found.text)
    body = found.json()
    for key in ("rows", "all", "cards", "groups", "summary", "weekly_meters", "heart", "figures", "logged"):
        if key not in body:
            raise AssertionError(key)
    if body["start_date"] != "2026-04-19" or body["goal_date"] != "2027-03-19":
        raise AssertionError((body["start_date"], body["goal_date"]))
    if "token" in str(body.get("strava")):
        raise AssertionError(body["strava"])
    me = client.get("/auth/me")
    zone_today = local_today("America/Los_Angeles").isoformat()
    if me.json()["today"] != zone_today:
        raise AssertionError(me.json()["today"])
    if body["figures"]["heart"] != "—":
        raise AssertionError(body["figures"])
    if body["figures"]["distance"] != "0.0 mi":
        raise AssertionError(body["figures"])


def test_intervals_body_returns_laps_and_the_same_seconds(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RIO_ADMIN_EMAIL", "admin@example.com")
    os.environ["RIO_ADMIN_EMAIL"] = "admin@example.com"
    os.environ["RIO_EXPLAIN_API_KEY"] = ""
    athlete = _signed(tmp_path / "athlete.json")
    if athlete.get("/fixtures/intervals/synthetic_se_400_with_recovery.json").status_code != 403:
        raise AssertionError("a normal account read the laps")
    if athlete.get("/fixtures/session?name=race_800").status_code != 403:
        raise AssertionError("a normal account opened Last Session")
    admin = _signed(tmp_path / "admin.json", "admin@example.com")
    admin.patch("/settings", json={"pace_units": "km"})
    filled = admin.get("/fixtures/intervals/synthetic_se_400_with_recovery.json")
    if filled.status_code != 200:
        raise AssertionError(filled.text)
    body = filled.json()
    payload, banner = open_intervals(FILE)
    laps = normalize(payload)["laps"]
    if body["laps"] != laps:
        raise AssertionError(body["laps"])
    if body["times"] != [lap["seconds"] for lap in laps]:
        raise AssertionError(body["times"])
    if body["distance_heading"] != "Distance (m)":
        raise AssertionError(body["distance_heading"])
    if body["rows"][0]["Seconds"] != 57.5 or body["rows"][0]["Rest (s)"] != 90:
        raise AssertionError(body["rows"][0])
    if body["rows"][0]["Distance (m)"] != "400":
        raise AssertionError(body["rows"][0])
    result = classify(payload)
    if body["family"] != result["family"] or body["prose"] != explain(result):
        raise AssertionError(body["prose"])
    if body["date"] != "2026-10-25" or banner is None:
        raise AssertionError((body["date"], banner))
    if "access_token" in filled.text:
        raise AssertionError("a token leaked into the lap body")
