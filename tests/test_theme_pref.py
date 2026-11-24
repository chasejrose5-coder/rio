# test_theme_pref.py — theme rides the existing settings save.

"""One field, light or dark or system. A missing value is system.

The same settings path writes it. No other preference moves.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from ui.accounts import create_account, read_local
from ui.cloud_store import MemoryDirectory
from ui.settings import normalize


def test_a_blank_theme_is_system_and_the_three_values_stay() -> None:
    if normalize({})["theme"] != "system":
        raise AssertionError(normalize({}))
    if normalize({"theme": "light"})["theme"] != "light":
        raise AssertionError("light was dropped")
    if normalize({"theme": "dark"})["theme"] != "dark":
        raise AssertionError("dark was dropped")
    if normalize({"theme": "neon"})["theme"] != "system":
        raise AssertionError("a bad theme was stored")
    kept = normalize({"theme": "dark", "pace_units": "km", "date_format": "iso"})
    if kept["pace_units"] != "km" or kept["date_format"] != "iso" or kept["theme"] != "dark":
        raise AssertionError(kept)


def test_local_settings_save_theme_and_leave_the_rest(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    email, _seal = create_account(path, "ada@example.com", "correct-horse", "Ada")
    client = TestClient(
        create_app(directory=None, accounts=path, frontend_origin="http://localhost:3000", load_env=False),
        base_url="https://testserver",
    )
    signed = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    before = client.get("/auth/me").json()["prefs"]
    if before["theme"] != "system":
        raise AssertionError(before)
    saved = client.patch("/settings", json={"theme": "dark"})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    prefs = saved.json()["prefs"]
    if prefs["theme"] != "dark" or prefs["pace_units"] != before["pace_units"]:
        raise AssertionError(prefs)
    if prefs["date_format"] != before["date_format"] or prefs["compact"] != before["compact"]:
        raise AssertionError(prefs)
    again = client.get("/auth/me").json()["prefs"]
    if again["theme"] != "dark":
        raise AssertionError(again)
    stored = read_local(path, email) or {}
    if stored.get("settings", {}).get("theme") != "dark":
        raise AssertionError(stored)
    refused = client.patch("/settings", json={"theme": "neon"})
    if refused.status_code != 400:
        raise AssertionError(refused.text)
    if client.get("/auth/me").json()["prefs"]["theme"] != "dark":
        raise AssertionError("a bad theme replaced the saved one")


def test_hosted_settings_save_theme_on_the_same_user(monkeypatch) -> None:
    monkeypatch.delenv("RIO_STRAVA_CLIENT_ID", raising=False)
    directory = MemoryDirectory()
    directory.sign_up("ada@example.com", "correct-horse", "Ada")
    client = TestClient(
        create_app(directory=directory, accounts=None, frontend_origin="http://localhost:3000", load_env=False),
        base_url="https://testserver",
    )
    signed = client.post("/auth/sign-in", json={"email": "ada@example.com", "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    if client.get("/auth/me").json()["prefs"]["theme"] != "system":
        raise AssertionError("a new account did not default to system")
    saved = client.patch("/settings", json={"theme": "light", "date_format": "iso"})
    if saved.status_code != 200:
        raise AssertionError(saved.text)
    prefs = saved.json()["prefs"]
    if prefs["theme"] != "light" or prefs["date_format"] != "iso":
        raise AssertionError(prefs)
    user = directory.users[directory.by_email["ada@example.com"]]
    if user.get("theme") != "light" or user.get("date_format") != "iso":
        raise AssertionError(user)
    kept = client.patch("/settings", json={"compact": True})
    if kept.status_code != 200 or kept.json()["prefs"]["theme"] != "light":
        raise AssertionError(kept.text)
    if kept.json()["prefs"]["compact"] is not True:
        raise AssertionError(kept.json()["prefs"])


def _theme_cookies(response) -> list[str]:
    return [item for item in response.headers.get_list("set-cookie") if item.lower().startswith("rio_theme=")]


def test_the_session_read_sets_a_readable_theme_cookie(tmp_path: Path) -> None:
    path = tmp_path / "accounts.json"
    email, _seal = create_account(path, "ada@example.com", "correct-horse", "Ada")
    client = TestClient(
        create_app(directory=None, accounts=path, frontend_origin="http://localhost:3000", load_env=False),
        base_url="https://testserver",
    )
    signed = client.post("/auth/sign-in", json={"email": email, "password": "correct-horse"})
    if signed.status_code != 200:
        raise AssertionError(signed.text)
    probe = client.get("/auth/session")
    theme = _theme_cookies(probe)
    if len(theme) != 1 or "rio_theme=system" not in theme[0]:
        raise AssertionError(theme)
    lowered = theme[0].lower()
    if "httponly" in lowered or "samesite=lax" not in lowered:
        raise AssertionError(theme[0])
    me = client.get("/auth/me")
    if _theme_cookies(me):
        raise AssertionError("reloading minted a cookie on /auth/me")
    saved = client.patch("/settings", json={"theme": "dark"})
    dark = _theme_cookies(saved)
    if len(dark) != 1 or not dark[0].startswith("rio_theme=dark"):
        raise AssertionError(dark)
    anonymous = TestClient(
        create_app(directory=None, accounts=path, frontend_origin="http://localhost:3000", load_env=False),
        base_url="https://testserver",
    )
    signed_out = anonymous.get("/auth/session")
    if signed_out.json().get("signed_in") is not False or _theme_cookies(signed_out):
        raise AssertionError(signed_out.headers)
