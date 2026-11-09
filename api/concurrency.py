# concurrency.py — If-Match against the season digest.

"""A missing header keeps the last write. A header that does not match is 412.

The digest is the one already returned on the season. Notes are not part of
it. Sending the header still refuses a stale tab before that write.
"""

from __future__ import annotations

from fastapi import Request

from api.errors import ApiError

STALE = "This season changed in another tab. Reload it and try again."


def presented_digest(request: Request) -> str | None:
    """The If-Match value, or None when the client did not send one."""
    raw = request.headers.get("if-match")
    if raw is None:
        return None
    token = str(raw).strip()
    if not token:
        return None
    if token.startswith("W/"):
        token = token[2:].strip()
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        token = token[1:-1]
    return token


def require_digest(request: Request, digest: str | None) -> None:
    """412 when If-Match is not the season the client loaded."""
    token = presented_digest(request)
    if token is None:
        return
    if token == "*" and digest:
        return
    if digest is None or token != digest:
        raise ApiError(412, STALE)
