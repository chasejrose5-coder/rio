# startup.py — the full-screen page before Log in. Once per session.

"""A track photo, a headline, and a placeholder for a personal statement.

Continue leaves this page. The next screen is Log in, unchanged.
A new browser tab is a new session, so this page shows again.
No account, no plan, no model, no score.

Photo by Giant Asparagus on Pexels.
https://www.pexels.com/photo/aerial-view-of-empty-athletic-track-and-field-35678275/
"""

from __future__ import annotations

from functools import lru_cache
from html import escape
from pathlib import Path

import streamlit as st

from ui.theme import (
    CARD_BORDER,
    CARD_FILL,
    CARD_SHADOW,
    FONT,
    LIGHT,
    RADIUS,
    TEXT,
    data_uri,
    fullscreen_rules,
    primary_button_css,
)

# Placeholder copy. Replace these two lines when the real words are ready.
HEADLINE = "RIO headline goes here"
CREATOR_STATEMENT = "Personal creator statement goes here."

# Photo by Giant Asparagus on Pexels.
PHOTO_CREDIT = "Photo by Giant Asparagus on Pexels"
CONTINUE_LABEL = "Continue"
SEEN_KEY = "rio_startup_seen"

PHOTO_PATH = Path(__file__).resolve().parent / "assets" / "startup_track.jpg"

_HTML = """
<div class="rio-startup-shade" aria-hidden="true"></div>
<section class="rio-startup-copy">
  <h1 class="rio-startup-headline">HEADLINE_TEXT</h1>
  <div class="rio-startup-statement" data-placeholder="personal-creator-statement">
    <p class="rio-startup-kicker">Placeholder</p>
    <p class="rio-startup-statement-label">Personal creator statement</p>
    <p class="rio-startup-statement-body">STATEMENT_TEXT</p>
  </div>
  <p class="rio-startup-credit">CREDIT_TEXT</p>
</section>
"""


def _layout_css() -> str:
    """Startup type and the glass statement. The photo comes from the theme."""
    return f"""
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stHeaderActionElements"],
[data-testid="stSidebar"],
#MainMenu,
footer,
header {{
  display: none !important;
  height: 0 !important;
}}
[data-testid="stMainBlockContainer"],
.block-container {{
  max-width: 40rem !important;
  min-height: 100vh !important;
  margin: 0 auto !important;
  padding: 4.5rem 1.4rem 5.5rem !important;
  box-sizing: border-box !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
}}
[data-testid="stMainBlockContainer"] > div,
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {{
  flex: 0 0 auto !important;
  gap: 0.2rem !important;
}}
.rio-startup-copy,
.rio-startup-copy h1,
.rio-startup-copy p,
[class*="st-key-rio-startup-continue"] button,
[class*="st-key-rio-startup-continue"] button p,
[class*="st-key-rio-startup-continue"] button span {{
  font-family: {FONT} !important;
}}
.rio-startup-copy {{
  position: relative;
  z-index: 2;
  text-align: center;
  color: {TEXT};
}}
.rio-startup-headline {{
  margin: 0 0 1.35rem !important;
  color: {TEXT} !important;
  font-size: clamp(2.15rem, 5vw, 3.35rem) !important;
  font-weight: 560 !important;
  letter-spacing: -0.03em !important;
  line-height: 1.12 !important;
  text-shadow: 0 2px 18px rgba(0, 0, 0, 0.55);
}}
.rio-startup-statement {{
  margin: 0 auto;
  max-width: 34rem;
  padding: 1.05rem 1.2rem 1.15rem;
  text-align: left;
  border: 1px solid {CARD_BORDER};
  border-radius: {RADIUS};
  background: {CARD_FILL};
  box-shadow: {CARD_SHADOW};
  backdrop-filter: blur(16px);
}}
.rio-startup-kicker {{
  margin: 0 0 0.35rem !important;
  color: {LIGHT} !important;
  font-size: 0.72rem !important;
  font-weight: 650 !important;
  letter-spacing: 0.16em !important;
  line-height: 1.3 !important;
  text-transform: uppercase;
}}
.rio-startup-statement-label {{
  margin: 0 0 0.4rem !important;
  color: {TEXT} !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  line-height: 1.35 !important;
}}
.rio-startup-statement-body {{
  margin: 0 !important;
  color: {TEXT} !important;
  font-size: 1.05rem !important;
  font-weight: 400 !important;
  line-height: 1.5 !important;
}}
.rio-startup-credit {{
  position: fixed;
  z-index: 3;
  left: 0;
  right: 0;
  bottom: 1rem;
  margin: 0 !important;
  color: rgba(244, 244, 244, 0.82) !important;
  font-size: 0.78rem !important;
  font-weight: 400 !important;
  letter-spacing: 0.01em !important;
  line-height: 1.4 !important;
  text-align: center;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.7);
  pointer-events: none;
}}
[class*="st-key-rio-startup-continue"] {{
  position: relative !important;
  z-index: 2 !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  width: 100% !important;
  background: transparent !important;
  margin-top: 1.35rem !important;
}}
[class*="st-key-rio-startup-continue"] button,
[class*="st-key-rio-startup-continue"] [data-testid="stBaseButton-primary"] {{
  min-width: 11.5rem !important;
}}
"""


def startup_pending(state: object) -> bool:
    """True until Continue has been used in this session."""
    getter = getattr(state, "get", None)
    if not callable(getter):
        return True
    return getter(SEEN_KEY) is not True


def acknowledge_startup(state: object) -> None:
    """Remember Continue for this session only. A new tab starts over."""
    state[SEEN_KEY] = True  # type: ignore[index]


@lru_cache(maxsize=1)
def _photo_uri() -> str:
    """The track photo as a data URI, or empty when the file is missing."""
    return data_uri(str(PHOTO_PATH))


def startup_html() -> str:
    """The headline, the marked placeholder, and the photo credit."""
    return (
        _HTML.replace("HEADLINE_TEXT", escape(HEADLINE))
        .replace("STATEMENT_TEXT", escape(CREATOR_STATEMENT))
        .replace("CREDIT_TEXT", escape(PHOTO_CREDIT))
    )


def startup_css(photo_uri: str | None = None) -> str:
    """Full-screen photo, dark shade, and the Continue control."""
    uri = _photo_uri() if photo_uri is None else photo_uri
    image = f'url("{uri}")' if uri else "none"
    return (
        "<style>"
        + fullscreen_rules(image)
        + _layout_css()
        + primary_button_css('[class*="st-key-rio-startup-continue"]')
        + "</style>"
    )


def render_startup() -> bool:
    """Draw the page. True when Continue was pressed."""
    st.markdown(startup_css(), unsafe_allow_html=True)
    st.markdown(startup_html(), unsafe_allow_html=True)
    with st.container(key="rio-startup-continue"):
        return bool(st.button(CONTINUE_LABEL, type="primary"))
