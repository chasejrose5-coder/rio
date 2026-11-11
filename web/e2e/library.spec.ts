import { expect, test, type Page, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-10",
  next_session: "2026-11-10",
  prefs: {
    easy_pace: "7:45",
    easy_pace_unit: "mi",
    intro_seen: true,
    no_watch: false,
    units: "miles",
    pace_units: "mi",
    show_ids: false,
    compact: false,
  },
};

const families = [
  { id: "aerobic", label: "Aerobic" },
  { id: "aerobic_power", label: "Aerobic power" },
  { id: "anaerobic_capacity", label: "Anaerobic" },
  { id: "max_velocity", label: "Max velocity" },
  { id: "race_readiness", label: "Race readiness" },
  { id: "speed", label: "Speed" },
  { id: "speed_endurance", label: "Speed endurance" },
  { id: "threshold", label: "Threshold" },
];

const workouts = [
  {
    id: "aer_10000_r0_x1",
    description: "Easy 50–60 min, about 6.2 mi",
    capacity: "Aerobic",
    family: "aerobic",
    phases: [1, 2, 3, 4, 5, 6, 7, 8],
  },
  {
    id: "aer_12000_r0_x1",
    description: "Long easy, about 7.5 mi",
    capacity: "Aerobic",
    family: "aerobic",
    phases: [1, 2, 3, 4, 5, 6, 7],
  },
  {
    id: "rr_800_r0_x1",
    description: "800 m race",
    capacity: "Race readiness",
    family: "race_readiness",
    phases: [8],
  },
  {
    id: "se_400_r90_x6",
    description: "6 × 400 m, 90 s rest",
    capacity: "Speed endurance",
    family: "speed_endurance",
    phases: [4],
  },
];

function menu(rows = workouts) {
  return { count: rows.length, workouts: rows, families };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(page: Page, options: { showIds?: boolean; fail?: string } = {}) {
  const person = { ...athlete, prefs: { ...athlete.prefs, show_ids: options.showIds === true } };
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/me") return json(route, person);
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/library") {
      if (options.fail) return json(route, { detail: options.fail }, 500);
      const q = url.searchParams.get("q") || "";
      const family = url.searchParams.get("family") || "";
      const phase = url.searchParams.get("phase");
      let rows = workouts;
      if (family) rows = rows.filter((row) => row.family === family);
      if (phase) rows = rows.filter((row) => row.phases.includes(Number(phase)));
      if (q) {
        const needle = q.toLowerCase();
        rows = rows.filter((row) => `${row.description} ${row.id} ${row.capacity}`.toLowerCase().includes(needle));
      }
      return json(route, menu(rows));
    }
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("the menu, a search, an empty result, and a load error", async ({ page }) => {
  await install(page);
  await page.goto("/library");
  await expect(page.getByRole("heading", { name: "Library" })).toBeVisible();
  await expect(page.getByText("SYNTHETIC")).toHaveCount(0);
  await expect(page.getByText("DEMO")).toHaveCount(0);
  await expect(page.locator("img")).toHaveCount(0);
  await expect(page.getByLabel("Search")).toHaveAttribute("placeholder", "Search workouts");
  await expect(page.getByText("The quality that workout builds, such as speed or endurance.")).toBeHidden();
  await page.getByRole("button", { name: "Help" }).first().hover();
  await expect(page.getByText("The quality that workout builds, such as speed or endurance.")).toBeVisible();
  await page.getByRole("button", { name: "Help" }).nth(1).focus();
  await expect(page.getByText("A phase is a training block. The season moves through eight of them.")).toBeVisible();
  await expect(page.getByLabel("What it trains")).toContainText("Aerobic power");
  await expect(page.getByLabel("Phase")).toContainText("Phase 8");
  await expect(page.getByText("4 workouts")).toBeVisible();
  await expect(page.getByText("Easy 50–60 min, about 6.2 mi")).toBeVisible();
  await expect(page.getByText("800 m race")).toBeVisible();
  await expect(page.getByText("aer_10000_r0_x1")).toHaveCount(0);
  await expect(page.locator(".rio-lib-row a")).toHaveCount(0);
  const background = await page.locator(".page-library").evaluate((el) => getComputedStyle(el).backgroundImage);
  expect(background).toBe("none");

  await page.getByLabel("Search").fill("rr_800");
  await expect(page.getByText("1 workout")).toBeVisible();
  await expect(page.getByText("800 m race")).toBeVisible();
  await expect(page.getByText("6 × 400 m, 90 s rest")).toHaveCount(0);

  await page.getByLabel("Search").fill("no-such-workout");
  await expect(page.getByText("No workouts.")).toBeVisible();
  await expect(page.getByText("0 workouts")).toBeVisible();

  await page.getByLabel("Search").fill("");
  await page.getByLabel("What it trains").selectOption("speed_endurance");
  await expect(page.getByText("1 workout")).toBeVisible();
  await expect(page.getByText("6 × 400 m, 90 s rest")).toBeVisible();
  await page.getByLabel("What it trains").selectOption("All");
  await page.getByLabel("Phase").selectOption("8");
  await expect(page.getByText("800 m race")).toBeVisible();
  await expect(page.getByText("Long easy, about 7.5 mi")).toHaveCount(0);
});

test("a failed menu is the exception sentence, not an empty list", async ({ page }) => {
  await install(page, { fail: "menu <broken>" });
  await page.goto("/library");
  await expect(page.getByText("menu <broken>")).toBeVisible();
  await expect(page.locator(".rio-error b")).toHaveCount(0);
  await expect(page.getByText("No workouts.")).toHaveCount(0);
  await expect(page.locator(".rio-lib-row")).toHaveCount(0);
});

test("template ids show only when the setting is on", async ({ page }) => {
  await install(page, { showIds: true });
  await page.goto("/library");
  await expect(page.getByText("aer_10000_r0_x1")).toBeVisible();
  await expect(page.getByText("rr_800_r0_x1")).toBeVisible();
});

test("More still lists the five pages under the nav", async ({ page }) => {
  await install(page);
  await page.goto("/more");
  const sub = page.getByRole("navigation", { name: "More" });
  await expect(sub.getByRole("link", { name: "Past seasons" })).toHaveAttribute("href", "/past-seasons");
  await expect(sub.getByRole("link", { name: "Profile" })).toHaveAttribute("href", "/profile");
  await expect(sub.getByRole("link", { name: "Settings" })).toHaveAttribute("href", "/settings");
  await expect(sub.getByRole("link", { name: "About" })).toHaveAttribute("href", "/about");
  await expect(sub.getByRole("link", { name: "Creators" })).toHaveAttribute("href", "/creators");
  await page.goto("/library");
  await expect(page.getByRole("navigation", { name: "More" })).toHaveCount(0);
});
