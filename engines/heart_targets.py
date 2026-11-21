# heart_targets.py — heart-rate zone on the workouts that use one.

"""Easy and long runs use Zone 2. Aerobic power is the tempo day and uses
Zone 3. Threshold uses Zone 4. Short reps and race-pace work stay on pace.

An heart-rate day still shows a pace range, never one pace. Until enough
Zone 2, 3, or 4 runs exist, that range is marked as still being created.
Pace on those days is not used to move later workouts.

qualifying_for_zone stays at zero until pace learning reads heart-rate
streams. The display already asks for the count.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from engines.heart_rate import SAFETY_NOTE
from engines.pace import (
    METERS_PER_KM,
    METERS_PER_MILE,
    PACE_KM,
    PACE_MILE,
    canonical_easy_pace,
    pace_seconds,
    pace_unit,
    parse_easy_pace,
    workout_recipe,
)

# Aerobic power is the sustained strong day that is not threshold and not
# 800 race pace. That is the tempo workout in this plan.
ZONE_BY_FAMILY = {"aer": 2, "ap": 3, "thr": 4}
# About 5–6 runs. Trust starts at 6.
QUALIFYING_NEEDED = 6
CREATING_NOTE = "still creating your estimate"
EFFORT_NOTE = "Stay in the zone. Pace can move with heat and hills."
# Seconds of pace either side of the current target, per mile.
RANGE_HALF_MILE = Decimal(20)


def zone_for_template(template_id: object) -> int | None:
    """The heart-rate zone for this workout, or None when it stays on pace."""
    recipe = workout_recipe(template_id)
    if recipe is None:
        return None
    family = str(recipe.get("family") or "")
    zone = ZONE_BY_FAMILY.get(family)
    if zone is None:
        return None
    if family == "aer" and not recipe.get("continuous"):
        return None
    return zone


def qualifying_for_zone(zone: int, runs: object = None) -> int:
    """Runs that can teach this zone's pace. Streams are not stored yet."""
    return 0


def training_logs(logs: list, heart: dict | None) -> list:
    """Drop heart-rate days from the pace correction when zones are in use.

    A hot or hilly easy run should not ease later workouts. Pace-based days
    still count.
    """
    if not heart:
        return logs
    kept = []
    for entry in logs:
        template = getattr(entry, "template_id", "")
        if zone_for_template(template) is None:
            kept.append(entry)
    return kept


def heart_overlay(template_id: object, times: dict | None, profile: dict | None, unit: object) -> dict | None:
    """The zone line and pace range for one workout, or None to leave pace as it is."""
    if not isinstance(profile, dict) or profile.get("no_monitor") is True:
        return None
    zone = zone_for_template(template_id)
    if zone is None:
        return None
    band = _zone_band(profile, zone)
    if band is None:
        return None
    chosen = pace_unit(unit)
    center = _center_pace(template_id, times, chosen)
    if center is None:
        return None
    low, high = _widen(center, chosen)
    if low >= high:
        high = low + 1
    count = qualifying_for_zone(zone)
    ready = count >= QUALIFYING_NEEDED
    low_text = _clock(low)
    high_text = _clock(high)
    label = "per mile" if chosen == PACE_MILE else "per kilometer"
    return {
        "zone": zone,
        "zone_name": band["name"],
        "low_bpm": band["low_bpm"],
        "high_bpm": band["high_bpm"],
        "pace_low": low_text,
        "pace_high": high_text,
        "pace_line": f"{low_text}\u2013{high_text} {label}",
        "pace_note": CREATING_NOTE if not ready else f"Learned from {count} Zone {zone} runs.",
        "estimate": "ready" if ready else "creating",
        "qualifying": count,
        "qualifying_needed": QUALIFYING_NEEDED,
        "effort": EFFORT_NOTE,
        "safety": SAFETY_NOTE,
        "line": f"Zone {zone} \u00b7 {band['name']} \u00b7 {band['low_bpm']}\u2013{band['high_bpm']} bpm",
    }


def _zone_band(profile: dict, zone: int) -> dict | None:
    rows = profile.get("zones")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict) or row.get("zone") != zone:
            continue
        low = row.get("low_bpm")
        high = row.get("high_bpm")
        name = row.get("name")
        if isinstance(low, bool) or isinstance(high, bool):
            return None
        if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
            return None
        if not isinstance(name, str) or not name:
            return None
        if int(low) >= int(high):
            return None
        return {"name": name, "low_bpm": int(low), "high_bpm": int(high)}
    return None


def _center_pace(template_id: object, times: dict | None, unit: str) -> Decimal | None:
    """Seconds per mile or per kilometer at the current target."""
    recipe = workout_recipe(template_id)
    if recipe and recipe.get("continuous") and isinstance(times, dict):
        phrase = times.get("easy_pace")
        if isinstance(phrase, str):
            pace = phrase.split(" per ", 1)[0].strip()
            seconds = parse_easy_pace(pace)
            if seconds is not None and canonical_easy_pace(pace):
                return seconds
    if not isinstance(times, dict):
        return None
    reps = times.get("reps")
    if not isinstance(reps, list) or not reps:
        return None
    row = reps[0]
    if not isinstance(row, dict):
        return None
    return pace_seconds(row.get("meters"), row.get("seconds"), unit)


def _widen(center: Decimal, unit: str) -> tuple[Decimal, Decimal]:
    half = RANGE_HALF_MILE
    if unit == PACE_KM:
        half = (RANGE_HALF_MILE * METERS_PER_KM / METERS_PER_MILE).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return center - half, center + half


def _clock(seconds: Decimal) -> str:
    whole = int(seconds.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if whole < 0:
        whole = 0
    return f"{whole // 60}:{whole % 60:02d}"
