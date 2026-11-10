/** Remaining pages after plan. One login. Failures do not stop the walk. */
import { chromium } from "@playwright/test";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const OUT = "/tmp/parity-evidence";
const NEXT = "http://localhost:3000";
const STREAM = "http://localhost:8501";
const PASSWORD = "correct-horse";

async function settle(page) {
  await page
    .addStyleTag({
      content: `[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }`,
    })
    .catch(() => {});
  await page.waitForTimeout(700);
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

async function login(page, base, email) {
  if (base === "stream") {
    await page.goto(STREAM);
    await page.getByRole("button", { name: "Continue" }).click();
    await page.getByLabel("Email", { exact: true }).fill(email);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Log in", exact: true }).click();
  } else {
    await page.goto(`${NEXT}/sign-in`);
    await page.getByRole("heading", { name: "Log in" }).waitFor();
    await page.waitForTimeout(400);
    await page.locator("#email").fill(email);
    await page.locator("#password").fill(PASSWORD);
    await page.getByRole("button", { name: "Log in", exact: true }).click();
  }
  await page.getByRole("link", { name: "Activity", exact: true }).first().waitFor({ timeout: 30000 });
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const next = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
  const stream = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
  await login(next, "next", "parity@example.com");
  await login(stream, "stream", "parity@example.com");

  const jobs = [
    async () => {
      await next.goto(`${NEXT}/session?date=2026-11-10`);
      await stream.getByRole("link", { name: "Start session" }).first().click();
      await next.getByText("23.0 s").waitFor({ timeout: 20000 });
      await stream.getByText("23.0 s").waitFor({ timeout: 20000 });
      await shot(next, "next-session");
      await shot(stream, "stream-session");
    },
    async () => {
      await next.goto(`${NEXT}/activity`);
      await stream.getByRole("link", { name: "Activity", exact: true }).first().click();
      await next.getByRole("heading", { name: "Activity" }).waitFor({ timeout: 20000 });
      await stream.getByRole("heading", { name: "Activity" }).waitFor({ timeout: 20000 });
      await shot(next, "next-activity");
      await shot(stream, "stream-activity");
    },
    async () => {
      await next.goto(`${NEXT}/library`);
      await stream.getByRole("link", { name: "Library", exact: true }).first().click();
      await next.getByRole("heading", { name: "Library" }).waitFor({ timeout: 20000 });
      await stream.getByRole("heading", { name: "Library" }).waitFor({ timeout: 20000 });
      await shot(next, "next-library");
      await shot(stream, "stream-library");
    },
    async () => {
      await next.goto(`${NEXT}/more`);
      await stream.getByRole("link", { name: "More", exact: true }).first().click();
      await next.getByRole("heading", { name: "More", exact: true }).waitFor({ timeout: 20000 });
      await stream.getByRole("heading", { name: "More", exact: true }).waitFor({ timeout: 20000 });
      await shot(next, "next-more");
      await shot(stream, "stream-more");
    },
  ];
  for (const job of jobs) {
    try {
      await job();
      console.log("ok");
    } catch (error) {
      console.error("FAILED", error.message.split("\n")[0]);
    }
  }

  const more = [
    ["/past-seasons", "Past seasons", "past"],
    ["/profile", "Profile", "profile"],
    ["/settings", "Settings", "settings"],
    ["/about", "About", "about"],
    ["/creators", "Creators", "creators"],
  ];
  for (const [pathname, label, name] of more) {
    try {
      await next.goto(`${NEXT}${pathname}`);
      await stream.getByRole("link", { name: label, exact: true }).first().click();
      if (name === "settings") {
        await next.locator("details").evaluateAll((nodes) => nodes.forEach((node) => (node.open = true)));
        const buttons = stream.locator('[data-testid="stExpander"] details');
        const count = await buttons.count();
        for (let index = 0; index < count; index += 1) await buttons.nth(index).evaluate((node) => (node.open = true));
      }
      const heading = name === "creators" ? "Built by a runner, for runners." : label;
      await next.getByRole("heading", { name: heading }).waitFor({ timeout: 20000 });
      await stream.getByRole("heading", { name: heading }).waitFor({ timeout: 20000 });
      await shot(next, `next-${name}`);
      await shot(stream, `stream-${name}`);
      console.log("ok", name);
    } catch (error) {
      console.error("FAILED", name, error.message.split("\n")[0]);
    }
  }

  try {
    await login(next, "next", "admin@example.com");
    await login(stream, "stream", "admin@example.com");
    await next.goto(`${NEXT}/admin`);
    await stream.getByRole("link", { name: "Admin", exact: true }).first().click();
    await next.getByRole("heading", { name: "Admin" }).waitFor({ timeout: 20000 });
    await stream.getByRole("heading", { name: "Admin" }).waitFor({ timeout: 20000 });
    await shot(next, "next-admin");
    await shot(stream, "stream-admin");
    await next.goto(`${NEXT}/library`);
    await stream.getByRole("link", { name: "Library", exact: true }).first().click();
    await next.getByText("aer_4000_r0_x1").first().waitFor({ timeout: 20000 });
    await stream.getByText("aer_4000_r0_x1").first().waitFor({ timeout: 20000 });
    await shot(next, "next-library-ids");
    await shot(stream, "stream-library-ids");
    await next.goto(`${NEXT}/home`);
    await stream.getByRole("link", { name: "Home", exact: true }).first().click();
    await shot(next, "next-home-ids");
    await shot(stream, "stream-home-ids");
    console.log("ok admin");
  } catch (error) {
    console.error("FAILED admin", error.message.split("\n")[0]);
  }

  await browser.close();
  execFileSync("python3", ["/agent/repos/rio/scripts/parity_compose.py", OUT], { stdio: "inherit" });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
