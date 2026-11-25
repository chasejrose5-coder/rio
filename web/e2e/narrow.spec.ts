import { expect, test, type Page, type Route } from "@playwright/test";

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
  },
};

const inputs = {
  current_time: "2:02.9",
  start_date: "2026-04-19",
  goal_time: "1:55.0",
  goal_date: "2027-03-19",
};

const home = {
  today,
  athlete,
  hello: "Hey, Ada",
  strava_offer: false,
  copy: "",
  season: {
    inputs,
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
    pace_status: "No runs yet",
    logging: "times",
    next: {
      date: today,
      shown_date: today,
      day_of_week: "Tuesday",
      template_id: "se_400_r90_x6",
      label: "6 × 400 m near goal 800 pace, 90 s rest",
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

const weeks = ["1", "2", "3", "4", "5", "6", "7", "8"].map((phase, index) => ({
  week: index + 1,
  phase,
  status: phase === "4" ? "current" : Number(phase) < 4 ? "past" : "upcoming",
  days_remaining: 11,
  meters: 0,
  volume: "0 m",
}));

const plan = {
  inputs,
  digest: "digest-1",
  marks: {},
  actuals: {},
  prefs: { ...athlete.prefs, today },
  months: ["2026-11-01"],
  month: "2026-11",
  month_title: "November 2026",
  pace_status: "No runs yet",
  calendar: [[
    { date: "2026-11-08", in_month: true, day: 8, label: "", template_id: "", today: false },
    { date: "2026-11-09", in_month: true, day: 9, label: "", template_id: "", today: false },
    { date: today, in_month: true, day: 10, label: "Speed", template_id: "se_400_r90_x6", today: true },
    { date: "2026-11-11", in_month: true, day: 11, label: "Rest", template_id: "", today: false },
    { date: "2026-11-12", in_month: true, day: 12, label: "", template_id: "", today: false },
    { date: "2026-11-13", in_month: true, day: 13, label: "", template_id: "", today: false },
    { date: "2026-11-14", in_month: true, day: 14, label: "Easy", template_id: "aer_8000_r0_x1", today: false },
  ]],
  weeks,
  sessions: home.season.next_days,
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
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/home") return json(route, home);
    if (path === "/plan") return json(route, plan);
    if (path === "/seasons/current") return json(route, { today, inputs, digest: "digest-1", plan: { sessions: plan.sessions } });
    if (path === "/activities") return json(route, { connected: false, rows: [], all: [], weeks: [] });
    if (path === "/heart-rate") return json(route, { no_monitor: true, resting_hr: null, max_hr: null, zones: [], custom: false, method: "karvonen", method_label: "Karvonen", method_sentence: "Zones use Karvonen.", safety: "Not medical advice.", strava_prefill: { available: false } });
    if (path === "/strava/status") return json(route, { connected: false });
    if (path.startsWith("/bike")) return json(route, { tracked: false, dates: [], minutes: 0, distance_m: 0, zone2_seconds: 0, zone_seconds: 0 });
    return json(route, { detail: "Not mocked." }, 404);
  });
}

async function overflow(page: Page) {
  return page.evaluate(() => {
    const client = document.documentElement.clientWidth;
    const scroll = document.documentElement.scrollWidth;
    const rows: { over: number; tag: string }[] = [];
    const contained = (el: Element) => {
      let node = el.parentElement;
      while (node) {
        const overflowX = getComputedStyle(node).overflowX;
        if (overflowX === "auto" || overflowX === "scroll" || overflowX === "hidden" || overflowX === "clip") return true;
        node = node.parentElement;
      }
      return false;
    };
    document.querySelectorAll<HTMLElement>("body *").forEach((el) => {
      if (contained(el)) return;
      const box = el.getBoundingClientRect();
      if (box.width < 1 || box.height < 1) return;
      const over = Math.max(box.right - client, -box.left);
      if (over <= 0.5) return;
      const cls = [...el.classList].slice(0, 3).join(".");
      rows.push({ over: Math.round(over * 10) / 10, tag: `${el.tagName.toLowerCase()}${cls ? `.${cls}` : ""}` });
    });
    rows.sort((a, b) => b.over - a.over);
    return { scroll, client, rows: rows.slice(0, 6) };
  });
}

test("home and plan stay inside a 320px viewport", async ({ page }) => {
  await install(page);
  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/home");
  await expect(page.locator(".rio-home-pair")).toBeVisible();
  await expect(page.locator(".rio-week-chip")).toHaveCount(7);
  const homeBox = await overflow(page);
  expect(homeBox.scroll, JSON.stringify(homeBox)).toBeLessThanOrEqual(homeBox.client);
  const narrowColumns = await page.locator(".rio-home-pair").evaluate((el) => getComputedStyle(el).gridTemplateColumns);
  expect(narrowColumns.trim().split(/\s+/)).toHaveLength(1);

  await page.goto("/plan");
  await expect(page.getByRole("group", { name: "Season phases" }).locator(".rio-phase")).toHaveCount(8);
  const planBox = await overflow(page);
  expect(planBox.scroll, JSON.stringify(planBox)).toBeLessThanOrEqual(planBox.client);

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/home");
  await expect(page.locator(".rio-home-pair")).toBeVisible();
  const wideColumns = await page.locator(".rio-home-pair").evaluate((el) => getComputedStyle(el).gridTemplateColumns);
  expect(wideColumns.trim().split(/\s+/).length).toBeGreaterThanOrEqual(2);
});
