import { expect, test, type Page, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-10",
  prefs: {
    easy_pace: "",
    easy_pace_unit: "mi",
    intro_seen: true,
    units: "miles",
    pace_units: "mi",
    usual_long_m: null as number | null,
    usual_long_note: "",
  },
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(page: Page) {
  const sent: unknown[] = [];
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    const method = route.request().method();
    if (path === "/auth/me" || path === "/auth/session") return json(route, { ...athlete, signed_in: true });
    if (path === "/seasons/current") return json(route, { detail: "No current season." }, 404);
    if (path === "/settings" && method === "PATCH") {
      const body = route.request().postDataJSON() as { usual_long_m?: number; pace_units?: string };
      sent.push(body);
      if (body.usual_long_m === 1000) return json(route, { detail: "Enter a distance between 2 and 26 mi." }, 400);
      athlete.prefs.usual_long_m = body.usual_long_m ?? null;
      athlete.prefs.usual_long_note = "";
      return json(route, athlete);
    }
    if (path === "/seasons" && method === "POST") {
      const body = route.request().postDataJSON();
      sent.push(body);
      return json(route, {
        inputs: body,
        committed: true,
        plan: { ontology_version: "v0.1", long_run_start_m: 11000, sessions: [] },
        strava_offer: false,
      });
    }
    if (path === "/home") {
      return json(route, {
        today: athlete.today,
        athlete,
        hello: "Hey, Ada",
        strava_offer: false,
        copy: "",
        season: null,
      });
    }
    if (path === "/profile") {
      return json(route, {
        ready: false,
        fields: [],
        easy_pace: "",
        easy_pace_phrase: "",
        usual_long_m: athlete.prefs.usual_long_m,
        usual_long_note: "",
        usual_long_locked: false,
        prefs: { units: "miles", date_format: "iso", compact: false },
      });
    }
    return json(route, { detail: "Not mocked." }, 404);
  });
  return sent;
}

test("easy pace, Start, and Profile ask for the usual long run", async ({ page }) => {
  const sent = await install(page);
  await page.goto("/easy-pace");
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();
  await expect(page.getByLabel("Usual long run")).toBeVisible();
  await expect(page.getByText(/builds 500 m a week up to 20 km/)).toBeVisible();
  await page.getByLabel("Easy pace").fill("7:45");
  await page.getByLabel("Usual long run").fill("8");
  await page.getByRole("button", { name: "Save easy pace" }).click();
  await expect.poll(() => sent.length).toBeGreaterThan(0);
  expect(sent[0]).toMatchObject({ easy_pace: "7:45", easy_pace_unit: "mi", usual_long_m: 12875, pace_units: "mi" });

  await page.goto("/start");
  await expect(page.getByLabel("Usual long run (mi)")).toHaveValue("8");
  await page.getByLabel("Your 800 m time today").fill("2:05.00");
  await page.getByLabel("800 m time you're aiming for").fill("1:58.00");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect.poll(() => sent.length).toBe(2);
  expect(sent[1]).toMatchObject({ usual_long_m: 12875, current_time: "2:05.00" });

  await page.goto("/profile");
  await expect(page.getByLabel("Usual long run (mi)")).toHaveValue("8");
  await page.getByLabel("Easy pace").fill("7:45");
  await page.getByLabel("Usual long run (mi)").fill("1");
  await page.getByRole("button", { name: "Save easy pace" }).click();
  await expect(page.getByText("Enter a distance between 2 and 26 mi.")).toBeVisible();
});

test("an open season keeps the usual long run read-only", async ({ page }) => {
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/me") return json(route, { ...athlete, prefs: { ...athlete.prefs, usual_long_m: 12875 } });
    if (path === "/profile") {
      return json(route, {
        ready: true,
        fields: [
          { label: "Current 800 time", value: "2:05.0" },
          { label: "Start date", value: "2026-11-10" },
          { label: "Goal 800m time", value: "1:58.0" },
          { label: "Goal date", value: "2027-04-10" },
        ],
        shown_goal: "1:58.0",
        goal_time: "1:58.0",
        easy_pace: "7:45",
        easy_pace_unit: "mi",
        easy_pace_phrase: "7:45 per mile",
        usual_long_m: 12875,
        usual_long_note: "",
        usual_long_locked: true,
        prefs: { units: "miles", date_format: "iso", compact: false },
      });
    }
    if (path === "/settings") return json(route, { detail: "Your usual long run applies when you start your next season." }, 400);
    return json(route, { detail: "Not mocked." }, 404);
  });
  await page.goto("/profile");
  const field = page.getByLabel("Usual long run (mi)");
  await expect(field).toHaveValue("8");
  await expect(field).toHaveAttribute("readonly", "");
  await expect(page.getByText("You can change your usual long run when you start your next season.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save easy pace" })).toBeVisible();
});
