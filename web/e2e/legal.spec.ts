import { expect, test } from "@playwright/test";

test("privacy and terms are public drafts with footer links", async ({ page }) => {
  await page.goto("/privacy");
  await expect(page.getByRole("note")).toContainText("DRAFT");
  await expect(page.getByRole("note")).toContainText("For review. This page is not in effect yet.");
  await expect(page.getByRole("note")).not.toContainText("[COMPANY NAME]");
  await expect(page.getByRole("note")).not.toContainText("[CONTACT EMAIL]");
  await expect(page.getByRole("heading", { name: "Privacy policy" })).toBeVisible();
  await expect(page.getByText("Not in effect.")).toBeVisible();
  await expect(page.getByText("Chase Rose, an individual")).toBeVisible();
  await expect(page.getByText("riorunning.app@gmail.com")).toBeVisible();
  await expect(page.getByText("The governing law chosen here is the law of the State of California.")).toBeVisible();
  await expect(page.getByText("RIO is not directed to children under 13.")).toBeVisible();
  await expect(page.getByText("mailing address")).toHaveCount(0);
  await expect(page.getByText("activity:read_all").first()).toBeVisible();
  await expect(page.getByText("Photo by")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Terms" }).first()).toBeVisible();

  await page.goto("/terms");
  await expect(page.getByRole("note")).toContainText("DRAFT");
  await expect(page.getByRole("note")).toContainText("For review. This page is not in effect yet.");
  await expect(page.getByRole("heading", { name: "Terms" })).toBeVisible();
  await expect(page.getByText("Not in effect.").first()).toBeVisible();
  await expect(page.getByText("any runner").first()).toBeVisible();
  await expect(page.getByText("Users must be at least 13.")).toBeVisible();
  await expect(page.getByText("Chase Rose, an individual")).toBeVisible();
  await expect(page.getByText("The governing law chosen here is the law of the State of California.")).toBeVisible();
  await expect(page.getByText("No warranty, liability cap, or refund rule is stated, because none is decided.")).toBeVisible();
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
