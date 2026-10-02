import { expect, test } from "@playwright/test";

import { expectAccessible } from "./helpers";

test("rectifies a birth time from events", async ({ page }) => {
  await page.goto("/rectify");
  await page.getByRole("button", { name: "Add event" }).click();
  await page.getByLabel("Event 3", { exact: true }).selectOption("child_birth");
  await page.getByLabel("Date of event 3").fill("2018-03-01");
  await page.getByLabel(/Kunda/).check();
  await page.getByRole("button", { name: "Rectify birth time" }).click();

  const table = page.getByRole("region", { name: "Candidate birth times" });
  await expect(table.getByRole("row")).toHaveCount(6);
  await expect(page.getByRole("img", { name: /Score of each candidate time/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "What changes between candidates" })).toBeVisible();
  await expectAccessible(page);
});
