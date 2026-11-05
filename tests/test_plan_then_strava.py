# test_plan_then_strava.py — the card after Generate, and the shared connect link.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.cloud_store import reset_memory_directory
from ui.intro import STEPS, guide_html
from ui.plan_strava import prompt_seen_value, should_offer_strava


def test_the_card_follows_a_successful_generate() -> None:
    if not should_offer_strava(just_generated=True, connected=False, dismissed=False):
        raise AssertionError("a new plan did not offer Strava")
    if should_offer_strava(just_generated=True, connected=True, dismissed=False):
        raise AssertionError("a connected account was prompted")
    if should_offer_strava(just_generated=True, connected=False, dismissed=True):
        raise AssertionError("Not now did not hide the card")
    if should_offer_strava(just_generated=False, connected=False, dismissed=False):
        raise AssertionError("the card showed before a plan was generated")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    start = app[app.index("def page_start(") : app.index("def _session_activity(")]
    if "_generate_season(" not in start or "_arm_strava_prompt()" not in start:
        raise AssertionError("generate does not arm the Strava card")
    arm_at = start.index("_arm_strava_prompt()")
    gen_at = start.index("_generate_season(")
    if arm_at < gen_at:
        raise AssertionError("the card is armed before generation succeeds")
    home = app[app.index("def page_dashboard(") : app.index("def _cal_cell(")]
    if "_maybe_strava_prompt()" not in home:
        raise AssertionError("home does not show the card")


def test_connect_uses_the_settings_oauth_path() -> None:
    source = (ROOT / "ui" / "strava_ui.py").read_text(encoding="utf-8")
    prompt = source[source.index("def render_plan_prompt(") : source.index("def prepare_activity(")]
    button = source[source.index("def render_connect_button(") : source.index("def render_plan_prompt(")]
    if "connect_url()" not in prompt or "connect_url()" not in button:
        raise AssertionError("Connect does not share the Settings OAuth path")
    if 'st.link_button(\n            "Connect Strava"' not in prompt and 'st.link_button("Connect Strava"' not in prompt:
        raise AssertionError(prompt)
    if 'type="primary"' not in prompt or 'st.button("Not now"' not in prompt:
        raise AssertionError("the card buttons are missing")
    if "Your plan is ready." not in prompt or "Connect Strava so your runs show up." not in prompt:
        raise AssertionError("the card copy is missing")
    if 'st.link_button("Connect with Strava"' not in button:
        raise AssertionError("Settings lost its connect button")


def test_not_now_is_stored_beside_intro_seen() -> None:
    directory = reset_memory_directory()
    session = directory.sign_up("ada@example.com", "long-password", "Ada")
    if directory.load_bundle(session["access_token"])["profile"].get("strava_prompt_seen") is True:
        raise AssertionError("a new account already dismissed the card")
    directory.save_strava_prompt_seen(session["access_token"], True)
    kept = directory.load_bundle(session["access_token"])["profile"]
    if kept.get("strava_prompt_seen") is not True or kept.get("intro_seen") is True:
        raise AssertionError(kept)
    if prompt_seen_value({"user_metadata": {}}) is not None:
        raise AssertionError("a missing flag looked stored")
    if prompt_seen_value({"user_metadata": {"strava_prompt_seen": True}}) is not True:
        raise AssertionError("a stored dismissal was dropped")
    if prompt_seen_value({"user_metadata": {"intro_seen": True, "strava_prompt_seen": False}}) is not False:
        raise AssertionError("a false dismissal was treated as seen")
    html = guide_html()
    for title, body in STEPS:
        if title not in html or body not in html:
            raise AssertionError("the welcome guide steps changed")


def main() -> None:
    test_the_card_follows_a_successful_generate()
    test_connect_uses_the_settings_oauth_path()
    test_not_now_is_stored_beside_intro_seen()
    print("plan then strava ok")


if __name__ == "__main__":
    main()
