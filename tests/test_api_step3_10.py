# test_api_step3_10.py — admin preview, fixture prose, and the broken home.

"""No network. No production Supabase. The model is not called."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import SPEND_CAP_MICRO_USD
from tests.test_api import _generate
from tests.test_api_step2c import _admin_env, _client, _hosted, _restore_admin
from ui.insights import _hard


def test_non_admin_is_forbidden_and_preview_does_not_write_this_login() -> None:
    previous = _admin_env("ada@example.com")
    try:
        directory, client = _hosted()
        generated = _generate(client)
        other = _client(directory)
        signed = other.post(
            "/auth/sign-up",
            json={"email": "bea@example.com", "password": "correct-horse", "name": "Bea"},
        )
        if signed.status_code != 200:
            raise AssertionError(signed.text)
        guarded = (
            "/admin/accounts",
            "/admin/hero",
            "/admin/test-season",
            "/fixtures",
            "/fixtures/planned",
            "/fixtures/ledger",
            "/fixtures/goal",
            "/home?preview=test",
            "/plan?preview=test",
            "/activities?preview=test",
        )
        for path in guarded:
            opened = other.get(path)
            if opened.status_code != 403 or opened.json()["detail"] != "That page is for the admin account.":
                raise AssertionError(path + " " + opened.text)
        if other.get("/auth/me").json()["role"] != "athlete":
            raise AssertionError(other.get("/auth/me").text)
        if client.get("/auth/me").json()["role"] != "admin":
            raise AssertionError(client.get("/auth/me").text)
        if client.get("/home?preview=test").status_code != 404:
            raise AssertionError("a missing test season opened a preview")
        loaded = client.post("/admin/test-season")
        if loaded.status_code != 200 or loaded.json()["name"] != "TEST Athlete":
            raise AssertionError(loaded.text)
        if client.get("/seasons/current").json()["digest"] != generated["digest"]:
            raise AssertionError("loading the test season wrote this login")
        home = client.get("/home?preview=test")
        if home.status_code != 200:
            raise AssertionError(home.text)
        body = home.json()
        if body["hello"] != "Hey, TEST Athlete" or body["preview"]["active"] is not True:
            raise AssertionError(body["hello"])
        if body["preview"]["banner"] != "TEST Athlete · read only. This login is not changed.":
            raise AssertionError(body["preview"])
        if not str(body["preview"]["status"]).startswith("TEST season · "):
            raise AssertionError(body["preview"])
        if body.get("broken") is True or body.get("season") is None:
            raise AssertionError("the test home did not draw")
        if client.get("/seasons/current").json()["digest"] != generated["digest"]:
            raise AssertionError("reading the preview wrote this login")
        blocked = client.post(
            "/seasons/current/marks",
            json={"week": 1, "choice": "on_track"},
            headers={"X-RIO-Preview": "test", "If-Match": generated["digest"]},
        )
        if blocked.status_code != 400 or blocked.json()["detail"] != "This login is not changed.":
            raise AssertionError(blocked.text)
        if client.get("/seasons/current").json()["digest"] != generated["digest"]:
            raise AssertionError("a preview write changed this login")
        activity = client.get("/activities?preview=test")
        if activity.status_code != 200 or not str(activity.json()["preview"]["status"]).startswith("TEST season · "):
            raise AssertionError(activity.text)
        plan = client.get("/plan?preview=test")
        if plan.status_code != 200 or plan.json()["preview"]["active"] is not True:
            raise AssertionError(plan.text)
        signed_out = other.post("/auth/sign-out", headers={"X-RIO-Preview": "test"})
        if signed_out.status_code != 200:
            raise AssertionError(signed_out.text)
    finally:
        _restore_admin(previous)


def test_a_plan_with_no_length_is_an_em_dash_state() -> None:
    previous = _admin_env("ada@example.com")
    try:
        directory, client = _hosted()
        _generate(client)
        user_id = directory.by_email["ada@example.com"]
        directory.plans[user_id][0]["plan"]["season_length_weeks"] = True
        home = client.get("/home")
        if home.status_code != 200 or home.json().get("broken") is not True:
            raise AssertionError(home.text)
        if home.json().get("season") is not None or home.json().get("copy"):
            raise AssertionError(home.text)
    finally:
        _restore_admin(previous)


def test_easy_days_and_lap_payloads_do_not_call_the_model() -> None:
    previous = _admin_env("ada@example.com")
    try:
        _directory, client = _hosted()
        _generate(client)
        plan = client.get("/plan")
        if plan.status_code != 200:
            raise AssertionError(plan.text)
        easy = next((row for row in plan.json()["sessions"] if isinstance(row, dict) and not _hard(row)), None)
        if easy is None:
            raise AssertionError("the season has no easy day")
        skipped = client.post("/insights/workout", json={"date": easy["date"]})
        if skipped.status_code != 200 or skipped.json()["status"] != "skipped":
            raise AssertionError(skipped.text)
        if client.app.state.insight_jobs:
            raise AssertionError("an easy day queued a note")
        leaked = client.post(
            "/insights/workout",
            json={"payload": {"laps": [{"distance_m": 400, "seconds": 70}], "strava": "activity"}},
        )
        if leaked.status_code != 400:
            raise AssertionError(leaked.text)
        if client.app.state.insight_jobs:
            raise AssertionError("a lap payload queued a note")
    finally:
        _restore_admin(previous)


def test_fixture_prose_is_the_rules_paragraph_and_hides_the_cap(tmp_path: Path) -> None:
    previous = _admin_env("ada@example.com")
    spend = tmp_path / "spend.json"
    spend.write_text(json.dumps({"micro_usd": SPEND_CAP_MICRO_USD}), encoding="utf-8")
    import os

    old = os.environ.get("RIO_EXPLAIN_SPEND_PATH")
    os.environ["RIO_EXPLAIN_SPEND_PATH"] = str(spend)
    try:
        _directory, client = _hosted()
        prescribed = client.post("/fixtures/prescribe", json={"name": "race_800"})
        if prescribed.status_code != 200 or not prescribed.json()["rows"]:
            raise AssertionError(prescribed.text)
        prose = prescribed.json()["rows"][0]["prose"]
        if not prose or "$25" in prose or "score" in prose.lower():
            raise AssertionError(prose)
        if prescribed.json().get("banner") != "FIXTURE":
            raise AssertionError(prescribed.text)
        planned = client.get("/fixtures/planned")
        if planned.status_code != 200 or not planned.json()["rows"]:
            raise AssertionError(planned.text)
        if not planned.json()["rows"][0]["prose"] or "$25" in json.dumps(planned.json()):
            raise AssertionError(planned.text)
        book = client.get("/fixtures/ledger")
        if book.status_code != 200 or book.json().get("banner") != "FIXTURE":
            raise AssertionError(book.text)
        if not book.json()["deposits_rows"]:
            raise AssertionError(book.text)
        goal = client.get("/fixtures/goal")
        if goal.status_code != 200 or goal.json().get("limiting_capacities") in (None, ""):
            raise AssertionError(goal.text)
        session = client.get("/fixtures/session?name=race_800")
        if session.status_code != 200 or "$25" in session.json().get("prose", ""):
            raise AssertionError(session.text)
        if "probability" in session.text or "readiness_score" in session.text:
            raise AssertionError(session.text)
    finally:
        if old is None:
            os.environ.pop("RIO_EXPLAIN_SPEND_PATH", None)
        else:
            os.environ["RIO_EXPLAIN_SPEND_PATH"] = old
        _restore_admin(previous)


def test_login_card_is_only_when_auth_is_unconfigured() -> None:
    directory, client = _hosted()
    hosted = client.get("/auth/availability")
    if hosted.status_code != 200 or hosted.json() != {"mode": "hosted"}:
        raise AssertionError(hosted.text)
    local = _client(None)
    found = local.get("/auth/availability")
    if found.status_code != 200 or found.json() != {"mode": "local"}:
        raise AssertionError(found.text)
    bare = _client(None)
    bare.app.state.directory = None
    bare.app.state.accounts_path = None
    missing = bare.get("/auth/availability")
    if missing.status_code != 200 or missing.json() != {"mode": "unconfigured"}:
        raise AssertionError(missing.text)
    if directory is None:
        raise AssertionError("hosted directory was dropped")


def test_reloading_does_not_mint_a_new_session_cookie() -> None:
    _directory, client = _hosted()
    me = client.get("/auth/me")
    if me.status_code != 200:
        raise AssertionError(me.text)
    if "set-cookie" in {key.lower() for key in me.headers}:
        raise AssertionError(me.headers)
    if "token" in me.text or "password" in me.text:
        raise AssertionError(me.text)


def test_splash_stays_on_the_track_photo() -> None:
    splash = (ROOT / "web" / "components" / "Splash.tsx").read_text(encoding="utf-8")
    startup = (ROOT / "ui" / "startup.py").read_text(encoding="utf-8")
    if "Photo by Giant Asparagus on Pexels" not in splash:
        raise AssertionError("the splash credit changed")
    if "enabled_frames" in startup:
        raise AssertionError("the splash started rotating hero frames")
    if "startup-track" not in (ROOT / "web" / "app" / "globals.css").read_text(encoding="utf-8"):
        raise AssertionError("the splash photo is not the track")
