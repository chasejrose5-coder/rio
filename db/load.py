# load.py — apply db/schema.sql and load fixture workouts into data/rio.sqlite.
# No classification and no language model.

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "db" / "schema.sql"
DB_PATH = ROOT / "data" / "rio.sqlite"
FIXTURES_DIR = ROOT / "tests" / "fixtures"
SEED_DIR = ROOT / "data" / "seed"
ATHLETE_NAME = "Chase"

SKIP_SEED_NAMES = {".gitkeep"}


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_fixture(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"line {line_number}: expected key: value")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"line {line_number}: missing key")
        values[key] = unquote(value.strip())
    return values


def session_note(values: dict[str, str]) -> str | None:
    parts = [values.get("note", "").strip(), values.get("detail", "").strip()]
    text = "\n".join(part for part in parts if part)
    return text or None


def count_seed_files(seed_dir: Path) -> int:
    if not seed_dir.is_dir():
        return 0
    count = 0
    for path in seed_dir.iterdir():
        if not path.is_file():
            continue
        if path.name in SKIP_SEED_NAMES or path.name.startswith("."):
            continue
        count += 1
    return count


def fixture_paths(fixtures_dir: Path) -> list[Path]:
    paths = list(fixtures_dir.glob("*.yml"))
    paths.extend(fixtures_dir.glob("*.yaml"))
    return sorted(paths)


def load_fixtures(conn: sqlite3.Connection, fixtures_dir: Path) -> tuple[int, int]:
    athlete_id = conn.execute(
        "INSERT INTO athletes (name) VALUES (?)",
        (ATHLETE_NAME,),
    ).lastrowid
    workouts = 0
    steps = 0
    for path in fixture_paths(fixtures_dir):
        values = parse_fixture(path.read_text(encoding="utf-8"))
        laps = int(values["laps"])
        distance_m = float(values["distance_m"])
        seconds = int(values["seconds"])
        rest_s = int(values["rest_s"])
        if laps < 1:
            raise ValueError(f"{path.name}: laps must be at least 1")
        # Elapsed time includes recovery between reps, not a rest after the last one.
        total_distance = laps * distance_m
        total_elapsed = laps * seconds + (laps - 1) * rest_s
        cursor = conn.execute(
            """
            INSERT INTO workouts (
                athlete_id, source, title, note, distance_m, elapsed_s
            ) VALUES (?, 'fixture', ?, ?, ?, ?)
            """,
            (
                athlete_id,
                path.stem,
                session_note(values),
                total_distance,
                total_elapsed,
            ),
        )
        workout_id = cursor.lastrowid
        workouts += 1
        for step_index in range(1, laps + 1):
            conn.execute(
                """
                INSERT INTO workout_steps (
                    workout_id, step_index, distance_m, seconds, rest_s
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (workout_id, step_index, distance_m, seconds, rest_s),
            )
            steps += 1
    return workouts, steps


def recreate_database(db_path: Path, schema_sql: str) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-journal", "-wal", "-shm"):
        sidecar = Path(f"{db_path}{suffix}")
        if sidecar.is_file():
            sidecar.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(schema_sql)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def main() -> None:
    seed_count = count_seed_files(SEED_DIR)
    if seed_count == 0:
        print("zero seed files")
    else:
        print(f"{seed_count} seed files")
    if not SCHEMA_PATH.is_file():
        raise SystemExit(f"missing schema: {SCHEMA_PATH}")
    if not FIXTURES_DIR.is_dir():
        raise SystemExit(f"missing fixtures directory: {FIXTURES_DIR}")
    conn = recreate_database(DB_PATH, SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        with conn:
            workouts, steps = load_fixtures(conn, FIXTURES_DIR)
    finally:
        conn.close()
    print(f"athlete: {ATHLETE_NAME}")
    print(f"workouts: {workouts}")
    print(f"workout_steps: {steps}")
    print(f"database: {DB_PATH}")


if __name__ == "__main__":
    main()
