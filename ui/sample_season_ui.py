# sample_season_ui.py — admin controls for the TEST athlete. Read only after that.

"""Load, delete, and open the test season. The signed-in season is put back."""

from __future__ import annotations

import html
from copy import deepcopy

import streamlit as st

from ui.cloud_config import cloud_settings
from ui.cloud_store import current_directory
from ui.strava_store import current_strava_store
from ui.sample_season import (
    TEST_NAME,
    TestSeasonError,
    delete_test_season,
    load_test_season,
    read_test_bundle,
)

_KEYS = (
    "season_plan",
    "season_inputs",
    "season_activities",
    "season_marks",
    "season_actuals",
    "season_quality_base",
    "season_generation",
    "rio_store_loaded",
    "rio_strava_runs",
    "rio_strava_count",
    "rio_strava_synced",
    "rio_strava_synced_at",
    "rio_strava_notice",
    "rio_strava_token",
    "rio_strava_checked",
    "activities_loaded",
    "activities_trigger",
    "activities_notice",
    "rio_cloud_saved_hash",
    "rio_local",
    "rio_adapt_pending",
)


def previewing() -> bool:
    return bool(st.session_state.get("rio_test_preview"))


def render_test_season() -> None:
    """The admin card. Other pages never call this."""
    st.markdown(
        '<div class="rio-card">'
        '<p class="rio-mark-label">Test season</p>'
        '<p class="rio-note">A separate TEST athlete with an 800 m season and eight weeks of runs. '
        "This login is not changed.</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    error = st.session_state.pop("rio_test_error", None)
    note = st.session_state.pop("rio_test_note", None)
    if isinstance(error, str) and error.strip():
        st.markdown(f'<p class="rio-error">{html.escape(error.strip())}</p>', unsafe_allow_html=True)
    if isinstance(note, str) and note.strip():
        st.markdown(f'<p class="rio-note">{html.escape(note.strip())}</p>', unsafe_allow_html=True)
    if st.button("Load test season", key="test-season-load", type="primary"):
        _load()
    confirm = st.checkbox(
        "Remove the TEST athlete and all of its data",
        key="test-season-confirm",
    )
    if st.button("Delete test season", key="test-season-delete"):
        _delete(confirm)
    home, plan, activity = st.columns(3)
    with home:
        if st.button("View test Home", key="test-season-view-home"):
            _arm("home")
    with plan:
        if st.button("View test Plan", key="test-season-view-plan"):
            _arm("plan")
    with activity:
        if st.button("View test Activity", key="test-season-view-activity"):
            _arm("activity")


def preview_banner() -> None:
    """A read-only bar. Back puts this login's season back."""
    if not previewing():
        return
    st.markdown(
        '<p class="rio-note">TEST Athlete · read only. This login is not changed.</p>',
        unsafe_allow_html=True,
    )
    if st.button("Back to admin", key="rio-test-back"):
        restore_admin_season()
        st.session_state["rio_test_go_admin"] = True
        st.rerun()


def apply_preview() -> None:
    """Show the stored TEST season. This login's copy stays in the backup."""
    bundle = st.session_state.get("rio_test_bundle")
    if not isinstance(bundle, dict) or not isinstance(bundle.get("plan"), dict):
        st.session_state.pop("rio_test_preview", None)
        return
    inputs = bundle.get("inputs")
    if isinstance(inputs, (list, tuple)) and len(inputs) == 4:
        st.session_state["season_inputs"] = tuple(str(item) for item in inputs)
    st.session_state["season_plan"] = bundle["plan"]
    activities = bundle.get("activities")
    st.session_state["season_activities"] = activities if isinstance(activities, list) else []
    st.session_state["season_marks"] = {}
    st.session_state["season_actuals"] = {}
    runs = bundle.get("runs")
    st.session_state["rio_strava_runs"] = runs if isinstance(runs, list) else []
    st.session_state["rio_strava_count"] = len(st.session_state["rio_strava_runs"])
    st.session_state["rio_store_loaded"] = True
    st.session_state["activities_loaded"] = True
    st.session_state.pop("activities_notice", None)
    st.session_state.pop("rio_strava_notice", None)
    local = st.session_state.get("rio_local")
    copied = dict(local) if isinstance(local, dict) else {}
    copied["name"] = TEST_NAME
    copied["preferred"] = ""
    st.session_state["rio_local"] = copied


def restore_admin_season() -> None:
    """Put back the season captured before the test view."""
    backup = st.session_state.pop("rio_admin_season_backup", None)
    st.session_state.pop("rio_test_preview", None)
    st.session_state.pop("rio_test_bundle", None)
    if not isinstance(backup, dict):
        return
    for key in backup.get("missing") or []:
        st.session_state.pop(key, None)
    present = backup.get("present")
    if isinstance(present, dict):
        for key, value in present.items():
            st.session_state[key] = deepcopy(value)


def drop_preview() -> None:
    """Leave the test view and drop its navigation flags."""
    restore_admin_season()
    for key in ("rio_test_go", "rio_test_go_admin"):
        st.session_state.pop(key, None)


def _load() -> None:
    directory, strava, service_key, caller_id, caller_email = _tools()
    try:
        load_test_season(
            directory,
            strava,
            service_key,
            caller_id=caller_id,
            caller_email=caller_email,
        )
    except TestSeasonError as exc:
        st.session_state["rio_test_error"] = str(exc)
        st.rerun()
    st.session_state.pop("rio_admin_rows", None)
    st.session_state["rio_test_note"] = "TEST Athlete is loaded."
    st.rerun()


def _delete(confirm: bool) -> None:
    if not confirm:
        st.session_state["rio_test_error"] = "Confirm the delete first."
        st.rerun()
    directory, strava, service_key, caller_id, caller_email = _tools()
    try:
        removed = delete_test_season(
            directory,
            strava,
            service_key,
            caller_id=caller_id,
            caller_email=caller_email,
        )
    except TestSeasonError as exc:
        st.session_state["rio_test_error"] = str(exc)
        st.rerun()
    st.session_state.pop("rio_admin_rows", None)
    if removed:
        st.session_state["rio_test_note"] = "TEST Athlete was removed."
    else:
        st.session_state["rio_test_note"] = "TEST Athlete is already gone."
    st.rerun()


def _arm(kind: str) -> None:
    directory, strava, service_key, _caller_id, _caller_email = _tools()
    bundle = read_test_bundle(directory, strava, service_key)
    if bundle is None:
        st.session_state["rio_test_error"] = "Load the test season first."
        st.rerun()
    if "rio_admin_season_backup" not in st.session_state:
        st.session_state["rio_admin_season_backup"] = _snapshot()
    st.session_state["rio_test_bundle"] = bundle
    st.session_state["rio_test_preview"] = kind
    st.session_state["rio_test_go"] = kind
    st.rerun()


def _tools():
    settings = cloud_settings() or {}
    return (
        current_directory(),
        current_strava_store(),
        str(settings.get("service_key") or ""),
        st.session_state.get("rio_cloud_user_id"),
        st.session_state.get("rio_account"),
    )


def _snapshot() -> dict:
    present = {}
    missing = []
    for key in _KEYS:
        if key in st.session_state:
            present[key] = deepcopy(st.session_state[key])
        else:
            missing.append(key)
    return {"present": present, "missing": missing}
