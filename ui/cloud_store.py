# cloud_store.py — one athlete's rows, or an offline stand-in.

"""Sign-up, sign-in, plans, and results.

The memory directory is the offline stand-in. It never opens a network
connection. A configured project uses the Supabase client instead.
The service role key is only accepted by list and delete. It is not
stored on a user session.
"""

from __future__ import annotations

import os
import secrets
import time
from copy import deepcopy
from datetime import datetime, timezone

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

    def exchange_code(self, code: object) -> dict:
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

    def save_pace_units(self, access_token: object, unit: object) -> None:
        """Remember per mile or per km on this athlete. The other account stays."""
        user_id = self.user_id(access_token)
        if not self._keep_pace(user_id, unit):
            raise CloudAuthError("Pace units could not be saved.")

    def save_intro_seen(self, access_token: object, seen: object) -> None:
        """Remember that this athlete dismissed the intro, or asked to see it again."""
        user_id = self.user_id(access_token)
        if not isinstance(seen, bool):
            raise CloudAuthError("The intro guide could not be saved.")
        user = self.users.get(user_id)
        if user is None:
            raise CloudAuthError("The intro guide could not be saved.")
        user["intro_seen"] = seen

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


# Code-verifier storage for the Google redirect only. It is not a PostgREST client,
# and user queries never read it. Each query builds its own client.
_OAUTH_STORAGE: object | None = None


def _fresh_options(*, oauth: bool = False):
    """No shared session and no automatic refresh. One visitor cannot replace another."""
    from supabase import ClientOptions

    storage = None
    if oauth:
        global _OAUTH_STORAGE
        if _OAUTH_STORAGE is None:
            from supabase_auth import SyncMemoryStorage

            _OAUTH_STORAGE = SyncMemoryStorage()
        storage = _OAUTH_STORAGE
    if storage is None:
        return ClientOptions(persist_session=False, auto_refresh_token=False)
    return ClientOptions(persist_session=False, auto_refresh_token=False, storage=storage)


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

    def _oauth_client(self):
        """The Google round trip keeps its code verifier. This client is not used for rows."""
        try:
            from supabase import create_client
        except ImportError as exc:
            raise CloudAuthError("Accounts could not be reached.") from exc
        return create_client(self.url, self.anon_key, options=_fresh_options(oauth=True))

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
        try:
            response = self._oauth_client().auth.sign_in_with_oauth(
                {
                    "provider": "google",
                    "options": {
                        "redirect_to": redirect_to,
                        "skip_browser_redirect": True,
                    },
                }
            )
        except Exception as exc:
            raise CloudAuthError("Google sign-in could not be started.") from exc
        url = getattr(response, "url", None) or (response.get("url") if isinstance(response, dict) else "")
        if not isinstance(url, str) or not url:
            raise CloudAuthError("Google sign-in could not be started.")
        return url

    def exchange_code(self, code: object) -> dict:
        if not isinstance(code, str) or not code:
            raise CloudAuthError("Sign-in could not be finished. Try again.")
        try:
            response = self._oauth_client().auth.exchange_code_for_session(
                {"auth_code": code}
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
            client.auth.set_session(token, token)
            client.auth.update_user({"password": password})
        except Exception as exc:
            raise CloudAuthError("That reset link is no longer valid.") from exc

    def load_bundle(self, access_token: object) -> dict:
        client = self._user_client(access_token)
        user_id = self._token_user(client, access_token)
        profile = _first(client.table("profiles").select("*").eq("id", user_id).execute())
        goal = _first(client.table("goals").select("*").eq("user_id", user_id).execute())
        plans = _rows(client.table("plans").select("*").eq("user_id", user_id).execute())
        results = _rows(client.table("results").select("*").eq("user_id", user_id).execute())
        profile = profile or {}
        auth_user = self._auth_user(access_token)
        pace = _pace_from_metadata(auth_user)
        intro = intro_seen_value(auth_user)
        if isinstance(profile, dict) and (pace or intro is not None):
            profile = dict(profile)
            if pace:
                profile["pace_units"] = pace
            if intro is not None:
                profile["intro_seen"] = intro
        return {
            "profile": profile,
            "goal": goal or _blank_goal(),
            "plans": plans,
            "results": results,
        }

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

    def save_bundle(self, access_token: object, bundle: object) -> None:
        if not isinstance(bundle, dict):
            raise CloudAuthError("This account could not be saved.")
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
                    saved = dict(plan)
                    saved["user_id"] = user_id
                    client.table("plans").upsert(saved).execute()
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
            saved_plan = deepcopy(plan_row)
            saved_plan["user_id"] = user_id
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
            plans = _rows(client.table("plans").select("*").eq("user_id", user_id).execute())
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
            return None
        return row

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
        if not isinstance(access_token, str) or not access_token:
            raise CloudAuthError("Sign in again.")
        try:
            user = client.auth.get_user(access_token)
        except Exception as exc:
            raise CloudAuthError("Sign in again.") from exc
        found = getattr(user, "user", user)
        user_id = getattr(found, "id", None)
        if not user_id and isinstance(found, dict):
            user_id = found.get("id")
        if not user_id:
            raise CloudAuthError("Sign in again.")
        return str(user_id)

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
        import urllib.request

        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.url.rstrip("/") + "/auth/v1/user",
            data=payload,
            headers={
                "apikey": self.anon_key,
                "Authorization": "Bearer " + access_token,
                "Content-Type": "application/json",
            },
            method=method,
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read()
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
    if isinstance(user.get("intro_seen"), bool):
        row["intro_seen"] = user["intro_seen"]
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


def _hosted_record(record: dict, issued: int) -> dict:
    expires = datetime.fromtimestamp(issued + SESSION_SECONDS, timezone.utc).isoformat()
    return {
        "user_id": str(record.get("user_id") or ""),
        "access_token": str(record.get("access_token") or ""),
        "refresh_token": str(record.get("refresh_token") or ""),
        "email": str(record.get("email") or ""),
        "display_name": str(record.get("display_name") or ""),
        "issued_at": issued,
        "expires_at": expires,
    }


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
