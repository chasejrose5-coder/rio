# test_api_step2b.py — Strava, insights, and the screen routes. No live network.

"""Strava HTTP and the model are stand-ins. Supabase is the in-memory directory.

A bad insight payload returns before the model is asked. A second Strava
sync uses the stored quality base.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from api.strava_flow import redirect_for_api
from engines.explain import insight_inputs_ok
from services.season_commit import apply_activity_marks, plan_for_adapt
from tests.test_api import INPUTS, NOTE, _generate, _golden, _sign_up, _six
from ui.accounts import create_account, read_local, write_local
from ui.cloud_store import MemoryDirectory
from ui.result import goal_seconds
from ui.strava import StravaError, make_state, redirect_uri

JSON_HEADER = {"x-rio-response": "json"}
INSIGHT = {
    "goal_800": "1:55",
    "race_date": "4 April 2027",
    "days_to_goal": 120,
    "phase": 4,
    "phase_name": "Speed endurance arrives",
    "week_number": 6,
    "session_date": "2026-12-01",
    "session_family": "speed endurance",
    "session_label": "Tuesday",
    "planned_summary": "Hit: reps near goal 800 pace (1:55) with the rest kept.",
    "result_band": "fell_short",
    "result_detail": "The reps were slow.",
    "pace_factor_before": None,
    "pace_factor_after": None,
    "pace_factor_delta": None,
    "hard_days_this_week": {
        "planned": 2,
        "logged": 1,
        "on_track": 0,
        "fell_short": 1,
        "went_better": 0,
    },
    "later_weeks_effect": "eased",
    "easy_hr_note": None,
    "tone": "chase",
    "max_sentences": 4,
}
REPLY = {
    "headline": "Tuesday fell short",
    "body": "Tuesday fell short. Later weeks eased. The goal stays 1:55.",
    "carry_forward": "",
    "used_result_band": "fell_short",
}


def _app(directory=None, accounts: Path | None = None) -> TestClient:
    app = create_app(directory=directory, accounts=accounts, frontend_origin="http://localhost:3000", load_env=False)
    return TestClient(app, base_url="https://testserver")


def _signed(email: str = "ada@example.com") -> tuple[MemoryDirectory, TestClient]:
    directory = MemoryDirectory()
    directory.sign_up(email, "correct-horse", "Ada")
    client = _app(directory)
    response = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if response.status_code != 200:
        raise AssertionError(response.text)
    return directory, client


def _strava_env(monkeypatch) -> None:
    monkeypatch.setenv("RIO_STRAVA_CLIENT_ID", "test-client")
    monkeypatch.setenv("RIO_STRAVA_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("RIO_STRAVA_REDIRECT_URI", "https://testserver/strava/callback")


def _install_transport(client: TestClient, rows: list, *, fail: dict | None = None) -> dict:
    seen = {"after": [], "posts": 0}

    def post(url: str, form: dict) -> dict:
        seen["posts"] += 1
        if "deauthorize" in url:
            return {}
        return {
            "access_token": "token-access-secret",
            "refresh_token": "token-refresh-secret",
            "expires_at": 4_000_000_000,
            "athlete": {"id": 7, "firstname": "Ada", "lastname": "Lovelace"},
        }

    def get(url: str, query: dict, access_token: str) -> object:
        if access_token != "token-access-secret":
            raise StravaError("Strava could not be reached.")
        if fail and fail.get("on"):
            raise StravaError("Strava could not be reached.")
        if isinstance(query, dict) and "after" in query:
            seen["after"].append(query["after"])
        page = query.get("page") if isinstance(query, dict) else None
        if page not in (None, 1, "1"):
            return []
        return list(rows)

    client.app.state.strava_post = post
    client.app.state.strava_get = get
    return seen


def _connect(client: TestClient) -> dict:
    response = client.get("/strava/connect")
    if response.status_code != 200:
        raise AssertionError(response.text)
    body = response.json()
    if "nonce" in body or "access_token" in body or "refresh_token" in body:
        raise AssertionError(body)
    return body


def _callback(client: TestClient, url: str) -> dict:
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    state = query["state"][0]
    response = client.get(
        "/strava/callback",
        params={"code": "test-code", "state": state},
        headers=JSON_HEADER,
    )
    if response.status_code != 200:
        raise AssertionError(response.text)
    return response.json()


def _run(day: str, ident: int) -> dict:
    return {
        "id": ident,
        "name": "Morning Run",
        "sport_type": "Run",
        "start_date_local": f"{day}T08:00:00",
        "distance": 5000.0,
        "moving_time": 1500,
        "elapsed_time": 1560,
        "average_heartrate": 148,
        "laps": [{"distance": 400, "moving_time": 20, "elapsed_time": 20}],
    }


def _session(plan: dict, week: int, weekday: str) -> dict:
    for session in plan["sessions"]:
        if session["week_number"] == week and session["day_of_week"] == weekday:
            return session
    raise AssertionError(f"week {week} has no {weekday}")


def test_strava_routes_require_sign_in() -> None:
    client = _app(MemoryDirectory())
    if client.get("/strava/status").status_code != 401:
        raise AssertionError("status was public")
    if client.get("/strava/connect").status_code != 401:
        raise AssertionError("connect was public")
    if client.post("/strava/sync", json={"scope": "recent"}).status_code != 401:
        raise AssertionError("sync was public")


def test_redirect_uri_is_configurable_and_streamlit_keeps_its_own(monkeypatch) -> None:
    monkeypatch.setenv("RIO_APP_URL", "https://riotraining.streamlit.app")
    monkeypatch.setenv("RIO_STRAVA_REDIRECT_URI", "https://new.example/strava/callback")
    if redirect_uri() != "https://riotraining.streamlit.app/":
        raise AssertionError(redirect_uri())
    if redirect_for_api() != "https://new.example/strava/callback":
        raise AssertionError(redirect_for_api())
    monkeypatch.delenv("RIO_STRAVA_REDIRECT_URI")
    if redirect_for_api() != "https://riotraining.streamlit.app/":
        raise AssertionError(redirect_for_api())


def test_connect_stores_the_nonce_and_callback_checks_it(monkeypatch) -> None:
    _strava_env(monkeypatch)
    directory, client = _signed()
    _install_transport(client, [])
    user_id = directory.by_email["ada@example.com"]
    forged = make_state(user_id, "not-stored")
    missed = client.get("/strava/callback", params={"code": "test-code", "state": forged}, headers=JSON_HEADER)
    if missed.status_code != 400:
        raise AssertionError(missed.text)
    if client.app.state.memory_strava.tokens:
        raise AssertionError("a nonce that was never stored connected Strava")
    started = _connect(client)
    parsed = urllib.parse.urlparse(started["url"])
    if parsed.netloc != "www.strava.com":
        raise AssertionError(started["url"])
    query = urllib.parse.parse_qs(parsed.query)
    if query["redirect_uri"][0] != "https://testserver/strava/callback":
        raise AssertionError(query)
    saved = client.app.state.oauth_nonces.get(user_id)
    if not isinstance(saved, dict) or saved["nonce"] not in query["state"][0]:
        raise AssertionError("the nonce was not stored on the server")
    if "rio_strava" in json.dumps(dict(client.cookies)):
        raise AssertionError("the nonce was written into a cookie")
    tampered = query["state"][0][:-1] + ("a" if query["state"][0][-1] != "a" else "b")
    refused = client.get("/strava/callback", params={"code": "test-code", "state": tampered}, headers=JSON_HEADER)
    if refused.status_code != 400:
        raise AssertionError(refused.text)
    if user_id not in client.app.state.oauth_nonces:
        raise AssertionError("a bad callback burned the stored nonce")
    done = _callback(client, started["url"])
    if done["connected"] is not True or done["athlete_name"] != "Ada Lovelace":
        raise AssertionError(done)
    if "token-access-secret" in json.dumps(done) or "token-refresh-secret" in json.dumps(done):
        raise AssertionError(done)
    if user_id in client.app.state.oauth_nonces:
        raise AssertionError("the nonce was still stored after the callback")
    again = client.get("/strava/callback", params={"code": "test-code", "state": query["state"][0]}, headers=JSON_HEADER)
    if again.status_code != 400:
        raise AssertionError("a used nonce was accepted")
    status = client.get("/strava/status")
    if status.json()["connected"] is not True or "token-access-secret" in status.text:
        raise AssertionError(status.text)
    browser = client.get("/strava/callback", params={"code": "x", "state": "nope"}, follow_redirects=False)
    if browser.status_code != 302 or "strava=error" not in (browser.headers.get("location") or ""):
        raise AssertionError(browser.headers.get("location"))


def test_another_athlete_cannot_finish_the_connect_or_read_the_token(monkeypatch) -> None:
    _strava_env(monkeypatch)
    directory, ada = _signed()
    _install_transport(ada, [])
    started = _connect(ada)
    directory.sign_up("bea@example.com", "correct-horse", "Bea")
    bea = _app(directory)
    signed = bea.post("/auth/sign-in", json={"email": "bea@example.com", "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    _install_transport(bea, [])
    parsed = urllib.parse.urlparse(started["url"])
    state = urllib.parse.parse_qs(parsed.query)["state"][0]
    stolen = bea.get("/strava/callback", params={"code": "test-code", "state": state}, headers=JSON_HEADER)
    if stolen.status_code != 400:
        raise AssertionError(stolen.text)
    if bea.get("/strava/status").json()["connected"] is not False:
        raise AssertionError("Bea looked connected")
    done = _callback(ada, started["url"])
    if done["connected"] is not True:
        raise AssertionError(done)
    if bea.get("/strava/status").json()["connected"] is not False:
        raise AssertionError("Bea read Ada's Strava connection")


def test_sync_uses_the_stored_base_and_a_failure_does_not_stick(monkeypatch) -> None:
    _strava_env(monkeypatch)
    _directory, client = _signed()
    original = _generate(client)["plan"]
    tuesday = _session(original, 1, "Tuesday")
    thursday = _session(original, 1, "Thursday")
    rows = [_run(tuesday["date"], 11), {"id": 99, "name": "Ride", "sport_type": "Ride", "start_date_local": tuesday["date"] + "T18:00:00", "distance": 1000, "moving_time": 300}]
    seen = _install_transport(client, rows)
    called = {"model": 0}

    def _model(_payload):
        called["model"] += 1
        raise AssertionError("sync called the model")

    monkeypatch.setattr("engines.explain.complete_insight", _model)

    def _intervals(*_args, **_kwargs):
        raise AssertionError("Strava was connected and Intervals was called")

    client.app.state.intervals_sync_recent = _intervals
    client.app.state.intervals_sync_all = _intervals
    _callback(client, _connect(client)["url"])
    first = client.post("/strava/sync", json={"scope": "all"})
    if first.status_code != 200:
        raise AssertionError(first.text)
    body = first.json()
    if body["synced"] is not True or body["count"] != 1:
        raise AssertionError(body)
    if "token-access-secret" in first.text or "token-refresh-secret" in first.text:
        raise AssertionError("the sync response included a token")
    if body["committed"] is not True or body["marks"].get("1") != "smashing":
        raise AssertionError(body["marks"])
    if body["quality_base_weeks"] != [1]:
        raise AssertionError(body["quality_base_weeks"])
    if called["model"]:
        raise AssertionError("the model ran during sync")
    first_plan = body["plan"]
    first_actuals = deepcopy(body["actuals"])
    first_marks = {int(key): value for key, value in body["marks"].items()}
    rows.append(_run(thursday["date"], 12))
    second = client.post("/strava/sync", json={"scope": "all"})
    if second.status_code != 200 or second.json()["synced"] is not True:
        raise AssertionError(second.text)
    acts = second.json()["activities"]
    goal = goal_seconds("1:55.0")
    with_base = apply_activity_marks(
        first_plan,
        acts,
        deepcopy(first_actuals),
        goal,
        {1: plan_for_adapt(original)},
        dict(first_marks),
    )
    without = apply_activity_marks(first_plan, acts, deepcopy(first_actuals), goal, {}, dict(first_marks))
    if with_base.plan is None or without.plan is None:
        raise AssertionError("the Thursday run did not adapt, so the base was not tested")
    if _six(with_base.plan) == _six(without.plan):
        raise AssertionError("this fixture no longer shows a double adapt")
    if _six(second.json()["plan"]) != _six(with_base.plan):
        raise AssertionError("the second sync did not use the stored quality base")
    if _six(second.json()["plan"]) == _six(without.plan):
        raise AssertionError("the second sync adapted the week from the already adapted plan")
    recent = client.post("/strava/sync", json={"scope": "recent"})
    full = client.post("/strava/sync", json={"scope": "all"})
    if recent.status_code != 200 or full.status_code != 200:
        raise AssertionError(full.text)
    if not seen["after"] or not (seen["after"][-2] > seen["after"][-1]):
        raise AssertionError(seen["after"])
    stuck = client.get("/strava/status").json()["last_sync_at"]
    client.app.state.strava_get = lambda *_args, **_kwargs: (_ for _ in ()).throw(StravaError("Strava could not be reached."))
    failed = client.post("/strava/sync", json={"scope": "recent"})
    if failed.status_code != 200 or failed.json()["synced"] is not False:
        raise AssertionError(failed.text)
    if client.get("/strava/status").json()["last_sync_at"] != stuck:
        raise AssertionError("a failed import moved last_sync_at")
    client.app.state.strava_gate.per_quarter = 0
    blocked = client.post("/strava/sync", json={"scope": "recent"})
    if blocked.status_code != 429:
        raise AssertionError(blocked.text)


def test_disconnect_removes_tokens_and_a_missing_setup_is_refused(monkeypatch) -> None:
    directory, client = _signed()
    missing = client.get("/strava/connect")
    if missing.status_code != 503:
        raise AssertionError(missing.text)
    _strava_env(monkeypatch)
    _install_transport(client, [])
    _generate(client)
    _callback(client, _connect(client)["url"])
    user_id = directory.by_email["ada@example.com"]
    if user_id not in client.app.state.memory_strava.tokens:
        raise AssertionError("the token was not stored")
    gone = client.post("/strava/disconnect")
    if gone.status_code != 200 or gone.json()["connected"] is not False:
        raise AssertionError(gone.text)
    if "token-access-secret" in gone.text:
        raise AssertionError(gone.text)
    if client.app.state.memory_strava.tokens or client.app.state.memory_strava.activities:
        raise AssertionError("disconnect left a token or a run")
    if client.get("/strava/status").json()["connected"] is not False:
        raise AssertionError("status still says connected")


def test_intervals_fallback_also_uses_the_stored_base(monkeypatch) -> None:
    monkeypatch.delenv("RIO_STRAVA_CLIENT_ID", raising=False)
    monkeypatch.delenv("RIO_STRAVA_CLIENT_SECRET", raising=False)
    _directory, client = _signed()
    original = _generate(client)["plan"]
    tuesday = _session(original, 1, "Tuesday")
    thursday = _session(original, 1, "Thursday")
    box = {"calls": []}

    def recent(sessions, stored, today, **_kwargs):
        box["calls"].append("recent")
        return [
            {
                "id": "tue",
                "date": tuesday["date"],
                "matched": True,
                "template_id": tuesday["template_id"],
                "name": "Run",
                "reps": [None, 20],
            }
        ]

    def every(sessions, stored, today, **_kwargs):
        box["calls"].append("all")
        return [
            {
                "id": "tue",
                "date": tuesday["date"],
                "matched": True,
                "template_id": tuesday["template_id"],
                "name": "Run",
                "reps": [None, 20],
            },
            {
                "id": "thu",
                "date": thursday["date"],
                "matched": True,
                "template_id": thursday["template_id"],
                "name": "Run",
                "reps": [None, 20],
            },
        ]

    client.app.state.intervals_sync_recent = recent
    client.app.state.intervals_sync_all = every
    first = client.post("/strava/sync", json={"scope": "recent"})
    if first.status_code != 200 or first.json()["synced"] is not True:
        raise AssertionError(first.text)
    if box["calls"] != ["recent"]:
        raise AssertionError(box["calls"])
    second = client.post("/strava/sync", json={"scope": "all"})
    if second.status_code != 200 or box["calls"] != ["recent", "all"]:
        raise AssertionError(second.text)
    goal = goal_seconds("1:55.0")
    marks = {int(key): value for key, value in first.json()["marks"].items()}
    with_base = apply_activity_marks(
        first.json()["plan"],
        second.json()["activities"],
        deepcopy(first.json()["actuals"]),
        goal,
        {1: plan_for_adapt(original)},
        dict(marks),
    )
    without = apply_activity_marks(
        first.json()["plan"],
        second.json()["activities"],
        deepcopy(first.json()["actuals"]),
        goal,
        {},
        dict(marks),
    )
    if with_base.plan is None or without.plan is None or _six(with_base.plan) == _six(without.plan):
        raise AssertionError("the fallback fixture did not separate the stored base")
    if _six(second.json()["plan"]) != _six(with_base.plan):
        raise AssertionError("the intervals sync did not use the stored quality base")


def test_a_bad_insight_returns_before_the_model_and_a_score_is_rejected(monkeypatch) -> None:
    calls = {"model": 0, "complete": 0}

    def _model(_payload):
        calls["model"] += 1
        raise AssertionError("the model was called")

    def _complete(*_args, **_kwargs):
        calls["complete"] += 1
        raise AssertionError("explain called the model")

    monkeypatch.setattr("engines.explain.complete_insight", _model)
    monkeypatch.setattr("engines.explain._complete", _complete)
    _directory, client = _signed()
    _generate(client)
    bad = dict(INSIGHT)
    bad["strava_laps"] = [{"lat": 1}]
    if insight_inputs_ok(bad) is not False:
        raise AssertionError("the fixture payload was supposed to fail the check")
    refused = client.post("/insights/workout", json={"payload": bad})
    if refused.status_code != 400:
        raise AssertionError(refused.text)
    scored = client.post("/insights/workout", json={"payload": INSIGHT, "plan": {"probability": 0.2}})
    if scored.status_code != 400:
        raise AssertionError(scored.text)
    open_week = client.post("/insights/digest", json={"payload": dict(INSIGHT)})
    if open_week.status_code != 400:
        raise AssertionError(open_week.text)
    explain = client.post("/insights/explain", json={"kind": "classification", "classification": {"family": "speed"}})
    if explain.status_code != 400:
        raise AssertionError(explain.text)
    if calls["model"] or calls["complete"]:
        raise AssertionError(calls)


def test_a_workout_note_is_pending_until_it_is_fetched(monkeypatch) -> None:
    def _note(_payload):
        return dict(REPLY)

    monkeypatch.setattr("engines.explain.complete_insight", _note)
    monkeypatch.setattr("engines.explain._complete", lambda *_args, **_kwargs: None)
    _directory, client = _signed()
    _generate(client)
    started = client.post("/insights/workout", json={"payload": INSIGHT})
    if started.status_code != 200:
        raise AssertionError(started.text)
    body = started.json()
    if body["status"] != "pending" or not body["id"]:
        raise AssertionError(body)
    fetched = client.get(f"/insights/jobs/{body['id']}")
    if fetched.status_code != 200 or fetched.json()["status"] != "ready":
        raise AssertionError(fetched.text)
    if fetched.json()["note"] != REPLY:
        raise AssertionError(fetched.json())
    by_day = client.get("/insights/workout/2026-12-01")
    if by_day.json()["note"] != REPLY:
        raise AssertionError(by_day.text)
    if "token" in fetched.text.lower() and "access_token" in fetched.text:
        raise AssertionError(fetched.text)


def test_digest_and_explain_return_pending_and_do_not_block(monkeypatch) -> None:
    def _note(_payload):
        return dict(REPLY)

    def _complete(*_args, **_kwargs):
        return None

    monkeypatch.setattr("engines.explain.complete_insight", _note)
    monkeypatch.setattr("engines.explain._complete", _complete)
    _directory, client = _signed()
    finished = dict(INSIGHT)
    finished["week_ended"] = True
    digest = client.post("/insights/digest", json={"payload": finished})
    if digest.status_code != 200 or digest.json()["status"] != "pending":
        raise AssertionError(digest.text)
    ready = client.get(f"/insights/jobs/{digest.json()['id']}")
    if ready.json()["status"] != "ready" or ready.json()["note"] != REPLY:
        raise AssertionError(ready.text)
    explained = client.post(
        "/insights/explain",
        json={
            "kind": "classification",
            "classification": {
                "family": "speed_endurance",
                "reason_codes": ["work_600_1000m"],
                "confidence": "high",
            },
        },
    )
    if explained.status_code != 200 or explained.json()["status"] != "pending":
        raise AssertionError(explained.text)
    text = client.get(f"/insights/jobs/{explained.json()['id']}")
    if text.json()["status"] != "ready" or "speed endurance" not in (text.json()["text"] or "").lower():
        raise AssertionError(text.text)


def test_settings_library_home_plan_profile_and_session(monkeypatch) -> None:
    monkeypatch.delenv("RIO_STRAVA_CLIENT_ID", raising=False)
    directory, client = _signed()
    saved = client.patch(
        "/settings",
        json={
            "pace_units": "km",
            "timezone": "Pacific/Auckland",
            "no_watch": True,
            "easy_pace": "4:40",
            "easy_pace_unit": "km",
            "display_name": "Ada Lovelace",
            "date_format": "short",
            "confirm_adapt": True,
            "intro_seen": True,
        },
    )
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    prefs = saved.json()["prefs"]
    if prefs["pace_units"] != "km" or prefs["no_watch"] is not True or prefs["logging"] != "done":
        raise AssertionError(prefs)
    if prefs["timezone"] != "Pacific/Auckland" or prefs["easy_pace"] != "4:40":
        raise AssertionError(prefs)
    if prefs["date_format"] != "short" or prefs["confirm_adapt"] is not True or prefs["intro_seen"] is not True:
        raise AssertionError(prefs)
    if saved.json()["display_name"] != "Ada Lovelace":
        raise AssertionError(saved.json())
    bad_pace = client.patch("/settings", json={"easy_pace": "fast", "easy_pace_unit": "km"})
    if bad_pace.status_code != 400:
        raise AssertionError(bad_pace.text)
    if client.get("/auth/me").json()["prefs"]["easy_pace"] != "4:40":
        raise AssertionError("a bad pace replaced the saved one")
    generated = _generate(client)
    if _six(generated["plan"]) != _golden()["canonical_season"]["sessions"]:
        raise AssertionError("settings changed the generated season")
    if generated["strava_offer"] is not True:
        raise AssertionError(generated.get("strava_offer"))
    home = client.get("/home")
    if home.status_code != 200 or home.json()["season"] is None:
        raise AssertionError(home.text)
    if home.json()["season"]["digest"] != generated["digest"]:
        raise AssertionError("home did not read the stored season")
    library = client.get("/library")
    if library.status_code != 200 or library.json()["count"] < 1:
        raise AssertionError(library.text)
    narrowed = client.get("/library", params={"q": "no-such-workout-xyz"})
    if narrowed.json()["count"] != 0:
        raise AssertionError(narrowed.text)
    plan = client.get("/plan")
    if plan.status_code != 200 or not plan.json()["calendar"] or not plan.json()["weeks"]:
        raise AssertionError(plan.text)
    profile = client.get("/profile")
    if profile.status_code != 200 or not profile.json()["profile_key"].startswith("rio.profile.v1"):
        raise AssertionError(profile.text)
    if profile.json()["goal_time"] != INPUTS["goal_time"]:
        raise AssertionError(profile.json())
    day = generated["plan"]["sessions"][0]["date"]
    session = client.get(f"/sessions/{day}")
    if session.status_code != 200 or session.json()["session"]["date"] != day:
        raise AssertionError(session.text)
    refused = client.post("/seasons/current/clear", json={"confirm": False})
    if refused.status_code != 400:
        raise AssertionError(refused.text)
    marked = client.post("/seasons/current/marks", json={"week": 1, "choice": "on_track"})
    if marked.status_code != 200 or marked.json()["quality_base_weeks"] != [1]:
        raise AssertionError(marked.text)
    cleared = client.post("/seasons/current/clear", json={"confirm": True})
    if cleared.status_code != 200 or cleared.json()["marks"] or cleared.json()["quality_base_weeks"]:
        raise AssertionError(cleared.text)
    if directory.users[directory.by_email["ada@example.com"]]["pace_units"] != "km":
        raise AssertionError("pace was not stored on the athlete")


def test_local_settings_use_the_account_file(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    email, seal = create_account(path, "local@example.com", "correct-horse", "Local")
    write_local(path, email, seal, "Local", "", "UTC", {"pace_units": "mi", "no_watch": False})
    client = _app(None, accounts=path)
    signed = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    saved = client.patch(
        "/settings",
        json={"pace_units": "km", "no_watch": True, "timezone": "UTC", "preferred": "Loc"},
    )
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    if saved.json()["prefs"]["pace_units"] != "km" or saved.json()["prefs"]["preferred"] != "Loc":
        raise AssertionError(saved.json())
    stored = read_local(path, email) or {}
    if stored.get("settings", {}).get("no_watch") is not True or stored.get("preferred") != "Loc":
        raise AssertionError(stored)
