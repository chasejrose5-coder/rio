import { expect, test, type Page, type Route } from "@playwright/test";

const today = "2026-11-10";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today,
  prefs: {
    easy_pace: "7:45",
    easy_pace_unit: "mi",
    intro_seen: true,
    date_format: "iso",
    units: "miles",
    confirm_adapt: false,
    timezone: "America/Los_Angeles",
  },
};

const inputs = {
  current_time: "2:05.0",
  start_date: "2026-11-08",
  goal_time: "1:58.0",
  goal_date: "2026-11-21",
};

function planBody(
  month = "2026-11",
  marks: Record<string, string> = {},
  prefs: typeof athlete.prefs = athlete.prefs,
) {
  const november = month === "2026-11";
  return {
    inputs,
    digest: "digest-1",
    marks,
    prefs: { ...prefs, today },
    months: ["2026-11-01", "2026-12-01"],
    month,
    month_title: november ? "November 2026" : "December 2026",
    calendar: november
      ? [[
          { date: "2026-11-01", in_month: false, day: 0, label: "", template_id: "", today: false },
          { date: "2026-11-02", in_month: true, day: 2, label: "", template_id: "", today: false },
          { date: "2026-11-03", in_month: true, day: 3, label: "Easy", template_id: "aer_8000_r0_x1", today: false },
          { date: "2026-11-10", in_month: true, day: 10, label: "Speed", template_id: "se_400_r90_x6", today: true },
          { date: "2026-11-11", in_month: true, day: 11, label: "", template_id: "", today: false },
          { date: "2026-11-12", in_month: true, day: 12, label: "", template_id: "", today: false },
          { date: "2026-11-13", in_month: true, day: 13, label: "", template_id: "", today: false },
        ]]
      : [[
          { date: "2026-11-29", in_month: false, day: 0, label: "Easy", template_id: "aer_8000_r0_x1", today: false },
          { date: "2026-12-01", in_month: true, day: 1, label: "Easy", template_id: "aer_5000_r0_x1", today: false },
          { date: "2026-12-02", in_month: true, day: 2, label: "", template_id: "", today: false },
          { date: "2026-12-03", in_month: true, day: 3, label: "", template_id: "", today: false },
          { date: "2026-12-04", in_month: true, day: 4, label: "", template_id: "", today: false },
          { date: "2026-12-05", in_month: true, day: 5, label: "", template_id: "", today: false },
          { date: "2026-12-06", in_month: true, day: 6, label: "", template_id: "", today: false },
        ]],
    weeks: [
      { week: 1, phase: "4", status: "current", days_remaining: 11, meters: 0, volume: "0 m" },
      { week: 2, phase: "4", status: "upcoming", days_remaining: 4, meters: 0, volume: "0 m" },
    ],
    sessions: [
      {
        date: "2026-11-10",
        shown_date: "2026-11-10",
        day_of_week: "Tuesday",
        week_number: 1,
        template_id: "se_400_r90_x6",
        label: "6 × 400 m near goal 800 pace, 90 s rest",
        target: "Hit: reps near goal 800 pace (1:58.0) with the rest kept.",
        reason_codes: ["phase_4", "phase_primary"],
        prescription: { line: "6 × 400 m @ 71.2 s, 90 s rest", tolerance: "68.0-74.4 s", block: "12:06.0" },
      },
      {
        date: "2026-11-12",
        shown_date: "2026-11-12",
        day_of_week: "Thursday",
        week_number: 1,
        template_id: "aer_8000_r0_x1",
        label: "8 km easy, Zone 2",
        target: "Hit: one continuous easy run, talkable the whole way.",
        reason_codes: ["phase_4", "extra_easy_day"],
        prescription: { line: "Run at 7:45 per mile", tolerance: "", block: "" },
      },
      {
        date: "2026-11-17",
        shown_date: "2026-11-17",
        day_of_week: "Tuesday",
        week_number: 2,
        template_id: "aer_5000_r0_x1",
        label: "5 km easy, Zone 2, talkable the whole way",
        target: "Hit: one continuous easy run, talkable the whole way.",
        reason_codes: ["phase_4", "extra_easy_week"],
        prescription: { line: "Run at 7:45 per mile", tolerance: "", block: "" },
      },
    ],
  };
}

const home = {
  today,
  athlete,
  hello: "Hey Ada",
  strava_offer: false,
  copy: "",
  season: {
    inputs,
    digest: "digest-1",
    view: { days_remaining: 11, phase: "4", mark: null, focus: "Speed endurance" },
    phase: null,
    pace_status: "No runs yet",
    next: null,
    upcoming: [],
    next_days: [],
    notes: [],
  },
};

const activities = {
  rows: [{ date: "2026-11-10", meters: 2400, work: "2,400 m", hr: "150 bpm", id: "run-1" }],
  all: [
    { date: "2026-11-11", name: "Shakeout", extra: true, id: "extra-1", shown_date: "2026-11-11" },
    { date: "2026-11-10", name: "Planned", extra: false, id: "run-1" },
  ],
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function installApi(page: Page, options: { season?: boolean; confirm?: boolean; dateFormat?: string; bad?: string; notice?: string | null }) {
  let marks: Record<string, string> = {};
  let signed = false;
  const prefs = { ...athlete.prefs, confirm_adapt: options.confirm === true, date_format: options.dateFormat || "iso" };
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/me") {
      if (!signed) return json(route, { detail: "Sign in again." }, 401);
      return json(route, { ...athlete, today, prefs: { ...prefs, today } });
    }
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/auth/sign-in") {
      signed = true;
      return json(route, { email: athlete.email, display_name: athlete.display_name, kind: "local" });
    }
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/seasons/current" && route.request().method() === "GET") {
      if (!options.season) return json(route, { detail: "No current season." }, 404);
      return json(route, { today, inputs, digest: "digest-1", marks, actuals: {}, plan: { sessions: planBody("2026-11", {}, prefs).sessions } });
    }
    if (path === "/home") return json(route, options.season ? home : { ...home, season: null, copy: "Generate a season on Start." });
    if (path === "/plan") {
      if (!options.season) return json(route, { detail: "No current season." }, 404);
      if (options.bad) return json(route, { detail: options.bad }, 400);
      const month = url.searchParams.get("month") || "2026-11";
      if (month !== "2026-11" && month !== "2026-12") return json(route, { detail: "The month is not YYYY-MM." }, 400);
      return json(route, planBody(month, marks, prefs));
    }
    if (path === "/activities") {
      if (!options.season) return json(route, { detail: "No current season." }, 404);
      return json(route, { ...activities, notice: options.notice ?? null });
    }
    if (path === "/seasons/current/marks" && route.request().method() === "POST") {
      const body = route.request().postDataJSON() as { week: number; choice: string };
      marks = { ...marks, [String(body.week)]: body.choice };
      return json(route, { digest: "digest-2", marks, committed: true, inputs });
    }
    return json(route, { detail: "Not mocked." }, 404);
  });
}

async function signIn(page: Page) {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
}

test("no season offers Start and does not draw an empty calendar", async ({ page }) => {
  await installApi(page, { season: false });
  await signIn(page);
  await page.goto("/plan");
  await expect(page.getByRole("heading", { name: "Plan" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Generate season plan" })).toBeVisible();
  await expect(page.getByText("Photo by Jan van der Wolf on Pexels")).toBeVisible();
  await expect(page.locator(".rio-cal")).toHaveCount(0);
  await expect(page.getByText("Coming in the next step.")).toHaveCount(0);
  const photo = await page.locator(".rio-plan-hero").evaluate((el) => getComputedStyle(el).backgroundImage);
  expect(photo).toContain("plan-curve");
  expect(photo).not.toContain("home-aerial");
  expect(photo).not.toContain("start-");
  await page.getByRole("link", { name: "Generate season plan" }).click();
  await expect(page).toHaveURL(/\/start$/);
});

test("a bad link is red and a bad length is a dash", async ({ page }) => {
  await installApi(page, { season: false });
  await signIn(page);
  await page.goto("/plan?current_time=nope&start_date=2026-11-10&goal_time=1:58.0&goal_date=2027-04-10");
  const error = page.locator(".rio-plan-hero .rio-error");
  await expect(error).toHaveText("current_time is not an 800 time");
  await expect(error).toHaveCSS("color", "rgb(255, 107, 74)");
  await expect(page.getByRole("link", { name: "Generate season plan" })).toHaveCount(0);
  await expect(page.locator(".rio-cal")).toHaveCount(0);

  await installApi(page, { season: true, bad: "This season has no weeks." });
  await signIn(page);
  await page.goto("/plan");
  await expect(page.getByRole("heading", { name: "Plan" })).toBeVisible();
  await expect(page.getByText("—", { exact: true })).toBeVisible();
  await expect(page.locator(".rio-cal")).toHaveCount(0);
});

test("a season shows the hero, phases, weeks, and all three views", async ({ page }) => {
  await installApi(page, { season: true });
  await signIn(page);
  await page.goto("/plan");
  await expect(page.getByRole("heading", { name: "2 weeks" })).toBeVisible();
  await expect(page.getByText("2026-11-08 — 2026-11-21")).toBeVisible();
  await expect(page.getByText("Pace status No runs yet.")).toBeVisible();
  await expect(page.getByText("Photo by Jan van der Wolf on Pexels")).toBeVisible();
  await expect(page.getByText("This week is phase 4.")).toBeVisible();
  await expect(page.locator(".rio-phase-now")).toContainText("W1");
  await expect(page.locator(".rio-phase")).toHaveCount(2);
  const weeks = page.locator("details.rio-weeks");
  await expect(weeks).not.toHaveAttribute("open", "");
  await weeks.locator("summary").click();
  await expect(page.getByText("No runs logged yet. A week shows distance after a workout is saved.")).toBeVisible();
  await expect(page.getByText("No runs logged").first()).toBeVisible();
  await expect(page.getByText("11 days to goal")).toBeVisible();
  await expect(page.getByText("2,400")).toHaveCount(0);

  await expect(page.getByRole("radio", { name: "Calendar" })).toBeChecked();
  await expect(page.getByRole("heading", { name: "November 2026" })).toBeVisible();
  for (const name of ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]) {
    await expect(page.locator(".rio-cal-dow", { hasText: name })).toBeVisible();
  }
  const todayCell = page.locator(".rio-cal-today");
  await expect(todayCell).toHaveAttribute("data-date", today);
  await expect(todayCell).toHaveAttribute("data-today", "true");
  await expect(page.locator(".rio-cal-out a")).toHaveCount(0);
  await page.getByLabel("Month").selectOption("2026-12");
  await expect(page.getByRole("heading", { name: "December 2026" })).toBeVisible();
  await expect(page.locator(".rio-cal-out a")).toHaveCount(0);
  await page.getByLabel("Month").selectOption("2026-11");
  await page.locator(".rio-cal-session", { hasText: "Speed" }).click();
  await expect(page).toHaveURL(/\/session\?date=2026-11-10$/);
  await page.goto("/plan");

  await page.getByRole("radio", { name: "This week" }).click();
  await expect(page.getByRole("heading", { name: "Week 1" })).toBeVisible();
  await expect(page.getByText("Phase 4 · 2026-11-08 — 2026-11-14")).toBeVisible();
  await expect(page.getByText("6 × 400 m @ 71.2 s, 90 s rest")).toBeVisible();
  await expect(page.getByText("Tolerance 68.0-74.4 s")).toBeVisible();
  await expect(page.getByText("Block 12:06.0")).toBeVisible();
  await expect(page.getByText("Run at 7:45 per mile").first()).toBeVisible();
  await expect(page.getByText("Extra sessions")).toBeVisible();
  await expect(page.getByText("Shakeout")).toBeVisible();
  await expect(page.getByText("Next week is an easy week.")).toBeVisible();
  await page.getByLabel("Week", { exact: true }).selectOption("2");
  await expect(page.getByRole("heading", { name: "Week 2" })).toBeVisible();
  await expect(page.getByText("the week before")).toBeVisible();
  await expect(page.getByText("This is the last week.")).toBeVisible();
  await page.getByRole("link", { name: /Tuesday 2026-11-17/ }).click();
  await expect(page).toHaveURL(/\/session\?date=2026-11-17$/);
  await page.goto("/plan");
  await page.getByRole("radio", { name: "This week" }).click();
  await page.getByRole("button", { name: "On track" }).click();
  await expect(page.getByRole("button", { name: "On track" })).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await page.getByRole("radio", { name: "This week" }).click();
  await expect(page.getByRole("button", { name: "On track" })).toHaveAttribute("aria-pressed", "true");

  await page.getByRole("radio", { name: "Full season" }).click();
  await expect(page.getByRole("heading", { name: "Full season" })).toBeVisible();
  await expect(page.locator(".rio-week")).toHaveCount(2);
  await expect(page.getByText("Week 1 · Phase 4")).toBeVisible();
  await page.locator("details.rio-reasons-box").first().locator("summary").click();
  await expect(page.getByText("Primary work for this phase").first()).toBeVisible();
  await expect(page.getByText("phase_4")).toHaveCount(0);
  await page.getByRole("link", { name: /Tuesday 2026-11-10/ }).click();
  await expect(page).toHaveURL(/\/session\?date=2026-11-10$/);

  await page.goto("/plan");
  await page.getByRole("radio", { name: "Full season" }).click();
  await page.reload();
  await expect(page.getByRole("radio", { name: "Full season" })).toBeChecked();
  const motion = await page.locator(".rio-plan-view").evaluate((el) => getComputedStyle(el).animationName);
  expect(motion === "rio-rise" || motion === "none").toBeTruthy();
});

test("confirm-adapt asks before a week mark is stored", async ({ page }) => {
  await installApi(page, { season: true, confirm: true });
  await signIn(page);
  await page.goto("/plan");
  await page.getByRole("radio", { name: "This week" }).click();
  await page.getByRole("button", { name: "Not hitting" }).click();
  await expect(page.getByText("Confirm Not hitting before the plan changes.")).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByText("Confirm Not hitting before the plan changes.")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Not hitting" })).toHaveAttribute("aria-pressed", "false");
  await page.getByRole("button", { name: "Smashing" }).click();
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect(page.getByRole("button", { name: "Smashing" })).toHaveAttribute("aria-pressed", "true");
});

test("a missing intervals key shows the Strava card, and another pull failure does not", async ({ page }) => {
  await installApi(page, { season: true, notice: "RIO_INTERVALS_API_KEY is not set. Set it in the environment." });
  await signIn(page);
  await page.goto("/plan");
  await page.getByRole("radio", { name: "This week" }).click();
  await expect(page.getByText("Strava isn't connected")).toBeVisible();
  await expect(page.getByText("Connect Strava in Settings to see your runs here.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open Settings" })).toHaveAttribute("href", "/settings");

  await installApi(page, { season: true, notice: "Intervals.icu returned 429" });
  await signIn(page);
  await page.goto("/plan");
  await page.getByRole("radio", { name: "This week" }).click();
  await expect(page.getByText("Runs could not be loaded. Try Refresh in a moment.")).toBeVisible();
  await expect(page.getByText("Strava isn't connected")).toHaveCount(0);
  await expect(page.getByText("Intervals.icu returned 429")).toHaveCount(0);
});

test("short dates follow the saved format", async ({ page }) => {
  await installApi(page, { season: true, dateFormat: "short" });
  await signIn(page);
  await page.goto("/plan");
  await expect(page.getByText("Nov 8, 2026 — Nov 21, 2026")).toBeVisible();
  await page.getByRole("radio", { name: "This week" }).click();
  await expect(page.getByText("Phase 4 · Nov 8, 2026 — Nov 14, 2026")).toBeVisible();
});

function monthsLater(iso: string, months: number): string {
  const [year, month, day] = iso.split("-").map(Number);
  const index = month - 1 + months;
  const nextYear = year + Math.floor(index / 12);
  const nextMonth = (index % 12) + 1;
  const last = new Date(Date.UTC(nextYear, nextMonth, 0)).getUTCDate();
  const kept = Math.min(day, last);
  return `${nextYear}-${String(nextMonth).padStart(2, "0")}-${String(kept).padStart(2, "0")}`;
}

test("a brand-new account reaches Plan from Start and can mark a week", async ({ page }) => {
  test.setTimeout(180_000);
  const email = `plan-${Date.now()}@example.com`;
  await page.goto("/create-account");
  await page.getByLabel("Name").fill("Bea");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();

  const zone = await page.evaluate(async () => {
    const response = await fetch("http://localhost:8000/settings", {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timezone: "America/Los_Angeles" }),
    });
    const me = await fetch("http://localhost:8000/auth/me", { credentials: "include" });
    const body = (await me.json()) as { today: string };
    return { ok: response.ok, today: body.today };
  });
  expect(zone.ok).toBeTruthy();
  const utc = new Date().toISOString().slice(0, 10);
  if (utc !== zone.today) expect(zone.today).not.toBe(utc);

  await page.getByLabel("Easy pace").fill("7:45");
  await page.getByRole("button", { name: "Save easy pace" }).click();
  await expect(page.getByRole("heading", { name: "Start here" })).toBeVisible();
  await page.getByRole("button", { name: "Done" }).click();
  await expect(page).toHaveURL(/\/start$/);

  await page.goto("/plan");
  await expect(page.getByRole("link", { name: "Generate season plan" })).toBeVisible();
  await expect(page.locator(".rio-cal")).toHaveCount(0);
  await page.getByRole("link", { name: "Generate season plan" }).click();
  await expect(page).toHaveURL(/\/start$/);

  const goal = monthsLater(zone.today, 5);
  await page.getByLabel("Your 800 m time today").fill("2:05.0");
  await page.getByLabel("800 m time you're aiming for").fill("1:58.0");
  await expect(page.getByLabel("Goal date")).toHaveValue(goal);
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page).toHaveURL(/\/home\?/);

  await page.goto("/plan");
  await expect(page.getByRole("heading", { name: /\d+ weeks/ })).toBeVisible();
  await expect(page.getByText("Pace status No runs yet.")).toBeVisible();
  await expect(page.getByText(/^This week is phase \d+\.$/)).toBeVisible();
  await expect(page.locator(".rio-phase-now")).toBeVisible();
  const todayCell = page.locator(".rio-cal-today");
  await expect(todayCell).toHaveAttribute("data-date", zone.today);
  await expect(page.locator(".rio-cal-out a")).toHaveCount(0);
  const phases = await page.locator(".rio-phase").count();
  expect(phases).toBeGreaterThan(1);

  await page.getByRole("radio", { name: "This week" }).click();
  await expect(page.getByText(/Run at 7:45 per mile|Set your easy pace before this run\./).first()).toBeVisible();
  const paceLine = page.locator(".rio-pace-line", { hasText: /@/ }).first();
  await expect(paceLine).toBeVisible();
  await expect(paceLine).not.toContainText("1.55");
  await page.getByRole("button", { name: "On track" }).click();
  await expect(page.getByRole("button", { name: "On track" })).toHaveAttribute("aria-pressed", "true");
  await page.getByLabel("Week", { exact: true }).selectOption({ index: 1 });
  await expect(page.getByText("the week before")).toBeVisible();

  await page.getByRole("radio", { name: "Full season" }).click();
  await expect(page.getByRole("heading", { name: "Full season" })).toBeVisible();
  await expect(page.locator(".rio-week")).toHaveCount(phases);
  await page.locator(".rio-cal-session, .rio-week .rio-hit").first().click();
  await expect(page).toHaveURL(/\/session\?date=\d{4}-\d{2}-\d{2}/);

  await page.goto("/plan");
  const formatted = await page.evaluate(async () => {
    const response = await fetch("http://localhost:8000/settings", {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ date_format: "short" }),
    });
    return response.ok;
  });
  expect(formatted).toBeTruthy();
  await page.reload();
  await expect(page.getByText(/[A-Z][a-z]{2} \d{1,2}, \d{4} — [A-Z][a-z]{2} \d{1,2}, \d{4}/)).toBeVisible();
  await page.reload();
  await expect(page.getByRole("button", { name: "On track" }).first()).toHaveAttribute("aria-pressed", "true");
});
