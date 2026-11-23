import { mkdirSync } from "node:fs";
import { expect, test, type Page, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-21",
  prefs: { easy_pace: "7:25", easy_pace_unit: "mi", intro_seen: true, no_watch: false },
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
      pace_low: "7:10",
      pace_high: "7:50",
      pace_line: "7:10–7:50 per mile",
      pace_note: "Learned from 6 Zone 2 runs.",
      estimate: "ready",
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
  match: null,
  heart_rate: "",
  zones: null,
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

test("a learned easy pace range is shown on the workout", async ({ page }) => {
  const shots = process.env.RIO_ARTIFACTS || "test-results";
  mkdirSync(shots, { recursive: true });
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
    if (path === "/heart-rate") return json(route, { no_monitor: false, resting_hr: 60, max_hr: 180, zones: [] });
    if (path === "/seasons/current") return json(route, { today: athlete.today, inputs: {}, digest: "digest-1" });
    if (path.startsWith("/sessions/")) return json(route, session);
    if (path === "/home") return json(route, { today: athlete.today, athlete, hello: "Hey Ada", season: null, copy: "" });
    return json(route, {});
  });
  await page.goto("/sign-in?skip=1");
  await page.getByLabel("Email").fill(athlete.email);
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await page.goto("/session?date=2026-11-21");
  await expect(page.getByText("Learned from 6 Zone 2 runs.")).toBeVisible();
  await expect(page.getByText("7:10–7:50 per mile")).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.screenshot({ path: `${shots}/pace-learn-desktop.png`, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: `${shots}/pace-learn-phone.png`, fullPage: true });
});
