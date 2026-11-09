# test_api.py — FastAPI routes against the in-memory directory and a local account file.

"""The engine contract fixture is the season the API must return.

No network. No production Supabase client. The model is not called.
"""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import load_settings
from engines.pace import easy_pace_phrase
from engines.season import adapt
from services.season_commit import adapt_from_result
from ui.accounts import create_account, last_key, read_record, write_easy_pace, write_local
from ui.cloud_store import MemoryDirectory
from ui.past_seasons import inputs_from_key, season_summary, summary_record
from ui.plan_store import storage_key
from ui.settings import format_date, local_today

FIXTURE = ROOT / "tests" / "fixtures" / "contracts" / "engines.json"
INPUTS = {
    "current_time": "2:02.9",
    "start_date": "2026-04-19",
    "goal_time": "1:55.0",
    "goal_date": "2027-03-19",
}
ORIGIN = "http://localhost:3000"
NOTE = {
    "headline": "On track today",
    "body": "That was on track. Leave the next week as written.",
    "carry_forward": "Same effort next time.",
    "used_result_band": "on_track",
}
PAST = {
    "current_time": "2:05.0",
    "start_date": "2020-01-06",
    "goal_time": "1:55.0",
    "goal_date": "2020-04-06",
}


def _client(directory=None, accounts: Path | None = None, origin: str = ORIGIN) -> TestClient:
    app = create_app(
        directory=directory,
        accounts=accounts,
        frontend_origin=origin,
        load_env=False,
    )
    return TestClient(app, base_url="https://testserver")


def _sign_up(directory: MemoryDirectory, email: str = "ada@example.com") -> TestClient:
    directory.sign_up(email, "correct-horse", "Ada")
    client = _client(directory)
    response = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if response.status_code != 200:
        raise AssertionError(response.text)
    return client


def _six(plan: dict) -> list[dict]:
    return [
        {
            "week_number": session["week_number"],
            "day_of_week": session["day_of_week"],
            "date": session["date"],
            "template_id": session["template_id"],
            "reason_codes": list(session["reason_codes"]),
            "target_outcome": session["target_outcome"],
        }
        for session in plan["sessions"]
    ]


def _golden() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _generate(client: TestClient, payload: dict | None = None) -> dict:
    response = client.post("/seasons", json=payload or INPUTS)
    if response.status_code != 200:
        raise AssertionError(response.text)
    return response.json()


def _panel(inputs: tuple, stored: object, date_format: str) -> list[dict]:
    stats = []
    for label, value in season_summary(inputs, stored):
        shown = value
        if label == "Season" and " – " in value:
            start, end = value.split(" – ", 1)
            shown = f"{format_date(start, date_format)} – {format_date(end, date_format)}"
        stats.append({"label": label, "value": shown})
    return stats


def test_health_is_open() -> None:
    response = _client(MemoryDirectory()).get("/health")
    if response.status_code != 200 or response.json() != {"ok": True}:
        raise AssertionError(response.text)


def test_cors_allows_only_the_configured_origin() -> None:
    client = _client(MemoryDirectory(), origin="http://127.0.0.1:3000")
    allowed = client.get("/health", headers={"Origin": "http://127.0.0.1:3000"})
    if allowed.headers.get("access-control-allow-origin") != "http://127.0.0.1:3000":
        raise AssertionError(dict(allowed.headers))
    blocked = client.get("/health", headers={"Origin": "https://evil.example"})
    if blocked.headers.get("access-control-allow-origin") == "https://evil.example":
        raise AssertionError(dict(blocked.headers))
    try:
        load_settings("*")
    except RuntimeError:
        return
    raise AssertionError("a wildcard origin was accepted")


def test_sign_in_sets_an_httponly_cookie_and_me_returns_the_athlete() -> None:
    directory = MemoryDirectory()
    directory.sign_up("ada@example.com", "correct-horse", "Ada")
    client = _client(directory)
    response = client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    if response.status_code != 200:
        raise AssertionError(response.text)
    body = response.json()
    if "access_token" in body or "refresh_token" in body or "seal" in body:
        raise AssertionError(body)
    cookie = response.headers.get("set-cookie") or ""
    lowered = cookie.lower()
    if "httponly" not in lowered or "secure" not in lowered or "samesite=lax" not in lowered:
        raise AssertionError(cookie)
    if "rio_hosted=rio1." not in cookie:
        raise AssertionError(cookie)
    token = next(iter(directory.sessions))
    if token and token in cookie:
        raise AssertionError("the access token was written into the cookie")
    me = client.get("/auth/me")
    if me.status_code != 200:
        raise AssertionError(me.text)
    athlete = me.json()
    if athlete["email"] != "ada@example.com" or athlete["display_name"] != "Ada":
        raise AssertionError(athlete)
    if athlete["kind"] != "hosted" or athlete["role"] != "athlete":
        raise AssertionError(athlete)
    signed_out = client.post("/auth/sign-out")
    if signed_out.status_code != 200:
        raise AssertionError(signed_out.text)
    if client.get("/auth/me").status_code != 401:
        raise AssertionError("sign-out left the session in place")
    if client.get("/seasons/current").status_code != 401:
        raise AssertionError("a signed-out request read a season")


def test_a_wrong_password_is_refused() -> None:
    directory = MemoryDirectory()
    directory.sign_up("ada@example.com", "correct-horse", "Ada")
    client = _client(directory)
    response = client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "nope-nope"})
    if response.status_code != 401:
        raise AssertionError(response.text)


def test_a_local_account_signs_in_without_supabase(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    create_account(path, "local@example.com", "correct-horse", "Local")
    client = _client(None, accounts=path)
    response = client.post("/auth/sign-in", json={"email": "local@example.com", "password": "correct-horse"})
    if response.status_code != 200:
        raise AssertionError(response.text)
    cookie = (response.headers.get("set-cookie") or "").lower()
    if "httponly" not in cookie or "secure" not in cookie:
        raise AssertionError(cookie)
    if "correct-horse" in cookie:
        raise AssertionError("the password left the server")
    me = client.get("/auth/me")
    if me.status_code != 200 or me.json()["kind"] != "local":
        raise AssertionError(me.text)
    generated = _generate(client)
    if generated["plan"]["ontology_version"] != "v0.1":
        raise AssertionError(generated["plan"])
    again = client.get("/seasons/current")
    if again.status_code != 200 or again.json()["digest"] != generated["digest"]:
        raise AssertionError(again.text)


def test_generate_matches_the_engine_contract() -> None:
    """Start's four inputs return the pinned sequence, including ontology_version."""
    body = _generate(_sign_up(MemoryDirectory()))
    golden = _golden()["canonical_season"]
    if body["plan"]["ontology_version"] != golden["ontology_version"]:
        raise AssertionError(body["plan"]["ontology_version"])
    if body["plan"]["season_length_weeks"] != golden["season_length_weeks"]:
        raise AssertionError(body["plan"]["season_length_weeks"])
    if body["plan"]["start_date"] != golden["start_date"]:
        raise AssertionError(body["plan"]["start_date"])
    if _six(body["plan"]) != golden["sessions"]:
        raise AssertionError("generated sessions drifted from the contract")
    dumped = json.dumps(body["plan"])
    if "probability" in dumped or "readiness_score" in dumped:
        raise AssertionError("the season response included a score")
    if not body["digest"] or body["quality_base_weeks"] != []:
        raise AssertionError(body["quality_base_weeks"])


def test_week_marks_match_the_adapt_contract() -> None:
    golden = _golden()
    cases = (
        (10, "on_track", "adapt_on_track_week_10"),
        (37, "not_hitting", "adapt_not_hitting_week_37"),
        (28, "smashing", "adapt_smashing_week_28"),
    )
    client = _sign_up(MemoryDirectory())
    for week, choice, key in cases:
        _generate(client)
        response = client.post("/seasons/current/marks", json={"week": week, "choice": choice})
        if response.status_code != 200:
            raise AssertionError(response.text)
        body = response.json()
        if body["committed"] is not True:
            raise AssertionError(body)
        if _six(body["plan"]) != golden[key]["sessions"]:
            raise AssertionError(key)
        if body["marks"] != {str(week): choice}:
            raise AssertionError(body["marks"])
        if body["quality_base_weeks"] != [week]:
            raise AssertionError(body["quality_base_weeks"])


def test_a_result_matches_the_judge_contract_and_does_not_wait_on_the_model(monkeypatch) -> None:
    """The judged mark is stored even when the model fails. The model sees that save."""
    called = {"count": 0, "saved_first": False}
    directory = MemoryDirectory()
    client = _sign_up(directory)
    generated = _generate(client)
    golden = _golden()
    judged = next(row for row in golden["judge"] if row["text"] == "57.5" and row["result"] is not None)
    matches = [session for session in generated["plan"]["sessions"] if session["template_id"] == judged["template_id"]]
    if not matches:
        raise AssertionError("the contract template is not in the generated season")
    day = matches[0]["date"]

    def _spy(_payload):
        called["count"] += 1
        user_id = directory.by_email["ada@example.com"]
        called["saved_first"] = any(
            isinstance(row, dict) and day in (row.get("actuals") or {})
            for row in directory.plans.get(user_id) or []
        )
        return None

    monkeypatch.setattr("engines.explain.complete_insight", _spy)
    response = client.post(
        "/seasons/current/results",
        json={"date": day, "text": judged["text"], "note": {"headline": "no"}},
    )
    if response.status_code != 200:
        raise AssertionError(response.text)
    body = response.json()
    if called["count"] and called["saved_first"] is not True:
        raise AssertionError("the model ran before the plan was saved")
    if body["insight"]["status"] not in ("pending", "skipped"):
        raise AssertionError(body["insight"])
    saved = body["actuals"][day]
    if saved["mark"] != judged["result"]["mark"] or saved["numbers"] != judged["result"]["numbers"]:
        raise AssertionError(saved)
    if body["note_saved"] is not False:
        raise AssertionError("a bad note was stored")
    if body["committed"] is not True:
        raise AssertionError(body)
    if client.get("/seasons/current").json()["digest"] != body["digest"]:
        raise AssertionError("the result was not stored")


def test_a_later_week_is_not_adapted_twice() -> None:
    """The stored base is the plan from before that week, so a second mark does not stack."""
    client = _sign_up(MemoryDirectory())
    original = _generate(client)["plan"]
    first = client.post("/seasons/current/marks", json={"week": 1, "choice": "on_track"})
    second = client.post("/seasons/current/marks", json={"week": 2, "choice": "not_hitting"})
    if first.status_code != 200 or second.status_code != 200:
        raise AssertionError(second.text)
    bases: dict = {}
    scratch: dict = {}
    plan = adapt_from_result(original, 1, "on_track", bases, scratch)
    plan = adapt_from_result(plan, 2, "not_hitting", bases, scratch)
    stacked = adapt(plan, 2, "on_track")
    restored = adapt_from_result(plan, 2, "on_track", bases, scratch)
    if _six(stacked) == _six(restored):
        raise AssertionError("this fixture no longer shows a stacked adapt")
    again = client.post("/seasons/current/marks", json={"week": 2, "choice": "on_track"})
    if again.status_code != 200:
        raise AssertionError(again.text)
    if _six(again.json()["plan"]) != _six(restored):
        raise AssertionError("the second week mark stacked on the adapted plan")
    if again.json()["quality_base_weeks"] != [1, 2]:
        raise AssertionError(again.json()["quality_base_weeks"])


def test_a_missing_base_is_rebuilt_from_sequence_before_the_next_adapt() -> None:
    """Week 2 not_hitting changes the plan. The next mark must not start from that copy."""
    directory = MemoryDirectory()
    client = _sign_up(directory)
    original = _generate(client)["plan"]
    marked = client.post("/seasons/current/marks", json={"week": 2, "choice": "not_hitting"})
    if marked.status_code != 200:
        raise AssertionError(marked.text)
    directory.api_season_state = {}
    current = client.get("/seasons/current")
    if current.json()["quality_base_source"] != "recomputed":
        raise AssertionError(current.json()["quality_base_source"])
    if current.json()["quality_base_weeks"] != [2]:
        raise AssertionError(current.json()["quality_base_weeks"])
    again = client.post("/seasons/current/marks", json={"week": 2, "choice": "on_track"})
    if again.status_code != 200:
        raise AssertionError(again.text)
    bases: dict = {}
    scratch: dict = {}
    shifted = adapt_from_result(original, 2, "not_hitting", bases, scratch)
    restored = adapt_from_result(shifted, 2, "on_track", bases, scratch)
    stacked = adapt(marked.json()["plan"], 2, "on_track")
    if _six(restored) == _six(stacked):
        raise AssertionError("stacking would have looked the same")
    if _six(again.json()["plan"]) != _six(restored):
        raise AssertionError("the rebuild did not start from sequence()")
    if again.json()["quality_base_source"] != "stored":
        raise AssertionError(again.json()["quality_base_source"])


def test_watchless_done_uses_the_same_adapt_as_a_timed_mark() -> None:
    client = _sign_up(MemoryDirectory())
    generated = _generate(client)
    tuesday = next(
        session
        for session in generated["plan"]["sessions"]
        if session["week_number"] == 1 and session["day_of_week"] == "Tuesday"
    )
    blank = client.post(
        "/seasons/current/watchless",
        json={"date": tuesday["date"], "outcome": "Ahead", "time": ""},
    )
    if blank.status_code != 200:
        raise AssertionError(blank.text)
    if _six(blank.json()["plan"]) != _six(generated["plan"]):
        raise AssertionError("Done without a time adapted the season")
    fresh = _generate(client)
    timed = client.post(
        "/seasons/current/watchless",
        json={"date": tuesday["date"], "outcome": "Ahead", "time": "1:12.4"},
    )
    if timed.status_code != 200 or timed.json()["committed"] is not True:
        raise AssertionError(timed.text)
    expected = adapt(fresh["plan"], 1, "smashing")
    if _six(timed.json()["plan"]) != _six(expected):
        raise AssertionError("the timed Done mark did not adapt week 1 once")
    saved = timed.json()["actuals"][tuesday["date"]]
    if saved.get("mark") != "smashing" or saved.get("completed") is not True:
        raise AssertionError(saved)


def test_notes_are_saved_without_changing_the_plan() -> None:
    client = _sign_up(MemoryDirectory())
    generated = _generate(client)
    day = generated["plan"]["sessions"][0]["date"]
    saved = client.post("/seasons/current/notes", json={"date": day, "note": NOTE, "viewed": False})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    body = saved.json()
    if body["digest"] != generated["digest"]:
        raise AssertionError("saving a note rewrote the plan")
    if body["notes"][day]["viewed"] is not False or body["notes"][day]["note"] != NOTE:
        raise AssertionError(body["notes"])
    seen = client.post("/seasons/current/notes", json={"date": day, "note": NOTE, "viewed": True})
    if seen.json()["notes"][day]["viewed"] is not True:
        raise AssertionError(seen.text)
    refused = client.post(
        "/seasons/current/notes",
        json={
            "date": day,
            "note": {
                "headline": "Strava lap",
                "body": "gps",
                "carry_forward": "",
                "used_result_band": "on_track",
            },
        },
    )
    if refused.status_code != 400:
        raise AssertionError(refused.text)
    if client.get("/seasons/current").json()["notes"][day]["note"] != NOTE:
        raise AssertionError("a refused note replaced the stored one")


def test_past_seasons_list_and_delete_use_the_confirm_panel() -> None:
    directory = MemoryDirectory()
    client = _sign_up(directory)
    token = next(iter(directory.sessions))
    directory.save_timezone(token, "America/Los_Angeles")
    _generate(client)
    created = _generate(client, PAST)
    if created["inputs"]["goal_date"] != "2020-04-06":
        raise AssertionError(created["inputs"])
    listed = client.get("/seasons/past")
    if listed.status_code != 200:
        raise AssertionError(listed.text)
    seasons = listed.json()["seasons"]
    if len(seasons) != 1 or seasons[0]["inputs"] != PAST:
        raise AssertionError(seasons)
    today = local_today("America/Los_Angeles")
    if listed.json()["today"] != today.isoformat():
        raise AssertionError(listed.json()["today"])
    user_id = directory.by_email["ada@example.com"]
    stored = next(item for item in directory.plans[user_id] if item.get("goal_date") == "2020-04-06")
    expected = _panel(("2:05.0", "2020-01-06", "1:55.0", "2020-04-06"), summary_record(stored), "short")
    if seasons[0]["stats"] != expected:
        raise AssertionError((seasons[0]["stats"], expected))
    refused = client.request("DELETE", "/seasons/past", json={**INPUTS, "confirm": True})
    if refused.status_code != 409:
        raise AssertionError(refused.text)
    unconfirmed = client.request("DELETE", "/seasons/past", json={**PAST, "confirm": False})
    if unconfirmed.status_code != 400:
        raise AssertionError(unconfirmed.text)
    if len(client.get("/seasons/past").json()["seasons"]) != 1:
        raise AssertionError("an unconfirmed delete removed the season")
    deleted = client.request("DELETE", "/seasons/past", json={**PAST, "confirm": True})
    if deleted.status_code != 200:
        raise AssertionError(deleted.text)
    if deleted.json()["stats"] != expected or deleted.json()["deleted"] is not True:
        raise AssertionError(deleted.json())
    if client.get("/seasons/past").json()["seasons"] != []:
        raise AssertionError("the past season is still listed")
    current = client.get("/seasons/current")
    if current.status_code != 200 or current.json()["inputs"]["goal_date"] != "2027-03-19":
        raise AssertionError(current.text)


def test_prefs_follow_the_existing_helpers_and_do_not_change_the_plan() -> None:
    directory = MemoryDirectory()
    client = _sign_up(directory)
    token = next(iter(directory.sessions))
    directory.save_timezone(token, "Pacific/Auckland")
    directory.save_pace_units(token, "km")
    directory.save_no_watch(token, True)
    directory.save_easy_pace(token, "4:40", "km")
    me = client.get("/auth/me")
    if me.status_code != 200:
        raise AssertionError(me.text)
    prefs = me.json()["prefs"]
    if prefs["timezone"] != "Pacific/Auckland" or prefs["pace_units"] != "km":
        raise AssertionError(prefs)
    if prefs["no_watch"] is not True or prefs["logging"] != "done":
        raise AssertionError(prefs)
    if prefs["easy_pace_phrase"] != easy_pace_phrase("4:40", "km"):
        raise AssertionError(prefs)
    if me.json()["today"] != local_today("Pacific/Auckland").isoformat():
        raise AssertionError(me.json()["today"])
    body = _generate(client)
    if _six(body["plan"]) != _golden()["canonical_season"]["sessions"]:
        raise AssertionError("pace or no-watch changed the generated season")
    if body["logging"] != "done" or body["prefs"]["units"] != "km":
        raise AssertionError(body["prefs"])


def test_one_athlete_cannot_read_another_season() -> None:
    directory = MemoryDirectory()
    ada = _sign_up(directory, "ada@example.com")
    _generate(ada, PAST)
    _generate(ada)
    directory.sign_up("bea@example.com", "correct-horse", "Bea")
    bea = _client(directory)
    signed = bea.post("/auth/sign-in", json={"email": "bea@example.com", "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    if bea.get("/seasons/current").status_code != 404:
        raise AssertionError("Bea read Ada's season")
    removed = bea.request("DELETE", "/seasons/past", json={**PAST, "confirm": True})
    if removed.status_code != 404:
        raise AssertionError(removed.text)
    if len(ada.get("/seasons/past").json()["seasons"]) != 1:
        raise AssertionError("Bea deleted Ada's past season")
    if ada.get("/seasons/current").status_code != 200:
        raise AssertionError("Ada's season was removed")


def test_local_past_delete_matches_the_panel_and_keeps_the_plan_key_last(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    email, seal = create_account(path, "local@example.com", "correct-horse", "Local")
    write_local(path, email, seal, "Local", "", "UTC", {"pace_units": "mi", "no_watch": False, "date_format": "iso"})
    write_easy_pace(path, email, seal, "7:25", "mi")
    client = _client(None, accounts=path)
    signed = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    _generate(client, PAST)
    _generate(client)
    raw = read_record(path, email, seal, storage_key(("2:05.0", "2020-01-06", "1:55.0", "2020-04-06")))
    parsed = json.loads(raw or "")
    expected = _panel(("2:05.0", "2020-01-06", "1:55.0", "2020-04-06"), summary_record(parsed), "iso")
    listed = client.get("/seasons/past").json()["seasons"]
    if listed[0]["stats"] != expected:
        raise AssertionError((listed[0]["stats"], expected))
    deleted = client.request("DELETE", "/seasons/past", json={**PAST, "confirm": True})
    if deleted.status_code != 200 or deleted.json()["stats"] != expected:
        raise AssertionError(deleted.text)
    last = last_key(path, email, seal)
    if inputs_from_key(last) != ("2:02.9", "2026-04-19", "1:55.0", "2027-03-19"):
        raise AssertionError(last)
    if client.get("/auth/me").json()["prefs"]["easy_pace"] != "7:25":
        raise AssertionError(client.get("/auth/me").text)
    today = local_today("UTC")
    current_goal = {
        "current_time": "2:02.9",
        "start_date": (today - timedelta(days=21)).isoformat(),
        "goal_time": "1:55.0",
        "goal_date": today.isoformat(),
    }
    _generate(client, current_goal)
    kept = client.request("DELETE", "/seasons/past", json={**current_goal, "confirm": True})
    if kept.status_code != 409:
        raise AssertionError(kept.text)
