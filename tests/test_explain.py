# test_explain.py — paragraphs for classifications and for prescribe() rows.

from __future__ import annotations

import json
import os
import sys
import tempfile
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.load import parse_fixture
from engines.classify import classify
from engines.explain import (
    GOAL_FIELDS,
    SPEND_CAP_MICRO_USD,
    STRUCTURE_WORDS,
    _complete,
    _prescription_acceptable,
    _read_spend,
    _reserve_spend,
    _settle_spend,
    explain,
    explain_prescription,
)
from engines.ledger import Ledger
from engines.prescribe import load_menu, prescribe

FIXTURES_DIR = ROOT / "tests" / "fixtures"
FIXTURE_NAMES = ("easy.yml", "race_800.yml", "se_400.yml", "vo2_800.yml")
ON = date(2026, 10, 17)


def explain_fixtures() -> None:
    for name in FIXTURE_NAMES:
        path = FIXTURES_DIR / name
        payload = parse_fixture(path.read_text(encoding="utf-8"))
        result = classify(payload)
        paragraph = explain(result)
        print(f"{path.stem}: {result['family']}")
        print(paragraph)


def test_explain_fixtures() -> None:
    explain_fixtures()


def _goal() -> dict:
    return Ledger().goal


def _check_paragraph(text: str, template_id: str, reason_codes: list[str], goal: dict) -> None:
    if not text or "\n" in text:
        raise AssertionError("paragraph is not one line")
    if len(text.split()) > 60:
        raise AssertionError("paragraph is over 60 words")
    if template_id not in text:
        raise AssertionError("paragraph dropped the chosen template id")
    menu_ids = {template["id"] for template in load_menu()}
    for other in menu_ids:
        if other != template_id and other in text:
            raise AssertionError("paragraph named a different template id")
    lowered = text.lower()
    for word in STRUCTURE_WORDS:
        if f" {word} " in f" {lowered} ":
            raise AssertionError(f"paragraph invented structure: {word}")
    if " x " in lowered or "×" in text:
        raise AssertionError("paragraph invented interval math")
    for key in GOAL_FIELDS:
        if str(goal[key]).lower() not in lowered:
            raise AssertionError(f"paragraph dropped {key}")
    if "probability" in lowered or "readiness" in lowered:
        raise AssertionError("paragraph added a score")
    families = _mentioned_from_restatement(template_id, reason_codes, goal)
    if not _prescription_acceptable(text, template_id, reason_codes, _goal_fields(goal), families):
        raise AssertionError("paragraph broke the prescription rules")


def _goal_fields(goal: dict) -> dict[str, str]:
    return {key: str(goal[key]).strip() for key in GOAL_FIELDS}


def _mentioned_from_restatement(template_id: str, reason_codes: list[str], goal: dict) -> set[str]:
    from engines.explain import _mentioned_families, _prescription_restatement

    paragraph = _prescription_restatement(template_id, reason_codes, _goal_fields(goal))
    return _mentioned_families(paragraph)


def explain_prescriptions() -> None:
    goal = _goal()
    recorded = ON - timedelta(days=1)
    for name in FIXTURE_NAMES:
        ledger = Ledger()
        ledger.record_fixture(FIXTURES_DIR / name, recorded)
        result = prescribe(ledger, ON)
        print(f"{Path(name).stem}:")
        for row in result["rows"]:
            paragraph = explain_prescription(row["template_id"], row["reason_codes"], goal)
            print(paragraph)
            _check_paragraph(paragraph, row["template_id"], row["reason_codes"], goal)


def test_explain_prescriptions() -> None:
    explain_prescriptions()


def test_wrong_id_loses() -> None:
    """A paragraph that names another id is dropped. The chosen id stays."""
    from engines import explain as explain_mod

    goal = _goal()
    chosen = "aer_4000_r0_x1"
    real = explain_mod._complete

    def disagree(*_args, **_kwargs):
        return (
            "The rules chose se_400_r90_x6. Run 6 x 400 with 90 s rest. "
            "The current mark is 2:02.90."
        )

    explain_mod._complete = disagree
    try:
        text = explain_prescription(chosen, ["no_second_hard_day"], goal)
    finally:
        explain_mod._complete = real
    if chosen not in text:
        raise AssertionError("chosen id did not win")
    if "se_400_r90_x6" in text or "6 x 400" in text:
        raise AssertionError("disagreeing paragraph was kept")


def test_invented_structure_is_rejected() -> None:
    goal = _goal_fields(_goal())
    template_id = "aer_4000_r0_x1"
    codes = ["no_second_hard_day"]
    from engines.explain import _prescription_restatement

    text = _prescription_restatement(template_id, codes, goal)
    families = _mentioned_from_restatement(template_id, codes, _goal())
    invented = text.replace(
        "Limiting capacities are unknown.",
        "Limiting capacities are unknown. Do 6 x 400 m with 90 s rest.",
    )
    if _prescription_acceptable(invented, template_id, codes, goal, families):
        raise AssertionError("invented interval math was accepted")
    other = text.replace(template_id, "se_400_r90_x6")
    if _prescription_acceptable(other, template_id, codes, goal, families):
        raise AssertionError("a different template id was accepted")


def test_explain_prescription_requires_goal_fields() -> None:
    try:
        explain_prescription("aer_4000_r0_x1", ["no_second_hard_day"], {"current_mark": "2:02.90"})
    except ValueError as exc:
        if "target_time" not in str(exc):
            raise AssertionError("missing goal field was not named") from exc
    else:
        raise AssertionError("missing goal field was accepted")


def test_spend_cap_blocks_the_api() -> None:
    directory = tempfile.mkdtemp()
    path = Path(directory) / "spend.json"
    path.write_text(
        json.dumps({"micro_usd": SPEND_CAP_MICRO_USD}),
        encoding="utf-8",
    )
    previous = {
        name: os.environ.get(name)
        for name in (
            "RIO_EXPLAIN_SPEND_PATH",
            "RIO_EXPLAIN_API_KEY",
            "RIO_EXPLAIN_MODEL",
            "RIO_EXPLAIN_BASE_URL",
        )
    }
    called: list[bool] = []

    def boom(*_args, **_kwargs):
        called.append(True)
        raise AssertionError("api was called")

    real = urllib.request.urlopen
    urllib.request.urlopen = boom
    os.environ["RIO_EXPLAIN_SPEND_PATH"] = str(path)
    os.environ["RIO_EXPLAIN_API_KEY"] = "test-key"
    os.environ["RIO_EXPLAIN_MODEL"] = "test-model"
    os.environ["RIO_EXPLAIN_BASE_URL"] = "https://example.com/v1"
    try:
        if _complete("The rules called this aerobic.") is not None:
            raise AssertionError("call was allowed at the $25 cap")
        if called:
            raise AssertionError("api was called at the $25 cap")
        if _read_spend(path) != SPEND_CAP_MICRO_USD:
            raise AssertionError("spend record changed")
    finally:
        urllib.request.urlopen = real
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def test_spend_reservation_stops_at_the_cap() -> None:
    directory = tempfile.mkdtemp()
    path = Path(directory) / "spend.json"
    previous = os.environ.get("RIO_EXPLAIN_SPEND_PATH")
    os.environ["RIO_EXPLAIN_SPEND_PATH"] = str(path)
    try:
        if _reserve_spend(1_000) is not True:
            raise AssertionError("first reservation was refused")
        if _read_spend(path) != 1_000:
            raise AssertionError("reservation was not recorded")
        _settle_spend(1_000, 400)
        if _read_spend(path) != 400:
            raise AssertionError("settlement did not replace the reservation")
        if _reserve_spend(SPEND_CAP_MICRO_USD) is not False:
            raise AssertionError("reservation past $25 was allowed")
        if _read_spend(path) != 400:
            raise AssertionError("refused reservation changed the record")
        if _reserve_spend(SPEND_CAP_MICRO_USD - 400) is not True:
            raise AssertionError("reservation up to $25 was refused")
        if _read_spend(path) != SPEND_CAP_MICRO_USD:
            raise AssertionError("record did not stop at $25")
        if _reserve_spend(1) is not False:
            raise AssertionError("spend past $25 was allowed")
    finally:
        if previous is None:
            os.environ.pop("RIO_EXPLAIN_SPEND_PATH", None)
        else:
            os.environ["RIO_EXPLAIN_SPEND_PATH"] = previous


if __name__ == "__main__":
    explain_fixtures()
    explain_prescriptions()
    test_wrong_id_loses()
    test_invented_structure_is_rejected()
    test_explain_prescription_requires_goal_fields()
    test_spend_cap_blocks_the_api()
    test_spend_reservation_stops_at_the_cap()
