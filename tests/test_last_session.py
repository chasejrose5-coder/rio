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
    activity_by_ref,
    activity_distance,
    activity_heart_rate,
    file_just_opened,
    fit_slots,
    heart_rate_text,
    intervals_json_paths,
    loaded_distances,
    open_intervals,
    quality_fill,
    work_distance,
    work_elapsed,
)
from ui.result import filled_times, goal_seconds, judge, result_box_count

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


def test_quality_file_fills_work_times() -> None:
    """WORK elapsed times fill the rep boxes. Recovery, warm-up, and cool-down stay out.

    The filled times use judge(). The activity id is kept. No live call, and
    the prose cap stays $25.
    """
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    band = (ROOT / "ui" / "result.py").read_text(encoding="utf-8")
    if "_BAND = 0.03" not in band:
        raise AssertionError("the ±3% rule moved")
    with patch("urllib.request.urlopen", side_effect=AssertionError("live API")):
        times, source = quality_fill(RECOVERY)
        auto_times, auto_source = quality_fill(AUTOSPLIT)
    if times != [57.5] * 6 or 90 in times or 600 in times or 540 in times:
        raise AssertionError(times)
    if source != "synthetic-se-400-with-recovery":
        raise AssertionError(source)
    if auto_times != [57.5] * 6 or auto_source != "synthetic-autosplit-no-rest":
        raise AssertionError((auto_times, auto_source))
    count = result_box_count("se_400_r90_x6")
    slots = fit_slots(times, count)
    text = filled_times(slots)
    marked = judge("se_400_r90_x6", text, goal_seconds("1:55.0"))
    if slots != [57.5] * 6 or marked is None or marked["mark"] != "on_track":
        raise AssertionError((slots, text, marked))
    if fit_slots(times, 4) != [57.5] * 4:
        raise AssertionError("extra WORK intervals were added as boxes")
    if fit_slots([58.0, 59.0], 6) != [58.0, 59.0, None, None, None, None]:
        raise AssertionError("a short file did not leave the later boxes empty")
    gapped = work_elapsed(
        {
            "icu_intervals": [
                {"type": "WARMUP", "elapsed_time": 600, "moving_time": 600},
                {"type": "WORK", "elapsed_time": 58, "moving_time": 40},
                {"type": "RECOVERY", "elapsed_time": 90, "moving_time": 0},
                {"type": "WORK", "moving_time": 50},
                {"type": "Work", "elapsed_time": 60.004},
                {"type": "INTERVAL", "elapsed_time": 10},
                {"type": "COOLDOWN", "elapsed_time": 540},
            ]
        }
    )
    if gapped != [58.0, None, 60.0]:
        raise AssertionError(gapped)
    if file_just_opened(None, source) is not True:
        raise AssertionError("a newly chosen file did not fill the boxes")
    if file_just_opened(source, source) is not False:
        raise AssertionError("the same file replaced an edit")
    if file_just_opened(source, None) or file_just_opened(source, "  "):
        raise AssertionError("a blank file filled the boxes")


def test_quality_file_stores_filename_without_an_id() -> None:
    """No activity id keeps the filename. A long id falls back to that name."""
    activity = {
        "icu_intervals": [
            {"type": "WORK", "distance": 400, "elapsed_time": 59},
            {"type": "RECOVERY", "elapsed_time": 90},
        ]
    }
    named = dict(activity)
    named["id"] = 44521
    long_id = dict(activity)
    long_id["id"] = "x" * 121
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        plain = folder / "real_tuesday.json"
        plain.write_text(json.dumps(activity), encoding="utf-8")
        numbered = folder / "real_44521.json"
        numbered.write_text(json.dumps(named), encoding="utf-8")
        huge = folder / "real_long.json"
        huge.write_text(json.dumps(long_id), encoding="utf-8")
        with patch("urllib.request.urlopen", side_effect=AssertionError("live API")):
            plain_times, plain_source = quality_fill(plain)
            id_times, id_source = quality_fill(numbered)
            long_times, long_source = quality_fill(huge)
    if plain_times != [59.0] or plain_source != "real_tuesday.json":
        raise AssertionError((plain_times, plain_source))
    if id_times != [59.0] or id_source != "44521":
        raise AssertionError((id_times, id_source))
    if long_times != [59.0] or long_source != "real_long.json":
        raise AssertionError((long_times, long_source))


def test_local_file_distance_and_heart_rate() -> None:
    """Activity distance and average heart rate come from the local JSON. No live call."""
    if SPEND_CAP_MICRO_USD != 25_000_000:
        raise AssertionError("spend cap is not $25")
    band = (ROOT / "ui" / "result.py").read_text(encoding="utf-8")
    if "_BAND = 0.03" not in band:
        raise AssertionError("the ±3% rule moved")
    with patch("urllib.request.urlopen", side_effect=AssertionError("live API")):
        recovery = activity_by_ref("synthetic-se-400-with-recovery")
        by_name = activity_by_ref("synthetic_se_400_with_recovery.json")
        autosplit = activity_by_ref("synthetic-autosplit-no-rest")
    if recovery is None or by_name is None or by_name.get("id") != recovery.get("id"):
        raise AssertionError("the activity id did not open the local file")
    if activity_distance(recovery) != 5600 or heart_rate_text(recovery) != "148 bpm":
        raise AssertionError((activity_distance(recovery), heart_rate_text(recovery)))
    if heart_rate_text(autosplit) != "162 bpm":
        raise AssertionError(heart_rate_text(autosplit))
    laps_only = {
        "distance": 4200,
        "icu_intervals": [{"type": "WORK", "distance": 400, "average_heartrate": 176}],
    }
    if activity_heart_rate(laps_only) is not None or heart_rate_text(laps_only) is not None:
        raise AssertionError("a lap heart rate was shown as the activity average")
    if activity_distance(laps_only) != 4200:
        raise AssertionError(activity_distance(laps_only))
    if activity_distance({"average_heartrate": 140}) is not None:
        raise AssertionError("a missing distance was invented")
    if activity_distance({"distance": None}) is not None or activity_distance({"distance": -1}) is not None:
        raise AssertionError("an unusable distance was kept")
    if activity_heart_rate({"average_heartrate": 0}) is not None:
        raise AssertionError("zero heart rate was shown")
    if activity_heart_rate({"average_heartrate": True}) is not None:
        raise AssertionError("a boolean heart rate was shown")
    if heart_rate_text({"average_heartrate": 141.5}) != "141.5 bpm":
        raise AssertionError(heart_rate_text({"average_heartrate": 141.5}))
    if "probability" in (heart_rate_text(recovery) or "") or "readiness" in (heart_rate_text(recovery) or ""):
        raise AssertionError("heart rate named a score")
    reader = (ROOT / "ui" / "last_session.py").read_text(encoding="utf-8")
    heart = _function(reader, "activity_heart_rate")
    if "icu_intervals" in heart:
        raise AssertionError("average heart rate was taken from a lap")


def test_loaded_distances_read_the_stored_file() -> None:
    """A stored id or filename contributes its WORK distance. A mismatch does not.

    Warm-up and cool-down stay out. The activity total is not the volume number.
    """
    sessions = [
        {"date": "2026-10-27", "template_id": "se_400_r90_x6"},
        {"date": "2026-10-29", "template_id": "se_400_r90_x6"},
    ]
    actuals = {
        "2026-10-27": {
            "template_id": "se_400_r90_x6",
            "intervals": "synthetic-se-400-with-recovery",
        },
        "2026-10-29": {
            "template_id": "other",
            "intervals": "synthetic-autosplit-no-rest",
        },
        "2026-10-31": {
            "template_id": "se_400_r90_x6",
            "intervals": "missing-file",
        },
    }
    with patch("urllib.request.urlopen", side_effect=AssertionError("live API")):
        found = loaded_distances(sessions, actuals)
        named = loaded_distances(
            sessions,
            {
                "2026-10-27": {
                    "template_id": "se_400_r90_x6",
                    "intervals": "synthetic_autosplit_no_rest.json",
                }
            },
        )
    recovery = json.loads(RECOVERY.read_text(encoding="utf-8"))
    autosplit = json.loads(AUTOSPLIT.read_text(encoding="utf-8"))
    if activity_distance(recovery) != 5600 or activity_distance(autosplit) != 5600:
        raise AssertionError("the fixture activity distance changed")
    if work_distance(recovery) != 2400 or work_distance(autosplit) != 2400:
        raise AssertionError((work_distance(recovery), work_distance(autosplit)))
    if found != {"2026-10-27": 2400.0} or named != {"2026-10-27": 2400.0}:
        raise AssertionError((found, named))
    activity = {"id": 44521, "distance": 8000, "average_heartrate": 151, "icu_intervals": []}
    blank = {"id": "no-distance", "icu_intervals": [{"distance": 400, "average_heartrate": 176}]}
    work = {
        "id": "work-day",
        "distance": 9000,
        "icu_intervals": [
            {"type": "WARMUP", "distance": 1600},
            {"type": "WORK", "distance": 400},
            {"type": "RECOVERY", "distance": 250},
            {"type": "WORK", "distance": 450},
            {"type": "COOLDOWN", "distance": 1600},
        ],
    }
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        (folder / "real_tuesday.json").write_text(json.dumps(activity), encoding="utf-8")
        (folder / "real_blank.json").write_text(json.dumps(blank), encoding="utf-8")
        (folder / "real_work.json").write_text(json.dumps(work), encoding="utf-8")
        (folder / "real_broken.json").write_text("{", encoding="utf-8")
        with patch("urllib.request.urlopen", side_effect=AssertionError("live API")):
            opened = activity_by_ref("44521", folder)
            distances = loaded_distances(
                [
                    {"date": "2026-10-20", "template_id": "se_400_r90_x6"},
                    {"date": "2026-10-21", "template_id": "se_400_r90_x6"},
                    {"date": "2026-10-22", "template_id": "se_400_r90_x6"},
                ],
                {
                    "2026-10-20": {"template_id": "se_400_r90_x6", "intervals": "44521"},
                    "2026-10-21": {"template_id": "se_400_r90_x6", "intervals": "no-distance"},
                    "2026-10-22": {"template_id": "se_400_r90_x6", "intervals": "work-day"},
                },
                folder,
            )
            missing = loaded_distances(
                [{"date": "2026-10-23", "template_id": "se_400_r90_x6"}],
                {"2026-10-23": {"template_id": "se_400_r90_x6", "intervals": "real_broken.json"}},
                folder,
            )
    if heart_rate_text(opened) != "151 bpm" or activity_distance(opened) != 8000:
        raise AssertionError((heart_rate_text(opened), activity_distance(opened)))
    if distances != {"2026-10-22": 850.0} or missing != {}:
        raise AssertionError((distances, missing))
    reader = (ROOT / "ui" / "last_session.py").read_text(encoding="utf-8")
    body = _function(reader, "loaded_distances")
    if "activity_distance(" in body or "work_distance(" not in body:
        raise AssertionError("loaded distance is not WORK interval distance")
    work_body = _function(reader, "work_distance")
    if "activity_distance(" in work_body or 'get("distance")' in work_body:
        raise AssertionError("WORK distance reads the activity total")


def test_session_shows_average_heart_rate() -> None:
    """Session detail shows Avg HR from the activity JSON. It does not call the API."""
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    page = _function(app, "page_session")
    if "heart_rate_text(" not in page or "Avg HR" not in page:
        raise AssertionError("the session page does not show average heart rate")
    if "fetch_activity" in page or "urlopen" in page or "explain(" in page or "SPEND_CAP" in page:
        raise AssertionError("the session page calls the network or spends")


def test_quality_session_prefills_from_the_file() -> None:
    """The session page fills the existing boxes and keeps judge() and adapt()."""
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    page = _function(app, "page_session")
    result = _function(app, "_render_result")
    commit = _function(app, "_commit_result")
    apply = _function(app, "_apply_result")
    choice = _function(app, "_intervals_choice")
    boxes = _function(app, "_time_box")
    if "quality_fill(" not in choice or "Intervals file" not in choice:
        raise AssertionError("a quality session cannot open an Intervals file")
    if "file_just_opened(" not in result or "fit_slots(" not in result:
        raise AssertionError("the file does not pre-fill the rep boxes")
    if "disabled" in boxes:
        raise AssertionError("the time boxes are locked")
    if "_apply_result(" not in result or "intervals=source" not in result:
        raise AssertionError("filled times do not go through the result path")
    if "judge(" not in apply or "_adapt_from_result(" not in commit:
        raise AssertionError("judge() or adapt() was bypassed")
    if 'row["intervals"]' not in commit or '"intervals"' not in apply:
        raise AssertionError("the file is not stored with the actuals")
    if "_quality_day(session)" not in page or "_render_result(" not in page:
        raise AssertionError("quality days lost the result boxes")
    if "fetch_activity" in app or "list_activities" in app or "urlopen" in app:
        raise AssertionError("the session page calls the live API")
    if "https://intervals.icu" in app:
        raise AssertionError("the session page calls Intervals.icu")
    if "explain(" in page or "SPEND_CAP" in page:
        raise AssertionError("the session page started spending")
    reader = (ROOT / "ui" / "last_session.py").read_text(encoding="utf-8")
    if "from engines" in reader or "explain(" in reader or "urlopen" in reader:
        raise AssertionError("the file reader started its own prose spend")


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
    test_quality_file_fills_work_times()
    test_quality_file_stores_filename_without_an_id()
    test_local_file_distance_and_heart_rate()
    test_loaded_distances_read_the_stored_file()
    test_session_shows_average_heart_rate()
    test_quality_session_prefills_from_the_file()
    test_page_keeps_the_fixture_dropdown_and_stays_offline()
    print("last session ok")
