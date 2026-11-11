# test_hosted_session_log.py — a failed app_sessions call is logged, and sb_secret is not a Bearer token.

"""No network. Keys, tokens, session ids, and emails stay out of the log and the health body."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.identity import _refresh_hosted, _remember_hosted, principal_from_cookie
from api.main import create_app
from ui.cloud_session import hosted_hash, new_hosted_sid
from ui.cloud_store import CloudAuthError, SupabaseDirectory, auth_health, open_session_secret, seal_session_secret

ANON = "super-secret-anon-key-value"
SECRET = "sb_secret_" + ("k" * 24)
JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIn0.sigvalue"
EMAIL = "ada@example.com"
TOKEN = "session-token-should-not-leak"
SID = "rio1." + ("a" * 32)
URL = "https://abcd.supabase.co"
PASSWORD = "horse-battery-staple-secret"


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class _Boom(Exception):
    def __init__(self) -> None:
        text = f"Invalid JWT apikey={SECRET} email={EMAIL} sid={SID} token={TOKEN}"
        super().__init__(text)
        self.message = text
        self.code = "PGRST301"
        self.status = 401


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


def _secrets_absent(text: str) -> None:
    for secret in (SECRET, ANON, JWT, EMAIL, TOKEN, SID, PASSWORD):
        if secret and secret in text:
            raise AssertionError("a secret reached the log or the body")


def _assert_warning(records: list[logging.LogRecord], action: str) -> None:
    warnings = [record for record in records if record.levelno == logging.WARNING and record.name == "rio.cloud"]
    text = _blob(warnings)
    _secrets_absent(text)
    needle = f"hosted session {action} failed:"
    if needle not in text:
        raise AssertionError(text)
    if "error=_Boom" not in text or "status=401" not in text or "code=PGRST301" not in text:
        raise AssertionError(text)
    if "Invalid JWT" not in text or "service_key=set" not in text or "format=sb_secret" not in text:
        raise AssertionError(text)


class _Query:
    def __init__(self, op: str, fail: set[str]) -> None:
        self.op = op
        self.fail = fail
        self.filters: list[str] = []
        self.limit_n: int | None = None
        self.cols: tuple = ()

    def select(self, *cols, **_kwargs):
        self.op = "select"
        self.cols = cols
        return self

    def upsert(self, _row):
        self.op = "upsert"
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, *_args):
        self.filters.append("eq")
        return self

    def lt(self, *_args):
        self.filters.append("lt")
        return self

    def limit(self, n):
        self.limit_n = n
        return self

    def execute(self):
        if self.op == "select" and self.limit_n == 0:
            return SimpleNamespace(data=[{"sid_hash": "hash", "access_token": TOKEN, "email": EMAIL}])
        if self.op == "select" and "select" not in self.fail:
            return SimpleNamespace(
                data=[
                    {
                        "sid_hash": "hash",
                        "user_id": "user-1",
                        "access_token": "stored-token",
                        "refresh_token": "stored-refresh",
                        "email": EMAIL,
                        "display_name": "Ada",
                        "issued_at": int(time.time()),
                    }
                ]
            )
        if self.op == "delete" and "lt" in self.filters and "purge" not in self.fail:
            return SimpleNamespace(data=[])
        if self.op in self.fail or (self.op == "delete" and "drop" in self.fail):
            raise _Boom()
        raise _Boom()


class _Client:
    def __init__(self, fail: set[str]) -> None:
        self.fail = fail
        self.auth = self

    def table(self, name):
        if name != "app_sessions":
            raise AssertionError(name)
        return _Query("", self.fail)

    def refresh_session(self, _token):
        raise _Boom()


def _directory(fail: set[str]) -> SupabaseDirectory:
    directory = SupabaseDirectory(URL, ANON, SECRET)

    def _new(_key):
        return _Client(fail)

    directory._client = _new  # type: ignore[method-assign]
    return directory


def _record() -> dict:
    return {
        "access_token": TOKEN,
        "refresh_token": "refresh-token",
        "user_id": "user-1",
        "email": EMAIL,
        "display_name": "Ada",
        "issued_at": int(time.time()),
    }


def test_sb_secret_is_not_sent_as_a_bearer_token() -> None:
    directory = SupabaseDirectory(URL, ANON, SECRET)
    secret_client = directory._client(SECRET)
    jwt_client = directory._client(JWT)

    def values(headers) -> dict[str, str]:
        found: dict[str, str] = {}
        for name, value in headers.items():
            found[str(name).lower()] = str(value)
        return found

    def bags(client):
        found = [values(client.options.headers), values(client.auth._headers), values(client.auth.admin._headers)]
        found.append(values(client.postgrest.headers))
        return found

    for headers in bags(secret_client):
        if headers.get("authorization"):
            raise AssertionError("sb_secret was copied into Authorization")
        if SECRET not in headers.get("apikey", ""):
            raise AssertionError("the secret key was dropped from apikey")
    for headers in bags(jwt_client):
        if headers.get("authorization") != "Bearer " + JWT:
            raise AssertionError("a legacy JWT key lost its bearer header")
        if headers.get("apikey") != JWT:
            raise AssertionError("a legacy JWT key lost its apikey header")


def test_session_failures_are_logged_without_secrets() -> None:
    def save():
        try:
            _directory({"upsert"}).save_hosted_session(_record())
        except CloudAuthError as exc:
            if str(exc) != "Sign in again.":
                raise
            return exc
        raise AssertionError("save swallowed the failure")

    _exc, records = _logged(save)
    _assert_warning(records, "save")

    def load():
        try:
            _directory({"select"}).load_hosted_session(SID)
        except CloudAuthError as exc:
            return exc
        raise AssertionError("load swallowed the failure")

    _exc, records = _logged(load)
    _assert_warning(records, "load")

    def update():
        try:
            _directory({"upsert"}).update_hosted_session(SID, _record())
        except CloudAuthError as exc:
            return exc
        raise AssertionError("update swallowed the failure")

    _exc, records = _logged(update)
    _assert_warning(records, "update")

    def drop():
        try:
            _directory({"drop"}).drop_hosted_session(SID)
        except CloudAuthError as exc:
            return exc
        raise AssertionError("drop swallowed the failure")

    _exc, records = _logged(drop)
    _assert_warning(records, "drop")

    def refresh():
        try:
            _directory(set()).refresh_session("refresh-token")
        except CloudAuthError as exc:
            return exc
        raise AssertionError("refresh swallowed the failure")

    _exc, records = _logged(refresh)
    _assert_warning(records, "refresh")


def test_identity_logs_a_swallowed_session_error() -> None:
    directory = _directory({"select"})

    def load():
        return principal_from_cookie(SimpleNamespace(), directory, None, SID)

    who, records = _logged(load)
    if who is not None:
        raise AssertionError(who)
    _assert_warning(records, "load")

    class _Broken:
        service_key = SECRET

        def save_hosted_session(self, _record):
            raise RuntimeError(f"write failed email={EMAIL} sid={SID} token={TOKEN} apikey={SECRET}")

    def remember():
        try:
            _remember_hosted(
                _Broken(),
                {"access_token": TOKEN, "refresh_token": "r", "user_id": "user-1", "email": EMAIL},
                missing="Sign in again.",
            )
        except CloudAuthError as exc:
            return str(exc)
        raise AssertionError("remember did not fail")

    text, records = _logged(remember)
    if text != "Sign in again.":
        raise AssertionError(text)
    warnings = _blob([record for record in records if record.levelno == logging.WARNING])
    _secrets_absent(warnings)
    if "hosted session save failed:" not in warnings or "error=RuntimeError" not in warnings:
        raise AssertionError(warnings)
    if "service_key=set" not in warnings or "format=sb_secret" not in warnings:
        raise AssertionError(warnings)

    def refresh():
        try:
            return _refresh_hosted(_directory(set()), SID, {"refresh_token": "refresh-token", "issued_at": int(time.time())})
        except CloudAuthError:
            return "raised"

    found, records = _logged(refresh)
    if found is not None:
        raise AssertionError(found)
    _assert_warning(records, "refresh")


def test_sign_in_stays_sign_in_again_when_the_session_row_fails() -> None:
    class _Directory(SupabaseDirectory):
        def sign_in(self, email, password):
            return {
                "access_token": TOKEN,
                "refresh_token": "refresh-token",
                "user_id": "user-1",
                "email": email,
                "display_name": "Ada",
            }

        def _client(self, _key):
            raise _Boom()

    app = create_app(directory=_Directory(URL, ANON, SECRET), frontend_origin="http://localhost:3000", load_env=False)

    def run():
        return TestClient(app, base_url="https://testserver").post(
            "/auth/sign-in",
            json={"email": EMAIL, "password": PASSWORD},
        )

    response, records = _logged(run)
    if response.status_code != 401 or response.json()["detail"] != "Sign in again.":
        raise AssertionError(response.text)
    if "set-cookie" in {key.lower() for key in response.headers}:
        raise AssertionError("a failed session write set a cookie")
    _secrets_absent(response.text)
    _assert_warning(records, "save")


def test_health_auth_probes_app_sessions_without_returning_values() -> None:
    seen: dict = {}

    class _Probe:
        def table(self, name):
            seen["table"] = name
            return self

        def select(self, *cols, **_kwargs):
            seen["select"] = cols
            return self

        def limit(self, n):
            seen["limit"] = n
            return self

        def execute(self):
            return SimpleNamespace(data=[{"access_token": TOKEN, "email": EMAIL, "sid_hash": SID}])

    directory = SupabaseDirectory(URL, ANON, SECRET)

    def _new(key):
        seen["key"] = key
        return _Probe()

    directory._client = _new  # type: ignore[method-assign]

    def run():
        from unittest.mock import patch

        with patch("ui.cloud_store.fetch_auth_settings", lambda *_args, **_kwargs: 200):
            return auth_health(directory)

    body, records = _logged(run)
    if seen.get("key") != SECRET or seen.get("table") != "app_sessions":
        raise AssertionError("the probe did not use the service role on app_sessions")
    if seen.get("select") != ("sid_hash",) or seen.get("limit") != 0:
        raise AssertionError(seen)
    if body["service_key_configured"] is not True or body["service_key_format"] != "sb_secret":
        raise AssertionError(body)
    if body["sessions_ok"] != {"ok": True, "code": None, "message": None}:
        raise AssertionError(body)
    _secrets_absent(str(body))
    if any("hosted session" in record.getMessage() for record in records):
        raise AssertionError(_blob(records))

    def fail():
        class _Fail(_Probe):
            def execute(self):
                raise _Boom()

        directory._client = lambda _key: _Fail()  # type: ignore[method-assign]
        from unittest.mock import patch

        with patch("ui.cloud_store.fetch_auth_settings", lambda *_args, **_kwargs: 200):
            return auth_health(directory)

    failed, records = _logged(fail)
    if failed["sessions_ok"]["ok"] is not False or failed["sessions_ok"]["code"] != "PGRST301":
        raise AssertionError(failed)
    if "Invalid JWT" not in (failed["sessions_ok"]["message"] or ""):
        raise AssertionError(failed)
    _secrets_absent(str(failed))
    _assert_warning(records, "sessions")

    empty = SupabaseDirectory(URL, ANON, "")
    from unittest.mock import patch

    with patch("ui.cloud_store.fetch_auth_settings", lambda *_args, **_kwargs: 200):
        missing = auth_health(empty)
    if missing["service_key_configured"] is not False or missing["service_key_format"] != "other":
        raise AssertionError(missing)
    if missing["sessions_ok"] != {"ok": False, "code": None, "message": None}:
        raise AssertionError(missing)

    app = create_app(directory=directory, frontend_origin="http://localhost:3000", load_env=False)
    # The failure probe replaced _client. A route read must still hide the key.
    with patch("ui.cloud_store.fetch_auth_settings", lambda *_args, **_kwargs: 200):
        response = TestClient(app, base_url="https://testserver").get("/health/auth")
    if response.status_code != 200:
        raise AssertionError(response.text)
    _secrets_absent(response.text)
    if response.json()["service_key_format"] != "sb_secret":
        raise AssertionError(response.text)


def test_a_normal_token_refresh_is_not_logged() -> None:
    class _Quiet:
        service_key = SECRET

        def load_hosted_session(self, _sid):
            return {
                "access_token": TOKEN,
                "refresh_token": "refresh-token",
                "user_id": "user-1",
                "email": EMAIL,
                "display_name": "Ada",
                "issued_at": int(time.time()),
            }

        def user_id(self, _token):
            raise CloudAuthError("Sign in again.")

        def refresh_session(self, _refresh):
            return {
                "access_token": "next-token",
                "refresh_token": "next-refresh",
                "user_id": "user-1",
                "email": EMAIL,
                "display_name": "Ada",
            }

        def update_hosted_session(self, _sid, _record):
            return None

    def run():
        return principal_from_cookie(SimpleNamespace(), _Quiet(), None, new_hosted_sid())

    who, records = _logged(run)
    if who is None or who.token != "next-token":
        raise AssertionError(who)
    if any("hosted session" in record.getMessage() for record in records):
        raise AssertionError(_blob(records))
    if any("session step failed" in record.getMessage() for record in records):
        raise AssertionError(_blob(records))


SESSION_KEY = "super-secret-session-key-value"
OTHER_KEY = "other-secret-session-key-value"
REFRESH = "refresh-token-should-not-leak"


def _step_text(records: list[logging.LogRecord]) -> str:
    lines = [
        record.getMessage()
        for record in records
        if record.levelno >= logging.WARNING and record.getMessage().startswith("session step failed:")
    ]
    return "\n".join(lines)


def _assert_step(records: list[logging.LogRecord], step: str) -> None:
    text = _step_text(records)
    _secrets_absent(text)
    for secret in (SESSION_KEY, OTHER_KEY, REFRESH, "f2.", "rio1."):
        if secret in text:
            raise AssertionError(text)
    prefix = hosted_hash(SID)[:12]
    needle = f"session step failed: step={step} sid_hash={prefix}"
    if needle not in text:
        raise AssertionError(text)


def test_session_step_logs_name_the_failure_and_hide_secrets() -> None:
    previous = os.environ.get("RIO_SESSION_KEY")
    try:
        os.environ["RIO_SESSION_KEY"] = SESSION_KEY
        sealed = seal_session_secret(TOKEN)
        if not sealed.startswith("f2.") or TOKEN in sealed or SESSION_KEY in sealed:
            raise AssertionError("the token was not sealed")

        def opened():
            if open_session_secret(sealed, SID) != TOKEN:
                raise AssertionError("a sealed token did not open")

        _value, records = _logged(opened)
        if any("session step failed" in record.getMessage() for record in records):
            raise AssertionError(_blob(records))

        def plain():
            if open_session_secret(TOKEN, SID) != TOKEN:
                raise AssertionError("plaintext stopped opening")

        _value, records = _logged(plain)
        if any("session step failed" in record.getMessage() for record in records):
            raise AssertionError(_blob(records))

        os.environ["RIO_SESSION_KEY"] = OTHER_KEY

        def decrypt_failed():
            if open_session_secret(sealed, SID) != "":
                raise AssertionError("a changed key still opened the token")

        _value, records = _logged(decrypt_failed)
        _assert_step(records, "decrypt failed or empty")
        if sealed in _step_text(records):
            raise AssertionError("the ciphertext reached the log")

        os.environ["RIO_SESSION_KEY"] = "   "

        def key_missing():
            if open_session_secret(sealed, SID) != "":
                raise AssertionError("a blank key still opened the token")

        _value, records = _logged(key_missing)
        _assert_step(records, "encryption key missing")

        os.environ.pop("RIO_SESSION_KEY", None)
        if auth_health(None)["session_key_configured"] is not False:
            raise AssertionError(auth_health(None))
        os.environ["RIO_SESSION_KEY"] = SESSION_KEY
        present = auth_health(None)
        if present["session_key_configured"] is not True or SESSION_KEY in str(present):
            raise AssertionError(present)

        class _Gone:
            def load_hosted_session(self, _sid):
                return None

        def missing():
            return principal_from_cookie(SimpleNamespace(), _Gone(), None, SID)

        who, records = _logged(missing)
        if who is not None:
            raise AssertionError(who)
        _assert_step(records, "row missing")

        def load_error():
            return principal_from_cookie(SimpleNamespace(), _directory({"select"}), None, SID)

        who, records = _logged(load_error)
        if who is not None:
            raise AssertionError(who)
        _assert_step(records, "row load error")
        if "hosted session load failed:" not in _blob(records):
            raise AssertionError(_blob(records))
        _secrets_absent(_blob(records))

        class _Empty:
            def load_hosted_session(self, _sid):
                return {
                    "access_token": "",
                    "refresh_token": REFRESH,
                    "user_id": "user-1",
                    "email": EMAIL,
                    "display_name": "Ada",
                    "issued_at": int(time.time()),
                }

        def empty():
            return principal_from_cookie(SimpleNamespace(), _Empty(), None, SID)

        who, records = _logged(empty)
        if who is not None:
            raise AssertionError(who)
        _assert_step(records, "decrypt failed or empty")

        class _Reject:
            def load_hosted_session(self, _sid):
                return {
                    "access_token": TOKEN,
                    "refresh_token": REFRESH,
                    "user_id": "user-1",
                    "email": EMAIL,
                    "display_name": "Ada",
                    "issued_at": int(time.time()),
                }

            def user_id(self, _token):
                raise CloudAuthError("Sign in again.")

            def refresh_session(self, _refresh):
                raise CloudAuthError("Sign in again.")

            def drop_hosted_session(self, _sid):
                return None

        def rejected():
            return principal_from_cookie(SimpleNamespace(), _Reject(), None, SID)

        who, records = _logged(rejected)
        if who is not None:
            raise AssertionError(who)
        _assert_step(records, "token rejected")
        _assert_step(records, "refresh failed")
        _secrets_absent(_blob(records))

        class _Ready:
            def load_hosted_session(self, _sid):
                return {
                    "access_token": TOKEN,
                    "refresh_token": REFRESH,
                    "user_id": "user-1",
                    "email": EMAIL,
                    "display_name": "Ada",
                    "issued_at": int(time.time()),
                }

            def user_id(self, token):
                if token != TOKEN:
                    raise AssertionError("the access token changed")
                return "user-1"

        def ready():
            return principal_from_cookie(SimpleNamespace(), _Ready(), None, SID)

        who, records = _logged(ready)
        if who is None or who.token != TOKEN or who.email != EMAIL:
            raise AssertionError(who)
        if any("session step failed" in record.getMessage() for record in records):
            raise AssertionError(_blob(records))
    finally:
        if previous is None:
            os.environ.pop("RIO_SESSION_KEY", None)
        else:
            os.environ["RIO_SESSION_KEY"] = previous
