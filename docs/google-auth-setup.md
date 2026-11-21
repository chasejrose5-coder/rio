# Google sign-in

Continue with Google is already in the app. It stays hidden until you turn it on. This page is the dashboard work. Do not put the Google client secret, or any Supabase key, in the repo, in a pull request, or in Vercel.

The live site is `https://www.riorunning.com`. Google talks to Supabase. Supabase then sends the browser to `https://www.riorunning.com/auth/callback`. That page signs the person in and sends a new account through the same first-run screens as email: easy pace, the intro, then Start. An account that already has a season opens Home.

The button is off until `NEXT_PUBLIC_GOOGLE_AUTH_ENABLED` is `true` on the Vercel build. Leave it unset while you do steps 1 through 4. Set it last, in step 5, and redeploy.

Deploy this change to the API and the web before you try a real Google sign-in. The callback page has to be on `www.riorunning.com`, and the API has to be this version. Leave `RIO_GOOGLE_REDIRECT_URI` unset on Render. With it unset, the API uses `{RIO_FRONTEND_ORIGIN}/auth/callback`, which is already `https://www.riorunning.com/auth/callback`.

No billing account is required for the Google client.

## 1. Create a free Google Cloud OAuth client

1. Open [https://console.cloud.google.com/](https://console.cloud.google.com/) and create a project, or pick one you already use for RIO. The project does not need a billing account.
2. Open **Google Auth Platform**. Older consoles call this **APIs & Services → OAuth consent screen**.
3. If Google asks for the user type, choose **External**.
4. Set the app name to `RIO`. Set the user support email to your own email. Under authorized domains, add `riorunning.com`. Set the developer contact email to your own email.
5. Add only these scopes: `openid`, `email`, and `profile`. Do not add extra scopes.
6. If Google asks for a privacy policy and terms before you can publish, use `https://www.riorunning.com/privacy` and `https://www.riorunning.com/terms`. Those pages are drafts.
7. Open **Clients** (older consoles: **APIs & Services → Credentials**) and create an OAuth client ID. The application type is **Web application**.
8. Under **Authorized JavaScript origins**, add `https://www.riorunning.com`. For a laptop check against this same client, also add `http://localhost:3000`.
9. Under **Authorized redirect URIs**, add the Supabase callback and nothing else. Copy it from the Supabase Google provider page in step 2. It is exactly:

   `https://<project-ref>.supabase.co/auth/v1/callback`

   `<project-ref>` is the subdomain of the Supabase project RIO already uses. Do not put `https://www.riorunning.com/auth/callback` here. That address belongs in Supabase, in step 3. Google only redirects to Supabase.
10. Create the client. Copy the client ID and the client secret once. Store the secret in a password manager. Do not commit it, and do not paste it into Vercel or Render.

While the Google app is in **Testing**, only the test users you list can sign in. Add your own Google account as a test user and try the button before you publish. When any Google account should be able to sign in, open **Audience** (or the OAuth consent screen) and click **Publish app**. `openid`, `email`, and `profile` are the non-sensitive scopes. Leave **Skip nonce check** off in Supabase. That switch is for native apps, not this website.

## 2. Paste the client into Supabase

In the Supabase dashboard for the project RIO already uses:

1. Open **Authentication**.
2. Open **Sign In / Providers** (older dashboards: **Providers**).
3. Open **Google**.
4. Turn Google on.
5. Paste the client ID and the client secret from step 1.
6. Leave **Skip nonce check** off.
7. Save.

The same page shows the callback URL. That is the value you put in Google Cloud in step 1. If you created the Google client first, come back and confirm the two strings match character for character, including `https://` and `/auth/v1/callback`.

Confirm email can stay on. Google has already verified the address, so a new Google account does not stop on Check your email.

A Google account whose email already has a RIO password is not merged by this app. That person keeps using the email form. If Google reports that the email is already registered, use Log in with the password.

## 3. Site URL and redirect URLs

**Authentication → URL Configuration.**

Site URL stays `https://www.riorunning.com`. Do not change it.

Leave every redirect URL that is already there. Do not delete the Streamlit or old Vercel entries. Add these if they are missing:

- `https://www.riorunning.com/auth/callback`
- `https://www.riorunning.com/auth/callback*`

The star is required. Each attempt adds `?flow=` so the API can tell one sign-in from another. Supabase's `*` matches the query string. An exact URL with no star does not.

For a laptop check, also add:

- `http://localhost:3000/auth/callback*`

Save. Supabase ignores a redirect that is not on this list and falls back to the Site URL. If that happens, the browser never reaches `/auth/callback` and the sign-in does not finish.

## 4. Confirm the button is still hidden

Open `https://www.riorunning.com/sign-in` and `https://www.riorunning.com/create-account`. Neither page should say Continue with Google yet. Email login is unchanged.

## 5. Set the Vercel flag

In the Vercel project for the web app (root directory `web`):

1. Open **Settings → Environment Variables**.
2. Add `NEXT_PUBLIC_GOOGLE_AUTH_ENABLED`.
3. Set the value to `true`.
4. Apply it to **Production**. Leave Preview unset. A preview host is not on the redirect list above, so the button there would not finish.
5. Redeploy the web service. This variable is read when the site is built. Saving it does not change the live site until the next deploy.

The value is public. It is baked into the browser bundle. It is not a secret. Do not put the Google client secret in this variable, or in any other Vercel or Render variable.

Do not set `RIO_GOOGLE_REDIRECT_URI` on Render. Unset is the live callback.

## 6. Check it

1. After the redeploy, Log in and Create account both show **Continue with Google**, with the email form still under it.
2. Use a Google account that has never had a RIO password. You should land on **Your easy pace**, then the intro, then Start. That is the same path as a new email account.
3. Sign out, and use Continue with Google again after a season exists. You should land on Home.
4. Cancel on Google's screen. You should come back to Log in, the email form should still work, and the page should say the Google sign-in could not be finished.
5. Set the Vercel value back to empty, or delete it, and redeploy if you need the button hidden again. The provider can stay on in Supabase. The button is what the flag controls.
