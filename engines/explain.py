# explain.py — prose for a stored classification, a prescription, and a decision. No scores.

"""Paragraphs only. This file is the only place a model is allowed.

A prescription paragraph copies the template id prescribe() already chose.
A decision paragraph copies the template id and the reason codes already
stored on a planned row. Neither decodes an id into reps, rest, or distances.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

WORD_LIMIT = 60

# Recorded spend stops here. $25, in microdollars.
SPEND_CAP_MICRO_USD = 25_000_000

# Used when price env vars are unset. High on purpose: recorded spend reaches
# $25 before a typical model's invoice does. Set the env vars if the real
# price is higher.
DEFAULT_INPUT_USD_PER_MILLION = 150.0
DEFAULT_OUTPUT_USD_PER_MILLION = 600.0

# The four fields in rio/v0.1/goal.yml. Unknown stays the word that is written.
GOAL_FIELDS = (
    "current_mark",
    "target_time",
    "target_date",
    "limiting_capacities",
)

# Plain words for reason codes. The paragraph may not add physiology past these.
REASON_TEXT = {
    "no_pattern": "no pattern matched",
    "rest_missing": "rest is missing",
    "conflicting_rules": "two rules fired",
    "work_60_150m": "most of the work steps are 60–150 m",
    "rest_gt_2min": "rest is longer than 2 minutes",
    "work_200_300m": "the work steps are 200–300 m",
    "work_300_500m": "the work steps are 300–500 m",
    "work_600_1000m": "the work steps are 600–1000 m",
    "rest_60_120s": "rest is 60–120 seconds",
    "pace_near_goal_800": "the pace is near goal 800 pace",
    "pace_strong_slower_than_goal_800": "the pace is strong but slower than goal 800 pace",
    "continuous_easy": "it is one continuous easy run",
    "talkable": "it could be done while talking",
    "single_800m": "it is a single 800 m",
    "race_effort": "it is a race effort",
}

FAMILY_TEXT = {
    "speed_endurance": "speed endurance",
    "anaerobic_capacity": "anaerobic capacity",
    "aerobic_power": "aerobic power",
    "race_readiness": "race readiness",
    "max_velocity": "max velocity",
    "threshold": "threshold",
    "aerobic": "aerobic",
    "speed": "speed",
    "unsure": "unsure",
}

# Snippets a rephrase has to keep. Digits match on their own, not inside 200 or 120.
REASON_MARKS = {
    "no_pattern": ("pattern",),
    "rest_missing": ("rest", "missing"),
    "conflicting_rules": ("two", "rules"),
    "work_60_150m": ("60", "150"),
    "rest_gt_2min": ("2", "minute"),
    "work_200_300m": ("200", "300"),
    "work_300_500m": ("300", "500"),
    "work_600_1000m": ("600", "1000"),
    "rest_60_120s": ("60", "120"),
    "pace_near_goal_800": ("near", "800"),
    "pace_strong_slower_than_goal_800": ("strong", "slower", "800"),
    "continuous_easy": ("continuous", "easy"),
    "talkable": ("talk",),
    "single_800m": ("800",),
    "race_effort": ("race",),
}

# A rephrase may not introduce these. They are not in the reason codes.
BANNED = (
    "you should",
    "try to",
    "recommend",
    "lactate",
    "vo2",
    "mitochondri",
    "glycogen",
    "heart rate",
    "neuromuscular",
)

PROMPT = """Rephrase the paragraph below in one paragraph under 60 words.
Keep the same family and every reason code.
Do not add training advice.
Do not add physiology that was not already in the paragraph.
Do not change or suggest a different family.
If the paragraph says the rules were unsure, keep that.
Cheesy is allowed. A wrong family is not.
Return the paragraph only.

"""

# Plain words for prescription reason codes. No reps, rest, or distances.
PRESCRIPTION_REASON_TEXT = {
    "no_quality_after_high_recovery": "no quality the day after a high recovery cost",
    "no_second_hard_day": "no second hard day",
    "no_back_to_back_speed_endurance": "no speed endurance on the next day",
    "closed_menu_only": "only a template already on the menu",
    "prefer_gap": "it trains a limiting capacity that is low or decaying",
    "prefer_variety": "it is a capacity not deposited in the last three days",
}

PRESCRIPTION_REASON_MARKS = {
    "no_quality_after_high_recovery": ("quality", "high", "recovery"),
    "no_second_hard_day": ("second", "hard"),
    "no_back_to_back_speed_endurance": ("speed endurance", "next day"),
    "closed_menu_only": ("template", "menu"),
    "prefer_gap": ("limiting", "low", "decaying"),
    "prefer_variety": ("capacity", "three"),
}

PRESCRIPTION_PROMPT = """Rephrase the paragraph below in one paragraph under 60 words.
Keep the same template id. Do not name a different template id.
Do not add reps, distances, rest, or any interval math.
Do not add numbers that are not already in the paragraph.
Keep every reason and every goal field already in the paragraph.
Do not add training advice.
Cheesy is allowed. A different template id is not.
Return the paragraph only.

"""

DECISION_PROMPT = """Rephrase the paragraph below in one paragraph under 60 words.
Keep the same template id. Do not name a different template id.
Do not add reps, distances, rest, or any interval math.
Do not add numbers that are not already in the paragraph.
Keep every reason already in the paragraph.
Do not add a goal, a date, parameters, or training advice.
Do not invent intervals, distances, or structure.
Cheesy is allowed. A different template id is not.
Return the paragraph only.

"""

# Workout words a prescription paragraph may not add. They are not in the inputs.
STRUCTURE_WORDS = (
    "rep",
    "reps",
    "repeat",
    "repeats",
    "interval",
    "intervals",
    "meter",
    "meters",
    "metre",
    "metres",
    "kilometer",
    "kilometers",
    "mile",
    "miles",
    "rest",
    "pace",
    "split",
    "splits",
    "jog",
    "stride",
    "strides",
    "lap",
    "laps",
    "seconds",
    "minute",
    "minutes",
)

_ID_TOKEN = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
_INTERVAL_MATH = re.compile(r"\d\s*[x×]\s*\d")


def explain(classification: dict) -> str:
    """Return one paragraph naming the family and the reason codes."""
    family = str(classification["family"]).strip()
    reason_codes = [
        str(code).strip()
        for code in classification["reason_codes"]
        if str(code).strip()
    ]
    if "confidence" not in classification:
        raise ValueError("confidence is missing")
    if not family:
        raise ValueError("family is empty")

    paragraph = _restatement(family, reason_codes)
    if not _acceptable(paragraph, family, reason_codes):
        raise ValueError("explanation broke its own rules")

    rephrased = _rephrase(paragraph, family, reason_codes)
    if rephrased is None:
        return paragraph
    return rephrased


def explain_prescription(template_id: str, reason_codes: list[str], goal: dict) -> str:
    """Return one paragraph for a prescribe() row.

    The template id, the reason codes, and the goal are already chosen.
    A rephrase that names a different id is dropped. The chosen id stays.
    """
    if isinstance(reason_codes, (str, bytes)) or not isinstance(reason_codes, (list, tuple)):
        raise ValueError("reason_codes must be a list")
    chosen = str(template_id).strip()
    codes = [str(code).strip() for code in reason_codes if str(code).strip()]
    fields = _goal_fields(goal)
    if not chosen:
        raise ValueError("template_id is empty")

    paragraph = _prescription_restatement(chosen, codes, fields)
    allowed_families = _mentioned_families(paragraph)
    if not _prescription_acceptable(paragraph, chosen, codes, fields, allowed_families):
        raise ValueError("explanation broke its own rules")

    rephrased = _rephrase_prescription(
        paragraph, chosen, codes, fields, allowed_families
    )
    if rephrased is None:
        return paragraph
    return rephrased


def explain_decision(template_id: str, reason_codes: list[str]) -> str:
    """Return one paragraph for a planned row on the Decisions page.

    The template id and the reason codes are already stored. Nothing else
    is read. A rephrase that names a different id, or that adds intervals,
    distances, or structure, is dropped. The stored id stays.
    """
    if isinstance(reason_codes, (str, bytes)) or not isinstance(reason_codes, (list, tuple)):
        raise ValueError("reason_codes must be a list")
    chosen = str(template_id).strip()
    codes = [str(code).strip() for code in reason_codes if str(code).strip()]
    if not chosen:
        raise ValueError("template_id is empty")

    paragraph = _decision_restatement(chosen, codes)
    allowed_families = _mentioned_families(paragraph)
    if not _decision_acceptable(paragraph, chosen, codes, allowed_families):
        raise ValueError("explanation broke its own rules")

    rephrased = _rephrase_decision(paragraph, chosen, codes, allowed_families)
    if rephrased is None:
        return paragraph
    return rephrased


def _plain_family(family: str) -> str:
    return FAMILY_TEXT.get(family, family.replace("_", " "))


def _plain_code(code: str) -> str:
    return REASON_TEXT.get(code, code.replace("_", " "))


def _restatement(family: str, reason_codes: list[str]) -> str:
    reasons = _reasons_sentence(reason_codes)
    if family == "unsure":
        lead = "The rules were unsure."
    else:
        lead = f"The rules called this {_plain_family(family)}."
    if not reasons:
        return lead
    return f"{lead} {reasons}"


def _reasons_sentence(reason_codes: list[str]) -> str:
    parts = [_plain_code(code) for code in reason_codes]
    if not parts:
        return ""
    if len(parts) == 1:
        body = parts[0]
    elif len(parts) == 2:
        body = f"{parts[0]} and {parts[1]}"
    else:
        body = ", ".join(parts[:-1]) + ", and " + parts[-1]
    return body[0].upper() + body[1:] + "."


def _rephrase(paragraph: str, family: str, reason_codes: list[str]) -> str | None:
    try:
        text = _complete(paragraph)
    except (
        OSError,
        urllib.error.URLError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
        TypeError,
    ):
        return None
    if text is None or not _acceptable(text, family, reason_codes):
        return None
    return text


def _rephrase_prescription(
    paragraph: str,
    template_id: str,
    reason_codes: list[str],
    goal: dict[str, str],
    allowed_families: set[str],
) -> str | None:
    try:
        text = _complete(paragraph, PRESCRIPTION_PROMPT)
    except (
        OSError,
        urllib.error.URLError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
        TypeError,
    ):
        return None
    if text is None or not _prescription_acceptable(
        text, template_id, reason_codes, goal, allowed_families
    ):
        return None
    return text


def _rephrase_decision(
    paragraph: str,
    template_id: str,
    reason_codes: list[str],
    allowed_families: set[str],
) -> str | None:
    try:
        text = _complete(paragraph, DECISION_PROMPT)
    except (
        OSError,
        urllib.error.URLError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
        TypeError,
    ):
        return None
    if text is None or not _decision_acceptable(
        text, template_id, reason_codes, allowed_families
    ):
        return None
    return text


def _complete(paragraph: str, prompt: str = PROMPT) -> str | None:
    """Ask the model to rephrase a restatement. None when it is not configured.

    Set RIO_EXPLAIN_API_KEY, RIO_EXPLAIN_MODEL, and RIO_EXPLAIN_BASE_URL.
    The base URL is the https API root, such as https://api.openai.com/v1.
    Calls stop once recorded spend reaches $25. Prices are USD per million
    tokens: RIO_EXPLAIN_INPUT_USD_PER_MILLION and
    RIO_EXPLAIN_OUTPUT_USD_PER_MILLION. When those are unset, $150 and $600
    are used so the record hits $25 before a typical invoice does.
    """
    key = os.environ.get("RIO_EXPLAIN_API_KEY", "").strip()
    model = os.environ.get("RIO_EXPLAIN_MODEL", "").strip()
    base = os.environ.get("RIO_EXPLAIN_BASE_URL", "").strip().rstrip("/")
    if (
        not key
        or not model
        or not base.startswith("https://")
        or any(char.isspace() for char in base)
    ):
        return None

    prices = _token_prices()
    if prices is None:
        return None
    price_in, price_out = prices
    message = prompt + paragraph
    worst = _worst_micro(message, price_in, price_out)
    if not _reserve_spend(worst):
        return None

    body = json.dumps(
        {
            "model": model,
            "temperature": 0.5,
            "max_tokens": 160,
            "messages": [{"role": "user", "content": message}],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        base + "/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError, OSError):
        _settle_spend(worst, 0)
        raise

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        _settle_spend(worst, worst)
        raise
    actual = _usage_micro(payload, price_in, price_out)
    _settle_spend(worst, worst if actual is None else actual)
    content = payload["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        return None
    text = content.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return text or None


def _acceptable(text: str, family: str, reason_codes: list[str]) -> bool:
    if not text or "\n" in text:
        return False
    if _word_count(text) > WORD_LIMIT:
        return False
    lowered = text.lower()
    if _plain_family(family).lower() not in lowered:
        return False
    if family == "unsure" and "the rules were unsure" not in lowered:
        return False
    if _mentioned_families(text) - {family}:
        return False
    for code in reason_codes:
        marks = REASON_MARKS.get(code, (_plain_code(code).lower(),))
        for mark in marks:
            if not _has_mark(lowered, mark.lower()):
                return False
    for banned in BANNED:
        if banned in lowered:
            return False
    return True


def _mentioned_families(paragraph: str) -> set[str]:
    """Family names in the paragraph. Longer names are taken first."""
    masked = paragraph.lower()
    found: set[str] = set()
    labels = sorted(FAMILY_TEXT.items(), key=lambda item: len(item[1]), reverse=True)
    for key, label in labels:
        needle = label.lower()
        if needle in masked:
            found.add(key)
            masked = masked.replace(needle, " ")
    return found


def _has_mark(text: str, mark: str) -> bool:
    if mark.isdigit():
        return re.search(r"(?<!\d)" + re.escape(mark) + r"(?!\d)", text) is not None
    return mark in text


def _word_count(text: str) -> int:
    return len(text.split())


def _plain_prescription_code(code: str) -> str:
    return PRESCRIPTION_REASON_TEXT.get(code, code.replace("_", " "))


def _decision_restatement(template_id: str, reason_codes: list[str]) -> str:
    parts = [_plain_prescription_code(code) for code in reason_codes]
    lead = f"The rules chose {template_id}."
    reasons = _join_clauses(parts)
    if not reasons:
        return lead
    return f"{lead} {reasons}"


def _decision_acceptable(
    text: str,
    template_id: str,
    reason_codes: list[str],
    allowed_families: set[str],
) -> bool:
    """Same guards as a prescription. A decision has no goal fields to copy."""
    return _prescription_acceptable(text, template_id, reason_codes, {}, allowed_families)


def _prescription_restatement(
    template_id: str, reason_codes: list[str], goal: dict[str, str]
) -> str:
    parts = [_plain_prescription_code(code) for code in reason_codes]
    lead = f"The rules chose {template_id}."
    reasons = _join_clauses(parts)
    chunks = [lead]
    if reasons:
        chunks.append(reasons)
    chunks.append(_goal_sentence(goal))
    return " ".join(chunks)


def _join_clauses(parts: list[str]) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        body = parts[0]
    elif len(parts) == 2:
        body = f"{parts[0]} and {parts[1]}"
    else:
        body = ", ".join(parts[:-1]) + ", and " + parts[-1]
    return body[0].upper() + body[1:] + "."


def _goal_fields(goal: dict) -> dict[str, str]:
    if not isinstance(goal, dict):
        raise ValueError("goal is missing")
    values: dict[str, str] = {}
    for key in GOAL_FIELDS:
        if key not in goal or goal[key] is None:
            raise ValueError(f"{key} is missing")
        values[key] = _field_text(goal[key])
    return values


def _field_text(value: object) -> str:
    if isinstance(value, (list, tuple)):
        bits = [str(item).strip() for item in value if str(item).strip()]
        if not bits:
            raise ValueError("goal field is empty")
        return ", ".join(bits)
    text = str(value).strip()
    if not text:
        raise ValueError("goal field is empty")
    return text


def _goal_sentence(goal: dict[str, str]) -> str:
    return (
        f"The current mark is {goal['current_mark']}. "
        f"The target time is {goal['target_time']}. "
        f"The target date is {goal['target_date']}. "
        f"Limiting capacities are {goal['limiting_capacities']}."
    )


def _prescription_acceptable(
    text: str,
    template_id: str,
    reason_codes: list[str],
    goal: dict[str, str],
    allowed_families: set[str],
) -> bool:
    if not text or "\n" in text:
        return False
    if _word_count(text) > WORD_LIMIT:
        return False
    if template_id not in text:
        return False
    allowed_ids = {template_id.lower()}
    for code in reason_codes:
        allowed_ids.add(code.lower())
    for value in goal.values():
        allowed_ids.update(_id_tokens(value))
    if _id_tokens(text) - allowed_ids:
        return False
    if _new_digits(text, template_id, reason_codes, goal):
        return False
    if _INTERVAL_MATH.search(text) is not None:
        return False
    lowered = text.lower()
    for word in STRUCTURE_WORDS:
        if re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", lowered):
            return False
    for banned in BANNED:
        if banned in lowered:
            return False
    if _mentioned_families(text) - allowed_families:
        return False
    for code in reason_codes:
        marks = PRESCRIPTION_REASON_MARKS.get(code, (_plain_prescription_code(code).lower(),))
        for mark in marks:
            if not _has_mark(lowered, mark.lower()):
                return False
    for value in goal.values():
        if any(char.isdigit() for char in value):
            if value not in text:
                return False
        elif value.lower() not in lowered:
            return False
    return True


def _id_tokens(text: str) -> set[str]:
    return set(_ID_TOKEN.findall(text.lower()))


def _new_digits(
    text: str, template_id: str, reason_codes: list[str], goal: dict[str, str]
) -> bool:
    """Digits left after the id, the reason codes, and the goal values are removed."""
    stripped = text
    for token in (template_id, *reason_codes, *goal.values()):
        if token:
            stripped = stripped.replace(token, " ")
    return re.search(r"\d", stripped) is not None


def _token_prices() -> tuple[float, float] | None:
    price_in = _usd_per_million(
        "RIO_EXPLAIN_INPUT_USD_PER_MILLION",
        DEFAULT_INPUT_USD_PER_MILLION,
    )
    price_out = _usd_per_million(
        "RIO_EXPLAIN_OUTPUT_USD_PER_MILLION",
        DEFAULT_OUTPUT_USD_PER_MILLION,
    )
    if price_in is None or price_out is None:
        return None
    return price_in, price_out


def _usd_per_million(name: str, default: float) -> float | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return None
    if value < 0:
        return None
    return value


def _micro(prompt_tokens: int, completion_tokens: int, price_in: float, price_out: float) -> int:
    # Prices are USD per million tokens. Microdollars = tokens x that price.
    cost = prompt_tokens * price_in + completion_tokens * price_out
    return int(round(cost))


def _worst_micro(message: str, price_in: float, price_out: float) -> int:
    input_tokens = max(len(message) // 2, 1)
    return _micro(input_tokens, 160, price_in, price_out)


def _usage_micro(payload: dict, price_in: float, price_out: float) -> int | None:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    priced = _micro_from_tokens(usage, price_in, price_out)
    reported = usage.get("cost")
    if isinstance(reported, bool) or not isinstance(reported, (int, float)):
        return priced
    if reported < 0:
        return priced
    reported_micro = int(round(float(reported) * 1_000_000))
    if priced is None:
        return reported_micro
    return max(priced, reported_micro)


def _micro_from_tokens(usage: dict, price_in: float, price_out: float) -> int | None:
    try:
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
    except (TypeError, ValueError):
        return None
    if prompt_tokens < 0 or completion_tokens < 0:
        return None
    if prompt_tokens == 0 and completion_tokens == 0:
        return None
    return _micro(prompt_tokens, completion_tokens, price_in, price_out)


def _spend_path() -> Path:
    override = os.environ.get("RIO_EXPLAIN_SPEND_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "data" / "explain_spend.json"


def _read_spend(path: Path) -> int | None:
    """Recorded microdollars. None when the record cannot be trusted."""
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = payload["micro_usd"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _write_spend(path: Path, micro: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps({"micro_usd": int(micro)}),
        encoding="utf-8",
    )
    temporary.replace(path)


def _reserve_spend(worst: int) -> bool:
    """Hold worst-case cost before a call. False when the $25 cap would break."""
    if worst < 0:
        return False
    path = _spend_path()
    spent = _read_spend(path)
    if spent is None or spent >= SPEND_CAP_MICRO_USD:
        return False
    if worst == 0:
        return True
    if spent + worst > SPEND_CAP_MICRO_USD:
        return False
    try:
        _write_spend(path, spent + worst)
    except OSError:
        return False
    return True


def _settle_spend(reserved: int, actual: int) -> None:
    """Replace a reservation with the cost of the call that just finished."""
    if actual < 0:
        actual = reserved
    path = _spend_path()
    spent = _read_spend(path)
    if spent is None:
        return
    updated = spent - reserved + actual
    if updated < 0:
        updated = 0
    try:
        _write_spend(path, updated)
    except OSError:
        return
