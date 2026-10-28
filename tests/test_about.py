# test_about.py — the About page explains the season. It does not change it.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.explain import SPEND_CAP_MICRO_USD
from engines.season import (
    _BANNED_PHASE_8,
    _PHASE_MENU,
    _PRIMARY,
    _QUALITY_DAYS,
    _RISE_DEN,
    _RISE_NUM,
    _SECONDARY,
    phase_lengths,
)
from ui.about import _EXTRA, _FAMILY, about_sections, phase_rows
from ui.result import _BAND


def _copy() -> str:
    parts: list[str] = []
    for section in about_sections():
        parts.append(section["title"])
        parts.extend(section["paragraphs"])
        parts.extend(section["closing"])
        for label, line in section["rows"]:
            parts.append(label)
            parts.append(line)
    return "\n".join(parts)


def _rep_lengths(phase: int, prefix: str) -> list[int]:
    found = []
    for template_id in _PHASE_MENU[phase]:
        if str(template_id).startswith(prefix):
            found.append(int(str(template_id).split("_")[1]))
    return found


def test_eight_phases_follow_the_season() -> None:
    """The eight lines name the families the season already stores."""
    rows = phase_rows()
    if [label for label, _line in rows] != [f"Phase {number}" for number in range(1, 9)]:
        raise AssertionError(rows)
    if set(_FAMILY) != {
        "aerobic",
        "threshold",
        "aerobic_power",
        "speed_endurance",
        "anaerobic_capacity",
        "race_readiness",
        "max_velocity",
        "speed",
    }:
        raise AssertionError("a family was added")
    for phase in range(1, 9):
        text = rows[phase - 1][1].lower()
        for family in _PRIMARY[phase] | _SECONDARY[phase]:
            if _FAMILY[family].lower() not in text:
                raise AssertionError((phase, family, rows[phase - 1][1]))
    if _rep_lengths(2, "mv_")[0] <= _rep_lengths(1, "mv_")[0]:
        raise AssertionError("phase 2 no longer steps the fast reps up")
    if "step up" not in rows[1][1]:
        raise AssertionError(rows[1][1])
    for prefix in ("se_", "ap_"):
        if min(_rep_lengths(5, prefix)) <= max(_rep_lengths(4, prefix)):
            raise AssertionError(f"phase 5 {prefix} reps are not longer")
    if "longer" not in rows[4][1]:
        raise AssertionError(rows[4][1])
    if _BANNED_PHASE_8 != {"speed_endurance", "anaerobic_capacity"}:
        raise AssertionError(_BANNED_PHASE_8)
    if "No hard speed endurance or anaerobic work." not in rows[7][1]:
        raise AssertionError(rows[7][1])
    if _EXTRA.keys() != {2, 5, 8}:
        raise AssertionError(_EXTRA)
    text = _copy()
    if "Friday is off" not in text or "Saturday is the long run" not in text:
        raise AssertionError("the week shape changed")
    if "800 m race" not in text or "last Saturday" not in text:
        raise AssertionError("the taper race changed")
    if phase_lengths(8) != [1, 1, 1, 1, 1, 1, 1, 1]:
        raise AssertionError("eight weeks is no longer one week per phase")
    if phase_lengths(9)[7] != 2 or phase_lengths(1) != [0, 0, 0, 0, 0, 0, 0, 1]:
        raise AssertionError("the taper length changed")
    if "one week when the season is one week or eight weeks" not in text:
        raise AssertionError("the taper sentence changed")


def test_the_ten_percent_rule_and_hard_days_match_the_code() -> None:
    """10% is the season's rise. Hard days use the existing 3% band."""
    if (_RISE_NUM, _RISE_DEN) != (11, 10):
        raise AssertionError("the 10% rule changed")
    if _BAND != 0.03:
        raise AssertionError("the hard-day band changed")
    if _QUALITY_DAYS != ("Tuesday", "Thursday"):
        raise AssertionError(_QUALITY_DAYS)
    text = _copy()
    for phrase in (
        "10%",
        "times 10",
        "times 11",
        "not easy runs",
        "within 3%",
        "on_track",
        "not_hitting",
        "smashing",
        "stays as written",
        "back one phase",
        "forward one phase",
        "stops at phase 7",
        "Phase 8 stays the taper",
        "Not hitting wins",
        "Later weeks are what change.",
    ):
        if phrase not in text:
            raise AssertionError(phrase)


def test_classification_is_rules_and_spend_stays_at_25() -> None:
    """Labels stay rules. The prose cap stays $25. The page does not spend."""
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    text = _copy()
    if "Classification is rules, not AI." not in text:
        raise AssertionError("classification was not described as rules")
    for phrase in (
        "ontology version",
        "A model does not pick the family.",
        "Last Session",
        "Next",
        "Decisions",
        "$25",
    ):
        if phrase not in text:
            raise AssertionError(phrase)
    lowered = text.lower()
    for banned in ("probability", "readiness_score", "strength", "core"):
        if banned in lowered:
            raise AssertionError(banned)
    source = (ROOT / "ui" / "about.py").read_text(encoding="utf-8")
    for token in (
        "explain(",
        "classify(",
        "sequence(",
        "adapt(",
        "prescribe(",
        "urlopen",
        "print(",
        "SPEND_CAP",
        "probability",
        "readiness_score",
        "strength",
        "core",
    ):
        if token in source:
            raise AssertionError(token)
    for path in (ROOT / "engines").glob("*.py"):
        body = path.read_text(encoding="utf-8")
        if "ui.about" in body or "page_about" in body:
            raise AssertionError(f"{path.name} was changed for About")


def test_about_is_in_the_nav_and_does_not_spend() -> None:
    """About is a top-nav page. Opening it does not label, adapt, or spend."""
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    line = '("About", st.Page(_with_plan(page_about), title="About", url_path="about"))'
    if line not in app:
        raise AssertionError("About is not in the nav")
    start = app.index("def page_about(")
    page = app[start : app.index("\ndef page_settings(", start)]
    if "about_sections(" not in page or '_open("About")' not in page:
        raise AssertionError("the page does not render the explanation")
    for token in (
        "explain(",
        "classify(",
        "sequence(",
        "adapt(",
        "prescribe(",
        "urlopen",
        "fetch_activity",
        "list_activities",
        "SPEND_CAP",
        "probability",
        "readiness_score",
        "strength",
    ):
        if token in page:
            raise AssertionError(token)
    if "https://intervals.icu" in app:
        raise AssertionError("About calls Intervals.icu")


def main() -> None:
    test_eight_phases_follow_the_season()
    test_the_ten_percent_rule_and_hard_days_match_the_code()
    test_classification_is_rules_and_spend_stays_at_25()
    test_about_is_in_the_nav_and_does_not_spend()
    print("about ok")


if __name__ == "__main__":
    main()
