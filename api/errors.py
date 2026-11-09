# errors.py — failures the route can show. No tokens in the message.

"""Status and a sentence. The route turns this into JSON."""

from __future__ import annotations


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
