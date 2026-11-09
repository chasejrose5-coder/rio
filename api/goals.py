# goals.py — the Profile goal-time override. The season is not rebuilt.

"""Streamlit keeps this in the browser. The API stores it beside the season.

Local accounts use a sealed record that is not a plan key. Hosted accounts
use auth user metadata. Neither path calls sequence() or adapt().
"""

from __future__ import annotations

import json

from api.errors import ApiError
from api.identity import Principal
from ui.accounts import AccountError, last_key, read_record, write_record
from ui.cloud_store import CloudAuthError
from ui.profile import clean_goal

# Not a plan key, so past seasons and Streamlit's plan list leave it alone.
GOAL_RECORD = "rio.api.goal.v1"


def _local_map(principal: Principal) -> dict:
    raw = read_record(principal.accounts_path, principal.email, principal.seal, GOAL_RECORD)
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): value for key, value in parsed.items() if isinstance(value, str)}


def read_override(principal: Principal, directory, profile_key: str) -> str | None:
    """The saved goal for this season key, or None."""
    if not profile_key:
        return None
    try:
        if principal.kind == "hosted":
            if directory is None or not isinstance(principal.token, str):
                return None
            found = directory.read_goal_override(principal.token, profile_key)
        else:
            found = _local_map(principal).get(profile_key)
    except (CloudAuthError, AccountError):
        return None
    return clean_goal(found)


def write_override(principal: Principal, directory, profile_key: str, goal_time: object) -> str:
    """Store one goal time. A bad time is refused and nothing is written."""
    cleaned = clean_goal(goal_time)
    if cleaned is None or not profile_key:
        raise ApiError(400, "goal_time is not an 800 time")
    try:
        if principal.kind == "hosted":
            if directory is None or not isinstance(principal.token, str):
                raise CloudAuthError("Sign in again.")
            directory.write_goal_override(principal.token, profile_key, cleaned)
        else:
            stored = _local_map(principal)
            stored[profile_key] = cleaned
            body = json.dumps(stored, separators=(",", ":"), sort_keys=True)
            # The plan key has to stay last. Streamlit opens whichever key was written last.
            previous = last_key(principal.accounts_path, principal.email, principal.seal)
            write_record(
                principal.accounts_path,
                principal.email,
                principal.seal,
                GOAL_RECORD,
                body,
            )
            if isinstance(previous, str) and previous and previous != GOAL_RECORD:
                kept = read_record(principal.accounts_path, principal.email, principal.seal, previous)
                if isinstance(kept, str) and kept:
                    write_record(
                        principal.accounts_path,
                        principal.email,
                        principal.seal,
                        previous,
                        kept,
                    )
    except CloudAuthError as exc:
        raise ApiError(400, str(exc)) from exc
    except AccountError as exc:
        raise ApiError(400, str(exc)) from exc
    return cleaned
