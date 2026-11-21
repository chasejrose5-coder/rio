# injury_routes.py — rebuilding areas and done marks.

"""The library decides the exercises. These routes only store what the runner marked.

Today comes from the Settings time zone on the signed-in account.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.errors import ApiError
from api.injury_store import clear_area, load_state, select_area, step_back, summary, toggle_completion
from api.routes import _resolved

router = APIRouter(prefix="/injury", tags=["injury"])


class AreaBody(BaseModel):
    area_id: str


class CompleteBody(BaseModel):
    block_id: str
    done: bool | None = None


def _today(resolved: dict) -> date:
    return resolved["today"]


def _span(start: str, end: str) -> tuple[date, date]:
    try:
        opened = date.fromisoformat(start)
        closed = date.fromisoformat(end)
    except ValueError:
        raise ApiError(400, "The date is not YYYY-MM-DD.") from None
    return opened, closed


@router.get("")
def read_injury(request: Request) -> dict:
    who, resolved = _resolved(request)
    return load_state(who, request.app.state.directory, _today(resolved))


@router.get("/summary")
def read_summary(start: str, end: str, request: Request) -> dict:
    who, resolved = _resolved(request)
    opened, closed = _span(start, end)
    return summary(who, request.app.state.directory, _today(resolved), opened, closed)


@router.post("/areas")
def add_area(body: AreaBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    return select_area(who, request.app.state.directory, _today(resolved), body.area_id)


@router.delete("/areas/{area_id}")
def remove_area(area_id: str, request: Request) -> dict:
    who, resolved = _resolved(request)
    return clear_area(who, request.app.state.directory, _today(resolved), area_id)


@router.post("/areas/{area_id}/step-back")
def lower_area(area_id: str, request: Request) -> dict:
    who, resolved = _resolved(request)
    return step_back(who, request.app.state.directory, _today(resolved), area_id)


@router.post("/completions")
def complete(body: CompleteBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    return toggle_completion(who, request.app.state.directory, _today(resolved), body.block_id, body.done)
