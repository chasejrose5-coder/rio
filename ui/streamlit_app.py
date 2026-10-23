# streamlit_app.py — Last Session, Next, Decisions, Ledger, Goal, and Season. Display only. No classification rules.

"""Six pages. Last Session reads normalize, classify, and explain. Next reads prescribe and explain. Decisions reads one planned row and explain. Ledger and Goal read the ledger. Season reads sequence and adapt. No scores."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from html import escape
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
from engines.season import adapt, sequence

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


def _parameter_rows(parameters: dict) -> list[dict]:
    rows: list[dict] = []
    for key in PARAMETER_KEYS:
        value = parameters.get(key)
        text = "" if value is None else str(value).strip()
        rows.append({"Parameter": key, "Value": text or "—"})
    return rows


def render_session(payload: dict) -> None:
    """Show one session. Labels are whatever classify returns. The paragraph is explain."""
    rows = _lap_rows(normalize(payload)["laps"])
    result = classify(payload)
    codes = result.get("reason_codes") or []
    _card(_label("Laps"), _table(rows))
    _card(
        _fields(
            [
                ("Date", _date_text(payload) or "—"),
                ("Family", result["family"]),
                ("Confidence", result["confidence"]),
                ("Reason codes", _codes(codes)),
            ]
        ),
        _prose(explain(result)),
    )


def selected_fixture_path() -> Path | None:
    paths = fixture_paths(FIXTURES_DIR)
    if not paths:
        return None
    names = [path.stem for path in paths]
    selected = st.selectbox("Session", names)
    return paths[names.index(selected)]


def page_last_session() -> None:
    paths = fixture_paths(FIXTURES_DIR)
    hero, controls = _open("Last Session", controls=bool(paths))
    if not paths:
        with hero:
            st.markdown(_page_hero("Last Session"), unsafe_allow_html=True)
        st.markdown('<p class="rio-empty">No session files.</p>', unsafe_allow_html=True)
        return
    with controls:
        path = selected_fixture_path()
    if path is None:
        with hero:
            st.markdown(_page_hero("Last Session"), unsafe_allow_html=True)
        st.markdown('<p class="rio-empty">No session files.</p>', unsafe_allow_html=True)
        return
    payload = parse_fixture(path.read_text(encoding="utf-8"))
    with hero:
        st.markdown(
            _page_hero("Last Session", _fixture_banner(payload.get("source"))),
            unsafe_allow_html=True,
        )
    render_session(payload)


def page_next() -> None:
    """Next templates for one fixture ledger.

    Ids, parameters, and reason codes come from prescribe().
    The paragraph names that template id, those reason codes, and the goal.
    """
    paths = fixture_paths(FIXTURES_DIR)
    hero, controls = _open("Next", controls=bool(paths))
    if not paths:
        with hero:
            st.markdown(_page_hero("Next"), unsafe_allow_html=True)
        st.markdown('<p class="rio-empty">No session files.</p>', unsafe_allow_html=True)
        return

    with controls:
        path = selected_fixture_path()
    if path is None:
        with hero:
            st.markdown(_page_hero("Next"), unsafe_allow_html=True)
        st.markdown('<p class="rio-empty">No session files.</p>', unsafe_allow_html=True)
        return
    payload = parse_fixture(path.read_text(encoding="utf-8"))
    today = date.today()
    ledger = Ledger()
    ledger.record_fixture(path, today - timedelta(days=1))
    result = prescribe(ledger, today)
    with hero:
        st.markdown(
            _page_hero("Next", _fixture_banner(payload.get("source"))),
            unsafe_allow_html=True,
        )

    limiting = ledger.goal.get("limiting_capacities")
    _card(_fields([("limiting_capacities", limiting if limiting not in (None, "") else "—")]))
    for row in result["rows"]:
        codes = row.get("reason_codes") or []
        template_id = str(row.get("template_id") or "").strip()
        parts = [
            _subject("template_id", template_id or "—"),
            _fields([("prescribed_on", row.get("prescribed_on") or "—")]),
            _label("parameters"),
            _fields(
                [
                    (item["Parameter"], item["Value"])
                    for item in _parameter_rows(row.get("parameters") or {})
                ]
            ),
            _fields([("Reason codes", _codes(codes))]),
        ]
        if template_id:
            parts.append(
                _prose(
                    explain_prescription(
                        template_id,
                        [str(code) for code in codes],
                        ledger.goal,
                    )
                )
            )
        _card(*parts)


def page_decisions() -> None:
    """One planned row from tests/fixtures/planned. Fields are the stored acceptance.

    The paragraph names that template id and those reason codes.
    """
    paths = sorted(PLANNED_DIR.glob("*.yml"))
    hero, controls = _open("Decisions", controls=len(paths) > 1)
    if not paths:
        with hero:
            st.markdown(_page_hero("Decisions"), unsafe_allow_html=True)
        st.markdown('<p class="rio-empty">No planned rows.</p>', unsafe_allow_html=True)
        return
    if controls is None:
        path = paths[0]
    else:
        with controls:
            names = [item.stem for item in paths]
            selected = st.selectbox("Planned", names)
            path = paths[names.index(selected)]

    row = load_planned(path)
    codes = row.get("reason_codes") or []
    template_id = str(row.get("template_id") or "").strip()
    with hero:
        st.markdown(
            _page_hero("Decisions", _fixture_banner(row.get("source"))),
            unsafe_allow_html=True,
        )
    parts = [
        _subject("template_id", template_id or "—"),
        _label("parameters"),
        _fields(
            [
                (item["Parameter"], item["Value"])
                for item in _parameter_rows(row.get("parameters") or {})
            ]
        ),
        _fields([("reason_codes", _codes(codes))]),
    ]
    if template_id:
        parts.append(_prose(explain_decision(template_id, [str(code) for code in codes])))
    parts.append(
        _fields(
            [
                ("placeholder_date", row.get("placeholder_date") or "—"),
                ("ontology_version", row.get("ontology_version") or "—"),
                ("source", row.get("source") or "—"),
            ]
        )
    )
    _card(*parts)


def page_ledger() -> None:
    """Deposits from the four fixtures. Windows are the ledger's, as of today."""
    hero, _controls = _open("Ledger")
    today = date.today()
    ledger = Ledger()
    entries = ledger.record_fixtures(today)
    banner = None
    if any(str(entry.get("source", "")).strip().lower() == "fixture" for entry in entries):
        banner = "FIXTURE"
    with hero:
        st.markdown(
            _page_hero("Ledger", banner, f"As of {today.isoformat()}"),
            unsafe_allow_html=True,
        )
    windows = ledger.deposits_on(today)
    _card(_label("Deposits"), _table(_deposit_rows(entries, with_windows=True)))
    _card(_label("Emerging"), _table(_deposit_rows(windows["emerging"])))
    _card(_label("Decaying"), _table(_deposit_rows(windows["decaying"])))


def page_goal() -> None:
    """The four goal.yml fields, as written. unknown stays unknown."""
    hero, _controls = _open("Goal")
    goal = Ledger().goal
    with hero:
        st.markdown(_page_hero("Goal"), unsafe_allow_html=True)
    _card(_fields([(key, goal.get(key)) for key in GOAL_FIELDS]))


_DAY_ORDER = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)
_DAY_RANK = {day: index for index, day in enumerate(_DAY_ORDER)}
_MARKS = ("on_track", "not_hitting", "smashing")


def _day_rank(session: dict) -> tuple[int, str]:
    day = str(session["day_of_week"])
    return (_DAY_RANK.get(day, len(_DAY_ORDER)), day)


def _phase_number(sessions: list[dict]) -> str:
    found: list[str] = []
    for session in sessions:
        for code in session["reason_codes"]:
            text = str(code)
            if len(text) == 7 and text.startswith("phase_") and text[6] in "12345678":
                number = text[6]
                if number not in found:
                    found.append(number)
    if len(found) == 1:
        return found[0]
    if not found:
        return "—"
    return ", ".join(found)


def _weeks(sessions: list[dict]) -> list[tuple[int, list[dict]]]:
    grouped: dict[int, list[dict]] = {}
    for session in sessions:
        grouped.setdefault(session["week_number"], []).append(session)
    return [
        (number, sorted(grouped[number], key=_day_rank))
        for number in sorted(grouped)
    ]


def _reason_text(codes: list) -> str:
    return ", ".join(str(code) for code in codes) if codes else "—"


def _season_plan(inputs: tuple[str, str, str, str], current_time, start_date, goal_time, goal_date) -> dict:
    """sequence() when the four inputs change. A submitted mark keeps adapt()'s plan."""
    if st.session_state.get("season_inputs") != inputs:
        plan = sequence(current_time, start_date, goal_time, goal_date)
        st.session_state["season_inputs"] = inputs
        st.session_state["season_plan"] = plan
        st.session_state["season_marks"] = {}
        st.session_state["season_generation"] = int(st.session_state.get("season_generation") or 0) + 1
    return st.session_state["season_plan"]


# Display labels for reason codes already on the session. Not a score.
_STATUS_LABELS = (
    ("harder_template", "Harder"),
    ("extra_easy_week", "Easy week"),
    ("extra_easy_day", "Easy"),
    ("ten_percent_hold", "Hold"),
    ("ten_percent_easier_template", "Easier"),
    ("weekly_aerobic_long_run", "Long"),
    ("moved_back_one_phase", "Moved back"),
    ("advanced_one_phase", "Advanced"),
    ("phase_8_freshness", "Fresh"),
    ("phase_8_no_hard_se_or_an", "Taper"),
    ("priority_speed_endurance", "Speed endurance"),
    ("priority_aerobic_power", "Aerobic power"),
    ("priority_anaerobic_capacity", "Anaerobic"),
    ("phase_primary", "Primary"),
    ("phase_secondary", "Secondary"),
    ("capacity_weight", "Weighted"),
)

# Card copy only. template_id stays on the session and inside reason codes.
_WORKOUT_TEXT = {
    "aer_4000_r0_x1": "4 km very easy, Zone 2",
    "aer_5000_r0_x1": "5 km easy, Zone 2, talkable the whole way",
    "aer_8000_r0_x1": "8 km easy, Zone 2",
    "aer_10000_r0_x1": "10 km easy, Zone 2, talkable",
    "aer_12000_r0_x1": "12 km easy, still talkable",
    "mv_60_r120_x10": "10 × 60 m fast, rolling start, full rest",
    "mv_80_r180_x8": "8 × 80 m fast, full recovery",
    "spd_150_r150_x8": "8 × 150 m at or faster than goal 800 pace, long rest",
    "thr_1000_r60_x5": "5 × 1000 m comfortably hard, not 800 pace, 60 s rest",
    "thr_1200_r60_x4": "4 × 1200 m comfortably hard, 60 s rest",
    "ap_600_r75_x6": "6 × 600 m strong, slower than goal 800 pace, 75 s rest",
    "ap_700_r90_x5": "5 × 700 m strong, not goal 800 pace, 90 s rest",
    "ap_800_r90_x5": "5 × 800 m strong, clearly slower than goal 800 pace, 90 s rest",
    "se_300_r75_x8": "8 × 300 m near goal 800 pace, 75 s rest",
    "se_400_r90_x6": "6 × 400 m near goal 800 pace, 90 s rest",
    "se_500_r120_x4": "4 × 500 m near goal 800 pace, 2 min rest",
    "an_600_r180_x3": "3 × 600 m hard, 3 min rest",
    "an_400_r45_x6": "Broken 800s, 3 × (400 + 400) near goal 800 pace, 45 s rest",
    "rr_200_r180_x4": "4 × 200 m at goal 800 pace, long rest",
    "rr_300_r180_x3": "3 × 300 m at goal 800 pace, long rest",
    "rr_400_r240_x2": "2 × 400 m at goal 800 pace, long rest",
    "rr_800_r0_x1": "800 m race",
}

_NAV = (
    ("Last Session", "/"),
    ("Next", "/next"),
    ("Decisions", "/decisions"),
    ("Ledger", "/ledger"),
    ("Goal", "/goal"),
    ("Season", "/season"),
)

_APP_CSS = """
<style>
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"],
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {
  background: #0f0f0f !important;
  color: #f0f0f0 !important;
}
html { color-scheme: dark; }
.stApp, .stApp button, .stApp input, .stApp label, .stApp summary, .stApp p,
.stMarkdown, .stMarkdown h1, .stMarkdown h2, .stMarkdown a, .stMarkdown p, .stMarkdown div,
.rio-nav, .rio-nav a, .rio-hero, .rio-hero h1, .rio-week-title, .rio-day, .rio-day div,
.rio-card, .rio-card h2, .rio-table, .rio-table th, .rio-table td {
  font-family: "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
}
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
#MainMenu,
footer {
  display: none !important;
  height: 0 !important;
}
[data-testid="stMainBlockContainer"],
.block-container {
  max-width: 880px !important;
  padding: 0.25rem 1.6rem 5rem !important;
}
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="stElementContainer"],
[data-testid="stMarkdownContainer"] {
  background: transparent !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] {
  margin-bottom: 0 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stElementContainer"] {
  margin-bottom: 0 !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {
  gap: 0 !important;
}
[data-testid="stHeaderActionElements"] { display: none !important; }
.stMarkdown a,
[data-testid="stMarkdownContainer"] a {
  text-decoration: none !important;
}

.rio-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 1.35rem 0 1rem;
  border-bottom: 1px solid #242424;
  position: sticky;
  top: 0;
  z-index: 30;
  background: #0f0f0f;
}
a.rio-brand {
  color: #f0f0f0 !important;
  text-decoration: none !important;
  font-weight: 600 !important;
  letter-spacing: 0.2em !important;
  font-size: 0.92rem !important;
}
.rio-links {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.35rem 1.15rem;
}
a.rio-link {
  color: #6f6f6f !important;
  text-decoration: none !important;
  font-size: 0.84rem !important;
  padding: 0.15rem 0 0.28rem;
  border-bottom: 2px solid transparent !important;
}
a.rio-link:hover { color: #f0f0f0 !important; }
a.rio-link.is-active {
  color: #f0f0f0 !important;
  border-bottom-color: #4E6E4D !important;
}
.rio-link:focus-visible,
.rio-brand:focus-visible,
button:focus-visible {
  outline: 1px solid #4E6E4D;
  outline-offset: 3px;
}

.rio-hero { padding: 3.1rem 0 2.1rem; }
.rio-synthetic {
  margin: 0 !important;
  color: #6a6a6a !important;
  font-size: 0.68rem !important;
  line-height: 1.3 !important;
  letter-spacing: 0.16em;
  font-weight: 500;
}
.rio-hero h1,
.stMarkdown .rio-hero h1 {
  margin: 0.7rem 0 0 !important;
  padding: 0 !important;
  color: #f0f0f0 !important;
  font-size: 3.35rem !important;
  font-weight: 500 !important;
  letter-spacing: -0.04em !important;
  line-height: 1.02 !important;
}
.rio-hero h1:first-child,
.stMarkdown .rio-hero h1:first-child {
  margin-top: 0 !important;
}
.rio-range {
  margin: 0.9rem 0 0 !important;
  color: #9a9a9a !important;
  font-size: 1.05rem !important;
  line-height: 1.4 !important;
  font-variant-numeric: tabular-nums;
}
.rio-error {
  margin: 0.85rem 0 0;
  color: #f0f0f0;
  font-size: 0.95rem;
}

[class*="st-key-rio-controls"] { margin: 0 0 2.6rem; }
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p {
  color: #8a8a8a !important;
  font-size: 0.75rem !important;
  font-weight: 400 !important;
}
[data-testid="stTextInputRootElement"],
[data-testid="stDateInputField"] {
  background: #1a1a1a !important;
  border: 1px solid #2a2a2a !important;
  border-radius: 8px !important;
  color: #f0f0f0 !important;
}
[data-testid="stTextInputField"] {
  color: #f0f0f0 !important;
  -webkit-text-fill-color: #f0f0f0 !important;
  background: transparent !important;
  caret-color: #f0f0f0 !important;
}
[data-testid="stDateInputField"] [role="spinbutton"],
[data-testid="stDateInputField"] span {
  color: #f0f0f0 !important;
}
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stDateInputField"]:focus-within {
  border-color: #4E6E4D !important;
  box-shadow: none !important;
}
[data-testid="stDateInput"] svg { fill: #8a8a8a !important; }
[data-testid="stDateInputField"] button {
  background: transparent !important;
  color: #8a8a8a !important;
  border: none !important;
}

[class*="st-key-rio-week"] {
  background: #1a1a1a !important;
  border: 1px solid #242424;
  border-radius: 16px;
  padding: 1.45rem 1.55rem 1.15rem !important;
  margin: 0 0 1.15rem !important;
}
.rio-week-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
}
.stMarkdown h2.rio-week-title,
h2.rio-week-title {
  margin: 0 !important;
  padding: 0 !important;
  color: #f0f0f0 !important;
  font-size: 1.28rem !important;
  font-weight: 500 !important;
  letter-spacing: -0.02em !important;
  line-height: 1.2 !important;
}
.rio-week-meta, .rio-applied {
  margin: 0 !important;
  color: #8a8a8a !important;
  font-size: 0.78rem !important;
  line-height: 1.3 !important;
  letter-spacing: 0.06em;
}
.rio-days { margin-top: 0.85rem; }
.rio-day {
  display: grid;
  grid-template-columns: 9.25rem minmax(0, 1fr) 8.5rem;
  column-gap: 1.35rem;
  align-items: start;
  padding: 0.95rem 0;
}
.rio-day + .rio-day { border-top: 1px solid #262626; }
.rio-dow {
  color: #f0f0f0;
  font-size: 0.98rem;
  font-weight: 500;
}
.rio-date {
  margin-top: 0.22rem;
  color: #8a8a8a;
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
}
.rio-name {
  color: #f0f0f0;
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.4;
  overflow-wrap: break-word;
}
.rio-target {
  margin-top: 0.28rem;
  color: #a3a3a3;
  font-size: 0.84rem;
  line-height: 1.45;
}
.rio-status {
  text-align: right;
  color: #6e6e6e;
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding-top: 0.22rem;
}
.rio-empty {
  margin: 0.9rem 0 0.2rem;
  color: #8a8a8a;
}
.rio-mark-label {
  margin: 0 !important;
  padding: 0.95rem 0 0.55rem !important;
  color: #6e6e6e !important;
  font-size: 0.68rem !important;
  line-height: 1.2 !important;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.rio-reason {
  margin: 0.22rem 0 !important;
  color: #7d7d7d !important;
  font-size: 0.78rem !important;
  line-height: 1.45 !important;
}
.rio-reason span {
  color: #a8a8a8;
  margin-right: 0.55rem;
}

[class*="st-key-rio-week"] [data-testid="stExpander"],
[class*="st-key-rio-week"] [data-testid="stExpander"] details {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
[class*="st-key-rio-week"] [data-testid="stExpander"] {
  margin-top: 0.35rem !important;
}
[class*="st-key-rio-week"] [data-testid="stExpander"] summary {
  background: transparent !important;
  color: #7a7a7a !important;
  font-size: 0.8rem !important;
  padding: 0.35rem 0 !important;
  border-radius: 0 !important;
}
[class*="st-key-rio-week"] [data-testid="stExpander"] summary:hover {
  background: transparent !important;
  color: #f0f0f0 !important;
}
[class*="st-key-rio-week"] [data-testid="stExpander"] svg {
  fill: #6a6a6a !important;
}
[class*="st-key-rio-week"] button {
  background: transparent !important;
  border: 1px solid #2c2c2c !important;
  border-radius: 8px !important;
  color: #cfcfcf !important;
  min-height: 2.15rem !important;
  padding: 0.35rem 0.7rem !important;
  font-size: 0.8rem !important;
  font-weight: 500 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-week"] button p { color: inherit !important; }
[class*="st-key-rio-week"] button[kind="primary"],
[class*="st-key-rio-week"] [data-testid="stBaseButton-primary"] {
  border-color: #4E6E4D !important;
  color: #d7e3d6 !important;
  background: transparent !important;
}
[class*="st-key-rio-week"] button[kind="secondary"]:hover,
[class*="st-key-rio-week"] [data-testid="stBaseButton-secondary"]:hover {
  border-color: #4E6E4D !important;
  color: #f0f0f0 !important;
  background: transparent !important;
}
[class*="st-key-rio-week"] button[kind="primary"]:hover,
[class*="st-key-rio-week"] [data-testid="stBaseButton-primary"]:hover {
  background: #4E6E4D !important;
  color: #f0f0f0 !important;
}
[class*="st-key-rio-week"] [data-testid="stHorizontalBlock"] {
  gap: 0.55rem !important;
}

.rio-card {
  background: #1a1a1a;
  border: 1px solid #242424;
  border-radius: 16px;
  padding: 1.35rem 1.55rem 1.15rem;
  margin: 0 0 1.15rem;
}
.rio-card > .rio-mark-label {
  padding: 0 0 0.45rem !important;
}
.rio-card .rio-fields + .rio-mark-label,
.rio-card .rio-table-wrap + .rio-mark-label,
.rio-card h2.rio-week-title + .rio-mark-label,
.rio-card .rio-prose + .rio-mark-label {
  padding-top: 1.05rem !important;
}
.rio-card h2.rio-week-title {
  margin: 0 0 0.95rem !important;
}
.rio-card .rio-empty {
  margin: 0.2rem 0 0.15rem;
}
.rio-fields { margin-top: 0.1rem; }
.rio-field {
  display: grid;
  grid-template-columns: 11.5rem minmax(0, 1fr);
  column-gap: 1.35rem;
  align-items: baseline;
  padding: 0.78rem 0;
}
.rio-field + .rio-field,
.rio-fields + .rio-fields > .rio-field:first-child { border-top: 1px solid #262626; }
.rio-k {
  color: #8a8a8a;
  font-size: 0.78rem;
  line-height: 1.35;
}
.rio-v {
  color: #f0f0f0;
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.rio-prose {
  margin: 0.35rem 0 0.15rem !important;
  padding-top: 0.95rem;
  border-top: 1px solid #262626;
  color: #e4e4e4 !important;
  font-size: 1.02rem !important;
  line-height: 1.6 !important;
}
.rio-table-wrap { overflow-x: auto; }
.rio-table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
}
.rio-table th {
  text-align: left;
  color: #6e6e6e;
  font-size: 0.72rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  padding: 0.15rem 0.7rem 0.55rem 0;
  border-bottom: 1px solid #262626;
  white-space: nowrap;
}
.rio-table td {
  color: #f0f0f0;
  font-size: 0.9rem;
  line-height: 1.4;
  padding: 0.72rem 0.7rem 0.72rem 0;
  border-bottom: 1px solid #262626;
  font-variant-numeric: tabular-nums;
  vertical-align: top;
  white-space: nowrap;
}
.rio-table tr:last-child td { border-bottom: none; }
.rio-table th:last-child,
.rio-table td:last-child { padding-right: 0; }

[data-testid="stSelectbox"] [role="group"] {
  background: #1a1a1a !important;
  border: 1px solid #2a2a2a !important;
  border-radius: 8px !important;
}
[data-testid="stSelectbox"] [role="group"]:focus-within {
  border-color: #4E6E4D !important;
  box-shadow: none !important;
}
[data-testid="stSelectbox"] input {
  background: transparent !important;
  color: #f0f0f0 !important;
  -webkit-text-fill-color: #f0f0f0 !important;
  border: none !important;
  box-shadow: none !important;
  caret-color: #f0f0f0 !important;
}
[data-testid="stSelectbox"] input:focus {
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
}
[data-testid="stSelectbox"] button {
  background: transparent !important;
  color: #8a8a8a !important;
  border: none !important;
  box-shadow: none !important;
}
[data-testid="stSelectbox"] svg { fill: #8a8a8a !important; }
[data-testid="stSelectboxVirtualDropdown"] {
  background: #1a1a1a !important;
  color: #f0f0f0 !important;
  border: 1px solid #2a2a2a !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"] {
  color: #f0f0f0 !important;
  background: transparent !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"],
[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover {
  background: #242424 !important;
  color: #d7e3d6 !important;
}

@media (max-width: 720px) {
  .rio-nav {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.85rem;
  }
  .rio-links { justify-content: flex-start; }
  .rio-hero h1,
  .stMarkdown .rio-hero h1 { font-size: 2.45rem !important; }
  .rio-day { grid-template-columns: 1fr; row-gap: 0.35rem; }
  .rio-status { text-align: left; padding-top: 0; }
  .rio-field { grid-template-columns: 1fr; row-gap: 0.22rem; padding: 0.7rem 0; }
}
</style>
"""


def _esc(value: object) -> str:
    return escape(str(value), quote=True)


def _plain(value: object) -> str:
    if isinstance(value, (list, tuple)):
        text = ", ".join(str(item).strip() for item in value if str(item).strip())
        return text or "—"
    if value is None:
        return "—"
    text = str(value).strip()
    return text or "—"


def _codes(codes: list) -> str:
    return ", ".join(str(code) for code in codes) if codes else "—"


def _fixture_banner(source: object) -> str | None:
    if str(source or "").strip().lower() == "fixture":
        return "FIXTURE"
    return None


def _page_hero(title: str, banner: str | None = None, subtitle: str | None = None) -> str:
    parts = ['<header class="rio-hero">']
    if banner:
        parts.append(f'<p class="rio-synthetic">{_esc(banner)}</p>')
    parts.append(f"<h1>{_esc(title)}</h1>")
    if subtitle:
        parts.append(f'<p class="rio-range">{_esc(subtitle)}</p>')
    parts.append("</header>")
    return "".join(parts)


def _open(page: str, *, controls: bool = False):
    st.markdown(_APP_CSS, unsafe_allow_html=True)
    st.markdown(_nav_html(page), unsafe_allow_html=True)
    hero = st.container(gap=None)
    box = st.container(key="rio-controls", gap="small") if controls else None
    return hero, box


def _card(*parts: str) -> None:
    st.markdown(f'<div class="rio-card">{"".join(parts)}</div>', unsafe_allow_html=True)


def _label(text: str) -> str:
    return f'<p class="rio-mark-label">{_esc(text)}</p>'


def _subject(label: str, value: object) -> str:
    return (
        f'<p class="rio-mark-label">{_esc(label)}</p>'
        f'<h2 class="rio-week-title">{_esc(_plain(value))}</h2>'
    )


def _fields(pairs: list[tuple[str, object]]) -> str:
    rows = []
    for label, value in pairs:
        rows.append(
            '<div class="rio-field">'
            f'<div class="rio-k">{_esc(label)}</div>'
            f'<div class="rio-v">{_esc(_plain(value))}</div>'
            "</div>"
        )
    return f'<div class="rio-fields">{"".join(rows)}</div>'


def _prose(text: str) -> str:
    return f'<p class="rio-prose">{_esc(text)}</p>'


def _table(rows: list[dict]) -> str:
    if not rows:
        return '<p class="rio-empty">—</p>'
    headers = list(rows[0].keys())
    head = "".join(f"<th>{_esc(header)}</th>" for header in headers)
    body = []
    for row in rows:
        cells = "".join(
            f"<td>{_esc('' if row.get(header) is None else row.get(header))}</td>"
            for header in headers
        )
        body.append(f"<tr>{cells}</tr>")
    return (
        '<div class="rio-table-wrap"><table class="rio-table"><thead><tr>'
        f"{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def _length_text(length: object) -> str:
    if isinstance(length, bool) or not isinstance(length, int):
        return "—"
    if length == 1:
        return "1 week"
    return f"{length} weeks"


def _status_label(codes: list) -> str:
    """One quiet word for a session, taken from reason codes already stored."""
    present = {str(code) for code in codes}
    for code, label in _STATUS_LABELS:
        if code in present:
            return label
    for code in codes:
        text = str(code)
        if len(text) == 7 and text.startswith("phase_") and text[6].isdigit():
            continue
        return text.replace("_", " ")
    return ""


def _nav_html(active: str) -> str:
    links = []
    for label, href in _NAV:
        on = label == active
        klass = "rio-link is-active" if on else "rio-link"
        current = ' aria-current="page"' if on else ""
        links.append(f'<a class="{klass}" href="{href}"{current}>{_esc(label)}</a>')
    return (
        '<nav class="rio-nav">'
        '<a class="rio-brand" href="/">RIO</a>'
        f'<div class="rio-links">{"".join(links)}</div>'
        "</nav>"
    )


def _hero_html(start: date, goal: date, plan: dict | None, error: str | None) -> str:
    synthetic = '<p class="rio-synthetic">SYNTHETIC / DEMO</p>'
    if error or plan is None:
        return (
            f'<header class="rio-hero">{synthetic}'
            "<h1>Season</h1>"
            f'<p class="rio-error">{_esc(error or "")}</p></header>'
        )
    return (
        f'<header class="rio-hero">{synthetic}'
        f"<h1>{_esc(_length_text(plan['season_length_weeks']))}</h1>"
        f'<p class="rio-range">{_esc(start.isoformat())} — {_esc(goal.isoformat())}</p>'
        "</header>"
    )


def _workout_text(template_id: object) -> str:
    """Plain description for a card. An unknown id stays as stored."""
    key = str(template_id or "").strip()
    if not key:
        return "—"
    return _WORKOUT_TEXT.get(key, key)


def _day_html(session: dict) -> str:
    status = _status_label(session["reason_codes"])
    status_html = f'<div class="rio-status">{_esc(status)}</div>' if status else ""
    return (
        '<div class="rio-day">'
        '<div class="rio-when">'
        f'<div class="rio-dow">{_esc(session["day_of_week"])}</div>'
        f'<div class="rio-date">{_esc(session["date"])}</div>'
        "</div>"
        '<div class="rio-work">'
        f'<div class="rio-name">{_esc(_workout_text(session["template_id"]))}</div>'
        f'<div class="rio-target">{_esc(session["target_outcome"])}</div>'
        "</div>"
        f"{status_html}"
        "</div>"
    )


def _render_mark(plan: dict, week_number: int, generation: int) -> None:
    """One mark for this week. A button calls adapt(); later weeks are what it returns."""
    applied = (st.session_state.get("season_marks") or {}).get(week_number)
    st.markdown('<p class="rio-mark-label">Mark</p>', unsafe_allow_html=True)
    columns = st.columns(3, gap="small")
    choice = None
    for column, mark in zip(columns, _MARKS):
        with column:
            if st.button(
                mark,
                key=f"season-mark-{generation}-{week_number}-{mark}",
                type="primary" if applied == mark else "secondary",
                width="stretch",
            ):
                choice = mark
    if choice is None:
        return
    try:
        updated = adapt(plan, week_number, choice)
    except ValueError as exc:
        st.markdown(
            f'<p class="rio-error">{_esc(exc)}</p>',
            unsafe_allow_html=True,
        )
        return
    marks = dict(st.session_state.get("season_marks") or {})
    marks[week_number] = choice
    st.session_state["season_marks"] = marks
    st.session_state["season_plan"] = updated
    st.rerun()


def _render_schedule(plan: dict, generation: int) -> None:
    length = plan["season_length_weeks"]
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        st.markdown('<p class="rio-empty">—</p>', unsafe_allow_html=True)
        return
    grouped = dict(_weeks(plan["sessions"]))
    marks = st.session_state.get("season_marks") or {}
    for number in range(1, length + 1):
        days = grouped.get(number, [])
        applied = marks.get(number)
        meta = f"Phase {_phase_number(days)}"
        if applied in _MARKS:
            meta = f"{meta} · {_esc(applied)}"
        with st.container(key=f"rio-week-{number}"):
            st.markdown(
                '<div class="rio-week-head">'
                f'<h2 class="rio-week-title">Week {number}</h2>'
                f'<p class="rio-week-meta">{meta}</p>'
                "</div>",
                unsafe_allow_html=True,
            )
            if not days:
                st.markdown('<p class="rio-empty">—</p>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="rio-days">{"".join(_day_html(session) for session in days)}</div>',
                    unsafe_allow_html=True,
                )
                with st.expander("Reason codes", key=f"season-reasons-{generation}-{number}"):
                    lines = []
                    for session in days:
                        lines.append(
                            '<p class="rio-reason">'
                            f'<span>{_esc(session["day_of_week"])} {_esc(session["date"])}</span>'
                            f'{_esc(_reason_text(session["reason_codes"]))}'
                            "</p>"
                        )
                    st.markdown("".join(lines), unsafe_allow_html=True)
            _render_mark(plan, number, generation)


def page_season() -> None:
    """The season sequence() returns from four inputs.

    Sessions are grouped by week and ordered Sunday through Saturday.
    Each row shows that day's calendar date. A mark calls adapt() for
    that week and shows the plan it returns.
    No recorded workouts.
    """
    chrome = st.container(gap=None)
    hero = st.container(gap=None)
    controls = st.container(key="rio-controls", gap="small")

    with chrome:
        st.markdown(_APP_CSS, unsafe_allow_html=True)
        st.markdown(_nav_html("Season"), unsafe_allow_html=True)

    with controls:
        current_col, start_col, goal_time_col, goal_date_col = st.columns(
            4, gap="medium", vertical_alignment="bottom"
        )
        with current_col:
            current_time = st.text_input("current_time", value="2:02.9")
        with start_col:
            start_date = st.date_input("start_date", value=date(2026, 4, 19))
        with goal_time_col:
            goal_time = st.text_input("goal_time", value="1:55.0")
        with goal_date_col:
            goal_date = st.date_input("goal_date", value=date(2027, 3, 19))

    inputs = (
        str(current_time).strip(),
        start_date.isoformat(),
        str(goal_time).strip(),
        goal_date.isoformat(),
    )
    try:
        plan = _season_plan(inputs, inputs[0], start_date, inputs[2], goal_date)
        error = None
    except ValueError as exc:
        plan = None
        error = str(exc)

    with hero:
        st.markdown(
            _hero_html(start_date, goal_date, plan, error),
            unsafe_allow_html=True,
        )
    if plan is None:
        return
    _render_schedule(plan, int(st.session_state.get("season_generation") or 0))


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
