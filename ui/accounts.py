# accounts.py — email and a password hash. Each account keeps its own plan records.

"""A local account file. The password is hashed. Plan records are sealed with it.

The file lives on this machine. No external auth service. No model. No spend.
No scores. A signed token holds the email and the seal key for one day. The
seal key is not written to the file.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
from pathlib import Path

# PBKDF2-HMAC-SHA256. High enough that a guessed password is slow here.
_ITERATIONS = 200_000
_SALT_BYTES = 16
_KEY_BYTES = 32
_PAYLOAD_LIMIT = 400_000
_KEY_LIMIT = 500
_RECORD_LIMIT = 64
# Used only so a missing account takes the same kind of work as a real one.
_DUMMY_SALT = bytes.fromhex("5c" * _SALT_BYTES)
# A token this old is cleared. Younger than this still restores the session.
_SESSION_MAX_AGE = 24 * 60 * 60
_SESSION_TOKEN_LIMIT = 4_000

_LOCK = threading.Lock()


class AccountError(ValueError):
    """The account file could not be used. The message is safe to show."""


def accounts_path() -> Path:
    """The local account file. RIO_ACCOUNTS_PATH overrides it for a test."""
    override = os.environ.get("RIO_ACCOUNTS_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "data" / "accounts.json"


def normalize_email(value: object) -> str | None:
    """A lowercase email, or None when the text is not one."""
    if not isinstance(value, str):
        return None
    text = value.strip().casefold()
    if not text or len(text) > 254:
        return None
    if any(ord(char) < 33 or ord(char) == 127 for char in text):
        return None
    if text.count("@") != 1:
        return None
    local, domain = text.split("@")
    if not local or not domain or "." not in domain:
        return None
    if ".." in text or local.startswith(".") or local.endswith("."):
        return None
    if domain.startswith(".") or domain.endswith("."):
        return None
    return text


def password_ok(value: object) -> bool:
    """At least 8 characters, and no control characters. The text is not stored."""
    if not isinstance(value, str):
        return False
    if len(value) < 8 or len(value) > 128:
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    return True


def create_account(path: Path, email: object, password: object) -> tuple[str, str]:
    """Create one account and return its email and seal key.

    The seal key opens that account's records for this session. A second
    create for the same email is refused. The password is not written.
    """
    cleaned = normalize_email(email)
    if cleaned is None:
        raise AccountError("Enter an email address.")
    if not password_ok(password) or not isinstance(password, str):
        raise AccountError("Use at least 8 characters.")
    with _LOCK:
        store = _load(path)
        if cleaned in store["accounts"]:
            raise AccountError("An account with that email already exists.")
        salt = secrets.token_bytes(_SALT_BYTES)
        seal = _seal_key(password, salt)
        store["accounts"][cleaned] = {
            "login": _login_hash(password, salt).hex(),
            "records": _seal_records({}, seal),
            "salt": salt.hex(),
        }
        _save(path, store)
    return cleaned, seal.hex()


def authenticate(path: Path, email: object, password: object) -> tuple[str, str] | None:
    """The email and seal key, or None when the email or password does not match."""
    cleaned = normalize_email(email)
    if cleaned is None or not password_ok(password) or not isinstance(password, str):
        return None
    with _LOCK:
        store = _load(path)
        account = store["accounts"].get(cleaned)
        if not isinstance(account, dict):
            _login_hash(password, _DUMMY_SALT)
            return None
        salt = _salt_bytes(account.get("salt"))
        login = account.get("login")
        if salt is None or not isinstance(login, str):
            raise AccountError("Accounts could not be read.")
        found = _login_hash(password, salt).hex()
        if len(login) != len(found) or not hmac.compare_digest(found, login):
            return None
        seal = _seal_key(password, salt)
        if _open_records(account.get("records"), seal) is None:
            raise AccountError("Accounts could not be read.")
        return cleaned, seal.hex()


def read_record(path: Path, email: object, secret: object, key: object) -> str | None:
    """One stored payload, "" when this account has no such key, None when the seal fails."""
    records = _locked_records(path, email, secret)
    if records is None or not _key_ok(key):
        return None
    value = records.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        return None
    return value


def write_record(path: Path, email: object, secret: object, key: object, payload: object) -> None:
    """Replace one record. A bad seal leaves the file as it was."""
    if not _key_ok(key) or not isinstance(payload, str) or len(payload) > _PAYLOAD_LIMIT:
        raise AccountError("This account could not be saved.")
    seal = _secret_bytes(secret)
    if seal is None or not isinstance(email, str):
        raise AccountError("This account could not be saved.")
    with _LOCK:
        store = _load(path)
        account = store["accounts"].get(email)
        if not isinstance(account, dict):
            raise AccountError("This account could not be saved.")
        opened = _open_bundle(account.get("records"), seal)
        if opened is None:
            raise AccountError("This account could not be saved.")
        records, previous = opened
        if key not in records and len(records) >= _RECORD_LIMIT:
            raise AccountError("This account could not be saved.")
        if records.get(key) == payload and previous == key:
            return
        records[key] = payload
        account["records"] = _seal_records(records, seal, key)
        _save(path, store)


def record_keys(path: Path, email: object, secret: object, prefix: object) -> list[str] | None:
    """Keys on this account that start with prefix. None when the seal fails."""
    records = _locked_records(path, email, secret)
    if records is None or not isinstance(prefix, str):
        return None
    found = [key for key in records if key.startswith(prefix)]
    found.sort()
    return found


def last_key(path: Path, email: object, secret: object) -> str | None:
    """The plan key last saved, "" when this account has none, None when the seal fails."""
    bundle = _locked_bundle(path, email, secret)
    if bundle is None:
        return None
    records, last = bundle
    if last:
        return last
    if len(records) == 1:
        return next(iter(records))
    return ""


def issue_session(email: str, secret: str, *, now: int) -> str:
    """A signed token that holds the email, the seal key, and when it was issued.

    The account file is not changed. The signing key stays on this machine.
    """
    cleaned = normalize_email(email)
    seal = _secret_bytes(secret)
    issued = _unix_time(now)
    if cleaned is None or seal is None or issued is None:
        raise AccountError("This session could not be saved.")
    key = _session_signing_key(create=True)
    if key is None:
        raise AccountError("This session could not be saved.")
    payload = json.dumps(
        {"email": cleaned, "issued": issued, "seal": seal.hex()},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    sig = hmac.new(key, payload, hashlib.sha256).digest()
    return "v1." + payload.hex() + "." + sig.hex()


def open_session(token: object, *, now: int) -> tuple[str, str] | None:
    """The email and seal key when the signature matches and the token is under a day old."""
    issued_now = _unix_time(now)
    if issued_now is None or not isinstance(token, str) or not token or len(token) > _SESSION_TOKEN_LIMIT:
        return None
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "v1":
        return None
    try:
        payload = bytes.fromhex(parts[1])
        sig = bytes.fromhex(parts[2])
    except ValueError:
        return None
    key = _session_signing_key(create=False)
    if key is None:
        return None
    expected = hmac.new(key, payload, hashlib.sha256).digest()
    if len(sig) != len(expected) or not hmac.compare_digest(sig, expected):
        return None
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    email = parsed.get("email")
    cleaned = normalize_email(email)
    if not isinstance(email, str) or cleaned is None or cleaned != email:
        return None
    seal = _secret_bytes(parsed.get("seal"))
    if seal is None or parsed.get("seal") != seal.hex():
        return None
    issued = _unix_time(parsed.get("issued"))
    if issued is None:
        return None
    age = issued_now - issued
    if age < 0 or age >= _SESSION_MAX_AGE:
        return None
    return cleaned, seal.hex()


def _locked_records(path: Path, email: object, secret: object) -> dict[str, str] | None:
    bundle = _locked_bundle(path, email, secret)
    if bundle is None:
        return None
    return bundle[0]


def _locked_bundle(path: Path, email: object, secret: object) -> tuple[dict[str, str], str] | None:
    seal = _secret_bytes(secret)
    if seal is None or not isinstance(email, str):
        return None
    with _LOCK:
        store = _load(path)
        account = store["accounts"].get(email)
        if not isinstance(account, dict):
            return None
        return _open_bundle(account.get("records"), seal)


def _load(path: Path) -> dict:
    if not path.is_file():
        return {"version": 1, "accounts": {}}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AccountError("Accounts could not be read.") from exc
    if not isinstance(parsed, dict) or parsed.get("version") != 1:
        raise AccountError("Accounts could not be read.")
    accounts = parsed.get("accounts")
    if not isinstance(accounts, dict):
        raise AccountError("Accounts could not be read.")
    return parsed


def _save(path: Path, store: dict) -> None:
    text = json.dumps(store, separators=(",", ":"), sort_keys=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)
    except OSError as exc:
        raise AccountError("Accounts could not be saved.") from exc


def _login_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt + b"login",
        _ITERATIONS,
        dklen=_KEY_BYTES,
    )


def _seal_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt + b"seal",
        _ITERATIONS,
        dklen=_KEY_BYTES,
    )


def _salt_bytes(value: object) -> bytes | None:
    if not isinstance(value, str):
        return None
    try:
        salt = bytes.fromhex(value)
    except ValueError:
        return None
    if len(salt) != _SALT_BYTES:
        return None
    return salt


def _secret_bytes(value: object) -> bytes | None:
    if not isinstance(value, str):
        return None
    try:
        key = bytes.fromhex(value)
    except ValueError:
        return None
    if len(key) != _KEY_BYTES:
        return None
    return key


def _key_ok(value: object) -> bool:
    if not isinstance(value, str) or not value or len(value) > _KEY_LIMIT:
        return False
    for char in value:
        if ord(char) < 32 and char != "\n":
            return False
        if ord(char) == 127:
            return False
    return True


def _seal_records(records: dict[str, str], key: bytes, last: str = "") -> str:
    payload: dict[str, object] = {"records": records}
    if last:
        payload["last"] = last
    text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return _seal(text.encode("utf-8"), key)


def _open_records(token: object, key: bytes) -> dict[str, str] | None:
    opened = _open_bundle(token, key)
    if opened is None:
        return None
    return opened[0]


def _open_bundle(token: object, key: bytes) -> tuple[dict[str, str], str] | None:
    if not isinstance(token, str) or not token:
        return None
    raw = _open_seal(token, key)
    if raw is None:
        return None
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    found = parsed.get("records")
    if not isinstance(found, dict):
        return None
    cleaned: dict[str, str] = {}
    for name, value in found.items():
        if _key_ok(name) and isinstance(value, str) and len(value) <= _PAYLOAD_LIMIT:
            cleaned[name] = value
    last = parsed.get("last")
    if not isinstance(last, str) or not _key_ok(last) or last not in cleaned:
        last = ""
    return cleaned, last


def _seal(plaintext: bytes, key: bytes) -> str:
    """HMAC-SHA256 in counter mode, then a tag. The token is ASCII."""
    nonce = secrets.token_bytes(16)
    cipher = _xor(plaintext, _keystream(key, nonce, len(plaintext)))
    tag = hmac.new(_mac_key(key), nonce + cipher, hashlib.sha256).digest()
    return (b"\x01" + nonce + tag + cipher).hex()


def _open_seal(token: str, key: bytes) -> bytes | None:
    try:
        raw = bytes.fromhex(token)
    except ValueError:
        return None
    if len(raw) < 1 + 16 + 32 or raw[0] != 1:
        return None
    nonce = raw[1:17]
    tag = raw[17:49]
    cipher = raw[49:]
    expected = hmac.new(_mac_key(key), nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        return None
    return _xor(cipher, _keystream(key, nonce, len(cipher)))


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    enc = hmac.new(key, b"enc", hashlib.sha256).digest()
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac.new(enc, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def _mac_key(key: bytes) -> bytes:
    return hmac.new(key, b"mac", hashlib.sha256).digest()


def _xor(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))


def _unix_time(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _session_key_path() -> Path:
    """The local signing key. RIO_SESSION_KEY_PATH overrides it for a test."""
    override = os.environ.get("RIO_SESSION_KEY_PATH", "").strip()
    if override:
        return Path(override)
    return accounts_path().parent / "session.key"


def _session_signing_key(*, create: bool) -> bytes | None:
    """The key that signs session tokens. It is not written into the account file."""
    override = os.environ.get("RIO_SESSION_KEY", "").strip()
    if override:
        key = _secret_bytes(override)
        if key is None and create:
            raise AccountError("This session could not be saved.")
        return key
    path = _session_key_path()
    with _LOCK:
        if path.is_file():
            try:
                found = _secret_bytes(path.read_text(encoding="utf-8").strip())
            except (OSError, UnicodeError):
                found = None
            if found is None and create:
                raise AccountError("This session could not be saved.")
            return found
        if not create:
            return None
        key = secrets.token_bytes(_KEY_BYTES)
        temporary = path.with_name(path.name + ".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(key.hex(), encoding="utf-8")
            temporary.replace(path)
        except OSError as exc:
            raise AccountError("This session could not be saved.") from exc
        return key
