import { expect, test } from "@playwright/test";

test("a missing page is a branded 404 with a way home", async ({ page }) => {
  const response = await page.goto("/not-a-rio-page");
  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "Page not found" })).toBeVisible();
  await expect(page.getByText("RIO", { exact: true }).first()).toBeVisible();
  await page.getByRole("link", { name: "Back home" }).click();
  await expect(page).toHaveURL(/\/$/);
});

test("robots and the sitemap name only the public site", async ({ page }) => {
  const robots = await page.goto("/robots.txt");
  expect(robots?.status()).toBe(200);
  const robotsText = await page.locator("body").innerText();
  expect(robotsText).toContain("Sitemap: https://www.riorunning.com/sitemap.xml");
  expect(robotsText).toContain("Disallow: /home");
  expect(robotsText).toContain("Disallow: /plan");
  expect(robotsText).not.toContain("Disallow: /about");
  expect(robotsText).not.toContain("Disallow: /sign-in");
  expect(robotsText).not.toContain("Disallow: /privacy");

  const map = await page.goto("/sitemap.xml");
  expect(map?.status()).toBe(200);
  const xml = await page.content();
  expect(xml).toContain("https://www.riorunning.com/about");
  expect(xml).toContain("https://www.riorunning.com/sign-in");
  expect(xml).toContain("https://www.riorunning.com/privacy");
  expect(xml).toContain("https://www.riorunning.com/terms");
  expect(xml).not.toContain("https://www.riorunning.com/home");
  expect(xml).not.toContain("https://www.riorunning.com/library");
});

test("the login photo is a modern image and the credit stays", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/sign-in");
  await expect(page.getByText("Photo by Steve Pancrate on Pexels")).toBeVisible();
  const image = await page.locator(".auth-screen").evaluate((el) => getComputedStyle(el).backgroundImage);
  expect(image).toMatch(/login-800\.(avif|webp)/);
  expect(image).not.toContain("startup-track");
});
