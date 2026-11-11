import { readFile } from "node:fs/promises";
import { expect, test, type Page, type Route } from "@playwright/test";

const athlete = {
  id: "ada",
  email: "ada@example.com",
  display_name: "Ada",
  role: "athlete",
  kind: "local",
  today: "2026-11-10",
  next_session: "2026-11-10",
  prefs: {
    timezone: "UTC",
    pace_units: "mi",
    units: "miles",
    no_watch: false,
    easy_pace: "7:25",
    easy_pace_unit: "mi",
    intro_seen: true,
    date_format: "short",
    start_date: "today",
    confirm_adapt: false,
    show_ids: false,
    compact: false,
    preferred: "",
  },
};

const season = {
  inputs: {
    current_time: "2:02.9",
    start_date: "2026-04-19",
    goal_time: "1:55.0",
    goal_date: "2027-03-19",
  },
  plan: { season_length_weeks: 12, sessions: [] },
  marks: { "1": "on_track" },
  actuals: { "2026-04-19": { template_id: "aer_800_r0_x1", completed: true } },
};

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function install(
  page: Page,
  options: { empty?: boolean; admin?: boolean; hosted?: boolean; strava?: "off" | "on" | "missing"; failOpen?: string } = {},
) {
  const user = structuredClone(athlete);
  if (options.admin) user.role = "admin";
  if (options.hosted) user.kind = "hosted";
  const patches: Record<string, unknown>[] = [];
  const posts: { path: string; body: unknown }[] = [];
  let connected = options.strava === "on";
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    const method = route.request().method();
    if (path === "/auth/me") return json(route, user);
    if (path === "/auth/google") return json(route, { detail: "Accounts are not available." }, 503);
    if (path === "/seasons/current" && method === "GET") {
      if (options.failOpen) return json(route, { detail: options.failOpen }, 500);
      if (options.empty) return json(route, { detail: "No current season." }, 404);
      return json(route, season);
    }
    if (path === "/settings" && method === "PATCH") {
      const body = route.request().postDataJSON() as Record<string, unknown>;
      patches.push(body);
      if (body.display_name === "!!!") return json(route, { detail: "Enter a name." }, 400);
      if (body.timezone === "Not/AZone") return json(route, { detail: "Choose a time zone from the list." }, 400);
      if (typeof body.display_name === "string") user.display_name = body.display_name;
      if (typeof body.preferred === "string") user.prefs.preferred = body.preferred;
      if (typeof body.timezone === "string") user.prefs.timezone = body.timezone;
      if (body.timezone === "Pacific/Auckland") user.today = "2026-11-11";
      if (typeof body.no_watch === "boolean") user.prefs.no_watch = body.no_watch;
      if (typeof body.pace_units === "string") user.prefs.pace_units = body.pace_units;
      if (typeof body.compact === "boolean") user.prefs.compact = body.compact;
      if (typeof body.show_ids === "boolean") user.prefs.show_ids = body.show_ids;
      if (typeof body.date_format === "string") user.prefs.date_format = body.date_format;
      if (typeof body.start_date === "string") user.prefs.start_date = body.start_date;
      if (typeof body.confirm_adapt === "boolean") user.prefs.confirm_adapt = body.confirm_adapt;
      if (typeof body.intro_seen === "boolean") user.prefs.intro_seen = body.intro_seen;
      return json(route, user);
    }
    if (path === "/auth/password" && method === "POST") {
      const body = route.request().postDataJSON() as { current_password?: string };
      posts.push({ path, body });
      if (body.current_password !== "correct-horse") return json(route, { detail: "Password does not match." }, 400);
      return json(route, { ok: true, message: "Password updated." });
    }
    if (path === "/auth/email" && method === "POST") {
      const body = route.request().postDataJSON() as { email?: string; password?: string };
      posts.push({ path, body });
      if (body.password !== "correct-horse") return json(route, { detail: "Password does not match." }, 400);
      if (body.email === "taken@example.com") {
        return json(route, { detail: "An account with that email already exists." }, 400);
      }
      user.email = String(body.email || user.email).toLowerCase();
      const message = options.hosted ? "Check your email to confirm the new address." : "Email updated.";
      return json(route, { ok: true, email: user.email, message });
    }
    if (path === "/auth/delete" && method === "POST") {
      const body = route.request().postDataJSON() as { confirm?: boolean; email?: string; password?: string };
      posts.push({ path, body });
      if (body.confirm !== true) return json(route, { detail: "Confirm to delete this account." }, 400);
      if (!options.hosted && body.email?.toLowerCase() !== user.email) {
        return json(route, { detail: "Confirm with your email to delete this account." }, 400);
      }
      if (!options.hosted && body.password !== "correct-horse") return json(route, { detail: "Password does not match." }, 400);
      return json(route, { deleted: true });
    }
    if (path === "/seasons/current/clear" && method === "POST") {
      posts.push({ path, body: route.request().postDataJSON() });
      return json(route, { ...season, marks: {}, actuals: {} });
    }
    if (path === "/seasons/reset" && method === "POST") {
      posts.push({ path, body: route.request().postDataJSON() });
      return json(route, { reset: true });
    }
    if (path === "/auth/sign-out") return json(route, { ok: true });
    if (path === "/strava/status") {
      if (options.strava === "on" || options.strava === "off") {
        return json(route, {
          configured: true,
          connected,
          athlete_name: connected ? "Ada Run" : "",
          last_sync_at: null,
        });
      }
      return json(route, { configured: false, connected: false, athlete_name: "", last_sync_at: null });
    }
    if (path === "/strava/connect") return json(route, { url: "https://www.strava.com/oauth/authorize?state=test" });
    if (path === "/strava/disconnect") {
      connected = false;
      return json(route, { connected: false });
    }
    return json(route, { detail: "Not mocked." }, 404);
  });
  return { user, patches, posts };
}

async function openSettings(page: Page) {
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
}

test("settings shows every section, and the hidden leftovers stay hidden", async ({ page }) => {
  await install(page);
  await openSettings(page);
  const summaries = page.locator(".page-settings summary");
  await expect(summaries).toHaveText([
    "Profile",
    "Logging",
    "Preferences",
    "Data",
    "Account",
    "Privacy",
    "About",
    "Strava",
    "Danger zone",
  ]);
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("SYNTHETIC");
  await expect(page.locator("body")).not.toContainText("DEMO");
  await expect(page.getByText("First name is enough. Saved on this machine.")).toBeVisible();
  await expect(page.locator("#settings-email")).toBeDisabled();
  await expect(page.locator("#settings-timezone")).toHaveValue("UTC");
  await expect(page.getByRole("button", { name: "Change password" })).toBeVisible();
  const hidden = page.locator(".page-settings [hidden]");
  await expect(hidden).toContainText("Notifications");
  await expect(hidden).toContainText("Placeholder. Nothing is sent.");
  await expect(hidden).toBeHidden();
  await expect(page.getByText("Theme", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Show template ids")).toHaveCount(0);
  await expect(page.locator(".rio-settings-kept")).toContainText("Delete account");
  await expect(page.locator(".rio-settings-kept")).toBeHidden();
  const label = page.locator("label[for='settings-name']");
  const input = page.locator("#settings-name");
  const labelColor = await label.evaluate((el) => getComputedStyle(el).color);
  const inputColor = await input.evaluate((el) => getComputedStyle(el).color);
  expect(labelColor).toBe("rgb(18, 17, 16)");
  expect(inputColor).toBe("rgb(18, 17, 16)");
  const labelBox = await label.boundingBox();
  const inputBox = await input.boundingBox();
  expect(labelBox && inputBox && inputBox.y > labelBox.y).toBeTruthy();
  expect(inputBox && labelBox && inputBox.width > labelBox.width * 0.8).toBeTruthy();
});

test("a rejected name stays an error and the saved name is unchanged", async ({ page }) => {
  const state = await install(page);
  await openSettings(page);
  await page.locator("#settings-name").fill("!!!");
  await page.locator("#settings-name").blur();
  await expect(page.locator(".rio-error")).toHaveText("Enter a name.");
  expect(state.patches.some((patch) => patch.display_name === "!!!")).toBeFalsy();
  await page.reload();
  await expect(page.locator("#settings-name")).toHaveValue("Ada");
});

test("timezone, pace, and each toggle are saved", async ({ page }) => {
  const state = await install(page, { admin: true });
  await openSettings(page);
  await page.locator("#settings-timezone").selectOption("Pacific/Auckland");
  await expect.poll(() => state.user.prefs.timezone).toBe("Pacific/Auckland");
  await expect(page.getByLabel("I don't use a watch")).toBeVisible();
  await page.getByLabel("I don't use a watch").check();
  await page.locator("summary", { hasText: "Preferences" }).click();
  await page.getByLabel("per km").check();
  await page.getByLabel("Next Sunday").check();
  await page.getByLabel("Show template ids").check();
  await page.getByLabel("Compact mode").check();
  await page.getByLabel("ISO").check();
  await page.getByLabel("Ask me before a timed run changes later weeks").check();
  await expect.poll(() => state.patches.map((patch) => Object.keys(patch)[0])).toEqual([
    "timezone",
    "no_watch",
    "pace_units",
    "start_date",
    "show_ids",
    "compact",
    "date_format",
    "confirm_adapt",
  ]);
  await page.reload();
  await expect(page.locator("#settings-timezone")).toHaveValue("Pacific/Auckland");
  await expect(page.getByLabel("I don't use a watch")).toBeChecked();
  await page.locator("#settings-current-password").fill("secret");
  await expect(page.locator("#settings-current-password")).toHaveAttribute("type", "password");
  await page.getByRole("button", { name: "Show password" }).first().click();
  await expect(page.locator("#settings-current-password")).toHaveAttribute("type", "text");
});

test("show intro guide opens the guide again", async ({ page }) => {
  const state = await install(page);
  await openSettings(page);
  await page.locator("summary", { hasText: "Preferences" }).click();
  await page.getByRole("button", { name: "Show intro guide" }).click();
  await expect(page).toHaveURL(/\/intro$/);
  await expect(page.getByRole("heading", { name: "Start here" })).toBeVisible();
  expect(state.patches.at(-1)).toEqual({ intro_seen: false });
});

test("export downloads the season, and an empty account says to start", async ({ page }) => {
  await install(page);
  await openSettings(page);
  await page.locator("summary", { hasText: "Data" }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export season as JSON" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("rio-season.json");
  const file = await download.path();
  expect(file).toBeTruthy();
  const text = await readFile(file as string, "utf8");
  const parsed = JSON.parse(text) as Record<string, string>;
  expect(parsed.current_time).toBe("2:02.9");
  expect(parsed.start_date).toBe("2026-04-19");
  expect(parsed.goal_time).toBe("1:55.0");
  expect(parsed.goal_date).toBe("2027-03-19");
  expect(text).not.toContain("password");
  expect(text).not.toContain("seal");
});

test("settings export without a season points at Start", async ({ page }) => {
  await install(page, { empty: true });
  await openSettings(page);
  await page.locator("summary", { hasText: "Data" }).click();
  await expect(page.getByText("Generate a season on Start.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Export season as JSON" })).toHaveCount(0);
});

test("password and email keep the person signed in when the secret is wrong", async ({ page }) => {
  await install(page);
  await openSettings(page);
  await page.getByLabel("Current password").fill("nope");
  await page.getByLabel("New password").fill("another-horse");
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.locator(".rio-error")).toHaveText("Password does not match.");
  await expect(page).toHaveURL(/\/settings$/);
  await page.getByLabel("Current password").fill("correct-horse");
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.locator(".rio-settings-flash")).toHaveText("Password updated.");
  await page.locator("summary", { hasText: "Account" }).click();
  await page.getByLabel("New email").fill("taken@example.com");
  await page.locator("#settings-email-password").fill("correct-horse");
  await page.getByRole("button", { name: "Change email" }).click();
  await expect(page.locator(".rio-error")).toHaveText("An account with that email already exists.");
  await expect(page.locator("#settings-email")).toHaveValue("ada@example.com");
});

test("hosted email success can ask for a confirmation mail", async ({ page }) => {
  await install(page, { hosted: true });
  await openSettings(page);
  await expect(page.getByText("First name is enough. Saved to your RIO account.")).toBeVisible();
  await page.locator("summary", { hasText: "Privacy" }).click();
  await expect(
    page.locator("details", { has: page.locator("summary", { hasText: /^Privacy$/ }) }).locator(".rio-settings-note"),
  ).toHaveText("Signs you out on this browser. Your season stays in your account.");
  await page.locator("summary", { hasText: "Account" }).click();
  await page.getByLabel("New email").fill("ada.new@example.com");
  await page.locator("#settings-email-password").fill("correct-horse");
  await page.getByRole("button", { name: "Change email" }).click();
  await expect(page.locator(".rio-settings-flash")).toHaveText("Check your email to confirm the new address.");
});

test("about is the version, and strava shows connect or disconnect", async ({ page }) => {
  await install(page, { strava: "missing" });
  await openSettings(page);
  await page.locator("summary", { hasText: "About" }).click();
  await expect(page.getByText("RIO 0.1")).toBeVisible();
  await page.locator("summary", { hasText: "Strava" }).click();
  await expect(page.getByText("Strava is not set up on this server yet.")).toBeVisible();
});

test("a configured strava account can disconnect", async ({ page }) => {
  await install(page, { strava: "on" });
  await openSettings(page);
  await page.locator("summary", { hasText: "Strava" }).click();
  await expect(page.getByText("Connected as Ada Run.")).toBeVisible();
  await expect(page.getByText("Strava data is only visible to you.")).toBeVisible();
  await page.getByRole("button", { name: "Disconnect" }).click();
  await expect(page.getByRole("button", { name: "Connect with Strava" })).toBeVisible();
});

test("danger actions ask before they run", async ({ page }) => {
  const state = await install(page);
  await openSettings(page);
  await expect(page.locator(".rio-danger-kicker")).toHaveText("Danger zone");
  await expect(
    page.getByText("Reset the plan, delete this account, or clear this browser. These sit apart from the settings above."),
  ).toBeVisible();
  await page.locator("summary", { hasText: "Danger zone" }).click();
  await page.getByRole("button", { name: "Clear all marks / actuals" }).click();
  await expect(page.locator(".rio-error")).toHaveText("Confirm to clear marks and actuals.");
  await page.getByLabel("Confirm clear").check();
  await page.getByRole("button", { name: "Clear all marks / actuals" }).click();
  await expect(page.locator(".rio-settings-flash")).toHaveText("Marks and actuals are cleared.");
  await page.getByRole("button", { name: "Reset plan" }).click();
  await expect(page.locator(".rio-error")).toHaveText("Confirm to reset the plan.");
  await page.getByRole("button", { name: "Delete my account" }).click();
  await expect(page.locator(".rio-error")).toHaveText("Confirm to delete this account.");
  await page.getByLabel("I understand this permanently deletes my season and runs").check();
  await page.getByRole("button", { name: "Delete my account" }).click();
  await expect(page.locator(".rio-error")).toHaveText("Confirm with your email to delete this account.");
  await page.getByRole("button", { name: "Clear local data" }).click();
  await expect(page.locator(".rio-error")).toHaveText("Confirm to clear local data.");
  expect(state.posts.map((post) => post.path)).toEqual(["/seasons/current/clear"]);
  await expect(page.locator(".rio-expander-danger").getByText("Clears this browser. The account stays on this machine.")).toBeVisible();
  await expect(page.getByText("Reset removes stored seasons. The account stays.")).toBeVisible();
});

test("save failures use the account sentences", async ({ page }) => {
  await install(page, { failOpen: "This account could not be opened." });
  await openSettings(page);
  await expect(page.locator(".rio-error")).toHaveText("This account could not be opened.");
  await page.getByLabel("Current password").fill("correct-horse");
  await page.getByLabel("New password").fill("another-horse");
  await page.route("**/auth/password", async (route) => {
    await json(route, { detail: "This session could not be saved." }, 400);
  });
  await page.getByRole("button", { name: "Change password" }).click();
  await expect(page.locator(".rio-error")).toHaveText("This session could not be saved.");
  await page.locator("summary", { hasText: "Account" }).click();
  await page.route("**/auth/email", async (route) => {
    await json(route, { detail: "This account could not be saved." }, 400);
  });
  await page.getByLabel("New email").fill("ada.new@example.com");
  await page.locator("#settings-email-password").fill("correct-horse");
  await page.getByRole("button", { name: "Change email" }).click();
  await expect(page.locator(".rio-error")).toHaveText("This account could not be saved.");
});
