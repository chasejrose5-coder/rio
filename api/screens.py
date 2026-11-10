# screens.py — the reads and settings writes the current pages already do.

"""Home, Plan, Activity, Library, Profile, and Settings.

These call the same helpers the Streamlit pages call. They do not
rebuild a season and they do not call the model. Easy pace is not
passed into sequence() or adapt().
"""

from __future__ import annotations

from datetime import date, timedelta

from api.errors import ApiError
from api.identity import Principal
from api.prefs import account_prefs, athlete_payload
from engines.pace import PACE_MILE, PaceLog, pace_unit, project_800, workout_recipe, workout_times
from ui.accounts import AccountError, normalize_name, read_local, write_easy_pace, write_local
from ui.activities import with_matched_distances
from ui.activity_board import build_cards, group_weeks, heart_points, week_summary, weekly_meters
from ui.activity_data import all_activities, session_rows
from ui.calendar import month_title, month_weeks, opening_month, plan_months
from ui.cloud_store import CloudAuthError
from ui.dashboard import current_week, dashboard_view, session_facts
from ui.settings import display_training, format_date
from ui.workout_text import WORKOUT_TEXT
from ui.insights import no_plan_copy, phase_story
from ui.library import filter_workouts, library_rows
from ui.no_watch import next_open_workout
from ui.profile import profile_fields, profile_key, shown_goal
from ui.progress import progress_weeks
from ui.settings import TIME_ZONES

_SCREEN = ("date_format", "start_date", "confirm_adapt", "show_ids", "compact", "preferred")


def json_ready(value):
    """Dates become YYYY-MM-DD. Everything else is left as the helper returned it."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value


def _phase(rows: list) -> int | None:
    for session in rows:
        if not isinstance(session, dict):
            continue
        for code in session.get("reason_codes") or []:
            text = str(code)
            if len(text) == 7 and text.startswith("phase_") and text[6] in "12345678":
                return int(text[6])
    return None


def next_session_day(plan_or_sessions, today: date) -> str | None:
    """The next planned date, or the latest one when nothing is left.

    Today is the athlete's date. Dates compare as YYYY-MM-DD.
    """
    sessions = plan_or_sessions
    if isinstance(plan_or_sessions, dict):
        sessions = plan_or_sessions.get("sessions")
    if not isinstance(sessions, list) or not isinstance(today, date):
        return None
    days = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        day = session.get("date")
        if isinstance(day, str) and day.strip():
            days.append(day.strip())
    if not days:
        return None
    days.sort()
    today_text = today.isoformat()
    for day in days:
        if day >= today_text:
            return day
    return days[-1]


def _upcoming(sessions: list, today: date, count: int = 3) -> list[dict]:
    rows = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        text = session.get("date")
        if not isinstance(text, str):
            continue
        try:
            day = date.fromisoformat(text)
        except ValueError:
            continue
        if day >= today:
            rows.append(session)
    rows.sort(key=lambda session: str(session.get("date")))
    return rows[:count]


_WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def _positive(values: object) -> list[float]:
    if not isinstance(values, (list, tuple)):
        return []
    found = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        number = float(value)
        if number > 0:
            found.append(number)
    return found


def _pace_logs(season) -> list[PaceLog]:
    """Logged times already stored. The average of a rep workout is one log."""
    logs: list[PaceLog] = []
    actuals = season.actuals if isinstance(season.actuals, dict) else {}
    activities = season.activities if isinstance(season.activities, list) else []
    by_day: dict[str, dict] = {}
    for row in activities:
        if isinstance(row, dict) and isinstance(row.get("date"), str) and row["date"] not in by_day:
            by_day[row["date"]] = row
    sessions = season.plan.get("sessions") if isinstance(season.plan, dict) else []
    if not isinstance(sessions, list):
        return logs
    for session in sessions:
        if not isinstance(session, dict):
            continue
        text = session.get("date")
        template = str(session.get("template_id") or "").strip()
        if not isinstance(text, str) or not template:
            continue
        try:
            day = date.fromisoformat(text)
        except ValueError:
            continue
        numbers: list[float] = []
        saved = actuals.get(text)
        if isinstance(saved, dict) and saved.get("template_id") == template:
            numbers = _positive(saved.get("numbers")) or _positive(saved.get("slots"))
        if not numbers:
            match = by_day.get(text)
            if isinstance(match, dict):
                numbers = _positive(match.get("reps"))
        if not numbers:
            continue
        logs.append(PaceLog(day, sum(numbers) / len(numbers), template))
    return logs


def _pace_status(season, today: date, easy_pace: str, easy_unit: str, logs: list[PaceLog]) -> str:
    if not logs:
        return "No runs yet"
    try:
        found = project_800(
            current_mark=season.inputs[0],
            goal_mark=season.inputs[2],
            start=date.fromisoformat(season.inputs[1]),
            goal_date=date.fromisoformat(season.inputs[3]),
            on=today,
            logs=logs,
            easy_pace=easy_pace,
            easy_unit=easy_unit,
        )
    except ValueError:
        return "Not enough data"
    text = str(found.get("status") or "on track")
    return text[:1].upper() + text[1:]


def _present_session(session: dict, season, *, units: str, date_format: str, easy_pace: str, easy_unit: str, logs: list[PaceLog]) -> dict:
    """The card copy, the facts, and the clock line. The stored plan is not changed."""
    shown = dict(session)
    template = str(session.get("template_id") or "").strip()
    raw = WORKOUT_TEXT.get(template, template)
    label = display_training(raw, units) if raw else "—"
    if not label:
        label = "—"
    facts = session_facts(template, raw or "")
    recipe = workout_recipe(template)
    continuous = bool(recipe and recipe.get("continuous"))
    distance = str(facts.get("distance") or "—")
    if continuous:
        converted = display_training(distance, units)
        distance = converted or distance
    pace = str(facts.get("pace") or "—")
    rest = str(facts.get("rest") or "—")
    if rest == "—":
        rest = "No rest"
    if continuous:
        pace = easy_pace_phrase_or_ask(easy_pace, easy_unit)
    shown["label"] = label
    shown["facts"] = {
        "distance": distance,
        "pace": pace,
        "rest": rest,
        "reps": str(facts.get("reps") or "—"),
    }
    day_text = str(session.get("date") or "")
    try:
        day = date.fromisoformat(day_text)
    except ValueError:
        day = None
    shown["shown_date"] = format_date(day_text, date_format) if day_text else "—"
    prescription = None
    if day is not None and template:
        try:
            found = workout_times(
                template,
                current_mark=season.inputs[0],
                goal_mark=season.inputs[2],
                start=date.fromisoformat(season.inputs[1]),
                goal_date=date.fromisoformat(season.inputs[3]),
                on=day,
                logs=logs,
                easy_pace=easy_pace,
                easy_unit=easy_unit,
            )
        except ValueError:
            found = None
        if isinstance(found, dict):
            line = str(found.get("line") or "").strip()
            if found.get("easy_unset") or (continuous and not line):
                line = "Set your easy pace before this run."
            elif continuous and line and not line.lower().startswith("run at "):
                line = f"Run at {line}"
            if line:
                prescription = {
                    "line": line,
                    "tolerance": "" if continuous else str(found.get("tolerance") or ""),
                    "block": "" if continuous else str(found.get("block") or ""),
                }
    shown["prescription"] = prescription
    return shown


def easy_pace_phrase_or_ask(easy_pace: str, easy_unit: str) -> str:
    from engines.pace import easy_pace_phrase

    phrase = easy_pace_phrase(easy_pace, easy_unit) if easy_pace else ""
    return phrase or "Set your easy pace"


def _blank_day(day: date, date_format: str) -> dict:
    return {
        "date": day.isoformat(),
        "shown_date": format_date(day, date_format),
        "day_of_week": _WEEKDAYS[day.weekday()],
        "template_id": "",
        "label": "—",
        "facts": None,
        "prescription": None,
    }


def _next_days(sessions: list, today: date, season, *, units: str, date_format: str, easy_pace: str, easy_unit: str, logs: list[PaceLog]) -> list[dict]:
    """The three calendar days after today. A rest day still takes a card."""
    by_date: dict[date, dict] = {}
    for session in sessions:
        if not isinstance(session, dict):
            continue
        text = session.get("date")
        if not isinstance(text, str):
            continue
        try:
            day = date.fromisoformat(text)
        except ValueError:
            continue
        if day <= today or day in by_date:
            continue
        by_date[day] = session
    rows = []
    for offset in range(1, 4):
        day = today + timedelta(days=offset)
        found = by_date.get(day)
        if found is None:
            rows.append(_blank_day(day, date_format))
            continue
        ready = json_ready(found)
        if isinstance(ready, dict):
            rows.append(
                _present_session(
                    ready,
                    season,
                    units=units,
                    date_format=date_format,
                    easy_pace=easy_pace,
                    easy_unit=easy_unit,
                    logs=logs,
                )
            )
    return rows


def home_view(principal, directory, today: date, season, *, connected: bool, strava: dict, just_generated: bool) -> dict:
    from ui.accounts import hey
    from ui.plan_strava import should_offer_strava

    prefs = account_prefs(principal, directory)
    body = {
        "today": today.isoformat(),
        "athlete": athlete_payload(principal, prefs),
        "hello": hey(principal.display_name),
        "strava": strava,
        "strava_offer": should_offer_strava(
            just_generated=just_generated,
            connected=connected,
            dismissed=prefs.get("strava_prompt_seen") is True,
        ),
        "season": None,
        "copy": no_plan_copy(),
        "next_session": None,
    }
    if season is None:
        return body
    sessions = season.plan.get("sessions") if isinstance(season.plan, dict) else []
    if not isinstance(sessions, list):
        sessions = []
    start_text = season.plan.get("start_date") if isinstance(season.plan, dict) else None
    length = season.plan.get("season_length_weeks") if isinstance(season.plan, dict) else None
    try:
        start = date.fromisoformat(str(start_text))
        goal = date.fromisoformat(season.inputs[3])
    except ValueError:
        return body
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        return body
    view = dashboard_view(
        start=start,
        goal=goal,
        length=length,
        sessions=sessions,
        marks=season.marks,
        today=today,
    )
    week = current_week(start=start, length=length, today=today)
    rows = [
        session
        for session in sessions
        if isinstance(session, dict) and week is not None and session.get("week_number") == week
    ]
    phase = _phase(rows)
    thin = not season.actuals and not connected
    story = None
    if phase is not None and isinstance(week, int):
        story = phase_story(phase=phase, week=week, sessions=sessions, thin=thin)
    shown = view.get("next")
    if prefs["prefs"].get("no_watch") is True:
        shown = next_open_workout(sessions, today, season.actuals)
    units = str(prefs["prefs"].get("units") or "miles")
    date_format = str(prefs["prefs"].get("date_format") or "iso")
    easy_pace = str(prefs.get("easy_pace") or "")
    easy_unit = str(prefs.get("easy_pace_unit") or "mi")
    logs = _pace_logs(season)
    ready_next = json_ready(shown)
    if isinstance(ready_next, dict):
        ready_next = _present_session(
            ready_next,
            season,
            units=units,
            date_format=date_format,
            easy_pace=easy_pace,
            easy_unit=easy_unit,
            logs=logs,
        )
    upcoming = []
    for item in json_ready(_upcoming(sessions, today)):
        if isinstance(item, dict):
            upcoming.append(
                _present_session(
                    item,
                    season,
                    units=units,
                    date_format=date_format,
                    easy_pace=easy_pace,
                    easy_unit=easy_unit,
                    logs=logs,
                )
            )
    notes = []
    for day, item in season.notes.items():
        if isinstance(item, dict) and item.get("viewed") is not True and isinstance(item.get("note"), dict):
            notes.append({"date": day, "note": item["note"], "viewed": False})
    body["copy"] = ""
    body["season"] = {
        "inputs": {
            "current_time": season.inputs[0],
            "start_date": season.inputs[1],
            "goal_time": season.inputs[2],
            "goal_date": season.inputs[3],
        },
        "digest": season.digest,
        "view": json_ready(view),
        "phase": story,
        "pace_status": _pace_status(season, today, easy_pace, easy_unit, logs),
        "next": ready_next,
        "upcoming": upcoming,
        "next_days": _next_days(
            sessions,
            today,
            season,
            units=units,
            date_format=date_format,
            easy_pace=easy_pace,
            easy_unit=easy_unit,
            logs=logs,
        ),
        "notes": notes,
        "activities": json_ready(season.activities),
        "logging": "done" if prefs["prefs"].get("no_watch") is True else "times",
        "next_session": next_session_day(sessions, today),
    }
    body["next_session"] = body["season"]["next_session"]
    day = body["season"]["next"].get("date") if isinstance(body["season"].get("next"), dict) else None
    actuals = season.actuals if isinstance(season.actuals, dict) else {}
    actual = actuals.get(day) if isinstance(day, str) else None
    template = body["season"]["next"].get("template_id") if isinstance(body["season"].get("next"), dict) else None
    if isinstance(actual, dict) and actual.get("template_id") == template and isinstance(body["season"].get("next"), dict):
        body["season"]["next"]["actual"] = actual
    return body


def plan_view(season, today: date, prefs: dict, month: str | None) -> dict:
    sessions = season.plan.get("sessions") if isinstance(season.plan, dict) else []
    if not isinstance(sessions, list):
        sessions = []
    try:
        start = date.fromisoformat(str(season.plan.get("start_date")))
        goal = date.fromisoformat(season.inputs[3])
    except ValueError:
        raise ApiError(400, "This season has no dates.")
    length = season.plan.get("season_length_weeks")
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        raise ApiError(400, "This season has no weeks.")
    months = plan_months(sessions)
    chosen = opening_month(months, today)
    if month is not None:
        # Omitted month is the month that contains today. A present value must be YYYY-MM.
        if (
            not isinstance(month, str)
            or len(month) != 7
            or month[4] != "-"
            or not month[:4].isdigit()
            or not month[5:7].isdigit()
        ):
            raise ApiError(400, "The month is not YYYY-MM.")
        try:
            chosen = date(int(month[:4]), int(month[5:7]), 1)
        except ValueError:
            raise ApiError(400, "The month is not YYYY-MM.") from None
    weeks = month_weeks(chosen.year, chosen.month, sessions, today)
    activities = season.activities if isinstance(season.activities, list) else []
    # Matched WORK meters only. A day with no file and no match stays at 0.
    # Template meters are not used. Intervals file laps are the known hole (W13).
    progress = progress_weeks(
        start=start,
        goal=goal,
        length=length,
        sessions=sessions,
        marks=season.marks,
        today=today,
        distances=with_matched_distances({}, activities),
    )
    units = str(prefs.get("units") or "miles")
    date_format = str(prefs.get("date_format") or "iso")
    easy_pace = str(prefs.get("easy_pace") or "")
    easy_unit = str(prefs.get("easy_pace_unit") or "mi")
    logs = _pace_logs(season)
    presented = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        ready = _present_session(
            session,
            season,
            units=units,
            date_format=date_format,
            easy_pace=easy_pace,
            easy_unit=easy_unit,
            logs=logs,
        )
        for key in ("probability", "readiness", "readiness_score"):
            ready.pop(key, None)
        raw_target = session.get("target_outcome")
        target = display_training(raw_target, units) if isinstance(raw_target, str) else ""
        ready["target"] = target or "—"
        template = str(session.get("template_id") or "")
        # Speed days show the rep line. Streamlit leaves the block clock off those cards.
        prescription = ready.get("prescription")
        if isinstance(prescription, dict) and template.startswith(("spd_", "mv_")):
            prescription = dict(prescription)
            prescription["block"] = ""
            ready["prescription"] = prescription
        presented.append(ready)
    return {
        "inputs": {
            "current_time": season.inputs[0],
            "start_date": season.inputs[1],
            "goal_time": season.inputs[2],
            "goal_date": season.inputs[3],
        },
        "digest": season.digest,
        "marks": {str(week): mark for week, mark in sorted(season.marks.items())},
        "prefs": prefs,
        "months": [item.isoformat() for item in months],
        "month": f"{chosen.year:04d}-{chosen.month:02d}",
        "month_title": month_title(chosen),
        "calendar": json_ready(weeks),
        "weeks": json_ready(progress),
        "sessions": json_ready(presented),
    }


def intervals_pull(connected: bool, sessions: list, stored: object, today: date) -> tuple[list, str | None]:
    """The pull Plan runs when Strava is not connected.

    A connected Strava account skips Intervals, so the notice stays empty.
    A missing key raises PullError with "is not set". Any other pull failure
    is the same notice string Streamlit stores. The raw text is not shown.
    """
    rows = stored if isinstance(stored, list) else []
    if connected:
        return rows, None
    from ui.activities import PullError, sync_recent

    try:
        # The process already loaded .env at startup. Do not read it again here.
        updated = sync_recent(sessions, rows, today, load_env=lambda: None)
    except PullError as exc:
        return rows, str(exc)
    if not isinstance(updated, list):
        return rows, None
    return updated, None


def library_view(query: str, family: str, phase: int | None) -> dict:
    from engines.prescribe import load_menu

    try:
        menu = load_menu()
    except ValueError as exc:
        raise ApiError(500, str(exc)) from exc
    rows = library_rows(menu)
    visible = filter_workouts(rows, query=query, family=family, phase=phase)
    families = []
    labels = {}
    for row in rows:
        name = row.get("family") or ""
        if name and name not in families:
            families.append(name)
            labels[name] = row.get("capacity") or name
    return {
        "count": len(visible),
        "workouts": visible,
        "families": [{"id": name, "label": labels.get(name, name)} for name in families],
    }


def activity_view(season, today: date, prefs: dict, easy_pace: str, easy_unit: str) -> dict:
    sessions = season.plan.get("sessions") if isinstance(season.plan, dict) else []
    if not isinstance(sessions, list):
        sessions = []
    try:
        start = date.fromisoformat(str(season.plan.get("start_date")))
        goal_day = date.fromisoformat(season.inputs[3])
    except ValueError:
        raise ApiError(400, "This season has no dates.")
    length = season.plan.get("season_length_weeks")
    if isinstance(length, bool) or not isinstance(length, int):
        length = 0
    unit = pace_unit(prefs.get("pace_units") or PACE_MILE)
    date_format = prefs.get("date_format") or "iso"
    activities = season.activities if isinstance(season.activities, list) else []
    cards = build_cards(
        [],
        activities,
        sessions,
        current=season.inputs[0],
        goal=season.inputs[2],
        start=start,
        goal_day=goal_day,
        unit=unit,
        date_format=date_format,
        easy_pace=easy_pace or None,
        easy_unit=easy_unit or None,
    )
    summary = week_summary(cards, today, unit)
    groups = group_weeks(cards, today)
    return {
        "rows": session_rows(activities, sessions, date_format=date_format),
        "all": all_activities(activities, date_format=date_format),
        "cards": json_ready(cards),
        "groups": json_ready(groups),
        "summary": json_ready(summary),
        "weekly_meters": weekly_meters(cards, start, length),
        "heart": heart_points(cards),
        "logged": logged_activities(activities, str(prefs.get("units") or "miles")),
    }


def profile_view(season, resolved: dict, override: str | None = None) -> dict:
    prefs = resolved["prefs"]
    easy = {
        "easy_pace": resolved["easy_pace"],
        "easy_pace_unit": resolved["easy_pace_unit"],
        "easy_pace_phrase": resolved["easy_pace_phrase"],
    }
    if season is None:
        return {
            "ready": False,
            "fields": [],
            "profile_key": "",
            "goal_time": "",
            "goal_override": None,
            "shown_goal": "",
            **easy,
            "prefs": prefs,
        }
    key = profile_key(season.inputs)
    shown = shown_goal(season.inputs[2], override)
    fields = profile_fields(season.inputs[0], season.inputs[1], shown, season.inputs[3])
    return {
        "ready": True,
        "fields": [{"label": label, "value": value} for label, value in fields],
        "profile_key": key,
        "goal_time": season.inputs[2],
        "goal_override": override,
        "shown_goal": shown,
        "inputs": {
            "current_time": season.inputs[0],
            "start_date": season.inputs[1],
            "goal_time": season.inputs[2],
            "goal_date": season.inputs[3],
        },
        **easy,
        "prefs": prefs,
    }


_REASON_PLAIN = {
    "phase_1": "Phase 1",
    "phase_2": "Phase 2",
    "phase_3": "Phase 3",
    "phase_4": "Phase 4",
    "phase_5": "Phase 5",
    "phase_6": "Phase 6",
    "phase_7": "Phase 7",
    "phase_8": "Phase 8",
    "phase_primary": "Primary work for this phase",
    "phase_secondary": "Secondary work for this phase",
    "weekly_aerobic_long_run": "The weekly long run",
    "priority_speed_endurance": "Speed endurance is a priority",
    "priority_aerobic_power": "Aerobic power is a priority",
    "priority_anaerobic_capacity": "Anaerobic capacity is a priority",
    "capacity_weight": "The higher capacity weight won",
    "ten_percent_hold": "Held so the week does not rise more than 10%",
    "ten_percent_easier_template": "An easier session, so the week stays within 10%",
    "extra_easy_day": "An extra easy day",
    "extra_easy_week": "An easy week",
    "harder_template": "A harder session",
    "moved_back_one_phase": "Moved back one phase",
    "advanced_one_phase": "Advanced one phase",
    "phase_8_freshness": "The taper stays fresh",
    "phase_8_no_hard_se_or_an": "No hard speed endurance or anaerobic work",
}


def _plain_reason(code: object) -> str:
    text = str(code).strip()
    if not text:
        return ""
    known = _REASON_PLAIN.get(text)
    if known:
        return known
    if len(text) == 7 and text.startswith("phase_") and text[6].isdigit():
        return f"Phase {text[6]}"
    return text.replace("_", " ")


def _reason_lines(codes: object) -> list[str]:
    lines = []
    for code in codes or []:
        words = _plain_reason(code)
        if words:
            lines.append(words)
    return lines


def _structure_text(template_id: str, units: str) -> str:
    key = template_id.strip()
    menu_text = ""
    if key:
        try:
            from engines.prescribe import load_menu

            for row in load_menu():
                if isinstance(row, dict) and str(row.get("id") or "").strip() == key:
                    menu_text = str(row.get("default_structure") or "").strip()
                    break
        except ValueError:
            menu_text = ""
    text = menu_text or WORKOUT_TEXT.get(key, key)
    shown = display_training(text, units) if isinstance(text, str) and text else ""
    return shown or "—"


def _result_summary(saved: object) -> str:
    if not isinstance(saved, dict):
        return ""
    parts = []
    for number in saved.get("numbers") or []:
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            continue
        if isinstance(number, float) and number.is_integer():
            parts.append(str(int(number)))
        else:
            parts.append(str(number))
    text = ", ".join(parts)
    mark = saved.get("mark")
    if text and mark in ("on_track", "not_hitting", "smashing"):
        return f"{text} · {mark}"
    return ""


def _seed_slots(saved: object, count: int) -> list:
    from services.season_commit import stored_slot

    slots: list = [None] * count
    if not isinstance(saved, dict):
        return slots
    stored = saved.get("slots")
    if isinstance(stored, list):
        for index in range(min(count, len(stored))):
            slots[index] = stored_slot(stored[index])
        return slots
    numbers = saved.get("numbers")
    if not isinstance(numbers, list):
        return slots
    filled = [stored_slot(number) for number in numbers]
    filled = [slot for slot in filled if slot is not None]
    for index, slot in enumerate(filled[:count]):
        slots[index] = slot
    return slots


def _match_block(match: object, units: str) -> dict | None:
    from ui.activities import meters_text
    from ui.last_session import heart_rate_text
    from ui.result import filled_times
    from ui.settings import display_distance

    if not isinstance(match, dict):
        return None
    reps = filled_times(match.get("reps") or [])
    volume = meters_text(match.get("work_m"))
    shown = display_distance(volume, units) if volume else ""
    heart = ""
    if match.get("heart_rate") is not None:
        heart = heart_rate_text({"average_heartrate": match.get("heart_rate")}) or ""
    if not reps and not shown and not heart:
        return None
    return {"reps": reps, "work": shown, "heart_rate": heart}


def logged_activities(activities: object, units: str) -> list[dict]:
    """One card per stored activity. An extra has matched false and no result form."""
    from ui.activities import meters_text
    from ui.last_session import heart_rate_text
    from ui.result import filled_times
    from ui.settings import display_distance

    rows = []
    for row in activities or []:
        if not isinstance(row, dict):
            continue
        ident = row.get("id")
        if not isinstance(ident, str) or not ident.strip():
            continue
        volume = meters_text(row.get("work_m"))
        shown = display_distance(volume, units) if volume else ""
        heart = ""
        if row.get("heart_rate") is not None:
            heart = heart_rate_text({"average_heartrate": row.get("heart_rate")}) or ""
        name = row.get("name")
        title = name.strip() if isinstance(name, str) and name.strip() else "Activity"
        rows.append(
            {
                "id": ident.strip(),
                "date": str(row.get("date") or ""),
                "name": title,
                "matched": row.get("matched") is True,
                "reps": filled_times(row.get("reps") or []),
                "volume": shown,
                "heart_rate": heart,
            }
        )
    return rows


def session_view(season, day: str, resolved: dict | None = None) -> dict | None:
    """One planned day, with the words and the clock the session page shows.

    Easy and long runs use the saved easy pace. Quality families keep the
    fractions workout_times already applied. The prep notes are not stored.
    """
    from engines.pace import average_rep_text, effort_pace, pace_unit, workout_recipe, workout_times
    from services.season_commit import quality_day
    from ui.activities import matched_on
    from ui.last_session import activity_by_ref, fit_slots, heart_rate_text
    from ui.result import result_box_count

    sessions = season.plan.get("sessions") if isinstance(season.plan, dict) else []
    found = None
    if isinstance(sessions, list):
        for session in sessions:
            if isinstance(session, dict) and str(session.get("date") or "") == day:
                found = session
                break
    if found is None:
        return None
    resolved = resolved or {}
    prefs = resolved.get("prefs") if isinstance(resolved.get("prefs"), dict) else {}
    units = str(prefs.get("units") or "miles")
    date_format = str(prefs.get("date_format") or "iso")
    easy_pace = str(resolved.get("easy_pace") or "")
    easy_unit = str(resolved.get("easy_pace_unit") or "mi")
    logs = _pace_logs(season)
    presented = _present_session(
        found,
        season,
        units=units,
        date_format=date_format,
        easy_pace=easy_pace,
        easy_unit=easy_unit,
        logs=logs,
    )
    template = str(found.get("template_id") or "")
    recipe = workout_recipe(template)
    continuous = bool(recipe and recipe.get("continuous"))
    activities = season.activities if isinstance(season.activities, list) else []
    match = matched_on(activities, day)
    block = _match_block(match, units)
    prescription = presented.get("prescription")
    if isinstance(prescription, dict):
        prescription = dict(prescription)
        if recipe and recipe.get("speed"):
            prescription["block"] = ""
        if continuous:
            prescription["average"] = ""
            actual_pace = effort_pace(match, pace_unit(prefs.get("pace_units") or "mi")) if isinstance(match, dict) else ""
            line = str(prescription.get("line") or "")
            if actual_pace and "Actual " not in line:
                prescription["line"] = f"{line} · Actual {actual_pace}"
        else:
            try:
                clock = workout_times(
                    template,
                    current_mark=season.inputs[0],
                    goal_mark=season.inputs[2],
                    start=date.fromisoformat(season.inputs[1]),
                    goal_date=date.fromisoformat(season.inputs[3]),
                    on=date.fromisoformat(day),
                    logs=logs,
                    easy_pace=easy_pace,
                    easy_unit=easy_unit,
                )
            except ValueError:
                clock = None
            average = average_rep_text(clock.get("reps") if isinstance(clock, dict) else None)
            prescription["average"] = average
        presented["prescription"] = prescription
    stored = season.actuals.get(day) if isinstance(season.actuals, dict) else None
    actual = stored if isinstance(stored, dict) else None
    same = actual if isinstance(actual, dict) and actual.get("template_id") == found.get("template_id") else None
    item = season.notes.get(day)
    note = item.get("note") if isinstance(item, dict) else None
    viewed = item.get("viewed") is True if isinstance(item, dict) else None
    hard = quality_day(found)
    logging = "done" if prefs.get("no_watch") is True else "times"
    count = result_box_count(template) if hard and logging == "times" else 0
    seed = _seed_slots(same, count) if count else []
    if count and same is None and isinstance(match, dict) and not any(slot is not None for slot in seed):
        seed = fit_slots(match.get("reps"), count)
    extra_hr = ""
    ref = same.get("intervals") if isinstance(same, dict) else None
    if isinstance(ref, str) and ref.strip():
        file_activity = activity_by_ref(ref)
        text = heart_rate_text(file_activity) if isinstance(file_activity, dict) else None
        shown = block.get("heart_rate") if isinstance(block, dict) else ""
        if text and text != shown:
            extra_hr = text
    target = presented.get("target") if isinstance(presented.get("target"), str) else ""
    if not target:
        raw_target = found.get("target_outcome")
        target = display_training(raw_target, units) if isinstance(raw_target, str) else ""
    return {
        "date": day,
        "session": found,
        "actual": actual,
        "quality": hard,
        "note": note if isinstance(note, dict) else None,
        "viewed": viewed,
        "digest": season.digest,
        "label": presented.get("label") or "—",
        "structure": _structure_text(template, units),
        "target": target or "—",
        "reasons": _reason_lines(found.get("reason_codes") or []),
        "shown_date": presented.get("shown_date") or day,
        "facts": presented.get("facts"),
        "prescription": presented.get("prescription"),
        "logging": logging,
        "confirm_adapt": prefs.get("confirm_adapt") is True,
        "show_id": prefs.get("show_ids") is True,
        "boxes": count,
        "seed": seed,
        "summary": _result_summary(same),
        "match": block,
        "heart_rate": extra_hr,
    }


def _reject_zone(zone: object) -> str:
    if not isinstance(zone, str) or zone not in TIME_ZONES:
        raise ApiError(400, "Choose a time zone from the list.")
    return zone


def _reject_pace(unit: object) -> str:
    if unit not in ("mi", "km"):
        raise ApiError(400, "Pace is per mile or per km.")
    return str(unit)


def apply_settings(principal: Principal, directory, patch: dict) -> dict:
    """Write the fields Settings and Profile already save. Unknown fields are ignored.

    A bad value is refused before any write. The plan is not touched.
    """
    known = (
        "pace_units",
        "timezone",
        "no_watch",
        "easy_pace",
        "easy_pace_unit",
        "display_name",
        "preferred",
        "intro_seen",
        "strava_prompt_seen",
        "date_format",
        "start_date",
        "confirm_adapt",
        "show_ids",
        "compact",
    )
    sent = {key: patch[key] for key in known if key in patch and patch[key] is not None}
    if not sent:
        raise ApiError(400, "Nothing to save.")
    if "pace_units" in sent:
        _reject_pace(sent["pace_units"])
    if "timezone" in sent:
        _reject_zone(sent["timezone"])
    if "no_watch" in sent and not isinstance(sent["no_watch"], bool):
        raise ApiError(400, "Logging could not be saved.")
    if "intro_seen" in sent and not isinstance(sent["intro_seen"], bool):
        raise ApiError(400, "The intro guide could not be saved.")
    if "strava_prompt_seen" in sent and not isinstance(sent["strava_prompt_seen"], bool):
        raise ApiError(400, "The Strava prompt could not be saved.")
    if "confirm_adapt" in sent and not isinstance(sent["confirm_adapt"], bool):
        raise ApiError(400, "That setting could not be saved.")
    if "show_ids" in sent and not isinstance(sent["show_ids"], bool):
        raise ApiError(400, "That setting could not be saved.")
    if "compact" in sent and not isinstance(sent["compact"], bool):
        raise ApiError(400, "That setting could not be saved.")
    if "display_name" in sent and normalize_name(sent["display_name"]) is None:
        raise ApiError(400, "Enter a name.")
    if "preferred" in sent and sent["preferred"] != "" and normalize_name(sent["preferred"]) is None:
        raise ApiError(400, "That nickname will not work.")
    if "date_format" in sent and sent["date_format"] not in ("iso", "short"):
        raise ApiError(400, "That setting could not be saved.")
    if "start_date" in sent and sent["start_date"] not in ("today", "sunday"):
        raise ApiError(400, "That setting could not be saved.")
    easy = None
    if "easy_pace" in sent or "easy_pace_unit" in sent:
        if "easy_pace" not in sent or "easy_pace_unit" not in sent:
            raise ApiError(400, "Enter a pace like 7:25.")
        from ui.cloud_store import stored_easy_pair

        easy = stored_easy_pair(sent["easy_pace"], sent["easy_pace_unit"])
        if easy is None:
            raise ApiError(400, "Enter a pace like 7:25.")
    screen = {key: sent[key] for key in _SCREEN if key in sent}
    if principal.kind == "local":
        _write_local(principal, sent, easy)
    else:
        _write_hosted(principal, directory, sent, easy, screen)
    return account_prefs(principal, directory)


def _write_local(principal: Principal, sent: dict, easy) -> None:
    path = principal.accounts_path
    local = read_local(path, principal.email) or {}
    settings = dict(local.get("settings") or {})
    for key in ("pace_units", "no_watch", "date_format", "start_date", "confirm_adapt", "show_ids", "compact", "intro_seen", "strava_prompt_seen"):
        if key in sent:
            settings[key] = sent[key]
    name = sent.get("display_name", local.get("name") or "")
    preferred = sent.get("preferred", local.get("preferred") or "")
    zone = sent.get("timezone", local.get("timezone") or "")
    try:
        saved = write_local(path, principal.email, principal.seal, name, preferred, zone, settings)
        if easy is not None:
            saved = write_easy_pace(path, principal.email, principal.seal, easy[0], easy[1])
    except AccountError as exc:
        raise ApiError(400, str(exc)) from exc
    if isinstance(saved, dict) and isinstance(saved.get("name"), str):
        principal.display_name = saved["name"]


def _write_hosted(principal: Principal, directory, sent: dict, easy, screen: dict) -> None:
    token = principal.token
    if not isinstance(token, str) or directory is None:
        raise ApiError(401, "Sign in again.")
    try:
        if "pace_units" in sent:
            directory.save_pace_units(token, sent["pace_units"])
        if "timezone" in sent:
            directory.save_timezone(token, sent["timezone"])
        if "no_watch" in sent:
            directory.save_no_watch(token, sent["no_watch"])
        if easy is not None:
            directory.save_easy_pace(token, easy[0], easy[1])
        if "intro_seen" in sent:
            directory.save_intro_seen(token, sent["intro_seen"])
        if "strava_prompt_seen" in sent:
            directory.save_strava_prompt_seen(token, sent["strava_prompt_seen"])
    except CloudAuthError as exc:
        raise ApiError(400, str(exc)) from exc
    if "display_name" in sent:
        name = normalize_name(sent["display_name"])
        if hasattr(directory, "users"):
            user = directory.users.get(principal.user_id)
            if isinstance(user, dict) and isinstance(name, str):
                user["display_name"] = name
                principal.display_name = name
        elif hasattr(directory, "_user_client"):
            try:
                client = directory._user_client(token)
                client.table("profiles").update({"display_name": name}).eq("id", principal.user_id).execute()
                principal.display_name = name or principal.display_name
            except Exception as exc:
                raise ApiError(400, "Enter a name.") from exc
    if screen or "preferred" in sent:
        stored = dict(screen)
        if "preferred" in sent:
            stored["preferred"] = normalize_name(sent["preferred"]) or ""
        if hasattr(directory, "users"):
            user = directory.users.get(principal.user_id)
            if isinstance(user, dict):
                user.update(stored)
        elif hasattr(directory, "_auth_user_update"):
            try:
                directory._auth_user_update(token, stored)
            except Exception as exc:
                raise ApiError(400, "That setting could not be saved.") from exc
