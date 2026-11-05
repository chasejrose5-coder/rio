# test_home_phase.py — Home tells the phase story and drops the old blocks.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.season import sequence
from ui.insights import phase_story


def _text(story: dict) -> str:
    return story["collapsed"] + "\n" + "\n".join(story["sentences"])


def _phase_four() -> list[dict]:
    rows = [
        ("Sunday", "2026-01-04", "aer_5000_r0_x1", ["phase_4"]),
        ("Monday", "2026-01-05", "aer_5000_r0_x1", ["phase_4"]),
        ("Tuesday", "2026-01-06", "se_400_r90_x6", ["phase_4", "phase_primary"]),
        ("Wednesday", "2026-01-07", "aer_5000_r0_x1", ["phase_4"]),
        ("Thursday", "2026-01-08", "ap_600_r75_x6", ["phase_4", "phase_primary"]),
        ("Saturday", "2026-01-10", "aer_12000_r0_x1", ["phase_4", "weekly_aerobic_long_run"]),
    ]
    sessions = []
    for day, when, template, codes in rows:
        sessions.append(
            {
                "week_number": 10,
                "day_of_week": day,
                "date": when,
                "template_id": template,
                "reason_codes": codes,
            }
        )
    sessions.append(
        {
            "week_number": 11,
            "day_of_week": "Tuesday",
            "date": "2026-01-13",
            "template_id": "se_400_r90_x6",
            "reason_codes": ["phase_4", "phase_primary"],
        }
    )
    return sessions


def test_phase_story_places_the_week_and_names_the_neighbors() -> None:
    story = phase_story(phase=4, week=10, sessions=_phase_four(), thin=False)
    if story is None:
        raise AssertionError("phase 4 produced no story")
    text = _text(story)
    if "2:05" in text or "1:55" in text or "2:02" in text:
        raise AssertionError("the phase story invented a personal time")
    if "week 1 of 2" not in story["collapsed"] or "phase 4" not in story["collapsed"]:
        raise AssertionError(story["collapsed"])
    if "because the season still needs speed endurance and aerobic power." not in story["collapsed"]:
        raise AssertionError(story["collapsed"])
    if "Speed endurance and aerobic power take the lead." not in text:
        raise AssertionError(text)
    if "Tuesday and Thursday are hard." not in text:
        raise AssertionError(text)
    if "Sunday, Monday, and Wednesday are easy." not in text:
        raise AssertionError(text)
    if "Saturday is the long run." not in text or "Friday is off." not in text:
        raise AssertionError(text)
    if "Hard-day marks can ease or advance later weeks." not in text:
        raise AssertionError(text)
    if "They do not rewrite this week after the fact." not in text:
        raise AssertionError(text)
    if "The phase before was phase 3, Threshold meets power." not in text:
        raise AssertionError(text)
    if "It brought in threshold and aerobic power" not in text:
        raise AssertionError(text)
    if "The next phase is phase 5, Longer specific reps." not in text:
        raise AssertionError(text)
    if "Same job as phase 4, with longer reps than phase 4." not in text:
        raise AssertionError(text)
    before = text.index("Hard-day marks can ease")
    after = text.index("The phase before")
    nxt = text.index("The next phase")
    if not (before < after < nxt):
        raise AssertionError("the neighbors came before the mark line")


def test_edges_omit_a_missing_neighbor_and_an_easy_day_stays_easy() -> None:
    opening = sequence("2:10.0", date(2026, 11, 1), "2:00.0", date(2027, 4, 4))
    first = phase_story(phase=1, week=1, sessions=opening["sessions"], thin=False)
    if first is None:
        raise AssertionError("phase 1 produced no story")
    opening_text = _text(first)
    if "2:10" in opening_text or "2:00" in opening_text:
        raise AssertionError("a stored mark leaked into the phase story")
    if "The phase before" in opening_text:
        raise AssertionError("phase 1 invented a previous phase")
    if "The next phase is phase 2, Base steps up." not in opening_text:
        raise AssertionError(opening_text)
    if "week 1 of" not in first["collapsed"]:
        raise AssertionError(first["collapsed"])
    if "because the season still needs aerobic." not in first["collapsed"]:
        raise AssertionError(first["collapsed"])
    easy = _phase_four()
    easy[2]["template_id"] = "aer_5000_r0_x1"
    easy[2]["reason_codes"] = ["phase_4", "extra_easy_day"]
    eased = phase_story(phase=4, week=10, sessions=easy, thin=False)
    if eased is None or "Tuesday and Thursday are hard." in _text(eased):
        raise AssertionError(eased)
    if "Thursday is hard." not in _text(eased) or "Tuesday" not in _text(eased):
        raise AssertionError(_text(eased))
    last = phase_story(
        phase=8,
        week=3,
        sessions=[
            {
                "week_number": 3,
                "day_of_week": "Saturday",
                "date": "2026-02-07",
                "template_id": "rr_800_r0_x1",
                "reason_codes": ["phase_8"],
            }
        ],
        thin=True,
    )
    if last is None:
        raise AssertionError("phase 8 produced no story")
    closing = _text(last)
    if "The next phase" in closing:
        raise AssertionError("phase 8 invented a following phase")
    if "the only week of this phase" not in last["collapsed"]:
        raise AssertionError(last["collapsed"])
    if "The phase before was phase 7, Race readiness." not in closing:
        raise AssertionError(closing)
    if "Saturday is the race." not in closing:
        raise AssertionError(closing)
    if "Connect Strava" not in closing:
        raise AssertionError("a thin week hid the log line")
    if phase_story(phase=0, week=1, sessions=[], thin=False) is not None:
        raise AssertionError("phase 0 still wrote a story")


def test_home_is_three_sections_without_the_removed_blocks() -> None:
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    start = app.index("def page_dashboard(")
    page = app[start : app.index("\ndef ", start + 1)]
    phase = page.index("_render_this_week(")
    workout = page.index("02  /  Today's workout")
    upcoming = page.index("03  /  Next 3 days")
    if not (phase < workout < upcoming):
        raise AssertionError("home sections are out of order")
    if "01  /  Next workout" not in page or "02  /  Next 3 days" not in page:
        raise AssertionError("a week outside the season lost its indexes")
    for banned in ("home_line(", "season_thesis(", "Planned vs actual", "Days to goal", "phase_outline("):
        if banned in page:
            raise AssertionError(f"home still shows {banned}")
    card = app[app.index("def _render_this_week(") : app.index("\ndef _remember_workout_note(")]
    if "01  /  Current phase" not in card or "phase_story(" not in card:
        raise AssertionError("the phase section is missing")
    for banned in ("season_thesis(", "current_phase_note(", "phase_outline(", "Your season is built"):
        if banned in card:
            raise AssertionError(f"the phase card still includes {banned}")
    meta = app[app.index("def _track_meta(") : app.index("def _season_goal_text(")]
    if "Progress status" not in meta or "Pace status" in meta or "Days to goal" in meta:
        raise AssertionError(meta)
    if "Training block" not in meta or "Last timed effort" not in meta:
        raise AssertionError(meta)
    if "A training block is one phase of the season." not in page:
        raise AssertionError("the glossary lost the training block")
    if "A timed effort is a run you logged." not in page:
        raise AssertionError("the glossary lost the timed effort")
    if "Times use minutes:seconds.tenths, like 2:05.0." not in page:
        raise AssertionError("the glossary lost the time format")
    if "_show_stored_insight(" not in card:
        raise AssertionError("the hard-day note left home")


def main() -> None:
    test_phase_story_places_the_week_and_names_the_neighbors()
    test_edges_omit_a_missing_neighbor_and_an_easy_day_stays_easy()
    test_home_is_three_sections_without_the_removed_blocks()
    print("home phase ok")


if __name__ == "__main__":
    main()
