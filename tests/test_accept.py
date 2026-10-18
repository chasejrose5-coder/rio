# test_accept.py — one planned row from the Phase 4 race-day prescription.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.accept import (
    FIXTURE_NAME,
    FIXTURE_ON,
    PLANNED_DIR,
    PLANNED_FIELDS,
    accept,
    accept_fixture_prescription,
    format_planned,
    load_planned,
)
from engines.ledger import Ledger
from engines.prescribe import PARAMETER_KEYS, load_menu, prescribe

EXAM = ROOT / "tests" / "labeled_sessions.yml"
FIXTURES_DIR = ROOT / "tests" / "fixtures"


def test_accept_race_fixture() -> None:
    if FIXTURE_ON == date.today():
        raise AssertionError("fixture date is today")
    exam = EXAM.read_text(encoding="utf-8")
    menu = {template["id"]: template for template in load_menu()}

    recorded = date(2026, 10, 16)
    ledger = Ledger()
    ledger.record_fixture(FIXTURES_DIR / FIXTURE_NAME, recorded)
    prescription = prescribe(ledger, FIXTURE_ON)
    first = prescription["rows"][0]
    if first["template_id"] != "aer_4000_r0_x1":
        raise AssertionError("day after the race is not the recovery row")

    row = accept_fixture_prescription(FIXTURE_NAME, FIXTURE_ON)
    if tuple(row) != PLANNED_FIELDS:
        raise AssertionError(f"planned row fields are {tuple(row)}")
    if row["template_id"] != first["template_id"]:
        raise AssertionError("template_id was changed")
    if row["template_id"] not in menu:
        raise AssertionError(f"{row['template_id']} is not in the frozen menu")
    if row["parameters"] != menu[row["template_id"]]:
        raise AssertionError("parameters were not copied from the recipe")
    if tuple(row["parameters"]) != PARAMETER_KEYS:
        raise AssertionError("parameters are not the recipe fields")
    if row["reason_codes"] != list(first["reason_codes"]):
        raise AssertionError("reason_codes were not copied from the prescriber")
    if row["placeholder_date"] != FIXTURE_ON.isoformat():
        raise AssertionError("placeholder_date is not the fixture date")
    if row["placeholder_date"] == date.today().isoformat():
        raise AssertionError("placeholder_date is today")
    if row["ontology_version"] != "v0.1":
        raise AssertionError("ontology_version is not v0.1")
    if row["source"] != "fixture":
        raise AssertionError("source is not fixture")
    for banned in ("probability", "readiness_score", "prescribed_on", "wellness"):
        if banned in row:
            raise AssertionError(f"planned row invented {banned}")

    path = PLANNED_DIR / f"{row['template_id']}.yml"
    written = sorted(PLANNED_DIR.glob("*.yml"))
    if written != [path]:
        raise AssertionError(f"planned directory has {written}")
    stored = load_planned(path)
    if stored != row:
        raise AssertionError("stored row does not match the acceptance")
    top = [
        line.split(":", 1)[0]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith(" ")
    ]
    if top != list(PLANNED_FIELDS):
        raise AssertionError(f"planned row fields are {top}")
    if EXAM.read_text(encoding="utf-8") != exam:
        raise AssertionError("labeled_sessions.yml was changed")

    try:
        accept("se_400_r90_x6", row["parameters"], row["reason_codes"], FIXTURE_ON)
    except ValueError:
        pass
    else:
        raise AssertionError("template_id was changed")
    if sorted(PLANNED_DIR.glob("*.yml")) != [path]:
        raise AssertionError("a second planned row was written")

    try:
        accept(row["template_id"], row["parameters"], row["reason_codes"], date.today())
    except ValueError:
        pass
    else:
        raise AssertionError("today was stored as the placeholder date")

    print(format_planned(row), end="")


if __name__ == "__main__":
    test_accept_race_fixture()
