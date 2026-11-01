# settings.py — display preferences. They are not part of the plan.

"""Session preferences for the settings page.

Units, dates, template ids, and compact mode change what the page shows.
They are not written onto a session and they are not passed to adapt.
Notifications are stored and do nothing else.

No model. No spend. No scores.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

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
# A ladder such as 200-300 m or 150, 200, 150 m shares one unit.
# "31,400" is one total. "8 km" is not a meter total.
_METERS = re.compile(
    r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?(?:(?:\s*[-–—]\s*|,\s+)\d+(?:\.\d+)?)*)\s*m\b"
)
_LADDER_SPLIT = re.compile(r"\s*[-–—]\s*|,\s+")
_REP = re.compile(r"(?:×|(?<![A-Za-z])x)\s*$", re.IGNORECASE)
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

# Display only. The season stays in meters. Theme does not switch.
APP_VERSION = "0.1"
TIME_ZONES = (
    "UTC",
    "Pacific/Honolulu",
    "America/Anchorage",
    "America/Los_Angeles",
    "America/Phoenix",
    "America/Denver",
    "America/Chicago",
    "America/New_York",
    "America/Sao_Paulo",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Africa/Johannesburg",
    "Asia/Kolkata",
    "Asia/Singapore",
    "Asia/Tokyo",
    "Australia/Sydney",
    "Pacific/Auckland",
)

DEFAULTS = {
    "units": "km",
    "show_ids": False,
    "compact": False,
    "date_format": "iso",
    "confirm_adapt": False,
    "notifications": False,
    "start_date": "today",
    "reminders": False,
    "recap": False,
    "theme": "dark",
}


def normalize(raw: object) -> dict:
    """A complete preference dict. Unknown or blank values use the defaults."""
    found = raw if isinstance(raw, dict) else {}
    units = found.get("units")
    date_format = found.get("date_format")
    start_date = found.get("start_date")
    reminders = found.get("reminders") is True
    recap = found.get("recap") is True
    return {
        "units": units if units in ("km", "miles") else DEFAULTS["units"],
        "show_ids": found.get("show_ids") is True,
        "compact": found.get("compact") is True,
        "date_format": date_format if date_format in ("iso", "short") else DEFAULTS["date_format"],
        "confirm_adapt": found.get("confirm_adapt") is True,
        "notifications": found.get("notifications") is True or reminders or recap,
        "start_date": start_date if start_date in ("today", "sunday") else DEFAULTS["start_date"],
        "reminders": reminders,
        "recap": recap,
        "theme": "dark",
    }


def suggested_timezone() -> str:
    """A zone from this machine when it is one we list. Otherwise UTC."""
    key = None
    try:
        key = getattr(datetime.now().astimezone().tzinfo, "key", None)
    except (OSError, OverflowError, ValueError):
        key = None
    if isinstance(key, str) and key in TIME_ZONES:
        return key
    return "UTC"


def start_on(day: date, behavior: object) -> date:
    """Today, or the Sunday that starts this training week or the next one.

    Sunday stays Sunday. Any other day moves forward to Sunday.
    """
    if not isinstance(day, date) or behavior != "sunday":
        if isinstance(day, date):
            return day
        raise ValueError("today is not a calendar date")
    shift = (6 - day.weekday()) % 7
    if shift == 0:
        return day
    return day + timedelta(days=shift)


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
    """Meter phrases as miles. A kilometer phrase is not a meter total."""
    if not isinstance(text, str):
        return ""
    if units != "miles":
        return text
    return _METERS.sub(_meters_as_miles, text)


def display_distance(text: object, units: str) -> str:
    """Distance labels for the settings toggle.

    Miles says mi. Kilometers keeps a rep in m and a longer continuous
    distance in km. Nothing is stored, and the word mileage is not used.
    """
    if not isinstance(text, str):
        return ""
    if units == "miles":
        return display_meters(display_km(text, "miles"), "miles")
    return _METERS.sub(_long_meters_as_km, text)


def distance_heading(units: str, distances: object = None) -> str:
    """Lap column. Miles says mi. A long metric lap says km, a shorter one m."""
    if units == "miles":
        return "Distance (mi)"
    amounts = _amounts(distances)
    if amounts and all(amount >= 1000 for amount in amounts):
        return "Distance (km)"
    return "Distance (m)"


def distance_number(meters: object, units: str, distances: object = None) -> str:
    """The lap figure under distance_heading. Display rounding only."""
    amount = _amount(meters)
    if amount is None:
        return "" if meters is None else str(meters).strip()
    heading = distance_heading(units, distances if distances is not None else [meters])
    if heading == "Distance (mi)":
        return _miles_label(amount).removesuffix(" mi")
    if heading == "Distance (km)":
        km = amount / 1000.0
        return str(int(km)) if km.is_integer() else f"{km:.1f}"
    if amount.is_integer():
        return str(int(amount))
    return f"{amount:g}"


def _meters_as_miles(match: re.Match) -> str:
    raw = match.group(1)
    if _is_ladder(raw):
        parts = [float(part) for part in _LADDER_SPLIT.split(raw)]
        places = 2 if any(abs(part * _M_TO_MI) < 0.1 for part in parts) else 1
        shown = [f"{part * _M_TO_MI:.{places}f}" for part in parts]
        return f"{_joiner(raw).join(shown)} mi"
    return _miles_label(float(raw.replace(",", "")))


def _long_meters_as_km(match: re.Match) -> str:
    """A continuous distance of at least 1 km. A rep or a ladder stays in m."""
    raw = match.group(1)
    if _is_ladder(raw):
        return match.group(0)
    meters = float(raw.replace(",", ""))
    if meters < 1000:
        return match.group(0)
    prefix = match.string[max(0, match.start() - 4) : match.start()]
    if _REP.search(prefix):
        return match.group(0)
    km = meters / 1000.0
    shown = str(int(km)) if km.is_integer() else f"{km:.1f}"
    return f"{shown} km"


def _is_ladder(raw: str) -> bool:
    return _LADDER_SPLIT.search(raw) is not None


def _joiner(raw: str) -> str:
    if "," in raw:
        return ", "
    if "–" in raw:
        return "–"
    if "—" in raw:
        return "—"
    return "-"


def _amounts(distances: object) -> list[float]:
    if not isinstance(distances, list):
        return []
    amounts: list[float] = []
    for item in distances:
        amount = _amount(item)
        if amount is None:
            return []
        amounts.append(amount)
    return amounts


def _amount(value: object) -> float | None:
    if isinstance(value, dict):
        value = value.get("distance_m")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and value != value:
        return None
    return float(value)


def _miles_label(meters: float) -> str:
    miles = meters * _M_TO_MI
    if abs(miles) >= 0.1:
        return f"{miles:.1f} mi"
    return f"{miles:.2f} mi"


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
