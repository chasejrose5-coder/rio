import { expect, type Page } from "@playwright/test";

/** Save resting and max heart rate. A new account is on easy pace, so open the form. */
export async function saveMeasuredHeartRate(page: Page, resting = "60", max = "180") {
  const heading = page.getByRole("heading", { name: "Heart rate", exact: true });
  const easy = page.getByRole("heading", { name: "Your easy pace" });
  await expect(heading.or(easy)).toBeVisible();
  if (!(await heading.isVisible())) {
    await page.goto("/heart-rate");
    await expect(heading).toBeVisible();
  }
  await page.getByLabel("Resting heart rate").fill(resting);
  await page.getByLabel("Max heart rate").fill(max);
  await page.getByRole("button", { name: "Save heart rate" }).click();
}
