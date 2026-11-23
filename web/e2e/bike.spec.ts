import { expect, test, type Page, type Route } from "@playwright/test";

const today = "2026-11-11";

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

const easy = {
  date: today,
  session: {
    date: today,
    day_of_week: "Wednesday",
    template_id: "aer_8000_r0_x1",
    week_number: 1,
    reason_codes: ["extra_easy_day"],
  },
  actual: null,
  quality: false,
  note: null,
  viewed: true,
  digest: "digest-1",
  label: "8 km easy",
  structure: "One continuous easy run, planned 8000 m.",
  target: "Stay conversational.",
  reasons: ["An easy day"],
  shown_date: today,
  prescription: { line: "Run at 7:45 per mile", tolerance: "", block: "", average: "" },
  logging: "times",
  confirm_adapt: true,
  show_id: false,
  boxes: 0,
  seed: [],
  summary: "",
  match: null,
  heart_rate: "",
};

function plan() {
  return {
    inputs,
    digest: "digest-1",
    marks: {},
    prefs: { ...athlete.prefs, today },
    months: ["2026-11-01"],
    month: "2026-11",
    month_title: "November 2026",
    calendar: [[]],
    weeks: [{ week: 1, phase: "4", status: "current", days_remaining: 10, meters: 2400, volume: "2,400 m" }],
    sessions: [
      {
        date: "2026-11-10",
        shown_date: "2026-11-10",
        day_of_week: "Tuesday",
        week_number: 1,
        template_id: "se_400_r90_x6",
        label: "6 × 400 m",
        reason_codes: ["phase_4"],
      },
      easy.session,
    ],
    actuals: { "2026-11-10": { template_id: "se_400_r90_x6", completed: true } },
    pace_status: "No runs yet",
  };
}

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
    if (path === "/auth/me") return json(route, athlete);
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/seasons/current") return json(route, { today, inputs, digest: "digest-1", actuals: {} });
    if (path.startsWith("/plan")) return json(route, plan());
    if (path.startsWith("/sessions/")) return json(route, easy);
    if (path === "/activities") return json(route, { rows: [{ date: "2026-11-10", meters: 2400 }], all: [], notice: null });
    if (path === "/bike/week") {
      return json(route, {
        tracked: true,
        dates: [today],
        minutes: 50,
        distance_m: 19312,
        zone2_seconds: 2400,
        zone_seconds: 3000,
      });
    }
    if (path === "/bike") {
      return json(route, {
        date: today,
        offer: true,
        suggest_first: true,
        minutes: 50,
        swaps_used: 0,
        swapped: false,
        zone2: { low_bpm: 126, high_bpm: 138, sentence: "Easy bike is zone 2, conversational." },
        log: null,
      });
    }
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("an easy day offers a bike swap, and the week recap keeps bike distance off the run total", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await install(page);
  await page.goto(`/session?date=${today}`);
  const swap = page.getByRole("region", { name: "Bike instead" });
  await expect(swap.getByRole("button", { name: "Bike instead" })).toBeVisible();
  await expect(swap.getByText("50 min")).toBeVisible();
  await expect(swap.getByText(/Zone 2, 126-138 bpm/)).toBeVisible();
  await expect(swap.getByText("Suggested while a shin, Achilles, or foot area is rebuilding.")).toBeVisible();
  await expect(page.getByText("Not medical advice.").first()).toBeVisible();
  await expect(page.getByText(/cadence|rpm/i)).toHaveCount(0);
  await expect(page.getByText("Run at 7:45 per mile")).toBeVisible();

  if (process.env.RIO_SHOTS) {
    await swap.evaluate((element) => element.scrollIntoView({ block: "center" }));
    await page.screenshot({ path: `${process.env.RIO_ARTIFACTS || "test-results"}/pr-bike-session-phone.png` });
  }

  await page.goto("/plan");
  await page.getByRole("radio", { name: "This week" }).click();
  const recap = page.locator(".rio-recap");
  await expect(recap.getByText("Sessions done")).toBeVisible();
  await expect(recap.getByText("2 of 2")).toBeVisible();
  await expect(recap.getByText("Bike")).toBeVisible();
  await expect(recap.getByText(/50 min/)).toBeVisible();
  await expect(recap.getByText(/in zone 2/)).toBeVisible();
  await expect(recap.getByText(/probability|readiness|cadence|rpm/i)).toHaveCount(0);

  if (process.env.RIO_SHOTS) {
    await recap.evaluate((element) => element.scrollIntoView({ block: "start" }));
    await page.screenshot({ path: `${process.env.RIO_ARTIFACTS || "test-results"}/pr-bike-recap-phone.png` });
  }
});
