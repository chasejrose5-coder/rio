# plan_strava.py — whether to ask for Strava right after a plan is built.

"""The decision only. The page draws the card. No network and no model."""

from __future__ import annotations

PROMPT_SEEN = "strava_prompt_seen"


def should_offer_strava(*, just_generated: bool, connected: bool, dismissed: bool) -> bool:
    """True only after a successful generate, while Strava is still unconnected."""
    return bool(just_generated) and not connected and not dismissed


def prompt_seen_value(user: object) -> bool | None:
    """True when this athlete already dismissed the card or connected. None if unset."""
    from ui.cloud_store import _metadata_dict

    meta = _metadata_dict(user)
    if meta is None or PROMPT_SEEN not in meta:
        return None
    return meta.get(PROMPT_SEEN) is True
