import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

/** No serious or critical WCAG A/AA violations, and no horizontal page scroll. */
export async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(results.violations.filter((v) => ["serious", "critical"].includes(v.impact ?? ""))).toEqual([]);
  // Compare with the configured viewport: a mobile browser widens its layout viewport
  // (and zooms out) when content overflows, so window.innerWidth would hide the problem.
  const width = page.viewportSize()?.width ?? 0;
  const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(scrollWidth).toBeLessThanOrEqual(width);
}
