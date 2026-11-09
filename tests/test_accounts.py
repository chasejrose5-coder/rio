# test_accounts.py — a local email and password. Each account keeps its own record.

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import SPEND_CAP_MICRO_USD
from ui.accounts import (
    AccountError,
    authenticate,
    change_email,
    change_password,
    create_account,
    delete_account,
    delete_records,
    hey,
    issue_session,
    last_key,
    normalize_email,
    normalize_name,
    open_session,
    password_ok,
    plan_title,
    read_local,
    read_record,
    record_keys,
    shown_name,
    write_local,
    write_record,
)
from ui.past_seasons import has_active_plan
from ui.plan_store import dump_record, load_record, storage_key
from ui.profile import profile_key

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
        email, secret = create_account(path, "Jay@Example.com", "correct-horse", "Jay")
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
            create_account(path, "jay@example.com", "another-password", "Jay")
        except AccountError as exc:
            if str(exc) != "An account with that email already exists.":
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("the same email was created twice")
        try:
            create_account(path, "second@example.com", "short", "Ada")
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
        first, first_secret = create_account(path, "one@example.com", "password-one", "One")
        second, second_secret = create_account(path, "two@example.com", "password-two", "Two")
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


def test_an_active_plan_is_a_goal_still_ahead() -> None:
    """Today or later is active. No plan, or a past goal, is not."""
    today = date(2026, 11, 1)
    current = ("2:02.9", "2026-04-19", "1:55.0", "2026-11-01")
    later = ("2:02.9", "2026-04-19", "1:55.0", "2027-03-19")
    finished = ("2:10.0", "2025-01-04", "2:00.0", "2026-10-31")
    if not has_active_plan([storage_key(current)], today):
        raise AssertionError("a goal today was finished")
    if not has_active_plan([storage_key(later)], today):
        raise AssertionError("a later goal was finished")
    if not has_active_plan([storage_key(finished), storage_key(later)], today):
        raise AssertionError("a later goal was ignored")
    if has_active_plan([storage_key(finished)], today):
        raise AssertionError("a past goal was active")
    if has_active_plan([], today) or has_active_plan(None, today) or has_active_plan("", today):
        raise AssertionError("a missing plan was active")
    if has_active_plan([profile_key(later)], today):
        raise AssertionError("a profile record was a season")
    _no_score(has_active_plan([storage_key(later)], today))


def _restore_env(saved: dict[str, str | None]) -> None:
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def test_a_signed_token_lasts_one_day() -> None:
    """The token holds the email and seal key, and it dies at one day.

    The account file is unchanged. Another signing key cannot open it.
    """
    directory, path = _fresh_file()
    saved = {
        "RIO_SESSION_KEY": os.environ.get("RIO_SESSION_KEY"),
        "RIO_SESSION_KEY_PATH": os.environ.get("RIO_SESSION_KEY_PATH"),
    }
    try:
        os.environ["RIO_SESSION_KEY"] = "ab" * 32
        os.environ.pop("RIO_SESSION_KEY_PATH", None)
        email, secret = create_account(path, "Jay@Example.com", "correct-horse", "Jay")
        before = path.read_bytes()
        now = 1_700_000_000
        token = issue_session(email, secret, now=now)
        if path.read_bytes() != before:
            raise AssertionError("issuing a token rewrote the account file")
        stored = path.read_text(encoding="utf-8")
        if secret in stored or token in stored or "correct-horse" in stored:
            raise AssertionError("the seal key was written to the account file")
        payload = bytes.fromhex(token.split(".")[1]).decode("utf-8")
        if email not in payload or secret not in payload:
            raise AssertionError("the token does not hold the email and seal key")
        if "correct-horse" in payload or "probability" in payload or "readiness" in payload:
            raise AssertionError("the token holds a password or a score")
        if open_session(token, now=now) != (email, secret):
            raise AssertionError("a fresh token did not open")
        day = 24 * 60 * 60
        if open_session(token, now=now + day - 1) != (email, secret):
            raise AssertionError("a token under a day was dropped")
        if open_session(token, now=now + day) is not None:
            raise AssertionError("a day-old token was kept")
        if open_session(token, now=now - 1) is not None:
            raise AssertionError("a token from the future was kept")
        flipped = token[:-1] + ("0" if token[-1] != "0" else "1")
        if open_session(flipped, now=now) is not None:
            raise AssertionError("a changed token was accepted")
        for bad in ("", None, "v1.zz.zz", "nope"):
            if open_session(bad, now=now) is not None:
                raise AssertionError(bad)
        try:
            issue_session(email, secret, now=True)
        except AccountError as exc:
            if str(exc) != "This session could not be saved.":
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("a bad time was signed")
        os.environ["RIO_SESSION_KEY"] = "cd" * 32
        if open_session(token, now=now) is not None:
            raise AssertionError("another key opened the token")
        if (directory / "session.key").exists():
            raise AssertionError("the env key was written to disk")
        os.environ.pop("RIO_SESSION_KEY", None)
        key_file = directory / "session.key"
        os.environ["RIO_SESSION_KEY_PATH"] = str(key_file)
        file_token = issue_session(email, secret, now=now)
        if path.read_bytes() != before:
            raise AssertionError("the signing key was written into the account file")
        if not key_file.is_file() or key_file.resolve() == path.resolve():
            raise AssertionError("the signing key is not a local file of its own")
        if secret in path.read_text(encoding="utf-8") or file_token in path.read_text(encoding="utf-8"):
            raise AssertionError("the seal key was written to the account file")
        if open_session(file_token, now=now) != (email, secret):
            raise AssertionError("the local key did not open the token")
        if open_session(token, now=now) is not None:
            raise AssertionError("a token from another key was accepted")
        _no_score(payload)
    finally:
        _restore_env(saved)
        shutil.rmtree(directory, ignore_errors=True)


def test_a_reload_restores_the_token_and_logout_clears_it() -> None:
    """Page load restores a young token. Log out and an old token clear it."""
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    source = (ROOT / "ui" / "accounts.py").read_text(encoding="utf-8")
    if "24 * 60 * 60" not in source:
        raise AssertionError("a session does not last one day")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    enter = app[app.index("def _enter_account(") : app.index("def _render_create_account(")]
    if "issue_session(" not in enter or '["rio_session_token"]' not in enter:
        raise AssertionError("login does not store a signed token")
    if "rio_reset_session" in enter:
        raise AssertionError("login sets rio_reset_session")
    sign_out = app[app.index("def _sign_out(") : app.index("def _restore_session(")]
    if 'pop("rio_session_token"' not in sign_out or "rio_session_clear" not in sign_out:
        raise AssertionError("logout does not clear the token")
    restore = app[app.index("def _restore_session(") : app.index("def _restore_record(")]
    if "open_session(" not in restore or "rio_session_clear" not in restore:
        raise AssertionError("a page load does not check the token")
    if "_sign_out()" not in restore:
        raise AssertionError("an old token stays signed in")
    if "authenticate(" in restore or "create_account(" in restore or "write_record(" in restore:
        raise AssertionError("a page load signs in again")
    boot = app[app.index("\nst.set_page_config(") :]
    gate_at = boot.index("if _account_identity() is None:")
    if "_restore_session()" not in boot[:gate_at]:
        raise AssertionError("a page load does not restore the session")
    session_js = app[app.index("_SESSION_STORE_JS") : app.index("def _session_component(")]
    if "rio.session.v1" not in session_js or "localStorage.removeItem" not in session_js:
        raise AssertionError("the session token is not stored in this browser")
    if "localStorage.setItem" not in session_js or "localStorage.getItem" not in session_js:
        raise AssertionError("login does not store the token in this browser")
    blob = enter + sign_out + restore + session_js
    if "probability" in blob.lower() or "readiness" in blob.lower():
        raise AssertionError("a score was added")
    if "https://intervals.icu" in app or "SPEND_CAP" in app:
        raise AssertionError("login started a pull or spend")


def test_a_reload_opens_home_when_a_plan_is_still_ahead() -> None:
    """A valid token on page load opens Home or Start. The token check stays."""
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    restore = app[app.index("def _restore_session(") : app.index("def _restore_record(")]
    if "rio_enter" in restore or "has_active_plan(" in restore or "switch_page(" in restore:
        raise AssertionError("a page load changed the token check")
    if "authenticate(" in restore or "create_account(" in restore or "issue_session(" in restore:
        raise AssertionError("a page load changed the token check")
    opened = app[app.index("def _open_restored_session(") : app.index("def _route_after_login(")]
    if '["rio_enter"]' not in opened or "_account_identity()" not in opened:
        raise AssertionError("a reload does not choose a page")
    if "was_signed_in" not in opened:
        raise AssertionError("a reload moves a session that was already open")
    for token in (
        "open_session(",
        "authenticate(",
        "create_account(",
        "issue_session(",
        "write_record(",
        "sequence(",
        "read_record(",
        "has_active_plan(",
    ):
        if token in opened:
            raise AssertionError("a reload rechecked the token or rebuilt a plan")
    boot = app[app.index("\nst.set_page_config(") :]
    gate_at = boot.index("if _account_identity() is None:")
    head = boot[:gate_at]
    if head.index("_open_restored_session(") < head.index("_restore_session()"):
        raise AssertionError("a reload routes before the token is restored")
    wrapped = app[app.index("def _with_plan(") : app.index("def _fresh_value(")]
    if 'get("rio_enter")' not in wrapped or "_route_after_login()" not in wrapped:
        raise AssertionError("a reload does not open Home or Start")
    route = app[app.index("def _route_after_login(") : app.index("def _with_plan(")]
    if "has_active_plan(" not in route or '_nav_page("Home")' not in route or "_start_page" not in route:
        raise AssertionError("a reload does not choose Home or Start")
    if "_athlete_today()" not in route:
        raise AssertionError("a reload does not use today")
    blob = opened + route
    if "probability" in blob.lower() or "readiness" in blob.lower():
        raise AssertionError("a score was added")
    if "https://intervals.icu" in app or "SPEND_CAP" in app:
        raise AssertionError("a reload started a pull or spend")


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
    enter = app[app.index("def _enter_account(") : app.index("def _render_create_account(")]
    create = app[app.index("def _render_create_account(") : app.index("def _render_login(")]
    login = app[app.index("def _render_login(") : app.index("\nst.set_page_config(")]
    route = app[app.index("def _route_after_login(") : app.index("def _with_plan(")]
    if "rio_reset_session" in enter or "rio_reset_session" in create or "rio_reset_session" in login:
        raise AssertionError("login sets rio_reset_session")
    if '["rio_account"]' not in enter or '["rio_account_secret"]' not in enter or '["rio_enter"]' not in enter:
        raise AssertionError("login does not set the account")
    if "_render_create_account()" not in login or "Log in" not in login or "Create account" not in login:
        raise AssertionError("create account is not its own screen")
    if "Back to log in" not in create or "Create account" not in create or "create_account(" not in create:
        raise AssertionError("create account is missing its screen")
    if 'st.text_input("Name"' not in create or "create_account(accounts_path(), email, password, name)" not in create:
        raise AssertionError("create account does not ask for a name")
    if "authenticate(" not in login:
        raise AssertionError("log in is missing its screen")
    if "has_active_plan(" not in route or '_nav_page("Home")' not in route or "_start_page" not in route:
        raise AssertionError("login does not choose Home or Start")
    if "st.switch_page(" not in route:
        raise AssertionError("login does not open a page")
    for token in (
        "sequence(",
        "write_record(",
        "_store_plan(",
        "_ensure_linked_plan(",
        "_restore_last_plan(",
        "read_record(",
    ):
        if token in route:
            raise AssertionError("login changed how a plan is stored or loaded")
    if "probability" in (enter + create + login + route).lower() or "readiness" in (
        enter + create + login + route
    ).lower():
        raise AssertionError("a score was added")
    if "https://intervals.icu" in app or "SPEND_CAP" in app:
        raise AssertionError("login started a pull or spend")
    for path in (ROOT / "engines").glob("*.py"):
        body = path.read_text(encoding="utf-8")
        if "ui.accounts" in body or "create_account" in body:
            raise AssertionError(f"{path.name} was changed for accounts")


def test_a_name_is_stored_with_the_account() -> None:
    """Create requires a name. Home can greet it. The password stays hashed."""
    if normalize_name("  Chase  ") != "Chase":
        raise AssertionError(normalize_name("  Chase  "))
    if normalize_name("Mary-Jane") != "Mary-Jane" or normalize_name("O'Brien") != "O'Brien":
        raise AssertionError("a real name was refused")
    for bad in ("", "   ", "123", "Chase!", None, "x" * 41):
        if normalize_name(bad) is not None:
            raise AssertionError(bad)
    if hey(shown_name("Chase", "")) != "Hey, Chase":
        raise AssertionError(hey(shown_name("Chase", "")))
    if hey(shown_name("Chase", "CJ")) != "Hey, CJ":
        raise AssertionError("the nickname was ignored")
    if plan_title(shown_name("Chase", "")) != "Chase's plan":
        raise AssertionError(plan_title("Chase"))
    if hey("") or plan_title("") or hey(None) or plan_title(None):
        raise AssertionError("a missing name grew a greeting")
    directory, path = _fresh_file()
    try:
        try:
            create_account(path, "ada@example.com", "correct-horse", "  ")
        except AccountError as exc:
            if str(exc) != "Enter a name.":
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("a blank name was stored")
        email, secret = create_account(path, "Ada@Example.com", "correct-horse", "  Chase ")
        local = read_local(path, email)
        if local is None or local["name"] != "Chase" or local["preferred"] != "":
            raise AssertionError(local)
        raw = path.read_text(encoding="utf-8")
        if "Chase" not in raw or "correct-horse" in raw:
            raise AssertionError("the name was hidden or the password was written")
        saved = write_local(
            path,
            email,
            secret,
            "Chase",
            "CJ",
            "America/Los_Angeles",
            {"units": "miles", "reminders": True},
        )
        if saved["preferred"] != "CJ" or saved["timezone"] != "America/Los_Angeles":
            raise AssertionError(saved)
        if saved["settings"].get("units") != "miles" or saved["settings"].get("reminders") is not True:
            raise AssertionError(saved["settings"])
        if read_local(path, email) != saved:
            raise AssertionError("the profile did not stay on the account")
        try:
            write_local(path, email, secret, "", "CJ", "UTC", {})
        except AccountError as exc:
            if str(exc) != "Enter a name.":
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("the name was cleared")
        if read_local(path, email)["name"] != "Chase":
            raise AssertionError("a refused edit changed the name")
        try:
            write_local(path, email, "ab" * 32, "Chase", "CJ", "UTC", {})
        except AccountError:
            pass
        else:
            raise AssertionError("a bad seal changed the profile")
        if read_local(path, email)["preferred"] != "CJ":
            raise AssertionError("a bad seal changed the nickname")
        _no_score(saved)
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_password_email_and_delete_stay_on_the_account() -> None:
    """A new password reseals records. Email moves. Delete removes the account."""
    directory, path = _fresh_file()
    try:
        email, secret = create_account(path, "chase@example.com", "correct-horse", "Chase")
        key = storage_key(INPUTS)
        payload = dump_record({2: "on_track"}, {}, [])
        write_record(path, email, secret, key, payload)
        before = path.read_bytes()
        try:
            change_password(path, email, secret, "wrong-password", "another-password")
        except AccountError as exc:
            if str(exc) != "Password does not match.":
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("a wrong password was accepted")
        if path.read_bytes() != before:
            raise AssertionError("a wrong password changed the file")
        try:
            change_password(path, email, secret, "correct-horse", "short")
        except AccountError as exc:
            if str(exc) != "Use at least 8 characters.":
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("a short password replaced the old one")
        new_secret = change_password(path, email, secret, "correct-horse", "new-password-1")
        if new_secret == secret or authenticate(path, email, "correct-horse") is not None:
            raise AssertionError("the old password still signs in")
        again = authenticate(path, email, "new-password-1")
        if again != (email, new_secret):
            raise AssertionError(again)
        if read_record(path, email, new_secret, key) != payload:
            raise AssertionError("the new password lost the record")
        if read_record(path, email, secret, key) is not None:
            raise AssertionError("the old seal still opens the record")
        if read_local(path, email)["name"] != "Chase":
            raise AssertionError("a new password dropped the name")
        if "new-password-1" in path.read_text(encoding="utf-8") or "correct-horse" in path.read_text(encoding="utf-8"):
            raise AssertionError("a password was written")
        other, _other_secret = create_account(path, "other@example.com", "other-password", "Other")
        try:
            change_email(path, email, new_secret, "new-password-1", other)
        except AccountError as exc:
            if str(exc) != "An account with that email already exists.":
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("two accounts share an email")
        moved = change_email(path, email, new_secret, "new-password-1", "New@Example.com")
        if moved != "new@example.com":
            raise AssertionError(moved)
        if authenticate(path, email, "new-password-1") is not None:
            raise AssertionError("the old email still signs in")
        if authenticate(path, moved, "new-password-1") != (moved, new_secret):
            raise AssertionError("the new email did not keep the seal")
        if read_record(path, moved, new_secret, key) != payload:
            raise AssertionError("the move dropped the record")
        if read_local(path, moved)["name"] != "Chase":
            raise AssertionError("the move dropped the name")
        try:
            delete_account(path, moved, new_secret, "wrong-password")
        except AccountError as exc:
            if str(exc) != "Password does not match.":
                raise AssertionError(exc) from exc
        else:
            raise AssertionError("a wrong password deleted the account")
        if read_local(path, moved)["name"] != "Chase":
            raise AssertionError("a refused delete removed the account")
        delete_account(path, moved, new_secret, "new-password-1")
        if read_local(path, moved) is not None or authenticate(path, moved, "new-password-1") is not None:
            raise AssertionError("the account was still there")
        if read_local(path, other)["name"] != "Other":
            raise AssertionError("another account was removed")
        _no_score(payload)
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def test_reset_removes_seasons_and_keeps_the_account() -> None:
    """Plan records can be removed. The name and the account stay."""
    directory, path = _fresh_file()
    try:
        email, secret = create_account(path, "chase@example.com", "correct-horse", "Chase")
        plan_key = storage_key(INPUTS)
        other_key = "rio.note.v1\nkeep"
        write_record(path, email, secret, plan_key, dump_record({1: "on_track"}, {}, []))
        write_record(path, email, secret, other_key, "note")
        delete_records(path, email, secret, "rio.plan.v1\n")
        if record_keys(path, email, secret, "rio.plan.v1\n") != []:
            raise AssertionError("a plan record stayed")
        if read_record(path, email, secret, other_key) != "note":
            raise AssertionError("a reset removed more than the plan")
        if read_local(path, email)["name"] != "Chase":
            raise AssertionError("a reset removed the account")
        if last_key(path, email, secret) != other_key:
            raise AssertionError(last_key(path, email, secret))
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def main() -> None:
    test_email_and_password_rules()
    test_create_login_and_a_wrong_password()
    test_each_account_keeps_its_own_plan()
    test_an_active_plan_is_a_goal_still_ahead()
    test_a_signed_token_lasts_one_day()
    test_a_reload_restores_the_token_and_logout_clears_it()
    test_a_reload_opens_home_when_a_plan_is_still_ahead()
    test_accounts_stay_local_and_spend_stays_capped()
    test_a_name_is_stored_with_the_account()
    test_password_email_and_delete_stay_on_the_account()
    test_reset_removes_seasons_and_keeps_the_account()
    print("accounts ok")


if __name__ == "__main__":
    main()
