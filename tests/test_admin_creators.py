# test_admin_creators.py — admin gate, photo config, creators, startup frames.

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image

from ui.access import ENV_NAME, configured_admin_email, viewer_is_admin
from ui.accounts import account_rows, create_account
from ui.creators import CREATORS
from ui.hero_config import enabled_frames, load_rotation, save_rotation
from ui.startup import PHOTO_CREDIT, startup_css, startup_html


def _without_admin():
    previous = os.environ.get(ENV_NAME)
    os.environ[ENV_NAME] = ""
    return previous


def _restore(previous: str | None) -> None:
    if previous is None:
        os.environ.pop(ENV_NAME, None)
    else:
        os.environ[ENV_NAME] = previous


def test_nobody_is_admin_until_the_email_is_set() -> None:
    """A missing or blank admin email leaves every login as a regular account."""
    previous = _without_admin()
    try:
        if configured_admin_email() is not None:
            raise AssertionError("a blank admin email was kept")
        if viewer_is_admin("someone@example.com"):
            raise AssertionError("a blank setting made someone admin")
        os.environ[ENV_NAME] = "   "
        if configured_admin_email() is not None or viewer_is_admin("owner@example.com"):
            raise AssertionError("spaces were treated as an admin")
        os.environ[ENV_NAME] = "Owner@Example.com"
        if configured_admin_email() != "owner@example.com":
            raise AssertionError(configured_admin_email())
        if not viewer_is_admin("owner@example.com"):
            raise AssertionError("the matching login was not admin")
        if viewer_is_admin("other@example.com") or viewer_is_admin("") or viewer_is_admin(None):
            raise AssertionError("another login was admin")
    finally:
        _restore(previous)


def test_account_list_is_names_only() -> None:
    """The admin list has an email and a name. It cannot remove an account."""
    import tempfile

    previous = os.environ.get("RIO_ACCOUNTS_PATH")
    folder = tempfile.mkdtemp()
    path = Path(folder) / "accounts.json"
    try:
        email, _secret = create_account(path, "runner@example.com", "a-long-password", "Runner")
        rows = account_rows(path)
        if rows != [{"email": email, "name": "Runner"}]:
            raise AssertionError(rows)
        for row in rows:
            if set(row) != {"email", "name"}:
                raise AssertionError(row)
        text = path.read_text(encoding="utf-8")
        if "a-long-password" in text or "a-long-password" in str(rows):
            raise AssertionError("the password was stored or listed")
    finally:
        if previous is None:
            os.environ.pop("RIO_ACCOUNTS_PATH", None)
        else:
            os.environ["RIO_ACCOUNTS_PATH"] = previous
        import shutil

        shutil.rmtree(folder, ignore_errors=True)


def test_photo_order_credit_and_enabled_round_trip(tmp_path: Path | None = None) -> None:
    """Reorder, hide, and edit a credit. The picture file stays put."""
    import tempfile

    folder = Path(tempfile.mkdtemp()) if tmp_path is None else tmp_path
    path = folder / "hero_rotation.json"
    try:
        rows = load_rotation()
        if [row["id"] for row in rows] != [
            "run-4-ffwpu",
            "writchid-snipes",
            "ansey-photography",
        ]:
            raise AssertionError([row["id"] for row in rows])
        if [row["credit"] for row in rows] != [
            "Photo by RUN 4 FFWPU on Pexels",
            "Photo by Writchid Snipes on Pexels",
            "Photo by Ansey Photography on Pexels",
        ]:
            raise AssertionError(rows)
        flipped = [
            {"id": rows[2]["id"], "enabled": False, "credit": "Photo by Ansey Photography on Pexels"},
            {"id": rows[0]["id"], "enabled": True, "credit": "Edited credit line"},
            {"id": rows[1]["id"], "enabled": True, "credit": rows[1]["credit"]},
        ]
        saved = save_rotation(flipped, path)
        if [row["id"] for row in saved] != [
            "ansey-photography",
            "run-4-ffwpu",
            "writchid-snipes",
        ]:
            raise AssertionError(saved)
        if saved[0]["enabled"] is not False or saved[0]["file"] != "hero_race.jpg":
            raise AssertionError(saved[0])
        if saved[1]["credit"] != "Edited credit line" or saved[1]["file"] != "hero_run.jpg":
            raise AssertionError(saved[1])
        again = load_rotation(path)
        if again != saved:
            raise AssertionError(again)
        try:
            save_rotation(flipped[:2], path)
        except ValueError:
            pass
        else:
            raise AssertionError("a short list was stored")
        try:
            save_rotation(
                [
                    {"id": row["id"], "enabled": True, "credit": "  "}
                    for row in rows
                ],
                path,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("a blank credit was stored")
    finally:
        if tmp_path is None:
            import shutil

            shutil.rmtree(folder, ignore_errors=True)


def test_startup_frames_and_creators_stay_in_place() -> None:
    """Startup uses the track photo only. The stored photo list stays editable."""
    frames = enabled_frames()
    if len(frames) != 3:
        raise AssertionError(frames)
    html = startup_html()
    css = startup_css()
    if html.count(PHOTO_CREDIT) != 1:
        raise AssertionError("the startup credit is not the track photo alone")
    for credit in (
        "Photo by RUN 4 FFWPU on Pexels",
        "Photo by Writchid Snipes on Pexels",
        "Photo by Ansey Photography on Pexels",
    ):
        if credit in html or credit in css:
            raise AssertionError(credit)
    if "rio-hero-frame" in html or "rio-hero-frame" in css:
        raise AssertionError("the startup page still rotates")
    for piece in (
        "data:image/jpeg;base64,",
        "background-size: cover",
        "rgba(0, 0, 0, 0.64)",
        "RIO",
        "Your Race, Your Plan, Your Result",
    ):
        if piece not in html and piece not in css:
            raise AssertionError(piece)
    for frame in frames:
        image = Image.open(frame["file"])
        width, _height = image.size
        if width < 2000 or width > 2600:
            raise AssertionError((frame["file"], image.size))
    names = [person["name"] for person in CREATORS]
    if names != ["Chase Rose", "Jay Rose"]:
        raise AssertionError(names)
    for person in CREATORS:
        if "Editable placeholder text." not in person["bio"]:
            raise AssertionError(person)
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    admin = app[app.index("def page_admin(") : app.index("\ndef ", app.index("def page_admin(") + 1)]
    if admin.index("viewer_is_admin(") > admin.index("account_rows("):
        raise AssertionError("the account list is not behind the admin check")
    if "st.switch_page(" not in admin or "st.stop()" not in admin:
        raise AssertionError("a regular login can stay on admin")
    nav = app[app.index("_NAV_PAGES[:]") : app.index("st.navigation(")]
    if "viewer_is_admin(" not in nav or '("Admin", _admin_page)' not in nav:
        raise AssertionError("the admin tab is not tied to the admin email")
    if '("Creators", st.Page(_with_plan(page_creators), title="Creators", url_path="creators"))' not in app:
        raise AssertionError("Creators is not beside About")
    about = '("About", st.Page(_with_plan(page_about), title="About", url_path="about"))'
    if about not in app:
        raise AssertionError("About moved")
    if "Chase Rose" not in app or "Jay Rose" not in app:
        raise AssertionError("the creators are not on the page")
    theme = (ROOT / "ui" / "theme.py").read_text(encoding="utf-8")
    for name in ("hero_run.jpg", "hero_blocks.jpg", "hero_race.jpg"):
        if name in theme:
            raise AssertionError(name)
    access = (ROOT / "ui" / "access.py").read_text(encoding="utf-8")
    if "@" in access or "@" in admin:
        raise AssertionError("an email was written into the admin gate")


def main() -> None:
    test_nobody_is_admin_until_the_email_is_set()
    test_account_list_is_names_only()
    test_photo_order_credit_and_enabled_round_trip()
    test_startup_frames_and_creators_stay_in_place()
    print("admin creators ok")


if __name__ == "__main__":
    main()
