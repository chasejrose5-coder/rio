# insight_routes.py — workout notes, the weekly digest, and explain.

"""A bad payload is refused before the model is scheduled.

The response is pending. GET reads the result after the task finishes.
Saving a plan does not wait on this router: the season routes save first.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel

from api.errors import ApiError
from api.insight_flow import (
    explain_error,
    fetch_day,
    fetch_job,
    queue_digest,
    queue_explain,
    queue_workout,
    reject_score,
)
from api.routes import _resolved
from api.season_service import open_season
from engines.explain import insight_inputs_ok, weekly_inputs_ok
from ui.insights import workout_inputs

router = APIRouter(prefix="/insights", tags=["insights"])


class WorkoutBody(BaseModel):
    date: str | None = None
    payload: dict | None = None
    plan: dict | None = None


class DigestBody(BaseModel):
    payload: dict
    plan: dict | None = None


class ExplainBody(BaseModel):
    kind: str
    classification: dict | None = None
    template_id: str | None = None
    reason_codes: list | None = None
    goal: dict | None = None
    plan: dict | None = None


def _built(who, directory, today, day: str) -> dict | None:
    season = open_season(who, directory, today)
    if any(key in season.plan for key in ("probability", "readiness_score")):
        raise ApiError(400, "A plan with a score is rejected.")
    sessions = season.plan.get("sessions") if isinstance(season.plan, dict) else []
    session = None
    if isinstance(sessions, list):
        for item in sessions:
            if isinstance(item, dict) and str(item.get("date") or "") == day:
                session = item
                break
    if session is None:
        raise ApiError(400, "That day is not in this season.")
    actual = season.actuals.get(day) if isinstance(season.actuals, dict) else None
    mark = str(actual.get("mark") or "") if isinstance(actual, dict) else ""
    detail = str(actual.get("text") or "") if isinstance(actual, dict) else ""
    try:
        from datetime import date as date_cls

        race = date_cls.fromisoformat(season.inputs[3])
    except ValueError:
        return None
    remaining = (race - today).days
    if remaining < 0:
        remaining = 0
    return workout_inputs(
        session=session,
        plan_sessions=sessions if isinstance(sessions, list) else [],
        goal=str(season.inputs[2]),
        race_date=str(season.inputs[3]),
        days_to_goal=remaining,
        mark=mark,
        result_detail=detail,
        first_name=str(who.display_name or ""),
    )


@router.post("/workout")
def post_workout(body: WorkoutBody, request: Request, background: BackgroundTasks) -> dict:
    who, resolved = _resolved(request)
    reject_score(body.model_dump())
    if body.payload is not None:
        if not insight_inputs_ok(body.payload):
            raise ApiError(400, "That insight could not be written.")
        return queue_workout(
            background,
            request.app,
            who,
            request.app.state.directory,
            resolved["today"],
            body.payload,
        )
    if not body.date:
        raise ApiError(400, "That insight could not be written.")
    payload = _built(who, request.app.state.directory, resolved["today"], body.date)
    if payload is None or not insight_inputs_ok(payload):
        return {"status": "skipped", "date": body.date, "id": "", "kind": "workout"}
    return queue_workout(
        background,
        request.app,
        who,
        request.app.state.directory,
        resolved["today"],
        payload,
    )


@router.get("/workout/{day}")
def get_workout(day: str, request: Request) -> dict:
    who, resolved = _resolved(request)
    return fetch_day(request.app, who, request.app.state.directory, resolved["today"], day)


@router.post("/digest")
def post_digest(body: DigestBody, request: Request, background: BackgroundTasks) -> dict:
    who, _resolved_view = _resolved(request)
    reject_score(body.model_dump())
    if not weekly_inputs_ok(body.payload):
        raise ApiError(400, "That week is not ready for a digest.")
    return queue_digest(background, request.app, who.user_id, body.payload)


@router.post("/explain")
def post_explain(body: ExplainBody, request: Request, background: BackgroundTasks) -> dict:
    who, _resolved_view = _resolved(request)
    reject_score(body.model_dump())
    raw = body.model_dump()
    error = explain_error(body.kind, raw)
    if error:
        raise ApiError(400, error)
    return queue_explain(background, request.app, who.user_id, body.kind, raw)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request) -> dict:
    who, _resolved_view = _resolved(request)
    return fetch_job(request.app, who.user_id, job_id)
