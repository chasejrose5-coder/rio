# streamlit_app.py — Last Session, Next, Decisions, Ledger, Goal, and Season. Display only. No classification rules.

"""Six pages. Last Session reads normalize, classify, and explain. Next reads prescribe and explain. Decisions reads one planned row and explain. Ledger and Goal read the ledger. Season reads sequence. No scores."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.load import fixture_paths, parse_fixture
from engines.accept import PLANNED_DIR, load_planned
from engines.classify import classify
from engines.explain import explain, explain_decision, explain_prescription
from engines.ledger import Ledger
from engines.normalize import normalize
from engines.prescribe import PARAMETER_KEYS, prescribe
from engines.season import sequence

FIXTURES_DIR = ROOT / "tests" / "fixtures"

GOAL_FIELDS = (
    "current_mark",
    "target_time",
    "target_date",
    "limiting_capacities",
)


def _date_text(payload: dict) -> str:
    for key in ("date", "started_at"):
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _cell(value: object) -> object:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if value is None:
        return ""
    return value


def _dose_cell(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "" if value is None else str(value)
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _lap_rows(laps: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for index, lap in enumerate(laps, start=1):
        rows.append(
            {
                "Lap": index,
                "Distance (m)": _cell(lap.get("distance_m")),
                "Seconds": _cell(lap.get("seconds")),
                "Rest (s)": _cell(lap.get("rest_s")),
            }
        )
    return rows


def _deposit_rows(entries: list[dict], with_windows: bool = False) -> list[dict]:
    rows: list[dict] = []
    for entry in entries:
        row = {
            "Capacity": entry["capacity"],
            "Dose": _dose_cell(entry["dose"]),
            "Date": entry["date"],
            "Source": entry["source"],
        }
        if with_windows:
            row["expression_window_days"] = entry["expression_window_days"]
            row["decay_days"] = entry["decay_days"]
        rows.append(row)
    return rows


def _show_rows(rows: list[dict]) -> None:
    if rows:
        st.table(rows)
    else:
        st.write("—")


def _parameter_rows(parameters: dict) -> list[dict]:
    rows: list[dict] = []
    for key in PARAMETER_KEYS:
        value = parameters.get(key)
        text = "" if value is None else str(value).strip()
        rows.append({"Parameter": key, "Value": text or "—"})
    return rows


def render_session(payload: dict) -> None:
    """Show one session. Labels are whatever classify returns. The paragraph is explain."""
    source = str(payload.get("source", "")).strip().lower()
    if source == "fixture":
        st.markdown("FIXTURE")

    st.markdown("**Date**")
    st.write(_date_text(payload) or "—")

    st.markdown("**Laps**")
    rows = _lap_rows(normalize(payload)["laps"])
    if rows:
        st.table(rows)
    else:
        st.write("—")

    result = classify(payload)
    st.markdown("**Family**")
    st.write(result["family"])
    st.markdown("**Confidence**")
    st.write(result["confidence"])
    st.markdown("**Reason codes**")
    codes = result.get("reason_codes") or []
    st.write(", ".join(str(code) for code in codes) if codes else "—")

    st.write(explain(result))


def selected_fixture_path() -> Path | None:
    paths = fixture_paths(FIXTURES_DIR)
    if not paths:
        return None
    names = [path.stem for path in paths]
    selected = st.selectbox("Session", names)
    return paths[names.index(selected)]


def selected_payload() -> dict | None:
    path = selected_fixture_path()
    if path is None:
        return None
    return parse_fixture(path.read_text(encoding="utf-8"))


def page_last_session() -> None:
    st.title("Last Session")
    payload = selected_payload()
    if payload is None:
        st.write("No session files.")
    else:
        render_session(payload)


def page_next() -> None:
    """Next templates for one fixture ledger.

    Ids, parameters, and reason codes come from prescribe().
    The paragraph names that template id, those reason codes, and the goal.
    """
    st.title("Next")
    path = selected_fixture_path()
    if path is None:
        st.write("No session files.")
        return

    payload = parse_fixture(path.read_text(encoding="utf-8"))
    if str(payload.get("source", "")).strip().lower() == "fixture":
        st.markdown("FIXTURE")

    today = date.today()
    ledger = Ledger()
    ledger.record_fixture(path, today - timedelta(days=1))
    result = prescribe(ledger, today)

    st.markdown("**limiting_capacities**")
    limiting = ledger.goal.get("limiting_capacities")
    st.write(limiting if limiting not in (None, "") else "—")

    for index, row in enumerate(result["rows"]):
        if index:
            st.divider()
        st.markdown("**prescribed_on**")
        st.write(row.get("prescribed_on") or "—")
        st.markdown("**template_id**")
        st.write(row.get("template_id") or "—")
        st.markdown("**parameters**")
        _show_rows(_parameter_rows(row.get("parameters") or {}))
        st.markdown("**Reason codes**")
        codes = row.get("reason_codes") or []
        st.write(", ".join(str(code) for code in codes) if codes else "—")
        template_id = str(row.get("template_id") or "").strip()
        if template_id:
            st.write(
                explain_prescription(
                    template_id,
                    [str(code) for code in codes],
                    ledger.goal,
                )
            )


def page_decisions() -> None:
    """One planned row from tests/fixtures/planned. Fields are the stored acceptance.

    The paragraph names that template id and those reason codes.
    """
    st.title("Decisions")
    paths = sorted(PLANNED_DIR.glob("*.yml"))
    if not paths:
        st.write("No planned rows.")
        return
    if len(paths) == 1:
        path = paths[0]
    else:
        names = [item.stem for item in paths]
        selected = st.selectbox("Planned", names)
        path = paths[names.index(selected)]

    row = load_planned(path)
    if str(row.get("source", "")).strip().lower() == "fixture":
        st.markdown("FIXTURE")

    st.markdown("**template_id**")
    st.write(row.get("template_id") or "—")

    st.markdown("**parameters**")
    _show_rows(_parameter_rows(row.get("parameters") or {}))

    st.markdown("**reason_codes**")
    codes = row.get("reason_codes") or []
    st.write(", ".join(str(code) for code in codes) if codes else "—")
    template_id = str(row.get("template_id") or "").strip()
    if template_id:
        st.write(explain_decision(template_id, [str(code) for code in codes]))

    st.markdown("**placeholder_date**")
    st.write(row.get("placeholder_date") or "—")

    st.markdown("**ontology_version**")
    st.write(row.get("ontology_version") or "—")

    st.markdown("**source**")
    st.write(row.get("source") or "—")


def page_ledger() -> None:
    """Deposits from the four fixtures. Windows are the ledger's, as of today."""
    st.title("Ledger")
    today = date.today()
    ledger = Ledger()
    entries = ledger.record_fixtures(today)
    if any(str(entry.get("source", "")).strip().lower() == "fixture" for entry in entries):
        st.markdown("FIXTURE")

    st.markdown("**Deposits**")
    _show_rows(_deposit_rows(entries, with_windows=True))

    windows = ledger.deposits_on(today)
    st.markdown("**As of**")
    st.write(today.isoformat())
    st.markdown("**Emerging**")
    _show_rows(_deposit_rows(windows["emerging"]))
    st.markdown("**Decaying**")
    _show_rows(_deposit_rows(windows["decaying"]))


def page_goal() -> None:
    """The four goal.yml fields, as written. unknown stays unknown."""
    st.title("Goal")
    goal = Ledger().goal
    for key in GOAL_FIELDS:
        st.markdown(f"**{key}**")
        value = goal.get(key)
        st.write(value if value not in (None, "") else "—")


def _session_rows(sessions: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for session in sessions:
        codes = session["reason_codes"]
        rows.append(
            {
                "week_number": session["week_number"],
                "day_of_week": session["day_of_week"],
                "template_id": session["template_id"],
                "reason_codes": ", ".join(str(code) for code in codes) if codes else "—",
                "target_outcome": session["target_outcome"],
            }
        )
    return rows


def page_season() -> None:
    """The season sequence() returns from four inputs.

    No recorded workouts. Template ids stay the ones sequence chose.
    """
    st.warning("SYNTHETIC / DEMO")
    st.title("Season")
    current_time = st.text_input("current_time", value="2:02.9")
    start_date = st.date_input("start_date", value=date(2026, 4, 19))
    goal_time = st.text_input("goal_time", value="1:55.0")
    goal_date = st.date_input("goal_date", value=date(2027, 3, 19))
    try:
        plan = sequence(current_time, start_date, goal_time, goal_date)
    except ValueError as exc:
        st.write(str(exc))
        return

    st.markdown("**season_length_weeks**")
    st.write(plan["season_length_weeks"])
    st.markdown("**Sessions**")
    _show_rows(_session_rows(plan["sessions"]))


st.set_page_config(page_title="rio", layout="centered")
st.navigation(
    [
        st.Page(page_last_session, title="Last Session", default=True),
        st.Page(page_next, title="Next", url_path="next"),
        st.Page(page_decisions, title="Decisions", url_path="decisions"),
        st.Page(page_ledger, title="Ledger", url_path="ledger"),
        st.Page(page_goal, title="Goal", url_path="goal"),
        st.Page(page_season, title="Season", url_path="season"),
    ],
    position="top",
).run()
