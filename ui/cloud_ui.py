# cloud_ui.py — sign in, Google, reset, and the account screens.

"""Shown when the project settings are present. The local form stays for tests.

Nothing here prints a key. The service role key is not read on these screens.
"""

from __future__ import annotations

import time

import streamlit as st

from ui.cloud_config import app_url, cloud_configured, cloud_settings
from ui.cloud_session import (
    cookie_max_age,
    hosted_sid,
    pack_cookie,
    plan_has_sessions,
    season_digest,
    unpack_cookie,
)
from ui.cloud_store import (
    ACCOUNTS_UNAVAILABLE,
    SIGNUP_CONFIRM,
    CloudAuthError,
    current_directory,
)


def render_cloud_auth(backdrop, notice, hero) -> None:
    """Email, Google, forgot password, or the reset page."""
    _consume_callback()
    if st.session_state.get("rio_cloud_reset") is True:
        _render_reset(backdrop, notice, hero)
        return
    if st.session_state.get("rio_auth_screen") == "confirm":
        _render_confirm(backdrop, notice, hero)
        return
    if st.session_state.get("rio_auth_screen") == "create":
        _render_sign_up(backdrop, notice, hero)
        return
    if st.session_state.get("rio_auth_screen") == "forgot":
        _render_forgot(backdrop, notice, hero)
        return
    _render_sign_in(backdrop, notice, hero)


def open_cloud_session(session: dict, *, bundle: dict | None = None, remember: bool = True) -> None:
    """Keep this sign-in in the page session. The service key is not included."""
    st.session_state["rio_account"] = session["email"]
    st.session_state["rio_account_secret"] = "cloud"
    st.session_state["rio_cloud_user_id"] = session["user_id"]
    st.session_state["rio_cloud_access"] = session["access_token"]
    st.session_state["rio_cloud_refresh"] = session.get("refresh_token") or ""
    st.session_state["rio_cloud_name"] = session.get("display_name") or ""
    st.session_state["rio_cloud_role"] = session.get("role") or "athlete"
    st.session_state["rio_cloud_profile"] = {
        "id": session["user_id"],
        "email": session["email"],
        "display_name": session.get("display_name") or "",
        "role": session.get("role") or "athlete",
    }
    st.session_state["rio_session_token"] = "cloud." + session["access_token"]
    st.session_state["rio_enter"] = True
    st.session_state.pop("rio_auth_screen", None)
    if remember:
        issued = int(session.get("issued_at") or time.time())
        _publish_cookie(session, issued)
    if st.session_state.get("rio_cloud_loaded") is not True:
        if bundle is None:
            _load_saved_season(session["access_token"])
        else:
            _apply_bundle(bundle)
        st.session_state["rio_cloud_loaded"] = True
    _sync_admin_role_once()


def restore_hosted_cookie(raw: str) -> bool:
    """Open the cookie session. An access token that expired is refreshed once.

    An opaque id is looked up on the server. A legacy JSON cookie still opens,
    then the next write stores only the id.
    """
    if hosted_sid(raw):
        directory = current_directory()
        if directory is None:
            return False
        try:
            record = directory.load_hosted_session(raw)
        except CloudAuthError:
            return False
        if not isinstance(record, dict):
            return False
        st.session_state["rio_hosted_sid"] = raw
        parsed = {
            "access_token": str(record.get("access_token") or ""),
            "refresh_token": str(record.get("refresh_token") or ""),
            "user_id": str(record.get("user_id") or ""),
            "email": str(record.get("email") or ""),
            "display_name": str(record.get("display_name") or ""),
            "issued_at": record.get("issued_at") or int(time.time()),
        }
        return _restore_parsed(parsed, sid=raw)
    parsed = unpack_cookie(raw)
    if parsed is None:
        return False
    return _restore_parsed(parsed, sid=None)


def _restore_parsed(parsed: dict, *, sid: str | None) -> bool:
    directory = current_directory()
    if directory is None:
        return False
    access = parsed["access_token"]
    refresh = parsed["refresh_token"]
    email = parsed["email"]
    name = parsed["display_name"]
    user_id = parsed["user_id"]
    issued = parsed["issued_at"]
    if isinstance(issued, str) and issued.isdigit():
        issued = int(issued)
    if not isinstance(issued, int):
        issued = int(time.time())
    bundle = None
    try:
        bundle = directory.load_bundle(access)
    except CloudAuthError:
        try:
            refreshed = directory.refresh_session(refresh)
        except CloudAuthError:
            return False
        access = refreshed["access_token"]
        refresh = refreshed.get("refresh_token") or refresh
        email = refreshed.get("email") or email
        name = refreshed.get("display_name") or name
        user_id = refreshed.get("user_id") or user_id
        _store_refreshed(sid, access, refresh, user_id, email, name, issued)
        try:
            bundle = directory.load_bundle(access)
        except CloudAuthError:
            bundle = None
    profile = bundle.get("profile") if isinstance(bundle, dict) else {}
    if not isinstance(profile, dict):
        profile = {}
    auth_email = _confirmed_email(directory, access, email)
    open_cloud_session(
        {
            "email": auth_email,
            "user_id": user_id,
            "access_token": access,
            "refresh_token": refresh,
            "display_name": profile.get("display_name") or name,
            "role": profile.get("role") or "athlete",
            "issued_at": issued,
        },
        bundle=bundle,
        remember=sid is None,
    )
    if isinstance(sid, str):
        st.session_state["rio_hosted_sid"] = sid
    return True


def restore_cloud_token(stored: str) -> bool:
    """Open a hosted session saved in this browser. A local token is ignored."""
    if not stored.startswith("cloud."):
        return False
    token = stored[6:]
    directory = current_directory()
    if directory is None or not token:
        return False
    try:
        bundle = directory.load_bundle(token)
    except CloudAuthError:
        return False
    profile = bundle.get("profile") or {}
    open_cloud_session(
        {
            "email": profile.get("email") or "",
            "user_id": profile.get("id") or "",
            "access_token": token,
            "refresh_token": "",
            "display_name": profile.get("display_name") or "",
        }
    )
    return True


def cloud_sign_out() -> None:
    token = st.session_state.get("rio_cloud_access")
    sid = st.session_state.get("rio_hosted_sid")
    directory = current_directory()
    if directory is not None and isinstance(token, str):
        try:
            directory.sign_out(token)
        except CloudAuthError:
            pass
    if directory is not None and hosted_sid(sid):
        try:
            directory.drop_hosted_session(sid)
        except CloudAuthError:
            pass
    for key in (
        "rio_cloud_user_id",
        "rio_cloud_access",
        "rio_cloud_refresh",
        "rio_cloud_name",
        "rio_cloud_reset",
        "rio_cloud_profile",
        "rio_cloud_role",
        "rio_cloud_loaded",
        "rio_cloud_saved_hash",
        "rio_intro_seen",
        "rio_intro_force",
        "rio_role_synced",
        "rio_cookie_write",
        "rio_cookie_max_age",
        "rio_hosted_sid",
        "rio_google_url",
        "rio_admin_rows",
        "rio_strava_token",
        "rio_strava_synced",
        "rio_strava_checked",
        "rio_strava_runs",
        "rio_strava_state",
        "rio_strava_nonce",
        "rio_strava_notice",
    ):
        st.session_state.pop(key, None)


def persist_cloud_season() -> None:
    """Write the season already in this session onto the signed-in user."""
    if st.session_state.get("rio_test_preview"):
        return
    token = st.session_state.get("rio_cloud_access")
    directory = current_directory()
    inputs = st.session_state.get("season_inputs")
    plan = st.session_state.get("season_plan")
    if directory is None or not isinstance(token, str) or not isinstance(plan, dict):
        return
    if not isinstance(inputs, (list, tuple)) or len(inputs) != 4:
        return
    goal = {
        "event": "800m",
        "current_mark": str(inputs[0]),
        "goal_time": str(inputs[2]),
        "goal_date": str(inputs[3]),
    }
    actuals = st.session_state.get("season_actuals")
    marks = st.session_state.get("season_marks") or {}
    digest = season_digest(inputs, plan, marks, actuals if isinstance(actuals, dict) else {})
    if digest == st.session_state.get("rio_cloud_saved_hash"):
        return
    try:
        directory.save_bundle(
            token,
            {
                "goal": goal,
                "plans": [
                    {
                        "current_time": str(inputs[0]),
                        "start_date": str(inputs[1]),
                        "goal_time": str(inputs[2]),
                        "goal_date": str(inputs[3]),
                        "plan": plan,
                        "marks": marks,
                        "actuals": actuals if isinstance(actuals, dict) else {},
                    }
                ],
                "profile": {"display_name": st.session_state.get("rio_cloud_name") or ""},
            },
        )
    except CloudAuthError:
        return
    st.session_state["rio_cloud_saved_hash"] = digest


def delete_signed_in_account() -> None:
    token = st.session_state.get("rio_cloud_access")
    directory = current_directory()
    settings = cloud_settings() or {}
    if directory is None or not isinstance(token, str):
        raise CloudAuthError("Sign in again.")
    directory.delete_user(token, settings.get("service_key") or "")


def admin_account_rows() -> list[dict] | None:
    """Every profile, or None when the server key is missing."""
    directory = current_directory()
    settings = cloud_settings() or {}
    if directory is None:
        return None
    return directory.list_users(settings.get("service_key") or "")


def _sync_admin_role_once() -> None:
    """Admin follows the confirmed auth user, not a profile email the athlete can edit."""
    if st.session_state.get("rio_role_synced") is True:
        return
    st.session_state["rio_role_synced"] = True
    token = st.session_state.get("rio_cloud_access")
    directory = current_directory()
    user = None
    if directory is not None and isinstance(token, str):
        try:
            user = directory.verified_user(token)
        except CloudAuthError:
            user = None
    email = None
    user_id = st.session_state.get("rio_cloud_user_id")
    if isinstance(user, dict) and user.get("email_confirmed_at"):
        found = user.get("email")
        if isinstance(found, str) and found:
            email = found
            st.session_state["rio_account"] = found
        found_id = user.get("id")
        if isinstance(found_id, str) and found_id:
            user_id = found_id
            st.session_state["rio_cloud_user_id"] = found_id
    if not isinstance(user_id, str):
        return
    from ui.access import viewer_is_admin

    if not viewer_is_admin(email):
        return
    settings = cloud_settings() or {}
    service_key = settings.get("service_key") or ""
    directory = current_directory()
    if directory is None or not service_key:
        return
    try:
        directory.set_role(user_id, "admin", service_key)
    except CloudAuthError:
        return
    st.session_state["rio_cloud_role"] = "admin"
    profile = st.session_state.get("rio_cloud_profile")
    if isinstance(profile, dict):
        profile["role"] = "admin"
        st.session_state["rio_cloud_profile"] = profile


def _apply_bundle(bundle: dict) -> None:
    profile = bundle.get("profile") if isinstance(bundle.get("profile"), dict) else {}
    if profile:
        st.session_state["rio_cloud_profile"] = {
            "id": profile.get("id") or st.session_state.get("rio_cloud_user_id") or "",
            "email": profile.get("email") or st.session_state.get("rio_account") or "",
            "display_name": profile.get("display_name") or "",
            "role": profile.get("role") or "athlete",
        }
        st.session_state["rio_cloud_role"] = st.session_state["rio_cloud_profile"]["role"]
        if profile.get("display_name"):
            st.session_state["rio_cloud_name"] = profile.get("display_name")
        pace = profile.get("pace_units")
        if pace in ("mi", "km"):
            current = st.session_state.get("rio_settings")
            settings = dict(current) if isinstance(current, dict) else {}
            settings["pace_units"] = pace
            st.session_state["rio_settings"] = settings
            st.session_state["rio_pace_saved"] = pace
        if "intro_seen" in profile:
            st.session_state["rio_intro_seen"] = profile.get("intro_seen") is True
    plans = bundle.get("plans") or []
    remembered = []
    for item in plans:
        if not isinstance(item, dict):
            continue
        remembered.append(
            (
                str(item.get("current_time") or ""),
                str(item.get("start_date") or ""),
                str(item.get("goal_time") or ""),
                str(item.get("goal_date") or ""),
            )
        )
    st.session_state["rio_cloud_season_inputs"] = remembered
    if not plans:
        _remember_digest()
        return
    latest = plans[-1]
    if not isinstance(latest, dict):
        _remember_digest()
        return
    inputs = (
        str(latest.get("current_time") or ""),
        str(latest.get("start_date") or ""),
        str(latest.get("goal_time") or ""),
        str(latest.get("goal_date") or ""),
    )
    plan = latest.get("plan")
    if isinstance(plan, dict) and plan_has_sessions(plan):
        marks = latest.get("marks")
        actuals = latest.get("actuals")
        st.session_state["season_inputs"] = inputs
        st.session_state["season_plan"] = plan
        st.session_state["season_marks"] = marks if isinstance(marks, dict) else {}
        st.session_state["season_actuals"] = actuals if isinstance(actuals, dict) else {}
        st.session_state["rio_store_loaded"] = True
    _remember_digest()


def _remember_digest() -> None:
    st.session_state["rio_cloud_saved_hash"] = season_digest(
        st.session_state.get("season_inputs"),
        st.session_state.get("season_plan"),
        st.session_state.get("season_marks"),
        st.session_state.get("season_actuals"),
    )


def _load_saved_season(token: str) -> None:
    directory = current_directory()
    if directory is None:
        return
    try:
        bundle = directory.load_bundle(token)
    except CloudAuthError:
        return
    _apply_bundle(bundle)


def _consume_callback() -> None:
    params = st.query_params
    code = params.get("code")
    if isinstance(code, str) and code and st.session_state.get("rio_cloud_user_id") is None:
        directory = current_directory()
        if directory is None:
            return
        try:
            session = directory.exchange_code(code)
        except CloudAuthError as exc:
            st.session_state["rio_login_error"] = str(exc)
            return
        open_cloud_session(session)
        st.query_params.clear()
        st.rerun()
    if params.get("reset") == "password" or params.get("type") == "recovery":
        st.session_state["rio_cloud_reset"] = True


def _render_sign_in(backdrop, notice, hero) -> None:
    backdrop()
    with st.container(key="rio-auth-card"):
        st.markdown(
            hero("Log in", "RIO", "Use your email and password."),
            unsafe_allow_html=True,
        )
        notice()
        with st.form("rio-cloud-login", border=False):
            email = st.text_input("Email", key="rio_cloud_email", autocomplete="email")
            password = st.text_input(
                "Password",
                type="password",
                key="rio_cloud_password",
                autocomplete="current-password",
            )
            submitted = st.form_submit_button("Log in", type="primary", width="stretch")
        _google_button("rio-google")
        forgot = st.button("Forgot password?", key="rio-forgot", type="tertiary")
        create = st.button("Create account", key="rio-open-create", width="stretch")
    if forgot:
        st.session_state["rio_auth_screen"] = "forgot"
        st.rerun()
    if create:
        st.session_state["rio_auth_screen"] = "create"
        st.rerun()
    if not submitted:
        return
    directory = _directory_or_notice()
    if directory is None:
        return
    try:
        session = directory.sign_in(email, password)
    except CloudAuthError as exc:
        st.session_state["rio_login_error"] = str(exc)
        st.rerun()
    open_cloud_session(session)
    st.rerun()


def _render_sign_up(backdrop, notice, hero) -> None:
    backdrop()
    with st.container(key="rio-auth-card"):
        st.markdown(hero("Create account", "RIO"), unsafe_allow_html=True)
        notice()
        with st.form("rio-cloud-create", border=False):
            name = st.text_input("Name", key="rio_cloud_name_input", autocomplete="name")
            email = st.text_input("Email", key="rio_cloud_create_email", autocomplete="email")
            password = st.text_input(
                "Password",
                type="password",
                key="rio_cloud_create_password",
                autocomplete="new-password",
            )
            submitted = st.form_submit_button("Create account", type="primary", width="stretch")
        _google_button("rio-google-create")
        back = st.button("Back to log in", key="rio-back-login", width="stretch")
    if back:
        st.session_state["rio_auth_screen"] = "login"
        st.rerun()
    if not submitted:
        return
    directory = _directory_or_notice()
    if directory is None:
        return
    try:
        session = directory.sign_up(email, password, name)
    except CloudAuthError as exc:
        st.session_state["rio_login_error"] = str(exc)
        if str(exc) == SIGNUP_CONFIRM:
            st.session_state["rio_auth_screen"] = "confirm"
        st.rerun()
    open_cloud_session(session)
    st.rerun()


def _render_confirm(backdrop, notice, hero) -> None:
    """Shown when the project asks the athlete to confirm the address first."""
    backdrop()
    with st.container(key="rio-auth-card"):
        st.markdown(
            hero("Check your inbox", "RIO", "Confirm your email, then log in."),
            unsafe_allow_html=True,
        )
        notice()
        st.markdown(SIGNUP_CONFIRM)
        back = st.button("Back to log in", key="rio-confirm-back", width="stretch")
    if back:
        st.session_state["rio_auth_screen"] = "login"
        st.rerun()


def _render_forgot(backdrop, notice, hero) -> None:
    backdrop()
    with st.container(key="rio-auth-card"):
        st.markdown(
            hero("Forgot password", "RIO", "We will email you a reset link."),
            unsafe_allow_html=True,
        )
        notice()
        with st.form("rio-cloud-forgot", border=False):
            email = st.text_input("Email", key="rio_cloud_forgot_email", autocomplete="email")
            submitted = st.form_submit_button("Send reset email", type="primary", width="stretch")
        back = st.button("Back to log in", key="rio-forgot-back", width="stretch")
    if back:
        st.session_state["rio_auth_screen"] = "login"
        st.rerun()
    if not submitted:
        return
    directory = _directory_or_notice()
    if directory is None:
        return
    try:
        directory.request_reset(email)
    except CloudAuthError as exc:
        st.session_state["rio_login_error"] = str(exc)
        st.rerun()
    st.session_state["rio_login_error"] = "Check your email for the reset link."
    st.session_state["rio_auth_screen"] = "login"
    st.rerun()


def _render_reset(backdrop, notice, hero) -> None:
    backdrop()
    with st.container(key="rio-auth-card"):
        st.markdown(hero("New password", "RIO"), unsafe_allow_html=True)
        notice()
        with st.form("rio-cloud-reset", border=False):
            password = st.text_input(
                "New password",
                type="password",
                key="rio_cloud_new_password",
                autocomplete="new-password",
            )
            submitted = st.form_submit_button("Save password", type="primary", width="stretch")
    if not submitted:
        return
    directory = _directory_or_notice()
    token = st.query_params.get("token") or st.query_params.get("code") or ""
    if directory is None:
        return
    try:
        directory.reset_password(token, password)
    except CloudAuthError as exc:
        st.session_state["rio_login_error"] = str(exc)
        st.rerun()
    st.session_state["rio_cloud_reset"] = False
    st.session_state["rio_auth_screen"] = "login"
    st.session_state["rio_login_error"] = "Password updated. Log in with the new one."
    st.query_params.clear()
    st.rerun()


def _publish_cookie(session: dict, issued: int) -> None:
    """Prefer an opaque id. The legacy JSON cookie is the fallback before the table exists.

    The browser bridge cannot set HttpOnly. The id is still readable to script,
    but it is not a Supabase token. localStorage does not get a copy of the token.
    """
    directory = current_directory()
    sid = None
    if directory is not None:
        try:
            sid = directory.save_hosted_session(
                {
                    "access_token": session["access_token"],
                    "refresh_token": session.get("refresh_token") or "",
                    "user_id": session["user_id"],
                    "email": session.get("email") or "",
                    "display_name": session.get("display_name") or "",
                    "issued_at": issued,
                }
            )
        except CloudAuthError:
            sid = None
    if hosted_sid(sid):
        st.session_state["rio_hosted_sid"] = sid
        st.session_state["rio_cookie_write"] = sid
    else:
        st.session_state["rio_cookie_write"] = pack_cookie(
            session["access_token"],
            session.get("refresh_token") or "",
            session["user_id"],
            session.get("email") or "",
            session.get("display_name") or "",
            issued,
        )
    st.session_state["rio_cookie_max_age"] = cookie_max_age(issued)
    # Empty on purpose: the hosted access token stays in this server session.
    st.session_state["rio_session_write"] = ""


def _store_refreshed(sid, access, refresh, user_id, email, name, issued) -> None:
    directory = current_directory()
    body = {
        "access_token": access,
        "refresh_token": refresh,
        "user_id": user_id,
        "email": email,
        "display_name": name,
        "issued_at": issued,
    }
    if hosted_sid(sid) and directory is not None:
        try:
            directory.update_hosted_session(sid, body)
        except CloudAuthError:
            pass
        st.session_state["rio_hosted_sid"] = sid
        return
    st.session_state["rio_cookie_write"] = pack_cookie(access, refresh, user_id, email, name, issued)
    st.session_state["rio_cookie_max_age"] = cookie_max_age(issued)
    st.session_state["rio_session_write"] = ""


def _confirmed_email(directory, access: str, fallback: str) -> str:
    """The auth user's email when it is confirmed. A profile email is ignored."""
    try:
        user = directory.verified_user(access)
    except CloudAuthError:
        user = None
    if isinstance(user, dict) and user.get("email_confirmed_at"):
        found = user.get("email")
        if isinstance(found, str) and found:
            return found
    return fallback


def _directory_or_notice():
    """The account directory, or a visible message when it is missing."""
    directory = current_directory()
    if directory is None:
        st.session_state["rio_login_error"] = ACCOUNTS_UNAVAILABLE
        st.rerun()
    return directory


def _google_button(key: str) -> None:
    """A link to the provider. A failed start leaves the email form in place."""
    directory = current_directory()
    if directory is None or not cloud_configured():
        return
    url = st.session_state.get("rio_google_url")
    if not isinstance(url, str) or not url:
        try:
            url = directory.google_url(app_url() + "/")
        except CloudAuthError:
            return
        st.session_state["rio_google_url"] = url
    st.link_button("Continue with Google", url, width="stretch", key=key)
