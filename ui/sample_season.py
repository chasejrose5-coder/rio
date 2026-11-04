# sample_season.py — one fixed TEST athlete. No network and no model.

"""A separate 800 m season with eight weeks of fake runs.

The dates, paces, laps, and heart rates are constants. Loading again
replaces that athlete. Another login is never written.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from ui.accounts import normalize_email
from ui.cloud_store import CloudAuthError
from ui.strava import match_runs, to_stored_activity

TEST_EMAIL = "test+rio@example.invalid"
TEST_NAME = "TEST Athlete"
CURRENT = "2:05.0"
START = "2026-09-08"
GOAL = "1:59.0"
GOAL_DAY = "2027-03-08"
# Eight weeks after the first day of training, fixed so a later clock does not
# change the runs.
CUTOFF = date(2026, 11, 3)
_FAST = Decimal("0.90")
_SLOW = Decimal("1.12")


class TestSeasonError(ValueError):
    """The test season could not be changed. The message is safe to show."""

    __test__ = False


def build_test_season() -> dict:
    """The goal, the full plan, and the fake runs. Two calls match."""
    from engines.pace import workout_times
    from engines.season import sequence

    plan = sequence(CURRENT, START, GOAL, GOAL_DAY)
    start = date.fromisoformat(START)
    goal_day = date.fromisoformat(GOAL_DAY)
    sessions = [row for row in plan["sessions"] if isinstance(row, dict)]
    planned = set()
    for session in sessions:
        text = session.get("date")
        if isinstance(text, str):
            planned.add(text)
    runs = _matched_runs(sessions, start, goal_day)
    runs.extend(_extra_runs(sessions, planned))
    runs.sort(key=lambda row: (row["date"], row["id"]))
    return {
        "email": TEST_EMAIL,
        "name": TEST_NAME,
        "inputs": (CURRENT, START, GOAL, GOAL_DAY),
        "goal": {
            "event": "800m",
            "goal_time": GOAL,
            "goal_date": GOAL_DAY,
            "current_mark": CURRENT,
        },
        "plan_row": {
            "current_time": CURRENT,
            "start_date": START,
            "goal_time": GOAL,
            "goal_date": GOAL_DAY,
            "plan": plan,
            "marks": {},
            "actuals": {},
        },
        "plan": plan,
        "runs": runs,
    }


def load_test_season(directory, strava, service_key: str, *, caller_id: object = None, caller_email: object = None) -> dict:
    """Create or replace the TEST athlete. The caller's rows stay put."""
    _ready(directory, strava, service_key, caller_email, "The test season could not be saved.")
    try:
        user_id = directory.find_user_by_email(TEST_EMAIL, service_key)
        created = user_id is None
        if user_id is None:
            user_id = directory.create_confirmed_user(TEST_EMAIL, TEST_NAME, service_key)
        if _is_caller(user_id, caller_id):
            raise TestSeasonError("This login was left unchanged.")
        built = build_test_season()
        directory.write_owned_season(user_id, service_key, built["goal"], built["plan_row"], TEST_NAME)
        strava.delete_user(user_id, service_key)
        strava.put_activities(user_id, built["runs"])
    except TestSeasonError:
        raise
    except CloudAuthError as exc:
        raise TestSeasonError(str(exc)) from None
    except Exception:
        raise TestSeasonError("The test season could not be saved.") from None
    return {"user_id": user_id, "runs": len(built["runs"]), "created": created}


def delete_test_season(directory, strava, service_key: str, *, caller_id: object = None, caller_email: object = None) -> bool:
    """Remove the TEST athlete and every row that belongs to it.

    False when that athlete is already gone. The caller's account stays.
    """
    _ready(directory, strava, service_key, caller_email, "The test season could not be removed.")
    try:
        user_id = directory.find_user_by_email(TEST_EMAIL, service_key)
        if user_id is None:
            return False
        if _is_caller(user_id, caller_id):
            raise TestSeasonError("This login was left unchanged.")
        strava.delete_user(user_id, service_key)
        directory.delete_user_by_id(user_id, service_key)
    except TestSeasonError:
        raise
    except CloudAuthError as exc:
        raise TestSeasonError(str(exc)) from None
    except Exception:
        raise TestSeasonError("The test season could not be removed.") from None
    return True


def read_test_bundle(directory, strava, service_key: str) -> dict | None:
    """The stored TEST season, matched to its plan. None when it is not loaded."""
    if directory is None or strava is None:
        return None
    if not isinstance(service_key, str) or not service_key.strip():
        return None
    try:
        user_id = directory.find_user_by_email(TEST_EMAIL, service_key)
        if user_id is None:
            return None
        owned = directory.read_owned_season(user_id, service_key)
    except CloudAuthError:
        return None
    if not isinstance(owned, dict):
        return None
    row = owned.get("plan_row")
    plan = row.get("plan") if isinstance(row, dict) else None
    if not isinstance(plan, dict):
        return None
    sessions = plan.get("sessions") if isinstance(plan.get("sessions"), list) else []
    try:
        runs = match_runs(strava.get_activities(user_id), sessions)
    except Exception:
        return None
    return {
        "user_id": user_id,
        "name": TEST_NAME,
        "inputs": (
            str(row.get("current_time") or ""),
            str(row.get("start_date") or ""),
            str(row.get("goal_time") or ""),
            str(row.get("goal_date") or ""),
        ),
        "plan": plan,
        "runs": runs,
        "activities": [to_stored_activity(run) for run in runs],
    }


def _ready(directory, strava, service_key: str, caller_email: object, message: str) -> None:
    if directory is None or strava is None:
        raise TestSeasonError(message)
    if not isinstance(service_key, str) or not service_key.strip():
        raise TestSeasonError(message)
    if normalize_email(caller_email) == TEST_EMAIL:
        raise TestSeasonError("This login was left unchanged.")


def _is_caller(user_id: object, caller_id: object) -> bool:
    return isinstance(user_id, str) and isinstance(caller_id, str) and user_id == caller_id and bool(user_id)


def _matched_runs(sessions: list, start: date, goal_day: date) -> list[dict]:
    from engines.pace import workout_times

    runs = []
    index = 0
    for session in sessions:
        text = session.get("date")
        template = session.get("template_id")
        if not isinstance(text, str) or not isinstance(template, str):
            continue
        try:
            day = date.fromisoformat(text)
        except ValueError:
            continue
        if day < date.fromisoformat(START) or day > CUTOFF:
            continue
        if index % 5 == 4:
            index += 1
            continue
        week = session.get("week_number")
        fast = isinstance(week, int) and not isinstance(week, bool) and week <= 2
        prescribed = workout_times(
            template,
            current_mark=CURRENT,
            goal_mark=GOAL,
            start=start,
            goal_date=goal_day,
            on=day,
            logs=[],
        )
        if not isinstance(prescribed, dict) or not prescribed.get("reps"):
            index += 1
            continue
        factor = _FAST if fast else _SLOW
        heart = None if index % 7 == 6 else 138 + (index % 5) * 4
        laps = []
        for rep in prescribed["reps"]:
            meters = int(rep["meters"])
            seconds = int((Decimal(rep["seconds"]) * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            if seconds < 1:
                seconds = 1
            lap = {"distance_m": float(meters), "moving_seconds": seconds}
            if heart is not None:
                lap["average_hr"] = heart
            laps.append(lap)
        runs.append(_run(text, f"TEST {template}", template, True, laps, heart, index))
        index += 1
    return runs


def _extra_runs(sessions: list, planned: set[str]) -> list[dict]:
    by_week: dict[int, date] = {}
    for session in sessions:
        text = session.get("date")
        week = session.get("week_number")
        if not isinstance(text, str) or isinstance(week, bool) or not isinstance(week, int):
            continue
        try:
            day = date.fromisoformat(text)
        except ValueError:
            continue
        if day > CUTOFF:
            continue
        by_week.setdefault(week, day)
    taken = set(planned)
    runs = []
    for week in sorted(by_week):
        anchor = _sunday(by_week[week])
        chosen = None
        for offset in range(7):
            candidate = anchor + timedelta(days=offset)
            if candidate < date.fromisoformat(START) or candidate > CUTOFF:
                continue
            if candidate.isoformat() in taken:
                continue
            chosen = candidate
            break
        if chosen is None:
            continue
        taken.add(chosen.isoformat())
        distance = 6000 if week % 2 == 0 else 4000
        seconds = 1980 if distance == 6000 else 1440
        heart = None if week % 3 == 0 else 132 + week
        lap = {"distance_m": float(distance), "moving_seconds": seconds}
        if heart is not None:
            lap["average_hr"] = heart
        runs.append(_run(chosen.isoformat(), "TEST Extra", "", False, [lap], heart, week))
    return runs


def _run(day: str, name: str, template: str, matched: bool, laps: list, heart: int | None, index: int) -> dict:
    distance = float(sum(lap["distance_m"] for lap in laps))
    total = sum(int(lap["moving_seconds"]) for lap in laps)
    average = int(round(total / len(laps))) if laps else total
    pace = (total / (distance / 1000.0)) if distance else None
    row = {
        "id": f"test-{day}",
        "name": name,
        "sport_type": "Run",
        "date": day,
        "start_local": f"{day}T07:{index % 50:02d}:00",
        "distance_m": distance,
        "moving_seconds": average,
        "elapsed_seconds": total,
        "pace_s_per_km": float(pace) if pace is not None else None,
        "average_hr": heart,
        "max_hr": None if heart is None else heart + 12,
        "laps": laps,
        "template_id": template,
        "matched": matched,
    }
    return row


def _sunday(day: date) -> date:
    return day - timedelta(days=(day.weekday() + 1) % 7)
