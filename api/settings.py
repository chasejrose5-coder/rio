# settings.py — API process settings. Values stay in the environment.

"""One frontend origin and the cookie name.

Supabase URL and keys are read by ui.cloud_config from the same environment
the Streamlit app already uses. They are not copied into this module.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from ui.cloud_session import COOKIE_NAME


@dataclass(frozen=True)
class ApiSettings:
    """What the process needs that is not a Supabase key."""

    frontend_origin: str
    cookie_name: str = COOKIE_NAME


def load_settings(origin: str | None = None) -> ApiSettings:
    """RIO_FRONTEND_ORIGIN, or the local Next port.

    A wildcard is refused. The browser only talks to the one origin that
    is configured for this process.
    """
    if origin is None:
        origin = os.environ.get("RIO_FRONTEND_ORIGIN", "http://localhost:3000")
    text = origin.strip().rstrip("/")
    if not text or text == "*" or any(char in text for char in "\n\r "):
        raise RuntimeError("RIO_FRONTEND_ORIGIN must be one http origin")
    if not text.startswith("http://") and not text.startswith("https://"):
        raise RuntimeError("RIO_FRONTEND_ORIGIN must be one http origin")
    return ApiSettings(frontend_origin=text)
