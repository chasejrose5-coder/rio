# test_auth_me_token.py — /auth/me checks the access token the hosted directory can resolve.

"""No network. No production Supabase. Tokens stay sealed and out of the log."""

from __future__ import annotations

import inspect
import logging
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.identity import principal_from_cookie
from api.main import create_app
from ui.cloud_session import COOKIE_NAME, new_hosted_sid
from ui.cloud_store import CloudAuthError, SupabaseDirectory

ANON = "super-secret-anon-key-value"
SECRET = "sb_secret_" + ("k" * 24)
SESSION_KEY = "session-key-should-not-leak"
EMAIL = "ada@example.com"
PASSWORD = "horse-battery-staple-secret"
ACCESS = "access-token-should-not-leak"
REFRESH = "refresh-token-should-not-leak"
URL = "https://abcd.supabase.co"
USER_ID = "user-1"


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class _Store:
    def __init__(self, *, accept: bool, refresh: bool) -> None:
        self.rows: dict[str, dict] = {}
        self.accept = accept
        self.refresh = refresh
        self.get_user: list[tuple[str, str]] = []
        self.refreshed: list[str] = []


class _Table:
    def __init__(self, store: _Store, name: str) -> None:
        self.store = store
        self.name = name
        self.op = ""
        self.row: dict | None = None
        self.filters: list[tuple] = []

    def upsert(self, row):
        self.op = "upsert"
        self.row = row
        return self

    def select(self, *_cols, **_kwargs):
        self.op = "select"
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def lt(self, column, value):
        self.filters.append(("lt", column, value))
        return self

    def limit(self, _n):
        return self

    def execute(self):
        if self.name != "app_sessions":
            return SimpleNamespace(data=[])
        if self.op == "upsert" and isinstance(self.row, dict):
            self.store.rows[str(self.row.get("sid_hash") or "")] = dict(self.row)
            return SimpleNamespace(data=[self.row])
        if self.op == "select":
            digest = next((value for column, value in self.filters if column == "sid_hash"), None)
            found = self.store.rows.get(str(digest))
            return SimpleNamespace(data=[] if found is None else [found])
        if self.op == "delete":
            if any(item[0] == "lt" for item in self.filters):
                return SimpleNamespace(data=[])
            digest = next((value for column, value in self.filters if column == "sid_hash"), None)
            self.store.rows.pop(str(digest), None)
            return SimpleNamespace(data=[])
        raise AssertionError(self.op)


class _Auth:
    def __init__(self, store: _Store, key: str) -> None:
        self.store = store
        self.key = key

    def get_user(self, token):
        self.store.get_user.append((self.key, str(token or "")))
        if not self.store.accept or token != ACCESS:
            raise RuntimeError("invalid jwt")
        return SimpleNamespace(
            user=SimpleNamespace(
                id=USER_ID,
                email=EMAIL,
                email_confirmed_at="2026-01-01T00:00:00Z",
                user_metadata={},
            )
        )

    def refresh_session(self, token):
        self.store.refreshed.append(str(token or ""))
        if not self.store.refresh:
            raise RuntimeError("refresh rejected")
        raise AssertionError("this test does not refresh a valid token")


class _Client:
    def __init__(self, store: _Store, key: str) -> None:
        self.auth = _Auth(store, key)
        self.postgrest = SimpleNamespace(auth=lambda _token: None)

    def table(self, name: str) -> _Table:
        return _Table(self.auth.store, name)


class _Directory(SupabaseDirectory):
    def __init__(self, store: _Store) -> None:
        super().__init__(URL, ANON, SECRET)
        self.store = store

    def _client(self, key):
        return _Client(self.store, key)

    def sign_in(self, email, password):
        if email != EMAIL or password != PASSWORD:
            raise CloudAuthError("Email or password does not match.")
        return {
            "access_token": ACCESS,
            "refresh_token": REFRESH,
            "user_id": USER_ID,
            "email": email,
            "display_name": "Ada",
        }


def _private_absent(text: str) -> None:
    for secret in (ANON, SECRET, SESSION_KEY, PASSWORD, ACCESS, REFRESH):
        if secret and secret in text:
            raise AssertionError("a secret reached the log or the body")


def _log_clean(text: str) -> None:
    _private_absent(text)
    if EMAIL in text:
        raise AssertionError("an email reached the log")


def _logged(run):
    logger = logging.getLogger("rio.cloud")
    handler = _Capture()
    previous = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:
        result = run()
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)
    return result, handler.records


def _blob(records: list[logging.LogRecord]) -> str:
    return "\n".join(record.getMessage() for record in records)


def _client(directory) -> TestClient:
    app = create_app(directory=directory, frontend_origin="http://localhost:3000", load_env=False)
    return TestClient(app, base_url="https://testserver")


def _with_session_key(run):
    previous = os.environ.get("RIO_SESSION_KEY")
    os.environ["RIO_SESSION_KEY"] = SESSION_KEY
    try:
        return run()
    finally:
        if previous is None:
            os.environ.pop("RIO_SESSION_KEY", None)
        else:
            os.environ["RIO_SESSION_KEY"] = previous


def _sign_in(store: _Store) -> tuple[TestClient, _Store]:
    client = _client(_Directory(store))

    def run():
        return client.post("/auth/sign-in", json={"email": EMAIL, "password": PASSWORD})

    response, records = _logged(run)
    if response.status_code != 200:
        raise AssertionError(response.text)
    _private_absent(response.text)
    _log_clean(_blob(records))
    if not store.rows:
        raise AssertionError("sign-in did not store a session")
    sealed = next(iter(store.rows.values()))
    access = str(sealed.get("access_token") or "")
    refresh = str(sealed.get("refresh_token") or "")
    if not access.startswith("f2.") or not refresh.startswith("f2."):
        raise AssertionError("the session tokens were not sealed")
    if ACCESS in access or REFRESH in refresh or EMAIL in access:
        raise AssertionError("a plaintext token was stored")
    return client, store


def test_a_sealed_session_returns_the_athlete() -> None:
    def run():
        client, store = _sign_in(_Store(accept=True, refresh=False))

        def me():
            return client.get("/auth/me")

        response, records = _logged(me)
        if response.status_code != 200:
            raise AssertionError(response.text)
        athlete = response.json()
        if athlete["email"] != EMAIL or athlete["display_name"] != "Ada":
            raise AssertionError(athlete)
        if athlete["id"] != USER_ID or athlete["kind"] != "hosted" or athlete["role"] != "athlete":
            raise AssertionError(athlete)
        if "access_token" in response.text or ACCESS in response.text or REFRESH in response.text:
            raise AssertionError(response.text)
        _private_absent(response.text)
        if not store.get_user or any(key != ANON or token != ACCESS for key, token in store.get_user):
            raise AssertionError(store.get_user)
        if any(token.startswith("f2.") for _key, token in store.get_user):
            raise AssertionError("get_user saw a sealed token")
        warnings = _blob([record for record in records if record.levelno >= logging.WARNING])
        _log_clean(warnings)
        if "hosted session" in warnings:
            raise AssertionError(warnings)

    _with_session_key(run)


def test_an_invalid_token_with_a_failed_refresh_is_401() -> None:
    def run():
        client, store = _sign_in(_Store(accept=False, refresh=False))

        def me():
            return client.get("/auth/me")

        response, records = _logged(me)
        if response.status_code != 401:
            raise AssertionError(response.text)
        if response.headers.get("content-type", "").startswith("text/plain"):
            raise AssertionError(response.headers.get("content-type"))
        if response.json()["detail"] != "Sign in again.":
            raise AssertionError(response.text)
        if "Internal Server Error" in response.text or EMAIL in response.text:
            raise AssertionError(response.text)
        _private_absent(response.text)
        if store.refreshed != [REFRESH]:
            raise AssertionError(store.refreshed)
        if any(token.startswith("f2.") for token in store.refreshed):
            raise AssertionError("refresh saw a sealed token")
        _log_clean(_blob(records))

    _with_session_key(run)


def test_supabase_directory_resolves_an_access_token_with_get_user() -> None:
    source = inspect.getsource(principal_from_cookie)
    if "directory.user_id(" not in source:
        raise AssertionError("principal_from_cookie does not call user_id")
    if not callable(getattr(SupabaseDirectory, "user_id", None)):
        raise AssertionError("SupabaseDirectory does not expose user_id")

    store = _Store(accept=True, refresh=False)
    directory = _Directory(store)
    if directory.user_id(ACCESS) != USER_ID:
        raise AssertionError("a valid token did not resolve")
    if store.get_user != [(ANON, ACCESS)]:
        raise AssertionError(store.get_user)

    store.accept = False
    try:
        directory.user_id(ACCESS)
    except CloudAuthError as exc:
        if str(exc) != "Sign in again.":
            raise AssertionError(str(exc)) from exc
    else:
        raise AssertionError("an invalid token was accepted")
    try:
        directory.user_id(None)
    except CloudAuthError:
        return
    raise AssertionError("a missing token was accepted")


def test_an_unexpected_cookie_error_is_401_and_logged() -> None:
    sid = new_hosted_sid()

    class _Broken:
        service_key = SECRET
        anon_key = ANON

        def load_hosted_session(self, _sid):
            raise RuntimeError(
                f"directory failed token={ACCESS} email={EMAIL} cookie={sid} apikey={ANON} key={SECRET}"
            )

    client = _client(_Broken())
    client.cookies.set(COOKIE_NAME, sid)

    def run():
        return client.get("/auth/me")

    response, records = _logged(run)
    if response.status_code != 401:
        raise AssertionError(response.text)
    if response.json().get("detail") != "Sign in again.":
        raise AssertionError(response.text)
    _private_absent(response.text)
    warnings = [record for record in records if record.levelno == logging.WARNING and record.name == "rio.cloud"]
    text = _blob(warnings)
    _log_clean(text)
    if sid in text:
        raise AssertionError(text)
    if "hosted session resolve failed:" not in text or "error=RuntimeError" not in text:
        raise AssertionError(text)
