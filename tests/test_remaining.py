# test_remaining.py — save errors, Strava state, and the goal-time note.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from types import SimpleNamespace

from ui.cloud_store import CloudAuthError, SupabaseDirectory, _log_store
from ui.settings import TIME_ZONES, suggested_timezone
from ui.strava import make_state, state_matches
from ui.startup import startup_html


class _Query:
    def upsert(self, *_args, **_kwargs):
        raise RuntimeError("database unavailable")

    def execute(self):
        raise RuntimeError("database unavailable")


class _Boom:
    def __init__(self) -> None:
        self.auth = SimpleNamespace(
            get_user=lambda jwt=None: SimpleNamespace(user=SimpleNamespace(id="user-1"))
        )
        self.postgrest = SimpleNamespace(auth=lambda _token: None)

    def table(self, _name):
        return _Query()


def test_a_store_error_is_a_cloud_auth_error() -> None:
    directory = SupabaseDirectory("https://example.supabase.co", "anon", "svc")
    directory._user_client = lambda _token: _Boom()
    try:
        directory.save_bundle("token", {"goal": {"goal_time": "1:59"}})
    except CloudAuthError as exc:
        if "Could not save" not in str(exc):
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a database failure was not shown")
    try:
        directory.load_bundle("token")
    except CloudAuthError as exc:
        if "Could not load" not in str(exc):
            raise AssertionError(str(exc))
    else:
        raise AssertionError("a load failure was not shown")
    _log_store("save", RuntimeError("secret-token"))


def test_strava_state_is_not_a_supabase_code() -> None:
    state = make_state("user-1", "nonce-1")
    if not state.startswith("strava:"):
        raise AssertionError(state)
    if not state_matches(state, "user-1", "nonce-1"):
        raise AssertionError("the prefixed state did not match")
    if state_matches(state[len("strava:") :], "user-1", "nonce-1") is not True:
        raise AssertionError("an older state stopped matching")
    ui = (ROOT / "ui" / "cloud_ui.py").read_text(encoding="utf-8")
    callback = ui[ui.index("def _consume_callback(") : ui.index("def _render_sign_in(")]
    if 'startswith("strava:")' not in callback:
        raise AssertionError("a Strava return can be exchanged as a login code")


def test_timezone_goal_note_and_hidden_copy() -> None:
    if suggested_timezone() not in TIME_ZONES:
        raise AssertionError(suggested_timezone())
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    if "does not rebuild the season" not in app:
        raise AssertionError("profile still implies a save rebuilds the plan")
    if "I understand this permanently deletes my season and runs" not in app:
        raise AssertionError("delete still uses the same words as the button")
    html = startup_html()
    if "rio-startup-statement" not in html or "Placeholder" not in html:
        raise AssertionError("the startup strings tests read were removed")
    if '<div class="rio-startup-statement' in html:
        raise AssertionError("the placeholder is still a hidden element")
    if "Bio coming soon." not in app:
        raise AssertionError("creators copy the tests read was removed")


def main() -> None:
    test_a_store_error_is_a_cloud_auth_error()
    test_strava_state_is_not_a_supabase_code()
    test_timezone_goal_note_and_hidden_copy()
    print("remaining ok")


if __name__ == "__main__":
    main()
