import { expect, type Page } from "@playwright/test";

/** A new account stops on heart rate before the easy-pace question. */
export async function saveMeasuredHeartRate(page: Page, resting = "60", max = "180") {
  await expect(page.getByRole("heading", { name: "Heart rate" })).toBeVisible();
  await page.getByLabel("Resting heart rate").fill(resting);
  await page.getByLabel("Max heart rate").fill(max);
  await page.getByRole("button", { name: "Save heart rate" }).click();
}
