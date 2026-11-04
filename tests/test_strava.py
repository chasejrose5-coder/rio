# test_strava.py — OAuth, import, matching, and disconnect. No live HTTP.

from __future__ import annotations

import os
import sys
import urllib.parse
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.strava import (
    SCOPE,
    RateGate,
    StravaLimited,
    authorize_url,
    deauthorize,
    exchange_code,
    import_runs,
    make_state,
    match_runs,
    parse_activity,
    parse_lap,
    planned_vs_actual,
    state_matches,
)
from ui.strava_store import reset_memory_strava

_NAMES = ("RIO_STRAVA_CLIENT_ID", "RIO_STRAVA_CLIENT_SECRET")


def _use_fake_secrets() -> dict:
    saved = {name: os.environ.get(name) for name in _NAMES}
    os.environ["RIO_STRAVA_CLIENT_ID"] = "test-client"
    os.environ["RIO_STRAVA_CLIENT_SECRET"] = "test-secret"
    return saved


def _restore(saved: dict) -> None:
    for name, value in saved.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def _token_payload(expires: int) -> dict:
    return {
        "access_token": "access-1",
        "refresh_token": "refresh-1",
        "expires_at": expires,
        "athlete": {"id": 7, "firstname": "Ada", "lastname": "Lovelace"},
    }


def test_oauth_state_and_exchange() -> None:
    saved = _use_fake_secrets()
    try:
        state = make_state("user-1", "nonce-1")
        if not state_matches(state, "user-1", "nonce-1"):
            raise AssertionError("the state did not match this user")
        if state_matches(state, "user-2", "nonce-1"):
            raise AssertionError("another user matched the state")
        url = authorize_url("test-client", "http://localhost:8501/", state)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if query.get("scope") != [SCOPE] or query.get("state") != [state] or "test-secret" in url:
            raise AssertionError(url)
        calls = []

        def post(url, form):
            calls.append(form.get("grant_type"))
            if "client_secret" not in form:
                raise AssertionError("the exchange omitted the secret")
            return _token_payload(1_800_000_000)

        token = exchange_code("code-1", post)
        if token["athlete_name"] != "Ada Lovelace" or token["refresh_token"] != "refresh-1":
            raise AssertionError(token)
        if calls != ["authorization_code"]:
            raise AssertionError(calls)
        refreshed = {"access_token": "access-2", "refresh_token": "refresh-2", "expires_at": 1_800_000_100}

        def refresh(url, form):
            if form.get("grant_type") != "refresh_token":
                raise AssertionError(form.get("grant_type"))
            return refreshed

        from ui.strava import refresh_if_needed

        again = refresh_if_needed(token, 1_800_000_000, refresh)
        if again["access_token"] != "access-2":
            raise AssertionError(again)
        kept = refresh_if_needed(again, 1_800_000_010, refresh)
        if kept["access_token"] != "access-2":
            raise AssertionError("a fresh token was refreshed again")
    finally:
        _restore(saved)


def test_import_parses_runs_and_matches_the_plan() -> None:
    saved = _use_fake_secrets()
    try:
        listed = [
            {
                "id": 5,
                "name": "Easy",
                "sport_type": "Run",
                "start_date_local": "2026-11-03T08:00:00",
                "distance": 5000,
                "moving_time": 1500,
                "elapsed_time": 1600,
                "average_heartrate": 140,
                "max_heartrate": 160,
            },
            {
                "id": 6,
                "name": "Ride",
                "sport_type": "Ride",
                "start_date_local": "2026-11-03T18:00:00",
                "distance": 10000,
                "moving_time": 2000,
                "elapsed_time": 2100,
            },
        ]
        detail = dict(listed[0])
        detail["laps"] = [
            {"distance": 1000, "moving_time": 300, "elapsed_time": 310, "average_heartrate": 142},
        ]

        def get(url, query, access):
            if url.endswith("/activities"):
                return listed
            return detail

        def post(url, form):
            return _token_payload(1_700_000_000 + 10_000)

        token, runs = import_runs(
            {"access_token": "a", "refresh_token": "r", "expires_at": 1_700_000_000 - 10, "athlete_name": "Ada"},
            now=1_700_000_000,
            last_sync=None,
            get=get,
            post=post,
            gate=RateGate(),
        )
        if len(runs) != 1 or runs[0]["name"] != "Easy":
            raise AssertionError(runs)
        lap = parse_lap(detail["laps"][0])
        if lap is None or lap["distance_m"] != 1000 or lap["average_hr"] != 142:
            raise AssertionError(lap)
        if runs[0]["laps"][0]["pace_s_per_km"] != 300:
            raise AssertionError(runs[0]["laps"])
        if runs[0]["pace_s_per_km"] != 300:
            raise AssertionError(runs[0]["pace_s_per_km"])
        ride = parse_activity(listed[1])
        if ride is not None:
            raise AssertionError("a ride was imported")
        matched = match_runs(runs, [{"date": "2026-11-03", "template_id": "aer_5000_r0_x1"}])
        if matched[0]["matched"] is not True or matched[0]["template_id"] != "aer_5000_r0_x1":
            raise AssertionError(matched)
        other = match_runs(runs, [{"date": "2026-11-04", "template_id": "aer_5000_r0_x1"}])
        if other[0]["matched"] is not False:
            raise AssertionError(other)
        compared = planned_vs_actual(
            matched[0],
            current="2:05.0",
            goal="1:59.0",
            start=date(2026, 11, 1),
            goal_day=date(2027, 4, 1),
            on=date(2026, 11, 3),
        )
        if compared["actual"].startswith("—") or compared["status"] not in ("On track", "Ahead", "Behind"):
            raise AssertionError(compared)
        if token["athlete_name"] != "Ada Lovelace":
            raise AssertionError(token)
    finally:
        _restore(saved)


def test_rate_limit_and_disconnect() -> None:
    saved = _use_fake_secrets()
    try:
        gate = RateGate(per_quarter=1, per_day=1)
        gate.take(1_000)
        try:
            gate.take(1_010)
        except StravaLimited as exc:
            if "Strava is busy" not in str(exc):
                raise AssertionError(exc)
        else:
            raise AssertionError("the rate limit was ignored")
        store = reset_memory_strava()
        store.put_token("user-a", {"access_token": "secret-access", "refresh_token": "secret-refresh"}, "server-key")
        store.put_activities("user-a", [{"id": "strava-1", "name": "Easy"}])
        store.put_activities("user-b", [{"id": "strava-2", "name": "Other"}])
        if store.get_token("user-a", "") is not None:
            raise AssertionError("a token was readable without the server key")
        if store.get_activities("user-b")[0]["id"] == "strava-1":
            raise AssertionError("user B saw user A's run")
        called = []

        def post(url, form):
            called.append(form.get("access_token"))
            return {}

        deauthorize("secret-access", post)
        if called != ["secret-access"]:
            raise AssertionError(called)
        store.delete_user("user-a", "server-key")
        if store.get_token("user-a", "server-key") is not None or store.get_activities("user-a"):
            raise AssertionError("disconnect left Strava data behind")
        if not store.get_activities("user-b"):
            raise AssertionError("disconnect removed another user")
        sql = (ROOT / "supabase" / "migrations" / "003_strava.sql").read_text(encoding="utf-8")
        if "grant select, insert, update, delete on table public.strava_activities to authenticated" not in sql:
            raise AssertionError("activities were not granted")
        if "to authenticated" in sql.split("strava_tokens", 1)[1].split("strava_activities", 1)[0]:
            raise AssertionError("tokens were granted to signed-in users")
        if "enable row level security" not in sql or "auth.uid() = user_id" not in sql:
            raise AssertionError("activities are missing a policy")
    finally:
        _restore(saved)


def main() -> None:
    test_oauth_state_and_exchange()
    test_import_parses_runs_and_matches_the_plan()
    test_rate_limit_and_disconnect()
    print("strava ok")


if __name__ == "__main__":
    main()
