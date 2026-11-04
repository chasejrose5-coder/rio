# about.py — plain words for the season. Display only.

"""Static explanation of the season already built by the rules.

Phase lines use the primary and secondary families the season already names.
Nothing here builds a plan, labels a workout, adapts a week, or calls a model.
"""

from __future__ import annotations

from engines.season import _PRIMARY, _SECONDARY

# Plain words for families the season already stores. Display only.
_FAMILY = {
    "aerobic": "Aerobic",
    "threshold": "Threshold",
    "aerobic_power": "Aerobic power",
    "speed_endurance": "Speed endurance",
    "anaerobic_capacity": "Anaerobic capacity",
    "race_readiness": "Race readiness",
    "max_velocity": "Max velocity",
    "speed": "Speed",
}
_ORDER = (
    "aerobic",
    "threshold",
    "speed_endurance",
    "aerobic_power",
    "anaerobic_capacity",
    "race_readiness",
    "max_velocity",
    "speed",
)

# Phase 2 steps the short fast reps up from phase 1. Phase 5 lengthens the
# reps from phase 4. Phase 8 stays a fresh taper.
_EXTRA = {
    2: "The short fast reps step up from phase 1.",
    5: "The reps are longer than in phase 4.",
    8: "The taper stays fresh. No hard speed endurance or anaerobic work.",
}

_PHASE_INTRO = (
    "Phases 1–7 are a six-day week. Sunday, Monday, and Wednesday are easy. "
    "Tuesday and Thursday are hard. Saturday is the long run. Friday is off.",
    "Phase 8 is a shorter taper. The 800 m race can sit on the last Saturday.",
)
_PHASE_CLOSE = (
    "From eight weeks up, phases 1–7 each get a week. Phase 8 is the last "
    "two weeks, or one week when the season is one week or eight weeks. "
    "Weeks still left fill phases 1–4 up to a cap, then phases 5–7. Anything "
    "past those caps rotates through phases 1–4. A shorter season fills the "
    "taper, then phases 7, 6, and 5, and compresses phases 1–4.",
)
_TEN_PERCENT = (
    "From one week to the next, planned distance and the number of hard "
    "sessions may rise by at most 10%. Hard sessions are the ones that are "
    "not easy runs. A rise fits when the new week times 10 is still no more "
    "than the previous week times 11.",
    "If the week as written would climb faster, the plan holds or uses an "
    "easier session. The taper may drop. The same cap still applies after a "
    "mark changes later weeks.",
)
_CLASSIFICATION = (
    "Classification is rules, not AI. The rules read each rep's distance, "
    "the rest, and the pace against the goal 800. The result is one family, "
    "the reason codes, and the ontology version.",
    "A model does not pick the family. On Last Session, Next, and Decisions, "
    "a model may only rephrase a paragraph the rules already wrote. A "
    "rephrase that changes the family, the template, or the reasons is "
    "dropped. Those calls stop once recorded spend reaches $25.",
)
_HARD_DAYS = (
    "A hard day is a Tuesday or Thursday that is not an easy run. A result "
    "within 3% of the target is on_track. Slower or shorter is not_hitting. "
    "Faster or longer is smashing. Season and Weekly can mark a week with "
    "those same three words.",
    "The marked week stays as written. On track leaves the later weeks. Not "
    "hitting moves them back one phase, or makes the next week easy when the "
    "phase cannot move back. Smashing moves them forward one phase and stops "
    "at phase 7, or uses a harder session from the menu when the phase cannot "
    "advance. Phase 8 stays the taper.",
    "Not hitting wins when more than one mark applies, then smashing. A "
    "matched activity on a hard day is judged when that day has no mark yet. "
    "Later weeks are what change.",
)


def _words(families: set[str]) -> str:
    labels = [_FAMILY[name] for name in _ORDER if name in families]
    if not labels:
        return ""
    words = [labels[0]] + [label[:1].lower() + label[1:] for label in labels[1:]]
    if len(words) == 1:
        return words[0]
    if len(words) == 2:
        return f"{words[0]} and {words[1]}"
    return ", ".join(words[:-1]) + f", and {words[-1]}"


def phase_rows() -> list[tuple[str, str]]:
    """One line per phase, in order. Families come from the season."""
    rows: list[tuple[str, str]] = []
    for phase in range(1, 9):
        primary = _words(_PRIMARY[phase])
        secondary = _SECONDARY[phase]
        if secondary:
            pronoun = "them" if len(_PRIMARY[phase]) > 1 else "it"
            line = f"{primary}, with {_words(secondary).lower()} beside {pronoun}."
        else:
            line = f"{primary}."
        extra = _EXTRA.get(phase, "")
        if extra:
            line = f"{line} {extra}"
        rows.append((f"Phase {phase}", line))
    return rows


# Athlete-facing lines. The older paragraphs stay on the section so a
# check of the full text still finds them. The page shows these instead.
_SHOWN = {
    "10% rule": (
        "From one week to the next, distance and the number of hard sessions "
        "can rise by at most 10%. Hard sessions are the ones that are not "
        "easy runs. If a week would climb faster, the plan holds or picks an "
        "easier session. The taper may drop.",
    ),
    "Classification": (
        "RIO labels each session with rules. It reads how far the rep is, "
        "how long you rest, and how that pace compares with your goal 800. "
        "You see one kind of work and a short reason.",
    ),
    "Hard days": (
        "Tuesday and Thursday are hard days, unless that day is an easy run. "
        "A result within 3% of the target is on track. Slower or shorter "
        "means the week fell short. Faster or longer means it went better. "
        "On track leaves later weeks as they are. Falling short moves later "
        "weeks back one phase. Doing better moves them forward one phase and "
        "stops at phase 7. Phase 8 stays the taper. When more than one mark "
        "applies, falling short wins. Later weeks are what change.",
    ),
}


def about_sections() -> list[dict]:
    """Four blocks for the About page. Copy only."""
    return [
        {
            "title": "Eight phases",
            "paragraphs": list(_PHASE_INTRO),
            "rows": phase_rows(),
            "closing": list(_PHASE_CLOSE),
        },
        {
            "title": "10% rule",
            "paragraphs": list(_TEN_PERCENT),
            "shown": list(_SHOWN["10% rule"]),
            "rows": [],
            "closing": [],
        },
        {
            "title": "Classification",
            "paragraphs": list(_CLASSIFICATION),
            "shown": list(_SHOWN["Classification"]),
            "rows": [],
            "closing": [],
        },
        {
            "title": "Hard days",
            "paragraphs": list(_HARD_DAYS),
            "shown": list(_SHOWN["Hard days"]),
            "rows": [],
            "closing": [],
        },
    ]
