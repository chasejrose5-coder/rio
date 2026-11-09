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

After the SQL:

1. Authentication, URL configuration. Site URL: `https://riotraining.streamlit.app`. Redirect URLs: `https://riotraining.streamlit.app` and `https://riotraining.streamlit.app/**`. For a laptop, also add `http://localhost:8501` and `http://localhost:8501/**`.
2. Authentication, Providers, Email. Keep "Confirm email" ON. Also turn on "Secure email change" if that switch is shown. Do not turn confirmation off.
3. Authentication, Providers, Google. Turn it on. The Google Cloud OAuth client needs this redirect URI exactly: `https://<project-ref>.supabase.co/auth/v1/callback`. Copy the client id and secret into the Google provider in Supabase.
4. Put the four settings in Streamlit Cloud secrets, or in `.env` on a laptop. The names are listed in `.env.example`. Do not commit the values.
