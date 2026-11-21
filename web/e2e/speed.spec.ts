import { expect, test, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-11",
  next_session: "2026-11-12",
  prefs: { easy_pace: "7:45", easy_pace_unit: "mi", intro_seen: true, no_watch: false },
};

const season = {
  today: "2026-11-11",
  inputs: {
    current_time: "2:02.0",
    start_date: "2026-11-05",
    goal_time: "1:55.0",
    goal_date: "2027-07-08",
  },
  plan: { sessions: [{ date: "2026-11-12" }] },
};

const home = {
  today: "2026-11-11",
  athlete,
  hello: "Hey, Ada",
  strava_offer: false,
  copy: "",
  season: {
    inputs: season.inputs,
    view: { days_remaining: 239, phase: "1", mark: null, focus: "Aerobic" },
    phase: null,
    pace_status: "No runs yet",
    next: null,
    next_days: [],
    notes: [],
  },
};

const DELAY = 400;

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

test("log in overlaps the session, heart rate, and the season", async ({ page }) => {
  const started = new Map<string, number>();
  let signed = false;
  let arm = false;
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    const tracked = path === "/auth/session" || path === "/auth/me" || path === "/heart-rate" || path === "/seasons/current";
    if (arm && tracked && !started.has(path)) started.set(path, Date.now());
    if (tracked) await new Promise((resolve) => setTimeout(resolve, DELAY));
    if (path === "/auth/sign-in") {
      signed = true;
      return json(route, { email: athlete.email, display_name: athlete.display_name, kind: "local" });
    }
    if (path === "/auth/availability") return json(route, { mode: "local" });
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/auth/session" || path === "/auth/me") {
      if (!signed) return json(route, { signed_in: false });
      return json(route, athlete);
    }
    if (path === "/heart-rate") {
      return json(route, { no_monitor: false, resting_hr: 60, max_hr: 180, zones: [] });
    }
    if (path === "/seasons/current") return json(route, season);
    if (path.startsWith("/home")) return json(route, home);
    return json(route, { detail: "Not mocked." }, 404);
  });

  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  arm = true;
  const began = Date.now();
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/home$/, { timeout: 15_000 });
  const elapsed = Date.now() - began;
  const sessionAt = started.get("/auth/session") ?? started.get("/auth/me") ?? 0;
  const heartAt = started.get("/heart-rate") ?? 0;
  const seasonAt = started.get("/seasons/current") ?? 0;
  expect(heartAt).toBeGreaterThan(0);
  expect(seasonAt).toBeGreaterThan(0);
  expect(Math.abs(heartAt - sessionAt)).toBeLessThan(200);
  expect(Math.abs(seasonAt - heartAt)).toBeLessThan(200);
  // Three serial 400 ms reads would pass 1.2 s before navigation. Overlap stays under two reads.
  expect(elapsed).toBeLessThan(DELAY * 2 + 500);
  console.log(`sign-in to /home ${elapsed}ms`);
});
