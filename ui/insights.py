# insights.py — Chase's season notes. Fill-ins come from the stored plan.

"""Authored paragraphs for a season that already exists.

The model is not called here. A thin week says so in the authored line.
Phase names and the one-line jobs are fixed. Capacity words come from the
season's primary and secondary families.
"""

from __future__ import annotations

from datetime import date

from engines.season import _PRIMARY, _SECONDARY

_FAMILY = {
    "aerobic": "aerobic",
    "threshold": "threshold",
    "aerobic_power": "aerobic power",
    "speed_endurance": "speed endurance",
    "anaerobic_capacity": "anaerobic capacity",
    "race_readiness": "race readiness",
    "max_velocity": "max velocity",
    "speed": "speed",
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

# Collapsed title, one line, then the expanded rest.
PHASES = (
    (
        1,
        "Base + spark",
        "Mostly easy aerobic, short max-velocity and speed.",
        "Builds the engine. Short fast reps stay short.",
    ),
    (
        2,
        "Base steps up",
        "Still aerobic-first. Short fast reps step up from phase 1.",
        "The base gets a little bigger. The fast reps stay short.",
    ),
    (
        3,
        "Threshold meets power",
        "Threshold and aerobic power, with aerobic and speed beside them.",
        "Controlled hard work shows up. Speed stays in the week.",
    ),
    (
        4,
        "Speed endurance arrives",
        "Speed endurance and aerobic power take the lead.",
        "This is the work that holds race pace when it hurts.",
    ),
    (
        5,
        "Longer specific reps",
        "Same job as phase 4, with longer reps than phase 4.",
        "The specific reps get longer. The aim stays the 800.",
    ),
    (
        6,
        "Anaerobic capacity",
        "Anaerobic capacity, with speed endurance and speed beside it.",
        "This is the kick fuel. Speed stays nearby.",
    ),
    (
        7,
        "Race readiness",
        "Race-like sessions, with speed endurance and speed nearby.",
        "The week starts to look like the race.",
    ),
    (
        8,
        "Taper",
        "Short and fresh. No hard speed-endurance or anaerobic piles.",
        "The race can sit on the last Saturday. You show up fresh.",
    ),
)

BRIDGE = (
    "Base (1–2) → controlled hard + power (3) → 800-specific endurance (4–5) "
    "→ kick fuel (6) → race reps (7) → fresh (8)."
)

THIN = (
    "Connect Strava, or log the hard day, so next week's note can talk about trending."
)

_BAND = {"on_track": "on_track", "not_hitting": "fell_short", "smashing": "went_better"}
_HARD_DAYS = {"Tuesday", "Thursday"}


def _join(names: set[str]) -> str:
    labels = [_FAMILY[name] for name in _ORDER if name in names]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def phase_name(phase: int) -> str:
    if not 1 <= phase <= 8:
        return ""
    return PHASES[phase - 1][1]


def phase_line(phase: int) -> str:
    if not 1 <= phase <= 8:
        return ""
    return PHASES[phase - 1][2]


def phase_rest(phase: int) -> str:
    if not 1 <= phase <= 8:
        return ""
    return PHASES[phase - 1][3]


def capacities(phase: int) -> tuple[str, str]:
    """Primary and secondary words for this phase. Empty when the phase is unknown."""
    if phase not in _PRIMARY:
        return "", ""
    return _join(_PRIMARY[phase]), _join(_SECONDARY[phase])


def _shown_date(value: object) -> str:
    if isinstance(value, date):
        return f"{value.day} {value.strftime('%B %Y')}"
    text = str(value or "").strip()
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return text
    return f"{parsed.day} {parsed.strftime('%B %Y')}"


def season_thesis(*, current_mark: str, goal: str, race_date: str) -> dict[str, str] | None:
    """The season paragraph. None when the plan has no goal to fill in."""
    mark = str(current_mark or "").strip()
    target = str(goal or "").strip()
    day = _shown_date(race_date)
    if not mark or not target or not day:
        return None
    collapsed = (
        f"Your season is built to get you to {target} by {day}. "
        "Every week has a job. Hard days build the capacities an 800 needs. "
        "Easy days protect that work."
    )
    expanded = (
        f"I'm Chase. RIO doesn't hand you a random mix of miles. "
        f"It builds toward one race. Your mark is {mark}. "
        f"Your goal is {target} on {day}.\n\n"
        "An 800 asks for several things at once. "
        "You need speed endurance so you can hold race pace when it hurts. "
        "You need aerobic power so the second lap doesn't collapse. "
        "You need some pure speed and a little anaerobic snap for the close. "
        "Easy aerobic running is the base that lets you absorb the hard days.\n\n"
        "The season is eight phases. Early phases lay the base and add short speed. "
        "Middle phases load the work that matters most for the 800. "
        "Late phases sharpen race readiness. "
        "The last phase is a short taper so you show up fresh. "
        "From week to week, hard work only steps up about 10%. "
        "That keeps the plan honest when life gets loud.\n\n"
        "When you finish a hard day, RIO marks how it went. "
        "On track leaves later weeks alone. Falling short eases them. "
        "Smashing moves them forward. You always know why this week exists."
    )
    return {"collapsed": collapsed, "expanded": expanded}


def this_week_copy(
    *,
    phase: int,
    days_to_goal: int,
    goal: str,
    race_date: str,
    thin: bool,
) -> dict[str, str] | None:
    """The this-week card. None when the phase or the goal is missing."""
    name = phase_name(phase)
    primary, secondary = capacities(phase)
    target = str(goal or "").strip()
    day = _shown_date(race_date)
    if not name or not primary or not target or not day:
        return None
    if isinstance(days_to_goal, bool) or not isinstance(days_to_goal, int) or days_to_goal < 0:
        return None
    collapsed = (
        f"You're in Phase {phase} — {name}. "
        f"This week's hard days train {primary}. "
        f"Easy days protect that work. "
        f"{days_to_goal} days to {target} on {day}."
    )
    beside = f" Hard days aim at {primary}"
    if secondary:
        beside += f" with {secondary} beside them."
    else:
        beside += "."
    expanded = (
        f"This week sits in phase {phase} because your season still needs {primary} before race day. "
        "Tuesday and Thursday are hard unless they are marked easy. "
        "Saturday is the long run. Easy days absorb the hard work."
        f"{beside} {phase_line(phase)} "
        "Hard-day marks can ease or advance later weeks. "
        "They do not rewrite this week after the fact."
    )
    if thin:
        expanded = f"{expanded} {THIN}"
    return {"collapsed": collapsed, "expanded": expanded, "title": "This week"}


def no_plan_copy() -> str:
    """Shown when there is no season to fill in."""
    return "Generate a season on Start. Then this note can name the phase and the goal."


def phase_outline() -> list[dict[str, str]]:
    """All eight phases. Collapsed is the title and one line."""
    rows = []
    for phase, name, line, rest in PHASES:
        primary, secondary = capacities(phase)
        rows.append(
            {
                "phase": str(phase),
                "title": f"Phase {phase} — {name}",
                "collapsed": line,
                "expanded": rest,
                "primary": primary,
                "secondary": secondary,
            }
        )
    return rows


def current_phase_note(phase: int) -> dict[str, str] | None:
    """One phase, not the whole list."""
    if not 1 <= phase <= 8:
        return None
    row = phase_outline()[phase - 1]
    return {
        "collapsed": f"{row['title']}. {row['collapsed']}",
        "expanded": f"{row['expanded']} {BRIDGE}",
    }


# What the phase before this one did. Display only. Present lines stay on PHASES.
_DID = {
    1: "built the engine and kept the fast reps short",
    2: "grew the base and stepped the short fast reps up",
    3: "brought in threshold and aerobic power, and kept speed in the week",
    4: "started the work that holds race pace when it hurts",
    5: "lengthened the specific reps and kept the aim on the 800",
    6: "built the kick and kept speed nearby",
    7: "made the week look like the race",
    8: "stayed short and fresh",
}
_DAY_ORDER = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)


def _day_list(days: list[str]) -> str:
    if len(days) == 1:
        return days[0]
    if len(days) == 2:
        return f"{days[0]} and {days[1]}"
    return ", ".join(days[:-1]) + f", and {days[-1]}"


def _session_role(session: dict) -> str:
    """Hard, easy, long run, race, or off. Read from the stored day."""
    template = str(session.get("template_id") or "").strip()
    codes = session.get("reason_codes") or []
    names = {str(code) for code in codes} if isinstance(codes, list) else set()
    if not template:
        return "off"
    if template == "rr_800_r0_x1":
        return "race"
    if "weekly_aerobic_long_run" in names:
        return "long"
    if template.startswith("aer_") or "extra_easy_day" in names or "extra_easy_week" in names:
        return "easy"
    return "hard"


def _phase_weeks(sessions: list, phase: int) -> list[int]:
    grouped: dict[int, list] = {}
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        week = session.get("week_number")
        if isinstance(week, bool) or not isinstance(week, int):
            continue
        grouped.setdefault(week, []).append(session)
    found = []
    for week in sorted(grouped):
        if _phase_in(grouped[week]) == phase:
            found.append(week)
    return found


def _week_roles(rows: list[dict]) -> dict[str, str]:
    """Each stored day in this week, plus Friday off when the week implies it."""
    present: dict[str, str] = {}
    for session in rows:
        day = str(session.get("day_of_week") or "").strip()
        if day not in _DAY_ORDER:
            continue
        present[day] = _session_role(session)
    if not present:
        return {}
    if (
        "Friday" not in present
        and "Saturday" in present
        and any(day in present for day in _DAY_ORDER[:5])
    ):
        present["Friday"] = "off"
    return present


def _role_sentences(rows: list[dict]) -> list[str]:
    """Hard and easy days from this week's stored sessions."""
    present = _week_roles(rows)
    if not present:
        return []
    groups = {"hard": [], "easy": [], "long": [], "race": [], "off": []}
    for day in _DAY_ORDER:
        role = present.get(day)
        if role is None:
            continue
        groups[role].append(day)
    sentences = []
    if groups["hard"]:
        verb = "is" if len(groups["hard"]) == 1 else "are"
        sentences.append(f"{_day_list(groups['hard'])} {verb} hard.")
    if groups["easy"]:
        verb = "is" if len(groups["easy"]) == 1 else "are"
        sentences.append(f"{_day_list(groups['easy'])} {verb} easy.")
    if groups["long"]:
        verb = "is" if len(groups["long"]) == 1 else "are"
        sentences.append(f"{_day_list(groups['long'])} {verb} the long run.")
    if groups["race"]:
        verb = "is" if len(groups["race"]) == 1 else "are"
        noun = "the race" if len(groups["race"]) == 1 else "races"
        sentences.append(f"{_day_list(groups['race'])} {verb} {noun}.")
    if groups["off"]:
        verb = "is" if len(groups["off"]) == 1 else "are"
        sentences.append(f"{_day_list(groups['off'])} {verb} off.")
    return sentences


def phase_story(
    *,
    phase: int,
    week: int,
    sessions: list,
    thin: bool = False,
) -> dict | None:
    """Where this week sits, what the phase does, then the phase on either side.

    The collapsed line is the because. The sentences are the expand.
    Times stay off this card. None when the phase is not one of the eight.
    """
    name = phase_name(phase)
    primary, _secondary = capacities(phase)
    if not name or not primary:
        return None
    if isinstance(week, bool) or not isinstance(week, int):
        week = -1
    span = _phase_weeks(sessions, phase)
    if week in span and len(span) == 1:
        place = ", the only week of this phase,"
    elif week in span:
        place = f", week {span.index(week) + 1} of {len(span)},"
    else:
        place = ""
    collapsed = (
        f"This week sits in phase {phase}{place} "
        f"because the season still needs {primary}."
    )
    sentences = []
    doing = phase_line(phase)
    aim = phase_rest(phase)
    if doing:
        sentences.append(doing if doing.endswith(".") else f"{doing}.")
    if aim and aim != doing:
        sentences.append(aim if aim.endswith(".") else f"{aim}.")
    sentences.extend(_role_sentences(_week_rows(sessions, week)))
    sentences.append("Hard-day marks can ease or advance later weeks.")
    sentences.append("They do not rewrite this week after the fact.")
    if phase > 1:
        previous = phase - 1
        sentences.append(f"The phase before was phase {previous}, {phase_name(previous)}.")
        sentences.append(f"It {_DID[previous]}.")
    if phase < 8:
        nxt = phase + 1
        sentences.append(f"The next phase is phase {nxt}, {phase_name(nxt)}.")
        following = phase_line(nxt)
        if following:
            sentences.append(following if following.endswith(".") else f"{following}.")
    if thin:
        sentences.append(THIN)
    focus_parts = []
    if doing:
        focus_parts.append(doing if doing.endswith(".") else f"{doing}.")
    if aim and aim != doing:
        focus_parts.append(aim if aim.endswith(".") else f"{aim}.")
    roles = _week_roles(_week_rows(sessions, week))
    days = []
    for day_name in _DAY_ORDER:
        role = roles.get(day_name)
        if not role:
            continue
        days.append({"day": day_name, "short": day_name[:3], "role": role})
    steps = []
    if phase > 1:
        steps.append(
            {"label": "Previous", "text": f"Phase {phase - 1}, {phase_name(phase - 1)}"}
        )
    steps.append({"label": "This", "text": f"Phase {phase}, {name}"})
    if phase < 8:
        steps.append({"label": "Next", "text": f"Phase {phase + 1}, {phase_name(phase + 1)}"})
    panel = {
        "headline": f"Phase {phase} — {name}",
        "focus": " ".join(focus_parts),
        "days": days,
        "steps": steps,
        "marks": (
            "Hard-day marks can ease or advance later weeks. "
            "They do not rewrite this week after the fact."
        ),
        "note": THIN if thin else "",
    }
    return {"collapsed": collapsed, "sentences": sentences, "panel": panel}


def _phase_in(sessions: list) -> int | None:
    found: list[int] = []
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        codes = session.get("reason_codes") or []
        if not isinstance(codes, list):
            continue
        for code in codes:
            text = str(code)
            if len(text) == 7 and text.startswith("phase_") and text[6] in "12345678":
                number = int(text[6])
                if number not in found:
                    found.append(number)
    if len(found) == 1:
        return found[0]
    return None


def _week_rows(sessions: list, week: int) -> list[dict]:
    rows = []
    for session in sessions or []:
        if isinstance(session, dict) and session.get("week_number") == week:
            rows.append(session)
    return rows


def _family(template_id: object) -> str:
    text = str(template_id or "")
    prefixes = (
        ("se_", "speed_endurance"),
        ("ap_", "aerobic_power"),
        ("an_", "anaerobic_capacity"),
        ("thr_", "threshold"),
        ("rr_", "race_readiness"),
        ("mv_", "max_velocity"),
        ("spd_", "speed"),
        ("aer_", "aerobic"),
    )
    for prefix, family in prefixes:
        if text.startswith(prefix):
            return family
    return ""


def _hard(session: dict) -> bool:
    if str(session.get("day_of_week") or "") not in _HARD_DAYS:
        return False
    return _family(session.get("template_id")) not in ("", "aerobic")


def later_effect(mark: str, phase: int) -> str:
    """What this mark does to later weeks. This week stays as written."""
    if mark == "on_track":
        return "unchanged"
    if mark == "not_hitting":
        return "next_week_easy" if phase <= 1 else "eased"
    if mark == "smashing":
        return "advanced" if phase < 7 else "unknown"
    return "unknown"


def result_band(mark: str) -> str:
    return _BAND.get(mark, "")


def workout_inputs(
    *,
    session: dict,
    plan_sessions: list,
    goal: str,
    race_date: str,
    days_to_goal: int,
    mark: str,
    result_detail: str,
    first_name: str = "",
) -> dict | None:
    """Reduced fields for one hard day. None when the day is not hard or the plan is thin."""
    if not isinstance(session, dict) or not _hard(session):
        return None
    week = session.get("week_number")
    if isinstance(week, bool) or not isinstance(week, int):
        return None
    phase = _phase_in(_week_rows(plan_sessions, week))
    if phase is None:
        return None
    band = result_band(mark)
    if not band:
        return None
    counts = {"planned": 0, "logged": 0, "on_track": 0, "fell_short": 0, "went_better": 0}
    for row in _week_rows(plan_sessions, week):
        if not _hard(row):
            continue
        counts["planned"] += 1
    counts["logged"] = 1
    counts[{"on_track": "on_track", "fell_short": "fell_short", "went_better": "went_better"}[band]] = 1
    family = _family(session.get("template_id"))
    payload = {
        "goal_800": str(goal or "").strip(),
        "race_date": _shown_date(race_date),
        "days_to_goal": days_to_goal,
        "phase": phase,
        "phase_name": phase_name(phase),
        "week_number": week,
        "session_date": str(session.get("date") or ""),
        "session_family": _FAMILY.get(family, family),
        "session_label": str(session.get("day_of_week") or ""),
        "planned_summary": str(session.get("target_outcome") or "").strip(),
        "result_band": band,
        "result_detail": str(result_detail or "").strip(),
        "pace_factor_before": None,
        "pace_factor_after": None,
        "pace_factor_delta": None,
        "hard_days_this_week": counts,
        "later_weeks_effect": later_effect(mark, phase),
        "easy_hr_note": None,
        "tone": "chase",
        "max_sentences": 4,
    }
    name = str(first_name or "").strip()
    if name:
        payload["athlete_first_name"] = name.split()[0]
    if not payload["goal_800"] or not payload["session_date"] or not payload["planned_summary"]:
        return None
    return payload
