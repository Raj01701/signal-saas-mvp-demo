import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests against the real API (uvicorn) and the Next.js app.
 * Set PW_CHROMIUM to use an installed Chromium instead of Playwright's download.
 */
const executablePath = process.env.PW_CHROMIUM || undefined;

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    launchOptions: { executablePath },
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], launchOptions: { executablePath } } },
    { name: "mobile", use: { ...devices["Pixel 7"], launchOptions: { executablePath } } },
  ],
  webServer: [
    {
      command: "uv run uvicorn jyotish_api.main:app --port 8000",
      cwd: "..",
      // Push reminders on, with a key made for these tests only.
      env: {
        JYOTISH_API_VAPID_PRIVATE_KEY: "1ypyskHgkGWGLncUlqmpi1NcYYShxCsvE386QduyzYg",
        JYOTISH_API_VAPID_SUBJECT: "mailto:e2e@example.org",
      },
      url: "http://localhost:8000/ready",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "pnpm build && pnpm start --port 3000",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 240_000,
    },
  ],
});
