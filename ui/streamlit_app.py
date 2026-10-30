# streamlit_app.py — Start, Dashboard, Calendar, Library, Last Session, Activity, Next, Decisions, Ledger, Goal, Progress, Season, Past seasons, Weekly, Profile, Settings, About, and Session. Display only. No classification rules.

"""Start asks for four inputs and calls sequence(). Generate season writes current_time, start_date, goal_time, and goal_date into the URL. Marks and actuals are saved in this browser's localStorage under those inputs. A page opened with the four inputs calls sequence() to rebuild the plan and restores marks and actuals from localStorage when this browser has them. Dashboard reads that plan: the next workout, the days until the goal, the current phase, the last mark, and one line for this week. Calendar shows that plan as a month. A session day carries a short label, and the day opens that session. Library lists the frozen menu. Last Session reads normalize, classify, and explain. Choosing a JSON file in tests/fixtures/intervals reads that file locally, runs to_normalize_input, then normalize, classify, and explain. The page does not call Intervals.icu. Activity lists one row per matched Intervals workout: the date, the template or label, completed work meters, and average heart rate. The line is weekly completed WORK distance. Warm-up, cool-down, and template meters stay out. A dot marks each matched workout that has an average heart rate, labeled with the date. An unmatched activity stays off that matched list. A matched activity with no work meters and no heart rate stays off it. A second table lists every activity: the date, the activity name, the activity distance, and average heart rate. An unmatched row is labeled extra. An activity with no distance and no heart rate stays off both lists. No stored match and no Intervals file leaves the matched list empty. That page does not call explain. Next reads prescribe and explain. Decisions reads one planned row and explain. Ledger and Goal read the ledger. Progress lists that plan by week and shows each week's completed work distance from WORK intervals in a loaded Intervals file. Warm-up and cool-down stay out. A day with no file contributes 0. A week with no file shows 0 m. A line on Progress plots that same weekly distance, and a week with no file stays at 0. Dots on Progress mark each matched activity that has an average heart rate, labeled with the day and the value. A day with no heart rate is left blank. Template meters are not used. Season shows that plan and reads adapt. Weekly shows one week of that plan, a recap of what was recorded, and reads adapt. Opening Dashboard, Weekly, Session, Progress, or Activity reads the last 14 days of activities with the local key and matches each activity to the planned session on that date. Refresh on Activity reads every activity for this athlete. A matched Tuesday or Thursday quality day with no stored mark is judged from that activity's WORK elapsed times. The mark and those times are stored with the session, and adapt() changes only later weeks. Those times fill the quality-day boxes and stay editable. A day that already has a mark is left as stored. Recovery days, long runs, extra activities, and empty rep times do not call adapt(). A matched day uses that activity for rep times, WORK distance, and average heart rate. An activity with no planned session is an extra session. The matches are saved in this browser with the marks and actuals. Another athlete opening the link uses the key on their own machine. The recap volume sums those WORK distances for this week and the week before. A day with no file contributes 0. A week with no file shows 0 m. Template meters are not used. Settings stores display preferences for this session. Profile shows the current 800 time, the start date, the goal 800 time, and the goal date already stored from Start. Saving a goal time keeps it in this browser and leaves the season as stored. Past seasons lists each season this browser has already stored. A row shows the start date, the goal date, and the goal time from that plan key. Choosing a row opens that season from those four inputs. The page does not build a season. Session shows one day of that plan. A matched activity shows its rep times, completed WORK distance, and average heart rate beside the template. Tuesday and Thursday quality take one time per rep and call adapt. Choosing an Intervals JSON file reads it locally and fills each rep box with that WORK interval's elapsed time. The numbers stay editable. Filled times go through judge() and can call adapt(). The activity id or the filename is stored with the actuals. Opening Session reads recent activities through the read-only adapter and does not write back to Intervals. When that activity JSON has an average heart rate, the page shows it. A continuous session takes one time. About states the eight phases, the 10% rule, that classification is rules, not AI, and that a hard-day mark adapts later weeks. About does not call a model. No scores. No spend."""

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
from engines.prescribe import PARAMETER_KEYS, load_menu, prescribe
from engines.season import adapt, sequence
from ui.about import about_sections
from ui.calendar import month_title, month_weeks, opening_month, plan_months
from ui.library import filter_workouts, library_rows
from ui.activities import (
    PullError,
    activity_by_id,
    activity_window,
    extras_between,
    matched_on,
    meters_text,
    sync_all,
    sync_recent,
    weekday_name,
    with_matched_distances,
)
from ui.activity_data import (
    activity_banner,
    all_activities,
    file_heart_rates,
    heart_rate_points,
    session_rows,
    weekly_completed_meters,
)
from ui.auto_adapt import auto_adapt
from ui.last_session import (
    IntervalsFileError,
    activity_by_ref,
    file_just_opened,
    fit_slots,
    heart_rate_text,
    intervals_json_paths,
    loaded_distances,
    open_intervals,
    quality_fill,
)
from ui.dashboard import dashboard_view
from ui.recap import recap_view
from ui.settings import (
    display_distance,
    distance_heading,
    distance_number,
    format_date,
    normalize as normalize_prefs,
)
from ui.plan_store import (
    dump_record,
    inputs_ok,
    load_record,
    plan_inputs,
    query_values,
    storage_key,
)
from ui.past_seasons import KEY_PREFIX, entry_fields, season_entries
from ui.profile import (
    clean_goal,
    dump_goal,
    load_goal,
    profile_fields,
    profile_key,
    shown_goal,
)
from ui.progress import (
    days_label,
    days_remaining,
    heart_rate_chart,
    matched_heart_rates,
    progress_weeks,
    volume_chart,
)
from ui.result import filled_times, goal_seconds, judge, result_box_count

FIXTURES_DIR = ROOT / "tests" / "fixtures"

GOAL_FIELDS = (
    "current_mark",
    "target_time",
    "target_date",
    "limiting_capacities",
)


def _payload_date(payload: dict) -> str:
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


def _lap_rows(laps: list[dict], units: str) -> list[dict]:
    amounts = [lap.get("distance_m") for lap in laps]
    heading = distance_heading(units, amounts)
    rows: list[dict] = []
    for index, lap in enumerate(laps, start=1):
        rows.append(
            {
                "Lap": index,
                heading: distance_number(lap.get("distance_m"), units, amounts),
                "Seconds": _cell(lap.get("seconds")),
                "Rest (s)": _cell(lap.get("rest_s")),
            }
        )
    return rows


def _empty_lap_table(units: str) -> str:
    """Headers and no rows. A missing laps list uses this instead of crashing."""
    heads = ("Lap", distance_heading(units), "Seconds", "Rest (s)")
    head = "".join(f"<th>{_esc(name)}</th>" for name in heads)
    return (
        '<div class="rio-table-wrap"><table class="rio-table"><thead><tr>'
        f"{head}</tr></thead><tbody></tbody></table></div>"
    )


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
    normalized = normalize(payload)
    found = normalized.get("laps") if isinstance(normalized, dict) else None
    laps = found if isinstance(found, list) else []
    units = _prefs()["units"]
    rows = _lap_rows(laps, units)
    result = classify(payload)
    codes = result.get("reason_codes") or []
    when = _payload_date(payload)
    _card(_label("Laps"), _table(rows) if rows else _empty_lap_table(units))
    _card(
        _fields(
            [
                ("Date", _date_text(when) if when else "—"),
                ("Family", result["family"]),
                ("Confidence", result["confidence"]),
                ("Reason codes", _codes(codes)),
            ]
        ),
        _prose(_copy(explain(result))),
    )


def selected_fixture_path() -> Path | None:
    paths = fixture_paths(FIXTURES_DIR)
    if not paths:
        return None
    names = [path.stem for path in paths]
    selected = st.selectbox("Session", names)
    return paths[names.index(selected)]


def _selected_intervals_path(paths: list[Path], *, optional: bool) -> Path | None:
    """One JSON file from tests/fixtures/intervals. Blank keeps the fixture."""
    names = [path.name for path in paths]
    if optional:
        labels = ["—", *names]
        selected = st.selectbox("Intervals file", labels, key="last-session-intervals")
        if selected == "—":
            return None
        return paths[names.index(selected)]
    selected = st.selectbox("Intervals file", names, key="last-session-intervals")
    return paths[names.index(selected)]


def _show_intervals_file(hero, path: Path) -> None:
    """to_normalize_input, then the same normalize, classify, and explain fields."""
    try:
        payload, banner = open_intervals(path)
    except IntervalsFileError as exc:
        with hero:
            st.markdown(_page_hero("Last Session"), unsafe_allow_html=True)
        st.markdown(f'<p class="rio-empty">{_esc(str(exc))}</p>', unsafe_allow_html=True)
        return
    with hero:
        st.markdown(_page_hero("Last Session", banner), unsafe_allow_html=True)
    render_session(payload)


def page_last_session() -> None:
    """The fixture drop-down, or one local Intervals JSON file.

    A chosen JSON file is read from disk. Prose spend stays capped at $25
    in explain. This page does not call Intervals.icu.
    """
    paths = fixture_paths(FIXTURES_DIR)
    interval_paths = intervals_json_paths()
    hero, controls = _open("Last Session", controls=bool(paths or interval_paths))
    if not paths and not interval_paths:
        with hero:
            st.markdown(_page_hero("Last Session"), unsafe_allow_html=True)
        st.markdown('<p class="rio-empty">No session files.</p>', unsafe_allow_html=True)
        return
    with controls:
        path = selected_fixture_path() if paths else None
        interval_path = (
            _selected_intervals_path(interval_paths, optional=bool(paths))
            if interval_paths
            else None
        )
    if interval_path is not None:
        _show_intervals_file(hero, interval_path)
        return
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
            _page_hero("Ledger", banner, f"As of {_date_text(today)}"),
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


def _plain_reason(code: object) -> str:
    text = str(code).strip()
    if not text:
        return ""
    known = _REASON_PLAIN.get(text)
    if known:
        return known
    if len(text) == 7 and text.startswith("phase_") and text[6].isdigit():
        return f"Phase {text[6]}"
    return text.replace("_", " ")


def _plain_reasons(codes: list) -> str:
    lines = []
    for code in codes or []:
        words = _plain_reason(code)
        if words:
            lines.append(f'<p class="rio-reason">{_esc(words)}</p>')
    if not lines:
        return '<p class="rio-empty">—</p>'
    return f'<div class="rio-reasons">{"".join(lines)}</div>'


def _menu_by_id() -> dict[str, dict]:
    """Frozen template recipes. Read for the structure sentence. Not a new plan."""
    global _MENU_BY_ID
    if _MENU_BY_ID is None:
        _MENU_BY_ID = {row["id"]: row for row in load_menu()}
    return _MENU_BY_ID


def _structure_text(template_id: object) -> str:
    """The recipe's plain structure: reps, rest, and distance, as written."""
    key = str(template_id or "").strip()
    row = _menu_by_id().get(key) if key else None
    if isinstance(row, dict):
        text = str(row.get("default_structure") or "").strip()
        if text:
            return _copy(text)
    return _copy(_workout_text(template_id))


def _query_text(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _query_date() -> str | None:
    return _query_text("date")


def _query_activity() -> str | None:
    return _query_text("activity")


def _session_on(plan: dict, day: str | None) -> dict | None:
    """The stored session for this calendar date. Dates are unique in the plan."""
    if not day:
        return None
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        return None
    for session in sessions:
        if isinstance(session, dict) and str(session.get("date")) == day:
            return session
    return None


# Reads and writes this browser's marks and actuals. The four inputs stay in the URL.
_PLAN_STORE_JS = """
export default function (component) {
  var data = component.data;
  if (!data || typeof data.key !== "string" || !data.key) {
    return;
  }
  var key = data.key;
  if (data.mode === "write" && typeof data.payload === "string") {
    try {
      if (window.localStorage.getItem(key) !== data.payload) {
        window.localStorage.setItem(key, data.payload);
      }
    } catch (err) {}
  }
  var body = "";
  try {
    var stored = window.localStorage.getItem(key);
    body = stored === null ? "" : String(stored);
  } catch (err) {
    body = "";
  }
  var token = key + "\\n" + body;
  if (window.__rioPlanStoreToken === token) {
    return;
  }
  window.__rioPlanStoreToken = token;
  component.setStateValue("record", { key: key, body: body });
}
"""


def _plan_component():
    """The browser bridge. Registered once per process, mounted on each run."""
    import ui.plan_store as plan_store

    cached = getattr(plan_store, "_browser_component", None)
    if cached is None:
        cached = st.components.v2.component(
            "rio_plan_store",
            js=_PLAN_STORE_JS,
            isolate_styles=False,
        )
        plan_store._browser_component = cached
    return cached


def _mount_store(data: dict, *, widget_key: str = "rio-plan-store"):
    """Mount the browser bridge. Read and write use different keys in one run."""
    return _plan_component()(
        key=widget_key,
        data=data,
        width="content",
        height="content",
    )


def _publish_inputs(inputs: tuple[str, str, str, str]) -> None:
    """Put the four inputs in the URL. Leave a session date where it is."""
    wanted = query_values(inputs)
    current = {key: str(st.query_params.get(key) or "") for key in wanted}
    if current == wanted:
        return
    st.query_params.update(wanted)


def _link_params(extra: dict | None = None) -> dict[str, str] | None:
    """Page links keep the four inputs. Streamlit clears them otherwise."""
    params: dict[str, str] = {}
    inputs = st.session_state.get("season_inputs")
    if inputs_ok(inputs) and isinstance(st.session_state.get("season_plan"), dict):
        params.update(query_values(inputs))
    if extra:
        for key, value in extra.items():
            text = "" if value is None else str(value).strip()
            if text:
                params[key] = text
    return params or None


def _inputs_from_form(current_time, start_date, goal_time, goal_date) -> tuple[str, str, str, str]:
    current = str(current_time).strip()
    goal_mark = str(goal_time).strip()
    start = start_date.isoformat() if isinstance(start_date, date) else str(start_date).strip()
    goal_day = goal_date.isoformat() if isinstance(goal_date, date) else str(goal_date).strip()
    return (current, start, goal_mark, goal_day)


def _clear_activity_pull() -> None:
    """Drop pulled activities when the plan identity changes."""
    st.session_state["season_activities"] = []
    st.session_state.pop("activities_trigger", None)
    st.session_state.pop("activities_loaded", None)
    st.session_state.pop("activities_notice", None)


def _store_plan(inputs: tuple[str, str, str, str], plan: dict, *, loaded: bool) -> None:
    """A new plan identity. loaded means this browser's record was already applied."""
    st.session_state["season_inputs"] = inputs
    st.session_state["season_plan"] = plan
    st.session_state["season_marks"] = {}
    st.session_state["season_actuals"] = {}
    st.session_state["season_quality_base"] = {}
    st.session_state["season_generation"] = int(st.session_state.get("season_generation") or 0) + 1
    st.session_state["rio_store_loaded"] = loaded
    st.session_state.pop("season_link_error", None)
    st.session_state.pop("season_link_attempt", None)
    st.session_state.pop("rio_adapt_pending", None)
    _clear_activity_pull()
    _publish_inputs(inputs)


def _reject_link(inputs: tuple[str, str, str, str], message: str) -> None:
    """The URL names a plan sequence() will not build. The old browser record stays."""
    st.session_state["season_link_attempt"] = inputs
    st.session_state["season_link_error"] = message
    st.session_state["season_inputs"] = inputs
    st.session_state["season_plan"] = None
    st.session_state["season_marks"] = {}
    st.session_state["season_actuals"] = {}
    st.session_state["season_quality_base"] = {}
    st.session_state["rio_store_loaded"] = True
    st.session_state.pop("rio_adapt_pending", None)
    _clear_activity_pull()


def _generate_season(current_time, start_date, goal_time, goal_date) -> dict:
    """sequence() for a submitted start. Replaces any plan adapt() has changed."""
    inputs = _inputs_from_form(current_time, start_date, goal_time, goal_date)
    plan = sequence(*inputs)
    _store_plan(inputs, plan, loaded=True)
    return plan


def _ensure_linked_plan(inputs: tuple[str, str, str, str]) -> None:
    """Page load with these four inputs rebuilds the plan through sequence()."""
    current = st.session_state.get("season_inputs")
    plan = st.session_state.get("season_plan")
    if current == inputs and isinstance(plan, dict):
        _publish_inputs(inputs)
        return
    if (
        st.session_state.get("season_link_attempt") == inputs
        and st.session_state.get("season_link_error")
        and not isinstance(plan, dict)
    ):
        return
    try:
        built = sequence(*inputs)
    except ValueError as exc:
        _reject_link(inputs, str(exc))
        return
    _store_plan(inputs, built, loaded=False)


def _restore_record(key: str) -> None:
    """Read this browser's marks and actuals once, before an empty plan is drawn."""
    result = _mount_store({"key": key, "mode": "read"})
    record = getattr(result, "record", None)
    if (
        not isinstance(record, dict)
        or record.get("key") != key
        or not isinstance(record.get("body"), str)
    ):
        st.stop()
    marks, actuals, activities = load_record(record["body"])
    st.session_state["season_marks"] = marks
    st.session_state["season_actuals"] = actuals
    st.session_state["season_activities"] = activities
    st.session_state["rio_store_loaded"] = True


def _sync_browser_store() -> None:
    """Save marks and actuals under the four inputs. Each browser has its own."""
    inputs = st.session_state.get("season_inputs")
    plan = st.session_state.get("season_plan")
    if not inputs_ok(inputs) or not isinstance(plan, dict):
        return
    key = storage_key(inputs)
    if not st.session_state.get("rio_store_loaded"):
        _restore_record(key)
        return
    _mount_store(
        {
            "key": key,
            "mode": "write",
            "payload": dump_record(
                st.session_state.get("season_marks"),
                st.session_state.get("season_actuals"),
                st.session_state.get("season_activities"),
            ),
        },
        widget_key="rio-plan-store-write",
    )


def _load_shared_plan() -> None:
    """URL inputs rebuild the plan. A visit that already has it keeps that plan.

    The browser record is restored here. The write happens after a pull so a
    match from this run is what gets saved.
    """
    found = plan_inputs(st.query_params)
    if found is None:
        inputs = st.session_state.get("season_inputs")
        if inputs_ok(inputs) and isinstance(st.session_state.get("season_plan"), dict):
            _publish_inputs(inputs)
    else:
        _ensure_linked_plan(found)
    _restore_if_needed()


def _restore_if_needed() -> None:
    """Read this browser's record once, before a pull replaces the window."""
    inputs = st.session_state.get("season_inputs")
    plan = st.session_state.get("season_plan")
    if not inputs_ok(inputs) or not isinstance(plan, dict):
        return
    if st.session_state.get("rio_store_loaded"):
        return
    _restore_record(storage_key(inputs))


# Dashboard, Weekly, Session, Progress, and Activity read the last 14
# days when they are opened. Refresh on Activity reads every activity.
# Any other first page is the app load and does not judge a mark. The names
# are the page functions _with_plan wraps.
_PULL_PAGES = (
    "page_dashboard",
    "page_plan",
    "page_weekly",
    "page_session",
    "page_progress",
    "page_activity",
)


def _pull_for(page_name: str) -> None:
    """Those pages match the last 14 days and judge an unmarked quality day.

    Opening Dashboard, Weekly, Session, Progress, or Activity reads the
    last 14 days through the existing adapter. Refresh on Activity reads
    every activity. A matched Tuesday or Thursday with no mark is judged from
    its WORK times, and adapt() changes only later weeks. A day that already
    has a mark is left as stored. A failure keeps the stored matches. The key
    stays in the environment. Nothing is written to Intervals.
    """
    plan = st.session_state.get("season_plan")
    if not isinstance(plan, dict):
        return
    refresh = page_name == "page_activity" and st.session_state.get("activity-refresh") is True
    opened = page_name in _PULL_PAGES
    if not refresh and not opened and st.session_state.get("activities_loaded"):
        return
    trigger = page_name if opened else "load"
    if not refresh and st.session_state.get("activities_trigger") == trigger:
        return
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    try:
        if refresh:
            updated = sync_all(
                sessions,
                st.session_state.get("season_activities"),
                date.today(),
            )
        else:
            updated = sync_recent(
                sessions,
                st.session_state.get("season_activities"),
                date.today(),
            )
    except PullError as exc:
        st.session_state["activities_notice"] = str(exc)
    else:
        st.session_state["season_activities"] = updated
        st.session_state.pop("activities_notice", None)
        if opened:
            _apply_activity_marks(plan)
    st.session_state["activities_trigger"] = trigger
    st.session_state["activities_loaded"] = True


def _with_plan(page):
    """Draw the page after the shared plan is in the session.

    Dashboard, Weekly, Session, Progress, and Activity read the last 14
    days when they are opened, then judge an unmarked quality day. Refresh
    on Activity reads every activity and judges the same way. The write
    saves the matches with the marks.
    """

    def wrapped() -> None:
        _load_shared_plan()
        _pull_for(page.__name__)
        _sync_browser_store()
        page()

    wrapped.__name__ = page.__name__
    return wrapped


def _seed_start_form() -> None:
    """Show the linked inputs. A value the user already edited stays."""
    inputs = st.session_state.get("season_inputs")
    if not inputs_ok(inputs):
        return
    current, start, goal, goal_day = inputs
    if "start_current_time" not in st.session_state:
        st.session_state["start_current_time"] = current
    if "start_goal_time" not in st.session_state:
        st.session_state["start_goal_time"] = goal
    if "start_start_date" not in st.session_state:
        st.session_state["start_start_date"] = date.fromisoformat(start)
    if "start_goal_date" not in st.session_state:
        st.session_state["start_goal_date"] = date.fromisoformat(goal_day)


def _fresh_value(key: str, default):
    if key in st.session_state:
        return {}
    return {"value": default}


def _stored_season() -> tuple[dict | None, date | None, date | None, str | None]:
    """The plan Start stored, plus the two dates the hero prints."""
    plan = st.session_state.get("season_plan")
    inputs = st.session_state.get("season_inputs")
    if not isinstance(plan, dict) or not inputs_ok(inputs):
        message = st.session_state.get("season_link_error")
        if isinstance(message, str) and message.strip():
            return None, None, None, message.strip()
        return None, None, None, None
    start = date.fromisoformat(inputs[1])
    goal = date.fromisoformat(inputs[3])
    return plan, start, goal, None


def _nav_page(label: str):
    for name, page in _NAV_PAGES:
        if name == label:
            return page
    return None


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

# Plain words for season reason codes already stored on the session.
_REASON_PLAIN = {
    "phase_1": "Phase 1",
    "phase_2": "Phase 2",
    "phase_3": "Phase 3",
    "phase_4": "Phase 4",
    "phase_5": "Phase 5",
    "phase_6": "Phase 6",
    "phase_7": "Phase 7",
    "phase_8": "Phase 8",
    "phase_primary": "Primary work for this phase",
    "phase_secondary": "Secondary work for this phase",
    "weekly_aerobic_long_run": "The weekly long run",
    "priority_speed_endurance": "Speed endurance is a priority",
    "priority_aerobic_power": "Aerobic power is a priority",
    "priority_anaerobic_capacity": "Anaerobic capacity is a priority",
    "capacity_weight": "The higher capacity weight won",
    "ten_percent_hold": "Held so the week does not rise more than 10%",
    "ten_percent_easier_template": "An easier session, so the week stays within 10%",
    "extra_easy_day": "An extra easy day",
    "extra_easy_week": "An easy week",
    "harder_template": "A harder session",
    "moved_back_one_phase": "Moved back one phase",
    "advanced_one_phase": "Advanced one phase",
    "phase_8_freshness": "The taper stays fresh",
    "phase_8_no_hard_se_or_an": "No hard speed endurance or anaerobic work",
}

_MENU_BY_ID: dict[str, dict] | None = None

# Filled after the pages exist, before navigation runs.
_HOME_PAGE: st.Page | None = None
_SESSION_PAGE: st.Page | None = None
_NAV_PAGES: list[tuple[str, st.Page]] = []
_MORE_PAGES: list[tuple[str, st.Page]] = []
_EMBEDDING = False
_MARK_PREFIX = "season"

_APP_CSS = """
<style>
::selection { background: #2a4a3a; color: #f4f4f4; }
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"],
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {
  background: #000000 !important;
  color: #f4f4f4 !important;
}
html { color-scheme: dark; }
.stApp, .stApp button, .stApp input, .stApp label, .stApp summary, .stApp p,
.stMarkdown, .stMarkdown h1, .stMarkdown h2, .stMarkdown a, .stMarkdown p, .stMarkdown div,
[class*="st-key-rio-nav"], [class*="st-key-rio-nav"] a, .rio-hero, .rio-hero h1, .rio-week-title, .rio-day, .rio-day div,
.rio-card, .rio-card h2, .rio-table, .rio-table th, .rio-table td,
.rio-progress, .rio-progress div {
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
  max-width: 960px !important;
  padding: 0.4rem 1.7rem 5.5rem !important;
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

[class*="st-key-rio-nav"] {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 1.5rem !important;
  padding: 1.35rem 0 1rem !important;
  border-bottom: 1px solid #1a1a1a !important;
  position: sticky;
  top: 0;
  z-index: 30;
  background: #000000 !important;
  width: 100% !important;
  overflow: visible !important;
  flex-wrap: wrap !important;
}
[class*="st-key-rio-nav"] > [data-testid="stElementContainer"]:first-child,
[class*="st-key-rio-nav"] > [data-testid="stLayoutWrapper"]:first-child {
  flex: 0 0 auto !important;
  width: auto !important;
  height: auto !important;
  min-width: 0 !important;
  min-height: 0 !important;
}
[class*="st-key-rio-nav"] > [data-testid="stElementContainer"]:last-child,
[class*="st-key-rio-nav"] > [data-testid="stLayoutWrapper"]:last-child {
  flex: 1 1 auto !important;
  width: auto !important;
  height: auto !important;
  min-width: 0 !important;
  min-height: 0 !important;
}
[class*="st-key-rio-links"] {
  justify-content: flex-end !important;
  align-items: center !important;
  align-content: flex-start !important;
  gap: 0.35rem 1.15rem !important;
  flex-wrap: wrap !important;
  height: auto !important;
  min-height: 0 !important;
}
[class*="st-key-rio-links"] > [data-testid="stElementContainer"],
[class*="st-key-rio-links"] > [data-testid="stLayoutWrapper"],
[class*="st-key-rio-brand"],
[class*="st-key-rio-tab-"] {
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
}
[class*="st-key-rio-nav"] [data-testid="stPageLink"],
[class*="st-key-rio-nav"] [data-testid="stPageLink"] > div,
[class*="st-key-rio-nav"] [data-testid="stPageLink"] > div > div,
[class*="st-key-rio-nav"] [data-testid="stMarkdownContainer"] {
  width: auto !important;
  min-width: 0 !important;
  background: transparent !important;
}
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"] {
  width: auto !important;
  display: inline-flex !important;
  align-items: center !important;
  background: transparent !important;
  border-radius: 0 !important;
  padding: 0.15rem 0 0.28rem !important;
  margin: 0 !important;
  gap: 0 !important;
  border-bottom: 2px solid transparent !important;
  color: #8f8f8f !important;
  text-decoration: none !important;
  line-height: 1.3 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"] p {
  color: #8f8f8f !important;
  font-size: 0.84rem !important;
  font-weight: 400 !important;
  letter-spacing: 0 !important;
  line-height: 1.3 !important;
  margin: 0 !important;
  padding: 0 !important;
  display: inline !important;
  width: auto !important;
  background: transparent !important;
  overflow: visible !important;
  text-overflow: unset !important;
  white-space: nowrap !important;
}
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"]:hover,
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"]:hover span,
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"]:hover p {
  color: #f4f4f4 !important;
  background: transparent !important;
}
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] {
  border-bottom-color: #4a8c6a !important;
}
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"],
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] p {
  color: #f4f4f4 !important;
}
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"] {
  border-bottom-color: transparent !important;
  padding: 0.15rem 0 !important;
}
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"],
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"] p,
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"]:hover,
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"]:hover span,
[class*="st-key-rio-brand"] [data-testid="stPageLink-NavLink"]:hover p {
  color: #f4f4f4 !important;
  font-weight: 600 !important;
  letter-spacing: 0.2em !important;
  font-size: 0.92rem !important;
  background: transparent !important;
}
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"]:focus-visible,
button:focus-visible {
  outline: 1px solid #6db892;
  outline-offset: 3px;
}

.rio-hero { padding: 3.1rem 0 2.1rem; }
.rio-synthetic {
  margin: 0 !important;
  color: #8f8f8f !important;
  font-size: 0.68rem !important;
  line-height: 1.3 !important;
  letter-spacing: 0.16em;
  font-weight: 500;
}
.rio-hero h1,
.stMarkdown .rio-hero h1 {
  margin: 0.7rem 0 0 !important;
  padding: 0 !important;
  color: #f4f4f4 !important;
  font-size: 3.35rem !important;
  font-weight: 500 !important;
  letter-spacing: -0.04em !important;
  line-height: 1.02 !important;
}
.rio-hero h1:first-child,
.stMarkdown .rio-hero h1:first-child {
  margin-top: 0 !important;
}

.rio-hero h1.rio-key,
.stMarkdown .rio-hero h1.rio-key {
  color: #6db892 !important;
}
.rio-range {
  margin: 0.9rem 0 0 !important;
  color: #d4d4d4 !important;
  font-size: 1.05rem !important;
  line-height: 1.4 !important;
  font-variant-numeric: tabular-nums;
}
.rio-error {
  margin: 0.85rem 0 0;
  color: #f4f4f4;
  font-size: 0.95rem;
}

[class*="st-key-rio-controls"] { margin: 0 0 2.6rem; }
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p {
  color: #d4d4d4 !important;
  font-size: 0.75rem !important;
  font-weight: 400 !important;
}
[data-testid="stTextInputRootElement"],
[data-testid="stDateInputField"] {
  background: #14241c !important;
  border: 1px solid #24382e !important;
  border-radius: 8px !important;
  color: #f4f4f4 !important;
}
[data-testid="stTextInputField"] {
  color: #f4f4f4 !important;
  -webkit-text-fill-color: #f4f4f4 !important;
  background: transparent !important;
  caret-color: #f4f4f4 !important;
}
[data-testid="stTextInputField"]::placeholder {
  color: #8f8f8f !important;
  -webkit-text-fill-color: #8f8f8f !important;
  opacity: 1 !important;
}
[data-testid="stDateInputField"] [role="spinbutton"],
[data-testid="stDateInputField"] span {
  color: #f4f4f4 !important;
}
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stDateInputField"]:focus-within {
  border-color: #6db892 !important;
  box-shadow: none !important;
}
[data-testid="stDateInput"] svg { fill: #d4d4d4 !important; }
[data-testid="stDateInputField"] button {
  background: transparent !important;
  color: #d4d4d4 !important;
  border: none !important;
}

[class*="st-key-rio-week"] {
  background: #14241c !important;
  border: 1px solid #24382e;
  border-radius: 16px;
  padding: 1.45rem 1.55rem 1.15rem !important;
  margin: 0 0 1.65rem !important;
}
.rio-week-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
  padding-bottom: 0.15rem;
}
.stMarkdown h2.rio-week-title,
h2.rio-week-title {
  margin: 0 !important;
  padding: 0 !important;
  color: #f4f4f4 !important;
  font-size: 1.28rem !important;
  font-weight: 500 !important;
  letter-spacing: -0.02em !important;
  line-height: 1.2 !important;
}
.rio-week-head h2.rio-week-title,
.stMarkdown .rio-week-head h2.rio-week-title {
  display: flex !important;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 0.7rem;
  font-size: 1.42rem !important;
}
.rio-week-sep {
  color: #d4d4d4 !important;
  font-weight: 400 !important;
  margin-left: 0.7rem !important;
  margin-right: 0.7rem !important;
}
.rio-week-phase {
  color: #d4d4d4 !important;
  font-size: 1.08rem !important;
  font-weight: 500 !important;
  letter-spacing: -0.01em !important;
}
.rio-week-meta, .rio-applied {
  margin: 0 !important;
  color: #d4d4d4 !important;
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
.rio-day + .rio-day,
.rio-day-next { border-top: 1px solid #24382e; }
.rio-dow {
  color: #f4f4f4;
  font-size: 0.98rem;
  font-weight: 500;
}
.rio-date {
  margin-top: 0.22rem;
  color: #d4d4d4;
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
}
.rio-name {
  color: #f4f4f4;
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.4;
  overflow-wrap: break-word;
}
.rio-target {
  margin-top: 0.28rem;
  color: #d4d4d4;
  font-size: 0.84rem;
  line-height: 1.45;
}
.rio-hero-week { padding-bottom: 1.15rem; }
[class*="st-key-rio-pick"] {
  max-width: 24rem;
  margin: 0 0 1.85rem !important;
}
.rio-daycard {
  background: #14241c;
  border: 1px solid #24382e;
  border-radius: 16px;
  padding: 1.7rem 1.75rem 1.5rem;
  margin: 0 0 0.95rem;
}
.rio-daycard-dow,
.rio-daycard-date,
.rio-daycard-work,
.rio-daycard-target {
  margin: 0;
}
.rio-daycard-dow {
  color: #f4f4f4;
  font-size: 1.5rem;
  font-weight: 500;
  letter-spacing: -0.03em;
  line-height: 1.15;
}
.rio-daycard-date {
  margin-top: 0.4rem;
  color: #d4d4d4;
  font-size: 0.92rem;
  font-variant-numeric: tabular-nums;
}
.rio-daycard-work {
  margin-top: 1.35rem;
  color: #f4f4f4;
  font-size: 1.22rem;
  font-weight: 500;
  line-height: 1.4;
  overflow-wrap: break-word;
}
.rio-daycard-target {
  margin-top: 0.95rem;
  padding-top: 0.9rem;
  border-top: 1px solid #24382e;
  color: #d4d4d4;
  font-size: 0.95rem;
  line-height: 1.5;
}
.rio-daycard-actual {
  margin-top: 0.75rem;
  color: #f4f4f4;
  font-size: 0.92rem;
  font-variant-numeric: tabular-nums;
  line-height: 1.45;
}
.rio-hero .rio-mark-label {
  margin: 0.95rem 0 0 !important;
  padding: 0 !important;
}
.rio-next-work {
  margin: 1.45rem 0 0 !important;
  max-width: 38rem;
  color: #f4f4f4 !important;
  font-size: 1.48rem !important;
  font-weight: 500 !important;
  line-height: 1.4 !important;
  letter-spacing: -0.02em;
}
[class*="st-key-rio-cal"] {
  margin: 0.2rem 0 0 !important;
}
[class*="st-key-rio-cal-head"],
[class*="st-key-rio-cal-week"] {
  margin: 0 0 0.35rem !important;
}
[class*="st-key-rio-cal-head"] [data-testid="stHorizontalBlock"],
[class*="st-key-rio-cal-week"] [data-testid="stHorizontalBlock"] {
  gap: 0.4rem !important;
  align-items: stretch !important;
  flex-wrap: nowrap !important;
}
[class*="st-key-rio-cal-head"] [data-testid="stColumn"],
[class*="st-key-rio-cal-week"] [data-testid="stColumn"],
[class*="st-key-rio-cal-head"] [data-testid="stHorizontalBlock"] > div,
[class*="st-key-rio-cal-week"] [data-testid="stHorizontalBlock"] > div {
  min-width: 0 !important;
  width: auto !important;
  flex: 1 1 0 !important;
}
.rio-cal-dow {
  color: #8f8f8f;
  font-size: 0.68rem;
  line-height: 1.2;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0 0.15rem 0.35rem;
}
.rio-cal-day {
  min-height: 4.85rem;
  height: 100%;
  box-sizing: border-box;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 0.42rem 0.4rem 0.45rem;
}
.rio-cal-session {
  background: #14241c;
  border-color: #24382e;
}
.rio-cal-today {
  border-color: #4a8c6a;
}
.rio-cal-num,
.rio-cal-label {
  margin: 0;
}
.rio-cal-num {
  color: #f4f4f4;
  font-size: 0.92rem;
  font-weight: 500;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}
.rio-cal-quiet .rio-cal-num {
  color: #8f8f8f;
}
.rio-cal-label {
  margin-top: 0.32rem;
  color: #d4d4d4;
  font-size: 0.72rem;
  line-height: 1.25;
  overflow-wrap: break-word;
}
[class*="st-key-rio-days-"] {
  margin-top: 0.85rem !important;
}
[class*="st-key-rio-hit-"] {
  position: relative !important;
}
[class*="st-key-rio-hit-"] [data-testid="stElementContainer"]:has([data-testid="stPageLink"]),
[class*="st-key-rio-hit-"] [data-testid="stLayoutWrapper"]:has([data-testid="stPageLink"]) {
  position: absolute !important;
  inset: 0 !important;
  z-index: 4 !important;
  width: 100% !important;
  height: 100% !important;
  min-height: 0 !important;
  margin: 0 !important;
}
[class*="st-key-rio-hit-"] [data-testid="stPageLink"],
[class*="st-key-rio-hit-"] [data-testid="stPageLink-NavLink"] {
  position: absolute !important;
  inset: 0 !important;
  z-index: 4 !important;
  display: block !important;
  width: 100% !important;
  height: 100% !important;
  min-height: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  opacity: 0 !important;
  box-shadow: none !important;
  cursor: pointer !important;
}
[class*="st-key-rio-hit-"] [data-testid="stPageLink-NavLink"]:focus-visible {
  outline: none !important;
}
[class*="st-key-rio-hit-row-"]:hover .rio-day {
  background: #1a2e24;
}
[class*="st-key-rio-hit-card-"]:hover .rio-daycard {
  border-color: #2a4a3a;
}
[class*="st-key-rio-hit-"]:focus-within .rio-day,
[class*="st-key-rio-hit-"]:focus-within .rio-daycard,
[class*="st-key-rio-hit-"]:focus-within .rio-cal-day,
[class*="st-key-rio-hit-"]:focus-within .rio-past-row,
[class*="st-key-rio-hit-dash"]:focus-within .rio-next,
[class*="st-key-rio-hit-dash"]:focus-within .rio-hero {
  outline: 1px solid #6db892;
  outline-offset: 2px;
}
[class*="st-key-rio-hit-cal-"]:hover .rio-cal-session {
  border-color: #2a4a3a;
}
[class*="st-key-rio-hit-dash"]:hover .rio-next-work {
  color: #8fd4b0 !important;
}
.rio-status {
  text-align: right;
  color: #8f8f8f;
  font-size: 0.62rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding-top: 0.26rem;
}
.rio-volume,
.rio-heart {
  background: #14241c;
  border: 1px solid #24382e;
  border-radius: 16px;
  padding: 0.95rem 1.15rem 0.55rem;
  margin: 0 0 1.15rem;
}
.rio-volume .rio-mark-label,
.rio-heart .rio-mark-label {
  margin: 0 !important;
  padding: 0 0 0.2rem !important;
}
.rio-volume-line,
.rio-heart-line {
  display: block;
  width: 100%;
  height: auto;
}
.rio-heart {
  padding-bottom: 0.9rem;
}
.rio-heart-label {
  fill: #f4f4f4 !important;
}
.rio-heart-dot {
  fill: #6db892 !important;
}
.rio-progress-list {
  background: #14241c;
  border: 1px solid #24382e;
  border-radius: 16px;
  padding: 0.2rem 1.35rem;
  margin: 0 0 1.15rem;
}
.rio-lib {
  background: #14241c;
  border: 1px solid #24382e;
  border-radius: 16px;
  padding: 0.15rem 1.35rem;
  margin: 0.35rem 0 1.15rem;
}
.rio-lib-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  column-gap: 1.25rem;
  align-items: start;
  padding: 0.92rem 0;
}
.rio-lib-row + .rio-lib-row { border-top: 1px solid #24382e; }
.rio-lib-name {
  color: #f4f4f4;
  font-size: 0.98rem;
  font-weight: 500;
  line-height: 1.4;
  overflow-wrap: break-word;
}
.rio-lib-id {
  margin-top: 0.22rem;
  color: #8f8f8f;
  font-size: 0.75rem;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
}
.rio-lib-cap {
  color: #d4d4d4;
  font-size: 0.84rem;
  line-height: 1.4;
  text-align: right;
  padding-top: 0.12rem;
}
.rio-lib-count {
  margin: 0 0 0.85rem !important;
}
[class*="st-key-rio-library"] {
  margin: 0 0 0.15rem !important;
}
[class*="st-key-rio-library"] [data-testid="stHorizontalBlock"] {
  gap: 0.85rem !important;
  align-items: start !important;
}
.rio-progress {
  display: grid;
  grid-template-columns: 0.65rem 6.5rem minmax(0, 1fr) 6.2rem auto;
  column-gap: 0.85rem;
  align-items: baseline;
  padding: 0.82rem 0;
}
.rio-progress + .rio-progress { border-top: 1px solid #24382e; }
.rio-progress-tick {
  width: 0.55rem;
  height: 0.55rem;
  border: 1px solid #8f8f8f;
  border-radius: 99px;
  background: transparent;
  align-self: center;
}
.rio-progress-done .rio-progress-tick {
  background: #4a8c6a;
  border-color: #4a8c6a;
}
.rio-progress-current .rio-progress-tick {
  background: #6db892;
  border-color: #6db892;
}
.rio-progress-week {
  color: #f4f4f4;
  font-size: 0.98rem;
  font-weight: 500;
  letter-spacing: -0.02em;
}
.rio-progress-phase {
  color: #d4d4d4;
  font-size: 0.92rem;
}
.rio-progress-volume {
  margin-top: 0.16rem;
  color: #d4d4d4;
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0;
}
.rio-progress-upcoming .rio-progress-volume,
.rio-progress-open .rio-progress-volume { color: #8f8f8f; }
.rio-progress-status {
  color: #d4d4d4;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-align: right;
}
.rio-progress-days {
  color: #d4d4d4;
  font-size: 0.84rem;
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}
.rio-progress-current .rio-progress-days { color: #f4f4f4; }
.rio-progress-done .rio-progress-days,
.rio-progress-open .rio-progress-days { color: #8f8f8f; }
.rio-progress-current .rio-progress-week,
.rio-progress-current .rio-progress-status { color: #f4f4f4; }
.rio-progress-done .rio-progress-week { color: #d4d4d4; }
.rio-progress-upcoming .rio-progress-week,
.rio-progress-upcoming .rio-progress-phase,
.rio-progress-open .rio-progress-week,
.rio-progress-open .rio-progress-phase { color: #8f8f8f; }
.rio-empty {
  margin: 0.9rem 0 0.2rem;
  color: #d4d4d4;
}
.rio-mark-label {
  margin: 0 !important;
  padding: 0.95rem 0 0.55rem !important;
  color: #8f8f8f !important;
  font-size: 0.68rem !important;
  line-height: 1.2 !important;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.rio-reason {
  margin: 0.22rem 0 !important;
  color: #8f8f8f !important;
  font-size: 0.78rem !important;
  line-height: 1.45 !important;
}
.rio-reason span {
  color: #d4d4d4;
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
  color: #8f8f8f !important;
  font-size: 0.8rem !important;
  padding: 0.35rem 0 !important;
  border-radius: 0 !important;
}
[class*="st-key-rio-week"] [data-testid="stExpander"] summary:hover {
  background: transparent !important;
  color: #f4f4f4 !important;
}
[class*="st-key-rio-week"] [data-testid="stExpander"] svg {
  fill: #8f8f8f !important;
}
[class*="st-key-rio-week"] button {
  background: transparent !important;
  border: 1px solid #24382e !important;
  border-radius: 8px !important;
  color: #f4f4f4 !important;
  min-height: 2.15rem !important;
  padding: 0.35rem 0.7rem !important;
  font-size: 0.8rem !important;
  font-weight: 500 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-week"] button p { color: inherit !important; }
[class*="st-key-rio-week"] button[kind="primary"],
[class*="st-key-rio-week"] [data-testid="stBaseButton-primary"] {
  border-color: #4a8c6a !important;
  color: #8fd4b0 !important;
  background: transparent !important;
}
[class*="st-key-rio-week"] button[kind="secondary"]:hover,
[class*="st-key-rio-week"] [data-testid="stBaseButton-secondary"]:hover {
  border-color: #4a8c6a !important;
  color: #f4f4f4 !important;
  background: transparent !important;
}
[class*="st-key-rio-week"] button[kind="primary"]:hover,
[class*="st-key-rio-week"] [data-testid="stBaseButton-primary"]:hover {
  background: #4a8c6a !important;
  color: #000000 !important;
}
[class*="st-key-rio-week"] [data-testid="stHorizontalBlock"] {
  gap: 0.55rem !important;
}
[class*="st-key-rio-week-mark"] {
  margin: 0.6rem 0 1.65rem !important;
}

.rio-card {
  background: #14241c;
  border: 1px solid #24382e;
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
.rio-card .rio-prose + .rio-mark-label,
.rio-card .rio-note + .rio-mark-label,
.rio-card .rio-prep + .rio-mark-label,
.rio-card .rio-reasons + .rio-mark-label {
  padding-top: 1.05rem !important;
}
.rio-card h2.rio-week-title {
  margin: 0 0 0.95rem !important;
  line-height: 1.35 !important;
  overflow-wrap: break-word;
}
.rio-card .rio-empty {
  margin: 0.2rem 0 0.15rem;
}
.rio-fields { margin-top: 0.1rem; }
.rio-card .rio-note + .rio-fields > .rio-field:first-child,
.rio-card .rio-prose + .rio-fields > .rio-field:first-child {
  border-top: 1px solid #24382e;
  margin-top: 0.85rem;
  padding-top: 0.85rem;
}
.rio-field {
  display: grid;
  grid-template-columns: 11.5rem minmax(0, 1fr);
  column-gap: 1.35rem;
  align-items: baseline;
  padding: 0.78rem 0;
}
.rio-field + .rio-field,
.rio-fields + .rio-fields > .rio-field:first-child { border-top: 1px solid #24382e; }
.rio-k {
  color: #d4d4d4;
  font-size: 0.78rem;
  line-height: 1.35;
}
.rio-v {
  color: #f4f4f4;
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.rio-v .rio-missing,
.rio-table td .rio-missing {
  color: #d4d4d4;
  font-weight: 400;
}
.rio-prose {
  margin: 0.35rem 0 0.15rem !important;
  padding-top: 0.95rem;
  border-top: 1px solid #24382e;
  color: #f4f4f4 !important;
  font-size: 1.02rem !important;
  line-height: 1.6 !important;
}
.rio-note {
  margin: 0 0 0.15rem !important;
  color: #f4f4f4 !important;
  font-size: 1.02rem !important;
  line-height: 1.6 !important;
}
.rio-prep {
  margin: 0.95rem 0 0.2rem !important;
  padding-top: 0.85rem;
  border-top: 1px solid #24382e;
}
.rio-prep-line {
  margin: 0 !important;
  padding: 0.22rem 0;
  color: #f4f4f4 !important;
  font-size: 0.95rem !important;
  line-height: 1.4 !important;
}
.rio-prep-line span {
  color: #d4d4d4;
}
.rio-card .rio-reason {
  margin: 0.28rem 0 !important;
  color: #f4f4f4 !important;
  font-size: 0.95rem !important;
  line-height: 1.45 !important;
}
.rio-table-wrap { overflow-x: auto; }
.rio-table {
  width: max-content;
  min-width: 100%;
  border-collapse: collapse;
}
.rio-table th {
  text-align: left;
  color: #8f8f8f;
  font-size: 0.72rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  padding: 0.15rem 0.7rem 0.55rem 0;
  border-bottom: 1px solid #24382e;
  white-space: nowrap;
}
.rio-table td {
  color: #f4f4f4;
  font-size: 0.9rem;
  line-height: 1.4;
  padding: 0.72rem 0.7rem 0.72rem 0;
  border-bottom: 1px solid #24382e;
  font-variant-numeric: tabular-nums;
  vertical-align: top;
  white-space: nowrap;
}
.rio-table tr:last-child td { border-bottom: none; }
.rio-table th:last-child,
.rio-table td:last-child { padding-right: 0; }

[class*="st-key-rio-activity-refresh"] {
  margin: 0.15rem 0 0.85rem;
}
[class*="st-key-rio-activity-refresh"] button {
  background: transparent !important;
  border: 1px solid #24382e !important;
  border-radius: 8px !important;
  color: #f4f4f4 !important;
  min-height: 2.15rem !important;
  padding: 0.35rem 0.85rem !important;
  font-size: 0.8rem !important;
  font-weight: 500 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-activity-refresh"] button p { color: inherit !important; }
[class*="st-key-rio-activity-refresh"] button:hover {
  border-color: #4a8c6a !important;
  color: #8fd4b0 !important;
}

[class*="st-key-rio-start"],
[class*="st-key-rio-profile-edit"] {
  max-width: 22rem;
  padding-bottom: 2.5rem;
}
[class*="st-key-rio-profile-edit"] {
  margin-top: 0.35rem;
}
[class*="st-key-rio-start"] [data-testid="stVerticalBlock"],
[class*="st-key-rio-profile-edit"] [data-testid="stVerticalBlock"] {
  gap: 0.85rem !important;
}
[class*="st-key-rio-start"] button,
[class*="st-key-rio-start"] [data-testid="stBaseButton-primary"],
[class*="st-key-rio-profile-edit"] button,
[class*="st-key-rio-profile-edit"] [data-testid="stBaseButton-primary"] {
  background: transparent !important;
  border: 1px solid #4a8c6a !important;
  border-radius: 8px !important;
  color: #8fd4b0 !important;
  min-height: 2.45rem !important;
  margin-top: 0.75rem !important;
  padding: 0.4rem 0.9rem !important;
  font-size: 0.9rem !important;
  font-weight: 500 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-start"] button p,
[class*="st-key-rio-start"] button span,
[class*="st-key-rio-profile-edit"] button p,
[class*="st-key-rio-profile-edit"] button span {
  color: inherit !important;
}
[class*="st-key-rio-start"] button:hover,
[class*="st-key-rio-start"] [data-testid="stBaseButton-primary"]:hover,
[class*="st-key-rio-profile-edit"] button:hover,
[class*="st-key-rio-profile-edit"] [data-testid="stBaseButton-primary"]:hover {
  background: #4a8c6a !important;
  border-color: #4a8c6a !important;
  color: #000000 !important;
}

[data-testid="stSelectbox"] [role="group"] {
  background: #14241c !important;
  border: 1px solid #24382e !important;
  border-radius: 8px !important;
}
[data-testid="stSelectbox"] [role="group"]:focus-within {
  border-color: #6db892 !important;
  box-shadow: none !important;
}
[data-testid="stSelectbox"] input {
  background: transparent !important;
  color: #f4f4f4 !important;
  -webkit-text-fill-color: #f4f4f4 !important;
  border: none !important;
  box-shadow: none !important;
  caret-color: #f4f4f4 !important;
}
[data-testid="stSelectbox"] input:focus {
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
}
[data-testid="stSelectbox"] button {
  background: transparent !important;
  color: #d4d4d4 !important;
  border: none !important;
  box-shadow: none !important;
}
[data-testid="stSelectbox"] svg { fill: #d4d4d4 !important; }
[data-testid="stSelectboxVirtualDropdown"] {
  background: #1a2e24 !important;
  color: #f4f4f4 !important;
  border: 1px solid #24382e !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"] {
  color: #f4f4f4 !important;
  background: transparent !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"],
[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover {
  background: #2a4a3a !important;
  color: #8fd4b0 !important;
}

[class*="st-key-rio-result"] {
  background: #14241c;
  border: 1px solid #24382e;
  border-radius: 16px;
  padding: 1.15rem 1.55rem 1.2rem;
  margin: 0 0 1.15rem;
}
[class*="st-key-rio-result"] .rio-mark-label {
  padding: 0 0 0.45rem !important;
}
[class*="st-key-rio-result"] .rio-rep-note {
  margin: 0 0 0.9rem !important;
  padding: 0 !important;
  color: #d4d4d4 !important;
  font-size: 0.84rem !important;
  line-height: 1.45 !important;
}
[class*="st-key-rio-result"] [data-testid="stHorizontalBlock"] {
  gap: 0.85rem 1.1rem !important;
  align-items: start !important;
  flex-wrap: nowrap !important;
}
[class*="st-key-rio-result"] [data-testid="stHorizontalBlock"] > div {
  min-width: 0 !important;
  flex: 1 1 0 !important;
  width: auto !important;
}
[class*="st-key-rio-result"] [data-testid="stNumberInput"] {
  margin: 0 0 0.75rem !important;
}
[class*="st-key-rio-result-one"] [data-testid="stNumberInput"] {
  max-width: 16rem;
}
[class*="st-key-rio-result"] [data-testid="stWidgetLabel"] {
  margin-bottom: 0.28rem !important;
}
[class*="st-key-rio-result"] [data-testid="stNumberInputContainer"] {
  background: #1a2e24 !important;
  border: 1px solid #24382e !important;
  border-radius: 8px !important;
}
[class*="st-key-rio-result"] [data-testid="stNumberInputContainer"]:focus-within {
  border-color: #6db892 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-result"] [data-testid="stNumberInputField"] {
  color: #f4f4f4 !important;
  -webkit-text-fill-color: #f4f4f4 !important;
  background: transparent !important;
  caret-color: #f4f4f4 !important;
}
[class*="st-key-rio-result"] [data-testid="stNumberInputStepUp"],
[class*="st-key-rio-result"] [data-testid="stNumberInputStepDown"] {
  display: none !important;
}
[class*="st-key-rio-result"] input[type="number"] {
  appearance: textfield;
  -moz-appearance: textfield;
}
[class*="st-key-rio-result"] input[type="number"]::-webkit-outer-spin-button,
[class*="st-key-rio-result"] input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
[class*="st-key-rio-result"] [data-testid="stNumberInputClearButton"] {
  color: #d4d4d4 !important;
}
[class*="st-key-rio-result"] .rio-week-meta {
  margin-top: 0.15rem !important;
}

.rio-template-id {
  margin-top: 0.28rem;
  color: #8f8f8f;
  font-size: 0.75rem;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
}
.rio-session-split {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(15rem, 18.5rem);
  column-gap: 2rem;
  align-items: start;
}
.rio-session-plan > .rio-mark-label,
.rio-supplied > .rio-mark-label {
  padding: 0 0 0.4rem !important;
}
.rio-supplied {
  border-left: 1px solid #24382e;
  padding: 0 0 0.1rem 1.35rem;
}
.rio-supplied .rio-field {
  grid-template-columns: 4.75rem minmax(0, 1fr);
  column-gap: 0.75rem;
  padding: 0.42rem 0;
}
.rio-supplied .rio-v {
  font-variant-numeric: tabular-nums;
}
.rio-daycard-id { margin-top: 0.45rem; }
.rio-next-id { margin-top: 0.45rem; }
.rio-settings-note {
  margin: 0.15rem 0 0.2rem !important;
  color: #8f8f8f !important;
  font-size: 0.8rem !important;
  line-height: 1.4 !important;
}
[class*="st-key-rio-settings"] {
  background: #14241c;
  border: 1px solid #24382e;
  border-radius: 16px;
  padding: 0.85rem 1.35rem 0.45rem;
  margin: 0 0 1.15rem !important;
}
[class*="st-key-rio-settings"] [data-testid="stWidgetLabel"] p,
[class*="st-key-rio-settings"] label,
[class*="st-key-rio-settings"] [data-testid="stMarkdownContainer"] p {
  color: #f4f4f4 !important;
}
[class*="st-key-rio-settings"] [role="radiogroup"] {
  gap: 1.1rem;
}
[class*="st-key-rio-settings"] input[type="radio"] {
  accent-color: #4a8c6a;
}
[class*="st-key-rio-settings"] [data-testid="stCheckbox"] label > div:first-of-type {
  background: #1a2e24 !important;
  border: 1px solid #24382e !important;
}
[class*="st-key-rio-settings"] [data-testid="stCheckbox"]:has(input:checked) label > div:first-of-type {
  background: #4a8c6a !important;
  border-color: #4a8c6a !important;
}
[class*="st-key-rio-confirm"] {
  margin: 0.35rem 0 0.8rem !important;
}
[class*="st-key-rio-plan-store"],
[class*="st-key-rio-profile-store"],
[class*="st-key-rio-past-seasons-store"] {
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  border: 0 !important;
}
[class*="st-key-rio-past-list"] {
  background: #14241c;
  border: 1px solid #24382e;
  border-radius: 16px;
  padding: 0.2rem 0.35rem;
  margin: 0.35rem 0 1.15rem !important;
}
.rio-past-row {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 1.15fr) auto;
  column-gap: 1.25rem;
  align-items: end;
  padding: 0.85rem 0.9rem;
}
.rio-past-rule { border-top: 1px solid #24382e; }
.rio-past-k {
  color: #8f8f8f;
  font-size: 0.68rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  line-height: 1.2;
}
.rio-past-v {
  margin-top: 0.28rem;
  color: #f4f4f4;
  font-size: 1rem;
  font-variant-numeric: tabular-nums;
  line-height: 1.3;
}
.rio-past-time { text-align: right; }
[class*="st-key-rio-hit-past-"]:hover .rio-past-row {
  background: #1a2e24;
}

h2.rio-section,
.stMarkdown h2.rio-section {
  margin: 2.4rem 0 0.85rem !important;
  padding: 0 !important;
  color: #f4f4f4 !important;
  font-size: 1.35rem !important;
  font-weight: 500 !important;
  letter-spacing: -0.03em !important;
  line-height: 1.2 !important;
}
.rio-section-sub {
  margin: -0.35rem 0 1.1rem !important;
}
.rio-stats {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  gap: 1.5rem 2rem;
  align-items: end;
  margin-top: 0.2rem;
}
.rio-stat .rio-mark-label {
  margin: 0 !important;
  padding: 0 0 0.45rem !important;
}
.rio-stat-value {
  margin: 0.15rem 0 0 !important;
  color: #f4f4f4 !important;
  font-size: 1.65rem !important;
  font-weight: 500 !important;
  letter-spacing: -0.03em !important;
  line-height: 1.2 !important;
}
.rio-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;
  margin: 0 0 1.15rem;
}
.rio-grid .rio-card {
  margin: 0;
  min-height: 7.5rem;
}
.rio-next {
  background: #14241c;
  border: 1px solid #24382e;
  border-radius: 16px;
  padding: 1.35rem 1.5rem 1.25rem;
  margin: 0 0 0.95rem;
}
.rio-next .rio-mark-label {
  margin: 0 !important;
  padding: 0 !important;
}
.rio-next-day {
  margin-top: 0.55rem;
  color: #f4f4f4;
  font-size: 1.85rem;
  font-weight: 500;
  letter-spacing: -0.03em;
  line-height: 1.1;
}
.rio-next .rio-range { margin-top: 0.35rem !important; }
.rio-next .rio-next-work { margin-top: 0.95rem !important; font-size: 1.15rem !important; }
.rio-mini {
  background: #14241c;
  border: 1px solid #24382e;
  border-radius: 14px;
  padding: 0.95rem 1rem 0.9rem;
  min-height: 7.2rem;
  height: 100%;
  box-sizing: border-box;
}
.rio-mini-dow {
  color: #f4f4f4;
  font-size: 0.98rem;
  font-weight: 500;
}
.rio-mini-date {
  margin-top: 0.2rem;
  color: #d4d4d4;
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
}
.rio-mini-work {
  margin-top: 0.75rem;
  color: #f4f4f4;
  font-size: 0.88rem;
  line-height: 1.4;
}
.rio-phases {
  display: flex;
  gap: 0.4rem;
  overflow-x: auto;
  padding: 0.35rem 0 0.15rem;
}
.rio-phase {
  flex: 1 0 3.1rem;
  min-width: 3.1rem;
  background: #14241c;
  border: 1px solid #24382e;
  border-radius: 10px;
  padding: 0.45rem 0.35rem 0.5rem;
  text-align: center;
}
.rio-phase-now {
  border-color: #4a8c6a;
}
.rio-phase-week {
  color: #8f8f8f;
  font-size: 0.62rem;
  letter-spacing: 0.06em;
}
.rio-phase-num {
  margin-top: 0.2rem;
  color: #f4f4f4;
  font-size: 0.95rem;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
.rio-card-tight { margin-top: 0.2rem; }
[class*="st-key-rio-subnav"] {
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 0.35rem 0.9rem !important;
  padding: 0.75rem 0 0.15rem !important;
  margin: 0 0 0.4rem !important;
}
[class*="st-key-rio-subnav"] [data-testid="stPageLink-NavLink"] {
  background: transparent !important;
  border-bottom: 1px solid transparent !important;
  padding: 0.1rem 0 0.2rem !important;
  color: #8f8f8f !important;
}
[class*="st-key-rio-subnav"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-subnav"] [data-testid="stPageLink-NavLink"] p {
  color: #8f8f8f !important;
  font-size: 0.78rem !important;
}
[class*="st-key-rio-sub-"][class*="-is-active"] [data-testid="stPageLink-NavLink"],
[class*="st-key-rio-sub-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-sub-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] p {
  color: #f4f4f4 !important;
  border-bottom-color: #4a8c6a !important;
}
[class*="st-key-rio-quick"] {
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 0.5rem !important;
  margin: 0.2rem 0 1.4rem !important;
}
[class*="st-key-rio-quick"] [data-testid="stPageLink-NavLink"] {
  background: #14241c !important;
  border: 1px solid #24382e !important;
  border-radius: 999px !important;
  padding: 0.38rem 0.85rem !important;
}
[class*="st-key-rio-quick"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-quick"] [data-testid="stPageLink-NavLink"] p {
  color: #f4f4f4 !important;
  font-size: 0.82rem !important;
}
[class*="st-key-rio-next3"] {
  display: flex !important;
  gap: 0.7rem !important;
  align-items: stretch !important;
  margin: 0 0 1.2rem !important;
}
[class*="st-key-rio-next3"] > div,
[class*="st-key-rio-next3"] [data-testid="stHorizontalBlock"] > div {
  flex: 1 1 0 !important;
  min-width: 0 !important;
}
[class*="st-key-rio-hit-mini-"]:hover .rio-mini {
  border-color: #2a4a3a;
}
[class*="st-key-rio-start"] { max-width: 26rem; }


[class*="st-key-rio-confirm"] button,
[class*="st-key-rio-confirm"] [data-testid="stBaseButton-primary"],
[class*="st-key-rio-confirm"] [data-testid="stBaseButton-secondary"] {
  background: transparent !important;
  border: 1px solid #24382e !important;
  border-radius: 8px !important;
  color: #f4f4f4 !important;
  min-height: 2.15rem !important;
  padding: 0.35rem 0.7rem !important;
  font-size: 0.8rem !important;
  font-weight: 500 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-confirm"] button p { color: inherit !important; }
[class*="st-key-rio-confirm"] button[kind="primary"],
[class*="st-key-rio-confirm"] [data-testid="stBaseButton-primary"] {
  border-color: #4a8c6a !important;
  color: #8fd4b0 !important;
  background: transparent !important;
}
[class*="st-key-rio-confirm"] button[kind="secondary"]:hover,
[class*="st-key-rio-confirm"] [data-testid="stBaseButton-secondary"]:hover {
  border-color: #4a8c6a !important;
  color: #f4f4f4 !important;
  background: transparent !important;
}
[class*="st-key-rio-confirm"] button[kind="primary"]:hover,
[class*="st-key-rio-confirm"] [data-testid="stBaseButton-primary"]:hover {
  background: #4a8c6a !important;
  border-color: #4a8c6a !important;
  color: #000000 !important;
}
[class*="st-key-rio-settings"] [data-testid="stCheckbox"]:has(input:checked) svg {
  fill: #000000 !important;
}

@media (max-width: 720px) {
  [class*="st-key-rio-nav"] {
    flex-direction: column !important;
    align-items: flex-start !important;
    justify-content: flex-start !important;
    gap: 0.85rem !important;
  }
  [class*="st-key-rio-nav"] > [data-testid="stElementContainer"]:last-child,
  [class*="st-key-rio-nav"] > [data-testid="stLayoutWrapper"]:last-child {
    width: 100% !important;
    flex: 1 1 auto !important;
    height: auto !important;
  }
  [class*="st-key-rio-links"] { justify-content: flex-start !important; }
  .rio-hero h1,
  .stMarkdown .rio-hero h1 { font-size: 2.45rem !important; }
  .rio-next-work { font-size: 1.22rem !important; }
  .rio-cal-day { min-height: 4.15rem; padding: 0.22rem 0.06rem 0.28rem; }
  .rio-cal-num { font-size: 0.68rem; }
  .rio-cal-label { font-size: 0.5rem; line-height: 1.15; }
  .rio-cal-dow { letter-spacing: 0.04em; font-size: 0.58rem; }
  .rio-day { grid-template-columns: 1fr; row-gap: 0.35rem; }
  .rio-lib-row { grid-template-columns: 1fr; row-gap: 0.22rem; }
  .rio-past-row { grid-template-columns: 1fr; row-gap: 0.55rem; }
  .rio-past-time { text-align: left; }
  .rio-lib-cap { text-align: left; padding-top: 0; }
  .rio-status { text-align: left; padding-top: 0; }
  .rio-progress {
    grid-template-columns: 0.65rem minmax(0, 1fr) auto;
    row-gap: 0.15rem;
  }
  .rio-progress-tick { grid-row: 1; align-self: center; }
  .rio-progress-phase { grid-column: 2; grid-row: 2; }
  .rio-progress-status { grid-column: 2; grid-row: 3; text-align: left; }
  .rio-progress-days { grid-column: 3; grid-row: 1 / span 3; align-self: center; }
  .rio-field { grid-template-columns: 1fr; row-gap: 0.22rem; padding: 0.7rem 0; }
  .rio-session-split { grid-template-columns: 1fr; row-gap: 1.05rem; }
  .rio-supplied {
    border-left: none;
    border-top: 1px solid #24382e;
    padding: 0.95rem 0 0;
  }
  .rio-supplied .rio-field {
    grid-template-columns: 4.75rem minmax(0, 1fr);
    row-gap: 0;
    padding: 0.42rem 0;
  }
  [class*="st-key-rio-pick"] { max-width: 100% !important; }
  [class*="st-key-rio-result-one"] [data-testid="stNumberInput"] { max-width: 100% !important; }
  .rio-daycard-dow { font-size: 1.32rem; }
  .rio-stats, .rio-grid { grid-template-columns: 1fr; }
  .rio-next-day { font-size: 1.45rem; }
}
</style>
"""

_COMPACT_CSS = """
<style>
.rio-hero { padding: 1.35rem 0 0.85rem !important; }
.rio-hero h1,
.stMarkdown .rio-hero h1 { font-size: 2.35rem !important; margin-top: 0.35rem !important; }
.rio-range { margin-top: 0.4rem !important; }
.rio-card { padding: 0.85rem 1.1rem 0.7rem; margin-bottom: 0.7rem; }
.rio-daycard { padding: 0.95rem 1.1rem 0.8rem; margin-bottom: 0.5rem; }
.rio-daycard-work { margin-top: 0.7rem; font-size: 1.05rem; }
.rio-daycard-target { margin-top: 0.55rem; padding-top: 0.55rem; }
.rio-day { padding: 0.5rem 0; }
[class*="st-key-rio-week"] {
  padding: 0.85rem 1.05rem 0.65rem !important;
  margin-bottom: 0.85rem !important;
}
[class*="st-key-rio-pick"] { margin-bottom: 0.85rem !important; }
.rio-lib-row { padding: 0.55rem 0; }
.rio-volume,
.rio-heart { padding: 0.7rem 0.95rem 0.4rem; margin-bottom: 0.7rem; }
</style>
"""


def _esc(value: object) -> str:
    return escape(str(value), quote=True)


def _prefs() -> dict:
    """Display preferences for this browser session. The plan is not touched."""
    raw = dict(st.session_state.get("rio_settings") or {})
    widget = (
        ("settings-units", "units"),
        ("settings-ids", "show_ids"),
        ("settings-compact", "compact"),
        ("settings-dates", "date_format"),
        ("settings-confirm", "confirm_adapt"),
        ("settings-notes", "notifications"),
    )
    for key, name in widget:
        if key in st.session_state:
            raw[name] = st.session_state[key]
    return normalize_prefs(raw)


def _css() -> str:
    css = _APP_CSS
    if _prefs()["compact"]:
        css += _COMPACT_CSS
    return css


def _date_text(value: object) -> str:
    return format_date(value, _prefs()["date_format"])


def _copy(text: object) -> str:
    """Distance words for the chosen units. The plan text is not rewritten."""
    return display_distance(text, _prefs()["units"])


def _id_html(template_id: object, extra: str = "") -> str:
    if not _prefs()["show_ids"]:
        return ""
    key = str(template_id or "").strip()
    if not key:
        return ""
    classes = "rio-template-id" if not extra else f"rio-template-id {extra}"
    return f'<div class="{classes}">{_esc(key)}</div>'


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
    if _EMBEDDING:
        parts = [f'<h2 class="rio-section">{_esc(title)}</h2>']
        if subtitle:
            parts.append(f'<p class="rio-range rio-section-sub">{_esc(subtitle)}</p>')
        return "".join(parts)
    parts = ['<header class="rio-hero">']
    if banner:
        parts.append(f'<p class="rio-synthetic">{_esc(banner)}</p>')
    parts.append(f"<h1>{_esc(title)}</h1>")
    if subtitle:
        parts.append(f'<p class="rio-range">{_esc(subtitle)}</p>')
    parts.append("</header>")
    return "".join(parts)


def _nest(draw) -> None:
    """Draw a page inside the one already open. Its own nav stays off."""
    global _EMBEDDING
    previous = _EMBEDDING
    _EMBEDDING = True
    try:
        draw()
    finally:
        _EMBEDDING = previous


def _render_subnav(active: str) -> None:
    """Same-tab links for the pages grouped under More."""
    if not _MORE_PAGES:
        return
    with st.container(
        key="rio-subnav",
        horizontal=True,
        vertical_alignment="center",
        gap=14,
    ):
        for label, page in _MORE_PAGES:
            slug = label.lower().replace(" ", "-")
            key = f"rio-sub-{slug}-is-active" if label == active else f"rio-sub-{slug}"
            with st.container(key=key, width="content"):
                st.page_link(
                    page,
                    label=label,
                    icon="",
                    query_params=_link_params(),
                    width="content",
                )


def _render_nav(active: str) -> None:
    """Page links follow Streamlit routing and stay in this tab."""
    if _EMBEDDING:
        return
    home = _HOME_PAGE
    if home is None and _NAV_PAGES:
        home = _NAV_PAGES[0][1]
    if home is None:
        return
    more_labels = {label for label, _page in _MORE_PAGES}
    shown = "More" if active in more_labels else active
    with st.container(
        key="rio-nav",
        horizontal=True,
        vertical_alignment="center",
        gap=24,
    ):
        with st.container(key="rio-brand", width="content"):
            st.page_link(
                home,
                label="RIO",
                icon="",
                query_params=_link_params(),
                width="content",
            )
        with st.container(
            key="rio-links",
            horizontal=True,
            horizontal_alignment="right",
            vertical_alignment="center",
            gap=18,
            width="stretch",
        ):
            for label, page in _NAV_PAGES:
                slug = label.lower().replace(" ", "-")
                key = f"rio-tab-{slug}-is-active" if label == shown else f"rio-tab-{slug}"
                with st.container(key=key, width="content"):
                    st.page_link(
                        page,
                        label=label,
                        icon="",
                        query_params=_link_params(),
                        width="content",
                    )
    if active == "More" or active in more_labels:
        _render_subnav(active)


def _open(page: str, *, controls: bool = False):
    st.markdown(_css(), unsafe_allow_html=True)
    _render_nav(page)
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


def _note(text: str) -> str:
    return f'<p class="rio-note">{_esc(text)}</p>'


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


def _hero_html(start: date | None, goal: date | None, plan: dict | None, error: str | None) -> str:
    if _EMBEDDING:
        return '<h2 class="rio-section">Full season</h2>'
    synthetic = '<p class="rio-synthetic">SYNTHETIC / DEMO</p>'
    if error or plan is None or start is None or goal is None:
        detail = f'<p class="rio-error">{_esc(error)}</p>' if error else ""
        return (
            f'<header class="rio-hero">{synthetic}'
            "<h1>Season</h1>"
            f"{detail}</header>"
        )
    return (
        f'<header class="rio-hero">{synthetic}'
        f"<h1>{_esc(_length_text(plan['season_length_weeks']))}</h1>"
        f'<p class="rio-range">{_esc(_date_text(start))} — {_esc(_date_text(goal))}</p>'
        "</header>"
    )


def _workout_text(template_id: object) -> str:
    """Plain description for a card. An unknown id stays as stored."""
    key = str(template_id or "").strip()
    if not key:
        return "—"
    return _copy(_WORKOUT_TEXT.get(key, key))


def _day_html(session: dict, *, first: bool = False) -> str:
    status = _status_label(session["reason_codes"])
    status_html = f'<div class="rio-status">{_esc(status)}</div>' if status else ""
    extra = "" if first else " rio-day-next"
    return (
        f'<div class="rio-day{extra}">'
        '<div class="rio-when">'
        f'<div class="rio-dow">{_esc(session["day_of_week"])}</div>'
        f'<div class="rio-date">{_esc(_date_text(session["date"]))}</div>'
        "</div>"
        '<div class="rio-work">'
        f'<div class="rio-name">{_esc(_workout_text(session["template_id"]))}</div>'
        f'{_id_html(session["template_id"])}'
        f'<div class="rio-target">{_esc(_copy(session["target_outcome"]))}</div>'
        "</div>"
        f"{status_html}"
        "</div>"
    )


def _week_sunday(start: date, week_number: int) -> date:
    """Sunday that opens this plan week. Week 1 is the week that contains start."""
    anchor = start - timedelta(days=(start.weekday() + 1) % 7)
    return anchor + timedelta(days=(week_number - 1) * 7)


def _week_containing(start: date, length: int, day: date) -> int:
    """The plan week that contains day, clamped to the season."""
    sunday = _week_sunday(start, 1)
    if day < sunday:
        return 1
    number = (day - sunday).days // 7 + 1
    if number > length:
        return length
    return number


def _week_option(start: date, week_number: int) -> str:
    sunday = _week_sunday(start, week_number)
    saturday = sunday + timedelta(days=6)
    return f"Week {week_number} · {_date_text(sunday)} — {_date_text(saturday)}"


def _weekly_hero(week_number: int, start: date, days: list[dict]) -> str:
    sunday = _week_sunday(start, week_number)
    saturday = sunday + timedelta(days=6)
    phase = _phase_number(days)
    span = f"{_date_text(sunday)} — {_date_text(saturday)}"
    subtitle = span if phase == "—" else f"Phase {phase} · {span}"
    hero = _page_hero(f"Week {week_number}", "SYNTHETIC / DEMO", subtitle)
    return hero.replace('class="rio-hero"', 'class="rio-hero rio-hero-week"', 1)


def _week_day_card(session: dict) -> str:
    """One large day: weekday, date, plain workout, target outcome.

    A matched activity adds its rep times, WORK distance, and heart rate.
    """
    detail = _activity_summary(matched_on(_stored_activities(), session.get("date")))
    actual = f'<div class="rio-daycard-actual">{_esc(detail)}</div>' if detail else ""
    return (
        '<div class="rio-daycard">'
        f'<div class="rio-daycard-dow">{_esc(session["day_of_week"])}</div>'
        f'<div class="rio-daycard-date">{_esc(_date_text(session["date"]))}</div>'
        f'<div class="rio-daycard-work">{_esc(_workout_text(session["template_id"]))}</div>'
        f'{_id_html(session["template_id"], "rio-daycard-id")}'
        f'<div class="rio-daycard-target">{_esc(_copy(session["target_outcome"]))}</div>'
        f"{actual}"
        "</div>"
    )


def _mini_day(session: dict) -> str:
    """A short day card. The workout stays in plain words."""
    return (
        '<div class="rio-mini">'
        f'<div class="rio-mini-dow">{_esc(session["day_of_week"])}</div>'
        f'<div class="rio-mini-date">{_esc(_date_text(session["date"]))}</div>'
        f'<div class="rio-mini-work">{_esc(_workout_text(session["template_id"]))}</div>'
        "</div>"
    )


def _session_link(session: dict, kind: str, *, first: bool = False) -> None:
    """The whole workout opens Session for this date. The plan stays as stored."""
    page = _SESSION_PAGE
    day = str(session["date"])
    if kind == "card":
        html = _week_day_card(session)
    elif kind == "mini":
        html = _mini_day(session)
    else:
        html = _day_html(session, first=first)
    if page is None:
        st.markdown(html, unsafe_allow_html=True)
        return
    label = f"{session['day_of_week']} {day}. {_workout_text(session['template_id'])}"
    with st.container(key=f"rio-hit-{kind}-{day}", gap=None):
        st.markdown(html, unsafe_allow_html=True)
        st.page_link(
            page,
            label=label,
            icon="",
            query_params=_link_params({"date": day}),
            width="stretch",
        )


_PLAN_KEYS = (
    "week_number",
    "day_of_week",
    "date",
    "template_id",
    "reason_codes",
    "target_outcome",
)


def _quality_day(session: dict) -> bool:
    """Tuesday and Thursday work. Recovery and the long run stay closed."""
    if str(session.get("day_of_week")) not in ("Tuesday", "Thursday"):
        return False
    template_id = str(session.get("template_id") or "")
    return bool(template_id) and not template_id.startswith("aer_")


def _plan_for_adapt(plan: dict) -> dict:
    """The six session fields adapt() checks. Result numbers stay off this copy."""
    sessions = []
    for session in plan["sessions"]:
        row = {}
        for key in _PLAN_KEYS:
            value = session[key]
            row[key] = list(value) if key == "reason_codes" else value
        sessions.append(row)
    return {
        "ontology_version": plan.get("ontology_version"),
        "season_length_weeks": plan.get("season_length_weeks"),
        "start_date": plan.get("start_date"),
        "sessions": sessions,
    }


def _actuals() -> dict:
    stored = st.session_state.get("season_actuals")
    if not isinstance(stored, dict):
        stored = {}
        st.session_state["season_actuals"] = stored
    return stored


def _stored_activities() -> list:
    stored = st.session_state.get("season_activities")
    if not isinstance(stored, list):
        return []
    return stored


def _activities_notice() -> None:
    message = st.session_state.get("activities_notice")
    if not isinstance(message, str) or not message.strip():
        return
    st.markdown(
        f'<p class="rio-error">{_esc(message.strip())}</p>',
        unsafe_allow_html=True,
    )


def _activity_summary(row: object, *, include_name: bool = True) -> str:
    """Rep times, WORK distance, and average heart rate for one stored activity."""
    if not isinstance(row, dict):
        return ""
    parts = []
    if include_name:
        name = str(row.get("name") or "").strip()
        if name:
            parts.append(name)
    reps = filled_times(row.get("reps") or [])
    if reps:
        parts.append(reps)
    volume = meters_text(row.get("work_m"))
    if volume:
        shown = display_distance(volume, _prefs()["units"])
        if shown:
            parts.append(shown)
    if row.get("heart_rate") is not None:
        text = heart_rate_text({"average_heartrate": row.get("heart_rate")})
        if text:
            parts.append(text)
    return " · ".join(parts)


def _activity_token(value: object) -> str:
    text = "".join(char if char.isalnum() or char in "-_" else "-" for char in str(value))
    return text[:60] or "activity"


def _render_extras(rows: list) -> None:
    if not rows:
        return
    st.markdown('<p class="rio-mark-label">Extra sessions</p>', unsafe_allow_html=True)
    for row in rows:
        if isinstance(row, dict):
            _extra_link(row)


def _extra_link(row: dict) -> None:
    """An unmatched activity opens its own session. The plan stays as stored."""
    day = str(row.get("date") or "")
    name = str(row.get("name") or "").strip() or "Activity"
    detail = _activity_summary(row, include_name=False)
    actual = f'<div class="rio-daycard-actual">{_esc(detail)}</div>' if detail else ""
    html = (
        '<div class="rio-daycard">'
        f'<div class="rio-daycard-dow">{_esc(weekday_name(day) or "Extra")}</div>'
        f'<div class="rio-daycard-date">{_esc(_date_text(day))}</div>'
        f'<div class="rio-daycard-work">{_esc(name)}</div>'
        f"{actual}"
        "</div>"
    )
    page = _SESSION_PAGE
    ident = str(row.get("id") or "")
    if page is None or not ident:
        st.markdown(html, unsafe_allow_html=True)
        return
    label = f"{weekday_name(day) or 'Extra'} {day}. {name}"
    with st.container(key=f"rio-hit-extra-{_activity_token(ident)}", gap=None):
        st.markdown(html, unsafe_allow_html=True)
        st.page_link(
            page,
            label=label,
            icon="",
            query_params=_link_params({"activity": ident}),
            width="stretch",
        )


def _render_logged_activity(row: dict) -> None:
    """One unmatched activity: name, rep times, WORK distance, and heart rate."""
    parts = [_subject("Activity", str(row.get("name") or "").strip() or "Activity")]
    reps = filled_times(row.get("reps") or [])
    if reps:
        parts.extend((_label("Reps"), _note(reps)))
    volume = meters_text(row.get("work_m"))
    shown = display_distance(volume, _prefs()["units"]) if volume else ""
    if shown:
        parts.extend((_label("Volume"), _note(shown)))
    if row.get("heart_rate") is not None:
        text = heart_rate_text({"average_heartrate": row.get("heart_rate")})
        if text:
            parts.extend((_label("Avg HR"), _note(text)))
    _card(*parts)


def _attach_actuals(plan: dict) -> None:
    """Write stored numbers onto sessions that still use that template."""
    stored = _actuals()
    by_date = {session["date"]: session for session in plan["sessions"]}
    for day in list(stored):
        saved = stored[day]
        session = by_date.get(day)
        if (
            not isinstance(saved, dict)
            or session is None
            or session.get("template_id") != saved.get("template_id")
        ):
            stored.pop(day, None)
            continue
        numbers = saved.get("numbers")
        if isinstance(numbers, list) and numbers:
            session["actual"] = list(numbers)


def _week_mark(plan: dict, week: int) -> str | None:
    """not_hitting wins, then smashing. Same order adapt() uses for a list."""
    found = []
    stored = _actuals()
    for session in plan["sessions"]:
        if session.get("week_number") != week or not _quality_day(session):
            continue
        saved = stored.get(session.get("date"))
        if not isinstance(saved, dict) or saved.get("template_id") != session.get("template_id"):
            continue
        mark = saved.get("mark")
        if mark in _MARKS:
            found.append(mark)
    if not found:
        return None
    if "not_hitting" in found:
        return "not_hitting"
    if "smashing" in found:
        return "smashing"
    return "on_track"


def _adapt_from_result(plan: dict, week: int, outcome: str) -> dict:
    """One adapt for this week, from the plan before this week's results."""
    bases = st.session_state.get("season_quality_base")
    if not isinstance(bases, dict):
        bases = {}
        st.session_state["season_quality_base"] = bases
    if week not in bases:
        bases[week] = _plan_for_adapt(plan)
    for later in list(bases):
        if later > week:
            del bases[later]
    updated = adapt(bases[week], week, outcome)
    _attach_actuals(updated)
    return updated


def _goal_mark_seconds() -> float | None:
    inputs = st.session_state.get("season_inputs")
    if not isinstance(inputs, tuple) or len(inputs) < 3:
        return None
    return goal_seconds(inputs[2])


def _format_numbers(numbers: list) -> str:
    parts = []
    for number in numbers:
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            continue
        if isinstance(number, float) and number.is_integer():
            parts.append(str(int(number)))
        else:
            parts.append(str(number))
    return ", ".join(parts)


def _stored_slot(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = round(float(value), 2)
    if number <= 0:
        return None
    return number


def _intervals_ref(value: object) -> str | None:
    """Activity id or filename kept with the actual. The record allows 120 characters."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > 120:
        return None
    return text


def _boxes_blank(keys: list[str]) -> bool:
    """True when every result box is empty or not on the page yet."""
    for key in keys:
        if key not in st.session_state:
            continue
        value = st.session_state.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        return False
    return True


def _initial_slots(saved: dict | None, count: int) -> list[float | None]:
    """Refill each box. A saved gap stays empty. Older results fill from the left."""
    slots: list[float | None] = [None] * count
    if not isinstance(saved, dict):
        return slots
    stored = saved.get("slots")
    if isinstance(stored, list):
        for index in range(min(count, len(stored))):
            slots[index] = _stored_slot(stored[index])
        return slots
    numbers = saved.get("numbers")
    if not isinstance(numbers, list):
        return slots
    filled = [slot for slot in (_stored_slot(number) for number in numbers) if slot is not None]
    for index, slot in enumerate(filled[:count]):
        slots[index] = slot
    return slots


def _adapt_pending() -> dict | None:
    """A confirm waiting on adapt. Ignored when confirm is off."""
    if not _prefs()["confirm_adapt"]:
        return None
    pending = st.session_state.get("rio_adapt_pending")
    if not isinstance(pending, dict):
        return None
    return pending


def _hold_adapt(pending: dict) -> None:
    st.session_state["rio_adapt_pending"] = pending
    st.rerun()


def _clear_adapt() -> None:
    st.session_state.pop("rio_adapt_pending", None)


def _confirm_adapt(label: str, confirm_key: str, cancel_key: str) -> str | None:
    """Ask before adapt runs. Cancel leaves the plan as stored."""
    st.markdown(
        f'<p class="rio-week-meta">Confirm {_esc(label)} before the plan changes.</p>',
        unsafe_allow_html=True,
    )
    with st.container(key="rio-confirm"):
        left, right = st.columns(2, gap="small")
        with left:
            confirm = st.button("Confirm", key=confirm_key, type="primary", width="stretch")
        with right:
            cancel = st.button("Cancel", key=cancel_key, width="stretch")
    if cancel:
        _clear_adapt()
        st.rerun()
    if confirm:
        return "confirm"
    return None


def _commit_result(
    plan: dict,
    session: dict,
    text: str,
    slots: list | None = None,
    intervals: str | None = None,
) -> None:
    """Store the numbers and call adapt once. Empty or invalid text does nothing."""
    if not text:
        return
    judged = judge(session.get("template_id"), text, _goal_mark_seconds())
    if judged is None:
        return
    day = str(session["date"])
    week = session["week_number"]
    stored = _actuals()
    previous = stored.get(day)
    row = {
        "text": text,
        "numbers": list(judged["numbers"]),
        "mark": judged["mark"],
        "template_id": session.get("template_id"),
    }
    if isinstance(slots, list):
        row["slots"] = [_stored_slot(item) for item in slots]
    ref = _intervals_ref(intervals)
    if ref is not None:
        row["intervals"] = ref
    stored[day] = row
    mark = _week_mark(plan, week)
    if mark is None:
        if previous is None:
            stored.pop(day, None)
        else:
            stored[day] = previous
        return
    try:
        updated = _adapt_from_result(plan, week, mark)
    except ValueError as exc:
        if previous is None:
            stored.pop(day, None)
        else:
            stored[day] = previous
        st.markdown(
            f'<p class="rio-error">{_esc(exc)}</p>',
            unsafe_allow_html=True,
        )
        return
    _clear_adapt()
    marks = dict(st.session_state.get("season_marks") or {})
    marks[week] = mark
    st.session_state["season_marks"] = marks
    st.session_state["season_plan"] = updated
    st.rerun()


def _apply_result(
    plan: dict,
    session: dict,
    text: str,
    slots: list | None = None,
    intervals: str | None = None,
) -> None:
    """Call adapt, or hold the result when confirm is on. Invalid text does nothing."""
    if not text:
        return
    if judge(session.get("template_id"), text, _goal_mark_seconds()) is None:
        return
    if _prefs()["confirm_adapt"]:
        _hold_adapt(
            {
                "kind": "result",
                "day": str(session["date"]),
                "week": session["week_number"],
                "text": text,
                "slots": list(slots) if isinstance(slots, list) else None,
                "intervals": _intervals_ref(intervals),
                "generation": int(st.session_state.get("season_generation") or 0),
            }
        )
        return
    _commit_result(plan, session, text, slots, intervals)


def _remember_intervals(day: str, template_id: object, source: object, text: str) -> None:
    """Keep the file on a result that already has these times. No second adapt."""
    ref = _intervals_ref(source)
    if ref is None or not text:
        return
    stored = _actuals()
    saved = stored.get(day)
    if (
        not isinstance(saved, dict)
        or saved.get("template_id") != template_id
        or saved.get("text") != text
        or saved.get("intervals") == ref
    ):
        return
    saved["intervals"] = ref
    st.rerun()


def _intervals_choice(stem: str) -> tuple[list | None, str | None, str | None]:
    """WORK times and the activity id or filename. Blank leaves the boxes.

    The JSON file is read from disk. This does not call Intervals.icu.
    """
    paths = intervals_json_paths()
    if not paths:
        return None, None, None
    names = [path.name for path in paths]
    selected = st.selectbox(
        "Intervals file",
        ["—", *names],
        key=f"{stem}-intervals",
    )
    if selected == "—":
        return None, None, None
    try:
        times, source = quality_fill(paths[names.index(selected)])
    except IntervalsFileError as exc:
        return None, None, str(exc)
    return times, source, None


def _time_box(label: str, key: str, *, show_label: bool) -> float | None:
    """One time. Empty stays empty so a blank rep is ignored."""
    value = st.number_input(
        label,
        key=key,
        value=None,
        step=0.1,
        format="%g",
        label_visibility="visible" if show_label else "collapsed",
    )
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _render_result(plan: dict, session: dict, generation: int) -> None:
    """One number per rep. A continuous session stays one box.

    Empty boxes are left out. The filled times go through judge(), then adapt().
    An Intervals file fills the boxes from its WORK elapsed times. The boxes
    stay editable. The activity id or filename is stored with the actuals.
    """
    day = str(session["date"])
    stem = f"season-result-{generation}-{day}"
    handled_key = f"{stem}-handled"
    applied_key = f"{stem}-intervals-open"
    saved = _actuals().get(day)
    if not isinstance(saved, dict) or saved.get("template_id") != session.get("template_id"):
        saved = None
    count = result_box_count(session.get("template_id"))
    keys = [f"{stem}-{index}" for index in range(count)]
    with st.container(key="rio-result"):
        st.markdown('<p class="rio-mark-label">Result</p>', unsafe_allow_html=True)
        times, source, file_error = _intervals_choice(stem)
        if file_error:
            st.markdown(
                f'<p class="rio-empty">{_esc(file_error)}</p>',
                unsafe_allow_html=True,
            )
        if file_just_opened(st.session_state.get(applied_key), source):
            fitted = fit_slots(times, count)
            if any(slot is not None for slot in fitted):
                for key, slot in zip(keys, fitted):
                    st.session_state[key] = slot
            st.session_state[applied_key] = source
        initial = _initial_slots(saved, count)
        seed_key = f"{stem}-activity-seed"
        actual_seed = f"{stem}-actual-seed"
        match = matched_on(_stored_activities(), day)
        seeded = False
        if (
            saved is None
            and isinstance(match, dict)
            and st.session_state.get(seed_key) != match.get("id")
            and not any(slot is not None for slot in initial)
        ):
            fitted = fit_slots(match.get("reps"), count)
            if any(slot is not None for slot in fitted):
                initial = fitted
                seeded = True
            st.session_state[seed_key] = match.get("id")
        elif (
            isinstance(saved, dict)
            and any(slot is not None for slot in initial)
            and _boxes_blank(keys)
        ):
            token = str(saved.get("text") or "")
            if token and st.session_state.get(actual_seed) != token:
                seeded = True
                st.session_state[actual_seed] = token
        for key, slot in zip(keys, initial):
            if key not in st.session_state or (seeded and st.session_state.get(key) is None):
                st.session_state[key] = slot
        if seeded or handled_key not in st.session_state:
            st.session_state[handled_key] = filled_times(
                [st.session_state.get(key) for key in keys]
            )
        if count > 1:
            st.markdown(
                '<p class="rio-rep-note">Enter the time for each rep.</p>',
                unsafe_allow_html=True,
            )
            columns = st.columns(2, gap="small")
            entered: list[float | None] = []
            for index, key in enumerate(keys):
                with columns[index % 2]:
                    entered.append(_time_box(f"Rep {index + 1}", key, show_label=True))
        else:
            with st.container(key="rio-result-one"):
                entered = [_time_box("Time", keys[0], show_label=False)]
        text = filled_times(entered)
        handled = str(st.session_state.get(handled_key) or "")
        if text != handled:
            st.session_state[handled_key] = text
            _apply_result(plan, session, text, entered, intervals=source)
        elif source:
            _remember_intervals(day, session.get("template_id"), source, text)
        saved = _actuals().get(day)
        if isinstance(saved, dict) and saved.get("template_id") == session.get("template_id"):
            numbers = _format_numbers(saved.get("numbers") or [])
            mark = saved.get("mark")
            if numbers and mark in _MARKS:
                st.markdown(
                    f'<p class="rio-week-meta">{_esc(numbers)} · {_esc(mark)}</p>',
                    unsafe_allow_html=True,
                )
    pending = _adapt_pending()
    if (
        isinstance(pending, dict)
        and pending.get("kind") == "result"
        and pending.get("day") == day
        and pending.get("generation") == generation
    ):
        answer = _confirm_adapt(
            "this result",
            f"adapt-confirm-result-{generation}-{day}",
            f"adapt-cancel-result-{generation}-{day}",
        )
        if answer == "confirm":
            slots = pending.get("slots")
            intervals = pending.get("intervals")
            _commit_result(
                plan,
                session,
                str(pending.get("text") or ""),
                slots if isinstance(slots, list) else None,
                intervals if isinstance(intervals, str) else None,
            )


def _apply_activity_marks(plan: dict) -> None:
    """Store a matched quality day's mark, then adapt later weeks.

    A day that already has a mark is left as stored. The key is not read
    here. Nothing is sent to a model.
    """
    bases = st.session_state.get("season_quality_base")
    if not isinstance(bases, dict):
        bases = {}
        st.session_state["season_quality_base"] = bases
    try:
        updated, actuals, week_marks = auto_adapt(
            plan,
            _stored_activities(),
            _actuals(),
            _goal_mark_seconds(),
            bases,
        )
    except ValueError as exc:
        st.session_state["activities_notice"] = str(exc)
        return
    if not week_marks:
        return
    st.session_state["season_actuals"] = actuals
    marks = dict(st.session_state.get("season_marks") or {})
    marks.update(week_marks)
    st.session_state["season_marks"] = marks
    st.session_state["season_plan"] = updated


def _commit_mark(plan: dict, week_number: int, choice: str) -> None:
    """One mark for this week. Later weeks are what adapt() returns."""
    try:
        updated = _adapt_from_result(plan, week_number, choice)
    except ValueError as exc:
        st.markdown(
            f'<p class="rio-error">{_esc(exc)}</p>',
            unsafe_allow_html=True,
        )
        return
    _clear_adapt()
    marks = dict(st.session_state.get("season_marks") or {})
    marks[week_number] = choice
    st.session_state["season_marks"] = marks
    st.session_state["season_plan"] = updated
    st.rerun()


def _render_mark(plan: dict, week_number: int, generation: int) -> None:
    """One mark for this week. Confirm can sit in front of adapt()."""
    prefix = _MARK_PREFIX
    applied = (st.session_state.get("season_marks") or {}).get(week_number)
    st.markdown('<p class="rio-mark-label">Mark</p>', unsafe_allow_html=True)
    columns = st.columns(3, gap="small")
    choice = None
    for column, mark in zip(columns, _MARKS):
        with column:
            if st.button(
                mark,
                key=f"{prefix}-mark-{generation}-{week_number}-{mark}",
                type="primary" if applied == mark else "secondary",
                width="stretch",
            ):
                choice = mark
    if choice is not None:
        if _prefs()["confirm_adapt"]:
            _hold_adapt(
                {
                    "kind": "mark",
                    "week": week_number,
                    "choice": choice,
                    "generation": generation,
                    "prefix": prefix,
                }
            )
            return
        _commit_mark(plan, week_number, choice)
        return
    pending = _adapt_pending()
    if (
        isinstance(pending, dict)
        and pending.get("prefix", "season") == prefix
        and pending.get("kind") == "mark"
        and pending.get("week") == week_number
        and pending.get("generation") == generation
        and pending.get("choice") in _MARKS
    ):
        answer = _confirm_adapt(
            str(pending["choice"]),
            f"{prefix}-adapt-confirm-{generation}-{week_number}",
            f"{prefix}-adapt-cancel-{generation}-{week_number}",
        )
        if answer == "confirm":
            _commit_mark(plan, week_number, str(pending["choice"]))


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
        mark = ""
        if applied in _MARKS:
            mark = f'<p class="rio-week-meta">{_esc(applied)}</p>'
        with st.container(key=f"rio-week-{number}"):
            st.markdown(
                '<div class="rio-week-head">'
                '<h2 class="rio-week-title">'
                f'<span class="rio-week-num">Week {number}</span>'
                '<span class="rio-week-sep">·</span>'
                f'<span class="rio-week-phase">Phase {_esc(_phase_number(days))}</span>'
                "</h2>"
                f"{mark}"
                "</div>",
                unsafe_allow_html=True,
            )
            if not days:
                st.markdown('<p class="rio-empty">—</p>', unsafe_allow_html=True)
            else:
                with st.container(key=f"rio-days-{number}", gap=None):
                    for index, session in enumerate(days):
                        _session_link(session, "row", first=index == 0)
                with st.expander("Reason codes", key=f"season-reasons-{generation}-{number}"):
                    lines = []
                    for session in days:
                        lines.append(
                            '<p class="rio-reason">'
                            f'<span>{_esc(session["day_of_week"])} {_esc(_date_text(session["date"]))}</span>'
                            f'{_esc(_reason_text(session["reason_codes"]))}'
                            "</p>"
                        )
                    st.markdown("".join(lines), unsafe_allow_html=True)
            _render_mark(plan, number, generation)


def page_start() -> None:
    """Four inputs. Generate calls sequence() and opens Home."""
    st.markdown(_css(), unsafe_allow_html=True)
    _render_nav("")
    st.markdown(
        _page_hero("Start", "SYNTHETIC / DEMO", "Current 800, the start, the goal, the date."),
        unsafe_allow_html=True,
    )
    _seed_start_form()
    with st.container(key="rio-start"):
        current_time = st.text_input(
            "Current 800",
            key="start_current_time",
            **_fresh_value("start_current_time", "2:02.9"),
        )
        start_date = st.date_input(
            "Start date",
            key="start_start_date",
            **_fresh_value("start_start_date", date(2026, 4, 19)),
        )
        goal_time = st.text_input(
            "Goal 800",
            key="start_goal_time",
            **_fresh_value("start_goal_time", "1:55.0"),
        )
        goal_date = st.date_input(
            "Goal date",
            key="start_goal_date",
            **_fresh_value("start_goal_date", date(2027, 3, 19)),
        )
        if not st.button("Generate", type="primary", width="stretch"):
            return
        try:
            _generate_season(current_time, start_date, goal_time, goal_date)
        except ValueError as exc:
            st.markdown(
                f'<p class="rio-error">{_esc(exc)}</p>',
                unsafe_allow_html=True,
            )
            return
        home = _nav_page("Home")
        if home is None:
            return
        st.switch_page(
            home,
            query_params=query_values(st.session_state["season_inputs"]),
        )


def _session_activity(session: dict, generation: int) -> dict | None:
    """The file chosen on this page, the matched activity, or the stored file.

    A chosen file is read from disk. A match uses the heart rate already stored
    with it. This does not call Intervals.icu.
    """
    day = str(session.get("date") or "")
    selected = st.session_state.get(f"season-result-{generation}-{day}-intervals")
    if isinstance(selected, str) and selected.strip() not in ("", "—"):
        return activity_by_ref(selected)
    match = matched_on(_stored_activities(), day)
    if isinstance(match, dict) and match.get("heart_rate") is not None:
        return {"average_heartrate": match["heart_rate"]}
    saved = _actuals().get(day)
    if not isinstance(saved, dict) or saved.get("template_id") != session.get("template_id"):
        return None
    return activity_by_ref(saved.get("intervals"))


def _progress_html(row: dict) -> str:
    """One checklist row. An unmarked past week keeps a blank status."""
    status = row["status"] or "—"
    kind = row["status"] or "open"
    volume = display_distance(row.get("volume") or "—", _prefs()["units"])
    return (
        f'<div class="rio-progress rio-progress-{kind}">'
        '<span class="rio-progress-tick"></span>'
        f'<div class="rio-progress-week">Week {_esc(row["week"])}</div>'
        '<div class="rio-progress-phase">'
        f'Phase {_esc(row["phase"])}'
        f'<div class="rio-progress-volume">{_esc(volume)}</div>'
        "</div>"
        f'<div class="rio-progress-status">{_esc(status)}</div>'
        f'<div class="rio-progress-days">{_esc(days_label(row["days_remaining"]))}</div>'
        "</div>"
    )


def _phase_text(phase: object) -> str:
    text = str(phase or "").strip()
    if not text or text == "—":
        return "—"
    return f"Phase {text}"


def _mark_text(mark: dict | None) -> str:
    if not isinstance(mark, dict):
        return "—"
    week = mark.get("week")
    name = mark.get("mark")
    if isinstance(week, bool) or not isinstance(week, int) or name not in _MARKS:
        return "—"
    return f"Week {week} · {name}"


def _dash_hero(workout: dict) -> None:
    """Day, date, and the plain workout. The block opens that session."""
    day = str(workout.get("day_of_week") or "—")
    when = str(workout.get("date") or "—")
    plain = _workout_text(workout.get("template_id"))
    html = (
        '<div class="rio-next">'
        '<p class="rio-mark-label">Next workout</p>'
        f'<div class="rio-next-day">{_esc(day)}</div>'
        f'<p class="rio-range">{_esc(_date_text(when))}</p>'
        f'<p class="rio-next-work">{_esc(plain)}</p>'
        f'{_id_html(workout.get("template_id"), "rio-next-id")}'
        "</div>"
    )
    page = _SESSION_PAGE
    if page is None or when == "—":
        st.markdown(html, unsafe_allow_html=True)
        return
    with st.container(key="rio-hit-dash", gap=None):
        st.markdown(html, unsafe_allow_html=True)
        st.page_link(
            page,
            label=f"{day} {when}. {plain}",
            icon="",
            query_params=_link_params({"date": when}),
            width="stretch",
        )


def _upcoming_days(sessions: list, today: date, count: int = 3) -> list:
    """The next sessions on or after today. Display only. The plan is unchanged."""
    rows = []
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        text = session.get("date")
        if not isinstance(text, str):
            continue
        try:
            day = date.fromisoformat(text)
        except ValueError:
            continue
        if day >= today:
            rows.append(session)
    rows.sort(key=lambda item: str(item.get("date")))
    return rows[:count]


def _phase_timeline(start: date, length: int, sessions: list) -> str:
    """One cell per week. The number is the phase already stored on that week."""
    grouped = dict(_weeks(sessions))
    current = _week_containing(start, length, date.today())
    cells = []
    for number in range(1, length + 1):
        phase = _phase_number(grouped.get(number, []))
        kind = " rio-phase-now" if number == current else ""
        cells.append(
            f'<div class="rio-phase{kind}">'
            f'<div class="rio-phase-week">W{number}</div>'
            f'<div class="rio-phase-num">{_esc(phase)}</div>'
            "</div>"
        )
    return f'<div class="rio-phases">{"".join(cells)}</div>'


def _home_stats(view: dict) -> str:
    remaining = view.get("days_remaining")
    number = str(remaining) if isinstance(remaining, int) and not isinstance(remaining, bool) else "—"
    return (
        '<header class="rio-hero">'
        '<p class="rio-synthetic">SYNTHETIC / DEMO</p>'
        '<div class="rio-stats">'
        '<div class="rio-stat">'
        '<p class="rio-mark-label">Days to goal</p>'
        f'<h1 class="rio-key">{_esc(number)}</h1>'
        "</div>"
        '<div class="rio-stat">'
        '<p class="rio-mark-label">Current phase</p>'
        f'<p class="rio-stat-value">{_esc(_phase_text(view.get("phase")))}</p>'
        "</div>"
        "</div>"
        "</header>"
    )


def _quick_links() -> None:
    items = (
        ("Plan", _nav_page("Plan")),
        ("Activity", _nav_page("Activity")),
        ("Library", _nav_page("Library")),
        ("More", _nav_page("More")),
    )
    links = [(label, page) for label, page in items if page is not None]
    if not links:
        return
    st.markdown('<p class="rio-mark-label">Open</p>', unsafe_allow_html=True)
    with st.container(key="rio-quick", horizontal=True, gap="small"):
        for label, page in links:
            with st.container(key=f"rio-quick-{label.lower()}", width="content"):
                st.page_link(
                    page,
                    label=label,
                    icon="",
                    query_params=_link_params(),
                    width="content",
                )


def page_dashboard() -> None:
    """The plan Start stored, as of today.

    The next workout is the first session on or after today. The phase and
    the one-line focus are that week's, from reason codes already stored.
    The last mark is the latest week mark, when one exists. Days until the
    goal count from today. Opening this page reads the last 14 days and
    matches each activity to that date. An unmarked quality day can already
    hold the mark from those WORK times. An unmatched activity is an extra
    session. No prose, so this page does not spend. No scores.
    """
    chrome = st.container(gap=None)
    hero = st.container(gap=None)
    with chrome:
        st.markdown(_css(), unsafe_allow_html=True)
        _render_nav("Home")

    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        with hero:
            if error:
                st.markdown(
                    '<header class="rio-hero">'
                    '<p class="rio-synthetic">SYNTHETIC / DEMO</p>'
                    "<h1>Home</h1>"
                    f'<p class="rio-error">{_esc(error)}</p></header>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    _page_hero("Home", "SYNTHETIC / DEMO"),
                    unsafe_allow_html=True,
                )
        if not error:
            st.markdown(
                '<p class="rio-empty">Generate a season on Start.</p>',
                unsafe_allow_html=True,
            )
        return

    length = plan.get("season_length_weeks")
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        with hero:
            st.markdown(_page_hero("Home", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
        st.markdown('<p class="rio-empty">—</p>', unsafe_allow_html=True)
        return

    marks = st.session_state.get("season_marks")
    view = dashboard_view(
        start=start,
        goal=goal,
        length=length,
        sessions=sessions,
        marks=marks if isinstance(marks, dict) else {},
        today=date.today(),
    )
    workout = view.get("next")
    with hero:
        st.markdown(_home_stats(view), unsafe_allow_html=True)
        if isinstance(workout, dict):
            _dash_hero(workout)
        else:
            st.markdown(
                '<p class="rio-empty">No workout left in this plan.</p>',
                unsafe_allow_html=True,
            )
    _activities_notice()
    st.markdown(
        '<div class="rio-grid">'
        '<div class="rio-card">'
        + _label("Last mark")
        + f'<p class="rio-stat-value">{_esc(_mark_text(view["mark"]))}</p>'
        + "</div>"
        '<div class="rio-card">'
        + _label("This week")
        + f'<p class="rio-stat-value">{_esc(view["focus"])}</p>'
        + "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    upcoming = _upcoming_days(sessions, date.today(), 3)
    if upcoming:
        st.markdown('<p class="rio-mark-label">Next 3 days</p>', unsafe_allow_html=True)
        with st.container(key="rio-next3", horizontal=True, gap="small"):
            for session in upcoming:
                _session_link(session, "mini")
    _quick_links()
    oldest, newest = activity_window(date.today())
    _render_extras(extras_between(_stored_activities(), oldest, newest))


_CAL_DOW = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


def _cal_cell(cell: dict) -> None:
    """One day. A session opens that day. An empty day stays a date."""
    in_month = bool(cell.get("in_month"))
    label = str(cell.get("label") or "") if in_month else ""
    template = str(cell.get("template_id") or "") if in_month else ""
    number = cell.get("day") if in_month else ""
    classes = ["rio-cal-day"]
    if not in_month:
        classes.append("rio-cal-out")
    elif template:
        classes.append("rio-cal-session")
    else:
        classes.append("rio-cal-quiet")
    if cell.get("today") and in_month:
        classes.append("rio-cal-today")
    html = (
        f'<div class="{" ".join(classes)}">'
        f'<div class="rio-cal-num">{_esc(number) if number else ""}</div>'
        f'<div class="rio-cal-label">{_esc(label)}</div>'
        "</div>"
    )
    page = _SESSION_PAGE
    when = str(cell.get("date") or "")
    if page is None or not template or not when:
        st.markdown(html, unsafe_allow_html=True)
        return
    with st.container(key=f"rio-hit-cal-{when}", gap=None):
        st.markdown(html, unsafe_allow_html=True)
        st.page_link(
            page,
            label=f"{when}. {label or 'Session'}",
            icon="",
            query_params=_link_params({"date": when}),
            width="stretch",
        )


def page_calendar() -> None:
    """One month of the plan Start stored.

    The grid opens on the month that contains today. A session day shows a
    short label and opens that session. Race is only the 800 race. No prose,
    so this page does not spend. No scores.
    """
    chrome = st.container(gap=None)
    hero = st.container(gap=None)
    with chrome:
        st.markdown(_css(), unsafe_allow_html=True)
        _render_nav("Calendar")

    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        with hero:
            if error:
                st.markdown(
                    '<header class="rio-hero">'
                    '<p class="rio-synthetic">SYNTHETIC / DEMO</p>'
                    "<h1>Calendar</h1>"
                    f'<p class="rio-error">{_esc(error)}</p></header>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    _page_hero("Calendar", "SYNTHETIC / DEMO"),
                    unsafe_allow_html=True,
                )
        if not error:
            st.markdown(
                '<p class="rio-empty">Generate a season on Start.</p>',
                unsafe_allow_html=True,
            )
        return

    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    months = plan_months(sessions)
    if not months:
        with hero:
            st.markdown(_page_hero("Calendar", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
        st.markdown('<p class="rio-empty">—</p>', unsafe_allow_html=True)
        return

    generation = int(st.session_state.get("season_generation") or 0)
    titles = [month_title(item) for item in months]
    key = f"calendar-month-{generation}"
    if key not in st.session_state or st.session_state.get(key) not in titles:
        st.session_state[key] = month_title(opening_month(months, date.today()))
    month = months[titles.index(st.session_state[key])]
    with hero:
        st.markdown(
            _page_hero(month_title(month), "SYNTHETIC / DEMO"),
            unsafe_allow_html=True,
        )
        with st.container(key="rio-pick-month", gap=None):
            st.selectbox("Month", titles, key=key)
    weeks = month_weeks(month.year, month.month, sessions, today=date.today())
    with st.container(key="rio-cal", gap="small"):
        with st.container(key="rio-cal-head", gap=None):
            heads = st.columns(7, gap="small")
            for column, name in zip(heads, _CAL_DOW):
                with column:
                    st.markdown(
                        f'<div class="rio-cal-dow">{_esc(name)}</div>',
                        unsafe_allow_html=True,
                    )
        for index, week in enumerate(weeks):
            with st.container(key=f"rio-cal-week-{index}", gap=None):
                columns = st.columns(7, gap="small")
                for column, cell in zip(columns, week):
                    with column:
                        _cal_cell(cell)


def _library_html(rows: list[dict]) -> str:
    parts = []
    show_ids = _prefs()["show_ids"]
    for row in rows:
        ident = (
            f'<div class="rio-lib-id">{_esc(row["id"])}</div>' if show_ids else ""
        )
        parts.append(
            '<div class="rio-lib-row">'
            '<div class="rio-lib-main">'
            f'<div class="rio-lib-name">{_esc(_copy(row["description"]))}</div>'
            f"{ident}"
            "</div>"
            f'<div class="rio-lib-cap">{_esc(row["capacity"])}</div>'
            "</div>"
        )
    return f'<div class="rio-lib">{"".join(parts)}</div>'


def page_library() -> None:
    """Every template on the frozen menu.

    Search matches the name, the id, or the capacity. Capacity and phase
    each narrow the same list. The phase list is the one the season already
    uses. No prose, so this page does not spend. No scores.
    """
    st.markdown(_css(), unsafe_allow_html=True)
    _render_nav("Library")
    st.markdown(_page_hero("Library", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
    try:
        menu = load_menu()
    except ValueError as exc:
        st.markdown(f'<p class="rio-error">{_esc(exc)}</p>', unsafe_allow_html=True)
        return
    rows = library_rows(menu)
    families = []
    for row in rows:
        family = row["family"]
        if family and family not in families:
            families.append(family)
    families.sort(key=lambda family: next(
        (item["capacity"] for item in rows if item["family"] == family),
        family,
    ))
    labels = {
        row["family"]: row["capacity"]
        for row in rows
        if row["family"]
    }
    with st.container(key="rio-library"):
        query = st.text_input("Search", key="library-search", placeholder="Search workouts")
        left, right = st.columns(2, gap="small")
        with left:
            family = st.selectbox(
                "Capacity",
                ["All", *families],
                format_func=lambda item, names=labels: names.get(item, item),
                key="library-capacity",
            )
        with right:
            phase = st.selectbox(
                "Phase",
                ["All", *range(1, 9)],
                format_func=lambda item: item if item == "All" else f"Phase {item}",
                key="library-phase",
            )
    chosen_family = "" if family == "All" else str(family)
    chosen_phase = None if phase == "All" else phase
    visible = filter_workouts(
        rows,
        query=query,
        family=chosen_family,
        phase=chosen_phase,
    )
    noun = "workout" if len(visible) == 1 else "workouts"
    st.markdown(
        f'<p class="rio-week-meta rio-lib-count">{len(visible)} {noun}</p>',
        unsafe_allow_html=True,
    )
    if not visible:
        st.markdown('<p class="rio-empty">No workouts.</p>', unsafe_allow_html=True)
        return
    st.markdown(_library_html(visible), unsafe_allow_html=True)


def page_progress() -> None:
    """Weeks of the plan Start stored.

    The week that contains today is current. Any other week that already
    has a mark is done. A week after today with no mark is upcoming.
    A done week has no countdown. The current week counts from today.
    An upcoming week counts from the Saturday that closes it.
    Volume sums WORK interval distance from a loaded Intervals file. A matched
    activity uses that activity's WORK distance for its day. Warm-up and
    cool-down stay out. A day with neither contributes 0. A week with neither
    shows 0 m. A line plots that same weekly distance, and a week with no
    file stays at 0. A dot marks each matched activity that has an average
    heart rate, labeled with the day and the value. A day with no heart rate
    is left blank. Template meters are not used. Opening this page reads the
    last 14 days and matches each activity to that date. No prose, so this
    page does not spend. No scores.
    """
    chrome = st.container(gap=None)
    hero = st.container(gap=None)
    with chrome:
        st.markdown(_css(), unsafe_allow_html=True)
        _render_nav("Progress")

    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        with hero:
            if error:
                st.markdown(
                    '<header class="rio-hero">'
                    '<p class="rio-synthetic">SYNTHETIC / DEMO</p>'
                    "<h1>Progress</h1>"
                    f'<p class="rio-error">{_esc(error)}</p></header>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    _page_hero("Progress", "SYNTHETIC / DEMO"),
                    unsafe_allow_html=True,
                )
        if not error:
            st.markdown(
                '<p class="rio-empty">Generate a season on Start.</p>',
                unsafe_allow_html=True,
            )
        return

    length = plan.get("season_length_weeks")
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        with hero:
            st.markdown(_page_hero("Progress", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
        st.markdown('<p class="rio-empty">—</p>', unsafe_allow_html=True)
        return

    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    marks = st.session_state.get("season_marks")
    actuals = st.session_state.get("season_actuals")
    rows = progress_weeks(
        start=start,
        goal=goal,
        length=length,
        sessions=sessions,
        marks=marks if isinstance(marks, dict) else {},
        today=date.today(),
        distances=with_matched_distances(
            loaded_distances(sessions, actuals if isinstance(actuals, dict) else {}),
            _stored_activities(),
        ),
    )
    with hero:
        st.markdown(
            _page_hero(
                "Progress",
                "SYNTHETIC / DEMO",
                f"{_date_text(start)} — {_date_text(goal)} · {days_label(days_remaining(goal, date.today()))}",
            ),
            unsafe_allow_html=True,
        )
    chart = volume_chart(
        [row["meters"] for row in rows],
        _prefs()["units"],
        [display_distance(str(row.get("volume") or ""), _prefs()["units"]) for row in rows],
    )
    if chart:
        st.markdown(chart, unsafe_allow_html=True)
    heart = heart_rate_chart(
        matched_heart_rates(_stored_activities()),
        start=start,
        weeks=length,
    )
    if heart:
        st.markdown(heart, unsafe_allow_html=True)
    st.markdown(
        f'<div class="rio-progress-list">{"".join(_progress_html(row) for row in rows)}</div>',
        unsafe_allow_html=True,
    )


def page_weekly() -> None:
    """One week of the plan Start stored.

    The control opens any week. The week that contains today is the one
    shown first. The recap reads that week: sessions already recorded, the
    marks already stored, WORK interval distance from loaded Intervals files
    beside the week before, and one sentence from adapt codes already on
    the next week. Warm-up and cool-down stay out. A day with no file
    contributes 0. A week with no file shows 0 m. Template meters are not
    used. Each day is a card:
    the day, the date, the plain workout, and the target outcome. A matched
    day adds that activity's rep times, WORK distance, and heart rate. An
    activity with no planned session on its date is an extra session. A card
    opens that session. Opening this page reads the last 14 days and matches
    each activity to that date. The mark calls adapt() for that week.
    No prose, so this page does not spend.
    """
    chrome = st.container(gap=None)
    hero = st.container(gap=None)
    with chrome:
        st.markdown(_css(), unsafe_allow_html=True)
        _render_nav("Weekly")

    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        with hero:
            if error:
                st.markdown(
                    '<header class="rio-hero">'
                    '<p class="rio-synthetic">SYNTHETIC / DEMO</p>'
                    "<h1>Weekly</h1>"
                    f'<p class="rio-error">{_esc(error)}</p></header>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    _page_hero("Weekly", "SYNTHETIC / DEMO"),
                    unsafe_allow_html=True,
                )
        if not error:
            st.markdown(
                '<p class="rio-empty">Generate a season on Start.</p>',
                unsafe_allow_html=True,
            )
        return

    length = plan["season_length_weeks"]
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        with hero:
            st.markdown(_page_hero("Weekly", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
        st.markdown('<p class="rio-empty">—</p>', unsafe_allow_html=True)
        return

    generation = int(st.session_state.get("season_generation") or 0)
    numbers = list(range(1, length + 1))
    default = _week_containing(start, length, date.today())
    key = f"weekly-week-{generation}"
    picked = st.session_state.get(key, default)
    if isinstance(picked, bool) or not isinstance(picked, int) or picked not in numbers:
        picked = default
    days = dict(_weeks(plan["sessions"])).get(picked, [])

    with hero:
        st.markdown(_weekly_hero(picked, start, days), unsafe_allow_html=True)
        with st.container(key="rio-pick-week", gap=None):
            st.selectbox(
                "Week",
                numbers,
                index=numbers.index(default),
                format_func=lambda item, start_day=start: _week_option(start_day, item),
                key=key,
            )

    _activities_notice()
    sessions = plan.get("sessions") or []
    actuals = st.session_state.get("season_actuals")
    recap = recap_view(
        week=picked,
        sessions=sessions,
        actuals=actuals,
        marks=st.session_state.get("season_marks"),
        distances=with_matched_distances(
            loaded_distances(sessions, actuals if isinstance(actuals, dict) else {}),
            _stored_activities(),
        ),
    )
    _card(
        _label("Recap"),
        _fields(
            [
                ("Sessions", recap["completed"]),
                ("Marks", recap["marks"]),
                ("Volume", display_distance(recap["volume"], _prefs()["units"])),
                ("Next week", recap["next"]),
            ]
        ),
    )

    if not days:
        st.markdown('<p class="rio-empty">—</p>', unsafe_allow_html=True)
    else:
        for session in days:
            _session_link(session, "card")
    sunday = _week_sunday(start, picked)
    _render_extras(extras_between(_stored_activities(), sunday, sunday + timedelta(days=6)))

    applied = (st.session_state.get("season_marks") or {}).get(picked)
    with st.container(key="rio-week-mark"):
        if applied in _MARKS:
            st.markdown(
                f'<p class="rio-week-meta">{_esc(applied)}</p>',
                unsafe_allow_html=True,
            )
        _render_mark(plan, picked, generation)


def page_season() -> None:
    """The plan sequence() returned from Start.

    Sessions are grouped by week and ordered Sunday through Saturday.
    Each row shows that day's calendar date. A row opens that session.
    A mark calls adapt() for that week and shows the plan it returns.
    No recorded workouts.
    """
    chrome = st.container(gap=None)
    hero = st.container(gap=None)

    with chrome:
        st.markdown(_css(), unsafe_allow_html=True)
        _render_nav("Season")

    plan, start, goal, error = _stored_season()
    with hero:
        st.markdown(_hero_html(start, goal, plan, error), unsafe_allow_html=True)
    if plan is None or start is None or goal is None:
        return
    _render_schedule(plan, int(st.session_state.get("season_generation") or 0))


def _prep_lines(session: dict) -> str:
    """Warm-up, cool-down, and core. Fixed copy. Quality days include core.

    The lines stay on the page. They are not written onto the session, so
    adapt() never reads them. No score.
    """
    lines = [
        ("Warm-up", "Do a warm-up."),
        ("Cool-down", "Do a cool-down."),
    ]
    if _quality_day(session):
        lines.append(("Core", "Do core."))
    rows = "".join(
        f'<p class="rio-prep-line"><span>{_esc(label)}:</span> {_esc(text)}</p>'
        for label, text in lines
    )
    return f'<div class="rio-prep">{rows}</div>'


def _supplied_html(match: object) -> str:
    """Rep times, completed WORK distance, and average heart rate from a match.

    These are the numbers stored from Intervals, shown beside the template.
    The time boxes stay separate and editable. Nothing here is written back.
    """
    if not isinstance(match, dict):
        return ""
    pairs: list[tuple[str, str]] = []
    reps = filled_times(match.get("reps") or [])
    if reps:
        pairs.append(("Reps", reps))
    volume = meters_text(match.get("work_m"))
    shown = display_distance(volume, _prefs()["units"]) if volume else ""
    if shown:
        pairs.append(("Work", shown))
    if match.get("heart_rate") is not None:
        text = heart_rate_text({"average_heartrate": match.get("heart_rate")})
        if text:
            pairs.append(("Avg HR", text))
    if not pairs:
        return ""
    return (
        '<div class="rio-supplied">'
        '<p class="rio-mark-label">Intervals</p>'
        f"{_fields(pairs)}"
        "</div>"
    )


def page_session() -> None:
    """One session from the plan Start stored.

    Season and Weekly link here with the session date. The workout words,
    the structure, the three placeholder lines, and the reason words are
    fixed. A Tuesday or Thursday quality day takes one time per rep and
    calls adapt(). Choosing an Intervals JSON file reads it locally and
    fills each box with that WORK interval's elapsed time. A matched
    quality day fills those same boxes from the stored WORK times. The
    numbers stay editable. Filled times go through judge(). The activity
    id or the filename is stored with the actuals. When that activity JSON
    has an average heart rate, the page shows it. A matched activity shows
    its rep times, its completed WORK distance, and that heart rate beside
    the template. An extra session
    opens on its own. A continuous session takes one time. This page does
    not call a model and does not spend. Nothing is written to Intervals.
    """
    chrome = st.container(gap=None)
    hero = st.container(gap=None)
    with chrome:
        st.markdown(_css(), unsafe_allow_html=True)
        _render_nav("")

    plan, start, goal, error = _stored_season()
    logged = activity_by_id(_stored_activities(), _query_activity())
    if isinstance(plan, dict) and isinstance(logged, dict) and logged.get("matched") is False:
        day = str(logged.get("date") or "")
        with hero:
            st.markdown(
                _page_hero(
                    weekday_name(day) or "Activity",
                    "SYNTHETIC / DEMO",
                    _date_text(day) if day else None,
                ),
                unsafe_allow_html=True,
            )
        _render_logged_activity(logged)
        return
    chosen = _query_date()
    session = _session_on(plan, chosen) if isinstance(plan, dict) else None
    with hero:
        if session is None:
            st.markdown(_page_hero("Session", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
        else:
            st.markdown(
                _page_hero(
                    str(session["day_of_week"]),
                    "SYNTHETIC / DEMO",
                    _date_text(session["date"]),
                ),
                unsafe_allow_html=True,
            )
    if plan is None or start is None or goal is None:
        if error:
            st.markdown(
                f'<p class="rio-error">{_esc(error)}</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<p class="rio-empty">Generate a season on Start.</p>',
                unsafe_allow_html=True,
            )
        return
    if not chosen:
        st.markdown(
            '<p class="rio-empty">Open a workout from Home or Plan.</p>',
            unsafe_allow_html=True,
        )
        return
    if session is None:
        st.markdown(
            '<p class="rio-empty">That session is not in this plan.</p>',
            unsafe_allow_html=True,
        )
        return
    match = matched_on(_stored_activities(), str(session.get("date") or ""))
    supplied = _supplied_html(match)
    workout = (
        '<div class="rio-session-plan">'
        f'{_subject("Workout", _workout_text(session["template_id"]))}'
        f'{_id_html(session["template_id"])}'
        "</div>"
    )
    if supplied:
        workout = f'<div class="rio-session-split">{workout}{supplied}</div>'
    parts = [
        workout,
        _label("Structure"),
        _note(_structure_text(session["template_id"])),
        _label("Target outcome"),
        _note(_copy(str(session.get("target_outcome") or "—"))),
        _prep_lines(session),
    ]
    activity = _session_activity(session, int(st.session_state.get("season_generation") or 0))
    hr = heart_rate_text(activity)
    match_hr = None
    if isinstance(match, dict) and match.get("heart_rate") is not None:
        match_hr = heart_rate_text({"average_heartrate": match.get("heart_rate")})
    if hr is not None and hr != match_hr:
        parts.extend((_label("Avg HR"), _note(hr)))
    parts.extend(
        (
            _label("Reasons"),
            _plain_reasons(session.get("reason_codes") or []),
        )
    )
    _card(*parts)
    if _quality_day(session):
        _render_result(plan, session, int(st.session_state.get("season_generation") or 0))


def _data_value(value: object) -> str:
    text = "" if value is None else str(value).strip()
    if text == "not pulled.":
        return '<span class="rio-missing">not pulled.</span>'
    return _esc(_plain(value))


def _data_table(rows: list[dict]) -> str:
    if not rows:
        return '<p class="rio-empty">—</p>'
    headers = list(rows[0].keys())
    head = "".join(f"<th>{_esc(header)}</th>" for header in headers)
    body = []
    for row in rows:
        cells = "".join(f"<td>{_data_value(row.get(header))}</td>" for header in headers)
        body.append(f"<tr>{cells}</tr>")
    return (
        '<div class="rio-table-wrap"><table class="rio-table"><thead><tr>'
        f"{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def _activity_banner(activities: object, actuals: object) -> str | None:
    """SYNTHETIC / FIXTURE when a stored match or a chosen file says synthetic."""
    for row in activities or []:
        found = activity_banner(row)
        if found:
            return found
    if not isinstance(actuals, dict):
        return None
    for row in actuals.values():
        if not isinstance(row, dict):
            continue
        found = activity_banner({"name": row.get("intervals"), "id": row.get("intervals")})
        if found:
            return found
    return None


def _activity_date_captions(rows: list[dict]) -> dict[str, str]:
    """Visible heart-rate labels. Each dot uses the session date."""
    captions: dict[str, str] = {}
    for row in rows:
        day = row.get("date")
        shown = row.get("shown_date")
        if not isinstance(day, str) or not day or not isinstance(shown, str):
            continue
        text = shown.strip()
        if text and text != "—":
            captions[day] = text
    return captions


def _all_activities_table(rows: list[dict]) -> str:
    """Date, activity name, distance, and average heart rate.

    An unmatched row is labeled extra. A matched row leaves that label blank.
    """
    if not rows:
        return '<p class="rio-empty">—</p>'
    units = _prefs()["units"]
    headers = ("Date", "Activity", "Distance", "Avg HR", "")
    head = "".join(f"<th>{_esc(header)}</th>" for header in headers)
    body = []
    for row in rows:
        distance = str(row.get("distance") or "—")
        if row.get("meters") is not None:
            distance = display_distance(distance, units) or distance
        values = (
            row.get("shown_date") or "—",
            row.get("name") or "—",
            distance,
            row.get("hr") or "—",
        )
        cells = "".join(f"<td>{_data_value(value)}</td>" for value in values)
        label = "extra" if row.get("extra") else ""
        cells += f"<td>{_esc(label)}</td>" if label else "<td></td>"
        body.append(f"<tr>{cells}</tr>")
    return (
        '<div class="rio-table-wrap"><table class="rio-table"><thead><tr>'
        f"{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def _activity_table(rows: list[dict]) -> str:
    """Date, template or label, work meters, and average heart rate."""
    units = _prefs()["units"]
    show_ids = _prefs()["show_ids"]
    table = []
    for row in rows:
        label = str(row.get("label") or "—")
        template_id = str(row.get("template_id") or "").strip()
        if show_ids and template_id and template_id not in label:
            label = f"{label} · {template_id}"
        work = str(row.get("work") or "—")
        if row.get("meters") is not None:
            work = display_distance(work, units) or work
        table.append(
            {
                "Date": row.get("shown_date") or "—",
                "Workout": label,
                "Work": work,
                "Avg HR": row.get("hr") or "—",
            }
        )
    return _data_table(table)


def page_activity() -> None:
    """Matched Intervals workouts from the plan Start stored.

    Opening this page reads the last 14 days through the Intervals adapter
    and matches them to that plan by date. Refresh reads every activity.
    One row per matched session: date, template or label, work meters, and
    average heart rate. The line is weekly completed WORK distance. Warm-up and
    cool-down stay out. Template meters are not used. A dot marks each
    matched workout that has an average heart rate, labeled with the date.
    An unmatched activity stays off that list. A matched activity with no
    work meters and no heart rate stays off it. A second table lists every
    activity: date, activity name, activity distance, and average heart
    rate. An unmatched row is labeled extra. An activity with no distance
    and no heart rate stays off both lists. A day that already has a mark
    is left as stored.
    No stored match and no Intervals file leaves the matched list empty.
    No prose, so this page does not spend. No scores.
    """
    chrome = st.container(gap=None)
    hero = st.container(gap=None)
    with chrome:
        st.markdown(_css(), unsafe_allow_html=True)
        _render_nav("Activity")

    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        with hero:
            if error:
                st.markdown(
                    '<header class="rio-hero">'
                    '<p class="rio-synthetic">SYNTHETIC / DEMO</p>'
                    "<h1>Activity</h1>"
                    f'<p class="rio-error">{_esc(error)}</p></header>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    _page_hero("Activity", "SYNTHETIC / DEMO"),
                    unsafe_allow_html=True,
                )
        if not error:
            st.markdown(
                '<p class="rio-empty">Generate a season on Start.</p>',
                unsafe_allow_html=True,
            )
        return

    length = plan.get("season_length_weeks")
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        with hero:
            st.markdown(_page_hero("Activity", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
        st.markdown('<p class="rio-empty">—</p>', unsafe_allow_html=True)
        return

    activities = _stored_activities()
    actuals = st.session_state.get("season_actuals")
    stored_actuals = actuals if isinstance(actuals, dict) else {}
    distances = loaded_distances(sessions, stored_actuals)
    rates = file_heart_rates(sessions, stored_actuals)
    date_format = _prefs()["date_format"]
    rows = session_rows(
        activities,
        sessions,
        file_distances=distances,
        file_heart_rates=rates,
        date_format=date_format,
    )
    all_rows = all_activities(activities, date_format=date_format)
    with hero:
        st.markdown(
            _page_hero(
                "Activity",
                _activity_banner(activities, stored_actuals),
                f"{_date_text(start)} — {_date_text(goal)}",
            ),
            unsafe_allow_html=True,
        )
    with st.container(key="rio-activity-refresh"):
        st.button("Refresh", key="activity-refresh")
    _activities_notice()
    if not rows:
        st.markdown(
            '<p class="rio-empty">No matched activities.</p>',
            unsafe_allow_html=True,
        )
    else:
        units = _prefs()["units"]
        meters = weekly_completed_meters(rows, start=start, length=length)
        if meters:
            captions = [display_distance(f"{value:,} m", units) for value in meters]
            chart = volume_chart(meters, units, captions)
            if chart:
                st.markdown(chart, unsafe_allow_html=True)
        heart = heart_rate_chart(
            heart_rate_points(rows),
            start=start,
            weeks=length,
            captions=_activity_date_captions(rows),
        )
        if heart:
            st.markdown(heart, unsafe_allow_html=True)
        _card(_label("Sessions"), _activity_table(rows))
    if all_rows:
        _card(_label("All activities"), _all_activities_table(all_rows))
    _nest(page_progress)


def _setting_widgets(prefs: dict) -> None:
    """Seed the controls once. Later runs keep the widget value."""
    seed = {
        "settings-units": prefs["units"],
        "settings-ids": prefs["show_ids"],
        "settings-compact": prefs["compact"],
        "settings-dates": prefs["date_format"],
        "settings-confirm": prefs["confirm_adapt"],
        "settings-notes": prefs["notifications"],
    }
    for key, value in seed.items():
        if key not in st.session_state:
            st.session_state[key] = value


# Reads and writes this browser's goal time. The four Start inputs stay in the URL.
_PROFILE_STORE_JS = """
export default function (component) {
  var data = component.data;
  if (!data || typeof data.key !== "string" || !data.key) {
    return;
  }
  var key = data.key;
  if (data.mode === "write" && typeof data.payload === "string") {
    try {
      if (window.localStorage.getItem(key) !== data.payload) {
        window.localStorage.setItem(key, data.payload);
      }
    } catch (err) {}
  }
  var body = "";
  try {
    var stored = window.localStorage.getItem(key);
    body = stored === null ? "" : String(stored);
  } catch (err) {
    body = "";
  }
  var token = key + "\\n" + body;
  if (window.__rioProfileToken === token) {
    return;
  }
  window.__rioProfileToken = token;
  component.setStateValue("record", { key: key, body: body });
}
"""


def _profile_component():
    """The goal-time bridge. Registered once per process."""
    import ui.profile as profile

    cached = getattr(profile, "_browser_component", None)
    if cached is None:
        cached = st.components.v2.component(
            "rio_profile_store",
            js=_PROFILE_STORE_JS,
            isolate_styles=False,
        )
        profile._browser_component = cached
    return cached


def _mount_profile(data: dict, *, widget_key: str = "rio-profile-store"):
    """Mount the goal-time bridge. Read and write use different keys in one run."""
    return _profile_component()(
        key=widget_key,
        data=data,
        width="content",
        height="content",
    )


def _profile_slot(inputs: tuple[str, str, str, str]) -> dict:
    """This browser's saved goal, read once. A miss stays empty."""
    key = profile_key(inputs)
    slot = st.session_state.get("rio_profile")
    if isinstance(slot, dict) and slot.get("key") == key and slot.get("loaded") is True:
        return slot
    result = _mount_profile({"key": key, "mode": "read"})
    record = getattr(result, "record", None)
    if (
        not isinstance(record, dict)
        or record.get("key") != key
        or not isinstance(record.get("body"), str)
    ):
        st.stop()
    goal = load_goal(record["body"])
    slot = {"key": key, "loaded": True, "goal_time": goal, "dirty": False}
    st.session_state["rio_profile"] = slot
    return slot


def _write_profile(inputs: tuple[str, str, str, str]) -> None:
    """Save the goal time on this browser. The URL and the season stay put."""
    slot = st.session_state.get("rio_profile")
    key = profile_key(inputs)
    if not isinstance(slot, dict) or slot.get("key") != key or slot.get("dirty") is not True:
        return
    goal = clean_goal(slot.get("goal_time"))
    if goal is None:
        return
    _mount_profile(
        {"key": key, "mode": "write", "payload": dump_goal(goal)},
        widget_key="rio-profile-store-write",
    )
    st.session_state["rio_profile"] = {
        "key": key,
        "loaded": True,
        "goal_time": goal,
        "dirty": False,
    }


def page_profile() -> None:
    """The four values Start stored. The goal time can be saved in this browser.

    The saved time stays on this browser. The season stays as stored.
    No prose, so this page does not spend.
    """
    inputs = st.session_state.get("season_inputs")
    plan, _start, _goal_day, error = _stored_season()
    ready = plan is not None and inputs_ok(inputs)
    slot = _profile_slot(inputs) if ready else None
    hero, _controls = _open("Profile")
    if not ready or slot is None or not inputs_ok(inputs):
        with hero:
            if error:
                st.markdown(
                    '<header class="rio-hero">'
                    '<p class="rio-synthetic">SYNTHETIC / DEMO</p>'
                    "<h1>Profile</h1>"
                    f'<p class="rio-error">{_esc(error)}</p></header>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    _page_hero("Profile", "SYNTHETIC / DEMO"),
                    unsafe_allow_html=True,
                )
        if not error:
            st.markdown(
                '<p class="rio-empty">Generate a season on Start.</p>',
                unsafe_allow_html=True,
            )
        return

    goal_time = shown_goal(inputs[2], slot.get("goal_time"))
    with hero:
        st.markdown(_page_hero("Profile", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
    _card(
        _fields(
            profile_fields(
                inputs[0],
                _date_text(inputs[1]),
                goal_time,
                _date_text(inputs[3]),
            )
        )
    )
    pending = st.session_state.pop("profile_goal_apply", None)
    if isinstance(pending, str):
        st.session_state["profile_goal_time"] = pending
    with st.container(key="rio-profile-edit"):
        with st.form("profile-goal", border=False, clear_on_submit=False):
            draft = st.text_input(
                "Goal 800 time",
                key="profile_goal_time",
                **_fresh_value("profile_goal_time", goal_time),
            )
            submitted = st.form_submit_button("Save", type="primary", width="stretch")
        if submitted:
            cleaned = clean_goal(draft)
            if cleaned is None:
                st.markdown(
                    '<p class="rio-error">goal_time is not an 800 time</p>',
                    unsafe_allow_html=True,
                )
            else:
                st.session_state["rio_profile"] = {
                    "key": profile_key(inputs),
                    "loaded": True,
                    "goal_time": cleaned,
                    "dirty": True,
                }
                st.session_state["profile_goal_apply"] = cleaned
                st.rerun()
        if isinstance(slot.get("goal_time"), str) and slot.get("goal_time"):
            st.markdown(
                '<p class="rio-settings-note">Saved in this browser.</p>',
                unsafe_allow_html=True,
            )
    _write_profile(inputs)


def page_about() -> None:
    """The eight phases, the 10% rule, rules-based labels, and hard-day marks.

    Static copy. This page does not build a plan, label a workout, adapt a
    week, or call a model. Recorded prose spend stays at $25.
    """
    hero, _controls = _open("About")
    with hero:
        st.markdown(_page_hero("About"), unsafe_allow_html=True)
    for section in about_sections():
        parts = [_label(section["title"])]
        for index, paragraph in enumerate(section["paragraphs"]):
            parts.append(_note(paragraph) if index == 0 else _prose(paragraph))
        if section["rows"]:
            parts.append(_fields(section["rows"]))
        for paragraph in section["closing"]:
            parts.append(_prose(paragraph))
        _card(*parts)


def page_settings() -> None:
    """Display preferences for this browser session.

    Units, dates, template ids, and compact mode change what is shown.
    Confirm sits in front of adapt(). Notifications are stored and do
    nothing else. Nothing here is written onto the plan.
    """
    st.markdown(_css(), unsafe_allow_html=True)
    _render_nav("Settings")
    st.markdown(_page_hero("Settings", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
    _setting_widgets(_prefs())
    with st.container(key="rio-settings"):
        units = st.radio(
            "Units",
            ["km", "miles"],
            horizontal=True,
            key="settings-units",
        )
        show_ids = st.toggle("Show template ids", key="settings-ids")
        compact = st.toggle("Compact mode", key="settings-compact")
        date_format = st.radio(
            "Date format",
            ["iso", "short"],
            format_func=lambda item: "ISO" if item == "iso" else "Short",
            horizontal=True,
            key="settings-dates",
        )
        confirm = st.toggle("Confirm before adapt", key="settings-confirm")
        notifications = st.toggle("Notifications", key="settings-notes")
        st.markdown(
            '<p class="rio-settings-note">Placeholder. Nothing is sent.</p>',
            unsafe_allow_html=True,
        )
    stored = normalize_prefs(
        {
            "units": units,
            "show_ids": show_ids,
            "compact": compact,
            "date_format": date_format,
            "confirm_adapt": confirm,
            "notifications": notifications,
        }
    )
    if not stored["confirm_adapt"]:
        _clear_adapt()
    st.session_state["rio_settings"] = stored


def page_plan() -> None:
    """Season length, phase weeks, the month, and the schedule.

    Week cards and the full season keep their marks. A card opens that
    session. This page does not build a plan.
    """
    global _MARK_PREFIX
    st.markdown(_css(), unsafe_allow_html=True)
    _render_nav("Plan")
    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        if error:
            st.markdown(
                '<header class="rio-hero">'
                '<p class="rio-synthetic">SYNTHETIC / DEMO</p>'
                "<h1>Plan</h1>"
                f'<p class="rio-error">{_esc(error)}</p></header>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(_page_hero("Plan", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
            st.markdown(
                '<p class="rio-empty">Generate a season on Start.</p>',
                unsafe_allow_html=True,
            )
        return
    length = plan.get("season_length_weeks")
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        st.markdown(_page_hero("Plan", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
        st.markdown('<p class="rio-empty">—</p>', unsafe_allow_html=True)
        return
    st.markdown(
        _page_hero(
            _length_text(length),
            "SYNTHETIC / DEMO",
            f"{_date_text(start)} — {_date_text(goal)}",
        ),
        unsafe_allow_html=True,
    )
    phase = _phase_number(
        dict(_weeks(sessions)).get(_week_containing(start, length, date.today()), [])
    )
    note = ""
    if phase != "—":
        note = f'<p class="rio-note">This week is phase {_esc(phase)}.</p>'
    st.markdown(
        '<div class="rio-card rio-card-tight">'
        + _label("Phases")
        + note
        + _phase_timeline(start, length, sessions)
        + "</div>",
        unsafe_allow_html=True,
    )
    saved = _MARK_PREFIX
    try:
        _MARK_PREFIX = "plan-week"
        _nest(page_calendar)
        _nest(page_weekly)
        _MARK_PREFIX = "plan-season"
        _nest(page_season)
    finally:
        _MARK_PREFIX = saved


_MORE_BLURB = (
    ("Last Session", "A fixture or a local file, labeled by the rules."),
    ("Next", "The next one to three days from the ledger."),
    ("Decisions", "The accepted planned row."),
    ("Ledger", "Deposits, and what is emerging or decaying."),
    ("Goal", "The four fields as written."),
    ("Past seasons", "Seasons this browser already stored."),
    ("Profile", "The four Start values. The goal time can be saved here."),
    ("Settings", "Units, dates, template ids, and compact mode."),
    ("About", "Phases, the 10% rule, and what a mark changes."),
)


def page_more() -> None:
    """Ledger, goal, decisions, and the rest. Links stay in this tab."""
    st.markdown(_css(), unsafe_allow_html=True)
    _render_nav("More")
    st.markdown(
        _page_hero("More", "SYNTHETIC / DEMO", "The rest of the season, still in this tab."),
        unsafe_allow_html=True,
    )
    pages = {label: page for label, page in _MORE_PAGES}
    if not pages:
        st.markdown('<p class="rio-empty">—</p>', unsafe_allow_html=True)
        return
    for label, blurb in _MORE_BLURB:
        page = pages.get(label)
        if page is None:
            continue
        slug = label.lower().replace(" ", "-")
        html = (
            '<div class="rio-card rio-card-tight">'
            + _label(label)
            + f'<p class="rio-note">{_esc(blurb)}</p>'
            + "</div>"
        )
        with st.container(key=f"rio-hit-more-{slug}", gap=None):
            st.markdown(html, unsafe_allow_html=True)
            st.page_link(
                page,
                label=label,
                icon="",
                query_params=_link_params(),
                width="stretch",
            )


# Reads the plan keys already in this browser. It does not write a season.
_PAST_SEASONS_JS = """
export default function (component) {
  var data = component.data;
  if (!data || typeof data.prefix !== "string" || !data.prefix) {
    return;
  }
  var prefix = data.prefix;
  var keys = [];
  try {
    for (var i = 0; i < window.localStorage.length; i++) {
      var key = window.localStorage.key(i);
      if (typeof key === "string" && key.indexOf(prefix) === 0) {
        keys.push(key);
      }
    }
  } catch (err) {
    keys = [];
  }
  keys.sort();
  var token = prefix + "\\n" + keys.join("\\n");
  if (window.__rioPastSeasonsToken === token) {
    return;
  }
  window.__rioPastSeasonsToken = token;
  component.setStateValue("record", { prefix: prefix, keys: keys });
}
"""


def _past_component():
    """The stored-season bridge. Registered once per process."""
    import ui.past_seasons as past_seasons

    cached = getattr(past_seasons, "_browser_component", None)
    if cached is None:
        cached = st.components.v2.component(
            "rio_past_seasons",
            js=_PAST_SEASONS_JS,
            isolate_styles=False,
        )
        past_seasons._browser_component = cached
    return cached


def _mount_past(data: dict):
    """Mount the list bridge. The plan body stays unread."""
    return _past_component()(
        key="rio-past-seasons-store",
        data=data,
        width="content",
        height="content",
    )


def _stored_season_keys() -> list:
    """Plan keys in this browser. A miss waits for the bridge."""
    result = _mount_past({"prefix": KEY_PREFIX})
    record = getattr(result, "record", None)
    if (
        not isinstance(record, dict)
        or record.get("prefix") != KEY_PREFIX
        or not isinstance(record.get("keys"), list)
    ):
        st.stop()
    return record["keys"]


def _past_token(inputs: tuple[str, str, str, str]) -> str:
    raw = "-".join(inputs)
    token = "".join(char if char.isalnum() or char in "-_" else "-" for char in raw)
    return token[:180] or "season"


def _past_row(inputs: tuple[str, str, str, str], *, first: bool) -> str:
    """Start date, goal date, and goal time. The dates use the display format."""
    cells = []
    for label, value in entry_fields(inputs):
        shown = value if label == "Goal time" else _date_text(value)
        kind = " rio-past-time" if label == "Goal time" else ""
        cells.append(
            f'<div class="rio-past-cell{kind}">'
            f'<div class="rio-past-k">{_esc(label)}</div>'
            f'<div class="rio-past-v">{_esc(shown)}</div>'
            "</div>"
        )
    rule = "" if first else " rio-past-rule"
    return f'<div class="rio-past-row{rule}">{"".join(cells)}</div>'


def _open_past(inputs: tuple[str, str, str, str], *, first: bool) -> None:
    """The row opens Season with the four inputs already stored."""
    html = _past_row(inputs, first=first)
    page = _nav_page("Plan")
    if page is None:
        st.markdown(html, unsafe_allow_html=True)
        return
    with st.container(key=f"rio-hit-past-{_past_token(inputs)}", gap=None):
        st.markdown(html, unsafe_allow_html=True)
        st.page_link(
            page,
            label=f"{inputs[1]} {inputs[3]} {inputs[2]}",
            icon="",
            query_params=query_values(inputs),
            width="stretch",
        )


def page_past_seasons() -> None:
    """Seasons this browser already stored.

    Each row is a start date, a goal date, and a goal time from a plan key
    already in this browser. Choosing a row opens that season from those
    four inputs. Nothing here builds a season. No prose, so this page does
    not spend.
    """
    rows = season_entries(_stored_season_keys())
    hero, _controls = _open("Past seasons")
    with hero:
        st.markdown(_page_hero("Past seasons", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
    if not rows:
        st.markdown(
            '<p class="rio-empty">No seasons in this browser.</p>',
            unsafe_allow_html=True,
        )
        return
    with st.container(key="rio-past-list"):
        for index, inputs in enumerate(rows):
            _open_past(inputs, first=index == 0)


st.set_page_config(page_title="rio", layout="centered")
_start_page = st.Page(_with_plan(page_start), title="Start", default=True)
_session_page = st.Page(_with_plan(page_session), title="Session", url_path="session")
_HOME_PAGE = _start_page
_SESSION_PAGE = _session_page
_NAV_PAGES[:] = [
    ("Home", st.Page(_with_plan(page_dashboard), title="Home", url_path="home")),
    ("Plan", st.Page(_with_plan(page_plan), title="Plan", url_path="plan")),
    ("Activity", st.Page(_with_plan(page_activity), title="Activity", url_path="activity")),
    ("Library", st.Page(_with_plan(page_library), title="Library", url_path="library")),
    ("More", st.Page(_with_plan(page_more), title="More", url_path="more")),
]
_MORE_PAGES[:] = [
    ("Last Session", st.Page(_with_plan(page_last_session), title="Last Session", url_path="last-session")),
    ("Next", st.Page(_with_plan(page_next), title="Next", url_path="next")),
    ("Decisions", st.Page(_with_plan(page_decisions), title="Decisions", url_path="decisions")),
    ("Ledger", st.Page(_with_plan(page_ledger), title="Ledger", url_path="ledger")),
    ("Goal", st.Page(_with_plan(page_goal), title="Goal", url_path="goal")),
    ("Past seasons", st.Page(_with_plan(page_past_seasons), title="Past seasons", url_path="past-seasons")),
    ("Profile", st.Page(_with_plan(page_profile), title="Profile", url_path="profile")),
    ("Settings", st.Page(_with_plan(page_settings), title="Settings", url_path="settings")),
    ("About", st.Page(_with_plan(page_about), title="About", url_path="about")),
]
st.navigation(
    [
        _start_page,
        _session_page,
        *(page for _, page in _NAV_PAGES),
        *(page for _, page in _MORE_PAGES),
    ],
    position="hidden",
).run()
