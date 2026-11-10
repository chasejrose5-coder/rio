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
    easy_pace: "7:25",
    easy_pace_unit: "mi",
    easy_pace_phrase: "7:25 per mile",
    intro_seen: true,
    no_watch: false,
    units: "miles",
    pace_units: "mi",
    date_format: "short",
    show_ids: false,
    compact: false,
  },
};

type MockProfile = {
  ready: boolean;
  fields: { label: string; value: string }[];
  profile_key: string;
  goal_time: string;
  goal_override: string | null;
  shown_goal: string;
  inputs?: {
    current_time: string;
    start_date: string;
    goal_time: string;
    goal_date: string;
  };
  easy_pace: string;
  easy_pace_unit: string;
  easy_pace_phrase: string;
  prefs: { date_format: string; compact: boolean };
};

const seasonProfile: MockProfile = {
  ready: true,
  fields: [
    { label: "Current 800 time", value: "2:02.9" },
    { label: "Start date", value: "2026-04-19" },
    { label: "Goal 800m time", value: "1:55.0" },
    { label: "Goal date", value: "2027-03-19" },
  ],
  profile_key: "rio.profile.v1\n2:02.9\n2026-04-19\n1:55.0\n2027-03-19",
  goal_time: "1:55.0",
  goal_override: null,
  shown_goal: "1:55.0",
  inputs: {
    current_time: "2:02.9",
    start_date: "2026-04-19",
    goal_time: "1:55.0",
    goal_date: "2027-03-19",
  },
  easy_pace: "7:25",
  easy_pace_unit: "mi",
  easy_pace_phrase: "7:25 per mile",
  prefs: { date_format: "short", compact: false },
};

function emptyProfile(): MockProfile {
  return {
    ready: false,
    fields: [],
    profile_key: "",
    goal_time: "",
    goal_override: null,
    shown_goal: "",
    easy_pace: "7:25",
    easy_pace_unit: "mi",
    easy_pace_phrase: "7:25 per mile",
    prefs: { date_format: "iso", compact: false },
  };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(
  page: Page,
  options: { fail?: string; empty?: boolean; blank?: boolean } = {},
) {
  let profile: MockProfile = options.empty ? emptyProfile() : structuredClone(seasonProfile);
  if (options.blank && profile.ready) {
    profile.fields = profile.fields.map((field) =>
      field.label === "Current 800 time" ? { ...field, value: "" } : field,
    );
  }
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/me") return json(route, athlete);
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/profile" && route.request().method() === "GET") {
      if (options.fail) return json(route, { detail: options.fail }, 500);
      return json(route, profile);
    }
    if (path === "/profile/goal" && route.request().method() === "PUT") {
      const body = route.request().postDataJSON() as { goal_time?: string };
      if (!body.goal_time || body.goal_time === "nope") {
        return json(route, { detail: "goal_time is not an 800 time" }, 400);
      }
      profile = {
        ...profile,
        goal_override: body.goal_time,
        shown_goal: body.goal_time,
        fields: profile.fields.map((field) =>
          field.label === "Goal 800m time" ? { ...field, value: body.goal_time || "" } : field,
        ),
      };
      return json(route, profile);
    }
    if (path === "/settings" && route.request().method() === "PATCH") {
      const body = route.request().postDataJSON() as { easy_pace?: string; easy_pace_unit?: string };
      if (!body.easy_pace || !/^\d{1,2}:[0-5]\d$/.test(body.easy_pace)) {
        return json(route, { detail: "Enter a pace like 7:25." }, 400);
      }
      const phrase = `${body.easy_pace} ${body.easy_pace_unit === "km" ? "per kilometer" : "per mile"}`;
      profile = { ...profile, easy_pace: body.easy_pace, easy_pace_unit: body.easy_pace_unit || "mi", easy_pace_phrase: phrase };
      return json(route, {
        ...athlete,
        prefs: { ...athlete.prefs, easy_pace: body.easy_pace, easy_pace_unit: body.easy_pace_unit, easy_pace_phrase: phrase },
      });
    }
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("the four values, a saved goal, a bad time, and a new easy pace", async ({ page }) => {
  await install(page, { blank: true });
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Profile", exact: true })).toBeVisible();
  await expect(page.getByText("SYNTHETIC")).toHaveCount(0);
  await expect(page.getByText("DEMO")).toHaveCount(0);
  await expect(page.locator("img")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();
  await expect(page.getByText("Saved: 7:25 per mile. You can change it here.")).toBeVisible();
  await expect(page.getByText("Quality workouts stay on your 800.")).toBeVisible();
  await expect(page.getByText("Four values from Start.")).toBeVisible();
  await expect(page.getByText("Current 800 time")).toBeVisible();
  await expect(page.getByText("—", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("Apr 19, 2026")).toBeVisible();
  await expect(page.getByText("Mar 19, 2027")).toBeVisible();
  await expect(page.getByLabel("Goal 800m time")).toHaveValue("1:55.0");
  await expect(page.getByLabel("Goal 800m time")).toHaveAttribute("placeholder", "1:55.0");
  await expect(page.getByText("Minutes, seconds, and tenths, like 1:55.0.")).toBeVisible();
  await expect(page.getByText("Saving keeps this time on your account. It does not rebuild the season.")).toBeVisible();
  const current = page.getByText("Current 800 time");
  await expect(page.locator("input").filter({ hasText: "Current 800 time" })).toHaveCount(0);
  await expect(current).toBeVisible();

  await page.getByLabel("Goal 800m time").fill("nope");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByText("goal_time is not an 800 time")).toBeVisible();
  await expect(page.getByText("Saved for this account.")).toHaveCount(0);

  await page.getByLabel("Goal 800m time").fill("1:54.0");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByText("Saved for this account.")).toBeVisible();
  await expect(page.getByLabel("Goal 800m time")).toHaveValue("1:54.0");
  await page.reload();
  await expect(page.getByLabel("Goal 800m time")).toHaveValue("1:54.0");
  await expect(page.getByText("Saved for this account.")).toBeVisible();

  await page.getByLabel("Easy pace").fill("5:00");
  await page.getByRole("radio", { name: "per kilometer" }).check();
  await page.getByRole("button", { name: "Save easy pace" }).click();
  await expect(page.getByText("Saved: 5:00 per kilometer. You can change it here.")).toBeVisible();

  const label = page.locator(".rio-mark-label").first();
  const color = await label.evaluate((el) => getComputedStyle(el).color);
  expect(color).toBe("rgb(60, 58, 54)");
});

test("no season shows easy pace and the way to Start", async ({ page }) => {
  await install(page, { empty: true });
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();
  await expect(page.getByText("Saved: 7:25 per mile. You can change it here.")).toBeVisible();
  await expect(page.getByText("Generate a season on Start.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Generate season plan" })).toHaveAttribute("href", "/start");
  await expect(page.getByText("Current 800 time")).toHaveCount(0);
  await expect(page.getByLabel("Goal 800m time")).toHaveCount(0);
  await expect(page.getByText("1:55.0")).toHaveCount(0);
});

test("a failed profile is the error, not a fake season", async ({ page }) => {
  await install(page, { fail: "profile <broken>" });
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Profile", exact: true })).toBeVisible();
  await expect(page.getByText("profile <broken>")).toBeVisible();
  await expect(page.locator(".rio-error b")).toHaveCount(0);
  await expect(page.getByText("Generate a season on Start.")).toHaveCount(0);
  await expect(page.getByText("Current 800 time")).toHaveCount(0);
  await expect(page.getByText("1:55.0")).toHaveCount(0);
});

test("the More menu lists the five pages", async ({ page }) => {
  await install(page);
  await page.goto("/more");
  await expect(page.getByRole("heading", { name: "More", exact: true })).toBeVisible();
  await expect(page.getByText("The rest of the season, still in this tab.")).toBeVisible();
  await expect(page.getByText("Coming in the next step.")).toHaveCount(0);
  await expect(page.locator("img")).toHaveCount(0);
  const cards = page.locator(".rio-more-list");
  await expect(cards.getByText("Seasons you have already saved.")).toBeVisible();
  await expect(cards.getByText("Your current 800, goal, and dates.")).toBeVisible();
  await expect(cards.getByText("Name, pace, and this account.")).toBeVisible();
  await expect(cards.getByText("Phases, the 10% rule, and what a mark changes.")).toBeVisible();
  await expect(cards.getByText("Chase Rose, Founder.")).toBeVisible();
  await expect(cards.getByRole("link", { name: /Past seasons/ })).toHaveAttribute("href", "/past-seasons");
  await expect(cards.getByRole("link", { name: /Profile/ })).toHaveAttribute("href", "/profile");
  await expect(cards.getByRole("link", { name: /Settings/ })).toHaveAttribute("href", "/settings");
  await expect(cards.getByRole("link", { name: /About/ })).toHaveAttribute("href", "/about");
  await expect(cards.getByRole("link", { name: /Creators/ })).toHaveAttribute("href", "/creators");
  const sub = page.getByRole("navigation", { name: "More" });
  await expect(sub.getByRole("link", { name: "Profile" })).toHaveAttribute("href", "/profile");
  await cards.getByRole("link", { name: /Past seasons/ }).click();
  await expect(page.getByRole("heading", { name: "Past seasons" })).toBeVisible();
  await expect(page.getByText("Coming in the next step.")).toBeVisible();
});
