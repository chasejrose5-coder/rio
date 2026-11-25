import { mkdirSync } from "node:fs";
import { expect, test, type Page, type Route } from "@playwright/test";

const WIDTHS = [320, 375, 768, 1024, 1280, 1440];
const THEMES = ["light", "dark"] as const;
const today = "2026-11-10";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today,
  next_session: today,
  prefs: {
    timezone: "America/Los_Angeles",
    pace_units: "mi",
    units: "miles",
    no_watch: false,
    easy_pace: "7:25",
    easy_pace_unit: "mi",
    intro_seen: true,
    date_format: "short",
    start_date: "today",
    confirm_adapt: false,
    show_ids: false,
    compact: false,
    preferred: "Ada",
    theme: "dark",
  },
};

const home = {
  today,
  athlete,
  hello: "Hey, Ada",
  strava_offer: false,
  copy: "",
  season: {
    inputs: { current_time: "2:02.9", start_date: "2026-04-19", goal_time: "1:55.0", goal_date: "2027-03-19" },
    digest: "abc",
    view: { days_remaining: 130, phase: "4", mark: null, focus: "Speed endurance" },
    phase: {
      collapsed: "This week sits in phase 4, week 1 of 2.",
      panel: {
        headline: "Phase 4 — Speed endurance",
        focus: "Speed endurance takes the lead.",
        days: [
          { short: "Mon", role: "easy" },
          { short: "Tue", role: "hard" },
          { short: "Wed", role: "easy" },
          { short: "Thu", role: "hard" },
          { short: "Fri", role: "off" },
          { short: "Sat", role: "long" },
          { short: "Sun", role: "easy" },
        ],
        steps: [
          { label: "Base", text: "Phase 1" },
          { label: "This", text: "Phase 4" },
        ],
        marks: "Hard-day marks can ease or advance later weeks.",
        note: "Keep the long run easy.",
      },
    },
    pace_status: "Behind",
    logging: "times",
    next: {
      date: today,
      shown_date: today,
      day_of_week: "Tuesday",
      template_id: "se_400_r90_x6",
      label: "6 × 400 m near goal 800 pace, 90 s rest",
      facts: { distance: "400 m", pace: "Near goal 800", rest: "90 s", reps: "6" },
      prescription: { line: "6 × 400 m @ 57.5 s, 90 s rest", tolerance: "55.0-60.0 s", block: "9:15.0" },
    },
    upcoming: [],
    next_days: [
      { date: today, shown_date: today, day_of_week: "Tuesday", template_id: "se_400_r90_x6", label: "6 × 400 m" },
      { date: "2026-11-11", shown_date: "2026-11-11", day_of_week: "Wednesday", template_id: "", label: "Rest" },
      { date: "2026-11-12", shown_date: "2026-11-12", day_of_week: "Thursday", template_id: "se_300_r60_x8", label: "8 × 300 m" },
    ],
    notes: [],
  },
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(page: Page) {
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/session" || path === "/auth/me") return json(route, { ...athlete, signed_in: true });
    if (path === "/auth/availability") return json(route, { mode: "local" });
    if (path === "/home") return json(route, home);
    if (path === "/heart-rate") {
      return json(route, { no_monitor: true, resting_hr: null, max_hr: null, zones: [] });
    }
    if (path === "/activities") return json(route, { connected: false, rows: [], all: [], weeks: [] });
    if (path === "/strava/status") return json(route, { connected: false });
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("the home photo credit stays clear of the cards", async ({ page }) => {
  test.setTimeout(180_000);
  await install(page);
  const shots = process.env.RIO_ARTIFACTS;
  const label = process.env.RIO_SHOT || "home-credit";
  const misses: string[] = [];

  for (const theme of THEMES) {
    athlete.prefs.theme = theme;
    await page.context().addCookies([{ name: "rio_theme", value: theme, url: "http://localhost:3000/" }]);
    await page.emulateMedia({ colorScheme: theme });
    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: width <= 375 ? 812 : 900 });
      await page.goto("/home");
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
      const credit = page.locator(".page-home .rio-photo-credit");
      await expect(credit).toHaveCount(1);
      await expect(credit).toHaveText("Photo by Gaby Lopez on Pexels");
      await expect(credit.getByRole("link", { name: "Gaby Lopez" })).toHaveAttribute(
        "href",
        "https://www.pexels.com/photo/birds-eye-view-of-athletics-stadium-18588227/",
      );
      await expect(credit.getByRole("link", { name: "Pexels" })).toHaveAttribute("href", "https://www.pexels.com");
      await page.evaluate(() => document.fonts.ready);
      await expect(page.locator(".rio-stat-tile", { hasText: "Progress" })).toBeVisible();
      await expect(page.locator(".rio-stat-tile", { hasText: "Behind" })).toBeVisible();

      if (width >= 1024) {
        const pair = await page.evaluate(() => {
          const root = document.querySelector(".rio-home-pair");
          const phase = root?.querySelector(":scope > .rio-home-phase")?.getBoundingClientRect();
          const todayCard = root?.querySelector(":scope > .rio-home-today")?.getBoundingClientRect();
          const phaseLabel = root?.querySelector(":scope > .rio-home-phase > .rio-index")?.getBoundingClientRect();
          const todayLabel = root?.querySelector(":scope > .rio-home-today > .rio-index")?.getBoundingClientRect();
          if (!phase || !todayCard || !phaseLabel || !todayLabel) return null;
          return {
            top: Math.abs(phase.top - todayCard.top),
            height: Math.abs(phase.height - todayCard.height),
            label: Math.abs(phaseLabel.top - todayLabel.top),
          };
        });
        expect(pair, `${theme} ${width} home pair`).not.toBeNull();
        expect(pair!.top, `${theme} ${width} phase top`).toBeLessThanOrEqual(1);
        expect(pair!.height, `${theme} ${width} phase height`).toBeLessThanOrEqual(1);
        expect(pair!.label, `${theme} ${width} label row`).toBeLessThanOrEqual(1);
      }

      const hits = await page.evaluate(() => {
        const creditBox = document.querySelector(".page-home .rio-photo-credit")?.getBoundingClientRect();
        if (!creditBox) return [{ name: "credit missing", gap: -1 }];
        const creditRect = {
          left: creditBox.left,
          right: creditBox.right,
          top: creditBox.top,
          bottom: creditBox.bottom,
        };
        const nodes = document.querySelectorAll(
          ".page-home .rio-stat-tile, .page-home .rio-home-phase, .page-home .rio-home-today, .page-home .rio-mini, .page-home .rio-hr-prompt, .page-home .rio-insight",
        );
        const overlap = (a: typeof creditRect, b: DOMRect) => {
          const overlapX = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const overlapY = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (overlapX > 0 && overlapY > 0) return -Math.min(overlapX, overlapY);
          const dx = Math.max(a.left - b.right, b.left - a.right, 0);
          const dy = Math.max(a.top - b.bottom, b.top - a.bottom, 0);
          return Math.hypot(dx, dy);
        };
        return [...nodes].map((node) => {
          const label = node.querySelector(".rio-mark-label, .rio-index, .rio-mini-dow")?.textContent?.trim() || node.className;
          return { name: label, gap: Math.round(overlap(creditRect, node.getBoundingClientRect()) * 10) / 10 };
        });
      });
      const covered = hits.filter((hit) => hit.gap < 8);
      if (covered.length) misses.push(`${theme} ${width}: ${covered.map((hit) => `${hit.name} ${hit.gap}`).join(", ")}`);
      if (shots && (width === 768 || width === 375 || width === 1280) && (theme === "dark" || (theme === "light" && width === 768))) {
        mkdirSync(shots, { recursive: true });
        await page.locator(".rio-home-hero").screenshot({ path: `${shots}/${label}-home-hero-${width}-${theme}.png` });
      }
    }
  }
  expect(misses).toEqual([]);
});
