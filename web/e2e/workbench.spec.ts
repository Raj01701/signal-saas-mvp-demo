import { expect, test } from "@playwright/test";

import { expectAccessible } from "./helpers";

test("calculates and shows a chart", async ({ page }) => {
  await page.goto("/workbench");
  await page.getByLabel("Date of birth").fill("1990-05-17");
  await page.getByLabel("Time of birth (local)").fill("12:00:00");
  await page.getByRole("button", { name: "Calculate chart" }).click();

  await expect(page.getByRole("tab", { name: "Chart", exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("img", { name: /Rasi \(D1\)/ })).toBeVisible();
  await expect(page.getByRole("img", { name: /D9/ })).toBeVisible();
  await expect(page.getByRole("rowheader", { name: "Sun" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Birth-time sensitivity" })).toBeVisible();
  await expect(page.getByText(/^Lagna/).first()).toBeVisible();

  await page.getByLabel("Chart style", { exact: true }).selectOption("south");
  await expect(page.getByRole("img", { name: /south Indian style/ }).first()).toBeVisible();

  await page.getByRole("tab", { name: "Dashas" }).click();
  await expect(page.getByText(/born in the .* mahadasha/)).toBeVisible();
  await page.getByRole("tab", { name: "Yogas" }).click();
  const yogas = page.getByRole("list", { name: "Yogas present" });
  await yogas.locator("summary").first().click();
  await expect(yogas.getByText("Why it applies").first()).toBeVisible();
  await page.getByRole("tab", { name: "Readings" }).click();
  await expect(page.getByRole("list", { name: "House lords" }).locator(":scope > li")).toHaveCount(12);
  await page.getByRole("tab", { name: "Timeline" }).click();
  await expect(page.getByRole("heading", { name: "Now" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Life-domain timeline" })).toBeVisible();
  await page.getByRole("button", { name: "Marriage" }).click();
  await expect(page.getByRole("list", { name: "Marriage windows" }).locator("li").first()).toBeVisible();
  await expectAccessible(page);
  await page.getByRole("tab", { name: "Report" }).click();
  await expect(page.getByRole("heading", { name: "The present period" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Evidence" })).toBeVisible();
  await page.getByLabel("Question").fill("How is my career now?");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByText(/not certainties/)).toBeVisible();
  await expectAccessible(page);
  await page.getByRole("tab", { name: "Strengths" }).click();
  await expect(page.getByText("Shadbala (rupas)")).toBeVisible();
  await page.getByRole("tab", { name: "KP" }).click();
  await expect(page.getByText(/Ruling planets:/)).toBeVisible();
  await page.getByRole("tab", { name: "Transits" }).click();
  await expect(page.getByText("Saturn from the natal Moon")).toBeVisible();
  await page.getByRole("tab", { name: "Chart" }).click();

  await expectAccessible(page);
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
