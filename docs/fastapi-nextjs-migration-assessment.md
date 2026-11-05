# RIO migration assessment: Streamlit to FastAPI + Next.js

Analysis only. This document describes the tree as read for this assessment. It does not change `rio/`, `db/`, `adapters/`, `AGENTS.md`, or any UI module.

Grounded in:

- `ui/streamlit_app.py` (6,518 lines), the multipage shell
- `ui/cloud_ui.py`, `ui/cloud_store.py`, `ui/cloud_session.py`, `ui/cloud_config.py`
- `ui/strava.py`, `ui/strava_store.py`, `ui/strava_ui.py`
- `engines/`, `adapters/`, `db/`, `supabase/migrations/`
- a full scan of `st.session_state` names, `st.rerun`, and `st.query_params` in `*.py`

`docs/architecture.md` is older than the hosted app. It still describes Intervals.icu as the activity pull and a browser-only plan record. The running shell now persists seasons in Supabase and prefers Strava. Where they disagree, this assessment follows the Python that `st.navigation` actually runs.

Product rules that the migration must keep, because the code and `AGENTS.md` already enforce them:

- 800 m is the only scored event. `engines/season.py` `sequence()` builds that season. `rio/v0.1/events.yml` lists other distances and no engine reads it.
- Classification is rules. `engines/classify.py` `classify()` returns `family`, `reason_codes`, `confidence`, and `ontology_version`. A model does not pick the family.
- AI writes prose only. `engines/explain.py` may rephrase a paragraph or return one post-workout note. It does not choose a template or call `adapt()`.
- No goal probability and no readiness score. `engines/season.py` `_check()` rejects a plan or session that contains `probability` or `readiness_score`. `ui/plan_store.py` `export_season()` strips those keys.
- Intervals.icu is an adapter, not the product. It is still in the tree. Strava is the hosted activity path. See section 1.8.

Live host named in `supabase/migrations/README.md`: `https://riotraining.streamlit.app`. Local default in `ui/cloud_config.py`: `http://localhost:8501`.

---

## Executive summary

RIO is one Streamlit process whose entire product surface is `ui/streamlit_app.py`, plus about forty UI modules. The season engine, the classifier, the pace math, and the Strava parser are already plain Python and can be wrapped 1:1. The thing that will not survive a port is the control flow: almost every user action writes `st.session_state` and calls `st.rerun()`, and the next script run is the database transaction.

Hosted accounts are Supabase Auth. The browser cookie `rio_hosted` is supposed to hold only an opaque id (`rio1.` + random), with access and refresh tokens in `public.app_sessions`. A legacy JSON cookie and `localStorage` key `rio.session.v1` can still carry the access token. Streamlit cannot set `HttpOnly`. That is the auth bug the new stack should close, not copy.

There is no Insights route. Phase copy is `ui/insights.py` (rules text). The model note is `engines/explain.py` `complete_insight()`, stored only in `rio_workout_notes` for the current Streamlit session. `weekly_digest()` exists and no page calls it.

Recommended target: keep Supabase Postgres, Auth, and the existing RLS. Put FastAPI in front of `engines/` and the Strava token table. Put Next.js App Router in front of the pages. Do not introduce a second schema with SQLModel unless a later phase has a reason to leave Supabase.

Working-day range for one strong engineer plus cloud agents, sequential: about 34–56 days. The spread is the 6,518-line shell and the 3,210-line stylesheet, not the engines.

---

## 1. Current codebase audit and state complexity

### 1.1 Shape of the process

Entry is the bottom of `ui/streamlit_app.py`, not a `pages/` directory.

Boot order on every full script run:

1. `load_local_env()` from `ui/activities.py` (reads `.env`, never prints values).
2. `_apply_session_reset()` if `rio_reset_session` is set.
3. `_boot_bridge()` mounts the `rio_session_store` component (`_SESSION_STORE_JS`) unless a sign-out clear is in progress.
4. Startup gate: `startup_pending()` until `rio_startup_seen` is true, unless the season already has sessions or `skip=1`.
5. `_restore_session()` opens a local Fernet token or a `cloud.` token.
6. `boot_strava()` from `ui/strava_ui.py`.
7. If `_account_identity()` is missing, `_render_login()` and `st.stop()`.
8. `st.navigation(..., position="hidden").run()`.

Every routed page is wrapped by `_with_plan()`:

- `rio_enter` sends the athlete to Home or Start via `_route_after_login()`.
- `rio_test_go_admin` sends an admin preview back to Admin.
- `_load_local()`, `_load_shared_plan()`, `_link_preview_note()`.
- `_intro_gate()` can return before the page draws.
- `_pull_for(page.__name__)` may import activities and call `auto_adapt()`.
- `_sync_browser_store()` writes the local encrypted record or `persist_cloud_season()`.
- Then the page function runs.

That wrapper is the unit of work a FastAPI request plus a Next.js loader has to replace. Today one navigation click re-executes auth restore, plan linking, activity pull policy, and a save.

`st.navigation` routes (assigned at the bottom of `ui/streamlit_app.py`):

| Screen | Function | `url_path` | How the athlete reaches it |
| --- | --- | --- | --- |
| Start | `page_start` | default page | First screen when there is no current season. Form keys `start_current_time`, `start_start_date`, `start_goal_time`, `start_goal_date`. Generate calls `sequence()` then `st.switch_page` to Plan. |
| Home | `page_dashboard` | `home` | Top nav. Track, phase story, Strava prompt, stored insight. |
| Plan | `page_plan` | `plan` | Top nav. Segmented control `plan-view` nests `page_calendar`, `page_weekly`, or `page_season`. Those three are not their own routes. |
| Session | `page_session` | `session` | Linked with `date` or `activity`. Not a top-nav label. Result boxes call `judge()` then `adapt()`. |
| Activity | `page_activity` | `activity` | Top nav. `ui/activity_board.py` cards. Refresh key `activity-refresh` / `rio-activity-refresh`. |
| Library | `page_library` | `library` | Top nav. `load_menu()` plus `filter_workouts()`. |
| More | `page_more` | `more` | Top nav. Links only. |
| Past seasons | `page_past_seasons` | `past-seasons` | More. |
| Profile | `page_profile` | `profile` | More. Goal time edit. Does not rebuild the season by itself. |
| Settings | `page_settings` | `settings` | More. Name, pace, confirm-before-adapt, account delete, Strava block. |
| About | `page_about` | `about` | More. `ui/about.py` `about_sections()`. |
| Creators | `page_creators` | `creators` | More. Static bio. Photo from `ui/theme.py`. |
| Admin | `page_admin` | `admin` | Top nav only when `viewer_is_admin(email)` (`ui/access.py`, env `RIO_ADMIN_EMAIL`). Read-only account table, test season, hero rotation. |
| Last Session | `page_last_session` | `last-session` | In `_KEPT_PAGES`, so the URL works. Not in the More blurb. Fixture YAML or `tests/fixtures/intervals/*.json`. Calls `normalize`, `classify`, `explain`. |
| Next | `page_next` | `next` | Kept URL. `prescribe()` plus `explain_prescription()`. Does not touch the season. |
| Decisions | `page_decisions` | `decisions` | Kept URL. Reads `engines/accept.py` planned YAML. Does not call `accept()`. |
| Ledger | `page_ledger` | `ledger` | Kept URL. In-memory `Ledger`. Dies with the process. |
| Goal | `page_goal` | `goal` | Kept URL. `rio/v0.1/goal.yml`, not the athlete's Start form. |
| Progress | `page_progress` | not registered | Function still exists. `progress_weeks()` is used by `_plan_weeks()` on Plan. `volume_chart()` and `heart_rate_chart()` are also drawn from `page_activity`. There is no `/progress` route. |

Startup (`ui/startup.py` `render_startup`) and the intro (`ui/intro.py` `render_intro`) are gates, not `st.Page`s.

There is no Insights hub page. See section 1.9.

### 1.2 Session state

Streamlit session state is per browser tab and per server process. It is not a database. A rerun sees the same dict. A new Cloud replica does not.

Two kinds of keys show up:

- Names the code assigns with `st.session_state["..."]` or reads with `.get` / `.pop`.
- Widget `key=` values. Streamlit writes those itself. `_ACCOUNT_SESSION` in `ui/streamlit_app.py` lists the ones that must be cleared when the account changes, including several that never appear as a string assignment.

`rio_startup_seen` is assigned as `state[SEEN_KEY]` inside `ui/startup.py` (`SEEN_KEY = "rio_startup_seen"`). A search for `st.session_state["rio_startup_seen"]` will miss it. The boot check is `startup_pending(st.session_state)`.

#### Season plan, marks, actuals

| Key | Role | Written by | Survives a reload? |
| --- | --- | --- | --- |
| `season_inputs` | Tuple `(current_time, start_date, goal_time, goal_date)`. | `_store_plan`, `_apply_bundle`, URL via `plan_inputs()`. | Cloud: columns on `public.plans`. Local: key `rio.plan.v1\n` + the four strings (`ui/plan_store.py` `storage_key`, `ui/past_seasons.py` `KEY_PREFIX`). |
| `season_plan` | Dict from `sequence()` or `adapt()`. `ontology_version`, `season_length_weeks`, `start_date`, `sessions`. | `_store_plan`, `_commit_result`, `_commit_mark`, `_apply_activity_marks`, cloud bundle. | Cloud `plans.plan` jsonb. Local encrypted record does **not** store the plan body; the URL or the four inputs rebuild it with `sequence()`, except cloud which stores the adapted plan. |
| `season_marks` | Week number to `on_track` / `not_hitting` / `smashing`. | Mark buttons, `auto_adapt`, cloud bundle, `load_record`. | Cloud `plans.marks`. Local record. |
| `season_actuals` | Date to `{text, numbers, mark, template_id, slots?, intervals?}`. The `intervals` field is a filename or activity id, including a Strava id. | `_commit_result`, `auto_adapt`. | Cloud `plans.actuals`. Local record. |
| `season_activities` | Reduced activity rows (Intervals pull and/or Strava). | `_pull_for`, `restore_rows`, `load_record`. | Local record via `dump_record`. **Not** in `persist_cloud_season()`. Hosted Strava runs are reloaded from `strava_activities`. A cloud user who is not on Strava loses Intervals matches on the next session. |
| `season_generation` | Integer bumped when a new plan replaces widget keys, so result boxes remount. | `_store_plan`, settings clear. | No. UI only. |
| `season_quality_base` | Map of week to the plan from before that week's auto-adapt, so a later mark does not adapt an already adapted plan. | `_apply_activity_marks`, `_adapt_from_result`. | **No.** Not in the cloud bundle, not in `dump_record`. |
| `season_link_attempt`, `season_link_error`, `season_link_preview` | URL four-tuple that failed or is waiting for confirm before `sequence()`. | `_reject_link`, `_ensure_linked_plan`, `_link_preview_note`. | No. |
| `rio_store_loaded` | Record has been read. Stops `_sync_browser_store` from treating an empty session as the save. | Restore paths. | No. |
| `rio_save_error` | Last `CloudAuthError` from `persist_cloud_season`. Popped by `_link_preview_note`. | `ui/cloud_ui.py`. | No. |
| `rio_adapt_pending` | Held result or week mark when `rio_settings["confirm_adapt"]` is true. | `_hold_adapt`. | No. |
| `rio_plan_last` | Last Plan segmented control: Calendar, This week, Full season. | `page_plan`. Widget key is `plan-view`. | No. |
| `rio_workout_notes` | `{date: {note, viewed}}` after `complete_insight()`. | `_remember_workout_note`, Got it button. | **No.** Not written to Supabase or the local record. |
| `rio_explain_cache` | Paragraph cache for Last Session / Next / Decisions via `ui/load_gate.py` `cached_paragraph`. | `_shown_prose`. | No. |
| `profile_goal_time`, `profile_goal_apply` | Profile form. | `page_profile`. | Goal text is also a profile record (`ui/profile.py` `profile_key`). |
| `rio_profile` | Cached profile goal payload. | Profile page. Cleared in `_ACCOUNT_SESSION`. | Depends on the profile record, not this key. |

`persist_cloud_season()` (`ui/cloud_ui.py`) writes `goals` plus one `plans` row (`current_time`, `start_date`, `goal_time`, `goal_date`, `plan`, `marks`, `actuals`) and skips the write when `season_digest()` matches `rio_cloud_saved_hash`. It does not send `season_activities`, `season_quality_base`, or `rio_workout_notes`. Test-season preview returns immediately (`rio_test_preview`).

#### Auth, cookies, hosted session

| Key | Role |
| --- | --- |
| `rio_account` | Email string. |
| `rio_account_secret` | Local Fernet seal key, or the literal `"cloud"`. `_hosted_account()` checks for `"cloud"`. |
| `rio_session_token` | Local signed token from `ui/accounts.py` `issue_session`, or `"cloud." + access_token`. |
| `rio_session_write` | Payload waiting for the browser bridge to write `localStorage` `rio.session.v1`. |
| `rio_cookie_write`, `rio_cookie_max_age` | Pending `rio_hosted` cookie body and `Max-Age`. Flushed by `_flush_cookie_if_needed`. |
| `rio_hosted_sid` | Opaque cookie value when it starts with `rio1.` (`ui/cloud_session.py` `HOSTED_PREFIX`). |
| `rio_session_clear`, `rio_clear_browser`, `rio_reset_session` | Sign-out. `clear-all` wipes `localStorage`. `_ACCOUNT_SESSION` is popped on the next run. |
| `rio_enter` | Set by login and by `_open_restored_session`. `_with_plan` consumes it and `st.switch_page`s to Home or Start. |
| `rio_startup_seen` | Startup Continue. Tab-local. |
| `rio_auth_screen` | `login` (default), `create`, `forgot`, `confirm`. |
| `rio_cloud_reset` | Password-recovery query (`reset=password` or `type=recovery`) forces `_render_reset`. |
| `rio_login_error` | Visible auth or Strava-unrelated form error. |
| `rio_cloud_user_id` | Supabase user uuid. |
| `rio_cloud_access` | Supabase access token. Also read by `ui/strava_store.py` when the user client is used. |
| `rio_cloud_refresh` | Supabase refresh token. |
| `rio_cloud_name`, `rio_cloud_role`, `rio_cloud_profile` | Display name, role, profile dict. |
| `rio_cloud_loaded` | Bundle already applied. Stops a second `load_bundle` inside `open_cloud_session`. |
| `rio_cloud_saved_hash` | `season_digest` of inputs, plan, marks, actuals. |
| `rio_cloud_season_inputs` | List of four-tuples already stored for this user. `hosted_link_action()` uses it. |
| `rio_cloud_plan_rows` | Raw `plans` rows. `row_for_inputs()` picks one. |
| `rio_role_synced` | `_sync_admin_role_once` has run. Admin email match calls `set_role(..., "admin")` with the service key. |
| `rio_verified_token`, `rio_verified_user` | Last auth user fetched for this access token. Avoids a repeat `get_user`. |
| `rio_google_url` | Cached Google authorize URL. The button is hidden: `SHOW_GOOGLE_SIGN_IN = False` in `ui/cloud_ui.py`. |
| `rio_local`, `rio_local_email` | Local-account settings blob from `read_local` / `write_local`. |

Widget keys that are session state because `st.text_input(..., key=)` uses them: `rio_cloud_email`, `rio_cloud_password`, `rio_cloud_name_input`, `rio_cloud_create_email`, `rio_cloud_create_password`, `rio_cloud_forgot_email`, `rio_cloud_new_password`, `rio_login_email`, `rio_login_password`, `rio_create_name`, `rio_create_email`, `rio_create_password`. Passwords sit in session state until the account-change clear. The Next.js forms should not mirror that.

#### Strava

All of these live in `ui/strava_ui.py` unless noted.

| Key | Role |
| --- | --- |
| `rio_strava_token` | Token dict cached after `strava_tokens` read. `None` means checked and absent. |
| `rio_strava_checked` | Skip another token read this session. |
| `rio_strava_sync_state` | `"done"` after the deferred import, or set immediately when there is no cloud user. |
| `rio_strava_defer_passes` | Counter for `run_deferred_strava`. The fragment `_paint_then_sync` runs every 1 second until the import finishes, then `st.rerun(scope="app")`. |
| `rio_strava_synced`, `rio_strava_synced_at`, `rio_strava_count` | One successful import this session, timestamp, run count. |
| `rio_strava_runs` | Parsed runs. `restore_rows()` merges them into `season_activities` with `source: "strava"`. |
| `rio_strava_nonce`, `rio_strava_state` | OAuth `state`. `make_state()` returns `strava:{user_id}.{nonce}.{hmac}`. |
| `rio_strava_notice` | Safe error string. |
| `rio_strava_draw_after_sync` | Activity refresh sets this, forces `sync_once`, reruns, then draws. |
| `rio_strava_offer`, `rio_strava_prompt_seen` | Home prompt after a plan is generated. `strava_prompt_seen` is also auth-user metadata via `save_strava_prompt_seen`. |
| `activity-refresh` | Truthy when the Activity refresh widget was clicked. `_pull_for` treats that as a full history pull. |

`cloud_sign_out()` pops the token, synced flag, checked flag, runs, state, nonce, and notice.

#### Intervals pull flags

| Key | Role |
| --- | --- |
| `rio_intervals_pulled` | `ui/load_gate.py` `pull_again()`: after the first pull, only Activity refresh pulls again. The name says Intervals. Strava restore still runs when the pull is skipped. |
| `activities_loaded`, `activities_trigger` | Trigger is the page function name, or `"load"`. Same trigger does not pull twice. |
| `activities_notice` | `PullError` or `auto_adapt` `ValueError`. |

`_pull_for` returns immediately on `rio_test_preview` and on `page_past_seasons`. If Strava is connected it does **not** call `sync_recent` / `sync_all`. If Strava is not connected it still calls those Intervals functions. Then it always `restore_rows()`.

#### Settings, intro, chrome

| Key | Role |
| --- | --- |
| `rio_settings` | Dict from `ui/settings.py` `normalize()`. Fields: `units`, `pace_units`, `show_ids`, `compact`, `date_format`, `confirm_adapt`, `notifications`, `start_date`, `reminders`, `recap`, `theme`. Not passed into `adapt()`. |
| `rio_settings_error`, `rio_settings_note` | Save failure or confirmation copy. |
| `rio_pace_saved` | Last pace unit written to auth user metadata (`mi` or `km`). |
| `rio_intro_seen`, `rio_intro_force` | Intro gate. Cloud copy is auth metadata `intro_seen`. |
| `rio_motion_page` | Last page name for the CSS motion class. |
| `_rio_heart_shown`, `_rio_volume_shown` | One-shot chart flags inside the shell. |
| `settings-pace` | Read by `ui/strava_ui.py` `_pace_choice()` as well as the settings widgets. |
| `settings-clear-ok`, `settings-clear-marks-ok`, `settings-reset-ok`, `settings-delete-cloud-ok`, `settings-delete-email`, `settings-email`, `settings-timezone` | Confirm steps and fields on Settings. |
| `settings-name`, `settings-preferred`, `settings-notes`, `settings-ids`, `settings-compact`, `settings-confirm`, `settings-dates`, `settings-start`, `settings-units`, `settings-reminders`, `settings-recap`, `settings-delete-password`, `settings-delete-ok` | Widget keys cleared with the account. Listed in `_ACCOUNT_SESSION`. |

#### Admin and the test season

| Key | Role |
| --- | --- |
| `rio_admin_rows` | Cached `admin_account_rows()`. |
| `rio_hero_order`, `rio_hero_notice`, `rio_hero_error` | Startup photo editor. Order is saved through `ui/hero_config.py`. |
| `rio_test_preview` | Admin is looking at the TEST athlete. Skips cloud save, Strava import, and Intervals pull. |
| `rio_test_bundle` | Loaded test season payload. |
| `rio_test_error`, `rio_test_note` | Admin test-season status. |
| `rio_test_go`, `rio_test_go_admin` | `home` / `plan` / `activity` switch targets. |
| `rio_admin_season_backup` | Real season snapshot while the preview is applied (`ui/sample_season_ui.py`). |

`apply_preview()` overwrites `season_inputs`, `season_plan`, `season_marks`, `season_actuals`, `season_activities`, and Strava run keys, and sets `rio_store_loaded`.

### 1.3 Cookies, localStorage, query params

**Cookie.** Name `rio_hosted` (`ui/cloud_session.py` `COOKIE_NAME`). Written from JavaScript in `_SESSION_STORE_JS`: `Path=/; SameSite=Lax; Secure`. `Max-Age` is the remainder of 24 hours (`SESSION_SECONDS`). Refreshing the Supabase token does not extend it (`cookie_max_age`). The cookie is **not** `HttpOnly`. The comment above the script says the component bridge cannot set `HttpOnly`. `SameSite=Lax` is deliberate so the OAuth return still sends the cookie.

Two bodies:

- Current: `rio1.` plus `secrets.token_urlsafe(32)`. Server stores `sha256(sid)` as `app_sessions.sid_hash` (`hosted_hash`). Row holds access token, refresh token, email, display name, `issued_at`, `expires_at`. Service role only. Migration `006_app_sessions.sql`.
- Legacy: `pack_cookie()` JSON with `access_token`, `refresh_token`, `user_id`, `email`, `display_name`, `issued_at`. `unpack_cookie()` rejects a body over 4,000 characters, a future `issued_at`, an age of 24 hours or more, and the substrings `service_role`, `service_key`, and `sb_secret_`. `restore_hosted_cookie()` still accepts this shape, then the next write can store only the id. Until migration 006 has been applied, the app keeps writing the older cookie (`supabase/migrations/README.md`).

**localStorage.**

- `rio.session.v1`: local signed session token, or a `cloud.` token. Bridge component name `rio_session_store`, widget key `rio-keep-session`.
- Plan bridge `_PLAN_STORE_JS`, component `rio_plan_store`, widget key `rio-plan-store`. Key is `storage_key(inputs)` which is `rio.plan.v1\n` plus the four inputs. The hosted path returns before the local write (`_sync_browser_store` returns when `rio_account_secret == "cloud"`). The JS bridge is still mounted for local accounts.
- Sign-out `clear-all` calls `localStorage.clear()`.

**First-run bridge.** `_boot_bridge()` calls `_browser_session("read")`. If the component has not answered, it returns and the startup page may `st.stop()`. The cookie is applied on the following run by `_restore_hosted_from_bridge()` then `restore_hosted_cookie()`. A signed-in rerun does not call the host again. This is why login feels like two paints.

**Query parameters.**

| Param | Owner | Meaning |
| --- | --- | --- |
| `current_time`, `start_date`, `goal_time`, `goal_date` | `ui/plan_store.py` `INPUTS` | The season identity. Dates must be `YYYY-MM-DD`. Each field at most 40 characters. `_publish_inputs` keeps them off the link for a hosted account. |
| `date` | `_query_date` | Session day. |
| `activity` | `_query_activity` | Extra (unmatched) activity id. |
| `skip` | Boot | `1` after startup Continue, so the splash does not repeat on that run. |
| `code`, `state`, `scope` | Strava `consume_callback` | OAuth return. Cleared after use. `state` must match `state_matches()`. |
| `code`, `flow` | `ui/cloud_ui.py` `_consume_callback` | Supabase PKCE / OAuth code exchange. **Skipped** when `state` starts with `strava:`, so the two `code` params do not steal each other. |
| `reset`, `type` | `_consume_callback` | `reset=password` or `type=recovery` sets `rio_cloud_reset`. |
| `token_hash`, `token` | `_render_reset` | Supabase recovery token. |

`load_is_app_root()` treats the path leaf `""`, `~`, `+`, or `home` as the app root. A deep link to Plan or Session stays put. Streamlit's own `~` and `+` leaves are why that function exists.

### 1.4 `st.rerun` hotspots

A rerun re-enters the whole module, including `_boot_bridge`, `boot_strava`, and `_with_plan`. These are the call sites, by enclosing function.

**Auth and session**

| Where | Why it reruns |
| --- | --- |
| `ui/cloud_ui.py` `_consume_callback` | Supabase `code` exchanged, query cleared. |
| `_render_sign_in`, `_render_sign_up`, `_render_confirm`, `_render_forgot`, `_render_reset` | Screen changes and successful sign-in. Each success calls `open_cloud_session` then reruns. |
| `_directory_or_notice` | Accounts not configured. |
| `ui/streamlit_app.py` `_sign_out` | Clears query params. |
| `_restore_session` | Dead token. |
| `_refresh_session` | Local token reissue failed or succeeded. |
| `_open_auth`, `_enter_account`, `_render_create_account`, `_render_login` | Local email/password path used when cloud settings are absent. |
| Module boot after `render_startup` | Sets `skip=1`. |
| `ui/sample_season_ui.py` `_load`, `_delete`, `_arm`, `preview_banner` | Admin TEST season. |

**Season plan**

| Where | Why it reruns |
| --- | --- |
| `_link_preview_note` | Hosted URL preview resolved. |
| `_hold_adapt`, `_confirm_adapt` | Confirm-before-adapt dialog. |
| `_commit_result` | `judge()` then `adapt()`, then `_remember_workout_note` (model call) **before** the rerun. |
| `_commit_mark` | Week mark buttons on Weekly and Season, which Plan nests. |
| `_clear_season_marks`, `_reset_saved_plan` | Settings destructive actions. Several reruns in a row for confirm widgets. |
| `page_profile` | Goal save. |
| `page_settings` | Name, email, password, pace, delete. About a dozen reruns in one function. |

**Workout session and insights**

| Where | Why it reruns |
| --- | --- |
| `_remember_intervals` | Attach a local JSON ref without a second `adapt()`. |
| `_show_stored_insight` | Got it sets `viewed` on `rio_workout_notes`. |
| `_intro_gate` | Intro finished. |
| `_maybe_strava_prompt` | Not now / connect dismissed. |

**Strava and Activity**

| Where | Why it reruns |
| --- | --- |
| `consume_callback` | Code exchanged, query cleared, `rio_strava_synced` popped so the next run imports. |
| `_paint_then_sync` | `st.rerun(scope="app")` after the deferred import. This is the only scoped rerun. |
| `prepare_activity` | Refresh clicked. |
| `_disconnect` | Token row deleted. |
| `_render_hero_editor` | Admin photo save. |

`st.switch_page` is the other full reload: login routing, nav links, Generate season, session day links, admin preview. Query params ride along via `_link_params()` / `query_values()`.

### 1.5 Module classification

Line counts are `wc -l` on this tree. “Pure” means no Streamlit import and no read of `st.session_state`. A thin FastAPI route can call the function. “Refactor” means the behavior should survive but the Streamlit, cookie, or Supabase client wiring should not be imported by a router as-is. “Replace” means the Next.js app draws it and the Python file goes away with Streamlit.

#### Keep as pure backend

| Module | Keep | Notes |
| --- | --- | --- |
| `engines/season.py` (1,552) | `sequence`, `adapt`, `season_length_weeks`, `work_meters` | Rules only. Copies the plan. Rejects probability and readiness. Reads `rio/v0.1/event_weights.yml` and `rio/templates/800m/`. |
| `engines/classify.py` | `classify`, `load_goal_800_seconds` | If-then. Reads `docs/goal.md` `Target 800` for pace bands. That file is a second goal (Chase, 2:02.9 to 1:55.0). The season builder does not read it. |
| `engines/normalize.py` | `normalize` | Laps only: `distance_m`, `seconds`, `rest_s`. |
| `engines/prescribe.py` (705) | `prescribe`, `load_menu`, `load_constraints` | Ledger in, one to three menu ids out. Does not call `sequence`. |
| `engines/ledger.py` | `Ledger`, `load_paper`, `load_goal`, `load_capacities` | In-memory. Does not write SQLite. |
| `engines/pace.py` (780) | `workout_times`, `display_workout`, `project_800`, `PaceLog`, `correction_factor`, `status_for` | Planned-versus-actual math. Strava and the Home track both use it. |
| `engines/explain.py` (980) | `explain`, `explain_prescription`, `explain_decision`, `complete_insight`, `insight_acceptable`, `weekly_digest` | The only model caller. Spend file `data/explain_spend.json` unless `RIO_EXPLAIN_SPEND_PATH` is set. Cap is $25. `weekly_digest` is unused by the UI. |
| `engines/accept.py` | `accept`, `load_planned`, `format_planned` | Writes `tests/fixtures/planned/`. The Decisions page only reads. Do not expose `accept()` as a public write of the fixture tree. |
| `ui/auto_adapt.py` | `auto_adapt` | No network. Judges Tuesday/Thursday non-`aer_` days from stored rows and calls `adapt()`. |
| `ui/result.py` | `judge`, `goal_seconds`, `result_box_count`, `filled_times` | 3 percent band. Does not call `adapt()`. |
| `ui/plan_store.py` (415) | `plan_inputs`, `dump_record`, `load_record`, `hosted_link_action`, `export_season`, `storage_key` | Record shape. The localStorage JS is not in this file. |
| `ui/insights.py` (579) | `phase_story`, `phase_name`, `workout_inputs`, `later_effect`, `season_thesis`, `this_week_copy` | Authored copy and the reduced payload for `complete_insight`. No model import. |
| `ui/activities.py` (573) | `sync_recent`, `sync_all`, `match_activities`, `merge_activities` | Intervals pull. Inject stand-ins in tests. Keep behind a flag. See 1.8. |
| `ui/strava.py` (645) | `import_runs`, `exchange_code`, `make_state`, `match_runs`, `planned_vs_actual`, `parse_activity`, `to_stored_activity` | HTTP is injected (`http_post`, `http_get`). Safe to call from a worker. |
| `ui/dashboard.py`, `calendar.py`, `library.py`, `progress.py`, `recap.py`, `activity_data.py`, `activity_board.py`, `last_session.py`, `settings.py` (`normalize`, formatters), `past_seasons.py`, `profile.py`, `about.py`, `plan_strava.py`, `load_gate.py`, `start_form.py` | Display and policy functions | No session reads. Home, Plan, Activity, and Library can call them from FastAPI or from the Next server. |
| `ui/sample_season.py` | `build_test_season`, `load_test_season`, `delete_test_season` | Admin fixture. Service role. Not athlete data. |
| `adapters/intervals_icu.py` | `fetch_activity`, `list_activities`, `to_normalize_input` | GET only. Env `RIO_INTERVALS_API_KEY`, `RIO_INTERVALS_ATHLETE_ID`. |
| `adapters/intervals_cli.py` | CLI | Not a page. |
| `rio/v0.1/*.yml`, `rio/templates/800m/*.yml` (40 recipes) | Data | Ontology `v0.1`. `events.yml` and `adaptations.yml` are unused by Python. |
| `db/load.py`, `db/schema.sql` | Fixture SQLite | The Streamlit app imports `parse_fixture` and `fixture_paths` only. It never opens `data/rio.sqlite`. Do not promote this schema to the product database. |

#### Refactor into FastAPI routers and dependencies

| Module | Becomes | Why it cannot be imported raw |
| --- | --- | --- |
| `ui/cloud_store.py` (1,632) | `services/directory.py` plus routers `auth`, `plans`, `goals`, `admin` | `SupabaseDirectory` and `MemoryDirectory` already have the right methods: `sign_up`, `sign_in`, `sign_out`, `refresh_session`, `exchange_code`, `google_url`, `request_reset`, `load_bundle`, `save_bundle`, `save_pace_units`, `save_intro_seen`, `save_strava_prompt_seen`, `list_users`, `delete_user`, `set_role`, `save_hosted_session`, `load_hosted_session`, `drop_hosted_session`, `write_owned_season`, `read_owned_season`. PKCE verifiers are process memory (`stash_verifier` / `take_verifier`). That breaks with more than one worker. |
| `ui/cloud_session.py` | Session dependency | Cookie pack/unpack and `season_digest` stay. The JS writer goes away. |
| `ui/cloud_config.py` | `Settings` | `RIO_SUPABASE_URL`, `RIO_SUPABASE_ANON_KEY`, `RIO_SUPABASE_SERVICE_ROLE_KEY`, `RIO_APP_URL`. Environment wins over `st.secrets`. |
| `ui/strava_store.py` | Repository | `SupabaseStrava` uses the service role for `strava_tokens` and `strava_activities`. Tokens are not granted to `authenticated` (`003_strava.sql`). |
| `ui/access.py` | `require_admin` | Compares the confirmed auth email to `RIO_ADMIN_EMAIL`. Role on `profiles` is locked by trigger. Do not trust a client-sent role. |
| `ui/accounts.py` (835) | Optional local dev store, or drop for hosted | Fernet-sealed JSON file. Production `riotraining.streamlit.app` uses Supabase when the three cloud settings exist. Porting this file into the hosted API preserves a second account system. |
| `ui/streamlit_app.py` orchestration, not the widgets | `services/season_app.py` | `_commit_result`, `_commit_mark`, `_apply_activity_marks`, `_pull_for`, `_ensure_linked_plan`, `_remember_workout_note`. These are the transactions. They are buried in the shell. |
| `ui/hero_config.py` | Small admin route | Reads and writes the startup rotation JSON. |

Suggested routers, each calling the service above and then the engine:

| Router | Endpoints that match today's behavior | Engine or store |
| --- | --- | --- |
| `POST /seasons` | `page_start` Generate | `sequence` |
| `POST /seasons/{id}/marks` | Week mark buttons | `adapt` |
| `POST /seasons/{id}/results` | Session boxes | `judge` then `adapt` then optional `complete_insight` |
| `POST /seasons/{id}/activities/sync` | `_pull_for` | Strava `import_runs`, or Intervals `sync_recent` / `sync_all` when Strava is absent |
| `GET /seasons`, `GET /seasons/{id}` | Bundle load, past seasons | `load_bundle` |
| `GET /menu` | Library | `load_menu` |
| `POST /classify` | Last Session | `normalize` + `classify` + `explain` |
| `POST /prescribe` | Next | `Ledger.record_fixture` + `prescribe` |
| `GET /insights/phase` | Home phase card | `phase_story` |
| `POST /insights/workout` | After a hard-day mark | `workout_inputs` + `complete_insight` |
| `POST /auth/*` | Login, signup, forgot, reset, logout | `SupabaseDirectory` |
| `GET /auth/session` | Cookie restore | `app_sessions` |
| `GET /strava/connect`, `GET /strava/callback`, `POST /strava/disconnect`, `POST /strava/sync` | Settings and the deferred import | `ui/strava.py` |
| `GET /admin/accounts`, test-season routes | `page_admin` | service role |

Dependencies: `get_settings`, `get_directory`, `get_session` (cookie to user), `get_strava_store`, `require_admin`. One service owns the copy-on-write plan update and the `season_digest` skip. Routers stay thin.

SQLModel is optional as a typed mirror of the tables in section 1.7. It should not replace Supabase Auth or the RLS policies in the first migration. A second Postgres model of `plans` will drift from `plans_season_key` and the `touch_plan_updated_at` trigger.

#### Streamlit-only UI to replace

| Module | Lines | What Next.js replaces |
| --- | --- | --- |
| `ui/streamlit_app.py` | 6,518 | Every `page_*`, nav, HTML string cards, rerun flow, both JS bridges. |
| `ui/cloud_ui.py` | 776 | Login, create, forgot, reset. Google and the confirm-email screen are flagged off. |
| `ui/strava_ui.py` | 641 | Connect button, settings block, home line, activity block, the 1-second fragment. The parser stays. |
| `ui/theme.py` | 1,554 | Photo URLs, a few injected rules. The bulk of the look is `ui/static/app.css`. |
| `ui/static/app.css` | 3,210 | Port the file first. Do not rewrite it as Tailwind utility classes before visual parity. |
| `ui/startup.py`, `ui/intro.py` | 342, 141 | Splash and first-run guide. |
| `ui/sample_season_ui.py` | 227 | Admin preview widgets. |
| `ui/css_href.py` | 23 | Cache-bust query. Next.js asset hashing replaces it. |
| `ui/creators.py` | 26 | Static list. The long bio is inline in `page_creators`. |

Tests under `tests/` (pytest, no Streamlit server; `.github/workflows/ci.yml` runs `pytest -q` and `pip-audit`) should keep passing against the engines during the move. Many tests read `ui/streamlit_app.py` as text and assert that a string is still there. Those tests will fail or become meaningless once the shell is deleted. They are a migration cost, not a runtime dependency.

### 1.6 Data layer

**Supabase Auth and Postgres.** Client: `supabase==2.34.0` (`requirements.txt`). Config names are in `.env.example` and `ui/cloud_config.py`:

- `RIO_SUPABASE_URL`
- `RIO_SUPABASE_ANON_KEY`
- `RIO_SUPABASE_SERVICE_ROLE_KEY` (optional for sign-in, required for admin list/delete, Strava tokens, `app_sessions`)
- `RIO_APP_URL`
- `RIO_ADMIN_EMAIL`
- `RIO_STRAVA_CLIENT_ID`
- `RIO_STRAVA_CLIENT_SECRET`

Streamlit Cloud secrets are the fallback when the environment variable is empty (`read_setting`). Do not commit values.

Migrations, applied by hand in the SQL editor, not by the app:

| File | What it does |
| --- | --- |
| `001_accounts.sql` | `profiles` (`id` = `auth.users.id`, `email`, `display_name`, `role` in `athlete`/`coach`/`admin`), `goals` (one row, event default `800m`), `plans` (jsonb `plan`, `marks`, `actuals`, quoted `"current_time"`), `results`. RLS: `auth.uid()` owns the row. |
| `002_lock_roles.sql` | Trigger `lock_profile_role`. Authenticated users cannot change `role`. Inserts forced to `athlete`. Service role may set it. Column grants on `profiles` reduced to `email`, `display_name`. |
| `003_strava.sql` | `strava_tokens` (service role only) and `strava_activities` (owner RLS, primary key `(user_id, activity_id)`). |
| `005_lock_profile_email.sql` | Trigger `lock_profile_email`. Email comes from the JWT on insert and cannot be updated by the user. There is no `004_*.sql` in the tree. |
| `006_app_sessions.sql` | `app_sessions`. No FK to `profiles` (a Google sign-in can store a session first). No policy for `authenticated`. |
| `007_plans_season_key.sql` | Deletes older duplicates, unique index `plans_season_key` on `(user_id, start_date, goal_date, "current_time", goal_time)`, trigger `touch_plan_updated_at`. |

`pace_units`, `intro_seen`, and `strava_prompt_seen` are **auth user metadata**, not profile columns (`save_pace_units` and the two siblings call `_auth_user_update`).

`public.results` is loaded by `load_bundle` and is not what Session writes. Session writes `plans.actuals`.

**SQLite** `db/schema.sql` (`ontology_versions`, `athletes`, `goals`, `workouts` with `source` `fixture` or `intervals`, `workout_steps`, `classifications`, `ledger_entries`, `prescriptions`) is a fixture loader. Leave it out of the product cutover.

**Local file accounts** (`ui/accounts.py`, path from `accounts_path()`) remain for tests and for a laptop without Supabase. Hosted identity is the cloud branch.

### 1.7 Intervals.icu versus Strava

Both exist. Neither was invented for this document.

**Strava is the hosted product path.**

- `ui/strava.py`: authorize `https://www.strava.com/oauth/authorize`, token, deauthorize, list `GET /api/v3/athlete/activities`, detail `GET /api/v3/activities/{id}`. Scope `activity:read_all`. Sports imported: `Run`, `TrailRun`, `VirtualRun`.
- Redirect is `app_url() + "/"`, so the callback lands on the Streamlit root with `code` and `state`.
- Tokens and activities: `ui/strava_store.py`, tables in `003_strava.sql`.
- UI: `ui/strava_ui.py`, prompt policy in `ui/plan_strava.py` `should_offer_strava`.
- Planned versus actual uses `engines/pace.py` `workout_times`, not a model. `complete_insight` refuses a payload whose keys or strings contain `strava` or `gps` (`_insight_has_stream`).

**Intervals.icu is still wired, as a read-only fallback and as local fixtures.**

- `adapters/intervals_icu.py`: GET one activity and GET a date range. HTTP basic auth. No POST. Raises `IntervalsIcuError` if `RIO_INTERVALS_API_KEY` is missing.
- `ui/activities.py` `sync_recent` (last 14 days, cap 40) and `sync_all` (from 1970-01-01) are what `_pull_for` calls when `strava_connected()` is false.
- `ui/last_session.py` reads `tests/fixtures/intervals/*.json` off disk. The two files there are synthetic.
- Session can still fill rep boxes from a local JSON via `quality_fill`. The stored actual field is still named `intervals`.
- `docs/architecture.md` and several page docstrings (`page_activity`, `page_session`, the module docstring) still say Intervals is the pull. The branch in `_pull_for` is the newer behavior: Strava connected means skip the Intervals GET.

Do not add a new Intervals write-back, and do not describe Intervals as the live activity system for `riotraining.streamlit.app`. Keep the adapter behind the same “only if Strava is not connected” rule, or drop the live GET in a later phase and keep the file fixtures for Last Session.

### 1.8 Insights

There is no `/insights` page and no hub.

What the athlete sees:

1. **Authored phase card on Home.** `_render_this_week` calls `phase_story()` and, when the week is thin (no actuals and Strava not connected), marks the copy thin. `_show_stored_insight()` with no session argument lists every unviewed note.
2. **Same note on Session.** `page_session` calls `_show_stored_insight(session)` for that date.
3. **Model note after a logged hard day.** `_commit_result` calls `_remember_workout_note`, which builds `workout_inputs()` (hard Tuesday/Thursday only, reduced fields, no lap stream) and `complete_insight()`. Accepted shape is `headline`, `body`, `carry_forward`, `used_result_band`. A failed check returns `None` and the authored card remains. The note is stored in `rio_workout_notes` and is gone when the Streamlit session dies.
4. **`weekly_digest`** in `engines/explain.py` is tested in `tests/test_insights.py` and is not called from `ui/`.

`page_session`'s docstring says the page does not call a model. The page function does not. `_commit_result` does, and Session's result boxes call `_commit_result`. `auto_adapt` does not call `complete_insight`. A mark that arrives from Strava or an Intervals pull through `_apply_activity_marks` does not generate the model note.

### 1.9 Explicit absences

- No goal probability function. The word is rejected or stripped.
- No readiness score. “Race readiness” is a training family (`rr_*` templates, weight 0.02), not a score.
- No coach UI despite `profiles.role` allowing `coach`. Nothing in the nav checks for coach.
- Google sign-in UI and the “check your email” screen are compile-time flags (`SHOW_GOOGLE_SIGN_IN`, `SHOW_SIGNUP_EMAIL_CONFIRM`). `google_url`, `exchange_code`, and `signup_outcome` remain.
- `public.results` is unused by the Session write path.
- SQLite is unused by the app.

---

## 2. Target architecture

### 2.1 FastAPI

```
api/
  main.py                 # app, CORS for the Next origin, no service key in logs
  deps.py                 # get_settings, get_session, get_directory, require_admin
  routers/
    auth.py
    seasons.py            # generate, get, list, marks, results
    activities.py         # strava sync + optional intervals pull
    strava.py             # connect URL, callback, disconnect
    library.py
    insights.py
    classify.py           # kept fixture tools
    admin.py
  services/
    season_flow.py        # the _commit_result / _commit_mark / auto_adapt transactions
    directory.py          # moved SupabaseDirectory methods
    strava_repo.py
    explain_budget.py     # spend cap in Postgres or a single-row lock, not a local JSON file
  domain/                 # engines/ and the pure ui modules, imported, not copied
```

Run on the existing CPython. The engines are not typed as Pydantic models today. Add request and response models at the router boundary. Do not rewrite `sequence()` to return a Pydantic object inside the engine. The dict shape is what `tests/test_season.py` locks.

**Idempotency.** `season_digest` is the current “do not write if nothing changed” key. The mark and result routes should take an `If-Match` of that digest, or a `season_generation` the client echoes. `adapt()` already returns a new dict and does not mutate the caller. The service must persist that new dict in the same request that stored the actual. Today the persist happens later, on the next `_with_plan` run, which is why a crash between reruns can show a mark that was not saved.

**Workers.** Move PKCE verifiers and the Strava OAuth nonce out of process memory. The nonce can be a short-lived row keyed by user id. The HMAC in `make_state` already binds `user_id` and nonce to `RIO_STRAVA_CLIENT_SECRET`. A missing nonce is currently allowed (`state_matches` only checks the nonce when one was passed). The API should require it.

**Explain spend.** `data/explain_spend.json` is wrong for more than one machine. Put the microdollar counter in Postgres with a row lock, same $25 cap, same “rules text wins if the call fails” behavior.

**Intervals.** One internal function `pull_activities(user)`:

- if a `strava_tokens` row exists, `import_runs` only;
- else if `RIO_INTERVALS_API_KEY` is set, `sync_recent` or `sync_all`;
- else return the stored rows.

Do not register an Intervals OAuth product. There is no Intervals OAuth in this repo. The adapter is an API key.

**SQLModel.** If a typed table layer is wanted, map the existing tables and let Supabase keep owning Auth and RLS. Do not generate a new migration that recreates `plans` without the quoted `"current_time"` column and the unique season key. The app does not apply SQL itself. Any new migration should be a file under `supabase/migrations/` that a person runs, consistent with `001`–`007`.

### 2.2 Next.js App Router

```
web/
  app/
    (public)/
      page.tsx                  # startup splash, then login
      login/page.tsx
      signup/page.tsx
      forgot/page.tsx
      reset/page.tsx
    (app)/
      layout.tsx                # nav: Home, Plan, Activity, Library, More, Admin?
      home/page.tsx
      plan/page.tsx             # ?view=calendar|week|season
      session/page.tsx          # ?date= &activity=
      activity/page.tsx
      library/page.tsx
      more/page.tsx
      past-seasons/page.tsx
      profile/page.tsx
      settings/page.tsx
      about/page.tsx
      creators/page.tsx
      admin/page.tsx
      last-session/page.tsx     # low priority, fixture tools
      next/page.tsx
      decisions/page.tsx
      ledger/page.tsx
      goal/page.tsx
    auth/callback/route.ts      # Supabase code exchange, not the Strava code
    strava/callback/route.ts    # or redirect to FastAPI; do not share a query name with auth
  lib/api.ts                    # typed fetch, credentials: 'include'
  lib/session.ts
  styles/app.css                # lift of ui/static/app.css
```

**Server components** for About, Creators, Library (menu is static YAML, cache it), and the first paint of Home and Plan from `GET /seasons`. Those pages do not need the season dict in the browser until the athlete edits.

**Client components** for:

- Start form and Generate
- Plan view switch and week mark buttons (`confirm_adapt`)
- Session rep boxes (`season_generation` becomes a `key` on the form)
- Activity refresh
- Settings destructive confirms
- Insight Got it
- Strava connect (a normal `<a href>`, which is already what `render_connect_button` does)

**Tailwind.** Use it for layout, focus, and the new nav. Keep `ui/static/app.css` as a global stylesheet until the screens match. Rewriting 3,210 lines of CSS into utilities is a visual rewrite, not a migration. `ui/theme.py` photo helpers become `next/image` sources under `web/public`, copied from `ui/static/photos/` and `ui/assets/`.

**Page map.** Match section 1.1. Do not invent an Insights hub. Home owns the phase story and the unviewed note. Session owns the note for that date. Progress stays a component inside Plan and Activity, not a route, unless someone explicitly wants `/progress` later. The kept fixture pages (Last Session, Next, Decisions, Ledger, Goal) can ship after the athlete loop. They are reachable URLs today and they are not in the More list.

**API client.** One module. Mutations send the season digest. Responses return the new plan, marks, actuals, and digest. The client replaces local state with that response. It does not reimplement `adapt()`.

### 2.3 Auth: replacing the Streamlit cookie

Today's sequence, for a hosted user:

1. `sign_in` returns Supabase tokens to the Streamlit process.
2. `open_cloud_session` puts the access token in `rio_cloud_access` and in `rio_session_token` as `cloud.{access_token}`.
3. `_publish_cookie` asks the browser to set `rio_hosted` to either `rio1.…` or the legacy JSON.
4. On the next full load, JS reads the cookie (any script on the origin can too) and the Python looks up `app_sessions` or unpacks the JSON.
5. If `load_bundle` returns 401, `refresh_session` runs once.

Replacement:

- FastAPI login calls the same `sign_in`, writes `app_sessions`, and sets `rio_hosted` as an **HttpOnly, Secure, SameSite=Lax** cookie containing only the `rio1.` id. `Max-Age` stays the remainder of 24 hours so existing `cookie_max_age` behavior holds.
- Next.js does not read the Supabase access token in client JavaScript.
- Middleware on the Next side only checks that the cookie exists and calls `GET /auth/session`. FastAPI loads the row with the service role, refreshes once if the access token is dead, and returns the user id, email, display name, and role.
- Legacy JSON cookies: one release accepts them, writes an opaque row, and re-sets the cookie. After that, reject JSON bodies. They contain refresh tokens in a JS-readable cookie.
- `localStorage` `rio.session.v1` is not needed for hosted users. Drop it. Local Fernet accounts stay a dev-only flag if tests still want `ui/accounts.py`.
- Put Strava's redirect on `/strava/callback` and Supabase's on `/auth/callback`. The `state` prefix hack in `_consume_callback` exists only because both flows return `code` to the Streamlit root.
- Google stays off until `SHOW_GOOGLE_SIGN_IN` is intentionally turned on. If it comes back, store the PKCE verifier in Postgres, not in a dict on the worker. Supabase redirect URLs in the dashboard must add the new origin. The README already lists `https://riotraining.streamlit.app` and `http://localhost:8501`.
- Admin stays `RIO_ADMIN_EMAIL` checked on the confirmed auth user, then `set_role`. The Next admin layout checks `GET /auth/session`, not a profile email the athlete could have edited before migration `005`.

Signup email confirmation is off in the UI and on in the Supabase project instructions (`Confirm email` ON). The API should keep returning the existing `SIGNUP_CONFIRM` path and the Next signup page should say to check email, which is the copy already written in `_render_confirm` and currently hidden.

### 2.4 What the client must not own

- Template choice, phase lengths, the 10 percent volume rule, and mark outcomes. Those are `sequence` and `adapt`.
- The 3 percent result band. That is `judge`.
- Classification. That is `classify`.
- Whether a Strava run matches a date. That is `match_runs` / `match_activities`.
- The insight payload. The client sends the mark and the result text. The server builds `workout_inputs` so a browser cannot add a lap stream or the word Strava and slip it to the model.

---

## 3. Migration effort

Assumes one engineer who already knows this repo, plus Cursor cloud agents for mechanical moves and tests. Days are working days, not calendar promises. Ranges are wide because `ui/streamlit_app.py` hides the transactions.

| Phase | What moves | Working days | What moves the range |
| --- | --- | --- | --- |
| 0. Freeze contracts | Keep `pytest` green. Add a few API-level tests around `sequence`, `adapt`, `judge`, `auto_adapt`, `import_runs` (fake HTTP), and `dump_record` before any router exists. | 2–3 | Almost fixed. The suite already covers the engines. |
| 1. API scaffold and engine wrap | FastAPI app, settings, season and library and classify routers, `season_flow` extracted from `_commit_result`, `_commit_mark`, `_apply_activity_marks`. No browser yet. | 6–9 | Finding every write to `season_plan` / `season_marks` / `season_actuals`. Most are in the shell, not in `engines/`. |
| 2. DB, auth, Strava | Cookie session on `app_sessions`, login/signup/reset, plan read/write through `save_bundle` / `load_bundle`, Strava callback on its own path, token table untouched, explain spend moved off the local JSON file. | 7–11 | Legacy cookie, PKCE memory, Strava `code` colliding with Supabase `code`, service-role-only token table, metadata (`pace_units`, `intro_seen`) living on the auth user rather than `profiles`. |
| 3. Next.js UI | App Router pages in section 2.2, `app.css` lifted, client state for marks and actuals, Home, Session, Plan, Activity, Settings, auth screens. Fixture pages last. | 15–25 | 6,518 lines of shell and 3,210 lines of CSS. Plan nests three pages. Session boxes remount on `season_generation`. Activity has both the board and the older charts. |
| 4. Cutover | Dual run, redirect URI updates, one forced re-login when the cookie becomes HttpOnly, Streamlit left up until the athlete loop matches. | 4–8 | Supabase dashboard redirect list, Strava app redirect list, in-flight seasons, admin hero JSON, test-season preview. |

**Sequential total: about 34–56 working days.** Overlap phase 3 layout (About, Creators, Library, login chrome) with the end of phase 1 and the result is closer to 7–10 weeks of one person, not 11. The engines do not get shorter if more agents edit `ui/streamlit_app.py` in parallel. That file is the bottleneck.

### What can stay 1:1

- `engines/season.py`, `classify.py`, `normalize.py`, `prescribe.py`, `ledger.py`, `pace.py`, and the prose guards in `explain.py`.
- The 40 YAML templates and `rio/v0.1` weights, capacities, constraints, goal.
- `auto_adapt`, `judge`, `plan_store` cleaners, `phase_story`, `workout_inputs`.
- `ui/strava.py` protocol functions, with the same injected HTTP.
- The Supabase tables and policies. No data migration if the API keeps writing `plans` jsonb.
- The Strava activity rows already stored.
- Pytest modules that import engines rather than scraping the shell.

### What is a rewrite

- Every `st.rerun` and `st.switch_page` path in section 1.4.
- Both component bridges and the non-HttpOnly cookie.
- `ui/cloud_ui.py` forms.
- `ui/strava_ui.py` widgets and the 1-second fragment. The fragment exists because a sync during the first paint blocked the shell. A POST from the client does not need that.
- HTML-in-Python cards. They become components. The CSS file can move first so the rewrite is structural.
- Text-lock tests in `tests/test_*.py` that assert on slices of `streamlit_app.py`.
- `page_progress` as a route. Do not revive it unless the Plan and Activity charts are intentionally split out.
- Local encrypted accounts on the hosted origin. Leave them for pytest.

### Suggested build order inside phase 3

1. Login, cookie, empty Home.
2. Start and a read-only Plan from a stored season.
3. Session result and week marks, with the digest.
4. Strava connect, callback, Activity.
5. Settings, Profile, Past seasons, Admin.
6. About, Creators, Library (can be earlier; they do not depend on the plan).
7. Fixture pages if anyone still opens `/last-session`.

---

## 4. Risks and friction

### 4.1 The rerun model versus a stateless API

Streamlit's transaction is "mutate the dict, rerun the script." The save is a side effect of the next `_with_plan`, not of the button handler. `persist_cloud_season` also no-ops when the digest matches, and it omits activities and notes.

Specific traps:

- **Two tabs.** Two browsers can hold two copies of `season_plan`. Both call `adapt()` from the same base and the later `save_bundle` wins. There is no row version today, only `updated_at` from the trigger and an in-memory digest. Add `If-Match` before real dual-tab use.
- **`season_quality_base` is invisible.** `auto_adapt` uses it so a second judged week does not stack adaptations on an already rewritten plan. If the API calls `auto_adapt` with `{}` on every sync, later weeks move more than once. Persist the bases next to the plan, or recompute them from the stored actuals in a documented order (the function already applies weeks from earliest to latest when bases are present).
- **`season_generation` is a widget-identity hack.** Rep boxes are keyed by generation so Streamlit forgets the old numbers. In React, key the form on `date + generation` or reset state from the server payload. Do not keep a global counter in a cookie.
- **Confirm-before-adapt** (`rio_adapt_pending`) holds the result in memory across a rerun. The API should not store a pending mark. The dialog lives in the client and the POST happens on Confirm. That removes `_hold_adapt` and its rerun.
- **`_FRESH` widget defaults.** `_fresh_value` returns `{}` once a key exists so Start does not fight the athlete's typing. React controlled inputs do this without a sentinel.

### 4.2 Marks, actuals, and the post-workout note

`_commit_result` order is: `judge`, write `season_actuals`, `adapt`, write `season_marks` and `season_plan`, **then** `complete_insight`, **then** `st.rerun`. The model call blocks the rerun. Spend and latency sit on the click.

On the new stack:

- POST the result, run `judge` and `adapt` in the request, return the plan.
- Enqueue the insight or run it after the response. The note is not allowed to fail the save. `complete_insight` already returns `None` on a bad reply.
- Store the note. Today it dies with the session, so "Got it" only matters until refresh. A `workout_notes` jsonb on the plan row, or a use of the unused `results` table, matches what the UI pretends. Either choice is new persistence, not a 1:1 copy.
- Do not call the model from `auto_adapt`. The current code does not, and the insight guard rejects Strava-shaped payloads.

### 4.3 Strava OAuth callback

- Callback URL is the site root. Supabase also uses `code` on that root. The guard is `state` starting with `strava:`. A new app that sends both to one route will log the athlete in with a Strava code or attach Strava with a Supabase code.
- `rio_strava_nonce` is session state. A Cloud rerun on another instance loses it. `state_matches` then skips the nonce check and relies on the HMAC. The HMAC is sound only while `RIO_STRAVA_CLIENT_SECRET` stays secret. Still store the nonce server-side and require it.
- Deferred sync is a `st.fragment(run_every=timedelta(seconds=1))` that counts `rio_strava_defer_passes` until a plan exists. Replace with: callback saves the token, client or a background task calls `import_runs` once `season_plan.sessions` is non-empty. `list_after` already starts at the later of last sync, season start, and 120 days.
- Rate limit is `StravaLimited`. The UI surfaces `rio_strava_notice` and does not set `rio_strava_synced`, so a later visit retries. Keep that. Do not mark the sync done on failure.
- Disconnect must delete `strava_tokens` and `strava_activities` (`SupabaseStrava`) and strip `source == "strava"` rows from the in-memory activity list (`_drop_strava_from_session`).
- Redirect URI in the Strava application settings has to change when the host changes. Until cutover, register both the Streamlit root and the new `/strava/callback`.

### 4.4 Cookie restore

- First paint often has no cookie yet, so `_boot_bridge` returns and startup may `st.stop()`. Users already live with a blank first run. HttpOnly cookies arrive on the first document request, which is simpler, but **every current session dies** when the cookie flag changes, because JavaScript will no longer be able to read the old value and the new server will not see a cookie the browser still considers a different attribute. Plan a single re-login. Do not try to read the old cookie from the Next client.
- Legacy cookies contain refresh tokens. Treat them as a secret leak window. The one-time exchange in phase 4 should be the last reader of `pack_cookie` JSON.
- 24-hour cap is from `issued_at`, not a sliding session. `refresh_session` does not extend `cookie_max_age`. Keep that unless product asks otherwise. A sliding session would be a behavior change.
- `rio_enter` plus `load_is_app_root` is why a restored login on `/` opens Home when the goal date is still ahead, and why a restored Plan URL does not. Next.js middleware should copy that leaf check rather than redirecting every authenticated hit to `/home`.

### 4.5 Other edges

- **Hosted URL preview.** `hosted_link_action` returns `same`, `open`, or `preview`. A signed-in user opening someone else's four query params must not overwrite their season. `_ensure_linked_plan` and `season_link_preview` implement that. The API should refuse `POST /seasons` that does not belong to the caller, and `GET` of a shared link should be an explicit adopt action (`rio-adopt-link` is the widget).
- **Test season.** `rio_test_preview` disables persist and pulls. If that flag is a query param on the new admin site, a missing check writes the TEST plan onto the admin's real `plans` row. Keep the skip inside the service, not only in the page.
- **Admin hero files.** `hero_config.py` writes rotation JSON on the server disk. Streamlit Cloud disk is ephemeral. Confirm where those files live before promising the editor still works. The assessment did not find a Supabase table for heroes.
- **`docs/goal.md` versus the athlete goal.** `classify()` pace bands use the file. Start and `sequence()` use the form. Moving classify behind an API without deciding which goal it reads will silently keep Chase's 1:55.0 as the classification pace. Call that out in the classify route; do not "fix" it during the port.
- **Dual account systems.** A user who exists only in the local Fernet file is not in Supabase. The hosted app is Supabase. Do not run a migration of `accounts_path()` unless someone still uses the local login in production. Tests use it heavily.
- **Shell-scanning tests** will fail as soon as pages move. Budget time to retarget them at the service, or they will block CI (`pytest -q` on every PR).
- **Service role key.** It bypasses RLS. It must stay on FastAPI. It must not ship to the Next.js browser bundle. Strava tokens are readable only with that key, which is why the Next client cannot talk to `strava_tokens` with the anon key.

### 4.6 Dual-run

Run both against the same Supabase project.

- Streamlit keeps `https://riotraining.streamlit.app` until the athlete loop (sign in, season, mark, Strava, Activity) matches.
- Next.js uses a second origin, added to Supabase redirect URLs and to the Strava app.
- Both may write `plans`. The unique key makes a double save of the same season an update, not a second row, **after** migration 007. Confirm 007 has been applied before dual-run. The README says that until it has, every save inserts a new row and readers take the newest `updated_at`.
- Do not run two explain spend files. Point both processes at one counter before both can call `complete_insight`.
- Feature flag by origin, not by a column on `profiles`, so a rollback is "send the host back to Streamlit."
- Cookie names can match (`rio_hosted`) only if the hosts differ. Same host cannot speak both the JS cookie and the HttpOnly cookie cleanly.
- Admin test-season writes real-looking rows with the service key (`write_owned_season`). Do not point the new admin at production users until `load_test_season` is checked against `caller_id`.

### 4.7 Top five

1. **Plan writes are rerun side effects, and `season_quality_base` is not stored.** A naive `POST` that calls `adapt()` or `auto_adapt()` from a partial body will double-shift later weeks or drop a mark that Streamlit only held in memory.
2. **The session cookie is JS-readable and sometimes contains the refresh token.** Replacing it with HttpOnly `rio1.` ids is the point of the auth work. It logs everyone out once, and a missed legacy parser leaves refresh tokens in the browser.
3. **Strava and Supabase share `code` on the site root, and the OAuth nonce lives in `st.session_state`.** Split the callbacks. Persist the nonce. Keep the "failed import does not stick `rio_strava_synced`" rule.
4. **The post-workout note blocks the rerun and is not persisted.** Moving `complete_insight` into the request without a store repeats today's data loss and adds model latency to every rep save. The spend file is local and will not survive two API workers.
5. **`ui/streamlit_app.py` plus `ui/static/app.css` dominate the calendar.** The engines are the small part. Parallel agents that rewrite the shell without extracting `_commit_result` and `_pull_for` first will fork the rules. Extract the transactions in phase 1, then let the UI follow.

---

## Appendix A. Boot and save, as a sequence

```
browser cookie rio_hosted
        |
        v
_boot_bridge -> restore_hosted_cookie
        |  rio1. sid -> app_sessions (service role)
        |  legacy JSON -> unpack_cookie
        v
open_cloud_session -> load_bundle
        |  profiles, goals, plans, results
        |  auth user metadata: pace_units, intro_seen, strava_prompt_seen
        v
_with_plan
        |  URL four-tuple or stored season_inputs
        |  sequence() only when the plan is missing (local) or rejected
        |  _pull_for: Strava restore, or Intervals sync_recent/sync_all
        |  auto_adapt on the pull pages
        v
page draws from session_state
        |
        v
next run: _sync_browser_store -> persist_cloud_season
        writes goals + plans (plan, marks, actuals) if digest changed
        does not write activities, quality bases, or workout notes
```

Pull pages named in `_PULL_PAGES`: `page_dashboard`, `page_plan`, `page_weekly`, `page_session`, `page_progress`, `page_activity`. `page_progress` is not routed, so that name never hits `_pull_for` through navigation. Weekly is nested inside Plan, and Plan's wrapper is `page_plan`, so opening Plan is what pulls, not a second Weekly navigation.

## Appendix B. Environment names

From `.env.example` and the readers above. Values stay out of git.

| Name | Reader |
| --- | --- |
| `RIO_SUPABASE_URL` | `ui/cloud_config.py` |
| `RIO_SUPABASE_ANON_KEY` | `ui/cloud_config.py` |
| `RIO_SUPABASE_SERVICE_ROLE_KEY` | `ui/cloud_config.py`, admin and Strava stores |
| `RIO_APP_URL` | Redirects. Default local `http://localhost:8501`, else hosted `https://riotraining.streamlit.app` when unset for email links (`auth_redirect_base`). |
| `RIO_ADMIN_EMAIL` | `ui/access.py` |
| `RIO_STRAVA_CLIENT_ID` | `ui/strava.py` |
| `RIO_STRAVA_CLIENT_SECRET` | `ui/strava.py` HMAC and token exchange |
| `RIO_INTERVALS_API_KEY`, `RIO_INTERVALS_ATHLETE_ID` | `adapters/intervals_icu.py` |
| `RIO_EXPLAIN_API_KEY`, `RIO_EXPLAIN_MODEL`, `RIO_EXPLAIN_BASE_URL`, `RIO_EXPLAIN_SPEND_PATH`, price variables | `engines/explain.py` |
| `RIO_INSIGHT_LOG_PATH` | `engines/explain.py` `_log_insight` |

## Appendix C. How this inventory was taken

- `st.session_state` string literals and `"key" in st.session_state` across `*.py`.
- Widget `key=` literals under `ui/`.
- `SEEN_KEY` in `ui/startup.py`.
- `_ACCOUNT_SESSION` tuple in `ui/streamlit_app.py` (the account-switch clear list).
- `st.rerun` and `st.query_params` call sites, mapped to the enclosing `def`.
- Migrations `001`, `002`, `003`, `005`, `006`, `007` and `supabase/migrations/README.md`.
- Public `def` lines in `engines/`, `adapters/`, `db/load.py`, and the UI modules cited above.

If a key appears only as a Streamlit widget default and is also listed in `_ACCOUNT_SESSION`, it is in section 1.2 even when no line assigns `st.session_state["that-key"]`.
