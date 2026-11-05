# probability_ui.py — the Admin stub. Athletes never reach this.

"""One line on Admin. No number is drawn."""

from __future__ import annotations

import streamlit as st

from engines.probability import admin_line, compute_goal_probability


def render_admin_stub() -> None:
    """Store the stub for this Admin view and show that it is not calibrated."""
    st.session_state["rio_goal_stub"] = compute_goal_probability(viewer="admin")
    text = admin_line()
    if not text:
        return
    st.markdown(f'<p class="rio-note">{text}</p>', unsafe_allow_html=True)
