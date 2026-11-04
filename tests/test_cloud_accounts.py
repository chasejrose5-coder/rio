# test_cloud_accounts.py — sign-in and row separation, offline.

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.access import ENV_NAME, viewer_is_admin
from ui.cloud_config import cloud_configured, setup_notice_html
from ui.cloud_store import CloudAuthError, reset_memory_directory

_NAMES = (
    "RIO_SUPABASE_URL",
    "RIO_SUPABASE_ANON_KEY",
    "RIO_SUPABASE_SERVICE_ROLE_KEY",
    "RIO_AUTH_BACKEND",
    ENV_NAME,
)


def _saved() -> dict:
    return {name: os.environ.get(name) for name in _NAMES}


def _restore(saved: dict) -> None:
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def test_sign_up_log_in_and_log_out() -> None:
    directory = reset_memory_directory()
    session = directory.sign_up("Athlete@Example.com", "long-password", "Athlete")
    if session["email"] != "athlete@example.com" or session["role"] != "athlete":
        raise AssertionError(session)
    again = directory.sign_in("athlete@example.com", "long-password")
    if again["user_id"] != session["user_id"]:
        raise AssertionError(again)
    try:
        directory.sign_in("athlete@example.com", "wrong-password")
    except CloudAuthError:
        pass
    else:
        raise AssertionError("a wrong password was accepted")
    directory.sign_out(again["access_token"])
    try:
        directory.load_bundle(again["access_token"])
    except CloudAuthError:
        pass
    else:
        raise AssertionError("a signed-out token still opened rows")
    token = directory.request_reset("athlete@example.com")
    directory.reset_password(token, "newer-password")
    fresh = directory.sign_in("athlete@example.com", "newer-password")
    if fresh["user_id"] != session["user_id"]:
        raise AssertionError(fresh)


def test_one_user_cannot_read_another() -> None:
    directory = reset_memory_directory()
    first = directory.sign_up("a@example.com", "password-one", "Ada")
    second = directory.sign_up("b@example.com", "password-two", "Bea")
    directory.save_bundle(
        first["access_token"],
        {
            "goal": {
                "event": "800m",
                "goal_time": "1:55",
                "goal_date": "2027-03-19",
                "current_mark": "2:02",
            },
            "plans": [{"current_time": "2:02", "plan": {"sessions": [1]}}],
            "results": [{"logged_on": "2026-11-03", "payload": {"numbers": [22.1]}}],
        },
    )
    other = directory.load_bundle(second["access_token"])
    if other["goal"]["goal_time"] or other["plans"] or other["results"]:
        raise AssertionError(other)
    own = directory.load_bundle(first["access_token"])
    if own["goal"]["goal_time"] != "1:55" or not own["plans"]:
        raise AssertionError(own)


def test_delete_removes_only_that_account() -> None:
    directory = reset_memory_directory()
    first = directory.sign_up("a@example.com", "password-one", "Ada")
    second = directory.sign_up("b@example.com", "password-two", "Bea")
    directory.save_bundle(second["access_token"], {"goal": {"goal_time": "2:00"}})
    try:
        directory.delete_user(first["access_token"], "")
    except CloudAuthError:
        pass
    else:
        raise AssertionError("delete worked without the server key")
    directory.delete_user(first["access_token"], "server-key")
    try:
        directory.load_bundle(first["access_token"])
    except CloudAuthError:
        pass
    else:
        raise AssertionError("a deleted account still opened")
    kept = directory.load_bundle(second["access_token"])
    if kept["goal"]["goal_time"] != "2:00":
        raise AssertionError(kept)


def test_admin_gate_and_missing_list() -> None:
    saved = _saved()
    try:
        os.environ[ENV_NAME] = ""
        if viewer_is_admin("someone@example.com"):
            raise AssertionError("an empty admin email matched")
        os.environ[ENV_NAME] = "Coach@Example.com"
        if not viewer_is_admin("coach@example.com"):
            raise AssertionError("the admin email did not match")
        if viewer_is_admin("athlete@example.com"):
            raise AssertionError("another email was admin")
        directory = reset_memory_directory()
        directory.sign_up("coach@example.com", "password-one", "Coach")
        if directory.list_users("") is not None:
            raise AssertionError("the list opened without the server key")
        rows = directory.list_users("server-key")
        if rows is None or rows[0]["email"] != "coach@example.com":
            raise AssertionError(rows)
        if "password" in rows[0]:
            raise AssertionError("a password was listed")
    finally:
        _restore(saved)


def test_missing_config_notice_has_no_setting_names() -> None:
    saved = _saved()
    try:
        for name in ("RIO_SUPABASE_URL", "RIO_SUPABASE_ANON_KEY"):
            os.environ[name] = ""
        os.environ.pop("RIO_AUTH_BACKEND", None)
        if cloud_configured():
            raise AssertionError("blank settings were treated as ready")
        html = setup_notice_html()
        if "Accounts aren't set up yet" not in html:
            raise AssertionError(html)
        for banned in ("RIO_SUPABASE", "SERVICE_ROLE", ".env", "secrets.toml"):
            if banned in html:
                raise AssertionError(banned)
        os.environ["RIO_SUPABASE_URL"] = "https://example.supabase.co"
        os.environ["RIO_SUPABASE_ANON_KEY"] = "anon-placeholder"
        if not cloud_configured():
            raise AssertionError("the placeholder settings were ignored")
    finally:
        _restore(saved)


def test_migration_locks_each_table() -> None:
    sql = (ROOT / "supabase" / "migrations" / "001_accounts.sql").read_text(encoding="utf-8")
    for table in ("profiles", "goals", "plans", "results"):
        if f"alter table public.{table} enable row level security" not in sql:
            raise AssertionError(table)
        if f"grant select, insert, update, delete on table public.{table} to authenticated" not in sql:
            raise AssertionError(table)
    if sql.count("auth.uid()") < 8:
        raise AssertionError("a table is missing its own-row policy")


def test_google_url_uses_the_app_redirect() -> None:
    directory = reset_memory_directory()
    url = directory.google_url("https://riotraining.streamlit.app/")
    if "https://riotraining.streamlit.app/" not in url or "code=" not in url:
        raise AssertionError(url)
    code = url.split("code=", 1)[1].split("&", 1)[0]
    session = directory.exchange_code(code)
    if session["role"] != "athlete":
        raise AssertionError(session)


def main() -> None:
    test_sign_up_log_in_and_log_out()
    test_one_user_cannot_read_another()
    test_delete_removes_only_that_account()
    test_admin_gate_and_missing_list()
    test_missing_config_notice_has_no_setting_names()
    test_migration_locks_each_table()
    test_google_url_uses_the_app_redirect()
    print("cloud accounts ok")


if __name__ == "__main__":
    main()
