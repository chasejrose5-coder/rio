# Supabase accounts

Run `001_accounts.sql` in the Supabase SQL editor. The project was created with new tables hidden and row level security on, so this file grants the signed-in role what it needs and adds the policies.

The service role bypasses those policies. The app uses it only on the server, and only to list accounts or delete an auth user.

`002_lock_roles.sql` stops a signed-in person from changing `profiles.role`. New profiles still default to athlete. The service role can still set the role. Run it the same way, in the SQL editor, after `001_accounts.sql`. It is safe to run again.

`003_strava.sql` adds Strava tokens and activities. Tokens are not granted to signed-in users. Activities are. Run it after 002. It is safe to run again.

`005_lock_profile_email.sql` stops a signed-in person from changing `profiles.email`. Admin is decided from the confirmed auth user, not from that column. Run it after 003. It is safe to run again.

`006_app_sessions.sql` stores hosted session tokens on the server. The browser cookie holds only an id. Run it after 005. It is safe to run again. Until it has been run, the app still writes the older cookie so a login is not lost.

`007_plans_season_key.sql` keeps one row per season and deletes older copies of that same season. A different season stays. Run it after 006. It is safe to run again. Until it has been run, a save still writes a new row, and a reload reads the newest `updated_at`.

`008_delete_past_season.sql` deletes one past season and the results tied to it, in one transaction, for the signed-in athlete. A goal date of today or later is refused. Run it after 007. It is safe to run again. Until it has been run, the app deletes those same rows one by one.

`009_season_state.sql` stores the quality base and the workout notes for one season. The plan row is unchanged. A signed-in athlete can read only their own rows. Run it after 008. It is safe to run again. It also updates `delete_past_season` so deleting a past season removes that row. Until it has been run, the API rebuilds a missing quality base from the stored marks, earliest week first. The Streamlit app does not read this table.

`010_strava_oauth.sql` stores the Strava OAuth nonce on the server. The service role is the only role granted the table. Run it after 009. It is safe to run again. Until it has been run, a hosted API connect cannot start. The Streamlit callback does not read this table.

`011_explain_spend.sql` stores the explain spend counter in one row. The service role is the only role granted the table and the functions. Run it after 010. It is safe to run again. It does not have to run before a deploy. Until it has been run, Streamlit and the API keep the JSON file. After it has been run, a process that is not pinned to `RIO_EXPLAIN_SPEND_PATH` uses the row.

`012_app_sessions_expires_at.sql` indexes `app_sessions.expires_at` so expired-session cleanup does not scan the table. Run it after 011. It is safe to run again.

`013_delete_any_owned_season.sql` lets the signed-in athlete delete any one of their seasons, including the season they are training on. It replaces `delete_past_season`. A goal date of today or later is no longer refused. Other athletes stay behind `auth.uid()`. Run it after 012. It is safe to run again. Until it has been run, a goal date of today or later is still refused by the function from 009.

`014_stretch.sql` adds `stretch_completions` and `sore_spots`. Completions store the runner, the calendar date (`done_on`), and the routine id. Sore spots store the region, the severity, the day they started, the check-in date, and whether they were cleared. A signed-in athlete can read and write only their own rows, scoped to `auth.uid()`. Run it after 013. It is safe to run again. Until it has been run, the Stretching tab cannot save Done or a sore spot. The exercise text is not in the database.

`017_injury_prevention.sql` stores rebuilding areas and injury-prevention done marks. An area row stores the area id, the level at the anchor date (`0` easy, `1` medium, `2` hard), and that anchor date. A completion stores the runner, the calendar date (`done_on`), and the block id (`general` or an area id). A signed-in athlete can read and write only their own rows, scoped to `auth.uid()`. Run it after 016. It is safe to run again. Until it has been run, a hosted account cannot save a rebuilding area or a done mark. The exercise text is not in the database.

`018_core_completions.sql` stores a done mark for the day’s core circuit. The row is the runner and the calendar date (`done_on`). A signed-in athlete can read and write only their own rows, scoped to `auth.uid()`. Run it after 017. It is safe to run again. Until it has been run, a hosted account cannot save a core done mark. The exercise text is not in the database.

`020_bike_sessions.sql` stores an easy-day bike swap. The row is the plan day. Minutes, distance, an optional average heart rate, a Strava id, and zone seconds are filled when the ride is logged. A signed-in athlete can read and write only their own rows, scoped to `auth.uid()`. Run it after 019. It is safe to run again. Until it has been run, a hosted account cannot save a bike swap. There is no cadence.

`019_foam_completions.sql` stores a done mark for the day’s foam-rolling routine. The row is the runner and the calendar date (`done_on`). A signed-in athlete can read and write only their own rows, scoped to `auth.uid()`. Run it after 018. It is safe to run again. Until it has been run, a hosted account cannot save a foam-rolling done mark. The exercise text is not in the database.

`016_run_hr_streams.sql` stores the heart-rate stream for one Strava run (`sample_time` and `sample_hr`). Time in zone is counted from those samples, so a later change to resting or max heart rate can recount. A signed-in athlete can read and write only their own rows, scoped to `auth.uid()`. Run it after 015. It is safe to run again. Until it has been run, a hosted account cannot save a stream. The connect scope stays `activity:read_all`. That scope can read activity streams. `profile:read_all` is not added.

`015_heart_rate.sql` adds `heart_rate`. One row per athlete stores resting heart rate, max heart rate, whether they use a heart rate monitor, and any zone boundaries they edited. Empty boundaries mean the Karvonen defaults. A signed-in athlete can read and write only their own row, scoped to `auth.uid()`. Run it after 014. It is safe to run again. Until it has been run, a hosted account cannot save heart rate. `004` was never added; `005` runs after `003`, so this file is `015`.

After the SQL:

1. Authentication, URL configuration. Site URL: `https://www.riorunning.com`. The live Render values of `RIO_FRONTEND_ORIGIN` and `RIO_CALLBACK_BASE_URL` are that origin, scheme and host, no path, no trailing slash. Strava's Authorization Callback Domain is `www.riorunning.com`.

   Leave these redirect URLs in place. Do not delete them:

   - `https://riotraining.streamlit.app` and `https://riotraining.streamlit.app/**`
   - `http://localhost:8501` and `http://localhost:8501/**`
   - `https://rio-one-mocha.vercel.app/`, `https://rio-one-mocha.vercel.app/reset-password`, and `https://rio-one-mocha.vercel.app/confirm`
   - `https://rio-rio-44fa.vercel.app/`, `https://rio-rio-44fa.vercel.app/reset-password`, and `https://rio-rio-44fa.vercel.app/confirm`

   The Next app's mail uses `RIO_FRONTEND_ORIGIN`. Add these as well, and do not edit them from the app:

   - `https://www.riorunning.com/update-password` — password reset mail
   - `https://www.riorunning.com/reset-password` — the same new-password form
   - `https://www.riorunning.com/confirm` — signup confirmation and email-change mail
   - `https://www.riorunning.com/`
   - `https://www.riorunning.com/auth/callback*` — Google sign-in. The `*` covers `?flow=` on each attempt. The steps are `docs/google-auth-setup.md`.

   When `RIO_FRONTEND_ORIGIN` is unset the API uses `http://localhost:3000`, so the laptop entries are `http://localhost:3000/update-password`, `http://localhost:3000/reset-password`, and `http://localhost:3000/confirm`. `{RIO_FRONTEND_ORIGIN}/**` also covers both. Signup confirmation uses `/confirm`. Password reset mail uses `/update-password`. Jay adds these in the Supabase dashboard. Nothing in the repo writes the allow list. The Resend steps are `docs/resend-email-setup.md`.
2. Authentication, Providers, Email. Keep "Confirm email" ON. Also turn on "Secure email change" if that switch is shown. Do not turn confirmation off.
3. Authentication, Providers, Google. Turn it on when you want Continue with Google. The click-by-click steps, including the Google Cloud client and the Vercel flag, are `docs/google-auth-setup.md`. The Google Cloud OAuth client needs this redirect URI exactly: `https://<project-ref>.supabase.co/auth/v1/callback`. Copy the client id and secret into the Google provider in Supabase. Do not commit them.
4. Put the four settings in Streamlit Cloud secrets, or in `.env` on a laptop. The names are listed in `.env.example`. Do not commit the values.
