# screen_routes.py — Home, Plan, Activity, Library, Profile, Settings, Session.

"""Reads for the pages step 3 will draw, and the settings those pages save.

None of these call the model. Settings does not rebuild the season.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.errors import ApiError
from api.prefs import athlete_payload, prefs_payload
from api.routes import _resolved
from api.goals import read_override, write_override
from api.screens import (
    activity_view,
    apply_settings,
    home_view,
    intervals_pull,
    library_view,
    plan_view,
    profile_view,
    session_view,
)
from api.season_service import open_season
from api.strava_flow import attach_activities, status

router = APIRouter(tags=["screens"])


class GoalBody(BaseModel):
    goal_time: str


class SettingsBody(BaseModel):
    pace_units: str | None = None
    timezone: str | None = None
    no_watch: bool | None = None
    easy_pace: str | None = None
    easy_pace_unit: str | None = None
    display_name: str | None = None
    preferred: str | None = None
    intro_seen: bool | None = None
    strava_prompt_seen: bool | None = None
    date_format: str | None = None
    start_date: str | None = None
    confirm_adapt: bool | None = None
    show_ids: bool | None = None
    compact: bool | None = None


def _open(request: Request, who, today):
    try:
        season = open_season(who, request.app.state.directory, today)
    except ApiError as exc:
        if exc.status == 404:
            return None
        raise
    attach_activities(request.app, who, season)
    return season


@router.get("/home")
def home(request: Request, just_generated: bool = False) -> dict:
    who, resolved = _resolved(request)
    season = _open(request, who, resolved["today"])
    found = status(request.app, who)
    return home_view(
        who,
        request.app.state.directory,
        resolved["today"],
        season,
        connected=found["connected"] is True,
        strava=found,
        just_generated=just_generated is True,
    )


@router.get("/plan")
def plan(request: Request, month: str | None = None) -> dict:
    who, resolved = _resolved(request)
    season = open_season(who, request.app.state.directory, resolved["today"])
    attach_activities(request.app, who, season)
    return plan_view(season, resolved["today"], prefs_payload(resolved), month)


@router.get("/library")
def library(request: Request, q: str = "", family: str = "", phase: int | None = None) -> dict:
    _resolved(request)
    return library_view(q, family, phase)


@router.get("/activities")
def activities(request: Request) -> dict:
    who, resolved = _resolved(request)
    season = open_season(who, request.app.state.directory, resolved["today"])
    found = status(request.app, who)
    sessions = season.plan.get("sessions") if isinstance(season.plan, dict) else []
    if not isinstance(sessions, list):
        sessions = []
    # Strava connected: Intervals is not called. Otherwise the same pull Plan uses.
    season.activities, notice = intervals_pull(
        found["connected"] is True,
        sessions,
        season.activities,
        resolved["today"],
    )
    attach_activities(request.app, who, season)
    body = activity_view(
        season,
        resolved["today"],
        resolved["prefs"],
        resolved["easy_pace"],
        resolved["easy_pace_unit"],
    )
    body["strava"] = found
    body["notice"] = notice
    return body


def _profile(request: Request, who, resolved, season) -> dict:
    key = ""
    if season is not None:
        from ui.profile import profile_key

        key = profile_key(season.inputs)
    override = read_override(who, request.app.state.directory, key) if key else None
    return profile_view(season, resolved, override)


@router.get("/profile")
def profile(request: Request) -> dict:
    who, resolved = _resolved(request)
    season = _open(request, who, resolved["today"])
    return _profile(request, who, resolved, season)


@router.put("/profile/goal")
def put_goal(body: GoalBody, request: Request) -> dict:
    """Save the Profile goal. The season digest does not change."""
    who, resolved = _resolved(request)
    season = _open(request, who, resolved["today"])
    if season is None:
        raise ApiError(404, "No current season.")
    from ui.profile import profile_key

    before = season.digest
    write_override(who, request.app.state.directory, profile_key(season.inputs), body.goal_time)
    again = open_season(who, request.app.state.directory, resolved["today"])
    if again.digest != before:
        raise ApiError(400, "The season was changed.")
    return _profile(request, who, resolved, again)


@router.get("/sessions/{day}")
def one_session(day: str, request: Request) -> dict:
    who, resolved = _resolved(request)
    season = open_season(who, request.app.state.directory, resolved["today"])
    found = session_view(season, day)
    if found is None:
        raise ApiError(404, "That day is not in this season.")
    return found


@router.patch("/settings")
def patch_settings(body: SettingsBody, request: Request) -> dict:
    who, _resolved_view = _resolved(request)
    # Fields the client left out stay None and are not written.
    sent = body.model_dump(exclude_unset=True)
    apply_settings(who, request.app.state.directory, sent)
    resolved = _resolved(request)[1]
    return athlete_payload(who, resolved)
