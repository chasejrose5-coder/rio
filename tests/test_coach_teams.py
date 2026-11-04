# test_coach_teams.py — codes, joining, and a read-only team list.

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.season import sequence
from ui.coach import _ALPHABET, change_member_role, new_code, season_summary
from ui.cloud_store import CloudAuthError, reset_memory_directory


def test_codes_are_short_and_a_new_one_replaces_the_old() -> None:
    for _ in range(20):
        code = new_code()
        if len(code) != 7 or any(char not in _ALPHABET for char in code):
            raise AssertionError(code)
        if any(char in code for char in "01IO"):
            raise AssertionError(code)
    directory = reset_memory_directory()
    coach = directory.sign_up("coach@example.com", "password-one", "Coach")
    directory.set_role(coach["user_id"], "coach", "server-key")
    coach = directory.sign_in("coach@example.com", "password-one")
    first = directory.ensure_team(coach["access_token"])
    second = directory.rotate_code(coach["access_token"])
    if first["code"] == second["code"]:
        raise AssertionError("the old code was kept")
    athlete = directory.sign_up("ada@example.com", "password-two", "Ada")
    try:
        directory.join_team(athlete["access_token"], first["code"])
    except CloudAuthError:
        pass
    else:
        raise AssertionError("the old code still joined")
    directory.join_team(athlete["access_token"], second["code"])
    if directory.membership(athlete["access_token"])["coach_name"] != "Coach":
        raise AssertionError("the athlete did not join")


def test_join_leave_and_one_team() -> None:
    directory = reset_memory_directory()
    coach = directory.sign_up("coach@example.com", "password-one", "Coach")
    other = directory.sign_up("other@example.com", "password-two", "Other")
    athlete = directory.sign_up("ada@example.com", "password-ada", "Ada")
    directory.set_role(coach["user_id"], "coach", "server-key")
    directory.set_role(other["user_id"], "coach", "server-key")
    coach = directory.sign_in("coach@example.com", "password-one")
    other = directory.sign_in("other@example.com", "password-two")
    first = directory.ensure_team(coach["access_token"])
    second = directory.ensure_team(other["access_token"])
    try:
        directory.join_team(coach["access_token"], first["code"])
    except CloudAuthError:
        pass
    else:
        raise AssertionError("a coach joined their own code")
    directory.join_team(athlete["access_token"], first["code"])
    try:
        directory.join_team(athlete["access_token"], second["code"])
    except CloudAuthError:
        pass
    else:
        raise AssertionError("an athlete joined a second team")
    directory.leave_team(athlete["access_token"])
    if directory.membership(athlete["access_token"]) is not None:
        raise AssertionError("leave did not remove the athlete")
    directory.join_team(athlete["access_token"], second["code"])
    if directory.membership(athlete["access_token"])["coach_name"] != "Other":
        raise AssertionError("the athlete did not move after leaving")
    try:
        change_member_role(directory, "ada@example.com", athlete["user_id"], "ada@example.com", "coach", "server-key")
    except CloudAuthError:
        pass
    else:
        raise AssertionError("an athlete changed their own role")
    try:
        directory.set_role(athlete["user_id"], "coach", "")
    except CloudAuthError:
        pass
    else:
        raise AssertionError("a role changed without the server key")


def test_the_team_list_is_read_only() -> None:
    directory = reset_memory_directory()
    coach = directory.sign_up("coach@example.com", "password-one", "Coach")
    stranger = directory.sign_up("other@example.com", "password-two", "Other")
    athlete = directory.sign_up("ada@example.com", "password-ada", "Ada")
    directory.set_role(coach["user_id"], "coach", "server-key")
    directory.set_role(stranger["user_id"], "coach", "server-key")
    coach = directory.sign_in("coach@example.com", "password-one")
    stranger = directory.sign_in("other@example.com", "password-two")
    code = directory.ensure_team(coach["access_token"])["code"]
    directory.ensure_team(stranger["access_token"])
    plan = sequence("2:05.0", "2026-11-01", "1:59.0", "2027-04-01")
    directory.save_bundle(
        athlete["access_token"],
        {
            "goal": {"goal_time": "1:59.0"},
            "plans": [
                {
                    "current_time": "2:05.0",
                    "start_date": "2026-11-01",
                    "goal_time": "1:59.0",
                    "goal_date": "2027-04-01",
                    "plan": plan,
                    "actuals": {},
                    "marks": {},
                }
            ],
        },
    )
    directory.join_team(athlete["access_token"], code)
    today = date(2026, 11, 4)
    roster = directory.roster(coach["access_token"], today=today)
    if roster["code"] != code or len(roster["athletes"]) != 1:
        raise AssertionError(roster)
    if roster["athletes"][0]["name"] != "Ada" or roster["athletes"][0]["goal_time"] != "1:59.0":
        raise AssertionError(roster["athletes"])
    if roster["athletes"][0]["status"] not in ("On track", "Ahead", "Behind"):
        raise AssertionError(roster["athletes"][0]["status"])
    other = directory.roster(stranger["access_token"], today=today)
    if other["athletes"]:
        raise AssertionError("another coach saw the athlete")
    record = directory.athlete_record(coach["access_token"], athlete["user_id"])
    if record is None or record["plan_row"]["goal_time"] != "1:59.0":
        raise AssertionError(record)
    if directory.athlete_record(athlete["access_token"], stranger["user_id"]) is not None:
        raise AssertionError("an athlete opened someone else's plan")
    if directory.athlete_record(stranger["access_token"], athlete["user_id"]) is not None:
        raise AssertionError("a coach opened an athlete who is not on the team")
    directory.save_bundle(coach["access_token"], {"goal": {"goal_time": "9:99"}})
    kept = directory.load_bundle(athlete["access_token"])
    if kept["goal"]["goal_time"] != "1:59.0":
        raise AssertionError("a coach wrote the athlete's goal")
    summary = season_summary(None, today=today)
    if summary != {"goal_time": "—", "days": "—", "phase": "—", "status": "—"}:
        raise AssertionError(summary)
    sql = (ROOT / "supabase" / "migrations" / "003_coach_teams.sql").read_text(encoding="utf-8")
    for piece in (
        "enable row level security",
        "grant select, insert, update on table public.teams to authenticated",
        "security definer",
        "join_team",
        "drop policy if exists",
        "coach_of",
    ):
        if piece not in sql:
            raise AssertionError(piece)
    if " for update " in sql and "goals" in sql.split("for update", 1)[-1][:80]:
        raise AssertionError("a coach can write goals")
    if "current_time" in sql and '"current_time"' not in sql:
        raise AssertionError("an unquoted reserved column")


def main() -> None:
    test_codes_are_short_and_a_new_one_replaces_the_old()
    test_join_leave_and_one_team()
    test_the_team_list_is_read_only()
    print("coach teams ok")


if __name__ == "__main__":
    main()
