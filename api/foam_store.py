# foam_store.py — done marks for foam rolling. The exercise text stays in the app.

"""One table, scoped to the signed-in athlete.

Hosted accounts use the signed-in Supabase key, so row level security applies.
The service role is not used. Local accounts use a sealed record that is not
a plan key. The in-memory directory keeps a bag per user id.

Today is the date the caller already resolved in the Settings time zone.
"""

from __future__ import annotations

import json
from datetime import date, datetime

from api.errors import ApiError
from api.identity import Principal
from ui.accounts import AccountError, last_key, read_record, write_record
from ui.cloud_store import CloudAuthError, MemoryDirectory

FOAM_RECORD = "rio.api.foam.v1"


def _blank() -> dict:
    return {"completions": []}


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


def _public(today: date, state: dict) -> dict:
    completions = []
    seen = set()
    for row in state.get("completions") or []:
        if isinstance(row, str):
            done = _iso(row)
        elif isinstance(row, dict):
            done = _iso(row.get("date") or row.get("done_on"))
        else:
            continue
        if done and done not in seen:
            seen.add(done)
            completions.append({"date": done})
    completions.sort(key=lambda row: row["date"])
    return {"today": today.isoformat(), "completions": completions}


def _memory_bag(directory) -> dict:
    bag = getattr(directory, "api_foam", None)
    if not isinstance(bag, dict):
        bag = {}
        setattr(directory, "api_foam", bag)
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
    _memory_bag(directory)[directory.user_id(token)] = {"completions": list(state.get("completions") or [])}


def _local_state(principal: Principal) -> dict:
    raw = read_record(principal.accounts_path, principal.email, principal.seal, FOAM_RECORD)
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
    body = json.dumps({"completions": list(state.get("completions") or [])}, separators=(",", ":"), sort_keys=True)
    previous = last_key(principal.accounts_path, principal.email, principal.seal)
    write_record(principal.accounts_path, principal.email, principal.seal, FOAM_RECORD, body)
    if isinstance(previous, str) and previous and previous != FOAM_RECORD:
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
        rows = _rows(client.table("foam_completions").select("done_on").eq("user_id", user_id).execute())
    except CloudAuthError:
        raise
    except Exception as exc:
        raise ApiError(503, "Foam could not be loaded. Run migration 019.") from exc
    return {"completions": [{"date": row.get("done_on")} for row in rows]}


def _save_hosted(directory, token: str, today: date, remove: bool) -> None:
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        table = client.table("foam_completions")
        if remove:
            table.delete().eq("user_id", user_id).eq("done_on", today.isoformat()).execute()
            return
        table.upsert(
            {"user_id": user_id, "done_on": today.isoformat()},
            on_conflict="user_id,done_on",
            ignore_duplicates=True,
        ).execute()
    except CloudAuthError:
        raise
    except Exception as exc:
        raise ApiError(503, "Foam could not be saved. Run migration 019.") from exc


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


def toggle_completion(principal: Principal, directory, today: date, done: object = None) -> dict:
    if done is not None and not isinstance(done, bool):
        raise ApiError(400, "Say whether the routine is done.")
    iso = today.isoformat()

    def present(state: dict) -> bool:
        for row in state.get("completions") or []:
            if isinstance(row, str) and _iso(row) == iso:
                return True
            if isinstance(row, dict) and _iso(row.get("date") or row.get("done_on")) == iso:
                return True
        return False

    def change(state):
        source = _hosted_state(directory, principal.token) if state is None else state
        has = present(source)
        remove = done is False or (done is None and has)
        if done is True:
            remove = False
        if state is None:
            if remove and has:
                _save_hosted(directory, principal.token, today, True)
            elif not remove and not has:
                _save_hosted(directory, principal.token, today, False)
            return
        dates = []
        for row in state.get("completions") or []:
            if isinstance(row, str):
                found = _iso(row)
            elif isinstance(row, dict):
                found = _iso(row.get("date") or row.get("done_on"))
            else:
                continue
            if found:
                dates.append(found)
        if remove:
            state["completions"] = [day for day in dates if day != iso]
        elif iso not in dates:
            dates.append(iso)
            state["completions"] = dates

    return _mutate(principal, directory, today, change)


def summary(principal: Principal, directory, today: date, start: date, end: date) -> dict:
    if start > end:
        raise ApiError(400, "The week starts after it ends.")
    state = load_state(principal, directory, today)
    done = sum(1 for row in state["completions"] if start.isoformat() <= row["date"] <= end.isoformat())
    return {"tracked": True, "done": done, "label": "Foam rolling"}
