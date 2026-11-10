/** Click through both apps after one login each. Not part of npm test. */
import { chromium } from "@playwright/test";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const OUT = process.env.PARITY_OUT || "/tmp/parity-evidence";
const NEXT = "http://localhost:3000";
const STREAM = "http://localhost:8501";
const PASSWORD = "correct-horse";
const ATHLETE = "parity@example.com";
const ADMIN = "admin@example.com";

fs.mkdirSync(path.join(OUT, "text"), { recursive: true });

async function settle(page) {
  await page
    .addStyleTag({
      content: `[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }`,
    })
    .catch(() => {});
  await page.waitForTimeout(900);
}

async function shot(page, name) {
  await settle(page);
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: true });
  const text = await page.evaluate(() => {
    const root = document.querySelector('[data-testid="stMain"]') || document.querySelector("main") || document.body;
    const hidden = [];
    root.querySelectorAll("[hidden]").forEach((node) => {
      const value = (node.textContent || "").replace(/\s+/g, " ").trim();
      if (value) hidden.push(value);
    });
    return { visible: root.innerText || "", hidden: hidden.join("\n") };
  });
  fs.writeFileSync(path.join(OUT, "text", `${name}.txt`), text.visible);
  fs.writeFileSync(path.join(OUT, "text", `${name}.hidden.txt`), text.hidden);
}

async function streamlitLogin(page, email) {
  await page.goto(STREAM);
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page.getByRole("link", { name: "Plan", exact: true }).first().waitFor({ timeout: 60000 });
}

async function nextLogin(page, email) {
  await page.goto(`${NEXT}/sign-in`);
  await page.getByRole("heading", { name: "Log in" }).waitFor();
  await page.waitForTimeout(500);
  await page.locator("#email").fill(email);
  await page.locator("#password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page.getByRole("link", { name: "Plan", exact: true }).first().waitFor({ timeout: 30000 });
}

async function pair(next, stream, name) {
  try {
    await shot(next, `next-${name}`);
    await shot(stream, `stream-${name}`);
    console.log("captured", name);
  } catch (error) {
    console.error("shot failed", name, error);
  }
}

async function step(name, action) {
  try {
    await action();
  } catch (error) {
    console.error("FAILED", name, error);
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const nextContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const streamContext = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const next = await nextContext.newPage();
  const stream = await streamContext.newPage();
  await nextLogin(next, ATHLETE);
  await streamlitLogin(stream, ATHLETE);
  await pair(next, stream, "home");

  await next.goto(`${NEXT}/plan`);
  await stream.getByRole("link", { name: "Plan", exact: true }).first().click();
  await next.getByText("23 weeks").waitFor({ timeout: 30000 });
  await stream.getByText("23 weeks").waitFor({ timeout: 30000 });
  await pair(next, stream, "plan-calendar");

  try {
  await next.getByText("This week", { exact: true }).click({ timeout: 8000 });
  await stream.getByText("This week", { exact: true }).click({ timeout: 8000 });
  await next.getByRole("heading", { name: /^Week / }).waitFor({ timeout: 30000 });
  await stream.getByRole("heading", { name: /^Week / }).waitFor({ timeout: 30000 });
  await pair(next, stream, "plan-week");

  await next.getByText("Full season", { exact: true }).click();
  await stream.getByText("Full season", { exact: true }).click();
  await next.getByRole("heading", { name: "Full season" }).waitFor({ timeout: 30000 });
  await stream.getByRole("heading", { name: "Full season" }).waitFor({ timeout: 30000 });
  await pair(next, stream, "plan-season");

  await next.goto(`${NEXT}/session?date=2026-11-10`);
  await stream.getByRole("link", { name: "Start session" }).first().click();
  await next.getByText("Average").waitFor({ timeout: 30000 });
  await stream.getByText("Average").waitFor({ timeout: 30000 });
  await pair(next, stream, "session");

  const top = [
    ["activity", "/activity", "Activity"],
    ["library", "/library", "Library"],
  ];
  for (const [name, pathname, label] of top) {
    await next.goto(`${NEXT}${pathname}`);
    await stream.getByRole("link", { name: label, exact: true }).first().click();
    await next.getByRole("heading", { name: label }).waitFor({ timeout: 30000 });
    await stream.getByRole("heading", { name: label }).waitFor({ timeout: 30000 });
    await pair(next, stream, name);
  }

  await next.goto(`${NEXT}/more`);
  await stream.getByRole("link", { name: "More", exact: true }).first().click();
  await next.getByRole("heading", { name: "More" }).waitFor();
  await stream.getByRole("heading", { name: "More" }).waitFor();
  await pair(next, stream, "more");

  const more = [
    ["past", "/past-seasons", "Past seasons"],
    ["profile", "/profile", "Profile"],
    ["settings", "/settings", "Settings"],
    ["about", "/about", "About"],
    ["creators", "/creators", "Creators"],
  ];
  for (const [name, pathname, label] of more) {
    await next.goto(`${NEXT}${pathname}`);
    await stream.getByRole("link", { name: label, exact: true }).first().click();
    if (name === "settings") {
      await next.locator("details").evaluateAll((nodes) => nodes.forEach((node) => (node.open = true)));
      const buttons = stream.locator('[data-testid="stExpander"] button, [data-testid="stExpander"] summary');
      const count = await buttons.count();
      for (let index = 0; index < count; index += 1) {
        const button = buttons.nth(index);
        if ((await button.getAttribute("aria-expanded")) === "false") await button.click();
      }
    }
    if (name === "creators") {
      await next.getByRole("heading", { name: "Built by a runner, for runners." }).waitFor({ timeout: 30000 });
      await stream.getByRole("heading", { name: "Built by a runner, for runners." }).waitFor({ timeout: 30000 });
    } else {
      await next.getByRole("heading", { name: label, exact: true }).waitFor({ timeout: 30000 });
      await stream.getByRole("heading", { name: label, exact: true }).waitFor({ timeout: 30000 });
    }
    await pair(next, stream, name);
  }

  await nextLogin(next, ADMIN);
  await streamlitLogin(stream, ADMIN);
  await next.goto(`${NEXT}/admin`);
  await stream.getByRole("link", { name: "Admin", exact: true }).first().click();
  await next.getByRole("heading", { name: "Admin" }).waitFor({ timeout: 30000 });
  await stream.getByRole("heading", { name: "Admin" }).waitFor({ timeout: 30000 });
  await pair(next, stream, "admin");

  await next.goto(`${NEXT}/library`);
  await stream.getByRole("link", { name: "Library", exact: true }).first().click();
  await next.getByText("aer_4000_r0_x1").first().waitFor({ timeout: 30000 });
  await stream.getByText("aer_4000_r0_x1").first().waitFor({ timeout: 30000 });
  await pair(next, stream, "library-ids");

  await next.goto(`${NEXT}/home`);
  await stream.getByRole("link", { name: "Home", exact: true }).first().click();
  await next.getByText("150 m").first().waitFor({ timeout: 30000 });
  await stream.getByText("150 m").first().waitFor({ timeout: 30000 });
  await pair(next, stream, "home-ids");

  for (const slug of ["last-session", "next", "decisions", "ledger", "goal"]) {
    await next.goto(`${NEXT}/${slug}`);
    await stream.goto(`${STREAM}/${slug}?skip=1`);
    await next.locator("h1").first().waitFor({ timeout: 30000 });
    await stream.locator("h1").first().waitFor({ timeout: 30000 });
    await pair(next, stream, slug);
  }

  } catch (error) {
    console.error(error);
  } finally {
    await browser.close();
    execFileSync("python3", ["/agent/repos/rio/scripts/parity_compose.py", OUT], { stdio: "inherit" });
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
