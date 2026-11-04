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
from copy import deepcopy
from datetime import datetime, timezone

from ui.accounts import normalize_email, normalize_name, password_ok

_MEMORY: "MemoryDirectory | None" = None


class CloudAuthError(ValueError):
    """A sign-in or save failed. The message is safe to show."""


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
        email = self.users[user_id]["email"]
        self.by_email.pop(email, None)
        self.users.pop(user_id, None)
        dead = [token for token, owner in self.sessions.items() if owner == user_id]
        for token in dead:
            self.sessions.pop(token, None)

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


# One anon client per project, so a Google redirect can finish in this process.
_ANON_CLIENTS: dict[str, object] = {}


class SupabaseDirectory:
    """The hosted project. Calls stay on the server. Keys are not returned."""

    def __init__(self, url: str, anon_key: str, service_key: str) -> None:
        self.url = url
        self.anon_key = anon_key
        self.service_key = service_key

    def _client(self, key: str):
        try:
            from supabase import create_client
        except ImportError as exc:
            raise CloudAuthError("Accounts could not be reached.") from exc
        if key == self.anon_key:
            cached = _ANON_CLIENTS.get(self.url)
            if cached is not None:
                return cached
        client = create_client(self.url, key)
        if key == self.anon_key:
            _ANON_CLIENTS[self.url] = client
        return client

    def sign_up(self, email: object, password: object, name: object) -> dict:
        cleaned = normalize_email(email)
        stored_name = normalize_name(name)
        if cleaned is None or stored_name is None or not isinstance(password, str):
            raise CloudAuthError("Enter an email address.")
        try:
            response = self._client(self.anon_key).auth.sign_up(
                {
                    "email": cleaned,
                    "password": password,
                    "options": {"data": {"display_name": stored_name}},
                }
            )
        except Exception as exc:
            raise CloudAuthError("The account could not be created.") from exc
        session = _session_dict(response, stored_name)
        self._ensure_profile(session, stored_name)
        return session

    def sign_in(self, email: object, password: object) -> dict:
        cleaned = normalize_email(email)
        if cleaned is None or not isinstance(password, str):
            raise CloudAuthError("Email or password does not match.")
        try:
            response = self._client(self.anon_key).auth.sign_in_with_password(
                {"email": cleaned, "password": password}
            )
        except Exception as exc:
            raise CloudAuthError("Email or password does not match.") from exc
        return _session_dict(response, "")

    def sign_out(self, access_token: object) -> None:
        try:
            client = self._client(self.anon_key)
            if isinstance(access_token, str) and access_token:
                client.auth.sign_out()
        except Exception:
            return

    def google_url(self, redirect_to: str) -> str:
        try:
            response = self._client(self.anon_key).auth.sign_in_with_oauth(
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
            response = self._client(self.anon_key).auth.exchange_code_for_session(
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
        from ui.cloud_config import app_url

        try:
            self._client(self.anon_key).auth.reset_password_for_email(
                cleaned,
                {"redirect_to": app_url() + "/?reset=password"},
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
        user_id = self._token_user(client)
        profile = _first(client.table("profiles").select("*").eq("id", user_id).execute())
        goal = _first(client.table("goals").select("*").eq("user_id", user_id).execute())
        plans = _rows(client.table("plans").select("*").eq("user_id", user_id).execute())
        results = _rows(client.table("results").select("*").eq("user_id", user_id).execute())
        return {
            "profile": profile or {},
            "goal": goal or _blank_goal(),
            "plans": plans,
            "results": results,
        }

    def save_bundle(self, access_token: object, bundle: object) -> None:
        if not isinstance(bundle, dict):
            raise CloudAuthError("This account could not be saved.")
        client = self._user_client(access_token)
        user_id = self._token_user(client)
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
        user_id = self._token_user(client)
        client.table("results").delete().eq("user_id", user_id).execute()
        client.table("plans").delete().eq("user_id", user_id).execute()
        client.table("goals").delete().eq("user_id", user_id).execute()
        client.table("profiles").delete().eq("id", user_id).execute()
        try:
            self._client(service_key).auth.admin.delete_user(user_id)
        except Exception as exc:
            raise CloudAuthError("This account could not be removed on the server.") from exc

    def _user_client(self, access_token: object):
        if not isinstance(access_token, str) or not access_token:
            raise CloudAuthError("Sign in again.")
        client = self._client(self.anon_key)
        try:
            client.postgrest.auth(access_token)
        except Exception as exc:
            raise CloudAuthError("Sign in again.") from exc
        return client

    def _token_user(self, client) -> str:
        try:
            user = client.auth.get_user()
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
        client = self._user_client(session["access_token"])
        client.table("profiles").upsert(
            {
                "id": session["user_id"],
                "email": session["email"],
                "display_name": name or session.get("display_name") or "",
            }
        ).execute()


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
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


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
