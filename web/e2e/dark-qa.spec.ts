import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { expect, test, type Page, type Route } from "@playwright/test";

const axePath = join(process.cwd(), "node_modules/axe-core/axe.min.js");
const shots = "/opt/cursor/artifacts";
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
    easy_pace: "7:25",
    easy_pace_unit: "mi",
    easy_pace_phrase: "7:25 per mile",
    intro_seen: true,
    no_watch: false,
    confirm_adapt: false,
    timezone: "America/Los_Angeles",
    date_format: "short",
    pace_units: "mi",
    units: "miles",
    show_ids: false,
    compact: false,
    theme: "dark",
    preferred: "Ada",
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
          { short: "Tue", role: "hard" },
          { short: "Thu", role: "hard" },
          { short: "Sat", role: "long" },
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
      facts: { distance: "400 m", pace: "Near goal 800", rest: "90 s", reps: "6" },
      prescription: { line: "6 × 400 m @ 57.5 s, 90 s rest", tolerance: "55.0-60.0 s", block: "9:15.0" },
    },
    upcoming: [],
    next_days: [
      { date: today, shown_date: today, day_of_week: "Tuesday", template_id: "se_400_r90_x6", label: "6 × 400 m", prescription: { line: "6 × 400 m", tolerance: "", block: "" } },
      { date: "2026-11-11", shown_date: "2026-11-11", day_of_week: "Wednesday", template_id: "", label: "Rest" },
      { date: "2026-11-12", shown_date: "2026-11-12", day_of_week: "Thursday", template_id: "se_300_r60_x8", label: "8 × 300 m" },
    ],
    notes: [],
  },
};

const plan = {
  inputs: home.season.inputs,
  digest: "digest-1",
  marks: {},
  actuals: {},
  prefs: { ...athlete.prefs, today },
  months: ["2026-11-01"],
  month: "2026-11",
  month_title: "November 2026",
  pace_status: "No runs yet",
  calendar: [[
    { date: "2026-11-09", in_month: true, day: 9, label: "", template_id: "", today: false },
    { date: today, in_month: true, day: 10, label: "Speed", template_id: "se_400_r90_x6", today: true },
    { date: "2026-11-11", in_month: true, day: 11, label: "Rest", template_id: "", today: false },
    { date: "2026-11-12", in_month: true, day: 12, label: "", template_id: "", today: false },
    { date: "2026-11-13", in_month: true, day: 13, label: "", template_id: "", today: false },
    { date: "2026-11-14", in_month: true, day: 14, label: "", template_id: "", today: false },
    { date: "2026-11-15", in_month: true, day: 15, label: "Easy", template_id: "aer_8000_r0_x1", today: false },
  ]],
  weeks: [{ week: 1, phase: "4", status: "current", days_remaining: 11, meters: 0, volume: "0 m" }],
  sessions: home.season.next_days,
  phases: [],
};

const session = {
  date: today,
  session: { date: today, day_of_week: "Tuesday", template_id: "se_400_r90_x6", week_number: 1 },
  actual: null,
  quality: true,
  note: null,
  viewed: true,
  digest: "digest-1",
  label: "6 × 400 m near goal 800 pace, 90 s rest",
  structure: "6 × 400 m, 90 s rest",
  target: "Hit the session.",
  reasons: ["Phase 4"],
  shown_date: today,
  prescription: { line: "6 × 400 m @ 71.2 s, 90 s rest", tolerance: "68.0-74.4 s", block: "12:06.0", average: "71.2 s" },
  logging: "times",
  confirm_adapt: false,
  show_id: false,
  boxes: 6,
  seed: [null, null, null, null, null, null],
  summary: "",
  match: null,
  heart_rate: "",
};

const library = {
  count: 2,
  families: [{ id: "aerobic", label: "Aerobic" }],
  workouts: [
    { id: "aer_10000_r0_x1", description: "Easy 50–60 min", capacity: "Aerobic", family: "aerobic", phases: [1, 2] },
    { id: "se_400_r90_x6", description: "6 × 400 m, 90 s rest", capacity: "Speed endurance", family: "speed_endurance", phases: [4] },
  ],
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
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/home") return json(route, home);
    if (path === "/plan") return json(route, plan);
    if (path === "/seasons/current") return json(route, { today, inputs: plan.inputs, digest: "digest-1", plan: { sessions: plan.sessions } });
    if (path.startsWith("/sessions/")) return json(route, session);
    if (path === "/library") return json(route, library);
    if (path === "/activities") return json(route, { connected: false, rows: [], all: [], weeks: [] });
    if (path === "/strava/status") return json(route, { connected: false });
    if (path === "/profile") {
      return json(route, {
        ready: true,
        fields: [
          { label: "Current 800 time", value: "2:02.9" },
          { label: "Start date", value: "Apr 19, 2026" },
          { label: "Goal 800m time", value: "1:55.0" },
          { label: "Goal date", value: "Mar 19, 2027" },
        ],
        profile_key: "k",
        goal_time: "1:55.0",
        goal_override: null,
        shown_goal: "1:55.0",
        inputs: plan.inputs,
        easy_pace: "7:25",
        easy_pace_unit: "mi",
        easy_pace_phrase: "7:25 per mile",
        prefs: { date_format: "short", compact: false },
      });
    }
    if (path === "/seasons/past") {
      return json(route, {
        seasons: [{
          inputs: plan.inputs,
          current: true,
          stats: [{ label: "Season", value: "Apr 19, 2026 – Mar 19, 2027" }],
        }],
      });
    }
    if (path === "/heart-rate") {
      return json(route, { no_monitor: false, resting_hr: null, max_hr: null, zones: [], custom: false, method: "karvonen", method_label: "Karvonen", method_sentence: "Zones use Karvonen.", safety: "Not medical advice.", strava_prefill: { available: false } });
    }
    if (path === "/stretch") return json(route, { today, spots: [], completions: [] });
    if (path === "/core") return json(route, { today, completions: [] });
    if (path === "/foam") return json(route, { today, completions: [] });
    if (path === "/injury" || path === "/recovery") return json(route, { today, areas: [] });
    if (path === "/settings" && route.request().method() === "PATCH") return json(route, athlete);
    return json(route, {});
  });
}

async function paintDark(page: Page) {
  await page.addInitScript(() => localStorage.setItem("rio-theme", "dark"));
  await page.emulateMedia({ colorScheme: "dark" });
}

function ratio(fg: string, bg: string): number {
  const channel = (value: number) => {
    const s = value / 255;
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  const lum = (color: string) => {
    const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (!match) return 0;
    return 0.2126 * channel(Number(match[1])) + 0.7152 * channel(Number(match[2])) + 0.0722 * channel(Number(match[3]));
  };
  const a = lum(fg);
  const b = lum(bg);
  const [hi, lo] = a > b ? [a, b] : [b, a];
  return (hi + 0.05) / (lo + 0.05);
}

async function contrastIssues(page: Page): Promise<string[]> {
  const found = await page.evaluate(() => {
    const opaque = (color: string) => {
      const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
      if (!match) return null;
      const alpha = match[4] === undefined ? 1 : Number(match[4]);
      if (alpha < 0.99) return null;
      return `rgb(${match[1]}, ${match[2]}, ${match[3]})`;
    };
    const background = (start: Element) => {
      let node: Element | null = start;
      while (node) {
        const style = getComputedStyle(node);
        if (style.backgroundImage && style.backgroundImage !== "none") return "photo";
        const color = opaque(style.backgroundColor);
        if (color) return color;
        node = node.parentElement;
      }
      return opaque(getComputedStyle(document.body).backgroundColor) || "rgb(20, 18, 17)";
    };
    const visible = (el: Element) => {
      const style = getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return false;
      const rect = el.getBoundingClientRect();
      return rect.width > 1 && rect.height > 1;
    };
    const rows: { fg: string; bg: string; size: number; weight: number; text: string }[] = [];
    const nodes = document.querySelectorAll("body *");
    nodes.forEach((el) => {
      if (!visible(el) || el.getAttribute("aria-hidden") === "true") return;
      let text = "";
      if (el.tagName === "text" || el.tagName === "tspan") text = (el.textContent || "").trim();
      else {
        el.childNodes.forEach((node) => {
          if (node.nodeType === Node.TEXT_NODE) text += node.textContent || "";
        });
        text = text.trim();
      }
      if (!text) return;
      const style = getComputedStyle(el);
      const fg = el.tagName === "text" || el.tagName === "tspan" ? style.fill : style.color;
      rows.push({
        fg,
        bg: background(el),
        size: Number.parseFloat(style.fontSize) || 16,
        weight: Number.parseInt(style.fontWeight, 10) || 400,
        text: text.slice(0, 60),
      });
    });
    document.querySelectorAll("input, select, textarea").forEach((el) => {
      if (!visible(el)) return;
      const style = getComputedStyle(el);
      if (style.borderTopStyle === "none" || Number.parseFloat(style.borderTopWidth) < 1) return;
      rows.push({ fg: style.borderTopColor, bg: background(el), size: 0, weight: 400, text: `ui:${el.tagName}` });
    });
    return rows;
  });
  return found.flatMap((row) => {
    if (row.bg === "photo") return [];
    const need = row.size === 0 ? 3 : row.size >= 24 || (row.size >= 18.5 && row.weight >= 700) ? 3 : 4.5;
    const score = ratio(row.fg, row.bg);
    if (score >= need) return [];
    return [`${score.toFixed(2)} < ${need} “${row.text}” ${row.fg} on ${row.bg}`];
  });
}

async function axeContrast(page: Page): Promise<string[]> {
  await page.addScriptTag({ path: axePath });
  return page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (node: Document, options: object) => Promise<{ violations: { nodes: { html: string; failureSummary?: string }[] }[] }> } }).axe;
    const result = await axe.run(document, { runOnly: { type: "rule", values: ["color-contrast"] } });
    return result.violations.flatMap((violation) => violation.nodes.slice(0, 6).map((node) => `${node.failureSummary || "contrast"} ${node.html.slice(0, 160)}`));
  });
}

const screens = [
  ["/", "landing"],
  ["/sign-in?skip=1", "sign-in"],
  ["/create-account", "create"],
  ["/privacy", "privacy"],
  ["/terms", "terms"],
  ["/home", "home"],
  ["/plan", "plan"],
  ["/session?date=2026-11-10", "session"],
  ["/library", "library"],
  ["/stretch", "stretch"],
  ["/recovery", "recovery"],
  ["/core", "core"],
  ["/foam", "foam"],
  ["/activity", "activity"],
  ["/heart-rate", "heart"],
  ["/more", "more"],
  ["/profile", "profile"],
  ["/settings", "settings"],
  ["/past-seasons", "past"],
  ["/guide", "guide"],
  ["/about", "about"],
  ["/creators", "creators"],
] as const;

test.describe("dark mode contrast", () => {
  test.describe.configure({ timeout: 240_000 });

  for (const width of [1280, 768, 375]) {
    test(`text and controls clear AA at ${width}`, async ({ page }) => {
      await paintDark(page);
      await install(page);
      const height = width === 375 ? 812 : width === 768 ? 1024 : 800;
      await page.setViewportSize({ width, height });
      const misses: string[] = [];
      for (const [path, name] of screens) {
        await page.goto(path, { waitUntil: "domcontentloaded" });
        await page.locator("body").waitFor();
        await page.evaluate(() => {
          document.querySelectorAll("details").forEach((node) => {
            node.open = true;
          });
        });
        const found = await contrastIssues(page);
        if (found.length) misses.push(`${name}: ${found.slice(0, 6).join(" | ")}`);
        if (width === 1280 && ["settings", "home", "library", "about", "stretch", "session"].includes(name)) {
          mkdirSync(shots, { recursive: true });
          await page.screenshot({ path: `${shots}/after-${name}-dark-1280.png`, fullPage: false });
        }
      }
      expect(misses).toEqual([]);
    });
  }

  test("axe finds no color-contrast violations in dark", async ({ page }) => {
    test.setTimeout(240_000);
    await paintDark(page);
    await install(page);
    await page.setViewportSize({ width: 1280, height: 900 });
    const misses: string[] = [];
    for (const [path, name] of screens) {
      await page.goto(path, { waitUntil: "networkidle" });
      await page.evaluate(() => {
        document.querySelectorAll("details").forEach((node) => {
          node.open = true;
        });
      });
      const found = await axeContrast(page);
      if (found.length) misses.push(`${name}: ${found.slice(0, 3).join(" | ")}`);
    }
    expect(misses).toEqual([]);
  });
});

test("home phase opens beside today's workout", async ({ page }) => {
  await install(page);
  for (const width of [1024, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/home");
    const phase = page.locator(".rio-phase-details");
    await expect(phase).toHaveAttribute("open", "");
    await expect(phase.locator(".rio-phase-headline")).toBeVisible();
    const boxes = await page.evaluate(() => {
      const pair = document.querySelector(".rio-home-pair");
      const left = pair?.querySelector(":scope > .rio-home-phase");
      const right = pair?.querySelector(":scope > .rio-home-today");
      const label = (node: Element | null | undefined) => node?.querySelector(":scope > .rio-index")?.getBoundingClientRect();
      const card = (node: Element | null | undefined) => node?.getBoundingClientRect();
      return {
        phase: card(left),
        today: card(right),
        phaseLabel: label(left),
        todayLabel: label(right),
      };
    });
    expect(boxes.phase && boxes.today && boxes.phaseLabel && boxes.todayLabel).toBeTruthy();
    expect(Math.abs(boxes.phase!.top - boxes.today!.top)).toBeLessThanOrEqual(1);
    expect(Math.abs(boxes.phase!.height - boxes.today!.height)).toBeLessThanOrEqual(1);
    expect(Math.abs(boxes.phaseLabel!.top - boxes.todayLabel!.top)).toBeLessThanOrEqual(1);
    if (width === 1280) {
      mkdirSync(shots, { recursive: true });
      await page.screenshot({ path: `${shots}/after-home-pair-1280.png` });
    }
  }
});

test("library filters share a top and are 44px tall", async ({ page }) => {
  await paintDark(page);
  await install(page);
  for (const width of [1280, 768, 375]) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    await page.goto("/library");
    await expect(page.locator("#library-search")).toBeVisible();
    const boxes = await page.evaluate(() => {
      const nodes = ["#library-search", "#library-capacity", "#library-phase"].map((selector) => {
        const node = document.querySelector(selector);
        const rect = node?.getBoundingClientRect();
        return rect ? { top: rect.top, height: rect.height } : null;
      });
      return nodes;
    });
    for (const box of boxes) {
      expect(box).not.toBeNull();
      expect(Math.abs((box?.height || 0) - 44)).toBeLessThanOrEqual(1);
    }
    if (width >= 1024) {
      expect(Math.abs((boxes[0]?.top || 0) - (boxes[1]?.top || 0))).toBeLessThanOrEqual(1);
      expect(Math.abs((boxes[1]?.top || 0) - (boxes[2]?.top || 0))).toBeLessThanOrEqual(1);
    } else if (width >= 768) {
      const searchWidth = await page.locator("#library-search").evaluate((node) => node.getBoundingClientRect().width);
      const formWidth = await page.locator(".rio-library").evaluate((node) => node.getBoundingClientRect().width);
      expect(searchWidth).toBeGreaterThan(formWidth * 0.9);
      expect(Math.abs((boxes[1]?.top || 0) - (boxes[2]?.top || 0))).toBeLessThanOrEqual(1);
      expect((boxes[1]?.top || 0) > (boxes[0]?.top || 0) + 20).toBe(true);
    } else {
      expect((boxes[1]?.top || 0) > (boxes[0]?.top || 0)).toBe(true);
      expect((boxes[2]?.top || 0) > (boxes[1]?.top || 0)).toBe(true);
    }
    const all = await page.locator("#library-capacity").evaluate((node) => getComputedStyle(node).color);
    expect(ratio(all, "rgb(40, 36, 33)")).toBeGreaterThanOrEqual(4.5);
    if (width === 1280) {
      mkdirSync(shots, { recursive: true });
      await page.screenshot({ path: `${shots}/after-library-dark-1280.png` });
    }
  }
});

test("a stale device theme does not paint before the account cookie", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.addInitScript(() => localStorage.setItem("rio-theme", "light"));
  await page.context().addCookies([{ name: "rio_theme", value: "dark", url: "http://localhost:3000/" }]);
  await page.goto("/", { waitUntil: "commit" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});

test("the landing fits 768 and 375 without scrolling", async ({ page }) => {
  for (const [width, height] of [[768, 1024], [375, 812]] as const) {
    await page.setViewportSize({ width, height });
    await page.goto("/");
    await page.getByRole("heading", { name: /Your Race/ }).waitFor();
    await page.evaluate(() => document.fonts.ready);
    const overflow = await page.evaluate(() => {
      const splash = document.querySelector(".rio-splash");
      return {
        overflow: document.documentElement.scrollHeight - document.documentElement.clientHeight,
        splash: splash ? Math.round(splash.getBoundingClientRect().height) : null,
        clip: splash ? getComputedStyle(splash).overflow : null,
        bottom: splash ? Math.round(splash.getBoundingClientRect().bottom) : null,
      };
    });
    expect(overflow.overflow, JSON.stringify(overflow)).toBeLessThanOrEqual(1);
  }
});

test("library and guide stick below the sub-nav", async ({ page }) => {
  await install(page);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/library");
  await expect(page.locator("#library-search")).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 700));
  const libraryClear = await page.evaluate(() => {
    const nav = document.querySelector(".rio-nav")?.getBoundingClientRect().bottom || 0;
    const bar = document.querySelector(".rio-library")?.getBoundingClientRect().top || 0;
    return bar + 1 >= nav;
  });
  expect(libraryClear).toBe(true);
  await page.goto("/guide");
  await expect(page.locator(".rio-guide-contents a[aria-current='true']")).toHaveCount(1);
  await page.evaluate(() => window.scrollTo(0, 700));
  const guideClear = await page.evaluate(() => {
    const nav = document.querySelector(".rio-nav")?.getBoundingClientRect().bottom || 0;
    const bar = document.querySelector(".rio-guide-contents")?.getBoundingClientRect().top || 0;
    return bar + 1 >= nav;
  });
  expect(guideClear).toBe(true);
});
