# test_audit_ui.py — splash stability, photo weight, and the Nov 9 fixes.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.startup import startup_css, startup_html
from ui.theme import (
    HOME_CREDIT,
    HOME_PHOTO,
    LOGIN_CREDIT,
    home_on_photo_css,
    motion_rules,
    plan_hero_css,
    static_url,
)

PHOTOS = ROOT / "ui" / "static" / "photos"
WEBP = {
    "home-aerial.webp": 340_000,
    "home-aerial-800.webp": 150_000,
    "home-aerial-480.webp": 80_000,
    "plan-curve.webp": 170_000,
    "plan-curve-800.webp": 50_000,
}


def _contrast(fg: str, bg: str) -> float:
    def channel(pair: str) -> float:
        value = int(pair, 16) / 255
        if value <= 0.03928:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    def lum(hex_color: str) -> float:
        text = hex_color.removeprefix("#")
        red, green, blue = channel(text[0:2]), channel(text[2:4]), channel(text[4:6])
        return 0.2126 * red + 0.7152 * green + 0.0722 * blue

    lighter, darker = sorted((lum(fg), lum(bg)))
    return (darker + 0.05) / (lighter + 0.05)


def test_splash_reserves_space_and_fades_after_layout() -> None:
    css = startup_css()
    html = startup_html()
    if len(css.encode()) > 80_000:
        raise AssertionError(len(css.encode()))
    for token in (
        "rio-splash-photo",
        "rio-splash-stage",
        "rio-splash-button-slot",
        "aspect-ratio: 16 / 9",
        "min-height:28rem",
        "startup-track-800.webp",
        "rel=\"preload\"",
    ):
        if token not in html and token not in css:
            raise AssertionError(token)
    if "animation: none !important;" not in css or ".rio-founder-words" not in css:
        raise AssertionError("the quote still waits on its own fade")
    if "rio-settled" not in css or "translate3d" not in css:
        raise AssertionError("the splash fade does not wait for layout")
    rules = motion_rules()
    if "from { opacity: 0; transform: translate3d(0, 8px, 0); }" not in rules:
        raise AssertionError("rio-fade is not opacity and transform")
    if "width:" in rules.split("@keyframes rio-fade")[1].split("}")[0]:
        raise AssertionError("rio-fade changes layout")
    if "prefers-reduced-motion: reduce" not in rules or "animation: none !important;" not in rules:
        raise AssertionError("reduced motion was dropped")
    if "rio-fade 200ms" not in rules:
        raise AssertionError("the section fade is not in the 150 to 250ms range")
    source = (ROOT / "ui" / "startup.py").read_text(encoding="utf-8")
    if "unsafe_allow_javascript=True" not in source or "rio-settled" not in source:
        raise AssertionError("the fade never starts after layout")


def test_home_and_plan_photos_are_lighter_and_the_credit_is_readable() -> None:
    for name, limit in WEBP.items():
        file = PHOTOS / name
        if not file.is_file() or file.stat().st_size > limit or file.stat().st_size < 1000:
            raise AssertionError((name, file.stat().st_size if file.is_file() else 0))
    home_jpg = (PHOTOS / "home-aerial.jpg").stat().st_size
    plan_jpg = (PHOTOS / "plan-curve.jpg").stat().st_size
    if (PHOTOS / "home-aerial.webp").stat().st_size >= home_jpg:
        raise AssertionError("the home webp is not lighter")
    if (PHOTOS / "plan-curve.webp").stat().st_size >= plan_jpg:
        raise AssertionError("the plan webp is not lighter")
    home_css = home_on_photo_css(static_url(HOME_PHOTO))
    plan_css = plan_hero_css(static_url("plan_curve.jpg"))
    for token in (
        "photos/home-aerial.jpg",
        "photos/home-aerial-800.jpg",
        "photos/home-aerial.webp",
        "photos/home-aerial-480.webp",
        "background-attachment: fixed, fixed",
        "background-attachment: scroll, scroll",
        "#121110",
        "#F4F1EC",
    ):
        if token not in home_css:
            raise AssertionError(token)
    if _contrast("#F4F1EC", "#121110") < 4.5:
        raise AssertionError(_contrast("#F4F1EC", "#121110"))
    if HOME_CREDIT != "Photo by Gaby Lopez on Pexels":
        raise AssertionError(HOME_CREDIT)
    if "photos/plan-curve.webp" not in plan_css or "background-attachment: scroll" not in plan_css:
        raise AssertionError("Plan lost the lighter track")
    if "home-aerial" in plan_css or "plan-curve" in home_css:
        raise AssertionError("the photos crossed pages")


def test_login_credit_is_the_recorded_name_and_chase_stays_blank() -> None:
    if LOGIN_CREDIT != "Photo by Steve Pancrate on Pexels":
        raise AssertionError(LOGIN_CREDIT)
    theme = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    if "0c4818c" not in theme:
        raise AssertionError("the login credit has no recorded source")
    cloud = (ROOT / "ui" / "cloud_ui.py").read_text(encoding="utf-8")
    if "LOGIN_CREDIT" not in cloud or "_paint_login_credit()" not in cloud:
        raise AssertionError("the live log-in screen still has no credit")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    creators = app[app.index("def page_creators(") : app.index("def page_admin(")]
    if "Photo by" in creators:
        raise AssertionError("Creators invented a photographer")


def test_small_fixes_keep_every_control() -> None:
    css = (ROOT / "ui" / "static" / "app.css").read_text(encoding="utf-8")
    behind = css[css.index("[class*=\"st-key-rio-done-behind\"] button,") :]
    behind = behind[: behind.index("[class*=\"st-key-rio-done-time\"]")]
    if "\n  color: #C2461F" in behind or "\n  color:#C2461F" in behind:
        raise AssertionError("Behind still uses the button orange as text")
    if "#FFFFFF" not in behind or "#C2461F" not in behind:
        raise AssertionError("Behind lost the white-on-button-orange fill")
    if "stIconMaterial" not in css or "keyboard_arrow_right" in css:
        raise AssertionError("the arrow words are still the icon")
    if "rio-strava-settings" not in css or "text-decoration: underline" not in css:
        raise AssertionError("the Strava line is not a link")
    if _contrast("#A63C1A", "#FFFCF7") < 4.5:
        raise AssertionError(_contrast("#A63C1A", "#FFFCF7"))
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    marker = 'label="Connect Strava in Settings"'
    activity = app[app.index(marker) - 280 : app.index(marker) + 120]
    if "rio-strava-settings" not in activity or 'icon=""' not in activity:
        raise AssertionError(activity)
    easy = (ROOT / "ui" / "easy_pace.py").read_text(encoding="utf-8")
    if "max-width: 36rem" in easy or "margin: -0.35rem" in easy:
        raise AssertionError("the easy-pace card is still the narrow tight one")
    if "width: 100%" not in easy or "0.7rem 0 1rem" not in easy:
        raise AssertionError("the easy-pace stack was not evened out")
    if "rio-plan-view-" not in app:
        raise AssertionError("a plan section does not fade in")


def main() -> None:
    test_splash_reserves_space_and_fades_after_layout()
    test_home_and_plan_photos_are_lighter_and_the_credit_is_readable()
    test_login_credit_is_the_recorded_name_and_chase_stays_blank()
    test_small_fixes_keep_every_control()
    print("audit ui ok")


if __name__ == "__main__":
    main()
