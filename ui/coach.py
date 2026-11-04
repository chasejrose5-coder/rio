# coach.py — team codes and the same pace status Home prints.

"""A team code is short and easy to read. Status comes from project_800.

The same marks and logs always return the same status. Nothing here is
learned, and a coach cannot write an athlete's plan through these helpers.
"""

from __future__ import annotations

import secrets
from datetime import date

from engines.pace import PaceLog, project_800
from ui.cloud_store import CloudAuthError
from ui.dashboard import dashboard_view

# No 0, O, 1, or I. Those are easy to misread.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CODE_LENGTH = 7


def new_code() -> str:
    """Seven characters. The old code stops working when a coach makes another."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LENGTH))


def code_ok(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip().upper()
    if len(text) < 6 or len(text) > 8:
        return False
    return all(char in _ALPHABET for char in text)


def normalize_code(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().upper()


def change_member_role(
    directory,
    actor_email: object,
    target_id: object,
    target_email: object,
    role: object,
    service_key: object,
) -> None:
    """Athlete or coach, with the server key. A person cannot change their own role."""
    from ui.accounts import normalize_email

    actor = normalize_email(actor_email)
    target = normalize_email(target_email)
    if actor is None or target is None or actor == target:
        raise CloudAuthError("You can't change your own role.")
    if role not in ("athlete", "coach"):
        raise CloudAuthError("Choose athlete or coach.")
    directory.set_role(target_id, role, service_key)


def season_summary(plan_row: object, *, today: date) -> dict:
    """Goal, days, phase, and pace status. Empty seasons stay blank."""
    blank = {"goal_time": "—", "days": "—", "phase": "—", "status": "—"}
    if not isinstance(plan_row, dict):
        return blank
    goal_time = str(plan_row.get("goal_time") or "").strip() or "—"
    plan = plan_row.get("plan") if isinstance(plan_row.get("plan"), dict) else {}
    sessions = plan.get("sessions") if isinstance(plan.get("sessions"), list) else []
    if not sessions:
        return {**blank, "goal_time": goal_time}
    try:
        start = date.fromisoformat(str(plan_row.get("start_date")))
        goal_day = date.fromisoformat(str(plan_row.get("goal_date")))
    except ValueError:
        return {**blank, "goal_time": goal_time}
    length = plan.get("season_length_weeks")
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        length = 1
    marks = plan_row.get("marks") if isinstance(plan_row.get("marks"), dict) else {}
    view = dashboard_view(
        start=start,
        goal=goal_day,
        length=length,
        sessions=sessions,
        marks=marks,
        today=today,
    )
    phase = str(view.get("phase") or "—")
    phase_text = "—" if phase in ("", "—") else f"Phase {phase}"
    status = _status(plan_row, sessions, start, goal_day, today)
    return {
        "goal_time": goal_time,
        "days": str(view.get("days_label") or "—"),
        "phase": phase_text,
        "status": status,
    }


def _status(plan_row: dict, sessions: list, start: date, goal_day: date, today: date) -> str:
    try:
        found = project_800(
            current_mark=plan_row.get("current_time"),
            goal_mark=plan_row.get("goal_time"),
            start=start,
            goal_date=goal_day,
            on=today,
            logs=_logs(sessions, plan_row.get("actuals")),
        )
    except ValueError:
        return "On track"
    text = str(found.get("status") or "on track")
    return text[:1].upper() + text[1:]


def _logs(sessions: list, actuals: object) -> list[PaceLog]:
    """Logged results stored in RIO. Matched files from elsewhere are not used."""
    if not isinstance(actuals, dict):
        return []
    logs: list[PaceLog] = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        text = session.get("date")
        template = str(session.get("template_id") or "").strip()
        if not isinstance(text, str) or not template:
            continue
        saved = actuals.get(text)
        if not isinstance(saved, dict) or saved.get("template_id") != template:
            continue
        numbers = []
        for key in ("numbers", "slots"):
            values = saved.get(key)
            if not isinstance(values, list):
                continue
            for value in values:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                number = float(value)
                if number > 0:
                    numbers.append(number)
            if numbers:
                break
        if not numbers:
            continue
        try:
            day = date.fromisoformat(text)
        except ValueError:
            continue
        logs.append(PaceLog(day, sum(numbers) / len(numbers), template))
    return logs
