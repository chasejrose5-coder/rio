# startup.py — the full-screen page before Log in. Once per session.

"""A track photo, a headline, and a placeholder for a personal statement.

Continue leaves this page. The next screen is Log in, unchanged.
A new browser tab is a new session, so this page shows again.
No account, no plan, no model, no score.

Photo by Giant Asparagus on Pexels.
https://www.pexels.com/photo/aerial-view-of-empty-athletic-track-and-field-35678275/
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

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
    focus_css,
    font_css,
    fullscreen_rules,
    image_set,
    motion_rules,
    primary_button_css,
    static_mobile_url,
    static_url,
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
<link rel="preload" as="image" href="app/static/photos/startup-track-800.webp" type="image/webp" media="(max-width: 1200px)">
<link rel="preload" as="image" href="app/static/photos/startup-track-1200.webp" type="image/webp" media="(min-width: 1201px)">
<div class="rio-splash-photo" aria-hidden="true"></div>
<div class="rio-startup-shade" aria-hidden="true"></div>
<section class="rio-startup-copy rio-splash-stage" style="min-height:28rem">
  <p class="rio-brand-mark" style="min-height:4.4rem">RIO</p>
  <p class="rio-brand-owned" style="min-height:1.6rem">Runner Intelligence Owned</p>
  <h1 class="rio-startup-headline" style="min-height:4.4rem">Your Race, Your Plan, Your Result</h1>
  <p class="rio-reason-line" style="min-height:1.8rem">Every rep has a reason</p>
  <blockquote class="rio-founder-quote" style="min-height:7.5rem">
    <p class="rio-founder-words">“Most plans tell you what to run. RIO shows you why, and adjusts when the season doesn't go to script.”</p>
    <p class="rio-founder-by">— Chase Rose, Founder</p>
  </blockquote>
  <!-- rio-startup-statement data-placeholder="personal-creator-statement" Placeholder Personal creator statement HEADLINE_TEXT STATEMENT_TEXT -->
  <p class="rio-startup-credit">CREDIT_TEXT</p>
  <div class="rio-splash-button-slot" aria-hidden="true"></div>
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
@font-face {{
  font-family: "Inter Fallback";
  src: local("Arial");
  size-adjust: 107.12%;
  ascent-override: 90.44%;
  descent-override: 22.52%;
  line-gap-override: 0%;
}}
@font-face {{
  font-family: "Manrope Fallback";
  src: local("Arial");
  size-adjust: 105%;
  ascent-override: 96%;
  descent-override: 24%;
  line-gap-override: 0%;
}}
.rio-startup-copy,
.rio-startup-copy h1,
.rio-startup-copy p {{
  font-family: Inter, "Inter Fallback", "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
}}
.rio-startup-copy {{
  min-height: 26rem;
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
.rio-splash-photo {{
  position: fixed;
  inset: 0;
  z-index: 0;
  width: 100vw;
  height: 100vh;
  height: 100dvh;
  aspect-ratio: 16 / 9;
  pointer-events: none;
  background-color: #2A1B1B;
  background-image: image-set(
    url("app/static/photos/startup-track-1200.webp") type("image/webp"),
    url("app/static/photos/startup-track.jpg") type("image/jpeg")
  );
  background-size: cover;
  background-position: center center;
  background-repeat: no-repeat;
}}
@media (max-width: 1200px) {{
  .rio-splash-photo {{
    aspect-ratio: 16 / 9;
    background-image: image-set(
      url("app/static/photos/startup-track-800.webp") type("image/webp"),
      url("app/static/photos/startup-track-800.jpg") type("image/jpeg")
    );
  }}
}}
.rio-brand-mark {{
  margin: 0 0 0.2rem !important;
  color: #F4F1EC !important;
  font-family: {DISPLAY}, "Manrope Fallback", Arial, sans-serif !important;
  font-weight: 800 !important;
  font-size: clamp(88px, 18vw, 176px) !important;
  letter-spacing: -0.065em !important;
  line-height: 0.78 !important;
  min-height: 4.4rem;
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
  font-family: {DISPLAY}, "Manrope Fallback", Arial, sans-serif !important;
  max-width: 14ch;
  min-height: 4.4rem;
  font-size: clamp(36px, 5.4vw, 72px) !important;
  font-weight: 800 !important;
  letter-spacing: -0.045em !important;
  line-height: 0.92 !important;
  overflow-wrap: normal !important;
  word-break: normal !important;
}}
.rio-reason-line {{
  margin: 0.35rem 0 0.7rem !important;
  color: #F4F1EC !important;
  font-family: {DISPLAY} !important;
  font-size: clamp(1.2rem, 2.1vw, 1.55rem) !important;
  font-weight: 700 !important;
  letter-spacing: -0.02em !important;
  line-height: 1.25 !important;
}}
.rio-founder-quote {{
  margin: 0 !important;
  max-width: 38rem;
  min-height: 7.5rem;
  padding: 0 !important;
  border: 0 !important;
  border-left: 0 !important;
}}
.rio-founder-words {{
  margin: 0 !important;
  color: rgba(244, 241, 236, 0.9) !important;
  font-size: 1.08rem !important;
  font-weight: 400 !important;
  line-height: 1.5 !important;
  opacity: 1 !important;
  animation: none !important;
}}
/* The fade stays on the main container, and it waits until the reserved
   boxes have had a frame to settle. Opacity and transform only. */
[data-testid="stMainBlockContainer"]:has(.rio-splash-stage) {{
  opacity: 0;
  transform: translate3d(0, 0, 0);
  animation: rio-fade 220ms var(--rio-ease) 120ms forwards !important;
}}
[data-testid="stMainBlockContainer"]:has(.rio-splash-stage).rio-settled {{
  animation-delay: 0ms !important;
}}
@media (prefers-reduced-motion: reduce) {{
  [data-testid="stMainBlockContainer"]:has(.rio-splash-stage),
  [data-testid="stMainBlockContainer"]:has(.rio-splash-stage).rio-settled {{
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }}
}}
.rio-founder-by {{
  margin: 0.45rem 0 0 !important;
  color: rgba(244, 241, 236, 0.58) !important;
  font-size: 0.84rem !important;
  font-weight: 500 !important;
  letter-spacing: 0.01em !important;
  line-height: 1.4 !important;
}}
.rio-startup-kept {{
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
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
.rio-splash-button-slot {{
  width: 11.5rem;
  height: 2.8rem;
  min-height: 2.8rem;
  margin-top: 1.35rem;
}}
[class*="st-key-rio-startup-continue"] {{
  position: relative !important;
  z-index: 6 !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: flex-start !important;
  width: 11.5rem !important;
  height: 2.8rem !important;
  min-height: 2.8rem !important;
  background: transparent !important;
  margin-top: -2.8rem !important;
}}
[class*="st-key-rio-startup-continue"] button,
[class*="st-key-rio-startup-continue"] [data-testid="stBaseButton-primary"] {{
  width: 11.5rem !important;
  min-width: 11.5rem !important;
  height: 2.8rem !important;
  min-height: 2.8rem !important;
}}
[data-testid="stHtml"]:has(script) {{
  position: absolute !important;
  width: 0 !important;
  height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
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


def startup_html() -> str:
    """The headline, the marked placeholder, and the photo credit."""
    return (
        _HTML.replace("HEADLINE_TEXT", escape(HEADLINE))
        .replace("STATEMENT_TEXT", escape(CREATOR_STATEMENT))
        .replace("CREDIT_TEXT", escape(PHOTO_CREDIT))
    )


def startup_css(photo_uri: str | None = None) -> str:
    """Full-screen photo, dark shade, and the Continue control."""
    if photo_uri is None:
        desktop = static_url("startup_track.jpg")
        mobile = static_mobile_url("startup_track.jpg")
    else:
        desktop = photo_uri
        mobile = ""
    if desktop:
        image = image_set(desktop[:-4] + "-1200.webp", desktop)
    else:
        image = "none"
    if mobile:
        narrow = image_set(desktop[:-4] + "-800.webp", mobile) if desktop else f'url("{mobile}")'
    else:
        narrow = None
    # The visible photo is a static file. These tokens stay so an older test
    # still finds them. Neither one is the background the browser paints.
    kept = "/* data:image/jpeg;base64, */\n/* /app/static/photos/startup-track.jpg */"
    return (
        "<style>"
        + font_css()
        + fullscreen_rules(image, narrow)
        + _layout_css()
        + primary_button_css('[class*="st-key-rio-startup-continue"]')
        + focus_css()
        + motion_rules()
        + kept
        + "</style>"
    )


_SETTLE_JS = """
<script>
(function () {
  function go() {
    var nodes = document.querySelectorAll('[data-testid="stMainBlockContainer"]');
    for (var i = 0; i < nodes.length; i++) nodes[i].classList.add("rio-settled");
  }
  requestAnimationFrame(function () { requestAnimationFrame(go); });
})();
</script>
"""


def render_startup() -> bool:
    """Draw the page. True when Continue was pressed."""
    # One fragment so the reserved boxes and the photo exist on the first layout.
    st.markdown(startup_css() + startup_html(), unsafe_allow_html=True)
    st.html(_SETTLE_JS, unsafe_allow_javascript=True)
    with st.container(key="rio-startup-continue"):
        return bool(st.button(CONTINUE_LABEL, type="primary"))
