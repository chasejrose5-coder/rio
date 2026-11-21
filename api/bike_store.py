# bike_store.py — easy-day bike swaps. The plan text stays in the app.

"""One row per plan day. Hosted accounts use the signed-in key, so row level
security applies. Local accounts use a sealed record. Memory keeps a bag.

A missing migration is an empty set on read, so Plan still opens.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from api.errors import ApiError
from api.identity import Principal
from engines.bike import WEEK_CAP, can_swap
from ui.accounts import AccountError, last_key, read_record, write_record
from ui.cloud_store import CloudAuthError, MemoryDirectory

BIKE_RECORD = "rio.api.bike.v1"


def _blank() -> dict:
    return {"sessions": []}


def _iso(value: object) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and len(value) >= 10:
        text = value[:10]
        try:
            date.fromisoformat(text)
        except ValueError:
            return ""
        return text
    return ""


def _int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value == int(value):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _zones(value: object) -> list[int] | None:
    if not isinstance(value, list) or len(value) != 5:
        return None
    found = []
    for item in value:
        number = _int(item)
        if number is None or number < 0:
            return None
        found.append(number)
    return found


def _row(raw: dict) -> dict | None:
    day = _iso(raw.get("date") or raw.get("done_on"))
    if not day:
        return None
    return {
        "date": day,
        "minutes": _int(raw.get("minutes")),
        "distance_m": _int(raw.get("distance_m")),
        "avg_hr": _int(raw.get("avg_hr")),
        "strava_id": raw.get("strava_id") if isinstance(raw.get("strava_id"), str) and raw.get("strava_id") else None,
        "zones": _zones(raw.get("zones") if raw.get("zones") is not None else raw.get("zone_seconds")),
    }


def _public(rows: list[dict]) -> list[dict]:
    found = []
    seen = set()
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        row = _row(raw)
        if row is None or row["date"] in seen:
            continue
        seen.add(row["date"])
        found.append(row)
    found.sort(key=lambda item: item["date"])
    return found


def _logged(row: dict) -> bool:
    return (isinstance(row.get("minutes"), int) and row["minutes"] > 0) or bool(row.get("strava_id"))


def week_bounds(day: date) -> tuple[date, date]:
    sunday = day - timedelta(days=(day.weekday() + 1) % 7)
    return sunday, sunday + timedelta(days=6)


def swaps_in_week(rows: list[dict], day: date, *, skip: str | None = None) -> int:
    start, end = week_bounds(day)
    count = 0
    for row in rows:
        if row["date"] == skip:
            continue
        current = date.fromisoformat(row["date"])
        if start <= current <= end:
            count += 1
    return count


def _memory_bag(directory) -> dict:
    bag = getattr(directory, "api_bike", None)
    if not isinstance(bag, dict):
        bag = {}
        setattr(directory, "api_bike", bag)
    return bag


def _memory_rows(directory, token: str) -> list[dict]:
    user_id = directory.user_id(token)
    bag = _memory_bag(directory)
    found = bag.get(user_id)
    if not isinstance(found, dict):
        found = _blank()
        bag[user_id] = found
    return _public(found.get("sessions") or [])


def _save_memory(directory, token: str, rows: list[dict]) -> None:
    _memory_bag(directory)[directory.user_id(token)] = {"sessions": [dict(row) for row in rows]}


def _local_rows(principal: Principal) -> list[dict]:
    raw = read_record(principal.accounts_path, principal.email, principal.seal, BIKE_RECORD)
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, dict):
        return []
    return _public(parsed.get("sessions") or [])


def _save_local(principal: Principal, rows: list[dict]) -> None:
    body = json.dumps({"sessions": rows}, separators=(",", ":"), sort_keys=True)
    previous = last_key(principal.accounts_path, principal.email, principal.seal)
    write_record(principal.accounts_path, principal.email, principal.seal, BIKE_RECORD, body)
    if isinstance(previous, str) and previous and previous != BIKE_RECORD:
        kept = read_record(principal.accounts_path, principal.email, principal.seal, previous)
        if isinstance(kept, str) and kept:
            write_record(principal.accounts_path, principal.email, principal.seal, previous, kept)


def _hosted(directory) -> bool:
    return directory is not None and not isinstance(directory, MemoryDirectory) and hasattr(directory, "_user_client")


def _rows_of(result) -> list:
    data = getattr(result, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def _hosted_rows(directory, token: str) -> list[dict]:
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        loaded = _rows_of(
            client.table("bike_sessions")
            .select("done_on,minutes,distance_m,avg_hr,strava_id,zone_seconds")
            .eq("user_id", user_id)
            .execute()
        )
    except CloudAuthError:
        raise
    except Exception as exc:
        raise ApiError(503, "Bike swaps could not be loaded. Run migration 020.") from exc
    return _public(loaded)


def _save_hosted(directory, token: str, row: dict | None, day: str) -> None:
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        table = client.table("bike_sessions")
        if row is None:
            table.delete().eq("user_id", user_id).eq("done_on", day).execute()
            return
        table.upsert(
            {
                "user_id": user_id,
                "done_on": day,
                "minutes": row.get("minutes"),
                "distance_m": row.get("distance_m"),
                "avg_hr": row.get("avg_hr"),
                "strava_id": row.get("strava_id"),
                "zone_seconds": row.get("zones"),
            },
            on_conflict="user_id,done_on",
        ).execute()
    except CloudAuthError:
        raise
    except Exception as exc:
        raise ApiError(503, "Bike swaps could not be saved. Run migration 020.") from exc


def load_rows(principal: Principal, directory) -> list[dict]:
    try:
        if principal.kind == "local":
            return _local_rows(principal)
        if not isinstance(principal.token, str) or not principal.token:
            raise ApiError(401, "Sign in again.")
        if _hosted(directory):
            return _hosted_rows(directory, principal.token)
        return _memory_rows(directory, principal.token)
    except CloudAuthError as exc:
        raise ApiError(401, str(exc)) from exc
    except AccountError as exc:
        raise ApiError(400, str(exc)) from exc
    except ApiError:
        raise


def _write(principal: Principal, directory, rows: list[dict], changed: dict | None, day: str) -> list[dict]:
    try:
        if principal.kind == "local":
            _save_local(principal, rows)
            return rows
        if not isinstance(principal.token, str) or not principal.token:
            raise ApiError(401, "Sign in again.")
        if _hosted(directory):
            _save_hosted(directory, principal.token, changed, day)
            return _hosted_rows(directory, principal.token)
        _save_memory(directory, principal.token, rows)
        return rows
    except CloudAuthError as exc:
        raise ApiError(401, str(exc)) from exc
    except AccountError as exc:
        raise ApiError(400, str(exc)) from exc


def _find(rows: list[dict], day: str) -> dict | None:
    for row in rows:
        if row["date"] == day:
            return row
    return None


def _replace(rows: list[dict], row: dict) -> list[dict]:
    kept = [item for item in rows if item["date"] != row["date"]]
    kept.append(row)
    kept.sort(key=lambda item: item["date"])
    return kept


def ensure_swap(principal: Principal, directory, day: date, *, easy: bool, before_race: bool) -> list[dict]:
    rows = load_rows(principal, directory)
    iso = day.isoformat()
    already = _find(rows, iso) is not None
    used = swaps_in_week(rows, day, skip=iso)
    if not can_swap(easy=easy, before_race=before_race, swaps_already=used, already=already):
        raise ApiError(400, "That easy day cannot be a bike.")
    if already:
        return rows
    row = {"date": iso, "minutes": None, "distance_m": None, "avg_hr": None, "strava_id": None, "zones": None}
    return _write(principal, directory, _replace(rows, row), row, iso)


def clear_swap(principal: Principal, directory, day: date) -> list[dict]:
    rows = load_rows(principal, directory)
    iso = day.isoformat()
    kept = [row for row in rows if row["date"] != iso]
    return _write(principal, directory, kept, None, iso)


def _check_log(minutes: object, distance_m: object, avg_hr: object) -> tuple[int, int | None, int | None]:
    logged = _int(minutes)
    if logged is None or logged <= 0 or logged > 600:
        raise ApiError(400, "Enter the ride in minutes.")
    distance = _int(distance_m) if distance_m is not None else None
    if distance_m is not None and (distance is None or distance < 0 or distance > 500_000):
        raise ApiError(400, "Enter the ride distance.")
    heart = _int(avg_hr) if avg_hr is not None else None
    if avg_hr is not None and (heart is None or heart < 30 or heart > 230):
        raise ApiError(400, "Enter an average heart rate between 30 and 230.")
    return logged, distance, heart


def save_log(
    principal: Principal,
    directory,
    day: date,
    *,
    easy: bool,
    before_race: bool,
    minutes: object,
    distance_m: object,
    avg_hr: object,
) -> list[dict]:
    logged, distance, heart = _check_log(minutes, distance_m, avg_hr)
    rows = ensure_swap(principal, directory, day, easy=easy, before_race=before_race)
    iso = day.isoformat()
    current = _find(rows, iso) or {}
    row = {
        "date": iso,
        "minutes": logged,
        "distance_m": distance,
        "avg_hr": heart,
        "strava_id": current.get("strava_id"),
        "zones": current.get("zones"),
    }
    return _write(principal, directory, _replace(rows, row), row, iso)


def save_ride(
    principal: Principal,
    directory,
    day: date,
    *,
    easy: bool,
    before_race: bool,
    minutes: int,
    distance_m: int | None,
    avg_hr: int | None,
    strava_id: str,
    zones: list[int] | None,
) -> list[dict]:
    """A Strava ride fills an empty swap. A hand log stays."""
    rows = load_rows(principal, directory)
    iso = day.isoformat()
    current = _find(rows, iso)
    if current is not None and current.get("strava_id") not in (None, strava_id) and _logged(current):
        return rows
    if current is not None and current.get("strava_id") is None and isinstance(current.get("minutes"), int):
        return rows
    already = current is not None
    used = swaps_in_week(rows, day, skip=iso)
    if not can_swap(easy=easy, before_race=before_race, swaps_already=used, already=already):
        return rows
    row = {
        "date": iso,
        "minutes": minutes,
        "distance_m": distance_m,
        "avg_hr": avg_hr,
        "strava_id": strava_id,
        "zones": zones,
    }
    return _write(principal, directory, _replace(rows, row), row, iso)


def week_summary(rows: list[dict], start: date, end: date) -> dict:
    dates = []
    minutes = 0
    distance = 0
    zone2 = 0
    total = 0
    for row in rows:
        current = date.fromisoformat(row["date"])
        if current < start or current > end or not _logged(row):
            continue
        dates.append(row["date"])
        if isinstance(row.get("minutes"), int):
            minutes += row["minutes"]
        if isinstance(row.get("distance_m"), int):
            distance += row["distance_m"]
        zones = row.get("zones")
        if isinstance(zones, list) and len(zones) == 5:
            zone2 += zones[1]
            total += sum(zones)
    return {
        "tracked": True,
        "dates": dates,
        "minutes": minutes,
        "distance_m": distance,
        "zone2_seconds": zone2,
        "zone_seconds": total,
    }
