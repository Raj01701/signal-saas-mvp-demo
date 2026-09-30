import { expect, test } from "@playwright/test";

import { expectAccessible } from "./helpers";

test("onboarding, dashboard and Hindi", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Get my reading" }).click();
  await expect(page.getByRole("heading", { name: "Your birth details" })).toBeVisible();

  await page.getByLabel("Your name (optional)").fill("Asha");
  await page.getByLabel("Date of birth").fill("1990-05-17");
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByText("Step 2 of 4")).toBeVisible();
  await page.getByLabel("Remembered by the family").check();
  await page.getByLabel("Time of birth (local)").fill("12:00");
  await page.getByLabel("Within 15 minutes").check();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByLabel("Place of birth")).toBeVisible();
  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByRole("heading", { name: "Check your details" })).toBeVisible();
  await page.getByRole("button", { name: "Save and see my reading" }).click();

  await expect(page.getByRole("heading", { name: "Namaste, Asha" })).toBeVisible();
  await expect(page.getByText(/^Rahu kalam \d\d:\d\d–\d\d:\d\d/)).toBeVisible();
  await expect(page.getByText(/mahadasha and the .* antardasha/)).toBeVisible();
  await expect(page.getByRole("list", { name: "The year ahead" }).locator("li").first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Add these to your calendar (.ics)" })).toHaveAttribute("download", "jyotish-reminders.ics");
  await expectAccessible(page);

  await page.getByRole("button", { name: "Switch the interface to Hindi" }).click();
  await expect(page.getByRole("heading", { name: "नमस्ते, Asha" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "आज" })).toBeVisible();
  await expect(page.getByText(/राहु काल/).first()).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  await expectAccessible(page);

  await page.reload();
  await expect(page.getByRole("heading", { name: "आने वाला वर्ष" })).toBeVisible();
  await page.getByRole("navigation").getByRole("link", { name: "पंचांग" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "पंचांग" })).toBeVisible();
  await expect(page.getByRole("button", { name: "पंचांग देखें" })).toBeVisible();
  await expect(page.getByText(/सूर्योदय/).first()).toBeVisible();

  await page.getByRole("navigation").getByRole("link", { name: "मेरी कुंडली" }).click();
  await page.getByRole("button", { name: "इस डिवाइस से हटाएँ" }).click();
  await expect(page.getByRole("heading", { name: "आपका जन्म विवरण" })).toBeVisible();
});
