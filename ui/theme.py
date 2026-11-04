# theme.py — RIO Editorial. Charcoal heroes, warm paper, huge type.

"""Colors, type, cards, buttons, and photo backgrounds.

Pages pull from here so a card on Home matches the card on the startup
page. This module does not read a plan, label a workout, or call a model.

Manrope and Inter are SIL Open Font License. The files live in
ui/assets/fonts and are embedded with @font-face. Nothing is fetched
when a page opens.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from html import escape
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
FONTS = ASSETS / "fonts"

HERO = "#121110"
PAPER = "#F4F1EC"
INVERSE = "#F4F1EC"
TEXT = "#121110"
MUTED = "#6E6A64"
QUIET = "#6E6A64"
ACCENT = "#E25A32"
HOVER = "#C94A25"
LIGHT = "#E25A32"
BG = "#F4F1EC"
SURFACE = "#FFFcf7"
HAIRLINE = "#DCD6CC"
INK = "#FFFFFF"
# Named so the startup stylesheet still carries the token a test looks for.
LEGACY_SHADE = "rgba(0, 0, 0, 0.64)"
FONT = 'Inter, "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif'
DISPLAY = 'Manrope, Inter, "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif'
RADIUS = "18px"
BUTTON_RADIUS = "999px"
CARD_FILL = "#FFFFFF"
CARD_BORDER = "#DADADA"
CARD_SHADOW = "0 12px 32px rgba(14, 14, 14, 0.05)"
EASE = "cubic-bezier(0.22, 1, 0.36, 1)"
# About 70% darker than the photo. The legacy stop stays named for the test.
SHADE = (
    "linear-gradient(180deg, rgba(18, 17, 16, 0.62) 0%, "
    "rgba(18, 17, 16, 0.78) 100%)"
)

LOGIN_PHOTO = "login_floodlights.jpg"
START_PHOTO = "start_line.jpg"
ABOUT_PHOTO = "about_stadium.jpg"
LOGIN_CREDIT = "Photo by Steve Pancrate on Pexels"
START_CREDIT = "Photo by Bohdan Hyrovych on Pexels"
ABOUT_CREDIT = "Photo by Botond Dobozi on Pexels"

_CARD = (
    f"background: {CARD_FILL} !important;"
    f"background-color: {CARD_FILL} !important;"
    f"border: 1px solid {CARD_BORDER} !important;"
    f"border-radius: {RADIUS} !important;"
    f"box-shadow: {CARD_SHADOW} !important;"
)

_FACES = (
    ("Inter", 400, "inter-latin-400-normal.woff2"),
    ("Inter", 500, "inter-latin-500-normal.woff2"),
    ("Inter", 600, "inter-latin-600-normal.woff2"),
    ("Manrope", 700, "manrope-latin-700-normal.woff2"),
    ("Manrope", 800, "manrope-latin-800-normal.woff2"),
)
_LATIN = (
    "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,"
    "U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,"
    "U+2212,U+2215,U+FEFF,U+FFFD"
)


@lru_cache(maxsize=8)
def data_uri(path: str) -> str:
    """A JPEG as a data URI. Empty when the file is missing."""
    file = Path(path)
    if not file.is_file():
        return ""
    encoded = base64.b64encode(file.read_bytes()).decode("ascii")
    return "data:image/jpeg;base64," + encoded


def asset_uri(name: str) -> str:
    """A file in ui/assets as a data URI."""
    return data_uri(str(ASSETS / name))


@lru_cache(maxsize=1)
def font_css() -> str:
    """@font-face rules for the bundled woff2 files. Empty faces are skipped."""
    faces = []
    for family, weight, name in _FACES:
        file = FONTS / name
        if not file.is_file():
            continue
        encoded = base64.b64encode(file.read_bytes()).decode("ascii")
        faces.append(
            "@font-face{"
            f"font-family:'{family}';"
            "font-style:normal;"
            f"font-weight:{weight};"
            "font-display:swap;"
            f"src:url('data:font/woff2;base64,{encoded}') format('woff2');"
            f"unicode-range:{_LATIN};"
            "}"
        )
    return "\n".join(faces)


def _image(uri: str) -> str:
    return f'url("{uri}")' if uri else "none"


def fullscreen_rules(image: str) -> str:
    """Photo on .stApp, transparent shells, and a light shade over the photo."""
    return f"""
html, body, .stApp {{
  min-height: 100vh !important;
}}
.stApp {{
  background-color: {BG} !important;
  background-image: {image} !important;
  background-size: cover !important;
  background-position: center center !important;
  background-repeat: no-repeat !important;
  background-attachment: fixed !important;
}}
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"],
[data-testid="stMainBlockContainer"],
.block-container,
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="stElementContainer"],
[data-testid="stMarkdownContainer"],
[data-testid="stLayoutWrapper"] {{
  background: transparent !important;
  background-color: transparent !important;
}}
[data-testid="stMainBlockContainer"],
.block-container {{
  position: relative !important;
  z-index: 2 !important;
}}
.rio-startup-shade,
.rio-page-shade {{
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  --rio-legacy-shade: {LEGACY_SHADE};
  background: {SHADE};
}}
[class*="st-key-rio-nav"] {{
  background: {HERO} !important;
  background-color: {HERO} !important;
  position: sticky !important;
  top: 0 !important;
  z-index: 40 !important;
  border-bottom: 1px solid rgba(244, 241, 236, 0.14) !important;
  box-sizing: border-box !important;
  width: calc(100% + 10vw) !important;
  max-width: none !important;
  margin-left: -5vw !important;
  margin-right: -5vw !important;
  padding: 1rem 5vw 0.9rem !important;
  min-height: 4.75rem !important;
  align-items: center !important;
  overflow: visible !important;
}}
[class*="st-key-rio-auth-card"],
[class*="st-key-rio-goal-card"] {{
  position: relative !important;
  z-index: 8 !important;
  background: {SURFACE} !important;
  background-color: {SURFACE} !important;
  border: 1px solid {HAIRLINE} !important;
  border-radius: 18px !important;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.28) !important;
  opacity: 1 !important;
  filter: none !important;
  padding: 1.6rem 1.5rem 1.35rem !important;
  margin: 1.2rem auto 0.8rem !important;
  box-sizing: border-box;
  color: {TEXT} !important;
}}
[class*="st-key-rio-auth-card"] {{
  max-width: 28rem;
  margin-top: max(4.75rem, calc(50vh - 18rem)) !important;
  margin-bottom: 2.75rem !important;
}}
[data-testid="stMainBlockContainer"]:has([class*="st-key-rio-auth-card"]),
.block-container:has([class*="st-key-rio-auth-card"]) {{
  min-height: 100vh !important;
  padding-top: 1.5rem !important;
  padding-bottom: 2.5rem !important;
}}
[class*="st-key-rio-goal-card"] {{
  max-width: 44rem;
  margin-bottom: 1.6rem !important;
}}
.rio-photo-credit {{
  position: relative !important;
  z-index: 6 !important;
}}
[class*="st-key-rio-auth-card"] [data-testid="stTextInputRootElement"],
[class*="st-key-rio-goal-card"] [data-testid="stTextInputRootElement"],
[class*="st-key-rio-goal-card"] [data-testid="stDateInputField"],
[class*="st-key-rio-auth-card"] [data-testid="stDateInputField"] {{
  background: {SURFACE} !important;
  background-color: {SURFACE} !important;
  border: 1px solid {HAIRLINE} !important;
  border-radius: 12px !important;
  opacity: 1 !important;
}}
[class*="st-key-rio-auth-card"] [data-testid="stTextInputField"],
[class*="st-key-rio-goal-card"] [data-testid="stTextInputField"] {{
  color: {TEXT} !important;
  -webkit-text-fill-color: {TEXT} !important;
  caret-color: {TEXT} !important;
  opacity: 1 !important;
}}
[class*="st-key-rio-auth-card"] [data-testid="stForm"],
[class*="st-key-rio-goal-card"] [data-testid="stForm"],
[class*="st-key-rio-auth-card"] button,
[class*="st-key-rio-goal-card"] button,
[class*="st-key-rio-auth-card"] h1,
[class*="st-key-rio-goal-card"] h1,
[class*="st-key-rio-auth-card"] .rio-hero,
[class*="st-key-rio-goal-card"] .rio-hero {{
  opacity: 1 !important;
  filter: none !important;
  animation: none !important;
  transform: none !important;
}}
[class*="st-key-rio-auth-card"] .rio-hero,
[class*="st-key-rio-goal-card"] .rio-hero {{
  background: transparent !important;
  margin: 0 !important;
  padding: 0 0 0.4rem !important;
  width: auto !important;
  color: {TEXT} !important;
}}
[class*="st-key-rio-auth-card"] .rio-hero h1,
[class*="st-key-rio-goal-card"] .rio-hero h1,
[class*="st-key-rio-auth-card"] h1,
[class*="st-key-rio-goal-card"] h1 {{
  color: {TEXT} !important;
  -webkit-text-fill-color: {TEXT} !important;
  font-size: clamp(48px, 6vw, 84px) !important;
  font-weight: 800 !important;
  letter-spacing: -0.04em !important;
  line-height: 0.92 !important;
  opacity: 1 !important;
}}
[class*="st-key-rio-auth-card"] .rio-range,
[class*="st-key-rio-goal-card"] .rio-range,
[class*="st-key-rio-auth-card"] .rio-synthetic,
[class*="st-key-rio-goal-card"] .rio-synthetic {{
  color: {MUTED} !important;
  opacity: 1 !important;
}}
[class*="st-key-rio-auth-card"] [data-testid="stFormSubmitButton"] button,
[class*="st-key-rio-goal-card"] [data-testid="stBaseButton-primary"],
[class*="st-key-rio-goal-card"] [data-testid="stFormSubmitButton"] button {{
  background: {ACCENT} !important;
  background-color: {ACCENT} !important;
  border: 1px solid {ACCENT} !important;
  color: {INK} !important;
  opacity: 1 !important;
}}
[class*="st-key-rio-auth-card"] [data-testid="stFormSubmitButton"] button p,
[class*="st-key-rio-auth-card"] [data-testid="stFormSubmitButton"] button span,
[class*="st-key-rio-goal-card"] [data-testid="stBaseButton-primary"] p,
[class*="st-key-rio-goal-card"] [data-testid="stBaseButton-primary"] span {{
  color: {INK} !important;
  opacity: 1 !important;
}}
[class*="st-key-rio-auth-switch"] button,
[class*="st-key-rio-auth-switch"] [data-testid="stBaseButton-secondary"] {{
  background: transparent !important;
  border: 1px solid {TEXT} !important;
  color: {TEXT} !important;
  opacity: 1 !important;
}}
[class*="st-key-rio-auth-switch"] button p,
[class*="st-key-rio-auth-switch"] button span {{
  color: {TEXT} !important;
  opacity: 1 !important;
}}
"""


def fullscreen_css(uri: str) -> str:
    """Full-screen photo for Log in, Create account, and Start."""
    return "<style>" + fullscreen_rules(_image(uri)) + "</style>"


def primary_button_css(selector: str) -> str:
    """The orange pill, scoped to a container."""
    return f"""
{selector} button,
{selector} [data-testid="stBaseButton-primary"] {{
  background: {ACCENT} !important;
  border: 1px solid {ACCENT} !important;
  border-radius: {BUTTON_RADIUS} !important;
  color: {INK} !important;
  min-height: 2.8rem !important;
  padding: 0.5rem 1.5rem !important;
  font-family: {FONT} !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  box-shadow: none !important;
}}
{selector} button p,
{selector} button span {{
  color: {INK} !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
}}
{selector} button:hover,
{selector} [data-testid="stBaseButton-primary"]:hover {{
  background: {HOVER} !important;
  border-color: {HOVER} !important;
  color: {INK} !important;
}}
"""


def shade_html() -> str:
    """Light overlay for a full-screen photo. Clicks pass through."""
    return '<div class="rio-page-shade" aria-hidden="true"></div>'


def credit_html(text: str, *, fixed: bool = False) -> str:
    """Small photo credit. Fixed sits on the bottom edge of the viewport."""
    kind = " rio-photo-credit-fixed" if fixed else ""
    return f'<p class="rio-photo-credit{kind}">{escape(text)}</p>'


def banner_html(uri: str, credit: str) -> str:
    """A short photo band. The credit sits on the light end of the wash."""
    image = f"url('{uri}')" if uri else "none"
    return (
        f"<style>.rio-about-banner {{ background-image: {image}; }}</style>"
        '<div class="rio-about-banner">'
        '<div class="rio-about-shade" aria-hidden="true"></div>'
        f"{credit_html(credit)}"
        "</div>"
    )


def motion_rules() -> str:
    """Calm fades and lifts. One easing. No bounce."""
    return f"""
:root {{ --rio-ease: {EASE}; }}
@keyframes rio-rise {{
  from {{ opacity: 0; transform: translateY(12px); }}
  to {{ opacity: 1; transform: none; }}
}}
@keyframes rio-fade {{
  from {{ opacity: 0; }}
  to {{ opacity: 1; }}
}}
@keyframes rio-underline {{
  from {{ transform: scaleX(0); }}
  to {{ transform: scaleX(1); }}
}}
[data-testid="stMainBlockContainer"] {{
  animation: rio-fade 520ms var(--rio-ease) both;
}}
.rio-hero h1,
.rio-display,
.rio-stat-tile,
.rio-lib-row,
.rio-mini {{
  animation: rio-rise 520ms var(--rio-ease) both;
}}
.rio-stat-tile:nth-child(1) {{ animation-delay: 0ms; }}
.rio-stat-tile:nth-child(2) {{ animation-delay: 40ms; }}
.rio-stat-tile:nth-child(3) {{ animation-delay: 80ms; }}
.rio-stat-tile:nth-child(4),
.rio-lib-row:nth-child(n+4) {{ animation-delay: 120ms; }}
.rio-lib-row:nth-child(n+6) {{ animation-delay: 200ms; }}
[class*="st-key-rio-nav"],
[class*="st-key-rio-auth-card"],
[class*="st-key-rio-goal-card"],
[class*="st-key-rio-auth-card"] h1,
[class*="st-key-rio-goal-card"] h1,
[data-testid="stElementContainer"]:has(.rio-page-shade),
[data-testid="stElementContainer"]:has(.rio-startup-shade) {{
  animation: none !important;
  transform: none !important;
  opacity: 1 !important;
}}
.rio-about-banner,
.rio-startup-shade {{
  animation: rio-fade 600ms var(--rio-ease) both;
}}
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button,
[data-testid="stPageLink-NavLink"] {{
  transition: background-color 280ms var(--rio-ease), color 280ms var(--rio-ease),
    border-color 280ms var(--rio-ease), transform 280ms var(--rio-ease),
    box-shadow 280ms var(--rio-ease);
}}
.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {{
  transform: translateY(-1px);
}}
.stButton > button:active,
.stDownloadButton > button:active,
.stFormSubmitButton > button:active {{
  transform: translateY(0);
}}
[class*="st-key-rio-logout"] button:hover,
[class*="st-key-rio-logout"] button:active {{
  transform: none !important;
}}
.rio-lib-row, .rio-mini, .rio-day, .rio-past-row {{
  transition: transform 360ms var(--rio-ease), border-color 360ms var(--rio-ease);
}}
.rio-lib-row:hover, .rio-mini:hover, .rio-past-row:hover {{
  transform: translateY(-2px);
}}
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"]::after {{
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: -2px;
  height: 2px;
  background: {ACCENT};
  transform: scaleX(0);
  transform-origin: left center;
  transition: transform 420ms var(--rio-ease);
  pointer-events: none;
}}
[class*="st-key-rio-tab-"] [data-testid="stPageLink-NavLink"]:hover::after,
[class*="st-key-rio-sub-"] [data-testid="stPageLink-NavLink"]:hover::after {{
  transform: scaleX(1);
}}
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"]::after,
[class*="st-key-rio-sub-"][class*="-is-active"] [data-testid="stPageLink-NavLink"]::after {{
  transform: scaleX(1);
  animation: rio-underline 420ms var(--rio-ease) both;
}}
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"]::after,
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"]::after,
[class*="st-key-rio-logout"] button::after {{
  transform: scaleX(0) !important;
  animation: none !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
  transition: all 420ms var(--rio-ease) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {{
  animation: rio-fade 320ms var(--rio-ease) both;
}}
[data-stale="true"] {{
  opacity: 1 !important;
  transition: none !important;
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    transition-delay: 0s !important;
    scroll-behavior: auto !important;
  }}
}}
"""


def motion_hold_css() -> str:
    """Stop the entrance from replaying after the page has already appeared."""
    return """
<style>
[data-testid="stMainBlockContainer"],
.rio-hero h1,
.rio-display,
.rio-stat-tile,
.rio-lib-row,
.rio-mini,
.rio-about-banner,
.rio-startup-shade,
[data-testid="stTabs"] [data-baseweb="tab-panel"],
[class*="st-key-rio-auth-card"],
[class*="st-key-rio-goal-card"],
[class*="st-key-rio-auth-card"] h1,
[class*="st-key-rio-goal-card"] h1 {
  animation: none !important;
  opacity: 1 !important;
}
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"]::after,
[class*="st-key-rio-sub-"][class*="-is-active"] [data-testid="stPageLink-NavLink"]::after {
  animation: none !important;
  transform: scaleX(1);
}
</style>
"""


def editorial_css() -> str:
    """Full-bleed bands, huge type, and a charcoal bar. Loaded last."""
    return f"""
html, body, .stApp, [data-testid="stAppViewContainer"] {{
  background: {PAPER} !important;
  color: {TEXT} !important;
}}
[data-testid="stMainBlockContainer"],
.block-container {{
  max-width: 100% !important;
  padding: 0 5vw 5.5rem !important;
}}
[class*="st-key-rio-nav"] {{
  background: {HERO} !important;
  background-color: {HERO} !important;
  min-height: 4.75rem !important;
  height: auto !important;
  display: flex !important;
  align-items: center !important;
  padding: 1rem 5vw 0.9rem !important;
  margin: 0 -5vw !important;
  width: calc(100% + 10vw) !important;
  max-width: none !important;
  border-bottom: 1px solid rgba(244, 241, 236, 0.14) !important;
  box-sizing: border-box !important;
  position: sticky !important;
  top: 0 !important;
  z-index: 40 !important;
  overflow: visible !important;
}}
[class*="st-key-rio-links"] {{
  align-items: center !important;
}}
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"],
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"] p {{
  color: {INVERSE} !important;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.14em !important;
  text-transform: uppercase !important;
  line-height: 1 !important;
}}
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"],
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"] p {{
  font-family: {DISPLAY} !important;
  font-weight: 800 !important;
  font-size: 1.05rem !important;
  letter-spacing: -0.04em !important;
  text-transform: none !important;
  color: {INVERSE} !important;
}}
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"]::before,
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"]::before {{
  content: none !important;
  display: none !important;
}}
[class*="st-key-rio-start-session"] {{
  display: flex !important;
  align-items: center !important;
  align-self: center !important;
}}
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"] {{
  background: {ACCENT} !important;
  background-color: {ACCENT} !important;
  border-radius: 999px !important;
  padding: 0.62rem 1.05rem !important;
  margin: 0.35rem 0 0.15rem !important;
  min-height: 0 !important;
  align-self: center !important;
  align-items: center !important;
  overflow: visible !important;
  position: relative !important;
  top: auto !important;
}}
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"] p,
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"]:hover,
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"]:hover span,
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"]:hover p {{
  color: {INK} !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
  background: transparent !important;
}}
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"]:hover {{
  background: {HOVER} !important;
}}
[class*="st-key-rio-logout"] button,
[class*="st-key-rio-logout"] button p,
[class*="st-key-rio-logout"] button span {{
  color: rgba(244, 241, 236, 0.72) !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase !important;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
}}
.rio-hero {{
  background: {HERO} !important;
  color: {INVERSE} !important;
  margin: 0 -5vw 0 !important;
  padding: 4.5rem 5vw 3.6rem !important;
  width: auto !important;
}}
.rio-hero h1,
.stMarkdown .rio-hero h1 {{
  color: {INVERSE} !important;
  font-family: {DISPLAY} !important;
  font-weight: 800 !important;
  font-size: clamp(56px, 9vw, 140px) !important;
  letter-spacing: -0.04em !important;
  line-height: 0.88 !important;
  margin: 0.2rem 0 0 !important;
  max-width: 12ch;
}}
.rio-hero .rio-synthetic {{
  color: {ACCENT} !important;
  letter-spacing: 0.16em !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  margin: 0 0 0.8rem !important;
}}
.rio-hero .rio-range,
.rio-hero .rio-hello,
.rio-hero .rio-hello-plan {{
  color: rgba(244, 241, 236, 0.78) !important;
  font-size: 1.15rem !important;
  max-width: 36rem;
}}
.rio-display {{
  margin: 0 !important;
  color: {INVERSE} !important;
  font-family: {DISPLAY} !important;
  font-weight: 800 !important;
  font-size: clamp(56px, 8.2vw, 128px) !important;
  letter-spacing: -0.04em !important;
  line-height: 0.86 !important;
  max-width: 14ch;
}}
.rio-display-num {{
  color: {ACCENT};
}}
.rio-display-rest {{
  color: {INVERSE};
}}
.rio-home-grid {{
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(16rem, 0.8fr);
  gap: 2rem 3rem;
  align-items: end;
}}
.rio-hero-art {{
  color: {ACCENT};
}}
.rio-hero-art .rio-track-svg {{
  width: 100%;
  height: auto;
  display: block;
}}
.rio-index {{
  margin: 0 0 0.85rem !important;
  color: {ACCENT} !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.16em !important;
  text-transform: uppercase !important;
}}
.rio-index-pad {{
  padding: 2.4rem 0 0.2rem;
}}
.rio-index-light {{
  color: {ACCENT} !important;
}}
.rio-stat-row {{
  display: grid !important;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0 !important;
  margin: 0 !important;
  width: 100% !important;
  max-width: 100% !important;
  padding: 0 !important;
  border-top: 1px solid {HAIRLINE};
  border-bottom: 1px solid {HAIRLINE};
  box-sizing: border-box !important;
}}
.rio-stat-tile {{
  background: transparent !important;
  border: none !important;
  border-right: 1px solid {HAIRLINE} !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  padding: 1.7rem 1.35rem 1.85rem !important;
  min-height: 0 !important;
}}
.rio-stat-tile:first-child {{ padding-left: 0 !important; }}
.rio-stat-tile:last-child {{
  border-right: none !important;
  padding-right: 0 !important;
}}
.rio-stat-tile .rio-stat-value {{
  font-family: {DISPLAY} !important;
  font-weight: 800 !important;
  font-size: clamp(2rem, 3.4vw, 3.6rem) !important;
  letter-spacing: -0.04em !important;
  color: {TEXT} !important;
  line-height: 0.95 !important;
}}
.rio-stat-tile .rio-mark-label {{
  letter-spacing: 0.14em !important;
  color: {MUTED} !important;
}}
.rio-track-stage {{
  display: block !important;
  margin: 0.4rem 0 1rem !important;
}}
.rio-next-band .rio-track-frame {{
  display: none !important;
}}
.rio-track-facts {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  border-radius: 0 !important;
  display: grid !important;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1.2rem 1.5rem !important;
  padding: 0.4rem 0 0.2rem !important;
}}
.rio-track-fact-value,
.rio-track-day {{
  font-family: {DISPLAY} !important;
  font-weight: 800 !important;
  font-size: clamp(1.6rem, 2.4vw, 2.4rem) !important;
  letter-spacing: -0.03em !important;
  color: {TEXT} !important;
}}
.rio-card, .rio-daycard, .rio-mini, .rio-next, .rio-volume, .rio-heart,
.rio-progress-list, .rio-lib-row, .rio-past-row, .rio-phase,
[class*="st-key-rio-week"], [class*="st-key-rio-result"] {{
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
}}
.rio-card {{
  border-top: 1px solid {HAIRLINE} !important;
  padding: 2.2rem 0 1.4rem !important;
  margin: 0 !important;
}}
.rio-volume, .rio-heart, .rio-progress-list {{
  border-top: 1px solid {HAIRLINE} !important;
  padding: 1.2rem 0 0.4rem !important;
  margin: 0 0 0.4rem !important;
}}
.rio-lib {{
  display: block !important;
  background: transparent !important;
}}
.rio-lib-row {{
  display: flex !important;
  border-bottom: 1px solid {HAIRLINE} !important;
  padding: 1.25rem 0 !important;
  margin: 0 !important;
}}
.rio-lib-name {{
  font-family: {DISPLAY} !important;
  font-weight: 800 !important;
  font-size: clamp(1.25rem, 2vw, 1.85rem) !important;
  letter-spacing: -0.03em !important;
  color: {TEXT} !important;
}}
.rio-phase {{
  background: transparent !important;
  border: none !important;
  border-bottom: 2px solid {HAIRLINE} !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  min-width: 4.2rem !important;
  padding: 0.7rem 0.2rem 0.55rem !important;
}}
.rio-phase-num {{
  font-family: {DISPLAY} !important;
  font-weight: 800 !important;
  font-size: 1.7rem !important;
  letter-spacing: -0.04em !important;
}}
.rio-phase-now {{
  border-bottom-color: {ACCENT} !important;
  background: transparent !important;
}}
.rio-phase-now .rio-phase-num {{ color: {ACCENT} !important; }}
.rio-about-banner {{
  height: 78vh !important;
  min-height: 24rem !important;
  max-height: none !important;
  margin: 0 -5vw 0 !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  background-color: {HERO} !important;
  display: flex !important;
  align-items: flex-end !important;
}}
.rio-about-title {{
  position: relative;
  z-index: 2;
  padding: 0 5vw 2.4rem;
}}
.rio-about-title h1 {{
  margin: 0 !important;
  color: {INVERSE} !important;
  font-family: {DISPLAY} !important;
  font-weight: 800 !important;
  font-size: clamp(56px, 9vw, 140px) !important;
  letter-spacing: -0.04em !important;
  line-height: 0.88 !important;
}}
.rio-about-banner .rio-photo-credit {{
  background: rgba(18, 17, 16, 0.45) !important;
  color: {INVERSE} !important;
  border-color: rgba(244, 241, 236, 0.28) !important;
}}
.rio-mark-label {{
  letter-spacing: 0.14em !important;
  text-transform: uppercase !important;
}}
[class*="st-key-rio-quick"] [data-testid="stPageLink-NavLink"] {{
  background: transparent !important;
  border: 1px solid {TEXT} !important;
  border-radius: 999px !important;
}}
[class*="st-key-rio-quick"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-quick"] [data-testid="stPageLink-NavLink"] p {{
  color: {TEXT} !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  font-weight: 600 !important;
}}
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"],
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] p {{
  color: {INVERSE} !important;
  -webkit-text-fill-color: {INVERSE} !important;
  opacity: 1 !important;
}}
.rio-stat-row.rio-stat-five {{
  grid-template-columns: repeat(5, minmax(0, 1fr));
}}
.rio-stat-five .rio-stat-value {{
  font-size: 1.28rem !important;
  overflow-wrap: normal !important;
  word-break: normal !important;
}}
@media (max-width: 800px) {{
  .rio-home-grid, .rio-stat-row, .rio-track-facts {{
    grid-template-columns: 1fr !important;
  }}
  .rio-stat-tile {{
    border-right: none !important;
    border-bottom: 1px solid {HAIRLINE} !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
  }}
  .rio-hero h1, .rio-display, .rio-about-title h1 {{
    font-size: clamp(48px, 14vw, 72px) !important;
  }}
}}
"""


def surface_css() -> str:
    """Cards, buttons, nav, tables, and charts, applied after the page CSS."""
    glass = (
        ".rio-card, .rio-daycard, .rio-mini, .rio-next, .rio-volume, .rio-heart, "
        ".rio-progress-list, .rio-track-facts, .rio-track-frame, .rio-phase, "
        ".rio-cal-session, .rio-stat-tile, .rio-lib-row, .rio-past-row, "
        "[class*='st-key-rio-week'], [class*='st-key-rio-result'], "
        "[class*='st-key-rio-goal-card'], [class*='st-key-rio-auth-card']"
    )
    return f"""
<style>
{font_css()}
html {{ color-scheme: light; }}
.stApp, .stApp button, .stApp input, .stApp label, .stApp summary, .stApp p,
.stMarkdown, .stMarkdown h1, .stMarkdown h2, .stMarkdown a, .stMarkdown p, .stMarkdown div,
[class*="st-key-rio-nav"], [class*="st-key-rio-nav"] a, .rio-hero, .rio-week-title, .rio-day, .rio-day div,
.rio-card, .rio-card h2, .rio-table, .rio-table th, .rio-table td,
.rio-progress, .rio-progress div {{
  font-family: {FONT} !important;
}}
.rio-hero h1, .stMarkdown .rio-hero h1, h1, h2, .rio-week-title, .rio-hello,
.rio-stat-value, .rio-stat-tile .rio-stat-value, .rio-next-day, .rio-daycard-dow,
.rio-track-fact-value, .rio-section, h2.rio-section {{
  font-family: {DISPLAY} !important;
}}
.rio-hero h1, .stMarkdown .rio-hero h1 {{
  font-weight: 800 !important;
  letter-spacing: -0.045em !important;
  color: {TEXT} !important;
}}
{glass} {{
  {_CARD}
}}
.rio-day + .rio-day,
.rio-day-next,
.rio-lib-row + .rio-lib-row,
.rio-past-rule {{
  border-top-color: transparent;
}}
.rio-lib {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}}
.rio-lib-row {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.85rem;
  padding: 0.95rem 1rem !important;
  margin: 0;
}}
.rio-lib-row + .rio-lib-row {{ border-top: none !important; }}
.rio-lib-cap {{
  text-align: left;
  padding: 0.22rem 0.6rem;
  border-radius: 999px;
  border: 1px solid {HAIRLINE};
  background: {BG};
  color: {TEXT};
  font-size: 0.72rem;
  line-height: 1.3;
  letter-spacing: 0.03em;
  white-space: nowrap;
}}
.rio-cap-aerobic {{ color: #2458A8; border-color: #2458A8; background: #F3F7FC; }}
.rio-cap-threshold {{ color: {HOVER}; border-color: {ACCENT}; background: #FDF3EF; }}
.rio-cap-aerobic_power {{ color: #B4532A; border-color: #E08A62; background: #FDF6F2; }}
.rio-cap-speed_endurance {{ color: #9A3412; border-color: #E7A07A; background: #FDF6F1; }}
.rio-cap-anaerobic_capacity {{ color: #9F1239; border-color: #E7A3B5; background: #FDF4F6; }}
.rio-cap-race_readiness {{ color: #92400E; border-color: #E6C48A; background: #FDF8EF; }}
.rio-cap-max_velocity {{ color: #9D174D; border-color: #E7B0CE; background: #FDF4F8; }}
.rio-cap-speed {{ color: #854D0E; border-color: #E6D08A; background: #FDF9EE; }}
[class*="st-key-rio-past-list"] {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}}
.rio-past-row {{
  margin: 0 0 0.7rem;
  border-radius: {RADIUS} !important;
  background: {SURFACE};
}}
.rio-past-rule {{ border-top: none; }}

.rio-stat-row {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 0.85rem 0 1.15rem;
}}
.rio-stat-tile {{
  padding: 0.9rem 1rem 1rem;
  min-height: 6.4rem;
  box-sizing: border-box;
}}
.rio-stat-tile .rio-mark-label {{
  margin: 0 !important;
  padding: 0 0 0.45rem !important;
}}
.rio-stat-tile .rio-stat-value {{
  margin: 0.1rem 0 0 !important;
  color: {TEXT} !important;
  font-size: 1.55rem !important;
  font-weight: 800 !important;
  letter-spacing: -0.04em !important;
  line-height: 1.15 !important;
}}
.rio-track-frame {{
  padding: 0.65rem 0.75rem 0.2rem;
}}
.rio-track-svg {{ color: {ACCENT}; }}
.rio-heart-label {{ fill: {TEXT} !important; }}
.rio-heart-dot {{ fill: {ACCENT} !important; }}
.rio-volume-line text, .rio-heart-line text {{ fill: {MUTED}; }}
.rio-progress-done .rio-progress-tick {{
  background: #C8C8C8 !important;
  border-color: #C8C8C8 !important;
}}
.rio-progress-current .rio-progress-tick {{
  background: {ACCENT} !important;
  border-color: {ACCENT} !important;
}}

.rio-cal-today {{
  border-color: {ACCENT} !important;
  background: rgba(226, 90, 50, 0.08) !important;
  box-shadow: inset 0 0 0 1px {ACCENT};
}}
.rio-cal-today .rio-cal-num {{ color: {HOVER} !important; }}

.rio-table tbody tr:nth-child(even) td {{
  background: rgba(14, 14, 14, 0.03);
}}

[class*="st-key-rio-nav"] {{
  background: {BG} !important;
  border-bottom: 1px solid {HAIRLINE} !important;
}}
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"] {{
  position: relative !important;
  border-bottom: none !important;
  color: {MUTED} !important;
}}
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"] p {{
  color: {MUTED} !important;
  font-weight: 500 !important;
}}
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"]:hover,
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"]:hover span,
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"]:hover p {{
  color: {TEXT} !important;
  background: transparent !important;
}}
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"],
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] p {{
  color: {INVERSE} !important;
  -webkit-text-fill-color: {INVERSE} !important;
  opacity: 1 !important;
  border-bottom-color: transparent !important;
}}
[class*="st-key-rio-sub-"][class*="-is-active"] [data-testid="stPageLink-NavLink"],
[class*="st-key-rio-sub-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-sub-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] p {{
  color: {TEXT} !important;
  -webkit-text-fill-color: {TEXT} !important;
  opacity: 1 !important;
  border-bottom-color: transparent !important;
}}
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"],
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"] p {{
  color: {TEXT} !important;
  font-family: {DISPLAY} !important;
  font-weight: 800 !important;
  letter-spacing: 0.14em !important;
}}
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"]::before {{
  content: "";
  width: 7px;
  height: 7px;
  margin-left: 0.35rem;
  border-radius: 99px;
  background: {ACCENT};
  order: 2;
}}
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"] {{
  background: {TEXT} !important;
  border-radius: 999px !important;
  padding: 0.48rem 0.95rem 0.48rem 0.8rem !important;
  gap: 0.45rem !important;
}}
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"] p,
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"]:hover,
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"]:hover span,
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"]:hover p {{
  color: {INK} !important;
  font-weight: 600 !important;
  font-size: 0.84rem !important;
  background: transparent !important;
}}
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"]::before {{
  content: "";
  width: 8px;
  height: 8px;
  border-radius: 99px;
  background: {ACCENT};
  flex: 0 0 auto;
}}
[class*="st-key-rio-start-session"] [data-testid="stPageLink-NavLink"]:hover {{
  background: #242424 !important;
}}

.stApp [data-testid="stBaseButton-primary"],
.stApp [data-testid="stFormSubmitButton"] button {{
  background: {ACCENT} !important;
  border: 1px solid {ACCENT} !important;
  border-radius: {BUTTON_RADIUS} !important;
  color: {INK} !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  box-shadow: none !important;
}}
.stApp [data-testid="stBaseButton-primary"] p,
.stApp [data-testid="stBaseButton-primary"] span,
.stApp [data-testid="stFormSubmitButton"] button p,
.stApp [data-testid="stFormSubmitButton"] button span {{
  color: {INK} !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
}}
.stApp [data-testid="stBaseButton-primary"]:hover,
.stApp [data-testid="stFormSubmitButton"] button:hover {{
  background: {HOVER} !important;
  border-color: {HOVER} !important;
  color: {INK} !important;
}}
[data-testid="stBaseButton-secondary"],
[data-testid="stDownloadButton"] button {{
  background: transparent !important;
  border: 1px solid {TEXT} !important;
  border-radius: {BUTTON_RADIUS} !important;
  color: {TEXT} !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}}
[data-testid="stBaseButton-secondary"] p,
[data-testid="stBaseButton-secondary"] span,
[data-testid="stDownloadButton"] button p,
[data-testid="stDownloadButton"] button span {{
  color: {TEXT} !important;
  font-weight: 600 !important;
}}
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stDownloadButton"] button:hover {{
  background: {BG} !important;
  border-color: {TEXT} !important;
  color: {TEXT} !important;
}}
.stApp [class*="st-key-rio-logout"] button,
.stApp [class*="st-key-rio-logout"] [data-testid="stBaseButton-secondary"],
.stApp [class*="st-key-rio-logout"] [data-testid="stBaseButton-primary"] {{
  background: transparent !important;
  border-width: 0 !important;
  border-style: none !important;
  border-color: transparent !important;
  border-radius: 0 !important;
  color: {MUTED} !important;
  min-height: 0 !important;
  height: auto !important;
  margin: 0 !important;
  padding: 0.15rem 0 0.28rem !important;
  font-size: 0.84rem !important;
  font-weight: 500 !important;
  letter-spacing: 0 !important;
  line-height: 1.3 !important;
  box-shadow: none !important;
}}
.stApp [class*="st-key-rio-logout"] button p,
.stApp [class*="st-key-rio-logout"] button span {{
  color: {MUTED} !important;
  font-size: 0.84rem !important;
  font-weight: 500 !important;
  letter-spacing: 0 !important;
}}
.stApp [class*="st-key-rio-logout"] button:hover,
.stApp [class*="st-key-rio-logout"] button:hover p,
.stApp [class*="st-key-rio-logout"] button:hover span {{
  background: transparent !important;
  border: none !important;
  color: {TEXT} !important;
}}

[class*="st-key-rio-goal-card"] [data-testid="stBaseButton-primary"],
[class*="st-key-rio-goal-card"] [data-testid="stFormSubmitButton"] button,
[class*="st-key-rio-auth-card"] [data-testid="stBaseButton-primary"],
[class*="st-key-rio-auth-card"] [data-testid="stFormSubmitButton"] button {{
  min-height: 3rem !important;
  margin-top: 0.85rem !important;
  font-size: 1rem !important;
  width: 100% !important;
  opacity: 1 !important;
}}
[class*="st-key-rio-goal-card"] .rio-hero,
[class*="st-key-rio-auth-card"] .rio-hero {{
  padding: 0.15rem 0 0.85rem !important;
}}
[class*="st-key-rio-goal-card"] .rio-hero h1,
[class*="st-key-rio-auth-card"] .rio-hero h1 {{
  font-size: 2.6rem !important;
}}
[data-testid="stTextInputRootElement"],
[data-testid="stDateInputField"],
[data-testid="stSelectbox"] [role="group"],
[data-testid="stNumberInputContainer"] {{
  background: {SURFACE} !important;
  border: 1px solid {HAIRLINE} !important;
  border-radius: 12px !important;
}}

[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
  background-color: {ACCENT} !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-border"] {{
  background-color: {HAIRLINE} !important;
}}
[data-testid="stTabs"] button[data-baseweb="tab"] {{
  background: transparent !important;
  color: {MUTED} !important;
  border-bottom: 2px solid transparent !important;
}}
[data-testid="stTabs"] button[data-baseweb="tab"] p,
[data-testid="stTabs"] button[data-baseweb="tab"] span {{
  color: {MUTED} !important;
  font-weight: 500 !important;
}}
[data-testid="stTabs"] button[aria-selected="true"],
[data-testid="stTabs"] button[aria-selected="true"] p,
[data-testid="stTabs"] button[aria-selected="true"] span {{
  color: {TEXT} !important;
  border-bottom-color: {ACCENT} !important;
}}

[data-testid="stExpander"] details {{
  {_CARD}
  overflow: hidden;
}}
[data-testid="stExpander"] summary {{
  background: transparent !important;
  color: {TEXT} !important;
  font-weight: 600 !important;
}}
[data-testid="stExpander"] summary:hover {{
  color: {TEXT} !important;
}}
[data-testid="stExpander"] svg {{ fill: {MUTED} !important; }}
[class*="st-key-rio-settings"] {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 0 0.75rem !important;
}}
[class*="st-key-rio-settings-danger"] [data-testid="stExpander"] details {{
  background: {SURFACE} !important;
  border: 1px solid #D64545 !important;
  box-shadow: {CARD_SHADOW} !important;
}}
.rio-danger-kicker {{
  margin: 0.4rem 0 0.35rem !important;
  color: #B42318 !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.14em !important;
  text-transform: uppercase;
}}
[class*="st-key-rio-settings-danger"] button,
[class*="st-key-rio-settings-danger"] [data-testid="stBaseButton-secondary"],
[class*="st-key-rio-settings-danger"] [data-testid="stBaseButton-primary"] {{
  background: transparent !important;
  border: 1px solid #D64545 !important;
  border-radius: {BUTTON_RADIUS} !important;
  color: #B42318 !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}}
[class*="st-key-rio-settings-danger"] button p,
[class*="st-key-rio-settings-danger"] button span {{
  color: #B42318 !important;
  font-weight: 600 !important;
}}
[class*="st-key-rio-settings-danger"] button:hover,
[class*="st-key-rio-settings-danger"] [data-testid="stBaseButton-secondary"]:hover {{
  background: #FDECEC !important;
  border-color: #D64545 !important;
  color: #8E1D14 !important;
}}

.rio-photo-credit {{
  width: fit-content;
  margin: 0.9rem auto 1.5rem !important;
  padding: 0.22rem 0.75rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid {HAIRLINE};
  color: {MUTED} !important;
  font-size: 0.78rem !important;
  font-weight: 400 !important;
  line-height: 1.4 !important;
  text-align: center;
}}
.rio-photo-credit-fixed {{
  position: fixed;
  z-index: 4;
  left: 0;
  right: 0;
  bottom: 0.85rem;
  pointer-events: none;
}}
.rio-about-banner {{
  position: relative;
  height: 36vh;
  min-height: 11rem;
  max-height: 22rem;
  margin: 0.35rem 0 1.15rem;
  border-radius: {RADIUS};
  overflow: hidden;
  background-color: {BG};
  background-size: cover;
  background-position: center;
  box-shadow: {CARD_SHADOW};
}}
.rio-about-shade {{
  position: absolute;
  inset: 0;
  --rio-legacy-shade: {LEGACY_SHADE};
  background: {SHADE};
}}
.rio-about-banner .rio-photo-credit {{
  position: absolute;
  left: 50%;
  right: auto;
  bottom: 0.7rem;
  z-index: 1;
  transform: translateX(-50%);
  margin: 0 !important;
}}

{motion_rules()}
{editorial_css()}

@media (max-width: 720px) {{
  .rio-lib, .rio-stat-row {{ grid-template-columns: 1fr; }}
  .rio-stat-tile .rio-stat-value {{ font-size: 1.25rem !important; }}
}}
</style>
"""
