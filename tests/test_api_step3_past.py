# test_api_step3_past.py — the past-seasons list, a stored open, and delete.

"""A past season can be deleted only after confirm. The current one cannot.

Opening a stored season reads it. It does not generate another. No network.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from engines.pace import FAMILY_FRACTION
from tests.test_api import INPUTS, PAST, _generate, _panel, _sign_up
from ui.accounts import create_account
from ui.cloud_store import MemoryDirectory
from ui.past_seasons import season_summary, summary_record
from ui.settings import local_today

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


def _signed(path: Path) -> TestClient:
    create_account(path, "ada@example.com", "correct-horse", "Ada")
    client = _client(path)
    signed = client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    return client


def _fractions() -> None:
    if FAMILY_FRACTION["aer"] != Decimal("1.55") or FAMILY_FRACTION["spd"] != Decimal("0.96"):
        raise AssertionError(FAMILY_FRACTION)


def test_the_list_keeps_the_current_season_beside_past_ones() -> None:
    directory = MemoryDirectory()
    client = _sign_up(directory)
    token = next(iter(directory.sessions))
    directory.save_timezone(token, "America/Los_Angeles")
    saved = client.patch("/settings", json={"date_format": "short"})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    _generate(client)
    older = {
        "current_time": "2:08.0",
        "start_date": "2019-03-02",
        "goal_time": "1:59.0",
        "goal_date": "2019-06-01",
    }
    _generate(client, PAST)
    _generate(client, older)
    listed = client.get("/seasons/past")
    if listed.status_code != 200:
        raise AssertionError(listed.text)
    body = listed.json()
    if body["today"] != local_today("America/Los_Angeles").isoformat():
        raise AssertionError(body["today"])
    starts = [row["inputs"]["start_date"] for row in body["seasons"]]
    if starts != ["2019-03-02", "2020-01-06"]:
        raise AssertionError(starts)
    if body["open"] != [] and body["open"][0]["inputs"]["goal_date"] != "2027-03-19":
        raise AssertionError(body["open"])
    if len(body["open"]) != 1:
        raise AssertionError(body["open"])
    user_id = directory.by_email["ada@example.com"]
    stored = next(item for item in directory.plans[user_id] if item.get("goal_date") == "2020-04-06")
    expected = _panel(("2:05.0", "2020-01-06", "1:55.0", "2020-04-06"), summary_record(stored), "short")
    if body["seasons"][1]["stats"] != expected:
        raise AssertionError((body["seasons"][1]["stats"], expected))
    labels = [stat["label"] for stat in body["seasons"][1]["stats"]]
    for missing in ("Event", "Notes", "Insights", "Adaptations", "Distance logged", "Last 800", "Best 800"):
        if missing in labels:
            raise AssertionError(labels)
    iso = client.patch("/settings", json={"date_format": "iso"})
    if iso.status_code != 200:
        raise AssertionError(iso.text)
    again = client.get("/seasons/past").json()["seasons"][1]["stats"]
    season = next(stat["value"] for stat in again if stat["label"] == "Season")
    if season != "2020-01-06 – 2020-04-06":
        raise AssertionError(season)
    _fractions()


def test_opening_a_stored_season_does_not_build_a_new_one() -> None:
    directory = MemoryDirectory()
    client = _sign_up(directory)
    _generate(client)
    _generate(client, PAST)
    user_id = directory.by_email["ada@example.com"]
    for row in directory.plans[user_id]:
        if row.get("goal_date") == "2020-04-06":
            row["marks"] = {"3": "on_track"}
    before = len(directory.plans[user_id])
    opened = client.get("/plan", params=PAST)
    if opened.status_code != 200:
        raise AssertionError(opened.text)
    body = opened.json()
    if body["inputs"] != PAST or body["marks"].get("3") != "on_track":
        raise AssertionError(body["inputs"])
    if not body["sessions"] or body["pace_status"] != "No runs yet":
        raise AssertionError("the stored plan did not open")
    if len(directory.plans[user_id]) != before:
        raise AssertionError("opening built another season")
    current = client.get("/seasons/current")
    if current.status_code != 200 or current.json()["inputs"]["goal_date"] != "2027-03-19":
        raise AssertionError(current.text)
    foreign = client.get("/plan", params={**PAST, "goal_time": "1:50.0"})
    if foreign.status_code != 200 or foreign.json()["inputs"]["goal_date"] != "2027-03-19":
        raise AssertionError(foreign.text)
    if len(client.get("/seasons/past").json()["seasons"]) != 1:
        raise AssertionError("a foreign link stored a season")
    _fractions()


def test_a_season_ending_today_cannot_be_deleted(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("ui.settings.datetime", _FrozenClock)
    client = _signed(tmp_path / "accounts.json")
    client.patch("/settings", json={"timezone": "America/Los_Angeles"})
    today = "2026-11-10"
    yesterday = "2026-11-09"
    ending = {
        "current_time": "2:04.0",
        "start_date": "2026-08-02",
        "goal_time": "1:56.0",
        "goal_date": today,
    }
    ended = {
        "current_time": "2:06.0",
        "start_date": "2026-06-01",
        "goal_time": "1:57.0",
        "goal_date": yesterday,
    }
    _generate(client, ending)
    _generate(client, ended)
    listed = client.get("/seasons/past")
    if listed.status_code != 200:
        raise AssertionError(listed.text)
    body = listed.json()
    if body["today"] != today:
        raise AssertionError(body["today"])
    if [row["inputs"]["goal_date"] for row in body["open"]] != [today]:
        raise AssertionError(body["open"])
    if [row["inputs"]["goal_date"] for row in body["seasons"]] != [yesterday]:
        raise AssertionError(body["seasons"])
    refused = client.request("DELETE", "/seasons/past", json={**ending, "confirm": True})
    if refused.status_code != 409 or refused.json()["detail"] != "The current season can't be deleted.":
        raise AssertionError(refused.text)
    if client.get("/seasons/current").json()["inputs"]["goal_date"] != today:
        raise AssertionError("the season that ends today was removed")
    _fractions()


def test_delete_still_needs_confirm_and_leaves_the_other_season() -> None:
    directory = MemoryDirectory()
    client = _sign_up(directory)
    _generate(client)
    older = {
        "current_time": "2:08.0",
        "start_date": "2019-03-02",
        "goal_time": "1:59.0",
        "goal_date": "2019-06-01",
    }
    _generate(client, older)
    _generate(client, PAST)
    bare = client.request("DELETE", "/seasons/past", json=PAST)
    if bare.status_code != 400:
        raise AssertionError(bare.text)
    missing = client.request(
        "DELETE",
        "/seasons/past",
        json={
            "current_time": "2:01.0",
            "start_date": "2018-01-01",
            "goal_time": "1:50.0",
            "goal_date": "2018-04-01",
            "confirm": True,
        },
    )
    if missing.status_code != 404:
        raise AssertionError(missing.text)
    if len(client.get("/seasons/past").json()["seasons"]) != 2:
        raise AssertionError("an unconfirmed delete removed a season")
    deleted = client.request("DELETE", "/seasons/past", json={**PAST, "confirm": True})
    if deleted.status_code != 200 or deleted.json()["deleted"] is not True:
        raise AssertionError(deleted.text)
    if deleted.json()["stats"][0]["label"] != "Season":
        raise AssertionError(deleted.json()["stats"])
    left = client.get("/seasons/past").json()
    if [row["inputs"]["goal_date"] for row in left["seasons"]] != ["2019-06-01"]:
        raise AssertionError(left["seasons"])
    if left["open"][0]["inputs"]["goal_date"] != "2027-03-19":
        raise AssertionError(left["open"])
    facts = season_summary(("2:05.0", "2020-01-06", "1:55.0", "2020-04-06"), None)
    if ("Workouts logged", "0") in facts:
        raise AssertionError(facts)
    _fractions()


def test_an_unreadable_account_uses_the_page_sentence(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    client = _signed(path)
    path.write_text("{", encoding="utf-8")
    listed = client.get("/seasons/past")
    if listed.status_code != 401 or listed.json()["detail"] != "Accounts could not be read.":
        raise AssertionError(listed.text)
    _fractions()
