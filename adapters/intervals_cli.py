# intervals_cli.py — normalize and classify one Intervals.icu activity.

"""Read-only CLI. A JSON file stays offline. A live fetch is not stored unless asked."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.intervals_icu import (
    IntervalsIcuError,
    fetch_activity,
    list_activities,
    to_normalize_input,
)
from engines.classify import classify
from engines.normalize import normalize


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    _check_args(parser, args)
    try:
        if args.file:
            _print_activity(_read_activity_file(Path(args.file)))
            return 0
        _load_dotenv()
        if args.list:
            _print_list(list_activities(args.oldest, args.newest))
            return 0
        activity = fetch_activity(args.activity_id)
        if args.save_json:
            _write_json(Path(args.save_json), activity)
        _print_activity(activity)
        return 0
    except IntervalsIcuError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m adapters.intervals_cli",
        description="Normalize and classify one Intervals.icu activity. Read-only.",
    )
    parser.add_argument("--file", help="Activity JSON file. Does not use the network.")
    parser.add_argument("--activity-id", help="Fetch this activity id from Intervals.icu.")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List activities from --oldest through --newest.",
    )
    parser.add_argument("--oldest", help="First day YYYY-MM-DD for --list.")
    parser.add_argument("--newest", help="Last day YYYY-MM-DD for --list.")
    parser.add_argument("--save-json", help="Write the fetched activity JSON to this path.")
    return parser


def _check_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    chosen = sum(bool(item) for item in (args.file, args.activity_id, args.list))
    if chosen != 1:
        parser.error("Choose one of --file, --activity-id, or --list.")
    if args.list and (not args.oldest or not args.newest):
        parser.error("--list requires --oldest YYYY-MM-DD and --newest YYYY-MM-DD.")
    if (args.oldest or args.newest) and not args.list:
        parser.error("--oldest and --newest are only used with --list.")
    if args.save_json and not args.activity_id:
        parser.error("--save-json writes the fetched activity. Pass --activity-id.")


def _print_activity(activity: dict) -> None:
    print(f"id: {_text(activity.get('id'))}")
    print(f"name: {_text(activity.get('name'))}")
    print(f"date: {_activity_date(activity)}")
    payload = to_normalize_input(activity)
    laps = normalize(payload)["laps"]
    print("laps:")
    print(json.dumps(laps, indent=2))
    result = classify(payload)
    print("classify:")
    print(
        json.dumps(
            {
                "family": result["family"],
                "reason_codes": result["reason_codes"],
                "confidence": result["confidence"],
                "ontology_version": result["ontology_version"],
            },
            indent=2,
        )
    )


def _print_list(rows: list[dict]) -> None:
    for row in rows:
        print(
            "id: {id} | name: {name} | date: {date} | type: {type}".format(
                id=_text(row.get("id")),
                name=_text(row.get("name")),
                date=_text(row.get("start_date_local")),
                type=_text(row.get("type")),
            )
        )


def _activity_date(activity: dict) -> str:
    for key in ("start_date_local", "start_date", "date"):
        value = activity.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _read_activity_file(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise IntervalsIcuError(f"Could not read activity file: {path}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise IntervalsIcuError(f"Activity file is not JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise IntervalsIcuError(f"Activity file must be a JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _load_dotenv() -> None:
    """Load KEY=VALUE lines from .env. Existing environment values win.

    The values are never printed.
    """
    seen: set[Path] = set()
    for directory in (Path.cwd(), ROOT):
        path = (directory / ".env").resolve()
        if path in seen or not path.is_file():
            seen.add(path)
            continue
        seen.add(path)
        _apply_dotenv(path)


def _apply_dotenv(path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise IntervalsIcuError(f"Could not read .env: {path}") from exc
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if name and name not in os.environ:
            os.environ[name] = value


if __name__ == "__main__":
    raise SystemExit(main())
