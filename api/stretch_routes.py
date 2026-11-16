# stretch_routes.py — Done marks and sore spots for the Stretching tab.

"""The plan decides the routine. These routes only store what the runner marked.

Today comes from the Settings time zone on the signed-in account.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.routes import _resolved
from api.stretch_store import check_in_spot, clear_spot, load_state, save_spot, toggle_completion

router = APIRouter(prefix="/stretch", tags=["stretch"])


class CompleteBody(BaseModel):
    routine_id: str
    done: bool | None = None


class SpotBody(BaseModel):
    region: str
    severity: str


class CheckBody(BaseModel):
    still: bool


def _today(resolved: dict):
    return resolved["today"]


@router.get("")
def read_stretch(request: Request) -> dict:
    who, resolved = _resolved(request)
    return load_state(who, request.app.state.directory, _today(resolved))


@router.post("/completions")
def complete(body: CompleteBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    return toggle_completion(who, request.app.state.directory, _today(resolved), body.routine_id, body.done)


@router.post("/spots")
def spot(body: SpotBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    return save_spot(who, request.app.state.directory, _today(resolved), body.region, body.severity)


@router.post("/spots/{region}/check-in")
def check_in(region: str, body: CheckBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    return check_in_spot(who, request.app.state.directory, _today(resolved), region, body.still)


@router.delete("/spots/{region}")
def clear(region: str, request: Request) -> dict:
    who, resolved = _resolved(request)
    return clear_spot(who, request.app.state.directory, _today(resolved), region)
