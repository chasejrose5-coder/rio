# result.py — quality-day result to on_track, not_hitting, or smashing.

"""One entered result, compared with the session target.

Rep times, a single average, or one distance are pace or distance.
Within 3% is on track. Slower or shorter than that is not hitting.
Faster or longer than that is smashing. Empty and unreadable input
is ignored. No score.
"""

from __future__ import annotations

import re

_BAND = 0.03
# Float noise on an exact 3% line stays inside the band.
_BAND_SLACK = 1e-9
_REP = re.compile(r"_(\d+)_r\d+_x(\d+)$")
_GOAL = re.compile(r"^(\d+):(\d{2}(?:\.\d+)?)$")
_TOKEN = re.compile(
    r"(\d+):(\d{2}(?:\.\d+)?)(?:\s*(?:seconds|second|secs|sec|s)\b)?"
    r"|(\d+(?:\.\d+)?)\s*(kilometers|kilometer|km|meters|meter|m|seconds|second|secs|sec|s)\b"
    r"|(\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)
_GAP = re.compile(
    r"^(?:[\s,;/]+|(?:in|at|for|avg|average|rep|reps|time|times|pace|of|the|a|an|on|and|x)\b\s*)*$",
    re.IGNORECASE,
)
_COUNT_GAP = re.compile(r"^[\s,;]*x[\s,;]*$", re.IGNORECASE)


def goal_seconds(mark: object) -> float | None:
    """Seconds in an 800 time such as 1:55.0. Anything else is unusable."""
    if not isinstance(mark, str):
        return None
    found = _GOAL.fullmatch(mark.strip())
    if found is None:
        return None
    seconds = int(found.group(1)) * 60 + float(found.group(2))
    if seconds <= 0:
        return None
    return seconds


def _rep_match(template_id: object) -> re.Match | None:
    if not isinstance(template_id, str):
        return None
    return _REP.search(template_id.strip())


def rep_meters(template_id: object) -> int | None:
    """Rep length written in a frozen id. The rep count is not the target."""
    found = _rep_match(template_id)
    if found is None:
        return None
    meters = int(found.group(1))
    if meters <= 0:
        return None
    return meters


def rep_count(template_id: object) -> int | None:
    """Reps named by a frozen id. One is a single continuous effort."""
    found = _rep_match(template_id)
    if found is None:
        return None
    count = int(found.group(2))
    if count <= 0:
        return None
    return count


def result_box_count(template_id: object) -> int:
    """One box per rep. Continuous work, and an id with no count, stay one."""
    count = rep_count(template_id)
    if count is None or count < 2:
        return 1
    return count


def filled_times(values: object) -> str:
    """Times that were entered, in order. Empty boxes are left out."""
    if not isinstance(values, (list, tuple)):
        return ""
    parts = []
    for value in values:
        token = _time_token(value)
        if token is not None:
            parts.append(token)
    return ", ".join(parts)


def _time_token(value: object) -> str | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = round(float(value), 2)
    if number <= 0:
        return None
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def parse_result(text: object) -> dict | None:
    """Times, one distance, or one distance with times. None if unreadable."""
    if not isinstance(text, str):
        return None
    raw = text.strip()
    if not raw:
        return None
    pieces: list[dict] = []
    cursor = 0
    for match in _TOKEN.finditer(raw):
        gap = raw[cursor:match.start()]
        if not _GAP.fullmatch(gap):
            return None
        cursor = match.end()
        piece = _piece(match)
        if piece is None:
            return None
        piece["gap"] = gap
        pieces.append(piece)
    if not _GAP.fullmatch(raw[cursor:]):
        return None
    if (
        len(pieces) > 1
        and pieces[0]["unit"] == ""
        and isinstance(pieces[0]["value"], int)
        and _COUNT_GAP.fullmatch(pieces[1]["gap"])
    ):
        pieces = pieces[1:]
    if not pieces:
        return None
    distances = [piece for piece in pieces if piece["kind"] == "distance"]
    times = [piece for piece in pieces if piece["kind"] == "time"]
    if len(distances) > 1 or (not distances and not times):
        return None
    numbers = [piece["value"] for piece in pieces]
    if distances and not times:
        return {
            "kind": "distance",
            "numbers": numbers,
            "distance": distances[0]["value"],
            "times": [],
        }
    if times and not distances:
        return {
            "kind": "pace",
            "numbers": numbers,
            "distance": None,
            "times": [piece["value"] for piece in times],
        }
    return {
        "kind": "pace_at",
        "numbers": numbers,
        "distance": distances[0]["value"],
        "times": [piece["value"] for piece in times],
    }


def judge(template_id: object, text: object, goal: float | None) -> dict | None:
    """Map one result onto a mark. None means empty or invalid, so ignore it.

    Times use goal 800 pace over the rep, or over the distance they wrote.
    A distance alone uses the rep length from the template id.
    """
    parsed = parse_result(text)
    if parsed is None:
        return None
    rep = rep_meters(template_id)
    if rep is None:
        return None
    if parsed["kind"] == "distance":
        mark = _against(
            float(parsed["distance"]),
            float(rep),
            high="smashing",
            low="not_hitting",
        )
    else:
        if goal is None or goal <= 0:
            return None
        distance = rep if parsed["distance"] is None else float(parsed["distance"])
        if distance <= 0:
            return None
        target = goal / 800 * distance
        actual = sum(float(item) for item in parsed["times"]) / len(parsed["times"])
        mark = _against(actual, target, high="not_hitting", low="smashing")
    if mark is None:
        return None
    return {"numbers": list(parsed["numbers"]), "mark": mark}


def _against(actual: float, target: float, *, high: str, low: str) -> str | None:
    """More than 3% above or below the target. The 3% line itself stays on track."""
    if actual <= 0 or target <= 0:
        return None
    change = (actual - target) / target
    if change > _BAND + _BAND_SLACK:
        return high
    if change < -(_BAND + _BAND_SLACK):
        return low
    return "on_track"


def _piece(match: re.Match) -> dict | None:
    if match.group(1) is not None:
        value = int(match.group(1)) * 60 + float(match.group(2))
        kind = "time"
        unit = "s"
    elif match.group(3) is not None:
        value = float(match.group(3))
        unit_name = match.group(4).lower()
        if unit_name in ("km", "kilometer", "kilometers"):
            value *= 1000
            kind = "distance"
        elif unit_name in ("m", "meter", "meters"):
            kind = "distance"
        else:
            kind = "time"
        unit = "m" if kind == "distance" else "s"
    else:
        value = float(match.group(5))
        kind = "time"
        unit = ""
    if value <= 0:
        return None
    return {"kind": kind, "value": _whole(value), "unit": unit}


def _whole(value: float) -> float | int:
    if value.is_integer():
        return int(value)
    return value
