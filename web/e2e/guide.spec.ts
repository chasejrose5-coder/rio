import { expect, test, type Page, type Route } from "@playwright/test";
import { GUIDE_LINK, GUIDE_TITLE, PAGE_MEANINGS } from "../lib/guide-copy";

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
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/library") {
      return json(route, {
        count: 1,
        families: [{ id: "aerobic", label: "Aerobic" }],
        workouts: [{ id: "aer_5000_r0_x1", description: "Easy 5 km", capacity: "Aerobic", family: "aerobic", phases: [1] }],
      });
    }
    if (path === "/seasons/current") return json(route, null);
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("the guide explains the season in plain words and stays free of photos", async ({ page }) => {
  await install(page);
  await page.goto("/guide");
  await expect(page.getByRole("heading", { name: GUIDE_TITLE, exact: true })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Pages" }).getByRole("link", { name: "More" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("navigation", { name: "More" }).getByRole("link", { name: "Guide" })).toHaveAttribute("href", "/guide");
  await expect(page.getByRole("navigation", { name: "More" }).getByRole("link", { name: "Guide" })).toHaveAttribute("aria-current", "page");
  const contents = page.getByRole("navigation", { name: "Guide sections" });
  await expect(contents.getByRole("link", { name: "Getting started" })).toHaveAttribute("href", "#getting-started");
  await expect(contents.getByRole("link", { name: "Today's workout" })).toHaveAttribute("href", "#today");
  await expect(contents.getByRole("link", { name: "Paces" })).toHaveAttribute("href", "#paces");
  await expect(contents.getByRole("link", { name: "The week" })).toHaveAttribute("href", "#week");
  await expect(page.getByRole("heading", { name: "Getting started" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Today's workout" })).toBeVisible();
  await page.getByText("Long-run ladder").click();
  await expect(page.getByText("8 km is outside the ladder.")).toBeVisible();
  await page.getByText("The eight phases").click();
  for (const name of ["Admin", "Creators", "Next", "Decisions", "Ledger", "Last Session", "Goal"]) {
    await expect(page.getByRole("heading", { name, exact: true })).toHaveCount(0);
    await expect(contents.getByRole("link", { name, exact: true })).toHaveCount(0);
  }
  await expect(page.locator(".page-guide main").getByText("Creators")).toHaveCount(0);
  await expect(page.getByText("9.5 km").first()).toBeVisible();
  await expect(page.getByText(/steps up 500 m/).first()).toBeVisible();
  await expect(page.getByText(/until 15 km/).first()).toBeVisible();
  await expect(page.getByText(/at most 10%/).first()).toBeVisible();
  await expect(page.getByText("7:25", { exact: false }).first()).toBeVisible();
  await expect(page.locator("img")).toHaveCount(0);
  const article = page.locator(".page-guide section");
  await expect(article.getByText("probability")).toHaveCount(0);
  await expect(article.getByText("Chase")).toHaveCount(0);
  await expect(page.getByText("Coming in the next step.")).toHaveCount(0);
  const meaning = page.locator(".rio-meaning");
  await expect(meaning.getByText("What this means")).toBeVisible();
  await expect(meaning.getByRole("link", { name: GUIDE_LINK })).toHaveAttribute("href", "/guide#getting-started");
});

test("library, plan, and about link their notes to the matching guide section", async ({ page }) => {
  await install(page);
  await page.goto("/library");
  await expect(page.getByRole("heading", { name: "Library", exact: true })).toBeVisible();
  await expect(page.locator("img")).toHaveCount(0);
  const library = page.locator(".rio-meaning");
  await expect(library.getByText(PAGE_MEANINGS.library.sentences[0])).toBeVisible();
  await library.getByRole("link", { name: GUIDE_LINK }).click();
  await expect(page).toHaveURL(/\/guide#pages$/);
  await expect(page.locator("#pages")).toBeVisible();

  await page.goto("/plan");
  await expect(page.locator(".rio-meaning").getByRole("link", { name: GUIDE_LINK })).toHaveAttribute("href", "/guide#pages");
  await expect(page.locator(".rio-meaning").getByText(PAGE_MEANINGS.plan.sentences[0])).toBeVisible();

  await page.goto("/about");
  const about = page.locator(".rio-meaning");
  await expect(about.getByText("What this means")).toBeVisible();
  await expect(about.getByRole("link", { name: GUIDE_LINK })).toHaveAttribute("href", "/guide#phases");
  await expect(page.getByText("Eight phases", { exact: true })).toBeVisible();
  await expect(page.locator(".page-about .rio-field")).toHaveCount(8);
});
