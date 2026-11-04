# access.py — Admin is one email from the environment.

"""RIO_ADMIN_EMAIL names the account that may open Admin.

The value is read after the local env file is loaded, the same way other
local settings are read. A value already in the environment wins. When the
name is missing or blank, nobody is admin and nothing here fails.
No address is written in this file. The value is never printed.
"""

from __future__ import annotations

import os

from ui.accounts import normalize_email
from ui.activities import load_local_env

ENV_NAME = "RIO_ADMIN_EMAIL"


def configured_admin_email() -> str | None:
    """The admin email, or None when it is unset or not an email."""
    try:
        load_local_env()
    except Exception:
        return None
    raw = os.environ.get(ENV_NAME, "")
    if not isinstance(raw, str):
        return None
    return normalize_email(raw)


def viewer_is_admin(email: object) -> bool:
    """True only when this login is the configured admin email."""
    admin = configured_admin_email()
    if admin is None:
        return False
    return normalize_email(email) == admin
