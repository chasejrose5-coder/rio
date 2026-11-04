# streamlit_app.py — Start, Dashboard, Calendar, Library, Last Session, Activity, Next, Decisions, Ledger, Goal, Progress, Season, Past seasons, Weekly, Profile, Settings, About, and Session. Display only. No classification rules.

"""Start asks for four inputs and calls sequence(). Generate season writes current_time, start_date, goal_time, and goal_date into the URL. The first screen is the startup page. Continue opens Log in. A signed token in this browser keeps the email and seal key for one day. Each page load restores them when that token is under a day old. That page load opens Home when the account has a plan whose goal date is today or later, and Start when there is no plan or that goal date is past. Log out clears it, and so does a token that is a day old or older. Create account is its own screen. A successful create or log in opens Home when a stored plan's goal date is today or later, and Start when there is no plan or that goal date is past. Marks and actuals are saved on that account under those inputs. A page opened with the four inputs calls sequence() to rebuild the plan and restores that account's marks and actuals. Dashboard reads that plan: a track for the next session, with distance, pace, rest, and reps, plus the days until the goal, the current phase, the last mark, and one line for this week. Calendar shows that plan as a month. A session day carries a short label, and the day opens that session. Library lists the frozen menu. Last Session reads normalize, classify, and explain. Choosing a JSON file in tests/fixtures/intervals reads that file locally, runs to_normalize_input, then normalize, classify, and explain. The page does not call Intervals.icu. Activity lists one row per matched Intervals workout: the date, the template or label, completed work meters, and average heart rate. The line is weekly completed WORK distance. Warm-up, cool-down, and template meters stay out. A dot marks each matched workout that has an average heart rate, labeled with the date. An unmatched activity stays off that matched list. A matched activity with no work meters and no heart rate stays off it. A second table lists every activity: the date, the activity name, the activity distance, and average heart rate. An unmatched row is labeled extra. An activity with no distance and no heart rate stays off both lists. No stored match and no Intervals file leaves the matched list empty. That page does not call explain. Next reads prescribe and explain. Decisions reads one planned row and explain. Ledger and Goal read the ledger. Progress lists that plan by week and shows each week's completed work distance from WORK intervals in a loaded Intervals file. Warm-up and cool-down stay out. A day with no file contributes 0. A week with no file shows 0 m. A line on Progress plots that same weekly distance, and a week with no file stays at 0. Dots on Progress mark each matched activity that has an average heart rate, labeled with the day and the value. A day with no heart rate is left blank. Template meters are not used. Season shows that plan and reads adapt. Weekly shows one week of that plan, a recap of what was recorded, and reads adapt. Opening Dashboard, Weekly, Session, Progress, or Activity reads the last 14 days of activities with the local key and matches each activity to the planned session on that date. Refresh on Activity reads every activity for this athlete. A matched Tuesday or Thursday quality day with no stored mark is judged from that activity's WORK elapsed times. The mark and those times are stored with the session, and adapt() changes only later weeks. Those times fill the quality-day boxes and stay editable. A day that already has a mark is left as stored. Recovery days, long runs, extra activities, and empty rep times do not call adapt(). A matched day uses that activity for rep times, WORK distance, and average heart rate. An activity with no planned session is an extra session. The matches are saved on that account with the marks and actuals. Another athlete opening the link uses the key on their own machine. The recap volume sums those WORK distances for this week and the week before. A day with no file contributes 0. A week with no file shows 0 m. Template meters are not used. Create account asks for a name and stores it with the account. Home greets that name. Settings keeps the name, local preferences, and account actions on this machine. Profile shows the current 800 time, the start date, the goal 800 time, and the goal date already stored from Start. Saving a goal time keeps it for this account in this browser and leaves the season as stored. Past seasons lists each season this account has already stored. A row shows the start date, the goal date, and the goal time from that plan key. Choosing a row opens that season from those four inputs. The page does not build a season. Session shows one day of that plan. Fixed pre-warm-up, warm-up, cool-down, and core notes follow the workout and are not stored on the session. A matched activity shows its rep times, completed WORK distance, and average heart rate beside the template. Tuesday and Thursday quality take one time per rep and call adapt. Choosing an Intervals JSON file reads it locally and fills each rep box with that WORK interval's elapsed time. The numbers stay editable. Filled times go through judge() and can call adapt(). The activity id or the filename is stored with the actuals. Opening Session reads recent activities through the read-only adapter and does not write back to Intervals. When that activity JSON has an average heart rate, the page shows it. A continuous session takes one time. About states the eight phases, the 10% rule, that classification is rules, not AI, and that a hard-day mark adapts later weeks. About does not call a model. No scores. No spend."""

from __future__ import annotations

import sys
import time
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
from engines.pace import (
    PaceLog,
    effort_pace,
    format_pace,
    format_span,
    project_800,
    workout_recipe,
    workout_times,
)
from engines.prescribe import PARAMETER_KEYS, load_menu, prescribe
from engines.season import adapt, sequence
from ui.about import about_sections
from ui.calendar import month_title, month_weeks, opening_month, plan_months
from ui.library import filter_workouts, library_rows
from ui.activities import (
    PullError,
    activity_by_id,
    load_local_env,
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
from ui.cloud_config import cloud_configured, setup_notice_html
from ui.creators import CREATORS
from ui.dashboard import dashboard_view, mark_label, plain_marks, session_facts
from ui.hero_config import load_rotation, save_rotation
from ui.recap import recap_view
from ui.settings import (
    APP_VERSION,
    TIME_ZONES,
    display_distance,
    distance_heading,
    distance_number,
    format_date,
    normalize as normalize_prefs,
    start_on,
    suggested_timezone,
)
from ui.start_form import start_form_defaults
from ui.startup import acknowledge_startup, render_startup, startup_pending
from ui import theme
from ui.access import viewer_is_admin
from ui.accounts import (
    AccountError,
    account_rows,
    accounts_path,
    authenticate,
    change_email,
    change_password,
    create_account,
    delete_account,
    delete_records,
    hey,
    issue_session,
    last_key,
    normalize_name,
    open_session,
    plan_title,
    read_local,
    read_record,
    record_keys,
    shown_name,
    write_local,
    write_record,
)
from ui.plan_store import (
    dump_record,
    export_season,
    inputs_ok,
    load_record,
    plan_inputs,
    query_values,
    storage_key,
)
from ui.past_seasons import KEY_PREFIX, entry_fields, has_active_plan, inputs_from_key, season_entries
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


def _fixture_allowed() -> bool:
    """Fixture pages stay available to an admin. Everyone else goes home."""
    who = _account_identity()
    email = who[0] if who is not None else ""
    return viewer_is_admin(email)


def _open_home() -> None:
    home = _nav_page("Home")
    if home is None:
        st.stop()
    params = _link_params()
    if params:
        st.switch_page(home, query_params=params)
    else:
        st.switch_page(home)
    st.stop()


def page_last_session() -> None:
    """The fixture drop-down, or one local Intervals JSON file.

    A chosen JSON file is read from disk. Prose spend stays capped at $25
    in explain. This page does not call Intervals.icu.
    """
    if not _fixture_allowed():
        _open_home()
        return
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
    if not _fixture_allowed():
        _open_home()
        return
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
    if not _fixture_allowed():
        _open_home()
        return
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
    if not _fixture_allowed():
        _open_home()
        return
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
    if not _fixture_allowed():
        _open_home()
        return
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


# Browser bridge for a plan key. Pages read and write the signed-in account.
# The four inputs stay in the URL.
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
    if st.session_state.get("rio_test_preview"):
        return
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
    from ui.cloud_ui import persist_cloud_season

    persist_cloud_season()


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


# Cleared when the signed-in account changes, before the next screen draws widgets.
_ACCOUNT_SESSION = (
    "activities_loaded",
    "activities_notice",
    "activities_trigger",
    "profile_goal_apply",
    "profile_goal_time",
    "rio-log-out",
    "rio_adapt_pending",
    "rio_auth_screen",
    "rio_create_email",
    "rio_create_name",
    "rio_create_password",
    "rio_local",
    "rio_local_email",
    "rio_settings",
    "settings-clear-ok",
    "settings-compact",
    "settings-confirm",
    "settings-dates",
    "settings-delete-email",
    "settings-delete-ok",
    "settings-delete-password",
    "settings-email",
    "settings-ids",
    "settings-name",
    "settings-notes",
    "settings-preferred",
    "settings-recap",
    "settings-reminders",
    "settings-reset-ok",
    "settings-start",
    "settings-timezone",
    "settings-pace",
    "settings-units",
    "settings-clear-marks-ok",
    "rio_login_email",
    "rio_login_error",
    "rio_login_password",
    "rio_profile",
    "rio_store_loaded",
    "season_activities",
    "season_actuals",
    "season_generation",
    "season_inputs",
    "season_link_attempt",
    "season_link_error",
    "season_marks",
    "season_plan",
    "season_quality_base",
    "start_current_time",
    "start_goal_date",
    "start_goal_time",
    "start_start_date",
)


def _account_identity() -> tuple[str, str] | None:
    """The signed-in email and the seal key for this session."""
    email = st.session_state.get("rio_account")
    secret = st.session_state.get("rio_account_secret")
    if not isinstance(email, str) or not email:
        return None
    if not isinstance(secret, str) or not secret:
        return None
    return email, secret


def _apply_session_reset() -> None:
    """Drop the previous account's plan before the next screen is drawn."""
    if st.session_state.get("rio_reset_session") is not True:
        return
    for key in _ACCOUNT_SESSION:
        st.session_state.pop(key, None)
    st.session_state.pop("rio_reset_session", None)


# This browser keeps a signed token for one day. The account file does not.
_SESSION_STORE_JS = """
export default function (component) {
  var data = component.data || {};
  var mode = data.mode;
  if (mode !== "read" && mode !== "write" && mode !== "clear" && mode !== "clear-all") {
    return;
  }
  var key = "rio.session.v1";
  var cookieName = "rio_hosted";
  function readCookie() {
    var parts = (document.cookie || "").split("; ");
    var prefix = cookieName + "=";
    for (var i = 0; i < parts.length; i++) {
      if (parts[i].indexOf(prefix) === 0) {
        try {
          return decodeURIComponent(parts[i].substring(prefix.length));
        } catch (err) {
          return "";
        }
      }
    }
    return "";
  }
  if (mode === "clear" || mode === "clear-all") {
    try {
      if (mode === "clear-all") {
        window.localStorage.clear();
      } else {
        window.localStorage.removeItem(key);
      }
    } catch (err) {}
    document.cookie = cookieName + "=; Path=/; Max-Age=0; SameSite=Lax; Secure";
  }
  if (mode === "write" && typeof data.payload === "string") {
    try {
      if (window.localStorage.getItem(key) !== data.payload) {
        window.localStorage.setItem(key, data.payload);
      }
    } catch (err) {}
  }
  if (mode === "write" && typeof data.cookie === "string" && data.cookie) {
    var maxAge = parseInt(data.max_age, 10);
    if (!maxAge || maxAge < 1) {
      maxAge = 86400;
    }
    document.cookie = cookieName + "=" + encodeURIComponent(data.cookie)
      + "; Path=/; Max-Age=" + String(maxAge) + "; SameSite=Lax; Secure";
  }
  var body = "";
  try {
    var stored = window.localStorage.getItem(key);
    body = stored === null ? "" : String(stored);
  } catch (err) {
    body = "";
  }
  var cookie = "";
  try {
    cookie = readCookie();
  } catch (err) {
    cookie = "";
  }
  var token = mode + "\\n" + body + "\\n" + cookie;
  if (window.__rioSessionToken === token) {
    return;
  }
  window.__rioSessionToken = token;
  component.setStateValue("record", { body: body, cookie: cookie });
}
"""


def _session_component():
    """The signed-token bridge. Registered once per process."""
    import ui.accounts as accounts

    cached = getattr(accounts, "_browser_component", None)
    if cached is None:
        cached = st.components.v2.component(
            "rio_session_store",
            js=_SESSION_STORE_JS,
            isolate_styles=False,
        )
        accounts._browser_component = cached
    return cached


def _mount_session(data: dict, *, widget_key: str):
    """Mount the token bridge. One run mounts one mode on one key."""
    return _session_component()(
        key=widget_key,
        data=data,
        width="content",
        height="content",
    )


# One browser bridge per run. A second mount on the same key breaks the page.
_BRIDGE_CACHE: dict | None = None


def _browser_session(
    mode: str,
    payload: str | None = None,
    cookie: str | None = None,
    max_age: int | None = None,
) -> str | None:
    """The token currently in this browser, once the bridge has answered."""
    global _BRIDGE_CACHE
    if _BRIDGE_CACHE is not None and mode == "read" and payload is None and cookie is None:
        body = _BRIDGE_CACHE.get("body")
        return body if isinstance(body, str) else None
    data = {"mode": mode}
    if payload is not None:
        data["payload"] = payload
    if cookie is not None:
        data["cookie"] = cookie
        data["max_age"] = int(max_age if isinstance(max_age, int) else 86400)
    result = _mount_session(data, widget_key="rio-keep-session")
    record = getattr(result, "record", None)
    hosted = ""
    if isinstance(record, dict) and isinstance(record.get("cookie"), str):
        hosted = record["cookie"]
    body = record.get("body") if isinstance(record, dict) else None
    _BRIDGE_CACHE = {"body": body if isinstance(body, str) else None, "cookie": hosted}
    if not isinstance(body, str):
        return None
    return body


def _flush_cookie_if_needed() -> None:
    """Write a pending hosted cookie. A read already mounted this run waits."""
    cookie = st.session_state.get("rio_cookie_write")
    pending = st.session_state.get("rio_session_write")
    if not isinstance(cookie, str) or not cookie:
        return
    if _BRIDGE_CACHE is not None:
        return
    payload = pending if isinstance(pending, str) else ""
    max_age = st.session_state.get("rio_cookie_max_age")
    written = _browser_session(
        "write",
        payload,
        cookie,
        max_age if isinstance(max_age, int) else None,
    )
    if written is None:
        return
    st.session_state.pop("rio_session_write", None)
    st.session_state.pop("rio_cookie_write", None)
    st.session_state.pop("rio_cookie_max_age", None)


def _restore_hosted_from_bridge() -> None:
    """A hosted cookie becomes this session before the startup page is chosen."""
    if not cloud_configured():
        return
    cached = _BRIDGE_CACHE or {}
    raw = cached.get("cookie") if isinstance(cached, dict) else ""
    if not isinstance(raw, str) or not raw:
        return
    from ui.cloud_ui import restore_hosted_cookie

    restore_hosted_cookie(raw)


def _boot_bridge() -> None:
    """Read the browser once. A signed-in rerun does not call the host again."""
    if st.session_state.get("rio_session_clear") is True:
        return
    if _account_identity() is not None:
        _flush_cookie_if_needed()
        return
    body = _browser_session("read")
    if body is None:
        st.stop()
    _restore_hosted_from_bridge()


def _has_current_season() -> bool:
    """A saved plan with sessions. That season opens Home, not the startup page."""
    from ui.cloud_session import plan_has_sessions

    return plan_has_sessions(st.session_state.get("season_plan"))


def _sign_out() -> None:
    """End this session and clear the signed token. The account file stays."""
    from ui.cloud_ui import cloud_sign_out

    cloud_sign_out()
    st.session_state["rio_reset_session"] = True
    st.session_state["rio_session_clear"] = True
    st.session_state.pop("rio_account", None)
    st.session_state.pop("rio_account_secret", None)
    st.session_state.pop("rio_session_token", None)
    st.session_state.pop("rio_session_write", None)
    st.query_params.clear()
    st.rerun()


def _restore_session() -> None:
    """On each page load, a signed token under a day old restores this session.

    Log out clears the token. A token a day old or older is cleared too.
    """
    now = int(time.time())
    if st.session_state.get("rio_session_clear") is True:
        mode = "clear-all" if st.session_state.get("rio_clear_browser") is True else "clear"
        if _browser_session(mode) == "":
            st.session_state.pop("rio_session_clear", None)
            st.session_state.pop("rio_clear_browser", None)
        return
    token = st.session_state.get("rio_session_token")
    if _account_identity() is not None:
        if str(st.session_state.get("rio_session_token") or "").startswith("cloud."):
            return
        if not isinstance(token, str) or open_session(token, now=now) is None:
            _sign_out()
            return
        pending = st.session_state.get("rio_session_write")
        if isinstance(pending, str) and pending:
            if _browser_session("write", pending) == pending:
                st.session_state.pop("rio_session_write", None)
        return
    body = _browser_session("read")
    if body is None:
        st.stop()
    if not body:
        return
    opened = open_session(body, now=now)
    if opened is None and isinstance(body, str) and body.startswith("cloud."):
        from ui.cloud_ui import restore_cloud_token

        if restore_cloud_token(body):
            return
    if opened is None:
        st.session_state["rio_session_clear"] = True
        st.rerun()
    st.session_state["rio_account"] = opened[0]
    st.session_state["rio_account_secret"] = opened[1]
    st.session_state["rio_session_token"] = body


def _restore_record(key: str) -> None:
    """Read this account's marks and actuals once, before an empty plan is drawn."""
    who = _account_identity()
    body = None if who is None else read_record(accounts_path(), who[0], who[1], key)
    if not isinstance(body, str):
        st.markdown(_css(), unsafe_allow_html=True)
        st.markdown(
            '<p class="rio-error">This account could not be opened.</p>',
            unsafe_allow_html=True,
        )
        st.stop()
    marks, actuals, activities = load_record(body)
    st.session_state["season_marks"] = marks
    st.session_state["season_actuals"] = actuals
    st.session_state["season_activities"] = activities
    st.session_state["rio_store_loaded"] = True


def _sync_browser_store() -> None:
    """Save marks and actuals on this account, under the four inputs."""
    if st.session_state.get("rio_test_preview"):
        return
    inputs = st.session_state.get("season_inputs")
    plan = st.session_state.get("season_plan")
    if not inputs_ok(inputs) or not isinstance(plan, dict):
        return
    who = _account_identity()
    if st.session_state.get("rio_cloud_user_id"):
        from ui.cloud_ui import persist_cloud_season

        persist_cloud_season()
    if who is None or st.session_state.get("rio_account_secret") == "cloud":
        return
    key = storage_key(inputs)
    if not st.session_state.get("rio_store_loaded"):
        _restore_record(key)
        return
    try:
        write_record(
            accounts_path(),
            who[0],
            who[1],
            key,
            dump_record(
                st.session_state.get("season_marks"),
                st.session_state.get("season_actuals"),
                st.session_state.get("season_activities"),
            ),
        )
    except AccountError:
        st.markdown(_css(), unsafe_allow_html=True)
        st.markdown(
            '<p class="rio-error">This account could not be saved.</p>',
            unsafe_allow_html=True,
        )


def _load_shared_plan() -> None:
    """URL inputs rebuild the plan. A visit that already has it keeps that plan.

    A test-season preview draws the TEST athlete and does not read this login's plan.

    This account's record is restored here. The write happens after a pull so a
    match from this run is what gets saved.
    """
    from ui.sample_season_ui import apply_preview, previewing

    if previewing():
        apply_preview()
        return
    found = plan_inputs(st.query_params)
    if found is None:
        inputs = st.session_state.get("season_inputs")
        if inputs_ok(inputs) and isinstance(st.session_state.get("season_plan"), dict):
            _publish_inputs(inputs)
        else:
            _restore_last_plan()
    else:
        _ensure_linked_plan(found)
    _restore_if_needed()


def _restore_last_plan() -> None:
    """Open the plan this account saved last, when the URL does not name one."""
    who = _account_identity()
    if who is None:
        return
    if isinstance(st.session_state.get("season_plan"), dict) and st.session_state.get("rio_store_loaded"):
        return
    key = last_key(accounts_path(), who[0], who[1])
    if not isinstance(key, str) or not key:
        return
    inputs = inputs_from_key(key)
    if inputs is None:
        return
    _ensure_linked_plan(inputs)


def _restore_if_needed() -> None:
    """Read this account's record once, before a pull replaces the window."""
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

    A test-season preview does not pull. The TEST runs are already stored.

    Opening Dashboard, Weekly, Session, Progress, or Activity reads the
    last 14 days through the existing adapter. Refresh on Activity reads
    every activity. A matched Tuesday or Thursday with no mark is judged from
    its WORK times, and adapt() changes only later weeks. A day that already
    has a mark is left as stored. A failure keeps the stored matches. The key
    stays in the environment. Nothing is written to Intervals.
    """
    if st.session_state.get("rio_test_preview"):
        return
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
    from ui.strava_ui import strava_connected

    if not strava_connected():
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
    from ui.strava_ui import restore_rows

    restore_rows()
    st.session_state["activities_trigger"] = trigger
    st.session_state["activities_loaded"] = True


def _open_restored_session(was_signed_in: bool) -> None:
    """A page load that just restored a valid token opens Home or Start.

    The token check already ran. A session that was already open stays on
    its page. No plan, or a goal date before today, opens Start.
    """
    if was_signed_in or _account_identity() is None:
        return
    st.session_state["rio_enter"] = True


def _route_after_login() -> None:
    """Home when a stored plan's goal date is today or later. Otherwise Start."""
    st.session_state.pop("rio_enter", None)
    page = _start_page
    who = _account_identity()
    if who is not None:
        keys = record_keys(accounts_path(), who[0], who[1], KEY_PREFIX)
        if has_active_plan(keys, date.today()) or _has_current_season():
            home = _nav_page("Home")
            if home is not None:
                page = home
    if page is not None:
        st.switch_page(page)


def _with_plan(page):
    """Draw the page after the shared plan is in the session.

    Dashboard, Weekly, Session, Progress, and Activity read the last 14
    days when they are opened, then judge an unmarked quality day. Refresh
    on Activity reads every activity and judges the same way. The write
    saves the matches with the marks.
    """

    def wrapped() -> None:
        # Log in and a restored token both set this. Home or Start opens first.
        if st.session_state.get("rio_enter") is True:
            _route_after_login()
        if st.session_state.pop("rio_test_go_admin", None):
            admin = _nav_page("Admin")
            if admin is not None:
                st.switch_page(admin)
        _load_local()
        _load_shared_plan()
        _pull_for(page.__name__)
        _sync_browser_store()
        page()

    wrapped.__name__ = page.__name__
    return wrapped


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
    for name, page in (*_NAV_PAGES, *_MORE_PAGES):
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
# Still routed. Left off the main nav and the More menu.
_KEPT_PAGES: list[tuple[str, st.Page]] = []
_EMBEDDING = False
_MARK_PREFIX = "season"

_APP_CSS = """
<style>
::selection { background: #F6E7E1; color: #0E0E0E; }
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"],
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {
  background: #F2F2F2 !important;
  color: #0E0E0E !important;
}
html { color-scheme: light; }
.stApp, .stApp button, .stApp input, .stApp label, .stApp summary, .stApp p,
.stMarkdown, .stMarkdown h1, .stMarkdown h2, .stMarkdown a, .stMarkdown p, .stMarkdown div,
[class*="st-key-rio-nav"], [class*="st-key-rio-nav"] a, .rio-hero, .rio-hero h1, .rio-week-title, .rio-day, .rio-day div,
.rio-card, .rio-card h2, .rio-table, .rio-table th, .rio-table td,
.rio-progress, .rio-progress div {
  font-family: Inter, "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
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
  max-width: 100% !important;
  padding: 0 5vw 5.5rem !important;
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
  border-bottom: 1px solid #DADADA !important;
  position: sticky;
  top: 0;
  z-index: 30;
  background: #F2F2F2 !important;
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
  color: #6B6B6B !important;
  text-decoration: none !important;
  line-height: 1.3 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"] p {
  color: #6B6B6B !important;
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
  color: #0E0E0E !important;
  background: transparent !important;
}
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] {
  border-bottom-color: #e25a32 !important;
}
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"],
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-tab-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] p {
  color: #0E0E0E !important;
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
  color: #0E0E0E !important;
  font-weight: 600 !important;
  letter-spacing: 0.2em !important;
  font-size: 0.92rem !important;
  background: transparent !important;
}
[class*="st-key-rio-nav"] [data-testid="stPageLink-NavLink"]:focus-visible,
button:focus-visible {
  outline: 1px solid #C94A25;
  outline-offset: 3px;
}
[class*="st-key-rio-logout"] {
  flex: 0 0 auto !important;
  width: auto !important;
}
[class*="st-key-rio-logout"] button {
  background: transparent !important;
  border: none !important;
  border-radius: 0 !important;
  color: #6B6B6B !important;
  min-height: 0 !important;
  height: auto !important;
  margin: 0 !important;
  padding: 0.15rem 0 0.28rem !important;
  font-size: 0.84rem !important;
  font-weight: 400 !important;
  line-height: 1.3 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-logout"] button p,
[class*="st-key-rio-logout"] button span {
  color: inherit !important;
  font-size: 0.84rem !important;
  font-weight: 400 !important;
}
[class*="st-key-rio-logout"] button:hover,
[class*="st-key-rio-logout"] button:hover p {
  background: transparent !important;
  border: none !important;
  color: #0E0E0E !important;
}

.rio-hero { padding: 3.4rem 0 2.2rem; }
.rio-synthetic {
  margin: 0 !important;
  color: #6B6B6B !important;
  font-size: 0.68rem !important;
  line-height: 1.3 !important;
  letter-spacing: 0.16em;
  font-weight: 500;
}
.rio-hero h1,
.stMarkdown .rio-hero h1 {
  margin: 0.7rem 0 0 !important;
  padding: 0 !important;
  color: #0E0E0E !important;
  font-family: Manrope, Inter, "Segoe UI", sans-serif !important;
  font-size: clamp(3rem, 7vw, 4.75rem) !important;
  font-weight: 800 !important;
  letter-spacing: -0.045em !important;
  line-height: 0.98 !important;
}
.rio-hero h1:first-child,
.stMarkdown .rio-hero h1:first-child {
  margin-top: 0 !important;
}

.rio-hero h1.rio-key,
.stMarkdown .rio-hero h1.rio-key {
  color: #C94A25 !important;
}
.rio-range {
  margin: 0.9rem 0 0 !important;
  color: #6B6B6B !important;
  font-size: 1.05rem !important;
  line-height: 1.4 !important;
  font-variant-numeric: tabular-nums;
}
.rio-hello {
  margin: 0.85rem 0 0 !important;
  color: #0E0E0E !important;
  font-size: 1.65rem !important;
  font-weight: 500 !important;
  letter-spacing: -0.03em !important;
  line-height: 1.15 !important;
}
.rio-hello-plan {
  margin: 0.35rem 0 0.85rem !important;
  color: #6B6B6B !important;
  font-size: 0.95rem !important;
  line-height: 1.4 !important;
}
.rio-error {
  margin: 0.85rem 0 0;
  color: #0E0E0E;
  font-size: 0.95rem;
}

[class*="st-key-rio-controls"] { margin: 0 0 2.6rem; }
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p {
  color: #6B6B6B !important;
  font-size: 0.75rem !important;
  font-weight: 400 !important;
}
[data-testid="stTextInputRootElement"],
[data-testid="stDateInputField"] {
  background: #FFFFFF !important;
  border: 1px solid #DADADA !important;
  border-radius: 8px !important;
  color: #0E0E0E !important;
}
[data-testid="stTextInputField"] {
  color: #0E0E0E !important;
  -webkit-text-fill-color: #0E0E0E !important;
  background: transparent !important;
  caret-color: #0E0E0E !important;
}
[data-testid="stTextInputField"]::placeholder {
  color: #6B6B6B !important;
  -webkit-text-fill-color: #6B6B6B !important;
  opacity: 1 !important;
}
[data-testid="stDateInputField"] [role="spinbutton"],
[data-testid="stDateInputField"] span {
  color: #0E0E0E !important;
}
[data-testid="stTextInputRootElement"]:focus-within,
[data-testid="stDateInputField"]:focus-within {
  border-color: #C94A25 !important;
  box-shadow: none !important;
}
[data-testid="stDateInput"] svg { fill: #6B6B6B !important; }
[data-testid="stDateInputField"] button {
  background: transparent !important;
  color: #6B6B6B !important;
  border: none !important;
}

[class*="st-key-rio-week"] {
  background: #FFFFFF !important;
  border: 1px solid #DADADA;
  border-radius: 18px;
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
  color: #0E0E0E !important;
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
  color: #6B6B6B !important;
  font-weight: 400 !important;
  margin-left: 0.7rem !important;
  margin-right: 0.7rem !important;
}
.rio-week-phase {
  color: #6B6B6B !important;
  font-size: 1.08rem !important;
  font-weight: 500 !important;
  letter-spacing: -0.01em !important;
}
.rio-week-meta, .rio-applied {
  margin: 0 !important;
  color: #6B6B6B !important;
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
.rio-day-next { border-top: 1px solid #DADADA; }
.rio-dow {
  color: #0E0E0E;
  font-size: 0.98rem;
  font-weight: 500;
}
.rio-date {
  margin-top: 0.22rem;
  color: #6B6B6B;
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
}
.rio-name {
  color: #0E0E0E;
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.4;
  overflow-wrap: break-word;
}
.rio-target {
  margin-top: 0.28rem;
  color: #6B6B6B;
  font-size: 0.84rem;
  line-height: 1.45;
}
.rio-hero-week { padding-bottom: 1.15rem; }
[class*="st-key-rio-pick"] {
  max-width: 24rem;
  margin: 0 0 1.85rem !important;
}
.rio-daycard {
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 18px;
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
  color: #0E0E0E;
  font-size: 1.5rem;
  font-weight: 500;
  letter-spacing: -0.03em;
  line-height: 1.15;
}
.rio-daycard-date {
  margin-top: 0.4rem;
  color: #6B6B6B;
  font-size: 0.92rem;
  font-variant-numeric: tabular-nums;
}
.rio-daycard-work {
  margin-top: 1.35rem;
  color: #0E0E0E;
  font-size: 1.22rem;
  font-weight: 500;
  line-height: 1.4;
  overflow-wrap: break-word;
}
.rio-daycard-target {
  margin-top: 0.95rem;
  padding-top: 0.9rem;
  border-top: 1px solid #DADADA;
  color: #6B6B6B;
  font-size: 0.95rem;
  line-height: 1.5;
}
.rio-daycard-actual {
  margin-top: 0.75rem;
  color: #0E0E0E;
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
  color: #0E0E0E !important;
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
  color: #6B6B6B;
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
  background: #FFFFFF;
  border-color: #DADADA;
}
.rio-cal-today {
  border-color: #e25a32;
}
.rio-cal-num,
.rio-cal-label {
  margin: 0;
}
.rio-cal-num {
  color: #0E0E0E;
  font-size: 0.92rem;
  font-weight: 500;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}
.rio-cal-quiet .rio-cal-num {
  color: #6B6B6B;
}
.rio-cal-label {
  margin-top: 0.32rem;
  color: #6B6B6B;
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
  background: #F7F7F7;
}
[class*="st-key-rio-hit-card-"]:hover .rio-daycard {
  border-color: #F6E7E1;
}
[class*="st-key-rio-hit-"]:focus-within .rio-day,
[class*="st-key-rio-hit-"]:focus-within .rio-daycard,
[class*="st-key-rio-hit-"]:focus-within .rio-cal-day,
[class*="st-key-rio-hit-"]:focus-within .rio-past-row,
[class*="st-key-rio-hit-dash"]:focus-within .rio-next,
[class*="st-key-rio-hit-dash"]:focus-within .rio-hero,
[class*="st-key-rio-hit-dash"]:focus-within .rio-track-stage {
  outline: 1px solid #C94A25;
  outline-offset: 2px;
}
[class*="st-key-rio-hit-cal-"]:hover .rio-cal-session {
  border-color: #F6E7E1;
}
[class*="st-key-rio-hit-dash"]:hover .rio-next-work {
  color: #C94A25 !important;
}
[class*="st-key-rio-hit-dash"]:hover .rio-track-svg {
  color: #C94A25 !important;
}
.rio-status {
  text-align: right;
  color: #6B6B6B;
  font-size: 0.62rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding-top: 0.26rem;
}
.rio-volume,
.rio-heart {
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 18px;
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
  fill: #0E0E0E !important;
}
.rio-heart-dot {
  fill: #E25A32 !important;
}
.rio-progress-list {
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 18px;
  padding: 0.2rem 1.35rem;
  margin: 0 0 1.15rem;
}
.rio-lib {
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 18px;
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
.rio-lib-row + .rio-lib-row { border-top: 1px solid #DADADA; }
.rio-lib-name {
  color: #0E0E0E;
  font-size: 0.98rem;
  font-weight: 500;
  line-height: 1.4;
  overflow-wrap: break-word;
}
.rio-lib-id {
  margin-top: 0.22rem;
  color: #6B6B6B;
  font-size: 0.75rem;
  line-height: 1.3;
  font-variant-numeric: tabular-nums;
}
.rio-lib-cap {
  color: #6B6B6B;
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
.rio-progress + .rio-progress { border-top: 1px solid #DADADA; }
.rio-progress-tick {
  width: 0.55rem;
  height: 0.55rem;
  border: 1px solid #6B6B6B;
  border-radius: 99px;
  background: transparent;
  align-self: center;
}
.rio-progress-done .rio-progress-tick {
  background: #e25a32;
  border-color: #e25a32;
}
.rio-progress-current .rio-progress-tick {
  background: #C94A25;
  border-color: #C94A25;
}
.rio-progress-week {
  color: #0E0E0E;
  font-size: 0.98rem;
  font-weight: 500;
  letter-spacing: -0.02em;
}
.rio-progress-phase {
  color: #6B6B6B;
  font-size: 0.92rem;
}
.rio-progress-volume {
  margin-top: 0.16rem;
  color: #6B6B6B;
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0;
}
.rio-progress-upcoming .rio-progress-volume,
.rio-progress-open .rio-progress-volume { color: #6B6B6B; }
.rio-progress-status {
  color: #6B6B6B;
  font-size: 0.72rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-align: right;
}
.rio-progress-days {
  color: #6B6B6B;
  font-size: 0.84rem;
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}
.rio-progress-current .rio-progress-days { color: #0E0E0E; }
.rio-progress-done .rio-progress-days,
.rio-progress-open .rio-progress-days { color: #6B6B6B; }
.rio-progress-current .rio-progress-week,
.rio-progress-current .rio-progress-status { color: #0E0E0E; }
.rio-progress-done .rio-progress-week { color: #6B6B6B; }
.rio-progress-upcoming .rio-progress-week,
.rio-progress-upcoming .rio-progress-phase,
.rio-progress-open .rio-progress-week,
.rio-progress-open .rio-progress-phase { color: #6B6B6B; }
.rio-empty {
  margin: 0.9rem 0 0.2rem;
  color: #6B6B6B;
}
.rio-mark-label {
  margin: 0 !important;
  padding: 0.95rem 0 0.55rem !important;
  color: #6B6B6B !important;
  font-size: 0.68rem !important;
  line-height: 1.2 !important;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.rio-reason {
  margin: 0.22rem 0 !important;
  color: #6B6B6B !important;
  font-size: 0.78rem !important;
  line-height: 1.45 !important;
}
.rio-reason span {
  color: #6B6B6B;
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
  color: #6B6B6B !important;
  font-size: 0.8rem !important;
  padding: 0.35rem 0 !important;
  border-radius: 0 !important;
}
[class*="st-key-rio-week"] [data-testid="stExpander"] summary:hover {
  background: transparent !important;
  color: #0E0E0E !important;
}
[class*="st-key-rio-week"] [data-testid="stExpander"] svg {
  fill: #6B6B6B !important;
}
[class*="st-key-rio-week"] button {
  background: transparent !important;
  border: 1px solid #0E0E0E !important;
  border-radius: 999px !important;
  color: #0E0E0E !important;
  min-height: 2.4rem !important;
  padding: 0.4rem 0.9rem !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-week"] button p { color: inherit !important; }
[class*="st-key-rio-week"] button[kind="primary"],
[class*="st-key-rio-week"] [data-testid="stBaseButton-primary"] {
  background: #E25A32 !important;
  border-color: #E25A32 !important;
  color: #FFFFFF !important;
}
[class*="st-key-rio-week"] button[kind="secondary"]:hover,
[class*="st-key-rio-week"] [data-testid="stBaseButton-secondary"]:hover {
  border-color: #0E0E0E !important;
  color: #0E0E0E !important;
  background: #F2F2F2 !important;
}
[class*="st-key-rio-week"] button[kind="primary"]:hover,
[class*="st-key-rio-week"] [data-testid="stBaseButton-primary"]:hover {
  background: #C94A25 !important;
  border-color: #C94A25 !important;
  color: #FFFFFF !important;
}
[class*="st-key-rio-week"] [data-testid="stHorizontalBlock"] {
  gap: 0.55rem !important;
}
[class*="st-key-rio-week-mark"] {
  margin: 0.6rem 0 1.65rem !important;
}

.rio-card {
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 18px;
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
  border-top: 1px solid #DADADA;
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
.rio-fields + .rio-fields > .rio-field:first-child { border-top: 1px solid #DADADA; }
.rio-k {
  color: #6B6B6B;
  font-size: 0.78rem;
  line-height: 1.35;
}
.rio-v {
  color: #0E0E0E;
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.rio-v .rio-missing,
.rio-table td .rio-missing {
  color: #6B6B6B;
  font-weight: 400;
}
.rio-prose {
  margin: 0.35rem 0 0.15rem !important;
  padding-top: 0.95rem;
  border-top: 1px solid #DADADA;
  color: #0E0E0E !important;
  font-size: 1.02rem !important;
  line-height: 1.6 !important;
}
.rio-note {
  margin: 0 0 0.15rem !important;
  color: #0E0E0E !important;
  font-size: 1.02rem !important;
  line-height: 1.6 !important;
}
.rio-prep {
  margin: 0.85rem 0 0.15rem !important;
  padding-top: 0.15rem;
  border-top: 1px solid #DADADA;
}
.rio-prep-block + .rio-prep-block {
  margin-top: 0.2rem;
  border-top: 1px solid #DADADA;
}
.rio-prep .rio-mark-label {
  padding: 0.9rem 0 0.4rem !important;
}
.rio-prep-line,
.rio-prep-lead {
  margin: 0 !important;
  color: #0E0E0E !important;
  font-size: 0.95rem !important;
  line-height: 1.5 !important;
}
.rio-prep-list + .rio-prep-lead {
  margin-top: 0.8rem !important;
}
.rio-prep-list {
  margin: 0.28rem 0 0.05rem !important;
  padding: 0 0 0 1.15rem !important;
  list-style: disc;
}
.rio-prep-list li {
  margin: 0.16rem 0 !important;
  padding: 0 !important;
  color: #0E0E0E !important;
  font-size: 0.95rem !important;
  line-height: 1.45 !important;
}
.rio-prep-list li::marker {
  color: #6B6B6B;
}
.rio-card .rio-reason {
  margin: 0.28rem 0 !important;
  color: #0E0E0E !important;
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
  color: #6B6B6B;
  font-size: 0.72rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  padding: 0.15rem 0.7rem 0.55rem 0;
  border-bottom: 1px solid #DADADA;
  white-space: nowrap;
}
.rio-table td {
  color: #0E0E0E;
  font-size: 0.9rem;
  line-height: 1.4;
  padding: 0.72rem 0.7rem 0.72rem 0;
  border-bottom: 1px solid #DADADA;
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
  border: 1px solid #0E0E0E !important;
  border-radius: 999px !important;
  color: #0E0E0E !important;
  min-height: 2.4rem !important;
  padding: 0.4rem 0.95rem !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-activity-refresh"] button p { color: inherit !important; }
[class*="st-key-rio-activity-refresh"] button:hover {
  border-color: #0E0E0E !important;
  color: #0E0E0E !important;
  background: #F2F2F2 !important;
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
  background: #E25A32 !important;
  border: 1px solid #E25A32 !important;
  border-radius: 999px !important;
  color: #FFFFFF !important;
  min-height: 2.75rem !important;
  margin-top: 0.75rem !important;
  padding: 0.45rem 1.1rem !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
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
  background: #C94A25 !important;
  border-color: #C94A25 !important;
  color: #FFFFFF !important;
}
[class*="st-key-rio-auth-switch"] button,
[class*="st-key-rio-auth-switch"] [data-testid="stBaseButton-secondary"] {
  background: #FFFFFF !important;
  border: 1px solid #0E0E0E !important;
  border-radius: 999px !important;
  color: #0E0E0E !important;
  min-height: 2.75rem !important;
  margin-top: 0.15rem !important;
  padding: 0.45rem 0.9rem !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-auth-switch"] button p,
[class*="st-key-rio-auth-switch"] button span {
  color: inherit !important;
}
[class*="st-key-rio-auth-switch"] button:hover,
[class*="st-key-rio-auth-switch"] [data-testid="stBaseButton-secondary"]:hover {
  background: #F2F2F2 !important;
  border-color: #0E0E0E !important;
  color: #0E0E0E !important;
}

[data-testid="stSelectbox"] [role="group"] {
  background: #FFFFFF !important;
  border: 1px solid #DADADA !important;
  border-radius: 8px !important;
}
[data-testid="stSelectbox"] [role="group"]:focus-within {
  border-color: #C94A25 !important;
  box-shadow: none !important;
}
[data-testid="stSelectbox"] input {
  background: transparent !important;
  color: #0E0E0E !important;
  -webkit-text-fill-color: #0E0E0E !important;
  border: none !important;
  box-shadow: none !important;
  caret-color: #0E0E0E !important;
}
[data-testid="stSelectbox"] input:focus {
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
}
[data-testid="stSelectbox"] button {
  background: transparent !important;
  color: #6B6B6B !important;
  border: none !important;
  box-shadow: none !important;
}
[data-testid="stSelectbox"] svg { fill: #6B6B6B !important; }
[data-testid="stSelectboxVirtualDropdown"] {
  background: #F7F7F7 !important;
  color: #0E0E0E !important;
  border: 1px solid #DADADA !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"] {
  color: #0E0E0E !important;
  background: transparent !important;
}
[data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"],
[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover {
  background: #F6E7E1 !important;
  color: #C94A25 !important;
}

[class*="st-key-rio-result"] {
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 18px;
  padding: 1.15rem 1.55rem 1.2rem;
  margin: 0 0 1.15rem;
}
[class*="st-key-rio-result"] .rio-mark-label {
  padding: 0 0 0.45rem !important;
}
[class*="st-key-rio-result"] .rio-rep-note {
  margin: 0 0 0.9rem !important;
  padding: 0 !important;
  color: #6B6B6B !important;
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
  background: #F7F7F7 !important;
  border: 1px solid #DADADA !important;
  border-radius: 8px !important;
}
[class*="st-key-rio-result"] [data-testid="stNumberInputContainer"]:focus-within {
  border-color: #C94A25 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-result"] [data-testid="stNumberInputField"] {
  color: #0E0E0E !important;
  -webkit-text-fill-color: #0E0E0E !important;
  background: transparent !important;
  caret-color: #0E0E0E !important;
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
  color: #6B6B6B !important;
}
[class*="st-key-rio-result"] .rio-week-meta {
  margin-top: 0.15rem !important;
}

.rio-template-id {
  margin-top: 0.28rem;
  color: #6B6B6B;
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
  border-left: 1px solid #DADADA;
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
  color: #6B6B6B !important;
  font-size: 0.8rem !important;
  line-height: 1.4 !important;
}
.rio-settings-kept {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
}
[class*="st-key-rio-settings"] {
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 18px;
  padding: 0.85rem 1.35rem 0.45rem;
  margin: 0 0 1.15rem !important;
}
[class*="st-key-rio-settings"] [data-testid="stWidgetLabel"] p,
[class*="st-key-rio-settings"] label,
[class*="st-key-rio-settings"] [data-testid="stMarkdownContainer"] p {
  color: #0E0E0E !important;
}
[class*="st-key-rio-settings"] [role="radiogroup"] {
  gap: 1.1rem;
}
[class*="st-key-rio-settings"] input[type="radio"] {
  accent-color: #e25a32;
}
[class*="st-key-rio-settings"] [data-testid="stCheckbox"] label > div:first-of-type {
  background: #F7F7F7 !important;
  border: 1px solid #DADADA !important;
}
[class*="st-key-rio-settings"] [data-testid="stCheckbox"]:has(input:checked) label > div:first-of-type {
  background: #e25a32 !important;
  border-color: #e25a32 !important;
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
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 18px;
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
.rio-past-rule { border-top: 1px solid #DADADA; }
.rio-past-k {
  color: #6B6B6B;
  font-size: 0.68rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  line-height: 1.2;
}
.rio-past-v {
  margin-top: 0.28rem;
  color: #0E0E0E;
  font-size: 1rem;
  font-variant-numeric: tabular-nums;
  line-height: 1.3;
}
.rio-past-time { text-align: right; }
[class*="st-key-rio-hit-past-"]:hover .rio-past-row {
  background: #F7F7F7;
}

h2.rio-section,
.stMarkdown h2.rio-section {
  margin: 2.4rem 0 0.85rem !important;
  padding: 0 !important;
  color: #0E0E0E !important;
  font-size: 1.35rem !important;
  font-weight: 500 !important;
  letter-spacing: -0.03em !important;
  line-height: 1.2 !important;
}
.rio-section-sub {
  margin: -0.35rem 0 1.1rem !important;
}
.rio-track-kicker {
  padding: 1.15rem 0 0;
}
.rio-track-stage {
  display: grid;
  grid-template-columns: minmax(0, 1.75fr) minmax(8.75rem, 0.62fr);
  column-gap: 1.6rem;
  align-items: center;
  margin: 0.15rem 0 0.35rem;
}
.rio-track-svg {
  display: block;
  width: 100%;
  height: auto;
  color: #E25A32;
}
.rio-track-facts {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  min-width: 0;
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 18px;
  padding: 0.95rem 1rem 1rem;
}
.rio-track-fact .rio-mark-label,
.rio-track-meta .rio-mark-label {
  margin: 0 !important;
  padding: 0 0 0.28rem !important;
}
.rio-track-day {
  margin: 0;
  color: #0E0E0E;
  font-size: 1.02rem;
  font-weight: 500;
  letter-spacing: -0.02em;
  line-height: 1.25;
}
.rio-track-sub {
  display: block;
  margin-top: 0.18rem;
  color: #6B6B6B;
  font-size: 0.78rem;
  font-weight: 400;
  letter-spacing: 0;
  font-variant-numeric: tabular-nums;
}
.rio-track-fact-value {
  margin: 0;
  color: #0E0E0E;
  font-size: 1.55rem;
  font-weight: 500;
  letter-spacing: -0.03em;
  line-height: 1.15;
  font-variant-numeric: tabular-nums;
  overflow-wrap: break-word;
}
.rio-track-id { margin-top: 0.15rem; }
.rio-track-meta {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 0.85rem 2rem;
  margin: 0.15rem 0 1.35rem;
  padding-top: 0.85rem;
  border-top: 1px solid #DADADA;
}
.rio-track-meta-value {
  margin: 0;
  color: #6B6B6B;
  font-size: 1.02rem;
  font-weight: 500;
  letter-spacing: -0.02em;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
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
  color: #0E0E0E !important;
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
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 18px;
  padding: 1.35rem 1.5rem 1.25rem;
  margin: 0 0 0.95rem;
}
.rio-next .rio-mark-label {
  margin: 0 !important;
  padding: 0 !important;
}
.rio-next-day {
  margin-top: 0.55rem;
  color: #0E0E0E;
  font-size: 1.85rem;
  font-weight: 500;
  letter-spacing: -0.03em;
  line-height: 1.1;
}
.rio-next .rio-range { margin-top: 0.35rem !important; }
.rio-next .rio-next-work { margin-top: 0.95rem !important; font-size: 1.15rem !important; }
.rio-mini {
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 18px;
  padding: 0.95rem 1rem 0.9rem;
  min-height: 7.2rem;
  height: 100%;
  box-sizing: border-box;
}
.rio-mini-dow {
  color: #0E0E0E;
  font-size: 0.98rem;
  font-weight: 500;
}
.rio-mini-date {
  margin-top: 0.2rem;
  color: #6B6B6B;
  font-size: 0.78rem;
  font-variant-numeric: tabular-nums;
}
.rio-mini-work {
  margin-top: 0.75rem;
  color: #0E0E0E;
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
  background: #FFFFFF;
  border: 1px solid #DADADA;
  border-radius: 10px;
  padding: 0.45rem 0.35rem 0.5rem;
  text-align: center;
}
.rio-phase-now {
  border-color: #e25a32;
}
.rio-phase-week {
  color: #6B6B6B;
  font-size: 0.62rem;
  letter-spacing: 0.06em;
}
.rio-phase-num {
  margin-top: 0.2rem;
  color: #0E0E0E;
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
  color: #6B6B6B !important;
}
[class*="st-key-rio-subnav"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-subnav"] [data-testid="stPageLink-NavLink"] p {
  color: #6B6B6B !important;
  font-size: 0.78rem !important;
}
[class*="st-key-rio-sub-"][class*="-is-active"] [data-testid="stPageLink-NavLink"],
[class*="st-key-rio-sub-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-sub-"][class*="-is-active"] [data-testid="stPageLink-NavLink"] p {
  color: #0E0E0E !important;
  border-bottom-color: #e25a32 !important;
}
[class*="st-key-rio-quick"] {
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 0.5rem !important;
  margin: 0.2rem 0 1.4rem !important;
}
[class*="st-key-rio-quick"] [data-testid="stPageLink-NavLink"] {
  background: #FFFFFF !important;
  border: 1px solid #DADADA !important;
  border-radius: 999px !important;
  padding: 0.38rem 0.85rem !important;
}
[class*="st-key-rio-quick"] [data-testid="stPageLink-NavLink"] span,
[class*="st-key-rio-quick"] [data-testid="stPageLink-NavLink"] p {
  color: #0E0E0E !important;
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
  border-color: #F6E7E1;
}
[class*="st-key-rio-start"] { max-width: 26rem; }


[class*="st-key-rio-confirm"] button,
[class*="st-key-rio-confirm"] [data-testid="stBaseButton-primary"],
[class*="st-key-rio-confirm"] [data-testid="stBaseButton-secondary"] {
  background: transparent !important;
  border: 1px solid #0E0E0E !important;
  border-radius: 999px !important;
  color: #0E0E0E !important;
  min-height: 2.4rem !important;
  padding: 0.4rem 0.9rem !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-confirm"] button p { color: inherit !important; }
[class*="st-key-rio-confirm"] button[kind="primary"],
[class*="st-key-rio-confirm"] [data-testid="stBaseButton-primary"] {
  background: #E25A32 !important;
  border-color: #E25A32 !important;
  color: #FFFFFF !important;
}
[class*="st-key-rio-confirm"] button[kind="secondary"]:hover,
[class*="st-key-rio-confirm"] [data-testid="stBaseButton-secondary"]:hover {
  border-color: #0E0E0E !important;
  color: #0E0E0E !important;
  background: #F2F2F2 !important;
}
[class*="st-key-rio-confirm"] button[kind="primary"]:hover,
[class*="st-key-rio-confirm"] [data-testid="stBaseButton-primary"]:hover {
  background: #C94A25 !important;
  border-color: #C94A25 !important;
  color: #FFFFFF !important;
}
[class*="st-key-rio-settings"] [data-testid="stCheckbox"]:has(input:checked) svg {
  fill: #FFFFFF !important;
}
[class*="st-key-rio-settings"] button,
[class*="st-key-rio-settings"] [data-testid="stBaseButton-primary"],
[class*="st-key-rio-settings"] [data-testid="stBaseButton-secondary"],
[class*="st-key-rio-settings"] [data-testid="stDownloadButton"] button {
  background: transparent !important;
  border: 1px solid #0E0E0E !important;
  border-radius: 999px !important;
  color: #0E0E0E !important;
  min-height: 2.4rem !important;
  margin-top: 0.35rem !important;
  padding: 0.4rem 0.95rem !important;
  font-size: 1rem !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}
[class*="st-key-rio-settings"] button p,
[class*="st-key-rio-settings"] button span {
  color: inherit !important;
}
[class*="st-key-rio-settings"] button:hover,
[class*="st-key-rio-settings"] [data-testid="stDownloadButton"] button:hover {
  border-color: #0E0E0E !important;
  color: #0E0E0E !important;
  background: #F2F2F2 !important;
}
[class*="st-key-rio-settings"] [data-testid="stBaseButton-primary"] {
  background: #E25A32 !important;
  border-color: #E25A32 !important;
  color: #FFFFFF !important;
}
[class*="st-key-rio-settings"] [data-testid="stBaseButton-primary"]:hover {
  background: #C94A25 !important;
  border-color: #C94A25 !important;
  color: #FFFFFF !important;
}
[class*="st-key-rio-settings"] input:disabled {
  color: #6B6B6B !important;
  -webkit-text-fill-color: #6B6B6B !important;
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
    border-top: 1px solid #DADADA;
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
  .rio-track-stage {
    grid-template-columns: 1fr;
    row-gap: 1.05rem;
  }
  .rio-track-facts {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.85rem 1.1rem;
  }
  .rio-track-facts > .rio-track-fact:first-child { grid-column: 1 / -1; }
  .rio-track-fact-value { font-size: 1.28rem; }
  .rio-pace-line { font-size: 0.92rem !important; }
  .rio-next-day { font-size: 1.45rem; }
  [class*="st-key-rio-next3"],
  [class*="st-key-rio-next3"] [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
  }
  [class*="st-key-rio-next3"] > div,
  [class*="st-key-rio-next3"] [data-testid="stHorizontalBlock"] > div {
    flex: 1 1 100% !important;
    width: 100% !important;
  }
}
.rio-pace { margin-top: 0.45rem; }
.rio-pace-line {
  margin: 0.12rem 0 0 !important;
  color: #121110 !important;
  font-size: 0.98rem !important;
  font-weight: 600 !important;
  line-height: 1.35 !important;
  font-variant-numeric: tabular-nums;
}
.rio-pace-range,
.rio-pace-block {
  margin: 0.1rem 0 0 !important;
  color: #6E6A64 !important;
  font-size: 0.86rem !important;
  line-height: 1.35 !important;
  font-variant-numeric: tabular-nums;
}
.rio-mini .rio-pace-line { font-size: 0.84rem !important; font-weight: 500 !important; }
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
.rio-track-kicker { padding-top: 0.45rem; }
.rio-track-meta { margin-bottom: 0.85rem; }
</style>
"""


def _esc(value: object) -> str:
    return escape(str(value), quote=True)


def _prefs() -> dict:
    """Display preferences for this browser session. The plan is not touched."""
    raw = dict(st.session_state.get("rio_settings") or {})
    widget = (
        ("settings-units", "units"),
        ("settings-pace", "pace_units"),
        ("settings-ids", "show_ids"),
        ("settings-compact", "compact"),
        ("settings-dates", "date_format"),
        ("settings-confirm", "confirm_adapt"),
        ("settings-start", "start_date"),
        ("settings-reminders", "reminders"),
        ("settings-recap", "recap"),
    )
    for key, name in widget:
        if key in st.session_state:
            raw[name] = st.session_state[key]
    prefs = normalize_prefs(raw)
    prefs["units"] = "km" if prefs.get("pace_units") == "km" else "miles"
    return prefs


def _load_local() -> None:
    """Read this account's name and preferences once. The plan is not opened."""
    who = _account_identity()
    if who is None:
        return
    if st.session_state.get("rio_local_email") == who[0] and isinstance(st.session_state.get("rio_local"), dict):
        return
    try:
        local = read_local(accounts_path(), who[0])
    except AccountError:
        return
    if not isinstance(local, dict):
        return
    st.session_state["rio_local"] = local
    st.session_state["rio_local_email"] = who[0]
    if "rio_settings" not in st.session_state:
        st.session_state["rio_settings"] = dict(local.get("settings") or {})


def _display_name() -> str:
    """The nickname, or the name stored with this account."""
    local = st.session_state.get("rio_local")
    if not isinstance(local, dict):
        return ""
    return shown_name(local.get("name"), local.get("preferred"))


def _refresh_session(email: str, secret: str) -> None:
    """Keep the signed token aligned with this email and seal key."""
    try:
        token = issue_session(email, secret, now=int(time.time()))
    except AccountError as exc:
        st.session_state["rio_settings_error"] = str(exc)
        st.rerun()
    st.session_state["rio_account"] = email
    st.session_state["rio_account_secret"] = secret
    st.session_state["rio_session_token"] = token
    st.session_state["rio_session_write"] = token
    st.session_state["rio_local_email"] = email
    st.session_state.pop("settings-email", None)


_MOTION_PAGE = ""
_MOTION_LOCKED = False
_MOTION_PLAY = True


def _arm_motion(page: str) -> None:
    """Name the page before the first stylesheet so a rerun can skip the entrance."""
    global _MOTION_PAGE
    if not _MOTION_LOCKED:
        _MOTION_PAGE = page


def _css(page: str | None = None) -> str:
    global _MOTION_LOCKED, _MOTION_PLAY
    if page:
        _arm_motion(page)
    css = _APP_CSS
    if _prefs()["compact"]:
        css += _COMPACT_CSS
    if not _MOTION_LOCKED:
        name = _MOTION_PAGE or "app"
        previous = st.session_state.get("rio_motion_page")
        _MOTION_PLAY = previous != name
        st.session_state["rio_motion_page"] = name
        _MOTION_LOCKED = True
    hold = "" if _MOTION_PLAY else theme.motion_hold_css()
    return css + theme.surface_css() + hold


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


def _demo_label(banner: object) -> bool:
    """True when a caption is a synthetic or demo badge. The data stays."""
    text = str(banner or "").lower()
    return "synthetic" in text or "demo" in text


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
    if banner and not _demo_label(banner):
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


def _next_session_day() -> str | None:
    """The next planned day, or the latest one when the season is finished."""
    plan = st.session_state.get("season_plan")
    if not isinstance(plan, dict):
        return None
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        return None
    days = []
    for session in sessions:
        if not isinstance(session, dict):
            continue
        day = session.get("date")
        if isinstance(day, str) and day.strip():
            days.append(day.strip())
    if not days:
        return None
    days.sort()
    today = date.today().isoformat()
    for day in days:
        if day >= today:
            return day
    return days[-1]


def _render_nav(active: str) -> None:
    """Page links follow Streamlit routing and stay in this tab."""
    if _EMBEDDING:
        return
    from ui.sample_season_ui import preview_banner

    preview_banner()
    home = _HOME_PAGE
    if home is None and _NAV_PAGES:
        home = _NAV_PAGES[0][1]
    if home is None:
        return
    more_labels = {label for label, _page in _MORE_PAGES}
    more_labels.update(label for label, _page in _KEPT_PAGES)
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
            if _SESSION_PAGE is not None:
                day = _next_session_day()
                with st.container(key="rio-start-session", width="content"):
                    st.page_link(
                        _SESSION_PAGE,
                        label="Start session",
                        icon="",
                        query_params=_link_params({"date": day} if day else None),
                        width="content",
                    )
            with st.container(key="rio-logout", width="content"):
                if st.button("Log out", key="rio-log-out"):
                    _sign_out()
    if active == "More" or active in more_labels:
        _render_subnav(active)


def _open(page: str, *, controls: bool = False):
    st.markdown(_css(page), unsafe_allow_html=True)
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
    synthetic = ""
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
        f'{_split_html(session.get("template_id"), session.get("date"))}'
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
        f'{_split_html(session.get("template_id"), session.get("date"))}'
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
        f'{_split_html(session.get("template_id"), session.get("date"))}'
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
    if page is None or not str(session.get("template_id") or "").strip():
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
    """A plain notice when runs could not be read. The raw error stays off the page."""
    message = st.session_state.get("activities_notice")
    if not isinstance(message, str) or not message.strip():
        return
    lowered = message.lower()
    missing = "is not set" in lowered or "not configured" in lowered
    if missing:
        st.markdown(
            '<div class="rio-card rio-card-tight">'
            "<p class=\"rio-mark-label\">Strava isn't connected</p>"
            '<p class="rio-note">Connect Strava in Settings to see your runs here.</p>'
            "</div>",
            unsafe_allow_html=True,
        )
        page = _nav_page("Settings")
        if page is not None:
            st.page_link(
                page,
                label="Open Settings",
                query_params=_link_params(),
            )
        return
    st.markdown(
        '<div class="rio-card rio-card-tight">'
        '<p class="rio-note">Runs could not be loaded. Try Refresh in a moment.</p>'
        "</div>",
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
        times, source, file_error = (None, None, None)
        if _fixture_allowed():
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
                mark_label(mark),
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
            mark_label(pending["choice"]),
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
            mark = f'<p class="rio-week-meta">{_esc(mark_label(applied))}</p>'
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
                with st.expander("Reasons", key=f"season-reasons-{generation}-{number}"):
                    lines = []
                    for session in days:
                        lines.append(
                            '<p class="rio-reason-day">'
                            f'{_esc(session["day_of_week"])} {_esc(_date_text(session["date"]))}'
                            "</p>"
                            f'{_plain_reasons(session["reason_codes"])}'
                        )
                    st.markdown("".join(lines), unsafe_allow_html=True)
            _render_mark(plan, number, generation)


def page_start() -> None:
    """Four inputs. Generate calls sequence() and opens Home.

    Start is today. The goal date is five months later. Both times stay blank
    until they are typed. A value already edited on this form stays.
    """
    st.markdown(_css("Start"), unsafe_allow_html=True)
    st.markdown(theme.fullscreen_css(theme.asset_uri(theme.START_PHOTO)), unsafe_allow_html=True)
    st.markdown(theme.shade_html(), unsafe_allow_html=True)
    _render_nav("")
    current_default, start_default, goal_default, goal_day_default = start_form_defaults(date.today())
    start_default = start_on(start_default, _prefs()["start_date"])
    with st.container(key="rio-goal-card"):
        st.markdown(
            _page_hero("Start", "SYNTHETIC / DEMO", "Current 800, the start, the goal, the date."),
            unsafe_allow_html=True,
        )
        left, right = st.columns(2, gap="medium")
        with left:
            current_time = st.text_input(
                "Current 800",
                key="start_current_time",
                **_fresh_value("start_current_time", current_default),
            )
        with right:
            start_date = st.date_input(
                "Start date",
                key="start_start_date",
                **_fresh_value("start_start_date", start_default),
            )
        left, right = st.columns(2, gap="medium")
        with left:
            goal_time = st.text_input(
                "Goal 800",
                key="start_goal_time",
                **_fresh_value("start_goal_time", goal_default),
            )
        with right:
            goal_date = st.date_input(
                "Goal date",
                key="start_goal_date",
                **_fresh_value("start_goal_date", goal_day_default),
            )
        generate = st.button("Generate", type="primary", width="stretch")
    st.markdown(theme.credit_html(theme.START_CREDIT), unsafe_allow_html=True)
    if not generate:
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


def _plan_weeks(start: date, goal: date, length: int, sessions: list) -> None:
    """Week status from the plan. The charts stay off this list."""
    actuals = st.session_state.get("season_actuals")
    marks = st.session_state.get("season_marks")
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
    if not rows:
        return
    with st.expander("Weeks", expanded=False):
        st.markdown(
            '<div class="rio-progress-list">'
            + "".join(_progress_html(row) for row in rows)
            + "</div>",
            unsafe_allow_html=True,
        )


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
    return f"Week {week} · {mark_label(name)}"


def _semi_right(cx: float, cy: float, radius: float) -> str:
    """12 o'clock to 6 o'clock through the right side."""
    return (
        f"A {radius:.2f} {radius:.2f} 0 0 1 {cx + radius:.2f} {cy:.2f} "
        f"A {radius:.2f} {radius:.2f} 0 0 1 {cx:.2f} {cy + radius:.2f} "
    )


def _bend_up(cx: float, cy: float, radius: float, sweep: str) -> str:
    """6 o'clock to 12 o'clock. sweep 0 leaves through the right, 1 through the left."""
    side = 1.0 if sweep == "0" else -1.0
    return (
        f"A {radius:.2f} {radius:.2f} 0 0 {sweep} {cx + side * radius:.2f} {cy:.2f} "
        f"A {radius:.2f} {radius:.2f} 0 0 {sweep} {cx:.2f} {cy - radius:.2f} "
    )


def _bend_down(cx: float, cy: float, radius: float, sweep: str) -> str:
    """12 o'clock to 6 o'clock. sweep 1 leaves through the right, 0 through the left."""
    side = 1.0 if sweep == "1" else -1.0
    return (
        f"A {radius:.2f} {radius:.2f} 0 0 {sweep} {cx + side * radius:.2f} {cy:.2f} "
        f"A {radius:.2f} {radius:.2f} 0 0 {sweep} {cx:.2f} {cy + radius:.2f} "
    )


def _track_svg() -> str:
    """Eight lanes in the reference oval. The home straight runs out to the left.

    The viewBox is unchanged, so the cards under the track stay put.
    """
    lanes = 8
    outer = 168.0
    inner = outer * (47.4 / 95.5)
    lane = (outer - inner) / lanes
    straight = outer * (117.6 / 95.5)
    vb_x, vb_y, vb_w, vb_h = 36.0, -6.0, 726.0, 388.0
    cy = 18.0 + outer
    mid = vb_x + vb_w / 2.0
    lx = mid - straight / 2.0
    rx = lx + straight
    left_end = lx - outer
    infield = (
        f"M {lx:.2f} {cy - inner:.2f} H {rx:.2f} "
        f"{_semi_right(rx, cy, inner)}"
        f"H {lx:.2f} {_bend_up(lx, cy, inner, '1')} Z"
    )
    shell = (
        f"M {lx:.2f} {cy - outer:.2f} H {rx:.2f} "
        f"{_semi_right(rx, cy, outer)}"
        f"H {left_end:.2f} V {cy:.2f} "
        f"A {outer:.2f} {outer:.2f} 0 0 1 {lx:.2f} {cy - outer:.2f} Z"
    )
    band = (
        f'<path fill="#000" d="{infield}"/>'
        f'<path fill="currentColor" fill-rule="evenodd" d="{shell} {infield}"/>'
    )
    lines = []
    for index in range(lanes + 1):
        radius = inner + lane * index
        lines.append(
            '<path fill="none" stroke="#fff" stroke-opacity="0.9" stroke-width="1.35" '
            f'd="M {left_end:.2f} {cy + radius:.2f} H {rx:.2f} '
            f"{_bend_up(rx, cy, radius, '0')}"
            f"H {lx:.2f} {_bend_down(lx, cy, radius, '0')}\"/>"
        )
    return (
        f'<svg class="rio-track-svg" viewBox="{vb_x:.1f} {vb_y:.1f} {vb_w:.1f} {vb_h:.1f}" '
        'aria-hidden="true">'
        f"{band}{''.join(lines)}</svg>"
    )


def _pace_marks() -> tuple[str, date, str, date] | None:
    """Current 800, start, goal 800, and goal date already stored with the season."""
    inputs = st.session_state.get("season_inputs")
    if not inputs_ok(inputs):
        return None
    try:
        start = date.fromisoformat(inputs[1])
        goal_day = date.fromisoformat(inputs[3])
    except ValueError:
        return None
    return str(inputs[0]), start, str(inputs[2]), goal_day


def _positive_numbers(values: object) -> list[float]:
    if not isinstance(values, (list, tuple)):
        return []
    found = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        number = float(value)
        if number > 0:
            found.append(number)
    return found


def _pace_logs(sessions: list) -> list[PaceLog]:
    """Logged race and workout times. A stored result wins over a matched file."""
    actuals = _actuals()
    activities = _stored_activities()
    logs = []
    for session in sessions or []:
        if not isinstance(session, dict):
            continue
        text = session.get("date")
        template = str(session.get("template_id") or "").strip()
        if not isinstance(text, str) or not template:
            continue
        try:
            day = date.fromisoformat(text)
        except ValueError:
            continue
        numbers: list[float] = []
        saved = actuals.get(text) if isinstance(actuals, dict) else None
        if isinstance(saved, dict) and saved.get("template_id") == template:
            numbers = _positive_numbers(saved.get("numbers"))
            if not numbers:
                numbers = _positive_numbers(saved.get("slots"))
        if not numbers:
            match = matched_on(activities, text)
            if isinstance(match, dict):
                numbers = _positive_numbers(match.get("reps"))
        if not numbers:
            continue
        logs.append(PaceLog(day, sum(numbers) / len(numbers), template))
    return logs


def _pace_bundle(template_id: object, day: object) -> dict | None:
    """Target line, tolerance, block, and status for one prescribed day."""
    marks = _pace_marks()
    if marks is None or not isinstance(day, str):
        return None
    try:
        on = date.fromisoformat(day)
    except ValueError:
        return None
    plan = st.session_state.get("season_plan")
    sessions = plan.get("sessions") if isinstance(plan, dict) else []
    if not isinstance(sessions, list):
        sessions = []
    current, start, goal_mark, goal_day = marks
    try:
        return workout_times(
            template_id,
            current_mark=current,
            goal_mark=goal_mark,
            start=start,
            goal_date=goal_day,
            on=on,
            logs=_pace_logs(sessions),
        )
    except ValueError:
        return None


def _pace_status_label() -> str:
    """On track, Ahead, or Behind for today. On track when the season is missing."""
    marks = _pace_marks()
    if marks is None:
        return "On track"
    plan = st.session_state.get("season_plan")
    sessions = plan.get("sessions") if isinstance(plan, dict) else []
    if not isinstance(sessions, list):
        sessions = []
    current, start, goal_mark, goal_day = marks
    try:
        found = project_800(
            current_mark=current,
            goal_mark=goal_mark,
            start=start,
            goal_date=goal_day,
            on=date.today(),
            logs=_pace_logs(sessions),
        )
    except ValueError:
        return "On track"
    text = str(found.get("status") or "on track")
    return text[:1].upper() + text[1:]


def _pace_unit() -> str:
    """Per mile or per km. The plan stays in meters."""
    return _prefs().get("pace_units") or "mi"


def _split_html(template_id: object, day: object) -> str:
    """Per-rep target, or pace for a continuous run. Blank when the id has none.

    Easy, aerobic, and long runs show pace in the chosen unit. A total
    clock time is not used for those. Rep workouts keep the rep line.
    """
    found = _pace_bundle(template_id, day)
    if not isinstance(found, dict):
        return ""
    recipe = workout_recipe(template_id)
    hidden = ""
    ident = str(template_id or "").strip()
    if ident:
        hidden = f'<span hidden class="rio-template-id">{_esc(ident)}</span>'
    if recipe and recipe["continuous"] and found.get("reps"):
        row = found["reps"][0]
        target = format_pace(row["meters"], row["seconds"], _pace_unit())
        if not target:
            return ""
        actual = _actual_pace(day, _pace_unit())
        line = f"Target {target}" if not actual else f"Target {target} · Actual {actual}"
        return (
            '<div class="rio-pace">'
            f'<p class="rio-pace-line">{_esc(line)}</p>'
            f"{hidden}</div>"
        )
    line = str(found.get("line") or "").strip()
    tolerance = str(found.get("tolerance") or "").strip()
    block = str(found.get("block") or "").strip()
    if not line:
        return ""
    block_html = ""
    if block and not (recipe and recipe.get("speed")):
        block_html = f'<p class="rio-pace-block">Block {_esc(block)}</p>'
    return (
        '<div class="rio-pace">'
        f'<p class="rio-pace-line">{_esc(line)}</p>'
        f'<p class="rio-pace-range">Tolerance {_esc(tolerance)}</p>'
        f"{block_html}"
        f"{hidden}</div>"
    )


def recipe_continuous(template_id: object, day: object = None) -> bool:
    """True for an easy, aerobic, or long run that is one effort."""
    recipe = workout_recipe(template_id)
    return bool(recipe and recipe["continuous"])


def _target_pace(template_id: object, day: object) -> str:
    found = _pace_bundle(template_id, day)
    if not isinstance(found, dict) or not found.get("reps"):
        return ""
    row = found["reps"][0]
    return format_pace(row["meters"], row["seconds"], _pace_unit())


def _actual_pace(day: object, unit: str) -> str:
    """Pace for the run stored on this date. Blank when that run has no time."""
    text = str(day or "")
    runs = st.session_state.get("rio_strava_runs")
    if isinstance(runs, list):
        for run in runs:
            if isinstance(run, dict) and str(run.get("date") or "") == text:
                found = effort_pace(run, unit)
                if found:
                    return found
    activities = st.session_state.get("season_activities")
    if isinstance(activities, list):
        for row in activities:
            if isinstance(row, dict) and str(row.get("date") or "") == text:
                found = effort_pace(row, unit)
                if found:
                    return found
    return ""


def _track_fact(label: str, value: str) -> str:
    return (
        '<div class="rio-track-fact">'
        f"{_label(label)}"
        f'<p class="rio-track-fact-value">{_esc(value)}</p>'
        "</div>"
    )


def _track_stage(workout: dict | None) -> str:
    """The oval, with the next session beside it. Display only."""
    if isinstance(workout, dict):
        template = str(workout.get("template_id") or "").strip()
        day = str(workout.get("day_of_week") or "—")
        when = _date_text(workout.get("date") or "—")
        facts = session_facts(template, _WORKOUT_TEXT.get(template, ""))
        distance = _copy(facts["distance"])
        ident = _id_html(template, "rio-track-id")
        caption = (
            '<div class="rio-track-fact">'
            f"{_label('Next workout')}"
            f'<p class="rio-track-day">{_esc(day)}'
            f'<span class="rio-track-sub">{_esc(when)}</span></p>'
            "</div>"
        )
        pace = str(facts["pace"])
        target = ""
        if recipe_continuous(template, workout.get("date")):
            target = _target_pace(template, workout.get("date"))
        if target:
            pace = f"{pace} · {target}"
        rest = str(facts["rest"])
        reps = str(facts["reps"])
        split = _split_html(template, workout.get("date"))
    else:
        distance = pace = rest = reps = "—"
        split = ""
        ident = ""
        caption = (
            '<div class="rio-track-fact">'
            f"{_label('Next workout')}"
            '<p class="rio-track-day">—</p>'
            "</div>"
        )
    details = "".join(
        (
            caption,
            _track_fact("Distance", distance),
            _track_fact("Pace", pace),
            _track_fact("Rest", rest),
            _track_fact("Reps", reps),
        )
    )
    return (
        '<div class="rio-track-stage rio-next-band">'
        f'<div class="rio-track-frame">{_track_svg()}</div>'
        f'<div class="rio-track-facts">{details}{ident}{split}</div>'
        "</div>"
    )


def _track_hero(workout: dict) -> None:
    """The track opens that session. The plan stays as stored."""
    day = str(workout.get("day_of_week") or "—")
    when = str(workout.get("date") or "—")
    plain = _workout_text(workout.get("template_id"))
    html = _track_stage(workout)
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


_WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def _upcoming_days(sessions: list, today: date, count: int = 3) -> list:
    """The three calendar days after today. Today is not in this list.

    A day with no session still takes a card. The plan is unchanged.
    """
    by_date: dict[date, dict] = {}
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
        if day <= today or day in by_date:
            continue
        by_date[day] = session
    rows = []
    for offset in range(1, count + 1):
        day = today + timedelta(days=offset)
        found = by_date.get(day)
        if found is not None:
            rows.append(found)
            continue
        rows.append(
            {
                "date": day.isoformat(),
                "day_of_week": _WEEKDAYS[day.weekday()],
                "template_id": "",
            }
        )
    return rows


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


def _activity_figures(meters: list, points: list, units: str) -> str:
    """Two big totals above the activity charts. The charts keep the detail."""
    total = 0
    for value in meters or []:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        total += int(value)
    shown = format_span(total, "mi" if units == "miles" else "km")
    bpm = "—"
    if points:
        last = points[-1]
        number = last.get("bpm") if isinstance(last, dict) else None
        if isinstance(number, (int, float)) and not isinstance(number, bool):
            text = str(int(number)) if float(number).is_integer() else f"{number:.1f}"
            bpm = f"{text} bpm"
    return (
        '<div class="rio-stat-row">'
        + _stat_tile("Completed work", shown)
        + _stat_tile("Latest heart rate", bpm)
        + "</div>"
    )


def _stat_tile(label: str, value: object) -> str:
    """One home figure. The same glass tile for every stat."""
    return (
        '<div class="rio-stat-tile">'
        f"{_label(label)}"
        f'<p class="rio-stat-value">{_esc(_plain(value))}</p>'
        "</div>"
    )


def _track_meta(view: dict, pace_status: str = "") -> str:
    """Days, phase, last mark, this week, and the pace status."""
    remaining = view.get("days_remaining")
    number = (
        str(remaining)
        if isinstance(remaining, int) and not isinstance(remaining, bool)
        else "—"
    )
    mark = view.get("mark")
    tiles = (
        _stat_tile("Days to goal", number)
        + _stat_tile("Current phase", _phase_text(view.get("phase")))
        + _stat_tile("Last mark", _mark_text(mark if isinstance(mark, dict) else None))
        + _stat_tile("This week", view.get("focus"))
    )
    kind = "rio-stat-row"
    if pace_status:
        tiles += _stat_tile("Pace status", pace_status)
        kind = "rio-stat-row rio-stat-five"
    return f'<div class="{kind}">{tiles}</div>'


def _season_goal_text() -> str:
    """The goal 800 already stored with this season. Display only."""
    inputs = st.session_state.get("season_inputs")
    if isinstance(inputs, (list, tuple)) and len(inputs) > 2:
        text = str(inputs[2] or "").strip()
        if text:
            return text
    return ""


def _home_headline(days: object, goal: str) -> str:
    """Giant line such as 151 days to 1:55, from values already on the page."""
    mark = goal or "goal"
    if isinstance(days, int) and not isinstance(days, bool):
        unit = "day" if days == 1 else "days"
        return (
            f'<span class="rio-display-num">{days}</span>'
            f'<span class="rio-display-rest"> {unit} to {_esc(mark)}</span>'
        )
    return _esc("—")


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
    st.markdown('<p class="rio-index rio-index-pad">04  /  Open</p>', unsafe_allow_html=True)
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

    The next workout is the first session on or after today. The track
    shows that session's distance, pace, rest, and reps. Days until the
    goal and the current phase sit under the track. The phase and the
    one-line focus are that week's, from reason codes already stored.
    The last mark is the latest week mark, when one exists. Days until the
    goal count from today. Opening this page reads the last 14 days and
    matches each activity to that date. An unmarked quality day can already
    hold the mark from those WORK times. An unmatched activity is an extra
    session. No prose, so this page does not spend. No scores.
    """
    chrome = st.container(gap=None)
    hero = st.container(gap=None)
    with chrome:
        st.markdown(_css("Home"), unsafe_allow_html=True)
        _render_nav("Home")
    named = _display_name()
    hello = hey(named)
    title = plan_title(named)

    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        with hero:
            if error:
                greet = f'<p class="rio-hello">{_esc(hello)}</p>' if hello else ""
                st.markdown(
                    '<header class="rio-hero">'
                    ''
                    "<h1>Home</h1>"
                    f"{greet}"
                    f'<p class="rio-error">{_esc(error)}</p></header>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    _page_hero("Home", "SYNTHETIC / DEMO", hello or None),
                    unsafe_allow_html=True,
                )
        if not error:
            _season_prompt()
        return

    length = plan.get("season_length_weeks")
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        with hero:
            st.markdown(
                _page_hero("Home", "SYNTHETIC / DEMO", hello or None),
                unsafe_allow_html=True,
            )
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
    headline = _home_headline(view.get("days_remaining"), _season_goal_text())
    greet = ""
    if hello:
        greet += f'<p class="rio-hello">{_esc(hello)}</p>'
    if title:
        greet += f'<p class="rio-hello-plan">{_esc(title)}</p>'
    with hero:
        st.markdown(
            '<header class="rio-hero rio-home-hero">'
            ''
            '<div class="rio-home-grid"><div class="rio-home-copy">'
            f'<h1 class="rio-display">{headline}</h1>'
            f"{greet}"
            "</div>"
            f'<div class="rio-hero-art">{_track_svg()}</div>'
            "</div></header>",
            unsafe_allow_html=True,
        )
        st.markdown(_track_meta(view, _pace_status_label()), unsafe_allow_html=True)
        from ui.strava_ui import home_line

        line = home_line()
        if line:
            st.markdown(line, unsafe_allow_html=True)
        st.markdown(
            '<p class="rio-index rio-index-pad">02  /  Next workout</p>',
            unsafe_allow_html=True,
        )
        if isinstance(workout, dict):
            _track_hero(workout)
        else:
            st.markdown(_track_stage(None), unsafe_allow_html=True)
            st.markdown(
                '<p class="rio-empty">No workout left in this plan.</p>',
                unsafe_allow_html=True,
            )
    upcoming = _upcoming_days(sessions, date.today(), 3)
    if upcoming:
        st.markdown(
            '<p class="rio-index rio-index-pad">03  /  Next 3 days</p>',
            unsafe_allow_html=True,
        )
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
        st.markdown(_css("Calendar"), unsafe_allow_html=True)
        _render_nav("Calendar")

    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        with hero:
            if error:
                st.markdown(
                    '<header class="rio-hero">'
                    ''
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
        family = str(row.get("family") or "")
        token = "".join(ch for ch in family.lower() if ch.isalnum() or ch == "_")
        cap_class = f"rio-lib-cap rio-cap rio-cap-{token}" if token else "rio-lib-cap rio-cap"
        parts.append(
            '<div class="rio-lib-row">'
            '<div class="rio-lib-main">'
            f'<div class="rio-lib-name">{_esc(_copy(row["description"]))}</div>'
            f"{ident}"
            "</div>"
            f'<div class="{cap_class}">{_esc(row["capacity"])}</div>'
            "</div>"
        )
    return f'<div class="rio-lib">{"".join(parts)}</div>'


def page_library() -> None:
    """Every template on the frozen menu.

    Search matches the name, the id, or the capacity. Capacity and phase
    each narrow the same list. The phase list is the one the season already
    uses. No prose, so this page does not spend. No scores.
    """
    st.markdown(_css("Library"), unsafe_allow_html=True)
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
        st.markdown(_css("Progress"), unsafe_allow_html=True)
        _render_nav("Progress")

    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        with hero:
            if error:
                st.markdown(
                    '<header class="rio-hero">'
                    ''
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
    if not _EMBEDDING or not st.session_state.get("_rio_volume_shown"):
        current = next(
            (index for index, row in enumerate(rows) if row.get("status") == "current"),
            None,
        )
        chart = volume_chart(
            [row["meters"] for row in rows],
            _prefs()["units"],
            [display_distance(str(row.get("volume") or ""), _prefs()["units"]) for row in rows],
            current,
        )
        if chart:
            st.markdown(chart, unsafe_allow_html=True)
    if not _EMBEDDING or not st.session_state.get("_rio_heart_shown"):
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
        st.markdown(_css("Weekly"), unsafe_allow_html=True)
        _render_nav("Weekly")

    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        with hero:
            if error:
                st.markdown(
                    '<header class="rio-hero">'
                    ''
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
                ("Marks", plain_marks(recap["marks"])),
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
                f'<p class="rio-week-meta">{_esc(mark_label(applied))}</p>',
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
        st.markdown(_css("Season"), unsafe_allow_html=True)
        _render_nav("Season")

    plan, start, goal, error = _stored_season()
    with hero:
        st.markdown(_hero_html(start, goal, plan, error), unsafe_allow_html=True)
    if plan is None or start is None or goal is None:
        return
    _render_schedule(plan, int(st.session_state.get("season_generation") or 0))


def _prep_list(items: tuple[str, ...]) -> str:
    rows = "".join(f"<li>{_esc(item)}</li>" for item in items)
    return f'<ul class="rio-prep-list">{rows}</ul>'


def _prep_lead(text: str) -> str:
    return f'<p class="rio-prep-lead">{_esc(text)}</p>'


def _prep_block(title: str, body: str) -> str:
    return (
        '<section class="rio-prep-block">'
        f'<p class="rio-mark-label">{_esc(title)}</p>'
        f"{body}"
        "</section>"
    )


def _prep_lines(session: dict) -> str:
    """Fixed notes after the workout. The same copy on every session.

    Nothing here is written onto the session, the template, or the plan,
    so adapt() never reads it. The result boxes stay as they are. No score.
    """
    blocks = (
        _prep_block("Pre-warm-up", '<p class="rio-prep-line">1 × 800 m easy</p>'),
        _prep_block(
            "Warm-up",
            _prep_lead("Active drills (20–30 m each):")
            + _prep_list(
                (
                    "Arm swings forward and reverse",
                    "Walking quad stretch",
                    "Hamstring sweeps",
                    "Lateral leg swings",
                    "Alternating knee drops",
                    "Rocking adductor stretch",
                )
            )
            + _prep_lead("Dynamic drills (20–30 m each):")
            + _prep_list(
                (
                    "A-skips",
                    "B-skips",
                    "Knee buffs",
                    "Straight-leg bounds",
                    "Lateral skips",
                )
            )
            + _prep_lead("Then:")
            + _prep_list(("4 × 100 m strides with walk-back",)),
        ),
        _prep_block(
            "Cool-down",
            _prep_lead("1 easy lap, then seated stretches for the full lower body:")
            + _prep_list(
                (
                    "Seated forward fold",
                    "Seated figure-four each side",
                    "Seated straddle",
                    "Seated hip-flexor each side",
                    "Seated calf stretch each side",
                    "Seated hamstring each side",
                    "Lying spinal twist each side",
                )
            ),
        ),
        _prep_block(
            "Core",
            _prep_lead("3 rounds of:")
            + _prep_list(
                (
                    "Plank",
                    "Side plank each side",
                    "Dead bug each side",
                    "Bird-dog each side",
                    "Glute bridge",
                    "Bicycle crunch each side",
                    "Reverse crunch",
                    "Split-lunge jumps (low volume)",
                )
            ),
        ),
    )
    return f'<div class="rio-prep">{"".join(blocks)}</div>'


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
    the structure, the fixed prep notes, and the reason words are
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
        st.markdown(_css("Session"), unsafe_allow_html=True)
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
        _split_html(session.get("template_id"), session.get("date")),
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
        st.markdown(_css("Activity"), unsafe_allow_html=True)
        _render_nav("Activity")

    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        with hero:
            if error:
                st.markdown(
                    '<header class="rio-hero">'
                    ''
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
            _season_prompt()
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

    with hero:
        st.markdown(
            _page_hero(
                "Activity",
                _activity_banner(_stored_activities(), st.session_state.get("season_actuals")),
                f"{_date_text(start)} — {_date_text(goal)}",
            ),
            unsafe_allow_html=True,
        )
    units = _prefs()["units"]
    pace = _pace_unit()
    with st.container(key="rio-activity-refresh"):
        st.button("Refresh", key="activity-refresh")
    _activities_notice()
    from ui.activity_board import (
        activity_style,
        build_cards,
        card_html,
        group_weeks,
        heart_axis_chart,
        heart_points,
        summary_html,
        week_summary,
        weekly_meters,
    )
    from ui.strava_ui import prepare_activity, status_html

    prepare_activity()
    st.markdown(status_html(), unsafe_allow_html=True)
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
    meters = weekly_completed_meters(rows, start=start, length=length) if rows else []
    points = heart_rate_points(rows) if rows else []
    st.markdown(_activity_figures(meters, points, units), unsafe_allow_html=True)
    runs = st.session_state.get("rio_strava_runs")
    marks = st.session_state.get("season_inputs")
    current_mark = str(marks[0]) if isinstance(marks, (list, tuple)) and len(marks) == 4 else ""
    goal_mark = str(marks[2]) if isinstance(marks, (list, tuple)) and len(marks) == 4 else ""
    cards = build_cards(
        runs if isinstance(runs, list) else [],
        activities,
        sessions,
        current=current_mark,
        goal=goal_mark,
        start=start,
        goal_day=goal,
        unit=pace,
        date_format=date_format,
    )
    st.markdown(activity_style() + summary_html(week_summary(cards, date.today(), pace)), unsafe_allow_html=True)
    volume_units = "miles" if pace == "mi" else "km"
    volume_values = weekly_meters(cards, start, length)
    volume_shown = False
    heart_shown = False
    if volume_values:
        highlight = _week_containing(start, length, date.today()) - 1
        end = min(len(volume_values), max(highlight, 0) + 1)
        shown_meters = volume_values[:end]
        captions = [display_distance(f"{value:,} m", volume_units) for value in shown_meters]
        chart = volume_chart(
            shown_meters,
            volume_units,
            captions,
            end - 1,
        )
        if chart:
            st.markdown(chart, unsafe_allow_html=True)
            volume_shown = True
    axis = heart_axis_chart(heart_points(cards))
    if axis:
        st.markdown(axis, unsafe_allow_html=True)
        heart_shown = True
    for group in group_weeks(cards, date.today()):
        with st.expander(group["title"], expanded=group["open"]):
            body = "".join(card_html(card) for card in group["cards"])
            st.markdown(body or '<p class="rio-empty">No runs this week.</p>', unsafe_allow_html=True)
    legacy = ['<div hidden class="rio-legacy-activity">']
    if not rows:
        legacy.append('<p class="rio-empty">No matched activities.</p>')
    else:
        heart = heart_rate_chart(
            points,
            start=start,
            weeks=length,
            captions=_activity_date_captions(rows),
        )
        if heart:
            legacy.append(heart)
        legacy.append(_label("Sessions"))
        legacy.append(_activity_table(rows))
    if all_rows:
        legacy.append(_label("All activities"))
        legacy.append(_all_activities_table(all_rows))
    legacy.append("</div>")
    st.markdown("".join(legacy), unsafe_allow_html=True)
    st.session_state["_rio_volume_shown"] = volume_shown
    st.session_state["_rio_heart_shown"] = heart_shown


def _season_prompt() -> None:
    """The way onto Start when this account has no season yet."""
    if _start_page is not None:
        st.page_link(
            _start_page,
            label="Generate Season Plan",
            query_params=_link_params(),
        )
    return


def _setting_widgets(prefs: dict) -> None:
    """Seed the controls once. Later runs keep the widget value."""
    seed = {
        "settings-units": prefs["units"],
        "settings-pace": prefs.get("pace_units") or "mi",
        "settings-ids": prefs["show_ids"],
        "settings-compact": prefs["compact"],
        "settings-dates": prefs["date_format"],
        "settings-confirm": prefs["confirm_adapt"],
        "settings-start": prefs["start_date"],
        "settings-reminders": prefs["reminders"],
        "settings-recap": prefs["recap"],
    }
    for key, value in seed.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _settings_line(kind: str, text: str) -> None:
    st.markdown(f'<p class="rio-{kind}">{_esc(text)}</p>', unsafe_allow_html=True)


def _seed_profile_fields(local: dict, email: str) -> None:
    zone = local.get("timezone") if isinstance(local.get("timezone"), str) else ""
    if zone not in TIME_ZONES:
        zone = suggested_timezone()
    cloud_name = st.session_state.get("rio_cloud_name")
    stored_name = local.get("name") if isinstance(local.get("name"), str) else ""
    if not stored_name and isinstance(cloud_name, str):
        stored_name = cloud_name
    seed = {
        "settings-name": stored_name,
        "settings-preferred": local.get("preferred") if isinstance(local.get("preferred"), str) else "",
        "settings-timezone": zone,
        "settings-email": email,
    }
    for key, value in seed.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _save_hosted_pace(unit: str) -> None:
    """Store pace units on the signed-in athlete. A local account uses the profile file."""
    if st.session_state.get("rio_test_preview"):
        return
    if st.session_state.get("rio_account_secret") != "cloud":
        return
    if unit not in ("mi", "km"):
        return
    if st.session_state.get("rio_pace_saved") == unit:
        return
    token = st.session_state.get("rio_cloud_access")
    if not isinstance(token, str) or not token:
        return
    from ui.cloud_store import current_directory

    directory = current_directory()
    if directory is None or not hasattr(directory, "save_pace_units"):
        return
    try:
        directory.save_pace_units(token, unit)
    except Exception:
        return
    st.session_state["rio_pace_saved"] = unit


def _persist_local(name: object, preferred: object, timezone: object, settings: dict) -> None:
    """Write name and preferences when they differ from the stored profile."""
    if st.session_state.get("rio_test_preview"):
        return
    who = _account_identity()
    if who is None:
        return
    local = st.session_state.get("rio_local")
    current = local if isinstance(local, dict) else {}
    stored_name = current.get("name") if isinstance(current.get("name"), str) else ""
    draft = name
    if normalize_name(name) is None:
        if isinstance(name, str) and name.strip():
            _settings_line("error", "Enter a name.")
        elif stored_name:
            _settings_line("error", "Enter a name.")
        draft = stored_name
    if st.session_state.get("rio_account_secret") == "cloud":
        if isinstance(draft, str) and draft.strip():
            st.session_state["rio_cloud_name"] = draft.strip()
        st.session_state["rio_local"] = {
            "name": draft if isinstance(draft, str) else "",
            "preferred": preferred if isinstance(preferred, str) else "",
            "timezone": timezone if isinstance(timezone, str) else "",
            "settings": dict(settings),
        }
        from ui.cloud_ui import persist_cloud_season

        persist_cloud_season()
        return
    try:
        saved = write_local(
            accounts_path(),
            who[0],
            who[1],
            draft,
            preferred,
            timezone,
            settings,
        )
    except AccountError as exc:
        _settings_line("error", str(exc))
        return
    previous = current.get("settings") if isinstance(current.get("settings"), dict) else {}
    if normalize_prefs(previous).get("start_date") != saved["settings"].get("start_date"):
        st.session_state.pop("start_start_date", None)
    st.session_state["rio_local"] = saved
    st.session_state["rio_local_email"] = who[0]
    st.session_state["rio_settings"] = dict(saved["settings"])


def _clear_season_marks() -> None:
    """Drop marks and actuals. The season is rebuilt from the four inputs."""
    if st.session_state.get("rio_test_preview"):
        return
    who = _account_identity()
    inputs = st.session_state.get("season_inputs")
    if who is None or not inputs_ok(inputs) or not isinstance(st.session_state.get("season_plan"), dict):
        st.session_state["rio_settings_error"] = "Generate a season on Start."
        st.rerun()
    try:
        fresh = sequence(*inputs)
    except ValueError as exc:
        st.session_state["rio_settings_error"] = str(exc)
        st.rerun()
    st.session_state["season_plan"] = fresh
    st.session_state["season_marks"] = {}
    st.session_state["season_actuals"] = {}
    st.session_state["season_activities"] = []
    st.session_state["season_quality_base"] = {}
    st.session_state["rio_store_loaded"] = True
    st.session_state["season_generation"] = int(st.session_state.get("season_generation") or 0) + 1
    try:
        write_record(
            accounts_path(),
            who[0],
            who[1],
            storage_key(inputs),
            dump_record({}, {}, []),
        )
    except AccountError as exc:
        st.session_state["rio_settings_error"] = str(exc)
        st.rerun()
    st.session_state["rio_settings_note"] = "Marks and actuals are cleared."
    st.rerun()


def _reset_saved_plan() -> None:
    """Remove stored seasons. The account stays."""
    if st.session_state.get("rio_test_preview"):
        return
    who = _account_identity()
    if who is None:
        return
    try:
        delete_records(accounts_path(), who[0], who[1], KEY_PREFIX)
    except AccountError as exc:
        st.session_state["rio_settings_error"] = str(exc)
        st.rerun()
    for key in (
        "activities_loaded",
        "activities_notice",
        "activities_trigger",
        "rio_adapt_pending",
        "rio_profile",
        "rio_store_loaded",
        "season_activities",
        "season_actuals",
        "season_generation",
        "season_inputs",
        "season_link_attempt",
        "season_link_error",
        "season_marks",
        "season_plan",
        "season_quality_base",
    ):
        st.session_state.pop(key, None)
    st.query_params.clear()
    if _start_page is not None:
        st.switch_page(_start_page)


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


def _profile_storage_key(inputs: tuple[str, str, str, str]) -> str:
    """This account's goal, in this browser. Another account has another key."""
    who = st.session_state.get("rio_account")
    email = who if isinstance(who, str) else ""
    return email + "\n" + profile_key(inputs)


def _profile_slot(inputs: tuple[str, str, str, str]) -> dict:
    """This account's saved goal, read once. A miss stays empty."""
    key = _profile_storage_key(inputs)
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
    """Save the goal time for this account. The URL and the season stay put."""
    slot = st.session_state.get("rio_profile")
    key = _profile_storage_key(inputs)
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
                    ''
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
                    "key": _profile_storage_key(inputs),
                    "loaded": True,
                    "goal_time": cleaned,
                    "dirty": True,
                }
                st.session_state["profile_goal_apply"] = cleaned
                st.rerun()
        if isinstance(slot.get("goal_time"), str) and slot.get("goal_time"):
            st.markdown(
                '<p class="rio-settings-note">Saved for this account.</p>',
                unsafe_allow_html=True,
            )
    _write_profile(inputs)


def page_about() -> None:
    """The eight phases, the 10% rule, rules-based labels, and hard-day marks.

    Static copy. This page does not build a plan, label a workout, adapt a
    week, or call a model. Recorded prose spend stays at $25.
    """
    hero, _controls = _open("About")
    photo = theme.asset_uri(theme.ABOUT_PHOTO)
    image = f"url('{photo}')" if photo else "none"
    with hero:
        st.markdown(
            f'<header class="rio-about-banner" style="background-image:{image}">'
            '<div class="rio-about-shade" aria-hidden="true"></div>'
            '<div class="rio-about-title">'
            '<p class="rio-index rio-index-light">About</p>'
            "<h1>About</h1>"
            "</div>"
            f"{theme.credit_html(theme.ABOUT_CREDIT)}"
            "</header>",
            unsafe_allow_html=True,
        )
    for section in about_sections():
        parts = [_label(section["title"])]
        shown = section.get("shown")
        body = shown if isinstance(shown, list) and shown else section["paragraphs"]
        for index, paragraph in enumerate(body):
            parts.append(_note(paragraph) if index == 0 else _prose(paragraph))
        if section["rows"]:
            parts.append(_fields(section["rows"]))
        if not shown:
            for paragraph in section["closing"]:
                parts.append(_prose(paragraph))
        else:
            hidden = list(section["paragraphs"]) + list(section["closing"])
            if hidden:
                parts.append(
                    '<div hidden>' + "".join(_prose(paragraph) for paragraph in hidden) + "</div>"
                )
        _card(*parts)


def page_settings() -> None:
    """Name, preferences, and account actions on this machine.

    Units, dates, template ids, and compact mode change what is shown.
    Reminders and the weekly recap are stored and are not sent. Nothing
    here is written onto the plan.
    """
    st.markdown(_css("Settings"), unsafe_allow_html=True)
    _render_nav("Settings")
    st.markdown(_page_hero("Settings", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
    notice = st.session_state.pop("rio_settings_error", None)
    note = st.session_state.pop("rio_settings_note", None)
    if isinstance(notice, str) and notice.strip():
        _settings_line("error", notice.strip())
    if isinstance(note, str) and note.strip():
        _settings_line("settings-note", note.strip())
    who = _account_identity()
    email = who[0] if who is not None else ""
    local = st.session_state.get("rio_local")
    if not isinstance(local, dict):
        local = {}
    _seed_profile_fields(local, email)
    _setting_widgets(_prefs())
    zones = list(TIME_ZONES)
    picked = st.session_state.get("settings-timezone")
    if isinstance(picked, str) and picked not in zones:
        zones.insert(0, picked)

    with st.container(key="rio-settings-profile"):
        with st.expander("Profile", expanded=True):
            st.markdown(_label("Profile"), unsafe_allow_html=True)
            name = st.text_input("Name", key="settings-name")
            preferred = st.text_input("Preferred name / nickname", key="settings-preferred")
            st.text_input("Email", key="settings-email", disabled=True)
            timezone = st.selectbox("Time zone", zones, key="settings-timezone")
            st.markdown(
                '<p class="rio-settings-note">First name is enough. Saved on this machine.</p>',
                unsafe_allow_html=True,
            )
            with st.form("rio-password", border=False, clear_on_submit=True):
                current_pw = st.text_input("Current password", type="password")
                new_pw = st.text_input("New password", type="password")
                change_pw = st.form_submit_button("Change password", type="primary")
            if change_pw and who is not None:
                try:
                    secret = change_password(accounts_path(), who[0], who[1], current_pw, new_pw)
                except AccountError as exc:
                    st.session_state["rio_settings_error"] = str(exc)
                    st.rerun()
                _refresh_session(who[0], secret)
                st.session_state["rio_settings_note"] = "Password updated."
                st.rerun()

    with st.container(key="rio-settings-prefs"):
        with st.expander("Preferences", expanded=True):
            st.markdown(_label("Preferences"), unsafe_allow_html=True)
            pace_units = st.radio(
                "Pace units",
                ["mi", "km"],
                format_func=lambda item: "per mile" if item == "mi" else "per km",
                horizontal=True,
                key="settings-pace",
            )
            st.markdown(
                '<p class="rio-settings-note">Distances and paces on Activity, Home, and Plan use this.</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div hidden>'
                '<span>Metric</span><span>Imperial</span>'
                '<span>Dark</span>'
                '<span>Notifications</span>'
                '<span>Workout reminders</span>'
                '<span>Weekly recap</span>'
                '<span>Placeholder. Nothing is sent.</span>'
                "</div>",
                unsafe_allow_html=True,
            )
            start_date = st.radio(
                "Default start date",
                ["today", "sunday"],
                format_func=lambda item: "Today" if item == "today" else "Next Sunday",
                horizontal=True,
                key="settings-start",
            )
            st.markdown(
                '<p class="rio-settings-note">Next Sunday starts the training week.</p>',
                unsafe_allow_html=True,
            )
            if viewer_is_admin(email):
                show_ids = st.toggle("Show template ids", key="settings-ids")
            else:
                show_ids = False
            compact = st.toggle("Compact mode", key="settings-compact")
            date_format = st.radio(
                "Date format",
                ["iso", "short"],
                format_func=lambda item: "ISO" if item == "iso" else "Short",
                horizontal=True,
                key="settings-dates",
            )
            confirm = st.toggle("Confirm before a mark changes later weeks", key="settings-confirm")
    reminders = False
    recap = False

    with st.container(key="rio-settings-data"):
        with st.expander("Data", expanded=True):
            st.markdown(_label("Data"), unsafe_allow_html=True)
            plan = st.session_state.get("season_plan")
            inputs = st.session_state.get("season_inputs")
            if isinstance(plan, dict) and inputs_ok(inputs):
                try:
                    body = export_season(
                        inputs,
                        plan,
                        st.session_state.get("season_marks"),
                        st.session_state.get("season_actuals"),
                    )
                except ValueError:
                    body = ""
                if body:
                    st.download_button(
                        "Export season as JSON",
                        data=body,
                        file_name="rio-season.json",
                        mime="application/json",
                        key="settings-export",
                    )
            else:
                st.markdown(
                    '<p class="rio-settings-note">Generate a season on Start.</p>',
                    unsafe_allow_html=True,
                )

    with st.container(key="rio-settings-account"):
        with st.expander("Account", expanded=True):
            st.markdown(_label("Account"), unsafe_allow_html=True)
            with st.form("rio-email", border=False, clear_on_submit=True):
                new_email = st.text_input("New email")
                email_pw = st.text_input("Password", type="password")
                change_mail = st.form_submit_button("Change email", type="primary")
            if change_mail and who is not None:
                try:
                    updated = change_email(accounts_path(), who[0], who[1], email_pw, new_email)
                except AccountError as exc:
                    st.session_state["rio_settings_error"] = str(exc)
                    st.rerun()
                _refresh_session(updated, who[1])
                st.session_state["rio_settings_note"] = "Email updated."
                st.rerun()

    with st.container(key="rio-settings-privacy"):
        with st.expander("Privacy", expanded=True):
            st.markdown(_label("Privacy"), unsafe_allow_html=True)
            st.markdown(
                '<p class="rio-settings-note">Clears this browser. The account stays on this machine.</p>',
                unsafe_allow_html=True,
            )

    with st.container(key="rio-settings-about"):
        with st.expander("About", expanded=True):
            st.markdown(_label("About"), unsafe_allow_html=True)
            st.markdown(
                f'<p class="rio-settings-note">RIO {_esc(APP_VERSION)}</p>',
                unsafe_allow_html=True,
            )

    with st.container(key="rio-settings-strava"):
        with st.expander("Strava", expanded=True):
            from ui.strava_ui import render_settings

            render_settings()

    with st.container(key="rio-settings-danger"):
        st.markdown('<p class="rio-danger-kicker">Danger zone</p>', unsafe_allow_html=True)
        with st.expander("Danger zone", expanded=True):
            st.markdown(_label("Data"), unsafe_allow_html=True)
            st.checkbox("Confirm clear", key="settings-clear-marks-ok")
            if st.button("Clear all marks / actuals", key="settings-clear-marks"):
                if st.session_state.get("settings-clear-marks-ok") is not True:
                    st.session_state["rio_settings_error"] = "Confirm to clear marks and actuals."
                    st.rerun()
                _clear_season_marks()
            st.checkbox("Confirm reset", key="settings-reset-ok")
            if st.button("Reset plan", key="settings-reset"):
                if st.session_state.get("settings-reset-ok") is not True:
                    st.session_state["rio_settings_error"] = "Confirm to reset the plan."
                    st.rerun()
                _reset_saved_plan()
            st.markdown(
                '<p class="rio-settings-note">Reset removes stored seasons. The account stays.</p>',
                unsafe_allow_html=True,
            )
            st.markdown(_label("Account"), unsafe_allow_html=True)
            st.markdown(
                '<p class="rio-settings-kept" aria-hidden="true">Delete account</p>',
                unsafe_allow_html=True,
            )
            delete_pw = ""
            if not st.session_state.get("rio_cloud_user_id"):
                st.text_input("Type your email to confirm", key="settings-delete-email")
                delete_pw = st.text_input("Password", type="password", key="settings-delete-password")
            st.checkbox("Delete my account", key="settings-delete-cloud-ok")
            if st.button("Delete my account", key="settings-delete-cloud"):
                if st.session_state.get("settings-delete-cloud-ok") is not True:
                    st.session_state["rio_settings_error"] = "Confirm to delete this account."
                    st.rerun()
                if st.session_state.get("rio_cloud_user_id"):
                    from ui.cloud_ui import CloudAuthError, delete_signed_in_account

                    try:
                        delete_signed_in_account()
                    except CloudAuthError as exc:
                        st.session_state["rio_settings_error"] = str(exc)
                        st.rerun()
                else:
                    typed = st.session_state.get("settings-delete-email")
                    typed_email = typed.strip().casefold() if isinstance(typed, str) else ""
                    if typed_email != email:
                        st.session_state["rio_settings_error"] = "Confirm with your email to delete this account."
                        st.rerun()
                    try:
                        delete_account(
                            accounts_path(),
                            email,
                            who[1] if who is not None else "",
                            delete_pw,
                        )
                    except AccountError as exc:
                        st.session_state["rio_settings_error"] = str(exc)
                        st.rerun()
                _sign_out()
            st.markdown(_label("Privacy"), unsafe_allow_html=True)
            st.checkbox("Clear data stored in this browser", key="settings-clear-ok")
            if st.button("Clear local data", key="settings-clear"):
                if st.session_state.get("settings-clear-ok") is not True:
                    st.session_state["rio_settings_error"] = "Confirm to clear local data."
                    st.rerun()
                st.session_state["rio_clear_browser"] = True
                _sign_out()
            st.markdown(
                '<p class="rio-settings-note">Clears this browser. The account stays on this machine.</p>',
                unsafe_allow_html=True,
            )

    stored = normalize_prefs(
        {
            "units": "miles" if pace_units == "mi" else "km",
            "pace_units": pace_units,
            "show_ids": show_ids,
            "compact": compact,
            "date_format": date_format,
            "confirm_adapt": confirm,
            "start_date": start_date,
            "reminders": reminders,
            "recap": recap,
            "notifications": bool(reminders or recap),
        }
    )
    if not stored["confirm_adapt"]:
        _clear_adapt()
    st.session_state["rio_settings"] = stored
    _persist_local(name, preferred, timezone, stored)
    _save_hosted_pace(stored.get("pace_units") or "mi")


def page_plan() -> None:
    """Season length, phase weeks, the month, and the schedule.

    Week cards and the full season keep their marks. A card opens that
    session. This page does not build a plan.
    """
    global _MARK_PREFIX
    st.markdown(_css("Plan"), unsafe_allow_html=True)
    _render_nav("Plan")
    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        if error:
            st.markdown(
                '<header class="rio-hero">'
                ''
                "<h1>Plan</h1>"
                f'<p class="rio-error">{_esc(error)}</p></header>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(_page_hero("Plan", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
            _season_prompt()
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
    st.markdown(
        f'<p class="rio-note">Pace status {_esc(_pace_status_label())}.</p>',
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
    _plan_weeks(start, goal, length, sessions)
    calendar_tab, week_tab, season_tab = st.tabs(["Calendar", "This week", "Full season"])
    saved = _MARK_PREFIX
    try:
        _MARK_PREFIX = "plan-week"
        with calendar_tab:
            _nest(page_calendar)
        with week_tab:
            _nest(page_weekly)
        _MARK_PREFIX = "plan-season"
        with season_tab:
            _nest(page_season)
    finally:
        _MARK_PREFIX = saved


_MORE_BLURB = (
    ("Past seasons", "Seasons you have already saved."),
    ("Profile", "Your current 800, goal, and dates."),
    ("Settings", "Name, pace, and this account."),
    ("About", "Phases, the 10% rule, and what a mark changes."),
    ("Creators", "Chase Rose and Jay Rose."),
)


def page_more() -> None:
    """Past seasons, profile, settings, and about. Links stay in this tab."""
    st.markdown(_css("More"), unsafe_allow_html=True)
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


def page_creators() -> None:
    """Chase Rose and Jay Rose. The bios are editable placeholder text."""
    hero, _controls = _open("Creators")
    with hero:
        st.markdown(
            _page_hero("Creators", "SYNTHETIC / DEMO", "Chase Rose and Jay Rose."),
            unsafe_allow_html=True,
        )
    for person in CREATORS:
        _card(
            _label(str(person["role"])),
            f'<h2 class="rio-week-title">{_esc(person["name"])}</h2>',
            _note(str(person["bio"])),
        )


def page_admin() -> None:
    """Accounts and the startup photos. Other logins are sent home."""
    who = _account_identity()
    email = who[0] if who is not None else ""
    if not viewer_is_admin(email):
        from ui.sample_season_ui import drop_preview

        drop_preview()
        home = _nav_page("Home")
        if home is not None:
            params = _link_params()
            if params:
                st.switch_page(home, query_params=params)
            else:
                st.switch_page(home)
        st.stop()
    pending = st.session_state.pop("rio_test_go", None)
    if pending in ("home", "plan", "activity"):
        target = {"home": "Home", "plan": "Plan", "activity": "Activity"}[pending]
        page = _nav_page(target)
        if page is not None:
            st.switch_page(page)
    st.markdown(_css("Admin"), unsafe_allow_html=True)
    _render_nav("Admin")
    st.markdown(
        _page_hero("Admin", "SYNTHETIC / DEMO", "Accounts and the startup photos."),
        unsafe_allow_html=True,
    )
    if cloud_configured():
        from ui.cloud_ui import admin_account_rows

        if "rio_admin_rows" not in st.session_state:
            st.session_state["rio_admin_rows"] = admin_account_rows()
        rows = st.session_state.get("rio_admin_rows")
        if rows is None:
            _card(
                _label("Accounts"),
                '<p class="rio-note">The account list isn\'t available on this server yet.</p>',
            )
        elif rows:
            table = [
                {
                    "Email": row.get("email") or "—",
                    "Name": row.get("display_name") or "—",
                    "Role": row.get("role") or "athlete",
                }
                for row in rows
            ]
            _card(_label("Accounts"), _table(table), _note("Read only."))
        else:
            _card(_label("Accounts"), '<p class="rio-empty">No accounts yet.</p>', _note("Read only."))
    else:
        rows = account_rows(accounts_path())
        if rows:
            table = [{"Email": row["email"], "Name": row["name"] or "—"} for row in rows]
            _card(_label("Accounts"), _table(table), _note("Read only."))
        else:
            _card(_label("Accounts"), '<p class="rio-empty">No accounts yet.</p>', _note("Read only."))
    from ui.sample_season_ui import render_test_season

    render_test_season()
    _render_hero_editor()


def _render_hero_editor() -> None:
    """Enable, reorder, and edit the credit for the startup photos."""
    photos = load_rotation()
    known = [photo["id"] for photo in photos]
    order = st.session_state.get("rio_hero_order")
    if not isinstance(order, list) or sorted(str(item) for item in order) != sorted(known):
        order = known
        st.session_state["rio_hero_order"] = list(order)
    by_id = {photo["id"]: photo for photo in photos}
    st.markdown(_label("Startup photos"), unsafe_allow_html=True)
    st.markdown(
        '<p class="rio-settings-note">Show, reorder, or edit the credit line.</p>',
        unsafe_allow_html=True,
    )
    notice = st.session_state.pop("rio_hero_notice", None)
    if isinstance(notice, str) and notice.strip():
        st.markdown(
            f'<p class="rio-settings-note">{_esc(notice.strip())}</p>',
            unsafe_allow_html=True,
        )
    problem = st.session_state.pop("rio_hero_error", None)
    if isinstance(problem, str) and problem.strip():
        st.markdown(
            f'<p class="rio-error">{_esc(problem.strip())}</p>',
            unsafe_allow_html=True,
        )
    for index, photo_id in enumerate(list(st.session_state["rio_hero_order"])):
        photo = by_id.get(photo_id)
        if photo is None:
            continue
        st.checkbox(
            "Show on the startup page",
            key=f"hero-on-{photo_id}",
            **_fresh_value(f"hero-on-{photo_id}", bool(photo["enabled"])),
        )
        st.text_input(
            "Credit line",
            key=f"hero-credit-{photo_id}",
            **_fresh_value(f"hero-credit-{photo_id}", str(photo["credit"])),
        )
        with st.container(key=f"rio-hero-move-{photo_id}", horizontal=True, gap="small"):
            up = st.button("Move up", key=f"hero-up-{photo_id}", disabled=index == 0)
            down = st.button(
                "Move down",
                key=f"hero-down-{photo_id}",
                disabled=index + 1 >= len(st.session_state["rio_hero_order"]),
            )
        if up or down:
            current = list(st.session_state["rio_hero_order"])
            swap = index - 1 if up else index + 1
            current[index], current[swap] = current[swap], current[index]
            st.session_state["rio_hero_order"] = current
            st.rerun()
    if st.button("Save photos", type="primary", key="hero-save"):
        drafted = []
        for photo_id in st.session_state["rio_hero_order"]:
            drafted.append(
                {
                    "id": photo_id,
                    "enabled": st.session_state.get(f"hero-on-{photo_id}") is True,
                    "credit": st.session_state.get(f"hero-credit-{photo_id}"),
                }
            )
        try:
            save_rotation(drafted)
        except (ValueError, OSError) as exc:
            st.session_state["rio_hero_error"] = str(exc)
            st.rerun()
        st.session_state["rio_hero_notice"] = "Startup photos saved."
        st.rerun()


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
    """Plan keys on this account. A miss stops before an empty list is drawn."""
    who = _account_identity()
    if who is None:
        return []
    found = record_keys(accounts_path(), who[0], who[1], KEY_PREFIX)
    if not isinstance(found, list):
        st.stop()
    return found


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
    """Seasons this account already stored.

    Each row is a start date, a goal date, and a goal time from a plan key
    on this account. Choosing a row opens that season from those four
    inputs. Nothing here builds a season. No prose, so this page does not
    spend.
    """
    rows = season_entries(_stored_season_keys())
    hero, _controls = _open("Past seasons")
    with hero:
        st.markdown(_page_hero("Past seasons", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
    if not rows:
        st.markdown(
            '<p class="rio-empty">No seasons on this account.</p>',
            unsafe_allow_html=True,
        )
        return
    with st.container(key="rio-past-list"):
        for index, inputs in enumerate(rows):
            _open_past(inputs, first=index == 0)


def _auth_screen() -> str:
    """Log in is the first screen. Create account is the other one."""
    if st.session_state.get("rio_auth_screen") == "create":
        return "create"
    return "login"


def _open_auth(screen: str) -> None:
    """Show Log in or Create account. A notice stays on the screen that wrote it."""
    st.session_state["rio_auth_screen"] = screen
    st.session_state.pop("rio_login_error", None)
    st.rerun()


def _enter_account(signed: tuple[str, str]) -> None:
    """Keep this account for the session. A signed token keeps it for one day."""
    try:
        token = issue_session(signed[0], signed[1], now=int(time.time()))
    except AccountError as exc:
        st.session_state["rio_login_error"] = str(exc)
        st.rerun()
    st.session_state.pop("rio_auth_screen", None)
    st.session_state.pop("rio_login_error", None)
    st.session_state.pop("rio_session_clear", None)
    st.session_state["rio_enter"] = True
    st.session_state["rio_account"] = signed[0]
    st.session_state["rio_account_secret"] = signed[1]
    st.session_state["rio_session_token"] = token
    st.session_state["rio_session_write"] = token
    st.rerun()


def _auth_notice() -> None:
    notice = st.session_state.pop("rio_login_error", None)
    if isinstance(notice, str) and notice.strip():
        st.markdown(
            f'<p class="rio-error">{_esc(notice.strip())}</p>',
            unsafe_allow_html=True,
        )


def _auth_backdrop() -> None:
    """Floodlights behind Log in and Create account. The form sits on a white card."""
    screen = "Create account" if _auth_screen() == "create" else "Log in"
    st.markdown(_css(screen), unsafe_allow_html=True)
    st.markdown(theme.fullscreen_css(theme.asset_uri(theme.LOGIN_PHOTO)), unsafe_allow_html=True)
    st.markdown(theme.shade_html(), unsafe_allow_html=True)


def _render_create_account() -> None:
    """Name, email, and password for a new account. Back returns to Log in."""
    _auth_backdrop()
    with st.container(key="rio-auth-card"):
        st.markdown(
            _page_hero("Create account", "RIO"),
            unsafe_allow_html=True,
        )
        _auth_notice()
        with st.form("rio-create", border=False):
            name = st.text_input("Name", key="rio_create_name")
            email = st.text_input("Email", key="rio_create_email")
            password = st.text_input("Password", type="password", key="rio_create_password")
            create = st.form_submit_button("Create account", type="primary", width="stretch")
        with st.container(key="rio-auth-switch"):
            back = st.button("Back to log in", key="rio-back-login", width="stretch")
        st.markdown(
            '<p class="rio-settings-note">First name is enough. At least 8 characters. Saved on this machine.</p>',
            unsafe_allow_html=True,
        )
    st.markdown(theme.credit_html(theme.LOGIN_CREDIT), unsafe_allow_html=True)
    if back:
        _open_auth("login")
    if not create:
        return
    try:
        signed = create_account(accounts_path(), email, password, name)
    except AccountError as exc:
        st.session_state["rio_login_error"] = str(exc)
        st.rerun()
    _enter_account(signed)


def _render_login() -> None:
    """Email and password. Create account opens its own screen."""
    if cloud_configured():
        from ui.cloud_ui import render_cloud_auth

        render_cloud_auth(_auth_backdrop, _auth_notice, _page_hero)
        return
    if _auth_screen() == "create":
        _render_create_account()
        return
    _auth_backdrop()
    with st.container(key="rio-auth-card"):
        st.markdown(
            _page_hero(
                "Log in",
                "RIO",
                "Use your email and password.",
            ),
            unsafe_allow_html=True,
        )
        _auth_notice()
        if not cloud_configured():
            setup_notice_html()
        with st.form("rio-login", border=False):
            email = st.text_input("Email", key="rio_login_email")
            password = st.text_input("Password", type="password", key="rio_login_password")
            log_in = st.form_submit_button("Log in", type="primary", width="stretch")
        with st.container(key="rio-auth-switch"):
            create = st.button("Create account", key="rio-open-create", width="stretch")
    st.markdown(theme.credit_html(theme.LOGIN_CREDIT), unsafe_allow_html=True)
    if create:
        _open_auth("create")
    if not log_in:
        return
    try:
        signed = authenticate(accounts_path(), email, password)
        if signed is None:
            raise AccountError("Email or password does not match.")
    except AccountError as exc:
        st.session_state["rio_login_error"] = str(exc)
        st.rerun()
    _enter_account(signed)


st.set_page_config(page_title="rio", layout="centered")
load_local_env()
_apply_session_reset()
_session_was_open = _account_identity() is not None
_boot_bridge()
# Once per session. A saved season with sessions opens Home instead.
if startup_pending(st.session_state) and not _has_current_season():
    if render_startup():
        acknowledge_startup(st.session_state)
        st.rerun()
    st.stop()
_restore_session()
_open_restored_session(_session_was_open)
from ui.strava_ui import boot_strava

boot_strava()
_start_page = st.Page(_with_plan(page_start), title="Start", default=True)
_session_page = st.Page(_with_plan(page_session), title="Session", url_path="session")
_HOME_PAGE = _start_page
_SESSION_PAGE = _session_page
_admin_page = st.Page(_with_plan(page_admin), title="Admin", url_path="admin")
_signed = _account_identity()
_signed_email = _signed[0] if _signed is not None else ""
_NAV_PAGES[:] = [
    ("Home", st.Page(_with_plan(page_dashboard), title="Home", url_path="home")),
    ("Plan", st.Page(_with_plan(page_plan), title="Plan", url_path="plan")),
    ("Activity", st.Page(_with_plan(page_activity), title="Activity", url_path="activity")),
    ("Library", st.Page(_with_plan(page_library), title="Library", url_path="library")),
]
if viewer_is_admin(_signed_email):
    _NAV_PAGES.append(("Admin", _admin_page))
_NAV_PAGES.append(("More", st.Page(_with_plan(page_more), title="More", url_path="more")))
_MORE_PAGES[:] = [
    ("Past seasons", st.Page(_with_plan(page_past_seasons), title="Past seasons", url_path="past-seasons")),
    ("Profile", st.Page(_with_plan(page_profile), title="Profile", url_path="profile")),
    ("Settings", st.Page(_with_plan(page_settings), title="Settings", url_path="settings")),
    ("About", st.Page(_with_plan(page_about), title="About", url_path="about")),
    ("Creators", st.Page(_with_plan(page_creators), title="Creators", url_path="creators")),
]
_KEPT_PAGES[:] = [
    ("Last Session", st.Page(_with_plan(page_last_session), title="Last Session", url_path="last-session")),
    ("Next", st.Page(_with_plan(page_next), title="Next", url_path="next")),
    ("Decisions", st.Page(_with_plan(page_decisions), title="Decisions", url_path="decisions")),
    ("Ledger", st.Page(_with_plan(page_ledger), title="Ledger", url_path="ledger")),
    ("Goal", st.Page(_with_plan(page_goal), title="Goal", url_path="goal")),
]
if _account_identity() is None:
    _render_login()
    st.stop()
_routed = [
    _start_page,
    _session_page,
    *(page for _, page in _NAV_PAGES),
    *(page for _, page in _MORE_PAGES),
    *(page for _, page in _KEPT_PAGES),
]
if _admin_page not in _routed:
    _routed.append(_admin_page)
st.navigation(
    _routed,
    position="hidden",
).run()
