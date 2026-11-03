# cloud_config.py — where account settings come from. Values are never printed.

"""RIO_SUPABASE_URL, RIO_SUPABASE_ANON_KEY, RIO_SUPABASE_SERVICE_ROLE_KEY, and RIO_APP_URL.

The environment wins. Streamlit secrets are used when a name is empty.
A missing URL or anon key means accounts are not set up. The service role
key is optional and is only for admin work on the server.
"""

from __future__ import annotations

import os

URL = "RIO_SUPABASE_URL"
ANON = "RIO_SUPABASE_ANON_KEY"
SERVICE = "RIO_SUPABASE_SERVICE_ROLE_KEY"
APP_URL = "RIO_APP_URL"
LOCAL_APP = "http://localhost:8501"
HOSTED_APP = "https://riotraining.streamlit.app"


def _clean(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _from_secrets(name: str) -> str:
    try:
        import streamlit as st

        found = st.secrets.get(name, "")
    except Exception:
        return ""
    return _clean(found)


def read_setting(name: str) -> str:
    """One setting. The environment wins over Streamlit secrets."""
    found = _clean(os.environ.get(name, ""))
    if found:
        return found
    return _from_secrets(name)


def app_url() -> str:
    """Redirect base. Local default is the Streamlit port. The hosted app is the other one."""
    found = read_setting(APP_URL)
    return found.rstrip("/") or LOCAL_APP


def cloud_settings() -> dict | None:
    """URL and anon key, or None when either is missing.

    The service role key may be blank. It is not required to sign in.
    """
    url = read_setting(URL)
    anon = read_setting(ANON)
    if not url or not anon:
        return None
    return {
        "url": url,
        "anon_key": anon,
        "service_key": read_setting(SERVICE),
        "app_url": app_url(),
    }


def cloud_configured() -> bool:
    return cloud_settings() is not None


def setup_notice_html() -> str:
    """The login notice when accounts are not connected. No setting names."""
    return (
        '<div class="rio-card rio-card-tight">'
        '<p class="rio-mark-label">Accounts aren\'t set up yet</p>'
        '<p class="rio-note">Sign-in will open here after accounts are connected.</p>'
        "</div>"
    )
