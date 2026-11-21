# bike_routes.py — swap an easy run for a bike, and read the week.

"""The offer is a rule. These routes store the swap and the logged ride.

Today comes from the Settings time zone. The plan day may be another date.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.bike_store import _find, clear_swap, ensure_swap, load_rows, save_log, swaps_in_week, week_summary
from api.errors import ApiError
from api.injury_store import load_state as load_injury
from api.routes import _resolved
from api.season_service import open_season
from engines.bike import bike_minutes, bike_zones, can_swap, day_before_race, day_kind, suggest_bike

router = APIRouter(prefix="/bike", tags=["bike"])


class SwapBody(BaseModel):
    date: str
    swap: bool | None = None
    minutes: int | None = None
    distance_m: int | None = None
    avg_hr: int | None = None


def _day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ApiError(400, "The date is not YYYY-MM-DD.") from None


def _sessions(season) -> list[dict]:
    plan = season.plan if isinstance(getattr(season, "plan", None), dict) else {}
    rows = plan.get("sessions")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _session_on(sessions: list[dict], day: str) -> dict | None:
    for session in sessions:
        if str(session.get("date") or "")[:10] == day:
            return session
    return None


def _run_seconds(season, day: date, template: str, easy_pace: str, easy_unit: str) -> int | None:
    from decimal import Decimal

    from engines.pace import workout_times

    try:
        found = workout_times(
            template,
            current_mark=season.inputs[0],
            goal_mark=season.inputs[2],
            start=date.fromisoformat(season.inputs[1]),
            goal_date=date.fromisoformat(season.inputs[3]),
            on=day,
            easy_pace=easy_pace or None,
            easy_unit=easy_unit or "mi",
        )
    except (ValueError, TypeError):
        return None
    if not isinstance(found, dict) or found.get("easy_unset") is True:
        return None
    block = found.get("block_seconds")
    if isinstance(block, Decimal) and block > 0:
        return int(block)
    if isinstance(block, (int, float)) and not isinstance(block, bool) and block > 0:
        return int(block)
    return None


def _zone2(heart: dict | None) -> dict | None:
    if not isinstance(heart, dict):
        return None
    shifted = bike_zones(heart.get("zones"))
    if not shifted:
        return None
    zone = next((row for row in shifted if row.get("zone") == 2), None)
    if not isinstance(zone, dict):
        return None
    return {
        "low_bpm": zone.get("low_bpm"),
        "high_bpm": zone.get("high_bpm"),
        "sentence": "Easy bike is zone 2, conversational.",
    }


def _offer(request: Request, who, day: date) -> dict:
    resolved = _resolved(request)[1]
    try:
        season = open_season(who, request.app.state.directory, resolved["today"])
    except ApiError:
        season = None
    sessions = _sessions(season) if season is not None else []
    session = _session_on(sessions, day.isoformat())
    easy = day_kind(session) == "easy" if session else False
    before = day_before_race(day.isoformat(), sessions)
    rows = []
    try:
        rows = load_rows(who, request.app.state.directory)
    except ApiError as exc:
        if exc.status != 503:
            raise
    current = _find(rows, day.isoformat())
    used = swaps_in_week(rows, day, skip=day.isoformat())
    areas = []
    try:
        injury = load_injury(who, request.app.state.directory, resolved["today"])
        areas = [row.get("area_id") for row in injury.get("areas") or []]
    except ApiError:
        areas = []
    minutes = None
    if easy and session is not None and season is not None:
        seconds = _run_seconds(
            season,
            day,
            str(session.get("template_id") or ""),
            str(resolved.get("easy_pace") or ""),
            str(resolved.get("easy_pace_unit") or "mi"),
        )
        if seconds:
            minutes = bike_minutes(seconds)
    from api.heart_rate_store import training_profile

    heart = None
    try:
        heart = training_profile(who, request.app.state.directory)
    except Exception:
        heart = None
    return {
        "date": day.isoformat(),
        "offer": can_swap(easy=easy, before_race=before, swaps_already=used, already=current is not None),
        "suggest_first": suggest_bike(areas),
        "minutes": minutes,
        "swaps_used": used + (1 if current is not None else 0),
        "swapped": current is not None,
        "zone2": _zone2(heart),
        "log": current,
    }


@router.get("")
def read_bike(day: str, request: Request) -> dict:
    who, _resolved_view = _resolved(request)
    return _offer(request, who, _day(day))


@router.get("/week")
def read_week(start: str, end: str, request: Request) -> dict:
    who, _resolved_view = _resolved(request)
    opened, closed = _day(start), _day(end)
    if opened > closed:
        raise ApiError(400, "The week starts after it ends.")
    try:
        rows = load_rows(who, request.app.state.directory)
    except ApiError as exc:
        if exc.status == 503:
            return {"tracked": False, "dates": [], "minutes": 0, "distance_m": 0, "zone2_seconds": 0, "zone_seconds": 0}
        raise
    return week_summary(rows, opened, closed)


@router.post("")
def write_bike(body: SwapBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    day = _day(body.date)
    offer = _offer(request, who, day)
    if body.minutes is not None:
        save_log(
            who,
            request.app.state.directory,
            day,
            easy=offer["offer"] or offer["swapped"],
            before_race=False if offer["offer"] or offer["swapped"] else True,
            minutes=body.minutes,
            distance_m=body.distance_m,
            avg_hr=body.avg_hr,
        )
    elif body.swap is False:
        clear_swap(who, request.app.state.directory, day)
    else:
        season = open_season(who, request.app.state.directory, resolved["today"])
        sessions = _sessions(season)
        session = _session_on(sessions, day.isoformat())
        ensure_swap(
            who,
            request.app.state.directory,
            day,
            easy=day_kind(session) == "easy",
            before_race=day_before_race(day.isoformat(), sessions),
        )
    return _offer(request, who, day)
