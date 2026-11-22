# warmup.py — warm-up, cool-down, and core notes for one session.

"""Display only. The same session always gets the same notes.

Easy runs get a short jog, leg swings, and a few light stretches.
Workout, quality, long, and race days keep the full warm-up, including
the active drills, the dynamic drills, and the strides.
Nothing here is stored on the session, the template, or the plan.
"""

from __future__ import annotations

from engines.bike import day_kind

_COOLDOWN = (
    "Seated forward fold",
    "Seated figure-four each side",
    "Seated straddle",
    "Seated hip-flexor each side",
    "Seated calf stretch each side",
    "Seated hamstring each side",
    "Lying spinal twist each side",
)

_CORE = (
    "Plank",
    "Side plank each side",
    "Dead bug each side",
    "Bird-dog each side",
    "Glute bridge",
    "Bicycle crunch each side",
    "Reverse crunch",
    "Split-lunge jumps (low volume)",
)

_FULL_DRILLS = (
    (
        "Active drills (20–30 m each):",
        (
            "Arm swings forward and reverse",
            "Walking quad stretch",
            "Hamstring sweeps",
            "Lateral leg swings",
            "Alternating knee drops",
            "Rocking adductor stretch",
        ),
    ),
    (
        "Dynamic drills (20–30 m each):",
        (
            "A-skips",
            "B-skips",
            "Knee buffs",
            "Straight-leg bounds",
            "Lateral skips",
        ),
    ),
    ("Then:", ("4 × 100 m strides with walk-back",)),
)

_EASY_STRETCHES = (
    "Lateral leg swings",
    "Walking quad stretch",
    "Hamstring sweeps",
    "Easy calf stretch each side",
)


def _block(title: str, lines: tuple[str, ...] = (), lead: tuple[str, ...] = (), groups: tuple[tuple[str, ...], ...] = ()) -> dict:
    return {
        "title": title,
        "lines": list(lines),
        "lead": list(lead),
        "groups": [list(group) for group in groups],
    }


def _cooldown() -> dict:
    return _block(
        "Cool-down",
        lead=("1 easy lap, then seated stretches for the full lower body:",),
        groups=(_COOLDOWN,),
    )


def _core() -> dict:
    return _block("Core", lead=("3 rounds of:",), groups=(_CORE,))


def _easy_warm() -> dict:
    return _block(
        "Warm-up",
        lines=("3–5 min easy jog",),
        lead=("Then leg swings and a few light stretches:",),
        groups=(_EASY_STRETCHES,),
    )


def _full_warm() -> dict:
    leads = tuple(lead for lead, _items in _FULL_DRILLS)
    groups = tuple(items for _lead, items in _FULL_DRILLS)
    return _block("Warm-up", lead=leads, groups=groups)


def prep_blocks(session: object) -> list[dict]:
    """The notes after the workout. Easy days skip drills and strides."""
    if day_kind(session) == "easy":
        return [_easy_warm(), _cooldown(), _core()]
    return [
        _block("Pre-warm-up", lines=("1 × 800 m easy",)),
        _full_warm(),
        _cooldown(),
        _core(),
    ]


def prep_text(session: object) -> str:
    """The notes as plain lines, in order. Tests read this."""
    lines: list[str] = []
    for block in prep_blocks(session):
        lines.append(str(block["title"]))
        lines.extend(block["lines"])
        for index, lead in enumerate(block["lead"]):
            lines.append(lead)
            group = block["groups"][index] if index < len(block["groups"]) else []
            lines.extend(group)
    return "\n".join(lines)
