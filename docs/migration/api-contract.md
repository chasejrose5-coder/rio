# API contract

The FastAPI app in `api/` is the backend for the Next.js app. The Streamlit app is still the live site and does not call these routes. Every route below is implemented. Shapes are JSON.

Auth, unless a route says otherwise, is the `rio_hosted` cookie set by `POST /auth/sign-in`. The value is an opaque `rio1.` id. The cookie is `HttpOnly`, `Secure`, and `SameSite=Lax`. Lax is what lets the Strava redirect send the cookie back. The Supabase access token and the local seal stay on the server. They are not in the cookie, not in `localStorage`, and not in these responses.

A missing or expired cookie is `401` `{"detail": "Sign in again."}`.

Errors from the app are `{"detail": "<sentence>"}`. A body that is not the shape below is `422` from the framework. `400` is a rejected value. `403` is a page this login is not allowed to open. `404` is a missing season, day, or job. `409` is a conflict (Strava already connected, or deleting the current season). `412` is a stale `If-Match` digest. `429` is a rate limit (Strava, or too many sign-up or sign-in attempts). `503` is Strava or Google not configured, or migration 010 not applied.

The browser origin that may call the API with credentials is `RIO_FRONTEND_ORIGIN` (default `http://localhost:3000`). A wildcard is refused.

Model keys (`RIO_EXPLAIN_API_KEY`, `RIO_EXPLAIN_MODEL`, `RIO_EXPLAIN_BASE_URL`) are read from the environment only. A request cannot pass a key.

## Shared shapes

`inputs`:

```json
{"current_time": "2:02.9", "start_date": "2026-04-19", "goal_time": "1:55.0", "goal_date": "2027-03-19"}
```

`prefs` on the athlete and on a season:

| Field | Values |
| --- | --- |
| `timezone` | An id from the Settings list, such as `Pacific/Auckland` |
| `pace_units` | `mi` or `km` |
| `no_watch` | bool |
| `easy_pace` | `m:ss`, or `""` |
| `easy_pace_unit` | `mi` or `km` |
| `easy_pace_phrase` | Display text, or `""` |
| `units` | `miles` when pace is `mi`, otherwise `km` |
| `date_format` | `iso` or `short` |
| `start_date` | `today` or `sunday` |
| `confirm_adapt` | bool. The client shows the confirm dialog. The API applies the mark on POST. |
| `today` | `YYYY-MM-DD` in the saved time zone. Popped onto the parent object on season and athlete responses. |
| `logging` | `done` when `no_watch` is true, otherwise `times` |
| `intro_seen` | `true`, `false`, or `null` when the athlete has not stored it |
| `strava_prompt_seen` | bool |
| `preferred` | Nickname, or `""` |

`season` (the body of the season routes):

| Field | Meaning |
| --- | --- |
| `inputs` | The four Start fields |
| `plan` | The season dict from `sequence` / `adapt`. `probability`, `readiness`, and `readiness_score` are removed. |
| `marks` | `{"1": "on_track"}`. Choices are `on_track`, `not_hitting`, `smashing`. |
| `actuals` | `{date: row}` |
| `digest` | Hash of inputs, plan, marks, and actuals |
| `notes` | `{date: {"note": insight, "viewed": bool}}` |
| `today` | The athlete's today |
| `prefs` | The table above, without `today` |
| `logging` | `done` or `times` |
| `quality_base_weeks` | Week numbers whose pre-adapt plan is held |
| `quality_base_source` | `stored`, `recomputed`, or `empty` |
| `quality_base_stored` | bool |
| `activities` | Stored rows. A Strava row has `source: "strava"`. Tokens are not included. |

An insight note has `headline`, `body`, `carry_forward`, and `used_result_band` (`on_track`, `fell_short`, or `went_better`).

`athlete` (`GET /auth/me` and `PATCH /settings`):

```json
{"id": "", "email": "", "display_name": "", "role": "athlete", "kind": "hosted", "today": "2026-11-09", "prefs": {}}
```

`kind` is `hosted` or `local`.

## Health

### `GET /health`

No cookie. `200` `{"ok": true}`.

## Auth

### `POST /auth/sign-in`

Body: `{"email": "", "password": ""}`.

`200` sets the cookie and returns `{"email": "", "display_name": "", "kind": "hosted"}`. `401` when the email or password does not match. The body never includes a token or a seal.

### `POST /auth/sign-out`

Cookie. `200` `{"ok": true}` and the cookie is cleared.

### `GET /auth/me`

Cookie. `200` is `athlete`.

### `POST /auth/sign-up`

No cookie. Body: `{"email": "", "password": "", "name": ""}`.

`200` when the account is created and a session exists. The cookie is set, the same way sign-in sets it. The body is `{"email": "", "display_name": "", "kind": "hosted", "confirm": false}`. `kind` is `local` when this process has no Supabase directory.

`200` `{"confirm": true, "message": "Check your email to confirm your account, then log in."}` when the project creates the user and returns no session. The cookie is not set. The Streamlit login screen still hides that sentence and shows "The account could not be created." The API returns the directory’s outcome so the new client can show the inbox screen.

`400` for a bad email, a bad name, a short password, or an email that already has an account. `429` when sign-up is rate limited. The body never includes a token or a seal.

### `POST /auth/forgot-password`

No cookie. Body: `{"email": ""}`.

`200` `{"ok": true, "message": "Check your email for the reset link."}`. An address with no account gets the same body. The reset token is not in the JSON. `400` when the text is not an email, or when this process is the local account file (that file has no mail). `400` when the reset mail could not be sent.

### `POST /auth/reset-password`

No cookie. Body: `{"token": "", "password": ""}`. `token` is the `token_hash` from the reset link, the same value Streamlit reads.

`200` `{"ok": true, "message": "Password updated. Log in with the new one."}`. `400` when the token is no longer valid, the password is shorter than 8 characters, or this process is the local account file.

### `POST /auth/password`

Cookie. Body: `{"current_password": "", "new_password": ""}`.

`200` `{"ok": true, "message": "Password updated."}`. The cookie stays. A local account is sealed again under that same cookie. `400` when the current password does not match or the new one is too short. `401` when the cookie is missing.

### `POST /auth/email`

Cookie. Body: `{"email": "", "password": ""}`.

`200` `{"ok": true, "email": "", "message": ""}`. A local account moves to the new email and the message is `Email updated.` A hosted account asks auth to change the address. `profiles.email` is not written. Migration 005 keeps that column locked for the signed-in role. On the in-memory directory the message is `Email updated.` On Supabase the message is `Check your email to confirm the new address.` because secure email change can keep the old address until that mail is confirmed. `400` when the password does not match, the email is unusable, or another account already has it.

### `POST /auth/delete`

Cookie. Body: `{"confirm": false, "email": "", "password": ""}`.

`confirm` must be true. `400` `{"detail": "Confirm to delete this account."}` otherwise. The cookie is cleared on success. `200` `{"deleted": true}`.

A hosted delete matches Settings: the checkbox is enough. The signed-in client deletes that athlete’s rows. The service role is used only to delete the auth user, which is what Streamlit already does. Row level security still applies to the row deletes.

A local delete matches Settings too: `email` must be this account’s email, and `password` must match. `400` when either does not.

### `GET /auth/google`

No cookie. `200` `{"url": "", "redirect_uri": ""}`. `url` is `directory.google_url` for `redirect_uri`. `503` when this process has no directory.

`RIO_GOOGLE_REDIRECT_URI` is that redirect. When it is unset, the redirect is the Streamlit callback (`RIO_APP_URL` + `/`, or `http://localhost:8501/`). `ui/cloud_ui.py` still builds its own link with `app_url() + "/"` and the button stays hidden (`SHOW_GOOGLE_SIGN_IN` is false). Set the variable to this API’s callback when the new site should receive the return.

### `GET /auth/google/callback?code=&flow=`

No cookie. The provider redirect is a top-level GET.

JSON, when `X-RIO-Response: json` is set: `200` sets the cookie and returns `{"email": "", "display_name": "", "kind": "hosted", "redirect_uri": ""}`. `400` when the code or the PKCE flow does not check out. A code can be used once.

Without that header the response is `302` to `{RIO_FRONTEND_ORIGIN}/?google=connected`, or `?google=error` when the code does not check out. The cookie is set on the success redirect.

## Seasons

All of these need the cookie. Today follows the Settings time zone. Easy pace, pace units, and no-watch are not passed into `sequence()` or `adapt()`.

A write may send `If-Match` with the `digest` from the season it loaded. Quotes around the digest are ignored. When the header is missing, the later write still wins. When it is present and it is not the current digest, the write is `412` `{"detail": "This season changed in another tab. Reload it and try again."}` and nothing is saved. This covers generate, results, Done, marks, notes, clear, reset, Strava sync, and `POST /insights/digest`. Notes are not part of the digest. A stale tab is still refused before the note is saved.

### `GET /seasons/current`

`200` is `season`. `404` when there is no current season.

### `POST /seasons`

Body is `inputs`. `200` is `season` plus `committed: true` and `strava_offer` (bool). `strava_offer` is true only when this generate just succeeded, Strava is not connected, and the athlete has not dismissed the prompt. `400` when an input is unusable. When all four strings are present, `detail` is the sentence from `sequence()`: "current_time is not an 800 time", "goal_time is not an 800 time", "goal_date is before start_date", "start_date is not a calendar date", or "goal_date is not a calendar date". A missing field stays "Enter a current time, a start date, a goal time, and a goal date." Nothing is stored on `400`. A plan that contains `probability` or `readiness_score` is rejected by `sequence()`.

### `POST /seasons/current/results`

Body:

```json
{"date": "2026-04-21", "text": "57.5", "slots": null, "intervals": null, "note": null}
```

`text` is the entered result. `slots` is an optional list. `intervals` is an optional reference string. `note`, when present, is an insight note to store. A note that fails the shape check is not stored (`note_saved: false`) and the plan stays saved.

`200` is `season` plus `committed` (bool), `note_saved` (`true`, `false`, or `null` when no note was sent), and `insight`:

```json
{"status": "pending", "date": "2026-04-21", "id": ""}
```

`status` is `pending` when a hard-day note was scheduled, `ready` when that date already has a note, or `skipped` when this day does not take a model note. The plan is saved before the model runs. The response does not wait for it. `400` when the date is not in the season or the result cannot be judged.

### `POST /seasons/current/watchless`

Body: `{"date": "", "outcome": "Ahead", "time": "1:12.4", "note": null}`.

`outcome` is `Behind`, `On target`, or `Ahead`. `time` may be empty. `missed: true` stores Couldn't finish: no time, no mark, and later weeks stay put. `200` matches the result route, including `insight`. A time on a hard day adapts later weeks. Done with no time does not. `400` when the date or the time is unusable.

### `POST /seasons/current/marks`

Body: `{"week": 1, "choice": "on_track"}`. `choice` is `on_track`, `not_hitting`, or `smashing`. `200` is `season` plus `committed`. This route does not call the model. `400` when the week or the choice is unusable.

### `POST /seasons/current/notes`

Body: `{"date": "", "note": {}, "viewed": false}`.

`200` is `season` plus `note_saved: true`. This is the Got it write (`viewed: true`) and a hand-saved note. It does not call the model. `400` when the date is not in the season or the note is the wrong shape (including a lap list, Strava, GPS, or a score).

### `POST /seasons/reset`

Body: `{"confirm": true}`. `200` `{"reset": true}`. Every stored season is removed. The account, the name, and the settings stay. `confirm` must be true. `400` otherwise. A stale `If-Match` is `412` and the seasons stay.

### `POST /seasons/current/clear`

Body: `{"confirm": true}`. `200` is `season` plus `committed: true`. The plan is `sequence()` for the same four inputs. Marks, actuals, and quality bases are empty. Notes stay. `confirm` must be true. `400` otherwise.

### `GET /seasons/past`

`200`:

```json
{"today": "2026-11-09", "seasons": [{"inputs": {}, "stats": [{"label": "Season", "value": ""}]}]}
```

`stats` is the confirm panel. Dates use the saved date format.

### `DELETE /seasons/past`

Body is `inputs` plus `confirm: true`. `200` `{"deleted": true, "inputs": {}, "stats": []}`. `400` when `confirm` is not true. `404` when that season is not on this account. `409` when the goal date is today or later.

## Strava

Tokens are stored with the service role (`strava_tokens` in `003_strava.sql`). The signed-in role cannot read that table. Activities stay on `strava_activities`. None of these responses include `access_token` or `refresh_token`.

The OAuth nonce is stored on the server, keyed by the athlete, for ten minutes. It is not written to a cookie or `localStorage`. The authorize URL still carries `state`, because that is how Strava echoes it back. The callback accepts the code only when `state` matches the stored nonce for this cookie. A second callback with the same state is refused. A state that was never stored is refused, even when the signature would match.

`RIO_STRAVA_REDIRECT_URI` is the redirect placed in the authorize URL. When it is unset, the redirect is the Streamlit callback (`RIO_APP_URL` + `/`). `ui/strava.py` `redirect_uri()` is unchanged, so the live Streamlit callback keeps working. Set the variable when the new site's callback is registered with Strava. A browser that lands on `GET /strava/callback` is sent to `{RIO_FRONTEND_ORIGIN}/settings?strava=connected` or `?strava=error`. A client that sends `X-RIO-Response: json` gets the JSON body instead.

Hosted connect needs `supabase/migrations/010_strava_oauth.sql`. Until that has been run, hosted connect returns `503`. The Streamlit app does not read that table.

### `GET /strava/status`

`200`:

```json
{"configured": true, "connected": false, "athlete_name": "", "last_sync_at": null, "redirect_uri": ""}
```

`configured` is false when the Strava client id or secret is missing. `redirect_uri` is empty in that case.

### `GET /strava/connect`

`200` `{"url": "https://www.strava.com/oauth/authorize?...", "redirect_uri": ""}`. `409` when Strava is already connected. `503` when Strava is not configured, or when the hosted nonce table is missing.

### `GET /strava/callback?code=&state=`

Cookie. The Strava redirect is a top-level GET, so the Lax cookie is sent.

JSON, when `X-RIO-Response: json` is set: `200` `{"connected": true, "athlete_name": "", "redirect_uri": ""}`. `400` when the code or the stored nonce does not check out. `401` when the cookie is missing.

Without that header the response is `302` to the frontend settings URL above. A missing cookie still redirects to `?strava=error` unless the JSON header is set, in which case it is `401`.

### `POST /strava/disconnect`

`200` `{"connected": false}`. Strava is deauthorized, and the token and activity rows for this athlete are deleted. Strava rows are also dropped from the open season. `400` when the delete fails.

### `POST /strava/sync`

Body: `{"scope": "recent"}` or `{"scope": "all"}`. `recent` continues from the last successful sync. `all` is the full history (the season start, and at least 120 days).

`200` is `season` plus:

```json
{"synced": true, "scope": "all", "count": 1, "notice": null, "committed": true}
```

`synced` is false and `notice` is set when the import fails. `last_sync_at` does not move on that failure. `committed` is true when a quality day took a mark. That mark uses the stored quality base, so a week is not adapted twice. This route does not call the model.

`429` when Strava's rate limit is hit. `400` when `scope` is neither `recent` nor `all`. `404` when there is no current season.

When Strava is not connected, the same route runs the Intervals fallback (`sync_recent` or `sync_all`) through `services/activity_pull.py`. There is no Intervals OAuth. A missing Intervals key comes back as `synced: false` and a notice.

## Insights

The model runs in a background task. The HTTP response is `pending` and does not wait. `GET` reads the result. A payload that fails the existing checks is `400` and the model is not called. A body that contains `probability`, `readiness`, or `readiness_score` is `400` `{"detail": "A plan with a score is rejected."}` before the model is called.

A finished workout note is also written to `season.notes` for that date. Pending jobs live in this process. After a restart, `GET /insights/workout/{date}` still returns a note that was saved. A job that had not finished is `absent` and can be requested again.

`status` on these objects is `pending`, `ready`, `absent`, or `skipped`.

### `POST /insights/workout`

Body, one of:

```json
{"payload": {}}
```

```json
{"date": "2026-04-21"}
```

`payload` is the reduced hard-day object `insight_inputs_ok` already checks. A bad payload, including a lap list or the word Strava, is `400` before the model. `date` builds that object on the server from the stored season, so the browser cannot add a lap stream. When that day is not a hard day, the response is `{"status": "skipped", "date": "", "id": "", "kind": "workout"}` and the model is not called.

`200` when a note was scheduled:

```json
{"status": "pending", "date": "2026-12-01", "id": "", "kind": "workout"}
```

Saving a plan or a hand-written note does not go through this route and does not wait on it. The result and Done routes schedule the same task after they have saved.

### `GET /insights/workout/{date}`

`200` is the job object: `id`, `kind` (`workout`), `status`, `date`, `note` (the insight or `null`), `text` (`null` here), `viewed` (bool or `null`). `404` when there is no current season.

### `POST /insights/digest`

Body: `{"payload": {}}`. The payload is the hard-day object plus `week_ended: true`. Anything else is `400` before the model, including a week that has not ended. `200` `{"status": "pending", "id": "", "kind": "digest"}`. The digest is not written onto a plan. Read it with `GET /insights/jobs/{id}`.

### `POST /insights/explain`

Body:

```json
{"kind": "classification", "classification": {"family": "speed_endurance", "reason_codes": [], "confidence": "high"}}
```

`kind` is `classification`, `prescription`, or `decision`. Prescription also needs `template_id`, `reason_codes` (a list), and `goal` (an object). Decision needs `template_id` and `reason_codes`. A body that fails those checks is `400` before the model. `200` `{"status": "pending", "id": "", "kind": "explain"}`. The finished `text` is the rules paragraph when the model is unset or refuses the rephrase.

### `GET /insights/jobs/{id}`

`200` is the job object described above. `404` when this athlete has no such job. One athlete cannot read another's job.

## Screens

These are the reads and writes Home, Plan, Activity, Library, Profile, Settings, and Session use. None of them call the model. None of them pass easy pace into `sequence()` or `adapt()`.

### `GET /home?just_generated=false`

`200`:

```json
{
  "today": "2026-11-09",
  "athlete": {},
  "hello": "Hey Ada",
  "strava": {},
  "strava_offer": false,
  "copy": "",
  "season": null
}
```

`strava` is the status object. `copy` is the no-plan sentence when `season` is null. When a season is open, `season` is:

| Field | Meaning |
| --- | --- |
| `inputs`, `digest` | The current season |
| `view` | Next workout, days remaining, phase, last mark, and this week's focus, from `dashboard_view` |
| `phase` | The authored phase story, or `null`. Not a model note. |
| `next` | Today's workout, or the next one. No-watch uses the next open workout. Also `label`, `facts` (`distance`, `pace`, `rest`, `reps`), `shown_date`, and `prescription`. |
| `upcoming` | The next three sessions on or after today, with the same card fields as `next` |
| `next_days` | The three calendar days after today. A day with no session is still a card (`label` is `—`). |
| `pace_status` | `No runs yet`, `Not enough data`, `On track`, `Ahead`, or `Behind` |
| `prescription` | `line`, `tolerance`, and `block`. `line` is the time per rep and the rest, or the easy pace, or the sentence that asks for an easy pace. `block` is the session clock for a rep workout. Easy pace is not passed into `sequence()` or `adapt()`. |
| `notes` | Unviewed insight notes: `[{"date": "", "note": {}, "viewed": false}]` |
| `activities` | The same activity rows as `season.activities` |
| `logging` | `done` or `times` |

`just_generated=true` is how the client asks whether to show the Strava card after Generate. `POST /seasons` already returns `strava_offer` for that moment.

### `GET /plan?month=YYYY-MM`

`200`:

| Field | Meaning |
| --- | --- |
| `inputs`, `digest`, `marks`, `prefs` | The current season |
| `months` | First day of each month in the plan, `YYYY-MM-DD` |
| `month` | The month in the response, `YYYY-MM`. Omitted query uses the month that contains today. |
| `month_title` | The month name |
| `calendar` | Sunday–Saturday weeks. Each day is `date`, `in_month`, `day`, `label`, `template_id`, `today`. |
| `weeks` | One row per season week: `week`, `phase`, `status`, `days_remaining`, `meters`, `volume` |

The session list itself is `plan.sessions` on `GET /seasons/current`. `400` when `month` is not `YYYY-MM`. `404` when there is no current season.

### `GET /activities`

`200` for the current season:

| Field | Meaning |
| --- | --- |
| `strava` | The status object |
| `rows` | Matched sessions: `date`, `shown_date`, `label`, `template_id`, `meters`, `work`, `heart_rate`, `hr`, `id`, `start` |
| `all` | Every activity with a distance or a heart rate. `extra` is true when it is not matched. |
| `cards` | One card per run: `id`, `date`, `shown_date`, `name`, `template_id`, `status`, `detail`, `laps`, `meters`, `heart_rate`, `continuous`, `speed` |
| `groups` | Cards grouped by week, newest first |
| `summary` | This week's distance, run count, and status counts |
| `weekly_meters` | Completed meters for each plan week |
| `heart` | `[{"date": "", "bpm": 0}]` |

`404` when there is no current season. Refresh is `POST /strava/sync`.

### `GET /library?q=&family=&phase=`

`200` `{"count": 0, "workouts": [], "families": [{"id": "", "label": ""}]}`.

A workout is `id`, `description`, `capacity`, `family`, `phases` (ints). `q` matches the name, the id, or the capacity. `family` is a family id. `phase` is 1–8. Empty filters leave that side open. This is the frozen menu. It does not change.

### `GET /profile`

`200`:

```json
{
  "ready": true,
  "fields": [{"label": "Current 800 time", "value": "2:02.9"}],
  "profile_key": "rio.profile.v1\n...",
  "goal_time": "1:55.0",
  "inputs": {},
  "easy_pace": "",
  "easy_pace_unit": "mi",
  "easy_pace_phrase": "",
  "prefs": {}
}
```

`ready` is false and `fields` is empty when there is no season. The four Start values are the season. `goal_time` is the season’s goal and does not change when Profile saves another time. `goal_override` is that saved time, or `null`. `shown_goal` is the override when there is one, otherwise `goal_time`. The Goal 800m time in `fields` is `shown_goal`. Saving it does not call `sequence()` or `adapt()`. Easy pace is saved with `PATCH /settings`.

Streamlit still keeps this override in the browser under `email + profile_key`. It does not read the API’s copy. A local API save is a sealed record, `rio.api.goal.v1`, and the plan key is written again afterward so Streamlit still opens the plan. A hosted save is `goal_overrides` on auth user metadata. `plans` is not written.

### `PUT /profile/goal`

Cookie. Body: `{"goal_time": "1:54.0"}`.

`200` is the profile object, with `goal_override` set. The season digest is unchanged. `400` `{"detail": "goal_time is not an 800 time"}` when the text is not an 800 time. `404` when there is no current season. `401` when the cookie is missing.

### `GET /sessions/{date}`

`200`:

```json
{"date": "", "session": {}, "actual": null, "quality": false, "note": null, "viewed": null, "digest": ""}
```

`session` is the planned day. `actual` is the stored result, or `null`. `quality` is true for a Tuesday or Thursday that is not an easy or long run. `note` is the insight, or `null`. `404` when the date is not in the season, or there is no season. Saving a result is `POST /seasons/current/results`. Got it is `POST /seasons/current/notes` with `viewed: true`.

### `PATCH /settings`

Cookie. Send only the fields to change. `200` is `athlete`.

| Field | Rule |
| --- | --- |
| `pace_units` | `mi` or `km` |
| `timezone` | One id from the Settings list |
| `no_watch` | bool |
| `easy_pace` and `easy_pace_unit` | Both, or neither. Pace is `m:ss`. |
| `display_name` | A name, 40 characters or fewer |
| `preferred` | A nickname, or `""` to clear it |
| `intro_seen` | bool |
| `strava_prompt_seen` | bool. This dismisses the Home Strava card. |
| `date_format` | `iso` or `short` |
| `start_date` | `today` or `sunday` |
| `confirm_adapt` | bool |
| `show_ids` | bool |
| `compact` | bool |

`400` when a value is unusable, or when the body changes nothing. The plan is not rewritten. A bad easy pace does not replace the one already saved.

Hosted pace, time zone, no-watch, easy pace, intro, and the Strava prompt are the same auth metadata the Streamlit Settings page writes. Date format, start date, confirm-adapt, show-ids, compact, and the nickname are saved on the account as well. The Streamlit page does not read those extra fields, so the live app is unchanged.

## Admin

Admin is the login whose email is `RIO_ADMIN_EMAIL`. Any other cookie is `403` `{"detail": "That page is for the admin account."}`. A missing cookie is `401`. The test season is a different athlete. Loading it does not write the signed-in plan.

### `GET /admin/accounts`

`200` `{"available": true, "accounts": [{"email": "", "display_name": "", "role": "athlete"}]}`. `available` is false when the server key is missing, which is the Streamlit "isn't available on this server yet" line. Passwords and tokens are not included. A local file returns the same shape with `role` `athlete`.

### `POST /admin/test-season`

`200` `{"loaded": true, "created": true, "runs": 0, "name": "TEST Athlete"}`. This is `load_test_season`. `400` when it cannot be saved, including a local file with no directory, and when this login is the TEST athlete.

### `GET /admin/test-season`

`200` `{"loaded": false}` when that athlete has no plan. Otherwise `loaded`, `name`, `inputs` (the four strings), `runs`, and `plan`. This is the read-only preview. It does not replace the caller’s season.

### `DELETE /admin/test-season`

Body: `{"confirm": true}`. `200` `{"deleted": true, "message": "TEST Athlete was removed."}` or `deleted: false` when that athlete is already gone. `confirm` must be true. `400` otherwise.

### `GET /admin/hero`

`200` `{"photos": [{"id": "", "file": "", "credit": "", "source": "", "enabled": true}]}`. The file is `ui/hero_config.py`’s JSON, the same file the Streamlit editor writes.

### `PUT /admin/hero`

Body: `{"photos": [{"id": "", "enabled": true, "credit": ""}]}`. The id list must be the startup set, each once. `200` is the hero object plus `saved: true`. `400` when a credit or an id is unusable.

## Fixtures

The Last Session, Next, Decisions, Ledger, and Goal pages. Admin only, same as `_fixture_allowed`. They call `classify`, `prescribe`, `accept`, and `Ledger`. They do not call the model. Prose is still `POST /insights/explain`.

### `GET /fixtures`

`200` `{"fixtures": ["easy", "race_800"]}`. The names are the stems in `tests/fixtures`.

### `POST /fixtures/classify`

Body: `{"name": "race_800"}` or `{"payload": {}}`. `payload` is a session object, the same shape `classify` already takes.

`200` `{"family": "", "reason_codes": [], "confidence": "", "ontology_version": "v0.1", "source": ""}`. `source` is present when the fixture or the payload has one. `400` when neither name nor payload is sent, or the session cannot be classified. `404` when the name is not a fixture.

### `POST /fixtures/prescribe`

Body: `{"name": "race_800"}`. `200`:

```json
{"name": "race_800", "on": "2026-11-09", "limiting_capacities": "unknown", "rows": [], "ontology_version": "v0.1"}
```

`on` is today. Each row is a `prescribe` row (`template_id`, `parameters`, `reason_codes`, `prescribed_on`). The ledger is not kept. `400` when the name is missing or the rules refuse it.

### `POST /fixtures/accept`

Body: `{"name": "race_800"}`. A missing name uses `race_800`, the fixture `accept_fixture_prescription` uses. The day is that fixture’s clock (`2026-10-17`), not today, because acceptance refuses a placeholder of today.

`200` `{"name": "race_800.yml", "on": "2026-10-17", "row": {}}`. `row` is the planned acceptance (`template_id`, `parameters`, `placeholder_date`, `ontology_version`, `source`, `reason_codes`). The file is written in a temporary directory and thrown away. The checked-in files in `tests/fixtures/planned` are not replaced.

### `GET /fixtures/ledger`

`200` `{"as_of": "2026-11-09", "entries": [], "emerging": [], "decaying": []}`. `as_of` is today. Entries are the four fixture deposits, the same tables the Ledger page shows.

### `GET /fixtures/goal`

`200` the four `goal.yml` fields: `current_mark`, `target_time`, `target_date`, `limiting_capacities`. `unknown` stays `unknown`.

## Explain spend

`RIO_EXPLAIN_SPEND_PATH` still selects the JSON file. Tests set it. Leave it unset in production.

When it is unset and the service role is configured, reserve and settle call `public.explain_spend` (migration 011). One row, id `global`. The cap stays `SPEND_CAP_MICRO_USD` in `engines/explain.py` and is passed into the function. A missing table or function uses the JSON file for that call, so Streamlit keeps working before the SQL runs. After it runs, Streamlit and this API share the row and do not also add to the file.

If the file already has a balance, the first shared reserve copies that balance up with `adopt_explain_spend` when the row is still lower. It does not add the file on top of a higher row.

## Left before step 3

The Next.js app can be built against the routes above. These are still not API routes:

- About, Creators, photos, and the startup splash. They are static. The hero order is `GET /admin/hero`. The splash itself is not.
- The Streamlit Google button and the "check your email" screen stay hidden. The API routes for both are above.
- Confirm-before-adapt stays on the client. `confirm_adapt` is a setting. The API applies the mark on POST.
- Workout and digest jobs still live in this process. A restart loses a job that had not finished. A saved note remains on the season.

Jay runs `supabase/migrations/010_strava_oauth.sql` in the SQL editor before a hosted Strava connect. It is safe to run again. Row level security is on, and only the service role is granted the table. The index is `strava_oauth_pkey` on `user_id` and `strava_oauth_expires_at` on `expires_at`. The trigger is `strava_oauth_touch_updated_at`. Migrations 005 through 009 are already applied. The Streamlit callback does not use this table.

Jay runs `supabase/migrations/011_explain_spend.sql` when this API and Streamlit should share one spend counter. It does not have to run before the merge. Until it has been run, both keep the JSON file. It is safe to run again. Row level security is on, and only the service role is granted the table and `reserve_explain_spend`, `settle_explain_spend`, and `adopt_explain_spend`. The primary key index is `explain_spend_pkey` on `id`. The trigger is `explain_spend_touch_updated_at`. There is no index beyond the primary key. The Streamlit app does not need a code change for the file to keep working before that SQL, or for the row to be used after it.
