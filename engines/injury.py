# injury.py — easy, medium, and hard for a rebuilding area.

"""A selected area starts at the stored level. Every 14 days it moves one
level toward hard. Stepping back stores the lower level and starts the
14 days again.

No model. The dates are calendar days the caller already resolved.
"""

from __future__ import annotations

from datetime import date

LEVELS = ("easy", "medium", "hard")

# Selectable areas. Exercise text stays in the web app.
AREAS = frozenset(
    {
        "plantar-fascia",
        "ankle-sprain",
        "peroneal",
        "achilles",
        "soleus",
        "shins",
        "bone-stress",
        "patellar",
        "pfps",
        "it-band",
        "glute-med",
        "hip-flexors",
        "adductors",
        "high-hamstring",
        "hamstring-strain",
        "low-back",
    }
)

# Done marks. General prevention is not an area.
BLOCKS = AREAS | {"general"}


def level_index(stored: object, anchor: object, today: object) -> int:
    """0 easy, 1 medium, 2 hard. A future anchor stays at the stored level."""
    if isinstance(stored, bool) or not isinstance(stored, int) or stored not in (0, 1, 2):
        raise ValueError("level is not easy, medium, or hard")
    if not isinstance(anchor, date) or not isinstance(today, date):
        raise ValueError("level dates are calendar days")
    if anchor > today:
        return stored
    periods = (today - anchor).days // 14
    return min(2, stored + periods)


def level_name(stored: object, anchor: object, today: object) -> str:
    return LEVELS[level_index(stored, anchor, today)]
