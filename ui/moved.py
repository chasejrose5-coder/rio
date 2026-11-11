# moved.py — the screen in front of the old Streamlit app.

"""RIO has a new home. This page does not sign in, load a plan, or call Strava.

streamlit_app.py draws this and then stops. The old screens are still in
that file. They run again if those two lines are removed.

The button and the address are not in the Streamlit app document. A click
there is handled by the app frame, which loads the new site inside the
Cloud iframe. st.iframe puts them in a nested srcdoc document. Clicks in
that document do not reach the app's handlers.

Streamlit 1.66.1 sandboxes that iframe from
static/static/js/IFrameUtil.*.js:

    allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox
    allow-same-origin allow-scripts allow-downloads

Community Cloud's outer iframe uses the same list. Both include
allow-popups and allow-popups-to-escape-sandbox, so a new tab can open
and leave the sandbox. Neither includes allow-top-navigation, so the top
window cannot be navigated. The button is a form that asks for a new tab. The submit gesture also
calls window.open. Chrome returns null from that call when the feature
string includes noopener, even if the tab opened, so the opener is
cleared afterward and the form is cancelled only when a window comes
back. If the call is blocked, the form still opens the tab. Copy link
is there when both are blocked.

st.components.v1.html is the deprecated name of this same iframe.
st.iframe is the 1.66.1 call, with height="content" so the frame matches
the page instead of a fixed box.
"""

from __future__ import annotations

from html import escape
from json import dumps

import streamlit as st

from ui.theme import (
    ACCENT,
    BUTTON,
    BUTTON_HOVER,
    DISPLAY,
    FONT,
    HAIRLINE,
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
COPY_LABEL = "Copy link"
FASTER = "The new site is faster, with more features."
ACCOUNT = "Your account is already there. Sign in with the same email and password."
OWNED = "Runner Intelligence Owned"


def moved_html() -> str:
    """The page inside the nested iframe: form, address, and copy control."""
    url = escape(NEW_HOME, quote=True)
    home = dumps(NEW_HOME)
    return f"""
<style>
{font_css()}
html, body {{
  margin: 0;
  padding: 0;
  background: {PAPER};
  color: {TEXT};
}}
.rio-moved,
.rio-moved p,
.rio-moved a,
.rio-moved button {{
  font-family: {FONT};
  word-break: normal;
  overflow-wrap: normal;
}}
.rio-moved {{
  margin: 0;
  max-width: 38rem;
  text-align: left;
  color: {TEXT};
}}
.rio-moved .rio-moved-mark {{
  margin: 0 0 0.35rem;
  color: {ACCENT};
  font-family: {DISPLAY};
  font-weight: 800;
  font-size: var(--rio-mark, clamp(72px, 16vw, 148px));
  letter-spacing: -0.065em;
  line-height: 0.78;
}}
.rio-moved .rio-moved-owned {{
  margin: 0 0 1.6rem;
  color: {MUTED};
  font-family: {DISPLAY};
  font-weight: 700;
  font-size: var(--rio-owned, clamp(0.95rem, 1.6vw, 1.12rem));
  letter-spacing: 0.08em;
  line-height: 1.3;
}}
.rio-moved h1 {{
  margin: 0 0 0.85rem;
  padding: 0;
  color: {TEXT};
  font-family: {DISPLAY};
  max-width: 12ch;
  font-size: var(--rio-title, clamp(36px, 5.2vw, 64px));
  font-weight: 800;
  letter-spacing: -0.045em;
  line-height: 0.94;
}}
.rio-moved-lead {{
  margin: 0 0 0.7rem;
  color: {TEXT};
  font-size: var(--rio-lead, clamp(1.15rem, 2vw, 1.4rem));
  font-weight: 500;
  line-height: 1.4;
}}
.rio-moved-account {{
  margin: 0 0 1.7rem;
  max-width: 34rem;
  color: {TEXT};
  font-size: 1.05rem;
  font-weight: 400;
  line-height: 1.5;
}}
.rio-moved-action {{
  margin: 0 0 0.95rem;
}}
button.rio-moved-go,
button.rio-moved-go:hover,
button.rio-moved-go:focus,
button.rio-moved-go:active {{
  appearance: none;
  -webkit-appearance: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  min-height: 3.4rem;
  margin: 0;
  padding: 0.9rem 1.7rem;
  background: {BUTTON};
  background-color: {BUTTON};
  border: 1px solid {BUTTON};
  border-radius: 999px;
  color: {INK};
  font-family: {FONT};
  font-size: 1.15rem;
  font-weight: 600;
  letter-spacing: 0;
  line-height: 1.2;
  text-decoration: none;
  box-shadow: none;
  cursor: pointer;
}}
button.rio-moved-go:hover {{
  background: {BUTTON_HOVER};
  background-color: {BUTTON_HOVER};
  border-color: {BUTTON_HOVER};
  color: {INK};
}}
.rio-moved-url {{
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem 0.9rem;
  margin: 0;
  font-size: 1rem;
  line-height: 1.45;
}}
.rio-moved-url a,
.rio-moved-url a:visited {{
  color: {MUTED};
  font-weight: 500;
  text-decoration: underline;
  text-underline-offset: 0.18em;
  overflow-wrap: anywhere;
  user-select: text;
  -webkit-user-select: text;
  cursor: pointer;
}}
button.rio-moved-copy {{
  appearance: none;
  -webkit-appearance: none;
  margin: 0;
  padding: 0.35rem 0.85rem;
  background: transparent;
  border: 1px solid {HAIRLINE};
  border-radius: 999px;
  color: {TEXT};
  font-family: {FONT};
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.2;
  cursor: pointer;
}}
button.rio-moved-copy:hover {{
  border-color: {TEXT};
}}
.rio-moved-copy-status {{
  color: {TEXT};
  font-size: 0.95rem;
  font-weight: 600;
}}
html.rio-narrow .rio-moved h1 {{
  max-width: 11ch;
}}
html.rio-narrow button.rio-moved-go {{
  width: 100%;
}}
{focus_css()}
</style>
<script>
(function () {{
  function clamp(value, min, max) {{
    return Math.max(min, Math.min(max, value));
  }}
  function applyViewport() {{
    var width = 1280;
    try {{
      width = window.parent.innerWidth || width;
    }} catch (err) {{
      width = window.innerWidth || width;
    }}
    var root = document.documentElement;
    root.style.setProperty("--rio-mark", clamp(width * 0.16, 72, 148) + "px");
    root.style.setProperty("--rio-owned", clamp(width * 0.016, 15.2, 17.92) + "px");
    root.style.setProperty("--rio-title", clamp(width * 0.052, 36, 64) + "px");
    root.style.setProperty("--rio-lead", clamp(width * 0.02, 18.4, 22.4) + "px");
    root.classList.toggle("rio-narrow", width <= 640);
  }}
  applyViewport();
  try {{
    window.parent.addEventListener("resize", applyViewport);
  }} catch (err) {{}}

  function bind() {{
    var home = {home};
    var form = document.getElementById("rio-moved-form");
    if (form) {{
      form.addEventListener("submit", function (event) {{
        var opened = null;
        try {{
          // The noopener feature makes Chrome return null even when the
          // tab opens, so the form would open a second tab. Null the
          // opener after a normal open instead.
          opened = window.open(home, "_blank");
        }} catch (err) {{
          opened = null;
        }}
        if (opened) {{
          try {{
            opened.opener = null;
          }} catch (err) {{}}
          event.preventDefault();
        }}
      }});
    }}
    var copy = document.getElementById("rio-moved-copy");
    var status = document.getElementById("rio-moved-copy-status");
    if (!copy || !status) {{
      return;
    }}
    function show(message) {{
      status.textContent = message;
    }}
    function selectAddress() {{
      var link = document.getElementById("rio-moved-link");
      if (!link) {{
        return;
      }}
      var range = document.createRange();
      range.selectNodeContents(link);
      var selection = window.getSelection();
      if (!selection) {{
        return;
      }}
      selection.removeAllRanges();
      selection.addRange(range);
    }}
    function fallback() {{
      var area = document.createElement("textarea");
      area.value = home;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.top = "0";
      area.style.left = "0";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.focus();
      area.select();
      var copied = false;
      try {{
        copied = document.execCommand("copy");
      }} catch (err) {{
        copied = false;
      }}
      document.body.removeChild(area);
      if (copied) {{
        show("Copied");
        return;
      }}
      selectAddress();
      show("Address selected. Copy it.");
    }}
    copy.addEventListener("click", function () {{
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(home).then(function () {{
          show("Copied");
        }}, fallback);
        return;
      }}
      fallback();
    }});
  }}
  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", bind);
  }} else {{
    bind();
  }}
}})();
</script>
<section class="rio-moved">
  <p class="rio-moved-mark">RIO</p>
  <p class="rio-moved-owned">{escape(OWNED)}</p>
  <h1>{escape(HEADLINE)}</h1>
  <p class="rio-moved-lead">{escape(FASTER)}</p>
  <p class="rio-moved-account">{escape(ACCOUNT)}</p>
  <form id="rio-moved-form" class="rio-moved-action" action="{url}" method="GET" target="_blank" rel="noopener noreferrer">
    <button class="rio-moved-go" type="submit">{escape(BUTTON_LABEL)}</button>
  </form>
  <p class="rio-moved-url">
    <a id="rio-moved-link" href="{url}" target="_blank" rel="noopener noreferrer">{escape(NEW_HOME)}</a>
    <button id="rio-moved-copy" class="rio-moved-copy" type="button">{escape(COPY_LABEL)}</button>
    <span id="rio-moved-copy-status" class="rio-moved-copy-status" role="status" aria-live="polite"></span>
  </p>
</section>
"""


def moved_css() -> str:
    """Paper page, hidden Streamlit chrome, and no box around the iframe."""
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
iframe.stIFrame,
[data-testid="stIFrame"] {{
  display: block !important;
  border: none !important;
  border-radius: 0 !important;
  outline: none !important;
  box-shadow: none !important;
  background: {PAPER} !important;
  background-color: {PAPER} !important;
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"],
  .block-container {{
    padding: 4.25rem 1.25rem 3rem !important;
  }}
}}
</style>
"""


def render_moved() -> None:
    """Draw the moved screen. The caller stops the script after this."""
    st.markdown(moved_css(), unsafe_allow_html=True)
    # Nested srcdoc iframe. Same sandbox as components.v1.html in 1.66.1.
    # height="content" sizes the frame to this page.
    st.iframe(
        moved_html(),
        width="stretch",
        height="content",
        alt="RIO has a new home",
    )
