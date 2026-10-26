# test_intervals_adapter.py — Intervals.icu JSON into normalize() and classify().

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from contextlib import contextmanager
from http.client import HTTPMessage
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.intervals_cli import main
from adapters.intervals_icu import (
    TIMEOUT_S,
    USER_AGENT,
    IntervalsIcuError,
    fetch_activity,
    list_activities,
    load_config,
    to_normalize_input,
)
from engines.classify import classify
from engines.normalize import normalize

FIXTURES = ROOT / "tests" / "fixtures" / "intervals"
RECOVERY = FIXTURES / "synthetic_se_400_with_recovery.json"
AUTOSPLIT = FIXTURES / "synthetic_autosplit_no_rest.json"
FAKE_KEY = "fixture-api-key"
MISSING_KEY = (
    "RIO_INTERVALS_API_KEY is not set. "
    "Set RIO_INTERVALS_API_KEY in the environment or .env."
)
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
NO_PATTERN = {
    "family": "unsure",
    "reason_codes": ["no_pattern"],
    "confidence": "unsure",
    "ontology_version": "v0.1",
}


def test_fixtures_are_marked_synthetic() -> None:
    for path in (RECOVERY, AUTOSPLIT):
        note = json.loads(path.read_text(encoding="utf-8")).get("note", "")
        if "SYNTHETIC" not in note:
            raise AssertionError(path.name)


def test_recovery_fixture_classifies_speed_endurance() -> None:
    raw = _load(RECOVERY)
    payload = to_normalize_input(raw)
    laps = normalize(payload)["laps"]
    if laps != [_work(90.0)] * 6:
        raise AssertionError(laps)
    if classify(payload) != SPEED_ENDURANCE:
        raise AssertionError(classify(payload))


def test_autosplit_fixture_is_rest_missing() -> None:
    raw = _load(AUTOSPLIT)
    payload = to_normalize_input(raw)
    laps = normalize(payload)["laps"]
    if laps != [_work(None)] * 6:
        raise AssertionError(laps)
    if classify(payload) != REST_MISSING:
        raise AssertionError(classify(payload))


def test_to_normalize_input_keeps_laps_and_drops_labels() -> None:
    raw = _load(RECOVERY)
    raw["family"] = "speed_endurance"
    raw["expected_family"] = "speed_endurance"
    raw["classification"] = {"family": "speed_endurance"}
    raw["icu_intervals"][0]["family"] = "aerobic"
    raw["icu_intervals"][0]["label"] = "warmup"
    raw["icu_intervals"][0]["expected_family"] = "aerobic"
    raw["icu_intervals"][0]["classification"] = "aerobic"
    payload = to_normalize_input(raw)
    steps = payload["intervals"]
    if set(payload) != {"intervals"}:
        raise AssertionError(set(payload))
    if len(steps) != len(raw["icu_intervals"]):
        raise AssertionError("a lap was dropped or merged")
    expected_roles = (
        "warmup",
        "work",
        "rest",
        "work",
        "rest",
        "work",
        "rest",
        "work",
        "rest",
        "work",
        "rest",
        "work",
        "rest",
        "cooldown",
    )
    if tuple(step["role"] for step in steps) != expected_roles:
        raise AssertionError([step["role"] for step in steps])
    for step, interval in zip(steps, raw["icu_intervals"]):
        if step["distance_m"] != interval["distance"]:
            raise AssertionError(step)
        if step["seconds"] != interval["elapsed_time"]:
            raise AssertionError(step)
        if set(step) - {"role", "distance_m", "seconds"}:
            raise AssertionError(step)
    if _keys(payload) & LABEL_KEYS:
        raise AssertionError(payload)


def test_null_and_unused_fields_stay_missing() -> None:
    payload = to_normalize_input(
        {
            "family": "speed_endurance",
            "icu_intervals": [
                {
                    "type": "WORK",
                    "distance": 400,
                    "elapsed_time": 57.5,
                    "moving_time": 50,
                    "average_speed": 8,
                    "average_heartrate": 176,
                    "start_time": 0,
                    "end_time": 57.5,
                    "family": "speed_endurance",
                    "classification": "speed_endurance",
                },
                {
                    "type": "WORK",
                    "distance": None,
                    "elapsed_time": None,
                    "moving_time": 57.5,
                    "average_speed": 6.9,
                },
                {"type": "RECOVERY", "distance": 0, "elapsed_time": 90, "moving_time": 0},
            ],
        }
    )
    steps = payload["intervals"]
    if steps[0] != {"role": "work", "distance_m": 400, "seconds": 57.5}:
        raise AssertionError(steps[0])
    if steps[1] != {"role": "work"}:
        raise AssertionError(steps[1])
    if steps[2] != {"role": "rest", "distance_m": 0, "seconds": 90}:
        raise AssertionError(steps[2])
    if _keys(payload) & LABEL_KEYS:
        raise AssertionError(payload)


def test_missing_intervals_are_no_pattern() -> None:
    for activity in ({}, {"icu_intervals": []}, {"icu_intervals": None}, {"name": "Empty"}):
        payload = to_normalize_input(activity)
        if payload != {"intervals": []}:
            raise AssertionError(payload)
        if classify(payload) != NO_PATTERN:
            raise AssertionError(classify(payload))


def test_load_config_requires_api_key_and_defaults_athlete() -> None:
    original = os.environ.get("RIO_INTERVALS_API_KEY")
    with _env(RIO_INTERVALS_API_KEY=None, RIO_INTERVALS_ATHLETE_ID=None):
        _expect_missing_key(original)
    with _env(RIO_INTERVALS_API_KEY="   ", RIO_INTERVALS_ATHLETE_ID="athlete-7"):
        _expect_missing_key(original)
    with _env(RIO_INTERVALS_API_KEY=FAKE_KEY, RIO_INTERVALS_ATHLETE_ID=None):
        config = load_config()
        if config["athlete_id"] != "0":
            raise AssertionError(config["athlete_id"])
        if config["api_key"] != FAKE_KEY:
            raise AssertionError("api key was not the environment value")
    with _env(RIO_INTERVALS_API_KEY=FAKE_KEY, RIO_INTERVALS_ATHLETE_ID="   "):
        if load_config()["athlete_id"] != "0":
            raise AssertionError(load_config()["athlete_id"])
    with _env(RIO_INTERVALS_API_KEY=FAKE_KEY, RIO_INTERVALS_ATHLETE_ID=" athlete-7 "):
        if load_config()["athlete_id"] != "athlete-7":
            raise AssertionError(load_config()["athlete_id"])


def test_fetch_activity_request() -> None:
    with _env(RIO_INTERVALS_API_KEY=FAKE_KEY, RIO_INTERVALS_ATHLETE_ID="0"):
        request, timeout, payload = _capture(lambda: fetch_activity("i123"))
    if payload != {"id": "i123", "icu_intervals": []}:
        raise AssertionError(payload)
    if timeout != TIMEOUT_S:
        raise AssertionError(timeout)
    if request.full_url != "https://intervals.icu/api/v1/activity/i123?intervals=true":
        raise AssertionError(request.full_url)
    if FAKE_KEY in request.full_url:
        raise AssertionError("activity URL included the API key")
    _expect_browser_agent(request)
    _expect_basic_auth(request)

    with _env(RIO_INTERVALS_API_KEY=FAKE_KEY, RIO_INTERVALS_ATHLETE_ID="0"):
        quoted, _, _ = _capture(lambda: fetch_activity("a/b"))
    if quoted.full_url != "https://intervals.icu/api/v1/activity/a%2Fb?intervals=true":
        raise AssertionError(quoted.full_url)


def test_fetch_activity_http_errors() -> None:
    cases = (
        (401, None, "Intervals.icu returned 401 Unauthorized. Check RIO_INTERVALS_API_KEY."),
        (404, None, "Intervals.icu returned 404 Not Found."),
        (429, "12", "Intervals.icu returned 429 Too Many Requests. Retry-After: 12"),
        (429, None, "Intervals.icu returned 429 Too Many Requests. Retry-After: missing"),
    )
    for code, retry_after, expected in cases:
        calls = {"n": 0}

        def fake(request, timeout=None, code=code, retry_after=retry_after):
            calls["n"] += 1
            raise _http_error(code, retry_after)

        with _env(RIO_INTERVALS_API_KEY=FAKE_KEY, RIO_INTERVALS_ATHLETE_ID="0"):
            with patch("adapters.intervals_icu.urllib.request.urlopen", side_effect=fake):
                try:
                    fetch_activity("i123")
                except IntervalsIcuError as exc:
                    message = str(exc)
                else:
                    raise AssertionError(f"{code} did not raise")
        if message != expected:
            raise AssertionError(_redact(message))
        if FAKE_KEY in message:
            raise AssertionError("error included the API key")
        if calls["n"] != 1:
            raise AssertionError(f"{code} retried")


def test_list_activities_request() -> None:
    body = json.dumps(
        [
            {
                "id": "i1",
                "name": "Easy",
                "start_date_local": "2026-10-02T07:00:00",
                "type": "Run",
                "description": "not returned",
            },
            {"id": "i2", "start_date_local": "2026-10-03T07:00:00", "type": "Ride"},
        ]
    ).encode("utf-8")
    with _env(RIO_INTERVALS_API_KEY=FAKE_KEY, RIO_INTERVALS_ATHLETE_ID="athlete-7"):
        request, _, rows = _capture(
            lambda: list_activities("2026-10-01", "2026-10-25"),
            body,
        )
    expected_url = (
        "https://intervals.icu/api/v1/athlete/athlete-7/activities"
        "?oldest=2026-10-01&newest=2026-10-25"
    )
    if request.full_url != expected_url:
        raise AssertionError(request.full_url)
    if FAKE_KEY in request.full_url:
        raise AssertionError("activity list URL included the API key")
    _expect_basic_auth(request)
    if rows != [
        {
            "id": "i1",
            "name": "Easy",
            "start_date_local": "2026-10-02T07:00:00",
            "type": "Run",
        },
        {
            "id": "i2",
            "name": None,
            "start_date_local": "2026-10-03T07:00:00",
            "type": "Ride",
        },
    ]:
        raise AssertionError(rows)


def test_cli_file_prints_classify_without_network() -> None:
    with patch("adapters.intervals_icu.urllib.request.urlopen", side_effect=AssertionError("network")):
        recovery = _cli_file(RECOVERY)
        autosplit = _cli_file(AUTOSPLIT)
    if recovery[0] != SPEED_ENDURANCE:
        raise AssertionError(recovery[0])
    if recovery[1] != [_work(90.0)] * 6:
        raise AssertionError(recovery[1])
    if autosplit[0] != REST_MISSING:
        raise AssertionError(autosplit[0])
    if autosplit[1] != [_work(None)] * 6:
        raise AssertionError(autosplit[1])


def test_cli_module_file_exits_zero() -> None:
    for path, expected in ((RECOVERY, SPEED_ENDURANCE), (AUTOSPLIT, REST_MISSING)):
        completed = subprocess.run(
            [sys.executable, "-m", "adapters.intervals_cli", "--file", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=_offline_env(),
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(_redact(completed.stderr or completed.stdout))
        if completed.stderr:
            raise AssertionError(_redact(completed.stderr))
        result, laps = _printed(completed.stdout)
        if result != expected:
            raise AssertionError(result)
        if not laps:
            raise AssertionError(completed.stdout)


def test_cli_save_json_writes_the_fetched_activity() -> None:
    activity = {
        "id": "i99",
        "name": "Fetched",
        "start_date_local": "2026-10-25T08:00:00",
        "note": "raw fetch",
        "icu_intervals": [],
    }
    with tempfile.TemporaryDirectory() as directory:
        destination = Path(directory) / "real_2026-10-25_fetched.json"
        with patch("adapters.intervals_icu.urllib.request.urlopen", side_effect=AssertionError("network")):
            with patch("adapters.intervals_cli._load_dotenv", return_value=None):
                with patch("adapters.intervals_cli.fetch_activity", return_value=activity) as fetch:
                    stdout = _capture_stdout(
                        ["--activity-id", "i99", "--save-json", str(destination)]
                    )
        if fetch.call_args.args != ("i99",):
            raise AssertionError("activity id was not passed through")
        saved = json.loads(destination.read_text(encoding="utf-8"))
        if saved != activity:
            raise AssertionError("saved JSON was not the fetched activity")
        result, laps = _printed(stdout)
        if result != NO_PATTERN or laps != []:
            raise AssertionError((result, laps))


def test_cli_list_prints_rows_without_network() -> None:
    rows = [
        {
            "id": "i1",
            "name": "Easy",
            "start_date_local": "2026-10-02T07:00:00",
            "type": "Run",
        }
    ]
    with patch("adapters.intervals_icu.urllib.request.urlopen", side_effect=AssertionError("network")):
        with patch("adapters.intervals_cli._load_dotenv", return_value=None):
            with patch("adapters.intervals_cli.list_activities", return_value=rows) as listed:
                stdout = _capture_stdout(
                    ["--list", "--oldest", "2026-10-01", "--newest", "2026-10-25"]
                )
    if listed.call_args.args != ("2026-10-01", "2026-10-25"):
        raise AssertionError("list dates were not passed through")
    if stdout.strip() != "id: i1 | name: Easy | date: 2026-10-02T07:00:00 | type: Run":
        raise AssertionError(stdout)


def test_cli_rejects_save_json_without_a_fetch() -> None:
    try:
        main(["--file", str(RECOVERY), "--save-json", "activity.json"])
    except SystemExit as exc:
        if exc.code == 0:
            raise AssertionError("save-json with --file was accepted")
    else:
        raise AssertionError("expected the CLI to reject --save-json with --file")


def _work(rest_s: float | None) -> dict:
    return {"distance_m": 400.0, "seconds": 57.5, "rest_s": rest_s}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _expect_missing_key(original: str | None) -> None:
    try:
        load_config()
    except IntervalsIcuError as exc:
        message = str(exc)
    else:
        raise AssertionError("missing RIO_INTERVALS_API_KEY did not raise")
    if message != MISSING_KEY:
        redacted = message
        if original:
            redacted = redacted.replace(original, "[redacted]")
        raise AssertionError(_redact(redacted))
    if FAKE_KEY in message or (original and original in message):
        raise AssertionError("missing-key error included a key value")


def _capture(call, body: bytes | None = None):
    if body is None:
        body = b'{"id":"i123","icu_intervals":[]}'
    captured: dict = {}

    def fake(request, timeout=None):
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response(body)

    with patch("adapters.intervals_icu.urllib.request.urlopen", side_effect=fake):
        payload = call()
    return captured["request"], captured["timeout"], payload


def _header(request: urllib.request.Request, name: str) -> str | None:
    return request.get_header(name.capitalize())


def _expect_browser_agent(request: urllib.request.Request) -> None:
    agent = _header(request, "User-Agent")
    if agent != USER_AGENT:
        raise AssertionError("User-Agent was not the adapter header")
    if not agent or "Mozilla/5.0" not in agent or agent.startswith("Python-urllib"):
        raise AssertionError("User-Agent is not browser-like")


def _expect_basic_auth(request: urllib.request.Request) -> None:
    header = _header(request, "Authorization")
    if not header or not header.startswith("Basic "):
        raise AssertionError("Authorization was not Basic auth")
    try:
        decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise AssertionError("Authorization was not base64") from exc
    user, separator, password = decoded.partition(":")
    if separator != ":" or user != "API_KEY":
        raise AssertionError("basic auth user was not API_KEY")
    if password != FAKE_KEY:
        raise AssertionError("basic auth password was not the configured API key")


def _http_error(code: int, retry_after: str | None) -> urllib.error.HTTPError:
    headers = HTTPMessage()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError(
        "https://intervals.icu/api/v1/activity/i123?intervals=true",
        code,
        "error",
        headers,
        None,
    )


def _cli_file(path: Path) -> tuple[dict, list]:
    stdout = _capture_stdout(["--file", str(path)])
    return _printed(stdout)


def _capture_stdout(argv: list[str]) -> str:
    from io import StringIO
    from contextlib import redirect_stdout

    buffer = StringIO()
    with redirect_stdout(buffer):
        code = main(argv)
    if code != 0:
        raise AssertionError(code)
    return buffer.getvalue()


def _printed(stdout: str) -> tuple[dict, list]:
    laps_at = stdout.find("laps:\n")
    classify_at = stdout.find("\nclassify:\n")
    if laps_at < 0 or classify_at < 0:
        raise AssertionError(stdout)
    laps = json.loads(stdout[laps_at + len("laps:\n") : classify_at])
    result = json.loads(stdout[classify_at + len("\nclassify:\n") :])
    return result, laps


def _offline_env() -> dict[str, str]:
    env = os.environ.copy()
    # A set value stops a buggy live path from replacing it with .env.
    env["RIO_INTERVALS_API_KEY"] = FAKE_KEY
    env["RIO_INTERVALS_ATHLETE_ID"] = "0"
    return env


def _redact(text: str) -> str:
    redacted = text.replace(FAKE_KEY, "[redacted]")
    original = os.environ.get("RIO_INTERVALS_API_KEY")
    if original:
        redacted = redacted.replace(original, "[redacted]")
    return redacted


class _Response:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> bool:
        return False


@contextmanager
def _env(**values: str | None):
    saved = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, old in saved.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
