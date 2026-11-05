# css_href.py — a stylesheet URL that changes when the file changes.

"""The query is a short hash of ui/static/app.css. Computed once per process."""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

_CSS_FILE = Path(__file__).resolve().parent / "static" / "app.css"


def app_css_href(css_bytes: bytes) -> str:
    """Relative URL. The version is the first 10 hex characters of the md5."""
    version = hashlib.md5(css_bytes).hexdigest()[:10]
    return "app/static/app.css?v=" + version


@lru_cache(maxsize=1)
def cached_app_css_href() -> str:
    """Read the stylesheet once and keep that URL for this process."""
    return app_css_href(_CSS_FILE.read_bytes())
