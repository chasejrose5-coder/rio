# recap.py — one selected week: what was recorded, and what the next week already says.

"""Display fields for the week chosen on Weekly. The plan is the one Start stored.

A session counts as completed when that day has a stored result for the
same template. A week mark with no results still counts as marked. Marks
are the stored on_track, not_hitting, and smashing words. Volume is this
week beside the week before. A day with a loaded Intervals file contributes
that file's WORK distance. A day with no file contributes 0. A week with
no file shows 0 m. Template meters are not used. The next-week sentence
is fixed words for an adapt reason code already stored on the following week.

No model. No spend. No scores.
"""

from __future__ import annotations

from ui.progress import MARKS, week_volume

# Adapt codes, in the order they are stored. The first one present is the sentence.
_CHANGE = (
    ("extra_easy_week", "Next week is an easy week."),
    ("harder_template", "Next week uses a harder session."),
    ("moved_back_one_phase", "Next week moves back one phase."),
    ("advanced_one_phase", "Next week advances one phase."),
)


def week_rows(sessions: list, week: int) -> list[dict]:
    """Sessions in this week, earliest date first."""
    if isinstance(week, bool) or not isinstance(week, int):
        return []
    rows = [
        session
        for session in sessions or []
        if isinstance(session, dict) and session.get("week_number") == week
    ]
    rows.sort(key=lambda session: str(session.get("date") or ""))
    return rows


def recap_view(
    *,
    week: int,
    sessions: list,
    actuals: dict | None,
    marks: dict | None,
    distances: dict | None = None,
) -> dict:
    """Completed sessions, marks, volume, and one sentence for the next week.

    Actuals and marks are the ones already stored. A missing week is a blank.
    Volume sums loaded WORK distance for this week and the week before.
    A day with no file contributes 0. A week with no file shows 0 m.
    Template meters are not used. The sentence reads the following week's
    reason codes and does not call adapt.
    """
    rows = week_rows(sessions, week)
    previous = week_rows(sessions, week - 1) if isinstance(week, int) and not isinstance(week, bool) else []
    following = week_rows(sessions, week + 1) if isinstance(week, int) and not isinstance(week, bool) else []
    stored = actuals if isinstance(actuals, dict) else {}
    week_mark = _week_mark(marks, week)
    return {
        "completed": _completed_text(rows, stored, week_mark),
        "marks": _marks_text(rows, stored, week_mark),
        "volume": _volume_text(rows, previous, distances),
        "next": _next_sentence(following),
    }


def _week_mark(marks: dict | None, week: int) -> str | None:
    if not isinstance(marks, dict) or isinstance(week, bool) or not isinstance(week, int):
        return None
    mark = marks.get(week)
    if mark in MARKS:
        return mark
    return None


def _saved(session: dict, actuals: dict) -> dict | None:
    row = actuals.get(session.get("date"))
    if not isinstance(row, dict):
        return None
    if row.get("template_id") != session.get("template_id"):
        return None
    return row


def _is_completed(row: dict) -> bool:
    numbers = row.get("numbers")
    if isinstance(numbers, list) and any(not isinstance(item, bool) for item in numbers):
        return True
    return row.get("mark") in MARKS


def _completed_text(rows: list[dict], actuals: dict, week_mark: str | None) -> str:
    done = sum(1 for session in rows if (saved := _saved(session, actuals)) and _is_completed(saved))
    if done == 0 and week_mark in MARKS:
        return "Marked"
    if not rows:
        return "—"
    return f"{done} of {len(rows)}"


def _marks_text(rows: list[dict], actuals: dict, week_mark: str | None) -> str:
    found: list[str] = []
    seen: list[str] = []
    for session in rows:
        saved = _saved(session, actuals)
        if saved is None:
            continue
        mark = saved.get("mark")
        if mark not in MARKS:
            continue
        if mark not in seen:
            seen.append(mark)
        day = str(session.get("day_of_week") or "").strip()
        found.append(f"{day} {mark}".strip() if day else mark)
    if week_mark in MARKS and week_mark not in seen:
        found.append(week_mark)
    if not found:
        return "—"
    return " · ".join(found)


def _volume_text(rows: list[dict], previous: list[dict], distances: dict | None) -> str:
    current = week_volume(rows, distances)
    if not previous:
        return current
    return f"{current} · {week_volume(previous, distances)} the week before"


def _next_sentence(following: list[dict]) -> str:
    if not following:
        return "This is the last week."
    codes: list[str] = []
    for session in following:
        found = session.get("reason_codes") or []
        if not isinstance(found, list):
            continue
        for code in found:
            text = str(code)
            if text not in codes:
                codes.append(text)
    for code, sentence in _CHANGE:
        if code in codes:
            return sentence
    return "Next week stays as written."
