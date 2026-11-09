# insight_flow.py — the model runs after the save, never inside it.

"""A result is stored first. The response says the note is pending.

complete_insight, weekly_digest, and explain run in a background task.
A payload that fails the existing checks is refused before that task is
scheduled, so the model is not called. Keys stay in the environment.
The route does not accept a key.
"""

from __future__ import annotations

import secrets
from datetime import date

import engines.explain as explain
from api.errors import ApiError
from api.state import note_ok

_SCORE = ("probability", "readiness", "readiness_score")


def _jobs(app) -> dict:
    bag = getattr(app.state, "insight_jobs", None)
    if not isinstance(bag, dict):
        bag = {}
        app.state.insight_jobs = bag
    return bag


def _dates(app) -> dict:
    bag = getattr(app.state, "insight_dates", None)
    if not isinstance(bag, dict):
        bag = {}
        app.state.insight_dates = bag
    return bag


def _scored(value: object) -> bool:
    """True when a dict carries a score key. Strings are not scanned."""
    if isinstance(value, dict):
        if any(key in value for key in _SCORE):
            return True
        return any(_scored(item) for item in value.values())
    if isinstance(value, list):
        return any(_scored(item) for item in value)
    return False


def _public(job: dict) -> dict:
    return {
        "id": job["id"],
        "kind": job["kind"],
        "status": job["status"],
        "date": job.get("date") or "",
        "note": job.get("note"),
        "text": job.get("text"),
        "viewed": job.get("viewed"),
    }


def _open_job(app, user_id: str, kind: str, day: str) -> dict:
    job_id = secrets.token_urlsafe(9)
    job = {
        "id": job_id,
        "kind": kind,
        "status": "pending",
        "date": day,
        "note": None,
        "text": None,
        "viewed": None,
    }
    _jobs(app)[(user_id, job_id)] = job
    if kind == "workout" and day:
        _dates(app)[(user_id, day)] = job_id
    return job


def _finish(app, user_id: str, job_id: str, status: str, note: dict | None, text: str | None) -> None:
    job = _jobs(app).get((user_id, job_id))
    if not isinstance(job, dict):
        return
    job["status"] = status
    job["note"] = note
    job["text"] = text
    if isinstance(note, dict):
        job["viewed"] = False


def fetch_job(app, user_id: str, job_id: str) -> dict:
    job = _jobs(app).get((user_id, job_id))
    if not isinstance(job, dict):
        raise ApiError(404, "That note is not ready.")
    return _public(job)


def fetch_day(app, principal, directory, today: date, day: str) -> dict:
    """The pending job, or the note already stored for this date."""
    job_id = _dates(app).get((principal.user_id, day))
    if isinstance(job_id, str):
        job = _jobs(app).get((principal.user_id, job_id))
        if isinstance(job, dict) and job.get("status") == "pending":
            return _public(job)
        if isinstance(job, dict) and job.get("status") == "ready" and isinstance(job.get("note"), dict):
            return _public(job)
    from api.season_service import open_season

    season = open_season(principal, directory, today)
    item = season.notes.get(day)
    if isinstance(item, dict) and isinstance(item.get("note"), dict):
        return {
            "id": job_id if isinstance(job_id, str) else "",
            "kind": "workout",
            "status": "ready",
            "date": day,
            "note": item["note"],
            "text": None,
            "viewed": item.get("viewed") is True,
        }
    if isinstance(job_id, str):
        job = _jobs(app).get((principal.user_id, job_id))
        if isinstance(job, dict):
            return _public(job)
    return {
        "id": "",
        "kind": "workout",
        "status": "absent",
        "date": day,
        "note": None,
        "text": None,
        "viewed": None,
    }


def _run_workout(app, principal, directory, today: date, day: str, payload: dict, job_id: str) -> None:
    """The model. The plan write already finished before this was scheduled."""
    user_id = principal.user_id
    try:
        if not explain.insight_inputs_ok(payload) or _scored(payload):
            _finish(app, user_id, job_id, "absent", None, None)
            return
        note = explain.complete_insight(payload)
        if not note_ok(note):
            _finish(app, user_id, job_id, "absent", None, None)
            return
        from api.season_service import _store_note, open_season

        season = open_season(principal, directory, today)
        saved = _store_note(principal, directory, season, day, note, False)
        if saved:
            _finish(app, user_id, job_id, "ready", note, None)
        else:
            _finish(app, user_id, job_id, "absent", None, None)
    except Exception:
        _finish(app, user_id, job_id, "absent", None, None)


def _run_digest(app, user_id: str, payload: dict, job_id: str) -> None:
    try:
        if not explain.weekly_inputs_ok(payload) or _scored(payload):
            _finish(app, user_id, job_id, "absent", None, None)
            return
        note = explain.weekly_digest(payload)
        if not note_ok(note):
            _finish(app, user_id, job_id, "absent", None, None)
            return
        _finish(app, user_id, job_id, "ready", note, None)
    except Exception:
        _finish(app, user_id, job_id, "absent", None, None)


def _run_explain(app, user_id: str, kind: str, body: dict, job_id: str) -> None:
    try:
        if kind == "classification":
            text = explain.explain(body["classification"])
        elif kind == "prescription":
            text = explain.explain_prescription(body["template_id"], body["reason_codes"], body["goal"])
        elif kind == "decision":
            text = explain.explain_decision(body["template_id"], body["reason_codes"])
        else:
            text = None
        if not isinstance(text, str) or not text.strip():
            _finish(app, user_id, job_id, "absent", None, None)
            return
        _finish(app, user_id, job_id, "ready", None, text)
    except Exception:
        _finish(app, user_id, job_id, "absent", None, None)


def _queue(background, fn, *args) -> None:
    background.add_task(fn, *args)


def after_result(
    background,
    app,
    principal,
    directory,
    today: date,
    season,
    session: dict,
    mark: str,
    detail: str,
) -> dict:
    """Schedule a hard-day note. Skipped days do not call the model.

    The caller has already saved the plan. This does not save again.
    """
    from ui.insights import workout_inputs

    day = str(session.get("date") or "")
    if day and day in season.notes:
        return {"status": "ready", "date": day, "id": ""}
    goal = season.inputs[3]
    try:
        race = date.fromisoformat(str(goal))
    except ValueError:
        return {"status": "skipped", "date": day, "id": ""}
    remaining = (race - today).days
    if remaining < 0:
        remaining = 0
    if _scored(season.plan):
        return {"status": "skipped", "date": day, "id": ""}
    payload = workout_inputs(
        session=session,
        plan_sessions=season.plan.get("sessions") if isinstance(season.plan, dict) else [],
        goal=str(season.inputs[2]),
        race_date=str(goal),
        days_to_goal=remaining,
        mark=mark,
        result_detail=detail,
        first_name=str(principal.display_name or ""),
    )
    if payload is None or not explain.insight_inputs_ok(payload) or _scored(payload):
        return {"status": "skipped", "date": day, "id": ""}
    job = _open_job(app, principal.user_id, "workout", day)
    _queue(background, _run_workout, app, principal, directory, today, day, payload, job["id"])
    return {"status": "pending", "date": day, "id": job["id"]}


def queue_workout(background, app, principal, directory, today: date, payload: dict) -> dict:
    """A payload the caller already checked. The model starts after this returns."""
    day = str(payload.get("session_date") or "")
    job = _open_job(app, principal.user_id, "workout", day)
    _queue(background, _run_workout, app, principal, directory, today, day, payload, job["id"])
    return {"status": "pending", "date": day, "id": job["id"], "kind": "workout"}


def queue_digest(background, app, user_id: str, payload: dict) -> dict:
    job = _open_job(app, user_id, "digest", "")
    _queue(background, _run_digest, app, user_id, payload, job["id"])
    return {"status": "pending", "id": job["id"], "kind": "digest"}


def queue_explain(background, app, user_id: str, kind: str, body: dict) -> dict:
    job = _open_job(app, user_id, "explain", "")
    _queue(background, _run_explain, app, user_id, kind, body, job["id"])
    return {"status": "pending", "id": job["id"], "kind": "explain"}


def explain_error(kind: object, body: dict) -> str | None:
    """The checks explain() makes before it calls the model. None when it can run."""
    if kind == "classification":
        found = body.get("classification")
        if not isinstance(found, dict):
            return "That explanation could not be written."
        if "confidence" not in found:
            return "That explanation could not be written."
        if not str(found.get("family") or "").strip():
            return "That explanation could not be written."
        codes = found.get("reason_codes")
        if isinstance(codes, (str, bytes)) or not isinstance(codes, list):
            return "That explanation could not be written."
        return None
    if kind in ("prescription", "decision"):
        if not str(body.get("template_id") or "").strip():
            return "That explanation could not be written."
        codes = body.get("reason_codes")
        if isinstance(codes, (str, bytes)) or not isinstance(codes, list):
            return "That explanation could not be written."
        if kind == "prescription" and not isinstance(body.get("goal"), dict):
            return "That explanation could not be written."
        return None
    return "That explanation could not be written."


def reject_score(value: object) -> None:
    if _scored(value):
        raise ApiError(400, "A plan with a score is rejected.")
