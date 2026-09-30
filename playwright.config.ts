import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: 'html',
  timeout: 360_000,
  actionTimeout: 30_000,
  expect: { timeout: 30_000 },
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'node tests/support/smtp_capture.js',
      url: 'http://127.0.0.1:8026/health',
      reuseExistingServer: false,
      timeout: 10_000,
    },
    {
      command: 'cd backend && .venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000',
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        JWT_SECRET_KEY: process.env.JWT_SECRET_KEY || 'local-playwright-test-secret-for-e2e-only',
        SMTP_HOST: '127.0.0.1',
        SMTP_PORT: '1025',
        SMTP_SECURITY: 'none',
        SMTP_USERNAME: '',
        SMTP_PASSWORD: '',
        SMTP_FROM: 'reviewer@example.test',
        APP_BASE_URL: 'http://localhost:3000',
        EMAIL_VERIFICATION_ENABLED: 'true',
      },
    },
    {
      command: 'cd frontend && npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_PASSWORD_RESET_ENABLED: 'false',
      },
    },
  ],
});
