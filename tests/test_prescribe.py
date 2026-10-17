# test_prescribe.py — template ids and reason codes for the four fixture ledgers.

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.ledger import Ledger
from engines.prescribe import (
    PARAMETER_KEYS,
    load_constraints,
    load_menu,
    prescribe,
    show_fixture_prescriptions,
)

FIXTURES = ("easy.yml", "race_800.yml", "se_400.yml", "vo2_800.yml")
FIXTURES_DIR = ROOT / "tests" / "fixtures"


def _hard_dose(rules: dict) -> float:
    for rule in rules["absolute"]:
        if rule["id"] == "no_second_hard_day":
            return rule["hard_dose"]
    raise ValueError("no_second_hard_day is missing")


def _check(on: date) -> None:
    rules = load_constraints()
    menu = {template["id"]: template for template in load_menu()}
    hard = _hard_dose(rules)
    recorded = on - timedelta(days=1)
    for name in FIXTURES:
        ledger = Ledger()
        entry = ledger.record_fixture(FIXTURES_DIR / name, recorded)
        held = len(ledger.entries)
        result = prescribe(ledger, on)
        if len(ledger.entries) != held:
            raise AssertionError("prescribe wrote on the fixture ledger")
        rows = result["rows"]
        if not 1 <= len(rows) <= 3:
            raise AssertionError(f"{name} returned {len(rows)} rows")
        if result["ontology_version"] != "v0.1":
            raise AssertionError("ontology_version is not v0.1")
        previous_cost = entry["recovery_cost"]
        previous_capacity = entry["capacity"]
        previous_day = date.fromisoformat(entry["date"])
        for row in rows:
            template_id = row["template_id"]
            if template_id not in menu:
                raise AssertionError(f"{template_id} is not in the frozen menu")
            if row["parameters"] != menu[template_id]:
                raise AssertionError(f"{template_id} parameters were not copied")
            if row["ontology_version"] != "v0.1":
                raise AssertionError(f"{template_id} is missing ontology_version")
            if "probability" in row or "readiness_score" in row:
                raise AssertionError("prescription has a score")
            if not row["reason_codes"]:
                raise AssertionError(f"{template_id} has no reason codes")
            day = date.fromisoformat(row["prescribed_on"])
            if (day - previous_day).days != 1:
                raise AssertionError("prescription days are not consecutive")
            family = row["parameters"]["family"]
            dose = float(ledger.capacities[family]["dose"])
            if previous_cost == "high" and dose == hard:
                raise AssertionError(f"{template_id} is quality after high recovery")
            if previous_cost in ("moderate", "high") and dose == hard:
                raise AssertionError(f"{template_id} is a second hard day")
            if (
                previous_capacity == "speed_endurance"
                and family == "speed_endurance"
                and (day - previous_day).days < 2
            ):
                raise AssertionError(f"{template_id} is back-to-back speed endurance")
            for key in PARAMETER_KEYS:
                if row["parameters"][key] != menu[template_id][key]:
                    raise AssertionError(f"{template_id} changed {key}")
            previous_cost = ledger.capacities[family]["recovery_cost"]
            previous_capacity = family
            previous_day = day
        if name == "race_800.yml":
            first = rows[0]
            if first["template_id"] != "aer_4000_r0_x1":
                raise AssertionError("day after the race is not the recovery row")
            codes = first["reason_codes"]
            if "no_quality_after_high_recovery" not in codes:
                raise AssertionError("race day missed no_quality_after_high_recovery")
            if "no_second_hard_day" not in codes:
                raise AssertionError("race day missed no_second_hard_day")
        if name == "se_400.yml":
            codes = rows[0]["reason_codes"]
            if rows[0]["parameters"]["family"] == "speed_endurance":
                raise AssertionError("speed endurance was prescribed the next day")
            if "no_second_hard_day" not in codes:
                raise AssertionError("se day missed no_second_hard_day")
            if "no_back_to_back_speed_endurance" not in codes:
                raise AssertionError("se day missed no_back_to_back_speed_endurance")
        if name == "vo2_800.yml":
            codes = rows[0]["reason_codes"]
            if rows[0]["parameters"]["family"] != "aerobic":
                raise AssertionError("day after aerobic power is not easy")
            if "no_second_hard_day" not in codes:
                raise AssertionError("vo2 day missed no_second_hard_day")
            if "no_quality_after_high_recovery" in codes:
                raise AssertionError("moderate recovery was treated as high")
        if name == "easy.yml":
            if rows[0]["parameters"]["family"] == "aerobic":
                raise AssertionError("variety repeated aerobic")
            if "prefer_variety" not in rows[0]["reason_codes"]:
                raise AssertionError("easy day missed prefer_variety")
            if "prefer_gap" in result["reason_codes"]:
                raise AssertionError("unknown limiting capacity was treated as a gap")


def test_prescribe_fixtures() -> None:
    _check(date(2026, 10, 17))
    show_fixture_prescriptions(date(2026, 10, 17))


if __name__ == "__main__":
    test_prescribe_fixtures()
