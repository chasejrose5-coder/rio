# activity_pull.py — decide which activities to read, then judge a quality day.

"""The pull behind Dashboard, Plan, Weekly, Session, Progress, and Activity.

A test-season preview does not pull. Past seasons does not pull. Refresh
on Activity reads every activity. Opening one of the live pages reads the
last 14 days. Any other first page is the app load: it reads that same
window and does not judge a mark. When Strava is connected the Intervals
sync is skipped. Strava rows are restored either way.

The network calls, the Strava restore, and the session writes are passed
in. This module does not import the UI shell.
"""

from __future__ import annotations

from ui.activities import PullError
from ui.load_gate import pull_again

# The names are the page functions the shell wraps. Keep this tuple in
# step with `_PULL_PAGES` in the shell. A test locks the two.
PULL_PAGES = (
    "page_dashboard",
    "page_plan",
    "page_weekly",
    "page_session",
    "page_progress",
    "page_activity",
)


def run_activity_pull(
    *,
    page_name: str,
    test_preview: bool,
    refresh: bool,
    already_pulled: bool,
    activities_loaded: object,
    activities_trigger: object,
    plan: object,
    activities,
    today,
    strava_connected,
    strava_gate_pending,
    sync_all,
    sync_recent,
    restore_rows,
    on_notice,
    clear_notice,
    on_activities,
    _apply_activity_marks,
    on_loaded,
    pull_pages: tuple[str, ...] = PULL_PAGES,
) -> None:
    """Match activities for this page and judge an unmarked quality day.

    `activities` and `today` are callables so they are read at the sync,
    not before the early returns. `strava_connected` is a callable for the
    same reason: looking up the token writes session flags.
    """
    if test_preview:
        return
    if page_name == "page_past_seasons":
        return
    if not isinstance(plan, dict):
        return
    if not pull_again(refresh, already_pulled):
        restore_rows()
        return
    opened = page_name in pull_pages
    if not refresh and not opened and activities_loaded:
        return
    trigger = page_name if opened else "load"
    if not refresh and activities_trigger == trigger:
        return
    sessions = plan.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    if not refresh and strava_gate_pending():
        return
    if not strava_connected():
        try:
            if refresh:
                updated = sync_all(
                    sessions,
                    activities(),
                    today(),
                )
            else:
                updated = sync_recent(
                    sessions,
                    activities(),
                    today(),
                )
        except PullError as exc:
            on_notice(str(exc))
        else:
            on_activities(updated)
            clear_notice()
            if opened:
                _apply_activity_marks(plan)
    restore_rows()
    on_loaded(trigger)
