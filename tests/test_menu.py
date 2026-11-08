# test_menu.py — the frozen 800 m menu after the 42-row expansion.

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.pace import workout_recipe
from engines.prescribe import PARAMETER_KEYS, load_menu
from ui.dashboard import session_facts

MENU_DIR = ROOT / "rio" / "templates" / "800m"

FAMILIES = {
    "aer": "aerobic",
    "thr": "threshold",
    "ap": "aerobic_power",
    "se": "speed_endurance",
    "an": "anaerobic_capacity",
    "spd": "speed",
    "mv": "max_velocity",
    "rr": "race_readiness",
}

NEW_IDS = {
    "aer_4500_r0_x1",
    "aer_5500_r0_x1",
    "aer_6000_r0_x1",
    "aer_6500_r0_x1",
    "aer_7000_r0_x1",
    "aer_7500_r0_x1",
    "aer_8500_r0_x1",
    "aer_9000_r0_x1",
    "aer_9500_r0_x1",
    "aer_10500_r0_x1",
    "aer_11000_r0_x1",
    "aer_11500_r0_x1",
    "aer_12500_r0_x1",
    "aer_13000_r0_x1",
    "aer_13500_r0_x1",
    "aer_14000_r0_x1",
    "aer_14500_r0_x1",
    "aer_15000_r0_x1",
    "thr_1600_r90_x4",
    "thr_2400_r120_x2",
    "thr_5000_r0_x1",
    "ap_600_r75_x8",
    "ap_800_r90_x4",
    "ap_800_r90_x6",
    "se_500_r120_x5",
    "an_400_r45_x4",
    "an_500_r150_x3",
    "an_800_r240_x2",
    "an_dn_800to400_r180_x3",
    "spd_150_r150_x6",
    "spd_150_r150_x10",
    "spd_200_r180_x8",
    "spd_250_r180_x6",
    "spd_300_r180_x4",
    "mv_40_r90_x12",
    "mv_60_r120_x8",
    "mv_80_r180_x6",
    "mv_100_r180_x8",
    "mv_120_r180_x4",
    "rr_150_r180_x4",
    "rr_300_r180_x2",
    "rr_up_150to400_r180_x4",
}

# Close calls that stay off the menu on purpose.
EXCLUDED_IDS = {
    "thr_800_r60_x6",
    "thr_1000_r60_x6",
    "ap_1000_r120_x5",
    "ap_1200_r150_x3",
    "se_200_r75_x10",
    "se_250_r75_x8",
    "se_300_r75_x6",
    "se_400_r90_x5",
    "an_300_r120_x6",
    "rr_400_r0_x1",
    "rr_600_r0_x1",
}

_ID = re.compile(
    r"^(aer|thr|ap|se|an|spd|mv|rr)_(?:(?:up|py|dn)_)?\d+(?:to\d+)?_r\d+_x\d+$"
)
_CLOCK = re.compile(r"\d+:\d{2}")


def _keys(path: Path) -> list[str]:
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            raise AssertionError(f"{path.name} has a line that is not a field")
        found.append(line.split(":", 1)[0].strip())
    return found


def test_menu_has_the_expanded_eighty_two() -> None:
    """load_menu reads every recipe. The expansion is these 42 ids, and no close calls."""
    menu = load_menu()
    files = sorted(MENU_DIR.glob("*.yml"))
    ids = [template["id"] for template in menu]
    if len(menu) != 82 or len(files) != 82 or len(ids) != len(set(ids)):
        raise AssertionError(f"{len(menu)} templates from {len(files)} files")
    if ids != sorted(ids):
        raise AssertionError("menu order is not id order")
    if set(NEW_IDS) - set(ids):
        raise AssertionError(f"missing {sorted(set(NEW_IDS) - set(ids))}")
    if len(NEW_IDS) != 42:
        raise AssertionError(f"the new list is {len(NEW_IDS)}, not 42")
    present = EXCLUDED_IDS & set(ids)
    if present:
        raise AssertionError(f"excluded ids were added: {sorted(present)}")
    for template_id in EXCLUDED_IDS:
        if (MENU_DIR / f"{template_id}.yml").exists():
            raise AssertionError(f"{template_id}.yml exists")
    stems = {path.stem for path in files}
    if stems != set(ids):
        raise AssertionError("a file name does not match its id")


def test_new_recipes_match_the_existing_schema() -> None:
    """Same fields, same family words, and a pace recipe for every new id."""
    menu = {template["id"]: template for template in load_menu()}
    allowed = set(FAMILIES.values())
    for path in sorted(MENU_DIR.glob("*.yml")):
        if _keys(path) != list(PARAMETER_KEYS):
            raise AssertionError(f"{path.name} fields are {_keys(path)}")
        template = menu[path.stem]
        if template["id"] != path.stem or _ID.fullmatch(template["id"]) is None:
            raise AssertionError(f"{path.name} id does not match the file pattern")
        prefix = template["id"].split("_", 1)[0]
        if template["family"] != FAMILIES[prefix]:
            raise AssertionError(f"{template['id']} family is {template['family']}")
        if template["primary_stimulus"] != template["family"]:
            raise AssertionError(f"{template['id']} primary stimulus changed")
        secondary = template["secondary_stimulus"]
        if secondary and secondary not in allowed:
            raise AssertionError(f"{template['id']} secondary is {secondary}")
        for key in ("name", "default_structure", "constraints"):
            if not str(template[key]).strip():
                raise AssertionError(f"{template['id']} is missing {key}")
    recovery = [
        template["id"]
        for template in menu.values()
        if "day-after-hard" in template["constraints"]
        or "day-after-race" in template["constraints"]
    ]
    if recovery != ["aer_4000_r0_x1"]:
        raise AssertionError(f"recovery rows are {recovery}")
    defaults = [
        template["id"]
        for template in menu.values()
        if "the default " in template["default_structure"].lower()
    ]
    references = [
        template["id"]
        for template in menu.values()
        if "the reference " in template["default_structure"].lower()
    ]
    if defaults != ["aer_8000_r0_x1"] or references != ["se_400_r90_x6"]:
        raise AssertionError((defaults, references))
    for template_id in NEW_IDS:
        text = (MENU_DIR / f"{template_id}.yml").read_text(encoding="utf-8")
        if _CLOCK.search(text):
            raise AssertionError(f"{template_id} invented a clock time")
        recipe = workout_recipe(template_id)
        if recipe is None or recipe["template_id"] != template_id:
            raise AssertionError(f"{template_id} did not parse as a workout")
        if not recipe["distances"] or recipe["reps"] < 1:
            raise AssertionError(f"{template_id} has no distances")
    descending = workout_recipe("an_dn_800to400_r180_x3")
    if descending is None or descending["distances"] != [800, 600, 400]:
        raise AssertionError(descending)
    if descending["rest_seconds"] != 180 or descending["reps"] != 3:
        raise AssertionError(descending)
    facts = session_facts("an_dn_800to400_r180_x3", "Hard, not a sprint on the 400.")
    if facts["distance"] != "800–400 m" or facts["reps"] != "3" or facts["rest"] != "3 min":
        raise AssertionError(facts)
    if facts["pace"] != "Hard":
        raise AssertionError(facts)
    easy = menu["aer_5000_r0_x1"]
    threshold = menu["thr_5000_r0_x1"]
    if easy["family"] == threshold["family"] or "30 min" not in easy["name"]:
        raise AssertionError("the easy 5 km and the threshold 5 km were mixed")
    if "comfortably hard" not in threshold["name"] or "easy 30 min" not in threshold["default_structure"]:
        raise AssertionError("the continuous threshold reads like the easy 5 km")


if __name__ == "__main__":
    test_menu_has_the_expanded_eighty_two()
    test_new_recipes_match_the_existing_schema()
    print("menu ok")
