# calendar.py — one month of the plan Start already stored. Display only.

"""A Sunday–Saturday month. A day with a session gets a short label.

Race is only the 800 race. Other race-readiness days stay race readiness.
The Saturday long run is Long. The easy aerobic days are Easy. Short fast
work is Speed. The other quality days keep their own short name.

No model. No spend. No scores.
"""

from __future__ import annotations

from datetime import date, timedelta

# The words on a day. Race is the one race template, not every rr_ day.
RACE_ID = "rr_800_r0_x1"
# Saturday long-run ids. 10 km stays Easy unless the week marks it as the
# long run, because that id is also an easy hold.
LONG_IDS = (
    "aer_9500_r0_x1",
    "aer_10500_r0_x1",
    "aer_11000_r0_x1",
    "aer_11500_r0_x1",
    "aer_12000_r0_x1",
    "aer_12500_r0_x1",
    "aer_13000_r0_x1",
    "aer_13500_r0_x1",
    "aer_14000_r0_x1",
    "aer_14500_r0_x1",
    "aer_15000_r0_x1",
)

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)

# Prefixes of the frozen ids, after Race, Long, and Easy have been taken.
_SPEED = ("spd_", "mv_")
_OTHER = (
    ("thr_", "Threshold"),
    ("ap_", "Aerobic power"),
    ("se_", "Speed endurance"),
    ("an_", "Anaerobic"),
)


def month_title(day: date) -> str:
    """October 2026. The name is fixed so it does not follow the machine locale."""
    return f"{_MONTHS[day.month - 1]} {day.year}"


def session_label(template_id: object, reason_codes: object = None) -> str:
    """The short word for one stored session. Blank when the id is blank.

    Race is only rr_800_r0_x1. A long-run id, or the weekly long-run code,
    is Long even when the id also starts with aer_. Other aerobic ids are Easy.
    """
    template = str(template_id or "").strip()
    if not template:
        return ""
    if template == RACE_ID:
        return "Race"
    if template.startswith("rr_"):
        return "Race readiness"
    codes = reason_codes if isinstance(reason_codes, list) else []
    if template in LONG_IDS or "weekly_aerobic_long_run" in codes:
        return "Long"
    if template.startswith("aer_"):
        return "Easy"
    if template.startswith(_SPEED):
        return "Speed"
    for prefix, label in _OTHER:
        if template.startswith(prefix):
            return label
    return ""


def plan_months(sessions: list) -> list[date]:
    """The first day of each month from the first session through the last."""
    found: list[date] = []
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        text = session.get("date")
        if not isinstance(text, str):
            continue
        try:
            found.append(date.fromisoformat(text))
        except ValueError:
            continue
    if not found:
        return []
    earliest = min(found)
    latest = max(found)
    cursor = date(earliest.year, earliest.month, 1)
    end = date(latest.year, latest.month, 1)
    months: list[date] = []
    while cursor <= end:
        months.append(cursor)
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return months


def opening_month(months: list[date], today: date) -> date:
    """The month that contains today, or the nearest end of the plan."""
    if not months:
        return date(today.year, today.month, 1)
    current = date(today.year, today.month, 1)
    if current in months:
        return current
    if current < months[0]:
        return months[0]
    return months[-1]


def month_weeks(
    year: int,
    month: int,
    sessions: list,
    today: date | None = None,
) -> list[list[dict]]:
    """Sunday–Saturday weeks covering the month.

    Days outside the month stay in the grid so the columns line up. They
    carry no session. A day in the month keeps its label and template id.
    """
    if isinstance(month, bool) or not isinstance(month, int) or not 1 <= month <= 12:
        return []
    if isinstance(year, bool) or not isinstance(year, int):
        return []
    by_date: dict[date, dict] = {}
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        text = session.get("date")
        if not isinstance(text, str):
            continue
        try:
            day = date.fromisoformat(text)
        except ValueError:
            continue
        if day not in by_date:
            by_date[day] = session
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    cursor = first - timedelta(days=(first.weekday() + 1) % 7)
    end = last + timedelta(days=(5 - last.weekday()) % 7)
    weeks: list[list[dict]] = []
    while cursor <= end:
        week: list[dict] = []
        for _ in range(7):
            in_month = cursor.year == year and cursor.month == month
            session = by_date.get(cursor) if in_month else None
            template = ""
            label = ""
            if isinstance(session, dict):
                template = str(session.get("template_id") or "").strip()
                label = session_label(template, session.get("reason_codes"))
            week.append(
                {
                    "date": cursor.isoformat(),
                    "in_month": in_month,
                    "day": cursor.day if in_month else 0,
                    "label": label,
                    "template_id": template,
                    "today": today == cursor and in_month,
                }
            )
            cursor += timedelta(days=1)
        weeks.append(week)
    return weeks
