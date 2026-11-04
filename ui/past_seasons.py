# past_seasons.py — seasons this browser already stored. Display only.

"""A row is a plan key already in this browser.

The key is the four inputs. Start date, goal date, and goal time are shown
from those inputs. A plan is active while its goal date is today or later.
Nothing here builds a season.

No model. No spend.
"""

from __future__ import annotations

from datetime import date

from ui.plan_store import inputs_ok, storage_key

# The plan key prefix. A profile record and any other key stay off this list.
KEY_PREFIX = "rio.plan.v1\n"


def inputs_from_key(key: object) -> tuple[str, str, str, str] | None:
    """The four inputs in a plan key, or None when the key is not one."""
    if not isinstance(key, str) or not key.startswith(KEY_PREFIX):
        return None
    parts = key[len(KEY_PREFIX) :].split("\n")
    if len(parts) != 4:
        return None
    inputs = (parts[0], parts[1], parts[2], parts[3])
    if not inputs_ok(inputs) or storage_key(inputs) != key:
        return None
    return inputs


def keys_from_inputs(rows: object) -> list[str]:
    """Plan keys for stored input rows. A bad row is left out."""
    if not isinstance(rows, list):
        return []
    keys: list[str] = []
    for item in rows:
        if isinstance(item, (list, tuple)):
            item = tuple(item)
        if not inputs_ok(item):
            continue
        key = storage_key(item)
        if key not in keys:
            keys.append(key)
    return keys


def season_entries(keys: object) -> list[tuple[str, str, str, str]]:
    """Stored seasons, one per plan key.

    Junk is left out. The same four inputs stay one row. Order is start
    date, then goal date, then goal time.
    """
    if not isinstance(keys, list):
        return []
    found: dict[tuple[str, str, str, str], None] = {}
    for key in keys:
        inputs = inputs_from_key(key)
        if inputs is None or inputs in found:
            continue
        found[inputs] = None
    rows = list(found)
    rows.sort(key=lambda item: (item[1], item[3], item[2], item[0]))
    return rows


def has_active_plan(keys: object, today: date) -> bool:
    """True when a stored plan's goal date is today or later.

    No plan is not active. A goal date before today is finished. A profile
    record and any other key stay out.
    """
    if type(today) is not date:
        return False
    for inputs in season_entries(keys):
        if date.fromisoformat(inputs[3]) >= today:
            return True
    return False


def entry_fields(inputs: tuple[str, str, str, str]) -> list[tuple[str, str]]:
    """Start date, goal date, and goal time, as stored."""
    return [
        ("Start date", inputs[1]),
        ("Goal date", inputs[3]),
        ("Goal time", inputs[2]),
    ]
