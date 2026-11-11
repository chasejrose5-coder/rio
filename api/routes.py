# routes.py — thin HTTP handlers. The season work is in season_service.

"""Sign-in, the current athlete, and the season routes.

Strava, insights, and the screen reads live in their own routers.
A result is saved before any insight task is scheduled.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Request, Response
from pydantic import BaseModel, Field

from api.concurrency import require_digest
from api.errors import ApiError
from api.identity import (
    clear_session_cookie,
    principal_from_cookie,
    set_session_cookie,
    sign_in_hosted,
    sign_in_local,
    sign_out,
)
from api.prefs import athlete_payload
from api.season_service import (
    clear_current,
    commit_done,
    commit_text,
    commit_week,
    delete_past,
    generate,
    list_seasons,
    open_season,
    remember_note,
    season_payload,
    viewer,
)
from ui.accounts import AccountError
from ui.cloud_store import SIGNIN_UNAVAILABLE, CloudAuthError, auth_health

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
    missed: bool = False


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


class ConfirmBody(BaseModel):
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


def _queue_insight(background: BackgroundTasks, request: Request, who, resolved, season, day: str, detail: str) -> dict:
    """Pending when a hard day can take a note. The plan is already saved."""
    from api.insight_flow import after_result

    skipped = {"status": "skipped", "date": day, "id": ""}
    session = next(
        (
            item
            for item in season.plan.get("sessions") or []
            if isinstance(item, dict) and str(item.get("date") or "") == day
        ),
        None,
    )
    actual = season.actuals.get(day) if isinstance(season.actuals, dict) else None
    mark = str(actual.get("mark") or "") if isinstance(actual, dict) else ""
    if not isinstance(session, dict) or not mark:
        return skipped
    return after_result(
        background,
        request.app,
        who,
        request.app.state.directory,
        resolved["today"],
        season,
        session,
        mark,
        detail,
    )


def _body(request: Request, who, resolved: dict, season, **kwargs) -> dict:
    from api.strava_flow import attach_activities

    attach_activities(request.app, who, season)
    return season_payload(season, resolved, **kwargs)


def _resolved(request: Request):
    who = _principal(request)
    try:
        resolved = viewer(who, request.app.state.directory)
    except CloudAuthError as exc:
        raise ApiError(401, str(exc)) from exc
    except AccountError as exc:
        raise ApiError(401, str(exc)) from exc
    return who, resolved


def _current(request: Request, who, today):
    """The open season, or None. A stale If-Match is refused before a write."""
    try:
        season = open_season(who, request.app.state.directory, today)
    except ApiError as exc:
        if exc.status != 404:
            raise
        season = None
    require_digest(request, None if season is None else season.digest)
    return season


@health_router.get("/health")
def health() -> dict:
    return {"ok": True}


@health_router.get("/health/auth")
def health_auth(request: Request) -> dict:
    """Whether this process's anon key is accepted. The key is not returned."""
    return auth_health(request.app.state.directory)


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
        status = 503 if str(exc) == SIGNIN_UNAVAILABLE else 401
        raise ApiError(status, str(exc)) from exc
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
    payload = athlete_payload(who, resolved)
    payload["next_session"] = _next_session(request, who, resolved)
    return payload


def _next_session(request: Request, who, resolved: dict) -> str | None:
    """The next planned day, or the last day when the season is over.

    Today is the Settings time zone already on this viewer. A missing season
    leaves the link without a date.
    """
    from api.screens import next_session_day

    try:
        season = open_season(who, request.app.state.directory, resolved["today"])
    except ApiError:
        return None
    return next_session_day(season.plan, resolved["today"])


@season_router.get("/current")
def current_season(request: Request) -> dict:
    who, resolved = _resolved(request)
    season = open_season(who, request.app.state.directory, resolved["today"])
    return _body(request, who, resolved, season)


@season_router.post("")
def create_season(body: GenerateBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    _current(request, who, resolved["today"])
    season = generate(who, request.app.state.directory, resolved["today"], body.model_dump())
    payload = _body(request, who, resolved, season, committed=True)
    from api.strava_flow import status as strava_status
    from ui.plan_strava import should_offer_strava

    connected = strava_status(request.app, who)["connected"]
    payload["strava_offer"] = should_offer_strava(
        just_generated=True,
        connected=connected,
        dismissed=resolved.get("strava_prompt_seen") is True,
    )
    return payload


@season_router.post("/current/results")
def post_result(body: ResultBody, request: Request, background: BackgroundTasks) -> dict:
    who, resolved = _resolved(request)
    _current(request, who, resolved["today"])
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
    payload = _body(request, who, resolved, season, committed=changed, note_saved=note_saved)
    if changed:
        payload["insight"] = _queue_insight(background, request, who, resolved, season, body.date, body.text)
    else:
        payload["insight"] = {"status": "skipped", "date": body.date, "id": ""}
    return payload


@season_router.post("/current/watchless")
def post_watchless(body: WatchlessBody, request: Request, background: BackgroundTasks) -> dict:
    who, resolved = _resolved(request)
    _current(request, who, resolved["today"])
    if body.missed:
        from api.season_service import commit_missed

        season, changed, note_saved = commit_missed(
            who,
            request.app.state.directory,
            resolved["today"],
            body.date,
        )
    else:
        season, changed, note_saved = commit_done(
            who,
            request.app.state.directory,
            resolved["today"],
            body.date,
            body.outcome,
            body.time,
            body.note,
        )
    payload = _body(request, who, resolved, season, committed=changed, note_saved=note_saved)
    if changed:
        payload["insight"] = _queue_insight(background, request, who, resolved, season, body.date, body.time)
    else:
        payload["insight"] = {"status": "skipped", "date": body.date, "id": ""}
    return payload


@season_router.post("/current/marks")
def post_mark(body: MarkBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    _current(request, who, resolved["today"])
    season, changed = commit_week(
        who,
        request.app.state.directory,
        resolved["today"],
        body.week,
        body.choice,
    )
    return _body(request, who, resolved, season, committed=changed)


@season_router.post("/current/notes")
def post_note(body: NoteBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    _current(request, who, resolved["today"])
    season = remember_note(
        who,
        request.app.state.directory,
        resolved["today"],
        body.date,
        body.note,
        body.viewed,
    )
    return _body(request, who, resolved, season, note_saved=True)


@season_router.post("/current/clear")
def clear_marks(body: ConfirmBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    _current(request, who, resolved["today"])
    season = clear_current(who, request.app.state.directory, resolved["today"], body.confirm)
    return _body(request, who, resolved, season, committed=True)


@season_router.post("/reset")
def reset_plan(body: ConfirmBody, request: Request) -> dict:
    """Delete every stored season. The account stays. confirm must be true."""
    if body.confirm is not True:
        raise ApiError(400, "Confirm to reset the plan.")
    who, resolved = _resolved(request)
    _current(request, who, resolved["today"])
    from api.account_flow import reset_seasons_for

    reset_seasons_for(who, request.app.state.directory)
    return {"reset": True}


@season_router.get("/past")
def past_seasons(request: Request) -> dict:
    who, resolved = _resolved(request)
    date_format = resolved["prefs"]["date_format"]
    past, opened = list_seasons(who, request.app.state.directory, resolved["today"], date_format)
    return {
        "today": resolved["today"].isoformat(),
        "seasons": past,
        "open": opened,
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
