# test_read_cache.py — duplicate signed-in reads share one round trip.

"""Offline. No network and no project secrets."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.cloud_store import SupabaseDirectory
from ui.read_cache import read_cache


def setup_function(_fn=None) -> None:
    read_cache.reset()


def test_parallel_reads_share_one_load() -> None:
    calls = []
    release = threading.Event()
    started = threading.Event()

    def load() -> dict:
        calls.append("load")
        started.set()
        if not release.wait(2):
            raise AssertionError("the read was not released")
        return {"plans": [1]}

    directory = object()
    found: list[dict] = []

    def run() -> None:
        found.append(read_cache.bundle(directory, "token-a", load, ttl=5))

    first = threading.Thread(target=run)
    first.start()
    if not started.wait(2):
        raise AssertionError("the first read did not start")
    second = threading.Thread(target=run)
    second.start()
    time.sleep(0.05)
    release.set()
    first.join(2)
    second.join(2)
    if calls != ["load"] or found != [{"plans": [1]}, {"plans": [1]}]:
        raise AssertionError((calls, found))


def test_a_write_during_the_read_is_not_served_next() -> None:
    release = threading.Event()
    started = threading.Event()

    def load() -> dict:
        started.set()
        release.wait(2)
        return {"n": 1}

    directory = object()
    worker = threading.Thread(target=lambda: read_cache.bundle(directory, "token-a", load, ttl=30))
    worker.start()
    if not started.wait(2):
        raise AssertionError("the read did not start")
    read_cache.forget(directory, "token-a")
    release.set()
    worker.join(2)
    calls = []

    def again() -> dict:
        calls.append("again")
        return {"n": 2}

    got = read_cache.bundle(directory, "token-a", again, ttl=30)
    if got != {"n": 2} or calls != ["again"]:
        raise AssertionError((got, calls))


def test_a_finished_token_check_is_not_reused() -> None:
    calls = []

    def load() -> dict:
        calls.append("auth")
        return {"id": "user-1"}

    directory = object()
    if read_cache.auth(directory, "token-a", load)["id"] != "user-1":
        raise AssertionError("the token check was dropped")
    read_cache.auth(directory, "token-a", load)
    if calls != ["auth", "auth"]:
        raise AssertionError(calls)


def test_two_tokens_do_not_share_a_bundle() -> None:
    directory = object()
    ada = read_cache.bundle(directory, "token-a", lambda: {"who": "ada"}, ttl=5)
    beau = read_cache.bundle(directory, "token-b", lambda: {"who": "beau"}, ttl=5)
    if ada != {"who": "ada"} or beau != {"who": "beau"}:
        raise AssertionError((ada, beau))
    if read_cache.bundle(directory, "token-a", lambda: {"who": "stale"}, ttl=5) != {"who": "ada"}:
        raise AssertionError("the second read missed the cache")


def test_purge_runs_once_per_interval() -> None:
    if not read_cache.purge_due(11, interval=60):
        raise AssertionError("the first cleanup was skipped")
    if read_cache.purge_due(11, interval=60):
        raise AssertionError("cleanup ran again inside the interval")
    if not read_cache.purge_due(22, interval=60):
        raise AssertionError("another process skipped cleanup")


def test_hosted_load_bundle_hits_supabase_once_until_a_save() -> None:
    hits: list[str] = []

    class _Table:
        def __init__(self, name: str) -> None:
            self.name = name
            self.query = ""

        def select(self, cols: str = "*", *args: object, **kwargs: object) -> "_Table":
            self.query = cols
            return self

        def eq(self, *args: object, **kwargs: object) -> "_Table":
            return self

        def limit(self, *args: object, **kwargs: object) -> "_Table":
            return self

        def execute(self) -> SimpleNamespace:
            hits.append(self.name + ":" + self.query)
            return SimpleNamespace(
                data=[
                    {
                        "id": "user-1",
                        "email": "ada@example.com",
                        "display_name": "Ada",
                        "role": "athlete",
                        "goals": [],
                        "plans": [],
                        "results": [],
                    }
                ]
            )

    class _Client:
        def __init__(self) -> None:
            self.auth = self
            self.postgrest = SimpleNamespace(auth=lambda token: None)

        def get_user(self, jwt: str | None = None) -> SimpleNamespace:
            hits.append("auth")
            return SimpleNamespace(
                user=SimpleNamespace(
                    id="user-1",
                    email="ada@example.com",
                    email_confirmed_at="2026-01-01T00:00:00Z",
                    user_metadata={},
                )
            )

        def table(self, name: str) -> _Table:
            return _Table(name)

    directory = SupabaseDirectory("https://example.supabase.co", "anon", "svc")
    directory._client = lambda key: _Client()  # type: ignore[method-assign]
    first = directory.load_bundle("token-a")
    second = directory.load_bundle("token-a")
    if first["profile"]["id"] != "user-1" or second["profile"]["id"] != "user-1":
        raise AssertionError("the bundle was dropped")
    if hits.count("auth") != 1 or not any(item.startswith("profiles:") for item in hits):
        raise AssertionError(hits)
    profile_hits = [item for item in hits if item.startswith("profiles:")]
    if len(profile_hits) != 1:
        raise AssertionError(hits)

    def _save(token: object, bundle: object) -> None:
        hits.append("save")

    directory._save_bundle = _save  # type: ignore[method-assign]
    directory.save_bundle("token-a", {"plans": []})
    directory.load_bundle("token-a")
    if hits.count("auth") != 2 or len([item for item in hits if item.startswith("profiles:")]) != 2:
        raise AssertionError(hits)
