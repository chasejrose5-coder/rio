# activity_pull.py — decide whether this page should say Strava is missing.

"""The check behind Dashboard, Plan, Weekly, Session, Progress, and Activity.

A test-season preview does not run. Past seasons does not run. When Strava
is not connected, stored runs stay and the page says Strava is not
configured. A connected account restores stored rows and does not fetch
them again here. Strava is the only activity source.

The Strava restore and the session writes are passed in. This module does
not import the UI shell.
"""

from __future__ import annotations

from ui.activities import NOT_CONNECTED_NOTICE
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
    strava_connected,
    strava_gate_pending,
    restore_rows,
    on_notice,
    on_loaded,
    pull_pages: tuple[str, ...] = PULL_PAGES,
) -> None:
    """Restore stored runs, or say Strava is not connected.

    `strava_connected` is a callable. Looking up the token writes session
    flags, so it runs only after the early returns.
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
    if not refresh and strava_gate_pending():
        return
    if not strava_connected():
        on_notice(NOT_CONNECTED_NOTICE)
    restore_rows()
    on_loaded(trigger)
