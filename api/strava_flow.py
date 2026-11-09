# strava_flow.py — connect, callback, and sync. Tokens stay on the server.

"""The OAuth nonce is stored on the server and checked on the way back.

RIO_STRAVA_REDIRECT_URI is the callback this process puts in the authorize
URL. When it is unset, the URL is the Streamlit callback (RIO_APP_URL + "/"),
so that registration keeps working. The new site sets the variable when its
own callback is registered with Strava.

Strava HTTP is injected. Tests pass a stand-in. The default is ui.strava.
"""

from __future__ import annotations

import secrets
import time
from datetime import datetime, timezone

from api.errors import ApiError
from services.activity_pull import run_activity_pull
from services.season_commit import apply_activity_marks
from ui.activities import PullError, sync_all, sync_recent
from ui.cloud_config import read_setting
from ui.result import goal_seconds
from ui.strava import (
    CLIENT_ID,
    RateGate,
    StravaError,
    StravaLimited,
    authorize_url,
    configured,
    deauthorize,
    exchange_code,
    http_get,
    http_post,
    import_runs,
    make_state,
    match_runs,
    redirect_uri,
    state_matches,
    to_stored_activity,
)
from ui.strava_store import MemoryStrava

# Ten minutes. A callback after that has to start connect again.
OAUTH_SECONDS = 10 * 60
# The in-memory store's gate. It is not a Supabase service role key.
_MEMORY_KEY = "memory-service"
REDIRECT_ENV = "RIO_STRAVA_REDIRECT_URI"


def redirect_for_api() -> str:
    """The redirect this process sends to Strava.

    A value in RIO_STRAVA_REDIRECT_URI wins. Otherwise the Streamlit root,
    which is what redirect_uri() already returns.
    """
    custom = read_setting(REDIRECT_ENV).strip()
    if custom:
        return custom
    return redirect_uri()


def _memory(app) -> MemoryStrava:
    store = getattr(app.state, "memory_strava", None)
    if not isinstance(store, MemoryStrava):
        store = MemoryStrava()
        app.state.memory_strava = store
    return store


def _memory_key(app) -> str:
    found = getattr(app.state, "strava_service_key", None)
    if isinstance(found, str) and found:
        return found
    return _MEMORY_KEY


def _gate(app) -> RateGate:
    found = getattr(app.state, "strava_gate", None)
    if not isinstance(found, RateGate):
        found = RateGate()
        app.state.strava_gate = found
    return found


def _post_get(app):
    post = getattr(app.state, "strava_post", None) or http_post
    get = getattr(app.state, "strava_get", None) or http_get
    return post, get


class MemoryNonce:
    """One outstanding connect per athlete, on this process."""

    def __init__(self, app) -> None:
        self.app = app

    def _bag(self) -> dict:
        bag = getattr(self.app.state, "oauth_nonces", None)
        if not isinstance(bag, dict):
            bag = {}
            self.app.state.oauth_nonces = bag
        return bag

    def put(self, user_id: str, nonce: str, state: str, redirect: str, expires: int) -> None:
        self._bag()[user_id] = {
            "nonce": nonce,
            "state": state,
            "redirect": redirect,
            "expires": expires,
        }

    def peek(self, user_id: str) -> dict | None:
        row = self._bag().get(user_id)
        if not isinstance(row, dict):
            return None
        expires = row.get("expires")
        if not isinstance(expires, int) or expires < int(time.time()):
            self._bag().pop(user_id, None)
            return None
        return row

    def take(self, user_id: str) -> None:
        self._bag().pop(user_id, None)


class HostedNonce:
    """The strava_oauth row. The service role is the only writer."""

    def __init__(self, directory) -> None:
        self.directory = directory

    def _table(self):
        client = self.directory._client(self.directory.service_key)
        return client.table("strava_oauth")

    def put(self, user_id: str, nonce: str, state: str, redirect: str, expires: int) -> None:
        when = datetime.fromtimestamp(expires, timezone.utc).isoformat()
        try:
            self._table().upsert(
                {
                    "user_id": user_id,
                    "nonce": nonce,
                    "state": state,
                    "redirect_uri": redirect,
                    "expires_at": when,
                },
                on_conflict="user_id",
            ).execute()
        except Exception as exc:
            raise ApiError(503, "Strava sign-in could not be saved. Run migration 010.") from exc

    def peek(self, user_id: str) -> dict | None:
        try:
            found = self._table().select("nonce,state,redirect_uri,expires_at").eq("user_id", user_id).limit(1).execute()
        except Exception as exc:
            raise ApiError(503, "Strava sign-in could not be saved. Run migration 010.") from exc
        rows = getattr(found, "data", None) or []
        if not rows or not isinstance(rows[0], dict):
            return None
        row = rows[0]
        expires = _expires_epoch(row.get("expires_at"))
        if expires is None or expires < int(time.time()):
            self.take(user_id)
            return None
        return {
            "nonce": row.get("nonce") or "",
            "state": row.get("state") or "",
            "redirect": row.get("redirect_uri") or "",
            "expires": expires,
        }

    def take(self, user_id: str) -> None:
        try:
            self._table().delete().eq("user_id", user_id).execute()
        except Exception:
            return


def _expires_epoch(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value:
        text = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return int(parsed.timestamp())
    return None


def _backend(app, principal):
    """Token store, the key that may read tokens, and the nonce store.

    A hosted Supabase directory uses the service role. Anything else uses
    the process memory stand-in. Tests never build a Supabase client here.
    """
    from ui.cloud_store import SupabaseDirectory

    directory = getattr(app.state, "directory", None)
    if (
        isinstance(directory, SupabaseDirectory)
        and principal.kind == "hosted"
        and isinstance(principal.token, str)
        and principal.token
        and directory.service_key
    ):
        from ui.strava_store import SupabaseStrava

        store = SupabaseStrava(
            directory.url,
            directory.anon_key,
            directory.service_key,
            principal.token,
        )
        return store, directory.service_key, HostedNonce(directory)
    return _memory(app), _memory_key(app), MemoryNonce(app)


def _token(store, user_id: str, service_key: str) -> dict | None:
    try:
        found = store.get_token(user_id, service_key)
    except Exception:
        return None
    if isinstance(found, dict) and found.get("access_token"):
        return found
    return None


def _public_status(token: dict | None) -> dict:
    connected = isinstance(token, dict)
    return {
        "configured": configured(),
        "connected": connected,
        "athlete_name": str(token.get("athlete_name") or "") if connected else "",
        "last_sync_at": token.get("last_sync_at") if connected else None,
        "redirect_uri": redirect_for_api() if configured() else "",
    }


def status(app, principal) -> dict:
    store, key, _nonce = _backend(app, principal)
    token = _token(store, principal.user_id, key) if configured() else None
    return _public_status(token)


def connect(app, principal) -> dict:
    """Mint a nonce, store it, and return the authorize URL. Not the nonce."""
    if not configured():
        raise ApiError(503, "Strava is not set up on this server yet.")
    store, key, nonces = _backend(app, principal)
    if _token(store, principal.user_id, key) is not None:
        raise ApiError(409, "Strava is already connected.")
    nonce = secrets.token_urlsafe(18)
    state = make_state(principal.user_id, nonce)
    redirect = redirect_for_api()
    expires = int(time.time()) + OAUTH_SECONDS
    nonces.put(principal.user_id, nonce, state, redirect, expires)
    url = authorize_url(read_setting(CLIENT_ID), redirect, state)
    return {"url": url, "redirect_uri": redirect}


def finish_callback(app, principal, code: object, state: object) -> dict:
    """Exchange the code only when the stored nonce matches this athlete."""
    if not isinstance(code, str) or not code.strip() or len(code) > 512 or any(ch.isspace() for ch in code):
        raise ApiError(400, "Strava could not be connected.")
    if not isinstance(state, str) or not state.startswith("strava:"):
        raise ApiError(400, "Strava could not be connected.")
    if not configured():
        raise ApiError(503, "Strava is not set up on this server yet.")
    store, key, nonces = _backend(app, principal)
    saved = nonces.peek(principal.user_id)
    nonce = saved.get("nonce") if isinstance(saved, dict) else ""
    if not isinstance(nonce, str) or not nonce:
        raise ApiError(400, "Strava could not be connected.")
    if not state_matches(state, principal.user_id, nonce):
        raise ApiError(400, "Strava could not be connected.")
    redirect = saved.get("redirect") if isinstance(saved, dict) else ""
    if redirect and redirect != redirect_for_api():
        raise ApiError(400, "Strava could not be connected.")
    nonces.take(principal.user_id)
    post, _get = _post_get(app)
    try:
        token = exchange_code(code.strip(), post)
    except StravaError as exc:
        raise ApiError(400, str(exc)) from exc
    try:
        store.put_token(principal.user_id, token, key)
    except Exception as exc:
        raise ApiError(400, "Strava could not be saved.") from exc
    return {"connected": True, "athlete_name": str(token.get("athlete_name") or "")}


def disconnect(app, principal) -> dict:
    store, key, nonces = _backend(app, principal)
    token = _token(store, principal.user_id, key)
    if isinstance(token, dict) and isinstance(token.get("access_token"), str):
        post, _get = _post_get(app)
        try:
            deauthorize(token["access_token"], post)
        except StravaError:
            pass
    try:
        store.delete_user(principal.user_id, key)
    except Exception as exc:
        raise ApiError(400, "Strava could not be disconnected.") from exc
    nonces.take(principal.user_id)
    return {"connected": False}


def _season_start(sessions: object) -> int | None:
    from datetime import date as date_cls

    days = []
    if not isinstance(sessions, list):
        return None
    for session in sessions:
        if not isinstance(session, dict):
            continue
        text = session.get("date")
        if not isinstance(text, str):
            continue
        try:
            days.append(date_cls.fromisoformat(text))
        except ValueError:
            continue
    if not days:
        return None
    start = min(days)
    return int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())


def _by_id(rows: object) -> tuple[list[str], dict[str, dict]]:
    order: list[str] = []
    found: dict[str, dict] = {}
    if not isinstance(rows, list):
        return order, found
    for row in rows:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        ident = str(row["id"])
        if ident not in found:
            order.append(ident)
        found[ident] = row
    return order, found


def merge_strava(existing: object, runs: list) -> list:
    """Imported runs replace the same id. Older runs stay."""
    order, found = _by_id(existing)
    for run in runs:
        if not isinstance(run, dict):
            continue
        activity = to_stored_activity(run)
        ident = str(activity.get("id") or "")
        if not ident:
            continue
        if ident not in found:
            order.append(ident)
        found[ident] = activity
    return [found[ident] for ident in order]


def drop_strava(existing: object) -> list:
    rows = existing if isinstance(existing, list) else []
    return [
        row
        for row in rows
        if not (isinstance(row, dict) and row.get("source") == "strava")
    ]


def _stored_runs(app, principal) -> list[dict]:
    store, key, _nonce = _backend(app, principal)
    try:
        rows = store.get_activities(principal.user_id, key)
    except Exception:
        return []
    found = []
    for row in rows or []:
        if isinstance(row, dict) and row.get("id"):
            found.append(to_stored_activity(row))
    return found


def attach_activities(app, principal, season) -> None:
    """The season list, with stored Strava runs winning on the same id."""
    order, found = _by_id(season.activities)
    for row in _stored_runs(app, principal):
        ident = str(row.get("id") or "")
        if not ident:
            continue
        if ident not in found:
            order.append(ident)
        found[ident] = row
    season.activities = [found[ident] for ident in order]


def _apply(season, activities: list):
    return apply_activity_marks(
        season.plan,
        activities,
        season.actuals,
        goal_seconds(season.inputs[2]),
        season.bases,
        season.marks,
    )


def _keep(season, outcome) -> bool:
    if outcome.notice or not outcome.applied or outcome.plan is None or outcome.marks is None:
        return False
    season.plan = outcome.plan
    season.marks = {int(week): mark for week, mark in outcome.marks.items()}
    if isinstance(outcome.actuals, dict):
        season.actuals = outcome.actuals
    return True


def _save_season(principal, directory, season) -> None:
    from api.season_service import _refresh_digest, _save

    previous = season.digest
    _refresh_digest(season)
    _save(principal, directory, season, previous)


def sync(app, principal, directory, today, season, scope: str) -> dict:
    """Recent is the last window. Full history ignores the previous sync time.

    A failed import does not write last_sync_at. Marks use the stored
    quality base, so a week already adapted is not adapted again.
    """
    if scope not in ("recent", "all"):
        raise ApiError(400, "Choose a recent sync or the full history.")
    store, key, _nonce = _backend(app, principal)
    token = _token(store, principal.user_id, key) if configured() else None
    notice = None
    count = 0
    imported = False
    if token is not None:
        post, get = _post_get(app)
        now = int(time.time())
        last = token.get("last_sync_at") if scope == "recent" else None
        sessions = season.plan.get("sessions") if isinstance(season.plan, dict) else []
        try:
            fresh, runs = import_runs(
                token,
                now=now,
                last_sync=last if isinstance(last, int) else None,
                get=get,
                post=post,
                gate=_gate(app),
                season_start=_season_start(sessions),
            )
        except StravaLimited as exc:
            raise ApiError(429, str(exc)) from exc
        except StravaError as exc:
            notice = str(exc)
            runs = []
        else:
            runs = match_runs(runs, sessions)
            fresh["last_sync_at"] = now
            fresh["athlete_name"] = fresh.get("athlete_name") or token.get("athlete_name") or ""
            try:
                store.put_activities(principal.user_id, runs)
                store.put_token(principal.user_id, fresh, key)
            except Exception:
                notice = "Strava could not be saved."
            else:
                season.activities = merge_strava(season.activities, runs)
                attach_activities(app, principal, season)
                count = len(runs)
                imported = True
    else:
        box = {"notice": None, "updated": False}

        def _notice(text: str) -> None:
            box["notice"] = text

        def _clear() -> None:
            box["notice"] = None

        def _set(updated) -> None:
            if isinstance(updated, list):
                season.activities = updated
                box["updated"] = True

        def _marks(_plan) -> None:
            return None

        recent = getattr(app.state, "intervals_sync_recent", None) or sync_recent
        every = getattr(app.state, "intervals_sync_all", None) or sync_all
        try:
            run_activity_pull(
                page_name="page_activity",
                test_preview=False,
                refresh=scope == "all",
                already_pulled=False,
                activities_loaded=False,
                activities_trigger=None,
                plan=season.plan,
                activities=lambda: season.activities,
                today=lambda: today,
                strava_connected=lambda: False,
                strava_gate_pending=lambda: False,
                sync_all=every,
                sync_recent=recent,
                restore_rows=lambda: None,
                on_notice=_notice,
                clear_notice=_clear,
                on_activities=_set,
                _apply_activity_marks=_marks,
                on_loaded=lambda _trigger: None,
            )
        except PullError as exc:
            box["notice"] = str(exc)
        notice = box["notice"]
        imported = box["updated"] and not notice
        if imported:
            count = len(season.activities)
    changed = False
    if imported:
        outcome = _apply(season, season.activities)
        if outcome.notice:
            notice = outcome.notice
        changed = _keep(season, outcome)
        _save_season(principal, directory, season)
    return {
        "synced": imported,
        "scope": scope,
        "count": count,
        "notice": notice,
        "committed": changed,
    }


def forget_season_runs(principal, directory, today) -> None:
    """Drop Strava rows from the open season. The table delete already ran."""
    from api.errors import ApiError as _ApiError
    from api.season_service import open_season

    try:
        season = open_season(principal, directory, today)
    except _ApiError:
        return
    season.activities = drop_strava(season.activities)
    _save_season(principal, directory, season)
