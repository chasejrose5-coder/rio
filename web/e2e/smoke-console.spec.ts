import { expect, test, type ConsoleMessage, type Page } from "@playwright/test";

test.describe.configure({ mode: "serial" });

const SIGNED_OUT = ["/", "/privacy", "/terms", "/about", "/sign-in", "/this-route-is-not-in-rio"];
const SIGNED_IN = [
  "/",
  "/home",
  "/plan",
  "/library",
  "/stretch",
  "/recovery",
  "/core",
  "/foam",
  "/activity",
  "/session",
  "/heart-rate",
  "/more",
  "/profile",
  "/settings",
  "/past-seasons",
  "/guide",
  "/about",
  "/creators",
  "/privacy",
  "/terms",
  "/this-route-is-not-in-rio",
];

function ignored(text: string, path: string): boolean {
  if (text.includes("Download the React DevTools")) return true;
  if (text.includes("favicon")) return true;
  if (text.includes("/_next/")) return true;
  if (path === "/this-route-is-not-in-rio" && text.includes("404")) return true;
  return false;
}

function watch(page: Page) {
  const errors: string[] = [];
  const onConsole = (msg: ConsoleMessage) => {
    if (msg.type() === "error") {
      const where = msg.location().url;
      errors.push(where ? `${msg.text()} @ ${where}` : msg.text());
    }
  };
  const onPage = (err: Error) => errors.push(String(err));
  page.on("console", onConsole);
  page.on("pageerror", onPage);
  page.on("response", (response) => {
    if (response.status() >= 400) errors.push(`HTTP ${response.status()} ${response.url()}`);
  });
  return {
    take(path: string) {
      const found = errors.filter((text) => !ignored(text, path));
      errors.length = 0;
      return found;
    },
  };
}

async function layout(page: Page, width: number) {
  const box = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    client: document.documentElement.clientWidth,
    heroLeft: (() => {
      const hero = document.querySelector(".rio-v3 .rio-hero:not(.rio-auth-hero):not(.rio-start-hero):not(.rio-hero-week), .rio-v3 .rio-plan-hero, .rio-splash, .page-about .rio-about-banner");
      if (!hero) return 0;
      return hero.getBoundingClientRect().left;
    })(),
    heroRight: (() => {
      const hero = document.querySelector(".rio-v3 .rio-hero:not(.rio-auth-hero):not(.rio-start-hero):not(.rio-hero-week), .rio-v3 .rio-plan-hero, .rio-splash, .page-about .rio-about-banner");
      if (!hero) return 0;
      return hero.getBoundingClientRect().right;
    })(),
    overlay: document.body.innerText.includes("Unhandled Runtime Error") || document.body.innerText.includes("Application error"),
  }));
  expect(box.overlay, "error overlay").toBe(false);
  expect(box.scroll, "horizontal overflow").toBeLessThanOrEqual(box.client + 1);
  if (box.heroRight > 0) {
    expect(box.heroLeft).toBeGreaterThanOrEqual(-1);
    expect(box.heroRight).toBeLessThanOrEqual(box.client + 1);
    expect(box.heroRight - box.heroLeft).toBeGreaterThan(width * 0.9);
  }
}

async function targets(page: Page, path: string, width: number) {
  if (path === "/guide" && width >= 1280) {
    await expect(page.locator(".rio-on-page nav a").first()).toBeVisible();
  }
  if (path !== "/settings" && path !== "/guide") return;
  const small = await page.evaluate((which) => {
    const selector = which === "/settings"
      ? ".rio-settings-index a, .rio-v3.page-settings input:not([type=checkbox]):not([type=radio]), .rio-v3.page-settings select, .rio-settings-button, .rio-danger-button"
      : ".rio-on-page nav a";
    return [...document.querySelectorAll<HTMLElement>(selector)].flatMap((node) => {
      const box = node.getBoundingClientRect();
      if (box.width < 1 || box.height < 1) return [];
      return Math.round(box.height) < 44 ? [`${Math.round(box.height)}px ${node.textContent?.trim().slice(0, 40)}`] : [];
    });
  }, path);
  expect(small, `${width} ${path} under 44px`).toEqual([]);
}

test("signed-out routes stay quiet", async ({ page }) => {
  test.setTimeout(180_000);
  const log = watch(page);
  for (const width of [1280, 375]) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    for (const path of SIGNED_OUT) {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(200);
      expect(log.take(path), `${width} ${path}`).toEqual([]);
      await layout(page, width);
      await targets(page, path, width);
    }
  }
});

test("signed-in routes stay quiet", async ({ page }) => {
  test.setTimeout(120_000);
  const email = `smoke-${Date.now()}@example.com`;
  const created = await page.request.post("http://localhost:8000/auth/sign-up", {
    data: { email, password: "correct-horse", name: "Smoke" },
  });
  expect([200, 400]).toContain(created.status());
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/sign-in?skip=1");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in", exact: true }).click({ force: true });
  await expect(page).not.toHaveURL(/\/sign-in/);
  const pace = await page.request.patch("http://localhost:8000/settings", {
    data: { easy_pace: "7:25", easy_pace_unit: "mi", intro_seen: true },
  });
  expect(pace.ok()).toBeTruthy();
  const season = await page.request.post("http://localhost:8000/seasons", {
    data: {
      current_time: "2:05.0",
      start_date: "2026-11-08",
      goal_time: "1:58.0",
      goal_date: "2027-07-08",
    },
  });
  expect(season.ok()).toBeTruthy();

  const log = watch(page);
  await page.goto("/home", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(300);
  log.take("warmup");
  for (const width of [1280, 375]) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    for (const path of SIGNED_IN) {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(200);
      expect(log.take(path), `${width} ${path}`).toEqual([]);
      await layout(page, width);
      await targets(page, path, width);
    }
  }
});
