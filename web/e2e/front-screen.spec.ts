import { mkdirSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

function channel(value: number): number {
  const s = value / 255;
  return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
}

function luminance(color: string): number {
  const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!match) return 0;
  const r = channel(Number(match[1]));
  const g = channel(Number(match[2]));
  const b = channel(Number(match[3]));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(fg: string, bg: string): number {
  const a = luminance(fg);
  const b = luminance(bg);
  const [hi, lo] = a > b ? [a, b] : [b, a];
  return (hi + 0.05) / (lo + 0.05);
}

async function contrast(page: Page, selector: string, backgroundSelector?: string) {
  return page.evaluate(
    ({ selector, backgroundSelector }) => {
      const node = document.querySelector(selector);
      if (!node) return null;
      const style = getComputedStyle(node);
      const backdrop = backgroundSelector ? document.querySelector(backgroundSelector) : node;
      const back = backdrop ? getComputedStyle(backdrop).backgroundColor : style.backgroundColor;
      return { fg: style.color, bg: back, border: style.borderTopColor };
    },
    { selector, backgroundSelector },
  );
}

test("the old-host banner keeps the space and stays off preview aliases", async ({ page }) => {
  await page.setExtraHTTPHeaders({ "x-forwarded-host": "rio-rio-44fa.vercel.app" });
  await page.goto("/");
  const banner = page.locator(".rio-old-home");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText("RIO now lives at riorunning.com");
  const gap = await banner.evaluate((node) => {
    const link = node.querySelector("a");
    const previous = link?.previousSibling;
    return previous?.textContent ?? "";
  });
  expect(gap.endsWith(" ") || gap.endsWith("\u00A0")).toBe(true);
  const paint = await banner.evaluate((node) => getComputedStyle(node).backgroundColor);
  expect(paint.replace(/\s/g, "")).toBe("rgb(18,17,16)");

  await page.setExtraHTTPHeaders({
    "x-forwarded-host": "rio-git-cursor-uiux-enhancement-v4-c72e-rio-44fa.vercel.app",
  });
  await page.goto("/");
  await expect(page.locator(".rio-old-home")).toHaveCount(0);
});

test("the landing fits a 1280x800 screen and links to About and Log in", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");
  await page.evaluate(() => document.fonts.ready);
  await expect(page.getByRole("heading", { name: "Your Race, Your Plan, Your Result" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Log in" })).toHaveAttribute("href", "/sign-in?skip=1");
  await expect(page.getByRole("link", { name: "About" })).toHaveAttribute("href", "/about");
  await expect(page.getByText("Photo by Giant Asparagus on Pexels")).toBeVisible();
  await expect(page.locator(".rio-splash").getByText(/Not medical advice/)).toHaveCount(0);
  const strip = page.locator(".rio-splash-strip");
  const wide = await strip.evaluate((node) => node.getBoundingClientRect().width / window.innerWidth);
  expect(wide).toBeGreaterThanOrEqual(0.9);
  const wraps = await strip.evaluate((node) => {
    const tops = (selector: string) => {
      const nodes = [...node.querySelectorAll(selector)];
      return new Set(nodes.map((el) => Math.round(el.getBoundingClientRect().top))).size;
    };
    const credit = node.querySelector(".rio-photo-credit");
    const creditLines = credit ? Math.round(credit.getBoundingClientRect().height / 18) : -1;
    return { credit: creditLines, links: tops(".rio-legal-links a") };
  });
  expect(wraps.credit).toBe(1);
  expect(wraps.links).toBe(1);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollHeight - document.documentElement.clientHeight,
  );
  expect(overflow).toBeLessThanOrEqual(1);
  const lines = await page.locator(".rio-splash h1 br").count();
  expect(lines).toBe(2);

  await page.setViewportSize({ width: 375, height: 812 });
  const position = await page.locator(".rio-splash").evaluate((node) => getComputedStyle(node).backgroundPosition);
  expect(position.startsWith("92%")).toBe(true);
  const stacked = await page.locator(".rio-splash-strip").evaluate((node) => {
    const style = getComputedStyle(node);
    const links = node.querySelector(".rio-legal-links")?.getBoundingClientRect().top ?? 0;
    const credit = node.querySelector(".rio-photo-credit")?.getBoundingClientRect().top ?? 0;
    return { flow: style.flexDirection, linksBeforeCredit: links < credit };
  });
  expect(stacked.flow).toBe("column");
  expect(stacked.linksBeforeCredit).toBe(true);

  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/sign-in?skip=1");
  await expect(page.locator(".auth-screen").getByText(/Not medical advice/)).toBeVisible();
});

test("landing footer shots", async ({ browser }) => {
  const dir = process.env.RIO_ARTIFACTS;
  test.skip(!dir, "screenshots are saved only when RIO_ARTIFACTS is set");
  mkdirSync(dir!, { recursive: true });
  for (const theme of ["light", "dark"] as const) {
    for (const width of [1280, 768, 375]) {
      const page = await browser.newPage({ viewport: { width, height: width === 375 ? 812 : 800 } });
      await page.addInitScript((value) => localStorage.setItem("rio-theme", value), theme);
      await page.goto("/");
      await page.getByRole("heading", { name: "Your Race, Your Plan, Your Result" }).waitFor();
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: `${dir}/landing-${width}-${theme}.png` });
      if (width === 1280 && theme === "light") {
        await page.goto("/sign-in?skip=1");
        await page.screenshot({ path: `${dir}/signin-1280-light.png` });
      }
      await page.close();
    }
  }
});

test("auth credit and input borders meet contrast in light and dark", async ({ page }) => {
  for (const theme of ["light", "dark"] as const) {
    await page.addInitScript((value) => localStorage.setItem("rio-theme", value), theme);
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/sign-in?skip=1");
    await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
    const credit = await contrast(page, ".auth-screen .rio-photo-credit");
    expect(credit).not.toBeNull();
    expect(ratio(credit!.fg, credit!.bg)).toBeGreaterThanOrEqual(4.5);
    const field = await contrast(page, ".rio-auth-card input", ".rio-auth-card");
    expect(field).not.toBeNull();
    expect(ratio(field!.border, field!.bg)).toBeGreaterThanOrEqual(3);
    if (!page.url().includes("google")) {
      const subtitle = page.locator(".rio-auth-hero .rio-range");
      if ((await subtitle.count()) > 0) {
        const text = await subtitle.innerText();
        const google = await page.getByRole("button", { name: "Continue with Google" }).count();
        if (google === 0) expect(text).toBe("Use your email and password.");
        else expect(text).toContain("Use Google");
      }
    }
  }
});
