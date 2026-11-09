# RIO API

The Streamlit app is still the live site. This process is the FastAPI backend for the Next.js app that comes later. It imports `engines/` and `services/`. It does not copy them.

## Run it locally

From the repository root, with Python 3.12:

```bash
pip install -r requirements.txt -r api/requirements.txt
uvicorn api.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/health`. It returns `{"ok": true}`.

Settings come from the environment. A `.env` file in the repository root is read the same way the Streamlit app reads it, and an existing environment value wins. Do not commit that file.

| Name | What it is |
| --- | --- |
| `RIO_FRONTEND_ORIGIN` | The one browser origin allowed to call this API. Default `http://localhost:3000`. A wildcard is refused. |
| `RIO_SUPABASE_URL` | Hosted accounts. When this and the anon key are set, sign-in uses Supabase. |
| `RIO_SUPABASE_ANON_KEY` | The anon key. It stays on the server. |
| `RIO_SUPABASE_SERVICE_ROLE_KEY` | Required for the hosted session table. It is not sent to the browser. |
| `RIO_APP_URL` | Already used by the Streamlit app for redirects. |
| `RIO_ACCOUNTS_PATH` | Local account file when Supabase is not configured. Tests set this. |

When the Supabase URL or anon key is missing, sign-in uses the local account file, the same accounts the Streamlit app uses on a laptop.

## Auth

`POST /auth/sign-in` with `email` and `password` sets a `rio_hosted` cookie. The value is an opaque `rio1.` id. The cookie is `HttpOnly`, `Secure`, and `SameSite=Lax`. Lax matches the OAuth return the app already depends on. The Supabase access token and the local seal stay on the server. They are not in the cookie and not in `localStorage`.

`GET /auth/me` returns the signed-in athlete. `POST /auth/sign-out` drops the server session and clears the cookie. The cookie lasts the rest of the original 24 hours. Refreshing the Supabase token does not extend it.

`POST /auth/sign-up` creates an account and sets the same cookie when a session comes back. `POST /auth/forgot-password` and `POST /auth/reset-password` are the reset mail. `POST /auth/password` and `POST /auth/email` change this account. `POST /auth/delete` requires `confirm: true`. `GET /auth/google` and `GET /auth/google/callback` are Google sign-in. `RIO_GOOGLE_REDIRECT_URI` defaults to the Streamlit callback.

## Seasons

All of these require the cookie.

| Method | Path | What it does |
| --- | --- | --- |
| `GET` | `/seasons/current` | Plan, marks, actuals, digest, notes, and the saved prefs. |
| `POST` | `/seasons` | Generate. Body is `current_time`, `start_date`, `goal_time`, `goal_date`, the same four Start fields. Calls `sequence()`. |
| `POST` | `/seasons/current/results` | One result. Calls `judge`, then `adapt`. |
| `POST` | `/seasons/current/watchless` | A Done mark. Body is `date`, `outcome` (`Behind`, `On target`, or `Ahead`), and an optional `time`. |
| `POST` | `/seasons/current/marks` | One week mark: `week` and `choice` (`on_track`, `not_hitting`, or `smashing`). |
| `POST` | `/seasons/current/notes` | Save a note for a date. This does not call the model. |
| `GET` | `/seasons/past` | Seasons whose goal date is before today. |
| `POST` | `/seasons/reset` | Delete every stored season. `confirm` must be true. The account stays. |
| `DELETE` | `/seasons/past` | Delete one past season. `confirm` must be true. A current season is refused. The response lists the same stats as the confirm panel. |

A season write can send `If-Match` with the digest it loaded. A mismatch is `412` and nothing is saved. A missing header still lets the later write win.

Today is the calendar date in the Settings time zone (`local_today`). Pace units, the no-watch preference, and the easy pace are read with the same helpers as Settings and included on the athlete and on the season. `logging` is `done` when no-watch is on and `times` otherwise. The easy pace is not passed into `sequence()` or `adapt()`.

The plan write finishes before a note is stored. A result or Done save does not wait on the model. When the day can take a note, the response includes `insight.status` of `pending`, and `GET /insights/workout/{date}` returns the note after the model finishes. A note that is the wrong shape is left out and the plan stays saved.

## Quality base and notes

`season_quality_base` is the plan from before each week's adapt. It is stored in `public.season_state.quality_base`, keyed by the same four season fields as `plans`. Week numbers are JSON strings. The API turns them back into ints.

`rio_workout_notes` is `{date: {note, viewed}}` in `workout_notes` on that same row. The note has `headline`, `body`, `carry_forward`, and `used_result_band`.

Run `supabase/migrations/009_season_state.sql` in the Supabase SQL editor. The app does not apply it. The table has row level security so an athlete sees only their own rows. Deleting a past season removes the row.

Until that migration has been run, a hosted save still writes the plan. A missing base is rebuilt before the next adapt:

1. Start from `sequence()` for the four inputs, not from the saved plan.
2. Apply marked weeks from the smallest week number to the largest.
3. Each week's base is the plan from before that week is adapted. Later weeks' bases are dropped when an earlier week is adapted again.

That is the order `auto_adapt` already uses. A later week is not adapted twice.

Local accounts store the same JSON in a sealed record, `rio.api.state.v1`, which is not a plan key. The plan key is written after it so Streamlit still opens the plan. If the sealed record cannot hold every base, the bases are left empty and the next request rebuilds them in the order above.

## Strava

`GET /strava/connect` stores a nonce on the server and returns the authorize URL. `GET /strava/callback` accepts the code only when that nonce matches. Tokens are written with the service role and are not in the JSON.

`RIO_STRAVA_REDIRECT_URI` is the redirect this process sends. When it is unset, the redirect is the Streamlit callback (`RIO_APP_URL` + `/`), so that registration keeps working. The new site sets the variable when its own callback is registered.

`POST /strava/sync` with `{"scope": "recent"}` or `{"scope": "all"}` imports runs. Marks from that import use the stored quality base. A failed import does not move `last_sync_at`. When Strava is not connected, the same route uses the Intervals fallback.

Run `supabase/migrations/010_strava_oauth.sql` before a hosted connect. The Streamlit app does not read that table.

## The rest of the routes

`docs/migration/api-contract.md` lists every route, the request and response, and who can call it. There is no Next.js app here.
