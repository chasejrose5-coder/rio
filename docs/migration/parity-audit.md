# Parity audit

Independent check of the Streamlit app against FastAPI and Next.js, on `main` at `674b637` (after #72 and #73). The checklist in `parity-checklist.md` says 188/188 done. This audit does not use that count as evidence. The inventory was read from `ui/streamlit_app.py` and the modules it draws. Both apps were then run locally against one account file, with the athlete time zone set to America/Los_Angeles. No production Supabase project was opened. The original audit fixed nothing. All four gaps are closed: reset and confirmation mail in the auth change, compact mode and template ids in the settings-effect change. The counts below include both. The Session side-by-side is finished.

## Counts

| Status | Count |
| --- | --- |
| PASS | 192 |
| GAP | 0 |
| N/A | 1 |
| Rows | 193 |

188 of those rows are the checklist items. P2 was the checklist gap; the reset mail now opens Next and that row is PASS. The other five rows are things the checklist does not name: two display effects, the signup confirmation redirect, the unrouted Progress page, and the ontology papers. Signup confirmation, compact mode, and template ids are PASS. Progress stays N/A.

## What was compared

The live Streamlit pages, widgets, gates, and copy were read from `ui/`. The Next routes under `web/app/` and the FastAPI routes under `api/` were matched to those pages. Plan generation is not reimplemented: `POST /seasons` calls `engines.season.sequence`, and the session clock calls `engines.pace.workout_times` and `average_rep_text`, which is what Streamlit's cards call.

Both apps were started with Supabase unset, `RIO_ACCOUNTS_PATH` pointed at one local file, and `RIO_ADMIN_EMAIL=admin@example.com`. The seeded athlete is in America/Los_Angeles, with easy pace 7:25 per mile, a current season (`2:08.0`, start `2026-11-08`, goal `1:59.0`, `2027-04-18`), and a past season in 2020. Today in that zone was 2026-11-10. Home on both apps showed "159 days to 1:59.0" and Tuesday's `8 × 150 m @ 23.0 s`.

Each side-by-side is two full-page screenshots placed next to each other after the fade. They are not scroll-stitched. Visible text was diffed after that. About, Creators, and the Settings sentences match once the nav chrome and a closed Streamlit expander are ignored. The hidden About and Creators paragraphs diff empty.

A new account was recorded on Next: splash, create account, easy pace, intro, Start, Generate, the Strava prompt, Home, Plan, Start session, Activity, Settings, Past seasons, About, Creators, and Log out. The video is `new-account-next.webm` on the PR.

## Checklist items this inventory adds

The checklist's 188 rows cover the screens. These behaviors are real in Streamlit and are not their own rows there:

- Compact mode is global CSS in `ui/streamlit_app.py` (`_COMPACT_CSS`). Next adds `is-compact` on Home, Plan, Session, and Activity as well as Settings, Library, Profile, More, Past seasons, About, and Creators.
- Show template ids paints the id on the Home track, the Plan day row, the Plan day card, and the Session page (`_id_html`). Next paints `rio-template-id` on the Home track and the Plan day row and day card when the setting is on, and already painted it on Session, Library, and the legacy Activity table.
- Hosted signup confirmation from the API uses `email_redirect_to` of `{RIO_FRONTEND_ORIGIN}/`. Streamlit's own sign-up still uses `auth_redirect_base() + "/"` (`ui/cloud_store.py`).
- `page_progress` is implemented and is not in `st.navigation`. Next does not add it. That is N/A.

## Gaps

All four gaps are closed.

### 1. Password reset mail still opens Streamlit

Severity: high for a hosted cutover. Closed.

Streamlit's own forgot screen still sends `redirect_to` of `auth_redirect_base() + "/?reset=password"`. That base is `RIO_APP_URL`, or the hosted Streamlit site when the variable is unset. The API's `POST /auth/forgot-password` sends `{RIO_FRONTEND_ORIGIN}/reset-password`. The local account file still sends no mail.

`/reset-password` reads the same fields Streamlit reads: `token`, `token_hash`, and `type`, from the query or the hash. Supabase's implicit redirect puts `access_token`, `refresh_token`, `token_type`, and `type=recovery` in the hash. That fragment sets the password on the recovery session. A fragment whose `type` is not `recovery` does not.

Evidence: `tests/test_auth_mail.py`; `web/e2e/reset-link.spec.ts`; `web/lib/reset-link.test.ts`; `docs/migration/parity-evidence/side/reset-password.jpg`. The side-by-side is one full-page shot of each reset form after the fade, in America/Los_Angeles. It is not stitched.

Supabase Auth redirect allow list. Add these two URLs. `RIO_FRONTEND_ORIGIN` is the exact Next origin, scheme and host, no path and no trailing slash. Do not remove the Streamlit entries while that app is still running. Jay adds them in the dashboard. This change does not.

- `{RIO_FRONTEND_ORIGIN}/reset-password`
- `{RIO_FRONTEND_ORIGIN}/`

When the variable is unset the API uses `http://localhost:3000`, so those are `http://localhost:3000/reset-password` and `http://localhost:3000/`. `{RIO_FRONTEND_ORIGIN}/**` also covers both.

### 2. Signup confirmation mail still opens Streamlit

Severity: high if email confirmation stays on and Streamlit is turned off. Closed.

Streamlit's own sign-up still sets `email_redirect_to` to `auth_redirect_base() + "/"`. The API's `POST /auth/sign-up` sets it to `{RIO_FRONTEND_ORIGIN}/`. The confirm screen itself stays hidden on both apps. No copy change.

The allow-list entry is the same `{RIO_FRONTEND_ORIGIN}/` named above. Evidence: `tests/test_auth_mail.py`.

### 3. Compact mode does not tighten Home, Plan, Session, or Activity

Severity: low. Closed.

The toggle saves on both apps. Streamlit injects `_COMPACT_CSS` on every signed-in page. Next adds `is-compact` on Home, Plan, Session, and Activity, with the same hero, card, day-card, day-row, track, and chart padding. The stored value is unchanged.

The Home aerial covers the whole page in compact and normal mode, including the next-3-days cards, the links, the credit, and the footer. The `03  /  Next 3 days` label stays on that photo.

Evidence: `web/e2e/display-prefs.spec.ts`; `docs/migration/parity-evidence/side/home.jpg`; `docs/migration/parity-evidence/side/home-compact.jpg`; `docs/migration/parity-evidence/side/plan-week-compact.jpg`; `docs/migration/parity-evidence/side/activity-compact.jpg`; `docs/migration/parity-evidence/side/session-compact.jpg`. Each pair is one full-page shot of each app after the fade, in America/Los_Angeles. They are not stitched.

### 4. Template ids stay off the Home track and the Plan cards

Severity: low. Admin only. Closed.

With Show template ids on, both apps draw `rio-template-id` on the Home track (`rio-track-id`), the Plan day row, and the Plan day card (`rio-daycard-id`). Session already showed it on Next when `show_id` is true. Library shows it. The visible Activity cards keep the id in a hidden span on both apps; the legacy table shows it when the setting is on. The id stays off when the setting is off.

Evidence: `web/e2e/display-prefs.spec.ts`; `docs/migration/parity-evidence/side/home-compact.jpg`; `docs/migration/parity-evidence/side/plan-week-compact.jpg`; `docs/migration/parity-evidence/side/plan-season-compact.jpg`.

## Schema

No SQL. This PR does not add or change a table.

The migrations in `supabase/migrations/` were applied to a local database named `rio_parity_audit` after stubbing `auth.users`, `auth.uid()`, `auth.role()`, and `auth.jwt()`. The catalog was read with `information_schema.columns`, `pg_indexes`, and `pg_trigger`. `information_schema.statistics` was not used. Production was not contacted.

Every column the hosted writers send is in that catalog: `profiles`, `goals`, `plans`, `results`, `app_sessions`, `season_state`, `strava_tokens`, `strava_activities`, `strava_oauth`, and `explain_spend`. Indexes include `plans_season_key`, `results_user_logged`, and `strava_oauth_expires_at`. Triggers include `profiles_lock_role`, `profiles_lock_email`, `plans_touch_updated_at`, `season_state_touch_updated_at`, `strava_oauth_touch_updated_at`, and `explain_spend_touch_updated_at`.

`season_state` and `strava_oauth` are API tables. Streamlit does not read them. The plan, marks, and actuals both apps store still live on `plans`. Those two migrations (009 and 010), plus 011 for the explain spend counter, still have to be applied before a hosted cutover. The app does not apply them itself. Until 009 is applied, a hosted save still writes the plan and rebuilds a missing quality base. Until 010 is applied, a hosted API connect cannot start.

The check is `tests/test_parity_schema.py`. It refuses any database whose `current_database()` is not `rio_parity_audit`, and it skips when that local database is absent, so CI does not need Postgres.

## Cutover prerequisites

No new environment name is required. These have to be set on the host before Streamlit is turned off.

| Name | What to set |
| --- | --- |
| `RIO_SUPABASE_URL`, `RIO_SUPABASE_ANON_KEY`, `RIO_SUPABASE_SERVICE_ROLE_KEY` | The same project Streamlit uses. The service role stays on the API. |
| `RIO_FRONTEND_ORIGIN` | The exact Next origin, scheme and host, no path and no wildcard. CORS allows that one origin and credentials. |
| `NEXT_PUBLIC_RIO_API_URL` | The API origin, baked into the Next build. The browser calls it with `credentials: "include"`. |
| `RIO_CALLBACK_BASE_URL` | The Next origin. Strava's redirect becomes `{base}/strava/callback` when `RIO_STRAVA_REDIRECT_URI` is unset. |
| `RIO_STRAVA_REDIRECT_URI` | Optional. A full URI here wins over the base. |
| `RIO_STRAVA_CLIENT_ID`, `RIO_STRAVA_CLIENT_SECRET` | The same Strava app. |
| `RIO_ADMIN_EMAIL` | The one address that sees Admin. Unset means nobody is admin. |
| `RIO_HERO_PATH` | A writable file for the startup photo rotation. It must survive a restart. |
| `RIO_APP_URL` | Still the Streamlit origin. Streamlit's own reset and confirmation links use it. The API mail uses `RIO_FRONTEND_ORIGIN` instead. |
| `RIO_GOOGLE_REDIRECT_URI` | Unset keeps the Streamlit callback. The Google button stays hidden on both apps. |

Strava: in the Strava app settings, register `{RIO_CALLBACK_BASE_URL}/strava/callback`. Leave the Streamlit callback registered until that app is off, then remove it. No code change picks the URI. The variable does.

Cookies: `rio_hosted` is `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, with no `Domain`. It is host-only on the API host. Lax is sent on a fetch when the page and the API are the same site. Host the API on a same-site name as the Next app (for example `api.` under the same registrable domain). A different site will not send this cookie. Do not widen it to `SameSite=None` as part of cutover unless the hosts cannot share a site.

Supabase Auth: Site URL and the redirect allow list must include the Next origin before reset or confirmation mail is pointed there. Confirm email stays on. Run migrations 009, 010, and 011 in the SQL editor if they are not already there. They are safe to run again. This audit does not run them on the hosted project.

Hosting: Next serves the public origin. The API is a separate process with the env above. `RIO_ACCOUNTS_PATH` is only for a machine with no Supabase URL. Do not ship the local account file.

## Workout math

`tests/test_parity_plan.py` generates six seasons through `POST /seasons` and compares every session to `sequence()`: week, day, date, template, reasons, target, and `ontology_version`. The Saturday long-run ids are the same list and each id is on the frozen 500 m ladder. Easy pace `7:25` per mile and `4:36` per kilometer change the continuous line to `Run at 7:25 per mile` and `Run at 4:36 per kilometer`. With no pace saved, that line is `Set your easy pace before this run.` Quality rep lines, tolerances, and the average do not change when the easy pace changes. Per km changes a continuous distance and does not change a rep clock. Today follows `America/Los_Angeles` and `Pacific/Auckland` through the same `local_today` Streamlit uses.

The plan week side-by-side shows the same lines on screen, including `8 × 150 m @ 23.0 s, 150 s rest`, `Run at 7:25 per mile`, and the long-run miles (`5.9`, `6.2`, `6.5`, then up the ladder). The dedicated Session side-by-side is `docs/migration/parity-evidence/side/session.jpg`. Both apps show Tuesday 2026-11-10, `8 × 150 m @ 23.0 s, 150 s rest`, `Average 23.0 s`, tolerance `22.8-23.2 s`, and the prep notes. The workout block sits flat on the page. It is one full-page shot of each app after the fade, in America/Los_Angeles, not stitched. `average_rep_text` is still asserted on `GET /sessions/{date}`.

## Feature table

PASS means the same thing is reachable with the same words or the same workout. GAP means something a person can see or do in Streamlit is missing or pointed at the wrong place. N/A means Streamlit does not offer it as a page.

| Feature | Evidence | Status |
| --- | --- | --- |
| S1. Splash photo and chrome | docs/migration/parity-evidence/side/splash.jpg; docs/migration/parity-evidence/text/splash.diff | PASS |
| S2. Splash words | docs/migration/parity-evidence/side/splash.jpg; docs/migration/parity-evidence/text/splash.diff | PASS |
| S3. Splash credit | docs/migration/parity-evidence/side/splash.jpg; docs/migration/parity-evidence/text/splash.diff | PASS |
| S4. Continue | docs/migration/parity-evidence/side/splash.jpg; docs/migration/parity-evidence/text/splash.diff | PASS |
| S5. Splash shows again in a new tab | docs/migration/parity-evidence/side/splash.jpg; docs/migration/parity-evidence/text/splash.diff | PASS |
| S6. Splash skipped when a season is already open | docs/migration/parity-evidence/side/splash.jpg; docs/migration/parity-evidence/text/splash.diff | PASS |
| S7. Splash contact line | docs/migration/parity-evidence/side/splash.jpg; docs/migration/parity-evidence/text/splash.diff | PASS |
| S8. Splash fade | docs/migration/parity-evidence/side/splash.jpg; docs/migration/parity-evidence/text/splash.diff | PASS |
| L1. Window title | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L2. Log in hero | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L3. Email and password | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L4. Log in button | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L5. Wrong email or password | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L6. Too many sign-in attempts | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L7. Unconfirmed email stays a mismatch | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L8. Accounts could not be reached | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L9. Create account link | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L10. Forgot password link | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L11. Floodlight photo | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L12. Local setup notice | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L13. Account file cannot be read | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| L14. Log in credit and footer | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/text/login.diff | PASS |
| N1. Create account hero | docs/migration/parity-evidence/side/create.jpg; docs/migration/parity-evidence/text/create.diff | PASS |
| N2. Name, email, password | docs/migration/parity-evidence/side/create.jpg; docs/migration/parity-evidence/text/create.diff | PASS |
| N3. What a name, email, and password must be | docs/migration/parity-evidence/side/create.jpg; docs/migration/parity-evidence/text/create.diff | PASS |
| N4. Too many sign-ups | docs/migration/parity-evidence/side/create.jpg; docs/migration/parity-evidence/text/create.diff | PASS |
| N5. Other create failures | docs/migration/parity-evidence/side/create.jpg; docs/migration/parity-evidence/text/create.diff | PASS |
| N6. Create account button and where it goes | docs/migration/parity-evidence/side/create.jpg; docs/migration/parity-evidence/text/create.diff | PASS |
| N7. Back to log in | docs/migration/parity-evidence/side/create.jpg; docs/migration/parity-evidence/text/create.diff | PASS |
| N8. Helper line | docs/migration/parity-evidence/side/create.jpg; docs/migration/parity-evidence/text/create.diff | PASS |
| N9. Create account photo, credit, footer | docs/migration/parity-evidence/side/create.jpg; docs/migration/parity-evidence/text/create.diff | PASS |
| P1. Forgot password screen | web/e2e/auth-home.spec.ts | PASS |
| P2. Reset from the link | tests/test_auth_mail.py; web/e2e/reset-link.spec.ts; docs/migration/parity-evidence/side/reset-password.jpg | PASS |
| P3. New password | web/e2e/auth-home.spec.ts | PASS |
| I1. Intro card | docs/migration/parity-evidence/side/intro.jpg; docs/migration/parity-evidence/text/intro.diff | PASS |
| I2. Step 1 | docs/migration/parity-evidence/side/intro.jpg; docs/migration/parity-evidence/text/intro.diff | PASS |
| I3. Step 2 | docs/migration/parity-evidence/side/intro.jpg; docs/migration/parity-evidence/text/intro.diff | PASS |
| I4. Step 3 | docs/migration/parity-evidence/side/intro.jpg; docs/migration/parity-evidence/text/intro.diff | PASS |
| I5. Skip and Done | docs/migration/parity-evidence/side/intro.jpg; docs/migration/parity-evidence/text/intro.diff | PASS |
| I6. When the intro appears | docs/migration/parity-evidence/side/intro.jpg; docs/migration/parity-evidence/text/intro.diff | PASS |
| E1. Easy pace card | docs/migration/parity-evidence/side/easy-pace.jpg; docs/migration/parity-evidence/text/easy-pace.diff | PASS |
| E2. Pace, unit, and save | docs/migration/parity-evidence/side/easy-pace.jpg; docs/migration/parity-evidence/text/easy-pace.diff | PASS |
| E3. Save failed | docs/migration/parity-evidence/side/easy-pace.jpg; docs/migration/parity-evidence/text/easy-pace.diff | PASS |
| E4. Gate order | docs/migration/parity-evidence/side/easy-pace.jpg; docs/migration/parity-evidence/text/easy-pace.diff | PASS |
| T1. Start photo | docs/migration/parity-evidence/side/start.jpg; docs/migration/parity-evidence/text/start.diff | PASS |
| T2. Start hero | docs/migration/parity-evidence/side/start.jpg; docs/migration/parity-evidence/text/start.diff | PASS |
| T3. Your 800 m time today | docs/migration/parity-evidence/side/start.jpg; docs/migration/parity-evidence/text/start.diff | PASS |
| T4. Start date | docs/migration/parity-evidence/side/start.jpg; docs/migration/parity-evidence/text/start.diff | PASS |
| T5. Goal 800 | docs/migration/parity-evidence/side/start.jpg; docs/migration/parity-evidence/text/start.diff | PASS |
| T6. Goal date | docs/migration/parity-evidence/side/start.jpg; docs/migration/parity-evidence/text/start.diff | PASS |
| T7. Generate season plan | docs/migration/parity-evidence/side/start.jpg; docs/migration/parity-evidence/text/start.diff | PASS |
| T8. Generate errors | docs/migration/parity-evidence/side/start.jpg; docs/migration/parity-evidence/text/start.diff | PASS |
| T9. Start credit | docs/migration/parity-evidence/side/start.jpg; docs/migration/parity-evidence/text/start.diff | PASS |
| T10. A link to a different season | docs/migration/parity-evidence/side/start.jpg; docs/migration/parity-evidence/text/start.diff | PASS |
| V1. Your plan is ready | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| V2. Connect Strava | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| V3. Not now | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H1. Home photo and credit | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H2. No season | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H3. Days to the goal | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H4. Track drawing | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H5. Four tiles | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H6. Glossary | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H7. Current phase | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H8. Today's workout or the next one | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H9. No workout left | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H10. Next 3 days | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H11. Quick links | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H12. Extra sessions | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H13. Broken season | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| H14. Home load failure | docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/text/home.diff | PASS |
| B1. Plan hero | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B2. No plan, and a bad plan | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B3. Pace status line | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B4. Phases strip | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B5. Calendar, This week, Full season | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B6. Weeks expander | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B7. Month calendar | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B8. This week | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B9. Recap | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B10. Week day cards and extras | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B11. Week mark | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B12. Full season | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B13. Plan credit | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| B14. This week activity notice | docs/migration/parity-evidence/side/plan-week.jpg; docs/migration/parity-evidence/text/plan-week.diff | PASS |
| W1. Start session | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| W2. Session with no plan, no date, or a bad date | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| W3. Session hero and workout | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| W4. Prep notes | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| W5. Pace line on the session | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| W6. Matched activity beside the template | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| W7. Watch logging | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| W8. Confirm before later weeks change | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| W9. No-watch Done | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| W10. Add a time | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| W11. Insight on the session | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| W12. An extra activity opened as a session | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| W13. Admin Intervals file on the session | tests/test_parity_plan.py; docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| Y1. Activity hero and no season | docs/migration/parity-evidence/side/activity.jpg; docs/migration/parity-evidence/text/activity.diff | PASS |
| Y2. Refresh | docs/migration/parity-evidence/side/activity.jpg; docs/migration/parity-evidence/text/activity.diff | PASS |
| Y3. Strava not connected | docs/migration/parity-evidence/side/activity.jpg; docs/migration/parity-evidence/text/activity.diff | PASS |
| Y4. Connected empty, and last synced | docs/migration/parity-evidence/side/activity.jpg; docs/migration/parity-evidence/text/activity.diff | PASS |
| Y5. This week summary | docs/migration/parity-evidence/side/activity.jpg; docs/migration/parity-evidence/text/activity.diff | PASS |
| Y6. Week groups and run cards | docs/migration/parity-evidence/side/activity.jpg; docs/migration/parity-evidence/text/activity.diff | PASS |
| Y7. Heart-rate chart | docs/migration/parity-evidence/side/activity.jpg; docs/migration/parity-evidence/text/activity.diff | PASS |
| Y8. Strava errors | docs/migration/parity-evidence/side/activity.jpg; docs/migration/parity-evidence/text/activity.diff | PASS |
| Y9. Strava in Settings | docs/migration/parity-evidence/side/activity.jpg; docs/migration/parity-evidence/text/activity.diff | PASS |
| Y10. Opening a page pulls recent runs | docs/migration/parity-evidence/side/activity.jpg; docs/migration/parity-evidence/text/activity.diff | PASS |
| Y11. Test-season line | docs/migration/parity-evidence/side/activity.jpg; docs/migration/parity-evidence/text/activity.diff | PASS |
| M1. Library hero | docs/migration/parity-evidence/side/library.jpg; docs/migration/parity-evidence/text/library.diff | PASS |
| M2. Search, family, phase | docs/migration/parity-evidence/side/library.jpg; docs/migration/parity-evidence/text/library.diff | PASS |
| M3. Count and rows | docs/migration/parity-evidence/side/library.jpg; docs/migration/parity-evidence/text/library.diff | PASS |
| R1. Easy pace on Profile | docs/migration/parity-evidence/side/profile.jpg; docs/migration/parity-evidence/text/profile.diff | PASS |
| R2. No season | docs/migration/parity-evidence/side/profile.jpg; docs/migration/parity-evidence/text/profile.diff | PASS |
| R3. The four values | docs/migration/parity-evidence/side/profile.jpg; docs/migration/parity-evidence/text/profile.diff | PASS |
| R4. Save goal time | docs/migration/parity-evidence/side/profile.jpg; docs/migration/parity-evidence/text/profile.diff | PASS |
| G1. Settings hero and notices | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| G2. Name, nickname, email, time zone | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| G3. Change password | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| G4. Logging | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| G5. Pace units, intro, start date, ids, compact, dates, confirm | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| G6. Export | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| G7. Change email | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| G8. Privacy note and version | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| G9. Danger zone | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| G10. Clear marks | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| G11. Reset plan | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| G12. Delete account | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| G13. Clear local data | docs/migration/parity-evidence/side/settings.jpg; docs/migration/parity-evidence/text/settings.diff | PASS |
| U1. Past seasons list | docs/migration/parity-evidence/side/past.jpg; docs/migration/parity-evidence/text/past.diff | PASS |
| U2. Current season has no delete | docs/migration/parity-evidence/side/past.jpg; docs/migration/parity-evidence/text/past.diff | PASS |
| U3. Delete asks with stats first | docs/migration/parity-evidence/side/past.jpg; docs/migration/parity-evidence/text/past.diff | PASS |
| O1. About hero and credit | docs/migration/parity-evidence/side/about.jpg; docs/migration/parity-evidence/text/about.diff | PASS |
| O2. Eight phases | docs/migration/parity-evidence/side/about.jpg; docs/migration/parity-evidence/text/about.diff | PASS |
| O3. 10% rule, classification, hard days | docs/migration/parity-evidence/side/about.jpg; docs/migration/parity-evidence/text/about.diff | PASS |
| O4. Creators | docs/migration/parity-evidence/side/about.jpg; docs/migration/parity-evidence/text/about.diff | PASS |
| F1. Contact footer | docs/migration/parity-evidence/side/more.jpg; docs/migration/parity-evidence/text/more.diff | PASS |
| F2. Nav | docs/migration/parity-evidence/side/more.jpg; docs/migration/parity-evidence/text/more.diff | PASS |
| F3. More subnav and page | docs/migration/parity-evidence/side/more.jpg; docs/migration/parity-evidence/text/more.diff | PASS |
| C1. Startup | docs/migration/parity-evidence/side/splash.jpg | PASS |
| C2. Log in and create account | docs/migration/parity-evidence/side/login.jpg; docs/migration/parity-evidence/side/create.jpg | PASS |
| C3. Home | docs/migration/parity-evidence/side/home.jpg | PASS |
| C4. Start | docs/migration/parity-evidence/side/start.jpg | PASS |
| C5. Plan | docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| C6. About | docs/migration/parity-evidence/side/about.jpg; docs/migration/parity-evidence/text/about.diff | PASS |
| C7. Creators | docs/migration/parity-evidence/side/creators.jpg; docs/migration/parity-evidence/text/creators.diff | PASS |
| C8. Admin hero frames | web/e2e/admin-fixtures.spec.ts | PASS |
| K1. Admin gate and hero | web/e2e/admin-fixtures.spec.ts | PASS |
| K2. Account list | web/e2e/admin-fixtures.spec.ts | PASS |
| K3. Test season | web/e2e/admin-fixtures.spec.ts | PASS |
| K4. Test preview banner | web/e2e/admin-fixtures.spec.ts | PASS |
| K5. Hero editor | web/e2e/admin-fixtures.spec.ts | PASS |
| K6. The splash does not rotate | web/e2e/admin-fixtures.spec.ts | PASS |
| K7. Fixture pages | web/e2e/admin-fixtures.spec.ts | PASS |
| Q1. Workout note | web/e2e/admin-fixtures.spec.ts; tests/test_explain.py | PASS |
| Q2. What does not get a model note | web/e2e/admin-fixtures.spec.ts; tests/test_explain.py | PASS |
| Q3. Explain prose on fixture pages | web/e2e/admin-fixtures.spec.ts; tests/test_explain.py | PASS |
| Q4. The $25 cap | web/e2e/admin-fixtures.spec.ts; tests/test_explain.py | PASS |
| Q5. A note must not carry a lap stream | web/e2e/admin-fixtures.spec.ts; tests/test_explain.py | PASS |
| X1. Generate a season on Start | tests/test_parity_plan.py | PASS |
| X2. An em dash for an empty value | tests/test_parity_plan.py | PASS |
| X3. Intervals file body | tests/test_parity_plan.py | PASS |
| X4. Account could not be opened or saved | tests/test_parity_plan.py | PASS |
| RL1. Sign-in | tests/test_api_step2b.py | PASS |
| RL2. Sign-up | tests/test_api_step2b.py | PASS |
| RL3. Strava | tests/test_api_step2b.py | PASS |
| RL4. Intervals | tests/test_api_step2b.py | PASS |
| D2. One day, then log in again | tests/test_parity_plan.py `test_timezone_decides_today_for_los_angeles_and_auckland`; web/e2e/auth-home.spec.ts | PASS |
| D3. Log out | tests/test_parity_plan.py `test_timezone_decides_today_for_los_angeles_and_auckland`; web/e2e/auth-home.spec.ts | PASS |
| D4. A deep link stays put | tests/test_parity_plan.py `test_timezone_decides_today_for_los_angeles_and_auckland`; web/e2e/auth-home.spec.ts | PASS |
| D5. Home when the goal is today or later | tests/test_parity_plan.py `test_timezone_decides_today_for_los_angeles_and_auckland`; web/e2e/auth-home.spec.ts | PASS |
| D6. Gates before the page | tests/test_parity_plan.py `test_timezone_decides_today_for_los_angeles_and_auckland`; web/e2e/auth-home.spec.ts | PASS |
| D7. Unsigned visitors | tests/test_parity_plan.py `test_timezone_decides_today_for_los_angeles_and_auckland`; web/e2e/auth-home.spec.ts | PASS |
| D1. Today | tests/test_parity_plan.py `test_timezone_decides_today_for_los_angeles_and_auckland`; web/e2e/auth-home.spec.ts | PASS |
| A1. Splash fade | web/app/globals.css; ui/startup.py | PASS |
| A2. Page fade and rise | web/app/globals.css; ui/startup.py | PASS |
| A3. Nav underline | web/app/globals.css; ui/startup.py | PASS |
| A4. Buttons and cards | web/app/globals.css; ui/startup.py | PASS |
| A5. Plan view rise | web/app/globals.css; ui/startup.py | PASS |
| A6. Reduced motion | web/app/globals.css; ui/startup.py | PASS |
| Z1. Google | web/e2e/auth-home.spec.ts; ui/cloud_ui.py `SHOW_GOOGLE_SIGN_IN` | PASS |
| Z2. Check your inbox | ui/cloud_ui.py `SHOW_SIGNUP_EMAIL_CONFIRM` | PASS |
| Z3. Synthetic and demo badges | ui/streamlit_app.py `_demo_label`; the badge is not painted | PASS |
| Z4. Settings leftovers | docs/migration/parity-evidence/text/settings.hidden.diff | PASS |
| Z5. About's long paragraphs | docs/migration/parity-evidence/text/about.hidden.diff | PASS |
| Z6. Jay Rose placeholder | docs/migration/parity-evidence/text/creators.hidden.diff | PASS |
| Z7. Legacy activity tables | web/components/ActivityView.tsx `rio-legacy-activity` | PASS |
| Z8. Planned versus actual | docs/migration/parity-evidence/side/plan-week.jpg | PASS |
| Compact mode on Home, Plan, Session, and Activity | web/e2e/display-prefs.spec.ts; docs/migration/parity-evidence/side/home.jpg; docs/migration/parity-evidence/side/home-compact.jpg; docs/migration/parity-evidence/side/plan-week-compact.jpg; docs/migration/parity-evidence/side/activity-compact.jpg; docs/migration/parity-evidence/side/session-compact.jpg | PASS |
| Template ids on the Home track and Plan cards | web/e2e/display-prefs.spec.ts; docs/migration/parity-evidence/side/home-compact.jpg; docs/migration/parity-evidence/side/plan-week-compact.jpg; docs/migration/parity-evidence/side/plan-season-compact.jpg | PASS |
| Signup confirmation redirect | tests/test_auth_mail.py; ui/cloud_store.py `email_redirect_to` | PASS |
| Progress page | ui/streamlit_app.py `page_progress` is not registered in `st.navigation` | N/A |
| Ontology papers | tests/test_parity_plan.py `test_papers_have_one_copy_and_both_apps_load_it` | PASS |
