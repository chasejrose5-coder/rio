# classify.py — deterministic session labels from normalized laps. No LLM.

"""Plain if-thens. No language model. If a session matches none of the rules, say unsure."""

from __future__ import annotations

import importlib
import re
from pathlib import Path

# rio/v0.1. Every classification carries this.
ONTOLOGY_VERSION = "v0.1"

# Longer than 2 minutes. Exactly 120 seconds does not match.
TWO_MINUTES_S = 120

# "Near" the Target 800 pace in docs/goal.md: within 5%, faster or slower.
NEAR_GOAL_TOLERANCE = 0.05

# "Strong but slower": slower than that near band, and not slower than this.
# 1.40 x 1:55 pace is about 3:21/km. Slower than that is not called strong.
STRONG_SLOWER_MAX = 1.40

# "Could be done while talking": 1.9 x goal 800 pace is roughly 7:15/mile at a 1:55 goal.
# The gap between strong and talkable matches no rule.
TALKABLE_PACE_RATIO = 1.9

_TARGET_800 = re.compile(r"Target\s+800\s*:\s*(\d+):(\d+(?:\.\d+)?)")

ROOT = Path(__file__).resolve().parent.parent
GOAL_PATH = ROOT / "docs" / "goal.md"

try:
    normalize = importlib.import_module("engines.normalize").normalize
except ModuleNotFoundError:
    normalize = importlib.import_module("normalize").normalize


def classify(payload: dict | list, goal_path: Path | None = None) -> dict:
    """Return family, reason_codes, confidence, and ontology_version.

    Confidence is "high" when one rule matches, and "unsure" when the family is unsure.
    """
    laps = normalize(payload)["laps"]
    path = GOAL_PATH if goal_path is None else Path(goal_path)
    goal_seconds = load_goal_800_seconds(path)
    goal_pace = goal_seconds / 800.0
    ratios = _pace_ratios(laps, goal_pace)

    if not laps:
        return _result("unsure", ["no_pattern"])

    # If rest is missing, family = unsure. Do not guess.
    if _interval_rests(laps) is None:
        return _result("unsure", ["rest_missing"])

    matched: list[dict] = []

    # Most of the work steps are 60–150 m and rest is longer than 2 minutes.
    if _most_in_range(laps, 60, 150) and _rest_longer_than(laps, TWO_MINUTES_S):
        matched.append(_result("max_velocity", ["work_60_150m", "rest_gt_2min"]))

    # Work steps are 200–300 m, rest is longer than 2 minutes, pace is near goal 800 pace.
    if (
        _all_in_range(laps, 200, 300)
        and _rest_longer_than(laps, TWO_MINUTES_S)
        and ratios is not None
        and _all_near_goal(ratios)
    ):
        matched.append(
            _result(
                "speed",
                ["work_200_300m", "rest_gt_2min", "pace_near_goal_800"],
            )
        )

    # Work steps are 300–500 m, rest is 60–120 seconds, pace is near goal 800 pace.
    if (
        _all_in_range(laps, 300, 500)
        and _rest_between(laps, 60, 120)
        and ratios is not None
        and _all_near_goal(ratios)
    ):
        matched.append(
            _result(
                "speed_endurance",
                ["work_300_500m", "rest_60_120s", "pace_near_goal_800"],
            )
        )

    # Work steps are 600–1000 m and the pace is strong but slower than goal 800 pace.
    if _all_in_range(laps, 600, 1000) and ratios is not None and _all_strong_slower(ratios):
        matched.append(
            _result(
                "aerobic_power",
                ["work_600_1000m", "pace_strong_slower_than_goal_800"],
            )
        )

    # One continuous easy run that could be done while talking.
    if (
        len(laps) == 1
        and laps[0]["rest_s"] == 0
        and ratios is not None
        and _all_talkable(ratios)
    ):
        matched.append(_result("aerobic", ["continuous_easy", "talkable"]))

    # A single 800 m race effort: one 800 m at or faster than the near-goal band.
    if (
        len(laps) == 1
        and _is_800_m(laps[0]["distance_m"])
        and ratios is not None
        and ratios[0] <= 1 + NEAR_GOAL_TOLERANCE + 1e-9
    ):
        matched.append(_result("race_readiness", ["single_800m", "race_effort"]))

    if len(matched) == 1:
        return matched[0]
    # Two rules fired. Do not guess.
    if len(matched) > 1:
        return _result("unsure", ["conflicting_rules"])
    return _result("unsure", ["no_pattern"])


def load_goal_800_seconds(path: Path) -> float:
    """Target 800 from docs/goal.md, in seconds. 1:55.0 is 115 seconds."""
    text = path.read_text(encoding="utf-8")
    match = _TARGET_800.search(text)
    if not match:
        raise ValueError(f"Target 800 not found in {path}")
    return int(match.group(1)) * 60 + float(match.group(2))


def _result(family: str, reason_codes: list[str]) -> dict:
    confidence = "unsure" if family == "unsure" else "high"
    return {
        "family": family,
        "reason_codes": list(reason_codes),
        "confidence": confidence,
        "ontology_version": ONTOLOGY_VERSION,
    }


def _pace_ratios(laps: list[dict], goal_pace: float) -> list[float] | None:
    """Rep seconds-per-meter divided by goal 800 seconds-per-meter. 1.0 is goal pace."""
    if goal_pace <= 0:
        return None
    ratios: list[float] = []
    for lap in laps:
        distance_m = lap.get("distance_m")
        seconds = lap.get("seconds")
        if (
            distance_m is None
            or seconds is None
            or distance_m <= 0
            or seconds <= 0
        ):
            return None
        ratios.append((seconds / distance_m) / goal_pace)
    return ratios


def _all_near_goal(ratios: list[float]) -> bool:
    limit = NEAR_GOAL_TOLERANCE + 1e-9
    return all(abs(ratio - 1.0) <= limit for ratio in ratios)


def _all_strong_slower(ratios: list[float]) -> bool:
    slow_edge = 1 + NEAR_GOAL_TOLERANCE
    return all(slow_edge < ratio <= STRONG_SLOWER_MAX + 1e-9 for ratio in ratios)


def _all_talkable(ratios: list[float]) -> bool:
    return all(ratio >= TALKABLE_PACE_RATIO for ratio in ratios)


def _most_in_range(laps: list[dict], low: float, high: float) -> bool:
    if not laps:
        return False
    inside = 0
    for lap in laps:
        distance_m = lap.get("distance_m")
        if distance_m is not None and low <= distance_m <= high:
            inside += 1
    return inside * 2 > len(laps)


def _all_in_range(laps: list[dict], low: float, high: float) -> bool:
    if not laps:
        return False
    for lap in laps:
        distance_m = lap.get("distance_m")
        if distance_m is None or not (low <= distance_m <= high):
            return False
    return True


def _is_800_m(distance_m: float | None) -> bool:
    return distance_m is not None and abs(distance_m - 800) <= 0.01


def _interval_rests(laps: list[dict]) -> list[float] | None:
    """Rests the rules read. None means rest is missing.

    One lap uses that lap's rest. Several laps use the rest after each rep
    except a final 0, which means the session stopped.
    """
    if not laps:
        return []
    if len(laps) == 1:
        rest_s = laps[0].get("rest_s")
        if rest_s is None:
            return None
        return [rest_s]

    rests: list[float] = []
    for lap in laps[:-1]:
        rest_s = lap.get("rest_s")
        if rest_s is None:
            return None
        rests.append(rest_s)
    last = laps[-1].get("rest_s")
    if last is not None and last != 0:
        rests.append(last)
    return rests


def _rest_longer_than(laps: list[dict], seconds: float) -> bool:
    rests = _interval_rests(laps)
    if not rests:
        return False
    return all(rest > seconds for rest in rests)


def _rest_between(laps: list[dict], low: float, high: float) -> bool:
    rests = _interval_rests(laps)
    if not rests:
        return False
    return all(low <= rest <= high for rest in rests)
