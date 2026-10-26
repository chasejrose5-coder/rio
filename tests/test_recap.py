# test_recap.py — weekly recap from a plan, stored results, and stored adapt codes.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.season import adapt, sequence, work_meters
from ui.recap import recap_view

START = date(2026, 4, 19)
GOAL_DAY = date(2027, 3, 19)
WEEK = 27


def _no_score(view: dict) -> None:
    if "probability" in view or "readiness" in view or "readiness_score" in view:
        raise AssertionError("a score was added")
    for value in view.values():
        text = str(value).lower()
        if "probability" in text or "readiness_score" in text:
            raise AssertionError("a score was named")


def _plan():
    return sequence("2:02.9", START, "1:55.0", GOAL_DAY)


def _rows(plan: dict, week: int) -> list[dict]:
    return [session for session in plan["sessions"] if session["week_number"] == week]


def _meters(plan: dict, week: int) -> int:
    return sum(work_meters(session["template_id"]) for session in _rows(plan, week))


def _codes(plan: dict, week: int) -> set[str]:
    found = set()
    for session in _rows(plan, week):
        found.update(session["reason_codes"])
    return found


def test_an_unmarked_week_is_a_blank_recap() -> None:
    """No results and no mark. Volume is this week beside the week before."""
    plan = _plan()
    view = recap_view(
        week=WEEK,
        sessions=plan["sessions"],
        actuals={},
        marks={},
    )
    _no_score(view)
    if view["completed"] != "0 of 6":
        raise AssertionError(f"completed was {view['completed']}")
    if view["marks"] != "—":
        raise AssertionError(f"marks were {view['marks']}")
    expected = f"{_meters(plan, WEEK):,} m · {_meters(plan, WEEK - 1):,} m the week before"
    if view["volume"] != expected:
        raise AssertionError(f"volume was {view['volume']}")
    if view["next"] != "Next week stays as written.":
        raise AssertionError(f"next was {view['next']}")
    if "explain(" in Path(ROOT / "ui" / "recap.py").read_text(encoding="utf-8"):
        raise AssertionError("the recap calls the model")


def test_results_and_a_week_mark() -> None:
    """A stored result counts. A week mark with no results counts as marked."""
    plan = _plan()
    days = {session["day_of_week"]: session for session in _rows(plan, WEEK)}
    tuesday = days["Tuesday"]
    thursday = days["Thursday"]
    actuals = {
        tuesday["date"]: {
            "template_id": tuesday["template_id"],
            "numbers": [90.0],
            "mark": "on_track",
        },
        thursday["date"]: {
            "template_id": "other",
            "numbers": [99.0],
            "mark": "smashing",
        },
    }
    view = recap_view(week=WEEK, sessions=plan["sessions"], actuals=actuals, marks={})
    _no_score(view)
    if view["completed"] != "1 of 6":
        raise AssertionError(f"a mismatched template counted: {view['completed']}")
    if view["marks"] != "Tuesday on_track":
        raise AssertionError(f"marks were {view['marks']}")

    actuals[thursday["date"]]["template_id"] = thursday["template_id"]
    view = recap_view(
        week=WEEK,
        sessions=plan["sessions"],
        actuals=actuals,
        marks={WEEK: "smashing"},
    )
    if view["completed"] != "2 of 6":
        raise AssertionError(f"completed was {view['completed']}")
    if view["marks"] != "Tuesday on_track · Thursday smashing":
        raise AssertionError(f"marks were {view['marks']}")
    both = recap_view(
        week=WEEK,
        sessions=plan["sessions"],
        actuals=actuals,
        marks={WEEK: "not_hitting"},
    )
    if both["marks"] != "Tuesday on_track · Thursday smashing · not_hitting":
        raise AssertionError(f"the week mark was dropped: {both['marks']}")

    marked = recap_view(week=WEEK, sessions=plan["sessions"], actuals={}, marks={WEEK: "smashing"})
    if marked["completed"] != "Marked" or marked["marks"] != "smashing":
        raise AssertionError(f"a week mark was {marked['completed']} / {marked['marks']}")


def test_next_sentence_uses_codes_on_the_following_week() -> None:
    """The sentence names an adapt code stored on the next week, or says it stays."""
    plan = _plan()
    stayed = adapt(plan, WEEK, "on_track")
    same = recap_view(week=WEEK, sessions=stayed["sessions"], actuals={}, marks={WEEK: "on_track"})
    _no_score(same)
    if same["completed"] != "Marked" or same["marks"] != "on_track":
        raise AssertionError("on_track was not the week's mark")
    if same["next"] != "Next week stays as written.":
        raise AssertionError(f"on_track changed the next week: {same['next']}")

    spoken = {
        "extra_easy_week": "Next week is an easy week.",
        "harder_template": "Next week uses a harder session.",
        "moved_back_one_phase": "Next week moves back one phase.",
        "advanced_one_phase": "Next week advances one phase.",
    }
    for outcome in ("not_hitting", "smashing"):
        updated = adapt(plan, WEEK, outcome)
        codes = _codes(updated, WEEK + 1)
        expected = None
        for code, sentence in spoken.items():
            if code in codes:
                expected = sentence
                break
        if expected is None:
            raise AssertionError(f"{outcome} stored no change code: {codes}")
        view = recap_view(
            week=WEEK,
            sessions=updated["sessions"],
            actuals={},
            marks={WEEK: outcome},
        )
        _no_score(view)
        if view["next"] != expected:
            raise AssertionError(f"{outcome} was said as {view['next']}")


def test_a_partial_load_counts_the_whole_week() -> None:
    """A loaded day uses that file. Every other day keeps its template meters.

    A week with no readable file keeps the template total.
    """
    plan = _plan()
    rows = _rows(plan, WEEK)
    first = rows[0]["date"]
    second = rows[1]["date"]
    previous_rows = _rows(plan, WEEK - 1)
    previous = previous_rows[0]["date"]
    rest = sum(work_meters(session["template_id"]) for session in rows[2:])
    if rest <= 0:
        raise AssertionError("the week had no unloaded day")
    view = recap_view(
        week=WEEK,
        sessions=plan["sessions"],
        actuals={},
        marks={},
        distances={first: 5600, second: 4000, "1999-01-01": 99999},
    )
    _no_score(view)
    expected = f"{5600 + 4000 + rest:,} m · {_meters(plan, WEEK - 1):,} m the week before"
    if view["volume"] != expected:
        raise AssertionError(f"loaded volume was {view['volume']}")
    others = sum(work_meters(session["template_id"]) for session in rows[1:])
    mixed_total = int(5600.6 + others + 0.5)
    mixed = recap_view(
        week=WEEK,
        sessions=plan["sessions"],
        actuals={},
        marks={},
        distances={first: 5600.6, second: None},
    )
    if mixed["volume"] != f"{mixed_total:,} m · {_meters(plan, WEEK - 1):,} m the week before":
        raise AssertionError(f"a blank file dropped the other days: {mixed['volume']}")
    prev_rest = sum(work_meters(session["template_id"]) for session in previous_rows[1:])
    if prev_rest <= 0:
        raise AssertionError("the week before had no unloaded day")
    earlier = recap_view(
        week=WEEK,
        sessions=plan["sessions"],
        actuals={},
        marks={},
        distances={previous: 8000},
    )
    if earlier["volume"] != f"{_meters(plan, WEEK):,} m · {8000 + prev_rest:,} m the week before":
        raise AssertionError(f"the week before ignored its other days: {earlier['volume']}")
    blank = recap_view(
        week=WEEK,
        sessions=plan["sessions"],
        actuals={},
        marks={},
        distances={first: None, second: "5600"},
    )
    template = f"{_meters(plan, WEEK):,} m · {_meters(plan, WEEK - 1):,} m the week before"
    if blank["volume"] != template:
        raise AssertionError(f"unreadable files left the template: {blank['volume']}")
    if "probability" in view["volume"] or "readiness" in view["volume"]:
        raise AssertionError("volume named a score")


def test_weekly_page_reads_loaded_files() -> None:
    source = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    start = source.index("def page_weekly(")
    end = source.index("\ndef page_season(")
    page = source[start:end]
    if "loaded_distances(" not in page or "distances=" not in page:
        raise AssertionError("weekly recap ignores loaded Intervals files")
    if "urlopen" in page or "fetch_activity" in page or "explain(" in page:
        raise AssertionError("weekly recap calls the network or the model")


def test_the_last_week_has_nothing_after_it() -> None:
    plan = _plan()
    last = plan["season_length_weeks"]
    view = recap_view(week=last, sessions=plan["sessions"], actuals={}, marks={})
    _no_score(view)
    if view["next"] != "This is the last week.":
        raise AssertionError(f"last week said {view['next']}")
    if "the week before" not in view["volume"]:
        raise AssertionError("the last week dropped the week before")
    first = recap_view(week=1, sessions=plan["sessions"], actuals={}, marks={})
    if "the week before" in first["volume"]:
        raise AssertionError("week 1 invented a previous week")
    if first["volume"] != f"{_meters(plan, 1):,} m":
        raise AssertionError(f"week 1 volume was {first['volume']}")


def main() -> None:
    test_an_unmarked_week_is_a_blank_recap()
    test_results_and_a_week_mark()
    test_next_sentence_uses_codes_on_the_following_week()
    test_a_partial_load_counts_the_whole_week()
    test_weekly_page_reads_loaded_files()
    test_the_last_week_has_nothing_after_it()
    print("recap ok")


if __name__ == "__main__":
    main()
