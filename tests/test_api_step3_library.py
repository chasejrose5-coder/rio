# test_api_step3_library.py — the frozen menu, in the athlete's distance words.

"""No network. No production Supabase. Explain is not called.

Family order is the capacity label. Search matches the stored name and the
name on screen. A failed menu is the exception sentence.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from api.screens import library_view
from ui.accounts import create_account

MENU = ROOT / "rio" / "templates" / "800m"


def _client(path: Path) -> TestClient:
    app = create_app(directory=None, accounts=path, frontend_origin="http://localhost:3000", load_env=False)
    return TestClient(app, base_url="https://testserver")


def _signed(path: Path) -> TestClient:
    create_account(path, "ada@example.com", "correct-horse", "Ada")
    client = _client(path)
    signed = client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    return client


def test_library_lists_every_template_and_sorts_families(tmp_path: Path) -> None:
    client = _signed(tmp_path / "accounts.json")
    body = client.get("/library")
    if body.status_code != 200:
        raise AssertionError(body.text)
    payload = body.json()
    files = sorted(MENU.glob("*.yml"))
    ids = [row["id"] for row in payload["workouts"]]
    if payload["count"] != len(files) or ids != sorted(ids) or len(ids) != len(set(ids)):
        raise AssertionError(f"{payload['count']} rows, {len(ids)} ids, {len(files)} files")
    labels = [item["label"] for item in payload["families"]]
    if labels != [
        "Aerobic",
        "Aerobic power",
        "Anaerobic",
        "Max velocity",
        "Race readiness",
        "Speed",
        "Speed endurance",
        "Threshold",
    ]:
        raise AssertionError(labels)
    again = client.get("/library")
    if [row["id"] for row in again.json()["workouts"]] != ids:
        raise AssertionError("the menu ids changed between loads")
    text = str(payload).lower()
    if "probability" in text or "readiness_score" in text:
        raise AssertionError("a score was added")
    easy = next(row for row in payload["workouts"] if row["id"] == "aer_10000_r0_x1")
    if "6.2 mi" not in easy["description"] or "10 km" in easy["description"]:
        raise AssertionError(easy["description"])
    if "explain(" in (ROOT / "api" / "screens.py").read_text(encoding="utf-8").split("def library_view")[1].split("\ndef ")[0]:
        raise AssertionError("library called explain")


def test_search_matches_the_shown_name_and_filters_stay_open(tmp_path: Path) -> None:
    client = _signed(tmp_path / "accounts.json")
    by_id = client.get("/library", params={"q": "rr_800"})
    if [row["id"] for row in by_id.json()["workouts"]] != ["rr_800_r0_x1"]:
        raise AssertionError(by_id.text)
    by_miles = client.get("/library", params={"q": "6.2 mi"})
    if "aer_10000_r0_x1" not in [row["id"] for row in by_miles.json()["workouts"]]:
        raise AssertionError(by_miles.text)
    by_km = client.get("/library", params={"q": "10 km"})
    if "aer_10000_r0_x1" not in [row["id"] for row in by_km.json()["workouts"]]:
        raise AssertionError("the stored name dropped out of search")
    empty = client.get("/library", params={"q": "no-such-workout"})
    if empty.json()["count"] != 0 or empty.json()["workouts"]:
        raise AssertionError(empty.text)
    if len(empty.json()["families"]) != 8:
        raise AssertionError("an empty search closed the family list")
    aerobic = client.get("/library", params={"family": "aerobic", "q": "12 km"})
    if [row["id"] for row in aerobic.json()["workouts"]] != ["aer_12000_r0_x1"]:
        raise AssertionError(aerobic.text)
    phase_8 = {row["id"] for row in client.get("/library", params={"phase": 8}).json()["workouts"]}
    if "rr_800_r0_x1" not in phase_8 or "aer_5000_r0_x1" not in phase_8:
        raise AssertionError("phase 8 dropped the race or the easy day")
    if "aer_12000_r0_x1" in phase_8 or "aer_8000_r0_x1" in phase_8:
        raise AssertionError("phase 8 kept a long run")
    if client.get("/library", params={"phase": 9}).json()["count"] != 0:
        raise AssertionError("a phase outside 1–8 matched a row")
    full = client.get("/library")
    if full.json()["count"] != len(list(MENU.glob("*.yml"))):
        raise AssertionError("clearing the filters did not restore the menu")


def test_kilometers_keep_the_menu_phrase_and_ids_follow_the_setting(tmp_path: Path) -> None:
    client = _signed(tmp_path / "accounts.json")
    me = client.get("/auth/me")
    if me.json()["prefs"].get("show_ids") is not False or me.json()["prefs"].get("compact") is not False:
        raise AssertionError(me.json()["prefs"])
    saved = client.patch("/settings", json={"pace_units": "km", "show_ids": True, "compact": True})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    prefs = saved.json()["prefs"]
    if prefs["units"] != "km" or prefs["show_ids"] is not True or prefs["compact"] is not True:
        raise AssertionError(prefs)
    easy = next(row for row in client.get("/library").json()["workouts"] if row["id"] == "aer_10000_r0_x1")
    if easy["description"] != "Easy 50–60 min, about 10 km":
        raise AssertionError(easy["description"])
    guest = _client(tmp_path / "accounts.json")
    if guest.get("/library").status_code != 401:
        raise AssertionError("a signed-out read opened the menu")


def test_a_failed_menu_is_the_exception_sentence(monkeypatch) -> None:
    def broken() -> list:
        raise ValueError("menu <broken>")

    monkeypatch.setattr("engines.prescribe.load_menu", broken)
    try:
        library_view("", "", None)
    except Exception as exc:
        if type(exc).__name__ != "ApiError" or str(exc) != "menu <broken>" or getattr(exc, "status", None) != 500:
            raise AssertionError(exc) from exc
    else:
        raise AssertionError("a failed menu looked like an empty list")
