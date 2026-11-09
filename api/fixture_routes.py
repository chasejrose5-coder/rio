# fixture_routes.py — classify, prescribe, accept, the ledger, and the goal.

"""The same engines the fixture pages call. The model is not called.

These pages are admin-only in Streamlit. A planned row from accept is written
to a temporary directory and returned. The checked-in planned fixtures stay.
"""

from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

from api.admin_routes import _admin
from api.errors import ApiError
from db.load import fixture_paths, parse_fixture
from engines.accept import FIXTURE_NAME, FIXTURE_ON, accept
from engines.classify import classify
from engines.ledger import Ledger
from engines.prescribe import FIXTURES_DIR, prescribe

router = APIRouter(prefix="/fixtures", tags=["fixtures"])

GOAL_FIELDS = (
    "current_mark",
    "target_time",
    "target_date",
    "limiting_capacities",
)


class ClassifyBody(BaseModel):
    name: str | None = None
    payload: dict | None = None


class NameBody(BaseModel):
    name: str = ""


def _paths() -> list[Path]:
    return fixture_paths(FIXTURES_DIR)


def _by_name(name: str) -> Path:
    text = name.strip()
    if text.endswith(".yml"):
        text = text[: -len(".yml")]
    for path in _paths():
        if path.stem == text:
            return path
    raise ApiError(404, "That fixture is not on this server.")


def _public_classification(result: dict) -> dict:
    return {
        "family": result.get("family"),
        "reason_codes": list(result.get("reason_codes") or []),
        "confidence": result.get("confidence"),
        "ontology_version": result.get("ontology_version"),
    }


@router.get("")
def names(request: Request) -> dict:
    _admin(request)
    return {"fixtures": [path.stem for path in _paths()]}


@router.post("/classify")
def post_classify(body: ClassifyBody, request: Request) -> dict:
    _admin(request)
    if body.payload is not None:
        payload = body.payload
    elif body.name:
        try:
            payload = parse_fixture(_by_name(body.name).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ApiError(400, str(exc)) from exc
    else:
        raise ApiError(400, "Name a fixture or send a session.")
    try:
        result = classify(payload)
    except (ValueError, KeyError, TypeError) as exc:
        raise ApiError(400, str(exc)) from exc
    body_out = _public_classification(result)
    if isinstance(payload, dict) and payload.get("source"):
        body_out["source"] = payload.get("source")
    return body_out


@router.post("/prescribe")
def post_prescribe(body: NameBody, request: Request) -> dict:
    _admin(request)
    path = _by_name(body.name) if body.name else None
    if path is None:
        raise ApiError(400, "Name a fixture.")
    today = date.today()
    ledger = Ledger()
    try:
        ledger.record_fixture(path, today - timedelta(days=1))
        result = prescribe(ledger, today)
    except (ValueError, OSError) as exc:
        raise ApiError(400, str(exc)) from exc
    goal = ledger.goal if isinstance(ledger.goal, dict) else {}
    return {
        "name": path.stem,
        "on": today.isoformat(),
        "limiting_capacities": goal.get("limiting_capacities"),
        "rows": result.get("rows") or [],
        "ontology_version": result.get("ontology_version"),
    }


@router.post("/accept")
def post_accept(body: NameBody, request: Request) -> dict:
    """Accept the first prescription row. The file is not the checked-in one."""
    _admin(request)
    name = body.name.strip() or FIXTURE_NAME
    if not name.endswith(".yml"):
        name = name + ".yml"
    # accept() refuses a placeholder that is today. The fixture clock is not today.
    on = FIXTURE_ON
    if on == date.today():
        on = date.today() - timedelta(days=2)
    recorded = on - timedelta(days=1)
    ledger = Ledger()
    try:
        ledger.record_fixture(FIXTURES_DIR / name, recorded)
        result = prescribe(ledger, on)
        first = result["rows"][0]
        with tempfile.TemporaryDirectory() as folder:
            row = accept(
                first["template_id"],
                first["parameters"],
                first["reason_codes"],
                on,
                directory=Path(folder),
            )
    except (ValueError, OSError, KeyError, IndexError) as exc:
        raise ApiError(400, str(exc)) from exc
    return {"name": name, "on": on.isoformat(), "row": row}


@router.get("/ledger")
def ledger(request: Request) -> dict:
    _admin(request)
    today = date.today()
    book = Ledger()
    try:
        entries = book.record_fixtures(today)
        windows = book.deposits_on(today)
    except (ValueError, OSError) as exc:
        raise ApiError(400, str(exc)) from exc
    return {
        "as_of": today.isoformat(),
        "entries": entries,
        "emerging": windows.get("emerging") or [],
        "decaying": windows.get("decaying") or [],
    }


@router.get("/goal")
def goal(request: Request) -> dict:
    _admin(request)
    stored = Ledger().goal
    if not isinstance(stored, dict):
        stored = {}
    return {key: stored.get(key) for key in GOAL_FIELDS}
