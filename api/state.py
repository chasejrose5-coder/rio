# state.py — quality bases and workout notes, outside the plan row.

"""season_quality_base and rio_workout_notes.

The plan row still holds the plan, marks, and actuals. These two stay
beside it so a Streamlit save, which does not send them, does not wipe
them on Supabase. Local accounts keep them in a sealed record that is
not the plan key.

Stored bases are used as written. When nothing is stored and the season
already has marks, bases are rebuilt in one order:

1. Start from sequence() for the four inputs. Not from the saved plan.
2. Walk the marked weeks from the smallest week number to the largest.
3. For each week, record the plan from before that week's adapt, drop
   any later week's base, then adapt that week. This is the same order
   auto_adapt uses when bases are already present.
4. The next adapt in this request uses those bases, and the request
   stores them. A later week is adapted from the plan recorded before
   that week, not from a plan that week already changed.

A sealed local record that cannot hold every base stores the plan and
the notes and leaves the bases empty, so the next request rebuilds them
in that same order.

The model is not called here. A note is the four fields complete_insight
already returns, saved after the plan write.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from engines.season import sequence
from services.season_commit import adapt_from_result
from ui.accounts import write_record
from ui.cloud_store import CloudAuthError, MemoryDirectory
from ui.plan_store import MARKS

# One sealed key per season. It is not a plan key, so the past-season list
# does not show it. The plan key is written after this one so it stays last.
STATE_PREFIX = "rio.api.state.v1\n"
# ui.accounts refuses a record longer than this. The message there is generic.
_RECORD_LIMIT = 400_000
_NOTE_KEYS = ("headline", "body", "carry_forward", "used_result_band")
_NOTE_BANDS = ("on_track", "fell_short", "went_better")


def state_key(inputs: tuple[str, str, str, str]) -> str:
    """The sealed key for this season's plan, bases, and notes."""
    return STATE_PREFIX + "\n".join(inputs)


def encode_bases(bases: object) -> dict[str, dict]:
    """Week numbers as strings. JSON objects cannot use int keys."""
    if not isinstance(bases, dict):
        return {}
    encoded: dict[str, dict] = {}
    for key, plan in bases.items():
        if not isinstance(plan, dict):
            continue
        try:
            week = int(key)
        except (TypeError, ValueError):
            continue
        if isinstance(key, bool) or week < 1:
            continue
        encoded[str(week)] = deepcopy(plan)
    return encoded


def decode_bases(raw: object) -> dict[int, dict]:
    """The stored map, with week numbers as ints again."""
    encoded = encode_bases(raw)
    return {int(key): plan for key, plan in encoded.items()}


def encode_notes(notes: object) -> dict[str, dict]:
    """Dates that have a note. A bad entry is left out."""
    if not isinstance(notes, dict):
        return {}
    cleaned: dict[str, dict] = {}
    for day, item in notes.items():
        if not isinstance(day, str) or not isinstance(item, dict):
            continue
        note = item.get("note")
        if not note_ok(note):
            continue
        cleaned[day] = {"note": deepcopy(note), "viewed": item.get("viewed") is True}
    return cleaned


def note_ok(note: object) -> bool:
    """The four insight fields. A lap list, Strava, or a score is refused.

    This does not call the model and does not check sentence counts. Those
    belong to the insight route. Saving a note only checks the shape.
    """
    if not isinstance(note, dict) or set(note) != set(_NOTE_KEYS):
        return False
    if note.get("used_result_band") not in _NOTE_BANDS:
        return False
    for key in ("headline", "body", "carry_forward"):
        text = note.get(key)
        if not isinstance(text, str):
            return False
        if any(ord(char) < 32 or ord(char) == 127 for char in text):
            return False
    blob = " ".join(str(note[key]) for key in _NOTE_KEYS).lower()
    if "strava" in blob or "gps" in blob:
        return False
    if "probability" in blob or "readiness" in blob:
        return False
    return True


def recompute_quality_bases(inputs: tuple[str, str, str, str], marks: dict) -> dict[int, dict]:
    """Bases for the marks already stored, earliest week first.

    The returned dict is the one adapt_from_result fills. The plan it
    builds is not returned: the caller keeps the stored plan until the
    next adapt replaces it.
    """
    plan = sequence(*inputs)
    bases: dict[int, dict] = {}
    scratch: dict = {}
    weeks = sorted(week for week in marks if isinstance(week, int) and not isinstance(week, bool))
    for week in weeks:
        outcome = marks.get(week)
        if outcome not in MARKS:
            continue
        plan = adapt_from_result(plan, week, outcome, bases, scratch)
    return bases


def resolve_bases(inputs: tuple[str, str, str, str], marks: dict, stored: object) -> tuple[dict, str]:
    """Stored bases, or a rebuild when the store has none.

    The source is "stored", "recomputed", or "empty".
    """
    bases = decode_bases(stored)
    if bases:
        return bases, "stored"
    if marks:
        return recompute_quality_bases(inputs, marks), "recomputed"
    return {}, "empty"


def season_state_row(user_id: str, inputs: tuple[str, str, str, str], bases: dict, notes: dict) -> dict:
    """One season_state row. The plan itself stays on public.plans."""
    return {
        "user_id": user_id,
        "current_time": inputs[0],
        "start_date": inputs[1],
        "goal_time": inputs[2],
        "goal_date": inputs[3],
        "quality_base": encode_bases(bases),
        "workout_notes": encode_notes(notes),
    }


class StateMissing(CloudAuthError):
    """The hosted state table is not there yet. The plan write already finished."""


def memory_bag(directory: Any) -> dict:
    """Per-user state on the in-memory directory. Other athletes stay apart."""
    bag = getattr(directory, "api_season_state", None)
    if not isinstance(bag, dict):
        bag = {}
        setattr(directory, "api_season_state", bag)
    return bag


def _user_key(directory: Any, token: str) -> str:
    return directory.user_id(token)


def load_memory_state(directory: Any, token: str, inputs: tuple) -> dict:
    bag = memory_bag(directory)
    found = bag.get(_user_key(directory, token), {}).get(inputs)
    if not isinstance(found, dict):
        return {}
    return deepcopy(found)


def save_memory_state(directory: Any, token: str, inputs: tuple, bases: dict, notes: dict) -> None:
    bag = memory_bag(directory)
    user_id = _user_key(directory, token)
    owned = bag.setdefault(user_id, {})
    owned[inputs] = {
        "quality_base": encode_bases(bases),
        "workout_notes": encode_notes(notes),
    }


def drop_memory_state(directory: Any, token: str, inputs: tuple) -> None:
    bag = memory_bag(directory)
    user_id = _user_key(directory, token)
    owned = bag.get(user_id)
    if isinstance(owned, dict):
        owned.pop(inputs, None)


def load_local_state(path, email: str, secret: str, inputs: tuple) -> dict:
    from ui.accounts import read_record

    raw = read_record(path, email, secret, state_key(inputs))
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def dump_local_state(plan: dict, bases: dict, notes: dict) -> str:
    """JSON for the sealed record. Bases are dropped when they do not fit."""
    full = {
        "notes": encode_notes(notes),
        "plan": plan,
        "quality_base": encode_bases(bases),
    }
    text = json.dumps(full, separators=(",", ":"), sort_keys=True, default=str)
    if len(text) <= _RECORD_LIMIT:
        return text
    slim = {
        "notes": encode_notes(notes),
        "plan": plan,
        "quality_base": {},
        "recompute": True,
    }
    text = json.dumps(slim, separators=(",", ":"), sort_keys=True, default=str)
    if len(text) > _RECORD_LIMIT:
        raise CloudAuthError("This season could not be saved.")
    return text


def save_local_state(path, email: str, secret: str, inputs: tuple, plan: dict, bases: dict, notes: dict) -> None:
    write_record(path, email, secret, state_key(inputs), dump_local_state(plan, bases, notes))


def drop_local_state(path, email: str, secret: str, inputs: tuple) -> None:
    from ui.accounts import delete_exact

    delete_exact(path, email, secret, [state_key(inputs)])


def _conflict() -> str:
    return "user_id,start_date,goal_date,current_time,goal_time"


def save_hosted_state(directory: Any, token: str, inputs: tuple, bases: dict, notes: dict) -> None:
    """Upsert one row with the signed-in key. The service role is not used."""
    if isinstance(directory, MemoryDirectory):
        save_memory_state(directory, token, inputs, bases, notes)
        return
    if not hasattr(directory, "_user_client"):
        save_memory_state(directory, token, inputs, bases, notes)
        return
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        row = season_state_row(user_id, inputs, bases, notes)
        client.table("season_state").upsert(row, on_conflict=_conflict()).execute()
    except CloudAuthError:
        raise
    except Exception as exc:
        raise StateMissing("Season state could not be saved. Run migration 009.") from exc


def load_hosted_state(directory: Any, token: str, inputs: tuple) -> dict:
    if isinstance(directory, MemoryDirectory) or not hasattr(directory, "_user_client"):
        return load_memory_state(directory, token, inputs)
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        found = (
            client.table("season_state")
            .select("quality_base,workout_notes")
            .eq("user_id", user_id)
            .eq("current_time", inputs[0])
            .eq("start_date", inputs[1])
            .eq("goal_time", inputs[2])
            .eq("goal_date", inputs[3])
            .limit(1)
            .execute()
        )
    except Exception as exc:
        raise StateMissing("Season state could not be read. Run migration 009.") from exc
    data = getattr(found, "data", None)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return {}


def drop_hosted_state(directory: Any, token: str, inputs: tuple) -> None:
    if isinstance(directory, MemoryDirectory) or not hasattr(directory, "_user_client"):
        drop_memory_state(directory, token, inputs)
        return
    try:
        client = directory._user_client(token)
        user_id = directory._token_user(client, token)
        (
            client.table("season_state")
            .delete()
            .eq("user_id", user_id)
            .eq("current_time", inputs[0])
            .eq("start_date", inputs[1])
            .eq("goal_time", inputs[2])
            .eq("goal_date", inputs[3])
            .execute()
        )
    except Exception:
        # The plan delete already succeeded. A missing table is the migration.
        return
