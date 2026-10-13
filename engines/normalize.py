# normalize.py — canonical laps from an adapter payload. No labels.

"""Turn an adapter payload into work laps. Classification labels are dropped."""

from __future__ import annotations

import math
import re

# Keys that would tell a classifier the answer. Never copied onto a lap.
LABEL_KEYS = {
    "expected_family",
    "family",
    "label",
    "labels",
    "classification",
    "primary_stimulus",
    "secondary_stimulus",
    "ontology_version",
}

LAP_LIST_KEYS = ("laps", "intervals", "steps", "workout_steps")

REST_ROLES = {
    "rest",
    "recovery",
    "recover",
    "interval_rest",
    "recovery_interval",
}
SKIP_ROLES = {
    "warmup",
    "warm-up",
    "warm_up",
    "cooldown",
    "cool-down",
    "cool_down",
}

_MISSING = {"", "none", "null", "missing", "nan"}
_DISTANCE = re.compile(
    r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*"
    r"(mi|mile|miles|km|kilometer|kilometers|m|meter|meters)?$",
    re.IGNORECASE,
)
_PACE = re.compile(
    r"^(\d+):(\d+(?:\.\d+)?)\s*(?:/|per)\s*(km|mi|mile|miles)$",
    re.IGNORECASE,
)


def normalize(payload: dict | list) -> dict[str, list]:
    """Return {"laps": [...]} with only distance_m, seconds, and rest_s.

    A missing rest stays None. Zero is a real rest value, not a missing one.
    """
    if isinstance(payload, list):
        return {"laps": _finish(_work_laps(payload))}
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict or a list of laps")

    activity_distance = _first_distance(payload)
    activity_seconds = _first_seconds(payload)
    activity_rest = _first_rest(payload)
    activity_pace = _pace_value(payload)

    for key in LAP_LIST_KEYS:
        laps_value = payload.get(key)
        if isinstance(laps_value, list):
            laps = _work_laps(laps_value)
            _fill_single_lap(laps, activity_distance, activity_seconds, activity_rest)
            _apply_activity_pace(laps, activity_pace)
            return {"laps": _finish(laps)}

    if "laps" in payload and not isinstance(payload.get("laps"), list):
        return {"laps": _finish(_expand_repeated(payload))}

    if (
        activity_distance is not None
        or activity_seconds is not None
        or activity_pace is not None
    ):
        lap = _canonical_lap(payload)
        _fill_single_lap([lap], activity_distance, activity_seconds, activity_rest)
        _apply_activity_pace([lap], activity_pace)
        return {"laps": _finish([lap])}

    return {"laps": []}


def _expand_repeated(payload: dict) -> list[dict]:
    count = _parse_count(payload.get("laps"))
    if count < 1:
        raise ValueError("laps must be at least 1")
    lap = _canonical_lap(payload)
    return [dict(lap) for _ in range(count)]


def _work_laps(raw_laps: list) -> list[dict]:
    work: list[dict] = []
    for raw in raw_laps:
        if not isinstance(raw, dict):
            raise TypeError("each lap must be a dict")
        role = _role(raw)
        if role in SKIP_ROLES:
            continue
        if role in REST_ROLES or _is_zero_distance_rest(raw, work):
            _attach_rest(work, raw)
            continue
        work.append(_canonical_lap(raw))
    return work


def _fill_single_lap(
    laps: list[dict],
    distance_m: float | None,
    seconds: float | None,
    rest_s: float | None,
) -> None:
    """Use activity-level fields only when the single lap left them blank."""
    if len(laps) != 1:
        return
    lap = laps[0]
    if lap["distance_m"] is None:
        lap["distance_m"] = distance_m
    if lap["seconds"] is None:
        lap["seconds"] = seconds
    if lap["rest_s"] is None:
        lap["rest_s"] = rest_s


def _canonical_lap(raw: dict) -> dict:
    return {
        "distance_m": _first_distance(raw),
        "seconds": _first_seconds(raw),
        "rest_s": _first_rest(raw),
        "_pace": _pace_value(raw),
        "_speed": _optional_speed(raw),
    }


def _attach_rest(work: list[dict], raw: dict) -> None:
    if not work:
        return
    if work[-1]["rest_s"] is not None:
        return
    seconds = _first_seconds(raw)
    if seconds is None:
        seconds = _first_rest(raw)
    work[-1]["rest_s"] = seconds


def _is_zero_distance_rest(raw: dict, work: list[dict]) -> bool:
    if not work:
        return False
    distance = _first_distance(raw)
    return distance == 0


def _role(raw: dict) -> str:
    for key in ("type", "kind", "role", "step_type", "interval_type"):
        value = raw.get(key)
        if value is None or key in LABEL_KEYS:
            continue
        return str(value).strip().lower().replace(" ", "_")
    return ""


def _first_distance(raw: dict) -> float | None:
    return _first_parsed(raw, ("distance_m", "distance", "lap_distance"), _parse_distance_m)


def _first_seconds(raw: dict) -> float | None:
    return _first_parsed(
        raw,
        ("seconds", "elapsed_s", "elapsed_time", "moving_time"),
        _parse_seconds,
    )


def _optional_speed(raw: dict) -> float | None:
    for key in ("average_speed", "avg_speed"):
        if key not in raw or key in LABEL_KEYS:
            continue
        try:
            return _parse_seconds(raw.get(key))
        except ValueError:
            return None
    return None


def _first_rest(raw: dict) -> float | None:
    return _first_parsed(
        raw,
        ("rest_s", "rest", "rest_seconds", "recovery_s", "rest_duration"),
        _parse_seconds,
    )


def _apply_activity_pace(laps: list[dict], pace: object) -> None:
    if len(laps) != 1 or pace is None:
        return
    if laps[0].get("_pace") is None:
        laps[0]["_pace"] = pace


def _finish(laps: list[dict]) -> list[dict]:
    """Drop adapter fields. Pace becomes seconds once distance is known."""
    finished: list[dict] = []
    for lap in laps:
        pace = lap.get("_pace")
        seconds = lap.get("seconds")
        distance_m = lap.get("distance_m")
        speed = lap.get("_speed")
        if (
            seconds is None
            and distance_m is not None
            and distance_m > 0
            and speed is not None
            and speed > 0
        ):
            seconds = distance_m / speed
        if seconds is None and pace is not None:
            seconds = _seconds_from_pace(pace, distance_m)
        finished.append(
            {
                "distance_m": distance_m,
                "seconds": seconds,
                "rest_s": lap.get("rest_s"),
            }
        )
    return finished


def _pace_value(raw: dict) -> object:
    for key in ("pace", "avg_pace", "average_pace"):
        if key not in raw or key in LABEL_KEYS:
            continue
        value = raw.get(key)
        if not _is_blank(value):
            return value
    return None


def _first_parsed(raw: dict, keys: tuple[str, ...], parser) -> float | None:
    for key in keys:
        if key not in raw or key in LABEL_KEYS:
            continue
        return parser(raw.get(key))
    return None


def _parse_count(value: object) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"laps is not a count: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or not value.is_integer():
            raise ValueError(f"laps is not a count: {value!r}")
        return int(value)
    text = _clean_text(value)
    if text is None or not re.fullmatch(r"\d+", text):
        raise ValueError(f"laps is not a count: {value!r}")
    return int(text)


def _parse_distance_m(value: object) -> float | None:
    if _is_blank(value):
        return None
    if isinstance(value, bool):
        raise ValueError(f"distance is not a number: {value!r}")
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = _clean_text(value)
    if text is None:
        return None
    match = _DISTANCE.match(text)
    if not match:
        raise ValueError(f"distance is not a number: {value!r}")
    amount = float(match.group(1))
    unit = (match.group(2) or "m").lower()
    if unit in {"mi", "mile", "miles"}:
        return amount * 1609.344
    if unit in {"km", "kilometer", "kilometers"}:
        return amount * 1000.0
    return amount


def _parse_seconds(value: object) -> float | None:
    if _is_blank(value):
        return None
    if isinstance(value, bool):
        raise ValueError(f"time is not a number: {value!r}")
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = _clean_text(value)
    if text is None:
        return None
    if ":" in text:
        parts = text.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        raise ValueError(f"time is not a number: {value!r}")
    unit = re.fullmatch(
        r"(\d+(?:\.\d+)?)\s*(s|sec|secs|second|seconds|min|mins|minute|minutes)",
        text,
        re.IGNORECASE,
    )
    if unit:
        amount = float(unit.group(1))
        if unit.group(2).lower().startswith("min"):
            return amount * 60
        return amount
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"time is not a number: {value!r}") from exc


def _seconds_from_pace(pace: object, distance_m: float | None) -> float | None:
    if _is_blank(pace) or isinstance(pace, bool):
        return None
    if isinstance(pace, (int, float)):
        if isinstance(pace, float) and math.isnan(pace):
            return None
        return float(pace)
    text = _clean_text(pace)
    if text is None:
        return None
    match = _PACE.match(text)
    if match:
        if distance_m is None or distance_m <= 0:
            return None
        pace_s = int(match.group(1)) * 60 + float(match.group(2))
        unit = match.group(3).lower()
        meters = 1609.344 if unit.startswith("mi") else 1000.0
        return (pace_s / meters) * distance_m
    if ":" in text and "/" not in text.lower() and "per" not in text.lower():
        return _parse_seconds(text)
    raise ValueError(f"pace is not a time: {pace!r}")


def _clean_text(value: object) -> str | None:
    text = str(value).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    if text.lower() in _MISSING:
        return None
    return text


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip().lower() in _MISSING:
        return True
    return False
