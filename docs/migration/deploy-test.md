# Test deploy beside Streamlit

This is the click path for a test site that runs next to the live Streamlit app. Streamlit stays on `https://riotraining.streamlit.app`. Nothing in this file creates an account, deploys, or merges.

The browser uses one host, the Vercel `*.vercel.app` URL. Next rewrites `/api/*` to the FastAPI service on Render. The `rio_hosted` cookie is `HttpOnly`, `Secure`, and `SameSite=Lax`, with no `Domain` attribute, so it sticks to the Vercel host only. `vercel.app` and `onrender.com` are different sites. Pointing the browser at the Render URL would drop the cookie.

`GET /health` already returns `{"ok": true}` with no cookie. Render's health check uses that path. It is not a new route.

## 1. Create the two accounts

1. Open [https://vercel.com/signup](https://vercel.com/signup). Choose **Continue with GitHub**. Approve access to the `rio` repository when GitHub asks.
2. Open [https://dashboard.render.com/register](https://dashboard.render.com/register). Choose **GitHub** and approve the same repository.
3. Use the Hobby workspace on both. Vercel Hobby is the free plan. Render's free web service is the plan in `render.yaml` (`plan: free`).

## 2. Create the Render service first

The onrender.com URL has to exist before the Vercel build, because that build bakes the rewrite target.

1. In the Render dashboard, choose **New**, then **Blueprint**.
2. Connect this repository. When it asks for the branch, pick the branch you are testing. After this pull request is merged, use `main`.
3. Render reads `render.yaml` at the repository root. Confirm the form shows:
   - Name: `rio-api`
   - Runtime: Python
   - Root directory: the repository root. Leave it blank if the form has a root field. It is not `web`. The API imports `engines/`, `services/`, and `ui/` from that root.
   - Build command: `pip install -r requirements.txt -r api/requirements.txt`
   - Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/health`
   - Instance type: Free
4. `PYTHON_VERSION` is already `3.12.11` in the blueprint, the same 3.12 line CI uses. If the build log says that patch is not offered, set `PYTHON_VERSION` to the newest 3.12 the dashboard lists and save.
5. The form asks for the other names in `render.yaml`. Fill the Supabase and admin values from the table in step 6 if you have them. Leave `RIO_FRONTEND_ORIGIN` and `RIO_CALLBACK_BASE_URL` empty for this first pass, and leave the Strava and explain boxes empty until steps 7 and 8. An empty box must not be saved as a blank value for `RIO_FRONTEND_ORIGIN`. A blank string stops the process. If the dashboard created the variable with an empty value, delete the variable on the Environment page so it is absent.
6. Choose **Apply** / **Deploy**. Wait until the service is live. Copy the URL. It looks like `https://rio-api.onrender.com`, with no path and no trailing slash. That host is `RIO_API_ORIGIN` on Vercel.
7. Open `https://<render-host>/health` in a browser. The body is `{"ok":true}`. The first request on the free plan can take about a minute while the service wakes.

Manual path, if you are not using the blueprint: **New**, **Web Service**, same repository and branch. Set the root, build, start, health check, and Free instance to the values above. Add `PYTHON_VERSION` = `3.12.11` under Environment. Add the other names from step 6 yourself. There is still no disk.

## 3. Import the Next app on Vercel

1. In Vercel, choose **Add New**, then **Project**.
2. Import the `rio` repository. Pick the same branch you gave Render.
3. **Root Directory**: **Edit**, set it to `web`. This is the only service whose root is `web`. Leave **Include source files outside of the Root Directory in the Build Step** enabled. It is on by default. The Next build reads `ui/static` from the repository root. If that switch is off, the build stops and tells you to turn it on.
4. **Framework Preset**: Next.js.
5. **Node.js Version**: 22.x, the version CI uses.
6. **Install Command**: `npm ci` if the field is shown. Otherwise leave the default.
7. **Build Command**: `npm run build`. Leave **Output Directory** empty. npm runs `prebuild` before `next build`. That step copies `ui/static/fonts` and `ui/static/photos` into `web/public` as real files. Do not set the command to `next build`. That skips the copy.
8. Leave the start command empty. Vercel runs the Next server. A custom start is not required.
9. Open **Environment Variables** and add these two for Production (and Preview, if you will open a preview URL):

| Name | Value you type |
| --- | --- |
| `NEXT_PUBLIC_RIO_API_URL` | `/api` |
| `RIO_API_ORIGIN` | The Render URL from step 2, `https://<render-host>`, no path and no trailing slash |

`/api` is same-origin on whatever `*.vercel.app` host Vercel assigns. It lines up with `RIO_FRONTEND_ORIGIN`: the browser, the cookie, CORS, Strava, reset, and confirm all use that Vercel origin. `RIO_API_ORIGIN` is read only by `web/next.config.ts` when it builds the rewrite. It is not a `NEXT_PUBLIC_` variable, so the client bundle does not need the Render host. The rewrite is `/api/:path*` to `<RIO_API_ORIGIN>/:path*`. Pages such as `/settings` and `/strava/callback` stay on Next. Those paths also exist on the API, which is why the browser prefix is `/api`.

10. Deploy. When it finishes, copy the URL. It looks like `https://rio-xxxx.vercel.app`, no path and no trailing slash. That origin is what you put on Render in the next step.
11. Changing either variable later needs another Vercel deploy. `NEXT_PUBLIC_RIO_API_URL` is compiled into the browser bundle, and the rewrite target is compiled into the routes at build time.

There is no `vercel.json`. The rewrite and the `Cache-Control: private, no-store` header on `/api/:path*` live in `web/next.config.ts`. With `RIO_API_ORIGIN` unset, the rewrite list is empty, which is how a laptop stays on port 8000.

## 4. Point Render at the Vercel origin

On the Render service, **Environment**. Set these two, then save. Render redeploys.

| Name | Value |
| --- | --- |
| `RIO_FRONTEND_ORIGIN` | `https://<vercel-host>` |
| `RIO_CALLBACK_BASE_URL` | `https://<vercel-host>` |

No path. No trailing slash. The two strings are the same origin.

`RIO_FRONTEND_ORIGIN` is the only browser origin CORS allows. A wildcard is refused. Reset mail opens `{RIO_FRONTEND_ORIGIN}/reset-password`. Confirmation mail opens `{RIO_FRONTEND_ORIGIN}/`. Strava's redirect, when `RIO_STRAVA_REDIRECT_URI` is unset, is `{RIO_CALLBACK_BASE_URL}/strava/callback`. After Strava returns, the API sends the browser to `{RIO_FRONTEND_ORIGIN}/settings?strava=connected` or `?strava=error`. The Next page at `/strava/callback` calls the API with `X-RIO-Response: json` and then opens Settings.

Leave `RIO_APP_URL` unset on Render. Streamlit Cloud keeps its own value, `https://riotraining.streamlit.app`. The API does not use `RIO_APP_URL` for reset or confirmation mail. Leave `RIO_GOOGLE_REDIRECT_URI` unset. Google sign-in stays hidden, and the Streamlit Google redirect stays the Streamlit callback. Leave `RIO_STRAVA_REDIRECT_URI` unset so the callback base above is what Strava sees.

## 5. Supabase Auth redirect URLs

Use the same Supabase project the live app already uses. In the dashboard: **Authentication**, **URL configuration**.

Leave **Site URL** as `https://riotraining.streamlit.app`.

Leave the existing redirect URLs in place, including `https://riotraining.streamlit.app`, `https://riotraining.streamlit.app/**`, and any `http://localhost:8501` entries.

Add these two, using the exact Vercel origin from step 3:

- `https://<vercel-host>/reset-password`
- `https://<vercel-host>/`

Save. The app does not write this list. A redirect that is not on the list is ignored and the mail falls back to the Site URL, which is still Streamlit.

## 6. Environment values, and where each one comes from

Type values only in the Vercel and Render dashboards. The repo keeps the names.

### Vercel (root directory `web`)

| Name | Where the value comes from |
| --- | --- |
| `NEXT_PUBLIC_RIO_API_URL` | The literal `/api`. Not a secret. Same origin as the Vercel URL. |
| `RIO_API_ORIGIN` | The Render service URL from step 2. |

### Render (repository root)

| Name | Where the value comes from |
| --- | --- |
| `PYTHON_VERSION` | `3.12.11`, already in `render.yaml`. Not a secret. |
| `RIO_SUPABASE_URL` | Supabase dashboard, **Project Settings**, **API**, Project URL. Same project as Streamlit. |
| `RIO_SUPABASE_ANON_KEY` | That same API page, the anon / public key. It stays on the server. The Next app does not get a copy. |
| `RIO_SUPABASE_SERVICE_ROLE_KEY` | That same API page, the service_role key. Required for hosted sessions, Strava tokens, and explain spend. Server only. |
| `RIO_FRONTEND_ORIGIN` | The Vercel origin from step 3. |
| `RIO_CALLBACK_BASE_URL` | The same Vercel origin. |
| `RIO_ADMIN_EMAIL` | The email that may open Admin. Copy the value already in Streamlit secrets if that account should be admin here too. |
| `RIO_STRAVA_CLIENT_ID` | The new Strava application's client id, from step 8. Leave unset until then. |
| `RIO_STRAVA_CLIENT_SECRET` | That new application's client secret. Leave unset until step 8. |
| `RIO_EXPLAIN_API_KEY` | The explain provider key already used by Streamlit, if you want rephrased notes on this test site. Leave unset until step 9 shows migration 011 is present. |
| `RIO_EXPLAIN_MODEL` | The model name already used with that key. Leave unset with the key. |
| `RIO_EXPLAIN_BASE_URL` | The provider base URL already used with that key. Leave unset with the key. |
| `RIO_EXPLAIN_INPUT_USD_PER_MILLION` | Optional. Unset uses the built-in price. |
| `RIO_EXPLAIN_OUTPUT_USD_PER_MILLION` | Optional. Unset uses the built-in price. |
| `RIO_INTERVALS_API_KEY` | Optional. The Intervals.icu key already in Streamlit secrets, for the fallback when Strava is not connected. |
| `RIO_INTERVALS_ATHLETE_ID` | Optional. The athlete id that goes with that key. Blank means the key's own athlete. |

### Leave unset on Render

These have a file or a test default. Setting them on the free service either pins a file that disappears on restart or points the test site at the wrong host.

| Name | Why it stays unset |
| --- | --- |
| `RIO_APP_URL` | Streamlit's own mail and callback. The live service keeps `https://riotraining.streamlit.app`. |
| `RIO_GOOGLE_REDIRECT_URI` | Unset keeps the Streamlit Google callback. The button stays hidden. |
| `RIO_STRAVA_REDIRECT_URI` | Unset so `RIO_CALLBACK_BASE_URL` builds `https://<vercel-host>/strava/callback`. |
| `RIO_HERO_PATH` | Unset uses `ui/assets/hero_rotation.json`, which ships in the deploy. |
| `RIO_EXPLAIN_SPEND_PATH` | Unset lets migration 011 store the counter in Supabase. |
| `RIO_INSIGHT_LOG_PATH` | The insight log is best-effort. A write error is ignored. |
| `RIO_ACCOUNTS_PATH` | Hosted sign-in uses Supabase, not the local account file. |
| `RIO_SESSION_KEY` | Hosted sessions are rows in Supabase, not a local seal file. |
| `RIO_SESSION_KEY_PATH` | Same. |
| `RIO_AUTH_BACKEND` | Test-only. |
| `RIO_STRAVA_TRANSPORT` | Test-only. |
| `RIO_STRAVA_FAIL_FILE` | Test-only. |
| `RIO_USE_HOSTED` | Local script flag. The Render process uses the Supabase variables directly. |

## 7. Strava callback, keeping the Streamlit one

Strava allows one API application per athlete account, and that application has one Authorization Callback Domain. The live app's domain stays `riotraining.streamlit.app`. Editing it would replace the Streamlit callback `https://riotraining.streamlit.app/`.

1. Open the live application's page at [https://www.strava.com/settings/api](https://www.strava.com/settings/api) only to confirm the callback domain is still `riotraining.streamlit.app`. Change nothing on that page.
2. Create a second Strava account. Strava's getting-started page says a Strava subscription is required to create an API application. If the new account is asked to subscribe, that charge is Strava's. Skip this whole step if you are not testing Strava yet, and leave `RIO_STRAVA_CLIENT_ID` and `RIO_STRAVA_CLIENT_SECRET` unset. The rest of the test site still runs.
3. On the new account, open [https://www.strava.com/settings/api](https://www.strava.com/settings/api) and create an application.
4. **Authorization Callback Domain**: the Vercel hostname only, for example `rio-xxxx.vercel.app`. No `https://` and no path.
5. Copy that application's client id and client secret into the Render variables `RIO_STRAVA_CLIENT_ID` and `RIO_STRAVA_CLIENT_SECRET`. Save so Render redeploys. Streamlit Cloud keeps the original pair.
6. A new application starts in single-player mode: only the Strava account that owns it can connect. Use that account when you press Connect on the test site.

The redirect the API sends is `https://<vercel-host>/strava/callback`.

## 8. Read-only check for migrations 009, 010, and 011

In the Supabase dashboard, open **SQL Editor**, **New query**. Paste this and run it. It only reads.

```sql
select
  to_regclass('public.season_state') is not null as migration_009,
  to_regclass('public.strava_oauth') is not null as migration_010,
  (
    to_regclass('public.explain_spend') is not null
    and exists (
      select 1
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
      where n.nspname = 'public'
        and p.proname = 'reserve_explain_spend'
    )
    and exists (
      select 1
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
      where n.nspname = 'public'
        and p.proname = 'settle_explain_spend'
    )
    and exists (
      select 1
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
      where n.nspname = 'public'
        and p.proname = 'adopt_explain_spend'
    )
  ) as migration_011;
```

You want one row: `migration_009` true, `migration_010` true, `migration_011` true.

If a column is false, open that file and run it in the SQL editor, then run the select again. Each file is safe to run again.

- `supabase/migrations/009_season_state.sql` — quality base and workout notes. The API can rebuild a missing base, but the table is what a hosted save expects.
- `supabase/migrations/010_strava_oauth.sql` — the OAuth nonce. A hosted connect cannot start until this is true. The Streamlit callback does not read this table.
- `supabase/migrations/011_explain_spend.sql` — the shared spend counter. After this is true, leave `RIO_EXPLAIN_SPEND_PATH` unset and you may set the explain key, model, and base URL. Streamlit and this API then share one row.

## 9. Smoke test on the Vercel URL

1. Open `https://<render-host>/health`. Body: `{"ok":true}`.
2. Open `https://<vercel-host>/api/health`. Body: `{"ok":true}`. That is the rewrite. If this one fails while the Render URL is still waking, wait and try once more. The free instance sleeps after about 15 minutes of no traffic, and the first hit can take about a minute. Vercel allows a proxied request about two minutes.
3. Open `https://<vercel-host>`. Create an account or sign in with an account on this Supabase project. If confirmation mail is on, the link opens the Vercel origin, then you log in. The create-account screen still uses the existing sentence when a session does not come back.
4. Open Settings. A loaded page means `rio_hosted` was stored for the Vercel host and sent again to `/api`.
5. **Forgot password**. The mail link opens `https://<vercel-host>/reset-password` and the new-password form. It does not open Streamlit.
6. If step 7 is done: **Connect Strava**. After you approve, the browser lands on `https://<vercel-host>/settings?strava=connected` or `?strava=error`.
7. Open `https://riotraining.streamlit.app` and sign in. The live app still loads. Its secrets were not part of this setup.

## 10. No persistent disk

A file on Render's filesystem is wiped on restart, redeploy, and the free plan's spin-down. Free instances cannot attach a disk. This test does not need one.

- Explain spend moves into `public.explain_spend` when migration 011 is present and `RIO_EXPLAIN_SPEND_PATH` is unset. That is the shared counter. A JSON file would reset toward zero on restart and could let the $25 cap drift.
- Hero order and credits are `ui/assets/hero_rotation.json` in the repository. Leave `RIO_HERO_PATH` unset. The shipped file is what the test site serves. An admin save writes the container filesystem and does not survive a restart. That save is not required for the test.
- Hosted sessions, plans, Strava tokens, and the OAuth nonce are Supabase rows (migrations 006 and 010), not files.
- The insight log ignores a failed write. Leave `RIO_INSIGHT_LOG_PATH` unset.

A disk is the upgrade only if an admin hero edit, or a spend file you chose not to move, must survive restarts. Attach it only on a paid instance, mount it, and point `RIO_HERO_PATH` at a file on that mount. This checklist does not do that.

## 11. What would need a paid plan

The test itself is the free Render instance plus Vercel Hobby.

- Render free sleeps after about 15 minutes without traffic, allows 750 hours a month, and has 512 MB of RAM. If `/api/health` keeps failing on wake-up after a retry, change the instance to the $7/month size. In the dashboard that is the Starter / 512 MB instance. The blueprint plan id for that size is `0.5c-512mb`. It does not sleep. You still do not add a disk.
- A persistent disk is $0.25 per GB per month and only attaches to a paid instance. Skip it for this test.
- Vercel Hobby includes the `*.vercel.app` URL. A custom domain is not required, and adding one is not part of this test.
- A second Strava application may require a Strava subscription on the new account. That is separate from Render and Vercel. Skip Strava and the test site still serves plans, sign-in, and reset.
