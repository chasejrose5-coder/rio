import { mkdirSync } from "node:fs";
import { expect, test, type Page, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-21",
  prefs: { easy_pace: "7:45", easy_pace_unit: "mi", intro_seen: true, no_watch: false },
};

const session = {
  date: "2026-11-21",
  session: { date: "2026-11-21", template_id: "aer_8000_r0_x1", week_number: 1 },
  actual: null,
  quality: false,
  note: null,
  viewed: true,
  digest: "digest-1",
  label: "5.9 mi easy, Zone 2, talkable",
  structure: "One continuous easy run.",
  target: "Hit: one continuous easy run, talkable.",
  reasons: ["Easy running"],
  shown_date: "Nov 21, 2026",
  prescription: {
    line: "Zone 2 · Easy / long · 132–144 bpm",
    tolerance: "",
    block: "",
    heart: {
      zone: 2,
      zone_name: "Easy / long",
      low_bpm: 132,
      high_bpm: 144,
      pace_low: "7:25",
      pace_high: "8:05",
      pace_line: "7:25–8:05 per mile",
      pace_note: "still creating your estimate",
      estimate: "creating",
      effort: "Stay in the zone. Pace can move with heat and hills.",
      safety: "This is not medical advice. Stop and seek help if your heart rate stays unusually high or you feel unwell.",
    },
  },
  logging: "done",
  confirm_adapt: false,
  show_id: false,
  boxes: 0,
  seed: [],
  summary: "",
  match: { reps: "", work: "5.9 mi", heart_rate: "158 bpm" },
  heart_rate: "",
  activity_id: "strava-42",
  zones: {
    zones: [
      { zone: 1, name: "Recovery", seconds: 120 },
      { zone: 2, name: "Easy / long", seconds: 300 },
      { zone: 3, name: "Tempo", seconds: 240 },
      { zone: 4, name: "Threshold", seconds: 900 },
      { zone: 5, name: "VO2max / race", seconds: 0 },
    ],
    above_seconds: 1140,
    target_zone: 2,
    warning:
      "You were above Zone 2 for much of this run. Next time, slow down or stop until your heart rate is back in the zone.",
  },
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(page: Page) {
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
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/auth/sign-in") {
      signed = true;
      return json(route, { email: athlete.email, display_name: athlete.display_name, kind: "local" });
    }
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/heart-rate") return json(route, { no_monitor: false, resting_hr: 60, max_hr: 180, zones: [] });
    if (path === "/seasons/current") return json(route, { today: athlete.today, inputs: {}, digest: "digest-1" });
    if (path.startsWith("/sessions/")) return json(route, session);
    if (path === "/activities") return json(route, { rows: [], logged: [], figures: {} });
    if (path === "/home") return json(route, { today: athlete.today, athlete, hello: "Hey Ada", season: null, copy: "" });
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("a run shows time in zone and tells the runner to slow down", async ({ page }) => {
  mkdirSync("/opt/cursor/artifacts", { recursive: true });
  await install(page);
  await page.goto("/sign-in?skip=1");
  await page.getByLabel("Email").fill(athlete.email);
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await page.goto("/session?date=2026-11-21");
  await expect(page.getByRole("heading", { name: "5.9 mi easy, Zone 2, talkable" })).toBeVisible();
  await expect(page.getByText("Time in zone")).toBeVisible();
  await expect(page.getByText("Zone 4 · Threshold")).toBeVisible();
  await expect(page.getByText("15:00")).toBeVisible();
  await expect(page.getByText(/slow down or stop/)).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.screenshot({ path: "/opt/cursor/artifacts/zone-time-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "/opt/cursor/artifacts/zone-time-phone.png", fullPage: true });
});
