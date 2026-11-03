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

from ui.hero_config import enabled_frames
from ui.theme import (
    ACCENT,
    CARD_BORDER,
    CARD_FILL,
    CARD_SHADOW,
    DISPLAY,
    FONT,
    MUTED,
    RADIUS,
    TEXT,
    data_uri,
    font_css,
    fullscreen_rules,
    motion_rules,
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
  <p class="rio-brand-mark">RIO</p>
  <p class="rio-brand-owned">Runner Intelligence Owned</p>
  <h1 class="rio-startup-headline">Your Race, Your Plan, Your Result</h1>
  <p class="rio-brand-line">Understand the work behind your goal</p>
  <div class="rio-startup-statement" data-placeholder="personal-creator-statement">
    <p class="rio-startup-kicker">Placeholder</p>
    <p class="rio-startup-statement-label">Personal creator statement</p>
    <p class="rio-startup-statement-body">HEADLINE_TEXT</p>
    <p class="rio-startup-statement-body">STATEMENT_TEXT</p>
  </div>
  <p class="rio-startup-credit">CREDIT_TEXT</p>
</section>
"""


def _layout_css() -> str:
    """Startup type and the paper statement. The photo comes from the theme."""
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
  max-width: 100% !important;
  min-height: 100vh !important;
  margin: 0 !important;
  padding: 14vh 6vw 5rem !important;
  box-sizing: border-box !important;
  display: flex !important;
  flex-direction: column !important;
  justify-content: flex-start !important;
  overflow: visible !important;
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
  z-index: 5;
  margin: 0;
  max-width: 100%;
  padding: 0;
  text-align: left;
  color: #F4F1EC;
  background: transparent;
  border: none;
  border-radius: 0;
  box-shadow: none;
}}
.rio-brand-mark {{
  margin: 0 0 0.2rem !important;
  color: #F4F1EC !important;
  font-family: {DISPLAY} !important;
  font-weight: 800 !important;
  font-size: clamp(88px, 18vw, 176px) !important;
  letter-spacing: -0.065em !important;
  line-height: 0.78 !important;
}}
.rio-brand-owned {{
  margin: 0 0 1.35rem !important;
  color: rgba(244, 241, 236, 0.86) !important;
  font-family: {DISPLAY} !important;
  font-weight: 700 !important;
  font-size: clamp(0.95rem, 1.6vw, 1.15rem) !important;
  letter-spacing: 0.08em !important;
  line-height: 1.3 !important;
}}
.rio-startup-headline {{
  margin: 0 0 0.7rem !important;
  color: #F4F1EC !important;
  font-family: {DISPLAY} !important;
  max-width: 14ch;
  font-size: clamp(36px, 5.4vw, 72px) !important;
  font-weight: 800 !important;
  letter-spacing: -0.045em !important;
  line-height: 0.92 !important;
  overflow-wrap: normal !important;
  word-break: normal !important;
}}
.rio-brand-line {{
  margin: 0 0 1.35rem !important;
  color: rgba(244, 241, 236, 0.78) !important;
  font-size: 1.05rem !important;
  font-weight: 400 !important;
  line-height: 1.45 !important;
}}
.rio-startup-statement {{
  margin: 0;
  max-width: none;
  padding: 0;
  text-align: left;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}}
.rio-startup-kicker {{
  margin: 0 0 0.35rem !important;
  color: {ACCENT} !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.16em !important;
  line-height: 1.3 !important;
  text-transform: uppercase;
}}
.rio-startup-statement-label {{
  margin: 0 0 0.4rem !important;
  color: #F4F1EC !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  line-height: 1.35 !important;
}}
.rio-startup-statement-body {{
  margin: 0 !important;
  color: rgba(244, 241, 236, 0.82) !important;
  font-size: 1.05rem !important;
  font-weight: 400 !important;
  line-height: 1.5 !important;
}}
.rio-startup-credit {{
  position: fixed;
  z-index: 4;
  left: 0;
  right: 0;
  bottom: 1rem;
  width: fit-content;
  margin: 0 auto !important;
  padding: 0.22rem 0.75rem;
  border-radius: 999px;
  background: rgba(18, 17, 16, 0.45);
  border: 1px solid rgba(244, 241, 236, 0.35);
  color: #F4F1EC !important;
  font-size: 0.78rem !important;
  font-weight: 400 !important;
  letter-spacing: 0.01em !important;
  line-height: 1.4 !important;
  text-align: center;
  pointer-events: none;
}}
[class*="st-key-rio-startup-continue"] {{
  position: relative !important;
  z-index: 6 !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: flex-start !important;
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


def _frames() -> list[dict]:
    """Enabled startup frames. A missing config leaves the original photo."""
    try:
        return enabled_frames()
    except OSError:
        return []


def _rotator_html(frames: list[dict]) -> str:
    """Crossfading photos and a credit for each one. Empty when none are on."""
    if not frames:
        return ""
    photos = []
    credits = []
    for index, frame in enumerate(frames):
        photos.append(f'<div class="rio-hero-frame rio-hero-frame-{index}"></div>')
        credits.append(
            f'<p class="rio-hero-credit-item rio-hero-credit-{index}">'
            f"{escape(str(frame.get('credit') or ''))}</p>"
        )
    return (
        '<div class="rio-hero-rotator" aria-hidden="true">'
        + "".join(photos)
        + "</div>"
        + '<div class="rio-hero-credits">'
        + "".join(credits)
        + "</div>"
    )


def _rotator_css(frames: list[dict]) -> str:
    """Slow crossfade. One photo stays put when motion is reduced."""
    if not frames:
        return ""
    count = len(frames)
    rules = []
    for index, frame in enumerate(frames):
        uri = data_uri(str(frame.get("file") or ""))
        image = f'url("{uri}")' if uri else "none"
        rules.append(
            f".rio-hero-frame-{index}{{background-image:{image};}}"
        )
    if count == 1:
        motion = """
.rio-hero-frame-0,
.rio-hero-credit-0 { opacity: 1 !important; }
"""
    else:
        hold = 8.0
        total = hold * count
        shown = 0.78 * hold / total * 100
        gone = min(hold / total * 100 + 2.0, 96.0)
        delays = []
        for index in range(count):
            delays.append(
                f".rio-hero-frame-{index},.rio-hero-credit-{index}"
                f"{{animation-delay:{index * hold:.1f}s;}}"
            )
        motion = f"""
@keyframes rio-hero-cross {{
  0% {{ opacity: 1; }}
  {shown:.2f}% {{ opacity: 1; }}
  {gone:.2f}% {{ opacity: 0; }}
  100% {{ opacity: 0; }}
}}
.rio-hero-frame,
.rio-hero-credit-item {{
  animation: rio-hero-cross {total:.1f}s cubic-bezier(0.22, 1, 0.36, 1) infinite;
}}
{"".join(delays)}
"""
    return f"""
.rio-hero-rotator {{
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}}
.rio-hero-frame {{
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center center;
  background-repeat: no-repeat;
  opacity: 0;
}}
.rio-hero-credit-item {{
  position: fixed;
  z-index: 6;
  left: 50%;
  bottom: 2.8rem;
  transform: translateX(-50%);
  margin: 0 !important;
  padding: 0.22rem 0.75rem;
  border-radius: 999px;
  background: rgba(18, 17, 16, 0.55);
  border: 1px solid rgba(244, 241, 236, 0.35);
  color: #F4F1EC !important;
  font-size: 0.78rem !important;
  line-height: 1.4 !important;
  opacity: 0;
  white-space: nowrap;
  pointer-events: none;
}}
{motion}
@media (prefers-reduced-motion: reduce) {{
  .rio-hero-frame,
  .rio-hero-credit-item {{
    animation: none !important;
    opacity: 0 !important;
  }}
  .rio-hero-frame-0,
  .rio-hero-credit-0 {{
    opacity: 1 !important;
  }}
}}
{"".join(rules)}
"""


def startup_html() -> str:
    """The headline, the marked placeholder, and the photo credit."""
    page = (
        _HTML.replace("HEADLINE_TEXT", escape(HEADLINE))
        .replace("STATEMENT_TEXT", escape(CREATOR_STATEMENT))
        .replace("CREDIT_TEXT", escape(PHOTO_CREDIT))
    )
    return _rotator_html(_frames()) + page


def startup_css(photo_uri: str | None = None) -> str:
    """Full-screen photo, dark shade, and the Continue control."""
    uri = _photo_uri() if photo_uri is None else photo_uri
    image = f'url("{uri}")' if uri else "none"
    return (
        "<style>"
        + font_css()
        + fullscreen_rules(image)
        + _layout_css()
        + _rotator_css(_frames())
        + primary_button_css('[class*="st-key-rio-startup-continue"]')
        + motion_rules()
        + _still_hero_css()
        + "</style>"
    )


def _still_hero_css() -> str:
    """After the shared motion rules, so a reduced-motion visit stays on frame one."""
    return """
@media (prefers-reduced-motion: reduce) {
  .rio-hero-frame,
  .rio-hero-credit-item {
    animation: none !important;
    opacity: 0 !important;
  }
  .rio-hero-frame-0,
  .rio-hero-credit-0 {
    opacity: 1 !important;
  }
}
"""


def render_startup() -> bool:
    """Draw the page. True when Continue was pressed."""
    st.markdown(startup_css(), unsafe_allow_html=True)
    st.markdown(startup_html(), unsafe_allow_html=True)
    with st.container(key="rio-startup-continue"):
        return bool(st.button(CONTINUE_LABEL, type="primary"))
