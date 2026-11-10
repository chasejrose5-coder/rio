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


@router.get("/intervals")
def interval_names(request: Request) -> dict:
    """JSON names under tests/fixtures/intervals. Rep times are not in this list."""
    _admin(request)
    from ui.last_session import intervals_json_paths

    return {"files": [path.name for path in intervals_json_paths()]}


def _today(request: Request):
    """Today in the Settings time zone. Fixture pages use the same clock."""
    from api.routes import _resolved

    _who, resolved = _resolved(request)
    return resolved["today"]


def _date_format(request: Request) -> str:
    from api.routes import _resolved

    _who, resolved = _resolved(request)
    prefs = resolved.get("prefs") if isinstance(resolved, dict) else {}
    found = prefs.get("date_format") if isinstance(prefs, dict) else "iso"
    return found if found in ("iso", "short") else "iso"


def _units(request: Request) -> str:
    from api.routes import _resolved

    _who, resolved = _resolved(request)
    prefs = resolved.get("prefs") if isinstance(resolved, dict) else {}
    units = prefs.get("units") if isinstance(prefs, dict) else "miles"
    return units if units in ("miles", "km") else "miles"


def _dose_cell(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "" if value is None else str(value)
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _parameter_rows(parameters: object) -> list[dict]:
    from engines.prescribe import PARAMETER_KEYS

    found = parameters if isinstance(parameters, dict) else {}
    rows = []
    for key in PARAMETER_KEYS:
        value = found.get(key)
        text = "" if value is None else str(value).strip()
        rows.append({"Parameter": key, "Value": text or "—"})
    return rows


def _prose(text: str, units: str) -> str:
    from ui.settings import display_training

    return display_training(text, units)


def _deposit_rows(entries: list, date_format: str, *, windows: bool) -> list[dict]:
    from ui.settings import format_date

    rows = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        row = {
            "Capacity": "" if entry.get("capacity") is None else entry.get("capacity"),
            "Dose": _dose_cell(entry.get("dose")),
            "Date": format_date(entry.get("date"), date_format),
            "Source": "" if entry.get("source") is None else entry.get("source"),
        }
        if windows:
            row["expression_window_days"] = entry.get("expression_window_days")
            row["decay_days"] = entry.get("decay_days")
        rows.append(row)
    return rows


def _cell(value: object) -> object:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if value is None:
        return ""
    return value


def _lap_rows(laps: list, units: str) -> tuple[list[dict], str]:
    """The Last Session table. Distance follows the Settings pace unit."""
    from ui.settings import distance_heading, distance_number

    amounts = [lap.get("distance_m") for lap in laps if isinstance(lap, dict)]
    heading = distance_heading(units, amounts)
    rows = []
    for index, lap in enumerate(laps, start=1):
        if not isinstance(lap, dict):
            continue
        rows.append(
            {
                "Lap": index,
                heading: distance_number(lap.get("distance_m"), units, amounts),
                "Seconds": _cell(lap.get("seconds")),
                "Rest (s)": _cell(lap.get("rest_s")),
            }
        )
    return rows, heading


def present_session(payload: dict, units: str, banner: str | None) -> dict:
    """Laps, the classification, and the rules paragraph. The same fields as render_session."""
    from engines.classify import classify
    from engines.explain import explain
    from engines.normalize import normalize

    normalized = normalize(payload)
    found = normalized.get("laps") if isinstance(normalized, dict) else None
    laps = found if isinstance(found, list) else []
    result = classify(payload)
    rows, heading = _lap_rows(laps, units)
    when = payload.get("date") if isinstance(payload.get("date"), str) else ""
    return {
        "date": when,
        "banner": banner,
        "laps": laps,
        "distance_heading": heading,
        "rows": rows,
        "family": result.get("family") or "",
        "confidence": result.get("confidence") or "",
        "reason_codes": list(result.get("reason_codes") or []),
        "prose": explain(result),
    }


def _interval_path(name: str):
    from ui.last_session import intervals_json_paths

    text = name.strip()
    if not text or "/" in text or "\\" in text or text.startswith("."):
        raise ApiError(404, "That file is not on this server.")
    return next((path for path in intervals_json_paths() if path.name == text), None)


@router.get("/intervals/{name}")
def interval_fill(name: str, request: Request) -> dict:
    """WORK times and the lap table from one local JSON file. Nothing is requested from Intervals.icu."""
    _admin(request)
    from ui.last_session import IntervalsFileError, open_intervals, quality_fill

    chosen = _interval_path(name)
    if chosen is None:
        raise ApiError(404, "That file is not on this server.")
    try:
        times, source = quality_fill(chosen)
        payload, banner = open_intervals(chosen)
        shown = present_session(payload, _units(request), banner)
    except IntervalsFileError as exc:
        raise ApiError(400, str(exc)) from exc
    except (TypeError, ValueError, OSError) as exc:
        message = str(exc).strip() or f"{chosen.name} could not be read."
        raise ApiError(400, message) from exc
    shown["name"] = chosen.name
    shown["times"] = times
    shown["source"] = source
    return shown


@router.get("/session")
def fixture_session(request: Request, name: str = "") -> dict:
    """One fixture the way Last Session draws it: laps, family, and the paragraph."""
    _admin(request)
    text = name.strip()
    if not text:
        raise ApiError(400, "Name a fixture.")
    path = _by_name(text)
    try:
        payload = parse_fixture(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ApiError(400, str(exc)) from exc
    source = str(payload.get("source") or "").strip().lower() if isinstance(payload, dict) else ""
    banner = "FIXTURE" if source == "fixture" else None
    try:
        shown = present_session(payload if isinstance(payload, dict) else {}, _units(request), banner)
    except (TypeError, ValueError, OSError) as exc:
        raise ApiError(400, str(exc)) from exc
    shown["name"] = path.stem
    return shown


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
    today = _today(request)
    ledger = Ledger()
    try:
        ledger.record_fixture(path, today - timedelta(days=1))
        result = prescribe(ledger, today)
    except (ValueError, OSError) as exc:
        raise ApiError(400, str(exc)) from exc
    goal = ledger.goal if isinstance(ledger.goal, dict) else {}
    from engines.explain import explain_prescription

    units = _units(request)
    rows = []
    for row in result.get("rows") or []:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        template_id = str(item.get("template_id") or "").strip()
        codes = [str(code) for code in (item.get("reason_codes") or [])]
        prose = ""
        if template_id:
            prose = _prose(explain_prescription(template_id, codes, goal), units)
        item["prose"] = prose
        item["parameter_rows"] = _parameter_rows(item.get("parameters"))
        rows.append(item)
    return {
        "name": path.stem,
        "on": today.isoformat(),
        "limiting_capacities": goal.get("limiting_capacities"),
        "rows": rows,
        "source": "fixture",
        "banner": "FIXTURE",
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


@router.get("/planned")
def planned(request: Request) -> dict:
    """Stored acceptance rows. The checked-in files are not rewritten."""
    _admin(request)
    from engines.accept import PLANNED_DIR, load_planned
    from engines.explain import explain_decision

    units = _units(request)
    rows = []
    for path in sorted(PLANNED_DIR.glob("*.yml")):
        try:
            row = load_planned(path)
        except (OSError, ValueError) as exc:
            raise ApiError(400, str(exc)) from exc
        template_id = str(row.get("template_id") or "").strip()
        codes = [str(code) for code in (row.get("reason_codes") or [])]
        prose = ""
        if template_id:
            prose = _prose(explain_decision(template_id, codes), units)
        source = str(row.get("source") or "")
        rows.append(
            {
                "name": path.stem,
                "template_id": template_id,
                "parameters": row.get("parameters") if isinstance(row.get("parameters"), dict) else {},
                "parameter_rows": _parameter_rows(row.get("parameters")),
                "reason_codes": codes,
                "placeholder_date": row.get("placeholder_date") or "",
                "ontology_version": row.get("ontology_version") or "",
                "source": source,
                "prose": prose,
                "banner": "FIXTURE" if source.strip().lower() == "fixture" else None,
            }
        )
    return {"rows": rows}


@router.get("/ledger")
def ledger(request: Request) -> dict:
    _admin(request)
    today = _today(request)
    book = Ledger()
    try:
        entries = book.record_fixtures(today)
        windows = book.deposits_on(today)
    except (ValueError, OSError) as exc:
        raise ApiError(400, str(exc)) from exc
    emerging = windows.get("emerging") or []
    decaying = windows.get("decaying") or []
    date_format = _date_format(request)
    banner = None
    if any(str(entry.get("source", "")).strip().lower() == "fixture" for entry in entries if isinstance(entry, dict)):
        banner = "FIXTURE"
    return {
        "as_of": today.isoformat(),
        "entries": entries,
        "emerging": emerging,
        "decaying": decaying,
        "banner": banner,
        "deposits_rows": _deposit_rows(entries, date_format, windows=True),
        "emerging_rows": _deposit_rows(emerging, date_format, windows=False),
        "decaying_rows": _deposit_rows(decaying, date_format, windows=False),
    }


@router.get("/goal")
def goal(request: Request) -> dict:
    _admin(request)
    stored = Ledger().goal
    if not isinstance(stored, dict):
        stored = {}
    return {key: stored.get(key) for key in GOAL_FIELDS}
