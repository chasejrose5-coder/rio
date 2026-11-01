# test_accounts.py — a local email and password. Each account keeps its own record.

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import SPEND_CAP_MICRO_USD
from ui.accounts import (
    AccountError,
    authenticate,
    create_account,
    last_key,
    normalize_email,
    password_ok,
    read_record,
    record_keys,
    write_record,
)
from ui.plan_store import dump_record, load_record, storage_key

INPUTS = ("2:02.9", "2026-04-19", "1:55.0", "2027-03-19")
OTHER = ("2:02.9", "2026-04-19", "1:55.0", "2027-03-20")


def _no_score(value: object) -> None:
    text = str(value).lower()
    if "probability" in text or "readiness" in text:
        raise AssertionError("a score was stored")


def test_email_and_password_rules() -> None:
    """An email is lowercase. A short password is refused."""
    if normalize_email("  Jay@Example.com ") != "jay@example.com":
        raise AssertionError(normalize_email("  Jay@Example.com "))
    for bad in ("", "jay", "jay@", "@example.com", "jay@localhost", "a b@example.com", None, 3):
        if normalize_email(bad) is not None:
            raise AssertionError(bad)
    if not password_ok("long-enough"):
        raise AssertionError("a usable password was refused")
    for bad in ("short", "", "has\nline", None, "x" * 129):
        if password_ok(bad):
            raise AssertionError(bad)


def _fresh_file() -> tuple[Path, Path]:
    directory = Path(tempfile.mkdtemp(prefix="rio-accounts-"))
    return directory, directory / "accounts.json"


def test_create_login_and_a_wrong_password() -> None:
    """Create signs in. The same email cannot be created twice. A wrong password does not."""
    directory, path = _fresh_file()
    try:
        email, secret = create_account(path, "Jay@Example.com", "correct-horse")
        if email != "jay@example.com" or not isinstance(secret, str) or len(secret) != 64:
            raise AssertionError(email)
        again = authenticate(path, "jay@example.com", "correct-horse")
        if again is None or again[0] != email or again[1] != secret:
            raise AssertionError(again)
        if authenticate(path, "jay@example.com", "wrong-password") is not None:
            raise AssertionError("a wrong password signed in")
        if authenticate(path, "missing@example.com", "correct-horse") is not None:
            raise AssertionError("a missing account signed in")
        if authenticate(path, "not-an-email", "correct-horse") is not None:
            raise AssertionError("a bad email signed in")
        try:
            create_account(path, "jay@example.com", "another-password")
        except AccountError as exc:
            if str(exc) != "An account with that email already exists.":
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("the same email was created twice")
        try:
            create_account(path, "second@example.com", "short")
        except AccountError as exc:
            if str(exc) != "Use at least 8 characters.":
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("a short password was stored")
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_each_account_keeps_its_own_plan() -> None:
    """The same four inputs are a different record on each account. The file hides them."""
    directory, path = _fresh_file()
    try:
        first, first_secret = create_account(path, "one@example.com", "password-one")
        second, second_secret = create_account(path, "two@example.com", "password-two")
        key = storage_key(INPUTS)
        other = storage_key(OTHER)
        left = dump_record({2: "not_hitting"}, {}, [])
        right = dump_record({3: "smashing"}, {}, [])
        extra = dump_record({1: "on_track"}, {}, [])
        _no_score(left)
        write_record(path, first, first_secret, key, left)
        write_record(path, first, first_secret, other, extra)
        write_record(path, second, second_secret, key, right)
        if read_record(path, first, first_secret, key) != left:
            raise AssertionError("the first account lost its record")
        if read_record(path, second, second_secret, key) != right:
            raise AssertionError("the second account saw the first record")
        if read_record(path, second, second_secret, other) != "":
            raise AssertionError("a missing record was invented")
        marks = load_record(read_record(path, first, first_secret, key))[0]
        if marks != {2: "not_hitting"}:
            raise AssertionError(marks)
        keys = record_keys(path, first, first_secret, "rio.plan.v1\n")
        if keys != sorted([key, other]):
            raise AssertionError(keys)
        if record_keys(path, second, second_secret, "rio.plan.v1\n") != [key]:
            raise AssertionError("the second account listed the first plan")
        raw = path.read_text(encoding="utf-8")
        if last_key(path, first, first_secret) != other:
            raise AssertionError(last_key(path, first, first_secret))
        if last_key(path, second, second_secret) != key:
            raise AssertionError("the second account kept the first plan")
        if last_key(path, first, second_secret) is not None:
            raise AssertionError("another account's key opened the last plan")
        if "password-one" in raw or "password-two" in raw:
            raise AssertionError("a password was written")
        if "not_hitting" in raw or "smashing" in raw or "2:02.9" in raw:
            raise AssertionError("a plan record was written in the clear")
        if read_record(path, second, first_secret, key) is not None:
            raise AssertionError("another account's key opened this record")
        try:
            write_record(path, second, first_secret, key, left)
        except AccountError:
            pass
        else:
            raise AssertionError("a bad key overwrote the record")
        if read_record(path, second, second_secret, key) != right:
            raise AssertionError("a bad key changed the record")
        parsed = json.loads(raw)
        token = parsed["accounts"]["one@example.com"]["records"]
        parsed["accounts"]["one@example.com"]["records"] = ("0" if token[0] != "0" else "1") + token[1:]
        path.write_text(json.dumps(parsed), encoding="utf-8")
        try:
            authenticate(path, "one@example.com", "password-one")
        except AccountError as exc:
            if str(exc) != "Accounts could not be read.":
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("a damaged file signed in")
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_accounts_stay_local_and_spend_stays_capped() -> None:
    """No engine, no model, no external auth. Prose spend stays at $25."""
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    source = (ROOT / "ui" / "accounts.py").read_text(encoding="utf-8")
    for token in (
        "engines",
        "explain(",
        "urlopen",
        "classify(",
        "sequence(",
        "adapt(",
        "prescribe(",
        "intervals",
        "probability",
        "readiness",
        "print(",
    ):
        if token in source:
            raise AssertionError(token)
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    gate = app.index("if _account_identity() is None:")
    nav = app.index("st.navigation(")
    if gate > nav or "_render_login()" not in app[gate:nav] or "st.stop()" not in app[gate:nav]:
        raise AssertionError("login is not the first screen")
    if "create_account(" not in app or "authenticate(" not in app or "Log out" not in app:
        raise AssertionError("login is not wired")
    if "https://intervals.icu" in app or "SPEND_CAP" in app:
        raise AssertionError("login started a pull or spend")
    for path in (ROOT / "engines").glob("*.py"):
        body = path.read_text(encoding="utf-8")
        if "ui.accounts" in body or "create_account" in body:
            raise AssertionError(f"{path.name} was changed for accounts")


def main() -> None:
    test_email_and_password_rules()
    test_create_login_and_a_wrong_password()
    test_each_account_keeps_its_own_plan()
    test_accounts_stay_local_and_spend_stays_capped()
    print("accounts ok")


if __name__ == "__main__":
    main()
