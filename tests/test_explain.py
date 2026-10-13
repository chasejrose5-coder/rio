# test_explain.py — print family and paragraph for the four fixtures.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.load import parse_fixture
from engines.classify import classify
from engines.explain import explain

FIXTURES_DIR = ROOT / "tests" / "fixtures"
FIXTURE_NAMES = ("easy.yml", "race_800.yml", "se_400.yml", "vo2_800.yml")


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


if __name__ == "__main__":
    explain_fixtures()
