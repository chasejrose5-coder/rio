# stretch_store.py — Done marks and sore spots. The exercise text stays in the app.

"""Two tables, scoped to the signed-in athlete.

Hosted accounts use the signed-in Supabase key, so row level security applies.
The service role is not used. Local accounts use a sealed record that is not
a plan key, and the plan key is written back so it stays last. The in-memory
directory keeps a bag per user id.

Today is the date the caller already resolved in the Settings time zone.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from api.errors import ApiError
from api.identity import Principal
from ui.accounts import AccountError, last_key, read_record, write_record
from ui.cloud_store import CloudAuthError, MemoryDirectory

# Not a plan key. Past seasons and the plan list leave it alone.
STRETCH_RECORD = "rio.api.stretch.v1"

REGIONS = frozenset(
    {
        "feet",
        "calves",
        "shins",
        "hamstrings",
        "quads",
        "hip-flexors",
        "glutes",
        "adductors",
        "it-band",
        "lower-back",
        "abs",
        "upper-back",
        "shoulders",
        "neck",
    }
)
ROUTINES = frozenset(
    {
        "pre-run",
        "q-warm-fast",
        "q-warm-hips",
        "post-run",
        "q-cool-hips",
        "q-cool-feet",
        "long-warm-easy",
        "long-warm-legs",
        "long-warm-ankles",
        "long-recovery",
        "long-cool-hips",
        "long-cool-feet",
        "easy-warm-flow",
        "easy-warm-feet",
        "easy-warm-hips",
        "hips",
        "easy-cool-yoga",
        "easy-cool-legs",
        "rest-warm-breath",
        "rest-warm-spine",
        "rest-warm-hips",
        "yoga",
        "rest-cool-fold",
        "rest-cool-back",
        "primer",
        "race-warm-strides",
        "race-warm-quick",
        "race-loose-ankles",
        "race-loose-hips",
        "race-loose-arms",
    }
)
SEVERITIES = frozenset({"mild", "moderate", "sharp"})


def _blank() -> dict:
    return {"completions": [], "spots": []}


def _copy(state: dict) -> dict:
    return {
        "completions": [dict(row) for row in state.get("completions") or [] if isinstance(row, dict)],
        "spots": [dict(row) for row in state.get("spots") or [] if isinstance(row, dict)],
    }


def _iso(value: object) -> str:
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


def _bool(value: object) -> bool:
    return value is True or value == "true"


def _public(today: date, state: dict) -> dict:
    completions = []
    for row in state.get("completions") or []:
        if not isinstance(row, dict):
            continue
        done = _iso(row.get("date") or row.get("done_on"))
        routine = row.get("routine_id")
        if done and isinstance(routine, str) and routine in ROUTINES:
            completions.append({"date": done, "routine_id": routine})
    completions.sort(key=lambda row: (row["date"], row["routine_id"]))
    spots = []
    for row in state.get("spots") or []:
        if not isinstance(row, dict):
            continue
        region = row.get("region")
        severity = row.get("severity")
        started = _iso(row.get("started_on"))
        check = _iso(row.get("check_in_on"))
        if not isinstance(region, str) or region not in REGIONS:
            continue
        if not isinstance(severity, str) or severity not in SEVERITIES or not started or not check:
            continue
        spots.append(
            {
                "region": region,
                "severity": severity,
                "started_on": started,
                "check_in_on": check,
                "cleared": _bool(row.get("cleared")),
            }
        )
    spots.sort(key=lambda row: row["region"])
    return {"today": today.isoformat(), "completions": completions, "spots": spots}


def _memory_bag(directory) -> dict:
    bag = getattr(directory, "api_stretch", None)
    if not isinstance(bag, dict):
        bag = {}
        setattr(directory, "api_stretch", bag)
    return bag


def _memory_state(directory, token: str) -> dict:
    user_id = directory.user_id(token)
    bag = _memory_bag(directory)
    found = bag.get(user_id)
    if not isinstance(found, dict):
        found = _blank()
        bag[user_id] = found
    return found


def _save_memory(directory, token: str, state: dict) -> None:
    user_id = directory.user_id(token)
    _memory_bag(directory)[user_id] = _copy(state)


def _local_state(principal: Principal) -> dict:
    raw = read_record(principal.accounts_path, principal.email, principal.seal, STRETCH_RECORD)
    if not isinstance(raw, str) or not raw.strip():
        return _blank()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return _blank()
    if not isinstance(parsed, dict):
        return _blank()
    return parsed


def _save_local(principal: Principal, state: dict) -> None:
    body = json.dumps(_copy(state), separators=(",", ":"), sort_keys=True)
    previous = last_key(principal.accounts_path, principal.email, principal.seal)
    write_record(principal.accounts_path, principal.email, principal.seal, STRETCH_RECORD, body)
    if isinstance(previous, str) and previous and previous != STRETCH_RECORD:
        kept = read_record(principal.accounts_path, principal.email, principal.seal, previous)
        if isinstance(kept, str) and kept:
            write_record(principal.accounts_path, principal.email, principal.seal, previous, kept)


def _rows(result) -> list:
    data = getattr(result, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def _hosted_state(directory, token: str) -> dict:
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        completions = _rows(
            client.table("stretch_completions").select("done_on,routine_id").eq("user_id", user_id).execute()
        )
        spots = _rows(
            client.table("sore_spots")
            .select("region,severity,started_on,check_in_on,cleared")
            .eq("user_id", user_id)
            .execute()
        )
    except CloudAuthError:
        raise
    except Exception as exc:
        raise ApiError(503, "Stretching could not be loaded. Run migration 014.") from exc
    return {
        "completions": [
            {"date": _iso(row.get("done_on")), "routine_id": row.get("routine_id")} for row in completions
        ],
        "spots": spots,
    }


def _save_hosted_completion(directory, token: str, today: date, routine_id: str, present: bool) -> None:
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        query = (
            client.table("stretch_completions")
            .delete()
            .eq("user_id", user_id)
            .eq("done_on", today.isoformat())
            .eq("routine_id", routine_id)
        )
        if present:
            query.execute()
            return
        client.table("stretch_completions").insert(
            {"user_id": user_id, "done_on": today.isoformat(), "routine_id": routine_id}
        ).execute()
    except CloudAuthError:
        raise
    except Exception as exc:
        raise ApiError(503, "Stretching could not be saved. Run migration 014.") from exc


def _save_hosted_spot(directory, token: str, spot: dict) -> None:
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        row = {"user_id": user_id, **spot}
        client.table("sore_spots").upsert(row, on_conflict="user_id,region").execute()
    except CloudAuthError:
        raise
    except Exception as exc:
        raise ApiError(503, "Stretching could not be saved. Run migration 014.") from exc


def _hosted(directory) -> bool:
    return directory is not None and not isinstance(directory, MemoryDirectory) and hasattr(directory, "_user_client")


def load_state(principal: Principal, directory, today: date) -> dict:
    if principal.kind == "local":
        return _public(today, _local_state(principal))
    if not isinstance(principal.token, str) or not principal.token:
        raise ApiError(401, "Sign in again.")
    if _hosted(directory):
        return _public(today, _hosted_state(directory, principal.token))
    return _public(today, _memory_state(directory, principal.token))


def _mutate(principal: Principal, directory, today: date, change) -> dict:
    try:
        if principal.kind == "local":
            state = _local_state(principal)
            change(state)
            _save_local(principal, state)
            return _public(today, state)
        if not isinstance(principal.token, str) or not principal.token:
            raise ApiError(401, "Sign in again.")
        if _hosted(directory):
            change(None)
            return load_state(principal, directory, today)
        state = _memory_state(directory, principal.token)
        change(state)
        _save_memory(directory, principal.token, state)
        return _public(today, state)
    except CloudAuthError as exc:
        raise ApiError(401, str(exc)) from exc
    except AccountError as exc:
        raise ApiError(400, str(exc)) from exc


def _find_completion(state: dict, today: str, routine_id: str) -> dict | None:
    for row in state.get("completions") or []:
        if isinstance(row, dict) and row.get("date") == today and row.get("routine_id") == routine_id:
            return row
    return None


def _find_spot(state: dict, region: str) -> dict | None:
    for row in state.get("spots") or []:
        if isinstance(row, dict) and row.get("region") == region:
            return row
    return None


def toggle_completion(principal: Principal, directory, today: date, routine_id: object) -> dict:
    if not isinstance(routine_id, str) or routine_id not in ROUTINES:
        raise ApiError(400, "That routine is not in the library.")
    iso = today.isoformat()

    def change(state):
        if state is None:
            current = _hosted_state(directory, principal.token)
            present = _find_completion(current, iso, routine_id) is not None
            _save_hosted_completion(directory, principal.token, today, routine_id, present)
            return
        rows = [row for row in state.get("completions") or [] if isinstance(row, dict)]
        if _find_completion({"completions": rows}, iso, routine_id):
            state["completions"] = [
                row for row in rows if not (row.get("date") == iso and row.get("routine_id") == routine_id)
            ]
        else:
            rows.append({"date": iso, "routine_id": routine_id})
            state["completions"] = rows

    return _mutate(principal, directory, today, change)


def _window(today: date) -> tuple[str, str]:
    return today.isoformat(), (today + timedelta(days=7)).isoformat()


def save_spot(principal: Principal, directory, today: date, region: object, severity: object) -> dict:
    if not isinstance(region, str) or region not in REGIONS:
        raise ApiError(400, "That area is not on the body map.")
    if not isinstance(severity, str) or severity not in SEVERITIES:
        raise ApiError(400, "Choose mild, moderate, or sharp.")
    started, check = _window(today)
    spot = {
        "region": region,
        "severity": severity,
        "started_on": started,
        "check_in_on": check,
        "cleared": False,
    }

    def change(state):
        if state is None:
            _save_hosted_spot(directory, principal.token, spot)
            return
        rows = [row for row in state.get("spots") or [] if isinstance(row, dict) and row.get("region") != region]
        rows.append(dict(spot))
        state["spots"] = rows

    return _mutate(principal, directory, today, change)


def check_in_spot(principal: Principal, directory, today: date, region: object, still: object) -> dict:
    if not isinstance(region, str) or region not in REGIONS:
        raise ApiError(400, "That area is not on the body map.")
    if not isinstance(still, bool):
        raise ApiError(400, "Say whether it is still bothering you.")
    started, check = _window(today)

    def change(state):
        source = _hosted_state(directory, principal.token) if state is None else state
        found = _find_spot(source, region)
        if found is None or _bool(found.get("cleared")):
            raise ApiError(404, "That sore spot is not active.")
        if still:
            updated = {
                "region": region,
                "severity": found.get("severity"),
                "started_on": started,
                "check_in_on": check,
                "cleared": False,
            }
        else:
            updated = {
                "region": region,
                "severity": found.get("severity"),
                "started_on": _iso(found.get("started_on")) or started,
                "check_in_on": _iso(found.get("check_in_on")) or check,
                "cleared": True,
            }
        if state is None:
            _save_hosted_spot(directory, principal.token, updated)
            return
        rows = [row for row in state.get("spots") or [] if isinstance(row, dict) and row.get("region") != region]
        rows.append(updated)
        state["spots"] = rows

    return _mutate(principal, directory, today, change)


def clear_spot(principal: Principal, directory, today: date, region: object) -> dict:
    if not isinstance(region, str) or region not in REGIONS:
        raise ApiError(400, "That area is not on the body map.")

    def change(state):
        source = _hosted_state(directory, principal.token) if state is None else state
        found = _find_spot(source, region)
        if found is None:
            raise ApiError(404, "That sore spot is not active.")
        updated = {
            "region": region,
            "severity": found.get("severity") if found.get("severity") in SEVERITIES else "mild",
            "started_on": _iso(found.get("started_on")) or today.isoformat(),
            "check_in_on": _iso(found.get("check_in_on")) or today.isoformat(),
            "cleared": True,
        }
        if state is None:
            _save_hosted_spot(directory, principal.token, updated)
            return
        rows = [row for row in state.get("spots") or [] if isinstance(row, dict) and row.get("region") != region]
        rows.append(updated)
        state["spots"] = rows

    return _mutate(principal, directory, today, change)
