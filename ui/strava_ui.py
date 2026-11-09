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
from datetime import date, timedelta

import streamlit as st

from ui.cloud_config import cloud_settings, read_setting
from ui.strava import (
    CLIENT_ID,
    RateGate,
    StravaError,
    StravaLimited,
    _as_epoch,
    authorize_url,
    configured,
    deauthorize,
    exchange_code,
    http_get,
    http_post,
    import_runs,
    make_state,
    match_runs,
    earlier_logs,
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


def connected_as_html(name: object) -> str:
    """The athlete name is escaped. A Strava display name is not trusted HTML."""
    label = name if isinstance(name, str) and name.strip() else "Strava athlete"
    return f'<p class="rio-settings-note">Connected as {_esc(label)}.</p>'


def _card(*parts: str) -> None:
    st.markdown(f'<div class="rio-card">{"".join(parts)}</div>', unsafe_allow_html=True)


def boot_strava() -> None:
    """Finish a redirect, then let the page paint before the import."""
    consume_callback()
    if st.session_state.get("rio_test_preview"):
        return
    if st.session_state.get("rio_strava_sync_state") == "done":
        return
    if not isinstance(st.session_state.get("rio_cloud_user_id"), str):
        st.session_state["rio_strava_sync_state"] = "done"
        return
    _paint_then_sync()


def strava_sync_action(passes: int) -> str:
    """The first call paints. The next call imports."""
    if passes < 1:
        return "skip"
    return "sync"


def strava_gate_pending() -> bool:
    """True until the deferred import has looked up this athlete's token."""
    if st.session_state.get("rio_strava_sync_state") == "done":
        return False
    if st.session_state.get("rio_strava_checked") is True:
        return False
    if "rio_strava_token" in st.session_state:
        return False
    return True


def run_deferred_strava(passes: int) -> str:
    """skip on the first pass, wait until a plan exists, then import once."""
    if strava_sync_action(passes) != "sync":
        return "skip"
    if not _plan_ready():
        return "wait"
    sync_once()
    return "synced"


@st.fragment(run_every=timedelta(seconds=1))
def _paint_then_sync() -> None:
    """Import after the first paint, then redraw so Activity and errors show."""
    passes = int(st.session_state.get("rio_strava_defer_passes") or 0)
    outcome = run_deferred_strava(passes)
    st.session_state["rio_strava_defer_passes"] = passes + 1
    if outcome != "synced":
        return
    st.session_state["rio_strava_sync_state"] = "done"
    st.rerun(scope="app")


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


def strava_connected() -> bool:
    return isinstance(_cached_token(), dict)


def sync_once(force: bool = False) -> bool:
    """Import once the season is loaded. A failed import does not stick the flag."""
    if st.session_state.get("rio_test_preview"):
        return False
    if st.session_state.get("rio_strava_synced") is True and not force:
        return False
    if not _plan_ready():
        return False
    user_id = st.session_state.get("rio_cloud_user_id")
    token = _cached_token()
    if not isinstance(user_id, str) or not isinstance(token, dict):
        return False
    store = current_strava_store()
    service_key = _service_key()
    if store is None or not service_key:
        st.session_state["rio_strava_notice"] = "Strava could not be saved."
        return False
    sessions = _sessions()
    now = int(time.time())
    last = _as_epoch(token.get("last_sync_at"))
    try:
        fresh, runs = import_runs(
            token,
            now=now,
            last_sync=last,
            get=http_get,
            post=http_post,
            gate=_GATE,
            season_start=_season_start(sessions),
        )
    except StravaLimited as exc:
        st.session_state["rio_strava_notice"] = str(exc)
        return False
    except StravaError as exc:
        st.session_state["rio_strava_notice"] = str(exc)
        return False
    runs = match_runs(runs, sessions)
    fresh["last_sync_at"] = now
    fresh["athlete_name"] = fresh.get("athlete_name") or token.get("athlete_name") or ""
    try:
        store.put_activities(user_id, runs)
        _save_token(user_id, fresh)
    except Exception:
        st.session_state["rio_strava_notice"] = "Strava could not be saved."
        return False
    st.session_state.pop("rio_strava_notice", None)
    st.session_state["rio_strava_synced"] = True
    st.session_state["rio_strava_synced_at"] = now
    st.session_state["rio_strava_count"] = len(runs)
    _remember(runs)
    return True


def render_settings() -> None:
    st.markdown(_label("Strava"), unsafe_allow_html=True)
    if not configured():
        st.markdown(
            _note("Strava is not set up on this server yet."),
            unsafe_allow_html=True,
        )
        return
    st.markdown(_note("Strava data is only visible to you."), unsafe_allow_html=True)
    token = _cached_token()
    if isinstance(token, dict) and token.get("athlete_name"):
        st.markdown(connected_as_html(token.get("athlete_name")), unsafe_allow_html=True)
        if st.button("Disconnect", key="rio-strava-disconnect"):
            _disconnect()
        return
    render_connect_button()


def connect_url() -> str | None:
    """The Strava authorize URL Settings uses. None when connect is not available."""
    if not configured() or isinstance(_cached_token(), dict):
        return None
    user_id = st.session_state.get("rio_cloud_user_id")
    if not isinstance(user_id, str) or not user_id:
        return None
    if "rio_strava_state" not in st.session_state:
        nonce = secrets.token_urlsafe(12)
        st.session_state["rio_strava_nonce"] = nonce
        st.session_state["rio_strava_state"] = make_state(user_id, nonce)
    state = st.session_state.get("rio_strava_state")
    if not isinstance(state, str):
        return None
    url = authorize_url(read_setting(CLIENT_ID), redirect_uri(), state)
    if os.environ.get("RIO_STRAVA_TRANSPORT") == "fake":
        url = redirect_uri() + "?" + urllib.parse.urlencode({"code": "fake-code", "state": state})
    return url


def render_connect_button() -> None:
    url = connect_url()
    if not url:
        return
    st.link_button("Connect with Strava", url, type="primary")


def render_plan_prompt() -> bool:
    """The card after Generate. True when the athlete taps Not now.

    Connect uses connect_url(), the same OAuth link as Settings.
    """
    st.markdown(
        '<div class="rio-card">'
        '<h2 class="rio-week-title">Your plan is ready.</h2>'
        '<p class="rio-note">Connect Strava so your runs show up.</p>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<style>"
        '[class*="st-key-rio-strava-connect"] [data-testid="stBaseLinkButton-primary"],'
        '[class*="st-key-rio-strava-connect"] a {'
        "background:#C2461F !important;border:1px solid #C2461F !important;"
        "color:#FFFFFF !important;}"
        '[class*="st-key-rio-strava-connect"] a p,'
        '[class*="st-key-rio-strava-connect"] a span {color:#FFFFFF !important;}'
        "</style>",
        unsafe_allow_html=True,
    )
    url = connect_url()
    if url:
        st.link_button(
            "Connect Strava",
            url,
            type="primary",
            key="rio-strava-connect",
        )
    dismissed = st.button("Not now", key="rio-strava-not-now") is True
    # Home's photo is dark here. The pill stays cream so the label can be read.
    st.markdown(
        "<style>"
        '[class*="st-key-rio-strava-not-now"] button,'
        '[class*="st-key-rio-strava-not-now"] [data-testid="stBaseButton-secondary"] {'
        "background:#FFFCF7 !important;background-color:#FFFCF7 !important;"
        "border:1px solid #DCD6CC !important;"
        "border-radius:999px !important;color:#121110 !important;}"
        '[class*="st-key-rio-strava-not-now"] button p,'
        '[class*="st-key-rio-strava-not-now"] button span {color:#121110 !important;}'
        "</style>",
        unsafe_allow_html=True,
    )
    return dismissed


def prepare_activity() -> None:
    """Sync before the lists are drawn, then load this user's saved runs."""
    if st.session_state.get("rio_test_preview"):
        return
    if not strava_connected():
        return
    st.session_state.pop("activities_notice", None)
    clicked = st.session_state.get("activity-refresh") is True
    drawing = st.session_state.get("rio_strava_draw_after_sync") is True
    if clicked and not drawing:
        st.session_state["rio_strava_synced"] = False
        sync_once(force=True)
        st.session_state["rio_strava_draw_after_sync"] = True
        st.rerun()
    if drawing:
        st.session_state["rio_strava_draw_after_sync"] = False
    else:
        sync_once()
    load_into_session()


def prepare_home() -> None:
    if st.session_state.get("rio_test_preview"):
        return
    if not strava_connected():
        return
    sync_once()
    load_into_session()


def status_html() -> str:
    """The sync line under Refresh, or the error from the last attempt."""
    if st.session_state.get("rio_test_preview"):
        count = st.session_state.get("rio_strava_count")
        if isinstance(count, int):
            return f'<p class="rio-note">TEST season · {count} runs</p>'
        return ""
    if not strava_connected() and not st.session_state.get("rio_strava_notice"):
        return ""
    notice = st.session_state.get("rio_strava_notice")
    if isinstance(notice, str) and notice.strip():
        return f'<p class="rio-error">{_esc(notice.strip())}</p>'
    when = st.session_state.get("rio_strava_synced_at")
    if not isinstance(when, int):
        token = _cached_token()
        if isinstance(token, dict):
            when = _as_epoch(token.get("last_sync_at"))
    count = st.session_state.get("rio_strava_count")
    runs = st.session_state.get("rio_strava_runs")
    if not isinstance(count, int) and isinstance(runs, list):
        count = len(runs)
    if not isinstance(when, int) or not isinstance(count, int):
        return ""
    return f'<p class="rio-note">Last synced {_local_when(when)}, {count} runs imported</p>'


def activity_block() -> None:
    """Activity draws one card per run. The old stacked list stays off the page."""
    return


def home_line() -> str:
    prepare_home()
    runs = st.session_state.get("rio_strava_runs")
    inputs = st.session_state.get("season_inputs")
    plan = st.session_state.get("season_plan")
    sessions = plan.get("sessions") if isinstance(plan, dict) else None
    if not isinstance(runs, list) or not runs:
        return ""
    if not isinstance(sessions, list):
        sessions = []
    if not isinstance(inputs, (list, tuple)) or len(inputs) != 4:
        return ""
    try:
        start = date.fromisoformat(str(inputs[1]))
        goal_day = date.fromisoformat(str(inputs[3]))
    except ValueError:
        return ""
    from ui.activity_board import build_cards
    from ui.settings import normalize

    raw = dict(st.session_state.get("rio_settings") or {})
    picked = st.session_state.get("settings-pace")
    if picked in ("mi", "km"):
        raw["pace_units"] = picked
    unit = normalize(raw)["pace_units"]
    try:
        cards = build_cards(
            runs,
            [],
            sessions,
            current=str(inputs[0]),
            goal=str(inputs[2]),
            start=start,
            goal_day=goal_day,
            unit=unit,
        )
    except (TypeError, ValueError):
        return ""
    matched = [card for card in cards if card.get("status") != "Extra"]
    pool = matched or cards
    if not pool:
        return ""
    card = max(pool, key=lambda item: (item["date"], item["id"]))
    hidden = ""
    template = str(card.get("template_id") or "").strip()
    if template:
        hidden = f'<span hidden class="rio-template-id">{_esc(template)}</span>'
    return (
        '<div class="rio-card rio-card-tight">'
        '<p class="rio-mark-label">Planned vs actual</p>'
        f'<p class="rio-note">{_esc(card["name"])} · {_esc(card["detail"])} · {_esc(card["status"])}</p>'
        f"{hidden}"
        "</div>"
    )


def _comparisons() -> list[dict]:
    runs = st.session_state.get("rio_strava_runs")
    inputs = st.session_state.get("season_inputs")
    if not isinstance(runs, list):
        return []
    start = goal_day = None
    current = goal = ""
    if isinstance(inputs, (list, tuple)) and len(inputs) == 4:
        current = str(inputs[0])
        goal = str(inputs[2])
        try:
            start = date.fromisoformat(str(inputs[1]))
            goal_day = date.fromisoformat(str(inputs[3]))
        except ValueError:
            start = goal_day = None
    rows = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        try:
            on = date.fromisoformat(str(run.get("date")))
        except ValueError:
            continue
        if start is None or goal_day is None:
            row = {
                "date": run.get("date") or "",
                "name": run.get("name") or "Run",
                "planned": "—",
                "actual": _actual_text(run),
                "status": "Extra",
            }
        else:
            from ui.easy_pace import pace_kwargs

            row = planned_vs_actual(
                run,
                current=current,
                goal=goal,
                start=start,
                goal_day=goal_day,
                on=on,
                logs=earlier_logs(runs, on),
                unit=_pace_choice(),
                **pace_kwargs(),
            )
            if run.get("matched") is not True:
                row["planned"] = "—"
                row["status"] = "Extra"
        rows.append(row)
    return rows


def _pace_choice() -> str:
    from ui.settings import normalize

    raw = dict(st.session_state.get("rio_settings") or {})
    picked = st.session_state.get("settings-pace")
    if picked in ("mi", "km"):
        raw["pace_units"] = picked
    return normalize(raw)["pace_units"]


def _actual_text(run: dict) -> str:
    from engines.pace import effort_pace

    found = effort_pace(run, _pace_choice())
    if found:
        return f"Actual {found}"
    return "Actual —"


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


def _plan_ready() -> bool:
    return bool(_sessions())


def _sessions() -> list:
    plan = st.session_state.get("season_plan")
    sessions = plan.get("sessions") if isinstance(plan, dict) else None
    if not isinstance(sessions, list):
        return []
    return sessions


def _season_start(sessions: list) -> int | None:
    days = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        text = session.get("date")
        if not isinstance(text, str):
            continue
        try:
            days.append(date.fromisoformat(text))
        except ValueError:
            continue
    if not days:
        return None
    start = min(days)
    from datetime import datetime, timezone

    return int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())


def load_into_session() -> None:
    """Read this user's saved runs and match them to the plan."""
    if st.session_state.get("rio_test_preview"):
        return
    user_id = st.session_state.get("rio_cloud_user_id")
    store = current_strava_store()
    service_key = _service_key()
    runs: list = []
    if isinstance(user_id, str) and store is not None and service_key:
        try:
            loaded = store.get_activities(user_id)
            runs = loaded if isinstance(loaded, list) else []
        except Exception:
            st.session_state["rio_strava_notice"] = "Strava activities could not be read."
            saved = st.session_state.get("rio_strava_runs")
            runs = saved if isinstance(saved, list) else []
    runs = match_runs(runs, _sessions())
    if "rio_strava_count" not in st.session_state:
        st.session_state["rio_strava_count"] = len(runs)
    _remember(runs)


def _zone_name() -> str:
    """The zone from Settings. UTC when this session has not chosen one."""
    try:
        settings = st.session_state.get("rio_settings")
    except Exception:
        return "UTC"
    if isinstance(settings, dict):
        zone = settings.get("timezone")
        if isinstance(zone, str) and zone:
            return zone
    return "UTC"


def _local_when(when: int) -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    try:
        zone = ZoneInfo(_zone_name())
    except Exception:
        zone = ZoneInfo("UTC")
    local = datetime.fromtimestamp(when, zone)
    hour = int(local.strftime("%I"))
    return f"{local.strftime('%b')} {local.day}, {hour}:{local.strftime('%M')} {local.strftime('%p')}"
