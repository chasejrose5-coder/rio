# test_landing.py — a current season opens Home. No current season opens Start.

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.past_seasons import has_active_plan, landing_target
from ui.plan_store import storage_key
from ui.settings import local_today

# Monday 9 Nov 2026, 03:30 UTC is still Sunday 8 Nov in Pacific time.
_MONDAY_MORNING_UTC = datetime(2026, 11, 9, 3, 30, tzinfo=timezone.utc)
_TODAY = date(2026, 11, 9)
_IN_PROGRESS = ("2:05.0", "2026-11-05", "1:56.0", "2027-07-08")
_ENDS_TODAY = ("2:05.0", "2026-06-01", "1:56.0", "2026-11-09")
_ENDED = ("2:10.0", "2025-11-01", "2:00.0", "2026-11-08")


def _function(source: str, name: str) -> str:
    start = source.index(f"def {name}(")
    rest = source[start + 1 :]
    nxt = rest.find("\ndef ")
    if nxt < 0:
        return source[start:]
    return source[start : start + 1 + nxt]


def test_a_season_in_progress_lands_on_home() -> None:
    """A goal date of today or later is Home. The zone decides which day today is."""
    keys = [storage_key(_IN_PROGRESS)]
    if landing_target(keys, _TODAY) != "Home":
        raise AssertionError("a season running through 2027 opened Start")
    if not has_active_plan(keys, _TODAY):
        raise AssertionError("the landing rule left the active-plan check")
    if landing_target([storage_key(_ENDS_TODAY)], _TODAY) != "Home":
        raise AssertionError("a goal date of today was treated as finished")
    pacific = local_today("America/Los_Angeles", _MONDAY_MORNING_UTC)
    utc = local_today("UTC", _MONDAY_MORNING_UTC)
    if pacific != date(2026, 11, 8) or utc != date(2026, 11, 9):
        raise AssertionError((pacific, utc))
    boundary = [storage_key(_ENDED)]
    if landing_target(boundary, pacific) != "Home":
        raise AssertionError("Pacific Sunday dropped a season that still ends that day")
    if landing_target(boundary, utc) != "Start":
        raise AssertionError("UTC Monday kept a season that ended on Sunday")


def test_no_current_season_lands_on_start() -> None:
    """No stored season opens Start."""
    if landing_target([], _TODAY) != "Start":
        raise AssertionError("an empty account opened Home")
    if landing_target(None, _TODAY) != "Start":
        raise AssertionError("a missing account opened Home")
    if landing_target("", _TODAY) != "Start":
        raise AssertionError("a bad key list opened Home")
    if landing_target([storage_key(_IN_PROGRESS)], "2026-11-09") != "Start":
        raise AssertionError("a non-date today opened Home")


def test_an_ended_season_lands_on_start() -> None:
    """The only season, already finished, opens Start. A later season still opens Home."""
    ended = [storage_key(_ENDED)]
    if landing_target(ended, _TODAY) != "Start":
        raise AssertionError("a finished season opened Home")
    if has_active_plan(ended, _TODAY):
        raise AssertionError("a finished goal date was still active")
    both = [storage_key(_ENDED), storage_key(_IN_PROGRESS)]
    if landing_target(both, _TODAY) != "Home":
        raise AssertionError("a current season was ignored because an older one had ended")


class _Page:
    def __init__(self, _body, *, title, url_path=None, default=False):
        self.title = title
        self.url_path = url_path
        self.default = default


def _root_pages(boot: str, home_first: bool) -> tuple[_Page, _Page | None, _Page]:
    """Run the root assignment. The wordmark is the first page."""
    start = boot.index("if _home_first:")
    end = boot.index("\n_SESSION_PAGE", start)
    snippet = boot[start:end]
    space = {
        "_home_first": home_first,
        "_with_plan": lambda page: page,
        "page_start": "page_start",
        "page_dashboard": "page_dashboard",
        "page_session": "page_session",
        "st": type("Streamlit", (), {"Page": _Page}),
    }
    exec(snippet, space)
    wordmark = space["_HOME_PAGE"]
    root = space["_root_home"]
    start_page = space["_start_page"]
    if not isinstance(wordmark, _Page) or not isinstance(start_page, _Page):
        raise AssertionError("the wordmark is not a page")
    if root is not None and not isinstance(root, _Page):
        raise AssertionError("the root is not a page")
    return wordmark, root, start_page


def test_the_wordmark_opens_the_root() -> None:
    """RIO opens Home when a season is current, and Start when it is not.

    /start, Past seasons, and reset still open Start.
    """
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    boot = app[app.index("\nst.set_page_config(") :]
    nav = _function(app, "_render_nav")
    brand = nav[nav.index('key="rio-brand"') : nav.index('key="rio-links"')]
    if "home = _HOME_PAGE" not in nav or "st.page_link(\n                home," not in brand:
        raise AssertionError("RIO does not open the wordmark page")
    if 'label="RIO"' not in brand:
        raise AssertionError("the wordmark is not RIO")
    current_flag = landing_target([storage_key(_IN_PROGRESS)], _TODAY) == "Home"
    today_flag = landing_target([storage_key(_ENDS_TODAY)], _TODAY) == "Home"
    if not current_flag or not today_flag:
        raise AssertionError("a current season was not Home")
    for flag in (current_flag, today_flag):
        wordmark, root, start = _root_pages(boot, flag)
        if wordmark is not root or wordmark.title != "Home" or wordmark.default is not True:
            raise AssertionError("a current season sends the wordmark to Start")
        if wordmark.url_path is not None:
            raise AssertionError("the wordmark left the root")
        if start.title != "Start" or start.url_path != "start":
            raise AssertionError("Start cannot be opened on purpose once Home is the root")
    for keys in ([], [storage_key(_ENDED)], None):
        flag = landing_target(keys, _TODAY) == "Home"
        if flag:
            raise AssertionError("no season or an ended season was not Start")
        wordmark, root, start = _root_pages(boot, flag)
        if root is not None or wordmark is not start or wordmark.title != "Start":
            raise AssertionError("no season or an ended season sends the wordmark to Home")
        if wordmark.default is not True:
            raise AssertionError("Start is not the root when no season is current")
    if 'url_path="past-seasons"' not in app:
        raise AssertionError("Past seasons was removed")
    if "st.switch_page(_start_page)" not in _function(app, "_reset_saved_plan"):
        raise AssertionError("reset no longer opens Start")
    if 'label="Generate season plan"' not in app or "_start_page," not in app:
        raise AssertionError("Start was removed from the app")


def test_sign_in_and_the_root_url_use_that_rule() -> None:
    """Hosted and local seasons share one check. Deep links and Start stay put."""
    app = (ROOT / "ui" / "streamlit_app.py").read_text(encoding="utf-8")
    past = (ROOT / "ui" / "past_seasons.py").read_text(encoding="utf-8")
    rule = _function(past, "landing_target")
    if "has_active_plan(" not in rule or "Home" not in rule or "Start" not in rule:
        raise AssertionError("landing left the existing season rule")
    route = _function(app, "_route_after_login")
    for token in (
        "_stored_season_keys()",
        "has_active_plan(",
        "landing_target(",
        "_athlete_today()",
        '_nav_page("Home")',
        "_start_page",
        "st.switch_page(",
        "_load_local()",
    ):
        if token not in route:
            raise AssertionError(token)
    if "_has_current_season()" in route or "record_keys(" in route:
        raise AssertionError("sign-in still ignores a hosted goal date or uses sessions alone")
    for token in (
        "sequence(",
        "write_record(",
        "_store_plan(",
        "_ensure_linked_plan(",
        "_restore_last_plan(",
        "read_record(",
    ):
        if token in route:
            raise AssertionError(token)
    boot = app[app.index("\nst.set_page_config(") :]
    if "_home_first = landing_target(_stored_season_keys(), _athlete_today())" not in boot:
        raise AssertionError("the root URL does not use the landing rule")
    if boot.index("_load_local()") > boot.index("_home_first"):
        raise AssertionError("today is chosen before the Settings zone is loaded")
    if 'title="Start", default=True' not in boot or 'title="Home", default=True' not in boot:
        raise AssertionError("Home and Start are not the two root pages")
    if 'title="Start", url_path="start"' not in boot:
        raise AssertionError("Start cannot be opened on purpose once Home is the root")
    for path in ("home", "plan", "settings", "past-seasons", "about"):
        if f'url_path="{path}"' not in app:
            raise AssertionError(path)
    if "_reset_saved_plan" not in app or "st.switch_page(_start_page)" not in app:
        raise AssertionError("reset no longer opens Start")
    if 'label="Generate season plan"' not in app or "_start_page," not in app:
        raise AssertionError("Start was removed from the app")
    opened = _function(app, "_open_restored_session")
    if "load_is_app_root(" not in opened or "has_active_plan(" in opened:
        raise AssertionError("a deep link is sent home before its page is chosen")


def main() -> None:
    test_a_season_in_progress_lands_on_home()
    test_no_current_season_lands_on_start()
    test_an_ended_season_lands_on_start()
    test_the_wordmark_opens_the_root()
    test_sign_in_and_the_root_url_use_that_rule()
    print("landing ok")


if __name__ == "__main__":
    main()
