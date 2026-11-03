# theme.py — one visual language for every RIO page.

"""Colors, type, glass, buttons, and photo backgrounds.

Pages pull from here so a card on Home matches the card on the startup
page. This module does not read a plan, label a workout, or call a model.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from html import escape
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"

TEXT = "#f4f4f4"
MUTED = "#d4d4d4"
QUIET = "#8f8f8f"
ACCENT = "#e25a32"
HOVER = "#ff7a45"
LIGHT = "#ffb089"
BG = "#000000"
INK = "#140c09"
FONT = '"Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif'
RADIUS = "10px"
BUTTON_RADIUS = "8px"
CARD_FILL = "rgba(0, 0, 0, 0.38)"
CARD_BORDER = "rgba(244, 244, 244, 0.22)"
CARD_SHADOW = "0 10px 30px rgba(0, 0, 0, 0.28)"
# Same dark wash as the startup page, including the middle stop.
SHADE = (
    "linear-gradient(180deg, rgba(0, 0, 0, 0.52) 0%, "
    "rgba(0, 0, 0, 0.64) 46%, rgba(0, 0, 0, 0.74) 100%)"
)

LOGIN_PHOTO = "login_floodlights.jpg"
START_PHOTO = "start_line.jpg"
ABOUT_PHOTO = "about_stadium.jpg"
LOGIN_CREDIT = "Photo by Steve Pancrate on Pexels"
START_CREDIT = "Photo by Bohdan Hyrovych on Pexels"
ABOUT_CREDIT = "Photo by Botond Dobozi on Pexels"

_GLASS = (
    f"background: {CARD_FILL} !important;"
    f"border: 1px solid {CARD_BORDER} !important;"
    f"border-radius: {RADIUS} !important;"
    f"box-shadow: {CARD_SHADOW} !important;"
    "backdrop-filter: blur(16px);"
    "-webkit-backdrop-filter: blur(16px);"
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


def _image(uri: str) -> str:
    return f'url("{uri}")' if uri else "none"


def fullscreen_rules(image: str) -> str:
    """Photo on .stApp, transparent shells, and the shared dark shade."""
    return f"""
html, body, .stApp {{
  min-height: 100vh !important;
}}
.stApp {{
  background-color: #050505 !important;
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
  background: {SHADE};
}}
"""


def fullscreen_css(uri: str) -> str:
    """Full-screen photo for Log in, Create account, and Start."""
    return "<style>" + fullscreen_rules(_image(uri)) + "</style>"


def primary_button_css(selector: str) -> str:
    """The orange Continue button, scoped to a container."""
    return f"""
{selector} button,
{selector} [data-testid="stBaseButton-primary"] {{
  background: {ACCENT} !important;
  border: 1px solid {ACCENT} !important;
  border-radius: {BUTTON_RADIUS} !important;
  color: {INK} !important;
  min-height: 2.8rem !important;
  padding: 0.45rem 1.5rem !important;
  font-size: 1rem !important;
  font-weight: 650 !important;
  letter-spacing: 0.03em !important;
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.35) !important;
}}
{selector} button p,
{selector} button span {{
  color: {INK} !important;
  font-size: 1rem !important;
  font-weight: 650 !important;
}}
{selector} button:hover,
{selector} [data-testid="stBaseButton-primary"]:hover {{
  background: {HOVER} !important;
  border-color: {HOVER} !important;
  color: {INK} !important;
}}
"""


def shade_html() -> str:
    """Dark overlay for a full-screen photo. Clicks pass through."""
    return '<div class="rio-page-shade" aria-hidden="true"></div>'


def credit_html(text: str, *, fixed: bool = False) -> str:
    """Small photo credit. Fixed sits on the bottom edge of the viewport."""
    kind = " rio-photo-credit-fixed" if fixed else ""
    return f'<p class="rio-photo-credit{kind}">{escape(text)}</p>'


def banner_html(uri: str, credit: str) -> str:
    """A short photo band. The credit sits on the dark end of the wash."""
    image = f"url('{uri}')" if uri else "none"
    return (
        f"<style>.rio-about-banner {{ background-image: {image}; }}</style>"
        '<div class="rio-about-banner">'
        '<div class="rio-about-shade" aria-hidden="true"></div>'
        f"{credit_html(credit)}"
        "</div>"
    )


def surface_css() -> str:
    """Glass, buttons, nav, tables, and charts, applied after the page CSS."""
    glass = (
        ".rio-card, .rio-daycard, .rio-mini, .rio-next, .rio-volume, .rio-heart, "
        ".rio-progress-list, .rio-track-facts, .rio-track-frame, .rio-phase, "
        ".rio-cal-session, .rio-stat-tile, .rio-lib-row, .rio-past-row, "
        "[class*='st-key-rio-week'], [class*='st-key-rio-result'], "
        "[class*='st-key-rio-goal-card'], [class*='st-key-rio-auth-card']"
    )
    return f"""
<style>
{glass} {{
  {_GLASS}
}}
.rio-card, .rio-daycard, .rio-mini, .rio-next, .rio-volume, .rio-heart,
.rio-progress-list, .rio-track-facts, [class*="st-key-rio-week"],
[class*="st-key-rio-result"] {{
  border-radius: {RADIUS} !important;
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
  border: 1px solid rgba(244, 244, 244, 0.28);
  color: {TEXT};
  font-size: 0.72rem;
  line-height: 1.3;
  letter-spacing: 0.03em;
  white-space: nowrap;
}}
.rio-cap-aerobic {{ color: #b9d4ff; border-color: rgba(140, 180, 240, 0.7); }}
.rio-cap-threshold {{ color: {LIGHT}; border-color: {ACCENT}; }}
.rio-cap-aerobic_power {{ color: {HOVER}; border-color: {HOVER}; }}
.rio-cap-speed_endurance {{ color: #ffd0b4; border-color: rgba(255, 176, 137, 0.8); }}
.rio-cap-anaerobic_capacity {{ color: #ffb4c4; border-color: rgba(226, 90, 120, 0.8); }}
.rio-cap-race_readiness {{ color: #ffe1a8; border-color: rgba(226, 176, 80, 0.85); }}
.rio-cap-max_velocity {{ color: #ffc4e4; border-color: rgba(230, 110, 170, 0.8); }}
.rio-cap-speed {{ color: #fff1b8; border-color: rgba(240, 200, 90, 0.8); }}
[class*="st-key-rio-past-list"] {{
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}}
.rio-past-row {{
  margin: 0 0 0.7rem;
  border-radius: {RADIUS} !important;
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
  font-size: 1.45rem !important;
  font-weight: 500 !important;
  letter-spacing: -0.03em !important;
  line-height: 1.2 !important;
}}
.rio-track-frame {{
  padding: 0.65rem 0.75rem 0.2rem;
}}
.rio-track-svg {{ color: {ACCENT}; }}

.rio-cal-today {{
  border-color: {ACCENT} !important;
  background: rgba(226, 90, 50, 0.24) !important;
  box-shadow: inset 0 0 0 1px {ACCENT};
}}
.rio-cal-today .rio-cal-num {{ color: {HOVER} !important; }}

.rio-table tbody tr:nth-child(even) td {{
  background: rgba(244, 244, 244, 0.06);
}}

[class*="st-key-rio-nav"] {{
  background: rgba(0, 0, 0, 0.72) !important;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(244, 244, 244, 0.12) !important;
}}
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] {{
  border-bottom: 2px solid {ACCENT} !important;
  border-bottom-color: {ACCENT} !important;
}}

.stApp [data-testid="stBaseButton-primary"],
.stApp [data-testid="stFormSubmitButton"] button {{
  background: {ACCENT} !important;
  border: 1px solid {ACCENT} !important;
  border-radius: {BUTTON_RADIUS} !important;
  color: {INK} !important;
  font-weight: 650 !important;
  letter-spacing: 0.03em !important;
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.35) !important;
}}
.stApp [data-testid="stBaseButton-primary"] p,
.stApp [data-testid="stBaseButton-primary"] span,
.stApp [data-testid="stFormSubmitButton"] button p,
.stApp [data-testid="stFormSubmitButton"] button span {{
  color: {INK} !important;
  font-weight: 650 !important;
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
  border: 1px solid rgba(244, 244, 244, 0.28) !important;
  border-radius: {BUTTON_RADIUS} !important;
  color: {MUTED} !important;
  font-weight: 500 !important;
  box-shadow: none !important;
}}
[data-testid="stBaseButton-secondary"] p,
[data-testid="stBaseButton-secondary"] span,
[data-testid="stDownloadButton"] button p,
[data-testid="stDownloadButton"] button span {{
  color: {MUTED} !important;
  font-weight: 500 !important;
}}
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stDownloadButton"] button:hover {{
  background: transparent !important;
  border-color: {ACCENT} !important;
  color: {LIGHT} !important;
}}
.stApp [class*="st-key-rio-logout"] button,
.stApp [class*="st-key-rio-logout"] [data-testid="stBaseButton-secondary"],
.stApp [class*="st-key-rio-logout"] [data-testid="stBaseButton-primary"] {{
  background: transparent !important;
  border-width: 0 !important;
  border-style: none !important;
  border-color: transparent !important;
  border-radius: 0 !important;
  color: {QUIET} !important;
  min-height: 0 !important;
  height: auto !important;
  margin: 0 !important;
  padding: 0.15rem 0 0.28rem !important;
  font-size: 0.84rem !important;
  font-weight: 400 !important;
  letter-spacing: 0 !important;
  line-height: 1.3 !important;
  box-shadow: none !important;
}}
.stApp [class*="st-key-rio-logout"] button p,
.stApp [class*="st-key-rio-logout"] button span {{
  color: {QUIET} !important;
  font-size: 0.84rem !important;
  font-weight: 400 !important;
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
[class*="st-key-rio-goal-card"] [data-testid="stFormSubmitButton"] button {{
  min-height: 3.35rem !important;
  margin-top: 0.85rem !important;
  font-size: 1.12rem !important;
  width: 100% !important;
}}
[class*="st-key-rio-goal-card"],
[class*="st-key-rio-auth-card"] {{
  padding: 1.25rem 1.3rem 1.15rem !important;
  margin: 0.2rem auto 0.8rem !important;
  max-width: 44rem;
  box-sizing: border-box;
}}
[class*="st-key-rio-goal-card"] .rio-hero,
[class*="st-key-rio-auth-card"] .rio-hero {{
  padding: 0.15rem 0 0.85rem !important;
}}
[class*="st-key-rio-goal-card"] .rio-hero h1,
[class*="st-key-rio-auth-card"] .rio-hero h1 {{
  font-size: 2.35rem !important;
}}
[class*="st-key-rio-auth-card"] {{
  max-width: 28rem;
}}
[data-testid="stTextInputRootElement"],
[data-testid="stDateInputField"],
[data-testid="stSelectbox"] [role="group"],
[data-testid="stNumberInputContainer"] {{
  background: rgba(0, 0, 0, 0.42) !important;
  border: 1px solid rgba(244, 244, 244, 0.22) !important;
  border-radius: {BUTTON_RADIUS} !important;
}}

[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
  background-color: {ACCENT} !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-border"] {{
  background-color: rgba(244, 244, 244, 0.16) !important;
}}
[data-testid="stTabs"] button[data-baseweb="tab"] {{
  background: transparent !important;
  color: {QUIET} !important;
  border-bottom: 2px solid transparent !important;
}}
[data-testid="stTabs"] button[data-baseweb="tab"] p,
[data-testid="stTabs"] button[data-baseweb="tab"] span {{
  color: {QUIET} !important;
  font-weight: 500 !important;
}}
[data-testid="stTabs"] button[aria-selected="true"],
[data-testid="stTabs"] button[aria-selected="true"] p,
[data-testid="stTabs"] button[aria-selected="true"] span {{
  color: {TEXT} !important;
  border-bottom-color: {ACCENT} !important;
}}

[data-testid="stExpander"] details {{
  {_GLASS}
  overflow: hidden;
}}
[data-testid="stExpander"] summary {{
  background: transparent !important;
  color: {TEXT} !important;
  font-weight: 500 !important;
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
  background: rgba(64, 12, 10, 0.72) !important;
  border: 1px solid rgba(214, 69, 69, 0.9) !important;
  box-shadow: 0 10px 30px rgba(80, 0, 0, 0.28) !important;
}}
.rio-danger-kicker {{
  margin: 0 0 0.35rem !important;
  color: #ffb4ae !important;
  font-size: 0.72rem !important;
  font-weight: 650 !important;
  letter-spacing: 0.14em !important;
  text-transform: uppercase;
}}
[class*="st-key-rio-settings-danger"] button,
[class*="st-key-rio-settings-danger"] [data-testid="stBaseButton-secondary"],
[class*="st-key-rio-settings-danger"] [data-testid="stBaseButton-primary"] {{
  background: transparent !important;
  border: 1px solid #d64545 !important;
  border-radius: {BUTTON_RADIUS} !important;
  color: #ffc9c4 !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}}
[class*="st-key-rio-settings-danger"] button p,
[class*="st-key-rio-settings-danger"] button span {{
  color: #ffc9c4 !important;
  font-weight: 600 !important;
}}
[class*="st-key-rio-settings-danger"] button:hover,
[class*="st-key-rio-settings-danger"] [data-testid="stBaseButton-secondary"]:hover {{
  background: #8d2a24 !important;
  border-color: #d64545 !important;
  color: {TEXT} !important;
}}

.rio-photo-credit {{
  width: fit-content;
  margin: 0.9rem auto 1.5rem !important;
  padding: 0.22rem 0.75rem;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.62);
  color: {TEXT} !important;
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
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.7);
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
  background-color: #050505;
  background-size: cover;
  background-position: center;
  box-shadow: {CARD_SHADOW};
}}
.rio-about-shade {{
  position: absolute;
  inset: 0;
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

@media (max-width: 720px) {{
  .rio-lib, .rio-stat-row {{ grid-template-columns: 1fr; }}
  .rio-stat-tile .rio-stat-value {{ font-size: 1.25rem !important; }}
}}
</style>
"""
