# test_account_polish.py — cookie lifetime, role lock, and a current season.

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.access import ENV_NAME, viewer_is_admin
from ui.cloud_session import (
    SESSION_SECONDS,
    cookie_max_age,
    pack_cookie,
    plan_has_sessions,
    unpack_cookie,
)
from ui.cloud_store import CloudAuthError, reset_memory_directory


def test_cookie_lasts_one_day_and_holds_no_server_key() -> None:
    issued = 1_700_000_000
    raw = pack_cookie("access-1", "refresh-1", "user-1", "ada@example.com", "Ada", issued)
    if "service_role" in raw or "sb_secret_" in raw or "service_key" in raw:
        raise AssertionError(raw)
    opened = unpack_cookie(raw, now=issued + 10)
    if opened is None or opened["access_token"] != "access-1" or opened["refresh_token"] != "refresh-1":
        raise AssertionError(opened)
    if unpack_cookie(raw, now=issued + SESSION_SECONDS) is not None:
        raise AssertionError("a day-old cookie still opened")
    if cookie_max_age(issued, now=issued + 60) != SESSION_SECONDS - 60:
        raise AssertionError("refresh extended the 24 hours")
    poisoned = raw.replace("access-1", "sb_secret_example")
    if unpack_cookie(poisoned, now=issued + 10) is not None:
        raise AssertionError("a server key was accepted")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    js = app[app.index("_SESSION_STORE_JS") : app.index("def _session_component(")]
    if "SameSite=Lax" not in js or "Secure" not in js or "rio_hosted" not in js:
        raise AssertionError("the cookie is not secure")
    if "Max-Age=0" not in js or "localStorage.removeItem" not in js:
        raise AssertionError("logout does not clear the cookie")


def test_admin_role_needs_the_server_key_and_the_client_cannot_set_it() -> None:
    saved = os.environ.get(ENV_NAME)
    try:
        os.environ[ENV_NAME] = "Coach@Example.com"
        directory = reset_memory_directory()
        coach = directory.sign_up("coach@example.com", "password-one", "Coach")
        athlete = directory.sign_up("ada@example.com", "password-two", "Ada")
        if coach["role"] != "athlete" or athlete["role"] != "athlete":
            raise AssertionError("a new profile was not an athlete")
        if not viewer_is_admin(coach["email"]) or viewer_is_admin(athlete["email"]):
            raise AssertionError("the admin email match changed")
        try:
            directory.set_role(coach["user_id"], "admin", "")
        except CloudAuthError:
            pass
        else:
            raise AssertionError("a role changed without the server key")
        directory.set_role(coach["user_id"], "admin", "server-key")
        directory.save_bundle(
            coach["access_token"],
            {"profile": {"display_name": "Coach", "role": "athlete"}},
        )
        kept = directory.load_bundle(coach["access_token"])
        if kept["profile"]["role"] != "admin" or kept["profile"]["display_name"] != "Coach":
            raise AssertionError(kept["profile"])
        refreshed = directory.refresh_session(coach["refresh_token"])
        if refreshed["user_id"] != coach["user_id"]:
            raise AssertionError(refreshed)
        other = directory.load_bundle(athlete["access_token"])
        if other["profile"]["role"] != "athlete":
            raise AssertionError(other["profile"])
    finally:
        if saved is None:
            os.environ.pop(ENV_NAME, None)
        else:
            os.environ[ENV_NAME] = saved


def test_a_plan_with_sessions_is_a_current_season() -> None:
    if plan_has_sessions({"sessions": []}) or plan_has_sessions({}) or plan_has_sessions(None):
        raise AssertionError("an empty plan counted as a season")
    if not plan_has_sessions({"sessions": [{"date": "2026-11-04"}]}):
        raise AssertionError("a plan with sessions was ignored")
    sql = (ROOT / "supabase" / "migrations" / "002_lock_roles.sql").read_text(encoding="utf-8")
    if "create or replace function public.lock_profile_role" not in sql:
        raise AssertionError("the role lock is not rerunnable")
    if "drop trigger if exists profiles_lock_role" not in sql:
        raise AssertionError("the trigger is not rerunnable")
    if "new.role := 'athlete'" not in sql or "new.role := old.role" not in sql:
        raise AssertionError(sql)
    if "revoke update on table public.profiles from authenticated" not in sql:
        raise AssertionError("authenticated can still update every column")
    if "grant update (email, display_name)" not in sql:
        raise AssertionError("name and email cannot be saved")
    if "current_time" in sql:
        raise AssertionError("a reserved column slipped into the role lock")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    login = app[app.index("def _render_login(") : app.index("\nst.set_page_config(")]
    if "cloud_configured()" not in login or "setup_notice_html()" not in login:
        raise AssertionError("the missing-config notice was removed")
    if "authenticate(" not in login:
        raise AssertionError("the local fallback was removed")


def main() -> None:
    test_cookie_lasts_one_day_and_holds_no_server_key()
    test_admin_role_needs_the_server_key_and_the_client_cannot_set_it()
    test_a_plan_with_sessions_is_a_current_season()
    print("account polish ok")


if __name__ == "__main__":
    main()
