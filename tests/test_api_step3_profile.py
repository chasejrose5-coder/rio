# test_api_step3_profile.py — Profile reads the season and can save a goal and an easy pace.

"""The goal override does not rebuild the season. Easy pace does not either.

Quality fractions stay. A blank Start value is an em dash. No network.
No production Supabase. The model is not called.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from api.screens import profile_view
from engines.pace import FAMILY_FRACTION
from ui.accounts import create_account

INPUTS = {
    "current_time": "2:02.9",
    "start_date": "2026-04-19",
    "goal_time": "1:55.0",
    "goal_date": "2027-03-19",
}


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


def _ids(plan: dict) -> list[str]:
    return [str(row.get("template_id") or "") for row in plan.get("sessions") or []]


def _pace_lines(node: object) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        facts = node.get("facts")
        if isinstance(facts, dict) and isinstance(facts.get("pace"), str):
            found.append(facts["pace"])
        prescription = node.get("prescription")
        if isinstance(prescription, dict) and isinstance(prescription.get("line"), str):
            found.append(prescription["line"])
        for value in node.values():
            found.extend(_pace_lines(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_pace_lines(item))
    return found


def test_profile_without_a_season_has_no_start_fields(tmp_path: Path) -> None:
    client = _signed(tmp_path / "accounts.json")
    body = client.get("/profile")
    if body.status_code != 200:
        raise AssertionError(body.text)
    payload = body.json()
    if payload["ready"] is not False or payload["fields"] != []:
        raise AssertionError(payload)
    if payload["goal_time"] or payload["goal_override"] is not None:
        raise AssertionError(payload)
    missing = client.put("/profile/goal", json={"goal_time": "1:54.0"})
    if missing.status_code != 404 or missing.json()["detail"] != "No current season.":
        raise AssertionError(missing.text)
    if _client(tmp_path / "accounts.json").get("/profile").status_code != 401:
        raise AssertionError("profile did not require a cookie")


def test_a_blank_start_value_is_an_em_dash() -> None:
    class Season:
        inputs = ("", "2026-04-19", "1:55.0", "  ")
        digest = "untouched"

    body = profile_view(
        Season(),
        {"prefs": {"date_format": "iso"}, "easy_pace": "", "easy_pace_unit": "mi", "easy_pace_phrase": ""},
        None,
    )
    shown = {row["label"]: row["value"] for row in body["fields"]}
    if shown["Current 800 time"] != "—" or shown["Goal date"] != "—":
        raise AssertionError(shown)
    if shown["Start date"] != "2026-04-19" or shown["Goal 800m time"] != "1:55.0":
        raise AssertionError(shown)
    if "probability" in str(body) or "readiness" in str(body):
        raise AssertionError("a score was added")


def test_saving_a_goal_does_not_rebuild_and_a_bad_time_is_refused(tmp_path: Path) -> None:
    client = _signed(tmp_path / "accounts.json")
    generated = client.post("/seasons", json=INPUTS)
    if generated.status_code != 200:
        raise AssertionError(generated.text)
    digest = generated.json()["digest"]
    ids = _ids(generated.json()["plan"])
    opened = client.get("/profile")
    if opened.status_code != 200 or opened.json()["shown_goal"] != "1:55.0":
        raise AssertionError(opened.text)
    fields = {row["label"]: row["value"] for row in opened.json()["fields"]}
    if fields != {
        "Current 800 time": "2:02.9",
        "Start date": "2026-04-19",
        "Goal 800m time": "1:55.0",
        "Goal date": "2027-03-19",
    }:
        raise AssertionError(fields)
    for sample in ("nope", "0:00", "0:00.0", ""):
        refused = client.put("/profile/goal", json={"goal_time": sample})
        if refused.status_code != 400 or refused.json()["detail"] != "goal_time is not an 800 time":
            raise AssertionError(refused.text)
    saved = client.put("/profile/goal", json={"goal_time": "1:54.0"})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    body = saved.json()
    if body["goal_override"] != "1:54.0" or body["shown_goal"] != "1:54.0" or body["goal_time"] != "1:55.0":
        raise AssertionError(body)
    again = client.get("/profile")
    if again.json()["goal_override"] != "1:54.0":
        raise AssertionError("the override did not stay")
    current = client.get("/seasons/current")
    if current.json()["digest"] != digest or current.json()["inputs"]["goal_time"] != "1:55.0":
        raise AssertionError("the season goal moved")
    if _ids(current.json()["plan"]) != ids:
        raise AssertionError("saving a goal rebuilt the workouts")
    home = client.get("/home")
    if home.json()["season"]["inputs"]["goal_time"] != "1:55.0":
        raise AssertionError(home.json()["season"]["inputs"])
    if _client(tmp_path / "accounts.json").put("/profile/goal", json={"goal_time": "1:54.0"}).status_code != 401:
        raise AssertionError("the override did not require a cookie")


def test_changing_easy_pace_updates_the_phrase_and_leaves_the_plan(tmp_path: Path) -> None:
    if FAMILY_FRACTION["aer"] != Decimal("1.55"):
        raise AssertionError("the aerobic fraction was changed")
    if FAMILY_FRACTION["spd"] != Decimal("0.96"):
        raise AssertionError("a quality fraction was changed")
    client = _signed(tmp_path / "accounts.json")
    first = client.patch("/settings", json={"easy_pace": "7:25", "easy_pace_unit": "mi"})
    if first.status_code != 200 or first.json()["prefs"]["easy_pace_phrase"] != "7:25 per mile":
        raise AssertionError(first.text)
    generated = client.post("/seasons", json=INPUTS)
    if generated.status_code != 200:
        raise AssertionError(generated.text)
    digest = generated.json()["digest"]
    ids = _ids(generated.json()["plan"])
    sessions = generated.json()["plan"]["sessions"]
    changed = client.patch("/settings", json={"easy_pace": "5:00", "easy_pace_unit": "km"})
    if changed.status_code != 200 or changed.json()["prefs"]["easy_pace_phrase"] != "5:00 per kilometer":
        raise AssertionError(changed.text)
    profile = client.get("/profile")
    if profile.json()["easy_pace_phrase"] != "5:00 per kilometer" or profile.json()["easy_pace_unit"] != "km":
        raise AssertionError(profile.text)
    current = client.get("/seasons/current")
    if current.json()["digest"] != digest or _ids(current.json()["plan"]) != ids:
        raise AssertionError("easy pace rebuilt the season")
    easy = next(row for row in sessions if str(row["template_id"]).startswith("aer_"))
    shown = client.get(f"/sessions/{easy['date']}")
    line = (shown.json().get("prescription") or {}).get("line") or ""
    if not line.startswith("Run at 5:00 per kilometer"):
        raise AssertionError(line)
    if "1.55" in line:
        raise AssertionError(line)
    home = client.get("/home")
    lines = _pace_lines(home.json().get("season"))
    if not any(line.startswith("5:00 per kilometer") or line.startswith("Run at 5:00 per kilometer") for line in lines):
        raise AssertionError(lines)
    quality = next(
        row
        for row in sessions
        if row["day_of_week"] in ("Tuesday", "Thursday") and not str(row["template_id"]).startswith("aer_")
    )
    hard = client.get(f"/sessions/{quality['date']}")
    hard_line = (hard.json().get("prescription") or {}).get("line") or ""
    if " m @" not in hard_line or "per kilometer" in hard_line or "1.55" in hard_line:
        raise AssertionError(hard_line)
    refused = client.patch("/settings", json={"easy_pace": "fast", "easy_pace_unit": "km"})
    if refused.status_code != 400 or refused.json()["detail"] != "Enter a pace like 7:25.":
        raise AssertionError(refused.text)
    if client.get("/profile").json()["easy_pace_phrase"] != "5:00 per kilometer":
        raise AssertionError("a bad pace replaced the saved one")
