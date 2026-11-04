# cloud_session.py — the hosted session cookie and the saved-season check.

"""A 24-hour cookie. New sessions store an opaque id.

The Supabase tokens stay on the server. pack_cookie still builds the older
JSON cookie so a browser that already has one can be opened, and so the
session table can be missing. The service role key is never packed into it.
A plan counts as a current season when it has at least one session.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time

SESSION_SECONDS = 24 * 60 * 60
COOKIE_NAME = "rio_hosted"
# Opaque browser value. The Supabase tokens stay in app_sessions.
HOSTED_PREFIX = "rio1."


def pack_cookie(
    access_token: str,
    refresh_token: str,
    user_id: str,
    email: str,
    display_name: str,
    issued_at: int,
) -> str:
    """JSON for the browser cookie. No server key is included."""
    payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": user_id,
        "email": email,
        "display_name": display_name,
        "issued_at": int(issued_at),
    }
    return json.dumps(payload, separators=(",", ":"))


def unpack_cookie(raw: object, *, now: int | None = None) -> dict | None:
    """The cookie payload, or None when it is missing, old, or unsafe."""
    if not isinstance(raw, str) or not raw or len(raw) > 4000:
        return None
    lowered = raw.lower()
    if "service_role" in lowered or "service_key" in lowered or "sb_secret_" in lowered:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    issued = data.get("issued_at")
    moment = int(time.time()) if now is None else int(now)
    if not isinstance(issued, int) or issued > moment + 60:
        return None
    if moment - issued >= SESSION_SECONDS:
        return None
    access = data.get("access_token")
    refresh = data.get("refresh_token")
    user_id = data.get("user_id")
    email = data.get("email")
    if not all(isinstance(item, str) and item for item in (access, refresh, user_id, email)):
        return None
    name = data.get("display_name")
    if not isinstance(name, str):
        name = ""
    return {
        "access_token": access,
        "refresh_token": refresh,
        "user_id": user_id,
        "email": email,
        "display_name": name,
        "issued_at": issued,
    }


def new_hosted_sid() -> str:
    """A cookie value with no Supabase token in it."""
    return HOSTED_PREFIX + secrets.token_urlsafe(32)


def hosted_sid(raw: object) -> bool:
    """True when this cookie is an opaque session id."""
    return isinstance(raw, str) and raw.startswith(HOSTED_PREFIX) and 8 < len(raw) < 200


def request_leaf(url: object) -> str:
    """The last path segment, without the host or the query."""
    from urllib.parse import urlparse

    if not isinstance(url, str) or not url:
        return ""
    path = urlparse(url).path.rstrip("/")
    return path.rsplit("/", 1)[-1]


def load_is_app_root(url: object) -> bool:
    """True for the app root and Home. A named page such as Plan stays put."""
    return request_leaf(url) in ("", "~", "+", "home")


def hosted_hash(sid: str) -> str:
    """The key stored on the server. The raw cookie is not stored."""
    return hashlib.sha256(sid.encode("utf-8")).hexdigest()


def cookie_max_age(issued_at: int, *, now: int | None = None) -> int:
    """Seconds left in the original 24 hours. Refreshing does not extend it."""
    moment = int(time.time()) if now is None else int(now)
    remaining = SESSION_SECONDS - (moment - int(issued_at))
    if remaining < 1:
        return 0
    return remaining


def plan_has_sessions(plan: object) -> bool:
    """True when this saved plan is a current season."""
    if not isinstance(plan, dict):
        return False
    sessions = plan.get("sessions")
    return isinstance(sessions, list) and len(sessions) > 0


def season_digest(inputs: object, plan: object, marks: object, actuals: object) -> str:
    """A fingerprint so an unchanged season is not written again."""
    payload = {
        "inputs": list(inputs) if isinstance(inputs, (list, tuple)) else [],
        "plan": plan if isinstance(plan, dict) else {},
        "marks": marks if isinstance(marks, dict) else {},
        "actuals": actuals if isinstance(actuals, dict) else {},
    }
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
