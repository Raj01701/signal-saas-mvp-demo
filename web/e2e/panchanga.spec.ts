import { expect, test } from "@playwright/test";

import { expectAccessible } from "./helpers";

test("shows a day's panchanga", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Panchanga" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Panchanga" })).toBeVisible();

  await page.getByLabel("Date", { exact: true }).fill("2026-09-30");
  await page.getByRole("button", { name: "Show panchanga" }).click();
  await expect(page.getByRole("heading", { name: "Budhavara, 30 September 2026" })).toBeVisible();
  await expect(page.getByText("Chaturthi (krishna paksha) until 14:56")).toBeVisible();
  await expect(page.getByText("Parabhava (40 of 60)")).toBeVisible();
  await expect(page.getByText(/^Rahu kalam: \d\d:\d\d to \d\d:\d\d$/)).toBeVisible();
  await expect(page.getByRole("table", { name: "Choghadiyas" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Panchanga" })).toHaveAttribute("aria-current", "page");
  await expectAccessible(page);
});
