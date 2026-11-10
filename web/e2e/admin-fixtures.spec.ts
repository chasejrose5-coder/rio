import { rmSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const API = "http://localhost:8000";

async function signIn(page: Page, email: string, name: string) {
  const created = await page.request.post(`${API}/auth/sign-up`, {
    data: { email, password: "correct-horse", name },
  });
  if (created.status() !== 200 && created.status() !== 400) {
    throw new Error(await created.text());
  }
  await page.goto("/sign-in?skip=1");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).not.toHaveURL(/\/sign-in/);
}

test("continue puts skip=1 on log in and a later visit skips the splash", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Your Race, Your Plan, Your Result" })).toBeVisible();
  await expect(page.getByText("Photo by Giant Asparagus on Pexels")).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/\/sign-in\?skip=1$/);
  await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
  await page.goto("/?skip=1");
  await expect(page).toHaveURL(/\/sign-in\?skip=1$/);
  await expect(page.getByRole("button", { name: "Continue" })).toHaveCount(0);
});

test("a non-admin never sees admin and the API refuses them", async ({ page }) => {
  await signIn(page, "ada310@example.com", "Ada");
  const me = await page.request.get(`${API}/auth/me`);
  expect((await me.json()).role).toBe("athlete");
  const denied = await page.request.get(`${API}/admin/accounts`);
  expect(denied.status()).toBe(403);
  expect((await denied.json()).detail).toBe("That page is for the admin account.");
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/home$/);
  await expect(page.getByRole("link", { name: "Admin", exact: true })).toHaveCount(0);
  await page.goto("/last-session");
  await expect(page).toHaveURL(/\/home$/);
  await page.goto("/goal");
  await expect(page).toHaveURL(/\/home$/);
});

test("the admin page, fixture pages, and the track splash stay put", async ({ page }) => {
  rmSync("/tmp/rio-playwright-hero.json", { force: true });
  await signIn(page, "admin@example.com", "Ada Admin");
  const me = await page.request.get(`${API}/auth/me`);
  expect((await me.json()).role).toBe("admin");
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Admin" })).toBeVisible();
  await expect(page.getByText("Accounts and the startup photos.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Admin", exact: true })).toBeVisible();
  await expect(page.getByText("Read only.")).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Email" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Role" })).toHaveCount(0);
  await expect(page.getByText("Test season", { exact: true })).toBeVisible();
  await expect(page.getByText("This login is not changed.")).toBeVisible();
  await page.getByRole("button", { name: "Load test season" }).click();
  await expect(page.getByText("The test season could not be saved.")).toBeVisible();
  await page.getByRole("button", { name: "Delete test season" }).click();
  await expect(page.getByText("Confirm the delete first.")).toBeVisible();
  await expect(page.getByText("Photo by RUN 4 FFWPU on Pexels")).toBeVisible();
  await expect(page.getByText("Photo by Writchid Snipes on Pexels")).toBeVisible();
  await expect(page.getByText("Photo by Ansey Photography on Pexels")).toBeVisible();
  const credit = page.getByLabel("Credit line").first();
  await credit.fill("Photo by the admin check");
  await page.getByRole("button", { name: "Save photos" }).click();
  await expect(page.getByText("Startup photos saved.")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Photo by the admin check")).toBeVisible();
  await page.getByRole("button", { name: "Log out" }).click();
  await page.goto("/");
  await expect(page.getByText("Photo by Giant Asparagus on Pexels")).toBeVisible();
  await expect(page.getByText("Photo by the admin check")).toHaveCount(0);
  await signIn(page, "admin@example.com", "Ada Admin");

  await page.goto("/next");
  await expect(page.getByRole("heading", { name: "Next" })).toBeVisible();
  await expect(page.getByLabel("Session")).toBeVisible();
  await expect(page.getByText("FIXTURE").first()).toBeVisible();
  await expect(page.locator(".rio-prose").first()).not.toHaveText("");
  await expect(page.getByText("$25")).toHaveCount(0);
  await expect(page.getByText("SYNTHETIC")).toHaveCount(0);
  await expect(page.getByText("DEMO")).toHaveCount(0);

  await page.goto("/decisions");
  await expect(page.getByRole("heading", { name: "Decisions" })).toBeVisible();
  await expect(page.locator(".rio-prose").first()).toBeVisible();

  await page.goto("/ledger");
  await expect(page.getByRole("heading", { name: "Ledger" })).toBeVisible();
  await expect(page.getByText("Deposits")).toBeVisible();
  await expect(page.getByText("Emerging")).toBeVisible();
  await expect(page.getByText("Decaying")).toBeVisible();
  await expect(page.getByText("As of")).toBeVisible();
  await expect(page.getByText("FIXTURE").first()).toBeVisible();

  await page.goto("/goal");
  await expect(page.getByRole("heading", { name: "Goal" })).toBeVisible();
  await expect(page.getByText("current_mark")).toBeVisible();
  await expect(page.getByText("limiting_capacities")).toBeVisible();
  await expect(page.getByText("Coming in the next step.")).toHaveCount(0);
});

test("home shows an em dash when the stored length cannot be read", async ({ page }) => {
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    if (url.pathname === "/auth/me") {
      await route.fulfill({
        json: {
          id: "ada",
          email: "ada@example.com",
          display_name: "Ada",
          role: "athlete",
          kind: "local",
          today: "2026-11-10",
          prefs: { easy_pace: "7:45", intro_seen: true },
        },
      });
      return;
    }
    if (url.pathname === "/home") {
      await route.fulfill({
        json: {
          today: "2026-11-10",
          athlete: { display_name: "Ada", prefs: { easy_pace: "7:45", intro_seen: true }, role: "athlete" },
          hello: "Hey, Ada",
          strava_offer: false,
          copy: "",
          season: null,
          broken: true,
        },
      });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: "Not mocked." } });
  });
  await page.goto("/home");
  await expect(page.getByRole("heading", { name: "Home" })).toBeVisible();
  await expect(page.getByText("—", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Generate season plan" })).toHaveCount(0);
});
