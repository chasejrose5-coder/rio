# Email setup

RIO does not send mail itself. Supabase Auth sends it, and Resend is the SMTP server Supabase uses. This page is the dashboard work. The app code is already in place. Do not put the Resend API key, or any Supabase key, in the repo or in a pull request.

The live site is `https://www.riorunning.com`. `riorunning.com` redirects there. On Render, `RIO_FRONTEND_ORIGIN` and `RIO_CALLBACK_BASE_URL` should both be `https://www.riorunning.com`, with `https://`, no path, and no trailing slash. This setup does not change Render, Vercel, or Supabase for you. You change Supabase in the dashboard after Resend is ready.

What the app does once this is saved:

- **Log in** shows **Forgot password?** when accounts are hosted. The reset link opens `/reset-password`. An address with no account gets the same sentence as one that has an account.
- **Create account** shows **Check your email** when Supabase asks for confirmation. The person cannot log in until they open the link. **Resend confirmation email** sends it again. The link opens `/confirm`.
- **Settings → Account → Change email** asks Supabase to send its confirmation. The address in Settings stays the old one until that link is confirmed. With secure email change on, Supabase also mails the old address, and both links have to be opened.

## 1. Create a free Resend account and an API key

1. Open [https://resend.com/signup](https://resend.com/signup) and create an account.
2. In the Resend dashboard, open **API Keys** and create a key. The permission can be **Sending access**. Full access also works.
3. Copy the key once. It starts with `re_`. Resend shows it only at creation. Store it in a password manager. You will paste it into Supabase as the SMTP password. Do not commit it.

The free plan, from Resend's account quotas, is:

- 3,000 transactional emails per month.
- 100 emails per UTC day. The day is midnight to midnight UTC, not a rolling 24 hours from the first send.
- Sent mail and received (inbound) mail both count. Each To, Cc, or Bcc recipient counts as its own email.
- Up to 3 verified domains.
- 10 requests per second for the whole team, not per key.
- Test messages count against the same quota.

When a quota stops a send, Resend returns `429` and does not queue the message. The next UTC day clears the daily cap. The monthly cap clears on the billing cycle. The free plan has no overage. A bounce rate at or above 4%, or a spam rate above 0.08%, can pause sending.

## 2. Verify a sending domain

Resend's SMTP guide lists a verified domain as a prerequisite. You send from an address on a domain you own, such as `rio@yourdomain.com`. You do not create that mailbox first. After the domain verifies, any address at that domain can be the From line.

1. In Resend, open **Domains** and add the domain. A subdomain such as `mail.yourdomain.com` or `auth.yourdomain.com` keeps this mail off the reputation of a root domain you might use for something else. The region and return path cannot be changed later.
2. Add the DNS records Resend shows (SPF, DKIM, and the return path) at the host that serves DNS for that domain. Add a DMARC record too if the domain does not have one.
3. In Resend, click **Verify**. DNS can take minutes, or longer. Leave the tab and check again. Do not turn on Supabase SMTP with a domain that still says pending.

### What happens with no verified domain

You cannot send RIO's signup, reset, or email-change mail to athletes.

Resend's current domain docs say you must verify at least one domain before Resend will send. The SMTP setup page says the same thing: an API key and a verified domain. The shared sender `onboarding@resend.dev` still appears in Resend's API examples. It is for experiments against Resend's own test inboxes (`delivered@resend.dev`, `bounced@resend.dev`, `complained@resend.dev`, `suppressed@resend.dev`). Those test inboxes do not deliver to a real person, and they still count toward the free quota. Some accounts can also send from `onboarding@resend.dev` only to the email on the Resend account. Neither path delivers a confirmation or a reset to Chase, or to anyone else who signs up.

The free-plan numbers in step 1 apply after the domain is verified. Verifying a domain does not raise the 100-per-day or 3,000-per-month cap.

Until this domain is verified, leave Supabase on its built-in mailer if you are only testing with the project's team addresses. That built-in mailer sends only to members of the Supabase organization, and Supabase currently caps it at about 2 messages per hour. It is not the production path.

## 3. Put the Resend SMTP settings in Supabase Auth

In the Supabase dashboard for the project RIO already uses:

1. Open **Authentication**.
2. Open **Email** under **Notifications**. (Older dashboards put this under **Authentication → Settings** or **Project Settings → Auth → SMTP**.)
3. Open **SMTP Settings**.
4. Turn custom SMTP on.
5. Use these values. The password is the Resend API key from step 1. The sender email must be on the verified domain.

| Field | Value |
| --- | --- |
| Host | `smtp.resend.com` |
| Port | `465` |
| Username | `resend` |
| Password | the Resend API key (`re_...`) |
| Sender email | an address on the verified domain, for example `rio@auth.yourdomain.com` |
| Sender name | `RIO` |

Port `465` is implicit TLS. Resend also accepts `587` for STARTTLS. Supabase's Resend guide uses `465`. Use that unless the form rejects it.

Save. After a custom SMTP server is on, Supabase sends to any address, then applies its own cap of about 30 messages per hour until you raise it. That cap is separate from Resend's 100 per day. Open **Authentication → Rate Limits** and raise the email rate if 30 per hour is too low for signups. Do not put the API key anywhere except this password field.

## 4. Turn on Confirm email

1. Open **Authentication → Sign In / Providers** (or **Providers**).
2. Open the **Email** provider.
3. Leave Email enabled.
4. Turn **Confirm email** on.
5. Leave **Secure email change** on if it is already on. That is what sends the change-email confirmation to the new address and, when secure change is on, to the old address as well.
6. Save.

Confirm email applies to accounts created after you turn it on. It does not send a confirmation by itself to people who already have an account. Step 7 is the detail for Chase.

## 5. Paste the templates

Supabase has a subject line and a body for each template. Paste the subject into the subject field. Paste the HTML file into the body. The files are the whole message Supabase will send. Leave Supabase's `{{ .ConfirmationURL }}` variables as they are. Do not replace them with a real link. Supabase fills them in when it sends.

Open **Authentication → Emails** (or **Notifications → Email → Templates**).

| Template in Supabase | Subject | Body file |
| --- | --- | --- |
| Confirm signup | `Confirm your RIO account` | `docs/email/confirm-signup.html` |
| Reset password | `Reset your RIO password` | `docs/email/reset-password.html` |
| Change email address | `Confirm your new RIO email` | `docs/email/change-email.html` |

The button background is `#C2461F` with white text. `#E25A32` is the RIO mark and the text link. Save each template.

The change-email template uses `{{ .NewEmail }}` as well as `{{ .ConfirmationURL }}`. The other two use `{{ .ConfirmationURL }}`. If a preview still shows the braces, the variable name does not match that template. Confirm signup and Reset password do not have `{{ .NewEmail }}`.

## 6. Redirect URLs

**Authentication → URL Configuration.**

Set **Site URL** to `https://www.riorunning.com`.

Leave these redirect URLs in place. Do not delete them. The parked Streamlit app still builds its own links, and a mail link that already points at an old host should still be allowed.

- `https://riotraining.streamlit.app`
- `https://riotraining.streamlit.app/**`
- `http://localhost:8501`
- `http://localhost:8501/**`
- `https://rio-one-mocha.vercel.app/`
- `https://rio-one-mocha.vercel.app/reset-password`
- `https://rio-one-mocha.vercel.app/confirm`
- `https://rio-rio-44fa.vercel.app/`
- `https://rio-rio-44fa.vercel.app/reset-password`
- `https://rio-rio-44fa.vercel.app/confirm`

Add these if they are not already on the allow list. Supabase ignores a redirect that is not listed and falls back to the Site URL.

- `https://www.riorunning.com/reset-password`
- `https://www.riorunning.com/confirm`
- `https://www.riorunning.com/`

Signup confirmation and email change both use `/confirm`. Password reset uses `/reset-password`. Mail uses the `www` origin. The apex `riorunning.com` redirects to `www`, and that redirect would drop the token fragment.

For a laptop check against this same project, also add:

- `http://localhost:3000/reset-password`
- `http://localhost:3000/confirm`

The code builds those paths from `RIO_FRONTEND_ORIGIN`. On Render that value is `https://www.riorunning.com`, so the live mail uses the `www` URLs. A local API only uses the localhost URLs when `RIO_FRONTEND_ORIGIN` is `http://localhost:3000`.

A link Supabase marks expired lands on `/confirm` or `/reset-password` with an error, and the page says the link is no longer valid. Reset offers **Send a new reset email**. A signup that is still unconfirmed can use **Resend confirmation email** on Check your email, or on Log in after a try with the right password.

## 7. Existing accounts, including Chase's

Turning **Confirm email** on does not wipe accounts, passwords, or seasons. It does not run SQL. Supabase sets `email_confirmed_at` when an account is created while confirmation is off. Those people are already confirmed.

Chase can keep logging in with his current password. He does not get a confirmation email just because the switch is on. His season stays where it is. Settings still shows the email he already uses.

The same is true for every other account that has logged in, or was created, while confirmation was off.

Someone whose `email_confirmed_at` is empty cannot log in after the switch. Log in says to check email and offers **Resend confirmation email**. That is the case for a new signup, and for an older account that was created while confirmation was already on but never finished. It is not the normal case for Chase.

After the switch:

- A new signup sees **Check your email**, then has to open the link before Log in will accept the password.
- Forgot password still sends a reset to a confirmed account. An address RIO does not have gets the same "Check your email for the reset link." sentence. The page does not say whether the account exists.
- Change email in Settings sends Supabase's confirmation and leaves the current address in place until the link is opened. If secure email change is on, open the message at the new address and the message at the old address. Then log in, or return to Settings on the browser that was already signed in. Settings shows the new address after the change has gone through. The profile email column stays locked by migration 005. The app reads the confirmed auth email, not a hand-edit of that column.

No migration is required for this. Do not run SQL to confirm Chase or anyone else.

## 8. Check it

Use a real inbox on the verified domain's sending path. `delivered@resend.dev` only proves Resend accepted a test.

1. Create a new account on `https://www.riorunning.com/create-account`. You should see **Check your email**, not a logged-in home page.
2. Open the message. It should land on `https://www.riorunning.com/confirm` and say the email is confirmed. Then log in with that password.
3. Before confirming, a login with the right password should say to check email and offer **Resend confirmation email**.
4. **Forgot password?** on Log in should send a reset that opens `/reset-password`. Save a new password, then log in with it. Try an address you know has no account. The sentence should match the one a real account gets.
5. In Settings, under Account, change the email. The flash should say to check email. The address shown above the form should stay the old one until the confirmation link is opened.
