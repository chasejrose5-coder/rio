# test_start_form.py — Start opens on today and a blank time.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import SPEND_CAP_MICRO_USD
from ui.start_form import start_form_defaults


def test_dates_are_today_and_five_months_later() -> None:
    """Start is today. The goal date is five calendar months later. Times are blank."""
    current, start, goal, goal_day = start_form_defaults(date(2026, 11, 1))
    if (current, start, goal, goal_day) != ("", date(2026, 11, 1), "", date(2027, 4, 1)):
        raise AssertionError((current, start, goal, goal_day))
    if start_form_defaults(date(2026, 12, 15))[3] != date(2027, 5, 15):
        raise AssertionError("a year boundary moved the day")
    if start_form_defaults(date(2026, 1, 31))[3] != date(2026, 6, 30):
        raise AssertionError("a short month kept a missing day")
    if start_form_defaults(date(2023, 9, 30))[3] != date(2024, 2, 29):
        raise AssertionError("a leap February was shortened")
    if start_form_defaults(date(2024, 9, 30))[3] != date(2025, 2, 28):
        raise AssertionError("a common February kept the 29th")
    if current or goal:
        raise AssertionError("a time was filled in")
    if "2:02" in current or "1:55" in goal or "2:02" in goal or "1:55" in current:
        raise AssertionError("a previous goal was copied")


def test_start_uses_the_defaults_and_stays_editable() -> None:
    """The form shows those defaults. The four fields stay editable. No engine change."""
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    source = (ROOT / "ui" / "start_form.py").read_text(encoding="utf-8")
    for token in (
        "engines",
        "sequence(",
        "adapt(",
        "explain(",
        "classify(",
        "prescribe(",
        "urlopen",
        "probability",
        "readiness",
        "2:02",
        "1:55",
    ):
        if token in source:
            raise AssertionError(token)
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    page = app[app.index("def page_start(") : app.index("def _session_activity(")]
    form = page[: page.index('st.button("Generate"')]
    if "start_form_defaults(" not in form or "_athlete_today()" not in form:
        raise AssertionError("Start does not default the dates")
    if "_seed_start_form(" in form or "season_inputs" in form:
        raise AssertionError("Start copied a previous goal or time")
    for old in ("2:02.9", "1:55.0", "date(2026, 4, 19)", "date(2027, 3, 19)"):
        if old in page:
            raise AssertionError(old)
    for key in (
        'key="start_current_time"',
        'key="start_start_date"',
        'key="start_goal_time"',
        'key="start_goal_date"',
    ):
        if key not in page:
            raise AssertionError(key)
    if "disabled" in page:
        raise AssertionError("a field is locked")
    for token in ("probability", "readiness", "explain(", "SPEND_CAP", "classify("):
        if token in page:
            raise AssertionError(token)
    for path in (ROOT / "engines").glob("*.py"):
        body = path.read_text(encoding="utf-8")
        if "start_form" in body:
            raise AssertionError(f"{path.name} was changed for Start defaults")


def main() -> None:
    test_dates_are_today_and_five_months_later()
    test_start_uses_the_defaults_and_stays_editable()
    print("start form ok")


if __name__ == "__main__":
    main()
