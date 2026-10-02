import { expect, test } from "@playwright/test";

import { expectAccessible } from "./helpers";

test("links the privacy notice and terms from every page", async ({ page }) => {
  await page.goto("/");
  const footer = page.getByRole("contentinfo");
  await expect(footer).toContainText("not certainties or professional advice");

  await footer.getByRole("link", { name: "Privacy" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Privacy notice" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Your rights" })).toBeVisible();
  await expectAccessible(page);

  await page.getByRole("contentinfo").getByRole("link", { name: "Terms" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Terms of use" })).toBeVisible();
  await expectAccessible(page);
});
