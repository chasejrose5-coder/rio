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
from ui.cloud_store import CloudAuthError, MemoryDirectory, SupabaseDirectory

NEXT = "https://next.example.test"
STREAMLIT = "https://riotraining.streamlit.app"


class _Auth:
    def __init__(self) -> None:
        self.payload = None
        self.reset = None
        self.otp = None
        self.session_args = None
        self.updated = None

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

    def verify_otp(self, body):
        self.otp = dict(body)
        return SimpleNamespace(session=SimpleNamespace(access_token="otp-access", refresh_token="otp-refresh"))

    def set_session(self, access, refresh):
        self.session_args = (access, refresh)

    def update_user(self, body):
        self.updated = dict(body)


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
    if reset_redirect_url(NEXT) != NEXT + "/reset-password":
        raise AssertionError(reset_redirect_url(NEXT))
    if confirm_redirect_url(NEXT + "/") != NEXT + "/":
        raise AssertionError(confirm_redirect_url(NEXT))
    if "streamlit" in reset_redirect_url(NEXT) or "localhost" in confirm_redirect_url(NEXT):
        raise AssertionError("the mail URL baked in a host")


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
    if created.status_code != 200 or directory.email_redirect_to != NEXT + "/":
        raise AssertionError((created.text, directory.email_redirect_to))
    missing = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    known = client.post("/auth/forgot-password", json={"email": "ada@example.com"})
    if missing.status_code != 200 or known.status_code != 200 or missing.json() != known.json():
        raise AssertionError((missing.text, known.text))
    if "token" in known.json() or directory.reset_redirect_to != NEXT + "/reset-password":
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


def main() -> None:
    test_redirect_urls_are_the_next_origin_with_no_hardcoded_host()
    test_streamlit_mail_stays_on_its_own_origin_when_the_frontend_is_set()
    test_an_explicit_redirect_is_what_the_hosted_client_sends()
    print("auth mail ok")


if __name__ == "__main__":
    main()
