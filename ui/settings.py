# settings.py — display preferences. They are not part of the plan.

"""Session preferences for the settings page.

Units, dates, template ids, and compact mode change what the page shows.
They are not written onto a session and they are not passed to adapt.
Notifications are stored and do nothing else.

No model. No spend. No scores.
"""

from __future__ import annotations

import re
from datetime import date

_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
# Statute mile. Display rounding only. The stored plan stays in meters.
_KM_TO_MI = 0.621371
_M_TO_MI = 1 / 1609.344
_KM = re.compile(r"(\d+(?:\.\d+)?)\s*km\b", re.IGNORECASE)
_METERS = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+)\s*m\b")
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

DEFAULTS = {
    "units": "km",
    "show_ids": False,
    "compact": False,
    "date_format": "iso",
    "confirm_adapt": False,
    "notifications": False,
}


def normalize(raw: object) -> dict:
    """A complete preference dict. Unknown or blank values use the defaults."""
    found = raw if isinstance(raw, dict) else {}
    units = found.get("units")
    date_format = found.get("date_format")
    return {
        "units": units if units in ("km", "miles") else DEFAULTS["units"],
        "show_ids": found.get("show_ids") is True,
        "compact": found.get("compact") is True,
        "date_format": date_format if date_format in ("iso", "short") else DEFAULTS["date_format"],
        "confirm_adapt": found.get("confirm_adapt") is True,
        "notifications": found.get("notifications") is True,
    }


def format_date(value: object, date_format: str) -> str:
    """ISO stays YYYY-MM-DD. Short is a fixed English day, such as Oct 24, 2026."""
    day = _as_date(value)
    if day is None:
        text = str(value).strip() if value is not None else ""
        return text or "—"
    if date_format == "short":
        return f"{_MONTHS[day.month - 1]} {day.day}, {day.year}"
    return day.isoformat()


def display_km(text: object, units: str) -> str:
    """Kilometer phrases as miles. Any other unit is left as written."""
    if not isinstance(text, str):
        return ""
    if units != "miles":
        return text

    def repl(match: re.Match) -> str:
        miles = float(match.group(1)) * _KM_TO_MI
        return f"{miles:.1f} mi"

    return _KM.sub(repl, text)


def display_meters(text: object, units: str) -> str:
    """Meter totals as miles. A kilometer phrase is not a meter total."""
    if not isinstance(text, str):
        return ""
    if units != "miles":
        return text

    def repl(match: re.Match) -> str:
        meters = int(match.group(1).replace(",", ""))
        return f"{meters * _M_TO_MI:.1f} mi"

    return _METERS.sub(repl, text)


def _as_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    found = _ISO.fullmatch(value.strip())
    if found is None:
        return None
    try:
        return date(int(found.group(1)), int(found.group(2)), int(found.group(3)))
    except ValueError:
        return None
