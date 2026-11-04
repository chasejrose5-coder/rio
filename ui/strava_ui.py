# strava_ui.py — Connect, sync once, and the planned-versus-actual lines.

"""The page calls this. HTTP and tokens stay in the Strava modules.

A missing client id or secret hides the button. Nothing here prints a secret.
"""

from __future__ import annotations

import html
import os
import secrets
import time
import urllib.parse
from datetime import date

import streamlit as st

from ui.cloud_config import cloud_settings, read_setting
from ui.strava import (
    CLIENT_ID,
    RateGate,
    StravaError,
    StravaLimited,
    authorize_url,
    configured,
    deauthorize,
    exchange_code,
    http_get,
    http_post,
    import_runs,
    make_state,
    match_runs,
    planned_vs_actual,
    redirect_uri,
    state_matches,
    to_stored_activity,
)
from ui.strava_store import current_strava_store

_GATE = RateGate()


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _label(text: str) -> str:
    return f'<p class="rio-mark-label">{_esc(text)}</p>'


def _note(text: str) -> str:
    return f'<p class="rio-note">{_esc(text)}</p>'


def _card(*parts: str) -> None:
    st.markdown(f'<div class="rio-card">{"".join(parts)}</div>', unsafe_allow_html=True)


def boot_strava() -> None:
    """Finish a redirect, then import once for this signed-in session."""
    consume_callback()
    sync_once()


def consume_callback() -> None:
    code = st.query_params.get("code")
    state = st.query_params.get("state")
    user_id = st.session_state.get("rio_cloud_user_id")
    nonce = st.session_state.get("rio_strava_nonce")
    if not isinstance(code, str) or not isinstance(state, str) or not isinstance(user_id, str):
        return
    if not state_matches(state, user_id, nonce if isinstance(nonce, str) else ""):
        return
    try:
        token = exchange_code(code, http_post)
        _save_token(user_id, token)
    except StravaError as exc:
        st.session_state["rio_strava_notice"] = str(exc)
    _clear_callback()
    st.session_state.pop("rio_strava_synced", None)
    st.rerun()


def sync_once(force: bool = False) -> None:
    if st.session_state.get("rio_strava_synced") is True and not force:
        return
    user_id = st.session_state.get("rio_cloud_user_id")
    token = _cached_token()
    if not isinstance(user_id, str) or not isinstance(token, dict):
        return
    store = current_strava_store()
    service_key = _service_key()
    if store is None or not service_key:
        return
    plan = st.session_state.get("season_plan")
    sessions = plan.get("sessions") if isinstance(plan, dict) else []
    now = int(time.time())
    last = token.get("last_sync_at") if isinstance(token.get("last_sync_at"), int) else None
    try:
        fresh, runs = import_runs(
            token,
            now=now,
            last_sync=last,
            get=http_get,
            post=http_post,
            gate=_GATE,
        )
    except StravaLimited as exc:
        st.session_state["rio_strava_notice"] = str(exc)
        st.session_state["rio_strava_synced"] = True
        return
    except StravaError as exc:
        st.session_state["rio_strava_notice"] = str(exc)
        return
    runs = match_runs(runs, sessions)
    fresh["last_sync_at"] = now
    fresh["athlete_name"] = fresh.get("athlete_name") or token.get("athlete_name") or ""
    try:
        store.put_activities(user_id, runs)
        _save_token(user_id, fresh)
    except Exception:
        st.session_state["rio_strava_notice"] = "Strava could not be saved."
        return
    _remember(runs)
    st.session_state["rio_strava_synced"] = True


def render_settings() -> None:
    if not configured():
        return
    st.markdown(_label("Strava"), unsafe_allow_html=True)
    st.markdown(_note("Strava data is only visible to you."), unsafe_allow_html=True)
    token = _cached_token()
    if isinstance(token, dict) and token.get("athlete_name"):
        st.markdown(
            f'<p class="rio-settings-note">Connected as {token["athlete_name"]}.</p>',
            unsafe_allow_html=True,
        )
        if st.button("Disconnect", key="rio-strava-disconnect"):
            _disconnect()
        return
    render_connect_button()


def render_connect_button() -> None:
    if not configured() or isinstance(_cached_token(), dict):
        return
    user_id = st.session_state.get("rio_cloud_user_id")
    if not isinstance(user_id, str) or not user_id:
        return
    if "rio_strava_state" not in st.session_state:
        nonce = secrets.token_urlsafe(12)
        st.session_state["rio_strava_nonce"] = nonce
        st.session_state["rio_strava_state"] = make_state(user_id, nonce)
    state = st.session_state.get("rio_strava_state")
    if not isinstance(state, str):
        return
    url = authorize_url(read_setting(CLIENT_ID), redirect_uri(), state)
    if os.environ.get("RIO_STRAVA_TRANSPORT") == "fake":
        url = redirect_uri() + "?" + urllib.parse.urlencode({"code": "fake-code", "state": state})
    st.link_button("Connect with Strava", url)


def activity_block() -> None:
    if st.session_state.get("activity-refresh") is True:
        st.session_state["rio_strava_synced"] = False
        sync_once(force=True)
    notice = st.session_state.get("rio_strava_notice")
    if isinstance(notice, str) and notice.strip():
        st.markdown(f'<p class="rio-note">{_esc(notice)}</p>', unsafe_allow_html=True)
    rows = _comparisons()
    if not rows:
        return
    lines = []
    for row in rows:
        lines.append(
            "<p>"
            f'{_esc(row["date"])} · {_esc(row["name"])}<br>'
            f'Planned {_esc(row["planned"])}<br>'
            f'Actual {_esc(row["actual"])} · {_esc(row["status"])}'
            "</p>"
        )
    _card(_label("Planned vs actual"), "".join(lines), _note("From your Strava runs."))


def home_line() -> str:
    rows = _comparisons()
    if not rows:
        return ""
    row = rows[-1]
    return (
        '<div class="rio-card rio-card-tight">'
        '<p class="rio-mark-label">Planned vs actual</p>'
        f'<p class="rio-note">{_esc(row["name"])} · {_esc(row["actual"])} · {_esc(row["status"])}</p>'
        "</div>"
    )


def _comparisons() -> list[dict]:
    runs = st.session_state.get("rio_strava_runs")
    inputs = st.session_state.get("season_inputs")
    if not isinstance(runs, list) or not isinstance(inputs, (list, tuple)) or len(inputs) != 4:
        return []
    try:
        start = date.fromisoformat(str(inputs[1]))
        goal_day = date.fromisoformat(str(inputs[3]))
    except ValueError:
        return []
    rows = []
    for run in runs:
        if not isinstance(run, dict) or run.get("matched") is not True:
            continue
        try:
            on = date.fromisoformat(str(run.get("date")))
        except ValueError:
            continue
        rows.append(
            planned_vs_actual(
                run,
                current=str(inputs[0]),
                goal=str(inputs[2]),
                start=start,
                goal_day=goal_day,
                on=on,
            )
        )
    return rows


def _cached_token() -> dict | None:
    if "rio_strava_token" in st.session_state:
        found = st.session_state.get("rio_strava_token")
        return found if isinstance(found, dict) else None
    if st.session_state.get("rio_strava_checked") is True:
        return None
    st.session_state["rio_strava_checked"] = True
    user_id = st.session_state.get("rio_cloud_user_id")
    store = current_strava_store()
    service_key = _service_key()
    if not isinstance(user_id, str) or store is None or not service_key:
        st.session_state["rio_strava_token"] = None
        return None
    try:
        token = store.get_token(user_id, service_key)
    except Exception:
        token = None
    st.session_state["rio_strava_token"] = token if isinstance(token, dict) else None
    return token if isinstance(token, dict) else None


def _save_token(user_id: str, token: dict) -> None:
    store = current_strava_store()
    service_key = _service_key()
    if store is None or not service_key:
        raise StravaError("Strava could not be connected.")
    store.put_token(user_id, token, service_key)
    st.session_state["rio_strava_token"] = token
    st.session_state["rio_strava_checked"] = True


def _disconnect() -> None:
    user_id = st.session_state.get("rio_cloud_user_id")
    token = _cached_token()
    if isinstance(token, dict) and isinstance(token.get("access_token"), str):
        try:
            deauthorize(token["access_token"], http_post)
        except StravaError:
            pass
    store = current_strava_store()
    service_key = _service_key()
    if isinstance(user_id, str) and store is not None and service_key:
        try:
            store.delete_user(user_id, service_key)
        except Exception:
            st.session_state["rio_strava_notice"] = "Strava could not be disconnected."
            return
    for key in (
        "rio_strava_token",
        "rio_strava_synced",
        "rio_strava_runs",
        "rio_strava_state",
        "rio_strava_nonce",
        "rio_strava_notice",
    ):
        st.session_state.pop(key, None)
    st.session_state["rio_strava_token"] = None
    st.session_state["rio_strava_checked"] = True
    _drop_strava_from_session()
    st.rerun()


def restore_rows() -> None:
    """Put imported runs back after another pull replaces the same dates."""
    runs = st.session_state.get("rio_strava_runs")
    if isinstance(runs, list) and runs:
        _remember(runs)


def _remember(runs: list[dict]) -> None:
    st.session_state["rio_strava_runs"] = runs
    stored = st.session_state.get("season_activities")
    rows = list(stored) if isinstance(stored, list) else []
    by_id = {}
    for row in rows:
        if isinstance(row, dict) and row.get("id") and row.get("source") != "strava":
            by_id[str(row["id"])] = row
    for run in runs:
        activity = to_stored_activity(run)
        by_id[str(activity["id"])] = activity
    st.session_state["season_activities"] = list(by_id.values())


def _drop_strava_from_session() -> None:
    stored = st.session_state.get("season_activities")
    if not isinstance(stored, list):
        return
    st.session_state["season_activities"] = [
        row for row in stored if not (isinstance(row, dict) and row.get("source") == "strava")
    ]


def _clear_callback() -> None:
    for key in ("code", "state", "scope"):
        if key in st.query_params:
            del st.query_params[key]


def _service_key() -> str:
    settings = cloud_settings() or {}
    return str(settings.get("service_key") or "")
