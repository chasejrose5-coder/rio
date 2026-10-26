# intervals_icu.py — read-only Intervals.icu adapter. Not the product.

"""Turn one Intervals.icu activity into the lap dict normalize() accepts."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import NoReturn

API_ROOT = "https://intervals.icu/api/v1"

# Cloudflare rejects the default Python-urllib agent.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT_S = 30

# Intervals.icu basic-auth username. The password is the API key.
API_USER = "API_KEY"

_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# RECOVERY becomes the rest role normalize() already attaches to the previous
# work lap. Other types are only lowercased: WARMUP and COOLDOWN stay in the
# list and match the skip roles normalize() already knows. Nothing is dropped.
_ROLE_NAMES = {
    "work": "work",
    "recovery": "rest",
}

_MISSING_KEY = (
    "RIO_INTERVALS_API_KEY is not set. "
    "Set RIO_INTERVALS_API_KEY in the environment or .env."
)


class IntervalsIcuError(Exception):
    """A readable Intervals.icu failure. The message never includes the API key."""


def load_config() -> dict[str, str]:
    """Read RIO_INTERVALS_API_KEY and RIO_INTERVALS_ATHLETE_ID from the environment.

    Athlete id defaults to "0" (the key's own athlete) when it is unset or blank.
    """
    if "RIO_INTERVALS_API_KEY" not in os.environ or os.environ["RIO_INTERVALS_API_KEY"].strip() == "":
        raise IntervalsIcuError(_MISSING_KEY)
    athlete = os.environ.get("RIO_INTERVALS_ATHLETE_ID")
    if athlete is None or athlete.strip() == "":
        athlete_id = "0"
    else:
        athlete_id = athlete.strip()
    return {
        "api_key": os.environ["RIO_INTERVALS_API_KEY"],
        "athlete_id": athlete_id,
    }


def fetch_activity(activity_id: object) -> dict:
    """GET one activity with intervals=true. One request, no retry."""
    config = load_config()
    payload = _get_json(_activity_url(activity_id), config["api_key"])
    if not isinstance(payload, dict):
        raise IntervalsIcuError("Intervals.icu activity response was not a JSON object.")
    return payload


def list_activities(oldest: str, newest: str) -> list[dict]:
    """Return id, name, start_date_local, and type for each activity in the range."""
    config = load_config()
    url = _activities_url(
        config["athlete_id"],
        _require_day("oldest", oldest),
        _require_day("newest", newest),
    )
    payload = _get_json(url, config["api_key"])
    if not isinstance(payload, list):
        raise IntervalsIcuError("Intervals.icu activity list was not a JSON array.")
    rows: list[dict] = []
    for item in payload:
        if not isinstance(item, dict):
            raise IntervalsIcuError("Intervals.icu activity list contained a non-object.")
        rows.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "start_date_local": item.get("start_date_local"),
                "type": item.get("type"),
            }
        )
    return rows


def to_normalize_input(activity_json: dict) -> dict:
    """Build {"intervals": [...]} from icu_intervals, in order.

    Distance is meters (distance_m). elapsed_time becomes seconds. WORK is the
    work role and RECOVERY is the rest role. Missing and null fields stay off
    the step. Label fields are not copied. Laps are not dropped, merged, or filled in.
    """
    if not isinstance(activity_json, dict):
        raise TypeError("activity JSON must be an object")
    raw_intervals = activity_json.get("icu_intervals")
    if raw_intervals is None:
        raw_intervals = []
    if not isinstance(raw_intervals, list):
        raise TypeError("icu_intervals must be a list")
    return {"intervals": [_step(raw) for raw in raw_intervals]}


def _step(raw: object) -> dict:
    if not isinstance(raw, dict):
        raise TypeError("each icu interval must be an object")
    step: dict = {}
    role = _role_name(raw.get("type"))
    if role is not None:
        step["role"] = role
    # ICU distance is already meters. normalize() reads distance_m, not "meters".
    if "distance" in raw and raw["distance"] is not None:
        step["distance_m"] = raw["distance"]
    # elapsed_time only. moving_time is not a fallback: a standing rest can be 0.
    if "elapsed_time" in raw and raw["elapsed_time"] is not None:
        step["seconds"] = raw["elapsed_time"]
    return step


def _role_name(icu_type: object) -> str | None:
    if icu_type is None:
        return None
    text = str(icu_type).strip().lower().replace(" ", "_").replace("-", "_")
    if text in {"", "none", "null"}:
        return None
    return _ROLE_NAMES.get(text, text)


def _activity_url(activity_id: object) -> str:
    if activity_id is None:
        raise IntervalsIcuError("activity id is missing")
    text = str(activity_id).strip()
    if not text:
        raise IntervalsIcuError("activity id is missing")
    quoted = urllib.parse.quote(text, safe="")
    return f"{API_ROOT}/activity/{quoted}?intervals=true"


def _activities_url(athlete_id: str, oldest: str, newest: str) -> str:
    quoted = urllib.parse.quote(str(athlete_id), safe="")
    query = urllib.parse.urlencode({"oldest": oldest, "newest": newest})
    return f"{API_ROOT}/athlete/{quoted}/activities?{query}"


def _require_day(label: str, value: object) -> str:
    text = str(value).strip() if value is not None else ""
    if _DAY.fullmatch(text) is None:
        raise IntervalsIcuError(f"{label} must be YYYY-MM-DD.")
    return text


def _get_json(url: str, api_key: str) -> object:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": _basic_authorization(api_key),
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        # HTTPError is a URLError, so it has to be handled first. No retry.
        _fail_http(exc)
    except urllib.error.URLError as exc:
        raise IntervalsIcuError(
            f"Intervals.icu request failed before a response ({exc.reason})."
        ) from exc
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntervalsIcuError("Intervals.icu returned a body that is not JSON.") from exc


def _basic_authorization(api_key: str) -> str:
    token = base64.b64encode(f"{API_USER}:{api_key}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _fail_http(exc: urllib.error.HTTPError) -> NoReturn:
    if exc.code == 401:
        raise IntervalsIcuError(
            "Intervals.icu returned 401 Unauthorized. Check RIO_INTERVALS_API_KEY."
        ) from exc
    if exc.code == 404:
        raise IntervalsIcuError("Intervals.icu returned 404 Not Found.") from exc
    if exc.code == 429:
        raise IntervalsIcuError(
            "Intervals.icu returned 429 Too Many Requests. "
            f"Retry-After: {_retry_after(exc)}"
        ) from exc
    raise IntervalsIcuError(f"Intervals.icu returned {exc.code}.") from exc


def _retry_after(exc: urllib.error.HTTPError) -> str:
    headers = exc.headers
    if not headers:
        return "missing"
    value = headers.get("Retry-After")
    if value is None or str(value).strip() == "":
        return "missing"
    return str(value).strip()
