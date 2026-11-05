# test_insights.py — authored this-week notes, and a hard-day reply that can be refused.

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import (
    complete_insight,
    insight_acceptable,
    insight_inputs_ok,
    weekly_digest,
    weekly_inputs_ok,
)
from ui.insights import (
    no_plan_copy,
    phase_outline,
    season_thesis,
    this_week_copy,
    workout_inputs,
)

_INPUTS = {
    "goal_800": "1:55",
    "race_date": "4 April 2027",
    "days_to_goal": 120,
    "phase": 4,
    "phase_name": "Speed endurance arrives",
    "week_number": 6,
    "session_date": "2026-12-01",
    "session_family": "speed endurance",
    "session_label": "Tuesday",
    "planned_summary": "Hit: reps near goal 800 pace (1:55) with the rest kept.",
    "result_band": "fell_short",
    "result_detail": "The reps were slow.",
    "pace_factor_before": None,
    "pace_factor_after": None,
    "pace_factor_delta": None,
    "hard_days_this_week": {
        "planned": 2,
        "logged": 1,
        "on_track": 0,
        "fell_short": 1,
        "went_better": 0,
    },
    "later_weeks_effect": "eased",
    "easy_hr_note": None,
    "tone": "chase",
    "max_sentences": 4,
}


def test_this_week_fills_the_plan_and_hides_without_one() -> None:
    card = this_week_copy(
        phase=4,
        days_to_goal=120,
        goal="1:55",
        race_date="2027-04-04",
        thin=True,
    )
    if card is None:
        raise AssertionError("a planned week produced no note")
    if "Phase 4 — Speed endurance arrives" not in card["collapsed"]:
        raise AssertionError(card["collapsed"])
    if "speed endurance and aerobic power" not in card["collapsed"]:
        raise AssertionError(card["collapsed"])
    if "120 days to 1:55 on 4 April 2027" not in card["collapsed"]:
        raise AssertionError(card["collapsed"])
    if "Connect Strava" not in card["expanded"]:
        raise AssertionError("a thin week hid the authored fallback")
    full = this_week_copy(
        phase=4,
        days_to_goal=120,
        goal="1:55",
        race_date="2027-04-04",
        thin=False,
    )
    if full is None or "Connect Strava" in full["expanded"]:
        raise AssertionError("a logged week still asked for Strava")
    thesis = season_thesis(current_mark="2:02", goal="1:55", race_date="2027-04-04")
    if thesis is None or "2:02" not in thesis["expanded"] or "1:55" not in thesis["collapsed"]:
        raise AssertionError(thesis)
    if this_week_copy(phase=0, days_to_goal=1, goal="1:55", race_date="2027-04-04", thin=False) is not None:
        raise AssertionError("a missing phase still wrote a week")
    if "Generate a season" not in no_plan_copy():
        raise AssertionError(no_plan_copy())
    rows = phase_outline()
    if len(rows) != 8 or rows[7]["title"] != "Phase 8 — Taper":
        raise AssertionError(rows[-1])


def test_home_shows_this_week_and_not_the_phase_library() -> None:
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    start = app.index("def page_dashboard(")
    page = app[start : app.index("\ndef ", start + 1)]
    if "_render_this_week(" not in page:
        raise AssertionError("home does not show this week")
    if "phase_outline(" in page or "explain(" in page:
        raise AssertionError("home renders every phase or calls the model")
    more = app[app.index("def page_more(") : app.index("def page_creators(")]
    if "phase_outline(" in more or "Insights" in more:
        raise AssertionError("More grew an insights hub")
    session = app[app.index("def page_session(") : app.index("\ndef ", app.index("def page_session(") + 1)]
    if "_show_stored_insight(" not in session or "explain(" in session:
        raise AssertionError("the session page does not keep the hard-day note")
    if '"viewed": False' not in app or 'st.button("Got it"' not in app:
        raise AssertionError("a hard-day note does not stay until it is seen")


def _good_reply() -> dict:
    return {
        "headline": "Tuesday fell short",
        "body": "Tuesday fell short. Later weeks eased. The goal stays 1:55.",
        "carry_forward": "",
        "used_result_band": "fell_short",
    }


def test_a_hard_day_reply_is_refused_when_it_breaks_the_rules() -> None:
    if insight_inputs_ok(_INPUTS) is not True:
        raise AssertionError("the reduced hard-day fields were refused")
    if insight_acceptable(_good_reply(), _INPUTS) is not True:
        raise AssertionError("a plain Chase note was refused")
    invented = _good_reply()
    invented["body"] = "Tuesday fell short. Later weeks eased. You ran 9 miles."
    if insight_acceptable(invented, _INPUTS) is not False:
        raise AssertionError("an invented number was kept")
    named = _good_reply()
    named["body"] = "Strava says Tuesday fell short. Later weeks eased."
    if insight_acceptable(named, _INPUTS) is not False:
        raise AssertionError("a service name was kept")
    wrong = _good_reply()
    wrong["used_result_band"] = "on_track"
    if insight_acceptable(wrong, _INPUTS) is not False:
        raise AssertionError("the reply ignored the result")
    leaked = dict(_INPUTS)
    leaked["strava_laps"] = [{"lat": 1}]
    if insight_inputs_ok(leaked) is not False:
        raise AssertionError("a lap list was allowed in")
    raw = json.dumps(_INPUTS).lower()
    if "strava" in raw or "gps" in raw:
        raise AssertionError("the reduced note still carries a stream")
    if complete_insight(leaked) is not None:
        raise AssertionError("a bad payload was sent on")
    if weekly_inputs_ok(dict(_INPUTS)) is not False:
        raise AssertionError("an open week was treated as finished")
    finished = dict(_INPUTS)
    finished["week_ended"] = False
    if weekly_digest(finished) is not None:
        raise AssertionError("a week that has not ended was written")


def test_workout_inputs_stay_reduced() -> None:
    session = {
        "date": "2026-12-01",
        "day_of_week": "Tuesday",
        "week_number": 6,
        "template_id": "se_400_r90_x6",
        "target_outcome": "Hit: reps near goal 800 pace (1:55) with the rest kept.",
        "reason_codes": ["phase_4", "phase_primary"],
    }
    payload = workout_inputs(
        session=session,
        plan_sessions=[session],
        goal="1:55",
        race_date="2027-04-04",
        days_to_goal=120,
        mark="not_hitting",
        result_detail="The reps were slow.",
        first_name="Chase",
    )
    if payload is None or payload.get("result_band") != "fell_short":
        raise AssertionError(payload)
    if payload.get("athlete_first_name") != "Chase":
        raise AssertionError(payload)
    if "strava" in json.dumps(payload).lower():
        raise AssertionError(payload)
    easy = dict(session)
    easy["template_id"] = "aer_8000_r0_x1"
    if workout_inputs(
        session=easy,
        plan_sessions=[easy],
        goal="1:55",
        race_date="2027-04-04",
        days_to_goal=10,
        mark="on_track",
        result_detail="",
    ) is not None:
        raise AssertionError("an easy day asked for a model note")


def main() -> None:
    test_this_week_fills_the_plan_and_hides_without_one()
    test_home_shows_this_week_and_not_the_phase_library()
    test_a_hard_day_reply_is_refused_when_it_breaks_the_rules()
    test_workout_inputs_stay_reduced()
    print("insights ok")


if __name__ == "__main__":
    main()
