# Parity checklist

Nothing in the live Streamlit app is optional on the way to Next.js. This file is the inventory of what a person can see or do there today. It is docs only. It does not change the app, and it does not touch production Supabase.

The inventory is the Streamlit app on `main`: `ui/streamlit_app.py`, `ui/`, `engines/`, `services/`, `ui/static/app.css`, and the photos and fonts under `ui/static/` and `ui/assets/`. The FastAPI app is not what the live site calls. Routes below are the contract a step-3 page is allowed to use.

## How to read an item

- **Sees** is one thing on screen, in the words the app uses.
- **Now** is the file and function that draw it.
- **API** is the route in `docs/migration/api-contract.md`.
  - A path with no prefix is in the contract on `main`.
  - `PR #61: METHOD /path` is only in that file on PR #61 (`cursor/next-web-scaffold-b006`). It is not on `main` until that PR merges. Do not call it from a branch that does not contain it.
  - `MISSING (static)` means neither contract has a route, and the contract says this is copy, a photo, or chrome, not an API.
  - `MISSING (data)` means the screen reads or writes something and neither contract has a route for it.
- **Step 3** is who builds it, from `docs/migration/step3-plan.md` on that same branch. PR #61 is step 3a. The nine later pages have no PR number yet.
- **Status** is `web/` on PR #61, compared with Streamlit.
  - `done` — the component shows the same thing.
  - `partial` — some of it is on screen, and **Gap** says what differs.
  - `not started` — missing, or only the line "Coming in the next step."
- **Verify** is how the PR that owns the item ticks it off. A screenshot of the real control, or a test that asserts the sentence.

`done` means the component source matches. It does not mean `npm run build` succeeds. See Gap 1.

Step 3 owners:

| Owner | What it covers |
| --- | --- |
| PR #61 (step 3a) | Sign in, create account, forgot and reset password, Home, and the shell that those pages already share (nav, footer, the Home photo). |
| 3.1 | Start, including the intro and the easy-pace step. No PR yet. |
| 3.2 | Plan. PR #64. |
| 3.3 | Start session and Session. |
| 3.4 | Activity, Last Session laps, and the Strava callback. PR #66. |
| 3.5 | Library. PR #67. |
| 3.6 | Profile and the More menu. PR #68. |
| 3.7 | Settings. PR #69. |
| 3.8 | Seasons and past seasons. PR #70. |
| 3.9 | About and Creators. Locked copy. This step does not rewrite them. |
| Unassigned | Not named in the plan: splash, admin, the test season, hero editing, fixture pages, explain prose. |

## Counts

| | |
| --- | --- |
| Total items | 188 |
| Done | 150 |
| Partial | 19 |
| Not started | 19 |
| API line starts with `MISSING` | 46 |
| of which `MISSING (static)` | 46 |
| of which `MISSING (data)` | 0 |

No data row is still missing. W13 reads WORK times from `GET /fixtures/intervals/{name}`, and X3 reads the lap table from the same response. The 46 static rows are copy, photos, or chrome. A few of those also name a route for the part that is stored (the intro flag, the confirm-adapt setting, sign-out). Photo credits are listed on the screen and again under Photo credits, so those rows are in the total twice on purpose.

## PR #61 gaps

These are the differences that matter for "nothing is lost." Item rows below repeat the ones that belong to a screen.

1. **Gap 1. Closed.** The API client is in `web/lib/` (`api.ts`, `auth.tsx`, `landing.ts`, `types.ts`). The second commit of #61 put it in the tree. This step re-ran lint, typecheck, the Playwright suite, and `npm run build`.
2. **Gap 2. Closed.** A new account stops on easy pace, then the intro, then Start. `Gate` reads `easy_pace` and `intro_seen`. The walk is `web/e2e/start.spec.ts` ("a brand-new local account") and `web/e2e/auth-home.spec.ts`.
3. **Gap 3. The splash is in.** `Splash` and `Gate` draw the track photo and Continue. Continue opens Log in. The seen flag is `sessionStorage` key `rio_startup_seen`. The URL does not gain `skip=1` (S4).
4. **Gap 4. Closed.** Start is the four-field form on `start_line.jpg` (`/photos/start.jpg`), with the Bohdan Hyrovych credit. Generate calls `POST /seasons`.
5. **Gap 5. Closed.** Generate opens `/home` with the four inputs and `just_generated=true`. Home asks `GET /home?just_generated=true` and draws the Strava card from `strava_offer`.
6. **Gap 6. Home's remaining hole is a broken plan.** Rest day, "03 / Open", extra sessions, and the no-watch Done controls are in `HomeView` and covered by `web/e2e/auth-home.spec.ts`. A stored plan `sequence()` would reject still has no "—" state (H13).
7. **Gap 7. Create-account helper copy.** The web always shows "First name is enough. At least 8 characters." Local Streamlit adds "Saved on this machine." Hosted Streamlit shows no helper line.
8. **Gap 8. Local log-in notice.** When Supabase is not configured, Streamlit still shows the form and the card "Accounts aren't set up yet" / "Sign-in will open here after accounts are connected." The web form does not show that card.
9. **Gap 9. Window title.** Streamlit is "RIO · Runner Intelligence Owned" with a runner icon. The web layout title is "RIO" and the description is "Runner Intelligence Owned".
10. **Gap 10. Closed.** Start session opens `GET /auth/me` `next_session`: the next planned day, or the last day when the season is over. Today is the Settings time zone. `tests/test_api_step3_session.py` `test_next_session_day_is_today_or_the_last_day` and `test_session_uses_easy_pace_and_states_the_rep_and_the_average`. The web check is `web/e2e/auth-home.spec.ts` ("start session opens the next planned day").
11. **Gap 11. The Admin tab never appears.** `Nav` shows Admin when `athlete.role === "admin"`. Sign-in still stores `role: "athlete"` (`api/identity.py`). Admin is the email in `RIO_ADMIN_EMAIL` (`ui/access.py` `viewer_is_admin`). The Admin page is also `ComingSoon`.
12. **Gap 12. Forgot password is gated on the wrong-shaped check, and the URL is always there.** The link shows when `GET /auth/google` returns 200 and hides on 503. That lines up with hosted versus the local file, which is what the plan asks. Opening `/forgot-password` directly still draws the form. On the local file the API returns 400 because that file has no mail. Streamlit has no forgot screen at all in local mode.
13. **Gap 13. Landing is unreadable in the commit, and create-account is untested.** `Gate` calls `landingPath` from the missing `web/lib/landing.ts`. The e2e only checks sign-in: current season → `/home`, no season → `/start`. `GET /seasons/current` already 404s when every goal date is before today (`api/season_service.py` `open_season`), so that split can match Streamlit if `landingPath` sends 404 to `/start` and 200 to `/home`. The test never uses a goal date of today, and it never walks intro or easy pace.
14. **Gap 14. Empty fields use the browser, not RIO's sentence.** Login and create mark the inputs `required`. An empty submit can stop on the browser bubble. Streamlit submits and shows "Enter a name.", "Enter an email address.", or "Use at least 8 characters."
15. **Gap 15. Later pages are still placeholders.** Admin still says "Coming in the next step." About and Creators are the step 3.9 pages. Past seasons is the step 3.8 page. Profile is the step 3.6 page, and More is its menu. Library is the step 3.5 page. Activity and Last Session are the step 3.4 pages. Settings is the step 3.7 page. Plan is step 3.2. Session is step 3.3.
16. **Gap 16. Motion.** Home staggers its blocks by 200ms (`web/app/globals.css` `.rio-stagger`). The splash fade, the nav underline that does not replay on the same page, and the hold that skips a same-page rerun are not there.

## Routes main still calls "not built"

PR #61's copy of `docs/migration/api-contract.md` adds these. They are not on `main`. Items that need them say `PR #61:` so a page is not built against a route this branch does not have.

- `POST /auth/sign-up`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `POST /auth/password`
- `POST /auth/email`
- `POST /auth/delete`
- `GET /auth/google`
- `GET /auth/google/callback`
- `POST /seasons/reset`
- `PUT /profile/goal`
- `If-Match` on a season write, answered `412` when the digest is stale
- `GET /admin/accounts`
- `POST /admin/test-season`
- `GET /admin/test-season`
- `DELETE /admin/test-season`
- `GET /admin/hero`
- `PUT /admin/hero`
- `GET /fixtures`
- `POST /fixtures/classify`
- `POST /fixtures/prescribe`
- `POST /fixtures/accept`
- `GET /fixtures/ledger`
- `GET /fixtures/goal`

`POST /insights/explain` is already on `main`. The shared spend counter (migration 011) is not a screen route.

## Missing routes

`MISSING (static)` — the contract says these are not API routes. The page still has to ship the pixels.

- Startup splash, Continue, and the once-per-session flag (S1–S8)
- Window title (L1)
- Local "accounts aren't set up" card (L12)
- Intro card (I1–I6)
- Easy-pace card copy (E1–E2)
- Start photo and credit (T1, C4)
- Home glossary (H8)
- Home "Rest day" is a display string; the day list itself is `GET /home` (H12 is partial, not a missing route)
- Plan, Activity, Library, More, About, and Creators photos and blurbs that are not data (C5–C8, F1, M1)
- Footer line (F1)
- Confirm-adapt dialog chrome (W8). The setting is `PATCH /settings`. The mark is the existing POST.
- Clear-this-browser checkbox (Settings G13). Sign-out is `POST /auth/sign-out`.
- Hidden copy that must stay hidden (Z1–Z7)
- Motion (A1–A6)

X3 is closed. `GET /fixtures/intervals/{name}` returns the lap table (`distance_m`, `seconds`, `rest_s`) and the WORK elapsed times. `GET /fixtures/session` is the YAML fixture. A normal account is `403`.

---

## Startup splash

Shown once per browser session until Continue, unless this session already holds a season with sessions, or the URL has `skip=1`. `ui/streamlit_app.py` runs `_boot_bridge`, then the splash, then `_restore_session`.

### S1. Splash photo and chrome

**Sees:** A full-viewport track photo and a dark shade. The Streamlit header, toolbar, sidebar, and decoration are hidden.
**Now:** `ui/startup.py` `render_startup`, `_layout_css`
**API:** MISSING (static)
**Step 3:** Unassigned. Not in the plan, and not in PR #61.
**Status:** done
**Verify:** New session, signed out. Screenshot before Continue. No app header.

### S2. Splash words

**Sees:** "RIO", "Runner Intelligence Owned", "Your Race, Your Plan, Your Result", "Every rep has a reason", then the quote "Most plans tell you what to run. RIO shows you why, and adjusts when the season doesn't go to script." and "— Chase Rose, Founder".
**Now:** `ui/startup.py` `_HTML` (the `HEADLINE` and `CREATOR_STATEMENT` constants are not what is drawn)
**API:** MISSING (static)
**Step 3:** Unassigned
**Status:** done
**Verify:** Screenshot the splash copy, including the quote and the attribution.

### S3. Splash credit

**Sees:** "Photo by Giant Asparagus on Pexels".
**Now:** `ui/startup.py` `PHOTO_CREDIT`
**API:** MISSING (static)
**Step 3:** Unassigned
**Status:** done
**Verify:** The credit is readable on the photo. See also C1.

### S4. Continue

**Sees:** A primary button, "Continue".
**Now:** `ui/startup.py` `render_startup` (`CONTINUE_LABEL`)
**API:** MISSING (static)
**Step 3:** Unassigned
**Status:** partial
**Gap:** Continue opens Log in. The seen flag is `sessionStorage` `rio_startup_seen`. The URL does not gain `skip=1`.
**Verify:** Click Continue. The next screen is Log in, and the URL gains `skip=1`.

### S5. Splash shows again in a new tab

**Sees:** A new browser tab shows the splash again until Continue is pressed in that session.
**Now:** `ui/startup.py` `startup_pending` (`SEEN_KEY` is `rio_startup_seen`)
**API:** MISSING (static)
**Step 3:** Unassigned
**Status:** done
**Verify:** Continue, then open a second tab. The splash is back.

### S6. Splash skipped when a season is already open

**Sees:** No splash, when this session already has a saved plan that has sessions.
**Now:** `ui/streamlit_app.py` around the `startup_pending` check, `_has_current_season`
**API:** `GET /seasons/current` (the skip itself is not a route)
**Step 3:** Unassigned
**Status:** done
**Verify:** Sign in with a current season, reload in the same session. Land on the app, not the splash.

### S7. Splash contact line

**Sees:** "Questions or feedback? Email chasejrose5@gmail.com", with a mailto link, fixed over the photo.
**Now:** `ui/streamlit_app.py` `_contact_footer`
**API:** MISSING (static)
**Step 3:** Unassigned
**Status:** done
**Verify:** The address is on the splash, in light type on the photo.

### S8. Splash fade

**Sees:** The splash copy fades in, about 220ms, after a short delay.
**Now:** `ui/startup.py` splash CSS and `_SETTLE_JS`
**API:** MISSING (static)
**Step 3:** Unassigned
**Status:** done
**Verify:** Record the first paint. Copy eases in. With "reduce motion" on, it does not travel. See A1.

---

## Log in

Hosted (Supabase configured) uses `ui/cloud_ui.py`. Otherwise the form in `ui/streamlit_app.py` `_render_login` talks to the account file. Both sit on the floodlight photo. Unsigned visitors never see the nav. `st.stop()` after the form.

### L1. Window title

**Sees:** The browser title "RIO · Runner Intelligence Owned" and a runner icon.
**Now:** `ui/streamlit_app.py` `st.set_page_config`
**API:** MISSING (static)
**Step 3:** PR #61
**Status:** partial
**Gap:** `web/app/layout.tsx` sets title "RIO" and description "Runner Intelligence Owned". No icon. Gap 9.
**Verify:** Compare the tab title with Streamlit.

### L2. Log in hero

**Sees:** Banner "RIO", heading "Log in", subtitle "Use your email and password."
**Now:** `ui/cloud_ui.py` `_render_sign_in`; local: `_render_login`
**API:** none for the words. Sign-in is `POST /auth/sign-in`.
**Step 3:** PR #61
**Status:** done
**Verify:** Open `/sign-in`. Heading, banner, and subtitle match. e2e "local sign-in hides forgot password and Google" already checks the heading.

### L3. Email and password

**Sees:** "Email" and "Password". Password is masked. Autocomplete is `email` and `current-password`.
**Now:** `_render_sign_in`, `_render_login`
**API:** `POST /auth/sign-in` body `{email, password}`
**Step 3:** PR #61
**Status:** done
**Verify:** Both fields are labeled. The password is not visible.

### L4. Log in button

**Sees:** Primary "Log in", full width. Success opens the app (Home or Start, then the gates).
**Now:** `_render_sign_in` then `open_cloud_session`; local `_enter_account`
**API:** `POST /auth/sign-in` sets the `rio_hosted` cookie. `401` `{"detail": "Sign in again."}` when a later call has no cookie. Wrong password is `401`.
**Step 3:** PR #61
**Status:** done
**Gap:** Where they land is Gap 2 and Gap 13, not this button. The button itself signs in and goes to `/`.
**Verify:** Sign in with a known account. The cookie is set. A wrong password stays on Log in.

### L5. Wrong email or password

**Sees:** "Email or password does not match."
**Now:** `ui/cloud_store.py` `SIGNIN_MISMATCH`; local `_render_login`
**API:** `POST /auth/sign-in` `401`, same sentence in `detail`
**Step 3:** PR #61
**Status:** done
**Verify:** Submit a bad password. The red `.rio-error` line is that sentence.

### L6. Too many sign-in attempts

**Sees:** "Too many sign-in attempts. Wait a few minutes and try again."
**Now:** `ui/cloud_store.py` `SIGNIN_RATE`
**API:** `POST /auth/sign-in` `429` (PR #61's contract also names sign-in rate limit; main's contract text says 429 is the Strava limit)
**Step 3:** PR #61
**Status:** done
**Verify:** Force a 429 body with that sentence. It is shown as-is, not rewritten.

### L7. Unconfirmed email stays a mismatch

**Sees:** On Log in, an unconfirmed account shows "Email or password does not match.", not "Check your email to confirm your account, then log in."
**Now:** `ui/cloud_ui.py` `_visible_auth_error` (`SHOW_SIGNUP_EMAIL_CONFIRM` is false)
**API:** `POST /auth/sign-in`
**Step 3:** PR #61
**Status:** done
**Verify:** The confirm sentence is not on the log-in screen. See Z2.

### L8. Accounts could not be reached

**Sees:** "Accounts aren't set up yet. Try again in a minute." or "Accounts could not be reached." when the directory is missing.
**Now:** `ui/cloud_store.py` `ACCOUNTS_UNAVAILABLE`; `ui/cloud_ui.py` `_directory_or_notice`
**API:** `POST /auth/sign-in` when the directory is down
**Step 3:** PR #61
**Status:** done
**Verify:** With the API returning that `detail`, the sentence is on the card.

### L9. Create account link

**Sees:** "Create account", full width, under the form.
**Now:** `_render_sign_in`, `_render_login`
**API:** none
**Step 3:** PR #61
**Status:** done
**Verify:** The link opens `/create-account`. It does not submit the log-in form.

### L10. Forgot password link

**Sees:** "Forgot password?" on a hosted log-in only. The local account file has no such control.
**Now:** `ui/cloud_ui.py` `_render_sign_in`. Local `_render_login` does not draw it.
**API:** The link is not a route. The screen it opens is `PR #61: POST /auth/forgot-password`.
**Step 3:** PR #61
**Status:** partial
**Gap:** The web shows the link when `GET /auth/google` is 200 and hides it on 503. That matches hosted versus local. Gap 12: `/forgot-password` still exists as a URL. Google itself stays hidden (Z1).
**Verify:** Local API: no "Forgot password?" link. Hosted API: the link is there, and no control says Google. The e2e covers both.

### L11. Floodlight photo

**Sees:** The log-in photo full bleed, with a dark shade, and the form on a light card.
**Now:** `ui/streamlit_app.py` `_auth_backdrop` (`theme.LOGIN_PHOTO`)
**API:** MISSING (static)
**Step 3:** PR #61
**Status:** done
**Verify:** `/sign-in` uses `login.jpg`, and a narrow window uses `login-800.jpg` (`web/app/globals.css` `.auth-screen`).

### L12. Local setup notice

**Sees:** On the local (no Supabase) log-in only: "Accounts aren't set up yet" and "Sign-in will open here after accounts are connected." The form still works.
**Now:** `ui/cloud_config.py` `setup_notice_html`, called from `_render_login`
**API:** MISSING (static)
**Step 3:** PR #61
**Status:** not started
**Gap:** Gap 8. The web never draws this card.
**Verify:** Run against the local account file. The card is above the form, and a real local login still succeeds.

### L13. Account file cannot be read

**Sees:** "Accounts could not be read."
**Now:** `ui/accounts.py` `authenticate` / the read path
**API:** `POST /auth/sign-in` `detail`
**Step 3:** PR #61
**Status:** done
**Verify:** A corrupt account file surfaces that sentence, not a stack trace.

### L14. Log in credit and footer

**Sees:** "Photo by Steve Pancrate on Pexels", then "Questions or feedback? Email chasejrose5@gmail.com".
**Now:** `theme.LOGIN_CREDIT`; `_contact_footer`
**API:** MISSING (static)
**Step 3:** PR #61
**Status:** done
**Verify:** Both lines are on `/sign-in`. The e2e checks the credit. Same chrome on create, forgot, and reset (`AuthScreen` `AuthFrame`).

---

## Create account

Its own screen. Back returns to Log in. Success signs the person in.

### N1. Create account hero

**Sees:** Banner "RIO" and heading "Create account". No subtitle.
**Now:** `ui/cloud_ui.py` `_render_sign_up`; local `_render_create_account`
**API:** `PR #61: POST /auth/sign-up`
**Step 3:** PR #61
**Status:** done
**Verify:** `/create-account` heading is "Create account" and there is no "Use your email and password."

### N2. Name, email, password

**Sees:** "Name", "Email", "Password" (masked, `new-password`).
**Now:** `_render_sign_up`, `_render_create_account`
**API:** `PR #61: POST /auth/sign-up` body `{email, password, name}`
**Step 3:** PR #61
**Status:** done
**Verify:** Three labeled fields. Password is hidden.

### N3. What a name, email, and password must be

**Sees:** "Enter a name." "Enter an email address." "Use at least 8 characters." "An account with that email already exists."
**Now:** `ui/accounts.py` `normalize_name`, `normalize_email`, `password_ok` (name up to 40 characters and must contain a letter; email up to 254, one `@`, no `..`; password 8–128 and no control characters). Cloud strings in `ui/cloud_store.py`.
**API:** `PR #61: POST /auth/sign-up` `400` for a bad name, email, short password, or an email that already exists. `429` is N4.
**Step 3:** PR #61
**Status:** partial
**Gap:** Gap 14. The web relies on `required` and on `detail`. An empty field can stop in the browser before "Enter a name."
**Verify:** Submit "x" as a password and see "Use at least 8 characters." Submit a duplicate email and see the exists sentence. Submit a blank name and see "Enter a name.", not only a browser bubble.

### N4. Too many sign-ups

**Sees:** "Too many sign-up attempts. Wait a few minutes and try again."
**Now:** `ui/cloud_store.py` `SIGNUP_RATE`
**API:** `PR #61: POST /auth/sign-up` `429`
**Step 3:** PR #61
**Status:** done
**Verify:** A 429 with that `detail` is shown unchanged.

### N5. Other create failures

**Sees:** "New accounts are turned off right now." "The account could not be created." "Your account was created, but the profile could not be saved. Log in and try again."
**Now:** `ui/cloud_store.py` `SIGNUP_DISABLED`, `SIGNUP_FAILED`, `SIGNUP_PROFILE`
**API:** `PR #61: POST /auth/sign-up`
**Step 3:** PR #61
**Status:** done
**Verify:** Each `detail` renders in `.rio-error`. A `confirm: true` body becomes "The account could not be created." (Z2), which is what Streamlit does while the inbox screen is hidden.

### N6. Create account button and where it goes

**Sees:** Primary "Create account". On success the person is signed in.
**Now:** `_render_sign_up` `open_cloud_session`; local `_enter_account` sets `rio_enter`
**API:** `PR #61: POST /auth/sign-up` sets the cookie when `confirm` is false
**Step 3:** PR #61 for the button. The next screens are 3.1.
**Status:** partial
**Gap:** Gap 2. Streamlit then shows easy pace, then the intro, then Start (no season). The web replaces to `/` and `Gate` opens the Start placeholder. Intro and easy pace never run.
**Verify:** Create a new local account. The next screen is easy pace, not Start and not Home. After a valid pace, the intro is next. After Skip or Done, Start is next. Screenshot all three.

### N7. Back to log in

**Sees:** "Back to log in".
**Now:** `_render_sign_up`, `_render_create_account`
**API:** none
**Step 3:** PR #61
**Status:** done
**Verify:** The control returns to `/sign-in` and does not create the account.

### N8. Helper line

**Sees:** On the local screen only: "First name is enough. At least 8 characters. Saved on this machine." The hosted screen has no helper line.
**Now:** `_render_create_account`. Hosted `_render_sign_up` does not print it.
**API:** none
**Step 3:** PR #61
**Status:** partial
**Gap:** Gap 7. The web always shows "First name is enough. At least 8 characters." and drops "Saved on this machine."
**Verify:** Local create shows the machine sentence. Hosted create shows no helper.

### N9. Create account photo, credit, footer

**Sees:** The same floodlight photo, "Photo by Steve Pancrate on Pexels", and the contact line.
**Now:** `_auth_backdrop`, `theme.LOGIN_CREDIT`, `_contact_footer`
**API:** MISSING (static)
**Step 3:** PR #61
**Status:** done
**Verify:** `/create-account` matches log-in chrome. The e2e checks the credit.

---

## Forgot or reset password

Hosted only. The local account file has no mail and no forgot screen. Google stays hidden (Z1).

### P1. Forgot password screen

**Sees:** "Forgot password", banner "RIO", subtitle "We will email you a reset link.", an Email field, primary "Send reset email", and "Back to log in".
**Now:** `ui/cloud_ui.py` `_render_forgot`
**API:** `PR #61: POST /auth/forgot-password`. `400` when this process is the local file, the text is not an email, or the mail could not be sent ("The reset email could not be sent.").
**Step 3:** PR #61
**Status:** partial
**Gap:** Gap 12. The screen matches, including the photo credit from `AuthFrame`. It is reachable by URL even when the log-in link is hidden.
**Verify:** From hosted log-in, open Forgot. Submit an address. Land back on Log in with "Check your email for the reset link." An unknown address gets the same sentence (the token is not in the JSON). On the local file, the log-in page has no link.

### P2. Reset from the link

**Sees:** The reset screen when the URL carries `reset=password` or `type=recovery`, using `token_hash` or `token`.
**Now:** `ui/cloud_ui.py` `_consume_callback`, `_render_reset`
**API:** `PR #61: POST /auth/reset-password` body `{token, password}`
**Step 3:** PR #61
**Status:** done
**Verify:** Open `/reset-password?token_hash=…`. The heading is "New password".

### P3. New password

**Sees:** "New password" (masked) and primary "Save password". Shorter than 8 characters: "Use at least 8 characters." A bad or used link: "That reset link is no longer valid."
**Now:** `_render_reset`
**API:** `PR #61: POST /auth/reset-password` `400`
**Step 3:** PR #61
**Status:** partial
**Gap:** Gap 14 for the short-password bubble versus the RIO sentence. A missing token shows "That reset link is no longer valid." and disables Save (`ResetScreen`). That part matches.
**Verify:** Empty token, short password, and a good token. Success returns to Log in with "Password updated. Log in with the new one."

---

## Intro after the first sign-in

Three steps. Skip and Done do the same thing: mark the intro seen. It runs after easy pace and before the page, inside `_with_plan`. The nav is on screen, with Home drawn as the active tab, but the page underneath does not render.

### I1. Intro card

**Sees:** Kicker "Welcome", heading "Start here", then three numbered steps.
**Now:** `ui/intro.py` `guide_html`, `STEPS`
**API:** MISSING (static) for the words. The flag is `PATCH /settings` field `intro_seen`.
**Step 3:** 3.1
**Status:** done
**Verify:** New account, after easy pace. Screenshot the card. No model, no plan.

### I2. Step 1

**Sees:** "1" "Set your goal" "On Start, enter your 800 m times and choose Generate season plan."
**Now:** `ui/intro.py` `STEPS`
**API:** MISSING (static)
**Step 3:** 3.1
**Status:** done
**Verify:** The first step's title and sentence match, including "Generate season plan".

### I3. Step 2

**Sees:** "2" "Connect Strava" "In Settings, connect Strava so your runs show up."
**Now:** `ui/intro.py` `STEPS`
**API:** MISSING (static)
**Step 3:** 3.1
**Status:** done
**Verify:** Second step copy matches.

### I4. Step 3

**Sees:** "3" "Check your plan" "Open Plan each day and mark how it went."
**Now:** `ui/intro.py` `STEPS`
**API:** MISSING (static)
**Step 3:** 3.1
**Status:** done
**Verify:** Third step copy matches.

### I5. Skip and Done

**Sees:** "Skip" and primary "Done". Either one leaves the guide.
**Now:** `ui/intro.py` `render_intro`; `ui/streamlit_app.py` `_intro_gate`, `_store_intro`
**API:** `PATCH /settings` `{intro_seen: true}`
**Step 3:** 3.1
**Status:** done
**Verify:** Each button, on its own new account, dismisses the guide and does not show it again on reload.

### I6. When the intro appears

**Sees:** The guide for an account that has not stored `intro_seen`, unless a current season already exists (that account is marked seen and the guide is skipped). Settings "Show intro guide" shows it again. A failed save says "The intro guide could not be saved. It will show again next time."
**Now:** `_intro_due`, `_store_intro`
**API:** `GET /auth/me` `prefs.intro_seen` (`true`, `false`, or `null`). Write with `PATCH /settings`.
**Step 3:** 3.1. The Settings button is 3.7 (Settings G5).
**Status:** done
**Verify:** New account: guide shows. Account with a current season: guide does not. After "Show intro guide": it shows once more. The button itself is G5. `intro_seen: false` shows the guide again, including when a season exists.

---

## Easy-pace screen

The first stop once an account exists and no easy pace is saved. It is before the intro. Profile uses the same form later (R1).

### E1. Easy pace card

**Sees:** Kicker "Start here", heading "Your easy pace", and "Easy and long runs use this pace. Enter minutes and seconds, like 7:25, and choose per mile or per kilometer. Quality workouts stay on your 800."
**Now:** `ui/easy_pace.py` `_card`, `render_easy_pace`
**API:** MISSING (static) for the words
**Step 3:** 3.1
**Status:** done
**Verify:** New account, first screen after sign-in, before the intro. Screenshot the card.

### E2. Pace, unit, and save

**Sees:** "Easy pace" with placeholder "7:25", hint "Minutes and seconds, like 7:25.", radio "Unit" as "per mile" or "per kilometer", and primary "Save easy pace".
**Now:** `ui/easy_pace.py` `render_easy_pace`. Range is 1:00 through 30:00 via `engines/pace.py` `canonical_easy_pace`.
**API:** `PATCH /settings` with both `easy_pace` and `easy_pace_unit`. A bad pace does not replace a pace already saved.
**Step 3:** 3.1
**Status:** done
**Verify:** "7:25" and per mile saves and leaves the screen. "abc" shows "Enter a pace like 7:25." and stays.

### E3. Save failed

**Sees:** "Easy pace could not be saved." The screen stays up.
**Now:** `ui/streamlit_app.py` `_store_easy_pace`
**API:** `PATCH /settings` error `detail`
**Step 3:** 3.1
**Status:** done
**Verify:** When the write fails, the sentence is shown and the next screen does not open. The screen uses the API `detail`, and "Easy pace could not be saved." when the failure is not an `ApiError`.

### E4. Gate order

**Sees:** Easy pace first, then the intro, then Start (new account) or Home (a season whose goal date is today or later). The nav is visible during the gate, with Home styled active. A test-season preview skips both gates.
**Now:** `_with_plan`, `_easy_pace_gate`, `_intro_gate`
**API:** `GET /auth/me` for `prefs.easy_pace`. Landing uses `GET /seasons/current` (404 means Start).
**Step 3:** 3.1
**Status:** done
**Verify:** Brand-new account: easy pace, then intro, then Start. Do not open Home first.

---

## Start

Four fields. Generate calls `engines/season.py` `sequence` and opens Home. The nav is on the page. The "SYNTHETIC / DEMO" banner passed into the hero is not shown (`_demo_label`).

### T1. Start photo

**Sees:** Full-bleed start-line photo and a dark shade.
**Now:** `page_start`; `theme.START_PHOTO`, `shade_html`
**API:** MISSING (static)
**Step 3:** 3.1
**Status:** done
**Verify:** Screenshot Start. The photo is `start_line.jpg`, not the Home aerial.

### T2. Start hero

**Sees:** Heading "Start" and "Your 800 m time today, the day you start, the time you want, and the race date."
**Now:** `page_start`, `_page_hero`
**API:** none
**Step 3:** 3.1
**Status:** done
**Verify:** Heading and subtitle match. No "SYNTHETIC / DEMO" badge.

### T3. Your 800 m time today

**Sees:** Label "Your 800 m time today", placeholder "2:05.0", help "Your best recent 800 metres, as minutes:seconds.tenths. A rough guess is fine." The box starts empty.
**Now:** `page_start`; defaults `ui/start_form.py` `start_form_defaults`
**API:** The value is `inputs.current_time` on `POST /seasons`
**Step 3:** 3.1
**Status:** done
**Verify:** Empty on first open. Help text matches. Placeholder is 2:05.0.

### T4. Start date

**Sees:** "Start date", help "The day this season starts." Default is today in the Settings time zone, or the next Sunday when that preference is on.
**Now:** `page_start`; `ui/settings.py` `start_on`
**API:** `inputs.start_date` on `POST /seasons`. The preference is `PATCH /settings` `start_date` (`today` or `sunday`).
**Step 3:** 3.1
**Status:** done
**Verify:** Default is today. With "Next Sunday" saved, the default is that Sunday. Today follows the time zone (item D1).

### T5. Goal 800

**Sees:** "800 m time you're aiming for", placeholder "1:58.0", help "The race time you want on your goal date. Same minutes:seconds.tenths format." Starts empty.
**Now:** `page_start`
**API:** `inputs.goal_time` on `POST /seasons`
**Step 3:** 3.1
**Status:** done
**Verify:** Placeholder 1:58.0. The box is empty until typed.

### T6. Goal date

**Sees:** "Goal date", help "The day of the race." Default is five calendar months after today. A shorter month keeps its last day.
**Now:** `page_start`; `start_form_defaults`
**API:** `inputs.goal_date` on `POST /seasons`
**Step 3:** 3.1
**Status:** done
**Verify:** On 31 March the default is 31 August, not 31 September. On 31 January it is 30 June.

### T7. Generate season plan

**Sees:** Primary "Generate season plan". Success opens Home with the season in the URL and arms the Strava card.
**Now:** `page_start`, `_generate_season`, `_arm_strava_prompt`
**API:** `POST /seasons`. `200` is the season plus `committed: true` and `strava_offer`. `400` when an input is unusable. A plan that contains `probability` or `readiness_score` is rejected.
**Step 3:** 3.1
**Status:** done
**Verify:** Valid times open Home, not a second Start. The Strava card is the next item. No score and no probability anywhere.

### T8. Generate errors

**Sees:** The sentence from `sequence()`, in red, and the form stays. The ones a person hits: "current_time is not an 800 time", "goal_time is not an 800 time", "goal_date is before start_date", "start_date is not a calendar date", "goal_date is not a calendar date".
**Now:** `page_start`; `engines/season.py`
**API:** `POST /seasons` `400` `detail`
**Step 3:** 3.1
**Status:** done
**Verify:** One screenshot per sentence. The plan is not stored.

### T9. Start credit

**Sees:** "Photo by Bohdan Hyrovych on Pexels".
**Now:** `page_start`; `theme.START_CREDIT`
**API:** MISSING (static)
**Step 3:** 3.1
**Status:** done
**Verify:** Credit sits on the photo. See C4.

### T10. A link to a different season

**Sees:** "This link names a different season. Your saved season was left as it is." and "Use this season". A save failure is the red `rio_save_error`.
**Now:** `_link_preview_note`, `_ensure_linked_plan`
**API:** `POST /seasons` for the four inputs in the link. Marks for those inputs come back on `GET /seasons/current`.
**Step 3:** 3.1
**Status:** done
**Verify:** Open a URL whose four inputs are not the saved season. The saved season stays until "Use this season".

---

## Strava prompt

After a successful Generate, once, if Strava is not connected and the person has not dismissed it. It is drawn on Home, not on Start.

### V1. Your plan is ready

**Sees:** "Your plan is ready." and "Connect Strava so your runs show up."
**Now:** `ui/strava_ui.py` `render_plan_prompt`; armed by `_arm_strava_prompt` and `ui/plan_strava.py` `should_offer_strava`
**API:** `POST /seasons` returns `strava_offer`. `GET /home?just_generated=true` returns the same flag.
**Step 3:** The card is on Home (PR #61). Generate, which arms it, is 3.1.
**Status:** done
**Verify:** Generate with Strava disconnected and the prompt not dismissed. Home shows the card. Generate again after "Not now" does not.

### V2. Connect Strava

**Sees:** Primary "Connect Strava", orange, when an authorize URL exists. No button when the URL is missing.
**Now:** `render_plan_prompt`, `render_connect_button`
**API:** `GET /strava/connect` `200` `{url}`. `409` if already connected. `503` if Strava is not configured or migration 010 is missing.
**Step 3:** PR #61 for the button. The OAuth return lands on Settings (`?strava=connected` or `?strava=error`), which is 3.7.
**Status:** partial
**Gap:** The button is on the card after Generate and calls `GET /strava/connect`. This local session has no Strava app, so the call is 503 and the browser stays on Home. The round trip to Strava and back is 3.7, when Settings can land `?strava=connected`.
**Verify:** Click Connect. The browser goes to Strava, then back. Tokens are not in the page.

### V3. Not now

**Sees:** "Not now". The card goes away and stays away.
**Now:** `render_plan_prompt`; `_store_strava_prompt_seen`
**API:** `PATCH /settings` `{strava_prompt_seen: true}`
**Step 3:** PR #61
**Status:** done
**Verify:** Not now, reload Home. The card is gone. Strava is still disconnected.

---

## Home

`page_dashboard`. Today is the athlete's today (D1). No-watch changes which workout is "next" and embeds the Done controls.

### H1. Home photo and credit

**Sees:** The aerial photo, shaded, and "Photo by Gaby Lopez on Pexels".
**Now:** `_paint_home_photo`, `_home_credit`; `theme.HOME_PHOTO`, `HOME_CREDIT`
**API:** MISSING (static)
**Step 3:** PR #61
**Status:** done
**Verify:** `/home` uses `home-aerial.webp` (800 and 480 on small screens) and the Gaby Lopez line. e2e checks the credit.

### H2. No season

**Sees:** Heading "Home", "Hey, {name}" when there is a name, the sentence "Generate a season on Start. Then this note can name the phase and the goal.", and a link "Generate season plan" to Start.
**Now:** `page_dashboard`, `_season_prompt`; `ui/insights.py` `no_plan_copy`; `ui/accounts.py` `hey`
**API:** `GET /home` when `season` is null: `hello`, `copy`, and the client links to Start.
**Step 3:** PR #61
**Status:** done
**Verify:** Account with no season. Those three lines, then the link. No track.

### H3. Days to the goal

**Sees:** A giant "{n} days to {goal time}" or "{n} day to {goal time}", or "—" when the count is missing. Under it, "Hey, {name}" and "{name}'s plan" when the name exists.
**Now:** `_home_headline`; `hey`; `plan_title`
**API:** `GET /home` `season.view.days_remaining`, `season.inputs.goal_time`, `hello`, `athlete.display_name`
**Step 3:** PR #61
**Status:** done
**Verify:** The e2e looks for "130" with the sample season. Also check the singular "1 day".

### H4. Track drawing

**Sees:** An eight-lane oval. The home straight runs out to the left. It is decoration.
**Now:** `_track_svg`
**API:** none
**Step 3:** PR #61
**Status:** done
**Verify:** `TrackArt` is on the hero. It has no text and no score.

### H5. Four tiles

**Sees:** "Training block" (for example "Phase 3", or "—"), "Last timed effort" ("No timed run yet" or "Week {n} · On track|Not hitting|Smashing"), "This week" (the focus line, or "—"), "Progress status" ("No runs yet", "On track", "Ahead", "Behind", or "Not enough data").
**Now:** `_track_meta`, `_mark_text`, `_pace_status_label`; `ui/dashboard.py` `phase_label`, `mark_label`, `week_focus`
**API:** `GET /home` `season.view.phase`, `season.view.mark`, `season.view.focus`, `season.pace_status` (the last field is in PR #61's contract)
**Step 3:** PR #61
**Status:** done
**Verify:** Screenshot the four labels with a fresh season ("No timed run yet", "No runs yet") and with a stored mark.

### H6. Glossary

**Sees:** "A training block is one phase of the season." "A timed effort is a run you logged." "Times use minutes:seconds.tenths, like 2:05.0."
**Now:** `page_dashboard`
**API:** MISSING (static)
**Step 3:** PR #61
**Status:** done
**Verify:** The three sentences are under the tiles, in that order.

### H7. Current phase

**Sees:** "01 / Current phase", a collapsed line such as "This week sits in phase {n}…", and an expanded panel: "Phase {n} — {name}", the focus, day chips Hard / Easy / Long / Race / Off, Previous / This / Next, a marks caption, and when there are no logs and no Strava the line "Connect Strava, or log the hard day, so next week's note can talk about trending."
**Now:** `_render_this_week`, `_phase_panel_html`; `ui/insights.py` `phase_story`, `THIN`
**API:** `GET /home` `season.phase` (`collapsed`, `panel`). This is the authored story, not a model note.
**Step 3:** PR #61
**Status:** done
**Verify:** Expand the bar. Chips and the thin-data sentence match. No probability and no readiness.

### H8. Today's workout or the next one

**Sees:** "02 / Today's workout" or "02 / Next workout" when the phase bar is up, otherwise "01 / …". The card is titled the same way and shows the weekday, the date, Distance, Pace, Rest, and Reps. A rep workout adds "Tolerance …" and "Block …". An easy run says "Run at …" or "Set your easy pace before this run." The whole card opens that session.
**Now:** `page_dashboard`, `_track_hero`, `_track_stage`, `_split_html`. No-watch picks `ui/no_watch.py` `next_open_workout`.
**API:** `GET /home` `season.next` (`label`, `facts`, `shown_date`, `prescription.line`, `prescription.tolerance`, `prescription.block` in PR #61's contract). Easy pace is not passed into `sequence()` or `adapt()`.
**Step 3:** PR #61 for the card. The Done controls on this card are W1 (step 3.3).
**Status:** done
**Verify:** A Tuesday quality day shows tolerance and block. An easy day shows the pace sentence, or the "set your easy pace" sentence when none is saved. Clicking opens Session for that date. The no-watch controls are under the card when `logging` is `done`. The Session page itself is step 3.3.

### H9. No workout left

**Sees:** "No workout left in this plan."
**Now:** `page_dashboard`
**API:** `GET /home` when `season.next` is null
**Step 3:** PR #61
**Status:** done
**Verify:** A season with nothing left on or after today shows that sentence, not an empty card.

### H10. Next 3 days

**Sees:** "03 / Next 3 days" or "02 / Next 3 days" (the lower number when there is no phase bar). Up to three day cards. A day with no workout says "Rest day". A workout card also shows its pace line, tolerance, and block, and opens Session.
**Now:** `_upcoming_days`, `_mini_day`, `_session_link`
**API:** `GET /home` `season.next_days` (PR #61 contract). A day with no session still has a card and `label` "—".
**Step 3:** PR #61
**Status:** done
**Verify:** Three cards. The empty one says "Rest day". A workout card links to `/session?date=`.

### H11. Quick links

**Sees:** Plan, Activity, Library, More. When the phase bar is hidden, an index "03 / Open" sits above them.
**Now:** `_quick_links`
**API:** none
**Step 3:** PR #61
**Status:** done
**Verify:** Home with no phase story shows "03 / Open". Home with a phase story does not.

### H12. Extra sessions

**Sees:** "Extra sessions", then unmatched runs labeled "Extra" or "Activity". Each opens Session with that activity.
**Now:** `_render_extras`, `_extra_link`
**API:** `GET /home` `season.activities` (same rows as the season). The client decides which are extra.
**Step 3:** PR #61
**Status:** done
**Verify:** An unmatched run in the last 14 days appears under the quick links and nowhere in the matched list.

### H13. Broken season

**Sees:** "—" when the stored plan's length cannot be read. A link error is the red sentence, not a fake plan.
**Now:** `page_dashboard`
**API:** `GET /home` or `GET /seasons/current`
**Step 3:** PR #61
**Status:** not started
**Verify:** A plan `sequence()` would reject does not paint tiles. The error sentence is the one stored, escaped.

### H14. Home load failure

**Sees:** Streamlit does not have a separate "Home could not be loaded." line. A failed read uses the account and season errors already on the page.
**Now:** `page_dashboard`
**API:** `GET /home` `detail`
**Step 3:** PR #61
**Status:** partial
**Gap:** `HomeView` adds "Home could not be loaded." when the throw is not an `ApiError`. An `ApiError` shows `detail`, which is right. The invented fallback should not replace a real `detail`.
**Verify:** A 401 shows "Sign in again." A network failure may use the fallback. It must not hide a `detail`.

---

## Plan

`page_plan`. Three views inside one page: Calendar, This week, Full season. The last view is remembered. Photo credit is in the hero.

### B1. Plan hero

**Sees:** "{n} weeks" or "1 week", then "{start} — {goal}" in the saved date format, on the curve photo.
**Now:** `page_plan`, `_length_text`, `_with_plan_credit`
**API:** `GET /plan` `inputs`. The session list is `plan.sessions` on `GET /seasons/current`.
**Step 3:** 3.2
**Status:** done
**Verify:** A 12-week season says "12 weeks". A one-week season says "1 week". Dates follow ISO or Short (Settings G5).

### B2. No plan, and a bad plan

**Sees:** Heading "Plan". With no season, "Generate season plan". With a bad length, "—". A link error is red.
**Now:** `page_plan`, `_season_prompt`
**API:** `GET /plan` `404` when there is no current season
**Step 3:** 3.2
**Status:** done
**Verify:** No season: the link opens Start. No empty calendar of fake days.

### B3. Pace status line

**Sees:** "Pace status No runs yet." or On track, Ahead, Behind, Not enough data, with a period.
**Now:** `page_plan`, `_pace_status_label`
**API:** `GET /home` `pace_status` is the same words. `GET /plan` does not repeat the sentence; the client can use the home field or the season.
**Step 3:** 3.2
**Status:** done
**Verify:** The line under the hero matches the Home tile.

### B4. Phases strip

**Sees:** Label "Phases", optional "This week is phase {n}.", and a cell per week (W1, W2, …) with the phase digit. The current week is marked.
**Now:** `page_plan`, `_phase_timeline`
**API:** `GET /plan` `weeks` (`week`, `phase`, `status`)
**Step 3:** 3.2
**Status:** done
**Verify:** The current week is visually distinct. Phase digits match the season.

### B5. Calendar, This week, Full season

**Sees:** A segmented control, label hidden, options "Calendar", "This week", "Full season". The choice sticks for the session. Switching views rises once.
**Now:** `page_plan`
**API:** none for the control. Calendar data is `GET /plan?month=YYYY-MM`.
**Step 3:** 3.2
**Status:** done
**Verify:** Each segment shows its view. Reload keeps the last one. Default is Calendar.

### B6. Weeks expander

**Sees:** Collapsed "Weeks". Empty: "No runs logged yet. A week shows distance after a workout is saved." Rows show week, phase, volume, a status word (`done`, `current`, `upcoming`, or "—"), and "{n} days to goal". Zero meters says "No runs logged".
**Now:** `_plan_weeks`, `_progress_html`; `ui/progress.py` `days_label`
**API:** `GET /plan` `weeks` (`meters`, `volume`, `days_remaining`, `status`)
**Step 3:** 3.2
**Status:** done
**Verify:** Collapsed on first open. A week with no file shows no distance, not template meters.

### B7. Month calendar

**Sees:** The month name, such as "October 2026", a "Month" select of every month in the plan, headers Sun through Sat, and day cells. A session day has a short label (Race, Long, Easy, Speed, Threshold, and the rest of `session_label`). Today is marked. A session day opens Session. A day outside the month is blank.
**Now:** `page_calendar`, `_cal_cell`; `ui/calendar.py` `month_title`, `session_label`, `month_weeks`
**API:** `GET /plan?month=YYYY-MM`. Omitted month is the month that contains today. `400` when `month` is not `YYYY-MM`. `404` with no season.
**Step 3:** 3.2
**Status:** done
**Verify:** Today has the today style. Clicking a workout opens that date. An off-month cell has no link.

### B8. This week

**Sees:** "Week {n}" and "Phase {p} · {Sunday} — {Saturday}". A "Week" select whose options are "Week {n} · {dates}". Then the recap and the day cards.
**Now:** `page_weekly`, `_weekly_hero`, `_week_option`
**API:** `GET /seasons/current` `plan.sessions`, plus `GET /plan` `weeks`
**Step 3:** 3.2
**Status:** done
**Verify:** Changing the select changes the seven days. Dates use the saved format.

### B9. Recap

**Sees:** "Recap" with Sessions, Marks, Volume, and Next week. Volume mentions "the week before". Next week uses the adapt sentence, such as "Next week is an easy week."
**Now:** `page_weekly`; `ui/recap.py` `recap_view`
**API:** The numbers are on the season (`marks`, `actuals`, `activities`). There is no separate recap route. The client builds the four lines from `GET /seasons/current` and `GET /activities`.
**Step 3:** 3.2
**Status:** done
**Verify:** A week with no logged work does not invent meters. Template meters stay out.

### B10. Week day cards and extras

**Sees:** One card per day, linking "{weekday} {date}. {workout}". "Extra sessions" for runs in that Sunday–Saturday window that are not on the plan.
**Now:** `page_weekly`, `_session_link`, `_render_extras`
**API:** `GET /activities` `rows` and `all` (`extra: true` when unmatched)
**Step 3:** 3.2
**Status:** done
**Verify:** A planned day opens Session. An extra run is under the week, labeled extra.

### B11. Week mark

**Sees:** "Mark", then "On track", "Not hitting", "Smashing". The applied mark is shown once it is stored. This also sits on each week of Full season.
**Now:** `_render_mark`; labels `ui/dashboard.py` `MARK_LABEL`
**API:** `POST /seasons/current/marks` body `{week, choice}`. `choice` is `on_track`, `not_hitting`, or `smashing`. This route does not call the model.
**Step 3:** 3.2. The confirm dialog is W8.
**Status:** done
**Verify:** Each button. With confirm-adapt on, the dialog comes first. With it off, later weeks move immediately. The marked week itself stays as written.

### B12. Full season

**Sees:** Heading "Full season" while nested in Plan. Each week: "Week {n} · Phase {p}", the day rows (workout, target, status, pace), a "Reasons" expander (or "—"), and the mark buttons. An empty week is "—".
**Now:** `page_season`, `_render_schedule`, `_day_html`, `_plain_reasons`
**API:** `GET /seasons/current` `plan`
**Step 3:** 3.2
**Status:** done
**Verify:** Every week of the season is listed. A row opens that session. Reasons are the plain words, not raw codes, unless the code has no plain form.

### B13. Plan credit

**Sees:** "Photo by Jan van der Wolf on Pexels" inside the hero.
**Now:** `_with_plan_credit`; `theme.PLAN_CREDIT`
**API:** MISSING (static)
**Step 3:** 3.2
**Status:** done
**Verify:** The credit is on the curve photo, not under the footer. See C5.

### B14. This week activity notice

**Sees:** When Strava is not connected and the Intervals pull fails because the key is missing, "Strava isn't connected", "Connect Strava in Settings to see your runs here.", and "Open Settings". Any other pull failure says "Runs could not be loaded. Try Refresh in a moment." A connected Strava account does not show the card. The raw adapter sentence stays off the page.
**Now:** `page_weekly` `_activities_notice`
**API:** `GET /activities` `notice`. The card is shown only when that text contains "is not set" or "not configured".
**Step 3:** 3.2
**Status:** done
**Verify:** Local Plan, This week, with no Intervals key. The three lines are on the page. A 429-style notice shows the refresh sentence instead.

---

## Start session and Session logging

"Start session" in the nav opens the next planned day. The Session page is one day. Fixed prep notes are not stored. Watch logging and no-watch logging are different. Tuesday and Thursday quality days adapt later weeks. Easy and long runs do not.

### W1. Start session

**Sees:** Nav control "Start session". It opens the next planned date, or the latest date when nothing is left.
**Now:** `_render_nav`, `_next_session_day`
**API:** `GET /auth/me` `next_session`. The same date is `GET /home` `next_session`.
**Step 3:** 3.3. The nav shell is PR #61.
**Status:** done
**Verify:** Mid-season, Start session opens today's workout or the next one, the same day Home shows. After the last day, it opens the last day. `tests/test_api_step3_session.py` `test_next_session_day_is_today_or_the_last_day`. `web/e2e/auth-home.spec.ts` "start session opens the next planned day". Video `session-new-account-log-result.mp4`.

### W2. Session with no plan, no date, or a bad date

**Sees:** "Generate season plan" when there is no season. "Open a workout from Home or Plan." when there is no date. "That session is not in this plan." when the date is not in the season.
**Now:** `page_session`
**API:** `GET /sessions/{date}` `404` when the date is not in the season or there is no season
**Step 3:** 3.3
**Status:** done
**Verify:** Three screenshots. No stack trace. No empty result form on a bad date. `web/e2e/session.spec.ts` "a session with no plan, no date, or a bad date" and "a bad date does not open the result form".

### W3. Session hero and workout

**Sees:** The weekday as the heading and the date under it. Card "Workout" in plain menu words. Optional "Structure" and "Target outcome" ("—" when blank). "Reasons" in plain words, or "—".
**Now:** `page_session`, `_structure_text`, `_plain_reasons`
**API:** `GET /sessions/{date}` `label`, `structure`, `target`, `reasons`
**Step 3:** 3.3
**Status:** done
**Verify:** The workout name matches Library. Reasons are sentences, not code tokens, when a plain form exists. `tests/test_api_step3_session.py` `test_session_uses_easy_pace_and_states_the_rep_and_the_average`. `web/e2e/session.spec.ts` "a quality day states the rep time".

### W4. Prep notes

**Sees:** "Pre-warm-up" ("1 × 800 m easy"), "Warm-up" (active drills, dynamic drills, then "4 × 100 m strides with walk-back"), "Cool-down" ("1 easy lap" and the seated stretches), and "Core" ("3 rounds of:" and the eight exercises). The same copy on every session. It is not saved.
**Now:** `_prep_lines`
**API:** MISSING (static). Do not store this on the session.
**Step 3:** 3.3
**Status:** done
**Verify:** Screenshot all four blocks. Logging a result does not change the prep text. `web/lib/session.test.ts` "prep notes are the four fixed blocks". `web/e2e/session.spec.ts` shows Pre-warm-up, Warm-up, Cool-down, and Core. Full-page screenshot `session-quality-side-by-side.png`.

### W5. Pace line on the session

**Sees:** Per rep, "Tolerance …" and "Block …", or for an easy run "Run at …" or "Set your easy pace before this run." A logged actual can show "Actual …".
**Now:** `_split_html`; `engines/pace.py` `workout_times`
**API:** `GET /sessions/{date}` `prescription` (`line`, `tolerance`, `block`, `average`). Easy pace comes from the saved pace and is not an input to `sequence()`.
**Step 3:** 3.3
**Status:** done
**Verify:** A 6×400 shows a tolerance band and a block clock. An easy run uses the saved pace, never the 1.55 aerobic fraction. `tests/test_api_step3_session.py` `test_session_uses_easy_pace_and_states_the_rep_and_the_average`. `web/e2e/session.spec.ts` "an easy run uses the saved pace". Full-page screenshots `session-quality-side-by-side.png` and `session-easy-side-by-side.png`. Both show "The higher capacity weight won" on the Tuesday, which is the plain form of `capacity_weight`. The Tuesday is 2026-11-10 and the Monday is 2026-11-09, today in America/Los_Angeles while the server clock was 2026-11-10 UTC.

### W6. Matched activity beside the template

**Sees:** "Intervals" with Reps, Work, and Avg HR from the matched run. A separate "Avg HR" when the page has a heart rate the match block did not show.
**Now:** `_supplied_html`, `page_session`
**API:** `GET /sessions/{date}` `match` (`reps`, `work`, `heart_rate`) and `actual`
**Step 3:** 3.3
**Status:** done
**Verify:** A matched quality day shows rep times that can still be edited. Warm-up meters are not in Work. `web/e2e/session.spec.ts` shows Intervals, Reps, and Avg HR beside the template. The boxes stay editable.

### W7. Watch logging

**Sees:** "Times save as you type." Label "Result". "Enter the time for each rep." when there is more than one. Boxes "Rep 1" … "Rep n", or a single "Time". A saved line "{times} · {mark}" using on_track, not_hitting, or smashing. Invalid keystrokes are ignored.
**Now:** `_render_result`, `_time_box`; `ui/result.py` `judge`, `result_box_count`
**API:** `POST /seasons/current/results` body `{date, text, slots, intervals, note}`. `400` when the date is not in the season or the result cannot be judged. The response includes `insight` (`pending`, `ready`, or `skipped`) and does not wait for the model.
**Step 3:** 3.3
**Status:** done
**Verify:** Type a rep time. It saves without a separate Save button. A hard day can change later weeks. An easy day does not call adapt. The plan is stored before any note runs. `tests/test_api_step3_session.py` `test_a_quality_result_adapts_and_an_easy_done_does_not`. `web/e2e/session.spec.ts` "a quality day states the rep time" (no Save button; Confirm is W8). Easy days render no result boxes.

### W8. Confirm before later weeks change

**Sees:** "Confirm this result before the plan changes." or, for Done with a time, "Confirm this workout before the plan changes." or, for a week mark, "Confirm {On track|Not hitting|Smashing} before the plan changes." Buttons "Confirm" and "Cancel". Only when Settings "Ask me before a timed run changes later weeks" is on. Cancel drops the pending change.
**Now:** `_confirm_adapt`, `_render_result`, `_render_watchless`, `_render_mark`
**API:** MISSING (static) for the dialog. The setting is `PATCH /settings` `confirm_adapt`. Confirm then calls `POST /seasons/current/results`, `POST /seasons/current/watchless`, or `POST /seasons/current/marks`. The API applies the mark. It does not know about the dialog.
**Step 3:** 3.3 for the dialog on a result. The setting is 3.7 (Settings G5). The week-mark copy is 3.2 (B11).
**Status:** done
**Verify:** Setting on: the dialog shows and Cancel leaves later weeks alone. Setting off: no dialog, later weeks move. An adapt error is red via `_finish_commit`. `web/e2e/session.spec.ts` "a quality day states the rep time" (Cancel posts nothing; Confirm posts once) and "no-watch shows Done". `web/lib/session.test.ts` "confirm copy matches the dialog". Full-page screenshot `session-confirm-side-by-side.png` shows Confirm and Cancel on both apps. Plan after the save is `session-plan-after.png`.

### W9. No-watch Done

**Sees:** Primary "Done", "Couldn't finish", and "Add a time". A hard day also shows "Behind", "On target", and "Ahead". Easy and long runs do not show those three. After a miss: "Couldn't finish. Done still completes this workout." A finished row reads "Completed · {Behind|On target|Ahead} · {time}".
**Now:** `_render_watchless`, `_watchless_choices`, `_watchless_summary`; `ui/no_watch.py` `CHOICES`
**API:** `POST /seasons/current/watchless` body `{date, outcome, time, note}`. `outcome` is `Behind`, `On target`, or `Ahead`. `time` may be empty. A time on a hard day adapts later weeks. Done with no time does not.
**Step 3:** 3.3. The same block is embedded on Home when no-watch is on (H8).
**Status:** done
**Verify:** Easy day: Done and Couldn't finish only, plus Add a time. Hard day: the three outcomes are required ("Choose behind, on target, or ahead." if missing). Done with no time does not move later weeks. `tests/test_api_step3_session.py` `test_a_quality_result_adapts_and_an_easy_done_does_not`. `web/e2e/session.spec.ts` "no-watch shows Done". Home uses the same block when `logging` is `done`.

### W10. Add a time

**Sees:** "Add a time" reveals "Time" with placeholder "1:12.4" and "Optional. One clock time, like 1:12.4. Leave it blank to finish without one." A bad clock says "Enter one time, like 1:12.4, or leave it blank."
**Now:** `_render_watchless`
**API:** `POST /seasons/current/watchless` `time`. `400` when the time is unusable.
**Step 3:** 3.3
**Status:** done
**Verify:** Blank time completes. "1:12.4" is stored as one number. "abc" shows the sentence and does not save. `tests/test_api_step3_session.py` `test_a_quality_result_adapts_and_an_easy_done_does_not` (the "abc" sentence and the blank Done). `web/e2e/session.spec.ts` types `1:12.4` before Confirm.

### W11. Insight on the session

**Sees:** The same note as Home: headline, body, "Carry forward", and "Got it".
**Now:** `page_session` calls `_show_stored_insight`
**API:** `GET /sessions/{date}` `note`. "Got it" is `POST /seasons/current/notes` `{date, note, viewed: true}`.
**Step 3:** 3.3. The note shape is item Q1.
**Status:** done
**Verify:** Got it hides the note on reload. It does not call the model. `web/e2e/session.spec.ts` shows the headline and clicks Got it, which posts `viewed: true` and does not call `POST /insights/workout`.

### W12. An extra activity opened as a session

**Sees:** The weekday and date, then a card "Activity" with reps, volume, and heart rate. No result boxes.
**Now:** `page_session`, `_render_logged_activity`
**API:** `GET /activities` `logged` for that id. `GET /sessions/{date}` `404` if that date is not a planned day, so the client must use the activity payload.
**Step 3:** 3.3
**Status:** done
**Verify:** Open an extra from Home or Activity. No Done form and no adapt. `web/e2e/session.spec.ts` "an extra activity has no Done form".

### W13. Admin Intervals file on the session

**Sees:** Only for the admin email: a select "Intervals file", first option "—", then JSON names. Choosing one fills the rep boxes from that file's WORK elapsed times. The numbers stay editable. A bad file says "Could not read {name}." or "{name} is not JSON."
**Now:** `_intervals_choice`, `_fixture_allowed`. Everyone else is sent Home.
**API:** `GET /fixtures/intervals` lists names. `GET /fixtures/intervals/{name}` returns the WORK elapsed times. A normal account is `403`.
**Step 3:** 3.3. The athlete result form must not show this select. The admin fill was the data hole on this row.
**Status:** done
**Verify:** A normal account has no file select. The admin account can fill reps from a fixture and still edit them. `tests/test_api_step3_session.py` `test_admin_intervals_fill_stays_off_a_normal_account`. `web/e2e/session.spec.ts` asserts the select is absent for an athlete.

---

## Activity and Strava sync

`page_activity`. Opening Home, Plan, Weekly, Session, or Activity pulls the last 14 days when Strava is not connected. Refresh pulls the full history. A connected Strava account skips the Intervals pull.

### Y1. Activity hero and no season

**Sees:** Heading "Activity" and the date range of the season. No season: "Generate season plan". A bad plan: "—". The synthetic banner is not shown.
**Now:** `page_activity`, `_season_prompt`
**API:** `GET /activities` `404` when there is no current season
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** No season does not call Strava. The link opens Start.

### Y2. Refresh

**Sees:** "Refresh from Strava", "Pulls the latest runs.", and a button "Refresh".
**Now:** `page_activity`; `_pull_for`
**API:** `POST /strava/sync` body `{scope: "all"}` for a full pull, `{scope: "recent"}` to continue from the last success. `429` when Strava rate-limits. `404` with no season. When Strava is not connected, the same route runs the Intervals fallback and a missing key comes back as `synced: false` and a `notice`.
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** Refresh imports runs. A failed import shows the notice and does not move "last synced". A quality day is not adapted twice.

### Y3. Strava not connected

**Sees:** "No runs yet." and "Connect Strava and your runs show up here, matched to your plan." Link "Connect Strava in Settings". Also the card "Strava isn't connected" / "Connect Strava in Settings to see your runs here." and "Open Settings".
**Now:** `page_activity`, `_activities_notice`
**API:** `GET /strava/status` `connected: false`
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** Disconnected account. Both the empty line and the Settings link. No fake rows.

### Y4. Connected empty, and last synced

**Sees:** "Last synced {date}, {count} runs imported". When connected and still empty: "No runs yet" / "Refresh from Strava. This week's runs, distance, and heart rate will show up here."
**Now:** `ui/strava_ui.py` `status_html`; `page_activity`
**API:** `GET /strava/status` `last_sync_at`; `GET /activities`
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** After a sync of zero runs, the empty card is the second sentence, not the disconnected one.

### Y5. This week summary

**Sees:** "This week" tiles: Distance, Runs, On track, Ahead, Behind, Extra.
**Now:** `ui/activity_board.py` `summary_html`
**API:** `GET /activities` `summary`
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** Counts match the cards below. Distance uses pace units (miles or km). Reps stay in meters.

### Y6. Week groups and run cards

**Sees:** An expander per week, newest first. Inside, one card per run: name, status pill On track, Ahead, Behind, or Extra, and the detail. An empty week says "No runs this week."
**Now:** `page_activity`; `ui/activity_board.py` `group_weeks`, `build_cards`
**API:** `GET /activities` `groups`, `cards`
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** An unmatched run is Extra, not dropped. A run with no distance and no heart rate is on neither list.

### Y7. Heart-rate chart

**Sees:** "Heart rate · bpm" and a chart labeled "Average heart rate" for screen readers. Hidden when no run has a heart rate.
**Now:** `ui/activity_board.py` `heart_axis_chart`
**API:** `GET /activities` `heart` (`date`, `bpm`)
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** Dots are dated. A run with no heart rate adds no dot. No chart at all when every bpm is missing.

### Y8. Strava errors

**Sees:** "Strava is busy. Try again in a few minutes." "Strava could not be reached." "Strava could not be saved." "Strava activities could not be read." "Strava could not be connected." "Strava could not be disconnected." A failed Intervals pull on the page says "Runs could not be loaded. Try Refresh in a moment." rather than the raw adapter text.
**Now:** `ui/strava.py`; `ui/strava_ui.py`; `_activities_notice`
**API:** `POST /strava/sync` `429` and `notice`. Connect and disconnect use `GET /strava/connect`, `GET /strava/callback`, `POST /strava/disconnect`.
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** A 429 shows the busy sentence. The page does not print a token or a stack trace.

### Y9. Strava in Settings

**Sees:** Section "Strava". Not configured: "Strava is not set up on this server yet." Always, when the block is up: "Strava data is only visible to you." Connected: "Connected as {name}." (or "Strava athlete") and "Disconnect". Not connected: "Connect with Strava".
**Now:** `ui/strava_ui.py` `render_settings`
**API:** `GET /strava/status`, `GET /strava/connect`, `POST /strava/disconnect`. Disconnect deauthorizes and deletes tokens and activities. The response has no `access_token` and no `refresh_token`.
**Step 3:** 3.7 for the Settings block. The return URL is part of `GET /strava/callback` (lands on `/settings?strava=connected` or `?strava=error`).
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** Connect, see the name, Disconnect, and the runs leave Activity. View the network response and confirm it has no token.

### Y10. Opening a page pulls recent runs

**Sees:** No spinner copy. Home, Plan, This week, Session, and Activity show matches from the last 14 days without asking. Refresh is the full history. A connected Strava account does not also pull Intervals.
**Now:** `_pull_for`; `services/activity_pull.py`
**API:** `POST /strava/sync` `{scope: "recent"}` on those opens, `{scope: "all"}` on Refresh
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** Open Activity twice. The second open does not duplicate rows. With Strava connected, Intervals is not called.

### Y11. Test-season line

**Sees:** While previewing the test athlete: "TEST season · {count} runs".
**Now:** `status_html`
**API:** `PR #61: GET /admin/test-season`
**Step 3:** Unassigned (admin). Activity for a real athlete is 3.4 and must not show this line.
**Status:** not started
**Verify:** Only the test preview shows it. A normal account does not.

---

## Library

The frozen menu. It does not change. Search does not call a model.

### M1. Library hero

**Sees:** Heading "Library". A menu that fails to load is a red error, not an empty list pretending to be the menu.
**Now:** `page_library`
**API:** `GET /library`
**Step 3:** 3.5
**Status:** done
**Evidence:** `web/e2e/library.spec.ts` "a failed menu is the exception sentence, not an empty list" and `tests/test_api_step3_library.py` `test_a_failed_menu_is_the_exception_sentence`. The heading is Library. There is no photo on the page.
**Verify:** The heading is Library. A load error is the exception sentence, escaped.

### M2. Search, family, phase

**Sees:** "Search" with placeholder "Search workouts". "What it trains" with help "The quality that workout builds, such as speed or endurance." Options "All" plus the family names. "Phase" with help "A phase is a training block. The season moves through eight of them." Options "All" or "Phase {n}" for 1–8.
**Now:** `page_library`; `ui/library.py` `filter_workouts`
**API:** `GET /library?q=&family=&phase=`. `q` matches name, id, or capacity. Empty filters stay open.
**Step 3:** 3.5
**Status:** done
**Evidence:** `web/e2e/library.spec.ts` "the menu, a search, an empty result, and a load error" and `tests/test_api_step3_library.py` `test_search_matches_the_shown_name_and_filters_stay_open`.
**Verify:** Each filter narrows the list. Clearing them restores the full menu. The menu ids do not change between loads.

### M3. Count and rows

**Sees:** "{n} workout" or "{n} workouts". "No workouts." when nothing matches. Each row is the recipe name and a capacity pill (Aerobic, Speed endurance, and the other family words).
**Now:** `page_library`, `_library_html`; `ui/library.py` `library_rows`
**API:** `GET /library` `count`, `workouts`, `families`
**Step 3:** 3.5
**Status:** done
**Evidence:** `web/e2e/library.spec.ts` and `tests/test_api_step3_library.py` `test_library_lists_every_template_and_sorts_families`. Ids follow `prefs.show_ids`.
**Verify:** Search for a nonsense word: "No workouts." Search for a known id: that row. Template ids are hidden unless Settings "Show template ids" is on (admin only, Settings G5).

---

## Profile

The four Start values, plus easy pace. Saving a goal time does not rebuild the season.

### R1. Easy pace on Profile

**Sees:** The same card as the gate. When a pace is saved: "Saved: {pace phrase}. You can change it here."
**Now:** `_easy_pace_section`; `ui/easy_pace.py` `render_easy_pace`
**API:** `PATCH /settings` `easy_pace` and `easy_pace_unit`. Read from `GET /profile` `easy_pace_phrase`.
**Step 3:** 3.6. The first-run gate is 3.1 (E1).
**Status:** done
**Evidence:** `web/e2e/profile.spec.ts` "the four values, a saved goal, a bad time, and a new easy pace" and `tests/test_api_step3_profile.py` `test_changing_easy_pace_updates_the_phrase_and_leaves_the_plan`. Home's easy run uses the new phrase. The season digest does not change.
**Verify:** Change 7:25 per mile to 5:00 per kilometer. Home's easy run uses the new phrase. The season's workouts do not rebuild.

### R2. No season

**Sees:** The profile hero, the easy-pace form, and "Generate season plan". No fake 800 times.
**Now:** `page_profile`
**API:** `GET /profile` `ready: false` and `fields: []`
**Step 3:** 3.6
**Status:** done
**Evidence:** `web/e2e/profile.spec.ts` "no season shows easy pace and the way to Start" and `tests/test_api_step3_profile.py` `test_profile_without_a_season_has_no_start_fields`.
**Verify:** New account after the gates. Easy pace is there. The four Start fields are not.

### R3. The four values

**Sees:** "Four values from Start. Current 800, the start date, and the goal date stay with the season. Goal 800m time is the one you can change." Then "Starting point" (help "Your current 800, and the day this season began.") with Current 800 time and Start date, and "The race" with Goal date and an editable "Goal 800m time" (placeholder "1:55.0", hint "Minutes, seconds, and tenths, like 1:55.0.").
**Now:** `page_profile`; `ui/profile.py` `profile_fields`, `shown_goal`
**API:** `GET /profile` `fields`, `inputs`, `goal_time`
**Step 3:** 3.6
**Status:** done
**Evidence:** `web/e2e/profile.spec.ts` "the four values, a saved goal, a bad time, and a new easy pace" and `tests/test_api_step3_profile.py` `test_saving_a_goal_does_not_rebuild_and_a_bad_time_is_refused`. Dates use the saved format. A blank value is "—".
**Verify:** Current 800, start date, and goal date match Start and are not editable. A blank value prints "—".

### R4. Save goal time

**Sees:** "Save" and "Saving keeps this time on your account. It does not rebuild the season." Success: "Saved for this account." A bad time: "goal_time is not an 800 time".
**Now:** `page_profile`; `ui/profile.py` `clean_goal`, `dump_goal`
**API:** `PR #61: PUT /profile/goal` body `{goal_time}`. `400` with that sentence. `404` with no season. The season digest does not change. On main's contract this override is not a route yet (it lived only in the browser under `profile_key`).
**Step 3:** 3.6
**Status:** done
**Evidence:** `web/e2e/profile.spec.ts` "the four values, a saved goal, a bad time, and a new easy pace" and `tests/test_api_step3_profile.py` `test_saving_a_goal_does_not_rebuild_and_a_bad_time_is_refused`. Home's goal stays the season goal. A bad time is "goal_time is not an 800 time".
**Verify:** Save 1:54.0. Home still shows the season's goal in the big "days to" line. Profile shows 1:54.0. Reload keeps it. The plan's sessions do not change.

---

## Settings

Changes to name, time zone, and the toggles save as they are edited. There is no Save button for those. Password, email, and the danger zone have their own buttons. "SYNTHETIC / DEMO" is not shown.

### G1. Settings hero and notices

**Sees:** Heading "Settings". A failure is red. A success note is the quieter settings note.
**Now:** `page_settings`
**API:** `PATCH /settings` returns the athlete. `400` when a value is unusable or the body changes nothing.
**Step 3:** 3.7
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "a rejected name stays an error and the saved name is unchanged" and `tests/test_api_step3_settings.py` `test_a_bad_value_does_not_wipe_the_name`. A bad zone returns "Choose a time zone from the list." and the stored name stays.
**Verify:** A bad time zone does not wipe the name. The previous value stays.

### G2. Name, nickname, email, time zone

**Sees:** Expander "Profile", open. "Name". Note "First name is enough. Saved to your RIO account." when hosted, or "First name is enough. Saved on this machine." when local. "Preferred name / nickname". "Email" disabled. "Time zone" listing the ids in `ui/settings.py` `TIME_ZONES` (UTC through Pacific/Auckland). An already-saved id that is not in the list still appears.
**Now:** `page_settings`, `_profile_save_note`
**API:** `PATCH /settings` `display_name`, `preferred` (empty string clears it), `timezone`. Email on this form is display-only. Changing it is Settings G7.
**Step 3:** 3.7
**Status:** done
**Evidence:** `tests/test_api_step3_settings.py` `test_the_greeting_uses_the_nickname_then_the_name` and `test_an_unlisted_saved_zone_still_appears`. `web/e2e/settings.spec.ts` covers the name error and the zone list. Home `hello` is the nickname, then the name.
**Verify:** Edit the name, reload, the greeting on Home uses it. Clear the nickname and the greeting falls back to the name. "Enter a name." when the name is rejected.

### G3. Change password

**Sees:** "Current password", "New password", button "Change password". Success: "Password updated."
**Now:** `page_settings`; `ui/accounts.py` `change_password`
**API:** `PR #61: POST /auth/password` body `{current_password, new_password}`. The cookie stays.
**Step 3:** 3.7
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "password and email keep the person signed in when the secret is wrong". The API round trip is `tests/test_api_step2c.py` `test_change_password_and_email_keep_the_session`.
**Verify:** Wrong current password stays signed in and shows the error. The right one lets the new password log in. The old one does not.

### G4. Logging

**Sees:** Expander "Logging". Toggle "I don't use a watch". Note "Complete workouts with Done instead of entering splits."
**Now:** `page_settings`
**API:** `PATCH /settings` `no_watch`. `prefs.logging` becomes `done` when that is true, otherwise `times`.
**Step 3:** 3.7. The Session behavior is W9.
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "timezone, pace, and each toggle are saved" posts `no_watch`. `tests/test_api_step3_settings.py` `test_the_saved_zone_decides_today_on_home_and_plan` keeps the session ids. Session already reads `logging`.
**Verify:** Turn it on. Session shows Done, not rep boxes. Turn it off. Rep boxes return. The plan is not rewritten.

### G5. Pace units, intro, start date, ids, compact, dates, confirm

**Sees:** Expander "Preferences". "Pace units" as "per mile" or "per km", note "Distances and paces on Activity, Home, and Plan use this. Reps stay in meters." Button "Show intro guide". "Default start date" as "Today" or "Next Sunday", note "Next Sunday starts the training week." Admin only: "Show template ids". "Compact mode". "Date format" as "ISO" or "Short". "Ask me before a timed run changes later weeks".
**Now:** `page_settings`. Short dates are like "Oct 24, 2026" (`ui/settings.py` `format_date`). ISO is `YYYY-MM-DD`.
**API:** `PATCH /settings` `pace_units`, `intro_seen`, `start_date`, `show_ids`, `compact`, `date_format`, `confirm_adapt`. The plan is not rewritten.
**Step 3:** 3.7
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "timezone, pace, and each toggle are saved" and "show intro guide opens the guide again". A non-admin has no "Show template ids". `PATCH /settings` does not rewrite the plan (`test_the_saved_zone_decides_today_on_home_and_plan`).
**Verify:** Per km changes Activity distance and does not change a rep from meters to miles. "Show intro guide" opens I1 on the next paint. Short versus ISO changes Plan and Past seasons. A non-admin has no "Show template ids".

### G6. Export

**Sees:** Expander "Data". "Export season as JSON" downloads `rio-season.json`. With no season: "Generate a season on Start."
**Now:** `page_settings`; `ui/plan_store.py` `export_season`
**API:** The file is built in the browser from `GET /seasons/current` (inputs, plan, marks, actuals). There is no separate export route.
**Step 3:** 3.7
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "export downloads the season, and an empty account says to start" saves `rio-season.json` with the four inputs and no password or seal. `web/lib/settings.test.ts` checks the file shape. No export route was added.
**Verify:** The file opens as JSON and contains the four inputs. No tokens.

### G7. Change email

**Sees:** Expander "Account". "New email", "Password", button "Change email". Local success: "Email updated." Hosted success can be "Check your email to confirm the new address."
**Now:** `page_settings`; `ui/accounts.py` `change_email`
**API:** `PR #61: POST /auth/email` body `{email, password}`
**Step 3:** 3.7
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "password and email keep the person signed in when the secret is wrong" and "hosted email success can ask for a confirmation mail". A taken address stays on the old email. Hosted success is "Check your email to confirm the new address."
**Verify:** Wrong password does not change the address. A taken address shows the error and stays on the old one.

### G8. Privacy note and version

**Sees:** Expander "Privacy" with "Signs you out on this browser. Your season stays in your account." (hosted) or "Clears this browser. The account stays on this machine." (local). Expander "About" with "RIO 0.1".
**Now:** `_browser_clear_note`; `ui/settings.py` `APP_VERSION`
**API:** none for the sentences. Version is static.
**Step 3:** 3.7
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "about is the version, and strava shows connect or disconnect" expects "RIO 0.1". Hosted and local privacy sentences are in "hosted email success can ask for a confirmation mail" and "danger actions ask before they run".
**Verify:** The version is 0.1. The privacy sentence matches hosted versus local.

### G9. Danger zone

**Sees:** Kicker "Danger zone" and "Reset the plan, delete this account, or clear this browser. These sit apart from the settings above."
**Now:** `page_settings`
**API:** none for the kicker
**Step 3:** 3.7
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "danger actions ask before they run". The kicker and the red expander are separate from Preferences. Each button without its checkbox shows that button's confirm sentence and does not call the route.
**Verify:** The block is visually separate from Preferences. Nothing in it runs without its own confirm.

### G10. Clear marks

**Sees:** "Confirm clear" and "Clear all marks / actuals". Without the box: "Confirm to clear marks and actuals." Success: "Marks and actuals are cleared." With no season: "Generate a season on Start."
**Now:** `page_settings`, `_clear_season_marks`
**API:** `POST /seasons/current/clear` body `{confirm: true}`. The plan is `sequence()` again for the same four inputs. Marks, actuals, and quality bases are empty. Notes stay.
**Step 3:** 3.7
**Status:** done
**Evidence:** `tests/test_api_step3_settings.py` `test_clear_keeps_notes_and_reset_keeps_the_account`. `web/e2e/settings.spec.ts` shows "Confirm to clear marks and actuals." before the box, then "Marks and actuals are cleared."
**Verify:** Confirm, then a logged rep is gone and an insight note is still there. The four inputs are unchanged.

### G11. Reset plan

**Sees:** "Confirm reset", "Reset plan", and "Reset removes stored seasons. The account stays." Without the box: "Confirm to reset the plan."
**Now:** `page_settings`, `_reset_saved_plan`
**API:** `PR #61: POST /seasons/reset` body `{confirm: true}`. The account, name, and settings stay.
**Step 3:** 3.7
**Status:** done
**Evidence:** `tests/test_api_step3_settings.py` `test_clear_keeps_notes_and_reset_keeps_the_account`. Reset without the box is "Confirm to reset the plan." After confirm, Home has no season, sign-in still works, and easy pace stays.
**Verify:** After reset, Home is the no-plan state. Log in still works. Easy pace is still saved.

### G12. Delete account

**Sees:** "I understand this permanently deletes my season and runs" and "Delete my account". Hosted: the checkbox is enough. Local: also "Type your email to confirm" and "Password". Without the box: "Confirm to delete this account." Wrong email: "Confirm with your email to delete this account."
**Now:** `page_settings`; `ui/accounts.py` `delete_account`; `ui/cloud_ui.py` `delete_signed_in_account`
**API:** `PR #61: POST /auth/delete`. `confirm` must be true. Hosted ignores email and password. Local requires both. The cookie is cleared.
**Step 3:** 3.7
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "danger actions ask before they run" shows "Confirm to delete this account." and "Confirm with your email to delete this account." The local API check is `tests/test_api_step2c.py` `test_local_delete_requires_the_email_and_the_password`. No production delete was run.
**Verify:** Use a throwaway account. After delete, that email cannot log in. Another account on the same browser is unaffected. Do not run this against production.

### G13. Clear local data

**Sees:** "Clear data stored in this browser" and "Clear local data". Without the box: "Confirm to clear local data." This signs the person out.
**Now:** `page_settings`, `_sign_out`
**API:** MISSING (static) for the checkbox. Sign-out is `POST /auth/sign-out`. The browser store is the client's.
**Step 3:** 3.7
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "danger actions ask before they run" shows "Confirm to clear local data." before the box. Confirm clears this browser's storage and calls `POST /auth/sign-out`. The account file is not deleted.
**Verify:** After clear, reload is Log in (or the splash). A hosted season is still there on the next log-in. A local account file is still on the machine.

---

## Seasons and deleting past seasons

`page_past_seasons`. A goal date of today is still current and cannot be deleted. Deleting asks with the stats first.

### U1. Past seasons list

**Sees:** Heading "Past seasons". Each row shows Start date, Goal date, and Goal time. The link text is those three, and it opens that season's plan. Empty: "No seasons on this account." Unreadable: "This account's seasons could not be read."
**Now:** `page_past_seasons`, `_past_entry`; `ui/past_seasons.py` `entry_fields`, `season_entries`
**API:** `GET /seasons/past` (`today`, `seasons[].inputs`, `seasons[].stats`, `open[]` for a goal date of today or later). Dates use the saved date format. Opening a row is `GET /plan` with the four inputs. That read does not call `sequence()` and does not save.
**Step 3:** 3.8
**Status:** done
**Evidence:** `web/e2e/past-seasons.spec.ts` "two stored seasons list start, goal, and time" and "opening a past season loads those inputs". `tests/test_api_step3_past.py` `test_the_list_keeps_the_current_season_beside_past_ones` and `test_opening_a_stored_season_does_not_build_a_new_one`. Short dates are "Jan 6, 2020". ISO stays `2020-01-06`. An unreadable file shows "This account's seasons could not be read." Empty is "No seasons on this account."
**Verify:** Two stored seasons. Each row's three values match Start. Opening one does not build a new season. It loads those four inputs.

### U2. Current season has no delete

**Sees:** No "Delete season" on a row whose goal date is today or later.
**Now:** `page_past_seasons`; `ui/past_seasons.py` `is_past_season`
**API:** `DELETE /seasons/past` `409` when the goal date is today or later. That season is in `open`, not `seasons`.
**Step 3:** 3.8
**Status:** done
**Evidence:** `web/e2e/past-seasons.spec.ts` "the current season has no delete control". `tests/test_api_step3_past.py` `test_a_season_ending_today_cannot_be_deleted`. The row for today has no "Delete season". Yesterday does. The API returns 409 for the season that ends today.
**Verify:** A season ending today has no delete control. A season that ended yesterday does.

### U3. Delete asks with stats first

**Sees:** "Delete season" opens "Delete this season?" and the stats, then "This permanently deletes this season and the workouts stored with it. It can't be undone." Buttons "Delete permanently" and "Cancel". Stats, when the season has them: Season, Goal time, Event, Workouts logged, Workouts completed, Distance logged, Phases completed, Notes, Insights, Adaptations, Last 800, Best 800. A missing fact is left out, not shown as zero.
**Now:** `_past_summary_html`; `ui/past_seasons.py` `season_summary`
**API:** `GET /seasons/past` `stats` is this panel. `DELETE /seasons/past` needs `confirm: true` plus the inputs. `400` without confirm. `404` when that season is not on the account.
**Step 3:** 3.8
**Status:** done
**Evidence:** `web/e2e/past-seasons.spec.ts` "delete asks with the stats, then removes only that season". `tests/test_api_step3_past.py` `test_delete_still_needs_confirm_and_leaves_the_other_season`. Cancel sends no delete. Confirm shows "Season deleted." The other past season and the current season stay. A missing count is not shown as zero.
**Verify:** Open delete. The stats are visible before "Delete permanently". Cancel closes the panel and deletes nothing. Confirm shows "Season deleted." and the row is gone. The other seasons stay.

---

## About and Creators

Locked copy. Step 3.9 does not rewrite it. About shows the short paragraphs. The longer ones stay in the page, hidden, so a check of the full text still finds them.

### O1. About hero and credit

**Sees:** Index "About", heading "About", on the stadium photo, with "Photo by Botond Dobozi on Pexels".
**Now:** `page_about`; `theme.ABOUT_CREDIT`
**API:** MISSING (static)
**Step 3:** 3.9
**Status:** done
**Evidence:** `web/e2e/about-creators.spec.ts` "about shows the stadium photo, the credit, and the eight phases". The index and the heading are both "About". The credit on the banner is "Photo by Botond Dobozi on Pexels". `tests/test_web_about_creators.py` diffs that text against Streamlit.
**Verify:** Credit is on the banner. See C6.

### O2. Eight phases

**Sees:** Title "Eight phases". The two intro sentences (six-day week, Sunday Monday Wednesday easy, Tuesday and Thursday hard, Saturday long, Friday off; phase 8 is a shorter taper and the 800 can sit on the last Saturday). Then "Phase 1" through "Phase 8" with the family line from the season. Then the closing on how weeks are filled.
**Now:** `page_about`; `ui/about.py` `about_sections`, `_PHASE_INTRO`, `phase_rows`, `_PHASE_CLOSE`
**API:** MISSING (static). Families come from `engines/season.py` `_PRIMARY` and `_SECONDARY`, not from a model.
**Step 3:** 3.9
**Status:** done
**Evidence:** `web/e2e/about-creators.spec.ts` reads the eight phase rows in order, including "The short fast reps step up from phase 1." and "The taper stays fresh. No hard speed endurance or anaerobic work." The page has no probability line. `tests/test_web_about_creators.py` diffs the rows against `phase_rows()`.
**Verify:** Eight rows. Phase 2 mentions the step up from phase 1. Phase 8 says the taper stays fresh. No score.

### O3. 10% rule, classification, hard days

**Sees:** The short paragraphs in `ui/about.py` `_SHOWN`, under "10% rule", "Classification", and "Hard days". Classification on screen does not mention $25. Hard days say Tuesday and Thursday, within 3%, on track, falling short moves later weeks back one phase, doing better moves them forward and stops at phase 7, phase 8 stays the taper, falling short wins.
**Now:** `page_about` uses `shown` when it is set, and puts `_TEN_PERCENT`, `_CLASSIFICATION`, and `_HARD_DAYS` in a hidden div
**API:** MISSING (static)
**Step 3:** 3.9
**Status:** done
**Evidence:** `web/e2e/about-creators.spec.ts` compares the visible paragraphs with `_SHOWN` and finds "Those calls stop once recorded spend reaches $25." only inside the hidden div. `tests/test_web_about_creators.py` diffs both lists against `ui/about.py`.
**Verify:** The visible classification paragraph is the `_SHOWN` one. The hidden div still contains "Those calls stop once recorded spend reaches $25." Do not delete the hidden paragraphs.

### O4. Creators

**Sees:** Heading "Built by a runner, for runners." with banner "Creators". Photo of Chase with alt "Chase Rose exploding out of the starting blocks." Name "Chase Rose, Founder". Three paragraphs: Bentley Upper School and soccer and track; the small school and training for the 800; the patellar tendon injury and "That's why I built RIO. The plan adjusts to what you actually run instead of pushing you past it." Close: "Every rep has a reason." No photographer credit. The Jay Rose placeholder bio is only in an HTML comment.
**Now:** `page_creators`; `theme.CHASE_PHOTO` (no credit, `theme.py`); `ui/creators.py` `CREATORS` is the hidden placeholder
**API:** MISSING (static)
**Step 3:** 3.9
**Status:** done
**Evidence:** `web/e2e/about-creators.spec.ts` "creators shows Chase and keeps the Jay Rose placeholder in a comment". The three paragraphs and "Every rep has a reason." are visible. The HTML comment still has the Jay Rose placeholder and is not in the visible text. There is no "Photo by" line. `tests/test_web_about_creators.py` diffs the comment against `page_creators`.
**Verify:** The three visible paragraphs match, including "Every rep has a reason." The comment still contains the Jay Rose placeholder. It is not visible. No photo credit line.

---

## Footer and nav

### F1. Contact footer

**Sees:** "Questions or feedback? Email chasejrose5@gmail.com" on the splash, on auth, and under signed-in pages. On a photo it is light type.
**Now:** `_contact_footer`
**API:** MISSING (static)
**Step 3:** PR #61 for the shell. Splash is unassigned (S7).
**Status:** done
**Verify:** The mailto is on Log in, Home, and a placeholder page. The address is chasejrose5@gmail.com. It is also on the splash.

### F2. Nav

**Sees:** "RIO" (home), "Home", "Plan", "Activity", "Library", "More", "Start session", "Log out". Admin email also sees "Admin" (K1). The active tab has an orange underline.
**Now:** `_render_nav`
**API:** none. Log out is `POST /auth/sign-out` (cookie cleared).
**Step 3:** PR #61
**Status:** partial
**Gap:** Gap 10 and Gap 11. Labels and Log out match (`Nav`). Start session has no date. Admin never shows, because `role` stays `athlete`.
**Verify:** Each tab. Log out returns to Log in and a reload stays logged out. The active tab is underlined.

### F3. More subnav and page

**Sees:** Under More: "Past seasons", "Profile", "Settings", "About", "Creators". The More page heading is "More" and the subtitle is "The rest of the season, still in this tab." Each card has a blurb: "Seasons you have already saved." "Your current 800, goal, and dates." "Name, pace, and this account." "Phases, the 10% rule, and what a mark changes." "Chase Rose, Founder."
**Now:** `_render_subnav`, `page_more`, `_MORE_BLURB`
**API:** MISSING (static)
**Step 3:** PR #61 drew the subnav. The More page body is not in the plan as its own step; it is the index for 3.6–3.9 and 3.8.
**Status:** done
**Evidence:** `web/e2e/profile.spec.ts` "the More menu lists the five pages". Past seasons, Settings, About, and Creators still open their current routes. Profile opens the profile page.
**Verify:** More shows five cards with those blurbs, and each opens its page. The subtitle matches.

---

## Photo credits per page

The string is the whole credit. Do not add a photographer where the file has none.

### C1. Startup

**Sees:** "Photo by Giant Asparagus on Pexels".
**Now:** `ui/startup.py` `PHOTO_CREDIT`. Photo `startup_track`.
**API:** MISSING (static)
**Step 3:** Unassigned
**Status:** not started
**Verify:** On the splash, not on Log in.

### C2. Log in and create account

**Sees:** "Photo by Steve Pancrate on Pexels". The repo has no Pexels URL stored for this file.
**Now:** `theme.LOGIN_CREDIT`. Photo `login_floodlights.jpg`.
**API:** MISSING (static)
**Step 3:** PR #61
**Status:** done
**Verify:** Sign-in, create, forgot, and reset.

### C3. Home

**Sees:** "Photo by Gaby Lopez on Pexels".
**Now:** `theme.HOME_CREDIT`. Photo `home_aerial.jpg`.
**API:** MISSING (static)
**Step 3:** PR #61
**Status:** done
**Verify:** Home only.

### C4. Start

**Sees:** "Photo by Bohdan Hyrovych on Pexels".
**Now:** `theme.START_CREDIT`. Photo `start_line.jpg`.
**API:** MISSING (static)
**Step 3:** 3.1
**Status:** done
**Verify:** Start only.

### C5. Plan

**Sees:** "Photo by Jan van der Wolf on Pexels".
**Now:** `theme.PLAN_CREDIT`. Photo `plan_curve.jpg`.
**API:** MISSING (static)
**Step 3:** 3.2
**Status:** done
**Verify:** Inside the Plan hero.

### C6. About

**Sees:** "Photo by Botond Dobozi on Pexels".
**Now:** `theme.ABOUT_CREDIT`. Photo `about_stadium.jpg`.
**API:** MISSING (static)
**Step 3:** 3.9
**Status:** done
**Evidence:** `web/e2e/about-creators.spec.ts` "about shows the stadium photo, the credit, and the eight phases". The credit sits on the About banner, over `photos/about.jpg`.
**Verify:** On the About banner.

### C7. Creators

**Sees:** Chase's photo, and no credit line. `chase_blocks.jpg` has no photographer on record.
**Now:** `page_creators`; `theme.py` comment on `CHASE_PHOTO`
**API:** MISSING (static)
**Step 3:** 3.9
**Status:** done
**Evidence:** `web/e2e/about-creators.spec.ts` "creators shows Chase and keeps the Jay Rose placeholder in a comment". The image alt is "Chase Rose exploding out of the starting blocks." and the page has no "Photo by" line.
**Verify:** The photo has the alt text from O4 and no "Photo by" line.

### C8. Admin hero frames

**Sees:** Each startup frame's own credit, edited in Admin. Defaults include "Photo by RUN 4 FFWPU on Pexels" and the other lines in `ui/assets/hero_rotation.json`.
**Now:** `ui/hero_config.py`; admin `_render_hero_editor`
**API:** `PR #61: GET /admin/hero` and `PUT /admin/hero`
**Step 3:** Unassigned
**Status:** not started
**Verify:** The credit field round-trips. The live splash does not rotate these frames (K6).

---

## Admin and test-season tools

Admin is the email in `RIO_ADMIN_EMAIL`. Anyone else who opens `/admin` is sent Home. Fixture pages (Last Session, Next, Decisions, Ledger, Goal) are registered but not in the nav. A non-admin who opens one is sent Home (`_fixture_allowed`).

### K1. Admin gate and hero

**Sees:** Heading "Admin" and "Accounts and the startup photos." Non-admins never see this. They land on Home.
**Now:** `page_admin`; `ui/access.py` `viewer_is_admin`
**API:** `PR #61: GET /admin/accounts` and the other `/admin` routes. A non-admin is `403` "That page is for the admin account."
**Step 3:** Unassigned
**Status:** not started
**Gap:** Gap 11. The nav check uses `role === "admin"`, which sign-in never sets.
**Verify:** The admin email sees the tab and the heading. Another account does not see the tab, and `/admin` sends them Home.

### K2. Account list

**Sees:** A table of Email, Name, and Role, note "Read only." Empty: "No accounts yet." No server key: "The account list isn't available on this server yet."
**Now:** `page_admin`
**API:** `PR #61: GET /admin/accounts` `{available, accounts}`. Passwords and tokens are not in the body.
**Step 3:** Unassigned
**Status:** not started
**Verify:** The table has no password column. `available: false` shows the "isn't available" sentence.

### K3. Test season

**Sees:** "Test season". "A separate TEST athlete with an 800 m season and eight weeks of runs. This login is not changed." Buttons "Load test season", "View test Home", "View test Plan", "View test Activity". Delete: "Remove the TEST athlete and all of its data" must be checked, then "Delete test season". Notes: "TEST Athlete is loaded." and the removed message. Unchecked delete: "Confirm the delete first."
**Now:** `ui/sample_season_ui.py` `render_test_season`
**API:** `PR #61: POST /admin/test-season`, `GET /admin/test-season`, `DELETE /admin/test-season` `{confirm: true}`
**Step 3:** Unassigned
**Status:** not started
**Verify:** Load does not change the admin's own plan. View opens the test Home. Delete with the box removes it. Delete without the box does not.

### K4. Test preview banner

**Sees:** "TEST Athlete · read only. This login is not changed." and "Back to admin".
**Now:** `ui/sample_season_ui.py` `preview_banner`
**API:** `PR #61: GET /admin/test-season` is the read-only preview. It must not replace the caller's season.
**Step 3:** Unassigned
**Status:** not started
**Verify:** The banner is on the preview. Back to admin restores the admin's season. Logging a result in the preview does not write the admin's plan.

### K5. Hero editor

**Sees:** "Startup photos". "Show, reorder, or edit the credit line." Per photo: "Show on the startup page", "Credit line", "Move up", "Move down", and "Save photos". Success: "Startup photos saved." A bad save is red.
**Now:** `_render_hero_editor`; `ui/hero_config.py` `load_rotation`, `save_rotation`
**API:** `PR #61: GET /admin/hero`, `PUT /admin/hero` body `{photos: [{id, enabled, credit}]}`. The id list must be the startup set, each once.
**Step 3:** Unassigned
**Status:** not started
**Verify:** Reorder, hide one, edit a credit, save, reload. The JSON matches. A credit that fails the check is not written.

### K6. The splash does not rotate

**Sees:** The splash is always the Giant Asparagus track (S1). Saving hero frames does not change it. `enabled_frames` is not called from `ui/startup.py`.
**Now:** `ui/startup.py`; `ui/hero_config.py`
**API:** `PR #61: GET /admin/hero` is the editor's read. The splash has no route.
**Step 3:** Unassigned
**Status:** not started
**Verify:** After K5, a fresh session still shows the track photo, not the first enabled frame. Do not invent a rotation the live app does not have.

### K7. Fixture pages

**Sees:** Last Session, Next, Decisions, Ledger, and Goal, by URL only, admin only. Last Session and Next: a "Session" or "Intervals file" select, or "No session files." Decisions: "Planned" or "No planned rows." Ledger: cards "Deposits", "Emerging", "Decaying", banner "FIXTURE". Goal: the four `goal.yml` fields. Empty table cells are "—".
**Now:** `page_last_session`, `page_next`, `page_decisions`, `page_ledger`, `page_goal`
**API:** `PR #61: GET /fixtures`, `POST /fixtures/classify`, `POST /fixtures/prescribe`, `POST /fixtures/accept`, `GET /fixtures/ledger`, `GET /fixtures/goal`. Lap rows and rep times from an Intervals file are X3. Prose is `POST /insights/explain` (Q3).
**Step 3:** Unassigned
**Status:** not started
**Verify:** A non-admin opening `/last-session` lands on Home. The admin sees the fixture banner and no score.

`page_progress` is not in `st.navigation`. It is not a live screen. Do not add it unless Streamlit does.

---

## Workout insight, explain notes, and the $25 cap

The model writes prose only. It does not classify, prescribe, or score. A hard-day note is stored on the season. Over the cap, the rules paragraph is what the person sees, with no mention of the cap.

### Q1. Workout note

**Sees:** A headline and a body. Optional expander "Carry forward". Button "Got it", which hides it.
**Now:** `_show_stored_insight`. The note is produced by `engines/explain.py` `complete_insight` and kept on the season.
**API:** `POST /seasons/current/results` and `POST /seasons/current/watchless` return `insight.status` of `pending`, `ready`, or `skipped` and do not wait. `GET /insights/workout/{date}` reads it. "Got it" is `POST /seasons/current/notes` with `viewed: true`. A note has `headline`, `body`, `carry_forward`, and `used_result_band` (`on_track`, `fell_short`, or `went_better`).
**Step 3:** Home display is PR #61 (the card is in `HomeView`). Generating it is 3.3.
**Status:** partial
**Gap:** The Home card matches, including Got it, for a note already on `GET /home` `season.notes`. Nothing in the web app logs a workout, so a new note is never requested. Session does not show the card (W11).
**Verify:** Log a hard day. The plan saves even if the note is still pending. When the note is ready, Home and Session show it. Got it hides it. A note that fails the shape check is not shown and the plan stays saved (`note_saved: false`).

### Q2. What does not get a model note

**Sees:** Nothing. Easy days, long runs, and a Done with no time do not grow a note. The phase bar on Home is the authored story (H7), not this note.
**Now:** the insight queue in `page` result paths; `ui/insights.py` `phase_story`
**API:** `insight.status` `skipped` when the day does not take a model note. `POST /insights/workout` with a date that is not a hard day returns `skipped` and does not call the model.
**Step 3:** 3.3
**Status:** not started
**Verify:** Log an easy run. No insight card appears. The network does not wait on a model.

### Q3. Explain prose on fixture pages

**Sees:** A paragraph under the family and the reason codes, on Last Session, Next, and Decisions. It is the rules paragraph, or a rephrase that did not change the family, the template, or the reasons. A bad rephrase is dropped.
**Now:** `_shown_prose`, `render_session`; `engines/explain.py` `explain`, `explain_prescription`, `explain_decision`
**API:** `POST /insights/explain` (`kind` `classification`, `prescription`, or `decision`). The finished `text` is the rules paragraph when the model is unset or refuses the rephrase.
**Step 3:** Unassigned
**Status:** not started
**Verify:** With no model key, the paragraph is the rules text. A rephrase that changes the family is not shown.

### Q4. The $25 cap

**Sees:** No cap message. Past $25 of recorded spend, the person still sees the rules paragraph. About's hidden classification paragraph is the only place the "$25" sentence exists (O3).
**Now:** `engines/explain.py` (the cap check returns the rules text). Spend file `RIO_EXPLAIN_SPEND_PATH`, otherwise `data/explain_spend.json`.
**API:** `POST /insights/explain` and `POST /insights/workout` already enforce it. There is no spend route. PR #61's contract says Streamlit and the API share one counter after migration 011. Until then both use the file. Do not keep two counters.
**Step 3:** Unassigned for the fixture prose. Workout notes are 3.3.
**Status:** not started
**Verify:** Drive the recorded spend to the cap in a local file. The next note or rephrase is the rules text. The UI does not say "$25" and does not show a score.

### Q5. A note must not carry a lap stream

**Sees:** The note never lists laps, a Strava payload, GPS, or a score.
**Now:** the shape check before the model is called
**API:** `POST /insights/workout` `400` before the model when the payload has a lap list or the word Strava. Sending `{date}` builds the payload on the server.
**Step 3:** 3.3
**Status:** not started
**Verify:** The browser posts a date, not a lap array. A hand-built payload with laps is rejected and the model is not called.

---

## Error and empty states

Screen-specific sentences are on their items (T8, W2, Y3, M3, U1, Settings G10). These are the ones that show up in more than one place.

### X1. Generate a season on Start

**Sees:** The link "Generate season plan", or the note "Generate a season on Start.", on Home, Plan, Activity, Library's neighbors, Session, Profile, and Settings export, whenever there is no season.
**Now:** `_season_prompt` and the per-page branches
**API:** `GET /seasons/current` `404` "No current season." `GET /home` `copy` when `season` is null.
**Step 3:** Each page's step. Home's version is done in PR #61 (H2). Profile is 3.6. Settings export is 3.7.
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "settings export without a season points at Start" shows "Generate a season on Start." Profile already has that note and "Generate season plan". Home, Plan, Session, and Activity already link to Start. Library loads the menu with no season, which is the Streamlit page.
**Verify:** On each of those pages, with no season, the person can get to Start. They never see a blank plan.

### X2. An em dash for an empty value

**Sees:** "—" for a missing tile, an empty week, a missing heart rate, a blank table cell, or a reason with no text.
**Now:** `_page` helpers and `_table`
**API:** The season and screen routes use "—" in labels the contract already names (`next_days.label`, focus, phase).
**Step 3:** Each page's step
**Status:** partial
**Gap:** Home, Plan, Session, and Activity use "—" for an empty value. A rest day on Home stays "Rest day" (H10). Library uses "—" for a missing name or capacity, and "No workouts." when a search matches nothing (M3). Profile uses "—" for a blank Start value (`tests/test_api_step3_profile.py` `test_a_blank_start_value_is_an_em_dash` and `web/e2e/profile.spec.ts`). The later pages are still open.
**Verify:** A missing focus tile is "—". A rest day is not.

### X3. Intervals file body

**Sees:** Laps (distance, seconds, rest) and rep times filled from a chosen JSON file, on Last Session and on the admin Session picker (W13).
**Now:** `ui/last_session.py` `open_intervals`; `_intervals_choice`
**API:** `GET /fixtures/intervals/{name}` returns `laps`, `rows`, and `times`. `GET /fixtures/session` is the YAML fixture. Admin only.
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** Admin only. A known fixture fills the same seconds Streamlit shows. A non-admin cannot open the picker.

### X4. Account could not be opened or saved

**Sees:** "This account could not be opened." "This account could not be saved." "This session could not be saved."
**Now:** `ui/accounts.py`; `_enter_account`
**API:** The auth routes' `detail`
**Step 3:** PR #61 for sign-in. Settings writes are 3.7.
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "save failures use the account sentences" shows "This account could not be opened.", "This session could not be saved.", and "This account could not be saved." in `.rio-error`. Sign-in already shows `detail`.
**Verify:** Each sentence can appear, escaped, in `.rio-error`. No traceback.

---

## Rate-limit messages

### RL1. Sign-in

**Sees:** "Too many sign-in attempts. Wait a few minutes and try again."
**Now:** `SIGNIN_RATE`. Item L6.
**API:** `POST /auth/sign-in` `429`
**Step 3:** PR #61
**Status:** done
**Verify:** The sentence is exact. The form stays.

### RL2. Sign-up

**Sees:** "Too many sign-up attempts. Wait a few minutes and try again."
**Now:** `SIGNUP_RATE`. Item N4.
**API:** `PR #61: POST /auth/sign-up` `429`
**Step 3:** PR #61
**Status:** done
**Verify:** Same as RL1, on create account.

### RL3. Strava

**Sees:** "Strava is busy. Try again in a few minutes."
**Now:** `ui/strava.py`. Item Y8.
**API:** `POST /strava/sync` `429`
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** The busy sentence. `last_sync_at` does not move.

### RL4. Intervals

**Sees:** The Activity page does not show the raw "Intervals.icu returned 429…" line. It shows "Runs could not be loaded. Try Refresh in a moment."
**Now:** `_activities_notice`. The adapter text is in `adapters/intervals_icu.py` and is not what the page prints.
**API:** `POST /strava/sync` `notice` when the fallback fails
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** A 429 from Intervals becomes the "Try Refresh" sentence, not the adapter sentence.

---

## Session persistence and the 1-day token

The live app keeps a signed token for one day. Refreshing does not extend it. Log out clears it. The API's cookie is the same clock.

### D2. One day, then log in again

**Sees:** Close the tab and come back the same day: still signed in. Come back after 24 hours from the original sign-in: Log in. Reloading at 23 hours does not buy another day.
**Now:** `ui/accounts.py` `issue_session`, `open_session` (`_SESSION_MAX_AGE` is 86400). Hosted: `ui/cloud_session.py` `cookie_max_age`, `SESSION_SECONDS`. The browser key for a local token is `rio.session.v1`. The hosted cookie name is `rio_hosted`.
**API:** `POST /auth/sign-in` sets `rio_hosted` (`HttpOnly`, `Secure`, `SameSite=Lax`) with `max_age` from `cookie_max_age` (`api/identity.py` `set_session_cookie`). A missing or expired cookie is `401` "Sign in again." The token and the seal are not in the cookie and not in these responses.
**Step 3:** PR #61
**Status:** partial
**Gap:** Gap 1. The web is supposed to send the cookie with `credentials: "include"` (`web/README.md`). The module that does it is not in the commit. Local Streamlit also writes `localStorage`. The API design does not, and the web should not copy the seal into `localStorage`.
**Verify:** Sign in, reload at once, still in. Set the cookie's clock forward a day, reload, Log in. Confirm the cookie is HttpOnly and the response body has no token.

### D3. Log out

**Sees:** "Log out" clears the account and the browser token or cookie. The next page is Log in, after the splash if that session has not continued past it.
**Now:** `_sign_out`, `_render_nav`
**API:** `POST /auth/sign-out` clears the cookie
**Step 3:** PR #61
**Status:** done
**Verify:** Log out, then Back. The app does not reopen the season. The e2e can assert the sign-out call.

### D4. A deep link stays put

**Sees:** Reloading Plan, Settings, or a session does not send the person to Home. Opening the root or Home does the Home-versus-Start choice.
**Now:** `_open_restored_session`; `ui/cloud_session.py` `load_is_app_root`
**API:** none for the rule. The page's own GET is what it reloads.
**Step 3:** PR #61 for the shell. Each page must keep it.
**Status:** partial
**Gap:** A signed-in visit to `/plan` stays, because only `/` uses `Gate`. That part matches. Signing in always `replace("/")`, which also matches a fresh log-in (Streamlit sets `rio_enter` and leaves the deep link). Gap 13: the function that chooses Home or Start is not in the commit.
**Verify:** Signed in, open `/plan` directly. Stay on Plan. Open `/`. Go to Home or Start by the goal date, not always Home.

---

## Routing rules

### D5. Home when the goal is today or later

**Sees:** After log-in, create, or a restored session at the root: Home if any stored season's goal date is today or later, in the Settings time zone. Otherwise Start. No season is Start. A goal date of today is Home. A goal date of yesterday is Start.
**Now:** `_route_after_login`; `ui/past_seasons.py` `landing_target`, `has_active_plan`. The default page in `st.navigation` uses the same rule, so `/` is Home or Start.
**API:** `GET /seasons/current` is 404 when every season is past (`open_season` skips `is_past_season`). Today on that call is the Settings time zone.
**Step 3:** PR #61
**Status:** partial
**Gap:** Gap 13. The e2e checks 200 versus 404 only. It does not check a goal date equal to today.
**Verify:** Three accounts, or one account edited between runs: no season → Start; goal today → Home; goal yesterday → Start. Then Gap 2 still puts easy pace and the intro in front of that page when they are due.

### D6. Gates before the page

**Sees:** On the way to that Home or Start: easy pace if none is saved, then the intro if it is due, then the page. Order is fixed.
**Now:** `_with_plan`
**API:** `GET /auth/me` `prefs.easy_pace`, `prefs.intro_seen`
**Step 3:** 3.1
**Status:** done
**Verify:** The screenshot sequence in N6. Brand-new account: easy pace, then the intro, then Start.

### D7. Unsigned visitors

**Sees:** Only Log in (after the splash). No nav. No Home.
**Now:** the `st.stop()` after `_render_login`
**API:** `401` on any cookie route
**Step 3:** PR #61
**Status:** done
**Verify:** Open `/home` signed out. Land on `/sign-in`. The nav is absent.

---

## Time-zone-aware today

### D1. Today

**Sees:** "Today" on the calendar, the Home workout, the landing rule, and the default Start date is the calendar date in the Settings time zone, not the server's zone. A blank or unknown zone falls back to the browser zone, then UTC.
**Now:** `ui/settings.py` `local_today`, `session_timezone`, `suggested_timezone`; `ui/streamlit_app.py` `_athlete_today`
**API:** `today` on `GET /auth/me`, `GET /home`, and `GET /seasons/current`. The contract says it is `YYYY-MM-DD` in the saved time zone. The zone is `PATCH /settings` `timezone`, one id from the Settings list.
**Step 3:** PR #61 for landing and Home. Start's default date is 3.1. The calendar cell is 3.2. The control is 3.7 (Settings G2).
**Status:** done
**Evidence:** `tests/test_api_step3_settings.py` `test_the_saved_zone_decides_today_on_home_and_plan`. At 2026-11-10 18:00 UTC, `Pacific/Auckland` makes `today` 2026-11-11 on `GET /auth/me`, `GET /home`, and the Plan calendar cell. `Pacific/Honolulu` makes that day 2026-11-10. The Settings select is the control.
**Verify:** Set the zone to `Pacific/Auckland` and compare with UTC around midnight. Home, the calendar's today cell, and Home-versus-Start agree. Document the zone in the screenshot.

---

## Transitions and animations

`prefers-reduced-motion` collapses the timed motion. That rule has to travel with every animation below.

### A1. Splash fade

**Sees:** Splash copy fades in. Item S8.
**Now:** `ui/startup.py`
**API:** MISSING (static)
**Step 3:** Unassigned
**Status:** not started
**Verify:** With reduced motion, the splash is just there.

### A2. Page fade and rise

**Sees:** The main column fades in about 200ms the first time a page name is shown. Hero numbers, stat tiles, and library rows rise about 8px. A rerun of the same page does not replay it.
**Now:** `ui/theme.py` `motion_rules`, `motion_hold_css`; `ui/streamlit_app.py` `_css`, `_arm_motion`
**API:** MISSING (static)
**Step 3:** Each page's step. Home's stagger is the partial stand-in.
**Status:** partial
**Gap:** Gap 16. Home staggers children. It does not suppress the animation on a same-page reload. Library, Profile, More, Settings, Past seasons, About, and Creators fade once and their blocks rise about 8px. A save on Profile or Settings, opening delete on Past seasons, or a same-page reload of About or Creators does not replay it. The splash fade is still open.
**Verify:** Open Home, then refresh Home. The second time does not replay the rise. Open Plan from Home. Plan fades once.

### A3. Nav underline

**Sees:** The active tab's orange underline grows in. Hover grows it too. It does not replay just because a widget on the page reran.
**Now:** `ui/theme.py` `motion_rules`
**API:** MISSING (static)
**Step 3:** PR #61
**Status:** not started
**Gap:** Gap 16. `Nav` sets `is-active` and does not animate an underline.
**Verify:** The active tab is underlined. Switching tabs animates once. Toggling a control does not.

### A4. Buttons and cards

**Sees:** Buttons lift 1px on hover. Log out does not. Home's day cards lift a little more.
**Now:** `ui/theme.py` `motion_rules`
**API:** MISSING (static)
**Step 3:** PR #61 for Home. Other pages with their steps.
**Status:** not started
**Verify:** Hover a primary button and Log out. Only the primary button moves. Reduced motion: neither moves.

### A5. Plan view rise

**Sees:** Switching Calendar / This week / Full season plays the rise on that view once.
**Now:** `motion_rules` on `.rio-plan-view-*`
**API:** MISSING (static)
**Step 3:** 3.2
**Status:** done
**Verify:** Switch views. The new view rises. Switching back does not loop.

### A6. Reduced motion

**Sees:** Animations collapse. Nothing travels across the screen.
**Now:** `ui/theme.py` `motion_rules` (the reduced-motion block)
**API:** MISSING (static)
**Step 3:** Every step that adds motion, starting with PR #61
**Status:** partial
**Gap:** `web/app/globals.css` has a reduced-motion block that sets `animation: none` on `.page-home`. The splash and the nav are not built, so they cannot honor it yet.
**Verify:** OS reduced motion on. Home does not stagger. Later pages do not fade.

---

## Hidden on purpose

These are in the code and must stay hidden. Shipping them would add something the live app does not show.

### Z1. Google

**Sees:** Nothing. "Continue with Google" exists in `ui/cloud_ui.py` `_google_button` and is not drawn (`SHOW_GOOGLE_SIGN_IN` is false).
**Now:** `ui/cloud_ui.py`
**API:** `PR #61: GET /auth/google` and `GET /auth/google/callback` exist. The button stays hidden, same as Streamlit. The plan says so.
**Step 3:** PR #61
**Status:** done
**Verify:** Log in and create account have no Google control. The e2e asserts that.

### Z2. Check your inbox

**Sees:** Nothing. The "Check your inbox" screen is not shown (`SHOW_SIGNUP_EMAIL_CONFIRM` is false). A signup that needs confirmation shows "The account could not be created." instead.
**Now:** `ui/cloud_ui.py` `_render_confirm`, `_visible_auth_error`
**API:** `PR #61: POST /auth/sign-up` can return `{confirm: true, message: "Check your email to confirm your account, then log in."}`. The web maps `confirm` to `SIGNUP_FAILED`, which matches Streamlit.
**Step 3:** PR #61
**Status:** done
**Verify:** A confirm response does not open an inbox screen. It shows "The account could not be created."

### Z3. Synthetic and demo badges

**Sees:** Nothing. Heroes are called with "SYNTHETIC / DEMO" and `_demo_label` drops that banner.
**Now:** `_demo_label`, `_page_hero`
**API:** none
**Step 3:** Every page
**Status:** partial
**Gap:** Home and auth do not show the badge. Unbuilt pages must keep not showing it. Fixture pages may show "FIXTURE" (K7). That one is real.
**Verify:** Home, Start, Plan, Settings, and Activity have no "SYNTHETIC" and no "DEMO".

### Z4. Settings leftovers

**Sees:** Nothing. A hidden div lists Metric, Imperial, Dark, Notifications, Workout reminders, Weekly recap, and "Placeholder. Nothing is sent."
**Now:** `page_settings`
**API:** `PATCH /settings` does not document these. `normalize` still stores `reminders`, `recap`, `notifications`, and `theme`, and nothing is sent.
**Step 3:** 3.7
**Status:** done
**Evidence:** `web/e2e/settings.spec.ts` "settings shows every section, and the hidden leftovers stay hidden". The hidden div still has Metric, Imperial, Dark, Notifications, Workout reminders, Weekly recap, and "Placeholder. Nothing is sent."
**Verify:** Settings has no theme toggle and no notification toggle. The hidden strings are still in the DOM if Streamlit's hidden div is kept, and they are not visible.

### Z5. About's long paragraphs

**Sees:** The short `_SHOWN` text (O3). The long paragraphs, including the $25 sentence, are in a hidden div.
**Now:** `page_about`
**API:** MISSING (static)
**Step 3:** 3.9
**Status:** done
**Evidence:** `web/e2e/about-creators.spec.ts` reads the hidden classification paragraph, including "Those calls stop once recorded spend reaches $25.", and asserts the hidden div is not visible. The visible paragraph is the short `_SHOWN` line.
**Verify:** View source. The long classification paragraph is present and not visible.

### Z6. Jay Rose placeholder

**Sees:** Nothing. The Creators HTML comment holds the placeholder bios from `ui/creators.py` `CREATORS`, including Jay Rose.
**Now:** `page_creators`
**API:** MISSING (static)
**Step 3:** 3.9
**Status:** done
**Evidence:** `web/e2e/about-creators.spec.ts` finds the HTML comment from `page_creators` in the page source. The visible article is Chase only. "Jay Rose" is not in the visible text.
**Verify:** The comment is in the page. The visible article is Chase only (O4).

### Z7. Legacy activity tables

**Sees:** Nothing. The old "Sessions" and "All activities" tables sit in a hidden `rio-legacy-activity` block, including "No matched activities."
**Now:** `page_activity`
**API:** `GET /activities` still returns `rows` and `all`, which those tables used. The visible UI is the cards (Y6).
**Step 3:** 3.4
**Status:** done
**Evidence:** `web/e2e/activity.spec.ts` and `tests/test_api_step3_activity.py`. Fresh side-by-sides on PR #66: activity, the error state with the stored runs still showing, and Last Session laps.
**Verify:** The visible Activity page is cards and the heart chart. The old tables are not on screen. Do not drop `rows` and `all` from the API. The hidden block can stay hidden.

### Z8. Planned versus actual

**Sees:** Nothing. `ui/strava_ui.py` `home_line` ("Planned vs actual") is not called from Home.
**Now:** `home_line` is unused by `page_dashboard`
**API:** none
**Step 3:** PR #61
**Status:** done
**Verify:** Home has no "Planned vs actual" card. Do not add one.

---

## What a later PR ticks

The PR that owns a step marks each of its items `done` in this file only after the **Verify** line is true against the running web app, with a screenshot or a test named in the PR. Partial items in PR #61 stay partial until the gap on that row is gone. Do not tick an item because the placeholder route exists.

Build order from the plan, after PR #61:

1. Start, the intro, and easy pace (3.1), including Gap 2.
2. Plan (3.2).
3. Start session and Session (3.3).
4. Activity and Strava (3.4).
5. Library (3.5).
6. Profile (3.6).
7. Settings (3.7).
8. Seasons and past seasons (3.8).
9. About and Creators, locked (3.9).

Splash, admin, the test season, hero editing, and the fixture pages are not in that list. They stay in this checklist so they are not dropped.
