import { mkdirSync } from "node:fs";
import { expect, test, type Page, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-10",
  next_session: null,
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
    preferred: "",
  },
};

const current = {
  inputs: {
    current_time: "2:04.0",
    start_date: "2026-08-02",
    goal_time: "1:56.0",
    goal_date: "2026-11-10",
  },
  current: true,
  stats: [
    { label: "Season", value: "Aug 2, 2026 – Nov 10, 2026" },
    { label: "Goal time", value: "1:56.0" },
  ],
};

const replaced = {
  inputs: {
    current_time: "2:08.0",
    start_date: "2026-11-04",
    goal_time: "1:55.0",
    goal_date: "2027-04-04",
  },
  current: false,
  stats: [
    { label: "Season", value: "Nov 4, 2026 – Apr 4, 2027" },
    { label: "Goal time", value: "1:55.0" },
    { label: "Workouts logged", value: "3" },
  ],
};

const older = {
  inputs: {
    current_time: "2:08.0",
    start_date: "2019-03-02",
    goal_time: "1:59.0",
    goal_date: "2019-06-01",
  },
  stats: [
    { label: "Season", value: "Mar 2, 2019 – Jun 1, 2019" },
    { label: "Goal time", value: "1:59.0" },
    { label: "Workouts logged", value: "4" },
    { label: "Notes", value: "1" },
  ],
};

const recent = {
  inputs: {
    current_time: "2:05.0",
    start_date: "2020-01-06",
    goal_time: "1:55.0",
    goal_date: "2020-04-06",
  },
  stats: [
    { label: "Season", value: "Jan 6, 2020 – Apr 6, 2020" },
    { label: "Goal time", value: "1:55.0" },
    { label: "Workouts logged", value: "2" },
  ],
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(
  page: Page,
  options: { empty?: boolean; fail?: boolean; iso?: boolean; hold?: Promise<void> } = {},
) {
  const user = structuredClone(athlete);
  if (options.iso) user.prefs.date_format = "iso";
  const deletes: unknown[] = [];
  let seasons = options.empty ? [] : [older, recent];
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    const method = route.request().method();
    if (path === "/auth/me") return json(route, user);
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/seasons/past" && method === "GET") {
      if (options.hold) await options.hold;
      if (options.fail) return json(route, { detail: "Accounts could not be read." }, 401);
      return json(route, { today: "2026-11-10", seasons, open: options.empty ? [] : [replaced, current] });
    }
    if (path === "/seasons/past" && method === "DELETE") {
      const body = route.request().postDataJSON() as { confirm?: boolean; goal_date?: string };
      deletes.push(body);
      if (body.confirm !== true) return json(route, { detail: "Confirm this season before it is deleted." }, 400);
      const training = body.goal_date === "2026-11-10";
      seasons = seasons.filter((row) => row.inputs.goal_date !== body.goal_date);
      return json(route, { deleted: true, current: training, inputs: body, stats: recent.stats });
    }
    if (path === "/plan" && method === "GET") {
      const goal = url.searchParams.get("goal_date");
      return json(route, {
        inputs: goal === "2020-04-06" ? recent.inputs : current.inputs,
        digest: "abc",
        marks: goal === "2020-04-06" ? { "3": "on_track" } : {},
        prefs: { date_format: user.prefs.date_format, today: "2026-11-10", units: "miles" },
        months: ["2020-01"],
        month: "2020-01",
        month_title: "January 2020",
        calendar: [],
        weeks: [{ week: 1, phase: "1", status: "past", days_remaining: 0, meters: 0, volume: "0" }],
        sessions: [],
        actuals: {},
        pace_status: "No runs yet",
      });
    }
    if (path === "/home") return json(route, { today: "2026-11-10", season: null, hello: "Ada", strava_offer: false, copy: "" });
    if (path === "/seasons/current") return json(route, { detail: "No current season." }, 404);
    if (path === "/activities") return json(route, { detail: "No current season." }, 404);
    return json(route, {});
  });
  return { deletes };
}

test("a slow list shows the nav and a skeleton", async ({ page }) => {
  let release: () => void = () => undefined;
  const hold = new Promise<void>((resolve) => {
    release = resolve;
  });
  await install(page, { hold });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/past-seasons");
  await expect(page.getByRole("navigation", { name: "Pages" }).getByRole("link", { name: "Home" })).toBeVisible();
  await expect(page.getByText("Loading", { exact: true })).toHaveCount(0);
  await expect(page.locator(".rio-skel").first()).toBeVisible();
  mkdirSync("/opt/cursor/artifacts", { recursive: true });
  await page.screenshot({ path: "/opt/cursor/artifacts/past-seasons-skeleton-phone.png", fullPage: true });
  release();
  await expect(page.getByText("Aug 2, 2026", { exact: false }).first()).toBeVisible();
  await expect(page.locator(".rio-skel")).toHaveCount(0);
});

test("an empty account says there are no seasons", async ({ page }) => {
  await install(page, { empty: true });
  await page.goto("/past-seasons");
  await expect(page.getByRole("heading", { name: "Past seasons" })).toBeVisible();
  await expect(page.getByText("No seasons on this account.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Delete season" })).toHaveCount(0);
});

test("two stored seasons list start, goal, and time", async ({ page }) => {
  await install(page);
  await page.goto("/past-seasons");
  await expect(page.getByRole("link", { name: "Open plan, Mar 2, 2019 Jun 1, 2019 1:59.0" })).toBeVisible();
  const opened = page.getByRole("link", { name: "Open plan, Jan 6, 2020 Apr 6, 2020 1:55.0" });
  await expect(opened).toBeVisible();
  await expect(opened).toHaveText("Open plan");
  await expect(page.getByRole("link", { name: "Open plan, Aug 2, 2026 Nov 10, 2026 1:56.0" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open plan, Nov 4, 2026 Apr 4, 2027 1:55.0" })).toBeVisible();
  await expect(page.getByText("2026-11-04 2027-04-04 1:55.0")).toHaveCount(0);
  await expect(page.getByText("Start date").first()).toBeVisible();
  await expect(page.getByText("Goal date").first()).toBeVisible();
  await expect(page.getByText("Goal time").first()).toBeVisible();
});

test("iso dates stay as calendar dates", async ({ page }) => {
  await install(page, { iso: true });
  await page.goto("/past-seasons");
  await expect(page.getByRole("link", { name: "Open plan, 2020-01-06 2020-04-06 1:55.0" })).toBeVisible();
});

test("a future season that is not the training season can be deleted", async ({ page }) => {
  await install(page);
  await page.goto("/past-seasons");
  const replacedRow = page.locator(".rio-past-item").filter({ hasText: "Apr 4, 2027" });
  await expect(replacedRow.getByRole("button", { name: "Delete season" })).toBeVisible();
  const training = page.locator(".rio-past-item").filter({ hasText: "Nov 10, 2026" });
  await expect(training.getByRole("button", { name: "Delete season" })).toBeVisible();
});

test("opening a past season loads those inputs", async ({ page }) => {
  await install(page);
  await page.goto("/past-seasons");
  await page.getByRole("link", { name: "Open plan, Jan 6, 2020 Apr 6, 2020 1:55.0" }).click();
  await expect(page).toHaveURL(/goal_date=2020-04-06/);
  await expect(page).toHaveURL(/start_date=2020-01-06/);
  await expect(page.getByRole("heading", { name: "1 week" })).toBeVisible();
  await expect(page.getByText("Jan 6, 2020 — Apr 6, 2020")).toBeVisible();
});

test("delete asks with the stats, then removes only that season", async ({ page }) => {
  const state = await install(page);
  await page.goto("/past-seasons");
  const row = page.locator(".rio-past-item").filter({ hasText: "Apr 6, 2020" });
  await row.getByRole("button", { name: "Delete season" }).click();
  await expect(page.getByText("Delete this season?")).toBeVisible();
  await expect(page.getByText("Jan 6, 2020 – Apr 6, 2020")).toBeVisible();
  await expect(page.getByText("Workouts logged", { exact: true })).toBeVisible();
  await expect(page.getByText("This permanently deletes this season and the workouts stored with it.")).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByText("Delete this season?")).toHaveCount(0);
  expect(state.deletes).toEqual([]);
  await row.getByRole("button", { name: "Delete season" }).click();
  await page.getByRole("button", { name: "Delete permanently" }).click();
  await expect(page.getByText("Season deleted.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open plan, Jan 6, 2020 Apr 6, 2020 1:55.0" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Open plan, Mar 2, 2019 Jun 1, 2019 1:59.0" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Open plan, Aug 2, 2026 Nov 10, 2026 1:56.0" })).toBeVisible();
  expect(state.deletes).toEqual([
    expect.objectContaining({ goal_date: "2020-04-06", confirm: true }),
  ]);
});

test("deleting the training season warns and opens Start", async ({ page }) => {
  await install(page);
  await page.goto("/past-seasons");
  const training = page.locator(".rio-past-item").filter({ hasText: "Nov 10, 2026" });
  await training.getByRole("button", { name: "Delete season" }).click();
  await expect(page.getByText("This is the season you're training on now.")).toBeVisible();
  await expect(page.getByText("Aug 2, 2026 – Nov 10, 2026")).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByText("This is the season you're training on now.")).toHaveCount(0);
  await training.getByRole("button", { name: "Delete season" }).click();
  await page.getByRole("button", { name: "Delete permanently" }).click();
  await expect(page).toHaveURL(/\/start\?new=1$/);
  await expect(page.getByRole("heading", { name: "Start" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate season plan" })).toBeVisible();
});

test("an unreadable account uses the page sentence", async ({ page }) => {
  await install(page, { fail: true });
  await page.goto("/past-seasons");
  await expect(page.getByText("This account's seasons could not be read.")).toBeVisible();
  await expect(page.getByText("No seasons on this account.")).toHaveCount(0);
});
