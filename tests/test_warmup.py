# test_warmup.py — easy days skip drills and strides. Other days keep them.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.warmup import prep_text

EASY = {"template_id": "aer_8000_r0_x1", "day_of_week": "Monday", "reason_codes": ["extra_easy_day"]}
QUALITY = {"template_id": "se_400_r90_x6", "day_of_week": "Tuesday", "reason_codes": ["phase_4"]}
RACE = {"template_id": "rr_800_r0_x1", "day_of_week": "Saturday", "reason_codes": []}
LONG = {
    "template_id": "aer_12000_r0_x1",
    "day_of_week": "Saturday",
    "reason_codes": ["weekly_aerobic_long_run"],
}

_FULL = (
    "Pre-warm-up",
    "1 × 800 m easy",
    "Warm-up",
    "Active drills (20–30 m each):",
    "Arm swings forward and reverse",
    "Dynamic drills (20–30 m each):",
    "A-skips",
    "B-skips",
    "Then:",
    "4 × 100 m strides with walk-back",
    "Cool-down",
    "Seated forward fold",
    "Core",
    "Plank",
    "Split-lunge jumps (low volume)",
)


def test_easy_warmup_is_a_jog_swings_and_light_stretches() -> None:
    text = prep_text(EASY)
    if "3–5 min easy jog" not in text:
        raise AssertionError(text)
    if "Then leg swings and a few light stretches:" not in text:
        raise AssertionError(text)
    for line in ("Lateral leg swings", "Walking quad stretch", "Hamstring sweeps", "Easy calf stretch each side"):
        if line not in text:
            raise AssertionError(line)
    for banned in (
        "Pre-warm-up",
        "1 × 800 m easy",
        "Active drills",
        "Dynamic drills",
        "A-skips",
        "B-skips",
        "strides",
        "Straight-leg bounds",
    ):
        if banned in text:
            raise AssertionError(banned)
    if "Cool-down" not in text or "Core" not in text:
        raise AssertionError("easy days lost the cool-down or the core")


def test_workout_quality_and_race_keep_the_full_warmup() -> None:
    for session in (QUALITY, RACE, LONG):
        text = prep_text(session)
        cursor = 0
        for phrase in _FULL:
            found = text.find(phrase, cursor)
            if found < 0:
                raise AssertionError(f"{session['template_id']} missing {phrase}")
            cursor = found + len(phrase)
        if "3–5 min easy jog" in text:
            raise AssertionError(session["template_id"])


def test_the_same_session_always_gets_the_same_notes() -> None:
    if prep_text(EASY) != prep_text(dict(EASY)):
        raise AssertionError("easy notes moved")
    if prep_text(QUALITY) != prep_text(dict(QUALITY)):
        raise AssertionError("quality notes moved")
    if prep_text({}) == prep_text(EASY):
        raise AssertionError("a blank session was treated as easy")
