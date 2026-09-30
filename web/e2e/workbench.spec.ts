import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("calculates and shows a chart", async ({ page }) => {
  await page.goto("/workbench");
  await page.getByLabel("Date of birth").fill("1990-05-17");
  await page.getByLabel("Time of birth (local)").fill("12:00:00");
  await page.getByRole("button", { name: "Calculate chart" }).click();

  await expect(page.getByRole("heading", { name: "Charts" })).toBeVisible();
  await expect(page.getByRole("img", { name: /Rasi \(D1\)/ })).toBeVisible();
  await expect(page.getByRole("img", { name: /D9/ })).toBeVisible();
  await expect(page.getByRole("rowheader", { name: "Sun" })).toBeVisible();
  await expect(page.getByText(/born in the .* mahadasha/)).toBeVisible();

  await page.getByLabel("Chart style", { exact: true }).selectOption("south");
  await expect(page.getByRole("img", { name: /south Indian style/ }).first()).toBeVisible();

  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""))).toEqual([]);

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("searches places", async ({ page }) => {
  await page.goto("/workbench");
  await page.getByLabel("Place of birth").fill("Varanasi");
  const option = page.getByRole("list", { name: "Matching places" }).getByRole("button").first();
  await expect(option).toContainText("Varanasi");
  await option.click();
  await expect(page.getByLabel("Place of birth")).toHaveAttribute("placeholder", /Varanasi/);
});

test("reports input the engine rejects", async ({ page }) => {
  await page.goto("/workbench");
  await page.getByLabel("Date of birth").fill("1700-01-01");
  await page.getByRole("button", { name: "Calculate chart" }).click();
  await expect(page.getByRole("status")).toContainText(/between .* and /);
});
