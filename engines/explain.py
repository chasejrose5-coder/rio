# explain.py — prose for a stored classification. No scores.

"""One paragraph from a classify() result. This file is the only place a model is allowed."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

WORD_LIMIT = 60

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


def _complete(paragraph: str) -> str | None:
    """Ask the model to rephrase a restatement. None when it is not configured.

    Set RIO_EXPLAIN_API_KEY, RIO_EXPLAIN_MODEL, and RIO_EXPLAIN_BASE_URL.
    The base URL is the https API root, such as https://api.openai.com/v1.
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

    body = json.dumps(
        {
            "model": model,
            "temperature": 0.5,
            "max_tokens": 160,
            "messages": [{"role": "user", "content": PROMPT + paragraph}],
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
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
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
