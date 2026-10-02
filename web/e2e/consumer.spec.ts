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
  // Push is on in the test API, so the notification choice appears with its privacy note.
  await expect(page.getByText("Only the reminder texts and dates go to our server, never your birth details.")).toBeVisible();
  // Any question in one's own words: a suggested one, then a typed one in Hindi.
  await page.getByRole("button", { name: /^How will \d{4} be for me\?$/ }).click();
  const conversation = page.getByRole("log", { name: "Conversation about your chart" });
  await expect(conversation.getByText(/^\d{4}: you turn \d+ on your birthday\./)).toBeVisible();
  await expect(conversation.getByText(/^Offline answer:/)).toBeVisible();
  await page.getByLabel("Your question").fill("मेरा सातवाँ भाव क्या बताता है?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(conversation.getByText(/^House 7 \(marriage and partnerships\)/)).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("button", { name: "Switch the interface to Hindi" }).click();
  await expect(page.getByRole("heading", { name: "नमस्ते, Asha" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "आज" })).toBeVisible();
  await expect(page.getByText(/राहु काल/).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "अपनी कुंडली के बारे में कुछ भी पूछें" })).toBeVisible();
  await expect(page.getByRole("log", { name: "आपकी कुंडली पर बातचीत" })).toBeVisible();
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
