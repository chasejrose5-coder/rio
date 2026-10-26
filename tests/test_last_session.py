# test_last_session.py — a local Intervals JSON file on Last Session.

from __future__ import annotations

import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.classify import classify
from engines.explain import SPEND_CAP_MICRO_USD, explain
from engines.normalize import normalize
from ui.last_session import (
    IntervalsFileError,
    intervals_json_paths,
    open_intervals,
)

FIXTURES = ROOT / "tests" / "fixtures" / "intervals"
RECOVERY = FIXTURES / "synthetic_se_400_with_recovery.json"
AUTOSPLIT = FIXTURES / "synthetic_autosplit_no_rest.json"
SPEED_ENDURANCE = {
    "family": "speed_endurance",
    "reason_codes": ["work_300_500m", "rest_60_120s", "pace_near_goal_800"],
    "confidence": "high",
    "ontology_version": "v0.1",
}
REST_MISSING = {
    "family": "unsure",
    "reason_codes": ["rest_missing"],
    "confidence": "unsure",
    "ontology_version": "v0.1",
}
LABEL_KEYS = {
    "family",
    "expected_family",
    "classification",
    "label",
    "labels",
    "primary_stimulus",
    "secondary_stimulus",
    "ontology_version",
}


def test_intervals_directory_lists_json_only() -> None:
    paths = intervals_json_paths()
    names = [path.name for path in paths]
    if names != [
        "synthetic_autosplit_no_rest.json",
        "synthetic_se_400_with_recovery.json",
    ]:
        raise AssertionError(names)
    if intervals_json_paths(ROOT / "tests" / "fixtures" / "missing-intervals") != []:
        raise AssertionError("a missing directory invented files")


def test_synthetic_file_uses_the_same_fields() -> None:
    """to_normalize_input, then normalize, classify, and explain. No live call."""
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    with patch("urllib.request.urlopen", side_effect=AssertionError("live API")):
        with _no_explain_api():
            recovery_payload, recovery_banner = open_intervals(RECOVERY)
            autosplit_payload, autosplit_banner = open_intervals(AUTOSPLIT)
            recovery = _shown(recovery_payload)
            autosplit = _shown(autosplit_payload)
    if recovery_banner != "SYNTHETIC / FIXTURE":
        raise AssertionError(recovery_banner)
    if autosplit_banner != "SYNTHETIC / FIXTURE":
        raise AssertionError(autosplit_banner)
    if recovery["date"] != "2026-10-25" or autosplit["date"] != "2026-10-25":
        raise AssertionError((recovery["date"], autosplit["date"]))
    if recovery["laps"] != [_work(90.0)] * 6:
        raise AssertionError(recovery["laps"])
    if recovery["classification"] != SPEED_ENDURANCE:
        raise AssertionError(recovery["classification"])
    if "speed endurance" not in recovery["prose"].lower():
        raise AssertionError(recovery["prose"])
    if autosplit["laps"] != [_work(None)] * 6:
        raise AssertionError(autosplit["laps"])
    if autosplit["classification"] != REST_MISSING:
        raise AssertionError(autosplit["classification"])
    if "unsure" not in autosplit["prose"].lower() or "rest" not in autosplit["prose"].lower():
        raise AssertionError(autosplit["prose"])
    for payload in (recovery_payload, autosplit_payload):
        if set(payload) - {"intervals", "date"}:
            raise AssertionError(set(payload))
        if _keys(payload) & LABEL_KEYS:
            raise AssertionError(payload)


def test_real_file_has_no_synthetic_banner() -> None:
    activity = {
        "note": "Chase ran this.",
        "name": "Easy",
        "synthetic": False,
        "start_date_local": "2026-10-20T09:00:00",
        "distance": 5000,
        "icu_intervals": [
            {"type": "WORK", "distance": 400, "elapsed_time": 57.5},
            {"type": "RECOVERY", "distance": 0, "elapsed_time": 90},
        ],
    }
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "real_2026-10-20_easy.json"
        path.write_text(json.dumps(activity), encoding="utf-8")
        with patch("urllib.request.urlopen", side_effect=AssertionError("live API")):
            payload, banner = open_intervals(path)
    if banner is not None:
        raise AssertionError(banner)
    if payload["date"] != "2026-10-20":
        raise AssertionError(payload["date"])
    if "distance" in payload or payload["intervals"][0]["distance_m"] != 400:
        raise AssertionError(payload)


def test_note_marks_a_real_name_synthetic() -> None:
    activity = {
        "note": "SYNTHETIC. Chase did not run this.",
        "start_date_local": "not-a-date",
        "icu_intervals": [],
    }
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "real_2026-10-25_empty.json"
        path.write_text(json.dumps(activity), encoding="utf-8")
        payload, banner = open_intervals(path)
    if banner != "SYNTHETIC / FIXTURE":
        raise AssertionError(banner)
    if "date" in payload or payload["intervals"] != []:
        raise AssertionError(payload)


def test_bad_json_stays_local() -> None:
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        broken = folder / "synthetic_broken.json"
        broken.write_text("{", encoding="utf-8")
        listed = folder / "notes.txt"
        listed.write_text("SYNTHETIC", encoding="utf-8")
        array = folder / "synthetic_array.json"
        array.write_text("[]", encoding="utf-8")
        names = [path.name for path in intervals_json_paths(folder)]
        if names != ["synthetic_array.json", "synthetic_broken.json"]:
            raise AssertionError(names)
        with patch("urllib.request.urlopen", side_effect=AssertionError("live API")):
            try:
                open_intervals(broken)
            except IntervalsFileError as exc:
                broken_message = str(exc)
            else:
                raise AssertionError("broken JSON was accepted")
            try:
                open_intervals(array)
            except IntervalsFileError as exc:
                array_message = str(exc)
            else:
                raise AssertionError("a JSON array was accepted")
    if broken_message != "synthetic_broken.json is not JSON.":
        raise AssertionError(broken_message)
    if array_message != "synthetic_array.json must be a JSON object.":
        raise AssertionError(array_message)


def test_page_keeps_the_fixture_dropdown_and_stays_offline() -> None:
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    page = _function(app, "page_last_session")
    opener = _function(app, "_show_intervals_file")
    picker = _function(app, "_selected_intervals_path")
    if "selected_fixture_path(" not in page:
        raise AssertionError("the fixture drop-down was removed")
    if 'st.selectbox("Session"' not in _function(app, "selected_fixture_path"):
        raise AssertionError("the fixture drop-down changed")
    if "open_intervals(" not in opener or "render_session(" not in opener:
        raise AssertionError("the intervals file does not show the session fields")
    if "_show_intervals_file(" not in page or "Intervals file" not in picker:
        raise AssertionError("Last Session has no Intervals file picker")
    if "fetch_activity" in app or "list_activities" in app or "urlopen" in app:
        raise AssertionError("Last Session calls the live API")
    if "https://intervals.icu" in app:
        raise AssertionError("Last Session calls Intervals.icu")
    reader = (ROOT / "ui" / "last_session.py").read_text(encoding="utf-8")
    if "fetch_activity" in reader or "list_activities" in reader or "urlopen" in reader:
        raise AssertionError("the file reader calls the live API")
    if "to_normalize_input" not in reader:
        raise AssertionError("to_normalize_input was skipped")
    if "SPEND_CAP" in reader or "explain(" in reader or "from engines" in reader:
        raise AssertionError("the file reader started its own prose spend")


def _shown(payload: dict) -> dict:
    """The fields render_session shows: laps, date, classification, prose."""
    laps = normalize(payload)["laps"]
    result = classify(payload)
    return {
        "date": payload.get("date") or "",
        "laps": laps,
        "classification": result,
        "prose": explain(result),
    }


def _work(rest_s: float | None) -> dict:
    return {"distance_m": 400.0, "seconds": 57.5, "rest_s": rest_s}


def _keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(str(key))
            found.update(_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_keys(item))
    return found


def _function(source: str, name: str) -> str:
    marker = f"def {name}("
    start = source.index(marker)
    nxt = source.index("\ndef ", start + len(marker))
    return source[start:nxt]


@contextmanager
def _no_explain_api():
    key = "RIO_EXPLAIN_API_KEY"
    old = os.environ.get(key)
    os.environ[key] = ""
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


if __name__ == "__main__":
    test_intervals_directory_lists_json_only()
    test_synthetic_file_uses_the_same_fields()
    test_real_file_has_no_synthetic_banner()
    test_note_marks_a_real_name_synthetic()
    test_bad_json_stays_local()
    test_page_keeps_the_fixture_dropdown_and_stays_offline()
    print("last session ok")
