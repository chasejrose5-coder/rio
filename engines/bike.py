# bike.py — an easy run may be swapped for a bike. The rules are fixed.

"""Easy days only. At most two swaps in a Sunday-through-Saturday week.
Race day and the day before stay a run. Duration is 1.3 times the planned
run, rounded to the nearest 5 minutes. Bike zones are the running Karvonen
zones, 6 bpm lower. The screen does not ask for a pedaling rate.

No model. No add-on spin. A bike does not add run distance.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

SHIFT_BPM = 6
WEEK_CAP = 2

# Rebuilding these areas puts the bike swap ahead of the easy run.
SUGGEST_AREAS = frozenset(
    {
        "plantar-fascia",
        "ankle-sprain",
        "peroneal",
        "achilles",
        "soleus",
        "shins",
        "bone-stress",
    }
)

RACE_ID = "rr_800_r0_x1"
_LONG_LADDER = {f"aer_{meters}_r0_x1" for meters in range(9500, 20001, 500)}
RIDE_TYPES = frozenset({"Ride", "VirtualRide"})


def bike_minutes(run_seconds: object) -> int:
    """1.3 times the planned run, to the nearest 5 minutes.

    40 minutes of running is 50 minutes on the bike.
    """
    if isinstance(run_seconds, bool) or not isinstance(run_seconds, (int, float, Decimal)):
        raise ValueError("run time is missing")
    seconds = Decimal(str(run_seconds))
    if seconds <= 0:
        raise ValueError("run time is missing")
    minutes = (seconds / Decimal(60)) * Decimal("1.3")
    steps = (minutes / Decimal(5)).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    whole = int(steps * 5)
    if whole < 5:
        return 5
    return whole


def minutes_from_seconds(seconds: object) -> int | None:
    """A logged ride's moving time, in whole minutes."""
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float, Decimal)):
        return None
    value = Decimal(str(seconds))
    if value <= 0:
        return None
    return int((value / Decimal(60)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def bike_zones(zones: object) -> list[dict] | None:
    """The same five zones, each edge 6 bpm lower. No separate bike max."""
    if not isinstance(zones, list) or len(zones) < 5:
        return None
    shifted = []
    for row in zones:
        if not isinstance(row, dict):
            return None
        low = row.get("low_bpm")
        high = row.get("high_bpm")
        if isinstance(low, bool) or isinstance(high, bool):
            return None
        if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
            return None
        next_low = int(low) - SHIFT_BPM
        next_high = int(high) - SHIFT_BPM
        if next_low < 30:
            next_low = 30
        if next_high <= next_low:
            next_high = next_low + 1
        copied = dict(row)
        copied["low_bpm"] = next_low
        copied["high_bpm"] = next_high
        shifted.append(copied)
    return shifted


def day_kind(session: object) -> str:
    """easy, long, race, quality, or rest. Matches the stretching day rule."""
    if not isinstance(session, dict):
        return "rest"
    template = str(session.get("template_id") or "").strip()
    if not template:
        return "rest"
    if template == RACE_ID:
        return "race"
    codes = session.get("reason_codes") if isinstance(session.get("reason_codes"), list) else []
    dow = str(session.get("day_of_week") or "").strip()
    long_coded = "weekly_aerobic_long_run" in codes or template in _LONG_LADDER
    if dow == "Saturday" and long_coded:
        return "long"
    if template.startswith("aer_") or "extra_easy_day" in codes:
        return "easy"
    return "quality"


def _parse(iso: object) -> date | None:
    if not isinstance(iso, str) or len(iso) < 10:
        return None
    try:
        return date.fromisoformat(iso[:10])
    except ValueError:
        return None


def day_before_race(day: object, sessions: object) -> bool:
    current = _parse(day)
    if current is None or not isinstance(sessions, list):
        return False
    nxt = (current + timedelta(days=1)).isoformat()
    for session in sessions:
        if isinstance(session, dict) and str(session.get("date") or "")[:10] == nxt and day_kind(session) == "race":
            return True
    return False


def can_swap(*, easy: bool, before_race: bool, swaps_already: int, already: bool) -> bool:
    """A third swap in the week is refused. The day before a race stays a run."""
    if not easy or before_race:
        return False
    if already:
        return True
    if isinstance(swaps_already, bool) or not isinstance(swaps_already, int):
        return False
    return swaps_already < WEEK_CAP


def suggest_bike(area_ids: object) -> bool:
    """Shins, Achilles, soleus, or the feet are rebuilding."""
    if not isinstance(area_ids, (list, tuple, set, frozenset)):
        return False
    return any(isinstance(area, str) and area in SUGGEST_AREAS for area in area_ids)


def is_ride(row: object) -> bool:
    if not isinstance(row, dict):
        return False
    labels = {str(row.get("sport_type") or ""), str(row.get("type") or "")}
    return bool(labels & RIDE_TYPES)


def zone2_share(zone2: object, total: object) -> int | None:
    """Whole percent of bike time spent in zone 2."""
    if isinstance(zone2, bool) or isinstance(total, bool):
        return None
    if not isinstance(zone2, (int, float)) or not isinstance(total, (int, float)):
        return None
    if total <= 0 or zone2 < 0:
        return None
    return int((Decimal(zone2) * 100 / Decimal(total)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
