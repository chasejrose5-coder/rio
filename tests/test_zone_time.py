# test_zone_time.py — time in zone from a heart-rate stream. No network.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.heart_rate import zones_for
from engines.zone_time import parse_hr_stream, zone_report
from ui.strava import import_runs
from ui.strava_store import MemoryStrava


def _zones() -> list:
    return zones_for(60, 180)["zones"]


def test_time_in_zone_ignores_drift_and_warns_when_the_run_is_above_the_target() -> None:
    # Zone 2 for 60/180 is 132–144. 160 is above it. 100 is below zone 1.
    times = list(range(0, 301, 1))
    rates = [140] * 60 + [160] * 180 + [100] * 61
    report = zone_report({"time": times, "hr": rates}, _zones(), 2)
    if report is None:
        raise AssertionError("stream")
    by_zone = {row["zone"]: row["seconds"] for row in report["zones"]}
    if by_zone[2] != 60 or by_zone[4] < 170:
        raise AssertionError(by_zone)
    if "slow down or stop" not in report["warning"] or "Zone 2" not in report["warning"]:
        raise AssertionError(report["warning"])
    inside = zone_report({"time": times, "hr": [138] * len(times)}, _zones(), 2)
    if inside is None or inside["warning"]:
        raise AssertionError(inside)
    if zone_report(None, _zones(), 2) is not None:
        raise AssertionError("missing stream")
    if zone_report({"time": times, "hr": rates}, [], 2) is not None:
        raise AssertionError("missing zones")


def test_a_stream_payload_is_kept_and_a_blank_one_is_not() -> None:
    parsed = parse_hr_stream(
        {"heartrate": {"data": [120, 130, 140]}, "time": {"data": [0, 1, 2]}}
    )
    if parsed != {"time": [0, 1, 2], "hr": [120, 130, 140]}:
        raise AssertionError(parsed)
    if parse_hr_stream({"heartrate": {"data": []}, "time": {"data": []}}) is not None:
        raise AssertionError("empty")
    if parse_hr_stream([{"type": "heartrate"}]) is not None:
        raise AssertionError("list shape is not used")


def test_import_keeps_a_heartrate_stream_and_the_memory_store_scopes_it() -> None:
    def get(url: str, query: dict, _token: str):
        if url.endswith("/streams"):
            return {
                "heartrate": {"data": [140, 142, 141, 143]},
                "time": {"data": [0, 10, 20, 30]},
            }
        if "/activities/" in url:
            return {
                "id": 42,
                "name": "Easy",
                "sport_type": "Run",
                "start_date_local": "2026-11-03T08:00:00",
                "distance": 5000.0,
                "moving_time": 1500,
                "elapsed_time": 1560,
                "average_heartrate": 141,
                "laps": [{"distance": 1000, "moving_time": 300, "elapsed_time": 300}],
            }
        return [
            {
                "id": 42,
                "name": "Easy",
                "sport_type": "Run",
                "start_date_local": "2026-11-03T08:00:00",
                "distance": 5000.0,
                "moving_time": 1500,
                "elapsed_time": 1560,
                "average_heartrate": 141,
            }
        ]

    def post(_url: str, _form: dict):
        return {
            "access_token": "fake-access",
            "refresh_token": "fake-refresh",
            "expires_at": 2_000_000_000,
            "athlete": {"id": 7, "firstname": "Ada", "lastname": "Run"},
        }

    from ui.strava import RateGate

    _token, runs = import_runs(
        {"access_token": "fake-access", "refresh_token": "fake-refresh", "expires_at": 2_000_000_000},
        now=1_700_000_000,
        last_sync=None,
        get=get,
        post=post,
        gate=RateGate(),
    )
    if len(runs) != 1 or runs[0].get("hr_stream", {}).get("hr") != [140, 142, 141, 143]:
        raise AssertionError(runs)
    store = MemoryStrava()
    store.put_streams("ada", runs)
    store.put_streams("bea", [{"id": "strava-9", "hr_stream": {"time": [0, 1], "hr": [100, 101]}}])
    ada = store.get_streams("ada")
    if list(ada) != ["strava-42"] or store.get_streams("bea")["strava-9"]["hr"][0] != 100:
        raise AssertionError((ada, store.get_streams("bea")))
    sql = (ROOT / "supabase" / "migrations" / "016_run_hr_streams.sql").read_text(encoding="utf-8").lower()
    if "information_schema.statistics" in sql or "activity:read_all" not in (ROOT / "supabase" / "migrations" / "README.md").read_text(encoding="utf-8"):
        raise AssertionError("migration note")
    if sql.count("auth.uid() = user_id") < 2:
        raise AssertionError("rls")
    scope = (ROOT / "ui" / "strava.py").read_text(encoding="utf-8")
    if 'SCOPE = "activity:read_all"' not in scope:
        raise AssertionError("scope change")
