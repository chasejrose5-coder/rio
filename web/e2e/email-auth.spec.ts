import { expect, test, type Page, type Route } from "@playwright/test";

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

async function hostAuth(page: Page) {
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.port !== "8000") {
      await route.continue();
      return;
    }
    const path = url.pathname;
    if (path === "/auth/availability") return json(route, { mode: "hosted" });
    if (path === "/auth/google") return json(route, { url: "https://example.test/google" });
    if (path === "/auth/me") return json(route, { detail: "Sign in again." }, 401);
    return json(route, { detail: "Not mocked." }, 404);
  });
}

test("hosted sign-up shows check your email and can resend", async ({ page }) => {
  let resent = "";
  await hostAuth(page);
  await page.route("**/auth/sign-up", async (route) => {
    await json(route, { confirm: true, message: "Check your email to confirm your account, then log in." });
  });
  await page.route("**/auth/resend-confirmation", async (route) => {
    resent = (route.request().postDataJSON() as { email: string }).email;
    await json(route, { ok: true, message: "If that address still needs confirmation, we sent another email." });
  });
  await page.goto("/create-account");
  await page.getByLabel("Name").fill("Bea");
  await page.getByLabel("Email").fill("bea@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
  await expect(page.getByText("We sent a confirmation link to bea@example.com.")).toBeVisible();
  await expect(page.getByText("The account could not be created.")).toHaveCount(0);
  await page.getByRole("button", { name: "Resend confirmation email" }).click();
  await expect(page.getByText("If that address still needs confirmation, we sent another email.")).toBeVisible();
  expect(resent).toBe("bea@example.com");
});

test("an unconfirmed sign-in offers a resend, and a rate limit stays visible", async ({ page }) => {
  let calls = 0;
  await hostAuth(page);
  await page.route("**/auth/sign-in", async (route) => {
    calls += 1;
    if (calls === 1) {
      await json(route, { detail: "Check your email to confirm your account, then log in." }, 401);
      return;
    }
    await json(route, { detail: "Too many sign-in attempts. Wait a few minutes and try again." }, 401);
  });
  await page.route("**/auth/resend-confirmation", async (route) => {
    await json(route, { detail: "Too many attempts. Wait a few minutes and try again." }, 429);
  });
  await page.goto("/sign-in");
  await page.getByLabel("Email").fill("bea@example.com");
  await page.getByLabel("Password", { exact: true }).fill("correct-horse");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByText("Check your email to confirm your account, then log in.")).toBeVisible();
  await page.getByRole("button", { name: "Resend confirmation email" }).click();
  await expect(page.getByText("Too many attempts. Wait a few minutes and try again.")).toBeVisible();
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByText("Too many sign-in attempts. Wait a few minutes and try again.")).toBeVisible();
});

test("forgot password uses one sentence and does not name a missing account", async ({ page }) => {
  const seen: string[] = [];
  await hostAuth(page);
  await page.route("**/auth/forgot-password", async (route) => {
    const email = (route.request().postDataJSON() as { email: string }).email;
    seen.push(email);
    if (email === "fast@example.com") {
      await json(route, { detail: "Too many attempts. Wait a few minutes and try again." }, 429);
      return;
    }
    await json(route, { ok: true, message: "Check your email for the reset link." });
  });
  await page.goto("/sign-in");
  await page.getByRole("link", { name: "Forgot password?" }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);
  await page.getByRole("button", { name: "Send reset email" }).click();
  await expect(page.getByText("Enter an email address.")).toBeVisible();
  expect(seen).toEqual([]);
  await page.getByLabel("Email").fill("nobody@example.com");
  await page.getByRole("button", { name: "Send reset email" }).click();
  await expect(page.getByText("Check your email for the reset link.")).toBeVisible();
  await expect(page.getByText(/no account|not found|unknown/i)).toHaveCount(0);
  await page.getByLabel("Email").fill("fast@example.com");
  await page.getByRole("button", { name: "Send reset email" }).click();
  await expect(page.getByText("Too many attempts. Wait a few minutes and try again.")).toBeVisible();
  expect(seen).toEqual(["nobody@example.com", "fast@example.com"]);
});

test("an expired confirmation link and a valid one land on the confirm page", async ({ page }) => {
  await page.goto("/confirm?error=access_denied&error_code=otp_expired");
  await expect(page.getByRole("heading", { name: "Confirm email" })).toBeVisible();
  await expect(page.getByText("That confirmation link is no longer valid.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Log in" })).toBeVisible();

  const sent: { body: Record<string, string> | null } = { body: null };
  await page.route("**/auth/confirm", async (route) => {
    sent.body = route.request().postDataJSON() as Record<string, string>;
    await json(route, {
      ok: true,
      kind: "signup",
      message: "Email confirmed. You can log in.",
      refreshed: false,
    });
  });
  await page.goto("/confirm?token_hash=hashed-token&type=signup");
  await expect(page.getByText("Email confirmed. You can log in.")).toBeVisible();
  expect(sent.body?.token).toBe("hashed-token");
  expect(sent.body?.type).toBe("signup");
  await expect(page).toHaveURL(/\/confirm$/);

  await page.goto("/sign-in");
  await page.goto("/confirm#access_token=frag-access&refresh_token=frag-refresh&type=recovery");
  await expect(page).toHaveURL(/\/update-password/);
  await expect(page.getByRole("heading", { name: "New password" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save password" })).toBeEnabled();
});

test("a confirmation link with no token asks for the email", async ({ page }) => {
  await page.goto("/confirm");
  await expect(page.getByText("Open the confirmation link in your email. It lands on this page.")).toBeVisible();
  await expect(page.getByText("That confirmation link is no longer valid.")).toHaveCount(0);
});
