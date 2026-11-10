# test_api_step3_session.py — the session page's read, and the day Start session opens.

"""Easy pace is the athlete's pace. Quality fractions stay as they are.

No network. No production Supabase client. The model is not called.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from api.screens import next_session_day
from engines.pace import FAMILY_FRACTION
from ui.accounts import create_account
from ui.settings import local_today

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


def test_next_session_day_is_today_or_the_last_day() -> None:
    plan = {"sessions": [{"date": "2026-01-01"}, {"date": "2026-01-08"}]}
    if next_session_day(plan, date(2026, 1, 3)) != "2026-01-08":
        raise AssertionError("a mid-season day did not open the next session")
    if next_session_day(plan, date(2026, 2, 1)) != "2026-01-08":
        raise AssertionError("a finished season did not open the last day")
    if next_session_day(plan, date(2025, 12, 1)) != "2026-01-01":
        raise AssertionError(next_session_day(plan, date(2025, 12, 1)))


def test_session_uses_easy_pace_and_states_the_rep_and_the_average(tmp_path: Path) -> None:
    if FAMILY_FRACTION["aer"] != __import__("decimal").Decimal("1.55"):
        raise AssertionError("the aerobic fraction was changed")
    if FAMILY_FRACTION["spd"] != __import__("decimal").Decimal("0.96"):
        raise AssertionError("a quality fraction was changed")
    client = _signed(tmp_path / "accounts.json")
    saved = client.patch("/settings", json={"easy_pace": "7:45", "easy_pace_unit": "mi", "timezone": "America/Los_Angeles"})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    generated = client.post("/seasons", json=INPUTS)
    if generated.status_code != 200:
        raise AssertionError(generated.text)
    me = client.get("/auth/me")
    if me.status_code != 200:
        raise AssertionError(me.text)
    zone_today = local_today("America/Los_Angeles").isoformat()
    if me.json()["today"] != zone_today:
        raise AssertionError(me.json()["today"])
    if me.json()["today"] == date.today().isoformat() and zone_today != date.today().isoformat():
        raise AssertionError("today followed the server clock")
    sessions = generated.json()["plan"]["sessions"]
    nxt = me.json()["next_session"]
    expected = next_session_day({"sessions": sessions}, date.fromisoformat(zone_today))
    if nxt != expected:
        raise AssertionError((nxt, expected, zone_today))
    easy = next(row for row in sessions if str(row["template_id"]).startswith("aer_"))
    body = client.get(f"/sessions/{easy['date']}")
    if body.status_code != 200:
        raise AssertionError(body.text)
    shown = body.json()
    line = (shown.get("prescription") or {}).get("line") or ""
    if not line.startswith("Run at 7:45 per mile"):
        raise AssertionError(line)
    if "1.55" in line or " m @" in line:
        raise AssertionError(line)
    if shown["quality"] is not False or shown["boxes"] != 0:
        raise AssertionError(shown)
    if not shown["structure"] or shown["structure"] == "—":
        raise AssertionError(shown["structure"])
    rep = next(row for row in sessions if str(row["template_id"]).startswith("se_"))
    quality = client.get(f"/sessions/{rep['date']}")
    if quality.status_code != 200:
        raise AssertionError(quality.text)
    card = quality.json()
    rep_line = (card.get("prescription") or {}).get("line") or ""
    average = (card.get("prescription") or {}).get("average") or ""
    if " m @" not in rep_line or not average:
        raise AssertionError((rep_line, average))
    if "1.55" in rep_line:
        raise AssertionError(rep_line)
    if card["quality"] is not True or card["boxes"] < 2:
        raise AssertionError(card)
    if any(code.startswith("phase_") for code in card["reasons"]):
        raise AssertionError(card["reasons"])
    if "files" in card:
        raise AssertionError("a session offered the admin file list")
    missing = client.get("/sessions/1999-01-01")
    if missing.status_code != 404 or missing.json()["detail"] != "That day is not in this season.":
        raise AssertionError(missing.text)


def test_a_quality_result_adapts_and_an_easy_done_does_not(tmp_path: Path) -> None:
    client = _signed(tmp_path / "accounts.json", "bea@example.com")
    client.patch("/settings", json={"easy_pace": "7:25", "easy_pace_unit": "mi", "confirm_adapt": True})
    generated = client.post("/seasons", json=INPUTS)
    if generated.status_code != 200:
        raise AssertionError(generated.text)
    sessions = generated.json()["plan"]["sessions"]
    easy = next(row for row in sessions if str(row["template_id"]).startswith("aer_") and row["day_of_week"] in ("Tuesday", "Thursday", "Sunday", "Monday", "Wednesday", "Friday", "Saturday"))
    before = [row["template_id"] for row in sessions]
    done = client.post("/seasons/current/watchless", json={"date": easy["date"], "outcome": "", "time": ""})
    if done.status_code != 200 or done.json().get("quality_base_weeks"):
        raise AssertionError(done.text)
    if [row["template_id"] for row in done.json()["plan"]["sessions"]] != before:
        raise AssertionError("an easy done changed later weeks")
    hard = next(row for row in sessions if row["day_of_week"] in ("Tuesday", "Thursday") and not str(row["template_id"]).startswith("aer_"))
    quiet = client.post("/seasons/current/watchless", json={"date": hard["date"], "outcome": "On target", "time": ""})
    if quiet.status_code != 200 or quiet.json().get("quality_base_weeks"):
        raise AssertionError(quiet.text)
    refused = client.post("/seasons/current/watchless", json={"date": hard["date"], "outcome": "", "time": "1:12.4"})
    if refused.status_code != 400 or "Choose behind, on target, or ahead." not in refused.json()["detail"]:
        raise AssertionError(refused.text)
    bad = client.post("/seasons/current/watchless", json={"date": hard["date"], "outcome": "On target", "time": "abc"})
    if bad.status_code != 400 or "Enter one time, like 1:12.4, or leave it blank." not in bad.json()["detail"]:
        raise AssertionError(bad.text)
    marked = client.post("/seasons/current/results", json={"date": hard["date"], "text": "90, 91, 92, 93, 94, 95"})
    if marked.status_code != 200:
        # A workout with a different rep count still stores when the text can be judged.
        marked = client.post("/seasons/current/results", json={"date": hard["date"], "text": "90"})
    if marked.status_code != 200 or not marked.json().get("quality_base_weeks"):
        raise AssertionError(marked.text)
    if marked.json()["insight"]["status"] not in ("pending", "ready", "skipped"):
        raise AssertionError(marked.json()["insight"])
    saved = marked.json()["actuals"][hard["date"]]
    if saved.get("mark") not in ("on_track", "not_hitting", "smashing"):
        raise AssertionError(saved)


def test_admin_intervals_fill_stays_off_a_normal_account(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RIO_ADMIN_EMAIL", "admin@example.com")
    os.environ["RIO_ADMIN_EMAIL"] = "admin@example.com"
    athlete = _signed(tmp_path / "accounts.json", "ada@example.com")
    hidden = athlete.get("/fixtures/intervals")
    if hidden.status_code != 403:
        raise AssertionError(hidden.text)
    admin_path = tmp_path / "admin.json"
    admin = _signed(admin_path, "admin@example.com")
    listed = admin.get("/fixtures/intervals")
    if listed.status_code != 200 or "synthetic_se_400_with_recovery.json" not in listed.json()["files"]:
        raise AssertionError(listed.text)
    filled = admin.get("/fixtures/intervals/synthetic_se_400_with_recovery.json")
    if filled.status_code != 200 or not filled.json()["times"]:
        raise AssertionError(filled.text)
    if any(item is not None and not isinstance(item, (int, float)) for item in filled.json()["times"]):
        raise AssertionError(filled.json())
    missing = admin.get("/fixtures/intervals/not-a-file.json")
    if missing.status_code != 404:
        raise AssertionError(missing.text)
    monkeypatch.setattr(
        "ui.last_session.intervals_json_paths",
        lambda directory=None: [tmp_path / "bad.json"],
    )
    (tmp_path / "bad.json").write_text("nope", encoding="utf-8")
    broken = admin.get("/fixtures/intervals/bad.json")
    if broken.status_code != 400 or broken.json()["detail"] != "bad.json is not JSON.":
        raise AssertionError(broken.text)
