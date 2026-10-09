import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

const API_URL = 'http://127.0.0.1:8000';
const PASSWORD = 'Playwright-local-test-2026';
const MAIL_CAPTURE_URL = 'http://127.0.0.1:8026';
const AGREEMENT_FILE = 'synthetic-service-agreement.pdf';
const AGREEMENT_PATH = path.join(__dirname, 'fixtures', AGREEMENT_FILE);
const PROCESSING_FAILED = 'Something went wrong while processing your document.';
const FAKE_ANALYSIS = {
  summary: 'Synthetic summary returned by the retry test.',
  key_points: [],
  risks: [],
  missing_information: [],
};

async function createAccount(request: APIRequestContext) {
  const email = 'e2e-' + Date.now() + '-' + Math.random().toString(16).slice(2) + '@example.com';
  const registration = await request.post(API_URL + '/auth/register', {
    data: { email, password: PASSWORD },
  });
  expect(registration.status()).toBe(201);

  let verificationToken = '';
  await expect.poll(async () => {
    const response = await request.get(MAIL_CAPTURE_URL + '/messages?to=' + encodeURIComponent(email));
    const data = await response.json() as { messages: { content: string }[] };
    const match = data.messages
      .map((message) => message.content.match(/\/verify-email\?token=([A-Za-z0-9_-]+)/))
      .find(Boolean);
    verificationToken = match?.[1] ?? '';
    return verificationToken;
  }).toBeTruthy();

  const verification = await request.post(API_URL + '/auth/verify-email', {
    data: { token: verificationToken },
  });
  expect(verification.status()).toBe(200);

  const login = await request.post(API_URL + '/auth/token', {
    form: { username: email, password: PASSWORD },
  });
  expect(login.ok()).toBeTruthy();
  return { email, token: (await login.json()).access_token as string };
}

async function uploadViaApi(request: APIRequestContext, token: string) {
  const response = await request.post(API_URL + '/documents', {
    headers: { Authorization: 'Bearer ' + token },
    multipart: {
      file: {
        name: AGREEMENT_FILE,
        mimeType: 'application/pdf',
        buffer: fs.readFileSync(AGREEMENT_PATH),
      },
    },
  });
  expect(response.status(), await response.text()).toBe(200);
  return (await response.json()).document_id as string;
}

async function signIn(page: Page, token: string) {
  await page.addInitScript((accessToken) => {
    window.localStorage.setItem('access_token', accessToken);
  }, token);
}

test.afterEach(async ({ request }, testInfo) => {
  const account = testInfo.annotations.find((annotation) => annotation.type === 'e2e-test-token');
  if (!account?.description) return;
  const headers = { Authorization: 'Bearer ' + account.description };
  const documents = await request.get(API_URL + '/documents', { headers });
  if (!documents.ok()) return;
  for (const document of (await documents.json()) as { document_id: string }[]) {
    await request.delete(API_URL + '/documents/' + document.document_id, { headers });
  }
});

// The PDF's pages must be drawn on the page itself (not a grey placeholder):
// page 1 is a canvas with dark text pixels on it.
async function expectDrawnPages(page: Page) {
  const firstPage = page.locator('canvas.pdf-page').first();
  await expect(firstPage).toBeVisible();
  await expect(firstPage).toHaveAttribute('aria-label', AGREEMENT_FILE + ', page 1 of 1');
  await expect.poll(() => firstPage.evaluate((canvas: HTMLCanvasElement) => {
    const { data } = canvas.getContext('2d')!.getImageData(0, 0, canvas.width, canvas.height);
    let dark = 0;
    for (let i = 0; i < data.length; i += 4) {
      if (data[i] < 100 && data[i + 1] < 100 && data[i + 2] < 100) dark += 1;
    }
    return dark;
  })).toBeGreaterThan(500);
}

// The PDF section shows only the document: no Open PDF button, no download
// link, and never the internal document ID.
async function expectNoDownloadButton(page: Page, documentId: string) {
  await expect(page.getByRole('link', { name: 'Open PDF' })).toHaveCount(0);
  await expect(page.locator('a[download]')).toHaveCount(0);
  await expect(page.locator('main')).not.toContainText(documentId);
}

// Opens a freshly uploaded document (analysis stubbed) and returns its ID.
async function openDocument(
  page: Page,
  request: APIRequestContext,
  testInfo: { annotations: { type: string; description?: string }[] },
) {
  const account = await createAccount(request);
  testInfo.annotations.push({ type: 'e2e-test-token', description: account.token });
  const documentId = await uploadViaApi(request, account.token);

  await signIn(page, account.token);
  await page.route('**/documents/*/analyze', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FAKE_ANALYSIS) }),
  );
  await page.goto('/documents/' + documentId);
  return documentId;
}

// User agents sent by real Chrome on an Android phone. Chrome reduces the
// device details to "Android 10; K". With "Desktop site" turned on, it sends a
// desktop Linux user agent instead. The page must not depend on either.
const ANDROID_PHONES = [
  {
    name: "owner's Android Chrome 154",
    userAgent:
      'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36',
  },
  {
    name: 'real Android Chrome',
    userAgent:
      'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36',
  },
  {
    name: 'Android Chrome with "Desktop site" on',
    userAgent:
      'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
  },
];

for (const phone of ANDROID_PHONES) test.describe(phone.name, () => {
  test.use({
    userAgent: phone.userAgent,
    viewport: { width: 412, height: 915 },
    deviceScaleFactor: 2.625,
    isMobile: true,
    hasTouch: true,
  });

  test('shows the actual PDF pages, with no grey box, ID, or download button', async ({ page, request }, testInfo) => {
    const documentId = await openDocument(page, request, testInfo);

    await expect(page.locator('iframe')).toHaveCount(0);
    await expectDrawnPages(page);
    await expectNoDownloadButton(page, documentId);

    const layout = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
    }));
    expect(layout.documentWidth).toBeLessThanOrEqual(layout.viewportWidth + 1);
  });
});

test.describe('wide screen with a mouse', () => {
  test.use({ viewport: { width: 1280, height: 800 }, hasTouch: false, isMobile: false });

  test("shows the PDF in the browser's viewer, with no download button", async ({ page, request }, testInfo) => {
    const documentId = await openDocument(page, request, testInfo);

    await expect(page.locator('iframe[title="' + AGREEMENT_FILE + '"]')).toBeVisible();
    await expect(page.locator('canvas.pdf-page')).toHaveCount(0);
    await expectNoDownloadButton(page, documentId);
  });
});

test.describe('narrow screen with a mouse', () => {
  test.use({ viewport: { width: 900, height: 800 }, hasTouch: false, isMobile: false });

  test('shows the drawn PDF pages instead of the built-in viewer', async ({ page, request }, testInfo) => {
    const documentId = await openDocument(page, request, testInfo);

    await expect(page.locator('iframe')).toHaveCount(0);
    await expectDrawnPages(page);
    await expectNoDownloadButton(page, documentId);
  });
});

test('upload processing failure shows a plain message and Retry re-runs processing', async ({ page, request }, testInfo) => {
  const account = await createAccount(request);
  testInfo.annotations.push({ type: 'e2e-test-token', description: account.token });

  await page.route(API_URL + '/documents', (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: PROCESSING_FAILED, document_id: 'failed-doc-1', reason: 'embedding_failed' }),
    });
  });
  const analyzeCalls: string[] = [];
  await page.route('**/documents/*/analyze', (route) => {
    analyzeCalls.push(route.request().url());
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FAKE_ANALYSIS) });
  });

  await signIn(page, account.token);
  await page.goto('/upload');
  await page.locator('input[type="file"]').setInputFiles(AGREEMENT_PATH);
  await page.getByRole('button', { name: 'Upload Document' }).click();

  await expect(page.getByText(PROCESSING_FAILED)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Upload Document' })).toBeDisabled();
  await page.getByRole('button', { name: 'Retry' }).click();

  await expect(page.getByText('Processed successfully.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Go to Dashboard' })).toBeVisible();
  expect(analyzeCalls).toEqual([API_URL + '/documents/failed-doc-1/analyze']);
});

test('document analysis failure shows Retry, and Retry loads the results', async ({ page, request }, testInfo) => {
  const account = await createAccount(request);
  testInfo.annotations.push({ type: 'e2e-test-token', description: account.token });
  const documentId = await uploadViaApi(request, account.token);

  // Fail every automatic attempt (next dev runs effects twice) until Retry.
  let retried = false;
  let callsAfterRetry = 0;
  await page.route('**/documents/*/analyze', (route) => {
    if (!retried) {
      return route.fulfill({
        status: 502,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Analysis could not be completed. Please try again.' }),
      });
    }
    callsAfterRetry += 1;
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FAKE_ANALYSIS) });
  });

  await signIn(page, account.token);
  await page.goto('/documents/' + documentId);

  const error = page.locator('.analysis-error');
  await expect(error).toContainText(PROCESSING_FAILED);
  retried = true;
  await error.getByRole('button', { name: 'Retry' }).click();

  await expect(page.getByText(FAKE_ANALYSIS.summary)).toBeVisible();
  await expect(page.locator('.analysis-error')).toHaveCount(0);
  expect(callsAfterRetry).toBe(1);
});
