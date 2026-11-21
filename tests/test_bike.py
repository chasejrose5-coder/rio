# test_bike.py — an easy run can be a bike. The rules stay in the engine.

"""No network. No production Supabase. A ride is not run distance.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.identity import Principal
from api.main import create_app
from api.strava_flow import _keep_rides
from engines.bike import (
    bike_minutes,
    bike_zones,
    can_swap,
    day_before_race,
    day_kind,
    is_ride,
    suggest_bike,
    zone2_share,
)
from engines.heart_rate import zones_for
from engines.zone_time import zone_report
from ui.cloud_store import MemoryDirectory
from ui.strava import RateGate, import_runs, import_training

ORIGIN = "http://localhost:3000"
INPUTS = {
    "current_time": "2:02.9",
    "start_date": "2026-04-19",
    "goal_time": "1:55.0",
    "goal_date": "2027-03-19",
}


def _client(directory=None) -> TestClient:
    app = create_app(directory=directory, frontend_origin=ORIGIN, load_env=False)
    return TestClient(app, base_url="https://testserver")


def _sign_up(directory: MemoryDirectory, email: str = "ada@example.com") -> TestClient:
    directory.sign_up(email, "correct-horse", "Ada")
    client = _client(directory)
    response = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if response.status_code != 200:
        raise AssertionError(response.text)
    return client


def _principal(opened: dict) -> Principal:
    return Principal(
        kind="hosted",
        email=opened["email"],
        display_name=opened["display_name"],
        user_id=opened["user_id"],
        role=opened["role"],
        token=opened["access_token"],
        refresh=opened["refresh_token"],
        seal=None,
        accounts_path=None,
        issued_at=0,
        sid="sid",
    )


def test_duration_zones_and_the_week_cap_are_fixed_rules() -> None:
    if bike_minutes(40 * 60) != 50:
        raise AssertionError(bike_minutes(40 * 60))
    if bike_minutes(41 * 60) != 55:
        raise AssertionError(bike_minutes(41 * 60))
    running = zones_for(60, 180)["zones"]
    shifted = bike_zones(running)
    if shifted is None or shifted[1]["low_bpm"] != running[1]["low_bpm"] - 6:
        raise AssertionError(shifted)
    if shifted[1]["high_bpm"] != running[1]["high_bpm"] - 6:
        raise AssertionError(shifted)
    easy = {"template_id": "aer_5000_r0_x1", "day_of_week": "Wednesday", "reason_codes": []}
    quality = {"template_id": "se_400_r90_x6", "day_of_week": "Tuesday", "reason_codes": ["phase_4"]}
    long = {"template_id": "aer_12000_r0_x1", "day_of_week": "Saturday", "reason_codes": ["weekly_aerobic_long_run"]}
    race = {"template_id": "rr_800_r0_x1", "day_of_week": "Saturday", "reason_codes": []}
    if day_kind(easy) != "easy" or day_kind(quality) != "quality" or day_kind(long) != "long" or day_kind(race) != "race":
        raise AssertionError((day_kind(easy), day_kind(quality), day_kind(long), day_kind(race)))
    sessions = [{"date": "2026-11-21", **race}]
    if not day_before_race("2026-11-20", sessions) or day_before_race("2026-11-19", sessions):
        raise AssertionError("the day before a race stays a run")
    if not can_swap(easy=True, before_race=False, swaps_already=1, already=False):
        raise AssertionError("the second swap is allowed")
    if can_swap(easy=True, before_race=False, swaps_already=2, already=False):
        raise AssertionError("a third swap is refused")
    if can_swap(easy=False, before_race=False, swaps_already=0, already=False):
        raise AssertionError("a quality day is not a bike")
    if can_swap(easy=True, before_race=True, swaps_already=0, already=False):
        raise AssertionError("the day before a race is not a bike")
    if not can_swap(easy=True, before_race=False, swaps_already=2, already=True):
        raise AssertionError("an existing swap can still be logged")
    if not suggest_bike(["shins"]) or not suggest_bike(["achilles", "knee"]):
        raise AssertionError("rebuilding shins or Achilles suggests the bike")
    if not suggest_bike(["soleus"]) or not suggest_bike(["plantar-fascia", "ankle-sprain", "peroneal", "bone-stress"]):
        raise AssertionError("soleus and the feet suggest the bike")
    if suggest_bike(["knee"]) or suggest_bike("shins"):
        raise AssertionError("other areas stay a run first")
    if zone2_share(40, 50) != 80 or zone2_share(0, 0) is not None:
        raise AssertionError(zone2_share(40, 50))
    if is_ride({"sport_type": "Ride"}) and is_ride({"type": "VirtualRide"}) and not is_ride({"sport_type": "Run"}):
        return
    raise AssertionError("Ride and VirtualRide are the only rides")


def test_migration_020_scopes_bike_rows_to_auth_uid() -> None:
    names = sorted(path.name for path in (ROOT / "supabase" / "migrations").glob("*.sql"))
    numbers = [int(name.split("_", 1)[0]) for name in names]
    if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
        raise AssertionError(names)
    if 20 not in numbers:
        raise AssertionError(names)
    sql = (ROOT / "supabase" / "migrations" / "020_bike_sessions.sql").read_text(encoding="utf-8").lower()
    if "information_schema.statistics" in sql:
        raise AssertionError("verification must not use information_schema.statistics")
    if "create table if not exists public.bike_sessions" not in sql:
        raise AssertionError(sql)
    if "enable row level security" not in sql or "revoke all on table public.bike_sessions from anon" not in sql:
        raise AssertionError(sql)
    if sql.count("auth.uid() = user_id") < 2:
        raise AssertionError("bike sessions need using and with check on auth.uid()")
    if "grant select, insert, update, delete on table public.bike_sessions to authenticated" not in sql:
        raise AssertionError(sql)
    readme = (ROOT / "supabase" / "migrations" / "README.md").read_text(encoding="utf-8")
    if "020_bike_sessions.sql" not in readme or "Run it after 019" not in readme:
        raise AssertionError("the migration note is missing")
    for path in (
        ROOT / "engines" / "bike.py",
        ROOT / "web" / "components" / "BikeSwap.tsx",
        ROOT / "api" / "bike_routes.py",
        ROOT / "api" / "bike_store.py",
    ):
        text = path.read_text(encoding="utf-8").lower()
        if "cadence" in text or "rpm" in text:
            raise AssertionError(path.name)


def test_a_ride_stays_out_of_the_run_list_and_keeps_its_heart_rate_stream() -> None:
    listed = [
        {
            "id": 5,
            "name": "Easy",
            "sport_type": "Run",
            "start_date_local": "2026-11-11T08:00:00",
            "distance": 5000,
            "moving_time": 1500,
            "elapsed_time": 1600,
            "average_heartrate": 140,
        },
        {
            "id": 6,
            "name": "Spin",
            "sport_type": "VirtualRide",
            "start_date_local": "2026-11-11T18:00:00",
            "distance": 12000,
            "moving_time": 3000,
            "elapsed_time": 3100,
            "average_heartrate": 130,
        },
    ]
    stream = {"time": {"data": [0, 30, 60]}, "heartrate": {"data": [130, 130, 130]}}

    def get(url, query, access):
        if str(url).endswith("/streams"):
            return stream
        if str(url).endswith("/activities"):
            return listed
        return listed[0]

    def post(url, form):
        return {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_at": 1_700_000_000 + 10_000,
            "athlete": {"firstname": "Ada", "lastname": "R"},
        }

    token = {"access_token": "a", "refresh_token": "r", "expires_at": 1_700_000_000 + 10_000, "athlete_name": "Ada"}
    fresh, runs, rides = import_training(
        token,
        now=1_700_000_000,
        last_sync=None,
        get=get,
        post=post,
        gate=RateGate(),
    )
    if len(runs) != 1 or runs[0]["sport_type"] != "Run":
        raise AssertionError(runs)
    if len(rides) != 1 or rides[0]["sport_type"] != "VirtualRide" or rides[0]["hr_stream"]["hr"] != [130, 130, 130]:
        raise AssertionError(rides)
    if fresh.get("detail_skips") not in (0, None) and not isinstance(fresh.get("detail_skips"), int):
        raise AssertionError(fresh)
    again, only_runs = import_runs(
        token,
        now=1_700_000_000,
        last_sync=None,
        get=get,
        post=post,
        gate=RateGate(),
    )
    if len(only_runs) != 1 or any(row.get("sport_type") == "VirtualRide" for row in only_runs):
        raise AssertionError(only_runs)
    if again.get("access_token") != fresh.get("access_token"):
        raise AssertionError("the run import used a different token")
    bands = bike_zones(zones_for(60, 180)["zones"])
    report = zone_report(rides[0]["hr_stream"], bands, None)
    if report is None or report["zones"][1]["seconds"] != 60:
        raise AssertionError(report)


def test_easy_day_swap_log_and_a_third_day_is_refused() -> None:
    directory = MemoryDirectory()
    ada = _sign_up(directory)
    opened = ada.post("/seasons", json=INPUTS)
    if opened.status_code != 200:
        raise AssertionError(opened.text)
    plan = ada.get("/plan")
    if plan.status_code != 200:
        raise AssertionError(plan.text)
    sessions = [row for row in plan.json()["sessions"] if isinstance(row, dict)]
    easy = [
        row
        for row in sessions
        if day_kind(row) == "easy" and not day_before_race(str(row.get("date") or ""), sessions)
    ]
    by_week: dict[str, list[str]] = {}
    for row in easy:
        day = date.fromisoformat(str(row["date"])[:10])
        sunday = day.toordinal() - ((day.weekday() + 1) % 7)
        by_week.setdefault(str(sunday), []).append(day.isoformat())
    week = next((days for days in by_week.values() if len(days) >= 3), None)
    if week is None:
        raise AssertionError("the plan has no week with three easy days")
    first, second, third = week[:3]
    heart = ada.put("/heart-rate", json={"resting_hr": 60, "max_hr": 180})
    if heart.status_code != 200:
        raise AssertionError(heart.text)
    offer = ada.get(f"/bike?day={first}")
    if offer.status_code != 200 or offer.json()["offer"] is not True or offer.json()["suggest_first"] is not False:
        raise AssertionError(offer.text)
    if offer.json()["zone2"]["sentence"] != "Easy bike is zone 2, conversational.":
        raise AssertionError(offer.text)
    marked = ada.post("/injury/areas", json={"area_id": "shins"})
    if marked.status_code != 200:
        raise AssertionError(marked.text)
    suggested = ada.get(f"/bike?day={first}")
    if suggested.json()["suggest_first"] is not True:
        raise AssertionError(suggested.text)
    swapped = ada.post("/bike", json={"date": first, "swap": True})
    if swapped.status_code != 200 or swapped.json()["swapped"] is not True:
        raise AssertionError(swapped.text)
    logged = ada.post("/bike", json={"date": first, "minutes": 50, "distance_m": 12000, "avg_hr": 130})
    if logged.status_code != 200 or logged.json()["log"]["minutes"] != 50:
        raise AssertionError(logged.text)
    quality = next(row for row in sessions if day_kind(row) == "quality")
    refused_day = ada.post("/bike", json={"date": quality["date"], "swap": True})
    if refused_day.status_code != 400:
        raise AssertionError(refused_day.text)
    race = next(row for row in sessions if day_kind(row) == "race")
    race_day = date.fromisoformat(str(race["date"])[:10])
    eve = date.fromordinal(race_day.toordinal() - 1)
    before = ada.get(f"/bike?day={eve.isoformat()}")
    if before.status_code != 200 or before.json()["offer"] is not False:
        raise AssertionError(before.text)
    second_swap = ada.post("/bike", json={"date": second, "minutes": 40})
    if second_swap.status_code != 200 or second_swap.json()["swaps_used"] != 2:
        raise AssertionError(second_swap.text)
    blocked = ada.post("/bike", json={"date": third, "swap": True})
    if blocked.status_code != 400:
        raise AssertionError(blocked.text)
    logged_day = date.fromisoformat(first)
    start = date.fromordinal(logged_day.toordinal() - ((logged_day.weekday() + 1) % 7))
    end = date.fromordinal(start.toordinal() + 6)
    summary = ada.get(f"/bike/week?start={start.isoformat()}&end={end.isoformat()}")
    body = summary.json()
    if summary.status_code != 200 or first not in body["dates"] or body["distance_m"] != 12000:
        raise AssertionError(summary.text)
    if body["minutes"] != 90:
        raise AssertionError(body)
    bob = _sign_up(directory, "bob@example.com")
    other = bob.get(f"/bike?day={first}")
    if other.status_code != 200 or other.json()["swapped"] is not False or other.json()["log"] is not None:
        raise AssertionError(other.text)


def test_a_strava_ride_fills_an_easy_day_and_a_hand_log_wins() -> None:
    directory = MemoryDirectory()
    opened = directory.sign_up("ada@example.com", "correct-horse", "Ada")
    who = _principal(opened)
    directory.api_heart_rate = {
        opened["user_id"]: {"no_monitor": False, "resting_hr": "60", "max_hr": "180", "zones": None}
    }
    day = "2026-11-11"
    season = SimpleNamespace(
        plan={
            "sessions": [
                {"date": day, "template_id": "aer_5000_r0_x1", "day_of_week": "Wednesday", "reason_codes": []},
                {"date": "2026-11-12", "template_id": "se_400_r90_x6", "day_of_week": "Thursday", "reason_codes": []},
            ]
        },
        activities=[],
    )
    rides = [
        {
            "id": "strava-9",
            "date": day,
            "start_local": "2026-11-11T07:00:00",
            "moving_seconds": 3000,
            "distance_m": 15000,
            "average_hr": 128,
            "hr_stream": {"time": [0, 30, 60], "hr": [130, 130, 130]},
        },
        {
            "id": "strava-8",
            "date": "2026-11-12",
            "start_local": "2026-11-12T07:00:00",
            "moving_seconds": 1800,
            "distance_m": 8000,
            "average_hr": 128,
        },
    ]
    _keep_rides(None, who, directory, date(2026, 11, 11), season, rides)
    from api.bike_store import load_rows, save_log

    rows = load_rows(who, directory)
    if len(rows) != 1 or rows[0]["date"] != day or rows[0]["strava_id"] != "strava-9":
        raise AssertionError(rows)
    if rows[0]["zones"] != [0, 60, 0, 0, 0]:
        raise AssertionError(rows[0]["zones"])
    if season.activities != []:
        raise AssertionError("a ride was stored as a run")
    save_log(
        who,
        directory,
        date(2026, 11, 18),
        easy=True,
        before_race=False,
        minutes=45,
        distance_m=10000,
        avg_hr=120,
    )
    later = {
        "id": "strava-10",
        "date": "2026-11-18",
        "start_local": "2026-11-18T07:00:00",
        "moving_seconds": 4000,
        "distance_m": 20000,
        "average_hr": 140,
    }
    season.plan["sessions"].append(
        {"date": "2026-11-18", "template_id": "aer_5000_r0_x1", "day_of_week": "Wednesday", "reason_codes": []}
    )
    _keep_rides(None, who, directory, date(2026, 11, 18), season, [later])
    kept = load_rows(who, directory)
    hand = next(row for row in kept if row["date"] == "2026-11-18")
    if hand["minutes"] != 45 or hand["strava_id"] is not None:
        raise AssertionError(hand)


def test_bike_zone_seconds_join_a_week_with_no_run_stream() -> None:
    from api.screen_routes import _add_bike_zones

    def rows(who, directory):
        return [{"date": "2026-11-10", "zones": [0, 60, 0, 0, 0]}]

    import api.bike_store as bike_store

    original = bike_store.load_rows
    bike_store.load_rows = rows
    try:
        season = SimpleNamespace(plan={"start_date": "2026-11-08", "season_length_weeks": 12})
        found = _add_bike_zones({}, None, None, season)
    finally:
        bike_store.load_rows = original
    zone = next(row for row in found["1"] if row["zone"] == 2)
    if zone["seconds"] != 60:
        raise AssertionError(found)
