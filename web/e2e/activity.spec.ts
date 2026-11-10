import { expect, test, type Page, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-09",
  next_session: "2026-11-10",
  prefs: {
    easy_pace: "7:45",
    easy_pace_unit: "mi",
    intro_seen: true,
    no_watch: false,
    confirm_adapt: false,
    timezone: "America/Los_Angeles",
    date_format: "iso",
    units: "miles",
    pace_units: "mi",
  },
};

const season = {
  today: "2026-11-09",
  inputs: {
    current_time: "2:02.9",
    start_date: "2026-04-19",
    goal_time: "1:55.0",
    goal_date: "2027-03-19",
  },
  plan: { season_length_weeks: 12, start_date: "2026-04-19" },
  digest: "digest-1",
};

function activities(options: { connected?: boolean; notice?: string | null; cards?: boolean; last?: number | null }) {
  const card = {
    id: "run-1",
    date: "2026-11-09",
    shown_date: "2026-11-09",
    name: "6 × 400 m",
    template_id: "se_400_r90_x6",
    status: "On track",
    detail: "Actual 71 s",
    laps: [{ rep: "1", target: "71 s", actual: "70 s", rest: "90 s" }],
    meters: 2400,
    heart_rate: 160,
  };
  return {
    rows: options.cards ? [{ date: "2026-11-09", shown_date: "2026-11-09", label: "6 × 400 m", work: "2,400 m", hr: "160 bpm", meters: 2400 }] : [],
    all: options.cards ? [{ date: "2026-11-09", shown_date: "2026-11-09", name: "Morning", distance: "5,000 m", hr: "148 bpm", extra: true, meters: 5000 }] : [],
    cards: options.cards ? [card] : [],
    groups: [{ title: "Nov 8 – Nov 14", open: true, cards: options.cards ? [card] : [] }],
    summary: { title: "Nov 8 – Nov 14", distance: options.cards ? "1.5 mi" : "0.0 mi", runs: options.cards ? 1 : 0, counts: { "On track": options.cards ? 1 : 0, Ahead: 0, Behind: 0, Extra: 0 } },
    weekly_meters: options.cards ? [2400] : [],
    heart: options.cards ? [{ date: "2026-11-09", bpm: 160 }] : [],
    figures: { distance: options.cards ? "1.5 mi" : "0.0 mi", heart: options.cards ? "160 bpm" : "—" },
    length: 12,
    start_date: "2026-04-19",
    goal_date: "2027-03-19",
    notice: options.notice ?? (options.connected ? null : "RIO_INTERVALS_API_KEY is not set."),
    strava: {
      configured: true,
      connected: options.connected === true,
      athlete_name: options.connected ? "Ada Lovelace" : "",
      last_sync_at: options.last === undefined ? null : options.last,
      count: options.connected ? 1 : undefined,
      redirect_uri: "http://localhost:3000/strava/callback",
    },
    logged: [],
  };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(
  page: Page,
  options: {
    season?: "open" | "none" | "bad";
    connected?: boolean;
    notice?: string | null;
    cards?: boolean;
    role?: string;
    configured?: boolean;
    sync?: { status: number; body: unknown };
  },
) {
  let signed = false;
  const calls: string[] = [];
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    calls.push(`${route.request().method()} ${path}`);
    if (path === "/auth/me") {
      if (!signed) return json(route, { detail: "Sign in again." }, 401);
      return json(route, { ...athlete, role: options.role || "athlete" });
    }
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/auth/sign-in") {
      signed = true;
      return json(route, { email: athlete.email, display_name: athlete.display_name, kind: "local" });
    }
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/home") return json(route, { today: athlete.today, athlete, hello: "Hey Ada", strava_offer: false, copy: "", season: null });
    if (path === "/seasons/current") {
      if (options.season === "none") return json(route, { detail: "No current season." }, 404);
      if (options.season === "bad") return json(route, { ...season, plan: { season_length_weeks: 0 } });
      return json(route, season);
    }
    if (path === "/strava/status") {
      return json(route, {
        configured: options.configured !== false,
        connected: options.connected === true,
        athlete_name: options.connected ? "Ada Lovelace" : "",
        last_sync_at: options.connected ? 1794295800 : null,
        count: options.connected ? 1 : undefined,
        redirect_uri: "http://localhost:3000/strava/callback",
      });
    }
    if (path === "/strava/sync") {
      if (options.sync) return json(route, options.sync.body, options.sync.status);
      return json(route, { synced: true, notice: null, count: 1 });
    }
    if (path === "/strava/connect") {
      return json(route, { url: "https://www.strava.com/oauth/authorize?client_id=test&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fstrava%2Fcallback&response_type=code&scope=read%2Cactivity%3Aread_all&state=strava%3Aada", redirect_uri: "http://localhost:3000/strava/callback" });
    }
    if (path === "/strava/disconnect") return json(route, { connected: false });
    if (path === "/strava/callback") return json(route, { connected: true, athlete_name: "Ada Lovelace" });
    if (path === "/activities") {
      if (options.season === "none") return json(route, { detail: "No current season." }, 404);
      return json(route, activities({ connected: options.connected, notice: options.notice, cards: options.cards, last: options.connected ? 1794295800 : null }));
    }
    if (path === "/fixtures") return json(route, { fixtures: ["race_800"] });
    if (path === "/fixtures/intervals") return json(route, { files: ["synthetic_se_400_with_recovery.json"] });
    if (path.startsWith("/fixtures/intervals/")) {
      return json(route, {
        name: "synthetic_se_400_with_recovery.json",
        times: [57.5],
        source: "synthetic-se-400-with-recovery",
        date: "2026-10-25",
        banner: "SYNTHETIC / FIXTURE",
        distance_heading: "Distance (m)",
        rows: [{ Lap: 1, "Distance (m)": "400", Seconds: 57.5, "Rest (s)": 90 }],
        family: "speed_endurance",
        confidence: "high",
        reason_codes: ["six_by_400"],
        prose: "Speed endurance, from the lap times.",
      });
    }
    if (path === "/fixtures/session") {
      return json(route, {
        name: "race_800",
        date: "2026-10-17",
        banner: "FIXTURE",
        distance_heading: "Distance (m)",
        rows: [],
        family: "race",
        confidence: "high",
        reason_codes: [],
        prose: "A race.",
      });
    }
    return json(route, { detail: "missing" }, 404);
  });
  return calls;
}

async function sign(page: Page) {
  await page.goto("/sign-in?skip=1");
  await page.getByLabel("Email").fill(athlete.email);
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL(/\/(home|start|easy-pace|intro)/);
}

test("no season does not call Strava and offers Start", async ({ page }) => {
  const calls = await install(page, { season: "none" });
  await sign(page);
  await page.goto("/activity");
  await expect(page.getByRole("heading", { name: "Activity" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Generate season plan" })).toHaveAttribute("href", "/start");
  await expect(page.getByText("SYNTHETIC")).toHaveCount(0);
  expect(calls.some((call) => call.includes("/strava"))).toBe(false);
});

test("a bad plan is an em dash", async ({ page }) => {
  await install(page, { season: "bad" });
  await sign(page);
  await page.goto("/activity");
  await expect(page.getByText("—", { exact: true })).toBeVisible();
});

test("a disconnected account shows the empty line and the Strava card", async ({ page }) => {
  await install(page, { notice: "RIO_INTERVALS_API_KEY is not set." });
  await sign(page);
  await page.goto("/activity");
  await expect(page.getByText("2026-04-19 — 2027-03-19")).toBeVisible();
  await expect(page.getByText("No runs yet.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Connect Strava in Settings" })).toHaveAttribute("href", "/settings");
  await expect(page.getByText("Strava isn't connected")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open Settings" })).toBeVisible();
  await expect(page.getByText("Intervals.icu")).toHaveCount(0);
  await expect(page.getByText("Refresh from Strava")).toHaveCount(0);
  await expect(page.locator(".rio-mark-label").first()).toHaveCSS("color", "rgb(60, 58, 54)");
});

test("an intervals failure stays off the raw adapter sentence and keeps the stored runs", async ({ page }) => {
  await install(page, { notice: "Intervals.icu returned 429", cards: true });
  await sign(page);
  await page.goto("/activity");
  await expect(page.getByText("Runs could not be loaded. Try Refresh in a moment.")).toBeVisible();
  await expect(page.getByText("Intervals.icu")).toHaveCount(0);
  await expect(page.getByText("Completed work")).toBeVisible();
  await expect(page.locator(".rio-stat-value", { hasText: "1.5 mi" })).toBeVisible();
  await expect(page.locator(".rio-stat-value", { hasText: "160 bpm" })).toBeVisible();
  await expect(page.getByText("This week")).toBeVisible();
  await expect(page.getByText("Heart rate · bpm")).toBeVisible();
});

test("a connected empty week names the sync in the saved zone", async ({ page }) => {
  await install(page, { connected: true, notice: null, cards: false });
  await sign(page);
  await page.goto("/activity");
  await expect(page.getByRole("button", { name: "Refresh" })).toBeVisible();
  await expect(page.getByText("Pulls the latest runs.")).toBeVisible();
  await expect(page.getByText(/Last synced Nov 9,/)).toBeVisible();
  await expect(page.getByText("No runs yet", { exact: true })).toBeVisible();
  await expect(page.getByText("TEST season")).toHaveCount(0);
});

test("runs, the heart chart, and the hidden tables", async ({ page }) => {
  await install(page, { connected: true, notice: null, cards: true });
  await sign(page);
  await page.goto("/activity");
  await expect(page.getByRole("heading", { name: "6 × 400 m" })).toBeVisible();
  await expect(page.getByRole("article").getByText("On track")).toBeVisible();
  await expect(page.getByText("This week")).toBeVisible();
  await expect(page.getByText("Heart rate · bpm")).toBeVisible();
  await expect(page.getByRole("img", { name: "Average heart rate" })).toBeVisible();
  await expect(page.getByText("Completed work")).toBeVisible();
  const legacy = page.locator(".rio-legacy-activity");
  await expect(legacy).toBeHidden();
  await expect(legacy.getByText("No matched activities.")).toHaveCount(0);
  await expect(legacy.getByText("Sessions")).toBeHidden();
});

test("Strava busy stays the busy sentence", async ({ page }) => {
  await install(page, { connected: true, notice: null, cards: false, sync: { status: 429, body: { detail: "Strava is busy. Try again in a few minutes." } } });
  await sign(page);
  await page.goto("/activity");
  await expect(page.getByText("Strava is busy. Try again in a few minutes.")).toBeVisible();
});

test("connect opens Strava and disconnect clears the name", async ({ page }) => {
  await install(page, { configured: true, connected: false });
  await page.route("https://www.strava.com/**", async (route) => {
    await route.fulfill({ status: 200, contentType: "text/html", body: "<title>Strava</title><p>Authorize</p>" });
  });
  await sign(page);
  await page.goto("/settings");
  await page.locator("summary", { hasText: "Strava" }).click();
  await expect(page.getByText("Strava data is only visible to you.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Connect with Strava" })).toBeVisible();
  await expect(page.locator(".rio-mark-label", { hasText: "Strava" })).toHaveCSS("color", "rgb(60, 58, 54)");
  await page.getByRole("button", { name: "Connect with Strava" }).click();
  await page.waitForURL(/strava\.com\/oauth\/authorize/);
  expect(page.url()).toContain("redirect_uri=");
  expect(page.url()).not.toContain("access_token");
});

test("the callback exchanges the code and lands on settings", async ({ page }) => {
  await install(page, { connected: true });
  await sign(page);
  await page.goto("/strava/callback?code=test-code&state=strava:ada");
  await page.waitForURL(/\/settings\?strava=connected/);
  await expect(page.getByText("Connected as Ada Lovelace.")).toBeVisible();
});

test("a non-admin is sent home from Last Session", async ({ page }) => {
  await install(page, { role: "athlete" });
  await sign(page);
  await page.goto("/last-session");
  await page.waitForURL(/\/home/);
});

test("an admin sees the lap table and not the synthetic banner", async ({ page }) => {
  await install(page, { role: "admin" });
  await sign(page);
  await page.goto("/last-session");
  await expect(page.getByRole("heading", { name: "Last Session" })).toBeVisible();
  await expect(page.getByLabel("Intervals file")).toBeVisible();
  await page.getByLabel("Intervals file").selectOption("synthetic_se_400_with_recovery.json");
  await expect(page.getByRole("columnheader", { name: "Seconds" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "57.5" })).toBeVisible();
  await expect(page.getByRole("cell", { name: "90" })).toBeVisible();
  await expect(page.locator(".rio-synthetic")).toHaveCount(0);
  await expect(page.getByText("Speed endurance, from the lap times.")).toBeVisible();
  await expect(page.locator(".rio-mark-label", { hasText: "Laps" })).toHaveCSS("color", "rgb(60, 58, 54)");
});
