# activity_board.py — one list of runs, grouped by week. Display only.

"""Plain names, pace lines, a week summary, and a heart-rate chart with an axis.

Raw template ids stay in hidden markup. The visible name is the workout
in words. Continuous runs use pace from engines.pace. Nothing here calls
a model or the network.
"""

from __future__ import annotations

import html
import re
from datetime import date, timedelta

from engines.pace import PACE_MILE, format_span, pace_unit, workout_recipe
from ui.calendar import LONG_IDS
from ui.progress import week_sunday
from ui.settings import format_date
from ui.strava import earlier_logs, planned_vs_actual

_CODE = re.compile(
    r"[A-Za-z]+_(?:(?:py|up)_)?\d+(?:to\d+)?_r\d+_x\d+",
    re.IGNORECASE,
)
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
_STATUSES = ("On track", "Ahead", "Behind", "Extra")
_BADGE = {
    "On track": "on-track",
    "Ahead": "ahead",
    "Behind": "behind",
    "Extra": "extra",
}


def plain_name(
    template_id: object,
    reason_codes: object = None,
    fallback: object = "",
    *,
    matched: bool = True,
) -> str:
    """Easy 5 km, Long 12 km, 8 × 150 m. A raw id is not the visible name."""
    recipe = workout_recipe(template_id)
    if recipe is not None:
        return _recipe_name(recipe, reason_codes)
    text = fallback.strip() if isinstance(fallback, str) else ""
    text = _CODE.sub("", text)
    text = text.replace("TEST", "").strip(" ·-")
    if matched and text and text.lower() != "extra":
        return text
    if text and text.lower() not in ("", "extra", "run"):
        return text
    return "Extra"


def build_cards(
    runs: object,
    activities: object,
    sessions: object,
    *,
    current: str,
    goal: str,
    start: date,
    goal_day: date,
    unit: object = PACE_MILE,
    date_format: str = "iso",
) -> list[dict]:
    """One card per run. A Strava row and the stored copy of it are one card."""
    chosen = pace_unit(unit)
    combined = _deduped(runs, activities)
    planned = _sessions_by_date(sessions)
    cards = []
    for run in combined:
        text = run.get("date")
        try:
            on = date.fromisoformat(str(text))
        except ValueError:
            continue
        session = planned.get(on.isoformat())
        template = str(run.get("template_id") or "")
        codes: list = []
        if isinstance(session, dict):
            if not template:
                found = session.get("template_id")
                if isinstance(found, str):
                    template = found
                    run = dict(run)
                    run["template_id"] = template
            raw_codes = session.get("reason_codes")
            if isinstance(raw_codes, list):
                codes = raw_codes
        matched = run.get("matched") is True and bool(template)
        try:
            compared = planned_vs_actual(
                run,
                current=current,
                goal=goal,
                start=start,
                goal_day=goal_day,
                on=on,
                logs=earlier_logs(combined, on),
                unit=chosen,
            )
        except (ValueError, ArithmeticError):
            compared = {
                "planned": "—",
                "actual": "Actual —",
                "status": "On track",
                "laps": [],
                "continuous": False,
                "speed": False,
            }
        status = str(compared.get("status") or "On track")
        if not matched:
            status = "Extra"
        if status not in _STATUSES:
            status = "On track"
        name = plain_name(template, codes, run.get("name"), matched=matched)
        if status == "Extra":
            name = _extra_name(name, run)
        meters = _meters(run)
        cards.append(
            {
                "id": str(run.get("id") or ""),
                "date": on.isoformat(),
                "on": on,
                "shown_date": format_date(on.isoformat(), date_format),
                "name": name,
                "template_id": template,
                "status": status,
                "detail": str(compared.get("actual") or "—"),
                "laps": compared.get("laps") if isinstance(compared.get("laps"), list) else [],
                "meters": meters,
                "heart_rate": _heart(run),
                "continuous": compared.get("continuous") is True,
                "speed": compared.get("speed") is True,
            }
        )
    return cards


def week_summary(cards: list[dict], today: date, unit: object = PACE_MILE) -> dict:
    """Distance, run count, and status counts for the week that contains today."""
    opening, closing = _week_span(today)
    chosen = [card for card in cards if opening <= card["on"] <= closing]
    counts = {label: 0 for label in _STATUSES}
    meters = 0.0
    for card in chosen:
        counts[card["status"]] = counts.get(card["status"], 0) + 1
        meters += float(card.get("meters") or 0)
    return {
        "start": opening,
        "end": closing,
        "title": _span_title(opening, closing),
        "distance": format_span(meters, unit),
        "runs": len(chosen),
        "counts": counts,
    }


def group_weeks(cards: list[dict], today: date) -> list[dict]:
    """Newest week first. The week that contains today is open."""
    buckets: dict[date, list[dict]] = {}
    for card in cards:
        opening, _closing = _week_span(card["on"])
        buckets.setdefault(opening, []).append(card)
    groups = []
    current, _end = _week_span(today)
    for opening in sorted(buckets, reverse=True):
        rows = sorted(buckets[opening], key=lambda card: (card["date"], card["id"]), reverse=True)
        closing = opening + timedelta(days=6)
        groups.append(
            {
                "start": opening,
                "end": closing,
                "title": _span_title(opening, closing),
                "open": opening == current,
                "cards": rows,
            }
        )
    return groups


def weekly_meters(cards: list[dict], start: date, length: int) -> list[int]:
    """Completed meters for each plan week, including an extra run."""
    if type(start) is not date or isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        return []
    origin = week_sunday(start, 1)
    totals = [0] * length
    found = False
    for card in cards:
        meters = card.get("meters")
        if isinstance(meters, bool) or not isinstance(meters, (int, float)) or meters < 0:
            continue
        day = card.get("on")
        if not isinstance(day, date):
            continue
        index = (day - origin).days // 7
        if index < 0 or index >= length:
            continue
        totals[index] += int(float(meters) + 0.5)
        found = True
    if not found:
        return []
    return totals


def heart_points(cards: list[dict]) -> list[dict]:
    """One point per run that has an average heart rate, oldest first."""
    points = []
    for card in cards:
        bpm = card.get("heart_rate")
        if isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or bpm <= 0:
            continue
        day = card.get("date")
        if not isinstance(day, str) or not day:
            continue
        points.append({"date": day, "bpm": float(bpm)})
    points.sort(key=lambda item: item["date"])
    return points


def summary_html(summary: dict) -> str:
    """The this-week figures. Status counts sit in one row."""
    counts = summary.get("counts") if isinstance(summary.get("counts"), dict) else {}
    tiles = [
        _tile("Distance", summary.get("distance") or "—"),
        _tile("Runs", str(summary.get("runs") or 0)),
        _tile("On track", str(counts.get("On track", 0))),
        _tile("Ahead", str(counts.get("Ahead", 0))),
        _tile("Behind", str(counts.get("Behind", 0))),
        _tile("Extra", str(counts.get("Extra", 0))),
    ]
    title = summary.get("title") or "This week"
    return (
        '<section class="rio-week-summary">'
        '<p class="rio-mark-label">This week</p>'
        f'<p class="rio-run-date">{_esc(title)}</p>'
        f'<div class="rio-summary-row">{"".join(tiles)}</div>'
        "</section>"
    )


def card_html(card: dict) -> str:
    """One run. The template id is in the markup and not shown."""
    status = str(card.get("status") or "Extra")
    kind = _BADGE.get(status, "extra")
    laps = _lap_table(card.get("laps"))
    detail = str(card.get("detail") or "—")
    if laps and " · Actual " in detail:
        detail = detail.split(" · Actual ", 1)[0]
    hidden = ""
    template = str(card.get("template_id") or "").strip()
    if template:
        hidden = f'<span hidden class="rio-template-id">{_esc(template)}</span>'
    return (
        '<article class="rio-run">'
        '<header class="rio-run-head">'
        "<div>"
        f'<h3 class="rio-run-name">{_esc(card.get("name") or "Run")}</h3>'
        f'<p class="rio-run-date">{_esc(card.get("shown_date") or "")}</p>'
        "</div>"
        f'<span class="rio-badge rio-badge-{kind}">{_esc(status)}</span>'
        "</header>"
        f'<p class="rio-run-detail">{_esc(detail)}</p>'
        f"{laps}{hidden}"
        "</article>"
    )


def heart_axis_chart(points: list[dict]) -> str:
    """Average heart rate with a vertical axis and a few date labels.

    Every run is a dot. Date labels are thinned so they stay on one row.
    The height does not grow with the number of runs.
    """
    dots = []
    for point in points or []:
        if not isinstance(point, dict):
            continue
        try:
            day = date.fromisoformat(str(point.get("date")))
        except ValueError:
            continue
        bpm = point.get("bpm")
        if isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or bpm <= 0:
            continue
        dots.append({"date": day, "bpm": float(bpm)})
    if not dots:
        return ""
    dots.sort(key=lambda item: (item["date"], item["bpm"]))
    width = 640
    height = 220
    left = 46
    right = 16
    top = 16
    bottom = 32
    plot_w = width - left - right
    plot_h = height - top - bottom
    low = min(item["bpm"] for item in dots)
    high = max(item["bpm"] for item in dots)
    if high == low:
        floor = low - 8
        peak = high + 8
    else:
        pad = max(4.0, (high - low) * 0.12)
        floor = low - pad
        peak = high + pad
    first = dots[0]["date"]
    last = dots[-1]["date"]
    span = (last - first).days or 1
    coords = []
    for item in dots:
        if len(dots) == 1:
            x = left + plot_w / 2
        else:
            x = left + plot_w * (item["date"] - first).days / span
        y = top + plot_h * (1 - (item["bpm"] - floor) / (peak - floor))
        coords.append((x, y, item))
    ticks = [(floor, top + plot_h), ((floor + peak) / 2, top + plot_h / 2), (peak, top)]
    parts = [
        '<div class="rio-heart rio-heart-axis">',
        '<p class="rio-mark-label">Heart rate · bpm</p>',
        (
            f'<svg class="rio-heart-axis-line" viewBox="0 0 {width} {height}" '
            'role="img" aria-label="Average heart rate" '
            'xmlns="http://www.w3.org/2000/svg">'
        ),
        "<title>Average heart rate</title>",
        (
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" '
            'stroke="#6B6B6B" stroke-width="1.25" />'
        ),
        (
            f'<line x1="{left}" y1="{top + plot_h}" x2="{width - right}" y2="{top + plot_h}" '
            'stroke="#DADADA" stroke-width="1" />'
        ),
    ]
    for value, y in ticks:
        label = str(int(round(value)))
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" '
            'stroke="#E4E4E4" stroke-width="1" />'
        )
        parts.append(
            f'<text x="{left - 8}" y="{y:.1f}" text-anchor="end" dominant-baseline="middle" '
            'fill="#6B6B6B" font-size="11" font-family="Inter, Helvetica, Arial, sans-serif">'
            f"{label}</text>"
        )
    for x, y, item in coords:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="#E25A32">'
            f"<title>{_esc(item['date'].isoformat())} · {int(round(item['bpm']))} bpm</title>"
            "</circle>"
        )
    for x, item in _thinned_dates(coords, left, width - right):
        parts.append(
            f'<text x="{x:.1f}" y="{height - 10}" text-anchor="middle" fill="#6B6B6B" '
            'font-size="11" font-family="Inter, Helvetica, Arial, sans-serif">'
            f"{_esc(_short_day(item['date']))}</text>"
        )
    parts.append("</svg></div>")
    return "".join(parts)


def activity_style() -> str:
    """Cards, badges, and the summary. The page background stays paper."""
    return """
<style>
.rio-week-summary, .rio-run {
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 18px;
  box-shadow: 0 12px 32px rgba(14, 14, 14, 0.05);
}
.rio-week-summary { padding: 0.9rem 1rem 1rem; margin: 0.4rem 0 0.9rem; }
.rio-summary-row {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0.55rem;
  margin-top: 0.7rem;
}
.rio-summary-tile {
  background: #F2F2F2;
  border-radius: 12px;
  padding: 0.45rem 0.5rem 0.55rem;
}
.rio-summary-kicker {
  margin: 0;
  color: #6E6A64;
  font-family: Inter, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 0.68rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.rio-summary-value {
  margin: 0.15rem 0 0;
  color: #121110;
  font-family: Manrope, Inter, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
}
.rio-run {
  padding: 0.85rem 1rem 0.9rem;
  margin: 0 0 0.7rem;
  transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
}
.rio-run:hover { transform: translateY(-1px); }
.rio-run-head { display: flex; justify-content: space-between; gap: 0.75rem; align-items: flex-start; }
.rio-run-name {
  margin: 0;
  color: #121110;
  font-family: Manrope, Inter, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
}
.rio-run-date, .rio-run-detail {
  margin: 0.2rem 0 0;
  color: #3C3A36;
  font-family: Inter, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 0.92rem;
}
.rio-badge {
  display: inline-block;
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  font-family: Inter, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}
.rio-badge-on-track { background: #E25A32; color: #FFFFFF; }
.rio-badge-ahead { background: #1F7A4D; color: #FFFFFF; }
.rio-badge-behind { background: #8C3A2F; color: #FFFFFF; }
.rio-badge-extra { background: #E4E4E4; color: #3A3A3A; }
.rio-laps {
  width: 100%;
  border-collapse: collapse;
  margin-top: 0.65rem;
  font-family: Inter, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 0.82rem;
  font-variant-numeric: tabular-nums;
}
.rio-laps th {
  text-align: left;
  color: #6E6A64;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.rio-laps td, .rio-laps th { padding: 0.28rem 0.35rem; border-bottom: 1px solid #E6E6E6; }
@media (max-width: 720px) {
  .rio-summary-row { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
</style>
"""


def visible_text(markup: str) -> str:
    """The words a person sees. Hidden template ids are left out."""
    text = re.sub(r"<span hidden\b[^>]*>.*?</span>", "", markup, flags=re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _recipe_name(recipe: dict, reason_codes: object) -> str:
    distances = recipe["distances"]
    if recipe["continuous"]:
        meters = int(distances[0])
        kind = "Long" if _is_long(recipe["template_id"], reason_codes) else "Easy"
        return f"{kind} {_distance_name(meters)}"
    if len(set(distances)) == 1:
        return f"{recipe['reps']} × {distances[0]} m"
    parts = "–".join(str(item) for item in distances)
    return f"{parts} m"


def _is_long(template_id: str, reason_codes: object) -> bool:
    if template_id in LONG_IDS:
        return True
    return isinstance(reason_codes, list) and "weekly_aerobic_long_run" in reason_codes


def _distance_name(meters: int) -> str:
    if meters >= 1000:
        km = meters / 1000.0
        if abs(km - round(km)) < 1e-9:
            return f"{int(round(km))} km"
        return f"{km:.1f} km"
    return f"{meters} m"


def _extra_name(name: str, run: dict) -> str:
    if name and name != "Extra":
        return name
    meters = _meters(run)
    if meters >= 1000:
        return f"Extra {_distance_name(int(meters + 0.5))}"
    if meters > 0:
        return f"Extra {int(meters + 0.5)} m"
    return "Extra"


def _deduped(runs: object, activities: object) -> list[dict]:
    found: list[dict] = []
    seen: set[str] = set()
    for run in runs or []:
        if not isinstance(run, dict):
            continue
        ident = str(run.get("id") or "")
        if ident and ident in seen:
            continue
        if ident:
            seen.add(ident)
        found.append(run)
    for activity in activities or []:
        if not isinstance(activity, dict):
            continue
        ident = str(activity.get("id") or "")
        if ident and ident in seen:
            continue
        if ident:
            seen.add(ident)
        found.append(_from_activity(activity))
    return found


def _from_activity(activity: dict) -> dict:
    reps = activity.get("reps") if isinstance(activity.get("reps"), list) else []
    laps = []
    for item in reps:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or item <= 0:
            continue
        laps.append({"moving_seconds": item})
    distance = activity.get("distance")
    if distance is None:
        distance = activity.get("work_m")
    return {
        "id": activity.get("id"),
        "name": activity.get("name") or "Run",
        "date": activity.get("date"),
        "distance_m": distance,
        "moving_seconds": activity.get("moving_seconds"),
        "elapsed_seconds": activity.get("elapsed_seconds"),
        "pace_s_per_km": activity.get("pace_s_per_km"),
        "average_hr": activity.get("heart_rate"),
        "laps": laps,
        "template_id": activity.get("template_id") or "",
        "matched": activity.get("matched") is True,
    }


def _sessions_by_date(sessions: object) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        day = session.get("date")
        if isinstance(day, str) and day and day not in found:
            found[day] = session
    return found


def _meters(run: dict) -> float:
    for key in ("distance_m", "distance", "work_m"):
        value = run.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if value > 0:
            return float(value)
    laps = run.get("laps")
    if isinstance(laps, list):
        total = 0.0
        for lap in laps:
            if isinstance(lap, dict) and isinstance(lap.get("distance_m"), (int, float)):
                total += float(lap["distance_m"])
        if total > 0:
            return total
    return 0.0


def _heart(run: dict) -> float | None:
    for key in ("average_hr", "heart_rate"):
        value = run.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if value > 0:
            return float(value)
    return None


def _week_span(day: date) -> tuple[date, date]:
    opening = day - timedelta(days=(day.weekday() + 1) % 7)
    return opening, opening + timedelta(days=6)


def _span_title(opening: date, closing: date) -> str:
    return f"{_MONTHS[opening.month - 1]} {opening.day} – {_MONTHS[closing.month - 1]} {closing.day}"


def _short_day(day: date) -> str:
    return f"{_MONTHS[day.month - 1]} {day.day}"


def _thinned_dates(coords: list[tuple], left: float, right: float) -> list[tuple]:
    """At most six dates, far enough apart to sit on one row."""
    if not coords:
        return []
    picks = [0]
    if len(coords) > 1:
        picks.append(len(coords) - 1)
    room = max(1, int((right - left) / 72))
    room = min(6, max(2, room))
    if len(coords) > 2 and room > 2:
        step = (len(coords) - 1) / (room - 1)
        for index in range(1, room - 1):
            picks.append(int(round(index * step)))
    ordered = sorted(set(picks))
    chosen = []
    last_x = None
    for index in ordered:
        x = coords[index][0]
        if last_x is not None and x - last_x < 64 and index != ordered[-1]:
            continue
        chosen.append((x, coords[index][2]))
        last_x = x
    if chosen and ordered and chosen[-1][1] is not coords[-1][2]:
        end_x = coords[-1][0]
        if not chosen or end_x - chosen[-1][0] >= 48:
            chosen.append((end_x, coords[-1][2]))
        else:
            chosen[-1] = (end_x, coords[-1][2])
    return chosen[:6]


def _tile(label: str, value: object) -> str:
    return (
        '<div class="rio-summary-tile">'
        f'<p class="rio-summary-kicker">{_esc(label)}</p>'
        f'<p class="rio-summary-value">{_esc(value)}</p>'
        "</div>"
    )


def _lap_table(laps: object) -> str:
    if not isinstance(laps, list) or not laps:
        return ""
    body = []
    for row in laps:
        if not isinstance(row, dict):
            continue
        body.append(
            "<tr>"
            f"<td>{_esc(row.get('rep'))}</td>"
            f"<td>{_esc(row.get('target') or '—')}</td>"
            f"<td>{_esc(row.get('actual') or '—')}</td>"
            f"<td>{_esc(row.get('rest') or '—')}</td>"
            "</tr>"
        )
    if not body:
        return ""
    return (
        '<table class="rio-laps"><thead><tr>'
        "<th>Rep</th><th>Target</th><th>Actual</th><th>Rest</th>"
        f"</tr></thead><tbody>{''.join(body)}</tbody></table>"
    )


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)
