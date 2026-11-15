# moved.py — the screen in front of the old Streamlit app.

"""RIO has a new home. This page does not sign in, load a plan, or call Strava.

streamlit_app.py draws this and then stops. The old screens are still in
that file. They run again if those two lines are removed.

The address is a link. It opens the live site in a new tab so the click
leaves Streamlit's frame. This page does not redirect there on its own.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from ui.theme import (
    ACCENT,
    BUTTON,
    BUTTON_ACTIVE,
    BUTTON_HOVER,
    BUTTON_RADIUS,
    DISPLAY,
    FONT,
    MUTED,
    PAPER,
    TEXT,
    focus_css,
    font_css,
)

NEW_HOME = "https://www.riorunning.com"
HEADLINE = "RIO has a new home"
FASTER = "The new site is faster, with more features."
ACCOUNT = "Your account is already there. Sign in with the same email and password."
COPY = "Open the new site."
OWNED = "Runner Intelligence Owned"


def moved_html() -> str:
    """The wordmark, the note, and the address as one link."""
    href = escape(NEW_HOME, quote=True)
    return f"""
<section class="rio-moved">
  <p class="rio-moved-mark">RIO</p>
  <p class="rio-moved-owned">{escape(OWNED)}</p>
  <h1>{escape(HEADLINE)}</h1>
  <p class="rio-moved-lead">{escape(FASTER)}</p>
  <p class="rio-moved-account">{escape(ACCOUNT)}</p>
  <p class="rio-moved-copy">{escape(COPY)}</p>
  <a class="rio-moved-url" href="{href}" target="_blank" rel="noopener noreferrer">{escape(NEW_HOME)}</a>
</section>
"""


def moved_css() -> str:
    """Paper page, orange wordmark, and the address as a button."""
    return f"""
<style>
{font_css()}
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {{
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
  background: transparent !important;
}}
[data-testid="stVerticalBlock"],
[data-testid="stVerticalBlockBorderWrapper"] {{
  gap: 0 !important;
}}
[data-testid="stElementContainer"],
[data-testid="element-container"],
[data-testid="stMarkdownContainer"] {{
  margin: 0 !important;
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}}
.rio-moved,
.rio-moved p,
.rio-moved a {{
  font-family: {FONT} !important;
  word-break: normal !important;
  overflow-wrap: normal !important;
  -webkit-user-select: text !important;
  user-select: text !important;
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
  padding: 0 !important;
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
  margin: 0 0 1.35rem !important;
  max-width: 34rem;
  color: {TEXT} !important;
  font-size: 1.05rem !important;
  font-weight: 400 !important;
  line-height: 1.5 !important;
}}
.rio-moved-copy {{
  margin: 0 0 0.85rem !important;
  max-width: 34rem;
  color: {TEXT} !important;
  font-size: 1.05rem !important;
  font-weight: 500 !important;
  line-height: 1.5 !important;
}}
a.rio-moved-url {{
  display: inline-block;
  max-width: 100%;
  box-sizing: border-box;
  margin: 0 !important;
  padding: 0.95rem 1.25rem !important;
  background: {BUTTON} !important;
  background-color: {BUTTON} !important;
  border: 1px solid {BUTTON} !important;
  border-radius: {BUTTON_RADIUS} !important;
  color: #FFFFFF !important;
  font-size: clamp(1.05rem, 2.4vw, 1.35rem) !important;
  font-weight: 600 !important;
  line-height: 1.35 !important;
  letter-spacing: -0.01em;
  text-decoration: none !important;
  overflow-wrap: anywhere !important;
  word-break: break-word !important;
  cursor: pointer !important;
  -webkit-user-select: text !important;
  user-select: text !important;
  -webkit-touch-callout: default !important;
}}
a.rio-moved-url:hover {{
  background: {BUTTON_HOVER} !important;
  background-color: {BUTTON_HOVER} !important;
  border-color: {BUTTON_HOVER} !important;
  color: #FFFFFF !important;
}}
a.rio-moved-url:active {{
  background: {BUTTON_ACTIVE} !important;
  background-color: {BUTTON_ACTIVE} !important;
  border-color: {BUTTON_ACTIVE} !important;
  color: #FFFFFF !important;
}}
a.rio-moved-url::selection {{
  background: #F0C2B4;
  color: {TEXT};
}}
[data-testid="stMarkdownContainer"]:has(.rio-moved),
[data-testid="stHeadingWithActionElements"] {{
  margin: 0 !important;
  padding: 0 !important;
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"],
  .block-container {{
    padding: 4.25rem 1.25rem 3rem !important;
  }}
  .rio-moved h1 {{
    max-width: 11ch;
  }}
  a.rio-moved-url {{
    padding: 0.85rem 0.95rem !important;
    font-size: 1.05rem !important;
  }}
}}
{focus_css()}
</style>
"""


def render_moved() -> None:
    """Draw the moved screen. The caller stops the script after this."""
    st.markdown(moved_css(), unsafe_allow_html=True)
    # anchors=False keeps the markdown heading chrome off the headline.
    # The address is a link in this document. The page does not redirect.
    st.markdown(moved_html(), unsafe_allow_html=True, anchors=False)
