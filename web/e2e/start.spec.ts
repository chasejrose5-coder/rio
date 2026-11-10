import { expect, test, type Page, type Route } from "@playwright/test";
import { monthsLater } from "../lib/start-form";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-10",
  prefs: { easy_pace: "7:45", easy_pace_unit: "mi", intro_seen: true, start_date: "sunday", no_watch: false },
};

const saved = {
  today: "2026-11-10",
  inputs: {
    current_time: "2:05.0",
    start_date: "2026-11-10",
    goal_time: "1:58.0",
    goal_date: "2027-04-10",
  },
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function laDate(): Promise<string> {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Los_Angeles",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

test("sunday start, generate errors, a scored plan, and a failed link stay on Start", async ({ page }) => {
  let stored = saved.inputs;
  let dismissed = false;
  let failSave = false;
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    const method = route.request().method();
    if (path === "/auth/me") return json(route, athlete);
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/seasons/current") {
      return json(route, { ...saved, inputs: stored });
    }
    if (path === "/seasons" && method === "POST") {
      const body = route.request().postDataJSON() as {
        current_time: string;
        start_date: string;
        goal_time: string;
        goal_date: string;
        score?: boolean;
      };
      if (failSave) return json(route, { detail: "This account could not be saved." }, 400);
      if (body.current_time === "score") {
        return json(route, { inputs: body, committed: true, plan: { probability: 0.2 }, strava_offer: false });
      }
      const problem = problemFor(body);
      if (problem) return json(route, { detail: problem }, 400);
      stored = body;
      return json(route, { inputs: body, committed: true, plan: { ontology_version: "v0.1", sessions: [] }, strava_offer: !dismissed });
    }
    if (path === "/home") {
      const offer = url.searchParams.get("just_generated") === "true" && !dismissed;
      return json(route, {
        today: athlete.today,
        athlete,
        hello: "Hey, Ada",
        strava_offer: offer,
        copy: "",
        season: {
          inputs: stored,
          digest: "abc",
          view: { days_remaining: 130, phase: "1", mark: null, focus: "—" },
          phase: null,
          pace_status: "No runs yet",
          next: null,
          upcoming: [],
          next_days: [],
          notes: [],
        },
      });
    }
    if (path === "/settings" && method === "PATCH") {
      dismissed = true;
      return json(route, athlete);
    }
    if (path === "/strava/connect") return json(route, { detail: "Strava is not configured." }, 503);
    return json(route, { detail: "Not mocked." }, 404);
  });

  await page.goto("/start");
  await expect(page.getByRole("heading", { name: "Start" })).toBeVisible();
  await expect(page.getByText("Your 800 m time today, the day you start, the time you want, and the race date.")).toBeVisible();
  await expect(page.getByText("SYNTHETIC / DEMO")).toHaveCount(0);
  await expect(page.getByLabel("Your 800 m time today")).toHaveValue("");
  await expect(page.getByLabel("Your 800 m time today")).toHaveAttribute("placeholder", "2:05.0");
  await expect(page.getByText("Your best recent 800 metres, as minutes:seconds.tenths. A rough guess is fine.")).toBeVisible();
  await expect(page.getByLabel("Start date")).toHaveValue("2026-11-15");
  await expect(page.getByText("The day this season starts.")).toBeVisible();
  await expect(page.getByLabel("800 m time you're aiming for")).toHaveValue("");
  await expect(page.getByLabel("800 m time you're aiming for")).toHaveAttribute("placeholder", "1:58.0");
  await expect(page.getByText("The race time you want on your goal date. Same minutes:seconds.tenths format.")).toBeVisible();
  await expect(page.getByLabel("Goal date")).toHaveValue("2027-04-10");
  await expect(page.getByText("The day of the race.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate season plan" })).toBeVisible();
  await expect(page.getByText("Photo by Bohdan Hyrovych on Pexels")).toBeVisible();
  await expect(page.getByRole("link", { name: "Home" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Plan" })).toBeVisible();
  const photo = await page.locator(".page-start").evaluate((el) => getComputedStyle(el).backgroundImage);
  expect(photo).toContain("/photos/start");
  expect(photo).not.toContain("home-aerial");
  expect(photo).not.toContain("startup-track");

  await page.getByLabel("Your 800 m time today").fill("nope");
  await page.getByLabel("800 m time you're aiming for").fill("1:58.0");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page.getByText("current_time is not an 800 time")).toBeVisible();
  await expect(page).toHaveURL(/\/start$/);

  await page.getByLabel("Your 800 m time today").fill("2:05.0");
  await page.getByLabel("800 m time you're aiming for").fill("nope");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page.getByText("goal_time is not an 800 time")).toBeVisible();

  await page.getByLabel("800 m time you're aiming for").fill("1:58.0");
  await page.getByLabel("Goal date").fill("2026-11-01");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page.getByText("goal_date is before start_date")).toBeVisible();

  await page.getByLabel("Start date").fill("not-a-date");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page.getByText("start_date is not a calendar date")).toBeVisible();

  await page.getByLabel("Start date").fill("2026-11-15");
  await page.getByLabel("Goal date").fill("not-a-date");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page.getByText("goal_date is not a calendar date")).toBeVisible();
  const color = await page.locator(".rio-goal-card .rio-error").evaluate((el) => getComputedStyle(el).color);
  expect(color).toBe("rgb(180, 35, 24)");

  await page.getByLabel("Your 800 m time today").fill("score");
  await page.getByLabel("Goal date").fill("2027-04-10");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page.getByText("season plan has a score")).toBeVisible();
  await expect(page).toHaveURL(/\/start$/);

  await page.getByLabel("Your 800 m time today").fill("2:05.0");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page).toHaveURL(/\/home\?/);
  await expect(page).toHaveURL(/just_generated=true/);
  await expect(page.getByRole("heading", { name: "Your plan is ready." })).toBeVisible();
  await expect(page.getByText("Connect Strava so your runs show up.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Connect Strava" })).toBeVisible();
  await page.getByRole("button", { name: "Not now" }).click();
  await expect(page.getByRole("heading", { name: "Your plan is ready." })).toHaveCount(0);
  await page.reload();
  await expect(page.getByText("Your plan is ready.")).toHaveCount(0);

  failSave = true;
  await page.goto("/start?current_time=2:10.0&start_date=2026-12-06&goal_time=1:59.0&goal_date=2027-05-06");
  await expect(page.getByText("This link names a different season. Your saved season was left as it is.")).toBeVisible();
  await page.getByRole("button", { name: "Use this season" }).click();
  await expect(page.getByText("This account could not be saved.")).toBeVisible();
  await expect(page).toHaveURL(/\/start\?/);
  expect(stored.current_time).toBe("2:05.0");

  failSave = false;
  await page.getByRole("button", { name: "Use this season" }).click();
  await expect(page).toHaveURL(/\/home\?/);
  expect(page.url()).not.toContain("just_generated=true");
  expect(stored).toEqual({
    current_time: "2:10.0",
    start_date: "2026-12-06",
    goal_time: "1:59.0",
    goal_date: "2027-05-06",
  });
});

function problemFor(body: { current_time: string; start_date: string; goal_time: string; goal_date: string }): string {
  if (!/^\d+:\d{2}(\.\d+)?$/.test(body.current_time)) return "current_time is not an 800 time";
  if (!/^\d+:\d{2}(\.\d+)?$/.test(body.goal_time)) return "goal_time is not an 800 time";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(body.start_date)) return "start_date is not a calendar date";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(body.goal_date)) return "goal_date is not a calendar date";
  if (body.goal_date < body.start_date) return "goal_date is before start_date";
  return "";
}

test("a brand-new local account generates from Start and can dismiss Strava", async ({ page }) => {
  test.setTimeout(180_000);
  const email = `start-${Date.now()}@example.com`;
  const today = await laDate();
  const goal = monthsLater(today, 5);

  await page.goto("/create-account");
  await expect(page.getByText("Saved on this machine.")).toBeVisible();
  await page.getByLabel("Name").fill("Bea");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct-horse");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");

  const patched = await page.evaluate(async () => {
    const response = await fetch("http://localhost:8000/settings", {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timezone: "America/Los_Angeles" }),
    });
    return response.ok ? response.status : await response.text();
  });
  expect(patched).toBe(200);

  await page.getByLabel("Easy pace").fill("7:45");
  await page.getByRole("button", { name: "Save easy pace" }).click();
  await expect(page.getByRole("heading", { name: "Start here" })).toBeVisible();
  await expect(page.getByText("On Start, enter your 800 m times and choose Generate season plan.")).toBeVisible();
  await expect(page.getByText("In Settings, connect Strava so your runs show up.")).toBeVisible();
  await expect(page.getByText("Open Plan each day and mark how it went.")).toBeVisible();
  await page.getByRole("button", { name: "Done" }).click();

  await expect(page).toHaveURL(/\/start$/);
  await expect(page.getByRole("heading", { name: "Start" })).toBeVisible();
  await expect(page.getByLabel("Your 800 m time today")).toHaveValue("");
  await expect(page.getByLabel("Start date")).toHaveValue(today);
  await expect(page.getByLabel("Goal date")).toHaveValue(goal);
  await expect(page.getByText("Photo by Bohdan Hyrovych on Pexels")).toBeVisible();
  const photo = await page.locator(".page-start").evaluate((el) => getComputedStyle(el).backgroundImage);
  expect(photo).toContain("/photos/start");
  expect(photo).not.toContain("home-aerial");

  await page.getByLabel("Your 800 m time today").fill("nope");
  await page.getByLabel("800 m time you're aiming for").fill("1:58.0");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page.getByText("current_time is not an 800 time")).toBeVisible();
  expect(await currentInputs(page)).toBeNull();

  await page.getByLabel("Your 800 m time today").fill("2:05.0");
  await page.getByLabel("800 m time you're aiming for").fill("nope");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page.getByText("goal_time is not an 800 time")).toBeVisible();

  await page.getByLabel("800 m time you're aiming for").fill("1:58.0");
  await page.getByLabel("Goal date").fill("2020-01-01");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page.getByText("goal_date is before start_date")).toBeVisible();

  await page.getByLabel("Start date").fill("not-a-date");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page.getByText("start_date is not a calendar date")).toBeVisible();

  await page.getByLabel("Start date").fill(today);
  await page.getByLabel("Goal date").fill("not-a-date");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page.getByText("goal_date is not a calendar date")).toBeVisible();
  expect(await currentInputs(page)).toBeNull();

  await page.getByLabel("Goal date").fill(goal);
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page).toHaveURL(/\/home\?/);
  await expect(page).toHaveURL(/just_generated=true/);
  await expect(page).toHaveURL(/current_time=/);
  await expect(page.getByRole("heading", { name: "Your plan is ready." })).toBeVisible();
  await expect(page.getByText("Connect Strava so your runs show up.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Connect Strava" })).toBeVisible();
  await expect(page.getByText("probability")).toHaveCount(0);
  await expect(page.getByText("readiness")).toHaveCount(0);
  const made = await currentInputs(page);
  expect(made).toMatchObject({ current_time: "2:05.0", start_date: today, goal_time: "1:58.0", goal_date: goal });

  await page.getByRole("button", { name: "Not now" }).click();
  await expect(page.getByRole("heading", { name: "Your plan is ready." })).toHaveCount(0);
  await page.reload();
  await expect(page.getByText("Your plan is ready.")).toHaveCount(0);

  const link = new URLSearchParams({
    current_time: "2:10.0",
    start_date: "2026-12-06",
    goal_time: "1:59.0",
    goal_date: "2027-05-06",
  });
  await page.goto(`/start?${link.toString()}`);
  await expect(page.getByText("This link names a different season. Your saved season was left as it is.")).toBeVisible();
  expect(await currentInputs(page)).toMatchObject({ current_time: "2:05.0", goal_time: "1:58.0" });
  await page.getByRole("button", { name: "Use this season" }).click();
  await expect(page).toHaveURL(/\/home\?/);
  expect(page.url()).not.toContain("just_generated=true");
  expect(await currentInputs(page)).toMatchObject({
    current_time: "2:10.0",
    start_date: "2026-12-06",
    goal_time: "1:59.0",
    goal_date: "2027-05-06",
  });

  await page.goto("/start");
  await page.getByLabel("Your 800 m time today").fill("2:08.0");
  await page.getByLabel("800 m time you're aiming for").fill("1:57.0");
  await page.getByRole("button", { name: "Generate season plan" }).click();
  await expect(page).toHaveURL(/just_generated=true/);
  await expect(page.getByText("Your plan is ready.")).toHaveCount(0);
});

test("skip on a new account leaves the intro and it stays gone", async ({ page }) => {
  test.setTimeout(90_000);
  const email = `skip-${Date.now()}@example.com`;
  await page.goto("/create-account");
  await page.getByLabel("Name").fill("Cara");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct-horse");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();
  await page.getByLabel("Easy pace").fill("8:00");
  await page.getByLabel("per kilometer").check();
  await page.getByRole("button", { name: "Save easy pace" }).click();
  await expect(page.getByRole("heading", { name: "Start here" })).toBeVisible();
  await page.getByRole("button", { name: "Skip" }).click();
  await expect(page).toHaveURL(/\/start$/);
  await page.goto("/");
  await expect(page).toHaveURL(/\/start$/);
  await expect(page.getByRole("heading", { name: "Start here" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Start" })).toBeVisible();
});

async function currentInputs(page: Page): Promise<Record<string, string> | null> {
  return page.evaluate(async () => {
    const response = await fetch("http://localhost:8000/seasons/current", { credentials: "include" });
    if (response.status === 404) return null;
    if (!response.ok) throw new Error(await response.text());
    const body = (await response.json()) as { inputs: Record<string, string> };
    return body.inputs;
  });
}

test("splash continue opens log in, and a new tab shows it again", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Your Race, Your Plan, Your Result" })).toBeVisible();
  await expect(page.getByText("Photo by Giant Asparagus on Pexels")).toBeVisible();
  await expect(page.getByText("chasejrose5@gmail.com")).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/\/sign-in\?skip=1$/);
  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
  const again = await page.context().newPage();
  await again.goto("/");
  await expect(again.getByRole("button", { name: "Continue" })).toBeVisible();
  await again.close();
});
