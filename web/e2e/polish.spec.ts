import { expect, test, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-11",
  next_session: null,
  prefs: { easy_pace: "7:45", intro_seen: true, compact: false },
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

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

test("html and font responses set security headers without a wildcard origin", async ({ request }) => {
  const privacy = await request.get("/privacy");
  expect(privacy.status()).toBe(200);
  const headers = privacy.headers();
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  expect(headers["x-frame-options"]).toBe("DENY");
  const policy = headers["content-security-policy"] || "";
  expect(headers["content-security-policy-report-only"]).toBeUndefined();
  expect(policy).toContain("default-src 'self'");
  expect(policy).toContain("frame-ancestors 'none'");
  expect(policy).toContain("https://accounts.google.com");
  expect(policy).toContain("https://fonts.gstatic.com");
  expect(policy).toContain("report-uri /csp-report");
  expect(headers["reporting-endpoints"]).toContain("/csp-report");
  expect(headers["permissions-policy"]).toContain("camera=()");
  expect(headers["permissions-policy"]).not.toContain("browsing-topics");
  expect(headers["permissions-policy"]).toContain("microphone=()");
  expect(headers["access-control-allow-origin"]).toBe("https://www.riorunning.com");

  const font = await request.get("/fonts/inter-latin-400-normal.woff2");
  expect(font.status()).toBe(200);
  expect(font.headers()["access-control-allow-origin"]).toBe("https://www.riorunning.com");
  expect(font.headers()["x-content-type-options"]).toBe("nosniff");
});

test("the splash and sign-in put their copy in a main landmark", async ({ page }) => {
  await page.goto("/");
  const splash = page.locator(".rio-splash");
  await expect(splash).toBeVisible();
  await expect(splash.getByRole("main")).toBeVisible();
  await expect(splash.getByRole("button", { name: "Get started" })).toBeVisible();
  await expect(splash.getByText("Photo by Giant Asparagus on Pexels")).toBeVisible();
  await expect(splash.locator(".rio-splash-strip .rio-photo-credit")).toHaveCount(1);
  await expect(splash.getByText(/Not medical advice/)).toHaveCount(0);

  await page.goto("/sign-in");
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.locator("main .rio-photo-credit")).toHaveCount(1);
  await expect(page.locator("main footer")).toHaveCount(1);
});

test("the guide link is at least 24px and Menu fits at 320px", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/about");
  await page.getByRole("button", { name: "What this page means" }).click();
  const guide = page.getByRole("link", { name: "Read this in the guide" });
  await expect(guide).toBeVisible();
  const guideBox = await guide.boundingBox();
  expect(guideBox?.height).toBeGreaterThanOrEqual(24);
  expect(guideBox?.width).toBeGreaterThanOrEqual(24);
  expect(guideBox?.height).toBeGreaterThanOrEqual(44);

  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/session" || path === "/auth/me") return json(route, athlete);
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/seasons/current") return json(route, { detail: "No current season." }, 404);
    return json(route, {});
  });
  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/about");
  const menu = page.getByRole("button", { name: "Menu" });
  await expect(menu).toBeVisible();
  const box = await menu.boundingBox();
  expect(box).not.toBeNull();
  expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThanOrEqual(320);
  expect(box?.width).toBeGreaterThanOrEqual(24);
  const text = await menu.evaluate((el) => el.scrollWidth <= el.clientWidth + 1);
  expect(text).toBe(true);
});

test("the login photo is a modern image and the credit stays", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/sign-in");
  await expect(page.getByText("Photo by Steve Pancrate on Pexels")).toBeVisible();
  const image = await page.locator(".auth-screen").evaluate((el) => getComputedStyle(el).backgroundImage);
  expect(image).toMatch(/login-800\.(avif|webp)/);
  expect(image).not.toContain("startup-track");
});
