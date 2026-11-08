# test_season.py — 800 m season length, phases, long run, and the 10% rule.

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.prescribe import load_menu
from engines.season import (
    _best,
    _ease,
    _menu,
    adapt,
    phase_lengths,
    season_length_weeks,
    sequence,
    work_meters,
)

EXAM = ROOT / "tests" / "labeled_sessions.yml"
START = date(2026, 4, 19)
GOAL_DAY = date(2027, 3, 19)
LONG_LADDER = [
    "aer_9500_r0_x1",
    "aer_10000_r0_x1",
    "aer_10500_r0_x1",
    "aer_11000_r0_x1",
    "aer_11500_r0_x1",
    "aer_12000_r0_x1",
    "aer_12500_r0_x1",
    "aer_13000_r0_x1",
    "aer_13500_r0_x1",
    "aer_14000_r0_x1",
    "aer_14500_r0_x1",
    "aer_15000_r0_x1",
]
LONG_RUNS = set(LONG_LADDER)
RECOVERY = "aer_5000_r0_x1"
WEEK_DAYS = {
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
}
STANDARD_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Saturday"]
EASY_DAYS = ("Sunday", "Monday", "Wednesday")
QUALITY_DAYS = ("Tuesday", "Thursday")
PHASE_8 = {
    "rr_200_r180_x4",
    "rr_300_r180_x3",
    "rr_800_r0_x1",
    "mv_60_r120_x10",
}
BANNED_TAPER = ("se_", "an_")


def _weeks(plan: dict) -> list[list[dict]]:
    grouped: dict[int, list[dict]] = {}
    for session in plan["sessions"]:
        grouped.setdefault(session["week_number"], []).append(session)
    return [grouped[number] for number in range(1, plan["season_length_weeks"] + 1)]


def _phase(week: list[dict]) -> int:
    found = set()
    for session in week:
        for code in session["reason_codes"]:
            if code.startswith("phase_") and code[-1].isdigit() and len(code) == 7:
                found.add(int(code[-1]))
    if len(found) != 1:
        raise AssertionError(f"week phase codes are {found}")
    return found.pop()


def _volume(week: list[dict]) -> int:
    return sum(work_meters(session["template_id"]) for session in week)


def _hard(week: list[dict], families: dict[str, str]) -> int:
    return sum(
        1
        for session in week
        if families[session["template_id"]] != "aerobic"
    )


def _ids(plan: dict) -> list[str]:
    return [session["template_id"] for session in plan["sessions"]]


def test_lengths() -> None:
    if season_length_weeks(START, GOAL_DAY) != 47:
        raise AssertionError("19 Apr 2026 to 19 Mar 2027 is not 47 whole weeks")
    if (GOAL_DAY - START).days != 334:
        raise AssertionError("the goal span is not 334 days")
    if phase_lengths(47) != [10, 9, 9, 9, 3, 3, 2, 2]:
        raise AssertionError(f"47 weeks allocated {phase_lengths(47)}")
    if phase_lengths(23) != [4, 3, 3, 3, 3, 3, 2, 2]:
        raise AssertionError(f"23 weeks allocated {phase_lengths(23)}")
    if phase_lengths(17) != [4, 3, 3, 2, 1, 1, 1, 2]:
        raise AssertionError(f"17 weeks allocated {phase_lengths(17)}")
    if phase_lengths(9) != [1, 1, 1, 1, 1, 1, 1, 2]:
        raise AssertionError(f"9 weeks allocated {phase_lengths(9)}")
    if phase_lengths(8) != [1, 1, 1, 1, 1, 1, 1, 1]:
        raise AssertionError(f"8 weeks allocated {phase_lengths(8)}")
    if phase_lengths(2) != [0, 0, 0, 0, 0, 0, 0, 2]:
        raise AssertionError("a two-week season is not all taper")
    if phase_lengths(1) != [0, 0, 0, 0, 0, 0, 0, 1]:
        raise AssertionError("a one-week season is not taper")
    if phase_lengths(0) != [0, 0, 0, 0, 0, 0, 0, 0]:
        raise AssertionError("an empty season allocated weeks")
    short = phase_lengths(6)
    long = phase_lengths(47)
    if sum(short[:4]) >= sum(long[:4]):
        raise AssertionError("a short season did not compress the early phases")
    if long[0] <= short[0] or long[5] != 3 or long[7] != 2:
        raise AssertionError("a long season did not stretch only the early phases")
    if sum(phase_lengths(47)) != 47:
        raise AssertionError("phase weeks do not add up")


def test_dates_and_times() -> None:
    try:
        sequence("2:02.9", GOAL_DAY, "1:55.0", START)
    except ValueError as exc:
        if "goal_date" not in str(exc):
            raise AssertionError("a reversed season was not named") from exc
    else:
        raise AssertionError("a reversed season was accepted")
    try:
        sequence("two minutes", START, "1:55.0", GOAL_DAY)
    except ValueError as exc:
        if "current_time" not in str(exc):
            raise AssertionError("a bad current time was not named") from exc
    else:
        raise AssertionError("a bad current time was accepted")
    empty = sequence("2:02.9", START, "1:55.0", START + timedelta(days=6))
    if empty["season_length_weeks"] != 0 or empty["sessions"]:
        raise AssertionError("a short-of-a-week season planned a week")


def test_plan_rules() -> None:
    exam = EXAM.read_text(encoding="utf-8")
    menu = {template["id"]: template for template in load_menu()}
    families = {template_id: template["family"] for template_id, template in menu.items()}
    slow = sequence("2:10.0", START, "1:55.0", GOAL_DAY)
    fast = sequence("1:58.0", START, "1:50.0", GOAL_DAY)
    if _ids(slow) != _ids(sequence("2:02.9", START, "1:55.0", GOAL_DAY)):
        raise AssertionError("current time changed the templates")
    if _ids(slow) != _ids(fast):
        raise AssertionError("goal time changed the templates")
    if slow["ontology_version"] != "v0.1":
        raise AssertionError("ontology_version is not v0.1")
    if "probability" in slow or "readiness_score" in slow:
        raise AssertionError("the season has a score")

    weeks = _weeks(slow)
    if len(weeks) != 47:
        raise AssertionError(f"the season has {len(weeks)} weeks")
    phases = [_phase(week) for week in weeks]
    if phases != [1] * 10 + [2] * 9 + [3] * 9 + [4] * 9 + [5] * 3 + [6] * 3 + [7] * 2 + [8] * 2:
        raise AssertionError(f"phases ran {phases}")

    previous_volume = None
    previous_hard = None
    long_ids: set[str] = set()
    for number, week in enumerate(weeks, start=1):
        ids = [session["template_id"] for session in week]
        for session in week:
            if tuple(session) != (
                "week_number",
                "day_of_week",
                "date",
                "template_id",
                "reason_codes",
                "target_outcome",
            ):
                raise AssertionError("session fields changed")
            named = (
                "Sunday",
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
            )
            try:
                held_day = date.fromisoformat(session["date"])
            except ValueError as exc:
                raise AssertionError("session date is not YYYY-MM-DD") from exc
            if session["date"] != held_day.isoformat():
                raise AssertionError("session date is not YYYY-MM-DD")
            if named[(held_day.weekday() + 1) % 7] != session["day_of_week"]:
                raise AssertionError(f"week {number} date does not match the day")
            if held_day < START:
                raise AssertionError("a session is before the start date")
            if session["template_id"] not in menu:
                raise AssertionError(f"{session['template_id']} left the menu")
            if not session["reason_codes"]:
                raise AssertionError(f"week {number} has no reason codes")
            if not session["target_outcome"].startswith("Hit:"):
                raise AssertionError(f"week {number} has no hit")
            if "probability" in session or "readiness_score" in session:
                raise AssertionError("a session has a score")
        phase = phases[number - 1]
        if phase < 8:
            longs = [template_id for template_id in ids if template_id in LONG_RUNS]
            if len(longs) != 1:
                raise AssertionError(f"week {number} has {longs}")
            if "weekly_aerobic_long_run" not in _codes(week, longs[0]):
                raise AssertionError(f"week {number} long run has no reason")
            long_ids.add(longs[0])
        else:
            if any(template_id in LONG_RUNS for template_id in ids):
                raise AssertionError(f"taper week {number} kept a long run")
            if any(template_id.startswith(BANNED_TAPER) for template_id in ids):
                raise AssertionError(f"taper week {number} has hard specific work")
            if any(template_id not in PHASE_8 for template_id in ids):
                raise AssertionError(f"taper week {number} left the phase 8 menu")
            if "phase_8_freshness" not in week[0]["reason_codes"]:
                raise AssertionError("taper week does not name freshness")
        _assert_week_shape(number, week, phase, families)
        if "rr_400_r240_x2" in ids and "se_400_r90_x6" in ids:
            raise AssertionError(f"week {number} pairs the sharpen with 6 × 400")
        volume = _volume(week)
        hard = _hard(week, families)
        if previous_volume is not None:
            if volume * 10 > previous_volume * 11:
                raise AssertionError(
                    f"week {number} volume {volume} is more than 10% over {previous_volume}"
                )
            if hard * 10 > previous_hard * 11:
                raise AssertionError(
                    f"week {number} hard load {hard} is more than 10% over {previous_hard}"
                )
        previous_volume = volume
        previous_hard = hard

    if long_ids != LONG_RUNS:
        raise AssertionError(f"long runs used were {sorted(long_ids)}")
    if "aer_8000_r0_x1" in long_ids:
        raise AssertionError("8 km was used as a Saturday long run")
    if weeks[-1][-1]["template_id"] != "rr_800_r0_x1":
        raise AssertionError("the last session is not the 800")
    if "1:55.0" not in weeks[-1][-1]["target_outcome"]:
        raise AssertionError("the race hit does not name the goal time")
    if "1:50.0" not in _weeks(fast)[-1][-1]["target_outcome"]:
        raise AssertionError("the other goal time was not written into the hit")

    phase_4 = [week for week in weeks if _phase(week) == 4]
    if any("spd_150_r150_x8" in _id_list(week) for week in phase_4):
        raise AssertionError("phase 4 added a third hard session")
    opening = {session["day_of_week"]: session for session in phase_4[0]}
    if opening["Tuesday"]["template_id"] != "se_300_r75_x8":
        raise AssertionError("phase 4 Tuesday is not speed endurance")
    if "capacity_weight" not in opening["Tuesday"]["reason_codes"]:
        raise AssertionError("phase 4 did not record the weight choice")
    if opening["Thursday"]["template_id"] != "ap_600_r75_x6":
        raise AssertionError("phase 4 Thursday did not keep aerobic power")
    if "capacity_weight" in opening["Thursday"]["reason_codes"]:
        raise AssertionError("equal weights were marked as a weight choice")
    if any(
        session["template_id"].startswith(("se_", "an_"))
        for week in weeks
        if _phase(week) == 8
        for session in week
    ):
        raise AssertionError("phase 8 contains speed endurance or anaerobic work")

    specific = [week for week in weeks if _phase(week) in (4, 5, 6)]
    for week in specific:
        families_present = {families[session["template_id"]] for session in week}
        if not families_present & {
            "speed_endurance",
            "aerobic_power",
            "anaerobic_capacity",
        }:
            raise AssertionError(f"specific week missed the 800 priorities: {_id_list(week)}")

    if EXAM.read_text(encoding="utf-8") != exam:
        raise AssertionError("labeled_sessions.yml was changed")


def _codes(week: list[dict], template_id: str) -> list[str]:
    for session in week:
        if session["template_id"] == template_id:
            return session["reason_codes"]
    raise AssertionError(f"{template_id} is missing")


def _id_list(week: list[dict]) -> list[str]:
    return [session["template_id"] for session in week]


def _assert_week_shape(number: int, week: list[dict], phase: int, families: dict) -> None:
    days = [session["day_of_week"] for session in week]
    ids = [session["template_id"] for session in week]
    if any(day not in WEEK_DAYS for day in days):
        raise AssertionError(f"week {number} has a day outside Sunday–Saturday")
    if len(days) != len(set(days)):
        raise AssertionError(f"week {number} repeats a day")
    repeated = [template_id for template_id in ids if template_id != RECOVERY]
    if len(repeated) != len(set(repeated)):
        raise AssertionError(f"week {number} repeats a template")
    if phase == 8:
        if len(week) >= 6:
            raise AssertionError(f"taper week {number} is not shorter")
        if any(template_id in LONG_RUNS for template_id in ids):
            raise AssertionError(f"taper week {number} kept a long run")
        return
    if days != STANDARD_DAYS:
        raise AssertionError(f"week {number} days are {days}")
    by_day = {session["day_of_week"]: session["template_id"] for session in week}
    for day in EASY_DAYS:
        if by_day[day] != RECOVERY:
            raise AssertionError(f"week {number} {day} is {by_day[day]}")
    if by_day["Saturday"] not in LONG_RUNS:
        raise AssertionError(f"week {number} Saturday is {by_day['Saturday']}")
    for day in QUALITY_DAYS:
        template_id = by_day[day]
        if families[template_id] == "aerobic" or template_id in LONG_RUNS:
            raise AssertionError(f"week {number} {day} is not quality")


def test_calendar_dates() -> None:
    full = sequence("2:02.9", START, "1:55.0", GOAL_DAY)
    if full["start_date"] != START.isoformat():
        raise AssertionError("start_date was not kept")
    if full["sessions"][0]["date"] != "2026-04-19":
        raise AssertionError("a Sunday start did not open on the start date")
    previous = None
    for session in full["sessions"]:
        held = date.fromisoformat(session["date"])
        if previous is not None and held <= previous:
            raise AssertionError("sessions are not in date order")
        if held > GOAL_DAY:
            raise AssertionError("a session is after the goal date")
        previous = held

    wednesday = date(2026, 4, 22)
    partial = sequence("2:02.9", wednesday, "1:55.0", GOAL_DAY)
    if partial["season_length_weeks"] != full["season_length_weeks"]:
        raise AssertionError("a mid-week start changed the season length")
    opener = _weeks(partial)[0]
    if [session["day_of_week"] for session in opener] != [
        "Wednesday",
        "Thursday",
        "Saturday",
    ]:
        raise AssertionError("week 1 kept days before the start date")
    if [session["date"] for session in opener] != [
        "2026-04-22",
        "2026-04-23",
        "2026-04-25",
    ]:
        raise AssertionError("week 1 dates are not the calendar days")
    full_weeks = _weeks(full)
    part_weeks = _weeks(partial)
    opener_by_day = {
        session["day_of_week"]: session["template_id"] for session in full_weeks[0]
    }
    for session in opener:
        if session["template_id"] != opener_by_day[session["day_of_week"]]:
            raise AssertionError("week 1 changed a template")
    for number, (whole, cut) in enumerate(zip(full_weeks, part_weeks), start=1):
        if number == 1:
            continue
        if _id_list(whole) != _id_list(cut):
            raise AssertionError(f"week {number} templates changed")
        if _phase(whole) < 8 and [session["day_of_week"] for session in cut] != STANDARD_DAYS:
            raise AssertionError(f"week {number} is not a full Sunday–Saturday week")
        sunday = START + timedelta(weeks=number - 1)
        for session in cut:
            index = (
                "Sunday",
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
            ).index(session["day_of_week"])
            if session["date"] != (sunday + timedelta(days=index)).isoformat():
                raise AssertionError(f"week {number} date does not match the day")
    if adapt(partial, 6, "on track")["sessions"] != partial["sessions"]:
        raise AssertionError("on track changed a partial first week")

    friday = date(2026, 4, 24)
    short = sequence("2:02.9", friday, "1:55.0", friday + timedelta(days=14))
    if short["season_length_weeks"] != 2:
        raise AssertionError("14 days was not two weeks")
    if any(session["week_number"] == 1 for session in short["sessions"]):
        raise AssertionError("week 1 kept a session before the start date")
    if short["sessions"][0]["week_number"] != 2:
        raise AssertionError("training did not resume the next Sunday")
    if short["sessions"][0]["date"] != "2026-04-28":
        raise AssertionError("the next week did not open on Tuesday")
    for session in short["sessions"]:
        if date.fromisoformat(session["date"]) < friday:
            raise AssertionError("a taper session is before the start date")
    if adapt(short, 1, "on track")["sessions"] != short["sessions"]:
        raise AssertionError("on track changed an empty opener")
    moved = adapt(short, 1, "not_hitting")
    if any(session["week_number"] == 1 for session in moved["sessions"]):
        raise AssertionError("adaptation restored days before the start date")
    if any(date.fromisoformat(session["date"]) < friday for session in moved["sessions"]):
        raise AssertionError("adaptation dated a session before the start date")


def test_quality_weights() -> None:
    """Higher primary-capacity weight wins a quality day. Equal weights do not."""
    plan = sequence("2:02.9", START, "1:55.0", GOAL_DAY)
    weeks = _weeks(plan)
    by_phase: dict[int, list[list[dict]]] = {}
    for week in weeks:
        by_phase.setdefault(_phase(week), []).append(week)

    def day(week: list[dict], name: str) -> dict:
        for session in week:
            if session["day_of_week"] == name:
                return session
        raise AssertionError(f"{name} is missing")

    # speed 0.16 over max velocity 0.10. Thursday has nothing left to compare.
    first = by_phase[1][0]
    if day(first, "Tuesday")["template_id"] != "spd_150_r150_x8":
        raise AssertionError("phase 1 Tuesday did not prefer speed")
    if "capacity_weight" not in day(first, "Tuesday")["reason_codes"]:
        raise AssertionError("phase 1 Tuesday did not record the weight")
    if day(first, "Thursday")["template_id"] != "mv_60_r120_x10":
        raise AssertionError("phase 1 Thursday is not max velocity")
    if "capacity_weight" in day(first, "Thursday")["reason_codes"]:
        raise AssertionError("phase 1 Thursday recorded a weight it did not use")
    if "capacity_weight" in day(first, "Sunday")["reason_codes"]:
        raise AssertionError("the easy day recorded a quality-day weight")
    if "capacity_weight" in day(first, "Saturday")["reason_codes"]:
        raise AssertionError("the long run recorded a quality-day weight")

    # aerobic power 0.16 over threshold 0.07. Same-weight threshold rotation stays.
    if day(by_phase[3][0], "Tuesday")["template_id"] != "ap_600_r75_x6":
        raise AssertionError("phase 3 Tuesday did not prefer aerobic power")
    if "capacity_weight" not in day(by_phase[3][0], "Tuesday")["reason_codes"]:
        raise AssertionError("phase 3 Tuesday did not record the weight")
    if day(by_phase[3][0], "Thursday")["template_id"] != "thr_1000_r60_x5":
        raise AssertionError("phase 3 did not keep the threshold rotation")
    if day(by_phase[3][1], "Thursday")["template_id"] != "thr_1200_r60_x4":
        raise AssertionError("phase 3 did not alternate threshold templates")
    if "capacity_weight" in day(by_phase[3][0], "Thursday")["reason_codes"]:
        raise AssertionError("phase 3 Thursday recorded a weight it did not use")

    # speed endurance 0.28 then aerobic power 0.16. Rotation inside the weight stays.
    fifth = [(_id_list(week)[2], _id_list(week)[4]) for week in by_phase[5]]
    if fifth != [
        ("se_400_r90_x6", "ap_800_r90_x5"),
        ("se_500_r120_x4", "ap_700_r90_x5"),
        ("se_400_r90_x6", "ap_700_r90_x5"),
    ]:
        raise AssertionError(f"phase 5 rotation changed: {fifth}")
    if "capacity_weight" not in day(by_phase[5][0], "Tuesday")["reason_codes"]:
        raise AssertionError("phase 5 Tuesday did not record the weight")
    if "capacity_weight" in day(by_phase[5][0], "Thursday")["reason_codes"]:
        raise AssertionError("phase 5 Thursday recorded a weight it did not use")

    # speed endurance 0.28, then anaerobic 0.18 over speed 0.16.
    if day(by_phase[6][0], "Tuesday")["template_id"] != "se_400_r90_x6":
        raise AssertionError("phase 6 Tuesday did not prefer speed endurance")
    if day(by_phase[6][0], "Thursday")["template_id"] != "an_400_r45_x6":
        raise AssertionError("phase 6 Thursday did not prefer anaerobic capacity")
    if day(by_phase[6][1], "Thursday")["template_id"] != "an_600_r180_x3":
        raise AssertionError("phase 6 did not alternate anaerobic templates")
    if any("spd_150_r150_x8" in _id_list(week) for week in by_phase[6]):
        raise AssertionError("phase 6 kept the lower-weight speed day")
    for name in ("Tuesday", "Thursday"):
        if "capacity_weight" not in day(by_phase[6][0], name)["reason_codes"]:
            raise AssertionError(f"phase 6 {name} did not record the weight")

    # Race readiness is 0.02. Speed endurance stays on both pre-comp weeks.
    # rr_400 cannot share a week with se_400.
    for week in by_phase[7]:
        ids = _id_list(week)
        if "se_400_r90_x6" not in ids or "rr_300_r180_x3" not in ids:
            raise AssertionError(f"phase 7 did not prefer speed endurance: {ids}")
        if "rr_400_r240_x2" in ids:
            raise AssertionError("phase 7 paired the sharpen with speed endurance")
        if "capacity_weight" not in day(week, "Tuesday")["reason_codes"]:
            raise AssertionError("phase 7 Tuesday did not record the weight")

    # Taper quality prefers max velocity 0.10 over race readiness 0.02.
    # The race stays on the last Saturday.
    taper = by_phase[8]
    if day(taper[0], "Tuesday")["template_id"] != "mv_60_r120_x10":
        raise AssertionError("taper Tuesday did not prefer max velocity")
    if "capacity_weight" not in day(taper[0], "Tuesday")["reason_codes"]:
        raise AssertionError("taper Tuesday did not record the weight")
    if day(taper[0], "Thursday")["template_id"] != "rr_300_r180_x3":
        raise AssertionError("taper Thursday is not the race-readiness touch")
    if "capacity_weight" in day(taper[0], "Thursday")["reason_codes"]:
        raise AssertionError("taper Thursday recorded a weight it did not use")
    if day(taper[1], "Tuesday")["template_id"] != "mv_60_r120_x10":
        raise AssertionError("race week quality did not prefer max velocity")
    if day(taper[1], "Saturday")["template_id"] != "rr_800_r0_x1":
        raise AssertionError("the race left Saturday")
    if "capacity_weight" in day(taper[1], "Saturday")["reason_codes"]:
        raise AssertionError("the race recorded a quality-day weight")


def _saturday(week: list[dict]) -> dict:
    for session in week:
        if session["day_of_week"] == "Saturday":
            return session
    raise AssertionError("Saturday is missing")


def test_saturday_long_run_buildup() -> None:
    """9.5 km, then 500 m a week, hold at 15 km. Phase 8 has no long run."""
    menu = {template["id"] for template in load_menu()}
    if not LONG_RUNS <= menu:
        raise AssertionError("a Saturday long run is not on the frozen menu")
    if work_meters("aer_9500_r0_x1") != 9500 or work_meters("aer_15000_r0_x1") != 15000:
        raise AssertionError("work_meters did not read the long-run id")
    plan = sequence("2:02.9", START, "1:55.0", GOAL_DAY)
    weeks = _weeks(plan)
    distances: list[int] = []
    for number, week in enumerate(weeks, start=1):
        phase = _phase(week)
        saturday = _saturday(week) if any(session["day_of_week"] == "Saturday" for session in week) else None
        if phase == 8:
            if saturday and saturday["template_id"] in LONG_RUNS:
                raise AssertionError(f"taper week {number} kept a long run")
            continue
        if saturday is None:
            raise AssertionError(f"week {number} has no Saturday")
        template_id = saturday["template_id"]
        if template_id not in LONG_RUNS or template_id == "aer_8000_r0_x1":
            raise AssertionError(f"week {number} Saturday is {template_id}")
        if "weekly_aerobic_long_run" not in saturday["reason_codes"]:
            raise AssertionError(f"week {number} long run has no reason")
        outcome = saturday["target_outcome"]
        if "talkable" not in outcome:
            raise AssertionError(f"week {number} outcome is {outcome}")
        meters = work_meters(template_id)
        if meters >= 12000 and "not a long threshold" not in outcome:
            raise AssertionError(f"week {number} outcome is {outcome}")
        if meters < 12000 and "not a long threshold" in outcome:
            raise AssertionError(f"week {number} outcome is {outcome}")
        ids = _id_list(week)
        if ids.count(template_id) != 1:
            raise AssertionError(f"week {number} repeats {template_id}")
        distances.append((meters, _volume(week)))
    if distances[0][0] != 9500:
        raise AssertionError(f"week 1 Saturday is {distances[0][0]} m")
    for (previous, prev_volume), (current, volume) in zip(distances, distances[1:]):
        if current - previous > 500:
            raise AssertionError(f"the long run jumped from {previous} to {current}")
        if current == previous + 500:
            continue
        if current == previous:
            if current != 15000:
                step = volume + 500
                if step * 10 <= prev_volume * 11:
                    raise AssertionError(f"held at {current} m without a 10% conflict")
            continue
        if current < previous:
            if current < 9500:
                raise AssertionError(f"the long run went below 9.5 km to {current}")
            # One rung longer would break the cap. The drop is no bigger than that.
            longer = volume + 500
            if longer * 10 <= prev_volume * 11:
                raise AssertionError(
                    f"eased from {previous} to {current} when {current + 500} still fit"
                )
            continue
        raise AssertionError(f"the long run moved from {previous} to {current}")
    if all(meters != 15000 for meters, _volume in distances):
        raise AssertionError("a full season never reached 15 km")
    if distances[-1][0] != 15000:
        raise AssertionError("the last training week did not hold 15 km")

    wednesday = date(2026, 4, 22)
    partial = sequence("2:02.9", wednesday, "1:55.0", GOAL_DAY)
    opener = _weeks(partial)[0]
    if _saturday(opener)["template_id"] != "aer_9500_r0_x1":
        raise AssertionError("a mid-week start changed the first Saturday")

    short = sequence("2:02.9", START, "1:55.0", START + timedelta(days=21))
    short_weeks = _weeks(short)
    if _phase(short_weeks[0]) >= 8:
        raise AssertionError("a three-week season had no training week")
    if _saturday(short_weeks[0])["template_id"] != "aer_9500_r0_x1":
        raise AssertionError("a short season did not start at 9.5 km")
    if any(session["template_id"] == "aer_15000_r0_x1" for week in short_weeks for session in week):
        raise AssertionError("a three-week season jumped to 15 km")
    for week in short_weeks:
        if _phase(week) == 8 and any(session["template_id"] in LONG_RUNS for session in week):
            raise AssertionError("the short taper kept a long run")


def test_long_run_stays_or_steps_down_one_rung() -> None:
    """A blocked step keeps last week. An ease moves 500 m, not back to 8 km."""
    menu = _menu()
    quality = ["spd_150_r150_x8", "mv_60_r120_x10"]
    base = work_meters("spd_150_r150_x8") + work_meters("mv_60_r120_x10") + 3 * work_meters(RECOVERY)
    # 10.5 km does not fit. 10 km does. A longer rung is not chosen.
    kept = _best(quality, 1, 24600, 2, 0, menu, "aer_10000_r0_x1", base, 0)
    if "aer_10500_r0_x1" in kept or "aer_12000_r0_x1" in kept or "aer_8000_r0_x1" in kept:
        raise AssertionError(f"a blocked step jumped to {kept}")
    if kept.count("aer_10000_r0_x1") != 1:
        raise AssertionError(f"the week did not keep 10 km: {kept}")

    week = quality + [RECOVERY, RECOVERY, RECOVERY, "aer_12000_r0_x1"]
    eased = _ease(week, 1, menu, None, None, 0)
    if "aer_11500_r0_x1" not in eased or "aer_12000_r0_x1" in eased:
        raise AssertionError(f"ease did not step down 500 m: {eased}")
    if "aer_8000_r0_x1" in eased or "aer_9500_r0_x1" in eased:
        raise AssertionError(f"ease jumped down the ladder: {eased}")
    held = _ease(week, 1, menu, None, None, 10**9)
    if "aer_12000_r0_x1" not in held:
        raise AssertionError("ease stepped down through the floor")
    floor = _ease(quality + [RECOVERY, RECOVERY, RECOVERY, "aer_9500_r0_x1"], 1, menu, None, None, 0)
    if "aer_9500_r0_x1" not in floor or "aer_8000_r0_x1" in floor:
        raise AssertionError(f"ease went below 9.5 km: {floor}")


def test_seventeen_week_season() -> None:
    goal = START + timedelta(days=17 * 7)
    plan = sequence("2:02.9", START, "1:55.0", goal)
    if plan["season_length_weeks"] != 17:
        raise AssertionError("119 days was not 17 weeks")
    phases = [_phase(week) for week in _weeks(plan)]
    if phases != [1] * 4 + [2] * 3 + [3] * 3 + [4] * 2 + [5, 6, 7] + [8] * 2:
        raise AssertionError(f"a 17-week season skipped a phase: {phases}")


def test_short_season() -> None:
    plan = sequence("2:02.9", START, "1:55.0", START + timedelta(days=14))
    weeks = _weeks(plan)
    if [ _phase(week) for week in weeks ] != [8, 8]:
        raise AssertionError("14 days was not two taper weeks")
    if any(session["template_id"] in LONG_RUNS for week in weeks for session in week):
        raise AssertionError("the taper kept a long run")
    if weeks[1][-1]["template_id"] != "rr_800_r0_x1":
        raise AssertionError("the race is not in the last week")
    if _volume(weeks[1]) * 10 > _volume(weeks[0]) * 11:
        raise AssertionError("taper week 2 rose more than 10%")


def test_adaptation() -> None:
    plan = sequence("2:02.9", START, "1:55.0", GOAL_DAY)
    held = adapt(plan, 10, "on track")
    if held["sessions"] != plan["sessions"]:
        raise AssertionError("on track changed the plan")
    if plan["sessions"][0]["template_id"] != sequence(
        "2:02.9", START, "1:55.0", GOAL_DAY
    )["sessions"][0]["template_id"]:
        raise AssertionError("adapt changed the caller's plan")

    moved = adapt(plan, 37, "not_hitting")
    moved_phases = [_phase(week) for week in _weeks(moved)]
    # Week 37 is the last phase-4 week. Later specific weeks step back.
    # The taper stays put.
    if moved_phases[37:] != [4, 4, 4, 5, 5, 5, 6, 6, 8, 8]:
        raise AssertionError(f"not hitting moved to {moved_phases[37:]}")
    if moved_phases[:37] != [_phase(week) for week in _weeks(plan)[:37]]:
        raise AssertionError("not hitting rewrote the judged weeks")
    _assert_ten_percent(moved)

    smashed = adapt(plan, 28, "Smashing")
    smashed_phases = [_phase(week) for week in _weeks(smashed)]
    # Week 28 is the last phase-3 week. Phase 4 advances. Phase 7 cannot
    # become the taper early, and phase 8 stays the last two weeks.
    if smashed_phases[28:] != [5] * 9 + [6] * 3 + [7] * 5 + [8] * 2:
        raise AssertionError(f"smashing moved to {smashed_phases[28:]}")
    _assert_ten_percent(smashed)

    same = adapt(plan, 47, ["not hitting", "smashing"])
    if same["sessions"] != plan["sessions"]:
        raise AssertionError("the last week changed the finished season")


def _assert_ten_percent(plan: dict) -> None:
    menu = {template["id"]: template["family"] for template in load_menu()}
    weeks = _weeks(plan)
    previous_volume = None
    previous_hard = None
    for number, week in enumerate(weeks, start=1):
        volume = _volume(week)
        hard = _hard(week, menu)
        if previous_volume is not None and volume * 10 > previous_volume * 11:
            raise AssertionError(f"adapted week {number} broke the volume cap")
        if previous_hard is not None and hard * 10 > previous_hard * 11:
            raise AssertionError(f"adapted week {number} broke the hard-load cap")
        phase = _phase(week)
        ids = _id_list(week)
        if phase < 8 and sum(template_id in LONG_RUNS for template_id in ids) != 1:
            raise AssertionError(f"adapted week {number} lost its one long run")
        if phase == 8 and any(template_id.startswith(BANNED_TAPER) for template_id in ids):
            raise AssertionError("adapted taper added hard specific work")
        _assert_week_shape(number, week, phase, menu)
        for session in week:
            if session["template_id"] not in menu:
                raise AssertionError("adapt invented a template")
        previous_volume = volume
        previous_hard = hard


if __name__ == "__main__":
    test_lengths()
    test_dates_and_times()
    test_plan_rules()
    test_calendar_dates()
    test_quality_weights()
    test_saturday_long_run_buildup()
    test_long_run_stays_or_steps_down_one_rung()
    test_seventeen_week_season()
    test_short_season()
    test_adaptation()
    print("season ok")
