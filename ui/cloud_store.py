# cloud_store.py — one athlete's rows, or an offline stand-in.

"""Sign-up, sign-in, plans, and results.

The memory directory is the offline stand-in. It never opens a network
connection. A configured project uses the Supabase client instead.
The service role key is only accepted by list and delete. It is not
stored on a user session.
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
from copy import deepcopy
from datetime import datetime, timezone
from urllib.parse import quote

from engines.pace import canonical_easy_pace
from ui.accounts import normalize_email, normalize_name, password_ok
from ui.cloud_session import SESSION_SECONDS, hosted_hash, hosted_sid, new_hosted_sid

_MEMORY: "MemoryDirectory | None" = None


class CloudAuthError(ValueError):
    """A sign-in or save failed. The message is safe to show."""


SIGNUP_CONFIRM = "Check your email to confirm your account, then log in."
SIGNUP_EXISTS = "An account with that email already exists."
SIGNUP_RATE = "Too many sign-up attempts. Wait a few minutes and try again."
SIGNUP_PASSWORD = "Use at least 8 characters."
SIGNUP_EMAIL = "Enter an email address."
SIGNUP_NAME = "Enter a name."
SIGNUP_FAILED = "The account could not be created."
SIGNUP_PROFILE = (
    "Your account was created, but the profile could not be saved. Log in and try again."
)
SIGNUP_DISABLED = "New accounts are turned off right now."
SIGNIN_RATE = "Too many sign-in attempts. Wait a few minutes and try again."
SIGNIN_MISMATCH = "Email or password does not match."
ACCOUNTS_UNAVAILABLE = "Accounts aren't set up yet. Try again in a minute."


class MemoryDirectory:
    """Accounts and rows kept in this process. Tests use this directory."""

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}
        self.by_email: dict[str, str] = {}
        self.sessions: dict[str, str] = {}
        self.refreshes: dict[str, str] = {}
        self.resets: dict[str, str] = {}
        self.goals: dict[str, dict] = {}
        self.plans: dict[str, list] = {}
        self.results: dict[str, list] = {}
        self.hosted: dict[str, dict] = {}

    def sign_up(self, email: object, password: object, name: object) -> dict:
        cleaned = normalize_email(email)
        stored_name = normalize_name(name)
        if cleaned is None:
            raise CloudAuthError("Enter an email address.")
        if stored_name is None:
            raise CloudAuthError("Enter a name.")
        if not password_ok(password) or not isinstance(password, str):
            raise CloudAuthError("Use at least 8 characters.")
        if cleaned in self.by_email:
            raise CloudAuthError("An account with that email already exists.")
        user_id = secrets.token_hex(8)
        self.users[user_id] = {
            "id": user_id,
            "email": cleaned,
            "password": password,
            "display_name": stored_name,
            "role": "athlete",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "email_confirmed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.by_email[cleaned] = user_id
        self.goals[user_id] = _blank_goal()
        self.plans[user_id] = []
        self.results[user_id] = []
        return self._open(user_id)

    def sign_in(self, email: object, password: object) -> dict:
        cleaned = normalize_email(email)
        user_id = self.by_email.get(cleaned or "")
        user = self.users.get(user_id or "")
        if user is None or not isinstance(password, str) or user["password"] != password:
            raise CloudAuthError("Email or password does not match.")
        return self._open(user["id"])

    def sign_out(self, access_token: object) -> None:
        if isinstance(access_token, str):
            self.sessions.pop(access_token, None)
            dead = [
                digest
                for digest, row in self.hosted.items()
                if row.get("access_token") == access_token
            ]
            for digest in dead:
                self.hosted.pop(digest, None)

    def google_url(self, redirect_to: str) -> str:
        code = secrets.token_hex(6)
        self.resets["google:" + code] = ""
        # The code stands in for the provider round trip. No request is sent.
        return f"{redirect_to}?code={code}&provider=google"

    def exchange_code(self, code: object, flow: object = None) -> dict:
        if not isinstance(code, str) or "google:" + code not in self.resets:
            raise CloudAuthError("Sign-in could not be finished. Try again.")
        self.resets.pop("google:" + code, None)
        email = "google-athlete@example.com"
        if email not in self.by_email:
            return self.sign_up(email, "google-password-1", "Athlete")
        return self._open(self.by_email[email])

    def request_reset(self, email: object) -> str:
        cleaned = normalize_email(email)
        user_id = self.by_email.get(cleaned or "")
        if user_id is None:
            return ""
        token = secrets.token_hex(8)
        self.resets[token] = user_id
        return token

    def reset_password(self, token: object, password: object) -> None:
        user_id = self.resets.get(token) if isinstance(token, str) else None
        user = self.users.get(user_id or "")
        if user is None:
            raise CloudAuthError("That reset link is no longer valid.")
        if not password_ok(password) or not isinstance(password, str):
            raise CloudAuthError("Use at least 8 characters.")
        user["password"] = password
        self.resets.pop(str(token), None)

    def user_id(self, access_token: object) -> str:
        if not isinstance(access_token, str):
            raise CloudAuthError("Sign in again.")
        user_id = self.sessions.get(access_token)
        if user_id is None or user_id not in self.users:
            raise CloudAuthError("Sign in again.")
        return user_id

    def load_bundle(self, access_token: object) -> dict:
        user_id = self.user_id(access_token)
        user = self.users[user_id]
        return {
            "profile": _public_user(user),
            "goal": deepcopy(self.goals.get(user_id) or _blank_goal()),
            "plans": deepcopy(self.plans.get(user_id) or []),
            "results": deepcopy(self.results.get(user_id) or []),
            "auth_user": {
                "id": user_id,
                "email": user["email"],
                "email_confirmed_at": user.get("email_confirmed_at") or "",
            },
        }

    def save_bundle(self, access_token: object, bundle: object) -> None:
        user_id = self.user_id(access_token)
        if not isinstance(bundle, dict):
            raise CloudAuthError("This account could not be saved.")
        goal = bundle.get("goal")
        if isinstance(goal, dict):
            self.goals[user_id] = _clean_goal(goal)
        plans = bundle.get("plans")
        if isinstance(plans, list):
            self.plans[user_id] = deepcopy(plans)
        results = bundle.get("results")
        if isinstance(results, list):
            self.results[user_id] = deepcopy(results)
        profile = bundle.get("profile")
        if isinstance(profile, dict):
            name = profile.get("display_name")
            if isinstance(name, str) and name.strip():
                self.users[user_id]["display_name"] = name.strip()
            self._keep_pace(user_id, profile.get("pace_units"))

    def save_timezone(self, access_token: object, zone: object) -> None:
        """Remember the Settings time zone. The other account stays."""
        user_id = self.user_id(access_token)
        if not self._keep_zone(user_id, zone):
            raise CloudAuthError("Time zone could not be saved.")

    def save_pace_units(self, access_token: object, unit: object) -> None:
        """Remember per mile or per km on this athlete. The other account stays."""
        user_id = self.user_id(access_token)
        if not self._keep_pace(user_id, unit):
            raise CloudAuthError("Pace units could not be saved.")

    def save_easy_pace(self, access_token: object, pace: object, unit: object) -> None:
        """Remember the easy pace on this athlete. The other account stays."""
        user_id = self.user_id(access_token)
        pair = stored_easy_pair(pace, unit)
        user = self.users.get(user_id)
        if pair is None or user is None:
            raise CloudAuthError("Easy pace could not be saved.")
        user["easy_pace"] = pair[0]
        user["easy_pace_unit"] = pair[1]

    def save_intro_seen(self, access_token: object, seen: object) -> None:
        """Remember that this athlete dismissed the intro, or asked to see it again."""
        user_id = self.user_id(access_token)
        if not isinstance(seen, bool):
            raise CloudAuthError("The intro guide could not be saved.")
        user = self.users.get(user_id)
        if user is None:
            raise CloudAuthError("The intro guide could not be saved.")
        user["intro_seen"] = seen

    def save_strava_prompt_seen(self, access_token: object, seen: object) -> None:
        """Remember that this athlete dismissed the Strava card, or connected."""
        user_id = self.user_id(access_token)
        if not isinstance(seen, bool):
            raise CloudAuthError("The Strava prompt could not be saved.")
        user = self.users.get(user_id)
        if user is None:
            raise CloudAuthError("The Strava prompt could not be saved.")
        user["strava_prompt_seen"] = seen

    def save_no_watch(self, access_token: object, enabled: object) -> None:
        """Remember Done-only logging on this athlete. The other account stays."""
        user_id = self.user_id(access_token)
        if not isinstance(enabled, bool):
            raise CloudAuthError("Logging could not be saved.")
        user = self.users.get(user_id)
        if user is None:
            raise CloudAuthError("Logging could not be saved.")
        user["no_watch"] = enabled

    def _keep_zone(self, user_id: str, zone: object) -> bool:
        from ui.settings import TIME_ZONES

        if not isinstance(zone, str) or zone not in TIME_ZONES:
            return False
        user = self.users.get(user_id)
        if user is None:
            return False
        user["timezone"] = zone
        return True

    def _keep_pace(self, user_id: str, unit: object) -> bool:
        if unit not in ("mi", "km"):
            return False
        user = self.users.get(user_id)
        if user is None:
            return False
        user["pace_units"] = unit
        return True

    def refresh_session(self, refresh_token: object) -> dict:
        if not isinstance(refresh_token, str):
            raise CloudAuthError("Sign in again.")
        access = self.refreshes.get(refresh_token)
        user_id = self.sessions.get(access or "")
        if user_id is None or user_id not in self.users:
            raise CloudAuthError("Sign in again.")
        return self._open(user_id)

    def set_role(self, user_id: object, role: object, service_key: object) -> None:
        """Set a role with the server key. The signed-in client cannot do this."""
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("This role could not be saved.")
        if role not in ("athlete", "coach", "admin") or not isinstance(user_id, str):
            raise CloudAuthError("This role could not be saved.")
        user = self.users.get(user_id)
        if user is None:
            raise CloudAuthError("This role could not be saved.")
        user["role"] = role

    def list_users(self, service_key: object) -> list[dict] | None:
        if not isinstance(service_key, str) or not service_key.strip():
            return None
        rows = [_public_user(user) for user in self.users.values()]
        rows.sort(key=lambda row: row["email"])
        return rows

    def delete_user(self, access_token: object, service_key: object) -> None:
        user_id = self.user_id(access_token)
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("This account could not be removed on the server.")
        self.goals.pop(user_id, None)
        self.plans.pop(user_id, None)
        self.results.pop(user_id, None)
        dead_hosted = [digest for digest, row in self.hosted.items() if row.get("user_id") == user_id]
        for digest in dead_hosted:
            self.hosted.pop(digest, None)
        email = self.users[user_id]["email"]
        self.by_email.pop(email, None)
        self.users.pop(user_id, None)
        dead = [token for token, owner in self.sessions.items() if owner == user_id]
        for token in dead:
            self.sessions.pop(token, None)

    def delete_season(self, access_token: object, inputs: object, today: object) -> None:
        """Remove one past season for the signed-in athlete. Other athletes stay."""
        from datetime import date

        from ui.past_seasons import is_past_season, without_season

        if type(today) is not date or not is_past_season(inputs, today):
            raise CloudAuthError("The current season can't be deleted.")
        user_id = self.user_id(access_token)
        plans, results = without_season(
            self.plans.get(user_id) or [],
            self.results.get(user_id) or [],
            inputs,
        )
        self.plans[user_id] = plans
        self.results[user_id] = results

    def find_user_by_email(self, email: object, service_key: object) -> str | None:
        """The user id for this email. The server key is required. No mail is sent."""
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("The test season could not be saved.")
        cleaned = normalize_email(email)
        if cleaned is None:
            return None
        return self.by_email.get(cleaned)

    def create_confirmed_user(self, email: object, name: object, service_key: object) -> str:
        """Add an athlete that can sign in only with the server key. No mail is sent."""
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("The test season could not be saved.")
        cleaned = normalize_email(email)
        stored_name = normalize_name(name)
        if cleaned is None or stored_name is None:
            raise CloudAuthError("The test season could not be saved.")
        existing = self.by_email.get(cleaned)
        if existing:
            self.users[existing]["display_name"] = stored_name
            return existing
        user_id = "rio-test-athlete"
        if user_id in self.users:
            user_id = "rio-test-athlete-" + secrets.token_hex(4)
        self.users[user_id] = {
            "id": user_id,
            "email": cleaned,
            "password": secrets.token_urlsafe(24),
            "display_name": stored_name,
            "role": "athlete",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "email_confirmed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.by_email[cleaned] = user_id
        self.goals[user_id] = _blank_goal()
        self.plans[user_id] = []
        self.results[user_id] = []
        return user_id

    def write_owned_season(self, user_id: object, service_key: object, goal: object, plan_row: object, name: object) -> None:
        """Replace one athlete's goal and plan. Other athletes stay as stored."""
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("The test season could not be saved.")
        if not isinstance(user_id, str) or user_id not in self.users:
            raise CloudAuthError("The test season could not be saved.")
        if not isinstance(goal, dict) or not isinstance(plan_row, dict):
            raise CloudAuthError("The test season could not be saved.")
        stored_name = normalize_name(name)
        if stored_name is not None:
            self.users[user_id]["display_name"] = stored_name
        self.goals[user_id] = _clean_goal(goal)
        self.plans[user_id] = [deepcopy(plan_row)]
        self.results[user_id] = []

    def read_owned_season(self, user_id: object, service_key: object) -> dict | None:
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("The test season could not be saved.")
        if not isinstance(user_id, str) or user_id not in self.users:
            return None
        plans = self.plans.get(user_id) or []
        plan_row = deepcopy(plans[-1]) if plans else None
        return {"goal": deepcopy(self.goals.get(user_id) or _blank_goal()), "plan_row": plan_row}

    def delete_user_by_id(self, user_id: object, service_key: object) -> bool:
        """Remove one athlete by id. The signed-in token is not used."""
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("The test season could not be removed.")
        if not isinstance(user_id, str) or user_id not in self.users:
            return False
        email = self.users[user_id]["email"]
        dead = [token for token, owner in self.sessions.items() if owner == user_id]
        dead_refresh = [refresh for refresh, access in self.refreshes.items() if access in dead]
        for token in dead:
            self.sessions.pop(token, None)
        for refresh in dead_refresh:
            self.refreshes.pop(refresh, None)
        self.goals.pop(user_id, None)
        self.plans.pop(user_id, None)
        self.results.pop(user_id, None)
        dead_hosted = [digest for digest, row in self.hosted.items() if row.get("user_id") == user_id]
        for digest in dead_hosted:
            self.hosted.pop(digest, None)
        self.by_email.pop(email, None)
        self.users.pop(user_id, None)
        return True

    def verified_user(self, access_token: object) -> dict | None:
        """The auth user for this token. The profile row is not consulted."""
        try:
            user_id = self.user_id(access_token)
        except CloudAuthError:
            return None
        user = self.users.get(user_id)
        if user is None:
            return None
        return {
            "id": user_id,
            "email": user["email"],
            "email_confirmed_at": user.get("email_confirmed_at") or "",
        }

    def save_hosted_session(self, record: object) -> str:
        """Store tokens under a hash. The returned cookie holds no token."""
        if not isinstance(record, dict):
            raise CloudAuthError("Sign in again.")
        access = record.get("access_token")
        user_id = record.get("user_id")
        if not isinstance(access, str) or not access or not isinstance(user_id, str) or not user_id:
            raise CloudAuthError("Sign in again.")
        sid = new_hosted_sid()
        issued = _issued(record.get("issued_at"))
        self.hosted[hosted_hash(sid)] = _hosted_record(record, issued)
        return sid

    def load_hosted_session(self, sid: object) -> dict | None:
        if not hosted_sid(sid):
            return None
        row = self.hosted.get(hosted_hash(str(sid)))
        if not isinstance(row, dict):
            return None
        if _hosted_expired(row):
            self.hosted.pop(hosted_hash(str(sid)), None)
            return None
        return dict(row)

    def update_hosted_session(self, sid: object, record: object) -> None:
        if not hosted_sid(sid) or not isinstance(record, dict):
            return
        digest = hosted_hash(str(sid))
        current = self.hosted.get(digest)
        if not isinstance(current, dict):
            return
        issued = int(current.get("issued_at") or _issued(None))
        merged = dict(current)
        merged.update(_hosted_record(record, issued))
        merged["issued_at"] = issued
        self.hosted[digest] = merged

    def drop_hosted_session(self, sid: object) -> None:
        if hosted_sid(sid):
            self.hosted.pop(hosted_hash(str(sid)), None)

    def _open(self, user_id: str) -> dict:
        token = secrets.token_hex(16)
        refresh = "refresh-" + token
        self.sessions[token] = user_id
        self.refreshes[refresh] = token
        user = self.users[user_id]
        return {
            "access_token": token,
            "refresh_token": refresh,
            "user_id": user_id,
            "email": user["email"],
            "display_name": user["display_name"],
            "role": user["role"],
        }


# One verifier per sign-in attempt. The key is the flow id in that browser's
# redirect, so two visitors cannot overwrite each other. Not a Supabase client.
_PKCE: dict[str, tuple[str, float]] = {}
_PKCE_SECONDS = 600

# Shared sockets only. No Authorization header and no user token live here.
_HTTP_POOL: object | None = None


def _http_pool():
    """One connection pool for this process. It does not keep a visitor's token."""
    global _HTTP_POOL
    if _HTTP_POOL is None:
        import httpx

        _HTTP_POOL = httpx.Client(timeout=8.0, follow_redirects=True)
    return _HTTP_POOL


def _fresh_options():
    """No shared session and no automatic refresh. One visitor cannot replace another."""
    from supabase import ClientOptions

    return ClientOptions(
        persist_session=False,
        auto_refresh_token=False,
        httpx_client=_http_pool(),
    )


def pkce_challenge(verifier: str) -> str:
    """S256 challenge. The verifier itself is not in the URL."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def stash_verifier(flow: str, verifier: str, *, now: float | None = None) -> None:
    """Remember this attempt. A later attempt uses a different flow id."""
    moment = time.time() if now is None else now
    _drop_old_verifiers(moment)
    _PKCE[flow] = (verifier, moment)


def take_verifier(flow: str, *, now: float | None = None) -> str:
    """The verifier for this attempt only. Another attempt stays put."""
    moment = time.time() if now is None else now
    _drop_old_verifiers(moment)
    verifier, created = _PKCE.pop(flow, ("", 0.0))
    if not verifier or moment - created > _PKCE_SECONDS:
        return ""
    return verifier


def _drop_old_verifiers(now: float) -> None:
    dead = [key for key, (_verifier, created) in _PKCE.items() if now - created > _PKCE_SECONDS]
    for key in dead:
        _PKCE.pop(key, None)


class SupabaseDirectory:
    """The hosted project. Calls stay on the server. Keys are not returned."""

    def __init__(self, url: str, anon_key: str, service_key: str) -> None:
        self.url = url
        self.anon_key = anon_key
        self.service_key = service_key

    def _client(self, key: str):
        """A new client. Auth state from another visitor is not reused."""
        try:
            from supabase import create_client
        except ImportError as exc:
            raise CloudAuthError("Accounts could not be reached.") from exc
        return create_client(self.url, key, options=_fresh_options())

    def sign_up(self, email: object, password: object, name: object) -> dict:
        cleaned = normalize_email(email)
        if cleaned is None:
            raise CloudAuthError(SIGNUP_EMAIL)
        stored_name = normalize_name(name)
        if stored_name is None:
            raise CloudAuthError(SIGNUP_NAME)
        if not password_ok(password) or not isinstance(password, str):
            raise CloudAuthError(SIGNUP_PASSWORD)
        from ui.cloud_config import auth_redirect_base

        try:
            response = self._client(self.anon_key).auth.sign_up(
                {
                    "email": cleaned,
                    "password": password,
                    "options": {
                        "data": {"display_name": stored_name},
                        "email_redirect_to": auth_redirect_base() + "/",
                    },
                }
            )
        except CloudAuthError:
            raise
        except Exception as exc:
            raise CloudAuthError(signup_error_message(exc)) from exc
        session = signup_outcome(response, stored_name)
        self._ensure_profile(session, stored_name)
        return session

    def sign_in(self, email: object, password: object) -> dict:
        cleaned = normalize_email(email)
        if cleaned is None or not isinstance(password, str) or not password:
            raise CloudAuthError(SIGNIN_MISMATCH)
        try:
            response = self._client(self.anon_key).auth.sign_in_with_password(
                {"email": cleaned, "password": password}
            )
        except CloudAuthError:
            raise
        except Exception as exc:
            raise CloudAuthError(signin_error_message(exc)) from exc
        session = _session_dict(response, "")
        signed_user = _response_parts(response)[1]
        meta_name = _attr(_attr(signed_user, "user_metadata"), "display_name")
        if isinstance(meta_name, str) and meta_name.strip():
            session["display_name"] = meta_name.strip()
        self._ensure_profile(session, session.get("display_name") or "")
        return session

    def sign_out(self, access_token: object) -> None:
        """Revoke this access token only. Other visitors' sessions stay."""
        if not isinstance(access_token, str) or not access_token:
            return
        try:
            self._client(self.anon_key).auth.admin.sign_out(access_token, "local")
        except Exception:
            return

    def google_url(self, redirect_to: str) -> str:
        """A Google link for this attempt. Another visitor gets a different verifier."""
        flow = secrets.token_urlsafe(16)
        verifier = secrets.token_urlsafe(64)
        stash_verifier(flow, verifier)
        joiner = "&" if "?" in redirect_to else "?"
        back = f"{redirect_to}{joiner}flow={quote(flow, safe='')}"
        return (
            f"{self.url.rstrip('/')}/auth/v1/authorize?provider=google"
            f"&redirect_to={quote(back, safe='')}"
            f"&code_challenge={quote(pkce_challenge(verifier), safe='')}"
            f"&code_challenge_method=s256"
        )

    def exchange_code(self, code: object, flow: object = None) -> dict:
        if not isinstance(code, str) or not code or not isinstance(flow, str) or not flow:
            raise CloudAuthError("Sign-in could not be finished. Try again.")
        verifier = take_verifier(flow)
        if not verifier:
            raise CloudAuthError("Sign-in could not be finished. Try again.")
        try:
            response = self._client(self.anon_key).auth.exchange_code_for_session(
                {"auth_code": code, "code_verifier": verifier}
            )
        except Exception as exc:
            raise CloudAuthError("Sign-in could not be finished. Try again.") from exc
        return _session_dict(response, "")

    def refresh_session(self, refresh_token: object) -> dict:
        if not isinstance(refresh_token, str) or not refresh_token:
            raise CloudAuthError("Sign in again.")
        try:
            response = self._client(self.anon_key).auth.refresh_session(refresh_token)
        except Exception as exc:
            raise CloudAuthError("Sign in again.") from exc
        return _session_dict(response, "")

    def set_role(self, user_id: object, role: object, service_key: object) -> None:
        """Set a role with the server key. The signed-in client cannot do this."""
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("This role could not be saved.")
        if role not in ("athlete", "coach", "admin") or not isinstance(user_id, str):
            raise CloudAuthError("This role could not be saved.")
        try:
            self._client(service_key).table("profiles").update({"role": role}).eq("id", user_id).execute()
        except Exception as exc:
            raise CloudAuthError("This role could not be saved.") from exc

    def request_reset(self, email: object) -> str:
        cleaned = normalize_email(email)
        if cleaned is None:
            raise CloudAuthError("Enter an email address.")
        from ui.cloud_config import auth_redirect_base

        try:
            self._client(self.anon_key).auth.reset_password_for_email(
                cleaned,
                {"redirect_to": auth_redirect_base() + "/?reset=password"},
            )
        except Exception as exc:
            raise CloudAuthError("The reset email could not be sent.") from exc
        return ""

    def reset_password(self, token: object, password: object) -> None:
        if not password_ok(password) or not isinstance(password, str):
            raise CloudAuthError("Use at least 8 characters.")
        if not isinstance(token, str) or not token:
            raise CloudAuthError("That reset link is no longer valid.")
        try:
            client = self._client(self.anon_key)
            verified = client.auth.verify_otp({"token_hash": token, "type": "recovery"})
            session = getattr(verified, "session", None)
            access = _attr(session, "access_token")
            refresh = _attr(session, "refresh_token")
            if not access or not refresh:
                raise CloudAuthError("That reset link is no longer valid.")
            client.auth.set_session(str(access), str(refresh))
            client.auth.update_user({"password": password})
        except CloudAuthError:
            raise
        except Exception as exc:
            raise CloudAuthError("That reset link is no longer valid.") from exc

    def load_bundle(self, access_token: object) -> dict:
        try:
            return self._load_bundle(access_token)
        except CloudAuthError:
            raise
        except Exception as exc:
            _log_store("load", exc)
            raise CloudAuthError("Could not load. Check your connection and try again.") from exc

    def _load_bundle(self, access_token: object) -> dict:
        client = self._user_client(access_token)
        record = self._auth_record(client, access_token)
        user_id = record["id"]
        try:
            profile, goal, plans, results = _embedded_bundle(
                _first(
                    client.table("profiles")
                    .select("*,goals(*),plans(*),results(*)")
                    .eq("id", user_id)
                    .limit(1)
                    .execute()
                )
            )
        except CloudAuthError:
            raise
        except Exception:
            profile, goal, plans, results = self._bundle_parallel(access_token, user_id)
        profile = profile or {}
        pace = _pace_from_metadata(record)
        intro = intro_seen_value(record)
        easy = easy_pace_from_metadata(record)
        zone = _zone_from_metadata(record)
        watch = no_watch_value(record)
        from ui.plan_strava import prompt_seen_value

        prompt = prompt_seen_value(record)
        if isinstance(profile, dict) and (
            pace
            or intro is not None
            or prompt is not None
            or easy is not None
            or zone
            or watch is not None
        ):
            profile = dict(profile)
            if pace:
                profile["pace_units"] = pace
            if intro is not None:
                profile["intro_seen"] = intro
            if prompt is not None:
                profile["strava_prompt_seen"] = prompt
            if easy is not None:
                profile["easy_pace"] = easy[0]
                profile["easy_pace_unit"] = easy[1]
            if zone:
                profile["timezone"] = zone
            if watch is not None:
                profile["no_watch"] = watch
        if isinstance(profile, dict):
            meta = _metadata_dict(record) or {}
            profile = dict(profile)
            for key in ("date_format", "start_date", "confirm_adapt", "show_ids", "compact", "preferred"):
                if key in meta:
                    profile[key] = meta[key]
        return {
            "profile": profile,
            "goal": goal or _blank_goal(),
            "plans": plans,
            "results": results,
            "auth_user": {
                "id": user_id,
                "email": record.get("email") or "",
                "email_confirmed_at": record.get("email_confirmed_at") or "",
            },
        }

    def _bundle_parallel(self, access_token: str, user_id: str) -> tuple:
        """Four row reads at once. Each read gets its own client."""
        from concurrent.futures import ThreadPoolExecutor

        def _profile():
            client = self._user_client(access_token)
            return _first(client.table("profiles").select("*").eq("id", user_id).execute())

        def _goal():
            client = self._user_client(access_token)
            return _first(client.table("goals").select("*").eq("user_id", user_id).execute())

        def _plans():
            client = self._user_client(access_token)
            return _rows(_plans_query(client, user_id).execute())

        def _results():
            client = self._user_client(access_token)
            return _rows(client.table("results").select("*").eq("user_id", user_id).execute())

        with ThreadPoolExecutor(max_workers=4) as pool:
            profile = pool.submit(_profile)
            goal = pool.submit(_goal)
            plans = pool.submit(_plans)
            results = pool.submit(_results)
            return profile.result(), goal.result(), plans.result(), results.result()

    def save_timezone(self, access_token: object, zone: object) -> None:
        """Store the Settings time zone on the auth user. No new table."""
        from ui.settings import TIME_ZONES

        if not isinstance(zone, str) or zone not in TIME_ZONES:
            raise CloudAuthError("Time zone could not be saved.")
        if not isinstance(access_token, str) or not access_token:
            raise CloudAuthError("Sign in again.")
        try:
            self._auth_user_update(access_token, {"timezone": zone})
        except CloudAuthError:
            raise
        except Exception:
            raise CloudAuthError("Time zone could not be saved.") from None

    def save_pace_units(self, access_token: object, unit: object) -> None:
        """Store per mile or per km on the auth user. No new table."""
        if unit not in ("mi", "km"):
            raise CloudAuthError("Pace units could not be saved.")
        if not isinstance(access_token, str) or not access_token:
            raise CloudAuthError("Sign in again.")
        try:
            self._auth_user_update(access_token, {"pace_units": unit})
        except CloudAuthError:
            raise
        except Exception:
            raise CloudAuthError("Pace units could not be saved.") from None

    def save_easy_pace(self, access_token: object, pace: object, unit: object) -> None:
        """Store the easy pace on the auth user, next to pace units. No new table."""
        pair = stored_easy_pair(pace, unit)
        if pair is None:
            raise CloudAuthError("Easy pace could not be saved.")
        if not isinstance(access_token, str) or not access_token:
            raise CloudAuthError("Sign in again.")
        try:
            self._auth_user_update(
                access_token,
                {"easy_pace": pair[0], "easy_pace_unit": pair[1]},
            )
        except CloudAuthError:
            raise
        except Exception:
            raise CloudAuthError("Easy pace could not be saved.") from None

    def save_intro_seen(self, access_token: object, seen: object) -> None:
        """Store the intro flag on the auth user, next to pace units."""
        if not isinstance(seen, bool):
            raise CloudAuthError("The intro guide could not be saved.")
        if not isinstance(access_token, str) or not access_token:
            raise CloudAuthError("Sign in again.")
        try:
            self._auth_user_update(access_token, {"intro_seen": seen})
        except CloudAuthError:
            raise
        except Exception:
            raise CloudAuthError("The intro guide could not be saved.") from None

    def save_strava_prompt_seen(self, access_token: object, seen: object) -> None:
        """Store the Strava prompt flag on the auth user, next to intro_seen."""
        if not isinstance(seen, bool):
            raise CloudAuthError("The Strava prompt could not be saved.")
        if not isinstance(access_token, str) or not access_token:
            raise CloudAuthError("Sign in again.")
        try:
            self._auth_user_update(access_token, {"strava_prompt_seen": seen})
        except CloudAuthError:
            raise
        except Exception:
            raise CloudAuthError("The Strava prompt could not be saved.") from None

    def save_no_watch(self, access_token: object, enabled: object) -> None:
        """Store Done-only logging on the auth user, next to pace units. No new table."""
        if not isinstance(enabled, bool):
            raise CloudAuthError("Logging could not be saved.")
        if not isinstance(access_token, str) or not access_token:
            raise CloudAuthError("Sign in again.")
        try:
            self._auth_user_update(access_token, {"no_watch": enabled})
        except CloudAuthError:
            raise
        except Exception:
            raise CloudAuthError("Logging could not be saved.") from None

    def save_bundle(self, access_token: object, bundle: object) -> None:
        if not isinstance(bundle, dict):
            raise CloudAuthError("This account could not be saved.")
        try:
            self._save_bundle(access_token, bundle)
        except CloudAuthError:
            raise
        except Exception as exc:
            _log_store("save", exc)
            raise CloudAuthError("Could not save. Check your connection and try again.") from exc

    def _save_bundle(self, access_token: object, bundle: dict) -> None:
        client = self._user_client(access_token)
        user_id = self._token_user(client, access_token)
        goal = bundle.get("goal")
        if isinstance(goal, dict):
            row = _clean_goal(goal)
            row["user_id"] = user_id
            client.table("goals").upsert(row).execute()
        plans = bundle.get("plans")
        if isinstance(plans, list):
            for plan in plans:
                if isinstance(plan, dict):
                    _save_plan(client, _plan_row(plan, user_id))
        results = bundle.get("results")
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    saved = dict(item)
                    saved["user_id"] = user_id
                    client.table("results").insert(saved).execute()

    def list_users(self, service_key: object) -> list[dict] | None:
        if not isinstance(service_key, str) or not service_key.strip():
            return None
        try:
            client = self._client(service_key)
            rows = _rows(client.table("profiles").select("*").execute())
        except Exception as exc:
            raise CloudAuthError("The account list could not be read.") from exc
        cleaned = []
        for row in rows:
            cleaned.append(
                {
                    "id": row.get("id", ""),
                    "email": row.get("email", ""),
                    "display_name": row.get("display_name", ""),
                    "role": row.get("role", "athlete"),
                    "created_at": row.get("created_at", ""),
                }
            )
        cleaned.sort(key=lambda item: str(item["email"]))
        return cleaned

    def delete_user(self, access_token: object, service_key: object) -> None:
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("This account could not be removed on the server.")
        try:
            self._delete_user(access_token, service_key)
        except CloudAuthError:
            raise
        except Exception as exc:
            _log_store("delete", exc)
            raise CloudAuthError("This account could not be removed on the server.") from exc

    def delete_season(self, access_token: object, inputs: object, today: object) -> None:
        """Remove one past season for this token. The service key is not used."""
        from datetime import date

        from ui.past_seasons import is_past_season

        if type(today) is not date or not is_past_season(inputs, today):
            raise CloudAuthError("The current season can't be deleted.")
        try:
            self._delete_season(access_token, inputs, today)
        except CloudAuthError:
            raise
        except Exception as exc:
            _log_store("delete-season", exc)
            raise CloudAuthError("This season could not be deleted.") from exc

    def _delete_user(self, access_token: object, service_key: object) -> None:
        client = self._user_client(access_token)
        user_id = self._token_user(client, access_token)
        self._drop_hosted_for_user(user_id)
        client.table("results").delete().eq("user_id", user_id).execute()
        client.table("plans").delete().eq("user_id", user_id).execute()
        client.table("goals").delete().eq("user_id", user_id).execute()
        client.table("profiles").delete().eq("id", user_id).execute()
        try:
            self._client(service_key).auth.admin.delete_user(user_id)
        except Exception as exc:
            raise CloudAuthError("This account could not be removed on the server.") from exc

    def _delete_season(self, access_token: object, inputs: tuple, today: object) -> None:
        """One transaction when the database function is there. Otherwise the same deletes."""
        client = self._user_client(access_token)
        user_id = self._token_user(client, access_token)
        try:
            client.rpc(
                "delete_past_season",
                {
                    "p_current_time": inputs[0],
                    "p_start_date": inputs[1],
                    "p_goal_time": inputs[2],
                    "p_goal_date": inputs[3],
                    "p_today": today.isoformat(),
                },
            ).execute()
        except Exception as exc:
            if not _missing_delete_season(exc):
                raise
            self._delete_season_rows(client, user_id, inputs)
            return
        return

    def _delete_season_rows(self, client, user_id: str, inputs: tuple) -> None:
        """Delete this athlete's season row and the results tied to it."""
        from ui.past_seasons import without_season

        plans = _rows(client.table("plans").select("*").eq("user_id", user_id).execute())
        results = _rows(client.table("results").select("*").eq("user_id", user_id).execute())
        _kept_plans, kept_results = without_season(plans, results, inputs)
        kept_ids = {id(item) for item in kept_results}
        removed = [item for item in results if id(item) not in kept_ids]
        for result in removed:
            ident = result.get("id")
            if not ident:
                continue
            client.table("results").delete().eq("user_id", user_id).eq("id", str(ident)).execute()
        (
            client.table("plans")
            .delete()
            .eq("user_id", user_id)
            .eq("current_time", inputs[0])
            .eq("start_date", inputs[1])
            .eq("goal_time", inputs[2])
            .eq("goal_date", inputs[3])
            .execute()
        )

    def find_user_by_email(self, email: object, service_key: object) -> str | None:
        """The profile id for this email, read with the server key."""
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("The test season could not be saved.")
        cleaned = normalize_email(email)
        if cleaned is None:
            return None
        try:
            row = _first(
                self._client(service_key).table("profiles").select("id").eq("email", cleaned).limit(1).execute()
            )
        except Exception:
            raise CloudAuthError("The test season could not be saved.") from None
        if isinstance(row, dict) and row.get("id"):
            return str(row["id"])
        return None

    def create_confirmed_user(self, email: object, name: object, service_key: object) -> str:
        """Create a confirmed athlete with the server key. No mail is sent."""
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("The test season could not be saved.")
        cleaned = normalize_email(email)
        stored_name = normalize_name(name)
        if cleaned is None or stored_name is None:
            raise CloudAuthError("The test season could not be saved.")
        try:
            client = self._client(service_key)
            existing = self.find_user_by_email(cleaned, service_key)
            if existing:
                client.table("profiles").update({"display_name": stored_name}).eq("id", existing).execute()
                return existing
            password = secrets.token_urlsafe(24)
            try:
                response = client.auth.admin.create_user(
                    {
                        "email": cleaned,
                        "password": password,
                        "email_confirm": True,
                        "user_metadata": {"display_name": stored_name},
                    }
                )
                user_id = _created_id(response)
            except Exception:
                user_id = _auth_user_id(client, cleaned)
            if not user_id:
                user_id = _auth_user_id(client, cleaned)
            if not user_id:
                raise CloudAuthError("The test season could not be saved.")
            client.table("profiles").upsert(
                {
                    "id": user_id,
                    "email": cleaned,
                    "display_name": stored_name,
                    "role": "athlete",
                }
            ).execute()
        except CloudAuthError:
            raise
        except Exception:
            raise CloudAuthError("The test season could not be saved.") from None
        return user_id

    def write_owned_season(self, user_id: object, service_key: object, goal: object, plan_row: object, name: object) -> None:
        """Replace one athlete's goal and plan. The signed-in user is not the target."""
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("The test season could not be saved.")
        if not isinstance(user_id, str) or not isinstance(goal, dict) or not isinstance(plan_row, dict):
            raise CloudAuthError("The test season could not be saved.")
        stored_name = normalize_name(name) or ""
        try:
            client = self._client(service_key)
            if stored_name:
                client.table("profiles").update({"display_name": stored_name}).eq("id", user_id).execute()
            saved_goal = _clean_goal(goal)
            saved_goal["user_id"] = user_id
            client.table("goals").upsert(saved_goal).execute()
            client.table("results").delete().eq("user_id", user_id).execute()
            client.table("plans").delete().eq("user_id", user_id).execute()
            saved_plan = _plan_row(plan_row, user_id)
            client.table("plans").insert(saved_plan).execute()
        except Exception:
            raise CloudAuthError("The test season could not be saved.") from None

    def read_owned_season(self, user_id: object, service_key: object) -> dict | None:
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("The test season could not be saved.")
        if not isinstance(user_id, str):
            return None
        try:
            client = self._client(service_key)
            goal = _first(client.table("goals").select("*").eq("user_id", user_id).execute())
            plans = _rows(_plans_query(client, user_id).execute())
        except Exception:
            raise CloudAuthError("The test season could not be saved.") from None
        return {"goal": goal or _blank_goal(), "plan_row": plans[-1] if plans else None}

    def delete_user_by_id(self, user_id: object, service_key: object) -> bool:
        """Remove one athlete by id with the server key. No other account is touched."""
        if not isinstance(service_key, str) or not service_key.strip():
            raise CloudAuthError("The test season could not be removed.")
        if not isinstance(user_id, str) or not user_id:
            return False
        try:
            client = self._client(service_key)
            self._drop_hosted_for_user(user_id)
            client.table("results").delete().eq("user_id", user_id).execute()
            client.table("plans").delete().eq("user_id", user_id).execute()
            client.table("goals").delete().eq("user_id", user_id).execute()
            client.table("profiles").delete().eq("id", user_id).execute()
            client.auth.admin.delete_user(user_id)
        except Exception:
            raise CloudAuthError("The test season could not be removed.") from None
        return True

    def verified_user(self, access_token: object) -> dict | None:
        """Auth identity for this JWT. profiles.email is not read."""
        raw = self._auth_user(access_token)
        if not isinstance(raw, dict):
            return None
        user_id = raw.get("id")
        email = raw.get("email")
        if not user_id or not isinstance(email, str) or not email:
            return None
        confirmed = raw.get("email_confirmed_at") or ""
        return {"id": str(user_id), "email": email, "email_confirmed_at": confirmed}

    def save_hosted_session(self, record: object) -> str:
        """Write tokens with the service role. The cookie is only the session id."""
        if not isinstance(record, dict) or not self.service_key:
            raise CloudAuthError("Sign in again.")
        access = record.get("access_token")
        user_id = record.get("user_id")
        if not isinstance(access, str) or not access or not isinstance(user_id, str) or not user_id:
            raise CloudAuthError("Sign in again.")
        sid = new_hosted_sid()
        issued = _issued(record.get("issued_at"))
        row = _hosted_record(record, issued)
        row["sid_hash"] = hosted_hash(sid)
        try:
            self._client(self.service_key).table("app_sessions").upsert(row).execute()
        except Exception as exc:
            raise CloudAuthError("Sign in again.") from exc
        return sid

    def load_hosted_session(self, sid: object) -> dict | None:
        if not hosted_sid(sid) or not self.service_key:
            return None
        try:
            row = _first(
                self._client(self.service_key)
                .table("app_sessions")
                .select("*")
                .eq("sid_hash", hosted_hash(str(sid)))
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise CloudAuthError("Sign in again.") from exc
        if not isinstance(row, dict) or _hosted_expired(row):
            if isinstance(row, dict):
                self.drop_hosted_session(sid)
            self._purge_expired_sessions()
            return None
        self._purge_expired_sessions()
        return _open_hosted_row(row)

    def update_hosted_session(self, sid: object, record: object) -> None:
        if not hosted_sid(sid) or not isinstance(record, dict) or not self.service_key:
            return
        current = self.load_hosted_session(sid)
        if not isinstance(current, dict):
            return
        issued = int(current.get("issued_at") or _issued(None))
        row = _hosted_record(record, issued)
        row["sid_hash"] = hosted_hash(str(sid))
        row["issued_at"] = issued
        try:
            self._client(self.service_key).table("app_sessions").upsert(row).execute()
        except Exception as exc:
            raise CloudAuthError("Sign in again.") from exc

    def _purge_expired_sessions(self) -> None:
        """Drop expired rows. A missing table does not block the sign-in."""
        if not self.service_key:
            return
        try:
            self._client(self.service_key).table("app_sessions").delete().lt(
                "expires_at", datetime.now(timezone.utc).isoformat()
            ).execute()
        except Exception:
            return

    def drop_hosted_session(self, sid: object) -> None:
        if not hosted_sid(sid) or not self.service_key:
            return
        try:
            self._client(self.service_key).table("app_sessions").delete().eq(
                "sid_hash", hosted_hash(str(sid))
            ).execute()
        except Exception as exc:
            raise CloudAuthError("Sign in again.") from exc

    def _drop_hosted_for_user(self, user_id: str) -> None:
        """Best effort. A missing table does not block account deletion."""
        if not self.service_key or not user_id:
            return
        try:
            self._client(self.service_key).table("app_sessions").delete().eq("user_id", user_id).execute()
        except Exception:
            return

    def _user_client(self, access_token: object):
        if not isinstance(access_token, str) or not access_token:
            raise CloudAuthError("Sign in again.")
        client = self._client(self.anon_key)
        try:
            client.postgrest.auth(access_token)
        except Exception as exc:
            raise CloudAuthError("Sign in again.") from exc
        return client

    def _token_user(self, client, access_token: str) -> str:
        """Who this token is. The client's saved session is not consulted."""
        return self._auth_record(client, access_token)["id"]

    def _auth_record(self, client, access_token: str) -> dict:
        """One server check of this token. The client's saved session is not read."""
        if not isinstance(access_token, str) or not access_token:
            raise CloudAuthError("Sign in again.")
        try:
            user = client.auth.get_user(access_token)
        except Exception as exc:
            raise CloudAuthError("Sign in again.") from exc
        found = getattr(user, "user", user)
        record = _plain_auth_user(found)
        if not record.get("id"):
            raise CloudAuthError("Sign in again.")
        return record

    def _ensure_profile(self, session: dict, name: str) -> None:
        """Insert this athlete's profile, or update the display name only.

        Role and email are not written on update. Email is set once, from
        the auth user, and the database lock keeps it there.
        """
        client = self._user_client(session["access_token"])
        table = client.table("profiles")
        user_id = str(session["user_id"])
        email = str(session.get("email") or "")
        display = (name or str(session.get("display_name") or "")).strip()
        try:
            if _has_profile(table, user_id):
                _touch_profile(table, user_id, email, display)
                return
            table.insert(
                {"id": user_id, "email": email, "display_name": display}
            ).execute()
        except CloudAuthError:
            raise
        except Exception:
            try:
                _touch_profile(table, user_id, email, display)
                if not _has_profile(table, user_id):
                    raise CloudAuthError(SIGNUP_PROFILE)
            except CloudAuthError:
                raise
            except Exception as exc:
                raise CloudAuthError(SIGNUP_PROFILE) from exc

    def _auth_user(self, access_token: object) -> dict | None:
        """The signed-in auth user, or None. The token is not returned."""
        if not isinstance(access_token, str) or not access_token:
            return None
        try:
            return self._auth_request("GET", access_token, None)
        except Exception:
            return None

    def _auth_user_update(self, access_token: str, data: dict) -> None:
        """Merge fields onto user_metadata. Existing name metadata stays."""
        self._auth_request("PUT", access_token, {"data": data})

    def _auth_request(self, method: str, access_token: str, body: dict | None) -> dict:
        import json

        payload = None if body is None else json.dumps(body).encode("utf-8")
        pool = _http_pool()
        response = pool.request(
            method,
            self.url.rstrip("/") + "/auth/v1/user",
            content=payload,
            headers={
                "apikey": self.anon_key,
                "Authorization": "Bearer " + access_token,
                "Content-Type": "application/json",
            },
            timeout=8,
        )
        response.raise_for_status()
        raw = response.content
        if not raw:
            return {}
        parsed = json.loads(raw.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}


def memory_directory() -> MemoryDirectory:
    global _MEMORY
    if _MEMORY is None:
        _MEMORY = MemoryDirectory()
    return _MEMORY


def reset_memory_directory() -> MemoryDirectory:
    global _MEMORY
    _MEMORY = MemoryDirectory()
    return _MEMORY


def current_directory():
    """The memory stand-in, the hosted project, or None when accounts are not set up."""
    if os.environ.get("RIO_AUTH_BACKEND", "").strip() == "memory":
        return memory_directory()
    from ui.cloud_config import cloud_settings

    settings = cloud_settings()
    if settings is None:
        return None
    return SupabaseDirectory(settings["url"], settings["anon_key"], settings["service_key"])


def _blank_goal() -> dict:
    return {
        "event": "800m",
        "goal_time": "",
        "goal_date": "",
        "current_mark": "",
    }


def _clean_goal(goal: dict) -> dict:
    cleaned = _blank_goal()
    for key in cleaned:
        value = goal.get(key)
        if isinstance(value, str):
            cleaned[key] = value.strip()
    return cleaned


def _public_user(user: dict) -> dict:
    row = {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "role": user["role"],
        "created_at": user["created_at"],
    }
    pace = user.get("pace_units")
    if pace in ("mi", "km"):
        row["pace_units"] = pace
    from ui.settings import TIME_ZONES

    zone = user.get("timezone")
    if isinstance(zone, str) and zone in TIME_ZONES:
        row["timezone"] = zone
    easy = stored_easy_pair(user.get("easy_pace"), user.get("easy_pace_unit"))
    if easy is not None:
        row["easy_pace"] = easy[0]
        row["easy_pace_unit"] = easy[1]
    if isinstance(user.get("intro_seen"), bool):
        row["intro_seen"] = user["intro_seen"]
    if isinstance(user.get("strava_prompt_seen"), bool):
        row["strava_prompt_seen"] = user["strava_prompt_seen"]
    if isinstance(user.get("no_watch"), bool):
        row["no_watch"] = user["no_watch"]
    for key in ("date_format", "start_date", "confirm_adapt", "show_ids", "compact", "preferred"):
        if key in user:
            row[key] = user[key]
    return row


def _metadata_dict(user: object) -> dict | None:
    """user_metadata from an auth user. Missing metadata is None."""
    meta = None
    if isinstance(user, dict):
        meta = user.get("user_metadata")
        if not isinstance(meta, dict):
            nested = user.get("user")
            if isinstance(nested, dict):
                meta = nested.get("user_metadata")
    else:
        meta = getattr(user, "user_metadata", None)
    if isinstance(meta, dict):
        return meta
    return None


def stored_easy_pair(pace: object, unit: object) -> tuple[str, str] | None:
    """Canonical easy pace and mi or km, or None when either is unusable."""
    text = canonical_easy_pace(pace)
    if text is None or unit not in ("mi", "km"):
        return None
    return text, unit


def easy_pace_from_metadata(user: object) -> tuple[str, str] | None:
    """The easy pace on the auth user, when both the pace and the unit are stored."""
    meta = _metadata_dict(user)
    if meta is None:
        return None
    return stored_easy_pair(meta.get("easy_pace"), meta.get("easy_pace_unit"))


def _zone_from_metadata(user: object) -> str | None:
    """The Settings time zone on the auth user, when it is one this app lists."""
    from ui.settings import TIME_ZONES

    meta = _metadata_dict(user)
    if meta is None:
        return None
    zone = meta.get("timezone")
    if isinstance(zone, str) and zone in TIME_ZONES:
        return zone
    return None


def _pace_from_metadata(user: object) -> str | None:
    """pace_units on the auth user, when it is per mile or per km."""
    meta = _metadata_dict(user)
    if meta is None:
        return None
    pace = meta.get("pace_units")
    if pace in ("mi", "km"):
        return pace
    return None


def intro_seen_value(user: object) -> bool | None:
    """True or False when the intro flag is stored. None when it is absent."""
    meta = _metadata_dict(user)
    if meta is None or "intro_seen" not in meta:
        return None
    return meta.get("intro_seen") is True


def no_watch_value(user: object) -> bool | None:
    """True or False when Done-only logging is stored. None when it is absent."""
    meta = _metadata_dict(user)
    if meta is None or "no_watch" not in meta:
        return None
    return meta.get("no_watch") is True


def _log_store(action: str, exc: BaseException) -> None:
    """Record the failure type. The message can contain a token, so it is not logged."""
    import logging

    logging.getLogger("rio.cloud").warning("supabase %s failed: %s", action, type(exc).__name__)


def _exc_text(exc: BaseException) -> str:
    parts = [type(exc).__name__, str(exc)]
    for attr in ("message", "code", "error_code", "error", "error_description"):
        value = getattr(exc, attr, None)
        if isinstance(value, str):
            parts.append(value)
    status = getattr(exc, "status", None)
    if status is not None:
        parts.append(str(status))
    return " ".join(parts).casefold()


def signup_error_message(exc: BaseException) -> str:
    """A human message for a sign-up failure. The raw response is not shown."""
    text = _exc_text(exc)
    status = getattr(exc, "status", None)
    if (
        status == 429
        or "429" in text
        or "rate limit" in text
        or "too many" in text
        or "over_email_send_rate_limit" in text
        or "over_request_rate_limit" in text
    ):
        return SIGNUP_RATE
    if any(
        token in text
        for token in (
            "already registered",
            "already been registered",
            "already exists",
            "user already",
            "email_exists",
            "duplicate",
        )
    ):
        return SIGNUP_EXISTS
    if "password" in text and any(
        token in text for token in ("short", "least", "weak", "length", "characters", "6")
    ):
        return SIGNUP_PASSWORD
    if any(
        token in text
        for token in (
            "signups not allowed",
            "signup is disabled",
            "signups disabled",
            "sign up is disabled",
        )
    ):
        return SIGNUP_DISABLED
    if "invalid" in text and "email" in text:
        return SIGNUP_EMAIL
    return SIGNUP_FAILED


def signin_error_message(exc: BaseException) -> str:
    """A human message for a sign-in failure. A wrong password stays generic."""
    text = _exc_text(exc)
    if (
        "not confirmed" in text
        or "email_not_confirmed" in text
        or "confirm your" in text
    ):
        return SIGNUP_CONFIRM
    status = getattr(exc, "status", None)
    if status == 429 or "rate limit" in text or "too many" in text:
        return SIGNIN_RATE
    return SIGNIN_MISMATCH


def _response_parts(response: object) -> tuple[object, object]:
    if isinstance(response, dict):
        return response.get("session"), response.get("user")
    return getattr(response, "session", None), getattr(response, "user", None)


def signup_outcome(response: object, name: str) -> dict:
    """A session, or a clear error when the project returns no session.

    Confirm email returns a user and no session. An address that already
    exists comes back with an empty identities list and no session.
    """
    session, user = _response_parts(response)
    access = _attr(session, "access_token")
    user_id = _attr(user, "id")
    if access and user_id:
        return _session_dict(response, name)
    if user_id:
        identities = _attr(user, "identities")
        if isinstance(identities, list) and len(identities) == 0:
            raise CloudAuthError(SIGNUP_EXISTS)
        raise CloudAuthError(SIGNUP_CONFIRM)
    raise CloudAuthError(SIGNUP_FAILED)


def _has_profile(table: object, user_id: str) -> bool:
    found = table.select("id").eq("id", user_id).execute()
    data = getattr(found, "data", None)
    return isinstance(data, list) and len(data) > 0


def _touch_profile(table: object, user_id: str, _email: str, display: str) -> None:
    """Display name only. profiles.email is not an athlete-writable column."""
    if not display:
        return
    table.update({"display_name": display}).eq("id", user_id).execute()


def _issued(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return int(time.time())
    return value


def _session_fernet():
    """Fernet from RIO_SESSION_KEY. None when the secret is not set."""
    raw = os.environ.get("RIO_SESSION_KEY", "").strip()
    if not raw:
        return None
    from cryptography.fernet import Fernet

    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode("utf-8")).digest())
    return Fernet(key)


def seal_session_secret(value: str) -> str:
    """Seal a token for app_sessions. Plaintext stays readable if no key is set."""
    if not value:
        return ""
    box = _session_fernet()
    if box is None:
        return value
    return "f2." + box.encrypt(value.encode("utf-8")).decode("ascii")


def open_session_secret(value: object) -> str:
    """Open a sealed token. An older plaintext row still opens."""
    if not isinstance(value, str) or not value:
        return ""
    if not value.startswith("f2."):
        return value
    box = _session_fernet()
    if box is None:
        return ""
    try:
        return box.decrypt(value[3:].encode("ascii")).decode("utf-8")
    except Exception:
        return ""


def _hosted_record(record: dict, issued: int) -> dict:
    expires = datetime.fromtimestamp(issued + SESSION_SECONDS, timezone.utc).isoformat()
    return {
        "user_id": str(record.get("user_id") or ""),
        "access_token": seal_session_secret(str(record.get("access_token") or "")),
        "refresh_token": seal_session_secret(str(record.get("refresh_token") or "")),
        "email": str(record.get("email") or ""),
        "display_name": str(record.get("display_name") or ""),
        "issued_at": issued,
        "expires_at": expires,
    }


def _open_hosted_row(row: dict) -> dict:
    opened = dict(row)
    opened["access_token"] = open_session_secret(row.get("access_token"))
    opened["refresh_token"] = open_session_secret(row.get("refresh_token"))
    return opened


PLAN_CONFLICT = "user_id,start_date,goal_date,current_time,goal_time"


def _plain_auth_user(found: object) -> dict:
    """id, email, and confirmation from a get_user result. The token is not copied."""
    if isinstance(found, dict):
        raw = found
    else:
        raw = {
            "id": getattr(found, "id", None),
            "email": getattr(found, "email", None),
            "email_confirmed_at": getattr(found, "email_confirmed_at", None),
            "user_metadata": getattr(found, "user_metadata", None),
        }
    user_id = raw.get("id")
    email = raw.get("email")
    confirmed = raw.get("email_confirmed_at")
    meta = raw.get("user_metadata")
    return {
        "id": "" if not user_id else str(user_id),
        "email": email if isinstance(email, str) else "",
        "email_confirmed_at": "" if not confirmed else str(confirmed),
        "user_metadata": meta if isinstance(meta, dict) else None,
    }


def _embedded_bundle(row: dict | None) -> tuple:
    """Split one profile response. No profile row is an empty bundle, not an error."""
    if row is None:
        return {}, None, [], []
    if not isinstance(row, dict) or any(key not in row for key in ("goals", "plans", "results")):
        raise RuntimeError("bundle embed")
    profile = {
        key: value
        for key, value in row.items()
        if key not in ("goals", "plans", "results")
    }
    return profile, _one_row(row.get("goals")), _sort_plans(_many_rows(row.get("plans"))), _many_rows(row.get("results"))


def _one_row(value: object) -> dict | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    return None


def _many_rows(value: object) -> list:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _sort_plans(plans: list) -> list:
    """Oldest first, matching the plans query, so the last row is the newest."""

    def _key(row: dict) -> tuple:
        updated = row.get("updated_at")
        ident = row.get("id")
        missing = not isinstance(updated, str) or not updated
        return (
            1 if missing else 0,
            "" if missing else updated,
            "" if ident is None else str(ident),
        )

    return sorted(plans, key=_key)


def _plans_query(client, user_id: str):
    """Oldest first, so the last row is the one most recently saved."""
    return (
        client.table("plans")
        .select("*")
        .eq("user_id", user_id)
        .order("updated_at")
        .order("id")
    )


def _plan_row(plan: dict, user_id: str) -> dict:
    """One season row. The primary key is not sent, so the season key can match."""
    saved = dict(plan)
    saved.pop("id", None)
    saved["user_id"] = user_id
    for key in ("start_date", "goal_date", "current_time", "goal_time"):
        if not isinstance(saved.get(key), str):
            saved[key] = ""
    saved["updated_at"] = datetime.now(timezone.utc).isoformat()
    return saved


def _missing_plan_key(exc: BaseException) -> bool:
    """True when the season unique index has not been created yet."""
    text = _exc_text(exc)
    return "42p10" in text or "no unique" in text or "no matching" in text or "on conflict" in text


def _missing_delete_season(exc: BaseException) -> bool:
    """True when delete_past_season has not been created yet."""
    text = _exc_text(exc)
    if "42883" in text or "pgrst202" in text:
        return True
    if "delete_past_season" in text and (
        "does not exist" in text or "could not find" in text or "schema cache" in text
    ):
        return True
    return False


def _save_plan(client, saved: dict) -> None:
    """Update the season in place. Fall back to an insert if the key is not there yet."""
    try:
        client.table("plans").upsert(saved, on_conflict=PLAN_CONFLICT).execute()
    except Exception as exc:
        if not _missing_plan_key(exc):
            raise
        import logging

        logging.getLogger("rio.cloud").warning(
            "plans_season_key unavailable; inserting a plan row"
        )
        client.table("plans").upsert(saved).execute()


def _hosted_expired(row: dict, *, now: int | None = None) -> bool:
    issued = row.get("issued_at")
    if isinstance(issued, str) and issued.isdigit():
        issued = int(issued)
    if isinstance(issued, bool) or not isinstance(issued, int):
        return True
    moment = int(time.time()) if now is None else int(now)
    return moment - issued >= SESSION_SECONDS


def _session_dict(response: object, name: str) -> dict:
    session = getattr(response, "session", None)
    user = getattr(response, "user", None)
    if session is None and isinstance(response, dict):
        session = response.get("session")
        user = response.get("user")
    access = _attr(session, "access_token")
    refresh = _attr(session, "refresh_token")
    user_id = _attr(user, "id")
    email = _attr(user, "email")
    if not access or not user_id:
        raise CloudAuthError("The account could not be opened.")
    return {
        "access_token": str(access),
        "refresh_token": str(refresh or ""),
        "user_id": str(user_id),
        "email": str(email or ""),
        "display_name": name,
        "role": "athlete",
    }


def _attr(obj: object, name: str):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _rows(response: object) -> list:
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return data
    return []


def _first(response: object) -> dict | None:
    rows = _rows(response)
    if rows and isinstance(rows[0], dict):
        return rows[0]
    return None


def _created_id(response: object) -> str | None:
    user = getattr(response, "user", None)
    if user is None and isinstance(response, dict):
        user = response.get("user") or response
    user_id = _attr(user, "id")
    if user_id:
        return str(user_id)
    return None


def _auth_user_id(client, email: str) -> str | None:
    """Find a confirmed user by email. Used when create reports the address is taken."""
    page = 1
    while page <= 20:
        try:
            batch = client.auth.admin.list_users(page=page, per_page=200)
        except TypeError:
            batch = client.auth.admin.list_users()
            page = 20
        users = _user_list(batch)
        if not users:
            return None
        for user in users:
            found = _attr(user, "email")
            if isinstance(found, str) and found.casefold() == email:
                user_id = _attr(user, "id")
                if user_id:
                    return str(user_id)
        if len(users) < 200:
            return None
        page += 1
    return None


def _user_list(batch: object) -> list:
    if isinstance(batch, list):
        return batch
    users = getattr(batch, "users", None)
    if isinstance(users, list):
        return users
    if isinstance(batch, dict):
        found = batch.get("users") or batch.get("data")
        if isinstance(found, list):
            return found
    return []
