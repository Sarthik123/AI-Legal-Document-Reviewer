import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import path from 'node:path';

const API_URL = 'http://127.0.0.1:8000';
const PASSWORD = 'Playwright-local-test-2026';
const AGREEMENT_FILE = 'synthetic-service-agreement.pdf';
const AGREEMENT_PATH = path.join(__dirname, 'fixtures', AGREEMENT_FILE);
const SCANNED_FILE = 'synthetic-scanned-agreement.pdf';
const SCANNED_PATH = path.join(__dirname, 'fixtures', SCANNED_FILE);
const MAIL_CAPTURE_URL = 'http://127.0.0.1:8026';
const AGREEMENT_TEXT = [
  'NORTHSTAR SERVICE AGREEMENT',
  'Synthetic E2E fixture; no real parties or obligations.',
  'Customer: Northstar Bicycle LLC.',
  'Provider: Blue Mesa Design LLC.',
  'Effective date: July 1, 2026.',
  'Services: Provider will deliver two monthly product-design reports.',
  'Customer must pay Provider $4,250 per month, due on the first day of each month.',
  'The initial term is 12 months, starting July 1, 2026.',
  'Provider may terminate this agreement at any time without notice. Customer cannot terminate during the initial term.',
  "Provider's total liability for any claim is capped at $10, regardless of the loss.",
  "Customer must cover all claims, including claims caused by Provider's own negligence, with no cap.",
  'This agreement does not name a governing law or dispute-resolution forum.',
].join('\n');

function uniqueEmail() {
  return 'e2e-' + Date.now() + '-' + Math.random().toString(16).slice(2) + '@example.com';
}

async function capturedEmailToken(
  request: APIRequestContext,
  email: string,
  route: 'verify-email' | 'reset-password',
) {
  await expect.poll(async () => {
    const response = await request.get(
      MAIL_CAPTURE_URL + '/messages?to=' + encodeURIComponent(email),
    );
    const data = await response.json() as { messages: { content: string }[] };
    return data.messages.some((message) =>
      message.content.includes('/' + route + '?token='),
    );
  }).toBeTruthy();

  const response = await request.get(
    MAIL_CAPTURE_URL + '/messages?to=' + encodeURIComponent(email),
  );
  const data = await response.json() as { messages: { content: string }[] };
  const matchingMessage = [...data.messages]
    .reverse()
    .find((message) => message.content.includes('/' + route + '?token='));
  expect(matchingMessage).toBeTruthy();

  const tokenMatch = matchingMessage?.content.match(
    new RegExp('/' + route + '\\?token=([A-Za-z0-9_-]+)'),
  );
  expect(tokenMatch).toBeTruthy();
  expect(tokenMatch![1]).toHaveLength(43);
  return tokenMatch![1];
}

async function createAccount(request: APIRequestContext, email = uniqueEmail()) {
  const registration = await request.post(API_URL + '/auth/register', {
    data: { email, password: PASSWORD },
  });
  expect(registration.status()).toBe(201);

  const verificationToken = await capturedEmailToken(request, email, 'verify-email');
  const verification = await request.post(API_URL + '/auth/verify-email', {
    data: { token: verificationToken },
  });
  expect(verification.status(), await verification.text()).toBe(200);

  const login = await request.post(API_URL + '/auth/token', {
    form: { username: email, password: PASSWORD },
  });
  expect(login.ok()).toBeTruthy();
  const tokenData = await login.json();
  return { email, password: PASSWORD, token: tokenData.access_token as string };
}

async function openAuthenticatedUploadPage(page: Page, token: string) {
  await page.addInitScript((accessToken) => {
    window.localStorage.setItem('access_token', accessToken);
  }, token);
  await page.goto('/upload');
  await expect(page.getByRole('heading', { name: 'Review a Document' })).toBeVisible();
}

async function getChatPanel(page: Page) {
  const panel = page.locator('div.overflow-hidden').filter({
    has: page.getByRole('heading', { name: 'Document Chat' }),
  });
  await expect(panel).toBeVisible();
  return panel;
}

function normalize(text: string) {
  return text.toLowerCase().replace(/[^a-z0-9$]+/g, ' ').replace(/\s+/g, ' ').trim();
}

test.afterEach(async ({ request }, testInfo) => {
  const account = testInfo.annotations.find((annotation) => annotation.type === 'e2e-test-account');
  if (!account) return;

  const login = await request.post(API_URL + '/auth/token', {
    form: { username: account.description, password: PASSWORD },
  });
  if (!login.ok()) return;

  const token = (await login.json()).access_token as string;
  const documentsResponse = await request.get(API_URL + '/documents', {
    headers: { Authorization: 'Bearer ' + token },
  });
  if (!documentsResponse.ok()) return;

  const documents = (await documentsResponse.json()) as { document_id: string }[];
  for (const document of documents) {
    await request.delete(API_URL + '/documents/' + document.document_id, {
      headers: { Authorization: 'Bearer ' + token },
    });
  }
});

test('registration, review, grounded chat, persistence, clear, and delete', async ({ page, request }, testInfo) => {
  const email = uniqueEmail();
  testInfo.annotations.push({ type: 'e2e-test-account', description: email });

  await page.goto('/register');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').nth(0).fill(PASSWORD);
  await page.locator('input[type="password"]').nth(1).fill(PASSWORD);
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.getByText('Account created. Check your email to verify it.')).toBeVisible();

  await page.getByRole('button', { name: 'Already have an account? Log in' }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page.getByText('Please verify your email before logging in.')).toBeVisible();

  await page.getByRole('link', { name: 'Resend verification' }).click();
  await expect(page).toHaveURL(/\/resend-verification$/);
  await page.locator('input[type="email"]').fill(email);
  await page.getByRole('button', { name: 'Send verification link' }).click();
  await expect(page.getByRole('status')).toHaveText(
    'If the account needs verification, an email will be sent.',
  );

  const verificationToken = await capturedEmailToken(request, email, 'verify-email');
  await page.goto('/verify-email?token=' + verificationToken);
  await expect(page.getByRole('status')).toHaveText('Email verified. You can now log in.');
  const reusedVerificationToken = await request.post(API_URL + '/auth/verify-email', {
    data: { token: verificationToken },
  });
  expect(reusedVerificationToken.status()).toBe(400);
  await page.getByRole('link', { name: 'Continue to log in' }).click();

  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(PASSWORD);
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page).toHaveURL(/\/upload$/);

  await page.locator('input[type="file"]').setInputFiles(AGREEMENT_PATH);
  const uploadResponsePromise = page.waitForResponse((response) =>
    response.url() === API_URL + '/documents' && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Upload Document' }).click();
  const uploadResponse = await uploadResponsePromise;
  expect(uploadResponse.status()).toBe(200);
  const uploadResult = await uploadResponse.json();
  const documentId = uploadResult.document_id as string;
  expect(uploadResult.text_length).toBeGreaterThan(100);
  await expect(page.getByText('Uploaded successfully.')).toBeVisible();

  await page.getByRole('button', { name: 'Go to Dashboard' }).click();
  await expect(page.getByRole('heading', { name: 'Your documents' })).toBeVisible();
  await expect(page.getByText(AGREEMENT_FILE, { exact: true })).toBeVisible();
  const analysisStartedAt = Date.now();
  const analysisResponsePromise = page.waitForResponse((response) =>
    response.url() === API_URL + '/documents/' + documentId + '/analyze' &&
    response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Open', exact: true }).click();
  const initialAnalysisResponse = await analysisResponsePromise;
  expect(initialAnalysisResponse.status()).toBe(200);
  const analysisElapsedMs = Date.now() - analysisStartedAt;
  console.log('Initial document analysis completed in ' + analysisElapsedMs + ' ms');
  expect(analysisElapsedMs).toBeLessThan(90_000);

  await expect(page.getByRole('heading', { name: AGREEMENT_FILE })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'PDF Document' })).toBeVisible();
  await expect(page.locator('iframe[title="' + AGREEMENT_FILE + '"]')).toBeVisible();
  await expect(page.getByText('processed', { exact: true })).toBeVisible();

  await expect(page.getByRole('heading', { name: 'Summary' })).toBeVisible({ timeout: 240_000 });
  const summary = page.getByRole('heading', { name: 'Summary' }).locator('xpath=following-sibling::p[1]');
  await expect(summary).not.toBeEmpty();
  const keyPoints = page.getByRole('heading', { name: 'Key Points' }).locator('xpath=following-sibling::div[1]');
  await expect(keyPoints.locator('div').first()).toBeVisible();

  const risks = page.getByRole('heading', { name: 'Potential Risks' }).locator('xpath=..');
  await expect(risks.locator('details').first()).toBeVisible();
  const missingInformation = page.getByRole('heading', { name: 'Missing Information' }).locator('xpath=..');
  await expect(missingInformation.locator('details').first()).toBeVisible();

  const ownerLogin = await request.post(API_URL + '/auth/token', {
    form: { username: email, password: PASSWORD },
  });
  const ownerToken = (await ownerLogin.json()).access_token as string;
  const otherAccount = await createAccount(request);
  const privateDocument = await request.get(API_URL + '/documents/' + documentId, {
    headers: { Authorization: 'Bearer ' + otherAccount.token },
  });
  expect(privateDocument.status()).toBe(404);
  const privateFile = await request.get(API_URL + '/documents/' + documentId + '/file', {
    headers: { Authorization: 'Bearer ' + otherAccount.token },
  });
  expect(privateFile.status()).toBe(404);

  const analysisResponse = await request.post(API_URL + '/documents/' + documentId + '/analyze', {
    headers: { Authorization: 'Bearer ' + ownerToken },
  });
  expect(analysisResponse.ok()).toBeTruthy();
  const analysis = await analysisResponse.json();
  expect(analysis.summary.trim().length).toBeGreaterThan(20);
  expect(analysis.key_points.length).toBeGreaterThan(0);
  expect(analysis.risks.length).toBeGreaterThan(0);
  expect(analysis.missing_information.length).toBeGreaterThan(0);
  for (const risk of analysis.risks) {
    expect(risk.source).toBe(1);
    expect(risk.evidence.trim().length).toBeGreaterThan(0);
    expect(normalize(AGREEMENT_TEXT)).toContain(normalize(risk.evidence));
  }
  for (const item of analysis.missing_information) {
    expect(item.source).toBe(1);
  }

  const chatPanel = await getChatPanel(page);
  await chatPanel.getByRole('textbox').fill('How much must the Customer pay each month?');
  await chatPanel.getByRole('button', { name: 'Send' }).click();
  let assistantBubble = chatPanel.locator('div.flex.justify-start > div').last();
  await expect(assistantBubble).toContainText('$4,250', { timeout: 240_000 });
  let sourceDetails = assistantBubble.locator('details').last();
  await expect(sourceDetails.locator('summary')).toContainText('Sources');
  await sourceDetails.locator('summary').click();
  let sourceText = await sourceDetails.innerText();
  expect(sourceText).toContain('Page 1');
  expect(normalize(sourceText)).toContain(normalize('$4,250 per month'));
  expect(normalize(AGREEMENT_TEXT)).toContain(normalize('$4,250 per month'));

  await chatPanel.getByRole('textbox').fill('hOW mUCH MUSt THE CUSTMER pay each mnoth?');
  await chatPanel.getByRole('button', { name: 'Send' }).click();
  let typoAnswer = chatPanel.locator('div.flex.justify-start > div').last();
  await expect(typoAnswer).toContainText('$4,250', { timeout: 30_000 });
  let typoSources = typoAnswer.locator('details').last();
  await typoSources.locator('summary').click();
  await expect(typoSources).toContainText('$4,250 per month');

  await chatPanel.getByRole('textbox').fill(
    "Compare the Provider's termination right with the Customer's restriction, including any notice details.",
  );
  await chatPanel.getByRole('button', { name: 'Send' }).click();
  let complexAnswer = chatPanel.locator('div.flex.justify-start > div').last();
  await expect(complexAnswer).toContainText('Provider may terminate', { timeout: 30_000 });
  await expect(complexAnswer).toContainText('without notice');
  await expect(complexAnswer).toContainText('Customer cannot terminate');
  let complexSources = complexAnswer.locator('details').last();
  await complexSources.locator('summary').click();
  await expect(complexSources).toContainText('Page 1');
  await expect(complexSources).toContainText('Customer cannot terminate');

  await page.reload();
  await expect(page.getByRole('heading', { name: AGREEMENT_FILE })).toBeVisible();
  const refreshedChatPanel = await getChatPanel(page);
  assistantBubble = refreshedChatPanel.locator('div.flex.justify-start > div').last();
  await expect(assistantBubble).toContainText('Customer cannot terminate', { timeout: 30_000 });
  sourceDetails = assistantBubble.locator('details').last();
  await expect(sourceDetails.locator('summary')).toContainText('Sources');
  await sourceDetails.locator('summary').click();
  sourceText = await sourceDetails.innerText();
  expect(sourceText).toContain('Page 1');
  expect(normalize(sourceText)).toContain(normalize('Customer cannot terminate'));

  await refreshedChatPanel.getByRole('button', { name: 'Clear chat' }).click();
  await expect(refreshedChatPanel.getByText('Ask your first question about this document.')).toBeVisible();
  const emptyHistory = await request.get(API_URL + '/documents/' + documentId + '/chat', {
    headers: { Authorization: 'Bearer ' + ownerToken },
  });
  expect((await emptyHistory.json()).messages).toEqual([]);

  await page.getByRole('button', { name: 'Back to Dashboard' }).click();
  await expect(page.getByRole('button', { name: 'Delete' })).toBeVisible();
  page.once('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Delete' }).click();
  await expect(page.getByText('No documents yet')).toBeVisible();

  await page.goto('/documents/' + documentId);
  await expect(page.getByText('Document not found.')).toBeVisible();
  const deletedDocument = await request.get(API_URL + '/documents/' + documentId, {
    headers: { Authorization: 'Bearer ' + ownerToken },
  });
  expect(deletedDocument.status()).toBe(404);
});

test('wrong password shows an authentication error', async ({ page }) => {
  await page.goto('/login');
  await page.locator('input[type="email"]').fill('unknown-user@example.com');
  await page.locator('input[type="password"]').fill('wrong-password');
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  await expect(page.getByText('Incorrect email or password.')).toBeVisible();
});

test('network failures show an actionable error', async ({ page }) => {
  await page.route('**/auth/token', (route) => route.abort('failed'));
  await page.goto('/login');
  await page.locator('input[type="email"]').fill('unknown-user@example.com');
  await page.locator('input[type="password"]').fill('wrong-password');
  await page.getByRole('button', { name: 'Log in', exact: true }).click();
  await expect(page.getByText('Unable to reach the server. Please try again.')).toBeVisible();
});

test('unauthenticated routes and document APIs are protected', async ({ page, request }) => {
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/\/login$/);

  const documents = await request.get(API_URL + '/documents');
  expect(documents.status()).toBe(401);
  const protectedDocument = await request.get(API_URL + '/documents/unauthenticated-test-id');
  expect(protectedDocument.status()).toBe(401);
});

test('password reset is clearly unavailable until email delivery is enabled', async ({ page, request }) => {
  await page.goto('/login');
  await page.getByRole('link', { name: 'Forgot password?' }).click();
  await expect(page).toHaveURL(/\/forgot-password$/);
  const disabledMessage = 'Password reset is temporarily unavailable. Please try again later.';
  await expect(page.getByRole('status')).toHaveText(disabledMessage);
  await expect(page.locator('input[type="email"]')).toHaveCount(0);

  const requestResponse = await request.post(API_URL + '/auth/password-reset/request', {
    data: { email: uniqueEmail() },
  });
  expect(requestResponse.ok()).toBeTruthy();
  expect((await requestResponse.json()).message).toBe(disabledMessage);

  const confirmationResponse = await request.post(API_URL + '/auth/password-reset/confirm', {
    data: { token: 'a'.repeat(43), password: 'Another-reset-password-2026' },
  });
  expect(confirmationResponse.status()).toBe(503);
  expect((await confirmationResponse.json()).detail).toBe(disabledMessage);

  await page.goto('/reset-password?token=old-reset-token');
  await expect(page.getByRole('status')).toHaveText(disabledMessage);
  await expect(page.getByLabel('New password', { exact: true })).toHaveCount(0);
});

test('upload screen rejects non-PDF and files larger than 10 MB', async ({ page, request }, testInfo) => {
  const account = await createAccount(request);
  testInfo.annotations.push({ type: 'e2e-test-account', description: account.email });
  await openAuthenticatedUploadPage(page, account.token);

  await page.locator('input[type="file"]').setInputFiles({
    name: 'notes.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('This is not a PDF.'),
  });
  await expect(page.getByText('Please select a PDF document.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Upload Document' })).toHaveCount(0);

  const oversizedPdf = Buffer.concat([
    Buffer.from('%PDF-1.4\n'),
    Buffer.alloc(10 * 1024 * 1024, 0x61),
    Buffer.from('\n%%EOF\n'),
  ]);
  await page.locator('input[type="file"]').setInputFiles({
    name: 'oversized.pdf',
    mimeType: 'application/pdf',
    buffer: oversizedPdf,
  });
  await expect(page.getByText('PDF files must be 10 MB or smaller.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Upload Document' })).toHaveCount(0);
});

test('scanned PDF text is extracted by OCR and remains available to document Q&A', async ({ page, request }, testInfo) => {
  test.setTimeout(600_000);
  const account = await createAccount(request);
  testInfo.annotations.push({ type: 'e2e-test-account', description: account.email });
  await openAuthenticatedUploadPage(page, account.token);

  await page.locator('input[type="file"]').setInputFiles(SCANNED_PATH);
  const responsePromise = page.waitForResponse((response) =>
    response.url() === API_URL + '/documents' && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Upload Document' }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const uploadResult = await response.json();
  expect(uploadResult.text_length).toBeGreaterThan(40);
  expect(uploadResult.chunk_count).toBeGreaterThan(0);
  await expect(page.getByText('Uploaded successfully.')).toBeVisible();

  await page.getByRole('button', { name: 'Go to Dashboard' }).click();
  await page.getByRole('button', { name: 'Open', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Summary' })).toBeVisible({ timeout: 300_000 });

  const chatPanel = await getChatPanel(page);
  await chatPanel.getByRole('textbox').fill('What is the OCR verification token?');
  await chatPanel.getByRole('button', { name: 'Send' }).click();
  const assistantBubble = chatPanel.locator('div.flex.justify-start > div').last();
  await expect(assistantBubble).toContainText('PINEAPPLE-7391-OTTER', { timeout: 240_000 });
  const sourceDetails = assistantBubble.locator('details').last();
  await expect(sourceDetails.locator('summary')).toContainText('Sources');
  await sourceDetails.locator('summary').click();
  await expect(sourceDetails).toContainText('PINEAPPLE-7391-OTTER');
  await expect(sourceDetails).toContainText('Page 1');
});

test('empty uploads, responsive layout, and logout remain safe', async ({ page, request }, testInfo) => {
  const account = await createAccount(request);
  testInfo.annotations.push({ type: 'e2e-test-account', description: account.email });
  await page.setViewportSize({ width: 390, height: 844 });
  await openAuthenticatedUploadPage(page, account.token);

  await page.locator('input[type="file"]').setInputFiles({
    name: 'empty.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.alloc(0),
  });
  await page.getByRole('button', { name: 'Upload Document' }).click();
  await expect(page.getByText('The uploaded file is empty.')).toBeVisible();

  const layout = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: window.innerWidth,
  }));
  expect(layout.documentWidth).toBeLessThanOrEqual(layout.viewportWidth + 1);

  await page.getByRole('button', { name: 'Logout' }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible();
});
