# API contract

The FastAPI app in `api/` is the backend for the Next.js app. The Streamlit app is still the live site and does not call these routes. Every route below is implemented. Shapes are JSON.

Auth, unless a route says otherwise, is the `rio_hosted` cookie set by `POST /auth/sign-in`. The value is an opaque `rio1.` id. The cookie is `HttpOnly`, `Secure`, and `SameSite=Lax`. Lax is what lets the Strava redirect send the cookie back. The Supabase access token and the local seal stay on the server. They are not in the cookie, not in `localStorage`, and not in these responses.

A missing or expired cookie is `401` `{"detail": "Sign in again."}`.

Errors from the app are `{"detail": "<sentence>"}`. A body that is not the shape below is `422` from the framework. `400` is a rejected value. `404` is a missing season, day, or job. `409` is a conflict (Strava already connected, or deleting the current season). `429` is the Strava rate limit. `503` is Strava not configured, or migration 010 not applied.

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

## Seasons

All of these need the cookie. Today follows the Settings time zone. Easy pace, pace units, and no-watch are not passed into `sequence()` or `adapt()`.

### `GET /seasons/current`

`200` is `season`. `404` when there is no current season.

### `POST /seasons`

Body is `inputs`. `200` is `season` plus `committed: true` and `strava_offer` (bool). `strava_offer` is true only when this generate just succeeded, Strava is not connected, and the athlete has not dismissed the prompt. `400` when an input is unusable. A plan that contains `probability` or `readiness_score` is rejected by `sequence()`.

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

`outcome` is `Behind`, `On target`, or `Ahead`. `time` may be empty. `200` matches the result route, including `insight`. A time on a hard day adapts later weeks. Done with no time does not. `400` when the date or the time is unusable.

### `POST /seasons/current/marks`

Body: `{"week": 1, "choice": "on_track"}`. `choice` is `on_track`, `not_hitting`, or `smashing`. `200` is `season` plus `committed`. This route does not call the model. `400` when the week or the choice is unusable.

### `POST /seasons/current/notes`

Body: `{"date": "", "note": {}, "viewed": false}`.

`200` is `season` plus `note_saved: true`. This is the Got it write (`viewed: true`) and a hand-saved note. It does not call the model. `400` when the date is not in the season or the note is the wrong shape (including a lap list, Strava, GPS, or a score).

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
| `next` | Today's workout, or the next one. No-watch uses the next open workout. |
| `upcoming` | The next three sessions on or after today |
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

`ready` is false and `fields` is empty when there is no season. The four Start values are the season. The goal-time override the Profile page keeps in the browser is not stored here and does not rebuild the season. The client may keep it under `profile_key`. Easy pace is saved with `PATCH /settings`.

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

## Left before step 3

The Next.js app can be built against the routes above. These are not routes yet:

- Create account, forgot password, reset password, change password, change email, and delete account.
- Reset plan (delete every stored season and keep the account).
- The Profile goal-time override. It stays in the browser under `profile_key` and does not rebuild the season.
- `If-Match` on the season digest. The digest is returned. Two tabs can still both save, and the later write wins.
- Admin, the test season, the hero rotation, and Google sign-in.
- Classify, prescribe, accept, the ledger, and the goal fixture page. The explain rephrase is `POST /insights/explain`.
- About, Creators, photos, and the startup splash. They are static and are not API routes.
- The explain spend cap is still the local JSON file (`RIO_EXPLAIN_SPEND_PATH`, otherwise `data/explain_spend.json`). Streamlit and this API should not keep two separate counters if both call the model.

Jay runs `supabase/migrations/010_strava_oauth.sql` in the SQL editor before a hosted Strava connect. It is safe to run again. Row level security is on, and only the service role is granted the table. The index is `strava_oauth_pkey` on `user_id` and `strava_oauth_expires_at` on `expires_at`. The trigger is `strava_oauth_touch_updated_at`. Migrations 005 through 009 are already applied. The Streamlit callback does not use this table.
