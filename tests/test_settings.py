# test_settings.py — display preferences stay off the plan.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.settings import (
    DEFAULTS,
    display_distance,
    display_km,
    display_meters,
    distance_heading,
    distance_number,
    format_date,
    normalize,
)


def _no_score(row: dict) -> None:
    if "probability" in row or "readiness" in row or "readiness_score" in row:
        raise AssertionError("a score was added")
    text = str(row).lower()
    if "probability" in text or "readiness_score" in text:
        raise AssertionError("a score was named")


def test_defaults_and_rejected_values() -> None:
    """Blank input is the default set. A bad value does not stick."""
    clean = normalize(None)
    _no_score(clean)
    if clean != DEFAULTS:
        raise AssertionError(f"defaults were {clean}")
    mixed = normalize(
        {
            "units": "yards",
            "show_ids": "yes",
            "compact": 1,
            "date_format": "long",
            "confirm_adapt": False,
            "notifications": True,
            "probability": 0.2,
        }
    )
    _no_score(mixed)
    if mixed["units"] != "km" or mixed["date_format"] != "iso":
        raise AssertionError("a bad choice was kept")
    if mixed["show_ids"] or mixed["compact"] or mixed["confirm_adapt"]:
        raise AssertionError("a non-boolean became on")
    if not mixed["notifications"]:
        raise AssertionError("notifications did not stay on")
    if "probability" in mixed:
        raise AssertionError("a score was stored")
    source = Path(ROOT / "ui" / "settings.py").read_text(encoding="utf-8")
    if "explain(" in source or "engines" in source:
        raise AssertionError("settings reached an engine")


def test_dates_and_distances_are_display_only() -> None:
    """ISO and kilometers stay available. Miles and the short day are display text."""
    day = date(2026, 10, 24)
    if format_date(day, "iso") != "2026-10-24":
        raise AssertionError("ISO changed")
    if format_date("2026-10-24", "short") != "Oct 24, 2026":
        raise AssertionError(f"short day was {format_date('2026-10-24', 'short')}")
    if format_date("not-a-date", "short") != "not-a-date":
        raise AssertionError("an unreadable day was rewritten")
    original = "8 km easy, Zone 2"
    if display_km(original, "km") != original:
        raise AssertionError("kilometers were rewritten")
    if display_km("8 km easy", "miles") != "5.0 mi easy":
        raise AssertionError(display_km("8 km easy", "miles"))
    if display_km("5 km easy and 12 km", "miles") != "3.1 mi easy and 7.5 mi":
        raise AssertionError(display_km("5 km easy and 12 km", "miles"))
    volume = "31,400 m · 31,600 m the week before"
    if display_meters(volume, "km") != volume:
        raise AssertionError("meter totals changed under kilometers")
    shown = display_meters(volume, "miles")
    if shown != "19.5 mi · 19.6 mi the week before":
        raise AssertionError(shown)
    if display_meters("8 km easy", "miles") != "8 km easy":
        raise AssertionError("a kilometer phrase was treated as meters")
    if display_meters("10 × 60 m fast", "miles") != "10 × 0.04 mi fast":
        raise AssertionError(display_meters("10 × 60 m fast", "miles"))
    ladder = display_meters("pyramid 200-300-400 m", "miles")
    if ladder != "pyramid 0.1-0.2-0.2 mi":
        raise AssertionError(ladder)
    if display_meters("2.5 min rest", "miles") != "2.5 min rest":
        raise AssertionError("a minute was treated as meters")


def test_distance_labels_follow_the_unit() -> None:
    """Miles says mi. Kilometers uses km or m. Neither label says mileage."""
    prose = "8 km easy, 6 × 400 m, planned 8000 m"
    miles = display_distance(prose, "miles")
    if miles != "5.0 mi easy, 6 × 0.2 mi, planned 5.0 mi":
        raise AssertionError(miles)
    if "mileage" in miles or "meter" in miles:
        raise AssertionError(miles)
    metric = display_distance(prose, "km")
    if metric != "8 km easy, 6 × 400 m, planned 8 km":
        raise AssertionError(metric)
    reps = "5 × 1000 m comfortably hard, 60 s rest"
    if display_distance(reps, "km") != reps:
        raise AssertionError(display_distance(reps, "km"))
    steps = "5 steps: 150, 200, 300, 200, 150 m"
    if display_distance(steps, "km") != steps:
        raise AssertionError("a meter ladder was rewritten under kilometers")
    shown = display_distance(steps, "miles")
    if shown != "5 steps: 0.09, 0.12, 0.19, 0.12, 0.09 mi":
        raise AssertionError(shown)
    volume = "31,400 m · 31,600 m the week before"
    if display_distance(volume, "km") != "31.4 km · 31.6 km the week before":
        raise AssertionError(display_distance(volume, "km"))
    if display_distance(volume, "miles") != "19.5 mi · 19.6 mi the week before":
        raise AssertionError(display_distance(volume, "miles"))
    if distance_heading("miles", [8000]) != "Distance (mi)":
        raise AssertionError(distance_heading("miles", [8000]))
    if distance_heading("km", [8000, 5000]) != "Distance (km)":
        raise AssertionError(distance_heading("km", [8000, 5000]))
    if distance_heading("km", [400]) != "Distance (m)":
        raise AssertionError(distance_heading("km", [400]))
    if distance_number(8000, "km") != "8" or distance_number(400, "km") != "400":
        raise AssertionError("a metric lap used the wrong unit")
    if distance_number(8000, "miles") != "5.0" or distance_number(60, "miles") != "0.04":
        raise AssertionError((distance_number(8000, "miles"), distance_number(60, "miles")))
    labels = (
        miles,
        metric,
        distance_heading("miles"),
        distance_heading("km", [8000]),
        distance_heading("km", [400]),
    )
    for label in labels:
        if "mileage" in label or "meters" in label:
            raise AssertionError(label)


def main() -> None:
    test_defaults_and_rejected_values()
    test_dates_and_distances_are_display_only()
    test_distance_labels_follow_the_unit()
    print("settings ok")


if __name__ == "__main__":
    main()
