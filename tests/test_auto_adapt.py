# test_auto_adapt.py — a matched quality day judges WORK times and adapts later weeks.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import SPEND_CAP_MICRO_USD
from engines.season import adapt, sequence
from ui.auto_adapt import auto_adapt
from ui.plan_store import dump_record, load_record
from ui.result import goal_seconds

START = date(2026, 4, 19)
GOAL_DAY = date(2027, 3, 19)
GOAL = goal_seconds("1:55.0")


def _plan() -> dict:
    return sequence("2:02.9", START, "1:55.0", GOAL_DAY)


def _session(plan: dict, week: int, weekday: str) -> dict:
    for session in plan["sessions"]:
        if session["week_number"] == week and session["day_of_week"] == weekday:
            return session
    raise AssertionError(f"week {week} has no {weekday}")


def _activity(session: dict, ident: object, reps: object, *, matched: bool = True) -> dict:
    row = {
        "id": ident,
        "date": session["date"],
        "matched": matched,
        "name": "Run",
        "reps": reps,
        "probability": 0.4,
        "readiness": 3,
    }
    if matched:
        row["template_id"] = session["template_id"]
    return row


def _ids(plan: dict, week: int) -> list[str]:
    return [
        session["template_id"]
        for session in plan["sessions"]
        if session["week_number"] == week
    ]


def _function(source: str, name: str) -> str:
    marker = f"def {name}("
    start = source.index(marker)
    nxt = source.find("\ndef ", start + len(marker))
    if nxt < 0:
        return source[start:]
    return source[start:nxt]


def test_a_quality_day_uses_work_times_and_adapts_later_weeks() -> None:
    """Tuesday WORK times become the mark. The judged week stays. Later weeks move."""
    plan = _plan()
    tuesday = _session(plan, 1, "Tuesday")
    bases: dict = {}
    sessions = plan["sessions"]
    blank: dict = {}
    updated, actuals, marks = auto_adapt(
        plan,
        [_activity(tuesday, 44521, [None, 20, None])],
        blank,
        GOAL,
        bases,
    )
    if plan["sessions"] is not sessions or blank:
        raise AssertionError("auto-adapt changed the caller's plan or actuals")
    row = actuals.get(tuesday["date"])
    if row is None or row["mark"] != "smashing" or row["numbers"] != [20]:
        raise AssertionError(row)
    if row["template_id"] != tuesday["template_id"] or row.get("intervals") != "44521":
        raise AssertionError(row)
    if None not in row["slots"] or 20.0 not in row["slots"]:
        raise AssertionError("a missing rep was not kept empty")
    if "probability" in row or "readiness" in row:
        raise AssertionError("a score was stored with the mark")
    if marks != {1: "smashing"}:
        raise AssertionError(marks)
    if _ids(updated, 1) != _ids(plan, 1):
        raise AssertionError("adapt changed the judged week")
    if updated["sessions"] != adapt(plan, 1, "smashing")["sessions"]:
        raise AssertionError("later weeks did not follow adapt()")
    stored = load_record(dump_record(marks, actuals))
    kept = stored[1].get(tuesday["date"])
    if kept is None or kept["mark"] != "smashing" or kept["numbers"] != [20]:
        raise AssertionError(kept)
    if "probability" in str(stored).lower() or "readiness" in str(stored).lower():
        raise AssertionError("the record stored a score")
    again, actuals_again, marks_again = auto_adapt(
        updated,
        [_activity(tuesday, 44521, [20])],
        actuals,
        GOAL,
        bases,
    )
    if marks_again or again["sessions"] != updated["sessions"]:
        raise AssertionError("a second match adapted the same week again")
    if actuals_again.get(tuesday["date"])["numbers"] != [20]:
        raise AssertionError("the stored times were replaced")
    stacked = adapt(updated, 1, "smashing")
    if stacked["sessions"] == updated["sessions"]:
        raise AssertionError("the double-adapt check no longer moves")


def test_not_hitting_wins_and_a_hand_mark_stays() -> None:
    """A stored mark is not replaced. not_hitting still wins the week."""
    plan = _plan()
    tuesday = _session(plan, 1, "Tuesday")
    thursday = _session(plan, 1, "Thursday")
    hand = {
        "text": "21.5",
        "numbers": [21.5],
        "mark": "on_track",
        "template_id": tuesday["template_id"],
    }
    bases: dict = {}
    smashed, after_smash, smash_marks = auto_adapt(
        plan,
        [_activity(tuesday, "tue", [None, 20])],
        {},
        GOAL,
        bases,
    )
    if smash_marks != {1: "smashing"}:
        raise AssertionError(smash_marks)
    combined, actuals, marks = auto_adapt(
        smashed,
        [
            _activity(tuesday, "tue", [20]),
            _activity(thursday, "thu", [9.5, None]),
        ],
        after_smash,
        GOAL,
        bases,
    )
    if actuals[tuesday["date"]]["numbers"] != [20] or actuals[tuesday["date"]]["mark"] != "smashing":
        raise AssertionError("the first day's mark was overwritten")
    if actuals[thursday["date"]]["mark"] != "not_hitting" or actuals[thursday["date"]]["numbers"] != [9.5]:
        raise AssertionError(actuals[thursday["date"]])
    if marks != {1: "not_hitting"}:
        raise AssertionError(marks)
    direct = adapt(plan, 1, "not_hitting")
    stacked = adapt(smashed, 1, "not_hitting")
    if combined["sessions"] != direct["sessions"]:
        raise AssertionError("the week was not judged from the plan before its results")
    if combined["sessions"] == stacked["sessions"]:
        raise AssertionError("not_hitting was applied on top of smashing")
    if _ids(combined, 1) != _ids(plan, 1):
        raise AssertionError("the judged week moved")
    held, held_actuals, held_marks = auto_adapt(
        plan,
        [_activity(tuesday, "hand", [20])],
        {tuesday["date"]: dict(hand)},
        GOAL,
        {},
    )
    if held_marks or held["sessions"] != plan["sessions"]:
        raise AssertionError("a hand-set mark called adapt()")
    if held_actuals[tuesday["date"]] != hand:
        raise AssertionError(held_actuals[tuesday["date"]])


def test_on_track_leaves_later_weeks() -> None:
    """Inside 3% stores on_track and does not move a later week."""
    plan = _plan()
    tuesday = _session(plan, 1, "Tuesday")
    updated, actuals, marks = auto_adapt(
        plan,
        [_activity(tuesday, "steady", [21.56])],
        {},
        "1:55.0",
        {},
    )
    row = actuals.get(tuesday["date"])
    if row is None or row["mark"] != "on_track" or marks != {1: "on_track"}:
        raise AssertionError((row, marks))
    if updated["sessions"] != plan["sessions"]:
        raise AssertionError("on_track changed a later week")


def test_recovery_long_run_extra_and_empty_reps_do_not_adapt() -> None:
    """Those activities store nothing and leave the plan where it is."""
    plan = _plan()
    tuesday = _session(plan, 1, "Tuesday")
    cases = [
        [_activity(_session(plan, 1, "Sunday"), "easy", [30])],
        [_activity(_session(plan, 1, "Saturday"), "long", [30])],
        [_activity(tuesday, "extra", [20], matched=False)],
        [_activity(tuesday, "blank", [None, None, 0])],
        [_activity(tuesday, "missing", None)],
        [
            _activity(tuesday, "extra-fast", [20], matched=False),
            _activity(tuesday, "real", [21.56]),
        ],
    ]
    for activities in cases:
        bases: dict = {}
        updated, actuals, marks = auto_adapt(plan, activities, {}, GOAL, bases)
        if activities[-1]["id"] == "real":
            row = actuals.get(tuesday["date"])
            if row is None or row["mark"] != "on_track" or marks != {1: "on_track"}:
                raise AssertionError("the extra activity was judged")
            if updated["sessions"] != plan["sessions"]:
                raise AssertionError("on_track changed a later week")
            continue
        if marks or bases or updated["sessions"] != plan["sessions"] or actuals:
            raise AssertionError(activities)
    fake = {
        "sessions": [
            {
                "date": "2026-04-21",
                "day_of_week": "Tuesday",
                "template_id": "not_a_rep",
                "week_number": 1,
            }
        ]
    }
    activity = {
        "id": "odd",
        "date": "2026-04-21",
        "matched": True,
        "template_id": "not_a_rep",
        "reps": [20],
    }
    skipped, skipped_actuals, skipped_marks = auto_adapt(fake, [activity], {}, GOAL, {})
    if skipped is not fake or skipped_actuals or skipped_marks:
        raise AssertionError("a template without a rep length was judged")


def test_a_later_week_adapts_from_that_week() -> None:
    """Week 2 can move week 3 without rewriting week 1."""
    plan = _plan()
    thursday = _session(plan, 2, "Thursday")
    updated, actuals, marks = auto_adapt(
        plan,
        [_activity(thursday, "wk2", [8])],
        {},
        GOAL,
        {},
    )
    if marks != {2: "smashing"} or actuals[thursday["date"]]["mark"] != "smashing":
        raise AssertionError((marks, actuals.get(thursday["date"])))
    if _ids(updated, 1) != _ids(plan, 1) or _ids(updated, 2) != _ids(plan, 2):
        raise AssertionError("adapt rewrote the judged weeks")
    if updated["sessions"] != adapt(plan, 2, "smashing")["sessions"]:
        raise AssertionError("week 2 did not adapt later weeks")


def test_a_changed_future_workout_is_not_judged_in_the_same_call() -> None:
    """Week 1's adapt can replace week 2. That new workout is not judged yet."""
    plan = _plan()
    tuesday = _session(plan, 1, "Tuesday")
    later = _session(plan, 2, "Thursday")
    updated, actuals, marks = auto_adapt(
        plan,
        [
            _activity(tuesday, "now", [20]),
            _activity(later, "later", [8]),
        ],
        {},
        GOAL,
        {},
    )
    if marks != {1: "smashing"} or later["date"] in actuals:
        raise AssertionError((marks, list(actuals)))
    if updated["sessions"] != adapt(plan, 1, "smashing")["sessions"]:
        raise AssertionError("week 2 was adapted from the workout it replaced")


def test_live_pages_pull_recent_and_judge() -> None:
    """Opening a live page reads the last 14 days and judges an unmarked quality day.

    Refresh on Activity data still reads every activity. The boxes show the
    stored times and stay editable. The page does not spend or score.
    """
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    source = (ROOT / "ui" / "auto_adapt.py").read_text(encoding="utf-8")
    if "print(" in source or "explain(" in source or "urlopen" in source:
        raise AssertionError("auto-adapt spends or prints")
    if "api_key" in source.lower() or "environ" in source:
        raise AssertionError("auto-adapt reads a secret")
    if "probability" in source.lower() or "readiness" in source.lower():
        raise AssertionError("auto-adapt adds a score")
    if "adapt(" not in source or "def adapt(" in source:
        raise AssertionError("auto-adapt does not call the existing adapt()")
    season = (ROOT / "engines" / "season.py").read_text(encoding="utf-8")
    if "auto_adapt" in season:
        raise AssertionError("season.py was changed for auto-adapt")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    block = app[app.index("_PULL_PAGES"):app.index("def _pull_for(")]
    for name in (
        "page_dashboard",
        "page_weekly",
        "page_session",
        "page_progress",
        "page_activity",
    ):
        if name not in block:
            raise AssertionError(f"{name} does not pull on open")
    pull_shell = _function(app, "_pull_for")
    pull = _function(
        (ROOT / "services" / "activity_pull.py").read_text(encoding="utf-8"),
        "run_activity_pull",
    )
    apply = _function(
        (ROOT / "services" / "season_commit.py").read_text(encoding="utf-8"),
        "apply_activity_marks",
    )
    if pull.count("_apply_activity_marks(") != 1:
        raise AssertionError("a live page does not judge a match once")
    if "if opened:" not in pull or "_apply_activity_marks(plan)" not in pull:
        raise AssertionError("opening a live page does not judge")
    if 'if page_name == "page_activity":\n            _apply_activity_marks(plan)' in pull:
        raise AssertionError("only activity data judges a match")
    if 'st.session_state.get("activity-refresh") is True' not in pull_shell:
        raise AssertionError("refresh does not read activities again")
    if "run_activity_pull(" not in pull_shell:
        raise AssertionError("opening a live page does not judge")
    branches = pull.split("if refresh:", 1)[1]
    history, recent = branches.split("else:", 1)
    if "sync_all(" not in history or "sync_recent(" not in recent:
        raise AssertionError("opening a live page does not use the recent adapter")
    if "sync_recent(" in history:
        raise AssertionError("refresh stopped reading every activity")
    if "auto_adapt(" not in apply:
        raise AssertionError("the match does not call adapt()")
    if "explain(" in apply or "print(" in apply or "SPEND_CAP" in apply:
        raise AssertionError("the match spends")
    page = _function(app, "page_activity")
    if "adapt(" in page or "explain(" in page or "probability" in page.lower():
        raise AssertionError("the activity page spends or classifies")
    result = _function(app, "_render_result")
    if "_initial_slots(" not in result or "actual-seed" not in result or "_boxes_blank(" not in result:
        raise AssertionError("a stored quality day does not fill the boxes")
    if "disabled" in _function(app, "_time_box"):
        raise AssertionError("the time boxes are locked")
    activities = (ROOT / "ui" / "activities.py").read_text(encoding="utf-8")
    if "from engines" in activities or "auto_adapt" in activities:
        raise AssertionError("the pull started calling adapt()")


def main() -> None:
    test_a_quality_day_uses_work_times_and_adapts_later_weeks()
    test_not_hitting_wins_and_a_hand_mark_stays()
    test_on_track_leaves_later_weeks()
    test_recovery_long_run_extra_and_empty_reps_do_not_adapt()
    test_a_later_week_adapts_from_that_week()
    test_a_changed_future_workout_is_not_judged_in_the_same_call()
    test_live_pages_pull_recent_and_judge()
    print("auto adapt ok")


if __name__ == "__main__":
    main()
