# accounts.py — email and a password hash. Each account keeps its own plan records.

"""A local account file. The password is hashed. Plan records are sealed with it.

The file seal is Fernet. Older HMAC-CTR seals still open. The hosted site
does not use this file. A signed token holds the email and the seal key for
one day so this machine can open the file again. The seal key is not written
to the account file. The name is stored with the account. No external auth
service. No model. No spend. No scores.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
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


def normalize_name(value: object) -> str | None:
    """A display name. A first name is enough. Blank is not a name."""
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or len(text) > 40:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in text):
        return None
    if not any(char.isalpha() for char in text):
        return None
    for char in text:
        if char.isalpha() or char in " '-.":
            continue
        return None
    return text


def shown_name(name: object, preferred: object) -> str:
    """The nickname when this account has one, otherwise the stored name."""
    if isinstance(preferred, str) and preferred.strip():
        return " ".join(preferred.split())
    if isinstance(name, str) and name.strip():
        return " ".join(name.split())
    return ""


def hey(name: object) -> str:
    """A short greeting. Blank when this account has no name."""
    text = shown_name(name, "")
    if not text:
        return ""
    return f"Hey, {text}"


def plan_title(name: object) -> str:
    """The plan line for this name. Blank when this account has no name."""
    text = shown_name(name, "")
    if not text:
        return ""
    return f"{text}'s plan"


def create_account(path: Path, email: object, password: object, name: object) -> tuple[str, str]:
    """Create one account and return its email and seal key.

    The name is stored with the account. The seal key opens that account's
    records for this session. A second create for the same email is refused.
    The password is not written.
    """
    cleaned = normalize_email(email)
    if cleaned is None:
        raise AccountError("Enter an email address.")
    stored_name = normalize_name(name)
    if stored_name is None:
        raise AccountError("Enter a name.")
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
            "name": stored_name,
            "profile": {"preferred": "", "settings": {}, "timezone": ""},
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


def account_rows(path: Path) -> list[dict[str, str]]:
    """Email and name for every account. Passwords, seals, and records stay out.

    The list is read only. Nothing here removes an account.
    """
    with _LOCK:
        store = _load(path)
    accounts = store.get("accounts")
    if not isinstance(accounts, dict):
        return []
    rows = []
    for email, account in accounts.items():
        if not isinstance(email, str) or not isinstance(account, dict):
            continue
        name = account.get("name")
        if not isinstance(name, str):
            name = ""
        rows.append({"email": email, "name": " ".join(name.split())})
    rows.sort(key=lambda row: row["email"])
    return rows


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


def read_local(path: Path, email: object) -> dict | None:
    """The stored name and local profile, or None when this email has no account.

    The seal is not required. A missing name is "".
    """
    cleaned = normalize_email(email)
    if cleaned is None:
        return None
    with _LOCK:
        store = _load(path)
        account = store["accounts"].get(cleaned)
        if not isinstance(account, dict):
            return None
        return _local_view(account)


def write_local(
    path: Path,
    email: object,
    secret: object,
    name: object,
    preferred: object,
    timezone: object,
    settings: object,
) -> dict:
    """Store the name and local profile. A bad seal leaves the file as it was."""
    cleaned = normalize_email(email)
    seal = _secret_bytes(secret)
    if cleaned is None or seal is None:
        raise AccountError("This account could not be saved.")
    with _LOCK:
        store = _load(path)
        account = store["accounts"].get(cleaned)
        if not isinstance(account, dict):
            raise AccountError("This account could not be saved.")
        if _open_bundle(account.get("records"), seal) is None:
            raise AccountError("This account could not be saved.")
        current = _local_view(account)
        nxt = {
            "name": _apply_name(current["name"], name),
            "preferred": _apply_preferred(preferred),
            "settings": _clean_settings(settings),
            "timezone": _apply_zone(timezone, current["timezone"]),
        }
        _keep_easy(nxt, current)
        if nxt != current:
            account["name"] = nxt["name"]
            account["profile"] = _profile_payload(nxt)
            _save(path, store)
        return nxt


def write_easy_pace(
    path: Path,
    email: object,
    secret: object,
    pace: object,
    unit: object,
) -> dict:
    """Store this athlete's easy pace. A bad seal or pace leaves the file as it was."""
    cleaned = normalize_email(email)
    seal = _secret_bytes(secret)
    easy = _accept_easy(pace, unit)
    if cleaned is None or seal is None or easy is None:
        raise AccountError("Enter a pace like 7:25.")
    with _LOCK:
        store = _load(path)
        account = store["accounts"].get(cleaned)
        if not isinstance(account, dict):
            raise AccountError("Enter a pace like 7:25.")
        if _open_bundle(account.get("records"), seal) is None:
            raise AccountError("Enter a pace like 7:25.")
        current = _local_view(account)
        nxt = dict(current)
        nxt["easy_pace"] = easy[0]
        nxt["easy_pace_unit"] = easy[1]
        if nxt != current:
            account["name"] = nxt["name"]
            account["profile"] = _profile_payload(nxt)
            _save(path, store)
        return nxt


def change_password(path: Path, email: object, secret: object, current: object, new: object) -> str:
    """Replace the password and return the new seal key. Records are sealed again."""
    cleaned = normalize_email(email)
    if cleaned is None:
        raise AccountError("This account could not be saved.")
    if not isinstance(new, str) or not password_ok(new):
        raise AccountError("Use at least 8 characters.")
    if not isinstance(current, str) or not password_ok(current):
        raise AccountError("Password does not match.")
    seal = _secret_bytes(secret)
    if seal is None:
        raise AccountError("This account could not be saved.")
    with _LOCK:
        store = _load(path)
        account = store["accounts"].get(cleaned)
        if not isinstance(account, dict):
            raise AccountError("This account could not be saved.")
        if not _password_matches(account, current):
            raise AccountError("Password does not match.")
        opened = _open_bundle(account.get("records"), seal)
        if opened is None:
            raise AccountError("This account could not be saved.")
        records, last = opened
        salt = secrets.token_bytes(_SALT_BYTES)
        nxt = _seal_key(new, salt)
        account["salt"] = salt.hex()
        account["login"] = _login_hash(new, salt).hex()
        account["records"] = _seal_records(records, nxt, last)
        _save(path, store)
    return nxt.hex()


def change_email(path: Path, email: object, secret: object, password: object, new_email: object) -> str:
    """Move this account to another email. The seal key stays the same."""
    cleaned = normalize_email(email)
    target = normalize_email(new_email)
    if cleaned is None or target is None:
        raise AccountError("Enter an email address.")
    if not isinstance(password, str) or not password_ok(password):
        raise AccountError("Password does not match.")
    seal = _secret_bytes(secret)
    if seal is None:
        raise AccountError("This account could not be saved.")
    with _LOCK:
        store = _load(path)
        account = store["accounts"].get(cleaned)
        if not isinstance(account, dict):
            raise AccountError("This account could not be saved.")
        if not _password_matches(account, password):
            raise AccountError("Password does not match.")
        if _open_bundle(account.get("records"), seal) is None:
            raise AccountError("This account could not be saved.")
        if target == cleaned:
            return cleaned
        if target in store["accounts"]:
            raise AccountError("An account with that email already exists.")
        store["accounts"][target] = account
        del store["accounts"][cleaned]
        _save(path, store)
    return target


def delete_account(path: Path, email: object, secret: object, password: object) -> None:
    """Remove this account after the password matches. Its records go with it."""
    cleaned = normalize_email(email)
    if cleaned is None:
        raise AccountError("This account could not be saved.")
    if not isinstance(password, str) or not password_ok(password):
        raise AccountError("Password does not match.")
    seal = _secret_bytes(secret)
    if seal is None:
        raise AccountError("This account could not be saved.")
    with _LOCK:
        store = _load(path)
        account = store["accounts"].get(cleaned)
        if not isinstance(account, dict):
            raise AccountError("This account could not be saved.")
        if not _password_matches(account, password):
            raise AccountError("Password does not match.")
        if _open_bundle(account.get("records"), seal) is None:
            raise AccountError("This account could not be saved.")
        del store["accounts"][cleaned]
        _save(path, store)


def delete_records(path: Path, email: object, secret: object, prefix: object) -> None:
    """Remove saved records whose key starts with prefix. The account stays."""
    if not isinstance(prefix, str) or len(prefix) < 8 or len(prefix) > _KEY_LIMIT:
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
        records, last = opened
        kept = {key: value for key, value in records.items() if not key.startswith(prefix)}
        if len(kept) == len(records):
            return
        if last not in kept:
            last = ""
        account["records"] = _seal_records(kept, seal, last)
        _save(path, store)


def delete_exact(path: Path, email: object, secret: object, keys: object) -> None:
    """Remove these records. Every other key on this account stays."""
    if not isinstance(keys, (list, tuple)) or not keys:
        raise AccountError("This season could not be deleted.")
    wanted: list[str] = []
    for key in keys:
        if not _key_ok(key):
            raise AccountError("This season could not be deleted.")
        if key not in wanted:
            wanted.append(key)
    seal = _secret_bytes(secret)
    if seal is None or not isinstance(email, str):
        raise AccountError("This season could not be deleted.")
    with _LOCK:
        store = _load(path)
        account = store["accounts"].get(email)
        if not isinstance(account, dict):
            raise AccountError("This season could not be deleted.")
        opened = _open_bundle(account.get("records"), seal)
        if opened is None:
            raise AccountError("This season could not be deleted.")
        records, last = opened
        kept = {key: value for key, value in records.items() if key not in wanted}
        if len(kept) == len(records):
            return
        if last not in kept:
            last = ""
        account["records"] = _seal_records(kept, seal, last)
        _save(path, store)


def delete_past_season(path: Path, email: object, secret: object, inputs: object, today: object) -> None:
    """Remove one past season and the profile stored with those four inputs.

    A current season is left as it is. Another season's records stay.
    """
    from datetime import date

    from ui.past_seasons import is_past_season
    from ui.plan_store import storage_key
    from ui.profile import profile_key

    if type(today) is not date or not is_past_season(inputs, today):
        raise AccountError("The current season can't be deleted.")
    delete_exact(path, email, secret, [storage_key(inputs), profile_key(inputs)])


def _local_view(account: dict) -> dict:
    raw_name = account.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) else ""
    profile = account.get("profile")
    if not isinstance(profile, dict):
        profile = {}
    preferred = profile.get("preferred")
    preferred = preferred.strip() if isinstance(preferred, str) else ""
    timezone = profile.get("timezone")
    if not _zone_ok(timezone):
        timezone = ""
    view = {
        "name": name,
        "preferred": preferred,
        "settings": _clean_settings(profile.get("settings")),
        "timezone": timezone,
    }
    easy = _accept_easy(profile.get("easy_pace"), profile.get("easy_pace_unit"))
    if easy is not None:
        view["easy_pace"] = easy[0]
        view["easy_pace_unit"] = easy[1]
    return view


def _apply_name(current: str, proposed: object) -> str:
    if not isinstance(proposed, str) or not proposed.strip():
        if current:
            raise AccountError("Enter a name.")
        return ""
    cleaned = normalize_name(proposed)
    if cleaned is None:
        raise AccountError("Enter a name.")
    return cleaned


def _apply_preferred(proposed: object) -> str:
    if not isinstance(proposed, str) or not proposed.strip():
        return ""
    cleaned = normalize_name(proposed)
    if cleaned is None:
        raise AccountError("That nickname will not work.")
    return cleaned


def _zone_ok(value: object) -> bool:
    if not isinstance(value, str) or not value or len(value) > 64:
        return False
    for char in value:
        if char.isalnum() or char in "+-_/":
            continue
        return False
    return True


def _apply_zone(proposed: object, current: str) -> str:
    if _zone_ok(proposed):
        return str(proposed)
    if _zone_ok(current):
        return current
    return "UTC"


_EASY_PACE = re.compile(r"^(\d{1,2}):([0-5]\d)$")
_EASY_TRAIL = re.compile(r"^\d{1,2}:[0-5]\d\.0+$")


def _accept_easy(pace: object, unit: object) -> tuple[str, str] | None:
    """A stored easy pace, or None. The same bounds as the pace screen."""
    if unit not in ("mi", "km") or not isinstance(pace, str):
        return None
    text = pace.strip()
    if _EASY_TRAIL.fullmatch(text):
        text = text.split(".", 1)[0]
    found = _EASY_PACE.fullmatch(text)
    if found is None:
        return None
    minutes = int(found.group(1))
    seconds = int(found.group(2))
    total = minutes * 60 + seconds
    if total < 60 or total > 30 * 60:
        return None
    return f"{minutes}:{seconds:02d}", unit


def _keep_easy(nxt: dict, current: dict) -> None:
    """A settings save does not drop an easy pace already on this profile."""
    if "easy_pace" in current and "easy_pace_unit" in current:
        nxt["easy_pace"] = current["easy_pace"]
        nxt["easy_pace_unit"] = current["easy_pace_unit"]


def _profile_payload(view: dict) -> dict:
    payload = {
        "preferred": view["preferred"],
        "settings": view["settings"],
        "timezone": view["timezone"],
    }
    if "easy_pace" in view and "easy_pace_unit" in view:
        payload["easy_pace"] = view["easy_pace"]
        payload["easy_pace_unit"] = view["easy_pace_unit"]
    return payload


def _clean_settings(value: object) -> dict:
    if not isinstance(value, dict):
        return {}
    cleaned: dict = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key or len(key) > 40:
            continue
        if any(ord(char) < 32 or ord(char) == 127 for char in key):
            continue
        if isinstance(item, bool):
            cleaned[key] = item
            continue
        if not isinstance(item, str):
            continue
        text = item.strip()
        if not text or len(text) > 64:
            continue
        if any(ord(char) < 32 or ord(char) == 127 for char in text):
            continue
        cleaned[key] = text
    return cleaned


def _password_matches(account: dict, password: str) -> bool:
    salt = _salt_bytes(account.get("salt"))
    login = account.get("login")
    if salt is None or not isinstance(login, str):
        raise AccountError("Accounts could not be read.")
    found = _login_hash(password, salt).hex()
    if len(login) != len(found):
        return False
    return hmac.compare_digest(found, login)


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
    """Fernet authenticated encryption. The token is ASCII."""
    from cryptography.fernet import Fernet

    token = Fernet(_fernet_key(key)).encrypt(plaintext)
    return "f2." + token.decode("ascii")


def _open_seal(token: str, key: bytes) -> bytes | None:
    if isinstance(token, str) and token.startswith("f2."):
        from cryptography.fernet import Fernet, InvalidToken

        try:
            return Fernet(_fernet_key(key)).decrypt(token[3:].encode("ascii"))
        except (InvalidToken, ValueError, TypeError):
            return None
    return _open_legacy_seal(token, key)


def _fernet_key(key: bytes) -> bytes:
    return base64.urlsafe_b64encode(key)


def _legacy_seal(plaintext: bytes, key: bytes) -> str:
    """Old HMAC-CTR seal. New writes do not use this. Old files still open."""
    nonce = secrets.token_bytes(16)
    cipher = _xor(plaintext, _keystream(key, nonce, len(plaintext)))
    tag = hmac.new(_mac_key(key), nonce + cipher, hashlib.sha256).digest()
    return (b"\x01" + nonce + tag + cipher).hex()


def _open_legacy_seal(token: str, key: bytes) -> bytes | None:
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
    try:
        return _xor(cipher, _keystream(key, nonce, len(cipher)))
    except ValueError:
        return None


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
    return bytes(a ^ b for a, b in zip(left, right, strict=True))


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
