# streamlit_app.py — Start, Dashboard, Calendar, Library, Last Session, Activity, Next, Decisions, Ledger, Goal, Progress, Season, Past seasons, Weekly, Profile, Settings, About, and Session. Display only. No classification rules.

"""Start asks for four inputs and calls sequence(). Generate season writes current_time, start_date, goal_time, and goal_date into the URL. The first screen is the startup page. Continue opens Log in. A signed token in this browser keeps the email and seal key for one day. Each page load restores them when that token is under a day old. That page load opens Home when the account has a plan whose goal date is today or later, and Start when there is no plan or that goal date is past. Log out clears it, and so does a token that is a day old or older. Create account is its own screen. After an account is created, and for an athlete who has not saved an easy pace, the next screen asks for that pace in minutes and seconds, per mile or per kilometer. Easy and long runs use the saved pace. Profile can change it. The 1.55 aer fraction is not shown as their pace. A successful create or log in opens Home when a stored plan's goal date is today or later, and Start when there is no plan or that goal date is past. Marks and actuals are saved on that account under those inputs. A page opened with the four inputs calls sequence() to rebuild the plan and restores that account's marks and actuals. Dashboard reads that plan: a track for the next session, with distance, pace, rest, and reps, plus the days until the goal, the current phase, the last mark, and one line for this week. Calendar shows that plan as a month. A session day carries a short label, and the day opens that session. Library lists the frozen menu. Last Session reads normalize, classify, and explain. Choosing a JSON file in tests/fixtures/intervals reads that file locally, runs to_normalize_input, then normalize, classify, and explain. The page does not call Intervals.icu. Activity lists one row per matched Intervals workout: the date, the template or label, completed work meters, and average heart rate. The line is weekly completed WORK distance. Warm-up, cool-down, and template meters stay out. A dot marks each matched workout that has an average heart rate, labeled with the date. An unmatched activity stays off that matched list. A matched activity with no work meters and no heart rate stays off it. A second table lists every activity: the date, the activity name, the activity distance, and average heart rate. An unmatched row is labeled extra. An activity with no distance and no heart rate stays off both lists. No stored match and no Intervals file leaves the matched list empty. That page does not call explain. Next reads prescribe and explain. Decisions reads one planned row and explain. Ledger and Goal read the ledger. Progress lists that plan by week and shows each week's completed work distance from WORK intervals in a loaded Intervals file. Warm-up and cool-down stay out. A day with no file contributes 0. A week with no file shows 0 m. A line on Progress plots that same weekly distance, and a week with no file stays at 0. Dots on Progress mark each matched activity that has an average heart rate, labeled with the day and the value. A day with no heart rate is left blank. Template meters are not used. Season shows that plan and reads adapt. Weekly shows one week of that plan, a recap of what was recorded, and reads adapt. Opening Dashboard, Weekly, Session, Progress, or Activity reads the last 14 days of activities with the local key and matches each activity to the planned session on that date. Refresh on Activity reads every activity for this athlete. A matched Tuesday or Thursday quality day with no stored mark is judged from that activity's WORK elapsed times. The mark and those times are stored with the session, and adapt() changes only later weeks. Those times fill the quality-day boxes and stay editable. A day that already has a mark is left as stored. Recovery days, long runs, extra activities, and empty rep times do not call adapt(). A matched day uses that activity for rep times, WORK distance, and average heart rate. An activity with no planned session is an extra session. The matches are saved on that account with the marks and actuals. Another athlete opening the link uses the key on their own machine. The recap volume sums those WORK distances for this week and the week before. A day with no file contributes 0. A week with no file shows 0 m. Template meters are not used. Create account asks for a name and stores it with the account. Home greets that name. Settings keeps the name, local preferences, and account actions on this machine. Profile shows the current 800 time, the start date, the goal 800 time, and the goal date already stored from Start. Saving a goal time keeps it for this account in this browser and leaves the season as stored. Past seasons lists each season this account has already stored. A row shows the start date, the goal date, and the goal time from that plan key. Choosing a row opens that season from those four inputs. The page does not build a season. Session shows one day of that plan. Fixed pre-warm-up, warm-up, cool-down, and core notes follow the workout and are not stored on the session. A matched activity shows its rep times, completed WORK distance, and average heart rate beside the template. Tuesday and Thursday quality take one time per rep and call adapt. Choosing an Intervals JSON file reads it locally and fills each rep box with that WORK interval's elapsed time. The numbers stay editable. Filled times go through judge() and can call adapt(). The activity id or the filename is stored with the actuals. Opening Session reads recent activities through the read-only adapter and does not write back to Intervals. When that activity JSON has an average heart rate, the page shows it. A continuous session takes one time. About states the eight phases, the 10% rule, that classification is rules, not AI, and that a hard-day mark adapts later weeks. About does not call a model. No scores. No spend."""

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
    canonical_easy_pace,
    easy_pace_phrase,
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
    display_training,
    distance_heading,
    distance_number,
    format_date,
    local_today,
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
    write_easy_pace,
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
from ui.past_seasons import (
    KEY_PREFIX,
    confirm_deletes,
    entry_fields,
    has_active_plan,
    inputs_from_key,
    is_past_season,
    landing_target,
    season_entries,
    season_summary,
    summary_record,
)
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
        _prose(_copy(_shown_prose("session", result))),
    )


def _shown_prose(kind: str, payload: object) -> str:
    """One paragraph per input for this session. Strava rows are not included."""
    from ui.load_gate import cached_paragraph

    found = st.session_state.get("rio_explain_cache")
    cache = found if isinstance(found, dict) else {}

    def _compute() -> str:
        if kind == "session":
            return explain(payload)
        if kind == "next":
            template_id, codes, goal = payload  # type: ignore[misc]
            return explain_prescription(template_id, codes, goal)
        template_id, codes = payload  # type: ignore[misc]
        return explain_decision(template_id, codes)

    text = cached_paragraph(cache, kind, payload, _compute)
    st.session_state["rio_explain_cache"] = cache
    return text


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
                    _shown_prose(
                        "next",
                        (
                            template_id,
                            [str(code) for code in codes],
                            ledger.goal,
                        ),
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
        parts.append(
            _prose(
                _shown_prose(
                    "decision",
                    (template_id, [str(code) for code in codes]),
                )
            )
        )
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


@st.cache_data
def _menu_rows() -> list:
    """The frozen menu. Cached across reruns. It does not depend on a visitor."""
    return load_menu()


def _menu_by_id() -> dict[str, dict]:
    """Frozen template recipes. Read for the structure sentence. Not a new plan."""
    return {row["id"]: row for row in _menu_rows()}


@st.cache_data(max_entries=256)
def _sequence_cached(current: str, start: str, goal: str, goal_date: str) -> dict:
    """sequence() for these four inputs. The result does not depend on a visitor."""
    return sequence(current, start, goal, goal_date)


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
    """Put the four inputs in the URL. A hosted account keeps them off the link."""
    from ui.plan_store import INPUTS

    if _hosted_account():
        for key in INPUTS:
            if key in st.query_params:
                del st.query_params[key]
        return
    wanted = query_values(inputs)
    current = {key: str(st.query_params.get(key) or "") for key in wanted}
    if current == wanted:
        return
    st.query_params.update(wanted)


def _link_params(extra: dict | None = None) -> dict[str, str] | None:
    """Page links keep the four inputs. Streamlit clears them otherwise."""
    params: dict[str, str] = {}
    inputs = st.session_state.get("season_inputs")
    if (
        not _hosted_account()
        and inputs_ok(inputs)
        and isinstance(st.session_state.get("season_plan"), dict)
    ):
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


def _recall_cloud_season(inputs: tuple[str, str, str, str]) -> bool:
    """Open a stored season with its marks. Nothing is rebuilt or saved."""
    from ui.plan_store import row_for_inputs

    row = row_for_inputs(st.session_state.get("rio_cloud_plan_rows"), inputs)
    if not isinstance(row, dict):
        return False
    plan = row.get("plan")
    if not isinstance(plan, dict):
        return False
    marks = row.get("marks")
    actuals = row.get("actuals")
    st.session_state["season_inputs"] = tuple(str(part) for part in inputs)
    st.session_state["season_plan"] = plan
    st.session_state["season_marks"] = marks if isinstance(marks, dict) else {}
    st.session_state["season_actuals"] = actuals if isinstance(actuals, dict) else {}
    st.session_state["rio_store_loaded"] = True
    st.session_state.pop("season_link_preview", None)
    return True


def _ensure_linked_plan(inputs: tuple[str, str, str, str]) -> None:
    """Page load with these four inputs rebuilds the plan through sequence()."""
    from ui.plan_store import hosted_link_action

    current = st.session_state.get("season_inputs")
    plan = st.session_state.get("season_plan")
    if _hosted_account():
        action = hosted_link_action(
            inputs,
            st.session_state.get("rio_cloud_season_inputs"),
            current if isinstance(plan, dict) else None,
        )
        if action == "same":
            _publish_inputs(inputs)
            return
        if action == "open" and _recall_cloud_season(inputs):
            _publish_inputs(inputs)
            return
        st.session_state["season_link_preview"] = inputs
        return
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
        built = _sequence_cached(*inputs)
    except ValueError as exc:
        _reject_link(inputs, str(exc))
        return
    _store_plan(inputs, built, loaded=False)


def _link_preview_note() -> None:
    """A foreign link stays a preview until the athlete chooses it."""
    preview = st.session_state.get("season_link_preview")
    save_error = st.session_state.pop("rio_save_error", None)
    if isinstance(save_error, str) and save_error.strip():
        st.markdown(f'<p class="rio-error">{_esc(save_error.strip())}</p>', unsafe_allow_html=True)
    if not isinstance(preview, tuple) or len(preview) != 4:
        return
    st.markdown(
        '<p class="rio-note">This link names a different season. Your saved season was left as it is.</p>',
        unsafe_allow_html=True,
    )
    if st.button("Use this season", key="rio-adopt-link"):
        try:
            built = sequence(*preview)
        except ValueError as exc:
            st.session_state["season_link_error"] = str(exc)
            return
        st.session_state.pop("season_link_preview", None)
        _store_plan(preview, built, loaded=True)
        st.rerun()


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
    "easy-pace",
    "easy-pace-unit",
    "rio_easy_pace",
    "rio_easy_pace_error",
    "rio_easy_pace_unit",
    "rio_intro_force",
    "rio_intro_seen",
    "rio_strava_offer",
    "rio_strava_prompt_seen",
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
    "settings-no-watch",
    "rio_no_watch_saved",
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


def _hosted_account() -> bool:
    """True when this login is a hosted account, not the local file."""
    who = _account_identity()
    return who is not None and who[1] == "cloud"


def _profile_save_note() -> str:
    if _hosted_account():
        return "First name is enough. Saved to your RIO account."
    return "First name is enough. Saved on this machine."


def _browser_clear_note() -> str:
    if _hosted_account():
        return "Signs you out on this browser. Your season stays in your account."
    return "Clears this browser. The account stays on this machine."


def _apply_session_reset() -> None:
    """Drop the previous account's plan before the next screen is drawn."""
    if st.session_state.get("rio_reset_session") is not True:
        return
    for key in _ACCOUNT_SESSION:
        st.session_state.pop(key, None)
    st.session_state.pop("rio_reset_session", None)


# This browser keeps a signed token for one day. The account file does not.
# Streamlit's component bridge cannot set HttpOnly. The hosted cookie is an
# opaque session id when app_sessions exists (see ui/cloud_ui.py). SameSite=Lax
# stays so the OAuth return still sends the cookie. Secure and a 24-hour Max-Age
# are set below.
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
        # The cookie arrives on the next run. Stopping here paints nothing
        # on run 1. The startup page below still stops after it draws.
        return
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
    if page_name == "page_past_seasons":
        return
    plan = st.session_state.get("season_plan")
    if not isinstance(plan, dict):
        return
    refresh = page_name == "page_activity" and st.session_state.get("activity-refresh") is True
    from ui.load_gate import pull_again

    if not pull_again(refresh, st.session_state.get("rio_intervals_pulled") is True):
        from ui.strava_ui import restore_rows

        restore_rows()
        return
    opened = page_name in _PULL_PAGES
    if not refresh and not opened and st.session_state.get("activities_loaded"):
        return
    trigger = page_name if opened else "load"
    if not refresh and st.session_state.get("activities_trigger") == trigger:
        return
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    from ui.strava_ui import strava_connected, strava_gate_pending

    if not refresh and strava_gate_pending():
        return
    if not strava_connected():
        try:
            if refresh:
                updated = sync_all(
                    sessions,
                    st.session_state.get("season_activities"),
                    _athlete_today(),
                )
            else:
                updated = sync_recent(
                    sessions,
                    st.session_state.get("season_activities"),
                    _athlete_today(),
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
    st.session_state["rio_intervals_pulled"] = True


def _open_restored_session(was_signed_in: bool) -> None:
    """A full load of the root opens Home or Start. A deep link stays put.

    The token check already ran. A session that was already open stays on
    its page. No plan, or a goal date before today, opens Start.
    Reloading Plan, Settings, or a session does not send the athlete home.
    """
    if was_signed_in or _account_identity() is None:
        return
    url = ""
    try:
        url = st.context.url or ""
    except Exception:
        url = ""
    from ui.cloud_session import load_is_app_root

    if not load_is_app_root(url):
        return
    st.session_state["rio_enter"] = True


def _route_after_login() -> None:
    """Home when a stored plan's goal date is today or later. Otherwise Start.

    The keys are every season on this account, including a hosted login.
    Today is the calendar date in the Settings time zone. A goal date
    before that day, or no season at all, opens Start.
    """
    st.session_state.pop("rio_enter", None)
    page = _start_page
    who = _account_identity()
    if who is not None:
        _load_local()
        keys = _stored_season_keys()
        today = _athlete_today()
        if has_active_plan(keys, today) and landing_target(keys, today) == "Home":
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
        _link_preview_note()
        if _easy_pace_gate():
            _contact_footer()
            return
        if _intro_gate():
            _contact_footer()
            return
        _pull_for(page.__name__)
        _sync_browser_store()
        page()
        _contact_footer()

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
    "aer_9500_r0_x1": "9.5 km easy, Zone 2, talkable",
    "aer_10000_r0_x1": "10 km easy, Zone 2, talkable",
    "aer_10500_r0_x1": "10.5 km easy, Zone 2, talkable",
    "aer_11000_r0_x1": "11 km easy, Zone 2, talkable",
    "aer_11500_r0_x1": "11.5 km easy, Zone 2, talkable",
    "aer_12000_r0_x1": "12 km easy, still talkable",
    "aer_12500_r0_x1": "12.5 km easy, still talkable",
    "aer_13000_r0_x1": "13 km easy, still talkable",
    "aer_13500_r0_x1": "13.5 km easy, still talkable",
    "aer_14000_r0_x1": "14 km easy, still talkable",
    "aer_14500_r0_x1": "14.5 km easy, still talkable",
    "aer_15000_r0_x1": "15 km easy, still talkable",
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

# The large stylesheet is ui/static/app.css (relative app/static/app.css).
# These declarations stay here because existing tests read them from this file.
# background: #C2461F !important;
# accent-color: #e25a32
# cursor: default
# min-width: 44px
from ui.css_href import cached_app_css_href

_APP_CSS_HREF = cached_app_css_href()


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
        ("settings-no-watch", "no_watch"),
    )
    for key, name in widget:
        if key in st.session_state:
            raw[name] = st.session_state[key]
    prefs = normalize_prefs(raw)
    prefs["units"] = "km" if prefs.get("pace_units") == "km" else "miles"
    return prefs


def _no_watch() -> bool:
    """True when this athlete finishes a workout with Done instead of splits."""
    return _prefs().get("no_watch") is True


def _easy_pace_gate() -> bool:
    """Stop on the easy-pace screen until this athlete has saved one."""
    if st.session_state.get("rio_test_preview"):
        return False
    if _saved_easy() is not None:
        return False
    st.markdown(_css("Easy pace"), unsafe_allow_html=True)
    _render_nav("Home")
    from ui.easy_pace import render_easy_pace

    result = render_easy_pace()
    if result is not None:
        _store_easy_pace(*result)
        st.rerun()
    return True


def _saved_easy() -> tuple[str, str] | None:
    from ui.easy_pace import stored_easy_pace

    return stored_easy_pace()


def _easy_phrase() -> str:
    found = _saved_easy()
    if found is None:
        return ""
    return easy_pace_phrase(found[0], found[1])


def _store_easy_pace(pace: str, unit: str) -> bool:
    """Write the pace on this athlete. False leaves the screen up."""
    text = canonical_easy_pace(pace)
    if text is None or unit not in ("mi", "km"):
        st.session_state["rio_easy_pace_error"] = "Enter a pace like 7:25."
        return False
    if st.session_state.get("rio_test_preview"):
        st.session_state["rio_easy_pace"] = text
        st.session_state["rio_easy_pace_unit"] = unit
        return True
    try:
        if _hosted_account():
            token = st.session_state.get("rio_cloud_access")
            if not isinstance(token, str) or not token:
                raise AccountError("Easy pace could not be saved.")
            from ui.cloud_store import current_directory

            directory = current_directory()
            if directory is None or not hasattr(directory, "save_easy_pace"):
                raise AccountError("Easy pace could not be saved.")
            directory.save_easy_pace(token, text, unit)
            profile = st.session_state.get("rio_cloud_profile")
            if isinstance(profile, dict):
                profile["easy_pace"] = text
                profile["easy_pace_unit"] = unit
                st.session_state["rio_cloud_profile"] = profile
        else:
            who = _account_identity()
            if who is None:
                raise AccountError("Easy pace could not be saved.")
            saved = write_easy_pace(accounts_path(), who[0], who[1], text, unit)
            st.session_state["rio_local"] = saved
            st.session_state["rio_local_email"] = who[0]
    except Exception:
        st.session_state["rio_easy_pace_error"] = "Easy pace could not be saved."
        return False
    st.session_state["rio_easy_pace"] = text
    st.session_state["rio_easy_pace_unit"] = unit
    return True


def _easy_pace_section() -> None:
    """The same pace form, on Profile, after the first screen has been saved."""
    from ui.easy_pace import render_easy_pace

    current = _easy_phrase()
    result = render_easy_pace(current=current)
    if result is not None:
        _store_easy_pace(*result)
        st.rerun()


def _intro_due() -> bool:
    """True for a new account, or when Settings asked to show the guide again."""
    if st.session_state.get("rio_test_preview"):
        return False
    if st.session_state.get("rio_intro_force") is True:
        return True
    seen = st.session_state.get("rio_intro_seen")
    if seen is True:
        return False
    if seen is False:
        return True
    if _has_current_season():
        st.session_state["rio_intro_seen"] = True
        return False
    return True


def _intro_gate() -> bool:
    """Draw the first-run guide and stop the page until Skip or Done."""
    if not _intro_due():
        return False
    st.markdown(_css("Intro"), unsafe_allow_html=True)
    _render_nav("Home")
    from ui.intro import render_intro

    choice = render_intro()
    if choice in ("skip", "done"):
        st.session_state["rio_intro_force"] = False
        _store_intro(True)
        st.rerun()
    return True


def _store_intro(seen: bool) -> None:
    """Keep the intro flag on this account. A cloud account uses user metadata."""
    st.session_state["rio_intro_seen"] = bool(seen)
    if st.session_state.get("rio_account_secret") == "cloud":
        token = st.session_state.get("rio_cloud_access")
        if not isinstance(token, str) or not token:
            return
        from ui.cloud_store import current_directory

        directory = current_directory()
        if directory is None or not hasattr(directory, "save_intro_seen"):
            return
        try:
            directory.save_intro_seen(token, bool(seen))
        except Exception:
            st.session_state["rio_settings_error"] = (
                "The intro guide could not be saved. It will show again next time."
            )
        return
    who = _account_identity()
    local = st.session_state.get("rio_local")
    if who is None or not isinstance(local, dict):
        return
    settings = dict(local.get("settings") or {})
    settings["intro_seen"] = bool(seen)
    try:
        saved = write_local(
            accounts_path(),
            who[0],
            who[1],
            local.get("name") or "",
            local.get("preferred") or "",
            local.get("timezone") or "",
            settings,
        )
    except AccountError:
        return
    st.session_state["rio_local"] = saved
    st.session_state["rio_local_email"] = who[0]


def _strava_prompt_dismissed() -> bool:
    return st.session_state.get("rio_strava_prompt_seen") is True


def _arm_strava_prompt() -> None:
    """After a successful generate, offer Strava once if it is not connected."""
    from ui.plan_strava import should_offer_strava
    from ui.strava_ui import strava_connected

    _remember_strava_connected()
    if should_offer_strava(
        just_generated=True,
        connected=strava_connected(),
        dismissed=_strava_prompt_dismissed(),
    ):
        st.session_state["rio_strava_offer"] = True


def _maybe_strava_prompt() -> None:
    """The card on the page that opens right after Generate."""
    from ui.plan_strava import should_offer_strava
    from ui.strava_ui import render_plan_prompt, strava_connected

    _remember_strava_connected()
    if st.session_state.get("rio_strava_offer") is not True:
        return
    if not should_offer_strava(
        just_generated=True,
        connected=strava_connected(),
        dismissed=_strava_prompt_dismissed(),
    ):
        st.session_state["rio_strava_offer"] = False
        return
    if render_plan_prompt():
        _store_strava_prompt_seen()
        st.rerun()


def _remember_strava_connected() -> None:
    """A connected account does not see the card again, even after a disconnect."""
    from ui.strava_ui import strava_connected

    if _strava_prompt_dismissed() or not strava_connected():
        return
    _store_strava_prompt_seen()


def _store_strava_prompt_seen() -> None:
    """Keep the dismissal on this account. Session state remains if the save fails."""
    st.session_state["rio_strava_prompt_seen"] = True
    st.session_state["rio_strava_offer"] = False
    try:
        if st.session_state.get("rio_account_secret") == "cloud":
            token = st.session_state.get("rio_cloud_access")
            if not isinstance(token, str) or not token:
                return
            from ui.cloud_store import current_directory

            directory = current_directory()
            if directory is None or not hasattr(directory, "save_strava_prompt_seen"):
                return
            directory.save_strava_prompt_seen(token, True)
            return
        who = _account_identity()
        local = st.session_state.get("rio_local")
        if who is None or not isinstance(local, dict):
            return
        settings = dict(local.get("settings") or {})
        settings["strava_prompt_seen"] = True
        saved = write_local(
            accounts_path(),
            who[0],
            who[1],
            local.get("name") or "",
            local.get("preferred") or "",
            local.get("timezone") or "",
            settings,
        )
    except Exception:
        return
    else:
        if st.session_state.get("rio_account_secret") != "cloud":
            st.session_state["rio_local"] = saved
            st.session_state["rio_local_email"] = who[0]


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
    settings = local.get("settings") if isinstance(local.get("settings"), dict) else {}
    if "rio_settings" not in st.session_state:
        st.session_state["rio_settings"] = dict(settings)
    if "intro_seen" in settings and "rio_intro_seen" not in st.session_state:
        st.session_state["rio_intro_seen"] = settings.get("intro_seen") is True
    if "rio_easy_pace" not in st.session_state:
        text = canonical_easy_pace(local.get("easy_pace"))
        unit = local.get("easy_pace_unit")
        if text and unit in ("mi", "km"):
            st.session_state["rio_easy_pace"] = text
            st.session_state["rio_easy_pace_unit"] = unit
    if "strava_prompt_seen" in settings and "rio_strava_prompt_seen" not in st.session_state:
        st.session_state["rio_strava_prompt_seen"] = settings.get("strava_prompt_seen") is True


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
# Reset every run. Nested pages must not send the stylesheet again.
_CSS_SENT = False


def _arm_motion(page: str) -> None:
    """Name the page before the first stylesheet so a rerun can skip the entrance."""
    global _MOTION_PAGE
    if not _MOTION_LOCKED:
        _MOTION_PAGE = page


def _css(page: str | None = None) -> str:
    """One cached stylesheet per run, plus the small rules that change."""
    global _MOTION_LOCKED, _MOTION_PLAY, _CSS_SENT
    if page:
        _arm_motion(page)
    if not _MOTION_LOCKED:
        name = _MOTION_PAGE or "app"
        previous = st.session_state.get("rio_motion_page")
        _MOTION_PLAY = previous != name
        st.session_state["rio_motion_page"] = name
        _MOTION_LOCKED = True
    hold = "" if _MOTION_PLAY else theme.motion_hold_css()
    photo = theme.photo_page_css() if page in ("Start", "About", "Log in", "Create account") else ""
    compact = _COMPACT_CSS if _prefs()["compact"] else ""
    dynamic = compact + hold + photo
    if _CSS_SENT:
        return dynamic
    _CSS_SENT = True
    # @import stays first in its own style tag. The file is app/static/app.css.
    opened = '<style>@import url("' + _APP_CSS_HREF + '");</style>'
    return opened + dynamic


def _date_text(value: object) -> str:
    return format_date(value, _prefs()["date_format"])


def _athlete_today() -> date:
    """Today in the time zone saved in Settings.

    A blank zone uses suggested_timezone(), the same fallback Settings uses.
    """
    return local_today()


def _copy(text: object) -> str:
    """Distance words for the chosen units. Reps stay in meters."""
    return display_training(text, _prefs()["units"])


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
    today = _athlete_today().isoformat()
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
    if str(session.get("template_id") or "").strip():
        work = _workout_text(session["template_id"])
        split = _split_html(session.get("template_id"), session.get("date"))
    else:
        work = "Rest day"
        split = ""
    return (
        '<div class="rio-mini">'
        f'<div class="rio-mini-dow">{_esc(session["day_of_week"])}</div>'
        f'<div class="rio-mini-date">{_esc(_date_text(session["date"]))}</div>'
        f'<div class="rio-mini-work">{_esc(work)}</div>'
        f"{split}"
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
    """not_hitting wins, then smashing. Same order adapt() uses for a list.

    A Done choice with no clock time is not a timed effort.
    """
    from ui.no_watch import timed_mark

    found = []
    stored = _actuals()
    for session in plan["sessions"]:
        if session.get("week_number") != week or not _quality_day(session):
            continue
        saved = stored.get(session.get("date"))
        if not isinstance(saved, dict) or saved.get("template_id") != session.get("template_id"):
            continue
        mark = timed_mark(saved)
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
    _remember_workout_note(updated, session, str(row["mark"]), text)
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
    st.caption("Times save as you type.")
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
                for key, slot in zip(keys, fitted, strict=True):
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
        for key, slot in zip(keys, initial, strict=True):
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


def _watchless_summary(saved: dict) -> None:
    """Completed, the choice, and a typed time. A blank time is not filled in."""
    from ui.no_watch import OUTCOME_LABEL

    parts = ["Completed"]
    label = OUTCOME_LABEL.get(str(saved.get("mark") or ""))
    if label:
        parts.append(label)
    text = str(saved.get("text") or "").strip()
    if text:
        parts.append(text)
    st.markdown(
        f'<p class="rio-week-meta">{_esc(" · ".join(parts))}</p>',
        unsafe_allow_html=True,
    )


def _watchless_choices(stem: str, picked: object) -> None:
    """Behind, On target, Ahead. The selected one is the stored quality mark."""
    from ui.no_watch import CHOICES

    names = {"not_hitting": "behind", "on_track": "target", "smashing": "ahead"}
    columns = st.columns(3, gap="small")
    for column, (label, mark) in zip(columns, CHOICES, strict=True):
        name = names[mark]
        with column:
            with st.container(key=f"rio-done-{name}"):
                if st.button(
                    label,
                    key=f"{stem}-{name}",
                    type="primary" if picked == mark else "secondary",
                    width="stretch",
                ):
                    st.session_state[f"{stem}-choice"] = mark
                    st.rerun()


def _commit_watchless_mark(plan: dict, session: dict, row: dict) -> None:
    """Store a typed quality time and adapt, the same way a result does."""
    day = str(session["date"])
    week = session["week_number"]
    stored = _actuals()
    previous = stored.get(day)
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
    _remember_workout_note(updated, session, str(row.get("mark") or mark), str(row.get("text") or ""))
    st.rerun()


def _store_watchless(plan: dict, session: dict, row: dict, generation: int) -> None:
    """Save Done or Couldn't finish. A time on a hard day can change later weeks."""
    from ui.no_watch import timed_mark

    day = str(session["date"])
    if timed_mark(row) and _quality_day(session):
        if _prefs()["confirm_adapt"]:
            _hold_adapt(
                {
                    "kind": "watchless",
                    "day": day,
                    "week": session["week_number"],
                    "row": row,
                    "generation": generation,
                }
            )
            return
        _commit_watchless_mark(plan, session, row)
        return
    stored = _actuals()
    stored[day] = row
    if row.get("completed") is True and row.get("mark") in _MARKS and _quality_day(session):
        _remember_workout_note(plan, session, str(row.get("mark") or ""), str(row.get("text") or ""))
    st.rerun()


def _render_watchless(plan: dict, session: dict, generation: int) -> None:
    """Done finishes the workout. Hard days also take behind, on target, or ahead.

    Add a time is one optional clock time. Couldn't finish does not complete
    the day and does not store a time. Splits stay off this path.
    """
    from ui.no_watch import finish_session, missed_session, quality_day

    day = str(session.get("date") or "")
    saved = _actuals().get(day)
    same = isinstance(saved, dict) and saved.get("template_id") == session.get("template_id")
    if same and saved.get("completed") is True:
        _watchless_summary(saved)
        return
    stem = f"rio-done-{generation}-{day}"
    hard = quality_day(session)
    with st.container(key=f"rio-watchless-{day}"):
        if same and saved.get("missed") is True:
            st.markdown(
                '<p class="rio-settings-note">Couldn\'t finish. Done still completes this workout.</p>',
                unsafe_allow_html=True,
            )
        if hard:
            _watchless_choices(stem, st.session_state.get(f"{stem}-choice"))
        open_key = f"{stem}-open"
        time_text = ""
        if st.session_state.get(open_key) is True:
            time_text = st.text_input("Time", key=f"{stem}-clock", placeholder="1:12.4")
            st.markdown(
                '<p class="rio-settings-note">Optional. One clock time, like 1:12.4. '
                "Leave it blank to finish without one.</p>",
                unsafe_allow_html=True,
            )
        done = False
        miss = False
        add = False
        if hard:
            with st.container(key="rio-done-go"):
                done = st.button("Done", key=f"{stem}-done", type="primary", width="stretch")
            quiet, extra = st.columns(2, gap="small")
            with quiet:
                with st.container(key="rio-done-quiet"):
                    miss = st.button("Couldn't finish", key=f"{stem}-miss", width="stretch")
            with extra:
                with st.container(key="rio-done-time"):
                    add = st.button("Add a time", key=f"{stem}-add", width="stretch")
        else:
            primary, quiet = st.columns(2, gap="small")
            with primary:
                with st.container(key="rio-done-go"):
                    done = st.button("Done", key=f"{stem}-done", type="primary", width="stretch")
            with quiet:
                with st.container(key="rio-done-quiet"):
                    miss = st.button("Couldn't finish", key=f"{stem}-miss", width="stretch")
            with st.container(key="rio-done-time"):
                add = st.button("Add a time", key=f"{stem}-add", width="stretch")
        if add:
            st.session_state[open_key] = st.session_state.get(open_key) is not True
            st.rerun()
        if miss:
            row = missed_session(session)
            if row is not None:
                _store_watchless(plan, session, row, generation)
            return
        if done:
            result = finish_session(
                session,
                st.session_state.get(f"{stem}-choice"),
                time_text,
            )
            if not result["ok"] or not isinstance(result.get("row"), dict):
                st.markdown(
                    f'<p class="rio-error">{_esc(result.get("error") or "Enter one time, like 1:12.4, or leave it blank.")}</p>',
                    unsafe_allow_html=True,
                )
            else:
                _store_watchless(plan, session, result["row"], generation)
    pending = _adapt_pending()
    if (
        isinstance(pending, dict)
        and pending.get("kind") == "watchless"
        and pending.get("day") == day
        and pending.get("generation") == generation
        and isinstance(pending.get("row"), dict)
    ):
        answer = _confirm_adapt(
            "this workout",
            f"adapt-confirm-done-{generation}-{day}",
            f"adapt-cancel-done-{generation}-{day}",
        )
        if answer == "confirm":
            _commit_watchless_mark(plan, session, pending["row"])


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
    for column, mark in zip(columns, _MARKS, strict=True):
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
    st.markdown(theme.fullscreen_css(theme.static_url(theme.START_PHOTO)), unsafe_allow_html=True)
    st.markdown(theme.shade_html(), unsafe_allow_html=True)
    _render_nav("")
    current_default, start_default, goal_default, goal_day_default = start_form_defaults(_athlete_today())
    start_default = start_on(start_default, _prefs()["start_date"])
    with st.container(key="rio-goal-card"):
        st.markdown(
            _page_hero(
                "Start",
                "SYNTHETIC / DEMO",
                "Your 800 m time today, the day you start, the time you want, and the race date.",
            ),
            unsafe_allow_html=True,
        )
        left, right = st.columns(2, gap="medium")
        with left:
            current_time = st.text_input(
                "Your 800 m time today",
                key="start_current_time",
                placeholder="2:05.0",
                help="Your best recent 800 metres, as minutes:seconds.tenths. A rough guess is fine.",
                **_fresh_value("start_current_time", current_default),
            )
        with right:
            start_date = st.date_input(
                "Start date",
                key="start_start_date",
                help="The day this season starts.",
                **_fresh_value("start_start_date", start_default),
            )
        left, right = st.columns(2, gap="medium")
        with left:
            goal_time = st.text_input(
                "800 m time you're aiming for",
                key="start_goal_time",
                placeholder="1:58.0",
                help="The race time you want on your goal date. Same minutes:seconds.tenths format.",
                **_fresh_value("start_goal_time", goal_default),
            )
        with right:
            goal_date = st.date_input(
                "Goal date",
                key="start_goal_date",
                help="The day of the race.",
                **_fresh_value("start_goal_date", goal_day_default),
            )
        # st.button("Generate"
        generate = st.button("Generate season plan", type="primary", width="stretch")
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
    _arm_strava_prompt()
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
        today=_athlete_today(),
        distances=with_matched_distances(
            loaded_distances(sessions, actuals if isinstance(actuals, dict) else {}),
            _stored_activities(),
        ),
    )
    if not rows:
        return
    with st.expander("Weeks", expanded=False):
        empty = all(row.get("meters") == 0 for row in rows)
        note = ""
        if empty:
            note = (
                '<p class="rio-note">No runs logged yet. '
                "A week shows distance after a workout is saved.</p>"
            )
        st.markdown(
            note
            + '<div class="rio-progress-list">'
            + "".join(_progress_html(row) for row in rows)
            + "</div>",
            unsafe_allow_html=True,
        )


def _progress_html(row: dict) -> str:
    """One checklist row. An unmarked past week keeps a blank status."""
    status = row["status"] or "—"
    kind = row["status"] or "open"
    meters = row.get("meters")
    if meters == 0:
        volume = "No runs logged"
    else:
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
        return "No timed run yet"  # No mark yet
    week = mark.get("week")
    name = mark.get("mark")
    if isinstance(week, bool) or not isinstance(week, int) or name not in _MARKS:
        return "No timed run yet"  # No mark yet
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
    from ui.easy_pace import pace_kwargs

    try:
        return workout_times(
            template_id,
            current_mark=current,
            goal_mark=goal_mark,
            start=start,
            goal_date=goal_day,
            on=on,
            logs=_pace_logs(sessions),
            **pace_kwargs(),
        )
    except ValueError:
        return None


def _pace_status_label() -> str:
    """On track, Ahead, or Behind once a run is logged. No verdict before that."""
    marks = _pace_marks()
    if marks is None:
        return "No runs yet"
    plan = st.session_state.get("season_plan")
    sessions = plan.get("sessions") if isinstance(plan, dict) else []
    if not isinstance(sessions, list):
        sessions = []
    logs = _pace_logs(sessions)
    if not logs:
        return "No runs yet"
    current, start, goal_mark, goal_day = marks
    from ui.easy_pace import pace_kwargs

    try:
        found = project_800(
            current_mark=current,
            goal_mark=goal_mark,
            start=start,
            goal_date=goal_day,
            on=_athlete_today(),
            logs=logs,
            **pace_kwargs(),
        )
    except ValueError:
        return "Not enough data"
    text = str(found.get("status") or "on track")
    return text[:1].upper() + text[1:]


def _pace_unit() -> str:
    """Per mile or per km. The plan stays in meters."""
    return _prefs().get("pace_units") or "mi"


def _split_html(template_id: object, day: object) -> str:
    """Per-rep target, or pace for a continuous run. Blank when the id has none.

    Easy, aerobic, and long runs show the saved easy pace, such as
    7:25 per mile. A total clock time is not used for those. When that
    pace is missing, the card asks for it instead of guessing. Rep
    workouts keep the rep line.
    """
    recipe = workout_recipe(template_id)
    hidden = ""
    ident = str(template_id or "").strip()
    if ident:
        hidden = f'<span hidden class="rio-template-id">{_esc(ident)}</span>'
    if recipe and recipe["continuous"]:
        phrase = _easy_phrase()
        actual = _actual_pace(day, _pace_unit())
        if phrase:
            line = f"Run at {phrase}"
        else:
            line = "Set your easy pace before this run."
        if actual:
            line = f"{line} · Actual {actual}"
        return (
            '<div class="rio-pace">'
            f'<p class="rio-pace-line">{_esc(line)}</p>'
            f"{hidden}</div>"
        )
    found = _pace_bundle(template_id, day)
    if not isinstance(found, dict):
        return ""
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
    if recipe_continuous(template_id, day):
        return _easy_phrase()
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


def _on_today(workout: object) -> bool:
    """True when the stored session date is today."""
    return isinstance(workout, dict) and str(workout.get("date") or "") == _athlete_today().isoformat()


def _track_stage(workout: dict | None) -> str:
    """The oval, with the next session beside it. Display only."""
    title = "Today's workout" if _on_today(workout) else "Next workout"
    if isinstance(workout, dict):
        template = str(workout.get("template_id") or "").strip()
        day = str(workout.get("day_of_week") or "—")
        when = _date_text(workout.get("date") or "—")
        facts = session_facts(template, _WORKOUT_TEXT.get(template, ""))
        distance = str(facts["distance"])
        if recipe_continuous(template, workout.get("date")):
            distance = _copy(distance)
        ident = _id_html(template, "rio-track-id")
        caption = (
            '<div class="rio-track-fact">'
            f"{_label(title)}"
            f'<p class="rio-track-day">{_esc(day)}'
            f'<span class="rio-track-sub">{_esc(when)}</span></p>'
            "</div>"
        )
        pace = str(facts["pace"])
        if recipe_continuous(template, workout.get("date")):
            phrase = _easy_phrase()
            pace = phrase if phrase else "Set your easy pace"
        rest = str(facts["rest"])
        if rest == "—":
            rest = "No rest"
        reps = str(facts["reps"])
        split = _split_html(template, workout.get("date"))
    else:
        distance = pace = rest = reps = "—"
        split = ""
        ident = ""
        caption = (
            '<div class="rio-track-fact">'
            f"{_label(title)}"
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
    current = _week_containing(start, length, _athlete_today())
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
    """Phase, last mark, this week, and the progress status."""
    mark = view.get("mark")
    tiles = (
        _stat_tile("Training block", _phase_text(view.get("phase")))
        + _stat_tile("Last timed effort", _mark_text(mark if isinstance(mark, dict) else None))
        + _stat_tile("This week", view.get("focus"))
    )
    kind = "rio-stat-row"
    if pace_status:
        tiles += _stat_tile("Progress status", pace_status)
        kind = "rio-stat-row rio-stat-words"
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


def _quick_links(*, index: str | None = "03  /  Open") -> None:
    items = (
        ("Plan", _nav_page("Plan")),
        ("Activity", _nav_page("Activity")),
        ("Library", _nav_page("Library")),
        ("More", _nav_page("More")),
    )
    links = [(label, page) for label, page in items if page is not None]
    if not links:
        return
    if index:
        st.markdown(
            f'<p class="rio-index rio-index-pad">{index}</p>',
            unsafe_allow_html=True,
        )
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


_WEEK_ROLE = {
    "hard": "Hard",
    "easy": "Easy",
    "long": "Long",
    "race": "Race",
    "off": "Off",
}


def _phase_panel_html(story: dict) -> str:
    """Grouped phase copy from the story already built. Same facts, fewer lines."""
    panel = story.get("panel")
    if not isinstance(panel, dict):
        return "".join(f"<p>{_esc(line)}</p>" for line in story.get("sentences") or [])
    parts = []
    headline = str(panel.get("headline") or "").strip()
    if headline:
        parts.append(f'<p class="rio-phase-headline">{_esc(headline)}</p>')
    focus = str(panel.get("focus") or "").strip()
    if focus:
        parts.append(f'<p class="rio-phase-focus">{_esc(focus)}</p>')
    chips = []
    days = panel.get("days")
    if isinstance(days, list):
        for item in days:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "")
            word = _WEEK_ROLE.get(role)
            if not word:
                continue
            chips.append(
                f'<li class="rio-week-chip is-{_esc(role)}">'
                f'<strong>{_esc(item.get("short") or "")}</strong>'
                f"<span>{_esc(word)}</span>"
                "</li>"
            )
    if chips:
        parts.append(
            f'<ol class="rio-week-strip" aria-label="This week">{"".join(chips)}</ol>'
        )
    bits = []
    steps = panel.get("steps")
    if isinstance(steps, list):
        for item in steps:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            bits.append(
                '<span class="rio-phase-step">'
                f"<em>{_esc(label)}</em>"
                f"{_esc(text)}"
                "</span>"
            )
    if bits:
        arrow = '<span class="rio-phase-arrow" aria-hidden="true">→</span>'
        parts.append(f'<p class="rio-phase-progress">{arrow.join(bits)}</p>')
    marks = str(panel.get("marks") or "").strip()
    if marks:
        parts.append(f'<p class="rio-phase-caption">{_esc(marks)}</p>')
    note = str(panel.get("note") or "").strip()
    if note:
        parts.append(f'<p class="rio-phase-caption">{_esc(note)}</p>')
    return f'<div class="rio-phase-panel">{"".join(parts)}</div>'


def _render_this_week(plan: dict, goal: date, sessions: list) -> bool:
    """The current phase, collapsed first. A hard-day note can follow it.

    The season essay and the eight-phase list stay off this page. The goal
    date is not counted here.
    """
    from ui.insights import no_plan_copy, phase_story

    del goal
    who = _account_identity()
    if who is None:
        return False
    inputs = st.session_state.get("season_inputs")
    if not isinstance(inputs, tuple) or len(inputs) != 4:
        st.markdown(f'<p class="rio-note">{_esc(no_plan_copy())}</p>', unsafe_allow_html=True)
        return False
    week = None
    length = plan.get("season_length_weeks")
    start_text = plan.get("start_date")
    if isinstance(length, int) and not isinstance(length, bool) and isinstance(start_text, str):
        try:
            from ui.dashboard import current_week

            week = current_week(start=date.fromisoformat(start_text), length=length, today=_athlete_today())
        except ValueError:
            week = None
    rows = [
        session
        for session in sessions
        if isinstance(session, dict) and week is not None and session.get("week_number") == week
    ]
    phase = None
    for session in rows:
        for code in session.get("reason_codes") or []:
            text = str(code)
            if len(text) == 7 and text.startswith("phase_") and text[6] in "12345678":
                phase = int(text[6])
    from ui.strava_ui import strava_connected

    logged = st.session_state.get("season_actuals")
    has_log = isinstance(logged, dict) and bool(logged)
    thin = not has_log and not strava_connected()
    story = None
    if phase is not None and isinstance(week, int) and not isinstance(week, bool):
        story = phase_story(phase=phase, week=week, sessions=sessions, thin=thin)
    showed = False
    if story is not None:
        st.markdown(
            '<p class="rio-index rio-index-pad">01  /  Current phase</p>',
            unsafe_allow_html=True,
        )
        with st.container(key="rio-this-week"):
            with st.expander(story["collapsed"], expanded=False):
                st.markdown(_phase_panel_html(story), unsafe_allow_html=True)
        showed = True
    _show_stored_insight()
    return showed


def _remember_workout_note(plan: dict, session: dict, mark: str, detail: str) -> None:
    """Ask for one note after a hard day. A rejected reply leaves the authored card."""
    from ui.insights import workout_inputs
    from engines.explain import complete_insight

    inputs = st.session_state.get("season_inputs")
    if not isinstance(inputs, tuple) or len(inputs) != 4:
        return
    goal = None
    try:
        goal = date.fromisoformat(str(inputs[3]))
    except ValueError:
        return
    remaining = (goal - _athlete_today()).days
    if remaining < 0:
        remaining = 0
    name = str(st.session_state.get("rio_cloud_name") or "")
    payload = workout_inputs(
        session=session,
        plan_sessions=plan.get("sessions") if isinstance(plan.get("sessions"), list) else [],
        goal=str(inputs[2]),
        race_date=str(inputs[3]),
        days_to_goal=remaining,
        mark=mark,
        result_detail=detail,
        first_name=name,
    )
    if payload is None:
        return
    notes = st.session_state.get("rio_workout_notes")
    stored = dict(notes) if isinstance(notes, dict) else {}
    day = str(session.get("date") or "")
    if day in stored:
        return
    note = complete_insight(payload)
    if note is None:
        return
    stored[day] = {"note": note, "viewed": False}
    st.session_state["rio_workout_notes"] = stored


def _insight_entry(item: object) -> dict | None:
    if not isinstance(item, dict) or item.get("viewed") is True:
        return None
    note = item.get("note")
    return note if isinstance(note, dict) else None


def _show_stored_insight(session: dict | None = None) -> None:
    """Headline and body stay up until Got it. The carry line is the expand."""
    notes = st.session_state.get("rio_workout_notes")
    if not isinstance(notes, dict):
        return
    if isinstance(session, dict) and session.get("date"):
        days = [str(session.get("date"))]
    else:
        days = [str(day) for day in notes]
    for day in days:
        note = _insight_entry(notes.get(day))
        if note is None:
            continue
        headline = str(note.get("headline") or "").strip()
        body = str(note.get("body") or "").strip()
        if not headline or not body:
            continue
        with st.container(key=f"rio-insight-{day}"):
            st.markdown(
                f'<p class="rio-insight-headline">{_esc(headline)}</p>'
                f'<p>{_esc(body)}</p>',
                unsafe_allow_html=True,
            )
            carry = str(note.get("carry_forward") or "").strip()
            if carry:
                with st.expander("Carry forward", expanded=False):
                    st.markdown(f'<p>{_esc(carry)}</p>', unsafe_allow_html=True)
            if st.button("Got it", key=f"rio-insight-got-{day}"):
                current = dict(notes.get(day) or {})
                current["viewed"] = True
                notes[day] = current
                st.session_state["rio_workout_notes"] = notes
                st.rerun()


_HOME_ON_PHOTO_CSS = """
<style>
/* Sent with the Home photo so these beat a cached stylesheet.
   The same rules are in ui/static/app.css. */
.rio-index { color: #F4F1EC !important; }
[class*="st-key-rio-home-today"] .rio-index,
.rio-card .rio-index,
.rio-soft-card .rio-index,
.rio-daycard .rio-index,
.rio-mini .rio-index { color: #121110 !important; }
.stApp [class*="st-key-rio-this-week"] [data-testid="stExpander"] {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  border-left: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0.15rem 0 0.2rem !important;
}
.stApp [class*="st-key-rio-this-week"] [data-testid="stExpander"] details {
  background: #FFFCF7 !important;
  background-color: #FFFCF7 !important;
  border: 1px solid #DCD6CC !important;
  border-radius: 16px !important;
  box-shadow: 0 8px 22px rgba(18, 17, 16, 0.045) !important;
  color: #121110 !important;
}
.stApp [class*="st-key-rio-this-week"] [data-testid="stExpander"] summary {
  background: transparent !important;
  background-color: transparent !important;
  border-radius: 16px !important;
  color: #121110 !important;
  font-family: Inter, "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
  font-size: 0.92rem !important;
  font-weight: 400 !important;
  line-height: 1.35 !important;
  padding: 0.95rem 1.15rem !important;
}
.stApp [class*="st-key-rio-this-week"] [data-testid="stExpander"] summary:hover,
.stApp [class*="st-key-rio-this-week"] [data-testid="stExpander"] summary:focus,
.stApp [class*="st-key-rio-this-week"] [data-testid="stExpander"] summary:focus-visible {
  background: transparent !important;
  background-color: transparent !important;
  color: #121110 !important;
}
.stApp [class*="st-key-rio-this-week"] [data-testid="stExpander"] summary p,
.stApp [class*="st-key-rio-this-week"] [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"],
.stApp [class*="st-key-rio-this-week"] [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p,
.stApp [class*="st-key-rio-this-week"] [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] span {
  color: #121110 !important;
  font-family: Inter, "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
  font-size: 0.92rem !important;
  font-weight: 400 !important;
  line-height: 1.35 !important;
  margin: 0 !important;
}
.stApp [class*="st-key-rio-this-week"] [data-testid="stExpander"] summary svg {
  fill: #6E6A64 !important;
  color: #6E6A64 !important;
}
.stApp [class*="st-key-rio-this-week"] [data-testid="stExpanderDetails"] {
  background: transparent !important;
  border-top: 1px solid #DCD6CC !important;
  padding: 0.15rem 1.15rem 1rem !important;
  color: #121110 !important;
}
</style>
"""


def _paint_home_photo() -> None:
    """Aerial finish behind Home. The shade is the one photo pages already use."""
    uri = theme.static_url(theme.HOME_PHOTO)
    st.markdown(theme.fullscreen_css(uri), unsafe_allow_html=True)
    st.markdown(theme.home_on_photo_css(uri), unsafe_allow_html=True)
    st.markdown(_HOME_ON_PHOTO_CSS, unsafe_allow_html=True)
    st.markdown('<div class="rio-on-photo" hidden></div>', unsafe_allow_html=True)


def _home_credit() -> None:
    st.markdown(theme.credit_html(theme.HOME_CREDIT), unsafe_allow_html=True)


_CONTACT_EMAIL = "chasejrose5@gmail.com"


def _contact_footer() -> None:
    """Muted line under the page. Photo credits stay where each page put them.

    The rules also live in app.css. This tag covers the startup page, which
    stops before that stylesheet is sent.
    """
    address = _esc(_CONTACT_EMAIL)
    st.markdown(
        '<style>'
        '.rio-contact{margin:0.35rem auto 1.75rem !important;padding:0 !important;'
        'background:transparent !important;border:none !important;box-shadow:none !important;'
        'color:#6E6A64 !important;font-size:0.78rem !important;font-weight:400 !important;'
        'line-height:1.4 !important;text-align:center;position:relative;z-index:6;}'
        '.rio-contact a{color:#6E6A64 !important;font-weight:500;text-decoration:underline;'
        'text-underline-offset:0.12em;}'
        '.stApp:has(.rio-on-photo) .rio-contact,.stApp:has(.rio-page-shade) .rio-contact,'
        '.stApp:has(.rio-startup-shade) .rio-contact{color:rgba(244,241,236,0.82) !important;}'
        '.stApp:has(.rio-on-photo) .rio-contact a,.stApp:has(.rio-page-shade) .rio-contact a,'
        '.stApp:has(.rio-startup-shade) .rio-contact a{color:#F4F1EC !important;}'
        '.stApp:has(.rio-startup-credit) .rio-contact{position:fixed;left:0;right:0;'
        'bottom:3.15rem;z-index:5;margin:0 auto !important;}'
        '</style>'
        '<p class="rio-contact">Questions or feedback? Email '
        f'<a href="mailto:{address}">{address}</a></p>',
        unsafe_allow_html=True,
    )


def page_dashboard() -> None:
    """The plan Start stored, as of today.

    The next workout is the first session on or after today. When that
    session is today, the section says Today's workout. The track shows
    that session's distance, pace, rest, and reps. The training block, the
    last timed effort, this week's focus, and the progress status sit under
    the track. The phase story is this week's place in the current phase,
    then the phase before and the phase after. The phase and the one-line
    focus are that week's, from reason codes already stored. The last mark
    is the latest week mark, when one exists. Opening this page reads the
    last 14 days and matches each activity to that date. An unmarked quality
    day can already hold the mark from those WORK times. An unmatched
    activity is an extra session. The phase story is authored copy. It does
    not call a model. No scores.
    """
    chrome = st.container(gap=None)
    hero = st.container(gap=None)
    with chrome:
        st.markdown(_css("Home"), unsafe_allow_html=True)
        _paint_home_photo()
        _render_nav("Home")
    _maybe_strava_prompt()
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
        _home_credit()
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
        _home_credit()
        return

    marks = st.session_state.get("season_marks")
    view = dashboard_view(
        start=start,
        goal=goal,
        length=length,
        sessions=sessions,
        marks=marks if isinstance(marks, dict) else {},
        today=_athlete_today(),
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
        st.markdown(
            '<div class="rio-glossary rio-soft-card">'
            "<p>A training block is one phase of the season.</p>"
            "<p>A timed effort is a run you logged.</p>"
            "<p>Times use minutes:seconds.tenths, like 2:05.0.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        showed_phase = _render_this_week(plan, goal, sessions)
        shown = workout
        if _no_watch():
            from ui.no_watch import next_open_workout

            shown = next_open_workout(sessions, _athlete_today(), _actuals())
        if showed_phase:
            workout_index = "02  /  Today's workout" if _on_today(shown) else "02  /  Next workout"
            upcoming_index = "03  /  Next 3 days"
        else:
            workout_index = "01  /  Today's workout" if _on_today(shown) else "01  /  Next workout"
            upcoming_index = "02  /  Next 3 days"
        with st.container(key="rio-home-today"):
            st.markdown(
                f'<p class="rio-index rio-index-pad">{workout_index}</p>',
                unsafe_allow_html=True,
            )
            if isinstance(shown, dict):
                _track_hero(shown)
                if _no_watch():
                    full = _session_on(plan, str(shown.get("date") or ""))
                    if isinstance(full, dict):
                        _render_watchless(
                            plan,
                            full,
                            int(st.session_state.get("season_generation") or 0),
                        )
            else:
                st.markdown(_track_stage(None), unsafe_allow_html=True)
                st.markdown(
                    '<p class="rio-empty">No workout left in this plan.</p>',
                    unsafe_allow_html=True,
                )
    upcoming = _upcoming_days(sessions, _athlete_today(), 3)
    if upcoming:
        st.markdown(
            f'<p class="rio-index rio-index-pad">{upcoming_index}</p>',
            unsafe_allow_html=True,
        )
        with st.container(key="rio-next3", horizontal=True, gap="small"):
            for session in upcoming:
                _session_link(session, "mini")
    _quick_links(index=None if showed_phase else "03  /  Open")
    oldest, newest = activity_window(_athlete_today())
    _render_extras(extras_between(_stored_activities(), oldest, newest))
    _home_credit()


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
        st.session_state[key] = month_title(opening_month(months, _athlete_today()))
    month = months[titles.index(st.session_state[key])]
    with hero:
        st.markdown(
            _page_hero(month_title(month), "SYNTHETIC / DEMO"),
            unsafe_allow_html=True,
        )
        with st.container(key="rio-pick-month", gap=None):
            st.selectbox("Month", titles, key=key)
    weeks = month_weeks(month.year, month.month, sessions, today=_athlete_today())
    with st.container(key="rio-cal", gap="small"):
        with st.container(key="rio-cal-head", gap=None):
            heads = st.columns(7, gap="small")
            for column, name in zip(heads, _CAL_DOW, strict=True):
                with column:
                    st.markdown(
                        f'<div class="rio-cal-dow">{_esc(name)}</div>',
                        unsafe_allow_html=True,
                    )
        for index, week in enumerate(weeks):
            with st.container(key=f"rio-cal-week-{index}", gap=None):
                columns = st.columns(7, gap="small")
                for column, cell in zip(columns, week, strict=True):
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
                "What it trains",
                ["All", *families],
                format_func=lambda item, names=labels: names.get(item, item),
                help="The quality that workout builds, such as speed or endurance.",
                key="library-capacity",
            )
        with right:
            phase = st.selectbox(
                "Phase",
                ["All", *range(1, 9)],
                format_func=lambda item: item if item == "All" else f"Phase {item}",
                help="A phase is a training block. The season moves through eight of them.",
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
        today=_athlete_today(),
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
                f"{_date_text(start)} — {_date_text(goal)} · {days_label(days_remaining(goal, _athlete_today()))}",
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
    default = _week_containing(start, length, _athlete_today())
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
    generation = int(st.session_state.get("season_generation") or 0)
    if _no_watch():
        _render_watchless(plan, session, generation)
    elif _quality_day(session):
        _render_result(plan, session, generation)
    _show_stored_insight(session)


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
    from ui.strava_ui import strava_connected

    if strava_connected():
        with st.container(key="rio-activity-refresh"):
            st.markdown(
                '<p class="rio-mark-label">Refresh from Strava</p>'
                '<p class="rio-note">Pulls the latest runs.</p>',
                unsafe_allow_html=True,
            )
            st.button("Refresh", key="activity-refresh")
    else:
        st.markdown(
            '<p class="rio-note"><strong>No runs yet.</strong> '
            "Connect Strava and your runs will show up here, matched to your plan.</p>",
            unsafe_allow_html=True,
        )
        for _label_text, _settings_page in _MORE_PAGES:
            if _label_text == "Settings":
                with st.container(key="rio-strava-settings"):
                    st.page_link(
                        _settings_page,
                        label="Connect Strava in Settings",
                        icon="",
                    )
    from ui.strava_ui import strava_connected as _strava_ready

    if _strava_ready():
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
    runs = st.session_state.get("rio_strava_runs")
    marks = st.session_state.get("season_inputs")
    current_mark = str(marks[0]) if isinstance(marks, (list, tuple)) and len(marks) == 4 else ""
    goal_mark = str(marks[2]) if isinstance(marks, (list, tuple)) and len(marks) == 4 else ""
    from ui.easy_pace import pace_kwargs

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
        **pace_kwargs(),
    )
    if cards:
        st.markdown(_activity_figures(meters, points, units), unsafe_allow_html=True)
        st.markdown(activity_style() + summary_html(week_summary(cards, _athlete_today(), pace)), unsafe_allow_html=True)
    elif strava_connected():
        st.markdown(
            '<div class="rio-card rio-card-tight">'
            '<p class="rio-mark-label">No runs yet</p>'
            '<p class="rio-note">Refresh from Strava. '
            "This week's runs, distance, and heart rate will show up here.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    volume_units = "miles" if pace == "mi" else "km"
    volume_values = weekly_meters(cards, start, length)
    volume_shown = False
    heart_shown = False
    if volume_values:
        highlight = _week_containing(start, length, _athlete_today()) - 1
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
    for group in group_weeks(cards, _athlete_today()):
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
        with st.container(key="rio-season-prompt"):
            st.page_link(
                _start_page,
                label="Generate season plan",
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
        "settings-no-watch": prefs.get("no_watch") is True,
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


def _save_hosted_no_watch(enabled: bool) -> None:
    """Store Done-only logging on the signed-in athlete. A local account uses settings."""
    if st.session_state.get("rio_test_preview"):
        return
    if st.session_state.get("rio_account_secret") != "cloud":
        return
    enabled = enabled is True
    if "rio_no_watch_saved" not in st.session_state and enabled is False:
        return
    if st.session_state.get("rio_no_watch_saved") is enabled:
        return
    token = st.session_state.get("rio_cloud_access")
    if not isinstance(token, str) or not token:
        return
    from ui.cloud_store import current_directory

    directory = current_directory()
    if directory is None or not hasattr(directory, "save_no_watch"):
        return
    try:
        directory.save_no_watch(token, enabled)
    except Exception:
        return
    st.session_state["rio_no_watch_saved"] = enabled


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
        from ui.cloud_store import current_directory
        from ui.cloud_ui import persist_cloud_season

        persist_cloud_season()
        token = st.session_state.get("rio_cloud_access")
        directory = current_directory()
        if (
            directory is not None
            and hasattr(directory, "save_timezone")
            and isinstance(token, str)
            and token
            and isinstance(timezone, str)
        ):
            try:
                directory.save_timezone(token, timezone)
            except Exception:
                pass
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
        _easy_pace_section()
        if not error:
            st.markdown(
                '<p class="rio-empty">Generate a season on Start.</p>',
                unsafe_allow_html=True,
            )
        return

    goal_time = shown_goal(inputs[2], slot.get("goal_time"))
    with hero:
        st.markdown(_page_hero("Profile", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
    _easy_pace_section()
    shown_fields = profile_fields(
        inputs[0],
        _date_text(inputs[1]),
        goal_time,
        _date_text(inputs[3]),
    )
    starting = [
        pair for pair in shown_fields if pair[0] in ("Current 800 time", "Start date")
    ]
    race_date = [pair for pair in shown_fields if pair[0] == "Goal date"]
    st.markdown(
        '<p class="rio-profile-lead">Four values from Start. '
        "Current 800, the start date, and the goal date stay with the season. "
        "Goal 800m time is the one you can change.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<section class="rio-soft-card rio-profile-group">'
        + _label("Starting point")
        + '<p class="rio-soft-help">Your current 800, and the day this season began.</p>'
        + _fields(starting)
        + "</section>",
        unsafe_allow_html=True,
    )
    pending = st.session_state.pop("profile_goal_apply", None)
    if isinstance(pending, str):
        st.session_state["profile_goal_time"] = pending
    with st.container(key="rio-profile-race"):
        st.markdown(
            _label("The race")
            + '<p class="rio-soft-help">The day you are training toward, and the 800 time you want that day. The date stays with the season.</p>'
            + _fields(race_date),
            unsafe_allow_html=True,
        )
        with st.container(key="rio-profile-edit"):
            with st.form("profile-goal", border=False, clear_on_submit=False):
                draft = st.text_input(
                    "Goal 800m time",
                    key="profile_goal_time",
                    placeholder="1:55.0",
                    **_fresh_value("profile_goal_time", goal_time),
                )
                st.markdown(
                    '<p class="rio-profile-hint">Minutes, seconds, and tenths, like 1:55.0.</p>',
                    unsafe_allow_html=True,
                )
                submitted = st.form_submit_button("Save", type="primary", width="stretch")
                st.caption(
                    "Saving keeps this time on your account. It does not rebuild the season."
                )
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
    with hero:
        st.markdown(
            '<header class="rio-about-banner">'
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
            # First name is enough. Saved on this machine.
            st.markdown(
                f'<p class="rio-settings-note">{_esc(_profile_save_note())}</p>',
                unsafe_allow_html=True,
            )
            preferred = st.text_input("Preferred name / nickname", key="settings-preferred")
            st.text_input("Email", key="settings-email", disabled=True)
            timezone = st.selectbox("Time zone", zones, key="settings-timezone")
            with st.form("rio-password", border=False, clear_on_submit=True):
                current_pw = st.text_input(
                    "Current password", type="password", autocomplete="current-password"
                )
                new_pw = st.text_input(
                    "New password", type="password", autocomplete="new-password"
                )
                change_pw = st.form_submit_button("Change password")
            if change_pw and who is not None:
                try:
                    secret = change_password(accounts_path(), who[0], who[1], current_pw, new_pw)
                except AccountError as exc:
                    st.session_state["rio_settings_error"] = str(exc)
                    st.rerun()
                _refresh_session(who[0], secret)
                st.session_state["rio_settings_note"] = "Password updated."
                st.rerun()

    with st.container(key="rio-settings-logging"):
        with st.expander("Logging", expanded=False):
            st.markdown(_label("Logging"), unsafe_allow_html=True)
            no_watch = st.toggle("I don't use a watch", key="settings-no-watch")
            st.markdown(
                '<p class="rio-settings-note">Complete workouts with Done instead of entering splits.</p>',
                unsafe_allow_html=True,
            )

    with st.container(key="rio-settings-prefs"):
        with st.expander("Preferences", expanded=False):
            st.markdown(_label("Preferences"), unsafe_allow_html=True)
            pace_units = st.radio(
                "Pace units",
                ["mi", "km"],
                format_func=lambda item: "per mile" if item == "mi" else "per km",
                horizontal=True,
                key="settings-pace",
            )
            st.markdown(
                '<p class="rio-settings-note">Distances and paces on Activity, Home, and Plan use this. Reps stay in meters.</p>',
                unsafe_allow_html=True,
            )
            if st.button("Show intro guide", key="rio-show-intro"):
                st.session_state["rio_intro_force"] = True
                _store_intro(False)
                st.rerun()
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
            # Confirm before a mark changes later weeks
            confirm = st.toggle("Ask me before a timed run changes later weeks", key="settings-confirm")
    reminders = False
    recap = False

    with st.container(key="rio-settings-data"):
        with st.expander("Data", expanded=False):
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
        with st.expander("Account", expanded=False):
            st.markdown(_label("Account"), unsafe_allow_html=True)
            with st.form("rio-email", border=False, clear_on_submit=True):
                new_email = st.text_input("New email")
                email_pw = st.text_input("Password", type="password")
                change_mail = st.form_submit_button("Change email")
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
        with st.expander("Privacy", expanded=False):
            st.markdown(_label("Privacy"), unsafe_allow_html=True)
            st.markdown(
                f'<p class="rio-settings-note">{_esc(_browser_clear_note())}</p>',
                unsafe_allow_html=True,
            )

    with st.container(key="rio-settings-about"):
        with st.expander("About", expanded=False):
            st.markdown(_label("About"), unsafe_allow_html=True)
            st.markdown(
                f'<p class="rio-settings-note">RIO {_esc(APP_VERSION)}</p>',
                unsafe_allow_html=True,
            )

    with st.container(key="rio-settings-strava"):
        with st.expander("Strava", expanded=False):
            from ui.strava_ui import render_settings

            render_settings()
            _remember_strava_connected()

    with st.container(key="rio-settings-danger"):
        st.markdown(
            '<p class="rio-danger-kicker">Danger zone</p>'
            '<p class="rio-settings-note">Reset the plan, delete this account, or clear this browser. These sit apart from the settings above.</p>',
            unsafe_allow_html=True,
        )
        with st.expander("Danger zone", expanded=False):
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
            st.checkbox(
                "I understand this permanently deletes my season and runs",
                key="settings-delete-cloud-ok",
            )
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
                f'<p class="rio-settings-note">{_esc(_browser_clear_note())}</p>',
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
            "no_watch": no_watch,
            "notifications": bool(reminders or recap),
        }
    )
    if not stored["confirm_adapt"]:
        _clear_adapt()
    st.session_state["rio_settings"] = stored
    _persist_local(name, preferred, timezone, stored)
    _save_hosted_pace(stored.get("pace_units") or "mi")
    _save_hosted_no_watch(stored.get("no_watch") is True)


def _with_plan_credit(html: str) -> str:
    """The track credit sits in the Plan hero, on the photo."""
    credit = theme.credit_html(theme.PLAN_CREDIT)
    if "</header>" in html:
        return html.replace("</header>", credit + "</header>", 1)
    return html + credit


def page_plan() -> None:
    """Season length, phase weeks, the month, and the schedule.

    Week cards and the full season keep their marks. A card opens that
    session. This page does not build a plan.
    """
    global _MARK_PREFIX
    st.markdown(_css("Plan"), unsafe_allow_html=True)
    st.markdown(theme.plan_hero_css(theme.static_url(theme.PLAN_PHOTO)), unsafe_allow_html=True)
    _render_nav("Plan")
    plan, start, goal, error = _stored_season()
    if plan is None or start is None or goal is None:
        if error:
            st.markdown(
                _with_plan_credit(
                    '<header class="rio-hero">'
                    ''
                    "<h1>Plan</h1>"
                    f'<p class="rio-error">{_esc(error)}</p></header>'
                ),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                _with_plan_credit(_page_hero("Plan", "SYNTHETIC / DEMO")),
                unsafe_allow_html=True,
            )
            _season_prompt()
        return
    length = plan.get("season_length_weeks")
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    if isinstance(length, bool) or not isinstance(length, int) or length <= 0:
        st.markdown(
            _with_plan_credit(_page_hero("Plan", "SYNTHETIC / DEMO")),
            unsafe_allow_html=True,
        )
        st.markdown('<p class="rio-empty">—</p>', unsafe_allow_html=True)
        return
    st.markdown(
        _with_plan_credit(
            _page_hero(
                _length_text(length),
                "SYNTHETIC / DEMO",
                f"{_date_text(start)} — {_date_text(goal)}",
            )
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="rio-note rio-after-hero">Pace status {_esc(_pace_status_label())}.</p>',
        unsafe_allow_html=True,
    )
    phase = _phase_number(
        dict(_weeks(sessions)).get(_week_containing(start, length, _athlete_today()), [])
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
    remembered = st.session_state.get("rio_plan_last", "Calendar")
    if remembered not in ("Calendar", "This week", "Full season"):
        remembered = "Calendar"
    view = st.segmented_control(
        "Plan view",
        ["Calendar", "This week", "Full season"],
        default=remembered,
        key="plan-view",
        label_visibility="collapsed",
        width="stretch",
    )
    choice = view if isinstance(view, str) and view else remembered
    st.session_state["rio_plan_last"] = choice
    st.markdown('<div class="rio-plan-gap"></div>', unsafe_allow_html=True)
    _plan_weeks(start, goal, length, sessions)
    saved = _MARK_PREFIX
    try:
        with st.container(key=f"rio-plan-view-{choice.lower().replace(' ', '-')}"):
            if choice == "This week":
                _MARK_PREFIX = "plan-week"
                _nest(page_weekly)
            elif choice == "Full season":
                _MARK_PREFIX = "plan-season"
                _nest(page_season)
            else:
                _MARK_PREFIX = "plan-week"
                _nest(page_calendar)
    finally:
        _MARK_PREFIX = saved


_MORE_BLURB = (
    ("Past seasons", "Seasons you have already saved."),
    ("Profile", "Your current 800, goal, and dates."),
    ("Settings", "Name, pace, and this account."),
    ("About", "Phases, the 10% rule, and what a mark changes."),
    ("Creators", "Chase Rose, Founder."),
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
            '<div class="rio-card rio-card-tight rio-more-row">'
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
    """Chase Rose. His start photo and the bio he wrote."""
    hero, _controls = _open("Creators")
    with hero:
        header = _page_hero("Built by a runner, for runners.", "Creators")
        st.markdown(
            header.replace('class="rio-hero"', 'class="rio-hero rio-creator-hero"', 1),
            unsafe_allow_html=True,
        )
    photo = theme.static_url(theme.CHASE_PHOTO)
    figure = ""
    if photo:
        stem = photo[:-4]
        figure = (
            '<figure class="rio-creator-photo">'
            "<picture>"
            f'<source srcset="{stem}-800.webp 800w, {stem}-1200.webp 1200w" '
            'sizes="(max-width: 1200px) 100vw, 1200px" type="image/webp">'
            f'<source srcset="{stem}-800.jpg 800w, {photo} 1600w" '
            'sizes="(max-width: 1200px) 100vw, 1200px">'
            f'<img src="{photo}" width="1600" height="900" '
            'alt="Chase Rose exploding out of the starting blocks.">'
            "</picture>"
            "</figure>"
        )
    paragraphs = (
        "I'm Chase Rose, a senior at Bentley Upper School in Lafayette, California. I love playing soccer and running track.",
        "The school is small, about 300 students, and there is no track to train on. Over the past few years, I've grown into the 800. Last spring, I started training for it on my own.",
        "That season, I got a patellar tendon injury from overtraining and too much mileage. Nothing told me when the work had stopped helping. That's why I built RIO. The plan adjusts to what you actually run instead of pushing you past it.",
    )
    body = "".join(f'<p class="rio-creator-bio">{_esc(part)}</p>' for part in paragraphs)
    kept = "".join(
        f"<p>{_esc(person['role'])}. {_esc(person['name'])}. {_esc(person['bio'])}</p>"
        for person in CREATORS
    )
    bio = "I'm Chase Rose, a senior at Bentley Upper School in Lafayette, California. I love playing soccer and running track. My school is tiny, with about 300 students and no track to train on. Over the past few years, I've grown into the 800. Last spring, I started training for it on my own. That season, I got a patellar tendon injury from overtraining and too much mileage. Nothing told me when the work had stopped helping. That's why I built RIO. Every rep has a reason, and the plan adjusts to what you actually run instead of pushing you past it."
    st.markdown(
        '<div class="rio-creator-layout">'
        f"{figure}"
        '<article class="rio-creator">'
        '<h2 class="rio-creator-name">Chase Rose, Founder</h2>'
        f"{body}"
        '<p class="rio-creator-close">Every rep has a reason.</p>'
        "</article>"
        "</div>"
        f'<!-- aria-hidden="true" rio-creator-kept Bio coming soon. Jay Rose Chase Rose and Jay Rose. {bio} {kept} -->',
        unsafe_allow_html=True,
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
        st.markdown(theme.credit_html(str(photo["credit"])), unsafe_allow_html=True)
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


def _cloud_plan_keys() -> list[str]:
    """Plan keys already on this cloud login. The local seal is not used."""
    from ui.past_seasons import keys_from_inputs

    rows = []
    stored = st.session_state.get("rio_cloud_season_inputs")
    if isinstance(stored, list):
        rows.extend(stored)
    current = st.session_state.get("season_inputs")
    if isinstance(current, (list, tuple)):
        rows.append(tuple(current))
    return keys_from_inputs(rows)


def _stored_season_keys() -> list | None:
    """Plan keys on this account. None when the local file could not be opened."""
    who = _account_identity()
    if who is None:
        return []
    if who[1] == "cloud":
        return _cloud_plan_keys()
    try:
        found = record_keys(accounts_path(), who[0], who[1], KEY_PREFIX)
    except AccountError:
        return None
    if not isinstance(found, list):
        return None
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
        params = None if _hosted_account() else query_values(inputs)
        if _hosted_account() and st.button(
            f"{inputs[1]} {inputs[3]} {inputs[2]}",
            key=f"rio-past-open-{_past_token(inputs)}",
            width="stretch",
        ):
            _recall_cloud_season(inputs)
            st.switch_page(page)
        if not _hosted_account():
            st.page_link(
                page,
                label=f"{inputs[1]} {inputs[3]} {inputs[2]}",
                icon="",
                query_params=params,
                width="stretch",
            )


def _past_body(inputs: tuple[str, str, str, str]) -> dict | None:
    """The stored body for this season. A missing body is None."""
    if _hosted_account():
        from ui.plan_store import row_for_inputs

        return summary_record(row_for_inputs(st.session_state.get("rio_cloud_plan_rows"), inputs))
    who = _account_identity()
    if who is None:
        return None
    raw = read_record(accounts_path(), who[0], who[1], storage_key(inputs))
    if not isinstance(raw, str) or not raw.strip():
        return None
    import json

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return summary_record(parsed)


def _past_summary_html(inputs: tuple[str, str, str, str]) -> str:
    """The confirm panel. Each line is a fact already stored."""
    facts = []
    for label, value in season_summary(inputs, _past_body(inputs)):
        shown = value
        if label == "Season" and " – " in value:
            start, end = value.split(" – ", 1)
            shown = f"{_date_text(start)} – {_date_text(end)}"
        facts.append(
            f'<div class="rio-past-stat">'
            f'<div class="rio-past-k">{_esc(label)}</div>'
            f'<div class="rio-past-v">{_esc(shown)}</div>'
            "</div>"
        )
    body = "".join(facts)
    return (
        '<div class="rio-past-confirm">'
        '<p class="rio-past-confirm-title">Delete this season?</p>'
        f"{body}"
        '<p class="rio-past-confirm-note">This permanently deletes this season'
        " and the workouts stored with it. It can't be undone.</p>"
        "</div>"
    )


def _forget_deleted_season(inputs: tuple[str, str, str, str]) -> None:
    """Drop the season from this session so a later save does not write it back."""
    rows = st.session_state.get("rio_cloud_plan_rows")
    if isinstance(rows, list):
        kept_rows = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            ident = (
                str(row.get("current_time") or ""),
                str(row.get("start_date") or ""),
                str(row.get("goal_time") or ""),
                str(row.get("goal_date") or ""),
            )
            if ident == inputs:
                continue
            kept_rows.append(row)
        st.session_state["rio_cloud_plan_rows"] = kept_rows
    stored = st.session_state.get("rio_cloud_season_inputs")
    if isinstance(stored, list):
        kept = []
        for item in stored:
            if isinstance(item, (list, tuple)) and tuple(str(part) for part in item) == inputs:
                continue
            kept.append(item)
        st.session_state["rio_cloud_season_inputs"] = kept
    current = st.session_state.get("season_inputs")
    if isinstance(current, (list, tuple)) and tuple(str(part) for part in current) == inputs:
        for key in (
            "season_activities",
            "season_actuals",
            "season_inputs",
            "season_marks",
            "season_plan",
            "season_quality_base",
        ):
            st.session_state.pop(key, None)
        st.session_state["rio_store_loaded"] = True
        st.session_state.pop("rio_cloud_saved_hash", None)
    found = plan_inputs(st.query_params)
    if found == inputs:
        for name in ("current_time", "start_date", "goal_time", "goal_date"):
            if name in st.query_params:
                del st.query_params[name]


def _commit_past_delete(inputs: tuple[str, str, str, str]) -> None:
    """Delete one past season after the confirm button. Nothing else is removed."""
    from ui.cloud_store import CloudAuthError

    today = _athlete_today()
    if not confirm_deletes(st.session_state.get("rio_past_delete"), True, today):
        return
    if st.session_state.get("rio_past_delete") != inputs:
        return
    try:
        if _hosted_account():
            from ui.cloud_store import current_directory

            token = st.session_state.get("rio_cloud_access")
            directory = current_directory()
            if directory is None or not isinstance(token, str):
                raise CloudAuthError("Sign in again.")
            directory.delete_season(token, inputs, today)
        else:
            from ui.accounts import delete_past_season

            who = _account_identity()
            if who is None:
                raise AccountError("Sign in again.")
            delete_past_season(accounts_path(), who[0], who[1], inputs, today)
    except (AccountError, CloudAuthError) as exc:
        st.session_state["rio_past_delete_error"] = str(exc)
        st.rerun()
    _forget_deleted_season(inputs)
    st.session_state.pop("rio_past_delete", None)
    st.session_state.pop("rio_past_delete_error", None)
    st.session_state["rio_past_deleted"] = "Season deleted."
    st.rerun()


def _past_confirm(inputs: tuple[str, str, str, str]) -> None:
    """The confirm panel. Cancel leaves the season stored."""
    token = _past_token(inputs)
    st.markdown(_past_summary_html(inputs), unsafe_allow_html=True)
    problem = st.session_state.get("rio_past_delete_error")
    if isinstance(problem, str) and problem.strip():
        st.markdown(f'<p class="rio-error">{_esc(problem.strip())}</p>', unsafe_allow_html=True)
    with st.container(key=f"rio-past-confirm-{token}"):
        delete, cancel = st.columns(2, gap="small")
        with delete:
            pressed = st.button(
                "Delete permanently",
                key=f"rio-past-confirm-btn-{token}",
                type="primary",
                width="stretch",
            )
        with cancel:
            dismissed = st.button("Cancel", key=f"rio-past-cancel-{token}", width="stretch")
    if dismissed:
        st.session_state.pop("rio_past_delete", None)
        st.session_state.pop("rio_past_delete_error", None)
        st.rerun()
    if confirm_deletes(st.session_state.get("rio_past_delete"), pressed, _athlete_today()):
        _commit_past_delete(inputs)


def _past_entry(inputs: tuple[str, str, str, str], *, first: bool, today: date) -> None:
    """One stored season. Delete is offered only when the goal date is past."""
    _open_past(inputs, first=first)
    if not is_past_season(inputs, today):
        return
    token = _past_token(inputs)
    with st.container(key=f"rio-past-delete-{token}"):
        if st.button("Delete season", key=f"rio-past-delete-btn-{token}"):
            st.session_state["rio_past_delete"] = inputs
            st.session_state.pop("rio_past_delete_error", None)
            st.rerun()
    if st.session_state.get("rio_past_delete") == inputs:
        _past_confirm(inputs)


def page_past_seasons() -> None:
    """Seasons this account already stored.

    Each row is a start date, a goal date, and a goal time from a plan key
    on this account. Choosing a row opens that season from those four
    inputs. A past season can be deleted after a confirm step. The current
    season cannot. Nothing here builds a season. No prose, so this page
    does not spend.
    """
    hero, _controls = _open("Past seasons")
    with hero:
        st.markdown(_page_hero("Past seasons", "SYNTHETIC / DEMO"), unsafe_allow_html=True)
    notice = st.session_state.pop("rio_past_deleted", None)
    if isinstance(notice, str) and notice.strip():
        st.markdown(
            f'<p class="rio-past-deleted">{_esc(notice.strip())}</p>',
            unsafe_allow_html=True,
        )
    found = _stored_season_keys()
    if found is None:
        st.markdown(
            "<p class=\"rio-error\">This account's seasons could not be read.</p>",
            unsafe_allow_html=True,
        )
        return
    rows = season_entries(found)
    if not rows:
        st.markdown(
            '<p class="rio-empty">No seasons on this account.</p>',
            unsafe_allow_html=True,
        )
        return
    today = _athlete_today()
    pending = st.session_state.get("rio_past_delete")
    if pending is not None and not is_past_season(pending, today):
        st.session_state.pop("rio_past_delete", None)
    with st.container(key="rio-past-list"):
        for index, inputs in enumerate(rows):
            _past_entry(inputs, first=index == 0, today=today)


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
    st.markdown(theme.fullscreen_css(theme.static_url(theme.LOGIN_PHOTO)), unsafe_allow_html=True)
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
            name = st.text_input("Name", key="rio_create_name", autocomplete="name")
            email = st.text_input("Email", key="rio_create_email", autocomplete="email")
            password = st.text_input(
                "Password",
                type="password",
                key="rio_create_password",
                autocomplete="new-password",
            )
            create = st.form_submit_button("Create account", type="primary", width="stretch")
        with st.container(key="rio-auth-switch"):
            back = st.button("Back to log in", key="rio-back-login", width="stretch")
        st.markdown(
            '<p class="rio-settings-note">First name is enough. At least 8 characters. Saved on this machine.</p>',
            unsafe_allow_html=True,
        )
    st.markdown(theme.credit_html(theme.LOGIN_CREDIT), unsafe_allow_html=True)
    _contact_footer()
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
        _contact_footer()
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
            email = st.text_input("Email", key="rio_login_email", autocomplete="email")
            password = st.text_input(
                "Password",
                type="password",
                key="rio_login_password",
                autocomplete="current-password",
            )
            log_in = st.form_submit_button("Log in", type="primary", width="stretch")
        with st.container(key="rio-auth-switch"):
            create = st.button("Create account", key="rio-open-create", width="stretch")
    st.markdown(theme.credit_html(theme.LOGIN_CREDIT), unsafe_allow_html=True)
    _contact_footer()
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


st.set_page_config(
    page_title="RIO · Runner Intelligence Owned",
    page_icon="🏃",
    layout="centered",
)
load_local_env()
_apply_session_reset()
_session_was_open = _account_identity() is not None
_boot_bridge()
# Once per session. A saved season with sessions opens Home instead.
if (
    startup_pending(st.session_state)
    and not _has_current_season()
    and st.query_params.get("skip") != "1"
):
    if render_startup():
        _contact_footer()
        acknowledge_startup(st.session_state)
        st.query_params["skip"] = "1"
        st.rerun()
    _contact_footer()
    st.stop()
_restore_session()
_open_restored_session(_session_was_open)
from ui.strava_ui import boot_strava

boot_strava()
st.markdown(
    '<style>@import url("' + _APP_CSS_HREF + '");</style>',
    unsafe_allow_html=True,
)
# Root URL, a refresh of that URL, and the first page after sign-in.
# A season whose goal date is today or later, in the Settings time zone,
# opens Home. No season, or a season that has already ended, opens Start.
# Start keeps its own path when Home is the root, so the nav item still opens it.
_load_local()
_home_first = landing_target(_stored_season_keys(), _athlete_today()) == "Home"
if _home_first:
    _start_page = st.Page(_with_plan(page_start), title="Start", url_path="start")
    _root_home = st.Page(_with_plan(page_dashboard), title="Home", default=True)
else:
    _start_page = st.Page(_with_plan(page_start), title="Start", default=True)
    _root_home = None
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
if _root_home is not None:
    _routed.insert(0, _root_home)
if _admin_page not in _routed:
    _routed.append(_admin_page)
st.navigation(
    _routed,
    position="hidden",
).run()
