# test_api_step2c.py — account, reset, goal override, If-Match, admin, fixtures, spend.

"""No network. No production Supabase. The model is not called."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.account_flow import google_redirect_uri
from api.main import create_app
from engines.explain import SPEND_CAP_MICRO_USD
from engines.spend import read_spend
from tests.test_api import INPUTS, _generate
from tests.test_api_step2b import INSIGHT
from ui.accounts import create_account
from ui.cloud_store import SIGNUP_CONFIRM, SIGNUP_RATE, CloudAuthError, MemoryDirectory
from ui.hero_config import load_rotation

ORIGIN = "http://localhost:3000"


def _client(directory=None, accounts: Path | None = None) -> TestClient:
    app = create_app(
        directory=directory,
        accounts=accounts,
        frontend_origin=ORIGIN,
        load_env=False,
    )
    return TestClient(app, base_url="https://testserver")


def _hosted(email: str = "ada@example.com", name: str = "Ada") -> tuple[MemoryDirectory, TestClient]:
    directory = MemoryDirectory()
    client = _client(directory)
    created = client.post(
        "/auth/sign-up",
        json={"email": email, "password": "correct-horse", "name": name},
    )
    if created.status_code != 200:
        raise AssertionError(created.text)
    return directory, client


def _admin_env(email: str):
    previous = os.environ.get("RIO_ADMIN_EMAIL")
    os.environ["RIO_ADMIN_EMAIL"] = email
    return previous


def _restore_admin(previous) -> None:
    if previous is None:
        os.environ.pop("RIO_ADMIN_EMAIL", None)
    else:
        os.environ["RIO_ADMIN_EMAIL"] = previous


def test_sign_up_sets_the_cookie_and_hides_the_token() -> None:
    directory, client = _hosted()
    me = client.get("/auth/me")
    if me.status_code != 200 or me.json()["email"] != "ada@example.com":
        raise AssertionError(me.text)
    if me.json()["display_name"] != "Ada" or me.json()["kind"] != "hosted":
        raise AssertionError(me.json())
    if "access_token" in me.text or "password" in me.text:
        raise AssertionError(me.text)
    again = client.post(
        "/auth/sign-up",
        json={"email": "ada@example.com", "password": "correct-horse", "name": "Ada"},
    )
    if again.status_code != 400 or "already exists" not in again.json()["detail"]:
        raise AssertionError(again.text)
    short = client.post(
        "/auth/sign-up",
        json={"email": "bea@example.com", "password": "short", "name": "Bea"},
    )
    if short.status_code != 400:
        raise AssertionError(short.text)
    if "bea@example.com" in directory.by_email:
        raise AssertionError("a short password created an account")
    anonymous = _client(directory)
    if anonymous.get("/auth/me").status_code != 401:
        raise AssertionError("sign-up was open without a cookie")


def test_sign_up_confirmation_does_not_set_a_cookie() -> None:
    directory = MemoryDirectory()

    def confirm(*_args, **_kwargs):
        raise CloudAuthError(SIGNUP_CONFIRM)

    directory.sign_up = confirm
    client = _client(directory)
    response = client.post(
        "/auth/sign-up",
        json={"email": "ada@example.com", "password": "correct-horse", "name": "Ada"},
    )
    if response.status_code != 200 or response.json().get("confirm") is not True:
        raise AssertionError(response.text)
    if "set-cookie" in {key.lower() for key in response.headers}:
        raise AssertionError(response.headers)
    if client.get("/auth/me").status_code != 401:
        raise AssertionError("a confirmation created a session")


def test_sign_up_rate_limit_is_429() -> None:
    directory = MemoryDirectory()

    def limited(*_args, **_kwargs):
        raise CloudAuthError(SIGNUP_RATE)

    directory.sign_up = limited
    response = _client(directory).post(
        "/auth/sign-up",
        json={"email": "ada@example.com", "password": "correct-horse", "name": "Ada"},
    )
    if response.status_code != 429:
        raise AssertionError(response.text)


def test_a_local_sign_up_uses_the_account_file(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    client = _client(None, accounts=path)
    created = client.post(
        "/auth/sign-up",
        json={"email": "Local@Example.com", "password": "correct-horse", "name": "Local"},
    )
    if created.status_code != 200 or created.json()["kind"] != "local":
        raise AssertionError(created.text)
    if client.get("/auth/me").json()["email"] != "local@example.com":
        raise AssertionError(client.get("/auth/me").text)
    if client.post("/auth/forgot-password", json={"email": "local@example.com"}).status_code != 400:
        raise AssertionError("local reset pretended to send mail")
    if client.get("/auth/google").status_code != 503:
        raise AssertionError("google was offered without a directory")


def test_forgot_and_reset_password_round_trip() -> None:
    directory, client = _hosted()
    missing = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    known = client.post("/auth/forgot-password", json={"email": "Ada@Example.com"})
    if missing.status_code != 200 or known.status_code != 200:
        raise AssertionError(known.text)
    if missing.json() != known.json():
        raise AssertionError("an unknown address was told apart")
    if "token" in known.json():
        raise AssertionError(known.json())
    blank = client.post("/auth/forgot-password", json={"email": "not-an-email"})
    if blank.status_code != 400:
        raise AssertionError(blank.text)
    token = next(iter(directory.resets))
    bad = client.post("/auth/reset-password", json={"token": "nope", "password": "another-horse"})
    if bad.status_code != 400:
        raise AssertionError(bad.text)
    short = client.post("/auth/reset-password", json={"token": token, "password": "short"})
    if short.status_code != 400:
        raise AssertionError(short.text)
    saved = client.post("/auth/reset-password", json={"token": token, "password": "another-horse"})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    signed_out = _client(directory)
    old = signed_out.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    if old.status_code != 401:
        raise AssertionError(old.text)
    new = signed_out.post("/auth/sign-in", json={"email": "ada@example.com", "password": "another-horse"})
    if new.status_code != 200:
        raise AssertionError(new.text)


def test_change_password_and_email_keep_the_session() -> None:
    directory, client = _hosted()
    if client.post("/auth/password", json={"current_password": "wrong-password", "new_password": "another-horse"}).status_code != 400:
        raise AssertionError("a wrong password was accepted")
    if client.post("/auth/password", json={"current_password": "correct-horse", "new_password": "short"}).status_code != 400:
        raise AssertionError("a short password was accepted")
    changed = client.post(
        "/auth/password",
        json={"current_password": "correct-horse", "new_password": "another-horse"},
    )
    if changed.status_code != 200:
        raise AssertionError(changed.text)
    if client.get("/auth/me").status_code != 200:
        raise AssertionError("the cookie died with the password")
    fresh = _client(directory)
    if fresh.post("/auth/sign-in", json={"email": "ada@example.com", "password": "another-horse"}).status_code != 200:
        raise AssertionError("the new password was not stored")
    other = _client(directory)
    other.post("/auth/sign-up", json={"email": "taken@example.com", "password": "correct-horse", "name": "Taken"})
    clash = client.post("/auth/email", json={"email": "taken@example.com", "password": "another-horse"})
    if clash.status_code != 400:
        raise AssertionError(clash.text)
    moved = client.post("/auth/email", json={"email": "Ada.New@Example.com", "password": "another-horse"})
    if moved.status_code != 200 or moved.json()["email"] != "ada.new@example.com":
        raise AssertionError(moved.text)
    if client.get("/auth/me").json()["email"] != "ada.new@example.com":
        raise AssertionError(client.get("/auth/me").text)
    anonymous = _client(directory)
    if anonymous.post("/auth/password", json={"current_password": "another-horse", "new_password": "third-horse-1"}).status_code != 401:
        raise AssertionError("password change did not require a cookie")


def test_a_local_password_and_email_change_still_open_the_file(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    client = _client(None, accounts=path)
    created = client.post(
        "/auth/sign-up",
        json={"email": "local@example.com", "password": "correct-horse", "name": "Local"},
    )
    if created.status_code != 200:
        raise AssertionError(created.text)
    changed = client.post(
        "/auth/password",
        json={"current_password": "correct-horse", "new_password": "another-horse"},
    )
    if changed.status_code != 200:
        raise AssertionError(changed.text)
    generated = _generate(client)
    if generated["plan"]["ontology_version"] != "v0.1":
        raise AssertionError("the new seal could not save a season")
    overridden = client.put("/profile/goal", json={"goal_time": "1:54.0"})
    if overridden.status_code != 200 or overridden.json()["goal_override"] != "1:54.0":
        raise AssertionError(overridden.text)
    if client.get("/seasons/current").json()["digest"] != generated["digest"]:
        raise AssertionError("the goal override rebuilt the season")
    moved = client.post("/auth/email", json={"email": "moved@example.com", "password": "another-horse"})
    if moved.status_code != 200 or client.get("/auth/me").json()["email"] != "moved@example.com":
        raise AssertionError(moved.text)
    if client.get("/seasons/current").json()["digest"] != generated["digest"]:
        raise AssertionError("the season did not follow the new email")
    from ui.accounts import authenticate, last_key

    found = authenticate(path, "moved@example.com", "another-horse")
    if found is None or not str(last_key(path, found[0], found[1]) or "").startswith("rio.plan"):
        raise AssertionError("the goal record became the plan Streamlit opens")


def test_delete_account_requires_confirm_and_signs_out() -> None:
    directory, client = _hosted()
    refused = client.post("/auth/delete", json={"confirm": False})
    if refused.status_code != 400 or "ada@example.com" not in directory.by_email:
        raise AssertionError(refused.text)
    removed = client.post("/auth/delete", json={"confirm": True})
    if removed.status_code != 200 or removed.json()["deleted"] is not True:
        raise AssertionError(removed.text)
    if "ada@example.com" in directory.by_email:
        raise AssertionError("the account stayed")
    if client.get("/auth/me").status_code != 401:
        raise AssertionError("delete left the cookie working")
    if _client(directory).post("/auth/delete", json={"confirm": True}).status_code != 401:
        raise AssertionError("delete did not require a cookie")


def test_local_delete_requires_the_email_and_the_password(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    client = _client(None, accounts=path)
    client.post(
        "/auth/sign-up",
        json={"email": "local@example.com", "password": "correct-horse", "name": "Local"},
    )
    if client.post("/auth/delete", json={"confirm": True, "email": "other@example.com", "password": "correct-horse"}).status_code != 400:
        raise AssertionError("a different email was accepted")
    if client.post("/auth/delete", json={"confirm": True, "email": "local@example.com", "password": "wrong-password"}).status_code != 400:
        raise AssertionError("a wrong password deleted the account")
    removed = client.post(
        "/auth/delete",
        json={"confirm": True, "email": "Local@Example.com", "password": "correct-horse"},
    )
    if removed.status_code != 200:
        raise AssertionError(removed.text)
    if client.post("/auth/sign-in", json={"email": "local@example.com", "password": "correct-horse"}).status_code != 401:
        raise AssertionError("the local account was still there")


def test_google_start_and_callback_use_the_redirect_env(monkeypatch) -> None:
    directory = MemoryDirectory()
    client = _client(directory)
    monkeypatch.delenv("RIO_GOOGLE_REDIRECT_URI", raising=False)
    started = client.get("/auth/google")
    if started.status_code != 200:
        raise AssertionError(started.text)
    if started.json()["redirect_uri"] != google_redirect_uri():
        raise AssertionError(started.json())
    if "access_token" in started.text:
        raise AssertionError(started.text)
    monkeypatch.setenv("RIO_GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/google/callback")
    pointed = client.get("/auth/google")
    if pointed.json()["redirect_uri"] != "http://localhost:3000/auth/google/callback":
        raise AssertionError(pointed.json())
    if not pointed.json()["url"].startswith("http://localhost:3000/auth/google/callback?"):
        raise AssertionError(pointed.json())
    from api.account_flow import code_from_authorize_url

    code = code_from_authorize_url(pointed.json()["url"])
    finished = client.get(
        "/auth/google/callback",
        params={"code": code},
        headers={"X-RIO-Response": "json"},
    )
    if finished.status_code != 200 or finished.json()["kind"] != "hosted":
        raise AssertionError(finished.text)
    if "access_token" in finished.text:
        raise AssertionError(finished.text)
    cookie = (finished.headers.get("set-cookie") or "").lower()
    if "httponly" not in cookie or "samesite=lax" not in cookie:
        raise AssertionError(cookie)
    if client.get("/auth/me").status_code != 200:
        raise AssertionError("google did not sign in")
    again = client.get(
        "/auth/google/callback",
        params={"code": code},
        headers={"X-RIO-Response": "json"},
    )
    if again.status_code != 400:
        raise AssertionError(again.text)
    browser = _client(directory).get("/auth/google/callback", params={"code": "missing"}, follow_redirects=False)
    if browser.status_code != 302 or "google=error" not in browser.headers.get("location", ""):
        raise AssertionError(browser.headers)


def test_reset_plan_keeps_the_account() -> None:
    directory, client = _hosted()
    _generate(client)
    refused = client.post("/seasons/reset", json={"confirm": False})
    if refused.status_code != 400 or client.get("/seasons/current").status_code != 200:
        raise AssertionError(refused.text)
    reset = client.post("/seasons/reset", json={"confirm": True})
    if reset.status_code != 200 or reset.json()["reset"] is not True:
        raise AssertionError(reset.text)
    if client.get("/seasons/current").status_code != 404:
        raise AssertionError("a season stayed")
    if client.get("/auth/me").status_code != 200:
        raise AssertionError("reset removed the account")
    if directory.users[directory.by_email["ada@example.com"]]["display_name"] != "Ada":
        raise AssertionError("the name was cleared")
    if _client(directory).post("/seasons/reset", json={"confirm": True}).status_code != 401:
        raise AssertionError("reset did not require a cookie")


def test_profile_goal_override_does_not_rebuild_the_season() -> None:
    _directory, client = _hosted()
    generated = _generate(client)
    if client.put("/profile/goal", json={"goal_time": "nope"}).status_code != 400:
        raise AssertionError("a bad goal was stored")
    if client.get("/profile").json()["goal_time"] != INPUTS["goal_time"]:
        raise AssertionError("the season goal moved")
    saved = client.put("/profile/goal", json={"goal_time": "1:54.0"})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    body = saved.json()
    if body["goal_time"] != INPUTS["goal_time"] or body["goal_override"] != "1:54.0":
        raise AssertionError(body)
    if body["shown_goal"] != "1:54.0":
        raise AssertionError(body)
    goal_field = next(row for row in body["fields"] if row["label"] == "Goal 800m time")
    if goal_field["value"] != "1:54.0":
        raise AssertionError(goal_field)
    current = client.get("/seasons/current").json()
    if current["digest"] != generated["digest"] or current["inputs"]["goal_time"] != INPUTS["goal_time"]:
        raise AssertionError(current["inputs"])
    if client.get("/profile").json()["goal_override"] != "1:54.0":
        raise AssertionError("the override was not stored")
    if _client(_directory).put("/profile/goal", json={"goal_time": "1:54.0"}).status_code != 401:
        raise AssertionError("the override did not require a cookie")


def test_if_match_refuses_a_stale_season_write() -> None:
    _directory, client = _hosted()
    generated = _generate(client)
    digest = generated["digest"]
    stale = client.post(
        "/seasons/current/marks",
        json={"week": 1, "choice": "on_track"},
        headers={"If-Match": "not-the-digest"},
    )
    if stale.status_code != 412:
        raise AssertionError(stale.text)
    if client.get("/seasons/current").json()["marks"]:
        raise AssertionError("a stale write landed")
    saved = client.post(
        "/seasons/current/marks",
        json={"week": 1, "choice": "on_track"},
        headers={"If-Match": f'"{digest}"'},
    )
    if saved.status_code != 200 or saved.json()["marks"] != {"1": "on_track"}:
        raise AssertionError(saved.text)
    later = saved.json()["digest"]
    cleared = client.post(
        "/seasons/current/clear",
        json={"confirm": True},
        headers={"If-Match": digest},
    )
    if cleared.status_code != 412:
        raise AssertionError(cleared.text)
    if client.get("/seasons/current").json()["digest"] != later:
        raise AssertionError("a stale clear changed the season")
    open_write = client.post("/seasons/current/marks", json={"week": 1, "choice": "smashing"})
    if open_write.status_code != 200:
        raise AssertionError("a write without If-Match was refused")


def test_digest_if_match_stops_a_stale_week(monkeypatch) -> None:
    def _note(_payload):
        return {
            "headline": "Tuesday fell short",
            "body": "Tuesday fell short. Later weeks eased. The goal stays 1:55.",
            "carry_forward": "",
            "used_result_band": "fell_short",
        }

    calls = {"n": 0}

    def _complete(*_args, **_kwargs):
        calls["n"] += 1
        return None

    monkeypatch.setattr("engines.explain.complete_insight", _note)
    monkeypatch.setattr("engines.explain._complete", _complete)
    _directory, client = _hosted()
    generated = _generate(client)
    finished = dict(INSIGHT)
    finished["week_ended"] = True
    stale = client.post(
        "/insights/digest",
        json={"payload": finished},
        headers={"If-Match": "stale"},
    )
    if stale.status_code != 412 or calls["n"]:
        raise AssertionError(stale.text)
    started = client.post(
        "/insights/digest",
        json={"payload": finished},
        headers={"If-Match": generated["digest"]},
    )
    if started.status_code != 200 or started.json()["status"] != "pending":
        raise AssertionError(started.text)


def test_admin_accounts_test_season_and_hero(tmp_path: Path) -> None:
    previous = _admin_env("ada@example.com")
    try:
        directory, client = _hosted()
        generated = _generate(client)
        outsider = MemoryDirectory()
        # Share the directory so the second login is a different athlete.
        other = _client(directory)
        other.post("/auth/sign-up", json={"email": "bea@example.com", "password": "correct-horse", "name": "Bea"})
        if other.get("/admin/accounts").status_code != 403:
            raise AssertionError("a non-admin opened admin")
        if _client(directory).get("/admin/accounts").status_code != 401:
            raise AssertionError("admin did not require a cookie")
        listed = client.get("/admin/accounts")
        if listed.status_code != 200:
            raise AssertionError(listed.text)
        emails = {row["email"] for row in listed.json()["accounts"]}
        if "ada@example.com" not in emails or "bea@example.com" not in emails:
            raise AssertionError(listed.json())
        if any("password" in row for row in listed.json()["accounts"]):
            raise AssertionError(listed.json())
        loaded = client.post("/admin/test-season")
        if loaded.status_code != 200 or loaded.json()["loaded"] is not True:
            raise AssertionError(loaded.text)
        if client.get("/seasons/current").json()["digest"] != generated["digest"]:
            raise AssertionError("the test season wrote this login")
        preview = client.get("/admin/test-season")
        if preview.status_code != 200 or preview.json()["loaded"] is not True:
            raise AssertionError(preview.text)
        if preview.json()["inputs"][0] != "2:05.0":
            raise AssertionError(preview.json()["inputs"])
        if other.request("DELETE", "/admin/test-season", json={"confirm": True}).status_code != 403:
            raise AssertionError("a non-admin deleted the test season")
        if client.request("DELETE", "/admin/test-season", json={"confirm": False}).status_code != 400:
            raise AssertionError("delete ran without confirm")
        removed = client.request("DELETE", "/admin/test-season", json={"confirm": True})
        if removed.status_code != 200 or removed.json()["deleted"] is not True:
            raise AssertionError(removed.text)
        if client.get("/admin/test-season").json()["loaded"] is not False:
            raise AssertionError("the test athlete stayed")
        if "test+rio@example.invalid" in directory.by_email:
            raise AssertionError(directory.by_email)
        hero_path = tmp_path / "hero.json"
        client.app.state.hero_path = hero_path
        current = client.get("/admin/hero")
        if current.status_code != 200 or len(current.json()["photos"]) != 3:
            raise AssertionError(current.text)
        drafted = []
        for index, photo in enumerate(reversed(current.json()["photos"])):
            drafted.append(
                {
                    "id": photo["id"],
                    "enabled": index != 1,
                    "credit": photo["credit"] if index else "Photo by the test",
                }
            )
        saved = client.put("/admin/hero", json={"photos": drafted})
        if saved.status_code != 200:
            raise AssertionError(saved.text)
        if saved.json()["photos"][0]["credit"] != "Photo by the test":
            raise AssertionError(saved.json())
        if load_rotation(hero_path)[0]["credit"] != "Photo by the test":
            raise AssertionError("the hero file was not the test file")
        if (ROOT / "ui" / "assets" / "hero_rotation.json").exists():
            # The shipped file, when present, must not gain the test credit.
            shipped = (ROOT / "ui" / "assets" / "hero_rotation.json").read_text(encoding="utf-8")
            if "Photo by the test" in shipped:
                raise AssertionError("the startup file was edited")
        bad = client.put("/admin/hero", json={"photos": [{"id": "nope", "enabled": True, "credit": "x"}]})
        if bad.status_code != 400:
            raise AssertionError(bad.text)
    finally:
        _restore_admin(previous)


def test_local_admin_lists_the_account_file(tmp_path: Path) -> None:
    previous = _admin_env("local@example.com")
    try:
        path = tmp_path / "accounts.json"
        create_account(path, "local@example.com", "correct-horse", "Local")
        client = _client(None, accounts=path)
        client.post("/auth/sign-in", json={"email": "local@example.com", "password": "correct-horse"})
        listed = client.get("/admin/accounts")
        if listed.status_code != 200 or listed.json()["accounts"][0]["email"] != "local@example.com":
            raise AssertionError(listed.text)
        if client.post("/admin/test-season").status_code != 400:
            raise AssertionError("a local file grew a hosted test athlete")
    finally:
        _restore_admin(previous)


def test_fixture_routes_match_the_pages() -> None:
    previous = _admin_env("ada@example.com")
    try:
        directory, client = _hosted()
        other = _client(directory)
        other.post("/auth/sign-up", json={"email": "bea@example.com", "password": "correct-horse", "name": "Bea"})
        if other.get("/fixtures").status_code != 403:
            raise AssertionError("a non-admin classified a fixture")
        if _client(directory).get("/fixtures/goal").status_code != 401:
            raise AssertionError("fixtures did not require a cookie")
        names = client.get("/fixtures")
        if names.status_code != 200 or "race_800" not in names.json()["fixtures"]:
            raise AssertionError(names.text)
        classified = client.post("/fixtures/classify", json={"name": "race_800"})
        if classified.status_code != 200 or not classified.json().get("family"):
            raise AssertionError(classified.text)
        if classified.json().get("ontology_version") != "v0.1":
            raise AssertionError(classified.json())
        if client.post("/fixtures/classify", json={}).status_code != 400:
            raise AssertionError("an empty classify was accepted")
        prescribed = client.post("/fixtures/prescribe", json={"name": "race_800"})
        if prescribed.status_code != 200 or not prescribed.json()["rows"]:
            raise AssertionError(prescribed.text)
        if prescribed.json()["rows"][0].get("template_id") is None:
            raise AssertionError(prescribed.json())
        accepted = client.post("/fixtures/accept", json={"name": "race_800"})
        if accepted.status_code != 200 or accepted.json()["row"]["template_id"] != prescribed.json()["rows"][0]["template_id"]:
            raise AssertionError(accepted.text)
        planned = ROOT / "tests" / "fixtures" / "planned"
        before = sorted(path.name for path in planned.glob("*.yml")) if planned.is_dir() else []
        if "Photo" in accepted.text:
            raise AssertionError(accepted.text)
        after = sorted(path.name for path in planned.glob("*.yml")) if planned.is_dir() else []
        if before != after:
            raise AssertionError("accept wrote a checked-in planned fixture")
        book = client.get("/fixtures/ledger")
        if book.status_code != 200 or len(book.json()["entries"]) != 4:
            raise AssertionError(book.text)
        goal = client.get("/fixtures/goal")
        if goal.status_code != 200 or set(goal.json()) != {
            "current_mark",
            "target_time",
            "target_date",
            "limiting_capacities",
        }:
            raise AssertionError(goal.text)
    finally:
        _restore_admin(previous)


def test_shared_spend_is_one_counter_and_a_missing_table_uses_the_file(tmp_path: Path) -> None:
    import engines.spend as spend

    class Counter:
        def __init__(self) -> None:
            self.micro = 0

        def __call__(self, name, args):
            if name == "adopt_explain_spend":
                incoming = int(args["p_micro"])
                if incoming > self.micro:
                    self.micro = incoming
                return self.micro
            if name == "reserve_explain_spend":
                worst = int(args["p_worst"])
                cap = int(args["p_cap"])
                if cap != SPEND_CAP_MICRO_USD:
                    raise AssertionError(cap)
                if self.micro >= cap or (worst and self.micro + worst > cap):
                    return False
                self.micro += worst
                return True
            if name == "settle_explain_spend":
                self.micro = max(0, self.micro - int(args["p_reserved"]) + int(args["p_actual"]))
                return None
            raise AssertionError(name)

    counter = Counter()
    previous_path = os.environ.pop("RIO_EXPLAIN_SPEND_PATH", None)
    previous_override = spend._rpc_override
    spend._rpc_override = counter
    try:
        if spend.reserve_spend(1_000) is not True or counter.micro != 1_000:
            raise AssertionError(counter.micro)
        spend.settle_spend(1_000, 400)
        if counter.micro != 400:
            raise AssertionError(counter.micro)
        if spend.reserve_spend(SPEND_CAP_MICRO_USD) is not False:
            raise AssertionError("the shared cap was ignored")
        if counter.micro != 400:
            raise AssertionError("a refused reserve changed the row")
    finally:
        spend._rpc_override = previous_override
        if previous_path is None:
            os.environ.pop("RIO_EXPLAIN_SPEND_PATH", None)
        else:
            os.environ["RIO_EXPLAIN_SPEND_PATH"] = previous_path

    path = tmp_path / "spend.json"
    previous_path = os.environ.get("RIO_EXPLAIN_SPEND_PATH")
    previous_override = spend._rpc_override
    real_path = spend.spend_path
    os.environ.pop("RIO_EXPLAIN_SPEND_PATH", None)

    def missing(_name, _args):
        raise RuntimeError("function public.reserve_explain_spend does not exist")

    spend._rpc_override = missing
    spend.spend_path = lambda: path
    try:
        if spend.reserve_spend(250) is not True:
            raise AssertionError("the file fallback was refused")
        if read_spend(path) != 250:
            raise AssertionError(read_spend(path))
        spend.settle_spend(250, 80)
        if read_spend(path) != 80:
            raise AssertionError("settle did not return to the file")
    finally:
        spend.spend_path = real_path
        spend._rpc_override = previous_override
        if previous_path is None:
            os.environ.pop("RIO_EXPLAIN_SPEND_PATH", None)
        else:
            os.environ["RIO_EXPLAIN_SPEND_PATH"] = previous_path

    pinned = tmp_path / "pinned.json"
    previous_path = os.environ.get("RIO_EXPLAIN_SPEND_PATH")
    previous_override = spend._rpc_override

    def boom(*_args, **_kwargs):
        raise AssertionError("the file path still called the table")

    os.environ["RIO_EXPLAIN_SPEND_PATH"] = str(pinned)
    spend._rpc_override = boom
    try:
        if spend.reserve_spend(30) is not True or read_spend(pinned) != 30:
            raise AssertionError(read_spend(pinned))
    finally:
        spend._rpc_override = previous_override
        if previous_path is None:
            os.environ.pop("RIO_EXPLAIN_SPEND_PATH", None)
        else:
            os.environ["RIO_EXPLAIN_SPEND_PATH"] = previous_path
