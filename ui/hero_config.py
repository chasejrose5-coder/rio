# hero_config.py — startup photo order, credits, and which frames are on.

"""The rotating startup photos live in a small JSON file under ui/assets.

The file stores order, a credit line, and whether a frame is shown.
It is not an account record. A page that is not the startup page does not
read these photos.
"""

from __future__ import annotations

import json
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
CONFIG_NAME = "hero_rotation.json"

# The only frames this file may name. The credit can change. The file cannot.
_DEFAULTS = (
    {
        "id": "run-4-ffwpu",
        "file": "hero_run.jpg",
        "credit": "Photo by RUN 4 FFWPU on Pexels",
        "source": "https://www.pexels.com/photo/athlete-winning-competition-11329597/",
    },
    {
        "id": "writchid-snipes",
        "file": "hero_blocks.jpg",
        "credit": "Photo by Writchid Snipes on Pexels",
        "source": "https://www.pexels.com/photo/athletics-starting-blocks-on-blue-track-37695154/",
    },
    {
        "id": "ansey-photography",
        "file": "hero_race.jpg",
        "credit": "Photo by Ansey Photography on Pexels",
        "source": "https://www.pexels.com/photo/athletes-competing-in-outdoor-track-race-30144519/",
    },
)
_BY_ID = {row["id"]: row for row in _DEFAULTS}
_CREDIT_LIMIT = 160


def config_path(path: Path | None = None) -> Path:
    """The JSON file. A test can point this at another file."""
    if path is None:
        return ASSETS / CONFIG_NAME
    return Path(path)


def load_rotation(path: Path | None = None) -> list[dict]:
    """Every known frame, in stored order. Missing frames use the defaults.

    An unknown id is ignored. A broken file falls back to the defaults.
    """
    stored = _read(config_path(path))
    ordered: list[dict] = []
    seen: set[str] = set()
    for item in stored:
        if not isinstance(item, dict):
            continue
        photo_id = item.get("id")
        if not isinstance(photo_id, str) or photo_id not in _BY_ID or photo_id in seen:
            continue
        ordered.append(_merge(_BY_ID[photo_id], item))
        seen.add(photo_id)
    for row in _DEFAULTS:
        if row["id"] not in seen:
            ordered.append(_merge(row, {"enabled": True}))
    return ordered


def enabled_frames(path: Path | None = None) -> list[dict]:
    """Frames that should crossfade, in order. A missing file is left out."""
    frames = []
    folder = config_path(path).parent if path is not None else ASSETS
    for row in load_rotation(path):
        if row["enabled"] is not True:
            continue
        file = folder / row["file"]
        if not file.is_file():
            continue
        frames.append(
            {
                "id": row["id"],
                "file": str(file),
                "credit": row["credit"],
            }
        )
    return frames


def save_rotation(rows: object, path: Path | None = None) -> list[dict]:
    """Write order, credits, and which frames are on.

    The id list must be the known frames, each once. The picture file stays
    the one shipped with that id. Returns the stored rows.
    """
    cleaned = _clean_rows(rows)
    payload = {"photos": cleaned}
    file = config_path(path)
    text = json.dumps(payload, indent=2) + "\n"
    temporary = file.with_name(file.name + ".tmp")
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(file)
    return load_rotation(file)


def _clean_rows(rows: object) -> list[dict]:
    if not isinstance(rows, (list, tuple)):
        raise ValueError("photos are not a list")
    if len(rows) != len(_DEFAULTS):
        raise ValueError("photos do not match the startup set")
    cleaned = []
    seen: set[str] = set()
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("photos do not match the startup set")
        photo_id = item.get("id")
        if not isinstance(photo_id, str) or photo_id not in _BY_ID or photo_id in seen:
            raise ValueError("photos do not match the startup set")
        seen.add(photo_id)
        base = _BY_ID[photo_id]
        enabled = item.get("enabled")
        if not isinstance(enabled, bool):
            raise ValueError("show is not on or off")
        cleaned.append(
            {
                "id": photo_id,
                "file": base["file"],
                "credit": clean_credit(item.get("credit")),
                "source": base["source"],
                "enabled": enabled,
            }
        )
    if seen != set(_BY_ID):
        raise ValueError("photos do not match the startup set")
    return cleaned


def clean_credit(value: object) -> str:
    """One credit line. Blank and huge lines are refused."""
    if not isinstance(value, str):
        raise ValueError("credit is empty")
    text = " ".join(value.split())
    if not text or len(text) > _CREDIT_LIMIT:
        raise ValueError("credit is empty")
    return text


def _merge(base: dict, item: dict) -> dict:
    enabled = item.get("enabled")
    if not isinstance(enabled, bool):
        enabled = True
    credit = item.get("credit")
    if not isinstance(credit, str) or not credit.strip():
        credit = base["credit"]
    else:
        credit = " ".join(credit.split())
        if len(credit) > _CREDIT_LIMIT:
            credit = base["credit"]
    return {
        "id": base["id"],
        "file": base["file"],
        "credit": credit,
        "source": base["source"],
        "enabled": enabled,
    }


def _read(path: Path) -> list:
    if not path.is_file():
        return []
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, dict):
        return []
    photos = parsed.get("photos")
    if not isinstance(photos, list):
        return []
    return photos
