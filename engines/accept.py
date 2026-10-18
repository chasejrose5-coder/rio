# accept.py — one planned row for a template the rules already chose.

"""Acceptance records a yes. It does not choose the workout.

The prescriber already chose the template id. This file copies that id,
the recipe parameters, the reason codes, and a fixture date.
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.ledger import ONTOLOGY_VERSION, Ledger
from engines.prescribe import (
    FIXTURES_DIR,
    PARAMETER_KEYS,
    load_menu,
    prescribe,
)

PLANNED_DIR = ROOT / "tests" / "fixtures" / "planned"
SOURCE = "fixture"

# Acceptance v0.1. A planned row has these fields and no others.
PLANNED_FIELDS = (
    "template_id",
    "parameters",
    "placeholder_date",
    "ontology_version",
    "source",
    "reason_codes",
)

# Phase 4 fixture clock. The day after race_800.yml was recorded.
FIXTURE_NAME = "race_800.yml"
FIXTURE_ON = date(2026, 10, 17)

_ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def accept(
    template_id: str,
    parameters: dict,
    reason_codes: list[str],
    placeholder_date,
    directory: Path | None = None,
) -> dict:
    """Write one planned row and return it.

    template_id must already be in the Phase 1 menu. parameters must be the
    recipe for that id. reason_codes are stored as given. placeholder_date
    is the fixture date, and it is not today.
    """
    if not isinstance(template_id, str) or template_id not in _menu():
        raise ValueError(f"{template_id!r} is not in the frozen menu")
    recipe = _menu()[template_id]
    if recipe["id"] != template_id:
        raise ValueError("template_id was changed")
    copied = _parameters_from_recipe(template_id, parameters, recipe)
    codes = _copy_reason_codes(reason_codes)
    when = _fixture_date(placeholder_date)

    row = {
        "template_id": template_id,
        "parameters": copied,
        "placeholder_date": when.isoformat(),
        "ontology_version": ONTOLOGY_VERSION,
        "source": SOURCE,
        "reason_codes": codes,
    }
    if tuple(row) != PLANNED_FIELDS:
        raise ValueError("planned row fields are not the acceptance fields")
    if row["template_id"] != template_id:
        raise ValueError("template_id was changed")

    folder = PLANNED_DIR if directory is None else Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    path = (folder / f"{template_id}.yml").resolve()
    if path.parent != folder.resolve():
        raise ValueError("template_id was changed")
    path.write_text(format_planned(row), encoding="utf-8")
    stored = load_planned(path)
    if stored != row:
        raise ValueError("stored planned row does not match the acceptance")
    return row


def accept_fixture_prescription(
    name: str = FIXTURE_NAME,
    on: date = FIXTURE_ON,
) -> dict:
    """Accept the first row of one Phase 4 fixture prescription."""
    if not isinstance(on, date) or isinstance(on, datetime):
        raise ValueError("fixture date is not a calendar date")
    if on == date.today():
        raise ValueError("placeholder_date is today")
    recorded = on - timedelta(days=1)
    ledger = Ledger()
    held = len(ledger.entries)
    ledger.record_fixture(FIXTURES_DIR / name, recorded)
    result = prescribe(ledger, on)
    if len(ledger.entries) != held + 1:
        raise ValueError("prescribe changed the fixture ledger")
    first = result["rows"][0]
    if first["prescribed_on"] != on.isoformat():
        raise ValueError("prescription day is not the fixture date")
    before = len(ledger.entries)
    row = accept(
        first["template_id"],
        first["parameters"],
        first["reason_codes"],
        on,
    )
    if len(ledger.entries) != before:
        raise ValueError("accept wrote on the fixture ledger")
    if row["template_id"] != first["template_id"]:
        raise ValueError("template_id was changed")
    if row["reason_codes"] != list(first["reason_codes"]):
        raise ValueError("reason_codes were changed")
    return row


def format_planned(row: dict) -> str:
    """YAML for one planned row. Only the acceptance fields are written."""
    if tuple(row) != PLANNED_FIELDS:
        raise ValueError("planned row fields are not the acceptance fields")
    lines = [
        f"template_id: {_quote(row['template_id'])}",
        "parameters:",
    ]
    parameters = row["parameters"]
    if tuple(parameters) != PARAMETER_KEYS:
        raise ValueError("parameters are not the recipe fields")
    for key in PARAMETER_KEYS:
        lines.append(f"  {key}: {_quote(parameters[key])}")
    lines.append(f"placeholder_date: {_quote(row['placeholder_date'])}")
    lines.append(f"ontology_version: {_quote(row['ontology_version'])}")
    lines.append("source: fixture")
    lines.append("reason_codes:")
    codes = row["reason_codes"]
    if not codes:
        raise ValueError("reason_codes is empty")
    for code in codes:
        lines.append(f"  - {_quote(code)}")
    lines.append("")
    return "\n".join(lines)


def load_planned(path: Path) -> dict:
    """Read one planned row. Unknown fields are an error."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    row: dict = {}
    index = 0
    while index < len(lines):
        raw = lines[index]
        if not raw.strip():
            index += 1
            continue
        if raw.startswith(" ") or raw.startswith("-") or "\t" in raw:
            raise ValueError(f"{path} line {index + 1}: unexpected indent")
        key, value = _split_field(raw, path, index + 1)
        if key in row:
            raise ValueError(f"{path} line {index + 1}: duplicate {key}")
        if key not in PLANNED_FIELDS:
            raise ValueError(f"{path} line {index + 1}: unknown field {key}")
        if key == "parameters":
            if value != "":
                raise ValueError(f"{path} line {index + 1}: parameters must be a block")
            parameters, index = _read_parameters(lines, index + 1, path)
            row[key] = parameters
            continue
        if key == "reason_codes":
            if value != "":
                raise ValueError(f"{path} line {index + 1}: reason_codes must be a list")
            codes, index = _read_codes(lines, index + 1, path)
            row[key] = codes
            continue
        row[key] = value
        index += 1
    missing = [key for key in PLANNED_FIELDS if key not in row]
    if missing:
        raise ValueError(f"{path} is missing {', '.join(missing)}")
    if tuple(row) != PLANNED_FIELDS:
        raise ValueError(f"{path} fields are not the acceptance fields")
    if row["source"] != SOURCE:
        raise ValueError(f"{path} source is not fixture")
    if row["ontology_version"] != ONTOLOGY_VERSION:
        raise ValueError(f"{path} ontology_version is not {ONTOLOGY_VERSION}")
    _fixture_date(row["placeholder_date"])
    return row


def _menu() -> dict[str, dict]:
    return {template["id"]: template for template in load_menu()}


def _parameters_from_recipe(template_id: str, parameters: dict, recipe: dict) -> dict:
    if not isinstance(parameters, dict):
        raise ValueError("parameters are not the recipe fields")
    copied = {key: recipe[key] for key in PARAMETER_KEYS}
    if parameters != copied:
        raise ValueError(f"{template_id} parameters were not copied from the recipe")
    if copied["id"] != template_id:
        raise ValueError("template_id was changed")
    return copied


def _copy_reason_codes(reason_codes) -> list[str]:
    if isinstance(reason_codes, str) or not isinstance(reason_codes, (list, tuple)):
        raise ValueError("reason_codes must be a list")
    codes: list[str] = []
    for code in reason_codes:
        if not isinstance(code, str) or not code:
            raise ValueError("reason code is empty")
        if "\n" in code or "\r" in code:
            raise ValueError("reason code is not a single line")
        codes.append(code)
    if not codes:
        raise ValueError("reason_codes is empty")
    return codes


def _fixture_date(value) -> date:
    if isinstance(value, datetime):
        when = value.date()
    elif isinstance(value, date):
        when = value
    elif isinstance(value, str) and _ISO_DAY.fullmatch(value):
        when = date.fromisoformat(value)
    else:
        raise ValueError(f"placeholder_date is not a fixture date: {value!r}")
    if when == date.today():
        raise ValueError("placeholder_date is today")
    return when


def _read_parameters(lines: list[str], start: int, path: Path) -> tuple[dict, int]:
    parameters: dict[str, str] = {}
    index = start
    while index < len(lines):
        raw = lines[index]
        if not raw.strip():
            break
        if not raw.startswith("  ") or raw.startswith("  -") or "\t" in raw:
            break
        key, value = _split_field(raw.strip(), path, index + 1)
        if key not in PARAMETER_KEYS:
            raise ValueError(f"{path} line {index + 1}: unknown field {key}")
        if key in parameters:
            raise ValueError(f"{path} line {index + 1}: duplicate {key}")
        parameters[key] = value
        index += 1
    if tuple(parameters) != PARAMETER_KEYS:
        raise ValueError(f"{path} parameters are not the recipe fields")
    return parameters, index


def _read_codes(lines: list[str], start: int, path: Path) -> tuple[list[str], int]:
    codes: list[str] = []
    index = start
    while index < len(lines):
        raw = lines[index]
        if not raw.strip():
            break
        if not raw.startswith("  - ") or "\t" in raw:
            break
        codes.append(_unquote(raw.strip()[2:].strip()))
        index += 1
    if not codes:
        raise ValueError(f"{path} reason_codes is empty")
    return codes, index


def _split_field(text: str, path: Path, line_number: int) -> tuple[str, str]:
    if ":" not in text:
        raise ValueError(f"{path} line {line_number}: expected key: value")
    key, value = text.split(":", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"{path} line {line_number}: missing key")
    return key, _unquote(value.strip())


def _quote(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("planned value is not text")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return value


if __name__ == "__main__":
    print(format_planned(accept_fixture_prescription()))
