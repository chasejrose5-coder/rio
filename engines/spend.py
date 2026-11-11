# spend.py — one $25 explain counter for Streamlit and the API.

"""The file is the counter until migration 011 exists.

RIO_EXPLAIN_SPEND_PATH still selects that file. Tests set it, and a laptop
without Supabase keeps using it. When the path is unset and the service role
is configured, reserve and settle go through public.explain_spend. A missing
table or function falls back to the file, so Streamlit keeps running before
the SQL is applied. After it is applied, both processes share the row.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


class SpendMissing(Exception):
    """The shared table or function is not there yet."""


def spend_path() -> Path:
    """The JSON counter. An override wins. Otherwise data/explain_spend.json."""
    override = os.environ.get("RIO_EXPLAIN_SPEND_PATH", "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "data" / "explain_spend.json"


def read_spend(path: Path) -> int | None:
    """Recorded microdollars. None when the record cannot be trusted."""
    if not path.exists():
        return 0
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        value = payload["micro_usd"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def write_spend(path: Path, micro: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps({"micro_usd": int(micro)}),
        encoding="utf-8",
    )
    temporary.replace(path)


def _cap() -> int:
    from engines.explain import SPEND_CAP_MICRO_USD

    return SPEND_CAP_MICRO_USD


class FileSpend:
    """The JSON file. One process, and the fallback before migration 011."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = spend_path() if path is None else path

    def reserve(self, worst: int) -> bool:
        if worst < 0:
            return False
        spent = read_spend(self.path)
        cap = _cap()
        if spent is None or spent >= cap:
            return False
        if worst == 0:
            return True
        if spent + worst > cap:
            return False
        try:
            write_spend(self.path, spent + worst)
        except OSError:
            return False
        return True

    def settle(self, reserved: int, actual: int) -> None:
        if actual < 0:
            actual = reserved
        spent = read_spend(self.path)
        if spent is None:
            return
        updated = spent - reserved + actual
        if updated < 0:
            updated = 0
        try:
            write_spend(self.path, updated)
        except OSError:
            return


def _missing_text(exc: BaseException) -> bool:
    text = str(exc).lower()
    needles = (
        "does not exist",
        "could not find the function",
        "schema cache",
        "pgrst202",
        "pgrst205",
        "undefined_function",
        "42p01",
    )
    return any(needle in text for needle in needles)


def _as_bool(data: object) -> bool:
    if isinstance(data, bool):
        return data
    if isinstance(data, list) and data:
        return _as_bool(data[0])
    if isinstance(data, dict):
        for value in data.values():
            return _as_bool(value)
        return False
    return bool(data)


class SharedSpend:
    """public.explain_spend, written with the service role only."""

    def __init__(self, call) -> None:
        self._call = call
        self._seeded = False

    def _seed(self) -> None:
        """Copy a file balance up once, so the cap does not restart at zero."""
        if self._seeded:
            return
        self._seeded = True
        spent = read_spend(spend_path())
        if not spent:
            return
        self._call("adopt_explain_spend", {"p_micro": int(spent)})

    def reserve(self, worst: int) -> bool:
        if worst < 0:
            return False
        try:
            self._seed()
            data = self._call(
                "reserve_explain_spend",
                {"p_worst": int(worst), "p_cap": _cap()},
            )
        except SpendMissing:
            raise
        except Exception as exc:
            if _missing_text(exc):
                raise SpendMissing(str(exc)) from exc
            return False
        return _as_bool(data)

    def settle(self, reserved: int, actual: int) -> None:
        if actual < 0:
            actual = reserved
        try:
            self._call(
                "settle_explain_spend",
                {"p_reserved": int(reserved), "p_actual": int(actual)},
            )
        except SpendMissing:
            raise
        except Exception as exc:
            if _missing_text(exc):
                raise SpendMissing(str(exc)) from exc
            return


# Tests set this to a callable. None means look at the environment.
_rpc_override: object | None = None
_active: dict[int, object] = {}


def _thread_id() -> int:
    import threading

    return threading.get_ident()


def supabase_rpc():
    """A service-role RPC, or None when accounts are not configured.

    The JSON path is left alone. This is not called when that path is set,
    so a test never opens a Supabase client.
    """
    if os.environ.get("RIO_EXPLAIN_SPEND_PATH", "").strip():
        return None
    from ui.cloud_config import cloud_settings

    settings = cloud_settings()
    if not isinstance(settings, dict):
        return None
    service = settings.get("service_key")
    url = settings.get("url")
    if not isinstance(service, str) or not service.strip() or not isinstance(url, str) or not url:
        return None

    def call(name: str, args: dict):
        from ui.cloud_store import supabase_client

        client = supabase_client(url, service)
        found = client.rpc(name, args).execute()
        return getattr(found, "data", None)

    return call


def _book():
    if os.environ.get("RIO_EXPLAIN_SPEND_PATH", "").strip():
        return FileSpend(spend_path())
    override = _rpc_override
    if callable(override):
        return SharedSpend(override)
    rpc = supabase_rpc()
    if rpc is None:
        return FileSpend(spend_path())
    return SharedSpend(rpc)


def reserve_spend(worst: int) -> bool:
    """Hold worst-case cost. False when the cap would break."""
    chosen = _book()
    try:
        ok = chosen.reserve(worst)
    except SpendMissing:
        chosen = FileSpend(spend_path())
        ok = chosen.reserve(worst)
    if ok:
        _active[_thread_id()] = chosen
    return ok


def settle_spend(reserved: int, actual: int) -> None:
    """Replace the reservation with the cost of the call that finished."""
    chosen = _active.pop(_thread_id(), None)
    if chosen is None:
        chosen = FileSpend(spend_path())
    try:
        chosen.settle(reserved, actual)
    except SpendMissing:
        FileSpend(spend_path()).settle(reserved, actual)
