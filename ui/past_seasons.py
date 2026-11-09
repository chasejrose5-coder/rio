# past_seasons.py — seasons this browser already stored. Display only.

"""A row is a plan key already in this browser.

The key is the four inputs. Start date, goal date, and goal time are shown
from those inputs. A plan is active while its goal date is today or later.
Nothing here builds a season.

No model. No spend.
"""

from __future__ import annotations

import math
import re
from datetime import date

from ui.plan_store import inputs_ok, storage_key

# A single 800, not a set of 800 repeats. The id is the one already stored.
_SINGLE_800 = re.compile(r"_800_r0_x1$")
_PHASE = re.compile(r"^phase_([1-8])$")
_CLOCK = re.compile(r"^(\d+):(\d{2})(\.\d+)?$")
_SUMMARY_KEYS = (
    "actuals",
    "activities",
    "plan",
    "event",
    "notes",
    "insights",
    "adaptations",
    "results",
)

# The plan key prefix. A profile record and any other key stay off this list.
KEY_PREFIX = "rio.plan.v1\n"


def inputs_from_key(key: object) -> tuple[str, str, str, str] | None:
    """The four inputs in a plan key, or None when the key is not one."""
    if not isinstance(key, str) or not key.startswith(KEY_PREFIX):
        return None
    parts = key[len(KEY_PREFIX) :].split("\n")
    if len(parts) != 4:
        return None
    inputs = (parts[0], parts[1], parts[2], parts[3])
    if not inputs_ok(inputs) or storage_key(inputs) != key:
        return None
    return inputs


def keys_from_inputs(rows: object) -> list[str]:
    """Plan keys for stored input rows. A bad row is left out."""
    if not isinstance(rows, list):
        return []
    keys: list[str] = []
    for item in rows:
        if isinstance(item, (list, tuple)):
            item = tuple(item)
        if not inputs_ok(item):
            continue
        key = storage_key(item)
        if key not in keys:
            keys.append(key)
    return keys


def season_entries(keys: object) -> list[tuple[str, str, str, str]]:
    """Stored seasons, one per plan key.

    Junk is left out. The same four inputs stay one row. Order is start
    date, then goal date, then goal time.
    """
    if not isinstance(keys, list):
        return []
    found: dict[tuple[str, str, str, str], None] = {}
    for key in keys:
        inputs = inputs_from_key(key)
        if inputs is None or inputs in found:
            continue
        found[inputs] = None
    rows = list(found)
    rows.sort(key=lambda item: (item[1], item[3], item[2], item[0]))
    return rows


def has_active_plan(keys: object, today: date) -> bool:
    """True when a stored plan's goal date is today or later.

    No plan is not active. A goal date before today is finished. A profile
    record and any other key stay out.
    """
    if type(today) is not date:
        return False
    for inputs in season_entries(keys):
        if date.fromisoformat(inputs[3]) >= today:
            return True
    return False


def entry_fields(inputs: tuple[str, str, str, str]) -> list[tuple[str, str]]:
    """Start date, goal date, and goal time, as stored."""
    return [
        ("Start date", inputs[1]),
        ("Goal date", inputs[3]),
        ("Goal time", inputs[2]),
    ]


def is_past_season(inputs: object, today: date) -> bool:
    """True when this stored season's goal date is before today.

    A goal date of today is still the current season. A bad date is not past.
    """
    if not inputs_ok(inputs) or type(today) is not date:
        return False
    return date.fromisoformat(inputs[3]) < today


def confirm_deletes(pending: object, pressed: object, today: date) -> bool:
    """True only when the athlete confirmed a season that is already past.

    Opening the panel does not confirm. A current season does not confirm.
    """
    return pressed is True and is_past_season(pending, today)


def summary_record(raw: object) -> dict | None:
    """The stored fields a summary can read. Anything else is left out."""
    if not isinstance(raw, dict):
        return None
    kept = {}
    for key in _SUMMARY_KEYS:
        if key in raw:
            kept[key] = raw[key]
    return kept


def season_summary(inputs: object, stored: object) -> list[tuple[str, str]]:
    """Facts already stored for this season. A missing fact is left out.

    Dates and the goal time come from the season key. Counts come from the
    stored body. Nothing here is estimated from a template or a calendar.
    """
    if not inputs_ok(inputs):
        return []
    rows = [("Season", f"{inputs[1]} – {inputs[3]}"), ("Goal time", inputs[2])]
    if not isinstance(stored, dict):
        return rows
    event = stored.get("event")
    if isinstance(event, str) and event.strip():
        rows.insert(1, ("Event", event.strip()))
    actuals = stored.get("actuals") if isinstance(stored.get("actuals"), dict) else None
    if "actuals" in stored and isinstance(stored.get("actuals"), dict):
        logged, completed, saw_completed = _workout_counts(stored["actuals"])
        rows.append(("Workouts logged", str(logged)))
        if saw_completed:
            rows.append(("Workouts completed", str(completed)))
    elif isinstance(stored.get("results"), list):
        logged = sum(1 for item in stored["results"] if isinstance(item, dict))
        rows.append(("Workouts logged", str(logged)))
    distance = _logged_distance(stored.get("activities"))
    if distance is not None:
        rows.append(("Distance logged", distance))
    rows.extend(_timed_800(actuals))
    phases = _phases_completed(stored.get("plan"), actuals)
    if phases is not None:
        rows.append(("Phases completed", str(phases)))
    notes = _named_count(stored, "notes")
    if notes is not None:
        rows.append(("Notes", str(notes)))
    insights = _named_count(stored, "insights")
    if insights is not None:
        rows.append(("Insights", str(insights)))
    adaptations = _named_count(stored, "adaptations")
    if adaptations is not None:
        rows.append(("Adaptations", str(adaptations)))
    return rows


def without_season(plans: object, results: object, inputs: object) -> tuple[list, list]:
    """This athlete's plans and results after one season is removed.

    Other seasons stay, including their actuals. A result stays unless it
    names this season or matches one of this season's logged days.
    """
    if not inputs_ok(inputs):
        kept_plans = [item for item in plans if isinstance(item, dict)] if isinstance(plans, list) else []
        kept_results = [item for item in results if isinstance(item, dict)] if isinstance(results, list) else []
        return kept_plans, kept_results
    others: list = []
    actuals: dict = {}
    if isinstance(plans, list):
        for row in plans:
            if not isinstance(row, dict):
                continue
            ident = (
                str(row.get("current_time") or ""),
                str(row.get("start_date") or ""),
                str(row.get("goal_time") or ""),
                str(row.get("goal_date") or ""),
            )
            if ident == inputs:
                found = row.get("actuals")
                if isinstance(found, dict):
                    actuals.update(found)
                continue
            others.append(row)
    other_dates: set[str] = set()
    for row in others:
        found = row.get("actuals")
        if isinstance(found, dict):
            other_dates.update(day for day in found if isinstance(day, str))
    kept_results: list = []
    if isinstance(results, list):
        for result in results:
            if result_belongs_to_season(result, inputs, actuals, other_dates):
                continue
            if isinstance(result, dict):
                kept_results.append(result)
    return others, kept_results


def result_belongs_to_season(
    result: object,
    inputs: object,
    actuals: object,
    other_dates: object,
) -> bool:
    """True when this result row is stored for this season.

    A payload that names the four inputs belongs to this season. A logged
    day belongs to it when that day is in this season's actuals, the template
    matches when one is stored, and the day is not also stored on another
    season. A date that only falls inside the season is not enough.
    """
    if not isinstance(result, dict) or not inputs_ok(inputs):
        return False
    payload = result.get("payload")
    if isinstance(payload, dict):
        named = (
            str(payload.get("current_time") or ""),
            str(payload.get("start_date") or ""),
            str(payload.get("goal_time") or ""),
            str(payload.get("goal_date") or ""),
        )
        if named == inputs and any(named):
            return True
    logged = result.get("logged_on")
    if not isinstance(logged, str) or not logged:
        return False
    if isinstance(other_dates, (set, list, tuple)) and logged in other_dates:
        return False
    if not isinstance(actuals, dict):
        return False
    row = actuals.get(logged)
    if not isinstance(row, dict):
        return False
    template = result.get("template_id")
    if isinstance(template, str) and template.strip():
        return template.strip() == str(row.get("template_id") or "")
    return True


def _workout_counts(actuals: dict) -> tuple[int, int, bool]:
    logged = 0
    completed = 0
    saw_completed = False
    for value in actuals.values():
        if not isinstance(value, dict):
            continue
        logged += 1
        if "completed" in value:
            saw_completed = True
        if value.get("completed") is True:
            completed += 1
    return logged, completed, saw_completed


def _logged_distance(activities: object) -> str | None:
    """Sum of stored activity distances, in the meters already stored."""
    if not isinstance(activities, list):
        return None
    total = 0.0
    found = False
    for item in activities:
        if not isinstance(item, dict):
            continue
        distance = item.get("distance")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)):
            continue
        if not math.isfinite(distance) or distance <= 0:
            continue
        total += float(distance)
        found = True
    if not found:
        return None
    if total.is_integer():
        shown = str(int(total))
    else:
        shown = f"{total:.3f}".rstrip("0").rstrip(".")
    return f"{shown} m"


def _timed_800(actuals: dict | None) -> list[tuple[str, str]]:
    """A stored single 800. Rep splits and other distances stay out."""
    if not isinstance(actuals, dict):
        return []
    efforts: list[tuple[str, float, str]] = []
    for day, value in actuals.items():
        if not isinstance(day, str) or not isinstance(value, dict):
            continue
        template = value.get("template_id")
        if not isinstance(template, str) or _SINGLE_800.search(template) is None:
            continue
        label = value.get("text") if isinstance(value.get("text"), str) else ""
        seconds = _clock_seconds(label)
        if seconds is None:
            numbers = value.get("numbers")
            if (
                isinstance(numbers, list)
                and len(numbers) == 1
                and isinstance(numbers[0], (int, float))
                and not isinstance(numbers[0], bool)
                and math.isfinite(float(numbers[0]))
                and float(numbers[0]) > 0
            ):
                seconds = float(numbers[0])
                label = _format_clock(seconds)
            else:
                continue
        text = label.strip()
        if not text:
            continue
        efforts.append((day, seconds, text))
    if not efforts:
        return []
    efforts.sort()
    last = efforts[-1]
    if len(efforts) == 1:
        return [("Timed 800", last[2])]
    best = min(efforts, key=lambda item: (item[1], item[0]))
    rows = [("Last 800", last[2])]
    if best[1] < last[1]:
        rows.insert(0, ("Best 800", best[2]))
    return rows


def _phases_completed(plan: object, actuals: dict | None) -> int | None:
    """Phases whose stored sessions are all marked completed.

    The phase number is the one stored on the session. A phase with no
    session, or a plan with no phase, is left out rather than counted.
    """
    if not isinstance(plan, dict):
        return None
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        return None
    by_phase: dict[int, list[str]] = {}
    for session in sessions:
        if not isinstance(session, dict):
            continue
        codes = session.get("reason_codes")
        if not isinstance(codes, list):
            continue
        phase = None
        for code in codes:
            if not isinstance(code, str):
                continue
            match = _PHASE.fullmatch(code)
            if match is not None:
                phase = int(match.group(1))
                break
        day = session.get("date")
        if phase is None or not isinstance(day, str) or not day:
            continue
        by_phase.setdefault(phase, []).append(day)
    if not by_phase:
        return None
    done = 0
    for dates in by_phase.values():
        if not dates:
            continue
        if all(_completed_on(actuals, day) for day in dates):
            done += 1
    return done


def _completed_on(actuals: dict | None, day: str) -> bool:
    if not isinstance(actuals, dict):
        return False
    row = actuals.get(day)
    return isinstance(row, dict) and row.get("completed") is True


def _named_count(stored: dict, key: str) -> int | None:
    """A stored list's length. A missing list is left out. An empty one is 0."""
    if key not in stored:
        return None
    value = stored.get(key)
    if not isinstance(value, list):
        return None
    return len(value)


def _clock_seconds(text: str) -> float | None:
    match = _CLOCK.fullmatch(text.strip())
    if match is None:
        return None
    seconds = int(match.group(1)) * 60 + int(match.group(2))
    if match.group(3):
        seconds += float(match.group(3))
    if seconds <= 0:
        return None
    return float(seconds)


def _format_clock(seconds: float) -> str:
    """The stored seconds as m:ss or m:ss.t. The number is not rounded away."""
    whole = int(seconds)
    minutes, rest = divmod(whole, 60)
    fraction = seconds - whole
    if fraction <= 0:
        return f"{minutes}:{rest:02d}"
    tenths = int(round(fraction * 10))
    if tenths >= 10:
        rest += 1
        tenths = 0
        if rest >= 60:
            minutes += 1
            rest = 0
    if tenths == 0:
        return f"{minutes}:{rest:02d}"
    return f"{minutes}:{rest:02d}.{tenths}"
