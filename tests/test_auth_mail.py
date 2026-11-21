# test_auth_mail.py — reset and confirmation mail open the app that sent them.

"""Streamlit stays on RIO_APP_URL. The API uses RIO_FRONTEND_ORIGIN.

No network. The local account file still sends no mail.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.account_flow import confirm_redirect_url, reset_redirect_url
from api.main import create_app
from ui.cloud_config import auth_redirect_base
from ui.cloud_store import (
    CONFIRM_EMAIL,
    CONFIRM_SIGNUP,
    MAIL_RATE,
    CloudAuthError,
    MemoryDirectory,
    SupabaseDirectory,
)

NEXT = "https://next.example.test"
STREAMLIT = "https://riotraining.streamlit.app"


class _Auth:
    def __init__(self) -> None:
        self.payload = None
        self.reset = None
        self.otp = None
        self.session_args = None
        self.updated = None
        self.update_options = None
        self.resent = None
        self.user_jwt = None
        self.fail = None

    def sign_up(self, payload):
        self.payload = payload
        user = SimpleNamespace(
            id="user-1",
            email="dad@example.com",
            identities=[{"id": "identity-1"}],
            user_metadata={"display_name": "Dad"},
        )
        session = SimpleNamespace(access_token="access-token", refresh_token="refresh-token")
        return SimpleNamespace(user=user, session=session)

    def reset_password_for_email(self, email, options):
        self.reset = (email, dict(options))
        if self.fail == "missing":
            raise RuntimeError("User not found")
        if self.fail == "rate":
            error = RuntimeError("Email rate limit exceeded")
            error.status = 429
            raise error

    def resend(self, body):
        self.resent = dict(body)
        if self.fail == "missing":
            raise RuntimeError("User not found")
        if self.fail == "rate":
            error = RuntimeError("over_email_send_rate_limit")
            error.status = 429
            raise error
        if self.fail == "confirmed":
            raise RuntimeError("Email address already confirmed")

    def verify_otp(self, body):
        self.otp = dict(body)
        if body.get("token_hash") == "expired":
            raise RuntimeError("Email link is invalid or has expired")
        if body.get("token_hash") == "limited":
            error = RuntimeError("over_request_rate_limit")
            error.status = 429
            raise error
        user = SimpleNamespace(
            id="user-1",
            email="dad@example.com",
            email_confirmed_at="2026-01-01T00:00:00Z",
        )
        return SimpleNamespace(
            user=user,
            session=SimpleNamespace(access_token="otp-access", refresh_token="otp-refresh"),
        )

    def set_session(self, access, refresh):
        self.session_args = (access, refresh)

    def update_user(self, body, options=None):
        self.updated = dict(body)
        self.update_options = dict(options or {})

    def get_user(self, jwt=None):
        self.user_jwt = jwt
        if jwt == "bad":
            raise RuntimeError("invalid token")
        return SimpleNamespace(
            user=SimpleNamespace(
                id="user-1",
                email="dad@example.com",
                email_confirmed_at="2026-01-01T00:00:00Z",
            )
        )


class _Query:
    def eq(self, *_args):
        return self

    def execute(self):
        return SimpleNamespace(data=[])


class _Table:
    def select(self, *_args):
        return _Query()

    def insert(self, _row):
        return _Query()

    def update(self, _row):
        return _Query()


class _Client:
    def __init__(self, auth: _Auth) -> None:
        self.auth = auth
        self.postgrest = SimpleNamespace(auth=lambda _token: None)

    def table(self, _name):
        return _Table()


class _Directory(SupabaseDirectory):
    def __init__(self, auth: _Auth) -> None:
        super().__init__("https://example.supabase.co", "anon-test", "")
        self._auth = auth

    def _client(self, _key):
        return _Client(self._auth)


def _keep(name: str, value: str | None):
    previous = os.environ.get(name)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    return previous


def _restore(name: str, previous: str | None) -> None:
    if previous is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous


def test_redirect_urls_are_the_next_origin_with_no_hardcoded_host() -> None:
    if reset_redirect_url(NEXT) != NEXT + "/update-password":
        raise AssertionError(reset_redirect_url(NEXT))
    if confirm_redirect_url(NEXT + "/") != NEXT + "/confirm":
        raise AssertionError(confirm_redirect_url(NEXT))
    if "streamlit" in reset_redirect_url(NEXT) or "localhost" in confirm_redirect_url(NEXT):
        raise AssertionError("the mail URL baked in a host")
    if "riorunning.com" in reset_redirect_url(NEXT):
        raise AssertionError(reset_redirect_url(NEXT))


def test_public_hosts_open_the_live_site() -> None:
    live = "https://www.riorunning.com"
    if confirm_redirect_url(live) != live + "/confirm":
        raise AssertionError(confirm_redirect_url(live))
    if reset_redirect_url(live) != live + "/update-password":
        raise AssertionError(reset_redirect_url(live))
    for old in (
        "https://riorunning.com/",
        "http://www.riorunning.com",
        "https://rio-one-mocha.vercel.app",
        "https://rio-rio-44fa.vercel.app/",
    ):
        if reset_redirect_url(old) != live + "/update-password":
            raise AssertionError((old, reset_redirect_url(old)))
        if confirm_redirect_url(old) != live + "/confirm":
            raise AssertionError((old, confirm_redirect_url(old)))
    if reset_redirect_url("http://localhost:3000") != "http://localhost:3000/update-password":
        raise AssertionError(reset_redirect_url("http://localhost:3000"))


def test_streamlit_mail_stays_on_its_own_origin_when_the_frontend_is_set() -> None:
    saved_app = _keep("RIO_APP_URL", STREAMLIT)
    saved_front = _keep("RIO_FRONTEND_ORIGIN", NEXT)
    try:
        if auth_redirect_base() != STREAMLIT:
            raise AssertionError(auth_redirect_base())
        auth = _Auth()
        directory = _Directory(auth)
        directory.sign_up("Dad@Example.com", "long-password", "Dad")
        directory.request_reset("dad@example.com")
    finally:
        _restore("RIO_APP_URL", saved_app)
        _restore("RIO_FRONTEND_ORIGIN", saved_front)
    redirect = auth.payload["options"]["email_redirect_to"]
    if redirect != STREAMLIT + "/":
        raise AssertionError(redirect)
    if auth.reset != ("dad@example.com", {"redirect_to": STREAMLIT + "/?reset=password"}):
        raise AssertionError(auth.reset)
    ui = (ROOT / "ui" / "cloud_ui.py").read_text(encoding="utf-8")
    forgot = ui[ui.index("def _render_forgot(") : ui.index("def _render_reset(")]
    signup = ui[ui.index("def _render_sign_up(") : ui.index("def _render_confirm(")]
    if "request_reset(email)" not in forgot or "redirect_to" in forgot:
        raise AssertionError("Streamlit forgot password no longer sends its own link")
    if "sign_up(email, password, name)" not in signup or "email_redirect_to" in signup:
        raise AssertionError("Streamlit sign-up no longer sends its own link")


def test_an_explicit_redirect_is_what_the_hosted_client_sends() -> None:
    auth = _Auth()
    directory = _Directory(auth)
    directory.sign_up(
        "dad@example.com",
        "long-password",
        "Dad",
        email_redirect_to=NEXT + "/",
    )
    directory.request_reset("dad@example.com", redirect_to=NEXT + "/reset-password")
    if auth.payload["options"]["email_redirect_to"] != NEXT + "/":
        raise AssertionError(auth.payload)
    if auth.reset[1]["redirect_to"] != NEXT + "/reset-password":
        raise AssertionError(auth.reset)
    directory.reset_password("hashed-token", "another-horse")
    if auth.otp != {"token_hash": "hashed-token", "type": "recovery"}:
        raise AssertionError(auth.otp)
    if auth.session_args != ("otp-access", "otp-refresh") or auth.updated != {"password": "another-horse"}:
        raise AssertionError((auth.session_args, auth.updated))
    auth.session_args = None
    auth.updated = None
    directory.reset_password(
        "",
        "another-horse",
        access_token="frag-access",
        refresh_token="frag-refresh",
        recovery_type="recovery",
    )
    if auth.session_args != ("frag-access", "frag-refresh"):
        raise AssertionError(auth.session_args)
    try:
        directory.reset_password(
            "",
            "another-horse",
            access_token="frag-access",
            refresh_token="frag-refresh",
            recovery_type="signup",
        )
    except CloudAuthError as exc:
        if str(exc) != "That reset link is no longer valid.":
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a signup fragment reset a password")


def test_api_mail_uses_the_frontend_origin_and_the_local_file_sends_none(tmp_path) -> None:
    directory = MemoryDirectory()
    client = TestClient(create_app(directory=directory, frontend_origin=NEXT, load_env=False))
    created = client.post(
        "/auth/sign-up",
        json={"email": "Ada@Example.com", "password": "correct-horse", "name": "Ada"},
    )
    if created.status_code != 200 or directory.email_redirect_to != NEXT + "/confirm":
        raise AssertionError((created.text, directory.email_redirect_to))
    missing = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    known = client.post("/auth/forgot-password", json={"email": "ada@example.com"})
    if missing.status_code != 200 or known.status_code != 200 or missing.json() != known.json():
        raise AssertionError((missing.text, known.text))
    if "token" in known.json() or directory.reset_redirect_to != NEXT + "/update-password":
        raise AssertionError((known.json(), directory.reset_redirect_to))
    opened = directory.sign_in("ada@example.com", "correct-horse")
    saved = client.post(
        "/auth/reset-password",
        json={
            "token": "",
            "password": "another-horse",
            "access_token": opened["access_token"],
            "refresh_token": opened["refresh_token"],
            "type": "recovery",
        },
    )
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    if directory.sign_in("ada@example.com", "another-horse")["email"] != "ada@example.com":
        raise AssertionError("the hash session did not set the password")
    local = TestClient(
        create_app(directory=None, accounts=tmp_path / "accounts.json", frontend_origin=NEXT, load_env=False)
    )
    signed = local.post(
        "/auth/sign-up",
        json={"email": "local@example.com", "password": "correct-horse", "name": "Local"},
    )
    if signed.status_code != 200 or signed.json().get("kind") != "local":
        raise AssertionError(signed.text)
    if local.post("/auth/forgot-password", json={"email": "local@example.com"}).status_code != 400:
        raise AssertionError("the local file sent reset mail")


def test_a_missing_address_matches_a_sent_mail_and_a_rate_limit_does_not() -> None:
    auth = _Auth()
    directory = _Directory(auth)
    auth.fail = "missing"
    if directory.request_reset("nobody@example.com", redirect_to=NEXT + "/reset-password") != "":
        raise AssertionError("a missing reset address was told apart")
    if directory.resend_signup("nobody@example.com", redirect_to=NEXT + "/confirm") != "":
        raise AssertionError("a missing confirmation address was told apart")
    auth.fail = "confirmed"
    if directory.resend_signup("dad@example.com", redirect_to=NEXT + "/confirm") != "":
        raise AssertionError("an already confirmed address was told apart")
    auth.fail = "rate"
    try:
        directory.request_reset("dad@example.com", redirect_to=NEXT + "/reset-password")
    except CloudAuthError as exc:
        if str(exc) != MAIL_RATE:
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a reset rate limit looked like a sent mail")
    try:
        directory.resend_signup("dad@example.com", redirect_to=NEXT + "/confirm")
    except CloudAuthError as exc:
        if str(exc) != MAIL_RATE:
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a confirmation rate limit looked like a sent mail")
    if auth.resent["options"]["email_redirect_to"] != NEXT + "/confirm":
        raise AssertionError(auth.resent)


def test_confirm_link_verifies_signup_and_email_change_and_rejects_a_bad_token() -> None:
    auth = _Auth()
    directory = _Directory(auth)
    saved = directory.confirm_link("hashed-token", link_type="signup")
    if saved["message"] != CONFIRM_SIGNUP or auth.otp != {"token_hash": "hashed-token", "type": "signup"}:
        raise AssertionError((saved, auth.otp))
    changed = directory.confirm_link(
        "",
        access_token="frag-access",
        refresh_token="frag-refresh",
        link_type="email_change",
    )
    if changed["kind"] != "email_change" or changed["message"] != CONFIRM_EMAIL:
        raise AssertionError(changed)
    if changed["email"] != "dad@example.com" or auth.user_jwt != "frag-access":
        raise AssertionError((changed, auth.user_jwt))
    try:
        directory.confirm_link("expired", link_type="signup")
    except CloudAuthError as exc:
        if str(exc) != "That confirmation link is no longer valid.":
            raise AssertionError(str(exc))
    else:
        raise AssertionError("an expired link confirmed an address")
    try:
        directory.confirm_link("limited", link_type="email")
    except CloudAuthError as exc:
        if str(exc) != MAIL_RATE:
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a confirm rate limit looked like a bad link")
    try:
        directory.confirm_link("hashed-token", link_type="recovery")
    except CloudAuthError as exc:
        if "no longer valid" not in str(exc):
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a recovery link was confirmed as signup")


def test_hosted_email_change_keeps_the_current_address_until_the_link() -> None:
    auth = _Auth()
    directory = _Directory(auth)
    directory.verified_user = lambda _token: {
        "id": "user-1",
        "email": "dad@example.com",
        "email_confirmed_at": "yes",
    }

    def _sign_in(email, _password):
        return {"email": email, "access_token": "access"}

    directory.sign_in = _sign_in
    updated = directory.change_email(
        "access-token",
        "long-password",
        "New@Example.com",
        redirect_to=NEXT + "/confirm",
    )
    if updated != "dad@example.com":
        raise AssertionError(updated)
    if auth.updated != {"email": "new@example.com"}:
        raise AssertionError(auth.updated)
    if auth.update_options != {"email_redirect_to": NEXT + "/confirm"}:
        raise AssertionError(auth.update_options)


def test_api_resend_and_confirm_hide_a_missing_address(tmp_path) -> None:
    directory = MemoryDirectory()
    client = TestClient(
        create_app(directory=directory, frontend_origin=NEXT, load_env=False),
        base_url="https://testserver",
    )
    created = client.post(
        "/auth/sign-up",
        json={"email": "Ada@Example.com", "password": "correct-horse", "name": "Ada"},
    )
    if created.status_code != 200:
        raise AssertionError(created.text)
    missing = client.post("/auth/resend-confirmation", json={"email": "nobody@example.com"})
    known = client.post("/auth/resend-confirmation", json={"email": "ada@example.com"})
    if missing.status_code != 200 or known.status_code != 200 or missing.json() != known.json():
        raise AssertionError((missing.text, known.text))
    if "nobody" in missing.text or "ada@" in known.text:
        raise AssertionError("the resend sentence named an address")
    if directory.confirm_redirect_to != NEXT + "/confirm" or not directory.last_confirm_token:
        raise AssertionError(directory.confirm_redirect_to)
    bad = client.post("/auth/confirm", json={"token": "nope", "type": "signup"})
    if bad.status_code != 400 or "no longer valid" not in bad.text:
        raise AssertionError(bad.text)
    good = client.post(
        "/auth/confirm",
        json={"token": directory.last_confirm_token, "type": "signup"},
    )
    if good.status_code != 200 or good.json().get("kind") != "signup" or good.json().get("refreshed") is not False:
        raise AssertionError(good.text)
    directory.confirms["change-token"] = {
        "type": "email_change",
        "email": "ada@example.com",
        "pending": "ada.new@example.com",
    }
    moved = client.post("/auth/confirm", json={"token": "change-token", "type": "email_change"})
    if moved.status_code != 200 or moved.json().get("refreshed") is not True:
        raise AssertionError(moved.text)
    if client.get("/auth/me").json().get("email") != "ada.new@example.com":
        raise AssertionError(client.get("/auth/me").text)
    raised = MemoryDirectory()

    def _missing(email, *, redirect_to=None):
        raise CloudAuthError("User not found")

    raised.request_reset = _missing
    raised.resend_signup = _missing
    loud = TestClient(create_app(directory=raised, frontend_origin=NEXT, load_env=False))
    forgot = loud.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    again = loud.post("/auth/resend-confirmation", json={"email": "nobody@example.com"})
    if forgot.status_code != 200 or "not found" in forgot.text.lower() or "nobody" in forgot.text:
        raise AssertionError(forgot.text)
    if again.status_code != 200 or again.json() != known.json():
        raise AssertionError(again.text)
    limited = MemoryDirectory()

    def _rate(email, *, redirect_to=None):
        raise CloudAuthError(MAIL_RATE)

    limited.request_reset = _rate
    limited.resend_signup = _rate
    waiting = TestClient(create_app(directory=limited, frontend_origin=NEXT, load_env=False))
    if waiting.post("/auth/forgot-password", json={"email": "ada@example.com"}).status_code != 429:
        raise AssertionError("a reset rate limit was hidden")
    if waiting.post("/auth/resend-confirmation", json={"email": "ada@example.com"}).status_code != 429:
        raise AssertionError("a resend rate limit was hidden")
    local = TestClient(
        create_app(directory=None, accounts=tmp_path / "accounts.json", frontend_origin=NEXT, load_env=False)
    )
    if local.post("/auth/resend-confirmation", json={"email": "local@example.com"}).status_code != 400:
        raise AssertionError("the local file sent confirmation mail")
    if local.post("/auth/confirm", json={"token": "x", "type": "signup"}).status_code != 400:
        raise AssertionError("the local file confirmed an address")


def test_mail_links_do_not_depend_on_a_discarded_pkce_verifier() -> None:
    text = (ROOT / "ui" / "cloud_store.py").read_text(encoding="utf-8")
    options = text[text.index("def _fresh_options(") : text.index("def service_key_format(")]
    if 'flow_type="implicit"' not in options:
        raise AssertionError("email links would need a verifier this server throws away")


def main() -> None:
    test_redirect_urls_are_the_next_origin_with_no_hardcoded_host()
    test_streamlit_mail_stays_on_its_own_origin_when_the_frontend_is_set()
    test_an_explicit_redirect_is_what_the_hosted_client_sends()
    print("auth mail ok")


if __name__ == "__main__":
    main()
