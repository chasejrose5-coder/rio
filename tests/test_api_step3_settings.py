# test_api_step3_settings.py — Settings writes, today, and the danger zone.

"""Name, nickname, and the time zone save without rebuilding the season.

A bad value is refused before the stored name changes. Clearing marks keeps
notes. Reset keeps the account. Quality fractions stay. No network.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from engines.pace import FAMILY_FRACTION
from tests.test_api import INPUTS, NOTE, _generate
from ui.accounts import create_account, write_local
from ui.settings import TIME_ZONES, chosen_timezone, local_today

_FROZEN = datetime(2026, 11, 10, 18, 0, tzinfo=timezone.utc)


class _FrozenClock(datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is not None:
            return _FROZEN.astimezone(tz)
        return _FROZEN


def _client(path: Path) -> TestClient:
    app = create_app(directory=None, accounts=path, frontend_origin="http://localhost:3000", load_env=False)
    return TestClient(app, base_url="https://testserver")


def _signed(path: Path, name: str = "Ada") -> TestClient:
    create_account(path, "ada@example.com", "correct-horse", name)
    client = _client(path)
    signed = client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    return client


def _ids(plan: dict) -> list[str]:
    return [str(row.get("template_id") or "") for row in plan.get("sessions") or []]


def _today_cell(calendar: list) -> str:
    for week in calendar:
        if not isinstance(week, list):
            continue
        for cell in week:
            if isinstance(cell, dict) and cell.get("today") is True:
                return str(cell.get("date") or "")
    return ""


def test_a_bad_value_does_not_wipe_the_name(tmp_path: Path) -> None:
    client = _signed(tmp_path / "accounts.json")
    saved = client.patch("/settings", json={"display_name": "Ada Lovelace", "preferred": "Addy"})
    if saved.status_code != 200 or saved.json()["display_name"] != "Ada Lovelace":
        raise AssertionError(saved.text)
    if saved.json()["prefs"]["preferred"] != "Addy":
        raise AssertionError(saved.json())
    empty = client.patch("/settings", json={})
    if empty.status_code != 400 or empty.json()["detail"] != "Nothing to save.":
        raise AssertionError(empty.text)
    bad_name = client.patch("/settings", json={"display_name": "!!!"})
    if bad_name.status_code != 400 or bad_name.json()["detail"] != "Enter a name.":
        raise AssertionError(bad_name.text)
    bad_zone = client.patch("/settings", json={"timezone": "America/Detroit", "display_name": "Gone"})
    if bad_zone.status_code != 400 or bad_zone.json()["detail"] != "Choose a time zone from the list.":
        raise AssertionError(bad_zone.text)
    me = client.get("/auth/me").json()
    if me["display_name"] != "Ada Lovelace" or me["prefs"]["preferred"] != "Addy":
        raise AssertionError(me)
    if me["prefs"]["timezone"] not in TIME_ZONES:
        raise AssertionError(me["prefs"])
    nick = client.patch("/settings", json={"preferred": ""})
    if nick.status_code != 200 or nick.json()["prefs"]["preferred"] != "":
        raise AssertionError(nick.text)
    if client.get("/auth/me").json()["display_name"] != "Ada Lovelace":
        raise AssertionError("clearing the nickname wiped the name")


def test_the_greeting_uses_the_nickname_then_the_name(tmp_path: Path) -> None:
    client = _signed(tmp_path / "accounts.json", "Chase")
    named = client.patch("/settings", json={"display_name": "Chase", "preferred": "CJ"})
    if named.status_code != 200:
        raise AssertionError(named.text)
    hello = client.get("/home").json()["hello"]
    if hello != "Hey, CJ":
        raise AssertionError(hello)
    cleared = client.patch("/settings", json={"preferred": ""})
    if cleared.status_code != 200:
        raise AssertionError(cleared.text)
    again = client.get("/home").json()["hello"]
    if again != "Hey, Chase":
        raise AssertionError(again)


def test_the_saved_zone_decides_today_on_home_and_plan(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("ui.settings.datetime", _FrozenClock)
    client = _signed(tmp_path / "accounts.json")
    generated = _generate(client)
    before = _ids(generated["plan"])
    auckland = client.patch("/settings", json={"timezone": "Pacific/Auckland", "pace_units": "km"})
    if auckland.status_code != 200:
        raise AssertionError(auckland.text)
    if auckland.json()["prefs"]["timezone"] != "Pacific/Auckland":
        raise AssertionError(auckland.json())
    if auckland.json()["today"] != "2026-11-11":
        raise AssertionError(auckland.json()["today"])
    home = client.get("/home").json()
    plan = client.get("/plan").json()
    if home["today"] != "2026-11-11" or plan["prefs"]["today"] != "2026-11-11":
        raise AssertionError((home["today"], plan["prefs"].get("today")))
    if _today_cell(plan["calendar"]) != "2026-11-11":
        raise AssertionError(plan["calendar"])
    islands = client.patch("/settings", json={"timezone": "Pacific/Honolulu"})
    if islands.status_code != 200 or islands.json()["today"] != "2026-11-10":
        raise AssertionError(islands.text)
    if client.get("/home").json()["today"] != "2026-11-10":
        raise AssertionError(client.get("/home").text)
    if client.get("/auth/me").json()["today"] != "2026-11-10":
        raise AssertionError("auth today ignored the zone")
    current = client.get("/seasons/current").json()
    if _ids(current["plan"]) != before:
        raise AssertionError("the time zone rewrote the season")
    if current["inputs"] != {
        "current_time": INPUTS["current_time"],
        "start_date": INPUTS["start_date"],
        "goal_time": INPUTS["goal_time"],
        "goal_date": INPUTS["goal_date"],
    }:
        raise AssertionError(current["inputs"])
    if FAMILY_FRACTION["aer"] != __import__("decimal").Decimal("1.55"):
        raise AssertionError(FAMILY_FRACTION["aer"])
    if FAMILY_FRACTION["spd"] != __import__("decimal").Decimal("0.96"):
        raise AssertionError(FAMILY_FRACTION["spd"])
    text = client.get("/seasons/current").text
    if "correct-horse" in text or "seal" in text:
        raise AssertionError("the season read included a secret")


def test_an_unlisted_saved_zone_still_appears(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    email, seal = create_account(path, "ada@example.com", "correct-horse", "Ada")
    write_local(path, email, seal, "Ada", "", "America/Detroit", {"pace_units": "mi"})
    client = _client(path)
    signed = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    me = client.get("/auth/me").json()
    if me["prefs"]["timezone"] != "America/Detroit":
        raise AssertionError(me["prefs"])
    if me["today"] != local_today(chosen_timezone(None)).isoformat():
        raise AssertionError(me["today"])


def test_clear_keeps_notes_and_reset_keeps_the_account(tmp_path: Path) -> None:
    client = _signed(tmp_path / "accounts.json")
    client.patch("/settings", json={"easy_pace": "7:45", "easy_pace_unit": "mi", "compact": True, "show_ids": True})
    generated = _generate(client)
    day = generated["plan"]["sessions"][0]["date"]
    noted = client.post("/seasons/current/notes", json={"date": day, "note": NOTE, "viewed": True})
    if noted.status_code != 200:
        raise AssertionError(noted.text)
    marked = client.post("/seasons/current/marks", json={"week": 1, "choice": "on_track"})
    if marked.status_code != 200 or not marked.json()["marks"]:
        raise AssertionError(marked.text)
    refused = client.post("/seasons/current/clear", json={"confirm": False})
    if refused.status_code != 400:
        raise AssertionError(refused.text)
    cleared = client.post("/seasons/current/clear", json={"confirm": True})
    if cleared.status_code != 200:
        raise AssertionError(cleared.text)
    body = cleared.json()
    if body["marks"] or body["actuals"] or body["quality_base_weeks"]:
        raise AssertionError(body)
    if body["notes"][day]["note"] != NOTE:
        raise AssertionError(body["notes"])
    if body["inputs"]["current_time"] != INPUTS["current_time"]:
        raise AssertionError(body["inputs"])
    blocked = client.post("/seasons/reset", json={"confirm": False})
    if blocked.status_code != 400 or blocked.json()["detail"] != "Confirm to reset the plan.":
        raise AssertionError(blocked.text)
    if client.get("/seasons/current").status_code != 200:
        raise AssertionError("a refused reset deleted the season")
    reset = client.post("/seasons/reset", json={"confirm": True})
    if reset.status_code != 200 or reset.json()["reset"] is not True:
        raise AssertionError(reset.text)
    if client.get("/seasons/current").status_code != 404:
        raise AssertionError("the season stayed")
    me = client.get("/auth/me").json()
    if me["display_name"] != "Ada" or me["prefs"]["easy_pace"] != "7:45":
        raise AssertionError(me)
    if me["prefs"]["compact"] is not True or me["prefs"]["show_ids"] is not True:
        raise AssertionError(me["prefs"])
    home = client.get("/home").json()
    if home["season"] is not None or "Generate a season on Start." not in (home.get("copy") or ""):
        raise AssertionError(home)
    if client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"}).status_code != 200:
        raise AssertionError("reset broke sign-in")
