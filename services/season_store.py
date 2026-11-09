# season_store.py — save, load, and delete one season. No Streamlit.

"""Local accounts use the sealed file. Hosted accounts use a directory
object with save_bundle, load_bundle, and delete_season.

The directory may be the in-memory stand-in or the Supabase directory.
This module never constructs a client and never reads an API key.
Quality bases and workout notes are not part of either record.
"""

from __future__ import annotations

from ui.accounts import AccountError, delete_past_season, delete_records, read_record, write_record
from ui.cloud_session import season_digest
from ui.cloud_store import CloudAuthError
from ui.past_seasons import KEY_PREFIX
from ui.plan_store import dump_record, load_record, storage_key

# Dropped from the session when the open season is the one just deleted.
# The shell pops these. They are not a database row.
CURRENT_SEASON_KEYS = (
    "season_activities",
    "season_actuals",
    "season_inputs",
    "season_marks",
    "season_plan",
    "season_quality_base",
)


class LocalSeasonError(Exception):
    """The sealed record could not be opened. The message is safe to show."""


def save_local_season(
    path,
    email: object,
    secret: object,
    key: object,
    marks: object,
    actuals: object,
    activities: object,
) -> None:
    """Write marks, actuals, and activities under this plan key."""
    write_record(path, email, secret, key, dump_record(marks, actuals, activities))


def load_local_season(path, email: object, secret: object, key: object) -> tuple[dict, dict, list]:
    """Marks, actuals, and activities. A bad seal raises LocalSeasonError."""
    body = read_record(path, email, secret, key)
    if not isinstance(body, str):
        raise LocalSeasonError("This account could not be opened.")
    return load_record(body)


def save_cleared_marks(path, email: object, secret: object, inputs: tuple) -> None:
    """Replace this season's record with empty marks, actuals, and activities."""
    save_local_season(path, email, secret, storage_key(inputs), {}, {}, [])


def delete_local_plans(path, email: object, secret: object) -> None:
    """Remove every stored season on this local account. The account stays."""
    delete_records(path, email, secret, KEY_PREFIX)


def hosted_save_bundle(
    *,
    inputs: object,
    plan: object,
    marks: object,
    actuals: object,
    display_name: object,
) -> dict | None:
    """The goals-plus-plans body, or None when the season is not ready to save.

    Activities, quality bases, and workout notes are left out.
    """
    if not isinstance(plan, dict):
        return None
    if not isinstance(inputs, (list, tuple)) or len(inputs) != 4:
        return None
    stored_actuals = actuals if isinstance(actuals, dict) else {}
    stored_marks = marks or {}
    return {
        "goal": {
            "event": "800m",
            "current_mark": str(inputs[0]),
            "goal_time": str(inputs[2]),
            "goal_date": str(inputs[3]),
        },
        "plans": [
            {
                "current_time": str(inputs[0]),
                "start_date": str(inputs[1]),
                "goal_time": str(inputs[2]),
                "goal_date": str(inputs[3]),
                "plan": plan,
                "marks": stored_marks,
                "actuals": stored_actuals,
            }
        ],
        "profile": {"display_name": display_name or ""},
    }


def save_hosted_season(
    directory,
    token: object,
    *,
    inputs: object,
    plan: object,
    marks: object,
    actuals: object,
    display_name: object,
    saved_hash: object,
) -> str | None:
    """Write the season when the digest changed. Return the new digest.

    None means nothing was written. CloudAuthError is left for the caller.
    """
    if directory is None or not isinstance(token, str):
        return None
    bundle = hosted_save_bundle(
        inputs=inputs,
        plan=plan,
        marks=marks,
        actuals=actuals,
        display_name=display_name,
    )
    if bundle is None:
        return None
    stored_actuals = actuals if isinstance(actuals, dict) else {}
    digest = season_digest(inputs, plan, marks or {}, stored_actuals)
    if digest == saved_hash:
        return None
    directory.save_bundle(token, bundle)
    return digest


def load_hosted_season(directory, token: object) -> dict:
    """The signed-in bundle. A missing directory or token asks for a new sign-in."""
    if directory is None or not isinstance(token, str) or token == "":
        raise CloudAuthError("Sign in again.")
    return directory.load_bundle(token)


def remove_past_season(
    *,
    hosted: bool,
    directory,
    token: object,
    path,
    email: object,
    secret: object,
    inputs: tuple,
    today,
) -> None:
    """Delete one past season. A current season is refused by the store."""
    if hosted:
        if directory is None or not isinstance(token, str):
            raise CloudAuthError("Sign in again.")
        directory.delete_season(token, inputs, today)
        return
    if not isinstance(email, str) or not email or not isinstance(secret, str) or not secret:
        raise AccountError("Sign in again.")
    delete_past_season(path, email, secret, inputs, today)


def filter_plan_rows(rows: object, inputs: tuple) -> list | None:
    """Plan rows after this season is removed. None when rows is not a list."""
    if not isinstance(rows, list):
        return None
    kept = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        ident = (
            str(row.get("current_time") or ""),
            str(row.get("start_date") or ""),
            str(row.get("goal_time") or ""),
            str(row.get("goal_date") or ""),
        )
        if ident == inputs:
            continue
        kept.append(row)
    return kept


def filter_saved_inputs(stored: object, inputs: tuple) -> list | None:
    """Saved input tuples after this season is removed. None when stored is not a list."""
    if not isinstance(stored, list):
        return None
    kept = []
    for item in stored:
        if isinstance(item, (list, tuple)) and tuple(str(part) for part in item) == inputs:
            continue
        kept.append(item)
    return kept


def same_season(current: object, inputs: tuple) -> bool:
    """True when the open season is the one that was just deleted."""
    return isinstance(current, (list, tuple)) and tuple(str(part) for part in current) == inputs
