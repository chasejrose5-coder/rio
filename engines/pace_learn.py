# pace_learn.py — easy, tempo, and threshold pace from time in zone.

"""A run counts for a zone when that zone holds at least half of the time
that fell inside the five zones. Runs without a heart-rate stream do not
count. Six runs are enough to trust the range. The slowest and fastest of
those paces are the range, widened when they are the same pace.

The same samples are counted again with the current zones, so a new resting
or max heart rate changes which runs qualify.
"""

from __future__ import annotations

from decimal import Decimal

from engines.heart_targets import QUALIFYING_NEEDED
from engines.pace import pace_seconds, pace_unit
from engines.zone_time import zone_report


def ranges_for_activities(activities: object, streams: object, zones: object, unit: object) -> dict[int, dict]:
    """Learn from stored runs that have a heart-rate stream."""
    runs = []
    if isinstance(activities, list) and isinstance(streams, dict):
        for row in activities:
            if not isinstance(row, dict):
                continue
            sample = streams.get(str(row.get("id") or ""))
            if not isinstance(sample, dict):
                continue
            runs.append(
                {
                    "distance_m": row.get("distance_m") if row.get("distance_m") is not None else row.get("distance") or row.get("work_m"),
                    "moving_seconds": row.get("moving_seconds"),
                    "stream": sample,
                }
            )
    return learn_ranges(runs, zones, unit)


def learn_ranges(runs: object, zones: object, unit: object) -> dict[int, dict]:
    """Pace samples for zones 2, 3, and 4."""
    chosen = pace_unit(unit)
    buckets: dict[int, list[Decimal]] = {2: [], 3: [], 4: []}
    if isinstance(runs, list):
        for run in runs:
            if not isinstance(run, dict):
                continue
            pace = _qualifying_pace(run, zones, chosen)
            if pace is None:
                continue
            zone, seconds = pace
            buckets[zone].append(seconds)
    found = {}
    for zone, paces in buckets.items():
        paces.sort()
        ready = len(paces) >= QUALIFYING_NEEDED
        low = paces[0] if ready else None
        high = paces[-1] if ready else None
        if ready and low is not None and high is not None and high - low < 10:
            mid = (low + high) / 2
            low = mid - Decimal(5)
            high = mid + Decimal(5)
        found[zone] = {"count": len(paces), "ready": ready, "low": low, "high": high}
    return found


def _qualifying_pace(run: dict, zones: object, unit: str) -> tuple[int, Decimal] | None:
    report = zone_report(run.get("stream"), zones, None)
    if report is None:
        return None
    rows = [row for row in report["zones"] if isinstance(row, dict)]
    total = sum(int(row.get("seconds") or 0) for row in rows)
    if total <= 0:
        return None
    best = max(rows, key=lambda row: int(row.get("seconds") or 0))
    zone = best.get("zone")
    held = int(best.get("seconds") or 0)
    if zone not in (2, 3, 4) or held * 2 < total:
        return None
    pace = pace_seconds(run.get("distance_m"), run.get("moving_seconds"), unit)
    if pace is None:
        return None
    return int(zone), pace
