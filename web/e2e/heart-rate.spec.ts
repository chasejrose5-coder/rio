import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

const shots = "/opt/cursor/artifacts";

test("onboarding saves Karvonen zones and settings can edit them", async ({ page }) => {
  test.setTimeout(120_000);
  mkdirSync(shots, { recursive: true });
  const email = `hr-${Date.now()}@example.com`;
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/create-account");
  await page.getByLabel("Name").fill("Rita");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/easy-pace$/);
  await page.goto("/heart-rate");

  await expect(page.getByRole("heading", { name: "Heart rate" })).toBeVisible();
  await expect(page.getByText("Zones use the Karvonen (heart rate reserve) method.")).toBeVisible();
  await expect(page.getByText("This is not medical advice. Stop and seek help if your heart rate stays unusually high or you feel unwell.")).toBeVisible();
  await expect(page.getByText("Not medical advice. If pain is sharp or getting worse, or your heart rate stays unusually high, stop and see a doctor or physio.")).toBeVisible();
  await page.getByLabel("Resting heart rate").fill("20");
  await page.getByLabel("Max heart rate").fill("180");
  await page.getByRole("button", { name: "Save heart rate" }).click();
  await expect(page.getByText("Enter a resting heart rate between 30 and 100.")).toBeVisible();

  await page.getByLabel("Resting heart rate").fill("60");
  await page.getByLabel("Max heart rate").fill("180");
  await expect(page.getByText("120–132 bpm")).toBeVisible();
  await expect(page.getByText("168–180 bpm")).toBeVisible();
  await page.screenshot({ path: `${shots}/heart-rate-onboarding.png`, fullPage: true });
  await page.getByRole("button", { name: "Save heart rate" }).click();
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();
  await expect(page.getByLabel("Easy pace")).toBeVisible();

  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await page.locator("#toc-heart-rate summary").click();
  await expect(page.getByText("Zones use the Karvonen (heart rate reserve) method.")).toBeVisible();
  await expect(page.getByText("120–132 bpm")).toBeVisible();
  await page.getByLabel("Max heart rate").fill("190");
  await page.getByLabel("Resting heart rate").click();
  await expect(page.getByText("125–138 bpm")).toBeVisible();
  await expect(page.getByText("177–190 bpm")).toBeVisible();

  await page.getByText("Adjust zone boundaries").click();
  await page.getByLabel("Zone 1 high").fill("128");
  await page.getByLabel("Zone 1 low").click();
  await expect(page.getByText("125–128 bpm")).toBeVisible();
  await expect(page.getByText("These boundaries are your edit.")).toBeVisible();
  await page.screenshot({ path: `${shots}/heart-rate-settings.png`, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: `${shots}/heart-rate-settings-mobile.png`, fullPage: true });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.getByRole("button", { name: "Reset to Karvonen defaults" }).click();
  await expect(page.getByText("125–138 bpm")).toBeVisible();
  await expect(page.getByText("These boundaries are your edit.")).toHaveCount(0);

  await page.getByLabel("I don't have a heart rate monitor").check();
  await expect(page.getByLabel("Easy pace")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save easy pace" })).toBeVisible();
  await page.getByLabel("Easy pace").fill("7:40");
  await page.getByRole("button", { name: "Save easy pace" }).click();
  await expect(page.getByLabel("Easy pace")).toHaveValue("7:40");

  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: `${shots}/heart-rate-settings-mobile.png`, fullPage: true });
});

test("the monitor toggle skips heart rate and keeps the easy pace question", async ({ page }) => {
  test.setTimeout(90_000);
  const email = `hr-skip-${Date.now()}@example.com`;
  await page.goto("/create-account");
  await page.getByLabel("Name").fill("Noel");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/easy-pace$/);
  await page.goto("/heart-rate");
  await expect(page.getByRole("heading", { name: "Heart rate" })).toBeVisible();
  await page.getByLabel("I don't have a heart rate monitor").check();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("heading", { name: "Your easy pace" })).toBeVisible();
  await expect(page.getByLabel("Easy pace")).toBeVisible();
});
