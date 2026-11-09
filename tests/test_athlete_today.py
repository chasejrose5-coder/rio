# test_athlete_today.py — today follows the time zone saved in Settings.

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.activities import activity_window
from ui.calendar import month_weeks
from ui.dashboard import current_week, next_workout
from ui.progress import days_remaining
from ui.settings import chosen_timezone, local_today, session_timezone, suggested_timezone

# Monday 9 Nov 2026, 03:30 UTC is Sunday 8 Nov 2026, 19:30 in Pacific standard time.
_MONDAY_MORNING_UTC = datetime(2026, 11, 9, 3, 30, tzinfo=timezone.utc)
# 07:30 UTC is still Sunday evening in Pacific and already Monday in New York.
_ZONE_CHANGE = datetime(2026, 11, 9, 7, 30, tzinfo=timezone.utc)
# Sunday 8 Nov 2026, 04:00 UTC is Saturday 7 Nov 2026, 20:00 in Pacific.
_SATURDAY_NIGHT_PACIFIC = datetime(2026, 11, 8, 4, 0, tzinfo=timezone.utc)
_SURFACES = (
    "_pull_for",
    "_route_after_login",
    "_next_session_day",
    "page_start",
    "_plan_weeks",
    "_pace_status_label",
    "_on_today",
    "_phase_timeline",
    "_render_this_week",
    "_remember_workout_note",
    "page_dashboard",
    "page_calendar",
    "page_progress",
    "page_weekly",
    "page_activity",
    "page_plan",
)


def _function(source: str, name: str) -> str:
    start = source.index(f"def {name}(")
    rest = source[start + 1 :]
    nxt = rest.find("\ndef ")
    if nxt < 0:
        return source[start:]
    return source[start : start + 1 + nxt]


def _marked(weeks: list, day: str) -> bool:
    for week in weeks:
        for cell in week:
            if cell.get("date") == day:
                return bool(cell.get("today"))
    raise AssertionError(day)


def test_pacific_sunday_during_utc_monday_morning() -> None:
    """America/Los_Angeles keeps Sunday until midnight Pacific."""
    sunday = local_today("America/Los_Angeles", _MONDAY_MORNING_UTC)
    if sunday != date(2026, 11, 8) or sunday.strftime("%A") != "Sunday":
        raise AssertionError(sunday)
    if local_today("UTC", _MONDAY_MORNING_UTC) != date(2026, 11, 9):
        raise AssertionError("UTC Monday morning was not Monday")
    naive = datetime(2026, 11, 9, 3, 30)
    if local_today("America/Los_Angeles", naive) != date(2026, 11, 8):
        raise AssertionError("a naive UTC clock was not treated as UTC")
    late_afternoon = datetime(2026, 11, 9, 0, 30, tzinfo=timezone.utc)
    if local_today("America/Los_Angeles", late_afternoon) != date(2026, 11, 8):
        raise AssertionError(late_afternoon)


def test_changing_the_saved_zone_changes_today() -> None:
    """The same instant is a different day after the saved zone changes."""
    pacific = local_today("America/Los_Angeles", _ZONE_CHANGE)
    eastern = local_today("America/New_York", _ZONE_CHANGE)
    utc = local_today("UTC", _ZONE_CHANGE)
    if pacific != date(2026, 11, 8):
        raise AssertionError(pacific)
    if eastern != date(2026, 11, 9) or utc != date(2026, 11, 9):
        raise AssertionError((eastern, utc))
    if chosen_timezone("America/Los_Angeles") != "America/Los_Angeles":
        raise AssertionError("the saved zone was dropped")
    if chosen_timezone("America/Los_Angeles", "America/New_York") != "America/New_York":
        raise AssertionError("a new Settings zone did not replace the saved one")
    if local_today(chosen_timezone("UTC", "Asia/Tokyo"), _ZONE_CHANGE) != date(2026, 11, 9):
        raise AssertionError("Tokyo did not move today")


def test_a_blank_zone_uses_the_settings_suggestion() -> None:
    """No saved zone uses suggested_timezone(), the fallback Settings already uses."""
    suggested = suggested_timezone()
    now = _MONDAY_MORNING_UTC
    if local_today("", now) != local_today(suggested, now):
        raise AssertionError("a blank zone did not use the suggestion")
    if local_today("Not/A_Zone", now) != local_today(suggested, now):
        raise AssertionError("an unknown zone did not use the suggestion")
    if chosen_timezone(None, None) != suggested or chosen_timezone("", "") != suggested:
        raise AssertionError(chosen_timezone("", ""))
    if session_timezone() != suggested:
        raise AssertionError(session_timezone())


def test_plan_surfaces_treat_that_sunday_as_today() -> None:
    """Calendar, next workout, the current week, days left, and the activity window."""
    sunday = local_today("America/Los_Angeles", _MONDAY_MORNING_UTC)
    monday = local_today("UTC", _MONDAY_MORNING_UTC)
    weeks = month_weeks(2026, 11, [], today=sunday)
    if not _marked(weeks, "2026-11-08") or _marked(weeks, "2026-11-09"):
        raise AssertionError("the calendar did not highlight Sunday")
    sessions = [
        {"date": "2026-11-08", "day_of_week": "Sunday", "template_id": "aer_5000_r0_x1"},
        {"date": "2026-11-09", "day_of_week": "Monday", "template_id": "aer_5000_r0_x1"},
    ]
    found = next_workout(sessions, sunday)
    if found is None or found["date"] != "2026-11-08":
        raise AssertionError(found)
    later = next_workout(sessions, monday)
    if later is None or later["date"] != "2026-11-09":
        raise AssertionError(later)
    # Sunday and the following Monday share a training week. The week rolls
    # at midnight Saturday in the saved zone, which is still Saturday in Pacific
    # while UTC has already reached Sunday.
    saturday = local_today("America/Los_Angeles", _SATURDAY_NIGHT_PACIFIC)
    sunday_utc = local_today("UTC", _SATURDAY_NIGHT_PACIFIC)
    if saturday != date(2026, 11, 7) or sunday_utc != date(2026, 11, 8):
        raise AssertionError((saturday, sunday_utc))
    start = date(2026, 10, 4)
    pacific_week = current_week(start=start, length=12, today=saturday)
    utc_week = current_week(start=start, length=12, today=sunday_utc)
    if pacific_week is None or utc_week != pacific_week + 1:
        raise AssertionError((pacific_week, utc_week))
    goal = date(2026, 12, 1)
    if days_remaining(goal, sunday) != days_remaining(goal, monday) + 1:
        raise AssertionError("days remaining ignored the zone")
    if activity_window(sunday)[1] != "2026-11-08":
        raise AssertionError(activity_window(sunday))
    if activity_window(monday)[1] != "2026-11-09":
        raise AssertionError(activity_window(monday))


def test_a_hosted_zone_reloads_and_changes_today() -> None:
    """The hosted account keeps the Settings zone. Another athlete is left alone."""
    from ui.cloud_store import CloudAuthError, _zone_from_metadata, reset_memory_directory

    if _zone_from_metadata({"user_metadata": {"timezone": "America/Los_Angeles"}}) != "America/Los_Angeles":
        raise AssertionError("metadata lost the zone")
    if _zone_from_metadata({"user_metadata": {}}) is not None:
        raise AssertionError("a missing zone was invented")
    if _zone_from_metadata({"user_metadata": {"timezone": "Not/A_Zone"}}) is not None:
        raise AssertionError("an unknown zone was accepted")
    directory = reset_memory_directory()
    ada = directory.sign_up("ada-zone@example.com", "password-one", "Ada")
    beau = directory.sign_up("beau-zone@example.com", "password-two", "Beau")
    directory.save_timezone(ada["access_token"], "America/New_York")
    kept = directory.load_bundle(ada["access_token"])
    if kept["profile"].get("timezone") != "America/New_York":
        raise AssertionError(kept["profile"])
    if local_today(kept["profile"]["timezone"], _ZONE_CHANGE) != date(2026, 11, 9):
        raise AssertionError("the reloaded zone did not change today")
    directory.save_timezone(ada["access_token"], "America/Los_Angeles")
    again = directory.load_bundle(ada["access_token"])
    if again["profile"].get("timezone") != "America/Los_Angeles":
        raise AssertionError(again["profile"])
    if local_today(again["profile"]["timezone"], _MONDAY_MORNING_UTC) != date(2026, 11, 8):
        raise AssertionError("Los Angeles did not stay on Sunday")
    other = directory.load_bundle(beau["access_token"])
    if "timezone" in other["profile"]:
        raise AssertionError(other["profile"])
    try:
        directory.save_timezone(ada["access_token"], "Not/A_Zone")
    except CloudAuthError:
        rejected = True
    else:
        rejected = False
    if not rejected:
        raise AssertionError("a bad zone was stored")
    if directory.load_bundle(ada["access_token"])["profile"].get("timezone") != "America/Los_Angeles":
        raise AssertionError("a bad zone replaced the saved one")


def test_athlete_pages_read_the_saved_zone() -> None:
    """Home, Plan, Start, Activity, and the other athlete pages share one today."""
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    settings = (ROOT / "ui" / "settings.py").read_text(encoding="utf-8")
    helper = _function(app, "_athlete_today")
    if "local_today()" not in helper:
        raise AssertionError(helper)
    for name in _SURFACES:
        body = _function(app, name)
        if "_athlete_today()" not in body or "date.today()" in body:
            raise AssertionError(name)
    home = _function(app, "page_dashboard")
    if "_upcoming_days(sessions, _athlete_today(), 3)" not in home:
        raise AssertionError("next 3 days still starts from the server date")
    if "today=_athlete_today()" not in home:
        raise AssertionError("Home does not pass the saved zone into the plan")
    for name in ("page_next", "page_ledger"):
        body = _function(app, name)
        if "date.today()" not in body:
            raise AssertionError(name)
    reader = _function(settings, "session_timezone")
    if 'get("rio_local")' not in reader or 'get("settings-timezone")' not in reader:
        raise AssertionError("today does not read the saved zone")
    if "suggested_timezone()" not in _function(settings, "chosen_timezone"):
        raise AssertionError("a blank zone lost the Settings suggestion")
    strava = (ROOT / "ui" / "strava_ui.py").read_text(encoding="utf-8")
    zone = _function(strava, "_zone_name")
    if "session_timezone()" not in zone:
        raise AssertionError("activity times ignore the saved zone")
    if "save_timezone(" not in _function(app, "_persist_local"):
        raise AssertionError("a hosted zone is not saved")
    cloud = (ROOT / "ui" / "cloud_ui.py").read_text(encoding="utf-8")
    if 'current["timezone"] = zone' not in _function(cloud, "_apply_bundle"):
        raise AssertionError("a hosted zone is not restored")
    store = (ROOT / "ui" / "cloud_store.py").read_text(encoding="utf-8")
    if 'profile["timezone"] = zone' not in _function(store, "_load_bundle"):
        raise AssertionError("a hosted bundle dropped the zone")


def main() -> None:
    test_pacific_sunday_during_utc_monday_morning()
    test_changing_the_saved_zone_changes_today()
    test_a_blank_zone_uses_the_settings_suggestion()
    test_plan_surfaces_treat_that_sunday_as_today()
    test_a_hosted_zone_reloads_and_changes_today()
    test_athlete_pages_read_the_saved_zone()
    print("athlete today ok")


if __name__ == "__main__":
    main()
