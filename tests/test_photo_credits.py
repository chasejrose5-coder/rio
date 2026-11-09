# test_photo_credits.py — Home and Plan photos, and a credit on every photo.

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.hero_config import load_rotation
from ui.startup import PHOTO_CREDIT, startup_html
from ui.theme import (
    ABOUT_CREDIT,
    HOME_CREDIT,
    HOME_PHOTO,
    LOGIN_CREDIT,
    PLAN_CREDIT,
    PLAN_PHOTO,
    SHADE,
    START_CREDIT,
    SURFACE,
    asset_uri,
    home_on_photo_css,
    plan_hero_css,
    static_url,
)

HOME_SHA = "2ec5508dbb27f066617ad3aaf9c350ace6d0e88cca00b308cd74ce86fced1fc9"
PLAN_SHA = "a81c6e6b559d631c62b48953bb64dc4de7f0d63eeb78c92247675266b0ca93be"
HERO_CREDITS = (
    "Photo by RUN 4 FFWPU on Pexels",
    "Photo by Writchid Snipes on Pexels",
    "Photo by Ansey Photography on Pexels",
)


def _slice(source: str, start: str, end: str) -> str:
    begin = source.index(start)
    return source[begin : source.index(end, begin + 1)]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_home_and_plan_use_the_attached_photos_once_each() -> None:
    home_file = ROOT / "ui" / "assets" / HOME_PHOTO
    plan_file = ROOT / "ui" / "assets" / PLAN_PHOTO
    if _sha(home_file) != HOME_SHA or _sha(plan_file) != PLAN_SHA:
        raise AssertionError("a served photo is not the attached file")
    if HOME_PHOTO == PLAN_PHOTO or _sha(home_file) == _sha(plan_file):
        raise AssertionError("Home and Plan share a photo")
    if static_url(HOME_PHOTO) != "app/static/photos/home-aerial.jpg":
        raise AssertionError(static_url(HOME_PHOTO))
    if static_url(PLAN_PHOTO) != "app/static/photos/plan-curve.jpg":
        raise AssertionError(static_url(PLAN_PHOTO))
    if asset_uri(HOME_PHOTO) == asset_uri(PLAN_PHOTO):
        raise AssertionError("the static paths are the same")
    for name in ("home-aerial.jpg", "home-aerial-800.jpg", "plan-curve.jpg", "plan-curve-800.jpg"):
        file = ROOT / "ui" / "static" / "photos" / name
        if not file.is_file() or file.stat().st_size < 1000:
            raise AssertionError(name)
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    home = _slice(app, "def _paint_home_photo(", "def _home_credit(")
    plan = _slice(app, "def page_plan(", "def page_more(")
    library = _slice(app, "def page_library(", "def page_progress(")
    if "theme.HOME_PHOTO" not in home or "home_on_photo_css" not in home:
        raise AssertionError("Home does not paint the aerial")
    if "PLAN_PHOTO" in home or "plan_curve" in home or "plan-curve" in home:
        raise AssertionError("Home reuses the Plan photo")
    if "theme.PLAN_PHOTO" not in plan or "plan_hero_css" not in plan or "_with_plan_credit(" not in plan:
        raise AssertionError("Plan does not paint the track in the hero")
    if "HOME_PHOTO" in plan or "home_aerial" in plan or "home-aerial" in plan:
        raise AssertionError("Plan reuses the Home photo")
    for banned in (
        "HOME_PHOTO",
        "PLAN_PHOTO",
        "home_aerial",
        "plan_curve",
        "home-aerial",
        "plan-curve",
        "Gaby Lopez",
        "Jan van der Wolf",
        "fullscreen_css",
        "plan_hero_css",
        "home_on_photo_css",
    ):
        if banned in library:
            raise AssertionError(f"Library gained a photo: {banned}")
    css = (ROOT / "ui" / "static" / "app.css").read_text(encoding="utf-8")
    if "home-aerial" in css or "plan-curve" in css:
        raise AssertionError("the shared stylesheet paints a photo on every page")
    for path in ROOT.rglob("*"):
        if path.suffix.lower() == ".png" and "mock" in path.name.lower():
            raise AssertionError(path)


def test_the_new_photos_keep_the_shade_and_name_their_photographers() -> None:
    if HOME_CREDIT != "Photo by Gaby Lopez on Pexels":
        raise AssertionError(HOME_CREDIT)
    if PLAN_CREDIT != "Photo by Jan van der Wolf on Pexels":
        raise AssertionError(PLAN_CREDIT)
    home_css = home_on_photo_css(static_url(HOME_PHOTO))
    plan_css = plan_hero_css(static_url(PLAN_PHOTO))
    if SHADE not in home_css or SHADE not in plan_css:
        raise AssertionError("a photo lost the shade")
    if "photos/home-aerial.jpg" not in home_css or "photos/home-aerial-800.jpg" not in home_css:
        raise AssertionError("Home is missing the aerial")
    if ".stApp" not in home_css or SURFACE not in home_css:
        raise AssertionError("Home is not a page background with solid cards")
    if "photos/plan-curve.jpg" not in plan_css or "photos/plan-curve-800.jpg" not in plan_css:
        raise AssertionError("Plan is missing the track")
    if ".rio-hero" not in plan_css or ".stApp" in plan_css:
        raise AssertionError("the track is not limited to the Plan hero")
    if "home-aerial" in plan_css or "plan-curve" in home_css:
        raise AssertionError("the two photos crossed pages")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    dashboard = _slice(app, "def page_dashboard(", "def _cal_cell(")
    if dashboard.count("_home_credit()") != 3:
        raise AssertionError("Home can open without the aerial credit")
    plan = _slice(app, "def page_plan(", "def page_more(")
    if plan.count("_with_plan_credit(") != 4:
        raise AssertionError("a Plan hero has no credit")
    if "theme.PLAN_CREDIT" not in _slice(app, "def _with_plan_credit(", "def page_plan("):
        raise AssertionError("the Plan credit is not Jan van der Wolf")


def test_existing_photo_credits_stay_visible_and_creators_is_not_invented() -> None:
    if LOGIN_CREDIT != "Photo by Steve Pancrate on Pexels":
        raise AssertionError(LOGIN_CREDIT)
    if START_CREDIT != "Photo by Bohdan Hyrovych on Pexels":
        raise AssertionError(START_CREDIT)
    if ABOUT_CREDIT != "Photo by Botond Dobozi on Pexels":
        raise AssertionError(ABOUT_CREDIT)
    if PHOTO_CREDIT != "Photo by Giant Asparagus on Pexels":
        raise AssertionError(PHOTO_CREDIT)
    html = startup_html()
    if html.count(PHOTO_CREDIT) != 1:
        raise AssertionError("the splash credit changed")
    for credit in HERO_CREDITS:
        if credit in html:
            raise AssertionError(credit)
    credits = [row["credit"] for row in load_rotation()]
    if credits != list(HERO_CREDITS):
        raise AssertionError(credits)
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    for token in ("theme.LOGIN_CREDIT", "theme.START_CREDIT", "theme.ABOUT_CREDIT"):
        if token not in app:
            raise AssertionError(token)
    editor = _slice(app, "def _render_hero_editor(", "def _past_component(")
    if 'theme.credit_html(str(photo["credit"]))' not in editor:
        raise AssertionError("the startup frames have no visible credit")
    creators = _slice(app, "def page_creators(", "def page_admin(")
    if "Photo by" in creators:
        raise AssertionError("Creators invented a photographer")
    theme = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    for banned in ("Rudisha", "London 2012", "london-2012"):
        if banned in theme or banned in app:
            raise AssertionError(banned)


def main() -> None:
    test_home_and_plan_use_the_attached_photos_once_each()
    test_the_new_photos_keep_the_shade_and_name_their_photographers()
    test_existing_photo_credits_stay_visible_and_creators_is_not_invented()
    print("photo credits ok")


if __name__ == "__main__":
    main()
