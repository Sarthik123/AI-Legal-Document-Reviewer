import { defineConfig, devices } from '@playwright/test';

// Runs against a deployed site (production by default). Starts no local servers.
// Required: PROD_TEST_EMAIL, PROD_TEST_PASSWORD (a verified test account).
export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.prod.ts',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  timeout: 300_000,
  expect: { timeout: 30_000 },
  use: {
    baseURL: process.env.PROD_BASE_URL || 'https://lawyerlens.in',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'pixel-7-chrome',
      use: { ...devices['Pixel 7'] },
    },
  ],
});
