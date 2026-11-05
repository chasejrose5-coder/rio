# probability.py — goal probability shape. The formula is not in this file.

"""A deterministic stub for a later formula.

Hit means target_time or faster in the race, or a marked race-sim or time
trial, by target_date. Training reps are not a hit. A later formula may
update after every planned hard day, done or missed. Easy days may nudge
only from heart rate, and only by a small amount. Caps, when they exist,
belong on a hard session and on a week. None of that math is here yet.

This module does not call a model and does not read an activity feed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoalProbability:
    """The fields a later formula will fill. percent stays empty until then."""

    percent: int | None
    projected_800: str | None
    gap_seconds: float | None
    trend: str
    confidence: str
    updated_at: str
    drivers: tuple[str, ...]


def compute_goal_probability(*, viewer: str = "athlete") -> GoalProbability | None:
    """None for an athlete. Admin gets an uncalibrated record, not a percent."""
    if viewer != "admin":
        return None
    return GoalProbability(
        percent=None,
        projected_800=None,
        gap_seconds=None,
        trend="unknown",
        confidence="low",
        updated_at="",
        drivers=(),
    )


def athlete_line() -> str:
    """Athletes do not see a probability."""
    return ""


def admin_line() -> str:
    """The only sentence the Admin page may show. It is not a percent."""
    found = compute_goal_probability(viewer="admin")
    if found is None or found.percent is not None:
        return ""
    return "Goal probability (stub). Not calibrated."
