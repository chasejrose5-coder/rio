# easy_pace.py — the pace easy and long runs actually use.

"""Minutes and seconds, and per mile or per kilometer.

The screen is the first one after an account exists when this pace is
not saved yet. Profile uses the same form later. Quality workouts are
not collected here. No model. No spend. No scores.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from engines.pace import canonical_easy_pace
from ui.theme import ACCENT, DISPLAY, FONT, HAIRLINE, MUTED, SURFACE, TEXT


def stored_easy_pace() -> tuple[str, str] | None:
    """The pace on this session, then the local profile, then the cloud profile."""
    candidates = [
        (st.session_state.get("rio_easy_pace"), st.session_state.get("rio_easy_pace_unit")),
    ]
    local = st.session_state.get("rio_local")
    if isinstance(local, dict):
        candidates.append((local.get("easy_pace"), local.get("easy_pace_unit")))
    cloud = st.session_state.get("rio_cloud_profile")
    if isinstance(cloud, dict):
        candidates.append((cloud.get("easy_pace"), cloud.get("easy_pace_unit")))
    for pace, unit in candidates:
        text = canonical_easy_pace(pace)
        if text and unit in ("mi", "km"):
            return text, unit
    return None


def pace_kwargs() -> dict:
    """Pass these to workout times. An empty pace means it is not saved yet."""
    found = stored_easy_pace()
    if found is None:
        return {"easy_pace": "", "easy_unit": "mi"}
    return {"easy_pace": found[0], "easy_unit": found[1]}


def render_easy_pace(*, current: str = "") -> tuple[str, str] | None:
    """Draw the form. The saved pace and unit when Save was pressed with a real pace."""
    found = stored_easy_pace()
    if "easy-pace" not in st.session_state and found is not None:
        st.session_state["easy-pace"] = found[0]
    if "easy-pace-unit" not in st.session_state:
        st.session_state["easy-pace-unit"] = found[1] if found is not None else "mi"
    st.markdown(_css() + _card(current), unsafe_allow_html=True)
    notice = st.session_state.pop("rio_easy_pace_error", None)
    if isinstance(notice, str) and notice.strip():
        st.markdown(
            f'<p class="rio-error">{escape(notice.strip())}</p>',
            unsafe_allow_html=True,
        )
    with st.form("rio-easy-pace", border=False):
        pace = st.text_input(
            "Easy pace",
            placeholder="7:25",
            key="easy-pace",
        )
        st.markdown(
            '<p class="rio-easy-hint">Minutes and seconds, like 7:25.</p>',
            unsafe_allow_html=True,
        )
        unit = st.radio(
            "Unit",
            ["mi", "km"],
            format_func=lambda item: "per mile" if item == "mi" else "per kilometer",
            horizontal=True,
            key="easy-pace-unit",
        )
        submitted = st.form_submit_button("Save easy pace", type="primary", width="stretch")
    if not submitted:
        return None
    text = canonical_easy_pace(pace)
    if text is None or unit not in ("mi", "km"):
        st.session_state["rio_easy_pace_error"] = "Enter a pace like 7:25."
        st.rerun()
    return text, unit


def _card(current: str) -> str:
    shown = ""
    if current:
        shown = f'<p class="rio-easy-now">Saved: {escape(current)}. You can change it here.</p>'
    return (
        '<section class="rio-easy">'
        '<p class="rio-easy-kicker">Start here</p>'
        "<h1>Your easy pace</h1>"
        '<p class="rio-easy-body">Easy and long runs use this pace. '
        "Enter minutes and seconds, like 7:25, and choose per mile or per kilometer. "
        "Quality workouts stay on your 800.</p>"
        f"{shown}"
        "</section>"
    )


def _css() -> str:
    return f"""
<style>
.rio-easy {{
  max-width: 36rem;
  margin: 0.85rem 0 0.4rem;
  padding: 1.15rem 1.25rem 0.35rem;
  background: {SURFACE};
  border: 1px solid {HAIRLINE};
  border-radius: 18px;
  color: {TEXT};
  font-family: {FONT};
}}
.rio-easy-kicker {{
  margin: 0 0 0.25rem !important;
  color: {ACCENT} !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.16em !important;
  text-transform: uppercase !important;
}}
.rio-easy h1 {{
  margin: 0 0 0.55rem !important;
  color: {TEXT} !important;
  font-family: {DISPLAY} !important;
  font-size: 1.85rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.04em !important;
  line-height: 1.05 !important;
}}
.rio-easy-body, .rio-easy-now, .rio-easy-hint {{
  color: {MUTED} !important;
  font-size: 0.95rem !important;
  line-height: 1.45 !important;
}}
.rio-easy-body {{ margin: 0 0 0.65rem !important; }}
.rio-easy-now {{ margin: 0 0 0.35rem !important; color: {TEXT} !important; }}
.rio-easy-hint {{ margin: -0.35rem 0 0.65rem !important; }}
[class*="st-key-rio-easy"] {{
  max-width: 36rem !important;
}}
</style>
"""
