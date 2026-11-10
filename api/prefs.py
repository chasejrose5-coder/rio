# prefs.py — time zone, pace, no-watch, and easy pace from the account.

"""The same helpers the settings page uses. Nothing here is passed to adapt.

units follows pace the way the shell does: per kilometer shows kilometers,
and per mile shows miles. Today is local_today in the saved zone.
"""

from __future__ import annotations

from datetime import date

from api.identity import Principal
from engines.pace import canonical_easy_pace, easy_pace_phrase
from ui.accounts import read_local
from ui.cloud_store import stored_easy_pair
from ui.settings import chosen_timezone, local_today, normalize


def _easy_from(pace: object, unit: object) -> tuple[str, str] | None:
    pair = stored_easy_pair(pace, unit)
    if pair is not None:
        return pair
    text = canonical_easy_pace(pace)
    if text and unit in ("mi", "km"):
        return text, unit
    return None


def account_prefs(principal: Principal, directory) -> dict:
    """Saved settings, the zone, today's date, and the easy pace."""
    raw: dict = {}
    zone = None
    easy = None
    profile: dict = {}
    if principal.kind == "hosted" and directory is not None and isinstance(principal.token, str):
        from services.season_store import load_hosted_season

        bundle = load_hosted_season(directory, principal.token)
        found = bundle.get("profile") if isinstance(bundle, dict) else None
        profile = found if isinstance(found, dict) else {}
        zone = profile.get("timezone")
        pace = profile.get("pace_units")
        if pace in ("mi", "km"):
            raw["pace_units"] = pace
        if "no_watch" in profile:
            raw["no_watch"] = profile.get("no_watch") is True
        for key in ("date_format", "start_date", "confirm_adapt", "show_ids", "compact"):
            if key in profile:
                raw[key] = profile[key]
        easy = _easy_from(profile.get("easy_pace"), profile.get("easy_pace_unit"))
        principal.display_name = str(profile.get("display_name") or principal.display_name)
        principal.role = str(profile.get("role") or principal.role or "athlete")
        if profile.get("id"):
            principal.user_id = str(profile.get("id"))
        if profile.get("email"):
            principal.email = str(profile.get("email"))
    elif principal.accounts_path is not None:
        local = read_local(principal.accounts_path, principal.email) or {}
        settings = local.get("settings")
        if isinstance(settings, dict):
            raw = dict(settings)
        zone = local.get("timezone")
        easy = _easy_from(local.get("easy_pace"), local.get("easy_pace_unit"))
        if isinstance(local.get("name"), str) and local.get("name"):
            principal.display_name = str(local.get("name"))
    intro_seen = None
    strava_prompt_seen = False
    preferred = ""
    if principal.kind == "hosted":
        if "intro_seen" in profile:
            intro_seen = profile.get("intro_seen") is True
        if "strava_prompt_seen" in profile:
            strava_prompt_seen = profile.get("strava_prompt_seen") is True
        if isinstance(profile.get("preferred"), str):
            preferred = profile["preferred"]
    else:
        if isinstance(raw.get("intro_seen"), bool):
            intro_seen = raw["intro_seen"]
        if "strava_prompt_seen" in raw:
            strava_prompt_seen = raw.get("strava_prompt_seen") is True
        local_preferred = raw.get("preferred") if principal.accounts_path is None else None
        if principal.accounts_path is not None:
            local_row = read_local(principal.accounts_path, principal.email) or {}
            if isinstance(local_row.get("preferred"), str):
                preferred = local_row["preferred"]
        elif isinstance(local_preferred, str):
            preferred = local_preferred
    prefs = normalize(raw)
    # The shell shows distance in the pace unit the athlete picked.
    prefs["units"] = "km" if prefs.get("pace_units") == "km" else "miles"
    # Today follows a listed zone. A saved id outside that list still comes
    # back so Settings can show it, and today falls back to the suggestion.
    timezone = chosen_timezone(zone, None)
    shown_zone = zone.strip() if isinstance(zone, str) and zone.strip() else timezone
    today = local_today(timezone)
    phrase = ""
    easy_pace = ""
    easy_unit = prefs["pace_units"] if prefs.get("pace_units") in ("mi", "km") else "mi"
    if easy is not None:
        easy_pace, easy_unit = easy
        phrase = easy_pace_phrase(easy_pace, easy_unit)
    return {
        "prefs": prefs,
        "timezone": shown_zone,
        "today": today,
        "easy_pace": easy_pace,
        "easy_pace_unit": easy_unit,
        "easy_pace_phrase": phrase,
        "profile": profile,
        "intro_seen": intro_seen,
        "strava_prompt_seen": strava_prompt_seen,
        "preferred": preferred,
    }


def prefs_payload(resolved: dict) -> dict:
    prefs = resolved["prefs"]
    today = resolved["today"]
    return {
        "timezone": resolved["timezone"],
        "pace_units": prefs["pace_units"],
        "no_watch": prefs["no_watch"] is True,
        "easy_pace": resolved["easy_pace"],
        "easy_pace_unit": resolved["easy_pace_unit"],
        "easy_pace_phrase": resolved["easy_pace_phrase"],
        "units": prefs["units"],
        "date_format": prefs["date_format"],
        "start_date": prefs["start_date"],
        "confirm_adapt": prefs["confirm_adapt"] is True,
        "today": today.isoformat() if isinstance(today, date) else "",
        "logging": "done" if prefs.get("no_watch") is True else "times",
        "intro_seen": resolved.get("intro_seen"),
        "strava_prompt_seen": resolved.get("strava_prompt_seen") is True,
        "preferred": resolved.get("preferred") or "",
        "show_ids": prefs.get("show_ids") is True,
        "compact": prefs.get("compact") is True,
    }


def athlete_payload(principal: Principal, resolved: dict) -> dict:
    """The signed-in athlete. The same shape as GET /auth/me."""
    from ui.access import viewer_is_admin

    prefs = prefs_payload(resolved)
    today = prefs.pop("today")
    role = principal.role or "athlete"
    if viewer_is_admin(principal.email):
        role = "admin"
    return {
        "id": principal.user_id,
        "email": principal.email,
        "display_name": principal.display_name,
        "role": role,
        "kind": principal.kind,
        "today": today,
        "prefs": prefs,
    }
