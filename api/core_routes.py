# core_routes.py — done marks for the daily core circuit.

"""The date decides the circuit. These routes only store what the runner marked.

Today comes from the Settings time zone on the signed-in account.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.core_store import load_state, summary, toggle_completion
from api.errors import ApiError
from api.routes import _resolved

router = APIRouter(prefix="/core", tags=["core"])


class CompleteBody(BaseModel):
    done: bool | None = None


def _span(start: str, end: str) -> tuple[date, date]:
    try:
        return date.fromisoformat(start), date.fromisoformat(end)
    except ValueError:
        raise ApiError(400, "The date is not YYYY-MM-DD.") from None


@router.get("")
def read_core(request: Request) -> dict:
    who, resolved = _resolved(request)
    return load_state(who, request.app.state.directory, resolved["today"])


@router.get("/summary")
def read_summary(start: str, end: str, request: Request) -> dict:
    who, resolved = _resolved(request)
    opened, closed = _span(start, end)
    return summary(who, request.app.state.directory, resolved["today"], opened, closed)


@router.post("/completions")
def complete(body: CompleteBody, request: Request) -> dict:
    who, resolved = _resolved(request)
    return toggle_completion(who, request.app.state.directory, resolved["today"], body.done)
