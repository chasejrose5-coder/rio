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
  prefs: { timezone: "America/Los_Angeles", intro_seen: true, compact: false, units: "miles", date_format: "iso" },
};

const inputs = {
  current_time: "2:05.0",
  start_date: "2026-11-08",
  goal_time: "1:58.0",
  goal_date: "2026-11-21",
};

function plan(withZones: boolean) {
  return {
    inputs,
    digest: "digest-1",
    marks: {},
    prefs: { ...athlete.prefs, today },
    months: ["2026-11-01"],
    month: "2026-11",
    month_title: "November 2026",
    calendar: [[]],
    weeks: [{ week: 1, phase: "4", status: "current", days_remaining: 11, meters: 2400, volume: "2,400 m" }],
    sessions: [
      {
        date: today,
        shown_date: today,
        day_of_week: "Tuesday",
        week_number: 1,
        template_id: "se_400_r90_x6",
        label: "6 × 400 m",
        reason_codes: ["phase_4"],
      },
      {
        date: "2026-11-12",
        shown_date: "2026-11-12",
        day_of_week: "Thursday",
        week_number: 1,
        template_id: "aer_8000_r0_x1",
        label: "8 km easy",
        reason_codes: ["extra_easy_day"],
      },
    ],
    actuals: { [today]: { template_id: "se_400_r90_x6", completed: true } },
    pace_status: "No runs yet",
    zone_weeks: withZones
      ? {
          "1": [
            { zone: 1, name: "Recovery", seconds: 30 },
            { zone: 2, name: "Easy / long", seconds: 600 },
            { zone: 3, name: "Tempo", seconds: 0 },
            { zone: 4, name: "Threshold", seconds: 90 },
            { zone: 5, name: "VO2max / race", seconds: 0 },
          ],
        }
      : undefined,
  };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(page: Page, options: { zones?: boolean; tracked?: boolean }) {
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/me") return json(route, athlete);
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/seasons/current") return json(route, { today, inputs, digest: "digest-1", actuals: {} });
    if (path.startsWith("/plan")) return json(route, plan(options.zones === true));
    if (path === "/activities") return json(route, { rows: [{ date: today, meters: 2400 }], all: [], notice: null });
    if (path === "/injury/summary" || path === "/core/summary" || path === "/foam/summary") {
      if (!options.tracked) return json(route, { detail: "Not found." }, 404);
      const label = path.startsWith("/injury") ? "Injury prevention" : path.startsWith("/core") ? "Core" : "Foam rolling";
      const done = path.startsWith("/injury") ? 2 : path.startsWith("/core") ? 1 : 0;
      return json(route, { tracked: true, done, label });
    }
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("the weekly recap shows distance, sessions, zones, tracked work, and the goal", async ({ page }) => {
  await install(page, { zones: true, tracked: true });
  await page.goto("/plan");
  await page.getByRole("radio", { name: "This week" }).click();
  const recap = page.locator(".rio-recap");
  await expect(recap.getByText("Sessions done")).toBeVisible();
  await expect(recap.getByText("1 of 2")).toBeVisible();
  await expect(recap.getByText("Distance")).toBeVisible();
  await expect(recap.getByText("Time in zone")).toBeVisible();
  await expect(recap.getByText("Zone 2 Easy / long · 10m")).toBeVisible();
  await expect(recap.getByText("Injury prevention")).toBeVisible();
  await expect(recap.getByText("2 marked done")).toBeVisible();
  await expect(recap.getByText("1 marked done")).toBeVisible();
  await expect(recap.getByText("0 marked done")).toBeVisible();
  await expect(recap.getByText("2:05.0 now · 1:58.0 goal · 11 days left")).toBeVisible();
  await expect(recap.getByText(/probability|readiness/i)).toHaveCount(0);

  if (process.env.RIO_SHOTS) {
    await page.setViewportSize({ width: 1280, height: 1100 });
    await recap.scrollIntoViewIfNeeded();
    await page.screenshot({ path: "/opt/cursor/artifacts/pr-d-recap-desktop.png" });
    await page.setViewportSize({ width: 390, height: 844 });
    await recap.evaluate((element) => element.scrollIntoView({ block: "start" }));
    await page.screenshot({ path: "/opt/cursor/artifacts/pr-d-recap-phone.png" });
  }
});

test("time in zone and extra work stay hidden when they are not tracked", async ({ page }) => {
  await install(page, { zones: false, tracked: false });
  await page.goto("/plan");
  await page.getByRole("radio", { name: "This week" }).click();
  const recap = page.locator(".rio-recap");
  await expect(recap.getByText("Distance")).toBeVisible();
  await expect(recap.getByText("Time in zone")).toHaveCount(0);
  await expect(recap.getByText("Injury prevention")).toHaveCount(0);
  await expect(recap.getByText("Core")).toHaveCount(0);
  await expect(recap.getByText("2:05.0 now · 1:58.0 goal · 11 days left")).toBeVisible();
});
