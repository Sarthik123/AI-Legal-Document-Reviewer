import { expect, test, type Page } from '@playwright/test';
import path from 'node:path';

const API_URL = process.env.PROD_API_URL || 'https://api.lawyerlens.in';
const EMAIL = process.env.PROD_TEST_EMAIL || '';
const PASSWORD = process.env.PROD_TEST_PASSWORD || '';
const PDF_PATH = path.join(__dirname, 'fixtures', 'synthetic-service-agreement.pdf');
const UPLOAD_TIMEOUT = 240_000;

test.beforeAll(() => {
  if (!EMAIL || !PASSWORD) {
    throw new Error('Set PROD_TEST_EMAIL and PROD_TEST_PASSWORD to a verified test account.');
  }
});

async function logIn(page: Page) {
  await page.goto('/login');
  await page.locator('input[type="email"]').fill(EMAIL);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.getByRole('button', { name: 'Log in' }).click();
  await page.waitForURL('**/upload', { timeout: 120_000 });
}

async function selectPdf(page: Page) {
  await page.locator('input[type="file"]').setInputFiles(PDF_PATH);
  await expect(page.getByText('Selected:')).toBeVisible();
}

async function deleteDocument(page: Page, documentId: string) {
  const token = await page.evaluate(() => localStorage.getItem('access_token'));
  const response = await page.request.delete(`${API_URL}/documents/${documentId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.ok()).toBeTruthy();
}

async function uploadAndExpectSuccess(page: Page) {
  const uploadResponse = page.waitForResponse(
    (response) =>
      response.url() === `${API_URL}/documents` &&
      response.request().method() === 'POST' &&
      response.ok(),
    { timeout: UPLOAD_TIMEOUT },
  );

  await page.getByRole('button', { name: 'Upload Document' }).click();
  const response = await uploadResponse;
  await expect(page.getByText('Uploaded successfully.')).toBeVisible({ timeout: UPLOAD_TIMEOUT });

  const data = await response.json() as { document_id: string };
  await deleteDocument(page, data.document_id);
}

test('uploads a small PDF on a Pixel 7', async ({ page }) => {
  await logIn(page);
  await selectPdf(page);
  await uploadAndExpectSuccess(page);
});

test('retries the upload after a network error', async ({ page }) => {
  let failedOnce = false;
  await page.route(`${API_URL}/documents`, async (route) => {
    if (route.request().method() === 'POST' && !failedOnce) {
      failedOnce = true;
      await route.abort('internetdisconnected');
      return;
    }
    await route.continue();
  });

  await logIn(page);
  await selectPdf(page);
  await uploadAndExpectSuccess(page);
  expect(failedOnce).toBe(true);
});

test('explains when the phone cannot read the file', async ({ page }) => {
  await page.addInitScript(() => {
    File.prototype.arrayBuffer = () =>
      Promise.reject(new DOMException('The file could not be read.', 'NotReadableError'));
  });

  let uploadRequests = 0;
  const createdIds: string[] = [];
  page.on('request', (request) => {
    if (request.url() === `${API_URL}/documents` && request.method() === 'POST') {
      uploadRequests += 1;
    }
  });
  page.on('response', async (response) => {
    if (
      response.url() === `${API_URL}/documents` &&
      response.request().method() === 'POST' &&
      response.ok()
    ) {
      createdIds.push(((await response.json()) as { document_id: string }).document_id);
    }
  });

  try {
    await logIn(page);
    await selectPdf(page);
    await page.getByRole('button', { name: 'Upload Document' }).click();

    await expect(
      page.getByText("Couldn't open this file. Save it to your phone first, then upload."),
    ).toBeVisible({ timeout: 60_000 });
    expect(uploadRequests).toBe(0);
  } finally {
    for (const id of createdIds) {
      await deleteDocument(page, id);
    }
  }
});
