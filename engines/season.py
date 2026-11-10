# season.py — 800 m season from start date to goal date. Rules only.

"""Season sequencer v0.1. 800 m only.

Inputs are the current 800 time, the start date, the goal 800 time, and the
goal date. The plan is an ordered list of sessions. Each session has a week
number, a day of the week, a calendar date, a frozen template id, reason
codes, and the target outcome that counts as a hit.

start_date is the first day of training. Each session is dated from that day
and its day of the week. Week 1 is the Sunday–Saturday week that contains
start_date, and days before start_date are left out. Later weeks are full
Sunday–Saturday weeks.

Quality days use the locked 800 m capacity weights. The phase menu is the
allowed set. The six-day week places Tuesday and Thursday quality, one
Saturday long run, and three aer_5000 recovery days. The long run starts
at 9.5 km and steps up 500 m a week to 15 km. When a quality day has more
than one eligible template, the higher primary-capacity weight wins, and
that session records capacity_weight.

No model. No spend. Prose spend stays capped at $25 in engines/explain.py.
This file does not write the exam file.
"""

from __future__ import annotations

import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.ledger import ONTOLOGY_VERSION, load_paper
from engines.prescribe import load_menu

# new * 10 <= previous * 11  is a rise of at most 10%.
_RISE_NUM = 11
_RISE_DEN = 10

# Saturday long run, shortest to longest. 500 m apart. Frozen menu ids.
# The first training week uses the first rung. Later training weeks step
# one rung up, hold at the last rung, or step one rung down. 8 km is not
# a Saturday long run.
_LONG_LADDER = tuple(f"aer_{meters}_r0_x1" for meters in range(9500, 15001, 500))
_LONG_INDEX = {template_id: index for index, template_id in enumerate(_LONG_LADDER)}
_LONG_RUNS = _LONG_LADDER

# Easy days the 10% rule may insert. They are frozen menu ids.
_HOLDS = ("aer_4000_r0_x1", "aer_5000_r0_x1", "aer_10000_r0_x1")

# Phases 1–7 are six sessions. Friday is the off day. Sunday, Monday, and
# Wednesday are the three easy runs. Tuesday and Thursday are quality.
# Saturday is the long run.
_WEEK_DAYS = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)
_EASY_DAYS = ("Sunday", "Monday", "Wednesday")
_QUALITY_DAYS = ("Tuesday", "Thursday")
_LONG_DAY = "Saturday"
_RECOVERY_ID = "aer_5000_r0_x1"
_STANDARD_DAYS = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Saturday",
)

# Phase 8 is the last 14 days (two whole weeks) when the season has them.
# One week is the taper when the season is one week, or eight weeks. Eight
# weeks is one week in every phase, so the second taper week would skip one.
_PHASE_8_WEEKS = 2

# Caps before extra weeks rotate through phases 1–4. From eight weeks up,
# phases 1–4 take leftover weeks before phases 5–7. A shorter season fills
# 7, then 6, then 5, and compresses phases 1–4 first.
_LATE_CAPS = ((7, 2), (6, 3), (5, 3))
_EARLY_CAPS = ((1, 4), (2, 3), (3, 3), (4, 3))

_PHASE_MENU = {
    1: (
        "aer_8000_r0_x1",
        "aer_10000_r0_x1",
        "mv_60_r120_x10",
        "spd_150_r150_x8",
    ),
    2: (
        "aer_8000_r0_x1",
        "spd_150_r150_x8",
        "mv_80_r180_x8",
    ),
    3: (
        "thr_1000_r60_x5",
        "thr_1200_r60_x4",
        "ap_600_r75_x6",
        "aer_8000_r0_x1",
    ),
    4: (
        "se_300_r75_x8",
        "ap_600_r75_x6",
        "aer_8000_r0_x1",
        "spd_150_r150_x8",
    ),
    5: (
        "se_400_r90_x6",
        "se_500_r120_x4",
        "ap_800_r90_x5",
        "ap_700_r90_x5",
    ),
    6: (
        "an_600_r180_x3",
        "an_400_r45_x6",
        "se_400_r90_x6",
        "spd_150_r150_x8",
    ),
    7: (
        "rr_400_r240_x2",
        "rr_300_r180_x3",
        "se_400_r90_x6",
    ),
    8: (
        "rr_200_r180_x4",
        "rr_300_r180_x3",
        "rr_800_r0_x1",
        "mv_60_r120_x10",
    ),
}

# Primary families, then secondary. Aerobic dose is 0. Every other family
# on the menu is dose 1, so hard-session load is the count of those sessions.
_PRIMARY = {
    1: {"aerobic"},
    2: {"aerobic"},
    3: {"threshold", "aerobic_power"},
    4: {"speed_endurance", "aerobic_power"},
    5: {"speed_endurance", "aerobic_power"},
    6: {"anaerobic_capacity"},
    7: {"race_readiness"},
    8: {"race_readiness", "max_velocity"},
}
_SECONDARY = {
    1: {"max_velocity", "speed"},
    2: {"max_velocity", "speed"},
    3: {"aerobic", "speed"},
    4: {"aerobic", "speed"},
    5: {"speed"},
    6: {"speed_endurance", "speed"},
    7: {"speed_endurance", "speed"},
    8: set(),
}

_PRIORITY = {
    "speed_endurance": "priority_speed_endurance",
    "aerobic_power": "priority_aerobic_power",
    "anaerobic_capacity": "priority_anaerobic_capacity",
}

# Locked 800 m weights from rio/v0.1/event_weights.yml. They sum to 1.
_LOCKED_800_WEIGHTS = {
    "speed_endurance": 0.28,
    "anaerobic_capacity": 0.18,
    "speed": 0.16,
    "aerobic_power": 0.16,
    "max_velocity": 0.10,
    "threshold": 0.07,
    "aerobic": 0.03,
    "race_readiness": 0.02,
}
_WEIGHTS_PATH = ROOT / "rio" / "v0.1" / "event_weights.yml"
_CACHED_WEIGHTS: dict[str, float] | None = None

# Same-weight templates keep the existing week-index rotation.
# Weight does not choose among them.
_SAME_WEIGHT_ORDER = {
    (3, "threshold"): ("thr_1000_r60_x5", "thr_1200_r60_x4"),
    (5, "speed_endurance"): (
        "se_400_r90_x6",
        "se_500_r120_x4",
        "se_400_r90_x6",
        "se_500_r120_x4",
    ),
    (5, "aerobic_power"): (
        "ap_800_r90_x5",
        "ap_700_r90_x5",
        "ap_700_r90_x5",
        "ap_800_r90_x5",
    ),
    (6, "anaerobic_capacity"): ("an_400_r45_x6", "an_600_r180_x3"),
    (8, "race_readiness"): ("rr_300_r180_x3", "rr_200_r180_x4"),
}

# One step along the frozen menu. Used only when a phase cannot move.
_HARDER = {
    "mv_60_r120_x10": "mv_80_r180_x8",
    "thr_1200_r60_x4": "thr_1000_r60_x5",
    "ap_600_r75_x6": "ap_700_r90_x5",
    "ap_700_r90_x5": "ap_800_r90_x5",
    "se_300_r75_x8": "se_400_r90_x6",
    "se_400_r90_x6": "se_500_r120_x4",
    "an_600_r180_x3": "an_400_r45_x6",
    "rr_200_r180_x4": "rr_300_r180_x3",
    "rr_300_r180_x3": "rr_400_r240_x2",
}
_REASON_ORDER = (
    "phase_1",
    "phase_2",
    "phase_3",
    "phase_4",
    "phase_5",
    "phase_6",
    "phase_7",
    "phase_8",
    "phase_primary",
    "phase_secondary",
    "weekly_aerobic_long_run",
    "priority_speed_endurance",
    "priority_aerobic_power",
    "priority_anaerobic_capacity",
    "capacity_weight",
    "ten_percent_hold",
    "ten_percent_easier_template",
    "extra_easy_day",
    "extra_easy_week",
    "harder_template",
    "moved_back_one_phase",
    "advanced_one_phase",
    "phase_8_freshness",
    "phase_8_no_hard_se_or_an",
)

_SESSION_FIELDS = (
    "week_number",
    "day_of_week",
    "date",
    "template_id",
    "reason_codes",
    "target_outcome",
)

_OUTCOMES = {
    "aer_4000_r0_x1": "Hit: one continuous very easy run. Truly easy.",
    "aer_5000_r0_x1": "Hit: one continuous easy run, talkable the whole way.",
    "aer_8000_r0_x1": "Hit: one continuous easy run, talkable, with no pace chase.",
    "aer_9500_r0_x1": "Hit: one continuous easy run, talkable.",
    "aer_10000_r0_x1": "Hit: one continuous easy run, talkable.",
    "aer_10500_r0_x1": "Hit: one continuous easy run, talkable.",
    "aer_11000_r0_x1": "Hit: one continuous easy run, talkable.",
    "aer_11500_r0_x1": "Hit: one continuous easy run, talkable.",
    "aer_12000_r0_x1": (
        "Hit: one continuous easy 12 km, still talkable, not a long threshold."
    ),
    "aer_12500_r0_x1": (
        "Hit: one continuous easy 12.5 km, still talkable, not a long threshold."
    ),
    "aer_13000_r0_x1": (
        "Hit: one continuous easy 13 km, still talkable, not a long threshold."
    ),
    "aer_13500_r0_x1": (
        "Hit: one continuous easy 13.5 km, still talkable, not a long threshold."
    ),
    "aer_14000_r0_x1": (
        "Hit: one continuous easy 14 km, still talkable, not a long threshold."
    ),
    "aer_14500_r0_x1": (
        "Hit: one continuous easy 14.5 km, still talkable, not a long threshold."
    ),
    "aer_15000_r0_x1": (
        "Hit: one continuous easy 15 km, still talkable, not a long threshold."
    ),
    "mv_60_r120_x10": (
        "Hit: fast reps from a rolling start. Form holds. Stop the set if form breaks."
    ),
    "mv_80_r180_x8": "Hit: short fast reps with full recovery. Form holds.",
    "spd_150_r150_x8": (
        "Hit: reps at or faster than goal 800 pace ({goal}) and rest stays long."
    ),
    "thr_1000_r60_x5": (
        "Hit: comfortably hard, short phrases possible, not goal 800 pace ({goal})."
    ),
    "thr_1200_r60_x4": "Hit: comfortably hard cruise reps, not a quality 800 day.",
    "ap_600_r75_x6": (
        "Hit: strong reps, slower than goal 800 pace ({goal}). Breathing is the limiter."
    ),
    "ap_700_r90_x5": "Hit: strong aerobic reps, not goal 800 pace ({goal}).",
    "ap_800_r90_x5": (
        "Hit: strong reps, clearly slower than goal 800 pace ({goal}). Not a race."
    ),
    "se_300_r75_x8": (
        "Hit: reps near goal 800 pace ({goal}), rest kept, last reps honest."
    ),
    "se_400_r90_x6": "Hit: reps near goal 800 pace ({goal}) with the rest kept.",
    "se_500_r120_x4": "Hit: reps near goal 800 pace ({goal}). Four reps is the cap.",
    "an_600_r180_x3": "Hit: hard reps completed with the full rest, under control.",
    "an_400_r45_x6": (
        "Hit: broken 800s near goal 800 pace ({goal}) or faster, short rest kept."
    ),
    "rr_200_r180_x4": (
        "Hit: four short reps at goal 800 pace ({goal}) with long rest. Sharp, not a fitness session."
    ),
    "rr_300_r180_x3": "Hit: three reps at goal 800 pace ({goal}), then stop.",
    "rr_400_r240_x2": (
        "Hit: two reps at goal 800 pace ({goal}) feel repeatable. Not a 6 × 400."
    ),
    "rr_800_r0_x1": "Hit: the 800 m race is run on pace for {goal}. Next day is easy or off.",
}

_TIME = re.compile(r"^(\d+):(\d{2})(\.\d+)?$")
_ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_WORK = re.compile(r"_(\d+)_r\d+_x(\d+)$")
_PHASE_CODE = re.compile(r"^phase_([1-8])$")
# Hits write the goal as "(1:55.0)" or, on the race, "for 1:55.0".
_GOAL_IN_TEXT = re.compile(
    r"(?:\(|\bfor )([0-9]+:[0-9]{2}(?:\.[0-9]+)?)\)?"
)

_BANNED_PHASE_8 = {"speed_endurance", "anaerobic_capacity"}
_RACE_SHARPEN = "rr_400_r240_x2"
_RACE_SE = "se_400_r90_x6"


def season_length_weeks(start_date, goal_date) -> int:
    """Whole weeks from the start date to the goal date."""
    start = _as_date(start_date, "start_date")
    goal = _as_date(goal_date, "goal_date")
    if goal < start:
        raise ValueError("goal_date is before start_date")
    return (goal - start).days // 7


def phase_lengths(weeks: int) -> list[int]:
    """Eight week-counts, phase 1 first.

    Phase 8 is one taper week when the season is one week or eight weeks,
    and the final two weeks otherwise. From eight weeks up, phases 1–7
    each get a week. Weeks still left stretch phases 1–4 up to their caps,
    then phases 5–7. Anything past the caps rotates through phases 1–4.
    A shorter season fills the taper, then phases 7, 6, and 5, and
    compresses phases 1–4.
    """
    if isinstance(weeks, bool) or not isinstance(weeks, int):
        raise ValueError("weeks is not a whole number")
    if weeks < 0:
        raise ValueError("weeks is negative")
    lengths = [0, 0, 0, 0, 0, 0, 0, 0]
    if weeks == 0:
        return lengths
    if weeks >= 8:
        taper = 1 if weeks == 8 else _PHASE_8_WEEKS
        lengths = [1, 1, 1, 1, 1, 1, 1, taper]
        rest = weeks - 7 - taper
        rest = _fill_caps(lengths, rest, _EARLY_CAPS)
        rest = _fill_caps(lengths, rest, _LATE_CAPS)
        _rotate_early(lengths, rest)
        return lengths
    lengths[7] = 1 if weeks == 1 else _PHASE_8_WEEKS
    rest = weeks - lengths[7]
    rest = _fill_caps(lengths, rest, _LATE_CAPS)
    rest = _fill_caps(lengths, rest, _EARLY_CAPS)
    _rotate_early(lengths, rest)
    return lengths


def _fill_caps(lengths: list[int], rest: int, caps: tuple[tuple[int, int], ...]) -> int:
    """Add weeks up to each cap, in the order given. Returns weeks still left."""
    for phase, cap in caps:
        take = min(cap - lengths[phase - 1], rest)
        lengths[phase - 1] += take
        rest -= take
    return rest


def _rotate_early(lengths: list[int], rest: int) -> None:
    """Give leftover weeks to phases 1–4, one phase at a time."""
    index = 0
    while rest:
        lengths[index % 4] += 1
        rest -= 1
        index += 1


def sequence(current_time, start_date, goal_time, goal_date) -> dict:
    """Build the season.

    The current time and the goal time are 800 m marks. They do not change
    which template is chosen. The goal time is what "hit" is measured against
    when the template is written against goal pace.
    """
    _parse_time(current_time, "current_time")
    goal = _parse_time(goal_time, "goal_time")
    start = _as_date(start_date, "start_date")
    weeks = season_length_weeks(start, goal_date)
    menu = _menu()
    phases = _expand(phase_lengths(weeks))
    built = _assemble(phases, menu)
    sessions = _sessions(built, goal, menu, start)
    plan = {
        "ontology_version": ONTOLOGY_VERSION,
        "season_length_weeks": weeks,
        "start_date": start.isoformat(),
        "sessions": sessions,
    }
    _check(plan, menu)
    _check_phases(plan, phases)
    return plan


def adapt(plan: dict, week_number: int, outcome) -> dict:
    """Apply one week of active adaptation to the weeks after `week_number`.

    On track leaves the rest of the plan as written. Not hitting moves future
    weeks back one phase, or makes the next week an easy week when the phase
    cannot move back. Smashing advances future weeks one phase, or steps a
    template up the frozen menu when the phase cannot advance. Phase 8 stays
    the final taper. The 10% rule still applies. The caller's plan is not changed.
    """
    menu = _menu()
    _check(plan, menu)
    copied = _copy_plan(plan)
    weeks = copied["season_length_weeks"]
    if isinstance(week_number, bool) or not isinstance(week_number, int):
        raise ValueError("week_number is not a whole number")
    if weeks == 0:
        return copied
    if not 1 <= week_number <= weeks:
        raise ValueError("week_number is outside the season")
    judgment = _judgment(outcome)
    if judgment == "on_track":
        return copied

    phases = _phases_from(copied)
    goal = _goal_from(copied)
    hooks: dict[int, str] = {}
    moved = False
    for index in range(week_number, weeks):
        current = phases[index]
        if judgment == "not_hitting":
            shifted = current if current == 8 else max(1, current - 1)
            code = "moved_back_one_phase"
        else:
            shifted = current if current >= 7 else current + 1
            code = "advanced_one_phase"
        if shifted != current:
            phases[index] = shifted
            hooks[index] = code
            moved = True
    if not moved:
        nxt = week_number  # first future week, 0-based index == week_number
        if nxt < weeks:
            if judgment == "not_hitting":
                hooks[nxt] = "extra_easy_week"
            else:
                for index in range(week_number, weeks):
                    hooks[index] = "harder_template"

    locked = _weeks_of(copied)[:week_number]
    start = _as_date(copied["start_date"], "start_date")
    # Days before start_date are already gone from week 1. The cap was applied
    # to that full week, so a rebuild of the following week uses the full week.
    rebuild_first = week_number == 1 and start > _sunday_on_or_before(start)
    built = _assemble(
        phases,
        menu,
        locked=locked,
        hooks=hooks,
        rebuild_first=rebuild_first,
    )
    # Judged weeks stay as written. Later weeks are rebuilt.
    sessions = _locked_sessions(copied, week_number) + _sessions(
        built[week_number:],
        goal,
        menu,
        start,
        first_week=week_number + 1,
    )
    updated = {
        "ontology_version": copied["ontology_version"],
        "season_length_weeks": weeks,
        "start_date": copied["start_date"],
        "sessions": sessions,
    }
    _check(updated, menu)
    return updated


def show_season(
    current_time="2:02.9",
    start_date: date | None = None,
    goal_time="1:55.0",
    goal_date: date | None = None,
) -> None:
    """Print one line per week for the goal in docs/goal.md."""
    start = date(2026, 4, 19) if start_date is None else start_date
    goal_day = date(2027, 3, 19) if goal_date is None else goal_date
    plan = sequence(current_time, start, goal_time, goal_day)
    menu = _menu()
    print(
        f"{plan['season_length_weeks']} weeks  {start.isoformat()} → {goal_day.isoformat()}"
    )
    grouped: dict[int, list[dict]] = {}
    for session in plan["sessions"]:
        grouped.setdefault(session["week_number"], []).append(session)
    for number in range(1, plan["season_length_weeks"] + 1):
        week = grouped.get(number)
        if not week:
            print(f"week {number:02d}  no session on or after {start.isoformat()}")
            continue
        ids = [session["template_id"] for session in week]
        phase = _one_phase(week, number)
        bits = [
            f"{session['date']} {session['day_of_week'][:3]} {session['template_id']}"
            for session in week
        ]
        print(
            f"week {number:02d}  phase {phase}  {_work(ids):5d} m  hard {_hard(ids, menu)}  {bits}"
        )


def _assemble(
    phases,
    menu,
    locked=None,
    hooks=None,
    rebuild_first: bool = False,
) -> list[dict]:
    """One dict per week: phase, ids, hold ids, and extra reason codes.

    `rebuild_first` rebuilds a calendar-cut week 1 so the 10% baseline stays
    the full week. The caller still emits the cut sessions.
    """
    locked = list(locked or [])
    hooks = dict(hooks or {})
    slots = _slots(phases)
    naturals = [_natural_volume(slot, menu) for slot in slots]
    needs = _volume_needs(slots, menu)
    built: list[dict] = []
    prev_volume = None
    prev_hard = None
    prev_long = None
    for index, slot in enumerate(slots):
        if index < len(locked) and not (rebuild_first and index == 0):
            ids = list(locked[index])
            row = {
                "phase": slot["phase"],
                "ids": ids,
                "holds": set(),
                "codes": set(),
            }
        else:
            nxt = naturals[index + 1] if index + 1 < len(naturals) else None
            # A shifted phase can ask for more quality than the cap allows.
            # Step back one phase at a time until the week fits. The 10% rule
            # wins over the phase move.
            phase_try = slot["phase"]
            hook_try = hooks.get(index, "")
            need_try = needs[index]
            row = None
            while row is None:
                attempt = dict(slot)
                attempt["phase"] = phase_try
                try:
                    row = _build_week(
                        attempt,
                        menu,
                        prev_volume,
                        prev_hard,
                        _future_peak(naturals, phases, index),
                        hook_try,
                        nxt,
                        prev_long,
                        need_try,
                    )
                except ValueError as exc:
                    if str(exc) != "no week fits the 10% rule" or phase_try <= 1:
                        raise
                    phase_try -= 1
                    hook_try = ""
                    need_try = 0
        built.append(row)
        prev_volume = _work(row["ids"])
        prev_hard = _hard(row["ids"], menu)
        prev_long = _long_in(row["ids"])
    return built


def _build_week(
    slot,
    menu,
    prev_volume,
    prev_hard,
    peak,
    hook: str,
    nxt,
    prev_long,
    need: int,
) -> dict:
    phase = slot["phase"]
    codes: set[str] = set()
    if hook in ("moved_back_one_phase", "advanced_one_phase"):
        codes.add(hook)
    if hook == "extra_easy_week" and phase == 8:
        easy, weighted = _easy_ids(slot, menu)
        # Skip the easy week when the next week's natural volume could not
        # return within 10%. The cap wins.
        if nxt is None or nxt * _RISE_DEN <= _work(easy) * _RISE_NUM:
            easy, dropped = _trim(easy, phase, menu, prev_volume, prev_hard)
            if dropped:
                codes.add("ten_percent_easier_template")
            codes.add("extra_easy_week")
            return _pack(easy, phase, menu, codes, weighted)
        hook = ""
    if phase == 8:
        ids, weighted = _natural_ids(slot, menu)
        if hook == "harder_template":
            hardened = _harden(ids, phase, menu, prev_volume, prev_hard)
            if hardened != ids:
                ids = hardened
                codes.add("harder_template")
        ids, dropped = _trim(ids, phase, menu, prev_volume, prev_hard)
        if dropped:
            codes.add("ten_percent_easier_template")
        return _pack(ids, phase, menu, codes, weighted)

    required, weighted = _natural_ids(slot, menu)
    required, dropped = _trim_hard(required, phase, menu, prev_hard)
    if dropped:
        codes.add("ten_percent_easier_template")
    quality = _cap_quality(required, phase, menu)
    floor = _floor_for(peak)
    base = _work(quality) + 3 * work_meters(_RECOVERY_ID)
    chosen = _best(
        quality,
        phase,
        prev_volume,
        prev_hard,
        floor,
        menu,
        prev_long,
        base,
        need,
    )
    if hook == "harder_template":
        hardened = _harden(chosen, phase, menu, prev_volume, prev_hard)
        if hardened != chosen:
            chosen = hardened
            codes.add("harder_template")
    if hook == "extra_easy_week":
        eased = _ease(chosen, phase, menu, prev_volume, prev_hard, floor)
        # Keep the cut only when the next week can still return within 10%.
        if eased != chosen and (nxt is None or nxt * _RISE_DEN <= _work(eased) * _RISE_NUM):
            chosen = eased
            codes.add("extra_easy_week")
    return _pack(chosen, phase, menu, codes, weighted)


def _easy_ids(slot: dict, menu) -> tuple[list[str], set[str]]:
    """Phase 8 drops the longer non-race session. The race stays."""
    ids, weighted = _natural_ids(slot, menu)
    if len(ids) < 2:
        return ids, weighted
    droppable = [template_id for template_id in ids if template_id != "rr_800_r0_x1"]
    victim = max(droppable, key=work_meters)
    return [template_id for template_id in ids if template_id != victim], weighted


def _pack(ids, phase, menu, codes: set[str], weight_capacities=None) -> dict:
    placed = _place(ids, phase, menu)
    return {
        "phase": phase,
        "ids": [template_id for _, template_id in placed],
        "days": [day for day, _ in placed],
        "holds": set(),
        "codes": codes,
        "weight_capacities": set(weight_capacities or ()),
    }


def _place(ids, phase, menu) -> list[tuple[str, str]]:
    """(day_of_week, template_id) in Sunday–Saturday order."""
    if phase == 8:
        return _place_taper(ids, menu)
    quality = _quality_in(ids, menu)
    longs = [template_id for template_id in ids if template_id in _LONG_RUNS]
    if len(quality) != 2 or len(longs) != 1:
        raise ValueError("week does not have two quality sessions and one long run")
    placed = {
        "Sunday": _RECOVERY_ID,
        "Monday": _RECOVERY_ID,
        "Tuesday": quality[0],
        "Wednesday": _RECOVERY_ID,
        "Thursday": quality[1],
        "Saturday": longs[0],
    }
    return [(day, placed[day]) for day in _STANDARD_DAYS]


def _place_taper(ids, menu) -> list[tuple[str, str]]:
    """Fewer sessions. Quality on Tuesday then Thursday. The race is Saturday."""
    race = [template_id for template_id in ids if template_id == "rr_800_r0_x1"]
    quality: list[str] = []
    easy_count = 0
    for template_id in ids:
        if template_id == "rr_800_r0_x1" or template_id in _LONG_RUNS:
            continue
        if template_id == _RECOVERY_ID or _family(template_id, menu) == "aerobic":
            easy_count += 1
            continue
        quality.append(template_id)
    placed: dict[str, str] = {}
    for day in ("Sunday", "Monday", "Wednesday", "Friday"):
        if easy_count <= 0:
            break
        placed[day] = _RECOVERY_ID
        easy_count -= 1
    for day, template_id in zip(_QUALITY_DAYS, quality):
        placed[day] = template_id
    if race:
        placed[_LONG_DAY] = race[0]
    if not placed:
        raise ValueError("taper week has no session")
    return [(day, placed[day]) for day in _WEEK_DAYS if day in placed]


def _quality_in(ids, menu) -> list[str]:
    return [
        template_id
        for template_id in ids
        if template_id not in _LONG_RUNS and _family(template_id, menu) != "aerobic"
    ]


def _cap_quality(ids, phase, menu) -> list[str]:
    """Tuesday and Thursday. A third hard session does not fit the week."""
    quality = _quality_in(ids, menu)
    while len(quality) > 2:
        victim = _drop_one(quality, phase, menu)
        if victim is None:
            return quality[:2]
        quality.remove(victim)
    return quality


def _ease(ids, phase, menu, prev_volume, prev_hard, floor) -> list[str]:
    """One easier step that keeps six sessions, two quality days, and the floor.

    The long run moves one 500 m rung down. It does not jump back to 8 km,
    and it does not go below 9.5 km.
    """
    chosen = list(ids)
    long_run = _long_in(chosen)
    if long_run is not None:
        lower = _lower_long(long_run)
        if lower != long_run and lower not in chosen:
            trial = [lower if template_id == long_run else template_id for template_id in chosen]
            if _work(trial) >= floor and _fits(trial, prev_volume, prev_hard, menu):
                chosen = trial
    easier = {harder: prior for prior, harder in _HARDER.items()}
    for index, template_id in enumerate(list(chosen)):
        prior = easier.get(template_id)
        if not prior or prior in chosen:
            continue
        if phase == 8 and _family(prior, menu) in _BANNED_PHASE_8:
            continue
        trial = list(chosen)
        trial[index] = prior
        if _RACE_SHARPEN in trial and _RACE_SE in trial:
            continue
        if _work(trial) >= floor and _fits(trial, prev_volume, prev_hard, menu):
            return trial
    return chosen


def _best(
    required,
    phase,
    prev_volume,
    prev_hard,
    _floor,
    menu,
    prev_long,
    base: int,
    need: int,
) -> list[str]:
    """Six-session week that keeps both quality days and fits 10%.

    The long run is the next 500 m step when that fits. A longer rung is
    used only when the next week could not be placed at 9.5 km otherwise.
    If the step would break the cap, last week's distance stays. Easing
    walks down one rung at a time and stops at 9.5 km. The floor does not
    stretch the long run: that would preload a later week onto this one.
    """
    candidates = _candidates(required, phase, prev_long, base, need)
    legal = [
        ids
        for ids in candidates
        if _fits(ids, prev_volume, prev_hard, menu)
        and not (_RACE_SHARPEN in ids and _RACE_SE in ids)
    ]
    if not legal:
        raise ValueError("no week fits the 10% rule")
    return min(legal, key=_candidate_key)


def _candidates(
    required: list[str],
    phase: int,
    prev_long: str | None,
    base: int,
    need: int,
) -> list[list[str]]:
    """Two quality sessions, three easy 5 km runs, and one long run.

    The first candidate is the 500 m step, or a higher rung when the next
    week needs it. The rest walk down to 9.5 km. Nothing above that target
    is offered, so a blocked step cannot skip ahead.
    """
    if phase >= 8:
        return []
    target = _target_long(prev_long, base, need)
    found: list[list[str]] = []
    recovery = [_RECOVERY_ID, _RECOVERY_ID, _RECOVERY_ID]
    index = _LONG_INDEX[target]
    while index >= 0:
        found.append(list(required) + recovery + [_LONG_LADDER[index]])
        index -= 1
    return found


def _candidate_key(ids: list[str]) -> tuple:
    # aer_4000 is the day-after-hard row. Use it only when no other easy day fits.
    # The longer legal long run wins: the step, else last week, else one
    # rung down. A shorter rung is not preferred.
    recovery = 1 if "aer_4000_r0_x1" in ids else 0
    long_run = _long_in(ids)
    progress = -work_meters(long_run) if long_run else 0
    return (recovery, progress, len(ids), tuple(ids))


def _trim_hard(required, phase, menu, prev_hard):
    required = list(required)
    dropped = False
    while prev_hard is not None and _hard(required, menu) * _RISE_DEN > prev_hard * _RISE_NUM:
        victim = _drop_one(required, phase, menu)
        if victim is None:
            break
        required.remove(victim)
        dropped = True
    return required, dropped


def _trim(ids, phase, menu, prev_volume, prev_hard):
    ids = list(ids)
    dropped = False
    while ids and not _fits(ids, prev_volume, prev_hard, menu):
        victim = _drop_one(
            [template_id for template_id in ids if template_id != "rr_800_r0_x1"],
            phase,
            menu,
        )
        if victim is None or victim not in ids:
            break
        ids.remove(victim)
        dropped = True
    if phase < 8 and _long_in(ids) is None:
        starter = _LONG_LADDER[0]
        if starter not in ids and _fits(ids + [starter], prev_volume, prev_hard, menu):
            ids.append(starter)
    return ids, dropped


def _drop_one(ids: list[str], phase: int, menu) -> str | None:
    """Drop secondary work before primary, and a hold before either."""
    if not ids:
        return None
    holds = [template_id for template_id in ids if template_id in _HOLDS]
    holds = [template_id for template_id in holds if template_id not in _PHASE_MENU[phase]]
    if holds:
        return max(holds, key=work_meters)
    ranked = sorted(ids, key=lambda template_id: _keep_rank(template_id, phase, menu))
    # Never drop the last primary if a lower rank exists.
    if len(ranked) == 1:
        return None
    return ranked[0]


def _keep_rank(template_id: str, phase: int, menu) -> tuple:
    family = _family(template_id, menu)
    if family in _PRIORITY and phase >= 4:
        band = 3
    elif family in _PRIMARY[phase]:
        band = 2
    elif family in _SECONDARY[phase]:
        band = 1
    else:
        band = 0
    return (band, -work_meters(template_id), template_id)


def _harden(ids, phase, menu, prev_volume, prev_hard) -> list[str]:
    chosen = list(ids)
    for index, template_id in enumerate(list(chosen)):
        nxt = _HARDER.get(template_id)
        if not nxt or nxt in chosen:
            continue
        if phase == 8 and _family(nxt, menu) in _BANNED_PHASE_8:
            continue
        trial = list(chosen)
        trial[index] = nxt
        if _RACE_SHARPEN in trial and _RACE_SE in trial:
            continue
        if _fits(trial, prev_volume, prev_hard, menu):
            return trial
    return chosen


def _capacity_weights() -> dict[str, float]:
    """Locked 800 m weights. The paper file is the source."""
    global _CACHED_WEIGHTS
    if _CACHED_WEIGHTS is not None:
        return _CACHED_WEIGHTS
    paper = load_paper(_WEIGHTS_PATH)
    block = None
    for key, value in paper.items():
        if str(key).strip().strip("\"'") == "800" and isinstance(value, dict):
            block = value
            break
    if block is None:
        raise ValueError("800 m weights are missing")
    if set(block) != set(_LOCKED_800_WEIGHTS):
        raise ValueError("800 m weights are not the locked capacities")
    weights: dict[str, float] = {}
    for name, expected in _LOCKED_800_WEIGHTS.items():
        value = block[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} weight is not a number")
        if abs(float(value) - expected) > 1e-9:
            raise ValueError(f"{name} weight is not the locked value")
        weights[name] = float(value)
    if abs(sum(weights.values()) - 1) > 1e-9:
        raise ValueError("800 m weights do not sum to 1")
    _CACHED_WEIGHTS = weights
    return weights


def _stimulus(template_id: str, menu) -> str:
    """Primary capacity of a frozen template."""
    template = menu[template_id]
    stimulus = template.get("primary_stimulus") or template["family"]
    if not isinstance(stimulus, str) or not stimulus.strip():
        raise ValueError(f"{template_id} has no primary capacity")
    return stimulus.strip()


def _quality_pool(phase: int, menu) -> list[str]:
    """Phase-menu templates that can fill Tuesday or Thursday."""
    pool = []
    for template_id in _PHASE_MENU[phase]:
        if template_id in _LONG_RUNS or template_id == "rr_800_r0_x1":
            continue
        if _family(template_id, menu) == "aerobic":
            continue
        pool.append(template_id)
    return pool


def _pair_ok(ids: list[str]) -> bool:
    return not (_RACE_SHARPEN in ids and _RACE_SE in ids)


def _choose_quality(slot: dict, menu) -> tuple[list[str], set[str]]:
    """Tuesday-then-Thursday quality ids, and capacities the weight picked.

    One capacity per quality day, highest locked weight first. A second
    template of a capacity already used is only taken when nothing else
    is eligible. Equal weights do not count as a weight decision.
    """
    phase = slot["phase"]
    pool = _quality_pool(phase, menu)
    count = 1 if phase == 8 and slot["last"] else 2
    chosen: list[str] = []
    used: list[str] = []
    weighted: set[str] = set()
    for _ in range(count):
        fresh = [
            template_id
            for template_id in pool
            if template_id not in chosen
            and _stimulus(template_id, menu) not in used
            and _pair_ok(chosen + [template_id])
        ]
        eligible = fresh
        repeated = False
        if not eligible:
            eligible = [
                template_id
                for template_id in pool
                if template_id not in chosen and _pair_ok(chosen + [template_id])
            ]
            repeated = True
        if not eligible:
            break
        groups: dict[str, list[str]] = {}
        for template_id in eligible:
            groups.setdefault(_stimulus(template_id, menu), []).append(template_id)
        capacity, decided = _winning_capacity(groups, phase, menu)
        if repeated:
            # Same capacity as a day already filled. Weight did not pick it.
            decided = False
        chosen.append(_rotate(groups[capacity], slot, phase, menu))
        used.append(capacity)
        if decided:
            weighted.add(capacity)
    if len(chosen) < count:
        raise ValueError(f"phase {phase} does not have enough quality templates")
    return chosen, weighted


def _winning_capacity(groups: dict[str, list[str]], phase: int, menu) -> tuple[str, bool]:
    """Highest 800 m weight. A tie is not a weight decision."""
    weights = _capacity_weights()

    def rank_weight(capacity: str) -> float:
        if capacity not in weights:
            raise ValueError(f"{capacity} has no 800 m weight")
        return weights[capacity]

    best = max(rank_weight(capacity) for capacity in groups)
    tied = [
        capacity
        for capacity in groups
        if abs(rank_weight(capacity) - best) < 1e-9
    ]
    # capacity_weight is recorded only when one capacity is strictly heavier.
    if len(tied) == 1 and len(groups) > 1:
        return tied[0], True
    if len(tied) == 1:
        return tied[0], False
    winner = max(
        tied,
        key=lambda capacity: max(
            _keep_rank(template_id, phase, menu) for template_id in groups[capacity]
        ),
    )
    return winner, False


def _rotate(candidates: list[str], slot: dict, phase: int, menu) -> str:
    """Pick one template inside a capacity. Weight does not do this."""
    if len(candidates) == 1:
        return candidates[0]
    family = _stimulus(candidates[0], menu)
    order = _SAME_WEIGHT_ORDER.get((phase, family))
    if order is None:
        order = [template_id for template_id in _PHASE_MENU[phase] if template_id in candidates]
    else:
        order = [template_id for template_id in order if template_id in set(candidates)]
    if not order:
        order = sorted(candidates)
    return order[slot["index"] % len(order)]


def _natural_ids(slot: dict, menu) -> tuple[list[str], set[str]]:
    """Quality templates for the week, Tuesday first, plus weight winners.

    The phase menu is the allowed set. Two quality days (one on the last
    taper week) take the higher primary-capacity weight when more than one
    template is eligible. The race is added on the last taper Saturday.
    """
    quality, weighted = _choose_quality(slot, menu)
    ids = list(quality)
    if slot["phase"] == 8 and slot["last"]:
        ids.append("rr_800_r0_x1")
    return ids, weighted


def _natural_volume(slot: dict, menu) -> int:
    """Volume of the week before the long run steps up.

    Phases 1–7 count two quality sessions, three easy 5 km runs, and the
    9.5 km long run. Later Saturday distance is decided week by week.
    Putting 15 km in here would make the floor preload that distance
    onto the early weeks.
    """
    if slot["phase"] >= 8:
        ids, _weighted = _natural_ids(slot, menu)
        quality = _cap_quality(ids, slot["phase"], menu)
        return _work(quality)
    return _training_base(slot, menu) + work_meters(_LONG_LADDER[0])


def _training_base(slot: dict, menu) -> int:
    """Quality plus three easy 5 km runs. The Saturday long run is separate."""
    ids, _weighted = _natural_ids(slot, menu)
    quality = _cap_quality(ids, slot["phase"], menu)
    return _work(quality) + 3 * work_meters(_RECOVERY_ID)


def _volume_needs(slots: list[dict], menu) -> list[int]:
    """Minimum volume each week must reach so the next week can exist.

    A training week's minimum is the 9.5 km long run. The requirement
    walks backward one week at a time, and only when the next training
    week would otherwise rise more than 10%. It does not jump the first
    week to 15 km to pay for a peak many weeks later.
    """
    needs: list[int] = []
    for slot in slots:
        if slot["phase"] >= 8:
            needs.append(0)
        else:
            needs.append(_training_base(slot, menu) + work_meters(_LONG_LADDER[0]))
    for index in range(len(slots) - 2, -1, -1):
        if slots[index]["phase"] >= 8 or slots[index + 1]["phase"] >= 8:
            continue
        required = (needs[index + 1] * _RISE_DEN + _RISE_NUM - 1) // _RISE_NUM
        if required > needs[index]:
            needs[index] = required
    return needs


def _long_in(ids) -> str | None:
    found = [template_id for template_id in ids if template_id in _LONG_INDEX]
    if not found:
        return None
    return found[-1]


def _step_long(prev_long: str | None) -> str:
    """Next Saturday distance. The first training week is 9.5 km."""
    if prev_long not in _LONG_INDEX:
        return _LONG_LADDER[0]
    index = _LONG_INDEX[prev_long]
    return _LONG_LADDER[min(index + 1, len(_LONG_LADDER) - 1)]


def _higher(template_id: str) -> str:
    index = _LONG_INDEX[template_id]
    return _LONG_LADDER[min(index + 1, len(_LONG_LADDER) - 1)]


def _lower_long(template_id: str) -> str:
    index = _LONG_INDEX.get(template_id)
    if index is None:
        return _LONG_LADDER[0]
    return _LONG_LADDER[max(index - 1, 0)]


def _target_long(prev_long: str | None, base: int, need: int) -> str:
    """The 500 m step, or the shortest higher rung the next week requires."""
    step = _step_long(prev_long)
    if need <= base + work_meters(step):
        return step
    target = step
    while base + work_meters(target) < need:
        nxt = _higher(target)
        if nxt == target:
            return target
        target = nxt
    return target


def _future_peak(naturals: list[int], phases: list[int], index: int) -> int:
    """Highest later natural volume before the taper.

    A drop is legal. It is not legal when it would make a later non-taper
    week jump more than 10%. Phase 8 is allowed to fall: freshness first.
    """
    peak = 0
    for later in range(index + 1, len(phases)):
        if phases[later] == 8:
            break
        if naturals[later] > peak:
            peak = naturals[later]
    return peak


def _floor_for(peak: int) -> int:
    if peak <= 0:
        return 0
    # Smallest volume whose 10% ceiling still reaches `peak`.
    return (peak * _RISE_DEN + _RISE_NUM - 1) // _RISE_NUM


def _sunday_on_or_before(day: date) -> date:
    """Sunday that opens the Sunday–Saturday week containing `day`."""
    return day - timedelta(days=(day.weekday() + 1) % 7)


def _session_day(start: date, week_number: int, day_name: str) -> date:
    """Calendar date of one session. Week 1 is the week that contains `start`."""
    anchor = _sunday_on_or_before(start)
    offset = (week_number - 1) * 7 + _WEEK_DAYS.index(day_name)
    return anchor + timedelta(days=offset)


def _sessions(
    weeks: list[dict],
    goal: str,
    menu,
    start: date,
    first_week: int = 1,
) -> list[dict]:
    sessions: list[dict] = []
    for offset, week in enumerate(weeks):
        number = first_week + offset
        phase = week["phase"]
        for day, template_id in zip(week["days"], week["ids"]):
            session_day = _session_day(start, number, day)
            # Week 1 keeps only the days on or after the first day of training.
            if session_day < start:
                continue
            codes = _codes(template_id, phase, week, menu)
            sessions.append(
                {
                    "week_number": number,
                    "day_of_week": day,
                    "date": session_day.isoformat(),
                    "template_id": template_id,
                    "reason_codes": codes,
                    "target_outcome": _outcome(template_id, goal),
                }
            )
    return sessions


def _locked_sessions(plan: dict, through_week: int) -> list[dict]:
    return [
        {
            "week_number": session["week_number"],
            "day_of_week": session["day_of_week"],
            "date": session["date"],
            "template_id": session["template_id"],
            "reason_codes": list(session["reason_codes"]),
            "target_outcome": session["target_outcome"],
        }
        for session in plan["sessions"]
        if session["week_number"] <= through_week
    ]


def _codes(template_id: str, phase: int, week: dict, menu) -> list[str]:
    family = _family(template_id, menu)
    codes = [f"phase_{phase}"]
    held = template_id in week["holds"]
    if held:
        codes.append("ten_percent_hold")
        codes.append("extra_easy_day")
    elif family in _PRIMARY[phase]:
        codes.append("phase_primary")
    elif family in _SECONDARY[phase]:
        codes.append("phase_secondary")
    if template_id in _LONG_RUNS and phase < 8:
        codes.append("weekly_aerobic_long_run")
    if phase >= 4 and family in _PRIORITY:
        codes.append(_PRIORITY[family])
    if _stimulus(template_id, menu) in week.get("weight_capacities", ()):
        codes.append("capacity_weight")
    if phase == 8:
        codes.append("phase_8_freshness")
        codes.append("phase_8_no_hard_se_or_an")
    for code in week["codes"]:
        if code not in codes:
            codes.append(code)
    return _ordered(codes)


def _outcome(template_id: str, goal: str) -> str:
    text = _OUTCOMES.get(template_id)
    if text is None:
        raise ValueError(f"no target outcome for {template_id}")
    return text.replace("{goal}", goal)


def _allowed(template_id: str, phase: int, codes: list[str]) -> bool:
    """Phase menu, the weekly long run, the easy 5 km, or an adaptation exception."""
    if template_id == _RECOVERY_ID:
        return True
    if phase == 8:
        return template_id in _PHASE_MENU[8]
    if template_id in _PHASE_MENU[phase] or template_id in _LONG_RUNS:
        return True
    if template_id in _HOLDS and (
        "ten_percent_hold" in codes or "extra_easy_week" in codes
    ):
        return True
    if "harder_template" in codes and template_id in _HARDER.values():
        return True
    if "extra_easy_week" in codes and template_id in _HARDER:
        return True
    return False


def _fits(ids, prev_volume, prev_hard, menu) -> bool:
    if prev_volume is None or prev_hard is None:
        return True
    if _work(ids) * _RISE_DEN > prev_volume * _RISE_NUM:
        return False
    if _hard(ids, menu) * _RISE_DEN > prev_hard * _RISE_NUM:
        return False
    return True


def _check(plan: dict, menu) -> None:
    if plan.get("ontology_version") != ONTOLOGY_VERSION:
        raise ValueError("ontology_version is not v0.1")
    if "probability" in plan or "readiness_score" in plan:
        raise ValueError("season plan has a score")
    weeks = plan["season_length_weeks"]
    if isinstance(weeks, bool) or not isinstance(weeks, int) or weeks < 0:
        raise ValueError("season_length_weeks is not a whole number")
    start = _as_date(plan.get("start_date"), "start_date")
    sessions = plan["sessions"]
    if not isinstance(sessions, list):
        raise ValueError("sessions is not a list")
    seen_weeks: list[int] = []
    seen_dates: set[str] = set()
    by_week: dict[int, list[dict]] = {}
    for session in sessions:
        if tuple(session) != _SESSION_FIELDS:
            raise ValueError("session fields are not the season fields")
        if "probability" in session or "readiness_score" in session:
            raise ValueError("session has a score")
        number = session["week_number"]
        if isinstance(number, bool) or not isinstance(number, int):
            raise ValueError("week_number is not a whole number")
        template_id = session["template_id"]
        if template_id not in menu:
            raise ValueError(f"{template_id} is not in the frozen menu")
        if session["day_of_week"] not in _WEEK_DAYS:
            raise ValueError(f"week {number} day is not Sunday–Saturday")
        text = session["date"]
        if not isinstance(text, str) or _ISO_DAY.fullmatch(text) is None:
            raise ValueError("session date is not YYYY-MM-DD")
        if text in seen_dates:
            raise ValueError("a session date is repeated")
        seen_dates.add(text)
        parsed = date.fromisoformat(text)
        expected_day = _session_day(start, number, session["day_of_week"])
        if parsed != expected_day or parsed < start:
            raise ValueError(
                f"week {number} {session['day_of_week']} is not {expected_day.isoformat()}"
            )
        phase_codes = [
            code for code in session["reason_codes"] if _PHASE_CODE.fullmatch(code)
        ]
        if len(phase_codes) == 1 and not _allowed(
            template_id, int(phase_codes[0][-1]), session["reason_codes"]
        ):
            raise ValueError(
                f"week {number} uses {template_id}, which that phase does not list"
            )
        if not session["reason_codes"]:
            raise ValueError(f"{template_id} has no reason codes")
        unknown = [
            code for code in session["reason_codes"] if code not in _REASON_ORDER
        ]
        if unknown:
            raise ValueError(f"unknown reason codes: {unknown}")
        outcome = session["target_outcome"]
        if not isinstance(outcome, str) or not outcome.startswith("Hit:"):
            raise ValueError(f"{template_id} has no target outcome")
        if number not in by_week:
            seen_weeks.append(number)
            by_week[number] = []
        by_week[number].append(session)
    expected_weeks = list(range(1, weeks + 1))
    if seen_weeks != expected_weeks:
        # Week 1 can disappear when every session day is before start_date.
        opener_cut = (
            weeks >= 2
            and seen_weeks == expected_weeks[1:]
            and start > _sunday_on_or_before(start)
        )
        if not opener_cut:
            raise ValueError("weeks are not 1..season_length_weeks in order")
    previous_volume = None
    previous_hard = None
    for number in range(1, weeks + 1):
        if number not in by_week:
            continue
        rows = by_week[number]
        ids = [row["template_id"] for row in rows]
        days = [row["day_of_week"] for row in rows]
        if len(days) != len(set(days)):
            raise ValueError(f"week {number} repeats a day")
        non_recovery = [template_id for template_id in ids if template_id != _RECOVERY_ID]
        if len(non_recovery) != len(set(non_recovery)):
            raise ValueError(f"week {number} repeats a template")
        if _RACE_SHARPEN in ids and _RACE_SE in ids:
            raise ValueError(f"week {number} pairs rr_400 with se_400")
        phase = _one_phase(rows, number)
        _check_shape(number, rows, phase, menu, start)
        volume = _work(ids)
        hard = _hard(ids, menu)
        if previous_volume is not None:
            if volume * _RISE_DEN > previous_volume * _RISE_NUM:
                raise ValueError(
                    f"week {number} volume {volume} rises more than 10% from {previous_volume}"
                )
            if hard * _RISE_DEN > previous_hard * _RISE_NUM:
                raise ValueError(
                    f"week {number} hard load {hard} rises more than 10% from {previous_hard}"
                )
        # The cap already bounded this week against the full opener. The days
        # before start_date are not a smaller training week.
        if _opener_fragment(number, phase, rows, start):
            continue
        previous_volume = volume
        previous_hard = hard


def _is_week_tail(days: list[str], expected: list[str]) -> bool:
    """True when `days` is `expected` with a Sunday-side prefix removed."""
    if len(days) > len(expected):
        return False
    if not days:
        return True
    return expected[-len(days) :] == days


def _tail_matches_start(
    number: int,
    days: list[str],
    expected: list[str],
    start: date,
) -> bool:
    if number != 1 or not _is_week_tail(days, expected):
        return False
    sunday = _sunday_on_or_before(start)
    kept = set(days)
    for day in expected:
        day_date = sunday + timedelta(days=_WEEK_DAYS.index(day))
        before = day_date < start
        if before and day in kept:
            return False
        if not before and day not in kept:
            return False
    return True


def _opener_fragment(number: int, phase: int, rows: list[dict], start: date) -> bool:
    """True when week 1 omits session days that fell before start_date."""
    if number != 1 or start <= _sunday_on_or_before(start):
        return False
    if phase < 8:
        days = [row["day_of_week"] for row in rows]
        return days != list(_STANDARD_DAYS)
    if not rows:
        return True
    first = min(date.fromisoformat(row["date"]) for row in rows)
    return first > start


def _check_shape(number: int, rows: list[dict], phase: int, menu, start: date) -> None:
    """Phases 1–7 are the six-day week. Phase 8 is a shorter taper.

    Week 1 may keep only the days on or after start_date.
    """
    ids = [row["template_id"] for row in rows]
    days = [row["day_of_week"] for row in rows]
    if phase == 8:
        if len(rows) >= 6:
            raise ValueError(f"week {number} taper is not shorter than six sessions")
        if any(template_id in _LONG_RUNS for template_id in ids):
            raise ValueError(f"week {number} keeps a long run in the taper")
        for template_id in ids:
            if _family(template_id, menu) in _BANNED_PHASE_8:
                raise ValueError(f"week {number} has hard work in the taper")
            if template_id != _RECOVERY_ID and template_id not in _PHASE_MENU[8]:
                raise ValueError(f"week {number} leaves the phase 8 menu")
        return
    expected = list(_STANDARD_DAYS)
    if days != expected and not _tail_matches_start(number, days, expected, start):
        raise ValueError(f"week {number} days are {days}")
    by_day = {row["day_of_week"]: row["template_id"] for row in rows}
    for day in _EASY_DAYS:
        if day not in by_day:
            if number == 1 and days != expected:
                continue
            raise ValueError(f"week {number} {day} is not the easy 5 km")
        if by_day[day] != _RECOVERY_ID:
            raise ValueError(f"week {number} {day} is not the easy 5 km")
    if by_day.get(_LONG_DAY) not in _LONG_RUNS:
        raise ValueError(f"week {number} Saturday is not the long run")
    for day in _QUALITY_DAYS:
        if day not in by_day:
            if number == 1 and days != expected:
                continue
            raise ValueError(f"week {number} {day} is not a quality session")
        template_id = by_day[day]
        if template_id in _LONG_RUNS or _family(template_id, menu) == "aerobic":
            raise ValueError(f"week {number} {day} is not a quality session")


def _check_phases(plan: dict, phases: list[int]) -> None:
    for session in plan["sessions"]:
        phase = _one_phase([session], session["week_number"])
        expected = phases[session["week_number"] - 1]
        if phase != expected:
            raise ValueError(
                f"week {session['week_number']} is phase {phase}, expected {expected}"
            )


def _one_phase(rows: list[dict], number: int) -> int:
    found = []
    for row in rows:
        for code in row["reason_codes"]:
            match = _PHASE_CODE.fullmatch(code)
            if match:
                found.append(int(match.group(1)))
    if len(set(found)) != 1:
        raise ValueError(f"week {number} does not have one phase")
    return found[0]


def _phases_from(plan: dict) -> list[int]:
    phases = []
    for number in range(1, plan["season_length_weeks"] + 1):
        rows = [
            session
            for session in plan["sessions"]
            if session["week_number"] == number
        ]
        if rows:
            phases.append(_one_phase(rows, number))
        else:
            phases.append(0)
    for index, phase in enumerate(phases):
        if phase != 0:
            continue
        # A whole opener can fall before start_date only in a taper week.
        if index != 0 or len(phases) < 2 or phases[1] != 8:
            raise ValueError(f"week {index + 1} has no sessions")
        phases[index] = 8
    return phases


def _weeks_of(plan: dict) -> list[list[str]]:
    weeks = []
    for number in range(1, plan["season_length_weeks"] + 1):
        weeks.append(
            [
                session["template_id"]
                for session in plan["sessions"]
                if session["week_number"] == number
            ]
        )
    return weeks


def _goal_from(plan: dict) -> str:
    for session in plan["sessions"]:
        match = _GOAL_IN_TEXT.search(session["target_outcome"])
        if match:
            return match.group(1)
    raise ValueError("plan is missing the goal time")


def _judgment(outcome) -> str:
    if isinstance(outcome, (list, tuple)):
        if not outcome:
            raise ValueError("outcome is empty")
        labels = [_one_judgment(item) for item in outcome]
        if "not_hitting" in labels:
            return "not_hitting"
        if "smashing" in labels:
            return "smashing"
        return "on_track"
    return _one_judgment(outcome)


def _one_judgment(outcome) -> str:
    if not isinstance(outcome, str):
        raise ValueError("outcome is not on_track, not_hitting, or smashing")
    text = outcome.strip().lower().replace(" ", "_").replace("-", "_")
    if text not in ("on_track", "not_hitting", "smashing"):
        raise ValueError("outcome is not on_track, not_hitting, or smashing")
    return text


def _expand(lengths: list[int]) -> list[int]:
    phases: list[int] = []
    for phase, count in enumerate(lengths, start=1):
        phases.extend([phase] * count)
    return phases


def _slots(phases: list[int]) -> list[dict]:
    totals = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    for phase in phases:
        totals[phase] += 1
    counts = [0, 0, 0, 0, 0, 0, 0, 0, 0]
    slots = []
    last = len(phases) - 1
    for index, phase in enumerate(phases):
        slots.append(
            {
                "phase": phase,
                "index": counts[phase],
                "count": totals[phase],
                "last": index == last,
            }
        )
        counts[phase] += 1
    return slots


def _copy_plan(plan: dict) -> dict:
    if not isinstance(plan, dict):
        raise ValueError("plan is not a season")
    return {
        "ontology_version": plan.get("ontology_version"),
        "season_length_weeks": plan.get("season_length_weeks"),
        "start_date": plan.get("start_date"),
        "sessions": [
            {
                "week_number": session["week_number"],
                "day_of_week": session["day_of_week"],
                "date": session["date"],
                "template_id": session["template_id"],
                "reason_codes": list(session["reason_codes"]),
                "target_outcome": session["target_outcome"],
            }
            for session in plan["sessions"]
        ],
    }


def work_meters(template_id: str) -> int:
    """Work distance written in a frozen id: reps times the rep length."""
    match = _WORK.search(template_id)
    if match is None:
        raise ValueError(f"{template_id} has no work distance")
    return int(match.group(1)) * int(match.group(2))


def _work(ids) -> int:
    return sum(work_meters(template_id) for template_id in ids)


def _hard(ids, menu) -> int:
    return sum(1 for template_id in ids if _family(template_id, menu) != "aerobic")


def _family(template_id: str, menu) -> str:
    if template_id not in menu:
        raise ValueError(f"{template_id} is not in the frozen menu")
    return menu[template_id]["family"]


def _family_of(template_id: str) -> str:
    """Family prefix on the id, used before a menu lookup is needed."""
    prefix = template_id.split("_", 1)[0]
    names = {
        "aer": "aerobic",
        "mv": "max_velocity",
        "spd": "speed",
        "thr": "threshold",
        "ap": "aerobic_power",
        "se": "speed_endurance",
        "an": "anaerobic_capacity",
        "rr": "race_readiness",
    }
    if prefix not in names:
        raise ValueError(f"{template_id} is not in the frozen menu")
    return names[prefix]


def _ordered(codes: list[str]) -> list[str]:
    rank = {code: index for index, code in enumerate(_REASON_ORDER)}
    return sorted(set(codes), key=lambda code: rank[code])


def _menu() -> dict:
    menu = {template["id"]: template for template in load_menu()}
    for phase, templates in _PHASE_MENU.items():
        for template_id in templates:
            if template_id not in menu:
                raise ValueError(f"{template_id} is not in the frozen menu")
    for template_id in (*_LONG_RUNS, *_HOLDS, *_HARDER, *_HARDER.values()):
        if template_id not in menu:
            raise ValueError(f"{template_id} is not in the frozen menu")
    return menu


def _parse_time(value, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} is not an 800 time")
    text = value.strip()
    match = _TIME.fullmatch(text)
    if match is None:
        raise ValueError(f"{name} is not an 800 time")
    seconds = int(match.group(1)) * 60 + int(match.group(2))
    if match.group(3):
        seconds += float(match.group(3))
    if seconds <= 0:
        raise ValueError(f"{name} is not an 800 time")
    return text


def _as_date(value, name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1]
        if _ISO_DAY.fullmatch(text):
            try:
                return date.fromisoformat(text)
            except ValueError:
                raise ValueError(f"{name} is not a calendar date") from None
        if "T" in text:
            return datetime.fromisoformat(text).date()
    raise ValueError(f"{name} is not a calendar date")


if __name__ == "__main__":
    show_season()
