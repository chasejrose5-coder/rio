# moved.py — the screen in front of the old Streamlit app.

"""RIO has a new home. This page does not sign in, load a plan, or call Strava.

streamlit_app.py draws this and then stops. The old screens are still in
that file. They run again if those two lines are removed.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from ui.theme import (
    ACCENT,
    BUTTON,
    BUTTON_HOVER,
    DISPLAY,
    FONT,
    INK,
    MUTED,
    PAPER,
    TEXT,
    focus_css,
    font_css,
)

NEW_HOME = "https://rio-one-mocha.vercel.app"
HEADLINE = "RIO has a new home"
BUTTON_LABEL = "Open the new RIO"
FASTER = "The new site is faster, with more features."
ACCOUNT = "Your account is already there. Sign in with the same email and password."
OWNED = "Runner Intelligence Owned"


def moved_html() -> str:
    """The wordmark, the note, and a same-tab link. No new window."""
    url = escape(NEW_HOME, quote=True)
    return f"""
<section class="rio-moved">
  <p class="rio-moved-mark">RIO</p>
  <p class="rio-moved-owned">{escape(OWNED)}</p>
  <h1>{escape(HEADLINE)}</h1>
  <p class="rio-moved-lead">{escape(FASTER)}</p>
  <p class="rio-moved-account">{escape(ACCOUNT)}</p>
  <p class="rio-moved-action">
    <a class="rio-moved-go" href="{url}" target="_self">{escape(BUTTON_LABEL)}</a>
  </p>
  <p class="rio-moved-url"><a href="{url}" target="_self">{escape(NEW_HOME)}</a></p>
</section>
"""


def moved_css() -> str:
    """Paper page, orange wordmark, and the darker orange behind white type."""
    return f"""
<style>
{font_css()}
html, body, .stApp {{
  background: {PAPER} !important;
  background-color: {PAPER} !important;
  color: {TEXT} !important;
}}
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stHeaderActionElements"],
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"],
#MainMenu,
footer,
header {{
  display: none !important;
  height: 0 !important;
}}
[data-testid="stMainBlockContainer"],
.block-container {{
  max-width: 46rem !important;
  margin: 0 !important;
  padding: 11vh 7vw 4.5rem !important;
  box-sizing: border-box !important;
}}
.rio-moved,
.rio-moved p,
.rio-moved a {{
  font-family: {FONT} !important;
}}
.rio-moved {{
  margin: 0;
  max-width: 38rem;
  text-align: left;
  color: {TEXT};
}}
.rio-moved .rio-moved-mark {{
  margin: 0 0 0.35rem !important;
  color: {ACCENT} !important;
  font-family: {DISPLAY} !important;
  font-weight: 800 !important;
  font-size: clamp(72px, 16vw, 148px) !important;
  letter-spacing: -0.065em !important;
  line-height: 0.78 !important;
}}
.rio-moved .rio-moved-owned {{
  margin: 0 0 1.6rem !important;
  color: {MUTED} !important;
  font-family: {DISPLAY} !important;
  font-weight: 700 !important;
  font-size: clamp(0.95rem, 1.6vw, 1.12rem) !important;
  letter-spacing: 0.08em !important;
  line-height: 1.3 !important;
}}
.rio-moved h1 {{
  margin: 0 0 0.85rem !important;
  color: {TEXT} !important;
  font-family: {DISPLAY} !important;
  max-width: 12ch;
  font-size: clamp(36px, 5.2vw, 64px) !important;
  font-weight: 800 !important;
  letter-spacing: -0.045em !important;
  line-height: 0.94 !important;
}}
.rio-moved-lead {{
  margin: 0 0 0.7rem !important;
  color: {TEXT} !important;
  font-size: clamp(1.15rem, 2vw, 1.4rem) !important;
  font-weight: 500 !important;
  line-height: 1.4 !important;
}}
.rio-moved-account {{
  margin: 0 0 1.7rem !important;
  max-width: 34rem;
  color: {TEXT} !important;
  font-size: 1.05rem !important;
  font-weight: 400 !important;
  line-height: 1.5 !important;
}}
.rio-moved-action {{
  margin: 0 0 0.9rem !important;
}}
a.rio-moved-go,
a.rio-moved-go:hover,
a.rio-moved-go:focus,
a.rio-moved-go:visited,
a.rio-moved-go:active {{
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-sizing: border-box !important;
  min-height: 3.4rem !important;
  padding: 0.9rem 1.7rem !important;
  background: {BUTTON} !important;
  background-color: {BUTTON} !important;
  border: 1px solid {BUTTON} !important;
  border-radius: 999px !important;
  color: {INK} !important;
  font-size: 1.15rem !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  line-height: 1.2 !important;
  text-decoration: none !important;
  box-shadow: none !important;
}}
a.rio-moved-go:hover {{
  background: {BUTTON_HOVER} !important;
  background-color: {BUTTON_HOVER} !important;
  border-color: {BUTTON_HOVER} !important;
  color: {INK} !important;
}}
.rio-moved-url {{
  margin: 0 !important;
  font-size: 0.95rem !important;
  line-height: 1.4 !important;
}}
.rio-moved-url a,
.rio-moved-url a:visited {{
  color: {MUTED} !important;
  font-weight: 500 !important;
  text-decoration: underline !important;
  text-underline-offset: 0.18em !important;
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"],
  .block-container {{
    padding: 4.25rem 1.25rem 3rem !important;
  }}
  .rio-moved h1 {{
    max-width: 11ch;
  }}
  a.rio-moved-go {{
    width: 100% !important;
  }}
}}
{focus_css()}
</style>
"""


def render_moved() -> None:
    """Draw the moved screen. The caller stops the script after this."""
    st.markdown(moved_css(), unsafe_allow_html=True)
    st.html(moved_html())
