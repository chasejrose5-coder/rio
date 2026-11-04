# strava.py — Strava OAuth and run import. Rules only. No model.

"""Authorization code flow, token refresh, and run parsing.

HTTP is injected so tests never call Strava. Tokens are not printed.
Only Run, TrackRun, and VirtualRun are imported.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

from engines.pace import PaceLog, workout_times

CLIENT_ID = "RIO_STRAVA_CLIENT_ID"
CLIENT_SECRET = "RIO_STRAVA_CLIENT_SECRET"
SCOPE = "activity:read_all"
RUN_TYPES = frozenset({"Run", "TrackRun", "VirtualRun"})
AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
DEAUTH_URL = "https://www.strava.com/oauth/deauthorize"
LIST_URL = "https://www.strava.com/api/v3/athlete/activities"
DETAIL_URL = "https://www.strava.com/api/v3/activities/{}"
QUARTER = 15 * 60
DAY = 24 * 60 * 60


class StravaError(ValueError):
    """A Strava call failed. The message is safe to show."""


class StravaLimited(StravaError):
    """The rate limit was reached. The message is safe to show."""


def configured() -> bool:
    """True when both Strava settings are present. Values are not returned."""
    from ui.cloud_config import read_setting

    return bool(read_setting(CLIENT_ID) and read_setting(CLIENT_SECRET))


def redirect_uri() -> str:
    from ui.cloud_config import app_url

    return app_url() + "/"


def make_state(user_id: str, nonce: str) -> str:
    """A state value bound to this user. The client secret never leaves the server."""
    from ui.cloud_config import read_setting

    secret = read_setting(CLIENT_SECRET).encode("utf-8")
    digest = hmac.new(secret, f"{user_id}.{nonce}".encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{user_id}.{nonce}.{digest}"


def state_matches(state: object, user_id: str, nonce: str = "") -> bool:
    """True when this state was signed for this user. A stored nonce is optional."""
    if not isinstance(state, str) or not user_id or "." not in state:
        return False
    prefix = f"{user_id}."
    if not state.startswith(prefix):
        return False
    rest = state[len(prefix) :]
    if "." not in rest:
        return False
    found, digest = rest.rsplit(".", 1)
    if nonce and found != nonce:
        return False
    from ui.cloud_config import read_setting

    secret = read_setting(CLIENT_SECRET).encode("utf-8")
    expected = hmac.new(secret, f"{user_id}.{found}".encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, expected)


def authorize_url(client_id: str, redirect: str, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect,
            "approval_prompt": "auto",
            "scope": SCOPE,
            "state": state,
        }
    )
    return f"{AUTH_URL}?{query}"


def parse_token(payload: object) -> dict:
    """The fields we keep from a token response. Nothing else is stored."""
    if not isinstance(payload, dict):
        raise StravaError("Strava could not be connected.")
    access = payload.get("access_token")
    refresh = payload.get("refresh_token")
    expires = payload.get("expires_at")
    if not isinstance(access, str) or not access or not isinstance(refresh, str) or not refresh:
        raise StravaError("Strava could not be connected.")
    if isinstance(expires, bool) or not isinstance(expires, int):
        raise StravaError("Strava could not be connected.")
    athlete = payload.get("athlete") if isinstance(payload.get("athlete"), dict) else {}
    first = str(athlete.get("firstname") or "").strip()
    last = str(athlete.get("lastname") or "").strip()
    name = (first + " " + last).strip()
    athlete_id = athlete.get("id")
    return {
        "access_token": access,
        "refresh_token": refresh,
        "expires_at": expires,
        "athlete_id": athlete_id if isinstance(athlete_id, int) else None,
        "athlete_name": name,
        "scope": SCOPE,
    }


def refresh_if_needed(token: dict, now: int, post) -> dict:
    """Return a usable token. An expired access token is refreshed once."""
    expires = token.get("expires_at")
    if isinstance(expires, int) and expires > now + 60:
        return token
    from ui.cloud_config import read_setting

    payload = post(
        TOKEN_URL,
        {
            "client_id": read_setting(CLIENT_ID),
            "client_secret": read_setting(CLIENT_SECRET),
            "grant_type": "refresh_token",
            "refresh_token": token.get("refresh_token") or "",
        },
    )
    fresh = parse_token(payload)
    if not fresh.get("athlete_name"):
        fresh["athlete_name"] = token.get("athlete_name") or ""
    if fresh.get("athlete_id") is None:
        fresh["athlete_id"] = token.get("athlete_id")
    return fresh


def exchange_code(code: str, post) -> dict:
    from ui.cloud_config import read_setting

    payload = post(
        TOKEN_URL,
        {
            "client_id": read_setting(CLIENT_ID),
            "client_secret": read_setting(CLIENT_SECRET),
            "code": code,
            "grant_type": "authorization_code",
        },
    )
    return parse_token(payload)


def deauthorize(access_token: str, post) -> None:
    post(DEAUTH_URL, {"access_token": access_token})


class RateGate:
    """100 requests in 15 minutes and 1000 in a day."""

    def __init__(self, per_quarter: int = 100, per_day: int = 1000) -> None:
        self.per_quarter = per_quarter
        self.per_day = per_day
        self.stamps: list[int] = []

    def take(self, now: int) -> None:
        self.stamps = [stamp for stamp in self.stamps if now - stamp < DAY]
        recent = [stamp for stamp in self.stamps if now - stamp < QUARTER]
        if len(self.stamps) >= self.per_day or len(recent) >= self.per_quarter:
            raise StravaLimited("Strava is busy. Try again in a few minutes.")
        self.stamps.append(now)


def pace_seconds_per_km(distance_m: object, moving_seconds: object) -> float | None:
    if isinstance(distance_m, bool) or isinstance(moving_seconds, bool):
        return None
    if not isinstance(distance_m, (int, float)) or not isinstance(moving_seconds, (int, float)):
        return None
    if distance_m <= 0 or moving_seconds <= 0:
        return None
    return float(moving_seconds) / (float(distance_m) / 1000.0)


def pace_text(seconds_per_km: float | None) -> str:
    if seconds_per_km is None or seconds_per_km <= 0:
        return "—"
    total = int(round(seconds_per_km))
    return f"{total // 60}:{total % 60:02d} /km"


def local_day(value: object) -> str:
    """YYYY-MM-DD from Strava's local start. A UTC stamp is the fallback."""
    if not isinstance(value, str) or len(value) < 10:
        return ""
    text = value[:10]
    try:
        date.fromisoformat(text)
    except ValueError:
        return ""
    return text


def parse_lap(row: object) -> dict | None:
    if not isinstance(row, dict):
        return None
    distance = row.get("distance")
    moving = row.get("moving_time")
    if moving is None:
        moving = row.get("elapsed_time")
    elapsed = row.get("elapsed_time")
    pace = pace_seconds_per_km(distance, moving)
    hr = row.get("average_heartrate")
    return {
        "distance_m": float(distance) if isinstance(distance, (int, float)) and not isinstance(distance, bool) else None,
        "moving_seconds": int(moving) if isinstance(moving, int) and not isinstance(moving, bool) else None,
        "elapsed_seconds": int(elapsed) if isinstance(elapsed, int) and not isinstance(elapsed, bool) else None,
        "pace_s_per_km": pace,
        "average_hr": int(hr) if isinstance(hr, (int, float)) and not isinstance(hr, bool) else None,
    }


def sport_type(row: dict) -> str:
    sport = row.get("sport_type") or row.get("type") or ""
    return str(sport)


def parse_activity(summary: object, detail: object | None = None) -> dict | None:
    """One run, or None when the sport is not a run."""
    source = detail if isinstance(detail, dict) else summary
    if not isinstance(source, dict):
        return None
    if sport_type(source) not in RUN_TYPES:
        return None
    ident = source.get("id")
    if isinstance(ident, bool) or not isinstance(ident, int):
        return None
    day = local_day(source.get("start_date_local")) or local_day(source.get("start_date"))
    if not day:
        return None
    distance = source.get("distance")
    moving = source.get("moving_time")
    elapsed = source.get("elapsed_time")
    avg = source.get("average_heartrate")
    maximum = source.get("max_heartrate")
    laps = []
    raw_laps = source.get("laps")
    if isinstance(raw_laps, list):
        for lap in raw_laps:
            parsed = parse_lap(lap)
            if parsed is not None:
                laps.append(parsed)
    return {
        "id": f"strava-{ident}",
        "strava_id": ident,
        "name": str(source.get("name") or "Run"),
        "sport_type": sport_type(source),
        "date": day,
        "start_local": str(source.get("start_date_local") or ""),
        "distance_m": float(distance) if isinstance(distance, (int, float)) and not isinstance(distance, bool) else None,
        "moving_seconds": int(moving) if isinstance(moving, int) and not isinstance(moving, bool) else None,
        "elapsed_seconds": int(elapsed) if isinstance(elapsed, int) and not isinstance(elapsed, bool) else None,
        "pace_s_per_km": pace_seconds_per_km(distance, moving),
        "average_hr": int(avg) if isinstance(avg, (int, float)) and not isinstance(avg, bool) else None,
        "max_hr": int(maximum) if isinstance(maximum, (int, float)) and not isinstance(maximum, bool) else None,
        "laps": laps,
    }


def match_runs(runs: list[dict], sessions: object) -> list[dict]:
    """A run matches the planned session on the same local date."""
    planned: set[str] = set()
    templates: dict[str, str] = {}
    if isinstance(sessions, list):
        for session in sessions:
            if not isinstance(session, dict):
                continue
            day = session.get("date")
            if isinstance(day, str):
                planned.add(day)
                template = session.get("template_id")
                if isinstance(template, str) and day not in templates:
                    templates[day] = template
    matched = []
    for run in runs:
        row = dict(run)
        day = row.get("date")
        row["matched"] = isinstance(day, str) and day in planned
        row["template_id"] = templates.get(day, "") if isinstance(day, str) else ""
        matched.append(row)
    return matched


def to_stored_activity(run: dict) -> dict:
    """The shape Activity and Home already match by date."""
    reps = []
    for lap in run.get("laps") or []:
        if isinstance(lap, dict) and isinstance(lap.get("moving_seconds"), int):
            reps.append(lap["moving_seconds"])
    return {
        "id": run.get("id"),
        "date": run.get("date"),
        "name": run.get("name") or "Run",
        "matched": run.get("matched") is True,
        "work_m": run.get("distance_m"),
        "heart_rate": run.get("average_hr"),
        "start": run.get("start_local") or "",
        "reps": reps,
        "source": "strava",
        "template_id": run.get("template_id") or "",
        "pace_s_per_km": run.get("pace_s_per_km"),
        "moving_seconds": run.get("moving_seconds"),
        "elapsed_seconds": run.get("elapsed_seconds"),
        "max_hr": run.get("max_hr"),
    }


def planned_vs_actual(run: dict, *, current: str, goal: str, start: date, goal_day: date, on: date) -> dict:
    """Planned line and status from workout_times, next to this run."""
    template = run.get("template_id") or ""
    logs = []
    if isinstance(run.get("pace_s_per_km"), float) and isinstance(run.get("moving_seconds"), int):
        try:
            logs.append(PaceLog(date.fromisoformat(str(run.get("date"))), float(run["moving_seconds"]), str(template)))
        except ValueError:
            logs = []
    found = None
    if template:
        try:
            found = workout_times(
                template,
                current_mark=current,
                goal_mark=goal,
                start=start,
                goal_date=goal_day,
                on=on,
                logs=logs,
            )
        except ValueError:
            found = None
    status = "On track"
    planned = "—"
    if isinstance(found, dict):
        planned = str(found.get("line") or "—")
        text = str(found.get("status") or "on track")
        status = text[:1].upper() + text[1:]
    distance = run.get("distance_m")
    distance_text = "—"
    if isinstance(distance, float):
        distance_text = f"{distance / 1000:.1f} km"
    return {
        "date": run.get("date") or "",
        "name": run.get("name") or "Run",
        "planned": planned,
        "actual": f"{distance_text} · {pace_text(run.get('pace_s_per_km'))}",
        "status": status,
    }


def list_after(now: int, last_sync: int | None) -> int:
    """Epoch for the list call. Thirty days, or the last sync when it is later."""
    month = int((datetime.fromtimestamp(now, timezone.utc) - timedelta(days=30)).timestamp())
    if isinstance(last_sync, int) and last_sync > month:
        return last_sync
    return month


def import_runs(token: dict, *, now: int, last_sync: int | None, get, post, gate: RateGate) -> tuple[dict, list[dict]]:
    """Refresh if needed, then import runs. Non-runs are dropped."""
    fresh = refresh_if_needed(token, now, post)
    gate.take(now)
    listed = get(
        LIST_URL,
        {"after": list_after(now, last_sync), "per_page": 100},
        fresh["access_token"],
    )
    if not isinstance(listed, list):
        raise StravaError("Strava activities could not be read.")
    runs = []
    for summary in listed:
        if not isinstance(summary, dict):
            continue
        if sport_type(summary) not in RUN_TYPES:
            continue
        detail = summary
        if not isinstance(summary.get("laps"), list):
            ident = summary.get("id")
            if isinstance(ident, int):
                gate.take(now)
                loaded = get(DETAIL_URL.format(ident), {}, fresh["access_token"])
                if isinstance(loaded, dict):
                    detail = loaded
        parsed = parse_activity(summary, detail)
        if parsed is not None:
            runs.append(parsed)
    return fresh, runs


def http_post(url: str, form: dict) -> dict:
    if os.environ.get("RIO_STRAVA_TRANSPORT") == "fake":
        return _fake_post(url, form)
    data = urllib.parse.urlencode(form).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise StravaError("Strava could not be reached.") from exc
    if not isinstance(payload, dict):
        raise StravaError("Strava could not be reached.")
    return payload


def http_get(url: str, query: dict, access_token: str) -> object:
    if os.environ.get("RIO_STRAVA_TRANSPORT") == "fake":
        return _fake_get(url, query)
    joined = url
    if query:
        joined = url + "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(joined, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise StravaError("Strava could not be reached.") from exc


def _fake_post(url: str, form: dict) -> dict:
    if url == DEAUTH_URL:
        return {}
    return {
        "access_token": "fake-access",
        "refresh_token": "fake-refresh",
        "expires_at": int(time.time()) + 3600,
        "athlete": {"id": 7, "firstname": "Ada", "lastname": "Lovelace"},
    }


def _fake_get(url: str, query: dict) -> object:
    if "/activities/" in url and not url.rstrip("/").endswith("activities"):
        return {
            "id": 42,
            "name": "Morning Run",
            "sport_type": "Run",
            "start_date_local": "2026-11-03T08:00:00",
            "distance": 5000.0,
            "moving_time": 1500,
            "elapsed_time": 1560,
            "average_heartrate": 148,
            "max_heartrate": 170,
            "laps": [
                {"distance": 1000, "moving_time": 300, "elapsed_time": 300, "average_heartrate": 145},
            ],
        }
    return [
        {
            "id": 42,
            "name": "Morning Run",
            "sport_type": "Run",
            "start_date_local": "2026-11-03T08:00:00",
            "distance": 5000.0,
            "moving_time": 1500,
            "elapsed_time": 1560,
            "average_heartrate": 148,
            "max_heartrate": 170,
        },
        {
            "id": 43,
            "name": "Ride",
            "sport_type": "Ride",
            "start_date_local": "2026-11-03T18:00:00",
            "distance": 20000,
            "moving_time": 3600,
            "elapsed_time": 3700,
        },
    ]
