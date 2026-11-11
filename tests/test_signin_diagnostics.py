# test_signin_diagnostics.py — a bad password stays generic. A dead auth service does not.

"""No network. The auth probe is a GET double. Keys stay out of the log and the body."""

from __future__ import annotations

import inspect
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from unittest.mock import patch

from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError, AuthInvalidCredentialsError, AuthRetryableError

from api.main import create_app
from ui.cloud_store import (
    SIGNIN_MISMATCH,
    SIGNIN_RATE,
    SIGNIN_UNAVAILABLE,
    SIGNUP_CONFIRM,
    MemoryDirectory,
    SupabaseDirectory,
    _httpx_get,
    auth_health,
    fetch_auth_settings,
    signin_error_message,
)

ANON = "super-secret-anon-key-value"
SERVICE = "super-secret-service-key-value"
PASSWORD = "horse-battery-staple-secret"
EMAIL = "ada@example.com"
HOST = "abcd.supabase.co"
URL = f"https://{HOST}"
JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIn0.signaturevalue"


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class _Auth:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    def sign_in_with_password(self, _payload):
        raise self.error


class _Directory(SupabaseDirectory):
    def __init__(self, error: BaseException) -> None:
        super().__init__(URL, ANON, SERVICE)
        self.error = error

    def _client(self, key):
        if key != self.anon_key:
            raise AssertionError("sign-in used a key other than the anon key")
        return SimpleNamespace(auth=_Auth(self.error))


class _Credentials(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid login credentials")
        self.message = "Invalid login credentials"
        self.status = 400
        self.code = "invalid_credentials"
        self.access_token = "session-token-should-not-leak"


class _ApiKey(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid API key")
        self.message = "Invalid API key"
        self.status = 401


class _Forbidden(Exception):
    def __init__(self) -> None:
        super().__init__("Forbidden")
        self.message = "Forbidden"
        self.status = 403


class _Upstream(Exception):
    def __init__(self) -> None:
        super().__init__("upstream failed")
        self.message = "upstream failed"
        self.status = 503
        self.code = "unexpected_failure"


class ConnectError(OSError):
    def __init__(self) -> None:
        super().__init__(111, "Connection refused")
        self.message = "Connection refused"


class _LeakyConnect(OSError):
    def __init__(self) -> None:
        text = (
            f"Connection refused password={PASSWORD} email={EMAIL} apikey={ANON} "
            f"authorization: Bearer {SERVICE} {JWT}"
        )
        super().__init__(text)
        self.message = text


class _Rate(Exception):
    def __init__(self) -> None:
        super().__init__("rate limit")
        self.message = "rate limit"
        self.status = 429


class _Unconfirmed(Exception):
    def __init__(self) -> None:
        super().__init__("Email not confirmed")
        self.message = "Email not confirmed"


def _client(directory=None) -> TestClient:
    app = create_app(
        directory=directory,
        frontend_origin="http://localhost:3000",
        load_env=False,
    )
    return TestClient(app, base_url="https://testserver")


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
    parts: list[str] = []
    for record in records:
        parts.append(record.getMessage())
        if record.args:
            parts.extend(str(arg) for arg in record.args)
    return "\n".join(parts)


def _secrets_absent(text: str) -> None:
    for secret in (PASSWORD, EMAIL, ANON, SERVICE, JWT, "session-token-should-not-leak"):
        if secret and secret in text:
            raise AssertionError(text)


def _sign_in(error: BaseException):
    client = _client(_Directory(error))
    return client.post("/auth/sign-in", json={"email": EMAIL, "password": PASSWORD})


def test_messages_keep_a_wrong_password_and_name_a_dead_service() -> None:
    wrong = SimpleNamespace(status=400, message="Invalid login credentials", code="invalid_credentials")
    if signin_error_message(wrong) != SIGNIN_MISMATCH:
        raise AssertionError(signin_error_message(wrong))
    labeled = SimpleNamespace(status=401, message="Invalid login credentials", code="invalid_credentials")
    if signin_error_message(labeled) != SIGNIN_MISMATCH:
        raise AssertionError("a credential rejection was called an outage")
    if signin_error_message(RuntimeError("database unavailable")) != SIGNIN_MISMATCH:
        raise AssertionError("an unknown failure was relabeled")
    if signin_error_message(SimpleNamespace(status=429, message="rate limit")) != SIGNIN_RATE:
        raise AssertionError("sign-in rate limit was hidden")
    if signin_error_message(RuntimeError("Email not confirmed")) != SIGNUP_CONFIRM:
        raise AssertionError("an unconfirmed email was relabeled")
    refused = SimpleNamespace(status=401, message="Invalid API key")
    if signin_error_message(refused) != SIGNIN_UNAVAILABLE:
        raise AssertionError(signin_error_message(refused))
    forbidden = SimpleNamespace(status=403, message="Forbidden")
    if signin_error_message(forbidden) != SIGNIN_UNAVAILABLE:
        raise AssertionError(signin_error_message(forbidden))
    down = SimpleNamespace(status=500, message="upstream failed", code="unexpected_failure")
    if signin_error_message(down) != SIGNIN_UNAVAILABLE:
        raise AssertionError(signin_error_message(down))
    if signin_error_message(ConnectError()) != SIGNIN_UNAVAILABLE:
        raise AssertionError("a connection error looked like a bad password")
    if signin_error_message(RuntimeError("Name or service not known")) != SIGNIN_UNAVAILABLE:
        raise AssertionError("a DNS failure looked like a bad password")
    bad = AuthApiError("Invalid login credentials", 400, "invalid_credentials")
    if signin_error_message(bad) != SIGNIN_MISMATCH:
        raise AssertionError(signin_error_message(bad))
    missing = AuthInvalidCredentialsError("Invalid login credentials")
    if signin_error_message(missing) != SIGNIN_MISMATCH:
        raise AssertionError(signin_error_message(missing))
    rejected = AuthApiError("Invalid API key", 401, None)
    if signin_error_message(rejected) != SIGNIN_UNAVAILABLE:
        raise AssertionError(signin_error_message(rejected))
    offline = AuthRetryableError("Name or service not known", 0)
    if signin_error_message(offline) != SIGNIN_UNAVAILABLE:
        raise AssertionError(signin_error_message(offline))
    limited = AuthApiError("Request rate limit reached", 429, "over_request_rate_limit")
    if signin_error_message(limited) != SIGNIN_RATE:
        raise AssertionError(signin_error_message(limited))
    hidden = RuntimeError("Client error '401 Unauthorized' for url 'https://abcd.supabase.co/auth/v1/token'")
    if signin_error_message(hidden) != SIGNIN_UNAVAILABLE:
        raise AssertionError(signin_error_message(hidden))


def test_wrong_password_stays_401_and_the_log_has_no_secrets() -> None:
    def run():
        return _sign_in(_Credentials())

    response, records = _logged(run)
    if response.status_code != 401 or response.json()["detail"] != SIGNIN_MISMATCH:
        raise AssertionError(response.text)
    if "set-cookie" in {key.lower() for key in response.headers}:
        raise AssertionError("a failed sign-in set a cookie")
    warnings = [record for record in records if record.levelno == logging.WARNING]
    if len(warnings) != 1:
        raise AssertionError([record.getMessage() for record in records])
    text = _blob(warnings)
    _secrets_absent(text)
    if "error=Credentials" not in text and "error=_Credentials" not in text:
        raise AssertionError(text)
    if "status=400" not in text or "invalid_credentials" not in text:
        raise AssertionError(text)
    if "Invalid login credentials" not in text or f"host={HOST}" not in text:
        raise AssertionError(text)
    if warnings[0].name != "rio.cloud":
        raise AssertionError(warnings[0].name)


def test_config_and_upstream_failures_are_503() -> None:
    cases = (
        (_ApiKey(), "Invalid API key", "401"),
        (_Forbidden(), "Forbidden", "403"),
        (_Upstream(), "unexpected_failure", "503"),
        (ConnectError(), "Connection refused", "-"),
        (_LeakyConnect(), None, "-"),
    )
    for error, detail, status in cases:
        def run(error=error):
            return _sign_in(error)

        response, records = _logged(run)
        if response.status_code != 503 or response.json()["detail"] != SIGNIN_UNAVAILABLE:
            raise AssertionError(response.text)
        warnings = [record for record in records if "sign-in failed" in record.getMessage()]
        if len(warnings) != 1 or warnings[0].levelno != logging.WARNING:
            raise AssertionError([record.getMessage() for record in records])
        text = _blob(warnings)
        _secrets_absent(text)
        if f"error={type(error).__name__}" not in text or f"host={HOST}" not in text:
            raise AssertionError(text)
        if f"status={status}" not in text:
            raise AssertionError(text)
        if detail is not None and detail not in text:
            raise AssertionError(text)


def test_existing_sign_in_failures_stay_401() -> None:
    directory = MemoryDirectory()
    directory.sign_up(EMAIL, "correct-horse", "Ada")

    def local():
        return _client(directory).post(
            "/auth/sign-in",
            json={"email": EMAIL, "password": PASSWORD},
        )

    response, records = _logged(local)
    if response.status_code != 401 or response.json()["detail"] != SIGNIN_MISMATCH:
        raise AssertionError(response.text)
    if any("sign-in failed" in record.getMessage() for record in records):
        raise AssertionError(_blob(records))
    for error, message in ((_Rate(), SIGNIN_RATE), (_Unconfirmed(), SIGNUP_CONFIRM)):
        response, _records = _logged(lambda error=error: _sign_in(error))
        if response.status_code != 401 or response.json()["detail"] != message:
            raise AssertionError(response.text)


def test_health_auth_is_closed_without_a_project() -> None:
    blank = {"configured": False, "url_host": None, "auth_reachable": False, "status": None}
    if auth_health(MemoryDirectory()) != blank:
        raise AssertionError(auth_health(MemoryDirectory()))
    if auth_health(None) != blank:
        raise AssertionError(auth_health(None))
    client = _client(MemoryDirectory())
    health = client.get("/health")
    if health.status_code != 200 or health.json() != {"ok": True}:
        raise AssertionError(health.text)
    probe = client.get("/health/auth")
    if probe.status_code != 200 or probe.json() != blank:
        raise AssertionError(probe.text)
    if ANON in probe.text or SERVICE in probe.text:
        raise AssertionError(probe.text)


def test_health_auth_reports_the_settings_status_without_secrets() -> None:
    directory = SupabaseDirectory(URL + "/rest/v1?apikey=" + ANON, ANON, SERVICE)
    seen: dict = {}

    def fake(url: str, anon_key: str, timeout: float = 5.0):
        seen["url"] = url
        seen["anon_key"] = anon_key
        seen["timeout"] = timeout
        return 200

    with patch("ui.cloud_store.fetch_auth_settings", fake):
        body = auth_health(directory)
    if seen["url"] != directory.url or seen["anon_key"] != ANON or SERVICE in str(seen):
        raise AssertionError(seen)
    if body != {"configured": True, "url_host": HOST, "auth_reachable": True, "status": 200}:
        raise AssertionError(body)
    _secrets_absent(str(body))
    client = _client(directory)
    with patch("ui.cloud_store.fetch_auth_settings", lambda *_args, **_kwargs: 401):
        response = client.get("/health/auth")
    if response.status_code != 200:
        raise AssertionError(response.text)
    if response.json() != {"configured": True, "url_host": HOST, "auth_reachable": False, "status": 401}:
        raise AssertionError(response.text)
    _secrets_absent(response.text)
    with patch("ui.cloud_store.fetch_auth_settings", lambda *_args, **_kwargs: None):
        missed = auth_health(directory)
    if missed["auth_reachable"] is not False or missed["status"] is not None or missed["configured"] is not True:
        raise AssertionError(missed)


def test_auth_settings_probe_is_a_get_and_drops_the_body() -> None:
    source = inspect.getsource(_httpx_get)
    if "client.get(" not in source or "follow_redirects=False" not in source:
        raise AssertionError(source)
    for verb in (".post(", ".put(", ".patch(", ".delete("):
        if verb in source or verb in inspect.getsource(fetch_auth_settings):
            raise AssertionError(verb)
    calls = []

    class _Response:
        status_code = 200

        @property
        def text(self):
            raise AssertionError("settings body was read")

        @property
        def content(self):
            raise AssertionError("settings body was read")

        def json(self):
            raise AssertionError("settings body was read")

    def opener(url, headers=None, timeout=None, follow_redirects=None):
        calls.append(
            {
                "url": url,
                "headers": dict(headers or {}),
                "timeout": timeout,
                "follow_redirects": follow_redirects,
            }
        )
        return _Response()

    status = fetch_auth_settings(URL + "/extra?apikey=" + ANON, ANON, opener=opener)
    if status != 200 or len(calls) != 1:
        raise AssertionError(calls)
    call = calls[0]
    if call["url"] != f"https://{HOST}/auth/v1/settings":
        raise AssertionError(call)
    if ANON in call["url"] or SERVICE in call["url"] or "?" in call["url"]:
        raise AssertionError(call)
    if call["follow_redirects"] is not False:
        raise AssertionError(call)
    headers = call["headers"]
    if headers.get("apikey") != ANON or headers.get("Authorization") != "Bearer " + ANON:
        raise AssertionError(headers)
    if SERVICE in str(headers):
        raise AssertionError(headers)
    calls.clear()

    def refuse(url, headers=None, timeout=None, follow_redirects=None):
        calls.append(url)
        raise OSError(ANON)

    logged, records = _logged(
        lambda: fetch_auth_settings("https://user:secret@abcd.supabase.co", ANON, opener=opener)
    )
    if logged is not None or calls:
        raise AssertionError((logged, calls))
    clear, _records = _logged(lambda: fetch_auth_settings("http://" + HOST, ANON, opener=opener))
    if clear is not None or calls:
        raise AssertionError((clear, calls))
    failed, records = _logged(lambda: fetch_auth_settings(URL, ANON, opener=refuse))
    if failed is not None:
        raise AssertionError(failed)
    text = _blob(records)
    _secrets_absent(text)
    if "error=OSError" not in text or f"host={HOST}" not in text:
        raise AssertionError(text)
    if any(record.levelno != logging.WARNING for record in records):
        raise AssertionError(text)
