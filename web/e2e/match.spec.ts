import { expect, test } from "@playwright/test";

import { expectAccessible } from "./helpers";

test("matches two charts", async ({ page }) => {
  await page.goto("/match");
  const groom = page.getByRole("group", { name: "Groom" });
  await groom.getByLabel("Date of birth").fill("1990-05-17");
  await groom.getByLabel("Time of birth (local)").fill("12:00:00");
  const bride = page.getByRole("group", { name: "Bride" });
  await bride.getByLabel("Date of birth").fill("1993-11-02");
  await bride.getByLabel("Time of birth (local)").fill("06:30:00");
  await page.getByRole("button", { name: "Match charts" }).click();

  await expect(page.getByRole("heading", { name: "Ashtakoota: 20 of 36" })).toBeVisible();
  await expect(page.getByRole("rowheader", { name: /^Nadi/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Ten kutas (South Indian): 8 of 10 agree" })).toBeVisible();
  await expect(page.getByText("Bhakoot dosha: present, cancelled by an exception")).toBeVisible();
  await expect(page.getByText(/^Groom: Not manglik/)).toBeVisible();
  await expectAccessible(page);

  await page.getByLabel("Koota tables").selectOption("maitreya");
  await page.getByRole("button", { name: "Match charts" }).click();
  await expect(page.getByText(/uses the maitreya profile/)).toBeVisible();
});
