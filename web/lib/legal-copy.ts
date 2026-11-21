/** Draft privacy and terms. The sentences describe this codebase.
 *
 * Placeholders stay in brackets until the operator fills them in.
 * Do not add a company, address, court, or support address here.
 */

export const DRAFT_NOTE =
  "For review. This page is not in effect. [COMPANY NAME], [CONTACT EMAIL], and the governing law are placeholders.";

export const LEGAL_UPDATED = "November 16, 2026";

export type LegalBlock =
  | { kind: "p"; text: string }
  | { kind: "ul"; items: string[] };

export type LegalSection = {
  id: string;
  title: string;
  blocks: LegalBlock[];
};

export type LegalPage = {
  path: "/privacy" | "/terms";
  title: string;
  description: string;
  sections: LegalSection[];
};

export const PRIVACY: LegalPage = {
  path: "/privacy",
  title: "Privacy policy",
  description:
    "Draft description of the account, training data, Strava runs, and session cookie RIO stores. Not in effect.",
  sections: [
    {
      id: "what-this-is",
      title: "What this draft is",
      blocks: [
        {
          kind: "p",
          text: "RIO (Runner Intelligence Owned) is a training app for any runner. This draft says what the public site at riorunning.com stores today. It is a description of the code, for review. It is not a finished privacy policy, and it does not claim that any privacy law is already met.",
        },
        {
          kind: "p",
          text: "The operator is [COMPANY NAME]. A mailing address is not decided. The legal contact is [CONTACT EMAIL]. The email in the site footer is the current questions line. This draft does not make that address the legal contact.",
        },
      ],
    },
    {
      id: "account",
      title: "Account",
      blocks: [
        {
          kind: "p",
          text: "Create account asks for a name (up to 40 characters), an email address, and a password of 8 to 128 characters. Continue with Google is on those screens only when Google sign-in is turned on for that deploy. Until then the button is not shown. Google sign-in receives the email and the name from Google and opens the same account. The signup form does not ask for a birth date, a phone number, or a payment card. The app does not take payment.",
        },
        {
          kind: "p",
          text: "On the public site the account is created in Supabase Auth. Supabase sends a confirmation link that opens /confirm on this site. Password reset mail opens /update-password. Changing the email sends a confirmation link and keeps the old address until that link is opened. Supabase Auth stores the password. The training tables do not.",
        },
        {
          kind: "p",
          text: "The profile row stores the email and the display name. Settings can also store a preferred name, a time zone from a fixed list, pace units (per mile or per kilometer), a date format, compact mode, whether the next season starts today or next Sunday, whether to ask before a timed run changes later weeks, an easy pace, and whether workouts are finished with Done instead of splits. Those preferences are saved on the auth user's metadata. Heart rate settings store a resting heart rate, a max heart rate, whether a heart rate monitor is used, and any zone boundaries the runner edits. That row is on the heart_rate table and is readable only by that athlete.",
        },
        {
          kind: "p",
          text: "A copy of the app run without Supabase keeps the account in a file on that computer. That mode does not offer password-reset email. The public site uses the hosted account.",
        },
      ],
    },
    {
      id: "training",
      title: "Training you enter",
      blocks: [
        {
          kind: "p",
          text: "The only scored event in this version is the 800 meters. Starting a season stores the current 800 time, the start date, the goal 800 time, and the goal date, plus the generated plan. Logging a day stores the workout template and the rep times you type, or a Done mark when you are not using a watch. A season note, when one is saved, is stored with that season.",
        },
        {
          kind: "p",
          text: "Stretching stores the routine id and the date you mark Done. The exercise text stays in the app, not in the database. A sore spot stores the body region, a severity of mild, moderate, or sharp, the day it started, the check-in date, and whether you cleared it.",
        },
        {
          kind: "p",
          text: "Settings can export the current season as JSON. That file downloads to your computer. The app does not compute a goal probability or a readiness score.",
        },
      ],
    },
    {
      id: "prose",
      title: "Short notes from a model",
      blocks: [
        {
          kind: "p",
          text: "Classification of a workout is rules in the app, not a model. After a hard day is saved, the API may ask a language model to phrase a short note. That call runs only when the server is configured with a model key, a model name, and an https address for that model. If that configuration is missing, no model is called.",
        },
        {
          kind: "p",
          text: "The message is a reduced note the app already built: the goal 800 time, the race date, the phase and its name, the session date, the session family, whether the day was on track, short, or better, how later weeks are affected, a count of hard days that week, days left until the goal, the week number, and a short easy-heart-rate category. It does not include the email, the password, lap lists, or a Strava activity stream. A payload that contains the word Strava or GPS is refused. The vendor is whatever host that address points at. This draft does not name one, because the address is configuration.",
        },
        {
          kind: "p",
          text: "When a note is accepted, the server may record a hash of that reduced input and the accepted note in a private log. The prompt itself is not written there. The note you see in the app is stored with the season.",
        },
      ],
    },
    {
      id: "strava",
      title: "Strava",
      blocks: [
        {
          kind: "p",
          text: "Connecting Strava is optional. Home or Settings sends you to Strava's authorization page. The scope requested is activity:read_all, which is read access to your activities, including ones marked private on Strava. RIO does not request write access, and it does not upload your plan, email, or name to Strava.",
        },
        {
          kind: "p",
          text: "After you approve, RIO keeps the token fields it parses: access token, refresh token, expiry, Strava athlete id, the athlete's first and last name as one name, and the scope. Those tokens are stored where the signed-in account cannot read them. The server reads them with a privileged role. A short-lived connect nonce is stored the same way until the callback finishes.",
        },
        {
          kind: "p",
          text: "A sync reads Strava's activity list at /athlete/activities. When a summary has no laps, it also reads /activities/{id}. It keeps runs only: sport type Run, TrailRun, or VirtualRun, or a Workout whose name reads as a run and not a walk. Other sports are dropped. For each kept run it stores the activity id, name, sport type, local start, distance, moving time, elapsed time, pace, average heart rate, max heart rate, and laps (distance, moving time, elapsed time, pace, and average heart rate). It also stores whether that local date matches a planned session, and that session's template id.",
        },
        {
          kind: "p",
          text: "A recent sync continues from the last successful sync. A full sync ignores that time. The window goes back to the season start when that is earlier, and always at least 120 days. Imported runs are visible to the signed-in athlete. Strava data for one athlete is not shown to another account.",
        },
        {
          kind: "p",
          text: "Disconnect is in Settings, under Strava. It calls Strava's deauthorize endpoint and then deletes that athlete's stored token and imported activities.",
        },
        {
          kind: "p",
          text: "Strava's API Policy asks for this statement: Strava may monitor and collect usage data about this application's calls to the Strava API, and may use that usage data for any business purpose, internal or external, including improvements to the Strava API or the Strava platform, developer or user support, checking compliance with Strava's agreement, or otherwise.",
        },
        {
          kind: "p",
          text: "Strava's privacy policy is at https://www.strava.com/legal/privacy. Strava's API Policy says that policy controls if it conflicts with this one. This draft does not change Strava's privacy policy. Strava's own terms apply to the Strava account.",
        },
        {
          kind: "p",
          text: "Imported runs stay in RIO until you disconnect Strava or delete the account. Delete my account calls Strava's deauthorize endpoint with the stored token before that token and those runs are removed. If Strava cannot be reached, the account is still deleted and the stored token is removed with it. You can also revoke RIO in the Strava account settings.",
        },
      ],
    },
    {
      id: "storage",
      title: "Where it is stored",
      blocks: [
        {
          kind: "p",
          text: "The public site stores accounts and training rows in Supabase (Auth and Postgres). Row level security limits each signed-in athlete to their own rows. Session rows, Strava tokens, and the Strava connect nonce are not readable by the signed-in account.",
        },
        {
          kind: "p",
          text: "What is stored: the profile (email, display name, role, and when the account was created), the 800 meter goal, the plan and the logged days, season notes, stretch completions, sore spots, Strava tokens, imported Strava runs, the connect nonce, and the session. A separate counter tracks how much has been reserved for model notes. That counter is not an athlete profile.",
        },
      ],
    },
    {
      id: "cookie",
      title: "Cookie and browser storage",
      blocks: [
        {
          kind: "p",
          text: "Signing in sets one cookie, rio_hosted. The value is an opaque id that starts with rio1. It is HttpOnly, Secure, and SameSite=Lax, on path /, with no Domain attribute, so it stays on the host you opened. It lasts for the rest of 24 hours from sign-in. Refreshing the session does not extend that 24 hours. The cookie does not contain the Supabase access token or refresh token.",
        },
        {
          kind: "p",
          text: "Those tokens stay on the server, keyed by a hash of the cookie id. The stored session holds the access token, refresh token, user id, email, display name, and the time the session started. Only a privileged server role can read it. Sign out deletes the session and clears the cookie.",
        },
        {
          kind: "p",
          text: "The pages use sessionStorage for interface state: whether the splash was already shown, which page last played its entrance, and the plan view you picked. The account is not stored in localStorage. Settings, under Danger zone, has Clear local data. That clears localStorage and sessionStorage in that browser and signs you out. It does not delete the account on the server.",
        },
        {
          kind: "p",
          text: "This version of the web app does not load a third-party analytics script or an advertising script, and it does not set an analytics cookie.",
        },
      ],
    },
    {
      id: "delete",
      title: "Deleting a season or the account",
      blocks: [
        {
          kind: "p",
          text: "Past seasons, under More, can delete one season, including the season you are training on. You confirm on that page. The delete removes that season's plan, its season-state row, and logged results tied to that season. It does not delete the account, the Strava activities, or the stretch rows. The page says the delete cannot be undone.",
        },
        {
          kind: "p",
          text: "Settings, Danger zone, Reset plan removes stored seasons: plans, logged results, and season state. The account stays. It does not, by itself, delete Strava activities. You confirm with a checkbox. The page says reset removes stored seasons and the account stays.",
        },
        {
          kind: "p",
          text: "Settings, Danger zone, Delete my account asks you to check “I understand this permanently deletes my season and runs”. On the hosted site that checkbox is the confirmation. A local file account also asks for the email and the password. The server then deletes the session rows, the logged results, the plans, the goal row, and the profile, and then deletes the Supabase Auth user. Rows that reference the profile are removed with it, including Strava tokens and activities, stretch completions, sore spots, season state, and the Strava connect nonce, where those records are present.",
        },
        {
          kind: "p",
          text: "After a successful delete, the app signs you out and opens the sign-in screen. It does not send an email that the delete finished. There is no undelete in the app.",
        },
      ],
    },
    {
      id: "open",
      title: "Still open",
      blocks: [
        {
          kind: "ul",
          items: [
            "[COMPANY NAME], a street address, and [CONTACT EMAIL] are not decided.",
            "No governing law or court is chosen in this draft.",
          ],
        },
      ],
    },
  ],
};

export const TERMS: LegalPage = {
  path: "/terms",
  title: "Terms",
  description:
    "Draft description of what RIO does, the account, and how a season or account is deleted. Not in effect.",
  sections: [
    {
      id: "what-this-is",
      title: "What this draft is",
      blocks: [
        {
          kind: "p",
          text: "These are draft terms for RIO, a training app for any runner, at riorunning.com. They describe the product as it works today. They are not in effect. Using the site while this draft is published does not make it a contract.",
        },
        {
          kind: "p",
          text: "The operator is [COMPANY NAME]. The legal contact is [CONTACT EMAIL]. No street address, price, warranty, liability cap, refund rule, age minimum, or governing law is decided here. The app does not ask for a birth date and does not block signup by age.",
        },
      ],
    },
    {
      id: "service",
      title: "The product",
      blocks: [
        {
          kind: "p",
          text: "You create an account, enter an 800 meter time you can run now, a start date, a goal time, and a race date. The app builds a plan from rules. You log workouts. You can connect Strava. The only scored event in this version is the 800 meters.",
        },
        {
          kind: "p",
          text: "The plan is not a prediction of your race. The app does not show a goal probability or a readiness score. It is not a medical device, and this draft does not add a medical disclaimer beyond that fact.",
        },
      ],
    },
    {
      id: "account",
      title: "The account",
      blocks: [
        {
          kind: "p",
          text: "Create account asks for a name, an email, and a password of 8 to 128 characters. On the public site, Supabase sends a confirmation email when the project requires one. You sign in with that email and password. A session lasts 24 hours from sign-in, then you sign in again. Sign out clears the session.",
        },
        {
          kind: "p",
          text: "Continue with Google is shown only when Google sign-in is turned on. A new Google account follows the same first-run screens as an email account. The app does not collect a payment.",
        },
      ],
    },
    {
      id: "data",
      title: "Your training data",
      blocks: [
        {
          kind: "p",
          text: "What is stored, including the Strava read, is described in the draft privacy policy. Other athletes are not given your rows. You can export a season as JSON from Settings.",
        },
        {
          kind: "p",
          text: "You can delete one season from Past seasons, including the season you are training on. Reset plan, in Settings, removes stored seasons and leaves the account. Disconnect, under Strava in Settings, tells Strava to deauthorize and deletes the imported runs stored here. Delete my account, in Settings, removes the account as the privacy draft describes, then the app returns you to sign-in.",
        },
      ],
    },
    {
      id: "strava",
      title: "Strava",
      blocks: [
        {
          kind: "p",
          text: "Connecting Strava is optional and happens on Strava's site. RIO reads runs with the activity:read_all scope and does not write activities back. Strava's terms and privacy policy apply to your Strava account. This draft does not change them. Strava's privacy policy is at https://www.strava.com/legal/privacy.",
        },
      ],
    },
    {
      id: "open",
      title: "Still open",
      blocks: [
        {
          kind: "ul",
          items: [
            "[COMPANY NAME], [CONTACT EMAIL], a street address, and the governing law are not decided. This draft does not choose a court.",
            "No warranty, liability cap, or refund rule is stated, because none is decided.",
            "No age rule is enforced by the signup form.",
          ],
        },
      ],
    },
  ],
};

export function legalPlainText(page: LegalPage): string {
  const parts = [page.title, DRAFT_NOTE];
  for (const section of page.sections) {
    parts.push(section.title);
    for (const block of section.blocks) {
      if (block.kind === "p") parts.push(block.text);
      else parts.push(...block.items);
    }
  }
  return parts.join("\n");
}
