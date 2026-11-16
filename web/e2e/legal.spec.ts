import { expect, test } from "@playwright/test";

test("privacy and terms are public drafts with footer links", async ({ page }) => {
  await page.goto("/privacy");
  await expect(page.getByRole("note")).toContainText("DRAFT");
  await expect(page.getByRole("note")).toContainText("[COMPANY NAME]");
  await expect(page.getByRole("note")).toContainText("[CONTACT EMAIL]");
  await expect(page.getByRole("heading", { name: "Privacy policy" })).toBeVisible();
  await expect(page.getByText("activity:read_all").first()).toBeVisible();
  await expect(page.getByText("Photo by")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Terms" }).first()).toBeVisible();

  await page.goto("/terms");
  await expect(page.getByRole("note")).toContainText("DRAFT");
  await expect(page.getByRole("heading", { name: "Terms" })).toBeVisible();
  await expect(page.getByText("any runner").first()).toBeVisible();
  await expect(page.getByText("Photo by")).toHaveCount(0);

  await page.goto("/");
  await expect(page.getByRole("link", { name: "Privacy" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Terms" })).toBeVisible();
  await expect(page.getByText("Photo by Giant Asparagus on Pexels")).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page).toHaveURL(/\/sign-in/);
  await expect(page.getByRole("link", { name: "Privacy" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Terms" })).toBeVisible();

  await page.goto("/create-account");
  await expect(page.getByRole("link", { name: "Privacy" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Terms" })).toBeVisible();
  await expect(page.getByText("Photo by Steve Pancrate on Pexels")).toBeVisible();
});
