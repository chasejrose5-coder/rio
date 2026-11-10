# identity.py — the signed-in athlete. The cookie holds an id, not a token.

"""Hosted sign-in uses the directory. Local sign-in uses the account file.

Both set rio_hosted to an opaque rio1. id. The Supabase tokens, and the
local seal key, stay on the server. The cookie is HttpOnly, Secure, and
SameSite=Lax. Lax is what the OAuth return already relies on. Nothing
here writes localStorage.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from fastapi import Response

from api.settings import ApiSettings
from ui.accounts import (
    AccountError,
    authenticate,
    read_local,
)
from ui.cloud_session import cookie_max_age, hosted_hash, hosted_sid, new_hosted_sid
from ui.cloud_store import CloudAuthError

_SESSION_SECONDS = 24 * 60 * 60


@dataclass
class Principal:
    """Who this cookie is. token is the hosted access token. seal is local."""

    kind: str
    email: str
    display_name: str
    user_id: str
    role: str
    token: str | None
    refresh: str | None
    seal: str | None
    accounts_path: Path | None
    issued_at: int
    sid: str


def _age(issued_at: int) -> int:
    remaining = cookie_max_age(issued_at)
    if remaining < 1:
        return 0
    return remaining


def set_session_cookie(response: Response, settings: ApiSettings, sid: str, issued_at: int) -> None:
    """The browser value is the id. Scripts on the page cannot read it."""
    response.set_cookie(
        key=settings.cookie_name,
        value=sid,
        max_age=_age(issued_at),
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response, settings: ApiSettings) -> None:
    response.delete_cookie(
        settings.cookie_name,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _local_sessions(app) -> dict:
    bag = getattr(app.state, "local_sessions", None)
    if not isinstance(bag, dict):
        bag = {}
        app.state.local_sessions = bag
    return bag


def _expired(issued_at: object, *, now: int | None = None) -> bool:
    if isinstance(issued_at, bool) or not isinstance(issued_at, int):
        return True
    moment = int(time.time()) if now is None else int(now)
    return moment - issued_at >= _SESSION_SECONDS or moment < issued_at


def _remember_hosted(directory, session: dict, *, missing: str) -> tuple[str, int, dict]:
    """Store the directory session and return the opaque cookie id."""
    if not isinstance(session, dict) or not session.get("access_token"):
        raise CloudAuthError(missing)
    issued = int(time.time())
    record = {
        "access_token": session.get("access_token"),
        "refresh_token": session.get("refresh_token") or "",
        "user_id": session.get("user_id") or "",
        "email": session.get("email") or "",
        "display_name": session.get("display_name") or "",
        "issued_at": issued,
    }
    try:
        sid = directory.save_hosted_session(record)
    except CloudAuthError:
        raise
    except Exception as exc:
        raise CloudAuthError("Sign in again.") from exc
    return sid, issued, session


def sign_in_hosted(directory, email: str, password: str) -> tuple[str, int, dict]:
    """Directory sign-in, then an opaque session row. Tokens stay in that row."""
    session = directory.sign_in(email, password)
    return _remember_hosted(directory, session, missing="Email or password does not match.")


def _remember_local(app, email: str, seal: str, name: str) -> tuple[str, int, dict]:
    """The seal stays under the cookie id. The cookie value is only the id."""
    issued = int(time.time())
    sid = new_hosted_sid()
    _local_sessions(app)[hosted_hash(sid)] = {
        "email": email,
        "seal": seal,
        "display_name": name,
        "issued_at": issued,
    }
    return sid, issued, {"email": email, "display_name": name, "user_id": email, "role": "athlete"}


def sign_in_local(app, path: Path, email: str, password: str) -> tuple[str, int, dict]:
    """The account file. The seal is stored under the cookie id, not in it."""
    found = authenticate(path, email, password)
    if found is None:
        raise AccountError("Email or password does not match.")
    cleaned, seal = found
    local = read_local(path, cleaned) or {}
    name = local.get("name") if isinstance(local.get("name"), str) else ""
    return _remember_local(app, cleaned, seal, name)


def update_local_session(app, sid: str, **fields: object) -> None:
    """Replace seal or email on this cookie. The cookie id stays."""
    row = _local_sessions(app).get(hosted_hash(sid))
    if not isinstance(row, dict):
        return
    for key, value in fields.items():
        if isinstance(value, str):
            row[key] = value


def sign_out(app, directory, sid: str | None) -> None:
    if not isinstance(sid, str) or not sid:
        return
    if directory is not None and hosted_sid(sid):
        try:
            directory.drop_hosted_session(sid)
        except CloudAuthError:
            pass
    _local_sessions(app).pop(hosted_hash(sid), None)


def _refresh_hosted(directory, sid: str, row: dict) -> dict | None:
    refresh = row.get("refresh_token")
    try:
        session = directory.refresh_session(refresh)
    except CloudAuthError:
        return None
    if not isinstance(session, dict) or not session.get("access_token"):
        return None
    issued = row.get("issued_at")
    if isinstance(issued, str) and issued.isdigit():
        issued = int(issued)
    if isinstance(issued, bool) or not isinstance(issued, int):
        issued = int(time.time())
    updated = {
        "access_token": session.get("access_token"),
        "refresh_token": session.get("refresh_token") or refresh or "",
        "user_id": session.get("user_id") or row.get("user_id") or "",
        "email": session.get("email") or row.get("email") or "",
        "display_name": session.get("display_name") or row.get("display_name") or "",
        "issued_at": issued,
    }
    try:
        directory.update_hosted_session(sid, updated)
    except CloudAuthError:
        return None
    return updated


def principal_from_cookie(app, directory, accounts_path: Path | None, raw: object) -> Principal | None:
    """The athlete for this cookie, or None when it is missing or expired."""
    if not hosted_sid(raw):
        return None
    sid = str(raw)
    if directory is not None:
        try:
            row = directory.load_hosted_session(sid)
        except CloudAuthError:
            row = None
        if not isinstance(row, dict):
            return None
        issued = row.get("issued_at")
        if isinstance(issued, str) and issued.isdigit():
            issued = int(issued)
        if _expired(issued):
            try:
                directory.drop_hosted_session(sid)
            except CloudAuthError:
                pass
            return None
        token = row.get("access_token")
        if not isinstance(token, str) or not token:
            return None
        try:
            directory.user_id(token)
        except CloudAuthError:
            refreshed = _refresh_hosted(directory, sid, row)
            if refreshed is None:
                try:
                    directory.drop_hosted_session(sid)
                except CloudAuthError:
                    pass
                return None
            row = refreshed
            token = str(row.get("access_token") or "")
        return Principal(
            kind="hosted",
            email=str(row.get("email") or ""),
            display_name=str(row.get("display_name") or ""),
            user_id=str(row.get("user_id") or ""),
            role="athlete",
            token=token,
            refresh=str(row.get("refresh_token") or ""),
            seal=None,
            accounts_path=None,
            issued_at=int(issued),
            sid=sid,
        )
    row = _local_sessions(app).get(hosted_hash(sid))
    if not isinstance(row, dict) or accounts_path is None:
        return None
    issued = row.get("issued_at")
    if _expired(issued):
        _local_sessions(app).pop(hosted_hash(sid), None)
        return None
    email = row.get("email")
    seal = row.get("seal")
    if not isinstance(email, str) or not isinstance(seal, str):
        return None
    return Principal(
        kind="local",
        email=email,
        display_name=str(row.get("display_name") or ""),
        user_id=email,
        role="athlete",
        token=None,
        refresh=None,
        seal=seal,
        accounts_path=accounts_path,
        issued_at=int(issued),
        sid=sid,
    )
