import { expect, test, type Page, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-10",
  prefs: {
    easy_pace: "7:25",
    easy_pace_unit: "mi",
    intro_seen: true,
    no_watch: false,
    confirm_adapt: false,
    timezone: "America/Los_Angeles",
    date_format: "short",
    pace_units: "mi",
    units: "miles",
    show_ids: false,
    compact: false,
    theme: "system",
  },
};

function ratio(fg: string, bg: string): number {
  const channel = (value: number) => {
    const s = value / 255;
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  const lum = (color: string) => {
    const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (!match) return 0;
    const r = channel(Number(match[1]));
    const g = channel(Number(match[2]));
    const b = channel(Number(match[3]));
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const a = lum(fg);
  const b = lum(bg);
  const [hi, lo] = a > b ? [a, b] : [b, a];
  return (hi + 0.05) / (lo + 0.05);
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(page: Page) {
  const person = structuredClone(athlete);
  const patches: Record<string, unknown>[] = [];
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/session" || path === "/auth/me") return json(route, person);
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/settings" && route.request().method() === "PATCH") {
      const body = route.request().postDataJSON() as Record<string, unknown>;
      patches.push(body);
      if (body.theme === "light" || body.theme === "dark" || body.theme === "system") person.prefs.theme = body.theme;
      return json(route, person);
    }
    if (path === "/heart-rate") {
      return json(route, {
        method: "karvonen",
        method_label: "Karvonen",
        method_sentence: "Zones use the Karvonen (heart rate reserve) method.",
        safety: "Not medical advice.",
        no_monitor: true,
        resting_hr: null,
        max_hr: null,
        custom: false,
        zones: [],
        strava_prefill: { resting_hr: null, max_hr: null, available: false, note: "" },
      });
    }
    if (path === "/seasons/current") return json(route, { detail: "No season." }, 404);
    if (path === "/home") return json(route, { today: person.today, athlete: person, hello: "Hey Ada", season: null, copy: "" });
    return json(route, {});
  });
  return { person, patches };
}

test("a stored theme is on the document before the page settles", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("rio-theme", "dark"));
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const paint = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  expect(paint.replace(/\s/g, "")).toBe("rgb(20,18,17)");
});

test("light stays light when the operating system is dark", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("rio-theme", "light"));
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("Appearance saves only theme and each segment is at least 44px", async ({ page }) => {
  const { person, patches } = await install(page);
  await page.goto("/settings");
  await page.locator("summary", { hasText: "Preferences" }).click();
  const group = page.getByRole("group", { name: "Appearance" });
  await expect(group).toBeVisible();
  const labels = group.locator("label");
  await expect(labels).toHaveCount(3);
  const short = await labels.evaluateAll((nodes) =>
    nodes.flatMap((node) => (Math.round(node.getBoundingClientRect().height) < 44 ? [node.textContent || ""] : [])),
  );
  expect(short).toEqual([]);
  await group.getByRole("radio", { name: "System" }).focus();
  await page.keyboard.press("ArrowLeft");
  await expect(group.getByRole("radio", { name: "Dark" })).toBeChecked();
  await expect.poll(() => patches.at(-1)).toEqual({ theme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(await page.evaluate(() => localStorage.getItem("rio-theme"))).toBe("dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  expect(person.prefs.theme).toBe("dark");
});

test("the account theme replaces a different device mirror", async ({ page }) => {
  const { person } = await install(page);
  person.prefs.theme = "dark";
  await page.addInitScript(() => localStorage.setItem("rio-theme", "light"));
  await page.goto("/settings");
  await page.locator("summary", { hasText: "Preferences" }).click();
  await expect(page.getByRole("radio", { name: "Dark" })).toBeChecked();
  await expect.poll(() => page.locator("html").getAttribute("data-theme")).toBe("dark");
  await expect.poll(() => page.evaluate(() => localStorage.getItem("rio-theme"))).toBe("dark");
});

test("dark body text meets AA on the page background", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("rio-theme", "dark"));
  await page.goto("/about");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  const found = await page.evaluate(() => {
    const body = getComputedStyle(document.body);
    const main = document.querySelector("main");
    const sample = main ? getComputedStyle(main) : body;
    return { fg: sample.color, bg: body.backgroundColor };
  });
  expect(ratio(found.fg, found.bg)).toBeGreaterThanOrEqual(4.5);
});
