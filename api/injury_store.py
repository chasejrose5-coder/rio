# injury_store.py — rebuilding areas and done marks. The exercise text stays in the app.

"""Two tables, scoped to the signed-in athlete.

Hosted accounts use the signed-in Supabase key, so row level security applies.
The service role is not used. Local accounts use a sealed record that is not
a plan key. The in-memory directory keeps a bag per user id.

Today is the date the caller already resolved in the Settings time zone.
The level clock is engines.injury.
"""

from __future__ import annotations

import json
from datetime import date, datetime

from api.errors import ApiError
from api.identity import Principal
from engines.injury import AREAS, BLOCKS, level_index, level_name
from ui.accounts import AccountError, last_key, read_record, write_record
from ui.cloud_store import CloudAuthError, MemoryDirectory

INJURY_RECORD = "rio.api.injury.v1"


def _blank() -> dict:
    return {"areas": [], "completions": []}


def _copy(state: dict) -> dict:
    return {
        "areas": [dict(row) for row in state.get("areas") or [] if isinstance(row, dict)],
        "completions": [dict(row) for row in state.get("completions") or [] if isinstance(row, dict)],
    }


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


def _stored_level(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        if isinstance(value, str) and value in {"0", "1", "2"}:
            return int(value)
        return None
    if value not in (0, 1, 2):
        return None
    return value


def _public(today: date, state: dict) -> dict:
    areas = []
    for row in state.get("areas") or []:
        if not isinstance(row, dict):
            continue
        area_id = row.get("area_id")
        anchor = _iso(row.get("anchor_on"))
        level = _stored_level(row.get("level"))
        if not isinstance(area_id, str) or area_id not in AREAS or not anchor or level is None:
            continue
        try:
            anchor_day = date.fromisoformat(anchor)
            now = level_index(level, anchor_day, today)
        except ValueError:
            continue
        areas.append(
            {
                "area_id": area_id,
                "anchor_on": anchor,
                "level": level,
                "level_now": now,
                "level_name": level_name(level, anchor_day, today),
            }
        )
    areas.sort(key=lambda row: row["area_id"])
    completions = []
    for row in state.get("completions") or []:
        if not isinstance(row, dict):
            continue
        done = _iso(row.get("date") or row.get("done_on"))
        block = row.get("block_id")
        if done and isinstance(block, str) and block in BLOCKS:
            completions.append({"date": done, "block_id": block})
    completions.sort(key=lambda row: (row["date"], row["block_id"]))
    return {"today": today.isoformat(), "areas": areas, "completions": completions}


def _memory_bag(directory) -> dict:
    bag = getattr(directory, "api_injury", None)
    if not isinstance(bag, dict):
        bag = {}
        setattr(directory, "api_injury", bag)
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
    raw = read_record(principal.accounts_path, principal.email, principal.seal, INJURY_RECORD)
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
    write_record(principal.accounts_path, principal.email, principal.seal, INJURY_RECORD, body)
    if isinstance(previous, str) and previous and previous != INJURY_RECORD:
        kept = read_record(principal.accounts_path, principal.email, principal.seal, previous)
        if isinstance(kept, str) and kept:
            write_record(principal.accounts_path, principal.email, principal.seal, previous, kept)


def _rows(result) -> list:
    data = getattr(result, "data", None)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def _hosted(directory) -> bool:
    return directory is not None and not isinstance(directory, MemoryDirectory) and hasattr(directory, "_user_client")


def _hosted_state(directory, token: str) -> dict:
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        areas = _rows(client.table("injury_areas").select("area_id,anchor_on,level").eq("user_id", user_id).execute())
        completions = _rows(
            client.table("injury_completions").select("done_on,block_id").eq("user_id", user_id).execute()
        )
    except CloudAuthError:
        raise
    except Exception as exc:
        raise ApiError(503, "Injury prevention could not be loaded. Run migration 017.") from exc
    return {
        "areas": [
            {"area_id": row.get("area_id"), "anchor_on": row.get("anchor_on"), "level": row.get("level")}
            for row in areas
        ],
        "completions": [
            {"date": row.get("done_on"), "block_id": row.get("block_id")} for row in completions
        ],
    }


def _save_hosted_area(directory, token: str, area: dict | None, area_id: str) -> None:
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        table = client.table("injury_areas")
        if area is None:
            table.delete().eq("user_id", user_id).eq("area_id", area_id).execute()
            return
        table.upsert(
            {"user_id": user_id, "area_id": area_id, "anchor_on": area["anchor_on"], "level": area["level"]},
            on_conflict="user_id,area_id",
        ).execute()
    except CloudAuthError:
        raise
    except Exception as exc:
        raise ApiError(503, "Injury prevention could not be saved. Run migration 017.") from exc


def _save_hosted_completion(directory, token: str, today: date, block_id: str, remove: bool) -> None:
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        table = client.table("injury_completions")
        if remove:
            table.delete().eq("user_id", user_id).eq("done_on", today.isoformat()).eq("block_id", block_id).execute()
            return
        table.upsert(
            {"user_id": user_id, "done_on": today.isoformat(), "block_id": block_id},
            on_conflict="user_id,done_on,block_id",
            ignore_duplicates=True,
        ).execute()
    except CloudAuthError:
        raise
    except Exception as exc:
        raise ApiError(503, "Injury prevention could not be saved. Run migration 017.") from exc


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


def _find_area(state: dict, area_id: str) -> dict | None:
    for row in state.get("areas") or []:
        if isinstance(row, dict) and row.get("area_id") == area_id:
            return row
    return None


def select_area(principal: Principal, directory, today: date, area_id: object) -> dict:
    if not isinstance(area_id, str) or area_id not in AREAS:
        raise ApiError(400, "That area is not in the library.")
    anchor = today.isoformat()

    def change(state):
        if state is None:
            current = _hosted_state(directory, principal.token)
            if _find_area(current, area_id) is None:
                _save_hosted_area(directory, principal.token, {"anchor_on": anchor, "level": 0}, area_id)
            return
        if _find_area(state, area_id) is not None:
            return
        rows = [row for row in state.get("areas") or [] if isinstance(row, dict)]
        rows.append({"area_id": area_id, "anchor_on": anchor, "level": 0})
        state["areas"] = rows

    return _mutate(principal, directory, today, change)


def clear_area(principal: Principal, directory, today: date, area_id: object) -> dict:
    if not isinstance(area_id, str) or area_id not in AREAS:
        raise ApiError(400, "That area is not in the library.")

    def change(state):
        if state is None:
            _save_hosted_area(directory, principal.token, None, area_id)
            return
        state["areas"] = [
            row for row in state.get("areas") or [] if isinstance(row, dict) and row.get("area_id") != area_id
        ]

    return _mutate(principal, directory, today, change)


def step_back(principal: Principal, directory, today: date, area_id: object) -> dict:
    if not isinstance(area_id, str) or area_id not in AREAS:
        raise ApiError(400, "That area is not in the library.")

    def change(state):
        source = _hosted_state(directory, principal.token) if state is None else state
        found = _find_area(source, area_id)
        if found is None:
            raise ApiError(404, "That area is not selected.")
        anchor = _iso(found.get("anchor_on"))
        level = _stored_level(found.get("level"))
        if not anchor or level is None:
            raise ApiError(400, "That area has no level.")
        current = level_index(level, date.fromisoformat(anchor), today)
        if current <= 0:
            raise ApiError(400, "This area is already at easy.")
        updated = {"area_id": area_id, "anchor_on": today.isoformat(), "level": current - 1}
        if state is None:
            _save_hosted_area(directory, principal.token, updated, area_id)
            return
        rows = [row for row in state.get("areas") or [] if isinstance(row, dict) and row.get("area_id") != area_id]
        rows.append(updated)
        state["areas"] = rows

    return _mutate(principal, directory, today, change)


def _wants_removed(present: bool, done: object) -> bool:
    if done is True:
        return False
    if done is False:
        return True
    return present


def toggle_completion(principal: Principal, directory, today: date, block_id: object, done: object = None) -> dict:
    if not isinstance(block_id, str) or block_id not in BLOCKS:
        raise ApiError(400, "That block is not in the library.")
    if done is not None and not isinstance(done, bool):
        raise ApiError(400, "Say whether the block is done.")
    iso = today.isoformat()

    def change(state):
        source = _hosted_state(directory, principal.token) if state is None else state
        rows = [row for row in source.get("completions") or [] if isinstance(row, dict)]
        present = any(_iso(row.get("date") or row.get("done_on")) == iso and row.get("block_id") == block_id for row in rows)
        remove = _wants_removed(present, done)
        if state is None:
            if remove and present:
                _save_hosted_completion(directory, principal.token, today, block_id, True)
            elif not remove and not present:
                _save_hosted_completion(directory, principal.token, today, block_id, False)
            return
        if remove:
            state["completions"] = [
                row
                for row in rows
                if not (_iso(row.get("date") or row.get("done_on")) == iso and row.get("block_id") == block_id)
            ]
        elif not present:
            rows.append({"date": iso, "block_id": block_id})
            state["completions"] = rows

    return _mutate(principal, directory, today, change)


def summary(principal: Principal, directory, today: date, start: date, end: date) -> dict:
    if start > end:
        raise ApiError(400, "The week starts after it ends.")
    state = load_state(principal, directory, today)
    done = 0
    for row in state["completions"]:
        if start.isoformat() <= row["date"] <= end.isoformat():
            done += 1
    return {"tracked": True, "done": done, "label": "Injury prevention"}
