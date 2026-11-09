# strava_routes.py — connect, callback, status, disconnect, and sync.

"""The callback checks the nonce stored by connect. Tokens are not in the JSON.

A browser navigation is redirected to the frontend. A client that sends
X-RIO-Response: json gets the body instead, which is what the tests use.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from api.errors import ApiError
from api.routes import _body, _resolved
from api.season_service import open_season
from api.strava_flow import (
    connect,
    disconnect,
    finish_callback,
    forget_season_runs,
    redirect_for_api,
    status,
    sync,
)

router = APIRouter(prefix="/strava", tags=["strava"])


class SyncBody(BaseModel):
    scope: str = "recent"


def _wants_json(request: Request) -> bool:
    return request.headers.get("x-rio-response", "").strip().lower() == "json"


def _front(request: Request, flag: str) -> str:
    origin = request.app.state.settings.frontend_origin
    return f"{origin}/settings?strava={flag}"


@router.get("/status")
def strava_status(request: Request) -> dict:
    who, _resolved_view = _resolved(request)
    return status(request.app, who)


@router.get("/connect")
def strava_connect(request: Request) -> dict:
    who, _resolved_view = _resolved(request)
    return connect(request.app, who)


@router.get("/callback")
def strava_callback(request: Request, code: str = "", state: str = ""):
    try:
        who, _resolved_view = _resolved(request)
    except ApiError:
        if _wants_json(request):
            raise
        return RedirectResponse(_front(request, "error"), status_code=302)
    try:
        body = finish_callback(request.app, who, code, state)
    except ApiError:
        if _wants_json(request):
            raise
        return RedirectResponse(_front(request, "error"), status_code=302)
    if _wants_json(request):
        body["redirect_uri"] = redirect_for_api()
        return body
    return RedirectResponse(_front(request, "connected"), status_code=302)


@router.post("/disconnect")
def strava_disconnect(request: Request) -> dict:
    who, resolved = _resolved(request)
    body = disconnect(request.app, who)
    forget_season_runs(who, request.app.state.directory, resolved["today"])
    return body


@router.post("/sync")
def strava_sync(body: SyncBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    season = open_season(who, request.app.state.directory, resolved["today"])
    outcome = sync(
        request.app,
        who,
        request.app.state.directory,
        resolved["today"],
        season,
        body.scope,
    )
    payload = _body(request, who, resolved, season, committed=outcome["committed"])
    payload.update(outcome)
    return payload
