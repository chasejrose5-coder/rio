import { expect, test, type Page, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-09",
  next_session: "2026-11-10",
  prefs: { easy_pace: "7:45", easy_pace_unit: "mi", intro_seen: true, no_watch: false, confirm_adapt: true },
};

function sessionBody(kind: "quality" | "easy" | "done") {
  const quality = kind === "quality";
  return {
    date: quality || kind === "done" ? "2026-11-10" : "2026-11-12",
    session: {
      date: quality || kind === "done" ? "2026-11-10" : "2026-11-12",
      day_of_week: quality || kind === "done" ? "Tuesday" : "Thursday",
      template_id: quality || kind === "done" ? "se_400_r90_x6" : "aer_8000_r0_x1",
      week_number: 1,
    },
    actual: null,
    quality: quality || kind === "done",
    note: kind === "quality" ? { headline: "On track today", body: "Leave the next week as written.", carry_forward: "Same effort next time." } : null,
    viewed: false,
    digest: "digest-1",
    label: quality || kind === "done" ? "6 × 400 m near goal 800 pace, 90 s rest" : "8 km easy, Zone 2",
    structure: quality || kind === "done" ? "6 × 400 m, 90 s rest" : "One continuous easy run, planned 8000 m.",
    target: "Hit the session.",
    reasons: ["Phase 4", "Primary work for this phase"],
    shown_date: quality || kind === "done" ? "2026-11-10" : "2026-11-12",
    prescription:
      quality || kind === "done"
        ? { line: "6 × 400 m @ 71.2 s, 90 s rest", tolerance: "68.0-74.4 s", block: "12:06.0", average: "71.2 s" }
        : { line: "Run at 7:45 per mile", tolerance: "", block: "", average: "" },
    logging: kind === "done" ? "done" : "times",
    confirm_adapt: true,
    show_id: false,
    boxes: quality ? 6 : 0,
    seed: quality ? [null, null, null, null, null, null] : [],
    summary: "",
    match: quality ? { reps: "70, 71", work: "2,400 m", heart_rate: "150 bpm" } : null,
    heart_rate: "",
  };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(page: Page, options: { session?: "quality" | "easy" | "done" | "missing" | "bad"; role?: string; posted?: { count: number } }) {
  let signed = false;
  let viewed = false;
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/me") {
      if (!signed) return json(route, { detail: "Sign in again." }, 401);
      return json(route, { ...athlete, role: options.role || "athlete" });
    }
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/auth/sign-in") {
      signed = true;
      return json(route, { email: athlete.email, display_name: athlete.display_name, kind: "local" });
    }
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/home") {
      return json(route, { today: athlete.today, athlete, hello: "Hey Ada", strava_offer: false, copy: "", season: null, next_session: athlete.next_session });
    }
    if (path === "/seasons/current") {
      if (options.session === "missing") return json(route, { detail: "No current season." }, 404);
      return json(route, { today: athlete.today, inputs: {}, digest: "digest-1" });
    }
    if (path.startsWith("/sessions/")) {
      if (options.session === "missing") return json(route, { detail: "No current season." }, 404);
      if (options.session === "bad") return json(route, { detail: "That day is not in this season." }, 404);
      const body = sessionBody(options.session || "quality");
      if (viewed) body.viewed = true;
      return json(route, body);
    }
    if (path === "/activities") {
      return json(route, {
        rows: [],
        all: [],
        logged: [{ id: "extra-1", date: "2026-11-11", name: "Shakeout", matched: false, reps: "300", volume: "3 km", heart_rate: "140 bpm" }],
      });
    }
    if (path === "/seasons/current/results") {
      if (options.posted) options.posted.count += 1;
      return json(route, { committed: true, digest: "digest-2", insight: { status: "skipped" }, inputs: {} });
    }
    if (path === "/seasons/current/notes") {
      viewed = true;
      return json(route, { note_saved: true });
    }
    if (path === "/seasons/current/watchless") return json(route, { committed: true, insight: { status: "skipped" } });
    if (path === "/fixtures/intervals") return json(route, { detail: "That page is for the admin account." }, 403);
    return json(route, { detail: "Not mocked." }, 404);
  });
}

async function signIn(page: Page) {
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
}

test("a session with no plan, no date, or a bad date has no result form", async ({ page }) => {
  await install(page, { session: "missing" });
  await signIn(page);
  await page.goto("/session?date=2026-11-10");
  await expect(page.getByText("Generate a season on Start.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Generate season plan" })).toBeVisible();
  await expect(page.getByLabel("Rep 1")).toHaveCount(0);

  await page.goto("/session");
  await expect(page.getByText("Open a workout from Home or Plan.")).toBeVisible();
  await expect(page.getByLabel("Rep 1")).toHaveCount(0);
});

test("a bad date does not open the result form", async ({ page }) => {
  await install(page, { session: "bad" });
  await signIn(page);
  await page.goto("/session?date=1999-01-01");
  await expect(page.getByText("That session is not in this plan.")).toBeVisible();
  await expect(page.getByText("Result")).toHaveCount(0);
});

test("a quality day states the rep time, the average, and asks before it saves", async ({ page }) => {
  const posted = { count: 0 };
  await install(page, { session: "quality", posted });
  await signIn(page);
  await page.goto("/session?date=2026-11-10");
  await expect(page.getByRole("heading", { name: "Tuesday" })).toBeVisible();
  await expect(page.getByText("6 × 400 m near goal 800 pace, 90 s rest")).toBeVisible();
  await expect(page.getByText("6 × 400 m @ 71.2 s, 90 s rest")).toBeVisible();
  await expect(page.getByText("Average 71.2 s")).toBeVisible();
  await expect(page.getByText("Tolerance 68.0-74.4 s")).toBeVisible();
  await expect(page.getByText("Block 12:06.0")).toBeVisible();
  await expect(page.getByText("Pre-warm-up")).toBeVisible();
  await expect(page.getByText("1 × 800 m easy")).toBeVisible();
  await expect(page.getByText("Warm-up", { exact: true })).toBeVisible();
  await expect(page.getByText("Cool-down")).toBeVisible();
  await expect(page.getByText("Core")).toBeVisible();
  await expect(page.getByText("Intervals")).toBeVisible();
  await expect(page.getByText("Primary work for this phase")).toBeVisible();
  await expect(page.getByText("phase_4")).toHaveCount(0);
  await expect(page.getByLabel("Intervals file")).toHaveCount(0);
  await expect(page.getByText("On track today")).toBeVisible();
  await page.getByRole("button", { name: "Got it" }).click();
  await expect(page.getByText("On track today")).toHaveCount(0);
  await expect(page.getByText("Times save as you type.")).toBeVisible();
  await page.getByLabel("Rep 1").fill("70");
  await expect(page.getByText("Confirm this result before the plan changes.")).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect.poll(() => posted.count).toBe(0);
  await page.getByLabel("Rep 1").fill("71");
  await expect(page.getByText("Confirm this result before the plan changes.")).toBeVisible();
  await page.getByRole("button", { name: "Confirm" }).click();
  await expect.poll(() => posted.count).toBe(1);
});

test("an easy run uses the saved pace and does not ask for a rep time", async ({ page }) => {
  await install(page, { session: "easy" });
  await signIn(page);
  await page.goto("/session?date=2026-11-12");
  await expect(page.getByText("Run at 7:45 per mile")).toBeVisible();
  await expect(page.getByText("1.55")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Behind" })).toHaveCount(0);
  await expect(page.getByLabel("Rep 1")).toHaveCount(0);
  await expect(page.getByText("Result")).toHaveCount(0);
});

test("no-watch shows Done and the confirm dialog only when a time is entered", async ({ page }) => {
  await install(page, { session: "done" });
  await signIn(page);
  await page.goto("/session?date=2026-11-10");
  await expect(page.getByRole("button", { name: "Done" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Couldn't finish" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Add a time" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Behind" })).toBeVisible();
  await page.getByRole("button", { name: "Done" }).click();
  await expect(page.getByText("Choose behind, on target, or ahead.")).toBeVisible();
  await page.getByRole("button", { name: "On target" }).click();
  await page.getByRole("button", { name: "Add a time" }).click();
  await page.getByLabel("Time").fill("1:12.4");
  await page.getByRole("button", { name: "Done" }).click();
  await expect(page.getByText("Confirm this workout before the plan changes.")).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByText("Confirm this workout before the plan changes.")).toHaveCount(0);
});

test("an extra activity has no Done form", async ({ page }) => {
  await install(page, { session: "quality" });
  await signIn(page);
  await page.goto("/session?activity=extra-1");
  await expect(page.getByRole("heading", { name: "Wednesday" })).toBeVisible();
  await expect(page.getByRole("main").getByText("Activity", { exact: true })).toBeVisible();
  await expect(page.getByText("Shakeout")).toBeVisible();
  await expect(page.getByRole("button", { name: "Done" })).toHaveCount(0);
  await expect(page.getByText("Result")).toHaveCount(0);
});
