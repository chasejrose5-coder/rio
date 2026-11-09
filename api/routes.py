# routes.py — thin HTTP handlers. The season work is in season_service.

"""Sign-in, the current athlete, and the season routes from step 2a.

Strava and the insight model are not on this app.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from api.errors import ApiError
from api.identity import (
    clear_session_cookie,
    principal_from_cookie,
    set_session_cookie,
    sign_in_hosted,
    sign_in_local,
    sign_out,
)
from api.prefs import prefs_payload
from api.season_service import (
    commit_done,
    commit_text,
    commit_week,
    delete_past,
    generate,
    list_past,
    open_season,
    remember_note,
    season_payload,
    viewer,
)
from ui.accounts import AccountError
from ui.cloud_store import CloudAuthError

auth_router = APIRouter(prefix="/auth", tags=["auth"])
season_router = APIRouter(prefix="/seasons", tags=["seasons"])
health_router = APIRouter(tags=["health"])


class SignInBody(BaseModel):
    email: str
    password: str


class GenerateBody(BaseModel):
    current_time: str
    start_date: str
    goal_time: str
    goal_date: str


class ResultBody(BaseModel):
    date: str
    text: str = ""
    slots: list | None = None
    intervals: str | None = None
    note: dict | None = None


class WatchlessBody(BaseModel):
    date: str
    outcome: str = ""
    time: str = ""
    note: dict | None = None


class MarkBody(BaseModel):
    week: int = Field(ge=1)
    choice: str


class NoteBody(BaseModel):
    date: str
    note: dict
    viewed: bool = False


class DeleteBody(BaseModel):
    current_time: str
    start_date: str
    goal_time: str
    goal_date: str
    confirm: bool = False


def _principal(request: Request):
    settings = request.app.state.settings
    raw = request.cookies.get(settings.cookie_name)
    who = principal_from_cookie(
        request.app,
        request.app.state.directory,
        request.app.state.accounts_path,
        raw,
    )
    if who is None:
        raise ApiError(401, "Sign in again.")
    return who


def _resolved(request: Request):
    who = _principal(request)
    try:
        resolved = viewer(who, request.app.state.directory)
    except CloudAuthError as exc:
        raise ApiError(401, str(exc)) from exc
    except AccountError as exc:
        raise ApiError(401, str(exc)) from exc
    return who, resolved


@health_router.get("/health")
def health() -> dict:
    return {"ok": True}


@auth_router.post("/sign-in")
def sign_in(body: SignInBody, request: Request, response: Response) -> dict:
    directory = request.app.state.directory
    try:
        if directory is not None:
            sid, issued, session = sign_in_hosted(directory, body.email, body.password)
            kind = "hosted"
        else:
            sid, issued, session = sign_in_local(
                request.app,
                request.app.state.accounts_path,
                body.email,
                body.password,
            )
            kind = "local"
    except CloudAuthError as exc:
        raise ApiError(401, str(exc)) from exc
    except AccountError as exc:
        raise ApiError(401, str(exc)) from exc
    set_session_cookie(response, request.app.state.settings, sid, issued)
    return {
        "email": session.get("email") or "",
        "display_name": session.get("display_name") or "",
        "kind": kind,
    }


@auth_router.post("/sign-out")
def log_out(request: Request, response: Response) -> dict:
    settings = request.app.state.settings
    sign_out(request.app, request.app.state.directory, request.cookies.get(settings.cookie_name))
    clear_session_cookie(response, settings)
    return {"ok": True}


@auth_router.get("/me")
def me(request: Request) -> dict:
    who, resolved = _resolved(request)
    prefs = prefs_payload(resolved)
    today = prefs.pop("today")
    return {
        "id": who.user_id,
        "email": who.email,
        "display_name": who.display_name,
        "role": who.role,
        "kind": who.kind,
        "today": today,
        "prefs": prefs,
    }


@season_router.get("/current")
def current_season(request: Request) -> dict:
    who, resolved = _resolved(request)
    season = open_season(who, request.app.state.directory, resolved["today"])
    return season_payload(season, resolved)


@season_router.post("")
def create_season(body: GenerateBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    season = generate(who, request.app.state.directory, resolved["today"], body.model_dump())
    return season_payload(season, resolved, committed=True)


@season_router.post("/current/results")
def post_result(body: ResultBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    season, changed, note_saved = commit_text(
        who,
        request.app.state.directory,
        resolved["today"],
        body.date,
        body.text,
        body.slots,
        body.intervals,
        body.note,
    )
    return season_payload(season, resolved, committed=changed, note_saved=note_saved)


@season_router.post("/current/watchless")
def post_watchless(body: WatchlessBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    season, changed, note_saved = commit_done(
        who,
        request.app.state.directory,
        resolved["today"],
        body.date,
        body.outcome,
        body.time,
        body.note,
    )
    return season_payload(season, resolved, committed=changed, note_saved=note_saved)


@season_router.post("/current/marks")
def post_mark(body: MarkBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    season, changed = commit_week(
        who,
        request.app.state.directory,
        resolved["today"],
        body.week,
        body.choice,
    )
    return season_payload(season, resolved, committed=changed)


@season_router.post("/current/notes")
def post_note(body: NoteBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    season = remember_note(
        who,
        request.app.state.directory,
        resolved["today"],
        body.date,
        body.note,
        body.viewed,
    )
    return season_payload(season, resolved, note_saved=True)


@season_router.get("/past")
def past_seasons(request: Request) -> dict:
    who, resolved = _resolved(request)
    date_format = resolved["prefs"]["date_format"]
    return {
        "today": resolved["today"].isoformat(),
        "seasons": list_past(who, request.app.state.directory, resolved["today"], date_format),
    }


@season_router.delete("/past")
def remove_season(body: DeleteBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    return delete_past(
        who,
        request.app.state.directory,
        resolved["today"],
        body.model_dump(),
        resolved["prefs"]["date_format"],
    )
