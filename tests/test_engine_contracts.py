# test_engine_contracts.py — pinned inputs and outputs for a later API.

"""The golden file is the contract a FastAPI backend can check.

The same inputs must keep returning these outputs. Pace fractions,
phase lengths, and template choices are not free to drift.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.load import parse_fixture
from engines.classify import classify
from engines.explain import complete_insight, weekly_digest
from engines.ledger import Ledger
from engines.pace import FAMILY_FRACTION, workout_times
from engines.prescribe import load_menu, prescribe
from engines.season import adapt, sequence
from ui.auto_adapt import auto_adapt
from ui.insights import phase_story, workout_inputs
from ui.plan_store import dump_record, export_season
from ui.result import goal_seconds, judge

FIXTURE = ROOT / "tests" / "fixtures" / "contracts" / "engines.json"
START = date(2026, 4, 19)
GOAL_DAY = date(2027, 3, 19)
INPUTS = ("2:02.9", "2026-04-19", "1:55.0", "2027-03-19")
ON = date(2026, 6, 1)
FRACTIONS = {
    "mv": "0.82",
    "spd": "0.96",
    "rr": "1.00",
    "se": "1.03",
    "an": "1.06",
    "ap": "1.12",
    "thr": "1.18",
    "aer": "1.55",
}
PACE_IDS = (
    "mv_60_r120_x10",
    "spd_200_r180_x6",
    "rr_800_r0_x1",
    "se_400_r90_x6",
    "an_400_r45_x4",
    "ap_800_r90_x4",
    "thr_1600_r90_x3",
    "aer_5000_r0_x1",
)


def _sessions(plan: dict) -> list[dict]:
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
    ]


def _num(value: object) -> object:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {key: _num(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_num(item) for item in value]
    return value


def _adapted(plan: dict, week: int, outcome: str) -> dict:
    updated = adapt(plan, week, outcome)
    return {
        "week_number": week,
        "outcome": outcome,
        "season_length_weeks": updated["season_length_weeks"],
        "sessions": _sessions(updated),
    }


def _live() -> dict:
    plan = sequence(*INPUTS)
    canonical = {
        "inputs": list(INPUTS),
        "ontology_version": plan["ontology_version"],
        "season_length_weeks": plan["season_length_weeks"],
        "start_date": plan["start_date"],
        "sessions": _sessions(plan),
    }
    pace = []
    for template_id in PACE_IDS:
        row = workout_times(
            template_id,
            current_mark="2:02.9",
            goal_mark="1:55.0",
            start=START,
            goal_date=GOAL_DAY,
            on=ON,
        )
        pace.append({"template_id": template_id, "on": ON.isoformat(), "result": _num(row)})
    judge_cases = []
    for template_id, text, goal in (
        ("se_400_r90_x6", "57.5", "1:55.0"),
        ("se_400_r90_x6", "60, 60, 60", "1:55.0"),
        ("se_400_r90_x6", "54", "1:55.0"),
        ("se_400_r90_x6", "400m", "1:55.0"),
        ("se_400_r90_x6", "", "1:55.0"),
        ("aer_5000_r0_x1", "25:00", "1:55.0"),
    ):
        judge_cases.append(
            {
                "template_id": template_id,
                "text": text,
                "goal": goal,
                "result": judge(template_id, text, goal_seconds(goal)),
            }
        )
    tuesday = next(
        session
        for session in plan["sessions"]
        if session["week_number"] == 1 and session["day_of_week"] == "Tuesday"
    )
    bases: dict = {}
    updated, actuals, marks = auto_adapt(
        plan,
        [
            {
                "id": 44521,
                "date": tuesday["date"],
                "matched": True,
                "name": "Run",
                "reps": [None, 20, None],
                "template_id": tuesday["template_id"],
            }
        ],
        {},
        goal_seconds("1:55.0"),
        bases,
    )
    story = phase_story(phase=1, week=1, sessions=plan["sessions"], thin=False)
    note = workout_inputs(
        session=tuesday,
        plan_sessions=plan["sessions"],
        goal="1:55.0",
        race_date="2027-03-19",
        days_to_goal=100,
        mark="on_track",
        result_detail="57.5",
        first_name="Ada",
    )
    menu = [{"id": row["id"], "family": row["family"]} for row in load_menu()]
    menu.sort(key=lambda row: row["id"])
    prescribed = prescribe(Ledger(), date(2026, 4, 19))
    classified = []
    for path in sorted((ROOT / "tests" / "fixtures").glob("*.yml")):
        result = classify(parse_fixture(path.read_text(encoding="utf-8")))
        classified.append(
            {
                "file": path.name,
                "family": result["family"],
                "reason_codes": result["reason_codes"],
                "confidence": result["confidence"],
                "ontology_version": result["ontology_version"],
            }
        )
    return {
        "family_fraction": {key: format(value, "f") for key, value in FAMILY_FRACTION.items()},
        "canonical_season": canonical,
        "adapt_on_track_week_10": _adapted(plan, 10, "on_track"),
        "adapt_not_hitting_week_37": _adapted(plan, 37, "not_hitting"),
        "adapt_smashing_week_28": _adapted(plan, 28, "smashing"),
        "pace": pace,
        "judge": judge_cases,
        "auto_adapt": {
            "date": tuesday["date"],
            "template_id": tuesday["template_id"],
            "actual": actuals[tuesday["date"]],
            "marks": {str(key): value for key, value in marks.items()},
            "week_2_template_ids": [
                session["template_id"]
                for session in updated["sessions"]
                if session["week_number"] == 2
            ],
            "base_weeks": sorted(int(week) for week in bases),
        },
        "phase_story_week_1": story,
        "workout_inputs": note,
        "menu": menu,
        "prescribe_empty_ledger": [
            {
                "template_id": row["template_id"],
                "prescribed_on": row["prescribed_on"],
                "reason_codes": row["reason_codes"],
            }
            for row in prescribed["rows"]
        ],
        "classify_fixtures": classified,
        "dump_record": dump_record(
            {1: "on_track", 2: "not_hitting"},
            {
                "2026-04-21": {
                    "text": "57.5",
                    "numbers": [57.5],
                    "mark": "on_track",
                    "template_id": "se_400_r90_x6",
                    "intervals": "file.json",
                }
            },
            [{"id": "a", "date": "2026-04-21", "matched": True, "name": "Run"}],
        ),
    }


def test_quality_family_fractions_stay_put() -> None:
    """The eight pace fractions are the ones the pages already use."""
    found = {key: format(value, "f") for key, value in FAMILY_FRACTION.items()}
    if found != FRACTIONS:
        raise AssertionError(found)
    if set(FAMILY_FRACTION) != {"mv", "spd", "rr", "se", "an", "ap", "thr", "aer"}:
        raise AssertionError(set(FAMILY_FRACTION))


def test_engine_outputs_match_the_golden_file() -> None:
    """Season, adapt, pace, judge, templates, insights, and classify stay put."""
    if not FIXTURE.is_file():
        raise AssertionError("the engine contract fixture is missing")
    golden = json.loads(FIXTURE.read_text(encoding="utf-8"))
    live = _live()
    if set(live) != set(golden):
        raise AssertionError(sorted(set(live) ^ set(golden)))
    for key, value in live.items():
        if value != golden[key]:
            raise AssertionError(key)
    season = live["canonical_season"]
    if season["ontology_version"] != "v0.1" or season["season_length_weeks"] != 47:
        raise AssertionError(season["season_length_weeks"])
    if any("probability" in session or "readiness_score" in session for session in season["sessions"]):
        raise AssertionError("a generated session stored a score")
    if live["family_fraction"] != FRACTIONS:
        raise AssertionError(live["family_fraction"])
    if live["auto_adapt"]["marks"] != {"1": "smashing"}:
        raise AssertionError(live["auto_adapt"])
    if live["workout_inputs"] is None or "probability" in live["workout_inputs"]:
        raise AssertionError(live["workout_inputs"])
    if "readiness_score" in json.dumps(live["phase_story_week_1"]):
        raise AssertionError("the phase story grew a score")


def test_a_score_is_rejected_and_the_insight_call_does_not_run() -> None:
    """probability and readiness_score are not part of a season or a note."""
    plan = sequence(*INPUTS)
    scored = json.loads(json.dumps(plan))
    scored["probability"] = 0.2
    try:
        adapt(scored, 1, "on_track")
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("adapt accepted a probability")
    if "score" not in message:
        raise AssertionError(message)
    text = export_season(INPUTS, scored, {}, {})
    if "probability" in text or "readiness" in text:
        raise AssertionError("export kept a score")
    if complete_insight({}) is not None or complete_insight(None) is not None:
        raise AssertionError("a bad insight payload called the model")
    if weekly_digest({}) is not None or weekly_digest({"week_ended": False}) is not None:
        raise AssertionError("a live week asked for a digest")


def main() -> None:
    test_quality_family_fractions_stay_put()
    test_engine_outputs_match_the_golden_file()
    test_a_score_is_rejected_and_the_insight_call_does_not_run()
    print("engine contracts ok")


if __name__ == "__main__":
    main()
