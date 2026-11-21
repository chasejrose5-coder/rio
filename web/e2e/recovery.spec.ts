import { expect, test, type Page, type Route } from "@playwright/test";
import { INJURY_DISCLAIMER, dayBlocks } from "../lib/injury-content";

const today = "2026-11-09";

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

type Area = {
  area_id: string;
  anchor_on: string;
  level: number;
  level_now: number;
  level_name: "easy" | "medium" | "hard";
};

function state(areas: Area[], completions: { date: string; block_id: string }[]) {
  return { today, areas, completions };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(page: Page) {
  const areas: Area[] = [];
  const completions: { date: string; block_id: string }[] = [];
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
        plan: { sessions: [{ date: today, day_of_week: "Monday", template_id: "aer_8000_r0_x1", reason_codes: ["extra_easy_day"] }] },
      });
    }
    if (path === "/sessions/2026-11-09") {
      return json(route, {
        date: today,
        session: { date: today, day_of_week: "Monday", template_id: "aer_8000_r0_x1", week_number: 1 },
        actual: null,
        quality: false,
        note: null,
        viewed: true,
        digest: "digest-1",
        label: "8 km easy",
        structure: "One continuous easy run.",
        target: "Stay easy.",
        reasons: ["Easy day"],
        shown_date: today,
        prescription: { line: "Run easy", tolerance: "", block: "", average: "" },
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
    if (path === "/injury" && method === "GET") return json(route, state(areas, completions));
    if (path === "/injury/areas" && method === "POST") {
      const payload = route.request().postDataJSON() as { area_id: string };
      if (!areas.some((area) => area.area_id === payload.area_id)) {
        areas.push({ area_id: payload.area_id, anchor_on: today, level: 0, level_now: 0, level_name: "easy" });
      }
      return json(route, state(areas, completions));
    }
    if (path.startsWith("/injury/areas/") && method === "DELETE") {
      const areaId = decodeURIComponent(path.split("/").pop() || "");
      const index = areas.findIndex((area) => area.area_id === areaId);
      if (index >= 0) areas.splice(index, 1);
      return json(route, state(areas, completions));
    }
    if (path === "/injury/completions" && method === "POST") {
      const payload = route.request().postDataJSON() as { block_id: string; done?: boolean };
      const index = completions.findIndex((row) => row.block_id === payload.block_id && row.date === today);
      if (payload.done === false) {
        if (index >= 0) completions.splice(index, 1);
      } else if (index < 0) {
        completions.push({ date: today, block_id: payload.block_id });
      }
      return json(route, state(areas, completions));
    }
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("recovery lists every exercise, saves a rebuilding area, and the day shows the set", async ({ page }) => {
  await install(page);
  await page.goto("/recovery");
  await expect(page.getByRole("heading", { name: "Recovery", exact: true })).toBeVisible();
  await expect(page.getByText(INJURY_DISCLAIMER).first()).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Training" }).getByRole("link", { name: "Recovery" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(page.getByRole("heading", { name: "Towel scrunches" })).toBeVisible();
  await expect(page.getByText("1×10").first()).toBeVisible();
  await page.getByRole("button", { name: "Achilles tendon" }).click();
  await expect(page.getByText("Achilles tendon is Easy.")).toBeVisible();
  await expect(page.getByText("Already at easy.")).toBeVisible();
  await page.getByRole("button", { name: "Bone stress" }).click();
  await expect(page.getByText("Walk-run return only. See a doctor first.")).toBeVisible();

  if (process.env.RIO_SHOTS) {
    await page.setViewportSize({ width: 1280, height: 1400 });
    await page.screenshot({ path: "/opt/cursor/artifacts/pr-a-recovery-desktop.png" });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.screenshot({ path: "/opt/cursor/artifacts/pr-a-recovery-phone.png" });
  }

  const monday = dayBlocks(today, [], []);
  const first = monday[0]?.exercises[0]?.exercise.name || "";
  await page.goto(`/session?date=${today}`);
  await expect(page.getByRole("region", { name: "Injury prevention" })).toBeVisible();
  await expect(page.getByText(INJURY_DISCLAIMER).first()).toBeVisible();
  await expect(page.getByText(first, { exact: false }).first()).toBeVisible();
  await page.getByRole("button", { name: "Mark done" }).click();
  await expect(page.getByRole("button", { name: "Done" })).toBeVisible();

  if (process.env.RIO_SHOTS) {
    const block = page.getByRole("region", { name: "Injury prevention" });
    await page.setViewportSize({ width: 1280, height: 1000 });
    await block.evaluate((element) => element.scrollIntoView({ block: "center" }));
    await page.screenshot({ path: "/opt/cursor/artifacts/pr-a-session-desktop.png" });
    await page.setViewportSize({ width: 390, height: 844 });
    await block.evaluate((element) => element.scrollIntoView({ block: "center" }));
    await page.screenshot({ path: "/opt/cursor/artifacts/pr-a-session-phone.png" });
  }
});
