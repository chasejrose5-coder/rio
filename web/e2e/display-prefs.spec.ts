import { expect, test, type Page, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "admin",
  kind: "local",
  today: "2026-11-10",
  next_session: "2026-11-10",
  prefs: {
    easy_pace: "7:25",
    easy_pace_unit: "mi",
    intro_seen: true,
    no_watch: false,
    confirm_adapt: false,
    timezone: "America/Los_Angeles",
    date_format: "iso",
    units: "miles",
    show_ids: true,
    compact: true,
  },
};

const template = "se_150_r150_x8";

const home = {
  today: "2026-11-10",
  athlete,
  hello: "Hey Ada",
  strava_offer: false,
  copy: "",
  season: {
    inputs: { current_time: "2:08.0", start_date: "2026-11-08", goal_time: "1:59.0", goal_date: "2027-04-18" },
    digest: "digest-1",
    view: { days_remaining: 159, phase: "4", mark: null, focus: "Speed" },
    phase: null,
    pace_status: "No runs yet",
    next: {
      date: "2026-11-10",
      shown_date: "2026-11-10",
      day_of_week: "Tuesday",
      template_id: template,
      label: "8 × 150 m",
      facts: { distance: "1,200 m", pace: "23.0 s", rest: "150 s", reps: "8" },
      prescription: { line: "8 × 150 m @ 23.0 s, 150 s rest", tolerance: "22.0-24.0 s", block: "" },
    },
    upcoming: [],
    next_days: [],
    notes: [],
  },
};

const plan = {
  inputs: home.season.inputs,
  digest: "digest-1",
  marks: {},
  prefs: { ...athlete.prefs, today: "2026-11-10" },
  months: ["2026-11-01"],
  month: "2026-11",
  month_title: "November 2026",
  calendar: [[{ date: "2026-11-10", in_month: true, day: 10, label: "Speed", template_id: template, today: true }]],
  weeks: [{ week: 1, phase: "4", status: "current", meters: 0, volume: "", days_remaining: 6 }],
  sessions: [
    {
      date: "2026-11-10",
      shown_date: "2026-11-10",
      week_number: 1,
      day_of_week: "Tuesday",
      template_id: template,
      label: "8 × 150 m",
      target: "Hit the session.",
      reason_codes: [],
    },
  ],
  pace_status: "No runs yet",
};

const session = {
  date: "2026-11-10",
  session: { date: "2026-11-10", day_of_week: "Tuesday", template_id: template, week_number: 1, reason_codes: [], target_outcome: "Hit the session." },
  actual: null,
  quality: true,
  note: null,
  viewed: false,
  digest: "digest-1",
  label: "8 × 150 m",
  structure: "8 × 150 m, 150 s rest",
  target: "Hit the session.",
  reasons: ["Phase 4"],
  shown_date: "2026-11-10",
  prescription: { line: "8 × 150 m @ 23.0 s, 150 s rest", tolerance: "22.0-24.0 s", block: "", average: "23.0 s" },
  logging: "times",
  confirm_adapt: false,
  show_id: true,
  boxes: 8,
  seed: [null, null, null, null, null, null, null, null],
  summary: "",
  match: null,
  heart_rate: "",
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(page: Page, options: { showIds?: boolean; compact?: boolean } = {}) {
  const person = {
    ...athlete,
    prefs: {
      ...athlete.prefs,
      show_ids: options.showIds !== false,
      compact: options.compact !== false,
    },
  };
  let signed = false;
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/me") {
      if (!signed) return json(route, { detail: "Sign in again." }, 401);
      return json(route, person);
    }
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/auth/sign-in") {
      signed = true;
      return json(route, { email: person.email, display_name: person.display_name, kind: "local" });
    }
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/home") return json(route, { ...home, athlete: person });
    if (path === "/plan") return json(route, { ...plan, prefs: { ...person.prefs, today: "2026-11-10" } });
    if (path === "/seasons/current") {
      return json(route, { today: "2026-11-10", inputs: plan.inputs, digest: "digest-1", plan: { season_length_weeks: 23 } });
    }
    if (path === "/activities") {
      return json(route, {
        rows: [],
        all: [],
        cards: [],
        groups: [],
        summary: null,
        weekly_meters: [],
        heart: [],
        figures: { distance: "0.0 mi", heart: "—" },
        length: 23,
        start_date: "2026-11-08",
        goal_date: "2027-04-18",
        notice: null,
        strava: { configured: false, connected: false, athlete_name: "", last_sync_at: null },
        logged: [],
      });
    }
    if (path === "/strava/status") {
      return json(route, { configured: false, connected: false, athlete_name: "", last_sync_at: null, redirect_uri: "" });
    }
    if (path.startsWith("/sessions/")) return json(route, session);
    return json(route, { detail: "Not mocked." }, 404);
  });
}

async function signIn(page: Page) {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/sign-in"));
}

test("compact mode tightens home, plan, session, and activity", async ({ page }) => {
  await install(page);
  await signIn(page);
  await page.goto("/home");
  await expect(page.locator(".page-home")).toHaveClass(/is-compact/);
  await expect(page.locator(".rio-track-id")).toHaveText(template);

  await page.goto("/plan");
  await expect(page.locator(".page-plan")).toHaveClass(/is-compact/);
  await page.getByText("This week", { exact: true }).click();
  await expect(page.locator(".rio-daycard-id")).toHaveText(template);
  await page.getByText("Full season", { exact: true }).click();
  await expect(page.locator(".rio-day .rio-template-id")).toHaveText(template);

  await page.goto("/session?date=2026-11-10");
  await expect(page.locator(".page-session")).toHaveClass(/is-compact/);
  await expect(page.locator(".rio-template-id")).toHaveText(template);

  await page.goto("/activity");
  await expect(page.locator(".page-activity")).toHaveClass(/is-compact/);
});

test("template ids stay off the track and the plan cards when the setting is off", async ({ page }) => {
  await install(page, { showIds: false, compact: false });
  await signIn(page);
  await page.goto("/home");
  await expect(page.locator(".page-home")).not.toHaveClass(/is-compact/);
  await expect(page.getByText("8 × 150 m @ 23.0 s, 150 s rest")).toBeVisible();
  await expect(page.locator(".rio-template-id")).toHaveCount(0);

  await page.goto("/plan");
  await expect(page.locator(".page-plan")).not.toHaveClass(/is-compact/);
  await page.getByText("This week", { exact: true }).click();
  await expect(page.locator(".rio-daycard")).toBeVisible();
  await expect(page.locator(".rio-template-id")).toHaveCount(0);
  await page.getByText("Full season", { exact: true }).click();
  await expect(page.locator(".rio-day")).toBeVisible();
  await expect(page.locator(".rio-template-id")).toHaveCount(0);
});
