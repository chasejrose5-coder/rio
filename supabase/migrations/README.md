# Supabase accounts

Run `001_accounts.sql` in the Supabase SQL editor. The project was created with new tables hidden and row level security on, so this file grants the signed-in role what it needs and adds the policies.

The service role bypasses those policies. The app uses it only on the server, and only to list accounts or delete an auth user.

`002_lock_roles.sql` stops a signed-in person from changing `profiles.role`. New profiles still default to athlete. The service role can still set the role. Run it the same way, in the SQL editor, after `001_accounts.sql`. It is safe to run again.

`003_coach_teams.sql` adds teams and memberships. A coach can read an athlete's rows and cannot write them. Codes are looked up by `join_team`, not by listing the table. Run it after 002. It is safe to run again.

After the SQL:

1. Authentication, URL configuration. Site URL: `https://riotraining.streamlit.app`. Redirect URLs: `https://riotraining.streamlit.app` and `https://riotraining.streamlit.app/**`. For a laptop, also add `http://localhost:8501` and `http://localhost:8501/**`.
2. Authentication, Providers, Email. Turn off "Confirm email".
3. Authentication, Providers, Google. Turn it on. The Google Cloud OAuth client needs this redirect URI exactly: `https://<project-ref>.supabase.co/auth/v1/callback`. Copy the client id and secret into the Google provider in Supabase.
4. Put the four settings in Streamlit Cloud secrets, or in `.env` on a laptop. The names are listed in `.env.example`. Do not commit the values.
