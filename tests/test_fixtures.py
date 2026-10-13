# test_fixtures.py — print family and reason codes for tests/fixtures.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.load import parse_fixture
from engines.classify import classify
from engines.normalize import normalize

FIXTURES_DIR = ROOT / "tests" / "fixtures"


def classify_fixtures() -> None:
    paths = sorted(FIXTURES_DIR.glob("*.yml"))
    for path in paths:
        payload = parse_fixture(path.read_text(encoding="utf-8"))
        result = classify(payload)
        print(f"{path.stem}: {result['family']} {result['reason_codes']}")


def test_classify_fixtures() -> None:
    classify_fixtures()


if __name__ == "__main__":
    classify_fixtures()
