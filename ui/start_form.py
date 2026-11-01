# start_form.py — the four Start fields before a season exists.

"""Defaults for Start. The dates are today and five months later.

The times stay blank. The caller can replace any of the four fields.
Nothing here builds a season.

No model. No spend. No scores.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date


def _months_later(day: date, months: int) -> date:
    """Calendar months after day. A shorter month keeps its last day."""
    if isinstance(months, bool) or not isinstance(months, int):
        raise ValueError("months is not a whole number")
    if months < 0:
        raise ValueError("months is before day")
    index = day.month - 1 + months
    year = day.year + index // 12
    month = index % 12 + 1
    last = monthrange(year, month)[1]
    return date(year, month, min(day.day, last))


def start_form_defaults(today: date) -> tuple[str, date, str, date]:
    """Blank times, today, and the day five calendar months later."""
    if not isinstance(today, date):
        raise ValueError("today is not a calendar date")
    return ("", today, "", _months_later(today, 5))
