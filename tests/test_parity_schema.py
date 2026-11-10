# test_parity_schema.py — the columns the app writes, read from Postgres catalogs.

"""Applies the Supabase migrations to a local database named rio_parity_audit
and reads them back with information_schema.columns, pg_indexes, and
pg_trigger. It does not open a hosted project and it does not read .env.

The database name is fixed. A different current_database() stops the test
before any statement that changes a schema.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "supabase" / "migrations"
DB = "rio_parity_audit"

# Columns the hosted writers send. A name that is not in the catalog is a
# schema drift. Extra catalog columns are allowed; this PR does not drop them.
WRITES = {
    "profiles": {"id", "email", "display_name", "role"},
    "goals": {"user_id", "event", "goal_time", "goal_date", "current_mark"},
    "plans": {"user_id", "current_time", "start_date", "goal_time", "goal_date", "plan", "marks", "actuals"},
    "results": {"user_id", "logged_on", "template_id"},
    "app_sessions": {"sid_hash", "user_id"},
    "season_state": {"user_id", "current_time", "start_date", "goal_time", "goal_date", "quality_base", "workout_notes"},
    "strava_tokens": {
        "user_id",
        "athlete_id",
        "athlete_name",
        "access_token",
        "refresh_token",
        "expires_at",
        "last_sync_at",
        "scope",
    },
    "strava_activities": {"user_id"},
    "strava_oauth": {"user_id"},
    "explain_spend": set(),
}


def _psql(*args: str, input_sql: str | None = None) -> str:
    completed = subprocess.run(
        ["psql", "-d", DB, "-v", "ON_ERROR_STOP=1", "-X", "-q", *args],
        input=input_sql,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr.strip() or completed.stdout)
    return completed.stdout


def test_migrations_do_not_use_the_mysql_statistics_view() -> None:
    for path in sorted(MIGRATIONS.glob("*.sql")):
        text = path.read_text(encoding="utf-8").lower()
        if "information_schema.statistics" in text:
            raise AssertionError(path.name)


def test_local_catalog_has_every_column_the_app_writes() -> None:
    if shutil.which("psql") is None:
        import pytest

        pytest.skip("psql is not installed")
    probe = subprocess.run(
        ["psql", "-d", DB, "-X", "-tA", "-c", "select current_database()"],
        text=True,
        capture_output=True,
        check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != DB:
        import pytest

        pytest.skip("local database rio_parity_audit is not available")

    _psql(
        input_sql="""
        drop schema if exists public cascade;
        create schema public;
        drop schema if exists auth cascade;
        create schema auth;
        create table auth.users (id uuid primary key);
        create or replace function auth.uid() returns uuid language sql stable as $$ select null::uuid $$;
        create or replace function auth.role() returns text language sql stable as $$ select ''::text $$;
        create or replace function auth.jwt() returns jsonb language sql stable as $$ select '{}'::jsonb $$;
        do $$ begin
          create role anon nologin;
        exception when duplicate_object then null;
        end $$;
        do $$ begin
          create role authenticated nologin;
        exception when duplicate_object then null;
        end $$;
        do $$ begin
          create role service_role nologin;
        exception when duplicate_object then null;
        end $$;
        grant usage on schema public to authenticated, service_role;
        """
    )
    for path in sorted(MIGRATIONS.glob("*.sql")):
        _psql("-f", str(path))

    name = _psql("-tA", "-c", "select current_database()").strip()
    if name != DB:
        raise AssertionError(name)

    columns = _psql(
        "-tA",
        "-F",
        "|",
        "-c",
        """
        select table_name, column_name
        from information_schema.columns
        where table_schema = 'public'
        order by table_name, ordinal_position
        """,
    )
    found: dict[str, set[str]] = {}
    for line in columns.splitlines():
        if not line.strip():
            continue
        table, column = line.split("|", 1)
        found.setdefault(table, set()).add(column)
    missing = []
    for table, needed in WRITES.items():
        have = found.get(table)
        if have is None:
            missing.append(f"{table} (table)")
            continue
        for column in sorted(needed - have):
            missing.append(f"{table}.{column}")
    if missing:
        raise AssertionError(missing)

    indexes = _psql(
        "-tA",
        "-c",
        "select indexname from pg_indexes where schemaname = 'public' order by indexname",
    )
    triggers = _psql(
        "-tA",
        "-c",
        """
        select tgname
        from pg_trigger
        where not tgisinternal
          and tgrelid in (select oid from pg_class where relnamespace = 'public'::regnamespace)
        order by tgname
        """,
    )
    index_names = {line.strip() for line in indexes.splitlines() if line.strip()}
    trigger_names = {line.strip() for line in triggers.splitlines() if line.strip()}
    for required in ("strava_oauth_expires_at",):
        if required not in index_names:
            raise AssertionError(sorted(index_names))
    for required in (
        "profiles_lock_role",
        "profiles_lock_email",
        "strava_oauth_touch_updated_at",
    ):
        if required not in trigger_names:
            raise AssertionError(sorted(trigger_names))
