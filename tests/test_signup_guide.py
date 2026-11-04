# test_signup_guide.py — sign-up messages, meter reps, intro, founder line.

"""Offline checks. No network, no keys, and no edits to older tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.cloud_config import HOSTED_APP, auth_redirect_base
from ui.cloud_store import (
    SIGNUP_CONFIRM,
    SIGNUP_DISABLED,
    SIGNUP_EXISTS,
    SIGNUP_FAILED,
    SIGNUP_PASSWORD,
    SIGNUP_PROFILE,
    SIGNUP_RATE,
    SIGNIN_RATE,
    CloudAuthError,
    SupabaseDirectory,
    intro_seen_value,
    reset_memory_directory,
    signin_error_message,
    signup_error_message,
    signup_outcome,
)
from ui.intro import STEPS, guide_html
from ui.settings import display_distance, display_training
from ui.startup import startup_html
from ui.theme import editorial_css


class _Auth:
    def __init__(self, response=None, error=None) -> None:
        self.response = response
        self.error = error
        self.payload = None

    def sign_up(self, payload):
        self.payload = payload
        if self.error is not None:
            raise self.error
        return self.response

    def sign_in_with_password(self, payload):
        self.payload = payload
        if self.error is not None:
            raise self.error
        return self.response


class _Query:
    def __init__(self, table, op: str, row=None) -> None:
        self.table = table
        self.op = op
        self.row = row

    def eq(self, *_args):
        return self

    def execute(self):
        if self.op == "select":
            return SimpleNamespace(data=list(self.table.rows))
        if self.op == "insert":
            if self.table.fail_insert:
                raise RuntimeError("new row blocked")
            self.table.inserts.append(dict(self.row))
            self.table.rows.append(dict(self.row))
            return SimpleNamespace(data=[dict(self.row)])
        if self.op == "update":
            if self.table.fail_update:
                raise RuntimeError("update blocked")
            self.table.updates.append(dict(self.row))
            if self.table.rows:
                self.table.rows[0].update(self.row)
            return SimpleNamespace(data=list(self.table.rows))
        return SimpleNamespace(data=[])


class _Table:
    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.inserts: list[dict] = []
        self.updates: list[dict] = []
        self.fail_insert = False
        self.fail_update = False

    def select(self, *_args):
        return _Query(self, "select")

    def insert(self, row):
        return _Query(self, "insert", row)

    def update(self, row):
        return _Query(self, "update", row)


class _Client:
    def __init__(self, auth: _Auth, table: _Table) -> None:
        self.auth = auth
        self.table_obj = table
        self.postgrest = SimpleNamespace(auth=lambda _token: None)

    def table(self, _name):
        return self.table_obj


class _Directory(SupabaseDirectory):
    def __init__(self, auth: _Auth, table: _Table) -> None:
        super().__init__("https://example.supabase.co", "anon-test", "")
        self._auth = auth
        self._table = table

    def _client(self, _key):
        return _Client(self._auth, self._table)


def _user(identities, *, user_id="user-1"):
    return SimpleNamespace(
        id=user_id,
        email="dad@example.com",
        identities=identities,
        user_metadata={"display_name": "Dad"},
    )


def _session_response():
    return SimpleNamespace(
        user=_user([{"id": "identity-1"}]),
        session=SimpleNamespace(access_token="access-token", refresh_token="refresh-token"),
    )


def test_confirm_email_no_session_is_a_clear_message() -> None:
    response = SimpleNamespace(user=_user([{"id": "identity-1"}]), session=None)
    try:
        signup_outcome(response, "Dad")
    except CloudAuthError as exc:
        if str(exc) != SIGNUP_CONFIRM:
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a missing session opened an account")
    missing = {"user": {"id": "user-2", "email": "dad@example.com"}, "session": None}
    try:
        signup_outcome(missing, "Dad")
    except CloudAuthError as exc:
        if str(exc) != SIGNUP_CONFIRM:
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a dict with no session opened an account")


def test_duplicate_rate_limit_and_short_password() -> None:
    empty = SimpleNamespace(user=_user([]), session=None)
    try:
        signup_outcome(empty, "Dad")
    except CloudAuthError as exc:
        if str(exc) != SIGNUP_EXISTS:
            raise AssertionError(str(exc))
    else:
        raise AssertionError("an empty identity list was treated as a new account")
    rate = RuntimeError("Email rate limit exceeded")
    if signup_error_message(rate) != SIGNUP_RATE:
        raise AssertionError(signup_error_message(rate))
    limited = SimpleNamespace(status=429, message="too many requests")
    if signup_error_message(limited) != SIGNUP_RATE:
        raise AssertionError(signup_error_message(limited))
    taken = RuntimeError("User already registered")
    if signup_error_message(taken) != SIGNUP_EXISTS:
        raise AssertionError(signup_error_message(taken))
    weak = RuntimeError("Password should be at least 6 characters")
    if signup_error_message(weak) != SIGNUP_PASSWORD:
        raise AssertionError(signup_error_message(weak))
    closed = RuntimeError("Signups not allowed for this instance")
    if signup_error_message(closed) != SIGNUP_DISABLED:
        raise AssertionError(signup_error_message(closed))
    if signup_error_message(RuntimeError("database unavailable")) != SIGNUP_FAILED:
        raise AssertionError("an unknown failure was relabeled")
    unconfirmed = RuntimeError("Email not confirmed")
    if signin_error_message(unconfirmed) != SIGNUP_CONFIRM:
        raise AssertionError(signin_error_message(unconfirmed))
    if signin_error_message(SimpleNamespace(status=429, message="rate limit")) != SIGNIN_RATE:
        raise AssertionError("sign-in rate limit was hidden")


def test_sign_up_uses_the_redirect_and_saves_a_profile_without_role() -> None:
    saved = os.environ.get("RIO_APP_URL")
    os.environ["RIO_APP_URL"] = "https://riotraining.streamlit.app"
    try:
        auth = _Auth(_session_response())
        table = _Table()
        directory = _Directory(auth, table)
        session = directory.sign_up("Dad@Example.com", "long-password", "Dad")
    finally:
        if saved is None:
            os.environ.pop("RIO_APP_URL", None)
        else:
            os.environ["RIO_APP_URL"] = saved
    if session["email"] != "dad@example.com" or session["access_token"] != "access-token":
        raise AssertionError(session)
    redirect = auth.payload["options"]["email_redirect_to"]
    if redirect != "https://riotraining.streamlit.app/":
        raise AssertionError(redirect)
    if auth.payload["options"]["data"]["display_name"] != "Dad":
        raise AssertionError(auth.payload)
    if not table.inserts or "role" in table.inserts[0]:
        raise AssertionError(table.inserts)
    if table.inserts[0]["display_name"] != "Dad" or table.inserts[0]["id"] != "user-1":
        raise AssertionError(table.inserts)
    try:
        directory.sign_up("dad@example.com", "short", "Dad")
    except CloudAuthError as exc:
        if str(exc) != SIGNUP_PASSWORD:
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a short password reached the server")
    try:
        directory.sign_up("not-an-email", "long-password", "Dad")
    except CloudAuthError as exc:
        if "email" not in str(exc).lower():
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a bad email was accepted")
    try:
        directory.sign_up("dad@example.com", "long-password", "123")
    except CloudAuthError as exc:
        if "name" not in str(exc).lower():
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a bad name was called an email error")


def test_profile_failure_and_sign_in_are_visible() -> None:
    auth = _Auth(_session_response())
    table = _Table()
    table.fail_insert = True
    table.fail_update = True
    directory = _Directory(auth, table)
    try:
        directory.sign_up("dad@example.com", "long-password", "Dad")
    except CloudAuthError as exc:
        if str(exc) != SIGNUP_PROFILE:
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a blocked profile was silent")
    auth.error = RuntimeError("Email rate limit exceeded")
    try:
        directory.sign_up("dad@example.com", "long-password", "Dad")
    except CloudAuthError as exc:
        if str(exc) != SIGNUP_RATE:
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a rate limit was swallowed")
    auth.error = None
    auth.response = SimpleNamespace(user=_user([]), session=None)
    try:
        directory.sign_up("dad@example.com", "long-password", "Dad")
    except CloudAuthError as exc:
        if str(exc) != SIGNUP_EXISTS:
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a duplicate sign-up opened a session")
    auth.response = _session_response()
    table.fail_insert = False
    table.fail_update = False
    table.rows.clear()
    signed = directory.sign_in("dad@example.com", "long-password")
    if signed["display_name"] != "Dad":
        raise AssertionError(signed)
    if not table.inserts:
        raise AssertionError("sign-in did not create the profile")
    auth.error = RuntimeError("Email not confirmed")
    try:
        directory.sign_in("dad@example.com", "long-password")
    except CloudAuthError as exc:
        if str(exc) != SIGNUP_CONFIRM:
            raise AssertionError(str(exc))
    else:
        raise AssertionError("an unconfirmed sign-in looked like a bad password")


def test_auth_links_use_the_hosted_site_when_the_url_is_unset() -> None:
    saved = os.environ.get("RIO_APP_URL")
    os.environ.pop("RIO_APP_URL", None)
    try:
        if auth_redirect_base() != HOSTED_APP:
            raise AssertionError(auth_redirect_base())
    finally:
        if saved is not None:
            os.environ["RIO_APP_URL"] = saved
    ui = (ROOT / "ui" / "cloud_ui.py").read_text(encoding="utf-8")
    signup = ui[ui.index("def _render_sign_up(") : ui.index("def _render_forgot(")]
    if "ACCOUNTS_UNAVAILABLE" not in ui and "Accounts aren't set up yet" not in signup:
        if "_directory_or_notice()" not in signup:
            raise AssertionError("a missing directory still fails silently")
    if "SIGNUP_CONFIRM" not in signup:
        raise AssertionError("confirm email does not return to log in")


def test_rep_distances_stay_in_meters() -> None:
    reps = "8 × 150 m at or faster than goal 800 pace, long rest"
    fast = "10 × 60 m fast, rolling start, full rest"
    easy = "5 km easy, Zone 2, talkable the whole way"
    if display_training(reps, "miles") != reps or display_training(reps, "km") != reps:
        raise AssertionError(display_training(reps, "miles"))
    if display_training(fast, "miles") != fast:
        raise AssertionError(display_training(fast, "miles"))
    if display_training(easy, "miles") != "3.1 mi easy, Zone 2, talkable the whole way":
        raise AssertionError(display_training(easy, "miles"))
    if display_training(easy, "km") != easy:
        raise AssertionError(display_training(easy, "km"))
    ladder = "5 steps: 150, 200, 300, 200, 150 m"
    if display_training(ladder, "miles") != ladder:
        raise AssertionError(display_training(ladder, "miles"))
    if display_distance("10 × 60 m fast", "miles") != "10 × 0.04 mi fast":
        raise AssertionError("the older distance helper changed")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    copy = app[app.index("def _copy(") : app.index("def _id_html(")]
    if "display_training(" not in copy:
        raise AssertionError("workout copy still converts reps")
    stage = app[app.index("def _track_stage(") : app.index("def _track_hero(")]
    if "recipe_continuous" not in stage:
        raise AssertionError("a rep fact still follows the mile toggle")


def test_intro_flag_and_guide_copy() -> None:
    if intro_seen_value({"user_metadata": {}}) is not None:
        raise AssertionError("a missing flag looked stored")
    if intro_seen_value({"user_metadata": {"intro_seen": True}}) is not True:
        raise AssertionError("a stored flag was dropped")
    if intro_seen_value({"user_metadata": {"intro_seen": False}}) is not False:
        raise AssertionError("reopen was treated as seen")
    directory = reset_memory_directory()
    ada = directory.sign_up("ada@example.com", "password-one", "Ada")
    beau = directory.sign_up("beau@example.com", "password-two", "Beau")
    if "intro_seen" in directory.load_bundle(ada["access_token"])["profile"]:
        raise AssertionError("a new account already had the flag")
    directory.save_intro_seen(ada["access_token"], True)
    kept = directory.load_bundle(ada["access_token"])["profile"]
    other = directory.load_bundle(beau["access_token"])["profile"]
    if kept.get("intro_seen") is not True:
        raise AssertionError(kept)
    if "intro_seen" in other:
        raise AssertionError(other)
    directory.save_intro_seen(ada["access_token"], False)
    if directory.load_bundle(ada["access_token"])["profile"].get("intro_seen") is not False:
        raise AssertionError("the guide could not be reopened")
    html = guide_html()
    for title, body in STEPS:
        if title not in html or body not in html:
            raise AssertionError((title, body))
    if "Generate Season Plan" not in html or "Strava" not in html or "Plan" not in html:
        raise AssertionError(html)
    source = (ROOT / "ui" / "intro.py").read_text(encoding="utf-8")
    if 'st.button("Skip"' not in source or 'st.button("Done"' not in source:
        raise AssertionError("Skip or Done is missing")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    if 'st.button("Show intro guide"' not in app or "save_intro_seen" not in app:
        raise AssertionError("Settings cannot reopen the guide")


def test_founder_line_and_compact_heroes() -> None:
    html = startup_html()
    if "Chase Rose, Founder" not in html:
        raise AssertionError("the founder line is missing")
    if "CEO" in html or "Founder and CEO" in (ROOT / "ui" / "startup.py").read_text(encoding="utf-8"):
        raise AssertionError("CEO is still on the startup page")
    if "Most plans tell you what to run" not in html:
        raise AssertionError("the quote changed")
    css = editorial_css()
    if "140px" in css or "4.5rem 5vw 3.6rem" in css or "78vh" in css:
        raise AssertionError("the page hero is still full height")
    if "clamp(1.7rem, 3.1vw, 2.35rem)" not in css:
        raise AssertionError("the compact title size is missing")


def main() -> None:
    test_confirm_email_no_session_is_a_clear_message()
    test_duplicate_rate_limit_and_short_password()
    test_sign_up_uses_the_redirect_and_saves_a_profile_without_role()
    test_profile_failure_and_sign_in_are_visible()
    test_auth_links_use_the_hosted_site_when_the_url_is_unset()
    test_rep_distances_stay_in_meters()
    test_intro_flag_and_guide_copy()
    test_founder_line_and_compact_heroes()
    print("signup guide ok")


if __name__ == "__main__":
    main()
