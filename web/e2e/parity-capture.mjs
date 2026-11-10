/**
 * One-shot visual parity capture. Not part of `npm test`.
 * Both apps must already be listening, on the same local account file.
 *
 *   NEXT  http://localhost:3000
 *   API   http://localhost:8000
 *   STREAMLIT http://localhost:8501
 */
import { chromium } from "@playwright/test";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const OUT = process.env.PARITY_OUT || "/tmp/parity-evidence";
const API = process.env.NEXT_PUBLIC_RIO_API_URL || "http://localhost:8000";
const NEXT = "http://localhost:3000";
const STREAM = "http://localhost:8501";

function streamUrl(pathname) {
  const join = pathname.includes("?") ? "&" : "?";
  return `${STREAM}${pathname}${join}skip=1`;
}
const PASSWORD = "correct-horse";
const ATHLETE = "parity@example.com";
const ADMIN = "admin@example.com";

fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(path.join(OUT, "text"), { recursive: true });

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function api(pathname, options = {}) {
  const response = await fetch(`${API}${pathname}`, {
    ...options,
    headers: {
      "content-type": "application/json",
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let body = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  return { status: response.status, body, headers: response.headers };
}

function cookieFrom(response) {
  const cookie = response.headers.getSetCookie?.() || [];
  const raw = cookie.find((item) => item.startsWith("rio_hosted=")) || "";
  return raw.split(";")[0];
}

async function signUp(email, name) {
  const created = await api("/auth/sign-up", {
    method: "POST",
    body: JSON.stringify({ email, password: PASSWORD, name }),
  });
  if (created.status === 200) return cookieFrom(created);
  const signed = await api("/auth/sign-in", {
    method: "POST",
    body: JSON.stringify({ email, password: PASSWORD }),
  });
  if (signed.status !== 200) {
    throw new Error(`sign-up ${email} ${created.status} ${JSON.stringify(created.body)}; sign-in ${signed.status}`);
  }
  return cookieFrom(signed);
}

async function authed(sid, pathname, options = {}) {
  return api(pathname, {
    ...options,
    headers: { cookie: sid, ...(options.headers || {}) },
  });
}

async function seed() {
  const athlete = await signUp(ATHLETE, "Parity");
  let saved = await authed(athlete, "/settings", {
    method: "PATCH",
    body: JSON.stringify({
      timezone: "America/Los_Angeles",
      easy_pace: "7:25",
      easy_pace_unit: "mi",
      intro_seen: true,
      date_format: "iso",
      pace_units: "mi",
      display_name: "Parity",
    }),
  });
  if (saved.status !== 200) throw new Error(`settings ${saved.status} ${JSON.stringify(saved.body)}`);
  const past = await authed(athlete, "/seasons", {
    method: "POST",
    body: JSON.stringify({
      current_time: "2:05.0",
      start_date: "2020-01-06",
      goal_time: "1:55.0",
      goal_date: "2020-04-06",
    }),
  });
  if (past.status !== 200) throw new Error(`past ${past.status} ${JSON.stringify(past.body)}`);
  const current = await authed(athlete, "/seasons", {
    method: "POST",
    body: JSON.stringify({
      current_time: "2:08.0",
      start_date: "2026-11-08",
      goal_time: "1:59.0",
      goal_date: "2027-04-18",
    }),
  });
  if (current.status !== 200) throw new Error(`current ${current.status} ${JSON.stringify(current.body)}`);

  const pace = await signUp("pace@example.com", "Pace");
  await authed(pace, "/settings", {
    method: "PATCH",
    body: JSON.stringify({ timezone: "America/Los_Angeles", intro_seen: false }),
  });

  const intro = await signUp("intro@example.com", "Intro");
  await authed(intro, "/settings", {
    method: "PATCH",
    body: JSON.stringify({
      timezone: "America/Los_Angeles",
      easy_pace: "7:25",
      easy_pace_unit: "mi",
      intro_seen: false,
    }),
  });

  const start = await signUp("start@example.com", "Start");
  await authed(start, "/settings", {
    method: "PATCH",
    body: JSON.stringify({
      timezone: "America/Los_Angeles",
      easy_pace: "7:25",
      easy_pace_unit: "mi",
      intro_seen: true,
    }),
  });

  const admin = await signUp(ADMIN, "Admin");
  await authed(admin, "/settings", {
    method: "PATCH",
    body: JSON.stringify({
      timezone: "America/Los_Angeles",
      easy_pace: "7:25",
      easy_pace_unit: "mi",
      intro_seen: true,
      show_ids: true,
      compact: true,
    }),
  });
  const adminSeason = await authed(admin, "/seasons", {
    method: "POST",
    body: JSON.stringify({
      current_time: "2:08.0",
      start_date: "2026-11-08",
      goal_time: "1:59.0",
      goal_date: "2027-04-18",
    }),
  });
  if (adminSeason.status !== 200) throw new Error(`admin season ${adminSeason.status}`);
}

async function settle(page) {
  await page.addStyleTag({
    content: `
      [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
      [data-testid="stStatusWidget"], #MainMenu, footer { display: none !important; }
    `,
  }).catch(() => {});
  await page.waitForTimeout(800);
}

async function textOf(page) {
  return page.evaluate(() => {
    const root = document.querySelector('[data-testid="stMain"]') || document.querySelector("main") || document.body;
    const visible = root.innerText || "";
    const hidden = [];
    root.querySelectorAll("[hidden]").forEach((node) => {
      const text = (node.textContent || "").replace(/\s+/g, " ").trim();
      if (text) hidden.push(text);
    });
    return { visible, hidden: hidden.join("\n") };
  });
}

async function shot(page, name) {
  await settle(page);
  const png = path.join(OUT, `${name}.png`);
  await page.screenshot({ path: png, fullPage: true });
  const text = await textOf(page);
  fs.writeFileSync(path.join(OUT, "text", `${name}.txt`), text.visible);
  fs.writeFileSync(path.join(OUT, "text", `${name}.hidden.txt`), text.hidden);
  return png;
}

async function streamlitLogin(page, email) {
  await page.goto(`${STREAM}/`, { waitUntil: "domcontentloaded" });
  const cont = page.getByRole("button", { name: "Continue" });
  await cont.waitFor({ timeout: 20000 });
  await cont.click();
  const emailBox = page.getByLabel("Email", { exact: true });
  await emailBox.waitFor({ timeout: 60000 });
  await emailBox.fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page
    .getByRole("heading", { name: /Your easy pace|Start here/ })
    .or(page.getByRole("link", { name: "Home" }))
    .first()
    .waitFor({ timeout: 60000 });
}

async function nextLogin(page, email) {
  await page.goto(`${NEXT}/sign-in`, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Log in" }).waitFor({ timeout: 30000 });
  await page.waitForTimeout(400);
  const emailBox = page.locator("#email");
  const passwordBox = page.locator("#password");
  await emailBox.fill(email);
  await passwordBox.fill(PASSWORD);
  if ((await emailBox.inputValue()) !== email) await emailBox.fill(email);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/sign-in"), { timeout: 30000 });
}

async function openDetails(page) {
  await page.evaluate(() => {
    document.querySelectorAll("details").forEach((node) => {
      node.open = true;
    });
  });
}

async function expandStreamlit(page) {
  const buttons = page.locator('[data-testid="stExpander"] summary, [data-testid="stExpander"] button');
  const count = await buttons.count();
  for (let index = 0; index < count; index += 1) {
    const button = buttons.nth(index);
    const expanded = await button.getAttribute("aria-expanded");
    if (expanded === "false") await button.click();
  }
}

async function capturePair(browser, name, email, go) {
  if (fs.existsSync(path.join(OUT, `next-${name}.png`)) && fs.existsSync(path.join(OUT, `stream-${name}.png`))) {
    console.log("skip", name);
    return;
  }
  const nextContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const streamContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const next = await nextContext.newPage();
  const stream = await streamContext.newPage();
  try {
    await nextLogin(next, email);
    await streamlitLogin(stream, email);
    await go(next, stream);
    await shot(next, `next-${name}`);
    await shot(stream, `stream-${name}`);
    console.log("captured", name);
  } catch (error) {
    console.error("FAILED", name, error);
    await next.screenshot({ path: path.join(OUT, `fail-next-${name}.png`), fullPage: true }).catch(() => {});
    await stream.screenshot({ path: path.join(OUT, `fail-stream-${name}.png`), fullPage: true }).catch(() => {});
  } finally {
    await nextContext.close();
    await streamContext.close();
  }
}

async function recordNewAccount(browser) {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: OUT, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();
  const email = "newcomer3906b@example.com";
  try {
    await page.goto(NEXT, { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByRole("link", { name: "Create account" }).click();
    await page.getByLabel("Name").fill("Jay");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Create account", exact: true }).click();
    await page.getByLabel("Easy pace").waitFor({ timeout: 30000 });
    await sleep(900);
    await page.getByLabel("Easy pace").fill("7:25");
    await page.getByRole("button", { name: "Save easy pace" }).click();
    await page.getByRole("heading", { name: "Start here" }).waitFor({ timeout: 30000 });
    await sleep(1200);
    await page.getByRole("button", { name: "Done" }).click();
    await page.getByRole("heading", { name: "Start" }).waitFor({ timeout: 30000 });
    await sleep(800);
    await page.locator("#current-time").fill("2:08.0");
    await page.locator("#start-date").fill("2026-11-15");
    await page.locator("#goal-time").fill("1:59.0");
    await page.locator("#goal-date").fill("2027-04-18");
    await sleep(600);
    await page.getByRole("button", { name: "Generate season plan" }).click();
    await page.getByRole("button", { name: "Not now" }).waitFor({ timeout: 30000 });
    await sleep(1200);
    await page.getByRole("button", { name: "Not now" }).click();
    const nav = page.getByRole("navigation", { name: "Pages" });
    await nav.getByRole("link", { name: "Home" }).waitFor();
    await sleep(1000);
    await nav.getByRole("link", { name: "Plan" }).click();
    await page.getByRole("heading", { name: /weeks|Plan/ }).first().waitFor({ timeout: 30000 });
    await sleep(1200);
    await nav.getByRole("link", { name: "Start session" }).click();
    await sleep(1500);
    await nav.getByRole("link", { name: "Activity" }).click();
    await sleep(1200);
    await nav.getByRole("link", { name: "More" }).click();
    await sleep(800);
    const more = page.getByRole("navigation", { name: "More" });
    await more.getByRole("link", { name: "Settings" }).click();
    await sleep(1200);
    await more.getByRole("link", { name: "Past seasons" }).click();
    await sleep(1000);
    await more.getByRole("link", { name: "About" }).click();
    await sleep(1200);
    await more.getByRole("link", { name: "Creators" }).click();
    await sleep(1200);
    await page.getByRole("button", { name: "Log out" }).click();
    await page.getByRole("heading", { name: "Log in" }).waitFor({ timeout: 30000 });
    await sleep(800);
    console.log("video flow finished");
  } catch (error) {
    console.error("VIDEO FAILED", error);
    await page.screenshot({ path: path.join(OUT, "fail-video.png"), fullPage: true }).catch(() => {});
  } finally {
    await context.close();
  }
}

async function main() {
  await seed();
  const browser = await chromium.launch({ headless: true });
  try {
    if (process.env.SKIP_VIDEO !== "1") await recordNewAccount(browser);

    const guest = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const next = await guest.newPage();
    const stream = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
    await next.goto(NEXT, { waitUntil: "domcontentloaded" });
    await stream.goto(STREAM, { waitUntil: "domcontentloaded" });
    await stream.getByRole("button", { name: "Continue" }).waitFor({ timeout: 60000 });
    await shot(next, "next-splash");
    await shot(stream, "stream-splash");
    await next.getByRole("button", { name: "Continue" }).click();
    await stream.getByRole("button", { name: "Continue" }).click();
    await next.getByRole("heading", { name: "Log in" }).waitFor();
    await stream.getByLabel("Email").waitFor({ timeout: 30000 });
    await shot(next, "next-login");
    await shot(stream, "stream-login");
    await next.getByRole("link", { name: "Create account" }).click();
    await stream.getByRole("button", { name: "Create account" }).click();
    await next.getByLabel("Name").waitFor();
    await stream.getByLabel("Name").waitFor({ timeout: 30000 });
    await shot(next, "next-create");
    await shot(stream, "stream-create");
    await guest.close();

    await capturePair(browser, "easy-pace", "pace@example.com", async (n, s) => {
      await n.getByRole("heading", { name: "Your easy pace" }).waitFor({ timeout: 30000 });
      await s.getByRole("heading", { name: "Your easy pace" }).waitFor({ timeout: 30000 });
    });
    await capturePair(browser, "intro", "intro@example.com", async (n, s) => {
      await n.getByRole("heading", { name: "Start here" }).waitFor({ timeout: 30000 });
      await s.getByRole("heading", { name: "Start here" }).waitFor({ timeout: 30000 });
    });
    await capturePair(browser, "start", "start@example.com", async (n, s) => {
      await n.getByRole("heading", { name: "Start" }).waitFor({ timeout: 30000 });
      await s.getByRole("heading", { name: "Start" }).waitFor({ timeout: 30000 });
    });
    await capturePair(browser, "home", ATHLETE, async (n, s) => {
      await n.getByRole("heading", { name: /days to|Hey/ }).first().waitFor({ timeout: 30000 }).catch(() => {});
      await s.getByText("Hey,").first().waitFor({ timeout: 30000 }).catch(async () => {
        await s.getByText(/days to|No workout/).first().waitFor({ timeout: 30000 });
      });
    });
    await capturePair(browser, "plan-calendar", ATHLETE, async (n, s) => {
      await n.goto(`${NEXT}/plan`);
      await s.goto(streamUrl("/plan"));
      await n.getByText("November 2026").first().waitFor({ timeout: 30000 });
      await s.getByText("November 2026").first().waitFor({ timeout: 30000 });
    });
    await capturePair(browser, "plan-week", ATHLETE, async (n, s) => {
      await n.goto(`${NEXT}/plan`);
      await s.goto(streamUrl("/plan"));
      await n.getByText("This week", { exact: true }).click();
      await s.getByText("This week", { exact: true }).click();
      await sleep(800);
    });
    await capturePair(browser, "plan-season", ATHLETE, async (n, s) => {
      await n.goto(`${NEXT}/plan`);
      await s.goto(streamUrl("/plan"));
      await n.getByText("Full season", { exact: true }).click();
      await s.getByText("Full season", { exact: true }).click();
      await sleep(800);
    });
    await capturePair(browser, "session", ATHLETE, async (n, s) => {
      await n.goto(`${NEXT}/session?date=2026-11-10`);
      await s.goto(streamUrl("/session?date=2026-11-10"));
      await n.getByText(/Run at|Tolerance|Tuesday/).first().waitFor({ timeout: 30000 });
      await s.getByText(/Run at|Tolerance|Tuesday/).first().waitFor({ timeout: 30000 });
    });
    const pages = [
      ["activity", "/activity", "Activity"],
      ["library", "/library", "Library"],
      ["profile", "/profile", "Profile"],
      ["past", "/past-seasons", "Past seasons"],
      ["about", "/about", "About"],
      ["more", "/more", "More"],
    ];
    for (const [name, pathname, heading] of pages) {
      await capturePair(browser, name, ATHLETE, async (n, s) => {
        await n.goto(`${NEXT}${pathname}`);
        await s.goto(streamUrl(pathname));
        await n.getByRole("heading", { name: heading }).waitFor({ timeout: 30000 });
        await s.getByRole("heading", { name: heading }).waitFor({ timeout: 30000 });
      });
    }
    await capturePair(browser, "settings", ATHLETE, async (n, s) => {
      await n.goto(`${NEXT}/settings`);
      await s.goto(streamUrl("/settings"));
      await n.getByRole("heading", { name: "Settings" }).waitFor({ timeout: 30000 });
      await s.getByRole("heading", { name: "Settings" }).waitFor({ timeout: 30000 });
      await openDetails(n);
      await expandStreamlit(s);
      await sleep(400);
    });
    await capturePair(browser, "creators", ATHLETE, async (n, s) => {
      await n.goto(`${NEXT}/creators`);
      await s.goto(streamUrl("/creators"));
      await n.getByRole("heading", { name: "Built by a runner, for runners." }).waitFor({ timeout: 30000 });
      await s.getByRole("heading", { name: "Built by a runner, for runners." }).waitFor({ timeout: 30000 });
    });
    await capturePair(browser, "admin", ADMIN, async (n, s) => {
      await n.goto(`${NEXT}/admin`);
      await s.goto(streamUrl("/admin"));
      await n.getByRole("heading", { name: "Admin" }).waitFor({ timeout: 30000 });
      await s.getByRole("heading", { name: "Admin" }).waitFor({ timeout: 30000 });
    });
    await capturePair(browser, "library-ids", ADMIN, async (n, s) => {
      await n.goto(`${NEXT}/library`);
      await s.goto(streamUrl("/library"));
      await n.getByText("aer_4000_r0_x1").first().waitFor({ timeout: 30000 });
      await s.getByText("aer_4000_r0_x1").first().waitFor({ timeout: 30000 });
    });
    await capturePair(browser, "home-ids", ADMIN, async (n, s) => {
      await n.goto(`${NEXT}/home`);
      await s.goto(streamUrl("/home"));
      await n.getByText(/days to|Hey/).first().waitFor({ timeout: 30000 });
      await s.getByText(/days to|Hey/).first().waitFor({ timeout: 30000 });
    });
    for (const slug of ["last-session", "next", "decisions", "ledger", "goal"]) {
      await capturePair(browser, slug, ADMIN, async (n, s) => {
        await n.goto(`${NEXT}/${slug}`);
        await s.goto(streamUrl(`/${slug}`));
        await n.locator("h1").first().waitFor({ timeout: 30000 });
        await s.locator("h1").first().waitFor({ timeout: 30000 });
      });
    }
  } finally {
    await browser.close();
  }

  execFileSync("python3", ["/agent/repos/rio/scripts/parity_compose.py", OUT], {
    stdio: "inherit",
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
