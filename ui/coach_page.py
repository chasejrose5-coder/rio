# coach_page.py — the coach roster and the team box in Settings.

"""Team data is read here, not on every page. A coach cannot edit an athlete.

The service role key is used only when the signed-in email is the admin email.
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from ui.cloud_config import cloud_configured, cloud_settings
from ui.cloud_store import CloudAuthError, current_directory
from ui.coach import change_member_role


def render_coach() -> None:
    from ui.streamlit_app import (
        _account_identity,
        _card,
        _css,
        _esc,
        _label,
        _nav_page,
        _note,
        _page_hero,
        _render_nav,
        _table,
    )

    who = _account_identity()
    email = who[0] if who is not None else ""
    if not _coach_allowed(email):
        home = _nav_page("Home")
        if home is not None:
            st.switch_page(home)
        st.stop()
    st.markdown(_css("Coach"), unsafe_allow_html=True)
    _render_nav("Coach")
    st.markdown(_page_hero("Coach", "RIO", "Your athletes and their season."), unsafe_allow_html=True)
    open_id = st.session_state.get("rio_coach_open")
    if isinstance(open_id, str) and open_id:
        _render_athlete(open_id, email, _card, _label, _note, _esc)
        return
    roster = _roster(email)
    code = str(roster.get("code") or "")
    if code:
        _card(
            _label("Team code"),
            f'<p class="rio-hero-figure">{_esc(code)}</p>',
            _note("Share this code. A new code replaces it."),
        )
        if st.button("New code", key="rio-new-code"):
            _rotate_code()
    elif _coach_allowed(email):
        _card(_label("Team code"), _note("A code appears here for a coach account."))
    athletes = roster.get("athletes") if isinstance(roster.get("athletes"), list) else []
    if not athletes:
        _card(_label("Athletes"), '<p class="rio-empty">No athletes on this team yet.</p>')
        return
    table = [
        {
            "Name": row.get("name") or "—",
            "Goal": row.get("goal_time") or "—",
            "Days": row.get("days") or "—",
            "Phase": row.get("phase") or "—",
            "Status": row.get("status") or "—",
        }
        for row in athletes
        if isinstance(row, dict)
    ]
    _card(_label("Athletes"), _table(table), _note("Read only."))
    for row in athletes:
        if not isinstance(row, dict):
            continue
        athlete_id = str(row.get("id") or "")
        if athlete_id and st.button(f"Open {row.get('name') or 'athlete'}", key=f"rio-open-{athlete_id}"):
            st.session_state["rio_coach_open"] = athlete_id
            st.rerun()


def render_team_settings() -> None:
    """Join or leave. Hidden unless this is a hosted athlete."""
    from ui.streamlit_app import _account_identity, _label

    if not cloud_configured() or not st.session_state.get("rio_cloud_user_id"):
        return
    if st.session_state.get("rio_cloud_role") in ("coach", "admin"):
        return
    who = _account_identity()
    if who is None:
        return
    st.markdown(_label("Team"), unsafe_allow_html=True)
    membership = _membership()
    if membership is not None:
        name = membership.get("coach_name") or "your coach"
        st.markdown(f'<p class="rio-settings-note">You are on {name}\'s team.</p>', unsafe_allow_html=True)
        if st.button("Leave team", key="rio-leave-team"):
            _leave_team()
        return
    code = st.text_input("Team code", key="rio-join-code")
    if st.button("Join team", key="rio-join-team"):
        _join_team(code)


def render_role_controls(rows: list) -> None:
    """Athlete or coach. The signed-in admin is not in the list."""
    from ui.access import viewer_is_admin
    from ui.streamlit_app import _account_identity, _label, _note

    who = _account_identity()
    actor = who[0] if who is not None else ""
    st.markdown(_label("Roles"), unsafe_allow_html=True)
    st.markdown(_note("Athlete or coach. Admin stays the configured email."), unsafe_allow_html=True)
    shown = False
    for row in rows:
        if not isinstance(row, dict):
            continue
        target = str(row.get("email") or "")
        if not target or viewer_is_admin(target) or target == actor:
            continue
        shown = True
        current = row.get("role") if row.get("role") in ("athlete", "coach") else "athlete"
        choice = st.selectbox(
            target,
            ["athlete", "coach"],
            index=0 if current == "athlete" else 1,
            key=f"rio-role-{row.get('id')}",
        )
        if st.button("Save role", key=f"rio-save-role-{row.get('id')}"):
            _save_role(actor, row.get("id"), target, choice)
    if not shown:
        st.markdown('<p class="rio-empty">No other accounts yet.</p>', unsafe_allow_html=True)


def _coach_allowed(email: str) -> bool:
    from ui.access import viewer_is_admin

    if viewer_is_admin(email):
        return True
    return st.session_state.get("rio_cloud_role") == "coach"


def _roster(email: str) -> dict:
    cached = st.session_state.get("rio_coach_roster")
    if isinstance(cached, dict):
        return cached
    directory = current_directory()
    token = st.session_state.get("rio_cloud_access")
    if directory is None or not isinstance(token, str):
        return {"code": "", "athletes": []}
    from ui.access import viewer_is_admin

    service_key = ""
    if viewer_is_admin(email):
        service_key = (cloud_settings() or {}).get("service_key") or ""
    try:
        if st.session_state.get("rio_cloud_role") in ("coach", "admin") or viewer_is_admin(email):
            directory.ensure_team(token)
        data = directory.roster(token, today=date.today(), service_key=service_key)
    except CloudAuthError:
        data = {"code": "", "athletes": []}
    if not isinstance(data, dict):
        data = {"code": "", "athletes": []}
    st.session_state["rio_coach_roster"] = data
    return data


def _rotate_code() -> None:
    directory = current_directory()
    token = st.session_state.get("rio_cloud_access")
    if directory is None or not isinstance(token, str):
        return
    try:
        directory.rotate_code(token)
    except CloudAuthError as exc:
        st.session_state["rio_login_error"] = str(exc)
        return
    st.session_state.pop("rio_coach_roster", None)
    st.session_state.pop("rio_coach_detail", None)
    st.rerun()


def _render_athlete(athlete_id: str, email: str, card, label, note, esc) -> None:
    record = _detail(athlete_id, email)
    if st.button("Back to team", key="rio-coach-back"):
        st.session_state.pop("rio_coach_open", None)
        st.rerun()
    if record is None:
        card(label("Athlete"), '<p class="rio-empty">This athlete is not on your team.</p>')
        return
    plan_row = record.get("plan_row") if isinstance(record.get("plan_row"), dict) else {}
    plan = plan_row.get("plan") if isinstance(plan_row.get("plan"), dict) else {}
    sessions = plan.get("sessions") if isinstance(plan.get("sessions"), list) else []
    actuals = plan_row.get("actuals") if isinstance(plan_row.get("actuals"), dict) else {}
    lines = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        day = str(session.get("date") or "—")
        name = str(session.get("template_id") or "Workout")
        logged = actuals.get(day)
        extra = ""
        if isinstance(logged, dict) and logged.get("numbers"):
            extra = " · " + ", ".join(str(item) for item in logged.get("numbers") or [])
        lines.append(f"<p>{esc(day)} · {esc(name)}{esc(extra)}</p>")
    body = "".join(lines) or '<p class="rio-empty">No season is stored yet.</p>'
    card(
        label(str(record.get("name") or "Athlete")),
        note("Read only. Logged in RIO."),
        body,
    )


def _detail(athlete_id: str, email: str) -> dict | None:
    store = st.session_state.get("rio_coach_detail")
    if not isinstance(store, dict):
        store = {}
        st.session_state["rio_coach_detail"] = store
    if athlete_id in store:
        found = store[athlete_id]
        return found if isinstance(found, dict) else None
    directory = current_directory()
    token = st.session_state.get("rio_cloud_access")
    if directory is None or not isinstance(token, str):
        return None
    from ui.access import viewer_is_admin

    service_key = ""
    if viewer_is_admin(email):
        service_key = (cloud_settings() or {}).get("service_key") or ""
    try:
        record = directory.athlete_record(token, athlete_id, service_key)
    except CloudAuthError:
        record = None
    if isinstance(record, dict):
        store[athlete_id] = record
    return record if isinstance(record, dict) else None


def _membership() -> dict | None:
    cached = st.session_state.get("rio_team_membership")
    if cached == "none":
        return None
    if isinstance(cached, dict):
        return cached
    directory = current_directory()
    token = st.session_state.get("rio_cloud_access")
    if directory is None or not isinstance(token, str):
        return None
    try:
        found = directory.membership(token)
    except CloudAuthError:
        found = None
    st.session_state["rio_team_membership"] = found if isinstance(found, dict) else "none"
    return found if isinstance(found, dict) else None


def _join_team(code: str) -> None:
    directory = current_directory()
    token = st.session_state.get("rio_cloud_access")
    if directory is None or not isinstance(token, str):
        return
    try:
        directory.join_team(token, code)
    except CloudAuthError as exc:
        st.session_state["rio_settings_error"] = str(exc)
        st.rerun()
    st.session_state.pop("rio_team_membership", None)
    st.session_state["rio_settings_note"] = "You joined the team."
    st.rerun()


def _leave_team() -> None:
    directory = current_directory()
    token = st.session_state.get("rio_cloud_access")
    if directory is None or not isinstance(token, str):
        return
    try:
        directory.leave_team(token)
    except CloudAuthError as exc:
        st.session_state["rio_settings_error"] = str(exc)
        st.rerun()
    st.session_state["rio_team_membership"] = "none"
    st.session_state["rio_settings_note"] = "You left the team."
    st.rerun()


def _save_role(actor: str, target_id: object, target_email: str, role: str) -> None:
    directory = current_directory()
    service_key = (cloud_settings() or {}).get("service_key") or ""
    if directory is None:
        return
    try:
        change_member_role(directory, actor, target_id, target_email, role, service_key)
    except CloudAuthError as exc:
        st.session_state["rio_login_error"] = str(exc)
        return
    st.session_state.pop("rio_admin_rows", None)
    st.rerun()

