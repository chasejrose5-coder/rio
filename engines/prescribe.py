# prescribe.py — next 800m session from ledger labels. Rules only.

"""One to three template ids from the frozen menu.

Reads constraints.yml, the Phase 1 template files, the goal object, and the
ledger. Absolute rules run first. Preferences only rank templates those rules
already allowed. Parameters are copied from the recipe.
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

PAPER = ROOT / "rio" / "v0.1"
CONSTRAINTS_PATH = PAPER / "constraints.yml"
MENU_DIR = ROOT / "rio" / "templates" / "800m"
FIXTURES_DIR = ROOT / "tests" / "fixtures"

# The next one to three days. One template each day.
MAX_DAYS = 3

PARAMETER_KEYS = (
    "id",
    "name",
    "family",
    "primary_stimulus",
    "secondary_stimulus",
    "default_structure",
    "constraints",
)

_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
}

_RECOVERY_RANK = {"low": 0, "moderate": 1, "high": 2}
_ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SPAN = re.compile(r"^(\d+)-(\d+)$")

# Absolute ids this file knows how to enforce. An unknown id is an error.
_ABSOLUTE_IDS = (
    "no_quality_after_high_recovery",
    "no_second_hard_day",
    "no_back_to_back_speed_endurance",
    "closed_menu_only",
)
_PREFERENCE_IDS = (
    "prefer_gap",
    "prefer_variety",
)


def load_constraints(path: Path | None = None) -> dict:
    """Absolute rules, then preferences, as written in constraints.yml."""
    paper = CONSTRAINTS_PATH if path is None else Path(path)
    version = None
    section = None
    current: dict | None = None
    grouped: dict[str, list[dict]] = {"absolute": [], "preference": []}

    text = paper.read_text(encoding="utf-8")
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        if "\t" in raw:
            raise ValueError(f"{paper} line {line_number}: tab indent")
        stripped = raw.strip()
        if stripped.startswith("- "):
            if section not in grouped:
                raise ValueError(f"{paper} line {line_number}: list outside a section")
            current = {}
            grouped[section].append(current)
            _store_field(current, stripped[2:].strip(), paper, line_number)
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        key, value = _split_field(stripped, paper, line_number)
        if indent == 0:
            if key == "ontology_version":
                version = value
                current = None
            elif value == "" and key in grouped:
                section = key
                current = None
            else:
                raise ValueError(f"{paper} line {line_number}: unexpected {key}")
        else:
            if current is None:
                raise ValueError(f"{paper} line {line_number}: value without a rule")
            current[key] = value

    if not version:
        raise ValueError(f"{paper} is missing ontology_version")
    if version != ONTOLOGY_VERSION:
        raise ValueError(
            f"ontology_version {version} does not match {ONTOLOGY_VERSION}"
        )
    _expect_ids(grouped["absolute"], _ABSOLUTE_IDS, paper)
    _expect_ids(grouped["preference"], _PREFERENCE_IDS, paper)
    parsed = {
        "ontology_version": version,
        "absolute": [_prepare_absolute(rule) for rule in grouped["absolute"]],
        "preference": [_prepare_preference(rule) for rule in grouped["preference"]],
    }
    return parsed


def load_menu(directory: Path | None = None) -> list[dict]:
    """Phase 1 recipes. The id in the file is the id the prescriber may return."""
    folder = MENU_DIR if directory is None else Path(directory)
    paths = sorted(folder.glob("*.yml"))
    if not paths:
        raise ValueError(f"no templates in {folder}")
    menu: list[dict] = []
    seen: set[str] = set()
    for path in paths:
        template = _load_template(path)
        if template["id"] in seen:
            raise ValueError(f"duplicate template id {template['id']}")
        if template["id"] != path.stem:
            raise ValueError(f"{path.name} id is {template['id']}")
        seen.add(template["id"])
        menu.append(template)
    menu.sort(key=lambda template: template["id"])
    return menu


def prescribe(ledger: Ledger, on=None) -> dict:
    """Return one to three prescription rows starting on `on`.

    Each row has a menu template_id, the parameters stored on that recipe,
    ontology_version, the day, and the reason codes that fired that day.
    The caller's ledger is left unchanged.
    """
    rules = load_constraints()
    menu = load_menu()
    menu_ids = {template["id"] for template in menu}
    version = rules["ontology_version"]
    start = date.today() if on is None else _as_date(on)
    goal = ledger.goal
    capacities = ledger.capacities

    scratch = _copy_ledger(ledger)
    for entry in scratch.entries:
        if entry["ontology_version"] != version:
            raise ValueError(
                f"ledger ontology_version {entry['ontology_version']} does not match {version}"
            )

    rows: list[dict] = []
    planned: list[tuple[date, str]] = []
    for offset in range(MAX_DAYS):
        day = start + timedelta(days=offset)
        legal, fired = _legal_templates(
            menu, rules, day, scratch.entries, capacities, goal, planned, menu_ids
        )
        if not legal:
            break
        chosen, preference_codes = _prefer(
            legal, rules, day, scratch, goal, capacities
        )
        if chosen["id"] not in menu_ids:
            raise ValueError(f"template {chosen['id']} is not in the frozen menu")
        reason_codes = _in_paper_order(fired + preference_codes, rules)
        row = {
            "template_id": chosen["id"],
            "parameters": {key: chosen[key] for key in PARAMETER_KEYS},
            "ontology_version": version,
            "prescribed_on": day.isoformat(),
            "reason_codes": reason_codes,
        }
        still_blocked, _ = _legal_templates(
            [chosen], rules, day, scratch.entries, capacities, goal, planned, menu_ids
        )
        if not still_blocked:
            raise ValueError(f"{chosen['id']} broke an absolute constraint")
        rows.append(row)
        scratch.record(
            {
                "family": chosen["family"],
                "reason_codes": list(reason_codes),
                "date": day,
                "source": "prescription",
                "ontology_version": version,
            }
        )
        planned.append((day, chosen["id"]))

    if not rows:
        raise ValueError("no legal template in the frozen menu")
    if len(rows) > MAX_DAYS:
        raise ValueError("prescription is longer than three days")

    union: list[str] = []
    for row in rows:
        for code in row["reason_codes"]:
            if code not in union:
                union.append(code)
    return {
        "ontology_version": version,
        "reason_codes": _in_paper_order(union, rules),
        "rows": rows,
    }


def _legal_templates(
    menu: list[dict],
    rules: dict,
    day: date,
    entries: list[dict],
    capacities: dict,
    goal: dict,
    planned: list[tuple[date, str]],
    menu_ids: set[str],
) -> tuple[list[dict], list[str]]:
    """Templates that pass every absolute rule and their own recipe ban."""
    fired: list[str] = []
    legal: list[dict] = []
    for template in menu:
        blocked = _absolute_blocks(
            template, rules, day, entries, capacities, menu_ids
        )
        for code in blocked:
            if code not in fired:
                fired.append(code)
        if blocked:
            continue
        legal.append(template)
    return legal, fired


def _absolute_blocks(
    template: dict,
    rules: dict,
    day: date,
    entries: list[dict],
    capacities: dict,
    menu_ids: set[str],
) -> list[str]:
    blocked: list[str] = []
    for rule in rules["absolute"]:
        if _absolute_hit(rule, rules, template, day, entries, capacities, menu_ids):
            blocked.append(rule["id"])
    return blocked


def _absolute_hit(
    rule: dict,
    rules: dict,
    template: dict,
    day: date,
    entries: list[dict],
    capacities: dict,
    menu_ids: set[str],
) -> bool:
    rule_id = rule["id"]
    if rule_id == "closed_menu_only":
        return template["id"] not in menu_ids
    if rule_id == "no_quality_after_high_recovery":
        if _yesterday_recovery(entries, day) != "high":
            return False
        return _dose_kind(template, capacities, rules) != "easy"
    if rule_id == "no_second_hard_day":
        recovery = _yesterday_recovery(entries, day)
        if recovery not in ("moderate", "high"):
            return False
        return _dose_kind(template, capacities, rules) == "hard"
    if rule_id == "no_back_to_back_speed_endurance":
        if not _is_speed_endurance(template):
            return False
        last = _last_before(entries, day)
        if last is None or last["capacity"] != "speed_endurance":
            return False
        elapsed = (day - date.fromisoformat(last["date"])).days
        return elapsed < rule["gap_days"]
    raise ValueError(f"absolute rule {rule_id} has no check")


def _prefer(
    legal: list[dict],
    rules: dict,
    day: date,
    scratch: Ledger,
    goal: dict,
    capacities: dict,
) -> tuple[dict, list[str]]:
    """Rank the legal list. Returns one template and the preference codes that cut."""
    pool = list(legal)
    fired: list[str] = []
    gaps = _gap_capacities(scratch, goal, capacities, day)
    if gaps:
        # Primary stimulus is the clearer gap. Secondary counts only when
        # no legal template trains the gap directly.
        direct = [
            template
            for template in pool
            if template["primary_stimulus"] in gaps or template["family"] in gaps
        ]
        addressing = direct or [
            template for template in pool if _trains_any(template, gaps)
        ]
        if addressing and len(addressing) < len(pool):
            pool = addressing
            fired.append("prefer_gap")

    variety = _rule_by_id(rules["preference"], "prefer_variety")
    fresh = [
        template
        for template in pool
        if not _deposited_recently(
            template["family"], scratch.entries, day, variety["recent_days"]
        )
    ]
    if fresh and len(fresh) < len(pool):
        pool = fresh
        fired.append("prefer_variety")

    return _choose(pool, day, scratch.entries, list(capacities)), fired


def _choose(
    pool: list[dict],
    day: date,
    entries: list[dict],
    capacity_order: list[str],
) -> dict:
    """One template from a tied pool.

    A recipe that names itself as the day-after-hard row wins on that day.
    Otherwise the first still-legal capacity in the ledger's capacity list
    is used, then that family's default or reference recipe if it has one.
    The lowest template id breaks a remaining tie. This is menu order, not a score.
    """
    recovery = _yesterday_recovery(entries, day)
    if recovery in ("moderate", "high"):
        named = [template for template in pool if _is_recovery_row(template)]
        if len(named) == 1:
            return named[0]
    ordered = [
        name
        for name in capacity_order
        if any(template["family"] == name for template in pool)
    ]
    if ordered:
        pool = [template for template in pool if template["family"] == ordered[0]]
    marked = [
        template
        for template in pool
        if _is_named_default(template) or _is_reference(template)
    ]
    if len(marked) == 1:
        return marked[0]
    return min(pool, key=lambda template: template["id"])


def _gap_capacities(
    scratch: Ledger, goal: dict, capacities: dict, day: date
) -> set[str]:
    """Limiting capacities the ledger currently shows as low or decaying."""
    limiting = _limiting(goal, capacities)
    if not limiting:
        return set()
    decaying = {
        entry["capacity"] for entry in scratch.deposits_on(day)["decaying"]
    }
    gaps: set[str] = set()
    for capacity in limiting:
        if capacity in decaying or _is_low(capacity, scratch.entries, day):
            gaps.add(capacity)
    return gaps


def _prepare_absolute(rule: dict) -> dict:
    prepared = {"id": rule["id"], "rule": rule["rule"]}
    if rule["id"] == "no_second_hard_day":
        supporting = re.search(r"supporting \(([0-9.]+)\)", rule["rule"], re.I)
        hard = re.search(r"\bhard \(([0-9.]+)\)", rule["rule"], re.I)
        if supporting is None or hard is None:
            raise ValueError("no_second_hard_day does not name supporting and hard doses")
        prepared["supporting_dose"] = float(supporting.group(1))
        prepared["hard_dose"] = float(hard.group(1))
    if rule["id"] == "no_back_to_back_speed_endurance":
        match = re.search(r"at least ([a-z]+) day", rule["rule"], re.I)
        if match is None or match.group(1).lower() not in _WORDS:
            raise ValueError("no_back_to_back_speed_endurance does not say how many days")
        # "At least one day must pass" means the next calendar day is too soon.
        prepared["gap_days"] = _WORDS[match.group(1).lower()] + 1
    return prepared


def _prepare_preference(rule: dict) -> dict:
    prepared = {"id": rule["id"], "rule": rule["rule"]}
    if rule["id"] == "prefer_variety":
        match = re.search(r"last ([a-z]+) days", rule["rule"], re.I)
        if match is None or match.group(1).lower() not in _WORDS:
            raise ValueError("prefer_variety does not say how many days")
        prepared["recent_days"] = _WORDS[match.group(1).lower()]
    return prepared


def _dose_kind(template: dict, capacities: dict, rules: dict) -> str:
    """easy, supporting, or hard.

    Hard and supporting are the doses named in no_second_hard_day.
    Any other ledger dose, including aerobic 0, is easy.
    """
    family = template["family"]
    if family not in capacities:
        raise ValueError(f"no capacity rules for {family}")
    dose = capacities[family]["dose"]
    if isinstance(dose, bool) or not isinstance(dose, (int, float)):
        raise ValueError(f"{family} dose is not a number")
    number = float(dose)
    hard_rule = _rule_by_id(rules["absolute"], "no_second_hard_day")
    if number == hard_rule["hard_dose"]:
        return "hard"
    if number == hard_rule["supporting_dose"]:
        return "supporting"
    return "easy"


def _is_speed_endurance(template: dict) -> bool:
    return (
        template["family"] == "speed_endurance"
        or template["primary_stimulus"] == "speed_endurance"
    )


def _trains_any(template: dict, capacities: set[str]) -> bool:
    trained = {template["primary_stimulus"], template["family"]}
    secondary = str(template.get("secondary_stimulus", "")).strip()
    if secondary:
        trained.add(secondary)
    return bool(trained & capacities)


def _is_recovery_row(template: dict) -> bool:
    text = template["constraints"].lower()
    return "day-after-hard" in text or "day-after-race" in text


def _is_named_default(template: dict) -> bool:
    return "the default " in template["default_structure"].lower()


def _is_reference(template: dict) -> bool:
    return "the reference " in template["default_structure"].lower()


def _limiting(goal: dict, capacities: dict) -> list[str]:
    raw = str(goal.get("limiting_capacities", "")).strip()
    if raw.lower() == "unknown" or not raw:
        return []
    found: list[str] = []
    for part in re.split(r",|\band\b", raw):
        key = part.strip().lower().replace(" ", "_")
        if key in capacities and key not in found:
            found.append(key)
    return found


def _is_low(capacity: str, entries: list[dict], day: date) -> bool:
    """Low: no deposit of this capacity is still inside its stored decay span."""
    for entry in entries:
        if entry["capacity"] != capacity:
            continue
        elapsed = (day - date.fromisoformat(entry["date"])).days
        if elapsed < 0:
            continue
        _, decay_hi = _span(str(entry["decay_days"]))
        if elapsed <= decay_hi:
            return False
    return True


def _deposited_recently(
    capacity: str, entries: list[dict], day: date, window: int
) -> bool:
    for entry in entries:
        if entry["capacity"] != capacity:
            continue
        elapsed = (day - date.fromisoformat(entry["date"])).days
        if 0 < elapsed <= window:
            return True
    return False


def _yesterday_entries(entries: list[dict], day: date) -> list[dict]:
    target = (day - timedelta(days=1)).isoformat()
    return [entry for entry in entries if entry["date"] == target]


def _yesterday_recovery(entries: list[dict], day: date) -> str | None:
    yesterday = _yesterday_entries(entries, day)
    if not yesterday:
        return None
    strictest = yesterday[0]["recovery_cost"]
    for entry in yesterday[1:]:
        cost = entry["recovery_cost"]
        if cost not in _RECOVERY_RANK or strictest not in _RECOVERY_RANK:
            raise ValueError(f"recovery cost is not low, moderate, or high: {cost}")
        if _RECOVERY_RANK[cost] > _RECOVERY_RANK[strictest]:
            strictest = cost
    if strictest not in _RECOVERY_RANK:
        raise ValueError(f"recovery cost is not low, moderate, or high: {strictest}")
    return strictest


def _last_before(entries: list[dict], day: date) -> dict | None:
    prior = [entry for entry in entries if entry["date"] < day.isoformat()]
    if not prior:
        return None
    return max(prior, key=lambda entry: entry["date"])


def _race_within(entries: list[dict], day: date, days: int) -> bool:
    return _capacity_within(entries, "race_readiness", day, days)


def _capacity_within(entries: list[dict], capacity: str, day: date, days: int) -> bool:
    for entry in entries:
        if entry["capacity"] != capacity:
            continue
        elapsed = (day - date.fromisoformat(entry["date"])).days
        if 0 <= elapsed <= days:
            return True
    return False


def _on_target_date(goal: dict, day: date) -> bool:
    value = goal.get("target_date")
    if value is None:
        return False
    text = str(value).strip()
    if text.lower() == "unknown" or not _ISO_DAY.fullmatch(text):
        return False
    return date.fromisoformat(text) == day


def _planned_recently(
    planned: list[tuple[date, str]], template_id: str, day: date, days: int
) -> bool:
    for planned_day, planned_id in planned:
        if planned_id != template_id:
            continue
        elapsed = (day - planned_day).days
        if 0 < elapsed <= days:
            return True
    return False


def _planned_same_week(
    planned: list[tuple[date, str]], template_id: str, day: date
) -> bool:
    week = day.isocalendar()[:2]
    for planned_day, planned_id in planned:
        if planned_id == template_id and planned_day.isocalendar()[:2] == week:
            return True
    return False


def _copy_ledger(ledger: Ledger) -> Ledger:
    scratch = Ledger()
    for entry in ledger.entries:
        scratch.record(
            {
                "family": entry["capacity"],
                "reason_codes": list(entry["reason_codes"]),
                "date": entry["date"],
                "source": entry["source"],
                "ontology_version": entry["ontology_version"],
            }
        )
    return scratch


def _rule_by_id(rules: list[dict], rule_id: str) -> dict:
    for rule in rules:
        if rule["id"] == rule_id:
            return rule
    raise ValueError(f"missing rule {rule_id}")


def _in_paper_order(codes: list[str], rules: dict) -> list[str]:
    order = [rule["id"] for rule in rules["absolute"]]
    order.extend(rule["id"] for rule in rules["preference"])
    present = set(codes)
    return [code for code in order if code in present]


def _expect_ids(rules: list[dict], expected: tuple[str, ...], paper: Path) -> None:
    found = [rule.get("id") for rule in rules]
    if tuple(found) != expected:
        raise ValueError(f"{paper} rules are {found}, expected {list(expected)}")
    for rule in rules:
        if "rule" not in rule or not str(rule["rule"]).strip():
            raise ValueError(f"{paper} rule {rule.get('id')} has no text")


def _store_field(current: dict, text: str, paper: Path, line_number: int) -> None:
    key, value = _split_field(text, paper, line_number)
    current[key] = value


def _split_field(text: str, paper: Path, line_number: int) -> tuple[str, str]:
    if ":" not in text:
        raise ValueError(f"{paper} line {line_number}: expected key: value")
    key, value = text.split(":", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"{paper} line {line_number}: missing key")
    return key, _unquote(value.strip())


def _load_template(path: Path) -> dict:
    template: dict[str, str] = {}
    text = path.read_text(encoding="utf-8")
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        key, value = _split_field(raw.strip(), path, line_number)
        if key in template:
            raise ValueError(f"{path} line {line_number}: duplicate {key}")
        template[key] = value
    missing = [key for key in PARAMETER_KEYS if key not in template]
    if missing:
        raise ValueError(f"{path} is missing {', '.join(missing)}")
    return {key: template[key] for key in PARAMETER_KEYS}


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _span(text: str) -> tuple[int, int]:
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


def show_fixture_prescriptions(on: date | None = None) -> None:
    """Print template ids and reason codes for the four fixture ledgers.

    Each fixture is its own ledger, recorded the day before `on`.
    """
    start = date.today() if on is None else _as_date(on)
    recorded = start - timedelta(days=1)
    names = ("easy.yml", "race_800.yml", "se_400.yml", "vo2_800.yml")
    print(
        f"as of {start.isoformat()}, fixture recorded {recorded.isoformat()}"
    )
    for name in names:
        ledger = Ledger()
        before = len(ledger.entries)
        ledger.record_fixture(FIXTURES_DIR / name, recorded)
        result = prescribe(ledger, start)
        if len(ledger.entries) != before + 1:
            raise ValueError("prescribe changed the fixture ledger")
        ids = [row["template_id"] for row in result["rows"]]
        print(f"{Path(name).stem}: {ids} {result['reason_codes']}")
        for row in result["rows"]:
            print(
                f"  {row['prescribed_on']} {row['template_id']} {row['reason_codes']}"
            )


if __name__ == "__main__":
    show_fixture_prescriptions()
