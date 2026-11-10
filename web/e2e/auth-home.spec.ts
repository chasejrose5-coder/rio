import { expect, test, type Page, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-09",
  prefs: { easy_pace: "7:45", easy_pace_unit: "mi", intro_seen: true, no_watch: false },
};

const season = {
  today: "2026-11-09",
  inputs: {
    current_time: "2:02.9",
    start_date: "2026-04-19",
    goal_time: "1:55.0",
    goal_date: "2027-03-19",
  },
};

const home = {
  today: "2026-11-09",
  athlete,
  hello: "Hey, Ada",
  strava_offer: false,
  copy: "",
  season: {
    inputs: season.inputs,
    digest: "abc",
    view: { days_remaining: 130, phase: "4", mark: null, focus: "Speed endurance" },
    phase: {
      collapsed: "This week sits in phase 4, week 1 of 2, because the season still needs speed endurance.",
      panel: {
        headline: "Phase 4 — Speed endurance",
        focus: "Speed endurance takes the lead.",
        days: [{ short: "Tue", role: "hard" }],
        steps: [{ label: "This", text: "Phase 4, Speed endurance" }],
        marks: "Hard-day marks can ease or advance later weeks.",
        note: "",
      },
    },
    pace_status: "No runs yet",
    next: {
      date: "2026-11-10",
      shown_date: "2026-11-10",
      day_of_week: "Tuesday",
      template_id: "se_400_r90_x6",
      label: "6 × 400 m near goal 800 pace, 90 s rest",
      facts: { distance: "400 m", pace: "Near goal 800", rest: "90 s", reps: "6" },
      prescription: { line: "6 × 400 m @ 57.5 s, 90 s rest", tolerance: "55.0-60.0 s", block: "9:15.0" },
    },
    upcoming: [],
    next_days: [
      {
        date: "2026-11-10",
        shown_date: "2026-11-10",
        day_of_week: "Tuesday",
        template_id: "se_400_r90_x6",
        label: "6 × 400 m near goal 800 pace, 90 s rest",
        prescription: { line: "6 × 400 m @ 57.5 s, 90 s rest", tolerance: "", block: "9:15.0" },
      },
      { date: "2026-11-11", shown_date: "2026-11-11", day_of_week: "Wednesday", template_id: "", label: "—" },
      { date: "2026-11-12", shown_date: "2026-11-12", day_of_week: "Thursday", template_id: "", label: "—" },
    ],
    notes: [],
  },
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function installApi(
  page: Page,
  options: { hosted?: boolean; season?: boolean; easyPace?: string; introSeen?: boolean | null; homeBody?: unknown },
) {
  let signed = false;
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/me") {
      if (!signed) return json(route, { detail: "Sign in again." }, 401);
      const pace = options.easyPace === undefined ? "7:45" : options.easyPace;
      const seen = options.introSeen === undefined ? true : options.introSeen;
      return json(route, {
        ...athlete,
        next_session: options.season ? "2026-11-10" : null,
        prefs: { ...athlete.prefs, easy_pace: pace, intro_seen: seen },
      });
    }
    if (path === "/auth/google") {
      if (options.hosted) return json(route, { url: "https://example.test/google", redirect_uri: "http://localhost:3000/" });
      return json(route, { detail: "Accounts are not available." }, 503);
    }
    if (path === "/auth/sign-in") {
      signed = true;
      return json(route, { email: athlete.email, display_name: athlete.display_name, kind: "local" });
    }
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/seasons/current") {
      if (!options.season) return json(route, { detail: "No current season." }, 404);
      return json(route, season);
    }
    if (path === "/home") return json(route, options.homeBody ?? home);
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("local sign-in hides forgot password and Google", async ({ page }) => {
  await installApi(page, { hosted: false, season: false });
  await page.goto("/sign-in");
  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Log in" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Create account" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Forgot password?" })).toHaveCount(0);
  await expect(page.getByText("Accounts aren't set up yet")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Show password" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Google/i })).toHaveCount(0);
  await expect(page.getByText("Photo by Steve Pancrate on Pexels")).toBeVisible();
});

test("hosted sign-in shows forgot password and still hides Google", async ({ page }) => {
  await installApi(page, { hosted: true, season: true });
  await page.goto("/sign-in");
  await expect(page.getByRole("link", { name: "Forgot password?" })).toBeVisible();
  await expect(page.getByText("Accounts aren't set up yet")).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Google/i })).toHaveCount(0);
});

test("create account asks for a name", async ({ page }) => {
  await installApi(page, { hosted: false, season: false });
  await page.goto("/create-account");
  await expect(page.getByRole("heading", { name: "Create account" })).toBeVisible();
  await expect(page.getByLabel("Name")).toBeVisible();
  await expect(page.getByRole("button", { name: "Create account" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to log in" })).toBeVisible();
  await expect(page.getByText("Photo by Steve Pancrate on Pexels")).toBeVisible();
});

test("sign-in with a current season opens Home", async ({ page }) => {
  await installApi(page, { hosted: false, season: true });
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByText("130")).toBeVisible();
  await expect(page.getByText("6 × 400 m @ 57.5 s, 90 s rest").first()).toBeVisible();
  await expect(page.getByText("Block 9:15.0").first()).toBeVisible();
  await expect(page.getByText("Photo by Gaby Lopez on Pexels")).toBeVisible();
  await expect(page.getByText("03  /  Next 3 days")).toBeVisible();
  await expect(page.getByText("Rest day").first()).toBeVisible();
  await expect(page.getByText("Coming in the next step.")).toHaveCount(0);
  await page.goto("/");
  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByRole("button", { name: "Continue" })).toHaveCount(0);
});

test("sign-in without a current season opens Start", async ({ page }) => {
  await installApi(page, { hosted: false, season: false });
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/start$/);
  await expect(page.getByRole("heading", { name: "Start" })).toBeVisible();
  await expect(page.getByLabel("Your 800 m time today")).toHaveValue("");
  await expect(page.getByText("Coming in the next step.")).toHaveCount(0);
});

test("a blank name says Enter a name", async ({ page }) => {
  await installApi(page, { hosted: false, season: false });
  await page.goto("/create-account");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Enter a name.")).toBeVisible();
});

test("local forgot password returns to log in", async ({ page }) => {
  await installApi(page, { hosted: false, season: false });
  await page.goto("/forgot-password");
  await expect(page).toHaveURL(/\/sign-in$/);
});

test("a new account walks easy pace, the intro, then Start", async ({ page }) => {
  let signed = false;
  let pace = "";
  let intro = false;
  const fresh = {
    ...athlete,
    display_name: "Bea",
    email: "bea@example.com",
    prefs: { easy_pace: "", intro_seen: null, no_watch: false },
  };
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    const body = route.request().postDataJSON() as { easy_pace?: string; intro_seen?: boolean } | null;
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/auth/sign-up") {
      signed = true;
      return json(route, { email: fresh.email, display_name: "Bea", kind: "local", confirm: false });
    }
    if (path === "/auth/me") {
      if (!signed) return json(route, { detail: "Sign in again." }, 401);
      return json(route, { ...fresh, prefs: { ...fresh.prefs, easy_pace: pace, intro_seen: intro ? true : null } });
    }
    if (path === "/settings" && route.request().method() === "PATCH") {
      if (body?.easy_pace) pace = String(body.easy_pace);
      if (body?.intro_seen === true) intro = true;
      return json(route, fresh);
    }
    if (path === "/seasons/current") return json(route, { detail: "No current season." }, 404);
    return json(route, { detail: "Not mocked." }, 404);
  });
  await page.goto("/create-account");
  await expect(page.getByText("Saved on this machine.")).toBeVisible();
  await page.getByLabel("Name").fill("Bea");
  await page.getByLabel("Email").fill("bea@example.com");
  await page.getByLabel("Password", { exact: true }).fill("short");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Use at least 8 characters.")).toBeVisible();
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();
  await page.getByLabel("Easy pace").fill("abc");
  await page.getByRole("button", { name: "Save easy pace" }).click();
  await expect(page.getByText("Enter a pace like 7:25.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();
  await page.getByLabel("Easy pace").fill("7:45");
  await page.getByRole("button", { name: "Save easy pace" }).click();
  await expect(page.getByRole("heading", { name: "Start here" })).toBeVisible();
  await expect(page.getByText("Generate season plan.")).toBeVisible();
  await page.getByRole("button", { name: "Done" }).click();
  await expect(page).toHaveURL(/\/start$/);
  await expect(page.getByRole("heading", { name: "Start" })).toBeVisible();
  await expect(page.getByLabel("Your 800 m time today")).toHaveValue("");
  await expect(page.getByText("Photo by Bohdan Hyrovych on Pexels")).toBeVisible();
  await expect(page.getByText("Coming in the next step.")).toHaveCount(0);
});

test("a failed easy-pace save stays on the card", async ({ page }) => {
  let signed = false;
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/auth/sign-in") {
      signed = true;
      return json(route, { email: athlete.email, display_name: athlete.display_name, kind: "local" });
    }
    if (path === "/auth/me") {
      if (!signed) return json(route, { detail: "Sign in again." }, 401);
      return json(route, { ...athlete, prefs: { ...athlete.prefs, easy_pace: "", intro_seen: null } });
    }
    if (path === "/seasons/current") return json(route, { detail: "No current season." }, 404);
    if (path === "/settings") return json(route, { detail: "Easy pace could not be saved." }, 500);
    return json(route, { detail: "Not mocked." }, 404);
  });
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();
  await page.getByLabel("Easy pace").fill("7:45");
  await page.getByRole("button", { name: "Save easy pace" }).click();
  await expect(page.getByText("Easy pace could not be saved.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Start here" })).toHaveCount(0);
});

test("an account with a season and no easy pace stops on easy pace", async ({ page }) => {
  await installApi(page, { hosted: false, season: true, easyPace: "" });
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();
});

test("home shows rest-day copy, extras, the open index, and no-watch controls", async ({ page }) => {
  await installApi(page, {
    hosted: false,
    season: true,
    homeBody: {
      ...home,
      season: {
        ...home.season,
        phase: null,
        logging: "done",
        activities: [{ date: "2026-11-08", name: "Shakeout", id: "x1", matched: false }],
      },
    },
  });
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByText("03  /  Open")).toBeVisible();
  await expect(page.getByText("Extra sessions")).toBeVisible();
  await expect(page.getByText("Shakeout")).toBeVisible();
  await expect(page.getByRole("button", { name: "Done" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Couldn't finish" })).toBeVisible();
  await expect(page.getByRole("button", { name: "On target" })).toBeVisible();
});

test("a current season skips the intro, and intro_seen false shows it again", async ({ page }) => {
  await installApi(page, { hosted: false, season: true, introSeen: null });
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByRole("heading", { name: "Start here" })).toHaveCount(0);
});

test("showing the intro again stops on the guide", async ({ page }) => {
  await installApi(page, { hosted: false, season: true, introSeen: false });
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByRole("heading", { name: "Start here" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Home" })).toHaveAttribute("aria-current", "page");
});

test("start session opens the next planned day after the settings today", async ({ page }) => {
  await installApi(page, { hosted: false, season: true });
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("ada@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByRole("link", { name: "Start session" })).toHaveAttribute("href", "/session?date=2026-11-10");
});
