# account_flow.py — create, reset, change, and delete. Streamlit stays the live UI.

"""Hosted calls go through the directory. Local calls use the account file.

Google uses the same directory.google_url and exchange_code the Streamlit
callback already uses. The redirect defaults to the Streamlit app URL.
"""

from __future__ import annotations

import os
import time
from urllib.parse import parse_qs, urlparse

from api.errors import ApiError
from api.identity import Principal, update_local_session
from ui.accounts import (
    AccountError,
    change_email,
    change_password,
    create_account,
    delete_account,
    delete_exact,
    record_keys,
)
from ui.cloud_config import app_url
from ui.cloud_store import (
    ACCOUNTS_UNAVAILABLE,
    SIGNUP_CONFIRM,
    CloudAuthError,
    MemoryDirectory,
)
GOOGLE_REDIRECT_ENV = "RIO_GOOGLE_REDIRECT_URI"


def google_redirect_uri() -> str:
    """Where Google sends the browser. Unset keeps the Streamlit callback."""
    raw = os.environ.get(GOOGLE_REDIRECT_ENV, "").strip()
    if raw:
        return raw
    return app_url().rstrip("/") + "/"


def service_key_for(directory) -> str:
    """The server key for admin deletes. The memory stand-in accepts any non-empty key."""
    if directory is None:
        return ""
    found = getattr(directory, "service_key", None)
    if isinstance(found, str) and found.strip():
        return found
    if isinstance(directory, MemoryDirectory):
        return "memory-service"
    return ""


def _rate(message: str) -> bool:
    text = message.lower()
    return "too many" in text or "wait a few minutes" in text


def raise_auth(exc: CloudAuthError | AccountError) -> None:
    message = str(exc)
    if _rate(message):
        raise ApiError(429, message) from exc
    raise ApiError(400, message) from exc


def open_hosted(directory, session: dict) -> tuple[str, int]:
    """Store the tokens and return the cookie id. The session is not the cookie."""
    if not isinstance(session, dict) or not session.get("access_token"):
        raise CloudAuthError("Sign in again.")
    issued = int(time.time())
    record = {
        "access_token": session.get("access_token"),
        "refresh_token": session.get("refresh_token") or "",
        "user_id": session.get("user_id") or "",
        "email": session.get("email") or "",
        "display_name": session.get("display_name") or "",
        "issued_at": issued,
    }
    sid = directory.save_hosted_session(record)
    return sid, issued


def sign_up_hosted(directory, email: str, password: str, name: str) -> dict:
    """Create the account. A confirmation-only project returns no session."""
    try:
        session = directory.sign_up(email, password, name)
    except CloudAuthError as exc:
        if str(exc) == SIGNUP_CONFIRM:
            return {"confirm": True, "message": SIGNUP_CONFIRM}
        raise_auth(exc)
    if not isinstance(session, dict) or not session.get("access_token"):
        return {"confirm": True, "message": SIGNUP_CONFIRM}
    try:
        sid, issued = open_hosted(directory, session)
    except CloudAuthError as exc:
        raise_auth(exc)
    return {
        "confirm": False,
        "sid": sid,
        "issued": issued,
        "email": session.get("email") or "",
        "display_name": session.get("display_name") or "",
        "kind": "hosted",
    }


def forgot_password(directory, email: str) -> dict:
    """Send the reset mail. An unknown address gets the same sentence."""
    from ui.accounts import normalize_email

    if directory is None:
        raise ApiError(400, "Password reset is not available for this account.")
    if normalize_email(email) is None:
        raise ApiError(400, "Enter an email address.")
    try:
        directory.request_reset(email)
    except CloudAuthError as exc:
        raise_auth(exc)
    return {"ok": True, "message": "Check your email for the reset link."}


def reset_password(directory, token: str, password: str) -> dict:
    if directory is None:
        raise ApiError(400, "Password reset is not available for this account.")
    try:
        directory.reset_password(token, password)
    except CloudAuthError as exc:
        raise_auth(exc)
    return {"ok": True, "message": "Password updated. Log in with the new one."}


def change_password_for(app, directory, principal: Principal, current: str, new: str) -> dict:
    if principal.kind == "hosted":
        if directory is None or not isinstance(principal.token, str):
            raise ApiError(401, "Sign in again.")
        try:
            directory.change_password(principal.token, current, new)
        except CloudAuthError as exc:
            raise_auth(exc)
        return {"ok": True, "message": "Password updated."}
    if principal.accounts_path is None or not isinstance(principal.seal, str):
        raise ApiError(401, "Sign in again.")
    try:
        seal = change_password(
            principal.accounts_path,
            principal.email,
            principal.seal,
            current,
            new,
        )
    except AccountError as exc:
        raise_auth(exc)
    update_local_session(app, principal.sid, seal=seal)
    principal.seal = seal
    return {"ok": True, "message": "Password updated."}


def change_email_for(app, directory, principal: Principal, password: str, new_email: str) -> dict:
    if principal.kind == "hosted":
        if directory is None or not isinstance(principal.token, str):
            raise ApiError(401, "Sign in again.")
        try:
            updated = directory.change_email(principal.token, password, new_email)
        except CloudAuthError as exc:
            raise_auth(exc)
        _rewrite_hosted_email(directory, principal.sid, updated)
        principal.email = updated
        if isinstance(directory, MemoryDirectory):
            message = "Email updated."
        else:
            # Secure email change keeps the old address until the mail is confirmed.
            # profiles.email is not written here. Migration 005 locks that column.
            message = "Check your email to confirm the new address."
        return {"ok": True, "email": updated, "message": message}
    if principal.accounts_path is None or not isinstance(principal.seal, str):
        raise ApiError(401, "Sign in again.")
    try:
        updated = change_email(
            principal.accounts_path,
            principal.email,
            principal.seal,
            password,
            new_email,
        )
    except AccountError as exc:
        raise_auth(exc)
    update_local_session(app, principal.sid, email=updated)
    principal.email = updated
    return {"ok": True, "email": updated, "message": "Email updated."}


def _rewrite_hosted_email(directory, sid: str, email: str) -> None:
    try:
        row = directory.load_hosted_session(sid)
    except CloudAuthError:
        return
    if not isinstance(row, dict):
        return
    row = dict(row)
    row["email"] = email
    try:
        directory.update_hosted_session(sid, row)
    except CloudAuthError:
        return


def delete_account_for(directory, principal: Principal, *, email: str, password: str) -> None:
    """Remove the account. Hosted deletes use the signed-in client, then the service role.

    The local form also requires the typed email and the password. The hosted
    form in Streamlit only requires the confirm checkbox, which the route checks.
    """
    if principal.kind == "hosted":
        if directory is None or not isinstance(principal.token, str):
            raise ApiError(401, "Sign in again.")
        key = service_key_for(directory)
        try:
            directory.delete_user(principal.token, key)
        except CloudAuthError as exc:
            raise_auth(exc)
        return
    typed = email.strip().casefold() if isinstance(email, str) else ""
    if typed != principal.email.strip().casefold():
        raise ApiError(400, "Confirm with your email to delete this account.")
    if principal.accounts_path is None or not isinstance(principal.seal, str):
        raise ApiError(401, "Sign in again.")
    try:
        delete_account(principal.accounts_path, principal.email, principal.seal, password)
    except AccountError as exc:
        raise_auth(exc)


def reset_seasons_for(principal: Principal, directory) -> None:
    """Remove stored seasons. The account stays."""
    if principal.kind == "hosted":
        if directory is None or not isinstance(principal.token, str):
            raise ApiError(401, "Sign in again.")
        try:
            directory.reset_seasons(principal.token)
        except CloudAuthError as exc:
            raise_auth(exc)
        return
    if principal.accounts_path is None or not isinstance(principal.seal, str):
        raise ApiError(401, "Sign in again.")
    path = principal.accounts_path
    email = principal.email
    seal = principal.seal
    try:
        from services.season_store import delete_local_plans

        delete_local_plans(path, email, seal)
        from api.state import STATE_PREFIX

        keys = record_keys(path, email, seal, STATE_PREFIX)
        if isinstance(keys, list) and keys:
            delete_exact(path, email, seal, keys)
    except AccountError as exc:
        raise_auth(exc)


def google_start(directory) -> dict:
    if directory is None:
        raise ApiError(503, ACCOUNTS_UNAVAILABLE)
    redirect = google_redirect_uri()
    try:
        url = directory.google_url(redirect)
    except CloudAuthError as exc:
        raise_auth(exc)
    return {"url": url, "redirect_uri": redirect}


def google_finish(directory, code: str, flow: str) -> dict:
    if directory is None:
        raise ApiError(503, ACCOUNTS_UNAVAILABLE)
    try:
        session = directory.exchange_code(code, flow or None)
        sid, issued = open_hosted(directory, session)
    except CloudAuthError as exc:
        raise ApiError(400, str(exc)) from exc
    return {
        "sid": sid,
        "issued": issued,
        "email": session.get("email") or "",
        "display_name": session.get("display_name") or "",
        "kind": "hosted",
        "redirect_uri": google_redirect_uri(),
    }


def code_from_authorize_url(url: str) -> str:
    """The code on a memory-directory Google link. A real authorize URL has none."""
    found = parse_qs(urlparse(url).query).get("code") or []
    return found[0] if found else ""
