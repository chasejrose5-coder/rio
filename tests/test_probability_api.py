# test_probability_api.py — the stub has a shape and no fake percent.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.probability import (
    GoalProbability,
    admin_line,
    athlete_line,
    compute_goal_probability,
)


def test_the_stub_has_the_api_shape_and_no_percent() -> None:
    hidden = compute_goal_probability(viewer="athlete")
    if hidden is not None:
        raise AssertionError(hidden)
    if compute_goal_probability() is not None:
        raise AssertionError("a default call showed a probability")
    stub = compute_goal_probability(viewer="admin")
    if not isinstance(stub, GoalProbability):
        raise AssertionError(stub)
    if stub.percent is not None or stub.projected_800 is not None or stub.gap_seconds is not None:
        raise AssertionError("the stub invented a result")
    if stub.trend != "unknown" or stub.confidence != "low":
        raise AssertionError((stub.trend, stub.confidence))
    if stub.updated_at != "" or stub.drivers != ():
        raise AssertionError("the stub filled drivers")
    if athlete_line() != "":
        raise AssertionError(athlete_line())
    shown = admin_line()
    if shown != "Goal probability (stub). Not calibrated.":
        raise AssertionError(shown)
    if "%" in shown or any(char.isdigit() for char in shown):
        raise AssertionError("the admin line looks calibrated")


def test_the_module_does_not_call_a_model_or_strava() -> None:
    source = (ROOT / "engines" / "probability.py").read_text(encoding="utf-8")
    for token in ("openai", "strava", "urlopen", "http", "explain("):
        if token in source.lower():
            raise AssertionError(token)
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    home = app[app.index("def page_dashboard(") : app.index("\ndef ", app.index("def page_dashboard(") + 1)]
    session = app[app.index("def page_session(") : app.index("\ndef ", app.index("def page_session(") + 1)]
    if "probability" in home.lower() or "probability" in session.lower():
        raise AssertionError("an athlete page shows the stub")
    admin = app[app.index("def page_admin(") : app.index("\ndef ", app.index("def page_admin(") + 1)]
    if admin.index("viewer_is_admin(") > admin.index("render_admin_stub("):
        raise AssertionError("the stub is not behind the admin check")


def main() -> None:
    test_the_stub_has_the_api_shape_and_no_percent()
    test_the_module_does_not_call_a_model_or_strava()
    print("probability api ok")


if __name__ == "__main__":
    main()
