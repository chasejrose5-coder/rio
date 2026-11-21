# heart_rate_store.py — one heart-rate row per athlete.

"""Hosted accounts use the signed-in Supabase key, so row level security applies.
The service role is not used. Local accounts use a sealed record that is not
a plan key, and the plan key is written back so it stays last. The in-memory
directory keeps a bag per user id.

zones_for in engines.heart_rate is what a later prescription should call.
This module only loads and saves the inputs.
"""

from __future__ import annotations

import json

from api.errors import ApiError
from api.identity import Principal
from engines.heart_rate import HeartRateInput, profile_from_stored, require_anchors
from ui.accounts import AccountError, last_key, read_record, write_record
from ui.cloud_store import CloudAuthError, MemoryDirectory

# Not a plan key. Past seasons and the plan list leave it alone.
HEART_RATE_RECORD = "rio.api.heart_rate.v1"


def _blank() -> dict:
    return {"no_monitor": False, "resting_hr": None, "max_hr": None, "zones": None}


def _copy(raw: dict) -> dict:
    zones = raw.get("zones")
    return {
        "no_monitor": raw.get("no_monitor") is True,
        "resting_hr": raw.get("resting_hr"),
        "max_hr": raw.get("max_hr"),
        "zones": [dict(row) for row in zones if isinstance(row, dict)] if isinstance(zones, list) else None,
    }


def _memory_bag(directory) -> dict:
    bag = getattr(directory, "api_heart_rate", None)
    if not isinstance(bag, dict):
        bag = {}
        setattr(directory, "api_heart_rate", bag)
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
    raw = read_record(principal.accounts_path, principal.email, principal.seal, HEART_RATE_RECORD)
    if not isinstance(raw, str) or not raw.strip():
        return _blank()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return _blank()
    if not isinstance(parsed, dict):
        return _blank()
    return _copy(parsed)


def _save_local(principal: Principal, state: dict) -> None:
    body = json.dumps(_copy(state), separators=(",", ":"), sort_keys=True)
    previous = last_key(principal.accounts_path, principal.email, principal.seal)
    write_record(principal.accounts_path, principal.email, principal.seal, HEART_RATE_RECORD, body)
    if isinstance(previous, str) and previous and previous != HEART_RATE_RECORD:
        kept = read_record(principal.accounts_path, principal.email, principal.seal, previous)
        if isinstance(kept, str) and kept:
            write_record(principal.accounts_path, principal.email, principal.seal, previous, kept)


def _rows(result) -> list:
    data = getattr(result, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _hosted(directory) -> bool:
    return directory is not None and not isinstance(directory, MemoryDirectory) and hasattr(directory, "_user_client")


def _hosted_state(directory, token: str) -> dict:
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        rows = _rows(
            client.table("heart_rate")
            .select("resting_hr,max_hr,no_monitor,zones")
            .eq("user_id", user_id)
            .execute()
        )
    except CloudAuthError:
        raise
    except Exception as exc:
        raise ApiError(503, "Heart rate could not be loaded. Run migration 015.") from exc
    if not rows:
        return _blank()
    return _copy(rows[0])


def _save_hosted(directory, token: str, state: dict) -> None:
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        stored = _copy(state)
        row = {"user_id": user_id, **stored}
        client.table("heart_rate").upsert(row, on_conflict="user_id").execute()
    except CloudAuthError:
        raise
    except Exception as exc:
        raise ApiError(503, "Heart rate could not be saved. Run migration 015.") from exc


def _read(principal: Principal, directory) -> dict:
    if principal.kind == "local":
        return _local_state(principal)
    if not isinstance(principal.token, str) or not principal.token:
        raise ApiError(401, "Sign in again.")
    if _hosted(directory):
        return _hosted_state(directory, principal.token)
    return _memory_state(directory, principal.token)


def _write(principal: Principal, directory, state: dict) -> None:
    if principal.kind == "local":
        _save_local(principal, state)
        return
    if not isinstance(principal.token, str) or not principal.token:
        raise ApiError(401, "Sign in again.")
    if _hosted(directory):
        _save_hosted(directory, principal.token, state)
        return
    _save_memory(directory, principal.token, state)


def load_profile(principal: Principal, directory) -> dict:
    try:
        return profile_from_stored(_read(principal, directory))
    except CloudAuthError as exc:
        raise ApiError(401, str(exc)) from exc
    except AccountError as exc:
        raise ApiError(400, str(exc)) from exc


def _store_number(number) -> str | None:
    if number is None:
        return None
    return format(number, "f")


def save_profile(principal: Principal, directory, patch: dict) -> dict:
    """Merge one edit. Unknown keys are ignored. A bad value is refused before the write."""
    if not patch:
        raise ApiError(400, "Nothing to save.")
    try:
        current = _read(principal, directory)
        stored = _apply(current, patch)
        _write(principal, directory, stored)
        return profile_from_stored(stored)
    except CloudAuthError as exc:
        raise ApiError(401, str(exc)) from exc
    except AccountError as exc:
        raise ApiError(400, str(exc)) from exc


def _apply(current: dict, patch: dict) -> dict:
    no_monitor = current.get("no_monitor") is True
    resting = current.get("resting_hr")
    maximum = current.get("max_hr")
    zones = current.get("zones") if isinstance(current.get("zones"), list) else None
    if "no_monitor" in patch:
        if not isinstance(patch["no_monitor"], bool):
            raise ApiError(400, "That setting could not be saved.")
        no_monitor = patch["no_monitor"]
    reset = patch.get("reset") is True
    if reset:
        zones = None
    if "resting_hr" in patch or "max_hr" in patch:
        if "resting_hr" not in patch or "max_hr" not in patch:
            raise ApiError(400, "Enter a resting heart rate and a max heart rate.")
        try:
            low, high = require_anchors(patch["resting_hr"], patch["max_hr"])
        except HeartRateInput as exc:
            raise ApiError(400, str(exc)) from exc
        resting = _store_number(low)
        maximum = _store_number(high)
        if "zones" not in patch and not reset:
            zones = None
    if "zones" in patch and not reset:
        if patch["zones"] is None:
            zones = None
        else:
            if resting is None or maximum is None:
                raise ApiError(400, "Enter a resting heart rate and a max heart rate.")
            try:
                built = require_anchors(resting, maximum)
                from engines.heart_rate import normalize_bounds

                custom = normalize_bounds(built[0], built[1], patch["zones"])
            except HeartRateInput as exc:
                raise ApiError(400, str(exc)) from exc
            zones = None if custom is None else [
                {"zone": row["zone"], "low_bpm": row["low_bpm"], "high_bpm": row["high_bpm"]} for row in custom
            ]
    if not no_monitor and resting is None:
        raise ApiError(400, "Enter a resting heart rate between 30 and 100.")
    if reset and resting is None:
        raise ApiError(400, "Enter a resting heart rate and a max heart rate.")
    return {
        "no_monitor": no_monitor,
        "resting_hr": resting,
        "max_hr": maximum,
        "zones": zones,
    }
