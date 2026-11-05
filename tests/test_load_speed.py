# test_load_speed.py — first paint stays small. Offline. No project secrets.

from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from ui.cloud_session import HOSTED_PREFIX
from ui.cloud_store import SupabaseDirectory, _http_pool
from ui.cloud_ui import restore_hosted_cookie
from ui.load_gate import cached_paragraph, pull_again
from ui.strava_ui import run_deferred_strava, strava_sync_action


def _wipe() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]


class _Table:
    def __init__(self, backend: "_Backend", name: str, token: str) -> None:
        self.backend = backend
        self.name = name
        self.token = token
        self.query = "*"

    def select(self, cols: str = "*", *args: object, **kwargs: object) -> "_Table":
        self.query = cols
        return self

    def eq(self, *args: object, **kwargs: object) -> "_Table":
        return self

    def order(self, *args: object, **kwargs: object) -> "_Table":
        return self

    def limit(self, *args: object, **kwargs: object) -> "_Table":
        return self

    def execute(self) -> SimpleNamespace:
        self.backend.hits.append(("table", self.name, self.token, self.query))
        if self.name == "app_sessions":
            return SimpleNamespace(data=[self.backend.session_row])
        if self.name == "profiles" and "goals(" in self.query:
            return SimpleNamespace(data=[self.backend.profile])
        raise AssertionError(self.name)


class _Client:
    def __init__(self, backend: "_Backend", key: str) -> None:
        self.backend = backend
        self.key = key
        self.token = ""
        self.auth = self
        self.postgrest = SimpleNamespace(auth=self._auth)
        backend.clients.append(self)

    def _auth(self, token: str) -> None:
        self.token = token
        self.backend.tokens.append(token)

    def get_user(self, jwt: str | None = None) -> SimpleNamespace:
        self.backend.hits.append(("auth", "/auth/v1/user", jwt or "", "get_user"))
        return SimpleNamespace(
            user=SimpleNamespace(
                id="user-1",
                email="ada@example.com",
                email_confirmed_at="2026-01-01T00:00:00Z",
                user_metadata={"intro_seen": True},
            )
        )

    def table(self, name: str) -> _Table:
        return _Table(self.backend, name, self.token or self.key)


class _Backend:
    def __init__(self) -> None:
        self.hits: list[tuple] = []
        self.clients: list[_Client] = []
        self.tokens: list[str] = []
        self.session_row = {
            "access_token": "access-1",
            "refresh_token": "refresh-1",
            "user_id": "user-1",
            "email": "ada@example.com",
            "display_name": "Ada",
            "issued_at": int(time.time()),
        }
        self.profile = {
            "id": "user-1",
            "email": "ada@example.com",
            "display_name": "Ada",
            "role": "athlete",
            "goals": {"user_id": "user-1"},
            "plans": [
                {"id": "b", "updated_at": "2026-02-01T00:00:00Z", "plan": {}},
                {"id": "a", "updated_at": "2026-01-01T00:00:00Z", "plan": {}},
            ],
            "results": [],
        }


def _directory(backend: _Backend) -> SupabaseDirectory:
    directory = SupabaseDirectory("https://example.supabase.co", "anon", "svc")

    def _new(key: str) -> _Client:
        return _Client(backend, key)

    def _second_auth(method: str, token: str, body: dict | None = None) -> dict:
        backend.hits.append(("auth", "/auth/v1/user", token, "request"))
        raise RuntimeError("a second auth request")

    directory._client = _new  # type: ignore[method-assign]
    directory._auth_request = _second_auth  # type: ignore[method-assign]
    return directory


def test_cookie_restore_uses_at_most_five_requests() -> None:
    """A returning sign-in is one session read, one auth check, and one bundle."""
    _wipe()
    backend = _Backend()
    directory = _directory(backend)
    import ui.cloud_ui as cloud_ui

    original = cloud_ui.current_directory
    cloud_ui.current_directory = lambda: directory  # type: ignore[method-assign]
    try:
        opened = restore_hosted_cookie(HOSTED_PREFIX + "a" * 24)
    finally:
        cloud_ui.current_directory = original  # type: ignore[method-assign]
    if opened is not True:
        raise AssertionError("the cookie did not restore")
    if len(backend.hits) > 5:
        raise AssertionError(backend.hits)
    auth = [hit for hit in backend.hits if hit[0] == "auth"]
    if len(auth) != 1 or auth[0][3] != "get_user":
        raise AssertionError(auth)
    if st.session_state.get("rio_account") != "ada@example.com":
        raise AssertionError(st.session_state.get("rio_account"))
    plans = st.session_state.get("rio_cloud_season_inputs")
    if not isinstance(plans, list) or len(plans) != 2:
        raise AssertionError(plans)
    _wipe()


def test_two_users_do_not_share_a_client_or_a_token() -> None:
    """Each visitor gets a new client. The pool does not keep either token."""
    directory = SupabaseDirectory("https://example.supabase.co", "anon", "svc")
    made: list[_Client] = []
    backend = _Backend()

    def _new(key: str) -> _Client:
        client = _Client(backend, key)
        made.append(client)
        return client

    directory._client = _new  # type: ignore[method-assign]
    first = directory._user_client("token-a")
    second = directory._user_client("token-b")
    if first is second or len(made) != 2:
        raise AssertionError("one client was reused")
    if first.token != "token-a" or second.token != "token-b":
        raise AssertionError((first.token, second.token))
    if first.token == second.token:
        raise AssertionError("the token was shared")

    sent: list[str] = []

    class _Pool:
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}

        def request(self, method: str, url: str, content: object = None, headers: dict | None = None, timeout: object = None):
            if any(str(key).lower() == "authorization" for key in self.headers):
                raise AssertionError(dict(self.headers))
            sent.append(str((headers or {}).get("Authorization")))

            class _Response:
                status_code = 200
                content = b"{}"

                def raise_for_status(self) -> None:
                    return None

            return _Response()

    pool = _Pool()
    import ui.cloud_store as cloud_store

    previous = cloud_store._HTTP_POOL
    cloud_store._HTTP_POOL = pool
    try:
        directory._auth_request("GET", "token-a", None)
        directory._auth_request("GET", "token-b", None)
        live = _http_pool()
    finally:
        cloud_store._HTTP_POOL = previous
    if sent != ["Bearer token-a", "Bearer token-b"]:
        raise AssertionError(sent)
    if live is not pool:
        raise AssertionError("the pool was rebuilt with a token on it")
    if any(str(key).lower() == "authorization" for key in getattr(live, "headers", {})):
        raise AssertionError("the pool stored a token")
    store = (ROOT / "ui" / "cloud_store.py").read_text(encoding="utf-8")
    ui = (ROOT / "ui" / "cloud_ui.py").read_text(encoding="utf-8")
    if "cache_resource" in store or "cache_resource" in ui or "st.cache" in store:
        raise AssertionError("a client is cached across visitors")


def test_strava_sync_waits_for_the_next_pass() -> None:
    """The first pass does not import. The next pass does, once a plan exists."""
    _wipe()
    if strava_sync_action(0) != "skip" or strava_sync_action(1) != "sync":
        raise AssertionError("the first pass still imports")
    import ui.strava_ui as strava_ui

    seen: list[str] = []
    original = strava_ui.sync_once

    def _sync(force: bool = False) -> bool:
        seen.append("sync")
        st.session_state["rio_strava_notice"] = "Strava could not be saved."
        return False

    strava_ui.sync_once = _sync  # type: ignore[method-assign]
    try:
        st.session_state["season_plan"] = {"sessions": [{"date": "2026-01-01"}]}
        if run_deferred_strava(0) != "skip" or seen:
            raise AssertionError(seen)
        if run_deferred_strava(1) != "synced" or seen != ["sync"]:
            raise AssertionError(seen)
        if st.session_state.get("rio_strava_notice") != "Strava could not be saved.":
            raise AssertionError("the sync error was dropped")
        st.session_state["season_plan"] = {}
        seen.clear()
        if run_deferred_strava(2) != "wait" or seen:
            raise AssertionError("a plan-less pass imported")
    finally:
        strava_ui.sync_once = original  # type: ignore[method-assign]
        _wipe()


def test_intervals_pull_and_explain_run_once_per_session() -> None:
    """Page switches do not pull again. The same paragraph is not asked twice."""
    if pull_again(False, False) is not True:
        raise AssertionError("the first page skipped the pull")
    if pull_again(False, True) is not False:
        raise AssertionError("a page switch pulled again")
    if pull_again(True, True) is not True:
        raise AssertionError("refresh did not pull")
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    pull = app[app.index("def _pull_for(") : app.index("\ndef _open_restored_session(")]
    if 'st.session_state.get("activity-refresh") is True' not in pull:
        raise AssertionError("refresh no longer reads activities")
    if "pull_again(" not in pull or "rio_intervals_pulled" not in pull:
        raise AssertionError("the pull is not once per session")
    if '"load"' not in pull or "sync_recent(" not in pull or "sync_all(" not in pull:
        raise AssertionError("the pull lost a branch")
    asked: list[str] = []

    def _compute() -> str:
        asked.append("once")
        return "One paragraph."

    cache: dict = {}
    payload = {"family": "aerobic", "reason_codes": ["easy"], "confidence": "high"}
    first = cached_paragraph(cache, "session", payload, _compute)
    second = cached_paragraph(cache, "session", payload, _compute)
    if first != second or asked != ["once"]:
        raise AssertionError(asked)
    if "strava" in json_key(cache):
        raise AssertionError("a Strava row was cached")


def json_key(cache: dict) -> str:
    return " ".join(str(key) for key in cache)


def main() -> None:
    test_cookie_restore_uses_at_most_five_requests()
    test_two_users_do_not_share_a_client_or_a_token()
    test_strava_sync_waits_for_the_next_pass()
    test_intervals_pull_and_explain_run_once_per_session()
    print("load speed ok")


if __name__ == "__main__":
    main()
