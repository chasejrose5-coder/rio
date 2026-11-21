# heart_rate.py — Karvonen zones from a measured resting and max heart rate.

"""Five zones from heart-rate reserve. Later prescriptions and analysis
should call zones_for. This module does not read a database or Strava.

target = resting + (max - resting) x percent

Zone 1 recovery is 50–60%, zone 2 easy/long 60–70%, zone 3 tempo 70–80%,
zone 4 threshold 80–90%, and zone 5 VO2max/race 90–100%. Beats are rounded
half up to a whole number.

max_hr_from_age is the hook for a later age formula. It does not estimate.
"""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

RESTING_LOW = Decimal("30")
RESTING_HIGH = Decimal("100")
MAX_LOW = Decimal("140")
MAX_HIGH = Decimal("230")
BOUND_LOW = 30
BOUND_HIGH = 230

METHOD = "karvonen"
METHOD_LABEL = "Karvonen (heart rate reserve)"
METHOD_SENTENCE = "Zones use the Karvonen (heart rate reserve) method."
SAFETY_NOTE = (
    "This is not medical advice. Stop and seek help if your heart rate stays unusually high or you feel unwell."
)
STRAVA_PREFILL_NOTE = (
    "Strava is not used to fill these yet. Connect uses the activity:read_all scope, "
    "and athlete heart-rate zones need profile:read_all. A later update can prefill "
    "resting and max heart rate when that data is available."
)

# Percent of heart-rate reserve, low then high. Names stay here so a stored
# boundary row only has to keep the zone number and the beats.
ZONES = (
    (1, "recovery", "Recovery", 50, 60),
    (2, "easy", "Easy / long", 60, 70),
    (3, "tempo", "Tempo", 70, 80),
    (4, "threshold", "Threshold", 80, 90),
    (5, "vo2", "VO2max / race", 90, 100),
)

_REST_KEYS = ("resting_heartrate", "resting_heart_rate", "resting_hr")
_MAX_KEYS = ("max_heartrate", "max_heart_rate", "max_hr")


class HeartRateInput(ValueError):
    """A resting heart rate, max heart rate, or zone boundary the runner can fix."""


def max_hr_from_age(age: object) -> None:
    """Reserved for a later age formula. This phase always asks for a measured max."""
    return None


def parse_bpm(value: object) -> Decimal | None:
    """A finite heart rate to one decimal, or None when it is not a real number."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, int):
        number = Decimal(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            return None
        number = Decimal(str(value))
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            number = Decimal(text)
        except InvalidOperation:
            return None
    else:
        return None
    if not number.is_finite():
        return None
    return number.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def require_anchors(resting: object, maximum: object) -> tuple[Decimal, Decimal]:
    """Measured resting and max heart rate, or HeartRateInput with a sentence."""
    low = parse_bpm(resting)
    high = parse_bpm(maximum)
    if low is None or low < RESTING_LOW or low > RESTING_HIGH:
        raise HeartRateInput("Enter a resting heart rate between 30 and 100.")
    if high is None or high < MAX_LOW or high > MAX_HIGH:
        raise HeartRateInput("Enter a max heart rate between 140 and 230.")
    if high <= low:
        raise HeartRateInput("Max heart rate has to be above resting heart rate.")
    return low, high


def anchors_in_order(resting: Decimal, maximum: Decimal) -> bool:
    """True when max is above resting. Ranges already make this true today."""
    return maximum > resting


def karvonen_bpm(resting: Decimal, maximum: Decimal, percent: int) -> int:
    """Beats at this percent of heart-rate reserve, rounded half up."""
    rest = int((resting * 10).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    top = int((maximum * 10).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    raw = Decimal(rest) + Decimal(top - rest) * Decimal(percent) / Decimal(100)
    return int((raw / Decimal(10)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _public_number(number: Decimal) -> int | float:
    if number == number.to_integral_value():
        return int(number)
    return float(number)


def _zone_row(spec: tuple, low_bpm: int, high_bpm: int) -> dict:
    number, key, name, low_percent, high_percent = spec
    return {
        "zone": number,
        "key": key,
        "name": name,
        "low_percent": low_percent,
        "high_percent": high_percent,
        "low_bpm": low_bpm,
        "high_bpm": high_bpm,
    }


def default_zones(resting: Decimal, maximum: Decimal) -> list[dict]:
    """The five Karvonen ranges for these anchors."""
    rows = []
    for spec in ZONES:
        rows.append(_zone_row(spec, karvonen_bpm(resting, maximum, spec[3]), karvonen_bpm(resting, maximum, spec[4])))
    return rows


def _bound_bpm(value: object) -> int | None:
    number = parse_bpm(value)
    if number is None:
        return None
    whole = int(number.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if whole < BOUND_LOW or whole > BOUND_HIGH:
        return None
    return whole


def normalize_bounds(resting: Decimal, maximum: Decimal, bounds: object) -> list[dict] | None:
    """Custom edges, or None when they are the Karvonen defaults.

    Five zones, each low below high, each edge shared with the next zone,
    and every beat from 30 through 230.
    """
    if not isinstance(bounds, list) or len(bounds) != 5:
        raise HeartRateInput("Zone boundaries have to stay in order.")
    found: dict[int, tuple[int, int]] = {}
    for row in bounds:
        if not isinstance(row, dict):
            raise HeartRateInput("Zone boundaries have to stay in order.")
        zone = row.get("zone")
        if isinstance(zone, bool) or not isinstance(zone, int) or zone not in range(1, 6) or zone in found:
            raise HeartRateInput("Zone boundaries have to stay in order.")
        low = _bound_bpm(row.get("low_bpm"))
        high = _bound_bpm(row.get("high_bpm"))
        if low is None or high is None:
            raise HeartRateInput("Enter a heart rate between 30 and 230.")
        if low >= high:
            raise HeartRateInput("Zone boundaries have to stay in order.")
        found[zone] = (low, high)
    if set(found) != {1, 2, 3, 4, 5}:
        raise HeartRateInput("Zone boundaries have to stay in order.")
    for zone in range(1, 5):
        if found[zone][1] != found[zone + 1][0]:
            raise HeartRateInput("Zone boundaries have to stay in order.")
    defaults = default_zones(resting, maximum)
    custom = []
    same = True
    for spec, default in zip(ZONES, defaults):
        low, high = found[spec[0]]
        if low != default["low_bpm"] or high != default["high_bpm"]:
            same = False
        custom.append(_zone_row(spec, low, high))
    if same:
        return None
    return custom


def zones_for(resting: object, maximum: object, bounds: object = None) -> dict:
    """The zones later prescriptions and post-run analysis should read.

    bounds is None for Karvonen defaults, or five zone rows the runner edited.
    A row that matches the defaults is stored as not custom.
    """
    low, high = require_anchors(resting, maximum)
    defaults = default_zones(low, high)
    custom = None
    if bounds is not None:
        custom = normalize_bounds(low, high, bounds)
    zones = custom if custom is not None else defaults
    return {
        "method": METHOD,
        "method_label": METHOD_LABEL,
        "method_sentence": METHOD_SENTENCE,
        "safety": SAFETY_NOTE,
        "resting_hr": _public_number(low),
        "max_hr": _public_number(high),
        "custom": custom is not None,
        "zones": zones,
    }


def anchors_from_strava(payload: object) -> tuple[int | float | None, int | float | None]:
    """Resting and max when the payload states them.

    Strava's /athlete/zones list does not include a resting heart rate.
    A top zone max of -1 is not a measured max, so that shape returns nothing.
    Explicit resting_heartrate and max_heartrate fields are kept when they
    fall in range. The live call is not made from here.
    """
    if not isinstance(payload, dict):
        return None, None
    resting = _named(payload, _REST_KEYS)
    maximum = _named(payload, _MAX_KEYS)
    heart = payload.get("heart_rate")
    if isinstance(heart, dict):
        if resting is None:
            resting = _named(heart, _REST_KEYS)
        if maximum is None:
            maximum = _named(heart, _MAX_KEYS)
    low = resting if resting is not None and RESTING_LOW <= resting <= RESTING_HIGH else None
    high = maximum if maximum is not None and MAX_LOW <= maximum <= MAX_HIGH else None
    if low is not None and high is not None and high <= low:
        return None, None
    return (_public_number(low) if low is not None else None, _public_number(high) if high is not None else None)


def _named(payload: dict, keys: tuple[str, ...]) -> Decimal | None:
    for key in keys:
        if key in payload:
            return parse_bpm(payload.get(key))
    return None


def strava_prefill() -> dict:
    """Nothing is filled from Strava until the zones endpoint is in scope."""
    return {
        "resting_hr": None,
        "max_hr": None,
        "available": False,
        "note": STRAVA_PREFILL_NOTE,
    }


def empty_profile() -> dict:
    """No anchors yet. Zones stay empty until both numbers are saved."""
    return {
        "method": METHOD,
        "method_label": METHOD_LABEL,
        "method_sentence": METHOD_SENTENCE,
        "safety": SAFETY_NOTE,
        "no_monitor": False,
        "resting_hr": None,
        "max_hr": None,
        "custom": False,
        "zones": [],
        "strava_prefill": strava_prefill(),
    }


def profile_from_stored(raw: dict) -> dict:
    """The API body for one stored row. A bad custom list falls back to Karvonen."""
    no_monitor = raw.get("no_monitor") is True
    resting = parse_bpm(raw.get("resting_hr"))
    maximum = parse_bpm(raw.get("max_hr"))
    if resting is None or maximum is None or resting < RESTING_LOW or resting > RESTING_HIGH:
        body = empty_profile()
        body["no_monitor"] = no_monitor
        return body
    if maximum < MAX_LOW or maximum > MAX_HIGH or maximum <= resting:
        body = empty_profile()
        body["no_monitor"] = no_monitor
        return body
    bounds = raw.get("zones")
    try:
        body = zones_for(resting, maximum, bounds if bounds else None)
    except HeartRateInput:
        body = zones_for(resting, maximum, None)
    body["no_monitor"] = no_monitor
    body["strava_prefill"] = strava_prefill()
    return body
