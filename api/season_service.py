# season_service.py — one athlete's season, using the existing services.

"""Generate, read, mark, and delete. sequence and adapt stay in the engines.

The plan is written before a note is stored. complete_insight is not called.
A note that fails the shape check does not undo the plan.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import date

from api.errors import ApiError
from api.identity import Principal
from api.prefs import account_prefs
from api.state import (
    StateMissing,
    drop_hosted_state,
    drop_local_state,
    encode_notes,
    load_hosted_state,
    load_local_state,
    note_ok,
    resolve_bases,
    save_hosted_state,
    save_local_state,
)
from engines.season import sequence
from services.season_commit import (
    commit_mark,
    commit_result,
    commit_watchless_mark,
    quality_day,
)
from services.season_store import (
    LocalSeasonError,
    load_hosted_season,
    load_local_season,
    remove_past_season,
    save_hosted_season,
    save_local_season,
)
from ui.accounts import AccountError
from ui.cloud_session import plan_has_sessions, season_digest
from ui.cloud_store import CloudAuthError, MemoryDirectory
from ui.no_watch import finish_session, timed_mark
from ui.past_seasons import (
    is_past_season,
    season_entries,
    season_summary,
    summary_record,
)
from ui.plan_store import MARKS, inputs_ok, plan_inputs, storage_key
from ui.result import goal_seconds
from ui.settings import format_date

_LOG = logging.getLogger("rio.api")
_DROP = ("probability", "readiness", "readiness_score")


@dataclass
class OpenSeason:
    inputs: tuple[str, str, str, str]
    plan: dict
    marks: dict
    actuals: dict
    activities: list
    bases: dict
    notes: dict
    base_source: str
    digest: str
    state_stored: bool = True
    display_name: str = ""


def _public_plan(plan: dict) -> dict:
    cleaned = {key: value for key, value in plan.items() if key not in _DROP}
    sessions = cleaned.get("sessions")
    if isinstance(sessions, list):
        cleaned["sessions"] = [
            {key: value for key, value in session.items() if key not in _DROP}
            if isinstance(session, dict)
            else session
            for session in sessions
        ]
    return cleaned


def _marks(raw: object) -> dict:
    found = {}
    if not isinstance(raw, dict):
        return found
    for key, value in raw.items():
        if isinstance(key, bool) or value not in MARKS:
            continue
        try:
            week = int(key)
        except (TypeError, ValueError):
            continue
        if week >= 1:
            found[week] = value
    return found


def _inputs_of(row: dict) -> tuple[str, str, str, str] | None:
    inputs = (
        str(row.get("current_time") or ""),
        str(row.get("start_date") or ""),
        str(row.get("goal_time") or ""),
        str(row.get("goal_date") or ""),
    )
    if not inputs_ok(inputs):
        return None
    return inputs


def _digest(season: OpenSeason) -> str:
    return season_digest(season.inputs, season.plan, season.marks, season.actuals)


def _refresh_digest(season: OpenSeason) -> None:
    season.digest = _digest(season)


def parse_inputs(payload: dict) -> tuple[str, str, str, str]:
    """The four Start fields, or a 400 when one of them is unusable."""
    found = plan_inputs(
        {
            "current_time": payload.get("current_time"),
            "start_date": payload.get("start_date"),
            "goal_time": payload.get("goal_time"),
            "goal_date": payload.get("goal_date"),
        }
    )
    if found is None:
        raise ApiError(400, "Enter a current time, a start date, a goal time, and a goal date.")
    return found


def _session_on(plan: dict, day: str) -> dict | None:
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        return None
    for session in sessions:
        if isinstance(session, dict) and str(session.get("date") or "") == day:
            return session
    return None


def _merge_plans(existing: object, incoming: list) -> list:
    """Keep every other season. The one just saved is last, which is current."""
    rows = [row for row in existing if isinstance(row, dict)] if isinstance(existing, list) else []
    for plan in incoming:
        if not isinstance(plan, dict):
            continue
        ident = _inputs_of(plan)
        if ident is None:
            continue
        rows = [row for row in rows if _inputs_of(row) != ident]
        rows.append(plan)
    return rows


class _KeepSeasons:
    """MemoryDirectory replaces the whole plan list. Supabase upserts one row.

    This wrapper merges before the memory save so an older season stays.
    """

    def __init__(self, directory) -> None:
        self._directory = directory

    def __getattr__(self, name: str):
        return getattr(self._directory, name)

    def save_bundle(self, token, bundle):
        if isinstance(bundle, dict) and isinstance(bundle.get("plans"), list):
            current = self._directory.load_bundle(token)
            merged = dict(bundle)
            merged["plans"] = _merge_plans(current.get("plans") if isinstance(current, dict) else [], bundle["plans"])
            bundle = merged
        return self._directory.save_bundle(token, bundle)


def _panel_stats(inputs: tuple, stored: object, date_format: str) -> list[dict]:
    """The confirm panel: season_summary, with the season dates formatted."""
    stats = []
    for label, value in season_summary(inputs, stored):
        shown = value
        if label == "Season" and " – " in value:
            start, end = value.split(" – ", 1)
            shown = f"{format_date(start, date_format)} – {format_date(end, date_format)}"
        stats.append({"label": label, "value": shown})
    return stats


def _apply_notes(season: OpenSeason, raw: object) -> None:
    season.notes = encode_notes(raw)


def _hosted_open(principal: Principal, directory, today: date) -> OpenSeason | None:
    bundle = load_hosted_season(directory, principal.token)
    plans = bundle.get("plans") if isinstance(bundle, dict) else []
    chosen = None
    if isinstance(plans, list):
        for row in plans:
            if not isinstance(row, dict):
                continue
            inputs = _inputs_of(row)
            plan = row.get("plan")
            if inputs is None or not isinstance(plan, dict) or not plan_has_sessions(plan):
                continue
            if is_past_season(inputs, today):
                continue
            chosen = row
    if chosen is None:
        return None
    inputs = _inputs_of(chosen)
    assert inputs is not None
    marks = _marks(chosen.get("marks"))
    actuals = chosen.get("actuals") if isinstance(chosen.get("actuals"), dict) else {}
    try:
        state = load_hosted_state(directory, principal.token, inputs)
        stored_ok = True
    except StateMissing:
        state = {}
        stored_ok = False
    bases, source = resolve_bases(inputs, marks, state.get("quality_base") if isinstance(state, dict) else {})
    season = OpenSeason(
        inputs=inputs,
        plan=deepcopy(chosen.get("plan")),
        marks=marks,
        actuals=deepcopy(actuals),
        activities=[],
        bases=bases,
        notes={},
        base_source=source,
        digest="",
        state_stored=stored_ok and source != "recomputed",
        display_name=principal.display_name,
    )
    _apply_notes(season, state.get("workout_notes") if isinstance(state, dict) else {})
    _refresh_digest(season)
    return season


def _local_open(principal: Principal, today: date) -> OpenSeason | None:
    from ui.accounts import last_key, record_keys
    from ui.past_seasons import KEY_PREFIX, inputs_from_key

    path = principal.accounts_path
    keys = record_keys(path, principal.email, principal.seal, KEY_PREFIX)
    if not isinstance(keys, list):
        raise ApiError(401, "Sign in again.")
    entries = season_entries(keys)
    last = last_key(path, principal.email, principal.seal)
    prefer = inputs_from_key(last) if isinstance(last, str) else None
    chosen = None
    if prefer in entries and not is_past_season(prefer, today):
        chosen = prefer
    else:
        for inputs in entries:
            if not is_past_season(inputs, today):
                chosen = inputs
    if chosen is None:
        return None
    return _load_local(principal, chosen)


def _load_local(principal: Principal, inputs: tuple[str, str, str, str]) -> OpenSeason:
    try:
        marks, actuals, activities = load_local_season(
            principal.accounts_path,
            principal.email,
            principal.seal,
            storage_key(inputs),
        )
    except LocalSeasonError as exc:
        raise ApiError(401, str(exc)) from exc
    state = load_local_state(principal.accounts_path, principal.email, principal.seal, inputs)
    stored_plan = state.get("plan") if isinstance(state, dict) else None
    stored_bases = state.get("quality_base") if isinstance(state, dict) else {}
    if isinstance(state, dict) and state.get("recompute") is True:
        stored_bases = {}
    marks = _marks(marks)
    if not isinstance(actuals, dict):
        actuals = {}
    bases, source = resolve_bases(inputs, marks, stored_bases)
    if isinstance(stored_plan, dict) and plan_has_sessions(stored_plan):
        plan = stored_plan
    else:
        plan, bases = _replay(inputs, marks, actuals)
        source = "recomputed" if marks else "empty"
    season = OpenSeason(
        inputs=inputs,
        plan=plan,
        marks=marks,
        actuals=actuals,
        activities=activities if isinstance(activities, list) else [],
        bases=bases,
        notes={},
        base_source=source,
        digest="",
        state_stored=source == "stored",
        display_name=principal.display_name,
    )
    _apply_notes(season, state.get("notes") if isinstance(state, dict) else {})
    _refresh_digest(season)
    return season


def _replay(inputs: tuple, marks: dict, actuals: dict) -> tuple[dict, dict]:
    """The adapted plan when the local record has marks and no stored plan."""
    from services.season_commit import adapt_from_result, attach_actuals

    plan = sequence(*inputs)
    bases: dict = {}
    scratch: dict = {}
    for week in sorted(marks):
        outcome = marks[week]
        if outcome not in MARKS:
            continue
        plan = adapt_from_result(plan, week, outcome, bases, scratch)
    attach_actuals(plan, deepcopy(actuals))
    return plan, bases


def open_season(principal: Principal, directory, today: date) -> OpenSeason:
    if principal.kind == "hosted":
        found = _hosted_open(principal, directory, today)
    else:
        found = _local_open(principal, today)
    if found is None:
        raise ApiError(404, "No current season.")
    return found


def _save(principal: Principal, directory, season: OpenSeason, previous: str | None) -> None:
    """Write the plan first. Notes and bases follow, and do not block that write."""
    if principal.kind == "hosted":
        target = _KeepSeasons(directory) if isinstance(directory, MemoryDirectory) else directory
        try:
            save_hosted_season(
                target,
                principal.token,
                inputs=season.inputs,
                plan=season.plan,
                marks=season.marks,
                actuals=season.actuals,
                display_name=season.display_name or principal.display_name,
                saved_hash=previous,
            )
        except CloudAuthError as exc:
            raise ApiError(401, str(exc)) from exc
        try:
            save_hosted_state(directory, principal.token, season.inputs, season.bases, season.notes)
        except StateMissing as exc:
            _LOG.warning("season state was not stored: %s", type(exc).__name__)
            season.state_stored = False
            if season.base_source == "stored":
                season.base_source = "recomputed"
            return
        season.state_stored = True
        if season.bases:
            season.base_source = "stored"
        return
    try:
        save_local_state(
            principal.accounts_path,
            principal.email,
            principal.seal,
            season.inputs,
            season.plan,
            season.bases,
            season.notes,
        )
        save_local_season(
            principal.accounts_path,
            principal.email,
            principal.seal,
            storage_key(season.inputs),
            season.marks,
            season.actuals,
            season.activities,
        )
    except (CloudAuthError, AccountError) as exc:
        raise ApiError(400, str(exc)) from exc
    season.state_stored = True
    if season.bases:
        season.base_source = "stored"


def _store_note(principal: Principal, directory, season: OpenSeason, day: str, note: object, viewed: bool) -> bool:
    """Save one note after the plan. A bad note is left out."""
    if not note_ok(note):
        return False
    season.notes[day] = {"note": deepcopy(note), "viewed": viewed is True}
    season.notes = encode_notes(season.notes)
    try:
        if principal.kind == "hosted":
            save_hosted_state(directory, principal.token, season.inputs, season.bases, season.notes)
        else:
            save_local_state(
                principal.accounts_path,
                principal.email,
                principal.seal,
                season.inputs,
                season.plan,
                season.bases,
                season.notes,
            )
            # Keep the plan key last so the Streamlit account file still opens it.
            save_local_season(
                principal.accounts_path,
                principal.email,
                principal.seal,
                storage_key(season.inputs),
                season.marks,
                season.actuals,
                season.activities,
            )
    except (StateMissing, CloudAuthError, AccountError):
        return False
    return True


def remember_note(principal: Principal, directory, today: date, day: str, note: object, viewed: bool) -> OpenSeason:
    season = open_season(principal, directory, today)
    if _session_on(season.plan, day) is None:
        raise ApiError(400, "That day is not in this season.")
    if not _store_note(principal, directory, season, day, note, viewed):
        raise ApiError(400, "That note could not be saved.")
    return season


def generate(principal: Principal, directory, today: date, payload: dict) -> OpenSeason:
    inputs = parse_inputs(payload)
    try:
        plan = sequence(*inputs)
    except ValueError as exc:
        raise ApiError(400, str(exc)) from exc
    season = OpenSeason(
        inputs=inputs,
        plan=plan,
        marks={},
        actuals={},
        activities=[],
        bases={},
        notes={},
        base_source="empty",
        digest="",
        display_name=principal.display_name,
    )
    _refresh_digest(season)
    _save(principal, directory, season, None)
    return season


def _commit_fields(season: OpenSeason, outcome) -> bool:
    if outcome.error:
        raise ApiError(400, outcome.error)
    if not outcome.committed or outcome.plan is None or outcome.marks is None:
        return False
    season.plan = outcome.plan
    season.marks = _marks(outcome.marks)
    if season.bases:
        season.base_source = "stored"
    return True


def commit_week(principal: Principal, directory, today: date, week: int, choice: str) -> tuple[OpenSeason, bool]:
    if isinstance(week, bool) or not isinstance(week, int) or week < 1:
        raise ApiError(400, "That week is not in this season.")
    if choice not in MARKS:
        raise ApiError(400, "Choose on track, not hitting, or smashing.")
    season = open_season(principal, directory, today)
    previous = season.digest
    outcome = commit_mark(season.plan, week, choice, season.actuals, season.marks, season.bases)
    changed = _commit_fields(season, outcome)
    if changed:
        _refresh_digest(season)
        _save(principal, directory, season, previous)
    return season, changed


def commit_text(
    principal: Principal,
    directory,
    today: date,
    day: str,
    text: str,
    slots: list | None,
    intervals: str | None,
    note: object,
) -> tuple[OpenSeason, bool, bool | None]:
    season = open_season(principal, directory, today)
    session = _session_on(season.plan, day)
    if session is None:
        raise ApiError(400, "That day is not in this season.")
    previous = season.digest
    outcome = commit_result(
        season.plan,
        session,
        text,
        slots,
        intervals,
        season.actuals,
        season.marks,
        season.bases,
        goal_seconds(season.inputs[2]),
    )
    changed = _commit_fields(season, outcome)
    note_saved = None
    if changed:
        _refresh_digest(season)
        _save(principal, directory, season, previous)
        if note is not None:
            note_saved = _store_note(principal, directory, season, day, note, False)
    return season, changed, note_saved


def commit_done(
    principal: Principal,
    directory,
    today: date,
    day: str,
    outcome_choice: str,
    time_text: str,
    note: object,
) -> tuple[OpenSeason, bool, bool | None]:
    season = open_season(principal, directory, today)
    session = _session_on(season.plan, day)
    if session is None:
        raise ApiError(400, "That day is not in this season.")
    finished = finish_session(session, outcome_choice, time_text)
    if not finished.get("ok") or not isinstance(finished.get("row"), dict):
        raise ApiError(400, str(finished.get("error") or "Enter one time, like 1:12.4, or leave it blank."))
    row = finished["row"]
    previous = season.digest
    changed = False
    if timed_mark(row) and quality_day(session):
        outcome = commit_watchless_mark(
            season.plan,
            session,
            row,
            season.actuals,
            season.marks,
            season.bases,
        )
        changed = _commit_fields(season, outcome)
    else:
        season.actuals[str(session.get("date"))] = row
        changed = True
    note_saved = None
    if changed:
        _refresh_digest(season)
        _save(principal, directory, season, previous)
        if note is not None:
            note_saved = _store_note(principal, directory, season, day, note, False)
    return season, changed, note_saved


def _hosted_rows(principal: Principal, directory) -> list[dict]:
    bundle = load_hosted_season(directory, principal.token)
    plans = bundle.get("plans") if isinstance(bundle, dict) else []
    if not isinstance(plans, list):
        return []
    return [row for row in plans if isinstance(row, dict)]


def list_past(principal: Principal, directory, today: date, date_format: str) -> list[dict]:
    rows = []
    if principal.kind == "hosted":
        for row in _hosted_rows(principal, directory):
            inputs = _inputs_of(row)
            if inputs is None or not is_past_season(inputs, today):
                continue
            rows.append(
                {
                    "inputs": _input_payload(inputs),
                    "stats": _panel_stats(inputs, summary_record(row), date_format),
                }
            )
        return rows
    from ui.accounts import read_record, record_keys
    from ui.past_seasons import KEY_PREFIX

    keys = record_keys(principal.accounts_path, principal.email, principal.seal, KEY_PREFIX)
    if not isinstance(keys, list):
        raise ApiError(401, "Sign in again.")
    for inputs in season_entries(keys):
        if not is_past_season(inputs, today):
            continue
        raw = read_record(principal.accounts_path, principal.email, principal.seal, storage_key(inputs))
        stored = None
        if isinstance(raw, str) and raw.strip():
            import json

            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = None
            stored = summary_record(parsed)
        rows.append({"inputs": _input_payload(inputs), "stats": _panel_stats(inputs, stored, date_format)})
    return rows


def delete_past(principal: Principal, directory, today: date, payload: dict, date_format: str) -> dict:
    inputs = parse_inputs(payload)
    if not is_past_season(inputs, today):
        raise ApiError(409, "The current season can't be deleted.")
    if payload.get("confirm") is not True:
        raise ApiError(400, "Confirm this season before it is deleted.")
    owned = _find_stored(principal, directory, inputs)
    if owned is None:
        raise ApiError(404, "That season is not on this account.")
    stats = _panel_stats(inputs, owned, date_format)
    try:
        remove_past_season(
            hosted=principal.kind == "hosted",
            directory=directory,
            token=principal.token,
            path=principal.accounts_path,
            email=principal.email,
            secret=principal.seal,
            inputs=inputs,
            today=today,
        )
    except (CloudAuthError, AccountError) as exc:
        raise ApiError(409, str(exc)) from exc
    if principal.kind == "hosted":
        drop_hosted_state(directory, principal.token, inputs)
    else:
        drop_local_state(principal.accounts_path, principal.email, principal.seal, inputs)
    return {"deleted": True, "inputs": _input_payload(inputs), "stats": stats}


def _find_stored(principal: Principal, directory, inputs: tuple) -> dict | None:
    if principal.kind == "hosted":
        for row in _hosted_rows(principal, directory):
            if _inputs_of(row) == inputs:
                return summary_record(row)
        return None
    from ui.accounts import read_record

    raw = read_record(principal.accounts_path, principal.email, principal.seal, storage_key(inputs))
    if not isinstance(raw, str) or not raw.strip():
        return None
    import json

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return summary_record(parsed)


def _input_payload(inputs: tuple[str, str, str, str]) -> dict:
    return {
        "current_time": inputs[0],
        "start_date": inputs[1],
        "goal_time": inputs[2],
        "goal_date": inputs[3],
    }


def season_payload(season: OpenSeason, resolved: dict, *, committed: bool | None = None, note_saved: bool | None = None) -> dict:
    from api.prefs import prefs_payload

    prefs = prefs_payload(resolved)
    source = season.base_source
    stored = bool(season.state_stored)
    if not stored and season.bases:
        source = "recomputed"
    body = {
        "inputs": _input_payload(season.inputs),
        "plan": _public_plan(season.plan),
        "marks": {str(week): mark for week, mark in sorted(season.marks.items())},
        "actuals": season.actuals,
        "digest": season.digest,
        "notes": season.notes,
        "today": prefs.pop("today"),
        "prefs": prefs,
        "logging": prefs["logging"],
        "quality_base_weeks": sorted(int(week) for week in season.bases),
        "quality_base_source": source,
        "quality_base_stored": stored,
    }
    if committed is not None:
        body["committed"] = committed
    if note_saved is not None:
        body["note_saved"] = note_saved
    return body


def viewer(principal: Principal, directory) -> dict:
    """Prefs for this request. Today follows the saved time zone."""
    return account_prefs(principal, directory)
