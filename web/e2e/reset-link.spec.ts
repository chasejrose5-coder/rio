import { expect, test, type Page } from "@playwright/test";

async function captureReset(page: Page) {
  let posted: Record<string, string> | null = null;
  await page.route("**/auth/reset-password", async (route) => {
    posted = route.request().postDataJSON() as Record<string, string>;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true, message: "Password updated. Log in with the new one." }),
    });
  });
  return {
    async submit() {
      await page.getByLabel("New password").fill("another-horse");
      await page.getByRole("button", { name: "Save password" }).click();
      await expect(page).toHaveURL(/\/sign-in\?note=/);
      return posted;
    },
  };
}

test("a query token_hash opens the reset form and is the token that is saved", async ({ page }) => {
  const reset = await captureReset(page);
  await page.goto("/reset-password?token_hash=hashed-token&token=plain-token&type=recovery");
  await expect(page.getByRole("heading", { name: "New password" })).toBeVisible();
  await expect(page.getByText("That reset link is no longer valid.")).toHaveCount(0);
  const posted = await reset.submit();
  expect(posted?.token).toBe("hashed-token");
  expect(posted?.type).toBe("recovery");
  expect(posted?.access_token || "").toBe("");
});

test("a hash fragment token and a recovery session are accepted", async ({ page }) => {
  const reset = await captureReset(page);
  await page.goto("/reset-password?reset=password#token_hash=from-hash&type=recovery");
  await expect(page.getByRole("heading", { name: "New password" })).toBeVisible();
  const fromHash = await reset.submit();
  expect(fromHash?.token).toBe("from-hash");

  await page.goto("/reset-password#access_token=frag-access&refresh_token=frag-refresh&token_type=bearer&type=recovery");
  await expect(page.getByRole("button", { name: "Save password" })).toBeEnabled();
  const fromSession = await reset.submit();
  expect(fromSession?.token || "").toBe("");
  expect(fromSession?.access_token).toBe("frag-access");
  expect(fromSession?.refresh_token).toBe("frag-refresh");
  expect(fromSession?.type).toBe("recovery");
});

test("a link with no recovery token stays closed", async ({ page }) => {
  await page.goto("/reset-password");
  await expect(page.getByRole("heading", { name: "New password" })).toBeVisible();
  await expect(page.getByText("That reset link is no longer valid.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save password" })).toBeDisabled();

  await page.goto("/reset-password#access_token=frag-access&refresh_token=frag-refresh&type=signup");
  await expect(page.getByRole("button", { name: "Save password" })).toBeDisabled();
});
