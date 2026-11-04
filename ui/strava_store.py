# strava_store.py — tokens stay on the server. Activities stay with their owner.

"""The service role key can read tokens. A signed-in user cannot.

Activities are stored per user. Another user's id returns nothing.
"""

from __future__ import annotations

import os
from copy import deepcopy

_MEMORY: "MemoryStrava | None" = None


class MemoryStrava:
    """Offline stand-in. Tokens are not returned without the server key."""

    def __init__(self) -> None:
        self.tokens: dict[str, dict] = {}
        self.activities: dict[str, list] = {}

    def put_token(self, user_id: str, record: dict, service_key: str) -> None:
        if not service_key:
            raise PermissionError("tokens stay on the server")
        self.tokens[user_id] = deepcopy(record)

    def get_token(self, user_id: str, service_key: str) -> dict | None:
        if not service_key:
            return None
        found = self.tokens.get(user_id)
        return deepcopy(found) if isinstance(found, dict) else None

    def put_activities(self, user_id: str, rows: list, service_key: str = "") -> None:
        del service_key
        current = list(self.activities.get(user_id) or [])
        by_id = {}
        for row in current:
            if isinstance(row, dict) and row.get("id"):
                by_id[row["id"]] = row
        for row in rows:
            if isinstance(row, dict) and row.get("id"):
                by_id[row["id"]] = deepcopy(row)
        self.activities[user_id] = list(by_id.values())

    def get_activities(self, user_id: str, service_key: str = "") -> list:
        del service_key
        return deepcopy(self.activities.get(user_id) or [])

    def delete_user(self, user_id: str, service_key: str) -> None:
        if not service_key:
            raise PermissionError("tokens stay on the server")
        self.tokens.pop(user_id, None)
        self.activities.pop(user_id, None)


def memory_strava() -> MemoryStrava:
    global _MEMORY
    if _MEMORY is None:
        _MEMORY = MemoryStrava()
    return _MEMORY


def reset_memory_strava() -> MemoryStrava:
    global _MEMORY
    _MEMORY = MemoryStrava()
    return _MEMORY


class SupabaseStrava:
    """Tokens use the service role client. Activities use the signed-in user."""

    def __init__(self, url: str, anon_key: str, service_key: str, access_token: str) -> None:
        self.url = url
        self.anon_key = anon_key
        self.service_key = service_key
        self.access_token = access_token

    def _service(self):
        from supabase import create_client
        from ui.cloud_store import _fresh_options

        return create_client(self.url, self.service_key, options=_fresh_options())

    def _owner_client(self):
        from supabase import create_client
        from ui.cloud_store import _fresh_options

        client = create_client(self.url, self.anon_key, options=_fresh_options())
        client.postgrest.auth(self.access_token)
        return client

    def _server_write(self, service_key: str) -> bool:
        return isinstance(service_key, str) and bool(service_key) and service_key == self.service_key

    def owner_id(self) -> str:
        """The auth user for this access token. A caller-supplied id is not trusted."""
        from supabase import create_client
        from ui.cloud_store import _fresh_options

        client = create_client(self.url, self.anon_key, options=_fresh_options())
        user = client.auth.get_user(self.access_token)
        found = getattr(user, "user", user)
        user_id = getattr(found, "id", None)
        if not user_id and isinstance(found, dict):
            user_id = found.get("id")
        if not user_id:
            raise PermissionError("activities stay with their owner")
        return str(user_id)

    def put_token(self, user_id: str, record: dict, service_key: str) -> None:
        if not service_key:
            raise PermissionError("tokens stay on the server")
        self._service().table("strava_tokens").upsert(
            {
                "user_id": user_id,
                "athlete_id": record.get("athlete_id"),
                "athlete_name": record.get("athlete_name") or "",
                "access_token": record.get("access_token") or "",
                "refresh_token": record.get("refresh_token") or "",
                "expires_at": record.get("expires_at"),
                "last_sync_at": record.get("last_sync_at"),
                "scope": record.get("scope") or "",
            }
        ).execute()

    def get_token(self, user_id: str, service_key: str) -> dict | None:
        if not service_key:
            return None
        response = self._service().table("strava_tokens").select("*").eq("user_id", user_id).execute()
        rows = getattr(response, "data", None) or []
        if not rows:
            return None
        row = rows[0]
        return {
            "access_token": row.get("access_token") or "",
            "refresh_token": row.get("refresh_token") or "",
            "expires_at": row.get("expires_at"),
            "athlete_id": row.get("athlete_id"),
            "athlete_name": row.get("athlete_name") or "",
            "scope": row.get("scope") or "",
            "last_sync_at": row.get("last_sync_at"),
        }

    def put_activities(self, user_id: str, rows: list, service_key: str = "") -> None:
        """Own rows use the signed-in JWT, in batches. Tokens stay on _service().

        The TEST season passes the server key and writes that athlete only.
        """
        client = self._service() if self._server_write(service_key) else self._owner_client()
        if not self._server_write(service_key) and self.owner_id() != user_id:
            raise PermissionError("activities stay with their owner")
        payload = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            payload.append(
                {
                    "user_id": user_id,
                    "activity_id": row.get("id"),
                    "name": row.get("name") or "",
                    "sport_type": row.get("sport_type") or "",
                    "start_local": row.get("date") or "",
                    "distance_m": row.get("distance_m"),
                    "moving_seconds": row.get("moving_seconds"),
                    "elapsed_seconds": row.get("elapsed_seconds"),
                    "pace_s_per_km": row.get("pace_s_per_km"),
                    "average_hr": row.get("average_hr"),
                    "max_hr": row.get("max_hr"),
                    "laps": row.get("laps") or [],
                    "template_id": row.get("template_id") or "",
                    "matched": row.get("matched") is True,
                }
            )
        for start in range(0, len(payload), 500):
            client.table("strava_activities").upsert(
                payload[start : start + 500],
                on_conflict="user_id,activity_id",
            ).execute()

    def get_activities(self, user_id: str, service_key: str = "") -> list:
        client = self._service() if self._server_write(service_key) else self._owner_client()
        if not self._server_write(service_key) and self.owner_id() != user_id:
            raise PermissionError("activities stay with their owner")
        response = (
            client.table("strava_activities").select("*").eq("user_id", user_id).execute()
        )
        rows = getattr(response, "data", None) or []
        found = []
        for row in rows:
            found.append(
                {
                    "id": row.get("activity_id"),
                    "name": row.get("name") or "Run",
                    "sport_type": row.get("sport_type") or "",
                    "date": row.get("start_local") or "",
                    "distance_m": row.get("distance_m"),
                    "moving_seconds": row.get("moving_seconds"),
                    "elapsed_seconds": row.get("elapsed_seconds"),
                    "pace_s_per_km": row.get("pace_s_per_km"),
                    "average_hr": row.get("average_hr"),
                    "max_hr": row.get("max_hr"),
                    "laps": row.get("laps") or [],
                    "template_id": row.get("template_id") or "",
                    "matched": row.get("matched") is True,
                    "start_local": row.get("start_local") or "",
                }
            )
        return found

    def delete_user(self, user_id: str, service_key: str) -> None:
        if not service_key:
            raise PermissionError("tokens stay on the server")
        client = self._service()
        client.table("strava_activities").delete().eq("user_id", user_id).execute()
        client.table("strava_tokens").delete().eq("user_id", user_id).execute()


def current_strava_store():
    """The memory stand-in, or the hosted project when a server key exists."""
    if os.environ.get("RIO_AUTH_BACKEND", "").strip() == "memory":
        return memory_strava()
    from ui.cloud_config import cloud_settings

    settings = cloud_settings()
    if settings is None or not settings.get("service_key"):
        return None
    try:
        import streamlit as st

        access = st.session_state.get("rio_cloud_access") or ""
    except Exception:
        access = ""
    return SupabaseStrava(settings["url"], settings["anon_key"], settings["service_key"], str(access))
