# test_heart_targets.py — zone targets for easy, tempo, and threshold days.

"""Short reps stay on pace. A heart-rate day shows a range, not one pace.
No network.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from engines.heart_rate import zones_for
from engines.heart_targets import (
    CREATING_NOTE,
    EFFORT_NOTE,
    heart_overlay,
    qualifying_for_zone,
    training_logs,
    zone_for_template,
)
from engines.pace import PaceLog, workout_times
from ui.accounts import create_account

ORIGIN = "http://localhost:3000"


def _profile() -> dict:
    body = zones_for(60, 180)
    body["no_monitor"] = False
    return body


def _times(template: str, easy: str | None = "7:25") -> dict | None:
    return workout_times(
        template,
        current_mark="2:05.0",
        goal_mark="1:55.0",
        start=date(2026, 4, 1),
        goal_date=date(2026, 7, 1),
        on=date(2026, 4, 8),
        easy_pace=easy,
        easy_unit="mi",
    )


def test_easy_tempo_and_threshold_take_zones_and_fast_work_does_not() -> None:
    if zone_for_template("aer_8000_r0_x1") != 2:
        raise AssertionError("easy and long runs are zone 2")
    if zone_for_template("ap_1000_r120_x4") != 3:
        raise AssertionError("aerobic power is the tempo day")
    if zone_for_template("thr_1600_r90_x3") != 4:
        raise AssertionError("threshold is zone 4")
    for template in ("spd_200_r180_x6", "rr_800_r0_x1", "se_400_r90_x6", "an_500_r150_x4", "mv_80_r180_x6"):
        if zone_for_template(template) is not None:
            raise AssertionError(template)
    if qualifying_for_zone(2) != 0:
        raise AssertionError("pace learning has not started")


def test_a_heart_day_shows_a_pace_range_and_the_zone() -> None:
    profile = _profile()
    easy = heart_overlay("aer_10000_r0_x1", _times("aer_10000_r0_x1"), profile, "mi")
    if easy is None:
        raise AssertionError("easy run")
    if easy["zone"] != 2 or easy["low_bpm"] != 132 or easy["high_bpm"] != 144:
        raise AssertionError(easy)
    if easy["line"] != "Zone 2 · Easy / long · 132–144 bpm":
        raise AssertionError(easy["line"])
    if "\u2013" not in easy["pace_line"] or easy["pace_line"].count(":") < 2:
        raise AssertionError(easy["pace_line"])
    if easy["pace_low"] == easy["pace_high"]:
        raise AssertionError("a single pace")
    if easy["pace_note"] != CREATING_NOTE or easy["estimate"] != "creating":
        raise AssertionError(easy)
    if easy["effort"] != EFFORT_NOTE or "not medical advice" not in easy["safety"]:
        raise AssertionError(easy)
    # 7:25 widened by 20 seconds is 7:05–7:45.
    if easy["pace_line"] != "7:05\u20137:45 per mile":
        raise AssertionError(easy["pace_line"])
    tempo = heart_overlay("ap_800_r90_x5", _times("ap_800_r90_x5"), profile, "mi")
    threshold = heart_overlay("thr_2000_r90_x3", _times("thr_2000_r90_x3"), profile, "mi")
    if tempo is None or tempo["zone"] != 3 or tempo["pace_low"] == tempo["pace_high"]:
        raise AssertionError(tempo)
    if threshold is None or threshold["zone"] != 4:
        raise AssertionError(threshold)
    speed = heart_overlay("spd_200_r180_x6", _times("spd_200_r180_x6"), profile, "mi")
    race = heart_overlay("rr_800_r0_x1", _times("rr_800_r0_x1"), profile, "mi")
    if speed is not None or race is not None:
        raise AssertionError("fast work stays on pace")
    skipped = dict(profile)
    skipped["no_monitor"] = True
    if heart_overlay("aer_8000_r0_x1", _times("aer_8000_r0_x1"), skipped, "mi") is not None:
        raise AssertionError("no monitor keeps the old pace")
    kept = training_logs(
        [PaceLog(date(2026, 4, 2), 2400.0, "aer_8000_r0_x1"), PaceLog(date(2026, 4, 3), 48.0, "spd_200_r180_x6")],
        profile,
    )
    if len(kept) != 1 or kept[0].template_id != "spd_200_r180_x6":
        raise AssertionError(kept)


def test_home_uses_the_zone_after_heart_rate_is_saved_and_pace_when_it_is_not(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    create_account(path, "ada@example.com", "correct-horse", "Ada")
    app = create_app(directory=None, accounts=path, frontend_origin=ORIGIN, load_env=False)
    client = TestClient(app, base_url="https://testserver")
    signed = client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    pace = client.patch("/settings", json={"easy_pace": "7:25", "easy_pace_unit": "mi"})
    if pace.status_code != 200:
        raise AssertionError(pace.text)
    start = date.today() - timedelta(days=2)
    goal = start + timedelta(days=140)
    made = client.post(
        "/seasons",
        json={
            "current_time": "2:05.0",
            "start_date": start.isoformat(),
            "goal_time": "1:55.0",
            "goal_date": goal.isoformat(),
        },
    )
    if made.status_code != 200:
        raise AssertionError(made.text)
    before = client.get("/home")
    if before.status_code != 200:
        raise AssertionError(before.text)
    plain = _lines(before.json())
    if not any(line.startswith("Run at ") for line in plain):
        raise AssertionError(plain)
    if any(line.startswith("Zone ") for line in plain):
        raise AssertionError(plain)
    saved = client.put("/heart-rate", json={"resting_hr": 60, "max_hr": 180})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    after = client.get("/home")
    zoned = _lines(after.json())
    if not any("Zone 2" in line and "132\u2013144 bpm" in line for line in zoned):
        raise AssertionError(zoned)
    notes = _notes(after.json())
    if CREATING_NOTE not in notes or "7:05\u20137:45 per mile" not in notes:
        raise AssertionError(notes)
    if any(line.startswith("Run at 7:25") for line in zoned):
        raise AssertionError(zoned)
    off = client.put("/heart-rate", json={"no_monitor": True})
    if off.status_code != 200:
        raise AssertionError(off.text)
    restored = _lines(client.get("/home").json())
    if not any(line.startswith("Run at ") for line in restored):
        raise AssertionError(restored)
    if any(line.startswith("Zone ") for line in restored):
        raise AssertionError(restored)


def _lines(body: dict) -> list[str]:
    season = body.get("season") if isinstance(body.get("season"), dict) else {}
    found = []
    for key in ("next",):
        row = season.get(key)
        if isinstance(row, dict):
            _collect(row, found)
    for row in season.get("upcoming") or []:
        if isinstance(row, dict):
            _collect(row, found)
    for row in season.get("next_days") or []:
        if isinstance(row, dict):
            _collect(row, found)
    return found


def _collect(row: dict, found: list[str]) -> None:
    prescription = row.get("prescription")
    if isinstance(prescription, dict) and isinstance(prescription.get("line"), str):
        found.append(prescription["line"])


def _notes(body: dict) -> str:
    season = body.get("season") if isinstance(body.get("season"), dict) else {}
    chunks = []
    for key in ("next",):
        row = season.get(key)
        if isinstance(row, dict):
            chunks.append(str(row.get("prescription")))
    for row in list(season.get("upcoming") or []) + list(season.get("next_days") or []):
        if isinstance(row, dict):
            chunks.append(str(row.get("prescription")))
    return "\n".join(chunks)
