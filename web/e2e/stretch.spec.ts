import { expect, test, type Page, type Route } from "@playwright/test";
import { prescribe } from "../lib/stretch-content";

const today = "2026-11-10";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today,
  next_session: today,
  prefs: { timezone: "America/Los_Angeles", intro_seen: true, compact: false },
};

const season = {
  today,
  inputs: {
    current_time: "2:05.0",
    start_date: "2026-11-08",
    goal_time: "1:58.0",
    goal_date: "2026-12-19",
  },
  plan: {
    sessions: [
      {
        date: today,
        day_of_week: "Tuesday",
        template_id: "se_400_r90_x6",
        reason_codes: ["phase_4", "phase_primary"],
      },
    ],
  },
};

type Spot = {
  region: string;
  severity: string;
  started_on: string;
  check_in_on: string;
  cleared: boolean;
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(page: Page) {
  const spots: Spot[] = [];
  const completions: { date: string; routine_id: string }[] = [];
  const body = () => ({ today, spots, completions });
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    const method = route.request().method();
    if (path === "/auth/me") return json(route, athlete);
    if (path === "/seasons/current") return json(route, season);
    if (path === "/stretch" && method === "GET") return json(route, body());
    if (path === "/stretch/spots" && method === "POST") {
      const payload = route.request().postDataJSON() as { region: string; severity: string };
      const next = {
        region: payload.region,
        severity: payload.severity,
        started_on: today,
        check_in_on: "2026-11-17",
        cleared: false,
      };
      const index = spots.findIndex((spot) => spot.region === payload.region);
      if (index >= 0) spots[index] = next;
      else spots.push(next);
      return json(route, body());
    }
    if (path === "/stretch/completions" && method === "POST") {
      const payload = route.request().postDataJSON() as { routine_id: string };
      const index = completions.findIndex((row) => row.routine_id === payload.routine_id && row.date === today);
      if (index >= 0) completions.splice(index, 1);
      else completions.push({ date: today, routine_id: payload.routine_id });
      return json(route, body());
    }
    if (path.startsWith("/stretch/spots/") && method === "DELETE") {
      const region = decodeURIComponent(path.split("/").pop() || "");
      const found = spots.find((spot) => spot.region === region);
      if (found) found.cleared = true;
      return json(route, body());
    }
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("tapping a region adds its stretches, sharp pain does not, and Done sticks", async ({ page }) => {
  await install(page);
  await page.goto("/stretch");
  await expect(page.getByRole("heading", { name: "Stretching", exact: true })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Pages" }).getByRole("link", { name: "Training" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(page.getByRole("navigation", { name: "Training" }).getByRole("link", { name: "Stretching" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  const todayPlan = prescribe({
    today,
    session: season.plan.sessions[0],
    sessions: season.plan.sessions,
  });
  const warmup = todayPlan.routines[0]?.routine.name || "";
  const cooldown = todayPlan.routines[1]?.routine.name || "";
  const prescription = page.getByTestId("stretch-prescription");
  await expect(prescription.getByRole("heading", { name: warmup })).toBeVisible();
  await expect(prescription.getByRole("heading", { name: cooldown })).toBeVisible();
  await expect(page.locator("img")).toHaveCount(0);
  await expect(prescription.locator("svg")).toHaveCount(0);
  await expect(page.getByTestId("stretch-library").locator("svg")).toHaveCount(0);
  await expect(page.getByTestId("body-front")).toBeAttached();

  const neck = page.getByRole("button", { name: "Neck, front view" });
  await neck.focus();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Sharp pain / getting worse" }).click();
  await expect(prescription.getByText("Stop stretching that area")).toBeVisible();
  await expect(prescription.getByRole("heading", { name: "Extra for sore spots" })).toHaveCount(0);

  await page.getByRole("button", { name: "Calves / Achilles, back view" }).locator("path").first().click();
  await page.getByRole("button", { name: "Moderate", exact: true }).click();
  const extras = page.getByTestId("stretch-extras");
  await expect(extras.getByRole("heading", { name: "Wall calf stretch, straight knee" })).toBeVisible();
  await expect(extras.getByRole("heading", { name: "Wall calf stretch, bent knee/soleus" })).toBeVisible();
  await expect(extras.getByRole("heading", { name: "Downward dog calf pedal" })).toBeVisible();
  await expect(prescription.getByRole("heading", { name: "Extra for sore spots" })).toBeVisible();

  await page.getByTestId("stretch-library").getByRole("button", { name: "Hamstrings", exact: true }).click();
  await page.getByRole("button", { name: "Static", exact: true }).click();
  await expect(page.getByTestId("stretch-library").getByRole("heading", { name: "Lying strap hamstring stretch" })).toBeVisible();
  await expect(page.getByTestId("stretch-library").getByRole("heading", { name: "Leg swings front-back" })).toHaveCount(0);

  await page.getByRole("button", { name: `Mark ${warmup} done` }).click();
  await expect(page.getByRole("button", { name: `${warmup} done` })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByTestId("stretch-week")).toHaveText("1 routine done this week · 1-day streak");
  await expect(page.getByText("What this means")).toBeVisible();
});
