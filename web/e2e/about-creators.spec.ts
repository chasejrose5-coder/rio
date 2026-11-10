import { expect, test, type Page, type Route } from "@playwright/test";
import { ABOUT } from "../lib/about-copy";
import { CREATORS } from "../lib/creators-copy";

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

async function install(page: Page, options: { compact?: boolean } = {}) {
  const user = structuredClone(athlete);
  if (options.compact) user.prefs.compact = true;
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/me") return json(route, user);
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    return json(route, { detail: "Not mocked." }, 404);
  });
}

function aboutVisible(): string[] {
  const lines: string[] = [ABOUT.heading, ABOUT.credit];
  for (const section of ABOUT.sections) {
    lines.push(section.title, ...section.visible);
    for (const row of section.rows) lines.push(row.label, row.line);
    lines.push(...section.closing);
  }
  return lines;
}

test("about shows the stadium photo, the credit, and the eight phases", async ({ page }) => {
  await install(page);
  await page.goto("/about");
  await expect(page.getByRole("heading", { name: "About", exact: true })).toBeVisible();
  await expect(page.getByText("Coming in the next step.")).toHaveCount(0);
  await expect(page.getByText("SYNTHETIC")).toHaveCount(0);
  await expect(page.getByText("probability")).toHaveCount(0);
  await expect(page.getByText(ABOUT.credit)).toBeVisible();
  const photo = await page.locator(".rio-about-banner").evaluate((el) => getComputedStyle(el).backgroundImage);
  expect(photo).toContain("/photos/about");
  expect(photo).not.toContain("chase-blocks");
  expect(photo).not.toContain("home-aerial");
  await expect(page.locator(".page-about .rio-index")).toHaveCount(0);
  await expect(page.locator(".page-about .rio-about-title h1")).toHaveCSS("color", "rgb(244, 241, 236)");
  await expect(page.locator(".page-about .rio-photo-credit")).toHaveCSS("color", "rgb(244, 241, 236)");
  await expect(page.locator(".page-about .rio-mark-label").first()).toHaveCSS("color", "rgb(60, 58, 54)");
  await expect(page.locator(".page-about .rio-k").first()).toHaveCSS("color", "rgb(60, 58, 54)");
  await expect(page.locator(".page-about .rio-note").first()).toHaveCSS("color", "rgb(18, 17, 16)");
  await expect(page.getByRole("navigation", { name: "More" }).getByRole("link", { name: "About" })).toHaveAttribute("href", "/about");

  const visible = await page.locator(".page-about").evaluate((root) => {
    const nodes = root.querySelectorAll(".rio-index, h1, .rio-photo-credit, .rio-mark-label, .rio-note, .rio-prose, .rio-k, .rio-v");
    return Array.from(nodes)
      .filter((node) => !node.closest("[hidden]"))
      .map((node) => (node.textContent || "").trim());
  });
  expect(visible).toEqual(aboutVisible());
  const hidden = await page.locator(".page-about [hidden] .rio-prose").allTextContents();
  expect(hidden.map((line) => line.trim())).toEqual(ABOUT.sections.flatMap((section) => [...section.hidden]));
  const hiddenBlocks = page.locator(".page-about [hidden]");
  await expect(hiddenBlocks).toHaveCount(3);
  for (const block of await hiddenBlocks.all()) {
    await expect(block).toBeHidden();
  }
  await expect(page.getByText("Those calls stop once recorded spend reaches $25.")).toBeHidden();
  await expect(page.getByText("The short fast reps step up from phase 1.")).toBeVisible();
  await expect(page.getByText("The taper stays fresh. No hard speed endurance or anaerobic work.")).toBeVisible();
  await expect(page.locator(".page-about .rio-field")).toHaveCount(8);
  await expect(page.getByText("chasejrose5@gmail.com")).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.sessionStorage.getItem("rio-motion-page"))).toBe("about");
});

test("creators shows Chase and keeps the Jay Rose placeholder in a comment", async ({ page }) => {
  await install(page);
  await page.goto("/creators");
  await expect(page.getByRole("heading", { name: CREATORS.heading })).toBeVisible();
  await expect(page.getByRole("heading", { name: CREATORS.name })).toBeVisible();
  await expect(page.getByText("Coming in the next step.")).toHaveCount(0);
  await expect(page.getByText("Photo by")).toHaveCount(0);
  await expect(page.getByText("SYNTHETIC")).toHaveCount(0);
  const img = page.locator(".rio-creator-photo img");
  await expect(img).toHaveAttribute("alt", CREATORS.alt);
  await expect(img).toHaveAttribute("src", "/photos/chase-blocks.jpg");
  const visible = await page.locator(".page-creators").evaluate((root) => {
    const nodes = root.querySelectorAll(".rio-synthetic, h1, .rio-creator-name, .rio-creator-bio, .rio-creator-close");
    return Array.from(nodes).map((node) => (node.textContent || "").trim());
  });
  expect(visible).toEqual([CREATORS.banner, CREATORS.heading, CREATORS.name, ...CREATORS.paragraphs, CREATORS.close]);
  const text = await page.locator(".page-creators").innerText();
  expect(text).not.toContain("Jay Rose");
  expect(text).not.toContain("Editable placeholder");
  expect(text).not.toContain("Bio coming soon");
  const html = await page.content();
  expect(html).toContain(CREATORS.comment);
  await expect(page.locator(".page-creators .rio-synthetic")).toHaveCSS("color", "rgb(226, 90, 50)");
  await expect(page.locator(".page-creators .rio-hero h1")).toHaveCSS("color", "rgb(244, 241, 236)");
  await expect(page.locator(".rio-creator-name")).toHaveCSS("color", "rgb(18, 17, 16)");
  await expect(page.locator(".rio-creator-bio").first()).toHaveCSS("color", "rgb(18, 17, 16)");
  await expect(page.locator(".rio-creator-close")).toHaveCSS("color", "rgb(226, 90, 50)");
  await expect(page.getByText("Every rep has a reason.")).toBeVisible();
  await expect(page.getByText("chasejrose5@gmail.com")).toBeVisible();
});

test("More opens About and Creators", async ({ page }) => {
  await install(page);
  await page.goto("/more");
  await page.locator(".rio-more-list").getByRole("link", { name: /About/ }).click();
  await expect(page).toHaveURL(/\/about$/);
  await expect(page.getByRole("heading", { name: "About", exact: true })).toBeVisible();
  await expect(page.getByText("Eight phases")).toBeVisible();
  await page.getByRole("navigation", { name: "More" }).getByRole("link", { name: "Creators" }).click();
  await expect(page).toHaveURL(/\/creators$/);
  await expect(page.getByRole("heading", { name: "Built by a runner, for runners." })).toBeVisible();
  await expect(page.locator(".page-creators").getByText("Photo by")).toHaveCount(0);
});

test("compact mode keeps the creators hero smaller", async ({ page }) => {
  await install(page, { compact: true });
  await page.goto("/creators");
  await expect(page.locator(".page-creators")).toHaveClass(/is-compact/);
  await expect(page.locator(".page-creators .rio-hero h1")).toHaveCSS("font-size", "37.6px");
});
