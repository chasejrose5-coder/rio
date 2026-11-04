# test_security_fixes.py — per-request auth, admin identity, and the hosted cookie.

"""Offline. No network and no project secrets."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.access import ENV_NAME, viewer_is_admin
from ui.accounts import _legacy_seal, _open_seal, _seal
from ui.cloud_session import hosted_hash, hosted_sid, pack_cookie, unpack_cookie
from ui.cloud_store import (
    SIGNUP_CONFIRM,
    CloudAuthError,
    SupabaseDirectory,
    reset_memory_directory,
)
from ui.strava_ui import connected_as_html


def test_token_user_uses_the_given_token() -> None:
    """Two tokens interleaved still resolve to two users."""
    directory = SupabaseDirectory("https://example.supabase.co", "anon", "svc")
    clients = []

    class _Auth:
        def __init__(self) -> None:
            self.session = None

        def get_user(self, jwt=None):
            if jwt is None:
                raise AssertionError("get_user asked the client session")
            self.session = "last"
            return SimpleNamespace(user=SimpleNamespace(id="id-" + jwt))

    class _Client:
        def __init__(self) -> None:
            self.auth = _Auth()
            self.postgrest = SimpleNamespace(auth=lambda _token: None)

    def _new(_key):
        client = _Client()
        clients.append(client)
        return client

    directory._client = _new
    first = directory._user_client("token-a")
    second = directory._user_client("token-b")
    if directory._token_user(first, "token-a") != "id-token-a":
        raise AssertionError("token a was not used")
    if directory._token_user(second, "token-b") != "id-token-b":
        raise AssertionError("token b was not used")
    if directory._token_user(first, "token-a") != "id-token-a":
        raise AssertionError("token a changed after token b")
    if first is second or len(clients) != 2:
        raise AssertionError("one client was reused")


def test_each_call_builds_a_fresh_client() -> None:
    import supabase

    calls = []
    original = supabase.create_client

    def _fake(url, key, options=None):
        calls.append((url, key, options))
        return object()

    supabase.create_client = _fake
    try:
        directory = SupabaseDirectory("https://example.supabase.co", "anon", "svc")
        directory._client("anon")
        directory._client("anon")
    finally:
        supabase.create_client = original
    if len(calls) != 2 or calls[0][2] is calls[1][2]:
        raise AssertionError("the anon client was cached")
    if calls[0][2].persist_session or calls[0][2].auto_refresh_token:
        raise AssertionError("session persistence stayed on")


def test_sign_out_revokes_only_this_token() -> None:
    seen = {}

    class _Admin:
        def sign_out(self, jwt, scope="global"):
            seen["jwt"] = jwt
            seen["scope"] = scope

    class _Client:
        def __init__(self) -> None:
            self.auth = SimpleNamespace(admin=_Admin())

    directory = SupabaseDirectory("https://example.supabase.co", "anon", "svc")
    directory._client = lambda _key: _Client()
    directory.sign_out("token-a")
    directory.sign_out("")
    if seen != {"jwt": "token-a", "scope": "local"}:
        raise AssertionError(seen)


def test_admin_uses_the_confirmed_auth_email() -> None:
    saved = os.environ.get(ENV_NAME)
    os.environ[ENV_NAME] = "owner@example.com"
    try:
        directory = SupabaseDirectory("https://example.supabase.co", "anon", "svc")
        users = {
            "good": {
                "id": "user-owner",
                "email": "owner@example.com",
                "email_confirmed_at": "2026-01-01T00:00:00Z",
            },
            "poison": {
                "id": "user-runner",
                "email": "runner@example.com",
                "email_confirmed_at": "2026-01-01T00:00:00Z",
            },
            "open": {
                "id": "user-open",
                "email": "owner@example.com",
                "email_confirmed_at": None,
            },
        }
        directory._auth_user = lambda token: users.get(token)
        good = directory.verified_user("good")
        poison = directory.verified_user("poison")
        open_email = directory.verified_user("open")
        if not good or not viewer_is_admin(good["email"]):
            raise AssertionError(good)
        if poison is None or viewer_is_admin(poison["email"]):
            raise AssertionError("a different auth email was admin")
        if open_email is None or open_email["email_confirmed_at"]:
            raise AssertionError(open_email)
        confirmed = open_email["email"] if open_email.get("email_confirmed_at") else None
        if viewer_is_admin(confirmed):
            raise AssertionError("an unconfirmed auth email was admin")
    finally:
        if saved is None:
            os.environ.pop(ENV_NAME, None)
        else:
            os.environ[ENV_NAME] = saved


def test_profile_update_does_not_write_email() -> None:
    from ui.cloud_store import _touch_profile

    class _Query:
        def __init__(self, table, row) -> None:
            self.table = table
            self.row = row

        def eq(self, *_args):
            return self

        def execute(self):
            self.table.updates.append(dict(self.row))
            return SimpleNamespace(data=[])

    class _Table:
        def __init__(self) -> None:
            self.updates = []

        def update(self, row):
            return _Query(self, row)

    table = _Table()
    _touch_profile(table, "user-1", "changed@example.com", "Ada")
    if table.updates != [{"display_name": "Ada"}]:
        raise AssertionError(table.updates)
    _touch_profile(table, "user-1", "changed@example.com", "")
    if len(table.updates) != 1:
        raise AssertionError("an empty name still wrote email")


def test_hosted_cookie_holds_no_token() -> None:
    directory = reset_memory_directory()
    session = directory.sign_up("ada@example.com", "long-password", "Ada")
    issued = int(time.time())
    sid = directory.save_hosted_session(
        {
            "access_token": session["access_token"],
            "refresh_token": session["refresh_token"],
            "user_id": session["user_id"],
            "email": session["email"],
            "display_name": "Ada",
            "issued_at": issued,
        }
    )
    if not hosted_sid(sid) or session["access_token"] in sid or session["refresh_token"] in sid:
        raise AssertionError("the cookie held a token")
    if sid in directory.hosted or hosted_hash(sid) not in directory.hosted:
        raise AssertionError("the raw id was stored")
    loaded = directory.load_hosted_session(sid)
    if loaded is None or loaded["access_token"] != session["access_token"]:
        raise AssertionError(loaded)
    directory.sign_out(session["access_token"])
    if directory.load_hosted_session(sid) is not None:
        raise AssertionError("sign-out left the server session")
    legacy = pack_cookie(
        session["access_token"],
        session["refresh_token"],
        session["user_id"],
        session["email"],
        "Ada",
        issued,
    )
    opened = unpack_cookie(legacy, now=issued + 10)
    if opened is None or opened["access_token"] != session["access_token"]:
        raise AssertionError("a legacy cookie no longer opens")


def test_local_seal_is_fernet_and_old_files_open() -> None:
    key = bytes.fromhex("ab" * 32)
    sealed = _seal(b"season", key)
    if not sealed.startswith("f2.") or _open_seal(sealed, key) != b"season":
        raise AssertionError("fernet seal did not round-trip")
    if _open_seal(sealed, bytes.fromhex("cd" * 32)) is not None:
        raise AssertionError("another key opened the seal")
    old = _legacy_seal(b"season", key)
    if old.startswith("f2.") or _open_seal(old, key) != b"season":
        raise AssertionError("an old seal no longer opens")


def test_strava_name_is_escaped() -> None:
    html = connected_as_html('<img src=x onerror="alert(1)">')
    if "<img" in html or "onerror" not in html:
        raise AssertionError(html)
    if "&lt;img" not in html:
        raise AssertionError(html)


def test_migrations_and_pin_and_confirm_copy() -> None:
    lock = (ROOT / "supabase" / "migrations" / "005_lock_profile_email.sql").read_text(encoding="utf-8")
    if "revoke update on table public.profiles from authenticated" not in lock:
        raise AssertionError("email update was not revoked")
    if "grant update (display_name)" not in lock or "new.email := old.email" not in lock:
        raise AssertionError(lock)
    if "grant update (email" in lock:
        raise AssertionError("email is still granted")
    sessions = (ROOT / "supabase" / "migrations" / "006_app_sessions.sql").read_text(encoding="utf-8")
    if "enable row level security" not in sessions:
        raise AssertionError("app_sessions is missing rls")
    if "to authenticated" in sessions and "revoke all on table public.app_sessions from authenticated" not in sessions:
        raise AssertionError("signed-in users can read session tokens")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    if "supabase==2.34.0" not in requirements or "cryptography==44.0.2" not in requirements:
        raise AssertionError(requirements)
    readme = (ROOT / "supabase" / "migrations" / "README.md").read_text(encoding="utf-8")
    if 'Turn off "Confirm email"' in readme or 'Keep "Confirm email" ON' not in readme:
        raise AssertionError("confirm email instructions were not updated")
    ui = (ROOT / "ui" / "cloud_ui.py").read_text(encoding="utf-8")
    if "def _render_confirm(" not in ui or "verified_user(" not in ui:
        raise AssertionError("confirm screen or auth identity check is missing")
    signup = ui[ui.index("def _render_sign_up(") : ui.index("def _render_forgot(")]
    if "SIGNUP_CONFIRM" not in signup:
        raise AssertionError("confirm email does not return to log in")
    if SIGNUP_CONFIRM != "Check your email to confirm your account, then log in.":
        raise AssertionError(SIGNUP_CONFIRM)
    store = (ROOT / "ui" / "strava_store.py").read_text(encoding="utf-8")
    writer = store[store.rindex("def put_activities(") : store.rindex("def get_activities(")]
    if "on_conflict" not in writer or "500" not in writer or "_owner_client" not in writer:
        raise AssertionError("activities are still written one row at a time with the server key")


def main() -> None:
    test_token_user_uses_the_given_token()
    test_each_call_builds_a_fresh_client()
    test_sign_out_revokes_only_this_token()
    test_admin_uses_the_confirmed_auth_email()
    test_profile_update_does_not_write_email()
    test_hosted_cookie_holds_no_token()
    test_local_seal_is_fernet_and_old_files_open()
    test_strava_name_is_escaped()
    test_migrations_and_pin_and_confirm_copy()
    print("security fixes ok")


if __name__ == "__main__":
    main()
