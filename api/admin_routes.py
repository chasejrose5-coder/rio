# admin_routes.py — accounts, the test season, and the startup photos.

"""Admin is the RIO_ADMIN_EMAIL login. Everyone else is refused.

The test season is a separate athlete. Loading it does not write this login's
plan. The hero file is the same JSON the Streamlit editor writes.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.account_flow import service_key_for
from api.errors import ApiError
from api.routes import _principal
from ui.access import viewer_is_admin
from ui.accounts import account_rows
from ui.cloud_store import CloudAuthError, MemoryDirectory
from ui.hero_config import load_rotation, save_rotation
from ui.sample_season import TestSeasonError, delete_test_season, load_test_season, read_test_bundle

router = APIRouter(prefix="/admin", tags=["admin"])


class ConfirmBody(BaseModel):
    confirm: bool = False


class HeroBody(BaseModel):
    photos: list


def _admin(request: Request):
    who = _principal(request)
    if not viewer_is_admin(who.email):
        raise ApiError(403, "That page is for the admin account.")
    return who


def _tools(request: Request, who):
    directory = request.app.state.directory
    if isinstance(directory, MemoryDirectory):
        strava = request.app.state.memory_strava
    else:
        from ui.strava_store import current_strava_store

        strava = current_strava_store()
    return directory, strava, service_key_for(directory), who.user_id, who.email


def _hero_path(request: Request):
    return getattr(request.app.state, "hero_path", None)


@router.get("/accounts")
def accounts(request: Request) -> dict:
    who = _admin(request)
    directory = request.app.state.directory
    if directory is not None:
        try:
            rows = directory.list_users(service_key_for(directory))
        except CloudAuthError as exc:
            raise ApiError(400, str(exc)) from exc
        if rows is None:
            return {"available": False, "accounts": []}
        cleaned = [
            {
                "email": row.get("email") or "",
                "display_name": row.get("display_name") or "",
                "role": row.get("role") or "athlete",
            }
            for row in rows
            if isinstance(row, dict)
        ]
        return {"available": True, "accounts": cleaned}
    rows = account_rows(request.app.state.accounts_path)
    return {
        "available": True,
        "accounts": [
            {"email": row["email"], "display_name": row["name"], "role": "athlete"}
            for row in rows
        ],
    }


@router.post("/test-season")
def load_season(request: Request) -> dict:
    who = _admin(request)
    directory, strava, key, caller_id, caller_email = _tools(request, who)
    try:
        loaded = load_test_season(
            directory,
            strava,
            key,
            caller_id=caller_id,
            caller_email=caller_email,
        )
    except TestSeasonError as exc:
        raise ApiError(400, str(exc)) from exc
    return {
        "loaded": True,
        "created": loaded.get("created") is True,
        "runs": loaded.get("runs") or 0,
        "name": "TEST Athlete",
    }


@router.get("/test-season")
def read_season(request: Request) -> dict:
    who = _admin(request)
    directory, strava, key, _caller_id, _caller_email = _tools(request, who)
    bundle = read_test_bundle(directory, strava, key)
    if not isinstance(bundle, dict):
        return {"loaded": False}
    inputs = bundle.get("inputs")
    shown = list(inputs) if isinstance(inputs, (list, tuple)) else []
    runs = bundle.get("runs")
    return {
        "loaded": True,
        "name": bundle.get("name") or "TEST Athlete",
        "inputs": shown,
        "runs": len(runs) if isinstance(runs, list) else 0,
        "plan": bundle.get("plan") if isinstance(bundle.get("plan"), dict) else {},
    }


@router.delete("/test-season")
def remove_season(body: ConfirmBody, request: Request) -> dict:
    if body.confirm is not True:
        raise ApiError(400, "Confirm the delete first.")
    who = _admin(request)
    directory, strava, key, caller_id, caller_email = _tools(request, who)
    try:
        removed = delete_test_season(
            directory,
            strava,
            key,
            caller_id=caller_id,
            caller_email=caller_email,
        )
    except TestSeasonError as exc:
        raise ApiError(400, str(exc)) from exc
    if removed:
        return {"deleted": True, "message": "TEST Athlete was removed."}
    return {"deleted": False, "message": "TEST Athlete is already gone."}


@router.get("/hero")
def hero(request: Request) -> dict:
    _admin(request)
    photos = load_rotation(_hero_path(request))
    return {
        "photos": [
            {
                "id": row["id"],
                "file": row["file"],
                "credit": row["credit"],
                "source": row["source"],
                "enabled": row["enabled"] is True,
            }
            for row in photos
        ]
    }


def preview_season(request: Request):
    """The TEST athlete as a season the screens can draw.

    None when that athlete has no plan. A non-admin is 403. This does not
    read or write the caller's season.
    """
    who = _admin(request)
    directory, strava, key, _caller_id, _caller_email = _tools(request, who)
    bundle = read_test_bundle(directory, strava, key)
    if not isinstance(bundle, dict) or not isinstance(bundle.get("plan"), dict):
        return None
    raw = bundle.get("inputs")
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    inputs = tuple(str(item) for item in raw)
    activities = bundle.get("activities") if isinstance(bundle.get("activities"), list) else []
    runs = bundle.get("runs") if isinstance(bundle.get("runs"), list) else []
    from api.season_service import OpenSeason
    from ui.cloud_session import season_digest

    season = OpenSeason(
        inputs=inputs,
        plan=bundle["plan"],
        marks={},
        actuals={},
        activities=activities,
        bases={},
        notes={},
        base_source="preview",
        digest=season_digest(inputs, bundle["plan"], {}, {}),
        display_name="TEST Athlete",
    )
    return season, len(runs)


@router.put("/hero")
def save_hero(body: HeroBody, request: Request) -> dict:
    _admin(request)
    try:
        stored = save_rotation(body.photos, _hero_path(request))
    except (ValueError, OSError) as exc:
        raise ApiError(400, str(exc)) from exc
    return {
        "saved": True,
        "photos": [
            {
                "id": row["id"],
                "file": row["file"],
                "credit": row["credit"],
                "source": row["source"],
                "enabled": row["enabled"] is True,
            }
            for row in stored
        ],
    }
