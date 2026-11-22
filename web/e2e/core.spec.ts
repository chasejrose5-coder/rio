import { expect, test, type Page, type Route } from "@playwright/test";
import { CORE_DISCLAIMER, circuitFor } from "../lib/core-content";
import { MEDICAL_NOTE } from "../lib/glossary";

const today = "2026-11-10";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today,
  next_session: today,
  prefs: { timezone: "America/Los_Angeles", intro_seen: true, compact: false },
};

const quality = {
  date: today,
  day_of_week: "Tuesday",
  template_id: "se_400_r90_x6",
  reason_codes: ["phase_4"],
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(page: Page) {
  const completions: { date: string }[] = [];
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    const method = route.request().method();
    if (path === "/auth/me") return json(route, athlete);
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/seasons/current") {
      return json(route, {
        today,
        inputs: { current_time: "2:05.0", start_date: "2026-11-08", goal_time: "1:58.0", goal_date: "2026-12-19" },
        plan: { sessions: [quality] },
      });
    }
    if (path === "/sessions/2026-11-10") {
      return json(route, {
        date: today,
        session: { ...quality, week_number: 1 },
        actual: null,
        quality: true,
        note: null,
        viewed: true,
        digest: "digest-1",
        label: "6 × 400 m",
        structure: "6 × 400 m, 90 s rest",
        target: "Hit the session.",
        reasons: ["Hard day"],
        shown_date: today,
        prescription: { line: "6 × 400 m", tolerance: "", block: "", average: "" },
        logging: "times",
        confirm_adapt: false,
        show_id: false,
        boxes: 0,
        seed: [],
        summary: "",
        match: null,
        heart_rate: "",
      });
    }
    if (path === "/core" && method === "GET") return json(route, { today, completions });
    if (path === "/core/completions" && method === "POST") {
      const payload = route.request().postDataJSON() as { done?: boolean };
      const index = completions.findIndex((row) => row.date === today);
      if (payload.done === false) {
        if (index >= 0) completions.splice(index, 1);
      } else if (index < 0) completions.push({ date: today });
      return json(route, { today, completions: [...completions] });
    }
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("the core library and a hard-day circuit stay near eight minutes", async ({ page }) => {
  await install(page);
  await page.goto("/core");
  await expect(page.getByRole("heading", { name: "Core", exact: true })).toBeVisible();
  await expect(page.getByText(MEDICAL_NOTE).first()).toBeVisible();
  await expect(page.getByText(CORE_DISCLAIMER).first()).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Training" }).getByRole("link", { name: "Core" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await page.getByRole("button", { name: "Anti-extension" }).click();
  await expect(page.getByRole("heading", { name: "Plank", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Anti-rotation" }).click();
  await expect(page.getByRole("heading", { name: "Pallof press" })).toBeVisible();
  await page.getByRole("button", { name: "Lateral" }).click();
  await expect(page.getByRole("heading", { name: "Copenhagen plank" })).toBeVisible();

  if (process.env.RIO_SHOTS) {
    await page.setViewportSize({ width: 1280, height: 1200 });
    await page.screenshot({ path: "/opt/cursor/artifacts/pr-b-core-desktop.png" });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: "/opt/cursor/artifacts/pr-b-core-phone.png" });
  }

  const circuit = circuitFor(today, [quality]);
  await page.goto(`/session?date=${today}`);
  await page.getByRole("button", { name: "Core", exact: true }).click();
  const block = page.getByRole("region", { name: "Core circuit" });
  await expect(block).toBeVisible();
  await expect(block.getByText("About 8 min")).toBeVisible();
  await expect(page.getByText(MEDICAL_NOTE).first()).toBeVisible();
  await expect(block.getByText(CORE_DISCLAIMER)).toBeVisible();
  await expect(block.getByText(MEDICAL_NOTE)).toHaveCount(0);
  await expect(block.getByText(circuit?.exercises[0]?.name || "", { exact: false }).first()).toBeVisible();
  await block.getByRole("button", { name: "Mark done" }).click();
  await expect(block.getByRole("button", { name: "Done" })).toBeVisible();

  if (process.env.RIO_SHOTS) {
    await page.setViewportSize({ width: 1280, height: 1000 });
    await block.evaluate((element) => element.scrollIntoView({ block: "center" }));
    await page.screenshot({ path: "/opt/cursor/artifacts/pr-b-session-desktop.png" });
    await page.setViewportSize({ width: 390, height: 844 });
    await block.evaluate((element) => element.scrollIntoView({ block: "center" }));
    await page.screenshot({ path: "/opt/cursor/artifacts/pr-b-session-phone.png" });
  }
});
