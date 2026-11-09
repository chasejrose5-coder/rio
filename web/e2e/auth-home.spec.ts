import { expect, test, type Page, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-09",
  prefs: {},
};

const season = {
  today: "2026-11-09",
  inputs: {
    current_time: "2:02.9",
    start_date: "2026-04-19",
    goal_time: "1:55.0",
    goal_date: "2027-03-19",
  },
};

const home = {
  today: "2026-11-09",
  athlete,
  hello: "Hey, Ada",
  strava_offer: false,
  copy: "",
  season: {
    inputs: season.inputs,
    digest: "abc",
    view: { days_remaining: 130, phase: "4", mark: null, focus: "Speed endurance" },
    phase: {
      collapsed: "This week sits in phase 4, week 1 of 2, because the season still needs speed endurance.",
      panel: {
        headline: "Phase 4 — Speed endurance",
        focus: "Speed endurance takes the lead.",
        days: [{ short: "Tue", role: "hard" }],
        steps: [{ label: "This", text: "Phase 4, Speed endurance" }],
        marks: "Hard-day marks can ease or advance later weeks.",
        note: "",
      },
    },
    pace_status: "No runs yet",
    next: {
      date: "2026-11-10",
      shown_date: "2026-11-10",
      day_of_week: "Tuesday",
      template_id: "se_400_r90_x6",
      label: "6 × 400 m near goal 800 pace, 90 s rest",
      facts: { distance: "400 m", pace: "Near goal 800", rest: "90 s", reps: "6" },
      prescription: { line: "6 × 400 m @ 57.5 s, 90 s rest", tolerance: "55.0-60.0 s", block: "9:15.0" },
    },
    upcoming: [],
    next_days: [
      {
        date: "2026-11-10",
        shown_date: "2026-11-10",
        day_of_week: "Tuesday",
        template_id: "se_400_r90_x6",
        label: "6 × 400 m near goal 800 pace, 90 s rest",
        prescription: { line: "6 × 400 m @ 57.5 s, 90 s rest", tolerance: "", block: "9:15.0" },
      },
      { date: "2026-11-11", shown_date: "2026-11-11", day_of_week: "Wednesday", template_id: "", label: "—" },
      { date: "2026-11-12", shown_date: "2026-11-12", day_of_week: "Thursday", template_id: "", label: "—" },
    ],
    notes: [],
  },
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function installApi(page: Page, options: { hosted?: boolean; season?: boolean }) {
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
      return json(route, athlete);
    }
    if (path === "/auth/google") {
      if (options.hosted) return json(route, { url: "https://example.test/google", redirect_uri: "http://localhost:3000/" });
      return json(route, { detail: "Accounts are not available." }, 503);
    }
    if (path === "/auth/sign-in") {
      signed = true;
      return json(route, { email: athlete.email, display_name: athlete.display_name, kind: "local" });
    }
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/seasons/current") {
      if (!options.season) return json(route, { detail: "No current season." }, 404);
      return json(route, season);
    }
    if (path === "/home") return json(route, home);
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("local sign-in hides forgot password and Google", async ({ page }) => {
  await installApi(page, { hosted: false, season: false });
  await page.goto("/sign-in");
  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password")).toBeVisible();
  await expect(page.getByRole("button", { name: "Log in" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Create account" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Forgot password?" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Google/i })).toHaveCount(0);
  await expect(page.getByText("Photo by Steve Pancrate on Pexels")).toBeVisible();
});

test("hosted sign-in shows forgot password and still hides Google", async ({ page }) => {
  await installApi(page, { hosted: true, season: true });
  await page.goto("/sign-in");
  await expect(page.getByRole("link", { name: "Forgot password?" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Google/i })).toHaveCount(0);
});

test("create account asks for a name", async ({ page }) => {
  await installApi(page, { hosted: false, season: false });
  await page.goto("/create-account");
  await expect(page.getByRole("heading", { name: "Create account" })).toBeVisible();
  await expect(page.getByLabel("Name")).toBeVisible();
  await expect(page.getByRole("button", { name: "Create account" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to log in" })).toBeVisible();
  await expect(page.getByText("Photo by Steve Pancrate on Pexels")).toBeVisible();
});

test("sign-in with a current season opens Home", async ({ page }) => {
  await installApi(page, { hosted: false, season: true });
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password").fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByText("130")).toBeVisible();
  await expect(page.getByText("6 × 400 m @ 57.5 s, 90 s rest").first()).toBeVisible();
  await expect(page.getByText("Block 9:15.0").first()).toBeVisible();
  await expect(page.getByText("Photo by Gaby Lopez on Pexels")).toBeVisible();
  await expect(page.getByText("03  /  Next 3 days")).toBeVisible();
  await expect(page.getByText("Coming in the next step.")).toHaveCount(0);
});

test("sign-in without a current season opens Start", async ({ page }) => {
  await installApi(page, { hosted: false, season: false });
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password").fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/start$/);
  await expect(page.getByText("Coming in the next step.")).toBeVisible();
});
