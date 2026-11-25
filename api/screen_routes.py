# screen_routes.py — Home, Plan, Activity, Library, Profile, Settings, Session.

"""Reads for the pages step 3 will draw, and the settings those pages save.

None of these call the model. Settings does not rebuild the season.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from api.errors import ApiError
from api.prefs import athlete_payload, distance_units, prefs_payload
from api.identity import set_theme_cookie
from api.routes import _principal, _resolved
from api.goals import read_override, write_override
from api.screens import (
    activity_view,
    apply_settings,
    home_view,
    connection_notice,
    library_view,
    plan_view,
    profile_view,
    session_view,
)
from api.season_service import open_named, open_season, parse_inputs
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
    theme: str | None = None
    usual_long_m: int | None = None


def _preview(request: Request):
    """The TEST season when the page asked for it. None on a normal read."""
    if request.query_params.get("preview") != "test":
        return None
    from api.admin_routes import preview_season

    found = preview_season(request)
    if found is None:
        raise ApiError(404, "Load the test season first.")
    return found


def _stamp(body: dict, runs: int) -> dict:
    body["preview"] = {
        "active": True,
        "banner": "TEST Athlete · read only. This login is not changed.",
        "runs": runs,
        "status": f"TEST season · {runs} runs",
    }
    return body


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
    preview = _preview(request)
    if preview is not None:
        season, runs = preview
        body = home_view(
            replace(who, display_name="TEST Athlete"),
            request.app.state.directory,
            resolved["today"],
            season,
            connected=False,
            strava={"connected": False, "configured": False, "athlete_name": "", "last_sync_at": None},
            just_generated=False,
        )
        from ui.accounts import hey

        body["hello"] = hey("TEST Athlete")
        body["strava_offer"] = False
        athlete = body.get("athlete")
        if isinstance(athlete, dict):
            athlete["display_name"] = "TEST Athlete"
            prefs = athlete.get("prefs")
            if isinstance(prefs, dict):
                athlete["prefs"] = {**prefs, "preferred": ""}
        return _stamp(body, runs)
    season = _open(request, who, resolved["today"])
    found = status(request.app, who)
    from api.strava_flow import streams_for

    return home_view(
        who,
        request.app.state.directory,
        resolved["today"],
        season,
        connected=found["connected"] is True,
        strava=found,
        just_generated=just_generated is True,
        streams=streams_for(request.app, who),
    )


def _named_season(who, directory, today, current_time, start_date, goal_time, goal_date):
    """A stored season named by the four inputs. A partial link stays the current one."""
    if not all(isinstance(value, str) and value.strip() for value in (current_time, start_date, goal_time, goal_date)):
        return None
    try:
        inputs = parse_inputs(
            {
                "current_time": current_time,
                "start_date": start_date,
                "goal_time": goal_time,
                "goal_date": goal_date,
            }
        )
    except ApiError:
        return None
    return open_named(who, directory, today, inputs)


@router.get("/plan")
def plan(
    request: Request,
    month: str | None = None,
    current_time: str | None = None,
    start_date: str | None = None,
    goal_time: str | None = None,
    goal_date: str | None = None,
) -> dict:
    who, resolved = _resolved(request)
    preview = _preview(request)
    if preview is not None:
        season, runs = preview
        body = plan_view(season, resolved["today"], prefs_payload(resolved), month, heart=None)
        return _stamp(body, runs)
    named = _named_season(
        who,
        request.app.state.directory,
        resolved["today"],
        current_time,
        start_date,
        goal_time,
        goal_date,
    )
    season = named if named is not None else open_season(who, request.app.state.directory, resolved["today"])
    attach_activities(request.app, who, season)
    from api.heart_rate_store import training_profile
    from api.strava_flow import streams_for
    from engines.pace_learn import ranges_for_activities

    heart = training_profile(who, request.app.state.directory)
    learned = None
    streams: dict = {}
    if heart is not None:
        streams = streams_for(request.app, who)
        learned = ranges_for_activities(
            season.activities,
            streams,
            heart.get("zones"),
            resolved.get("easy_pace_unit") or "mi",
        )
    body = plan_view(
        season,
        resolved["today"],
        prefs_payload(resolved),
        month,
        heart=heart,
        learned=learned,
    )
    zones = _zone_weeks(season, streams, heart)
    zones = _add_bike_zones(zones, who, request.app.state.directory, season)
    if zones:
        body["zone_weeks"] = zones
    return body


def _zone_weeks(season, streams: dict, heart: dict | None) -> dict:
    """Seconds in each zone for a plan week, from run_hr_streams. Empty when none exist."""
    if not isinstance(heart, dict) or not heart.get("zones") or not streams:
        return {}
    plan = season.plan if isinstance(getattr(season, "plan", None), dict) else {}
    try:
        start = date.fromisoformat(str(plan.get("start_date")))
    except ValueError:
        return {}
    length = plan.get("season_length_weeks")
    from ui.activities import activity_day
    from engines.zone_time import season_week, sum_zone_reports, zone_report

    grouped: dict[int, list] = {}
    activities = season.activities if isinstance(getattr(season, "activities", None), list) else []
    for activity in activities:
        if not isinstance(activity, dict):
            continue
        day_text = activity_day(activity)
        ident = activity.get("id")
        if not day_text or ident is None:
            continue
        stream = streams.get(str(ident))
        if not isinstance(stream, dict):
            continue
        try:
            day = date.fromisoformat(day_text)
        except ValueError:
            continue
        week = season_week(start, day, length)
        if week is None:
            continue
        report = zone_report(stream, heart.get("zones"), None)
        if report:
            grouped.setdefault(week, []).append(report)
    found = {}
    for week, reports in grouped.items():
        combined = sum_zone_reports(reports)
        if combined:
            found[str(week)] = combined["zones"]
    return found


def _add_bike_zones(found: dict, who, directory, season) -> dict:
    """Bike time in each zone joins the week's run zones. Run distance is unchanged."""
    try:
        from api.bike_store import load_rows

        rows = load_rows(who, directory)
    except Exception:
        return found
    plan = season.plan if isinstance(getattr(season, "plan", None), dict) else {}
    try:
        start = date.fromisoformat(str(plan.get("start_date")))
    except ValueError:
        return found
    length = plan.get("season_length_weeks")
    from engines.zone_time import season_week, sum_zone_reports

    grouped: dict[int, list] = {}
    for row in rows:
        zones = row.get("zones")
        if not isinstance(zones, list) or len(zones) != 5:
            continue
        try:
            day = date.fromisoformat(row["date"])
        except (TypeError, ValueError):
            continue
        week = season_week(start, day, length)
        if week is None:
            continue
        grouped.setdefault(week, []).append(
            {"zones": [{"zone": index + 1, "name": "", "seconds": zones[index]} for index in range(5)]}
        )
    for week, reports in grouped.items():
        key = str(week)
        existing = found.get(key)
        pile = list(reports)
        if isinstance(existing, list):
            pile.insert(0, {"zones": existing})
        combined = sum_zone_reports(pile)
        if combined:
            found[key] = combined["zones"]
    return found


@router.get("/library")
def library(request: Request, q: str = "", family: str = "", phase: int | None = None) -> dict:
    who = _principal(request)
    return library_view(q, family, phase, distance_units(who, request.app.state.directory))


@router.get("/activities")
def activities(request: Request) -> dict:
    who, resolved = _resolved(request)
    preview = _preview(request)
    if preview is not None:
        season, runs = preview
        body = activity_view(
            season,
            resolved["today"],
            resolved["prefs"],
            resolved["easy_pace"],
            resolved["easy_pace_unit"],
        )
        body["strava"] = {
            "configured": False,
            "connected": False,
            "athlete_name": "",
            "last_sync_at": None,
            "count": runs,
        }
        body["notice"] = None
        return _stamp(body, runs)
    season = open_season(who, request.app.state.directory, resolved["today"])
    found = status(request.app, who)
    season.activities, notice = connection_notice(
        found["connected"] is True,
        season.activities,
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


def _zone_breakdown(request: Request, who, found: dict, heart: dict | None) -> dict | None:
    """Time in zone for the run matched to this day. No stream means no breakdown."""
    if not heart:
        return None
    activity_id = found.get("activity_id")
    if not isinstance(activity_id, str) or not activity_id:
        return None
    session = found.get("session") if isinstance(found.get("session"), dict) else {}
    from api.strava_flow import _backend
    from engines.heart_targets import zone_for_template
    from engines.zone_time import zone_report

    try:
        store, _key, _nonce = _backend(request.app, who)
        streams = store.get_streams(who.user_id) if hasattr(store, "get_streams") else {}
    except Exception:
        return None
    sample = streams.get(activity_id) if isinstance(streams, dict) else None
    return zone_report(sample, heart.get("zones"), zone_for_template(str(session.get("template_id") or "")))


@router.get("/sessions/{day}")
def one_session(day: str, request: Request) -> dict:
    who, resolved = _resolved(request)
    preview = _preview(request)
    if preview is not None:
        season, _runs = preview
    else:
        season = open_season(who, request.app.state.directory, resolved["today"])
    from api.heart_rate_store import training_profile

    heart = None if preview is not None else training_profile(who, request.app.state.directory)
    learned = None
    if heart is not None:
        from api.strava_flow import streams_for
        from engines.pace_learn import ranges_for_activities

        learned = ranges_for_activities(
            season.activities,
            streams_for(request.app, who),
            heart.get("zones"),
            resolved.get("easy_pace_unit") or "mi",
        )
    found = session_view(season, day, resolved, heart, learned)
    if found is not None and preview is None:
        found["zones"] = _zone_breakdown(request, who, found, heart)
    if found is None:
        raise ApiError(404, "That day is not in this season.")
    return found


@router.patch("/settings")
def patch_settings(body: SettingsBody, request: Request, response: Response) -> dict:
    who, _resolved_view = _resolved(request)
    # Fields the client left out stay None and are not written.
    sent = body.model_dump(exclude_unset=True)
    apply_settings(who, request.app.state.directory, sent)
    resolved = _resolved(request)[1]
    payload = athlete_payload(who, resolved)
    set_theme_cookie(response, payload)
    return payload
