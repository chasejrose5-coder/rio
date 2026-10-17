# ledger.py — stored classifications, each with ontology_version.

"""One ledger entry per classification.

Dose, expression window, decay, and recovery cost are copied from capacities.yml.
target_date and limiting_capacities stay unknown, as written in goal.yml.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from db.load import parse_fixture
from engines.classify import classify

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "rio" / "v0.1"
CAPACITIES_PATH = PAPER / "capacities.yml"
GOAL_PATH = PAPER / "goal.yml"
FIXTURES_DIR = ROOT / "tests" / "fixtures"
ONTOLOGY_VERSION = PAPER.name

_SPAN = re.compile(r"^(\d+)-(\d+)$")
_INT = re.compile(r"^-?\d+$")
_FLOAT = re.compile(r"^-?\d+\.\d+$")
_ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Fields copied onto an entry. Description is paper text, not an entry field.
CAPACITY_FIELDS = (
    "dose",
    "expression_window_days",
    "decay_days",
    "recovery_cost",
)


def load_paper(path: Path) -> dict:
    """Read a v0.1 paper file. Values stay as written, including unknown."""
    root: dict = {}
    current: dict | None = None
    text = Path(path).read_text(encoding="utf-8")
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        if "\t" in raw:
            raise ValueError(f"{path} line {line_number}: tab indent")
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            raise ValueError(f"{path} line {line_number}: expected key: value")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"{path} line {line_number}: missing key")
        value = value.strip()
        if indent == 0:
            if value == "":
                current = {}
                root[key] = current
            else:
                root[key] = _scalar(value)
                current = None
        elif isinstance(current, dict):
            if value == "":
                raise ValueError(f"{path} line {line_number}: nested block")
            current[key] = _scalar(value)
        else:
            raise ValueError(f"{path} line {line_number}: value without a block")
    return root


def load_capacities(path: Path | None = None) -> dict:
    """Capacity rows from capacities.yml. Missing fields are not filled in."""
    paper = CAPACITIES_PATH if path is None else Path(path)
    rows = load_paper(paper)
    for name, body in rows.items():
        if not isinstance(body, dict):
            raise ValueError(f"{name} has no fields in {paper}")
        for field in CAPACITY_FIELDS:
            if field not in body:
                raise ValueError(f"{name} is missing {field} in {paper}")
        if isinstance(body["dose"], bool) or not isinstance(body["dose"], (int, float)):
            raise ValueError(f"{name} dose is not a number in {paper}")
        _span(str(body["expression_window_days"]))
        _span(str(body["decay_days"]))
        if not str(body["recovery_cost"]).strip():
            raise ValueError(f"{name} recovery_cost is empty in {paper}")
    return rows


def load_goal(path: Path | None = None) -> dict:
    """Goal rows from goal.yml. unknown stays the word unknown."""
    paper = GOAL_PATH if path is None else Path(path)
    return load_paper(paper)


class Ledger:
    """Stored classifications. Each entry keeps the ontology version of the paper."""

    def __init__(
        self,
        capacities_path: Path | None = None,
        goal_path: Path | None = None,
    ) -> None:
        self.capacities = load_capacities(capacities_path)
        self.goal = load_goal(goal_path)
        self.entries: list[dict] = []

    def record(self, classification: dict) -> dict:
        """Write one entry for a classification result.

        The result carries family, reason codes, date, and source.
        Dose and windows come from the capacity row for that family.
        """
        family = str(_required(classification, "family")).strip()
        if family not in self.capacities:
            raise ValueError(f"no capacity rules for {family}")
        version = classification.get("ontology_version", ONTOLOGY_VERSION)
        if version != ONTOLOGY_VERSION:
            raise ValueError(
                f"ontology_version {version} does not match {ONTOLOGY_VERSION}"
            )
        source = str(_required(classification, "source")).strip()
        if not source:
            raise ValueError("source is empty")
        reason_codes = _required(classification, "reason_codes")
        if not isinstance(reason_codes, (list, tuple)):
            raise ValueError("reason_codes must be a list")

        rules = self.capacities[family]
        entry = {
            "capacity": family,
            "dose": rules["dose"],
            "expression_window_days": rules["expression_window_days"],
            "decay_days": rules["decay_days"],
            "recovery_cost": rules["recovery_cost"],
            "ontology_version": version,
            "source": source,
            "date": _as_date(_required(classification, "date")).isoformat(),
            "reason_codes": [str(code) for code in reason_codes],
        }
        self.entries.append(entry)
        return entry

    def record_fixture(self, path: Path, on) -> dict:
        """Classify one fixture file and write one entry.

        The session date is `on`. Fixture files do not contain a date.
        Source is the source written on the fixture.
        """
        payload = parse_fixture(Path(path).read_text(encoding="utf-8"))
        result = classify(payload)
        result["date"] = on
        result["source"] = payload["source"]
        return self.record(result)

    def record_fixtures(self, on, directory: Path | None = None) -> list[dict]:
        """Classify each fixture in tests/fixtures and write one entry each."""
        folder = FIXTURES_DIR if directory is None else Path(directory)
        paths = sorted(folder.glob("*.yml"))
        if not paths:
            raise ValueError(f"no fixtures in {folder}")
        return [self.record_fixture(path, on) for path in paths]

    def deposits_on(self, day) -> dict[str, list[dict]]:
        """Return which deposits are still emerging and which are decaying.

        Emerging: the day falls inside expression_window_days.
        Decaying: the day falls inside decay_days.
        Both spans are counted from the entry date. The entry date is day 0.
        The spans in capacities.yml are inclusive.
        """
        when = _as_date(day)
        emerging: list[dict] = []
        decaying: list[dict] = []
        for entry in self.entries:
            elapsed = (when - date.fromisoformat(entry["date"])).days
            if elapsed < 0:
                continue
            express_lo, express_hi = _span(str(entry["expression_window_days"]))
            decay_lo, decay_hi = _span(str(entry["decay_days"]))
            if express_lo <= elapsed <= express_hi:
                emerging.append(entry)
            if decay_lo <= elapsed <= decay_hi:
                decaying.append(entry)
        return {"emerging": emerging, "decaying": decaying}


def _required(classification: dict, key: str):
    if key not in classification:
        raise ValueError(f"{key} is missing")
    return classification[key]


def _scalar(value: str):
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1]
    if _INT.fullmatch(text):
        return int(text)
    if _FLOAT.fullmatch(text):
        return float(text)
    return text


def _span(text: str) -> tuple[int, int]:
    """Inclusive day span as written, such as 1-3."""
    match = _SPAN.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"day span is not a paper range: {text!r}")
    start = int(match.group(1))
    end = int(match.group(2))
    if start > end:
        raise ValueError(f"day span is reversed: {text!r}")
    return start, end


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1]
        if _ISO_DAY.fullmatch(text):
            return date.fromisoformat(text)
        if "T" in text:
            return datetime.fromisoformat(text).date()
    raise ValueError(f"date is not a calendar date: {value!r}")
