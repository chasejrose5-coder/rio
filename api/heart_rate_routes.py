# heart_rate_routes.py — resting heart rate, max heart rate, and Karvonen zones.

"""GET returns the saved zones. PUT saves resting, max, the monitor toggle,
or edited boundaries. Nothing here changes a workout.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from api.heart_rate_store import load_profile, save_profile
from api.routes import _resolved

router = APIRouter(prefix="/heart-rate", tags=["heart-rate"])


class ZoneBody(BaseModel):
    zone: int
    low_bpm: float
    high_bpm: float


class HeartRateBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    no_monitor: bool | None = None
    resting_hr: float | None = None
    max_hr: float | None = None
    zones: list[ZoneBody] | None = None
    reset: bool | None = None


@router.get("")
def read_heart_rate(request: Request) -> dict:
    who, _resolved_prefs = _resolved(request)
    return load_profile(who, request.app.state.directory)


@router.put("")
def write_heart_rate(body: HeartRateBody, request: Request) -> dict:
    who, _resolved_prefs = _resolved(request)
    patch = body.model_dump(exclude_unset=True)
    if "zones" in patch and patch["zones"] is not None:
        patch["zones"] = [dict(row) for row in patch["zones"]]
    return save_profile(who, request.app.state.directory, patch)
