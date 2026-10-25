# library.py — the frozen menu as a searchable list. Display only.

"""Every template load_menu already returns. Nothing is added to the menu.

A row keeps the recipe name, the template id, and the capacity. The phase
filter uses the phase lists the season already has, plus the easy day and
the long runs those phases place. Search looks at the name, the id, and
the capacity.

No model. No spend. No scores.
"""

from __future__ import annotations

from engines.season import _LONG_RUNS, _PHASE_MENU, _RECOVERY_ID

# Plain words for capacities already stored on the menu.
_CAPACITY = {
    "aerobic": "Aerobic",
    "aerobic_power": "Aerobic power",
    "anaerobic_capacity": "Anaerobic",
    "max_velocity": "Max velocity",
    "race_readiness": "Race readiness",
    "speed": "Speed",
    "speed_endurance": "Speed endurance",
    "threshold": "Threshold",
}


def capacity_label(family: object, stimulus: object = None) -> str:
    """The capacity shown on a row. A different stimulus is kept beside it."""
    primary = _plain(family)
    other = _plain(stimulus)
    if not primary:
        return other or "—"
    if not other or other == primary:
        return primary
    return f"{primary} · {other}"


def phases_for(template_id: object) -> list[int]:
    """Phases that already list this id, in order.

    The easy day is placed in every phase. The long runs are placed in
    phases 1–7. Any other id is only the phases whose menu names it.
    """
    template = str(template_id or "").strip()
    if not template:
        return []
    found: list[int] = []
    for phase in range(1, 9):
        ids = _PHASE_MENU.get(phase, ())
        if template in ids and phase not in found:
            found.append(phase)
    if template == _RECOVERY_ID:
        for phase in range(1, 9):
            if phase not in found:
                found.append(phase)
    if template in _LONG_RUNS:
        for phase in range(1, 8):
            if phase not in found:
                found.append(phase)
    return found


def library_rows(menu: list) -> list[dict]:
    """One row per frozen template, in menu order."""
    rows: list[dict] = []
    for item in menu or []:
        if not isinstance(item, dict):
            continue
        template_id = str(item.get("id") or "").strip()
        if not template_id:
            continue
        name = str(item.get("name") or "").strip() or template_id
        family = str(item.get("family") or "").strip()
        stimulus = str(item.get("primary_stimulus") or "").strip()
        rows.append(
            {
                "id": template_id,
                "description": name,
                "capacity": capacity_label(family, stimulus),
                "family": family,
                "phases": phases_for(template_id),
            }
        )
    return rows


def filter_workouts(
    rows: list,
    *,
    query: str = "",
    family: str = "",
    phase: int | None = None,
) -> list[dict]:
    """Keep rows whose name, id, or capacity contains the query.

    An empty family and an empty phase leave that side open. A phase
    outside 1–8 matches nothing.
    """
    needle = " ".join(str(query or "").casefold().split())
    wanted = str(family or "").strip()
    if isinstance(phase, bool) or (phase is not None and not isinstance(phase, int)):
        phase = -1
    kept: list[dict] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        if wanted and str(row.get("family") or "") != wanted:
            continue
        if phase is not None:
            phases = row.get("phases") or []
            if phase not in phases:
                continue
        if needle and needle not in _haystack(row):
            continue
        kept.append(row)
    return kept


def _plain(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    known = _CAPACITY.get(text)
    if known:
        return known
    return text.replace("_", " ")


def _haystack(row: dict) -> str:
    parts = (
        str(row.get("description") or ""),
        str(row.get("id") or ""),
        str(row.get("capacity") or ""),
    )
    return " ".join(parts).casefold()
