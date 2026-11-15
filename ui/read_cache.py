# read_cache.py — one shared read for the burst of requests a page fires.

"""A signed-in page used to check the token and load the account once per
request, and several requests at once. Overlapping token checks share one
round trip and are not kept: the next call asks again, so a revoked token
fails. The account bundle is kept for a few seconds. A write drops it,
including a read that was already in flight, so the next read sees the write.
"""

from __future__ import annotations

import copy
import hashlib
import threading
import time
from typing import Callable

# Token checks are coalesced only while they are in flight. A finished check
# is not reused, so the next request can still see a revoked token.
AUTH_TTL = 0.0
BUNDLE_TTL = 4.0
PURGE_INTERVAL = 60.0
_WAIT = 30.0


class _Slot:
    def __init__(self) -> None:
        self.event = threading.Event()
        self.value = None
        self.error: BaseException | None = None


class ReadCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: dict[tuple, tuple[float, object]] = {}
        self._flight: dict[tuple, _Slot] = {}
        self._gen: dict[tuple, int] = {}
        self._purge_at: dict[int, float] = {}

    def reset(self) -> None:
        with self._lock:
            self._values.clear()
            self._flight.clear()
            self._gen.clear()
            self._purge_at.clear()

    def auth(self, directory: object, token: object, load: Callable[[], dict], ttl: float = AUTH_TTL) -> dict:
        return self._read(self._key("auth", directory, token), load, ttl)

    def bundle(self, directory: object, token: object, load: Callable[[], dict], ttl: float = BUNDLE_TTL) -> dict:
        return self._read(self._key("bundle", directory, token), load, ttl)

    def forget(self, directory: object, token: object) -> None:
        if not isinstance(token, str) or not token:
            return
        with self._lock:
            for kind in ("auth", "bundle"):
                key = self._key(kind, directory, token)
                self._gen[key] = self._gen.get(key, 0) + 1
                self._values.pop(key, None)

    def purge_due(self, directory_id: int, interval: float = PURGE_INTERVAL) -> bool:
        """True once per interval. The caller deletes expired session rows then."""
        now = time.monotonic()
        with self._lock:
            last = self._purge_at.get(directory_id)
            # A missing stamp has never run. Zero is not that stamp: monotonic()
            # can still be under the interval right after boot.
            if last is not None and now - last < interval:
                return False
            self._purge_at[directory_id] = now
            return True

    def _key(self, kind: str, directory: object, token: object) -> tuple:
        digest = ""
        if isinstance(token, str) and token:
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return (kind, id(directory), digest)

    def _read(self, key: tuple, load: Callable[[], dict], ttl: float) -> dict:
        now = time.monotonic()
        with self._lock:
            hit = self._values.get(key)
            if hit is not None and hit[0] > now:
                return copy.deepcopy(hit[1])
            slot = self._flight.get(key)
            if slot is None:
                slot = _Slot()
                self._flight[key] = slot
                owner = True
                generation = self._gen.get(key, 0)
            else:
                owner = False
                generation = 0
        if not owner:
            if not slot.event.wait(_WAIT):
                return copy.deepcopy(load())
            if slot.error is not None:
                raise slot.error
            return copy.deepcopy(slot.value)
        try:
            value = load()
        except BaseException as exc:
            slot.error = exc
            raise
        else:
            stored = copy.deepcopy(value)
            slot.value = stored
            if ttl > 0:
                with self._lock:
                    if self._gen.get(key, 0) == generation:
                        self._values[key] = (time.monotonic() + ttl, stored)
            return copy.deepcopy(stored)
        finally:
            slot.event.set()
            with self._lock:
                if self._flight.get(key) is slot:
                    self._flight.pop(key, None)


read_cache = ReadCache()
