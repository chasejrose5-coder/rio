# Resend email setup

Jay does these steps in Resend, DNS, Supabase, and Vercel. The app does not send mail. Supabase Auth sends it, and Resend is the SMTP server. Nothing in this list belongs in the repo, a pull request, or a Vercel variable except the public flag in step 7.

The live site is `https://www.riorunning.com`. Confirmation mail opens `https://www.riorunning.com/confirm`. Password-reset mail opens `https://www.riorunning.com/update-password`. `/reset-password` is the same new-password form, for a link that already points there. The apex `riorunning.com` redirects to `www`, and that redirect drops the token fragment, so the mail uses `www`.

Do not turn on Supabase SMTP, and do not set the Vercel flag, until the domain in Resend says verified and a test message has arrived.

## 1. Create a free Resend account

1. Open [https://resend.com/signup](https://resend.com/signup) and create an account. The free plan is enough.
2. Free-plan limits, from Resend's account quotas: 3,000 emails per month, 100 emails per UTC day (midnight to midnight UTC), up to 3 verified domains, and 10 requests per second for the team. Each recipient counts. A day over the cap returns `429` and does not queue the message. There is no overage on the free plan.

## 2. Verify `riorunning.com`

The sender in step 4 is `no-reply@riorunning.com`, so the domain you add is the root `riorunning.com`, not a subdomain. You do not create that mailbox. After the domain verifies, Resend will send from that address.

1. In Resend, open **Domains** and choose **Add Domain**.
2. Enter `riorunning.com`.
3. Pick a region before you save. It cannot be changed later. `us-east-1` is the usual choice for mail read in North America. The MX host Resend shows includes that region.
4. Open the domain's **Records** tab. Add every record it lists at the DNS host for `riorunning.com` (the registrar, Cloudflare, or wherever the nameservers point). Copy the values. Do not retype them.

These are the records Resend shows for a root domain. If a row on the dashboard differs, the dashboard wins.

| What it is | Type | Name | Value |
| --- | --- | --- | --- |
| DKIM | TXT | `resend._domainkey` | Copy from Resend. It is a long string that starts with `p=`. |
| SPF | MX | `send` | Copy the mail server from Resend. It looks like `feedback-smtp.us-east-1.amazonses.com` when the region is `us-east-1`. Priority `10`. |
| SPF | TXT | `send` | Copy from Resend. The current value is `v=spf1 include:amazonses.com ~all`. |
| Tracking, if listed | CNAME | `links` | Copy from Resend. |

If the domain has no DMARC record yet, add one more TXT. Name: `_dmarc`. Value: `v=DMARC1; p=none;`.

How to enter the names:

- If the DNS host appends the domain for you, the name is `send`, `resend._domainkey`, or `_dmarc`. It is not `send.riorunning.com`.
- If the host wants the full name, use `send.riorunning.com`, `resend._domainkey.riorunning.com`, and `_dmarc.riorunning.com`.
- Leave these records DNS-only. On Cloudflare, the proxy (orange cloud) stays off. A proxied record does not verify.
- Do not add a second SPF TXT on the root (`@`). Resend's SPF is on `send`, which is `send.riorunning.com`. A second SPF on the root breaks mail that already uses the root.
- The MX priority has to be unique on that name. If `10` is taken, use the next free number and the same number Resend shows if you can.

5. In Resend, click **Verify**. It often finishes within 15 minutes. It can take up to 72 hours. [https://dns.email](https://dns.email) shows whether the records are public. If it is still pending after 72 hours, use **Restart verification**. Leave Supabase on its built-in mailer until the domain says verified. That built-in mailer only reaches members of the Supabase organization, at about 2 messages per hour. `onboarding@resend.dev` does not deliver to athletes.

## 3. Create an API key

1. In Resend, open **API Keys** and create a key. Permission: **Sending access**. Full access also works.
2. Copy the key once. It starts with `re_`. Resend shows it only at creation. Store it in a password manager.
3. The key is the SMTP password in the next step. Do not commit it. Do not put it in Vercel, Render, GitHub, or this repo.

## 4. Turn on custom SMTP in Supabase

Use the Supabase project RIO already uses.

1. Open **Authentication**.
2. Open **Email** under **Notifications**. Older dashboards put this under **Authentication → Settings** or **Project Settings → Auth → SMTP**.
3. Open **SMTP Settings** and turn custom SMTP on.
4. Enter these values. The password is the Resend API key from step 3.

| Field | Value |
| --- | --- |
| Host | `smtp.resend.com` |
| Port | `465` |
| Username | `resend` |
| Password | the Resend API key (`re_...`) |
| Sender email | `no-reply@riorunning.com` |
| Sender name | `RIO` |

Port `465` is implicit TLS. The username is the word `resend`, not an email address. The sender has to be on the verified domain. Save.

After custom SMTP is on, Supabase sends to any address and then applies its own cap of about 30 messages per hour. That cap is separate from Resend's 100 per day. **Authentication → Rate Limits** is where that email cap is raised, if signups need more than 30 in an hour.

## 5. Paste the templates

**Authentication → Emails** (or **Notifications → Email → Templates**). Paste the subject into the subject field and the HTML file into the body. Leave `{{ .ConfirmationURL }}` and `{{ .NewEmail }}` as they are. Supabase fills them in when it sends.

| Template in Supabase | Subject | Body file |
| --- | --- | --- |
| Confirm signup | `Confirm your RIO account` | `docs/email/confirm-signup.html` |
| Reset password | `Reset your RIO password` | `docs/email/reset-password.html` |
| Change email address | `Confirm your new RIO email` | `docs/email/change-email.html` |

The button background is `#C2461F` with white text. `#E25A32` is the RIO mark and the text link. Confirm signup and Reset password use `{{ .ConfirmationURL }}` only. Change email also uses `{{ .NewEmail }}`. Save each template.

**Authentication → Sign In / Providers → Email**: leave Email enabled, turn **Confirm email** on, and leave **Secure email change** on if it is already on. Save. Accounts that already have a confirmed email, including Chase's, stay confirmed. This switch does not send them a new message and it does not change a password.

## 6. Point the links at the live site

**Authentication → URL Configuration.**

Set **Site URL** to `https://www.riorunning.com`.

Add these if they are missing. Do not delete the Streamlit URLs or the old Vercel URLs. A redirect that is not on the list is ignored, and the mail falls back to the Site URL.

- `https://www.riorunning.com/update-password`
- `https://www.riorunning.com/reset-password`
- `https://www.riorunning.com/confirm`
- `https://www.riorunning.com/`

For a laptop check against this same project, also add:

- `http://localhost:3000/update-password`
- `http://localhost:3000/reset-password`
- `http://localhost:3000/confirm`

On Render, confirm `RIO_FRONTEND_ORIGIN` is `https://www.riorunning.com` with `https://`, no path, and no trailing slash. If it already is, leave it. The API builds confirmation links as `{RIO_FRONTEND_ORIGIN}/confirm` and reset links as `{RIO_FRONTEND_ORIGIN}/update-password`. The apex and the old `vercel.app` hosts are rewritten to `https://www.riorunning.com` so the token is not dropped.

## 7. Set the Vercel flag

Log in hides **Forgot password?** until this variable is the string `true`. Visiting `/forgot-password` returns to Log in while it is off.

1. Open the Vercel project for `https://www.riorunning.com`. The root directory is `web`.
2. Open **Settings → Environment Variables**.
3. Add `NEXT_PUBLIC_PASSWORD_RESET_ENABLED`. The value is `true`. Apply it to **Production**. It is not a secret.
4. Saving the variable does not change the site that is already deployed. Next reads `NEXT_PUBLIC_` values when it builds. After SMTP is saving mail, start a new production deployment yourself. Do not set the flag, and do not redeploy for it, before a real message has arrived. A merge of the app change does not turn the link on by itself.

## 8. Check it

Use a real inbox. `delivered@resend.dev` only proves Resend accepted a test, and it still counts toward the free quota.

1. Create an account at `https://www.riorunning.com/create-account`. The page should say to check email.
2. Open the message. It should land on `https://www.riorunning.com/confirm` and say the email is confirmed. Then log in.
3. After the Vercel flag is `true` on the deployment you are looking at, **Forgot password?** on Log in should send a reset that opens `https://www.riorunning.com/update-password`. Save a new password, then log in with it.
4. Try an address that has no account. The sentence should match the one a real account gets. The page does not say whether the account exists.
5. In Settings, under Account, change the email. The address shown stays the old one until the confirmation link is opened.
