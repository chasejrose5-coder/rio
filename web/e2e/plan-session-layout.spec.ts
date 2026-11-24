import { expect, test } from "@playwright/test";

const WIDTHS = [375, 768, 1024, 1280, 1440];

test("the plan calendar fills the page, and a session log appears only inside a workout that has one", async ({ page, browser }) => {
  test.setTimeout(180_000);
  const email = `layout-${Date.now()}@example.com`;
  const created = await page.request.post("http://localhost:8000/auth/sign-up", {
    data: { email, password: "correct-horse", name: "Layout" },
  });
  expect(created.ok()).toBeTruthy();
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

  const plan = await page.request.get("http://localhost:8000/plan");
  expect(plan.ok()).toBeTruthy();
  const days = (await plan.json()).calendar.flat() as { date: string; in_month: boolean; template_id: string }[];
  let easy = "";
  let quality = "";
  for (const day of days) {
    if (!day.in_month || !day.template_id) continue;
    const session = await page.request.get(`http://localhost:8000/sessions/${day.date}`);
    if (!session.ok()) continue;
    const row = (await session.json()) as { boxes: number; logging: string };
    if (!quality && row.boxes > 0) quality = day.date;
    if (!easy && row.boxes === 0 && row.logging !== "done") easy = day.date;
    if (easy && quality) break;
  }
  expect(easy, "easy day").not.toBe("");
  expect(quality, "quality day").not.toBe("");

  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/plan");
    await expect(page.getByRole("group", { name: "Season phases" })).toBeVisible();
    await expect(page.locator(".rio-cal")).toBeVisible();
    await expect(page.locator(".rio-phase-detail")).toHaveCount(0);
    await page.locator(".rio-phase-now").click();
    const planBox = await page.evaluate(() => {
      const main = document.querySelector("main");
      const column = document.querySelector(".rio-plan-main");
      const cal = document.querySelector(".rio-cal");
      const bar = document.querySelector(".rio-phase-bar");
      const panel = document.querySelector(".rio-phase-detail");
      if (!main || !column || !cal || !bar || !panel) return null;
      const style = getComputedStyle(main);
      const content = main.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
      const button = document.querySelector(".rio-phase-week-list button");
      return {
        scroll: document.documentElement.scrollWidth,
        client: document.documentElement.clientWidth,
        split: document.querySelectorAll(".rio-plan-split").length,
        content,
        col: column.getBoundingClientRect().width,
        cal: cal.getBoundingClientRect().width,
        panelTop: panel.getBoundingClientRect().top,
        barBottom: bar.getBoundingClientRect().bottom,
        panelLeft: panel.getBoundingClientRect().left,
        barLeft: bar.getBoundingClientRect().left,
        weekButton: button ? Math.round(button.getBoundingClientRect().height) : 0,
      };
    });
    expect(planBox, `${width} plan`).not.toBeNull();
    expect(planBox!.split, `${width} phase column`).toBe(0);
    expect(planBox!.scroll, `${width} plan overflow`).toBeLessThanOrEqual(planBox!.client + 1);
    expect(Math.abs(planBox!.col - planBox!.content), `${width} calendar column`).toBeLessThan(4);
    expect(planBox!.cal, `${width} calendar`).toBeGreaterThan(planBox!.col * 0.95);
    expect(planBox!.panelTop, `${width} phase dropdown`).toBeGreaterThanOrEqual(planBox!.barBottom - 2);
    expect(Math.abs(planBox!.panelLeft - planBox!.barLeft), `${width} phase alignment`).toBeLessThan(8);
    expect(planBox!.weekButton, `${width} week button`).toBeGreaterThanOrEqual(44);

    await page.goto(`/session?date=${easy}`);
    await expect(page.getByRole("region", { name: "Before workout" })).toBeVisible();
    await expect(page.locator(".rio-session-log")).toHaveCount(0);
    await expect(page.getByText("Log", { exact: true })).toHaveCount(0);
    await expect(page.getByLabel("Rep 1")).toHaveCount(0);
    const easyStack = await page.evaluate(() => {
      const groups = [...document.querySelectorAll(".rio-session-group")].map((node) => {
        const box = node.getBoundingClientRect();
        return { label: node.getAttribute("aria-label"), top: box.top, left: box.left };
      });
      return { groups, scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth };
    });
    expect(easyStack.groups.map((group) => group.label), `${width} easy groups`).toEqual([
      "Before workout",
      "Workout",
      "After workout",
    ]);
    expect(easyStack.scroll, `${width} easy overflow`).toBeLessThanOrEqual(easyStack.client + 1);
    for (let index = 1; index < easyStack.groups.length; index += 1) {
      expect(easyStack.groups[index].top, `${width} easy stack`).toBeGreaterThan(easyStack.groups[index - 1].top);
      expect(Math.abs(easyStack.groups[index].left - easyStack.groups[0].left), `${width} easy column`).toBeLessThan(2);
    }

    await page.goto(`/session?date=${quality}`);
    await expect(page.locator(".rio-session-log")).toHaveCount(0);
    await expect(page.getByRole("region", { name: "Workout" }).getByLabel("Rep 1")).toBeVisible();
    const qualityStack = await page.evaluate(() => {
      const groups = [...document.querySelectorAll(".rio-session-group")].map((node) => node.getBoundingClientRect().left);
      const workout = document.querySelector('[aria-label="Workout"]');
      const cards = workout
        ? [...workout.children]
            .filter((node) => node.classList.contains("rio-card"))
            .map((node) => node.getBoundingClientRect().top)
        : [];
      return {
        spread: groups.length ? Math.max(...groups) - Math.min(...groups) : 0,
        cards,
        scroll: document.documentElement.scrollWidth,
        client: document.documentElement.clientWidth,
      };
    });
    expect(qualityStack.scroll, `${width} quality overflow`).toBeLessThanOrEqual(qualityStack.client + 1);
    expect(qualityStack.spread, `${width} quality column`).toBeLessThan(2);
    expect(qualityStack.cards.length, `${width} workout card`).toBeGreaterThanOrEqual(1);
    const blocks = await page.evaluate(() => {
      const group = document.querySelector('[aria-label="After workout"]');
      const cards = group
        ? [...group.children].filter((node) => node.classList.contains("rio-session-box") || node.classList.contains("rio-foam-block"))
        : [];
      const boxes = cards.map((node) => {
        const box = node.getBoundingClientRect();
        return { top: box.top, width: Math.round(box.width) };
      });
      const meaning = document.querySelector(".rio-contact .rio-page-meaning");
      const privacy = document.querySelector(".rio-legal-links a");
      const meaningBox = meaning?.getBoundingClientRect();
      const privacyBox = privacy?.getBoundingClientRect();
      return {
        widths: boxes.map((box) => box.width),
        gaps: boxes.slice(1).map((box, index) => Math.round(box.top - boxes[index].top - cards[index].getBoundingClientRect().height)),
        meaningWidth: meaningBox ? Math.round(meaningBox.width) : 0,
        sameRow: meaningBox && privacyBox ? Math.abs(meaningBox.top - privacyBox.top) < 8 : false,
        note: document.querySelector('[aria-label="After workout"] .rio-medical')?.textContent || "",
      };
    });
    const uniqueWidths = [...new Set(blocks.widths)];
    expect(uniqueWidths, `${width} session cards`).toHaveLength(1);
    expect(Math.max(...blocks.gaps) - Math.min(...blocks.gaps), `${width} foam gap`).toBeLessThan(4);
    expect(blocks.sameRow, `${width} page note`).toBe(true);
    expect(blocks.meaningWidth, `${width} page note width`).toBeLessThan(280);
    expect(blocks.note).toContain("Not medical advice");
  }

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto("/more");
  await expect(page.locator(".rio-more-row")).toHaveCount(6);
  const more = await page.evaluate(() => {
    const tiles = [...document.querySelectorAll(".rio-more-row")].map((node) => node.getBoundingClientRect());
    const edge = Math.max(...tiles.map((box) => box.right));
    const rows = new Map<number, number>();
    for (const box of tiles) {
      const key = Math.round(box.top);
      rows.set(key, Math.max(rows.get(key) || 0, box.right));
    }
    return {
      count: tiles.length,
      short: [...rows.values()].filter((right) => edge - right > 2).length,
    };
  });
  expect(more.count).toBe(6);
  expect(more.short).toBe(0);

  await page.goto("/recovery");
  await expect(page.locator(".rio-recover-ask")).toBeVisible();
  const recovery = await page.evaluate(() => {
    const main = document.querySelector("main");
    const ask = document.querySelector(".rio-recover-ask");
    if (!main || !ask) return null;
    const style = getComputedStyle(main);
    const content = main.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    return { content, ask: ask.getBoundingClientRect().width };
  });
  expect(recovery).not.toBeNull();
  expect(recovery!.ask).toBeGreaterThan(recovery!.content * 0.6);
  expect(recovery!.ask).toBeLessThan(recovery!.content * 0.75);
  const meaning = await page.locator(".rio-meaning-card").boundingBox();
  expect(meaning && meaning.width).toBeGreaterThan(200);

  const signedOut = await browser.newContext();
  const fresh = await signedOut.newPage();
  await fresh.setViewportSize({ width: 375, height: 812 });
  await fresh.goto("/sign-in?skip=1");
  await expect(fresh.locator(".rio-auth-about a")).toBeVisible();
  const about = await fresh.locator(".rio-auth-about a").boundingBox();
  expect(about && Math.round(about.height)).toBeGreaterThanOrEqual(44);
  await fresh.goto("/create-account");
  await expect(fresh.locator(".rio-auth-about a")).toBeVisible();
  const create = await fresh.locator(".rio-auth-about a").boundingBox();
  expect(create && Math.round(create.height)).toBeGreaterThanOrEqual(44);
  await signedOut.close();
});
