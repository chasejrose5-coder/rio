# load_gate.py — once-per-session pull and paragraph cache. No network.

"""Pace logic stays in engines/. This only remembers a result already computed."""

from __future__ import annotations

import json


def pull_again(refresh: bool, already: bool) -> bool:
    """A manual refresh pulls again. Every other page uses the first pull."""
    return bool(refresh) or not already


def cached_paragraph(cache: dict, kind: str, payload: object, compute) -> str:
    """Return the stored paragraph for this input, or compute it once.

    The payload is the classification, the template, or the goal. It is not
    a Strava activity.
    """
    try:
        key = kind + "\n" + json.dumps(payload, sort_keys=True, default=str)
    except (TypeError, ValueError):
        key = kind + "\n" + repr(payload)
    found = cache.get(key)
    if isinstance(found, str):
        return found
    text = compute()
    if isinstance(text, str):
        cache[key] = text
    return text if isinstance(text, str) else ""
