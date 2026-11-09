# Step 1 state inventory

What the Streamlit shell holds between reruns, and what a later FastAPI request has to store itself. This is the tree after the season transactions moved into `services/`. The shell still owns `st.session_state`. The services never read it.

A rerun sees the same dict. A new process does not. Keys below are either written into the local sealed file, a Supabase row, the browser cookie or `localStorage`, or they die with the tab.

## Persist these, or later weeks move twice

`season_quality_base` is the plan from before each week's adapt. `auto_adapt` and `adapt_from_result` use it so a second mark for that week does not adapt an already adapted plan. It is set in `_quality_bases`, `_store_plan`, `_reject_link`, and `_clear_season_marks`. It is read only by `_quality_bases`, which passes the dict into `services/season_commit.py`. It is not in `dump_record`, and `hosted_save_bundle` does not send it. A reload starts from `{}`. Calling adapt again with an empty base stacks the shift.

`rio_workout_notes` is `{date: {note, viewed}}` after `complete_insight()`. Set and read in `_remember_workout_note` and `_show_stored_insight`. Got it flips `viewed`. It is not in the local record or the cloud bundle. A refresh drops the note. The model call still runs inside the shell, after the plan is committed and before `st.rerun()`.

`rio_explain_cache` is the Last Session / Next / Decisions paragraph cache (`_shown_prose`, `ui/load_gate.py` `cached_paragraph`). Session-only. Safe to recompute. Do not send a Strava row through it.

`rio_adapt_pending` holds a result, watchless row, or week mark while confirm-before-adapt is on (`_hold_adapt`, `_adapt_pending`, `_clear_adapt`). Session-only. The new client can keep the dialog and POST on confirm. Do not store the pending mark.

`season_generation` is an integer bumped in `_store_plan` and `_clear_season_marks` so result boxes remount. Session-only. It is not season data.

`rio_cloud_saved_hash` is the `season_digest` of inputs, plan, marks, and actuals. `save_hosted_season` skips the write when it matches. Session-only. Recompute it. It does not cover activities, quality bases, or notes.

`rio_strava_nonce` and `rio_strava_state` are the OAuth state for the current tab (`strava_ui.connect_url`, `consume_callback`). Session-only. A different process loses the nonce. Step 2 should store the nonce server-side. This step does not.

## Season data

| Key | Set | Read | Stored? |
| --- | --- | --- | --- |
| `season_inputs` | `_store_plan`, `_recall_cloud_season`, `_reject_link`, cloud `_apply_bundle` | `_sync_browser_store`, `persist_cloud_season`, plan and Strava pages | Cloud `plans` columns. Local: the storage key and the URL, not a field in the JSON body. |
| `season_plan` | `_store_plan`, `_finish_commit`, `_apply_activity_marks`, `_clear_season_marks`, cloud `_apply_bundle` | Every plan page. `persist_cloud_season` reads it for the bundle. | Cloud `plans.plan`. Local does not store the body. A local reload rebuilds it with `sequence()` unless the cloud row is the source. |
| `season_marks` | `_finish_commit`, `_apply_activity_marks`, `_clear_season_marks`, cloud `_apply_bundle` | Mark buttons, `save_local_season`, `save_hosted_season` | Cloud `plans.marks` and the local record. |
| `season_actuals` | `_actuals` (created empty), commit and activity-mark services, cloud `_apply_bundle` | Result boxes, `save_local_season`, `save_hosted_season` | Cloud `plans.actuals` and the local record. The service mutates the dict the shell passes in. |
| `season_activities` | `_pull_for` callbacks, Strava `restore_rows`, `_restore_record`, `_clear_activity_pull` | Pull, Activity, volume, `save_local_season` | Local record only. `hosted_save_bundle` leaves it out. A hosted athlete not on Strava loses Intervals matches on the next session. Strava runs are reloaded from `strava_activities`. |
| `season_quality_base` | `_quality_bases`, `_store_plan`, `_reject_link`, `_clear_season_marks` | `_quality_bases` only | **No.** See above. |
| `rio_store_loaded` | Restore, `_store_plan`, `_clear_season_marks`, `_forget_deleted_season` | `_sync_browser_store`, `_restore_if_needed` | No. Stops an empty tab from overwriting the saved record. |
| `season_link_attempt`, `season_link_error`, `season_link_preview` | `_reject_link`, `_ensure_linked_plan` | `_ensure_linked_plan`, `_link_preview_note` | No. A hosted URL for someone else's four inputs must stay a preview. |
| `rio_save_error` | `persist_cloud_season` on `CloudAuthError` | `_link_preview_note` (then popped) | No. |
| `rio_cloud_plan_rows`, `rio_cloud_season_inputs` | Cloud `_apply_bundle`, `_forget_deleted_season` | `_recall_cloud_season`, `_past_body`, `_ensure_linked_plan`, `_cloud_plan_keys` | Cache of `plans` rows already stored for this user. The rows themselves are in Supabase. |
| `profile_goal_time`, `profile_goal_apply`, `rio_profile` | Profile page | Profile page | The goal text is the profile record (`ui/profile.py`). These keys are the form cache. |

`save_local_season` writes marks, actuals, and activities through `dump_record`. `save_hosted_season` writes one goals row and one plans row (`current_time`, `start_date`, `goal_time`, `goal_date`, `plan`, `marks`, `actuals`) plus `profile.display_name`. Neither writes `season_quality_base` or `rio_workout_notes`. `rio_test_preview` still returns before either save.

## Auth and account

| Key | Set | Read | Stored? |
| --- | --- | --- | --- |
| `rio_account`, `rio_account_secret` | Login, `_restore_session`, `open_cloud_session` | `_account_identity` | Local: Fernet seal in `localStorage` `rio.session.v1`. Hosted secret is the literal `"cloud"`. |
| `rio_session_token` | `issue_session`, or `cloud.` plus the access token | `_restore_session` | Same browser record. |
| `rio_session_write`, `rio_cookie_write`, `rio_cookie_max_age` | Login and refresh, waiting for the JS bridge | `_flush_cookie_if_needed` | Pending write. The cookie is `rio_hosted`. Max age is the rest of 24 hours from `issued_at`. |
| `rio_hosted_sid` | Cookie restore when the value starts with `rio1.` | Sign-out | Opaque id. The access token for that id is `app_sessions`, not this key. |
| `rio_cloud_user_id`, `rio_cloud_access`, `rio_cloud_refresh` | `open_cloud_session` | Cloud save, Strava store, delete | Access and refresh live in the session and, for the legacy cookie, in a JS-readable cookie. Step 2 should keep only the opaque id in the cookie. |
| `rio_cloud_name`, `rio_cloud_role`, `rio_cloud_profile` | Bundle apply | Home, settings, admin check | Cache of `profiles` and auth metadata. |
| `rio_cloud_loaded`, `rio_role_synced`, `rio_verified_token`, `rio_verified_user` | Once per session | The same functions | No. They stop a second `load_bundle` or `get_user`. |
| `rio_settings`, `rio_local`, `rio_local_email` | `_load_local`, `_persist_local`, bundle apply | `_prefs`, timezone, pace | Local file via `write_local`. Hosted pace, timezone, no-watch, intro, and Strava-prompt flags are auth user metadata. These keys are the cache. |
| `rio_easy_pace`, `rio_easy_pace_unit` | `_store_easy_pace`, `_load_local`, bundle apply | `stored_easy_pace` | Local profile and hosted auth metadata. |
| `rio_intro_seen`, `rio_strava_prompt_seen` | Intro and Home prompt | `_intro_due`, `_strava_prompt_dismissed` | Hosted auth metadata. Also cached here. |
| `rio_startup_seen` | `ui/startup.py` `acknowledge_startup` (`SEEN_KEY`) | `startup_pending` | No. Tab-local. A search for the literal string misses the assignment. |
| `rio_enter` | Login and `_open_restored_session` | `_with_plan` | No. Consumed to open Home or Start. |
| `rio_auth_screen`, `rio_login_error`, `rio_cloud_reset` | Auth screens | `render_cloud_auth` | No. |
| `rio_session_clear`, `rio_clear_browser`, `rio_reset_session` | Sign-out | Next boot | No. `clear-all` wipes `localStorage`. |

Widget keys cleared with the account, and not otherwise assigned in Python, are form fields only: `rio_cloud_email`, `rio_cloud_password`, `rio_cloud_name_input`, `rio_cloud_create_email`, `rio_cloud_create_password`, `rio_cloud_forgot_email`, `rio_cloud_new_password`, `rio_login_email`, `rio_login_password`, `rio_create_name`, `rio_create_email`, `rio_create_password`, and the `settings-*` / `start_*` keys in the list at the bottom. Passwords sit in the tab until the account-change clear. Do not copy that into Next.js.

## Strava and the pull

All session-only unless noted. Set and read in `ui/strava_ui.py` except `activity-refresh` and `rio_intervals_pulled`, which `_pull_for` reads and passes into `run_activity_pull`.

| Key | Role |
| --- | --- |
| `rio_strava_token`, `rio_strava_checked` | Cache of `strava_tokens`. `None` means checked and absent. The table is the store. |
| `rio_strava_runs` | Parsed runs. `restore_rows` merges them into `season_activities`. |
| `rio_strava_synced`, `rio_strava_synced_at`, `rio_strava_count`, `rio_strava_notice` | One import this session. A failed import does not stick `rio_strava_synced`. |
| `rio_strava_sync_state`, `rio_strava_defer_passes`, `rio_strava_draw_after_sync` | The deferred import fragment. |
| `rio_strava_nonce`, `rio_strava_state` | OAuth state. See the top of this note. |
| `rio_strava_offer`, `rio_strava_prompt_seen` | Home prompt. `strava_prompt_seen` is also auth metadata. |
| `rio_intervals_pulled`, `activities_loaded`, `activities_trigger` | Pull-once flags. Not stored. |
| `activities_notice` | `PullError` or an adapt `ValueError` from the pull. Not stored. |
| `activity-refresh` | Widget. Refresh reads full history. |

`run_activity_pull` does not call Strava when `strava_connected()` is true. It still calls `restore_rows`. It does not judge a match on that path. Judging runs only after an Intervals `sync_recent` or `sync_all` on a pull page.

## Other session-only keys

| Key | Set / read | Why it exists |
| --- | --- | --- |
| `rio_workout_notes` | `_remember_workout_note`, `_show_stored_insight` | Post-workout note. Not stored. |
| `rio_explain_cache` | `_shown_prose` | Paragraph cache. |
| `season_generation` | `_store_plan`, result and mark widgets | Remounts inputs. |
| `rio_adapt_pending` | `_hold_adapt`, confirm buttons | Confirm-before-adapt. |
| `rio_plan_last` | `page_plan` | Last Plan segment. The widget key is `plan-view`. |
| `rio_test_preview`, `rio_test_bundle`, `rio_test_go`, `rio_test_go_admin`, `rio_test_note`, `rio_test_error`, `rio_admin_season_backup` | `ui/sample_season_ui.py` | Admin test season. Preview skips save and pull. |
| `rio_hero_order`, `rio_hero_notice`, `rio_hero_error` | `_render_hero_editor` | Editor state. Rotation JSON is a file on disk, not these keys. |
| `rio_past_delete`, `rio_past_delete_error`, `rio_past_deleted` | Past seasons confirm | The delete itself is `remove_past_season`. |
| `rio_settings_error`, `rio_settings_note` | Settings actions | Flash text. |
| `rio_motion_page` | `_css` | Which page CSS to paint. |
| `_rio_volume_shown`, `_rio_heart_shown` | Activity and Progress | Chart mount guards. |
| `rio_google_url` | `_google_button` | Cached URL. Google sign-in is off. |
| `rio_admin_rows` | `page_admin` | Account table cache. |
| `rio_intervals_pulled` | `_pull_for` | See the pull table. |

## Widget and account-clear keys

These are Streamlit `key=` values or names only popped in `_apply_session_reset`. They do not round-trip through `save_local_season` or `save_hosted_season`.

`rio-log-out`, `easy-pace`, `easy-pace-unit`, `rio_easy_pace_error`, `rio_intro_force`, `rio_no_watch_saved`, `rio_pace_saved`, `settings-clear-ok`, `settings-clear-marks-ok`, `settings-compact`, `settings-confirm`, `settings-dates`, `settings-delete-email`, `settings-delete-ok`, `settings-delete-password`, `settings-delete-cloud-ok`, `settings-email`, `settings-ids`, `settings-name`, `settings-notes`, `settings-preferred`, `settings-recap`, `settings-reminders`, `settings-reset-ok`, `settings-start`, `settings-timezone`, `settings-pace`, `settings-no-watch`, `settings-units`, `start_current_time`, `start_goal_date`, `start_goal_time`, `start_start_date`, `rio_create_email`, `rio_create_name`, `rio_create_password`, `rio_login_email`, `rio_login_password`.

`settings-timezone` is read by `session_timezone` before it is saved onto the account. `settings-pace` is read by the Strava pace line the same way. The saved copy is `rio_settings` or auth metadata, not the widget key.
