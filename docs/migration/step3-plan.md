# Step 3 plan

Step 3a is the Next.js app in `web/`. Streamlit stays the live site. The pages below are still placeholders that say they are coming in the next step. Each one is its own pull request, in this order.

1. Start. Easy pace and the three-step intro already shipped with the scaffold and stay as they are. This step replaces the Start placeholder: the start-line photo, the four fields, Generate, and the link that names a different season. Generate opens Home and arms the Strava card.
2. Plan.
3. Start session and Session.
4. Activity and Strava.
5. Library.
6. Profile.
7. Settings.
8. Seasons and past seasons.
9. About and Creators. Those pages stay the locked copy. This step does not rewrite them.

Home, sign-in, create account, and reset are in step 3a. Google sign-in stays hidden, the same as Streamlit. Forgot password shows only when accounts are hosted. A laptop using the local account file does not show it.

## Run the API and the site together

From the repository root:

```bash
bash scripts/dev-local.sh
```

That starts the API on port 8000 and the Next.js app on port 3000. It clears `RIO_SUPABASE_URL`, `RIO_SUPABASE_ANON_KEY`, and `RIO_SUPABASE_SERVICE_ROLE_KEY` for those two processes, so a `.env` in the repo cannot point this session at production. Sign-in uses the local account file.

Open `http://localhost:3000`. The API allows that origin by default (`RIO_FRONTEND_ORIGIN`). The browser reads `NEXT_PUBLIC_RIO_API_URL`, which defaults to `http://localhost:8000`. Copy `web/.env.example` to `web/.env.local` only if the API is on another port.

Do not set `RIO_USE_HOSTED=1` against the production project. That flag keeps whatever Supabase variables are already in the environment.

Jay does not have to run SQL for this step. Migrations 010 and 011 stay as they were: 010 before a hosted Strava connect, 011 when the API and Streamlit should share one explain-spend counter. Neither is required to open this front end.
