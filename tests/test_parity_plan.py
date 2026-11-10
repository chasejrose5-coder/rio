# test_parity_plan.py — the season the API returns is the season Streamlit builds.

"""Several goals and dates. The workouts, the long-run ladder, the easy
pace, and the rep clocks come from the same engines the Streamlit pages
call. A difference here is a lost workout, not a layout change.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from api.main import create_app
from engines.pace import average_rep_text, easy_pace_phrase, workout_recipe, workout_times
from engines.season import _LONG_LADDER, sequence
from ui.dashboard import session_facts
from ui.settings import display_training, local_today
from ui.workout_text import WORKOUT_TEXT

# Spread on purpose: the golden contract, a short season, a mid-length
# season, a long season, a slow athlete, and a close pair of marks.
CASES = (
    ("2:02.9", "2026-04-19", "1:55.0", "2027-03-19"),
    ("2:10.0", "2026-11-08", "2:02.0", "2027-02-28"),
    ("2:18.0", "2026-06-07", "1:59.0", "2026-08-02"),
    ("2:05.5", "2026-03-02", "1:56.0", "2026-04-06"),
    ("1:59.0", "2026-01-04", "1:52.0", "2026-12-27"),
    ("2:30.0", "2026-09-06", "2:10.0", "2027-01-31"),
)


def _client(path: Path) -> TestClient:
    app = create_app(accounts=path, frontend_origin="http://localhost:3000", load_env=False)
    return TestClient(app, base_url="https://testserver")


def _sign_in(path: Path, email: str = "parity@example.com") -> TestClient:
    client = _client(path)
    created = client.post(
        "/auth/sign-up",
        json={"email": email, "password": "correct-horse", "name": "Parity"},
    )
    if created.status_code != 200:
        raise AssertionError(created.text)
    return client


def _six(plan: dict) -> list[dict]:
    rows = []
    for session in plan["sessions"]:
        rows.append(
            {
                "week_number": session["week_number"],
                "day_of_week": session["day_of_week"],
                "date": session["date"],
                "template_id": session["template_id"],
                "reason_codes": list(session["reason_codes"]),
                "target_outcome": session["target_outcome"],
            }
        )
    return rows


def _long_runs(plan: dict) -> list[tuple[str, str]]:
    found = []
    for session in plan["sessions"]:
        template = str(session.get("template_id") or "")
        if session.get("day_of_week") == "Saturday" and template.startswith("aer_"):
            found.append((str(session["date"]), template))
    return found


def _streamlit_clock(template: str, inputs: tuple, day: str, easy: str, unit: str) -> dict:
    """The line Streamlit's _split_html draws, plus the average it states."""
    recipe = workout_recipe(template)
    continuous = bool(recipe and recipe.get("continuous"))
    clock = workout_times(
        template,
        current_mark=inputs[0],
        goal_mark=inputs[2],
        start=date.fromisoformat(inputs[1]),
        goal_date=date.fromisoformat(inputs[3]),
        on=date.fromisoformat(day),
        easy_pace=easy or None,
        easy_unit=unit or None,
    )
    if continuous:
        phrase = easy_pace_phrase(easy, unit) if easy else ""
        line = f"Run at {phrase}" if phrase else "Set your easy pace before this run."
        return {"line": line, "tolerance": "", "block": "", "average": ""}
    if not isinstance(clock, dict):
        return {"line": "", "tolerance": "", "block": "", "average": ""}
    block = "" if recipe and recipe.get("speed") else str(clock.get("block") or "")
    return {
        "line": str(clock.get("line") or "").strip(),
        "tolerance": str(clock.get("tolerance") or ""),
        "block": block,
        "average": average_rep_text(clock.get("reps")),
    }


def _sample_days(plan: dict) -> list[dict]:
    """One continuous run, one quality day, and the last long run."""
    picked: list[dict] = []
    seen: set[str] = set()
    long_run = None
    for session in plan["sessions"]:
        template = str(session.get("template_id") or "")
        recipe = workout_recipe(template)
        if recipe is None:
            continue
        kind = "continuous" if recipe.get("continuous") else "quality"
        if kind not in seen:
            picked.append(session)
            seen.add(kind)
        if session.get("day_of_week") == "Saturday" and template.startswith("aer_"):
            long_run = session
    if long_run is not None and long_run not in picked:
        picked.append(long_run)
    return picked


def test_several_goals_and_dates_match_the_streamlit_season(tmp_path: Path) -> None:
    client = _sign_in(tmp_path / "accounts.json")
    for current, start, goal, goal_date in CASES:
        payload = {
            "current_time": current,
            "start_date": start,
            "goal_time": goal,
            "goal_date": goal_date,
        }
        built = sequence(current, start, goal, goal_date)
        response = client.post("/seasons", json=payload)
        if response.status_code != 200:
            raise AssertionError(response.text)
        body = response.json()
        plan = body["plan"]
        if plan.get("ontology_version") != built["ontology_version"]:
            raise AssertionError(plan.get("ontology_version"))
        if plan.get("season_length_weeks") != built["season_length_weeks"]:
            raise AssertionError((payload, plan.get("season_length_weeks"), built["season_length_weeks"]))
        if _six(plan) != _six(built):
            raise AssertionError(payload)
        api_long = _long_runs(plan)
        engine_long = _long_runs(built)
        if api_long != engine_long:
            raise AssertionError((payload, api_long, engine_long))
        # Buildup is the frozen 500 m ladder. A week may hold, step, or
        # take the rung the next week needs. Both sides use that ladder.
        for _day, template in api_long:
            if template not in _LONG_LADDER:
                raise AssertionError((payload, template))


def test_rep_clocks_follow_the_athlete_easy_pace(tmp_path: Path) -> None:
    client = _sign_in(tmp_path / "accounts.json")
    inputs = CASES[1]
    payload = {
        "current_time": inputs[0],
        "start_date": inputs[1],
        "goal_time": inputs[2],
        "goal_date": inputs[3],
    }
    generated = client.post("/seasons", json=payload)
    if generated.status_code != 200:
        raise AssertionError(generated.text)
    plan = generated.json()["plan"]
    samples = _sample_days(plan)
    if len(samples) < 2:
        raise AssertionError("the season had no quality day and no continuous run")

    def clocks(easy: str, unit: str, *, save: bool) -> dict[str, dict]:
        if save:
            saved = client.patch("/settings", json={"easy_pace": easy, "easy_pace_unit": unit})
            if saved.status_code != 200:
                raise AssertionError(saved.text)
        found = {}
        for session in samples:
            day = session["date"]
            template = session["template_id"]
            response = client.get(f"/sessions/{day}")
            if response.status_code != 200:
                raise AssertionError(response.text)
            body = response.json()
            prescription = body.get("prescription") or {}
            expected = _streamlit_clock(template, inputs, day, easy, unit)
            got = {
                "line": prescription.get("line") or "",
                "tolerance": prescription.get("tolerance") or "",
                "block": prescription.get("block") or "",
                "average": prescription.get("average") or "",
            }
            if got != expected:
                raise AssertionError((template, day, easy, unit, got, expected))
            facts = session_facts(template, WORKOUT_TEXT.get(template, ""))
            distance = str(facts.get("distance") or "—")
            recipe = workout_recipe(template)
            if recipe and recipe.get("continuous"):
                distance = display_training(distance, "miles") or distance
            if (body.get("facts") or {}).get("distance") != distance:
                raise AssertionError((template, body.get("facts"), distance))
            found[template] = got
        home = client.get("/home")
        if home.status_code != 200:
            raise AssertionError(home.text)
        season = home.json().get("season") or {}
        card = season.get("next") if isinstance(season, dict) else None
        card = card if isinstance(card, dict) else {}
        template = str(card.get("template_id") or "")
        day = str(card.get("date") or "")
        if template and day:
            expected = _streamlit_clock(template, inputs, day, easy, unit)
            prescription = card.get("prescription") or {}
            if (prescription.get("line") or "") != expected["line"]:
                raise AssertionError((template, prescription, expected))
        return found

    unset = clocks("", "mi", save=False)
    per_mile = clocks("7:25", "mi", save=True)
    per_km = clocks("4:36", "km", save=True)
    for template, row in per_mile.items():
        recipe = workout_recipe(template)
        if recipe and recipe.get("continuous"):
            if row["line"] != "Run at 7:25 per mile":
                raise AssertionError(row)
            if per_km[template]["line"] != "Run at 4:36 per kilometer":
                raise AssertionError(per_km[template])
            if unset[template]["line"] != "Set your easy pace before this run.":
                raise AssertionError(unset[template])
        else:
            if row != per_km[template] or row != unset[template]:
                raise AssertionError((template, unset[template], row, per_km[template]))
            if not row["average"]:
                raise AssertionError((template, row))


def test_units_change_distance_and_leave_rep_meters(tmp_path: Path) -> None:
    client = _sign_in(tmp_path / "accounts.json")
    inputs = CASES[0]
    payload = {
        "current_time": inputs[0],
        "start_date": inputs[1],
        "goal_time": inputs[2],
        "goal_date": inputs[3],
    }
    if client.post("/seasons", json=payload).status_code != 200:
        raise AssertionError("generate failed")
    pace = client.patch("/settings", json={"easy_pace": "7:25", "easy_pace_unit": "mi", "pace_units": "mi"})
    if pace.status_code != 200:
        raise AssertionError(pace.text)
    plan = client.get("/seasons/current").json()["plan"]
    continuous = next(
        session
        for session in plan["sessions"]
        if workout_recipe(session["template_id"]) and workout_recipe(session["template_id"]).get("continuous")
    )
    quality = next(
        session
        for session in plan["sessions"]
        if workout_recipe(session["template_id"]) and not workout_recipe(session["template_id"]).get("continuous")
    )
    miles = client.get(f"/sessions/{continuous['date']}").json()
    quality_miles = client.get(f"/sessions/{quality['date']}").json()
    switched = client.patch("/settings", json={"pace_units": "km"})
    if switched.status_code != 200 or switched.json()["prefs"]["units"] != "km":
        raise AssertionError(switched.text)
    kilometers = client.get(f"/sessions/{continuous['date']}").json()
    quality_km = client.get(f"/sessions/{quality['date']}").json()
    raw = str(session_facts(continuous["template_id"], WORKOUT_TEXT.get(continuous["template_id"], "")).get("distance"))
    if miles["facts"]["distance"] != (display_training(raw, "miles") or raw):
        raise AssertionError(miles["facts"])
    if kilometers["facts"]["distance"] != (display_training(raw, "km") or raw):
        raise AssertionError(kilometers["facts"])
    if miles["facts"]["distance"] == kilometers["facts"]["distance"]:
        raise AssertionError("per km did not change the continuous distance")
    if "km" not in kilometers["facts"]["distance"].lower() and "kilometer" not in kilometers["facts"]["distance"].lower():
        raise AssertionError(kilometers["facts"]["distance"])
    if quality_miles["prescription"] != quality_km["prescription"]:
        raise AssertionError("per km changed a rep clock")
    if "mi" in (quality_km["facts"].get("distance") or "").lower():
        raise AssertionError(quality_km["facts"])


def test_timezone_decides_today_for_los_angeles_and_auckland(tmp_path: Path) -> None:
    client = _sign_in(tmp_path / "accounts.json")
    for zone in ("America/Los_Angeles", "Pacific/Auckland"):
        saved = client.patch("/settings", json={"timezone": zone, "date_format": "iso"})
        if saved.status_code != 200:
            raise AssertionError(saved.text)
        home = client.get("/home")
        if home.status_code != 200:
            raise AssertionError(home.text)
        expected = local_today(zone).isoformat()
        if home.json()["today"] != expected:
            raise AssertionError((zone, home.json()["today"], expected))
        if client.get("/auth/me").json()["today"] != expected:
            raise AssertionError(zone)
    short = client.patch("/settings", json={"date_format": "short", "timezone": "America/Los_Angeles"})
    if short.status_code != 200 or short.json()["prefs"]["date_format"] != "short":
        raise AssertionError(short.text)


def test_a_goal_before_the_start_is_the_same_sentence(tmp_path: Path) -> None:
    client = _sign_in(tmp_path / "accounts.json")
    response = client.post(
        "/seasons",
        json={
            "current_time": "2:05.0",
            "start_date": "2026-11-10",
            "goal_time": "1:58.0",
            "goal_date": "2026-11-01",
        },
    )
    if response.status_code != 400 or response.json()["detail"] != "goal_date is before start_date":
        raise AssertionError(response.text)


def test_locked_settings_sentences_match_streamlit() -> None:
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    view = (ROOT / "web" / "components" / "SettingsView.tsx").read_text(encoding="utf-8")
    helper = (ROOT / "web" / "lib" / "settings.ts").read_text(encoding="utf-8")
    web = view + "\n" + helper
    sentences = (
        "First name is enough. Saved on this machine.",
        "First name is enough. Saved to your RIO account.",
        "Clears this browser. The account stays on this machine.",
        "Signs you out on this browser. Your season stays in your account.",
        "Distances and paces on Activity, Home, and Plan use this. Reps stay in meters.",
        "Complete workouts with Done instead of entering splits.",
        "Ask me before a timed run changes later weeks",
        "Next Sunday starts the training week.",
        "Reset removes stored seasons. The account stays.",
        "Reset the plan, delete this account, or clear this browser. These sit apart from the settings above.",
        "I understand this permanently deletes my season and runs",
        "Clear data stored in this browser",
        "Clear all marks / actuals",
        "Export season as JSON",
        "Generate a season on Start.",
        "Show template ids",
        "Compact mode",
        "I don't use a watch",
        "Preferred name / nickname",
        "Show intro guide",
        "Change password",
        "Change email",
        "Delete my account",
        "Clear local data",
        "Confirm clear",
        "Confirm reset",
        "Type your email to confirm",
        "Strava data is only visible to you.",
    )
    # The two hosted/local notes live in the Python helpers, not only the page.
    app = app + "\n" + (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    missing = [sentence for sentence in sentences if sentence not in app or sentence not in web]
    # Strava's privacy line is drawn by the Strava panel, not SettingsView itself.
    strava = (ROOT / "ui" / "strava_ui.py").read_text(encoding="utf-8")
    strava_web = (ROOT / "web" / "components" / "StravaSettings.tsx").read_text(encoding="utf-8")
    still = []
    for sentence in missing:
        left = sentence in app or sentence in strava
        right = sentence in web or sentence in strava_web
        if not left or not right:
            still.append(sentence)
    if still:
        raise AssertionError(still)


def test_papers_have_one_copy_and_both_apps_load_it() -> None:
    from engines.ledger import CAPACITIES_PATH, GOAL_PATH, load_paper
    from engines.prescribe import CONSTRAINTS_PATH, load_constraints
    from engines.season import _WEIGHTS_PATH

    papers = (CAPACITIES_PATH, GOAL_PATH, CONSTRAINTS_PATH, _WEIGHTS_PATH)
    for path in papers:
        if not path.is_file():
            raise AssertionError(path)
        if "web" in path.parts:
            raise AssertionError(path)
    # Capacities, the goal, and the weights carry no version key. The
    # folder name is the version both engines store on a plan.
    if not load_paper(CAPACITIES_PATH) or not load_paper(GOAL_PATH) or not load_paper(_WEIGHTS_PATH):
        raise AssertionError("a paper did not load")
    rules = load_constraints(CONSTRAINTS_PATH)
    if rules.get("ontology_version") != "v0.1":
        raise AssertionError("constraints paper")
    duplicates = []
    for path in (ROOT / "web").rglob("*.yml"):
        if path.name in {item.name for item in papers}:
            duplicates.append(str(path))
    if duplicates:
        raise AssertionError(duplicates)
