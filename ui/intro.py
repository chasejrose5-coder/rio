# intro.py — three steps after a new account's first sign-in.

"""A short guide. Skip and Done both leave it. Settings can open it again.

The flag lives on the auth user, next to pace units. This module does not
read a plan, call a model, or open the network.
"""

from __future__ import annotations

import streamlit as st

from ui.theme import ACCENT, DISPLAY, FONT, HAIRLINE, MUTED, SURFACE, TEXT

STEPS = (
    (
        "Set your goal",
        "On Start, enter your times and choose Generate Season Plan.",
    ),
    (
        "Connect Strava",
        "In Settings, connect Strava so your runs show up.",
    ),
    (
        "Check your plan",
        "Open Plan each day and mark how it went.",
    ),
)


def guide_html() -> str:
    """The three steps. Buttons are drawn beside this card."""
    steps = []
    for index, (title, body) in enumerate(STEPS, start=1):
        steps.append(
            '<li class="rio-intro-step">'
            f'<span class="rio-intro-num">{index}</span>'
            '<div>'
            f'<p class="rio-intro-title">{title}</p>'
            f'<p class="rio-intro-body">{body}</p>'
            "</div></li>"
        )
    return (
        '<section class="rio-intro">'
        '<p class="rio-intro-kicker">Welcome</p>'
        "<h1>Start here</h1>"
        '<ol class="rio-intro-steps">'
        + "".join(steps)
        + "</ol></section>"
    )


def intro_css() -> str:
    return f"""
<style>
.rio-intro {{
  max-width: 36rem;
  margin: 0.85rem 0 0.4rem;
  padding: 1.15rem 1.25rem 0.35rem;
  background: {SURFACE};
  border: 1px solid {HAIRLINE};
  border-radius: 18px;
  color: {TEXT};
  font-family: {FONT};
}}
.rio-intro-kicker {{
  margin: 0 0 0.25rem !important;
  color: {ACCENT} !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.16em !important;
  text-transform: uppercase !important;
}}
.rio-intro h1 {{
  margin: 0 0 0.75rem !important;
  color: {TEXT} !important;
  font-family: {DISPLAY} !important;
  font-size: 1.85rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.04em !important;
  line-height: 1.05 !important;
}}
.rio-intro-steps {{
  list-style: none;
  margin: 0;
  padding: 0;
}}
.rio-intro-step {{
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  padding: 0.65rem 0;
  border-top: 1px solid {HAIRLINE};
}}
.rio-intro-num {{
  flex: 0 0 auto;
  width: 1.6rem;
  height: 1.6rem;
  border-radius: 999px;
  background: {ACCENT};
  color: #fff;
  font-family: {DISPLAY};
  font-size: 0.85rem;
  font-weight: 800;
  line-height: 1.6rem;
  text-align: center;
}}
.rio-intro-title {{
  margin: 0 !important;
  color: {TEXT} !important;
  font-family: {DISPLAY} !important;
  font-size: 1.02rem !important;
  font-weight: 700 !important;
}}
.rio-intro-body {{
  margin: 0.15rem 0 0 !important;
  color: {MUTED} !important;
  font-size: 0.95rem !important;
  line-height: 1.4 !important;
}}
[class*="st-key-rio-intro-actions"] {{
  max-width: 36rem !important;
  margin-top: 0.65rem !important;
}}
</style>
"""


def render_intro() -> str | None:
    """Draw the guide. 'skip' or 'done' when that button was pressed."""
    st.markdown(intro_css() + guide_html(), unsafe_allow_html=True)
    with st.container(key="rio-intro-actions"):
        skip, done = st.columns(2)
        with skip:
            if st.button("Skip", key="rio-intro-skip", width="stretch"):
                return "skip"
        with done:
            if st.button("Done", key="rio-intro-done", type="primary", width="stretch"):
                return "done"
    return None
