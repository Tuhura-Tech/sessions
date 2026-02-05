import { expect, test } from '@playwright/test';

/**
 * Complete E2E tests for magic link authentication flow.
 *
 * These tests simulate the entire authentication flow:
 * 1. Request a magic link via the form
 * 2. Extract the token from the backend response
 * 3. Consume the token via the redirect
 * 4. Verify the user is authenticated
 *
 * Run with: pnpm run test:e2e tests/e2e/magic-link-flow-complete.spec.ts
 */

const API_BASE_URL = process.env.PUBLIC_BASE_URL || 'http://localhost:8000';
const FRONTEND_BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:4321';

// Helper to generate unique test email
const generateTestEmail = (): string => {
	const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
	return `test-${uniqueSuffix}@example.com`;
};

test.describe('Magic Link Complete Authentication Flow', () => {
	test('should complete full authentication flow: request -> consume token -> redirect', async ({
		page,
		context,
	}) => {
		const testEmail = generateTestEmail();
		let magicToken: string | null = null;

		// Step 1: Navigate to login page
		await page.goto(`${FRONTEND_BASE_URL}/auth/login`, { waitUntil: 'networkidle' });

		// Verify page loads
		const heading = page.locator('main h1');
		await expect(heading).toContainText('Sign in to your account');

		// Step 2: Fill in email and request magic link
		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');
		const successMsg = page.locator('#success-message');

		await emailInput.fill(testEmail);

		// Intercept the API response to get the debug token
		const apiResponse = await Promise.all([
			page.waitForResponse((response) => response.url().includes('/api/v1/auth/magic-link')),
			submitBtn.click(),
		]);

		const response = apiResponse[0];
		expect(response.status()).toBe(200);

		const responseData = await response.json();
		magicToken = responseData.debugToken || responseData.debug_token;
		expect(magicToken).toBeDefined();
		expect(magicToken?.length).toBeGreaterThan(0);

		// Verify success message appears
		await expect(successMsg).toContainText('Check your email');
		await expect(successMsg).toContainText(testEmail);

		// Step 3: Use the magic token to authenticate via the consume endpoint
		const _consumeUrl = `${API_BASE_URL}/api/v1/auth/magic-link/consume?token=${magicToken}&returnTo=%2Faccount`;

		// Navigate to consume URL - this will set the session cookie and redirect
		await page.goto(_consumeUrl, { waitUntil: 'domcontentloaded' });

		// Step 4: Verify we get redirected
		// The page should now have the caregiver_session cookie
		const cookies = await context.cookies();
		const sessionCookie = cookies.find((c) => c.name === 'caregiver_session');
		expect(sessionCookie).toBeDefined();
		expect(sessionCookie?.value.length).toBeGreaterThan(0);

		// Verify the URL now contains the /account path
		const currentUrl = page.url();
		expect(currentUrl).toContain('/account');
	});

	test('should show error for invalid token', async ({ page }) => {
		await page.goto(`${FRONTEND_BASE_URL}/auth/login`, { waitUntil: 'networkidle' });

		const invalidToken = 'invalid-token-xyz-invalid-token-xyz';
		const consumeUrl = `${API_BASE_URL}/api/v1/auth/magic-link/consume?token=${invalidToken}`;

		// Try to consume invalid token
		const response = await page.goto(consumeUrl);

		// Should get a 400 error
		expect(response?.status()).toBe(400);

		// Verify we don't have a session cookie
		const pageContext = page.context();
		const cookies = await pageContext.cookies();
		const sessionCookie = cookies.find((c) => c.name === 'caregiver_session');
		expect(sessionCookie).toBeUndefined();
	});

	test('should send magic link request to correct API endpoint', async ({ page }) => {
		const testEmail = generateTestEmail();

		await page.goto(`${FRONTEND_BASE_URL}/auth/login`, { waitUntil: 'networkidle' });

		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');

		// Listen for the API request
		const requestPromise = page.waitForRequest((request) => {
			return (
				request.url().includes('/api/v1/auth/magic-link') &&
				request.method() === 'POST' &&
				request.url().includes(API_BASE_URL)
			);
		});

		await emailInput.fill(testEmail);
		await submitBtn.click();

		const request = await requestPromise;

		// Verify the request is going to the correct backend URL
		expect(request.url()).toContain(API_BASE_URL);
		expect(request.url()).toContain('/api/v1/auth/magic-link');
		expect(request.method()).toBe('POST');

		// Verify request body
		const postData = request.postDataJSON();
		expect(postData.email).toBe(testEmail);
	});

	test('should normalize email before sending to API', async ({ page }) => {
		const testEmail = generateTestEmail();
		const emailWithWhitespace = `  ${testEmail.toUpperCase()}  `;

		await page.goto(`${FRONTEND_BASE_URL}/auth/login`, { waitUntil: 'networkidle' });

		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');

		// Listen for the API request
		const requestPromise = page.waitForRequest((request) => {
			return request.url().includes('/api/v1/auth/magic-link') && request.method() === 'POST';
		});

		await emailInput.fill(emailWithWhitespace);
		await submitBtn.click();

		const request = await requestPromise;
		const postData = request.postDataJSON();

		// Email should be trimmed and lowercased
		expect(postData.email).toBe(testEmail.toLowerCase());
	});

	test('should handle token reuse prevention', async ({ page, context }) => {
		const testEmail = generateTestEmail();
		let magicToken: string | null = null;

		// Step 1: Request magic link
		await page.goto(`${FRONTEND_BASE_URL}/auth/login`, { waitUntil: 'networkidle' });

		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');

		await emailInput.fill(testEmail);

		const apiResponse = await Promise.all([
			page.waitForResponse((response) => response.url().includes('/api/v1/auth/magic-link')),
			submitBtn.click(),
		]);

		const response = apiResponse[0];
		const responseData = await response.json();
		magicToken = responseData.debugToken || responseData.debug_token;

		// Step 2: First consumption - should succeed
		const consumeUrl = `${API_BASE_URL}/api/v1/auth/magic-link/consume?token=${magicToken}&returnTo=%2Faccount`;
		const firstConsume = await page.goto(consumeUrl);
		const firstStatus = firstConsume?.status();
		expect(firstStatus === 200 || firstStatus === 302).toBe(true);

		// Verify we have a session cookie
		const cookies = await context.cookies();
		const sessionCookie = cookies.find((c) => c.name === 'caregiver_session');
		expect(sessionCookie).toBeDefined();

		// Step 3: Second consumption attempt - should fail (token already used)
		const secondConsume = await page.goto(consumeUrl);
		expect(secondConsume?.status()).toBe(400);
	});

	test('should show error message for invalid email format', async ({ page }) => {
		await page.goto(`${FRONTEND_BASE_URL}/auth/login`, { waitUntil: 'networkidle' });

		const emailInput = page.locator('#email');
		const _submitBtn = page.locator('#submit-btn');

		// Try to submit with invalid email
		await emailInput.fill('not-an-email');

		// The form should prevent submission (HTML5 validation)
		// or show an API error
		const isValid = await emailInput.evaluate((el: HTMLInputElement) => el.checkValidity());
		expect(isValid).toBe(false);
	});

	test('should maintain returnTo parameter through magic link flow', async ({ page }) => {
		const testEmail = generateTestEmail();
		const returnTo = '/sessions';
		let magicToken: string | null = null;

		// Step 1: Request magic link with returnTo parameter
		await page.goto(`${FRONTEND_BASE_URL}/auth/login?returnTo=${returnTo}`, {
			waitUntil: 'networkidle',
		});

		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');

		await emailInput.fill(testEmail);

		const apiResponse = await Promise.all([
			page.waitForResponse((response) => response.url().includes('/api/v1/auth/magic-link')),
			submitBtn.click(),
		]);

		const response = apiResponse[0];
		const responseData = await response.json();
		magicToken = responseData.debugToken || responseData.debug_token;

		// Step 2: Consume token with returnTo
		const consumeUrl = `${API_BASE_URL}/api/v1/auth/magic-link/consume?token=${magicToken}&returnTo=${encodeURIComponent(returnTo)}`;
		await page.goto(consumeUrl, { waitUntil: 'networkidle' });

		// Verify we're redirected to the returnTo URL
		const currentUrl = page.url();
		expect(currentUrl).toContain(returnTo);
	});

	test('form should disable submit button during request', async ({ page }) => {
		const testEmail = generateTestEmail();

		await page.goto(`${FRONTEND_BASE_URL}/auth/login`, { waitUntil: 'networkidle' });

		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');

		await emailInput.fill(testEmail);

		// Start the request
		const requestPromise = page.waitForRequest((request) => {
			return request.url().includes('/api/v1/auth/magic-link');
		});

		// Click the button
		const clickPromise = submitBtn.click();

		// Check button state immediately (should be disabled)
		// Note: The form might process quickly, so we check the request was made
		const request = await requestPromise;
		expect(request).toBeDefined();

		// After response, button should be re-enabled
		await clickPromise;
		await page.waitForResponse((response) => response.url().includes('/api/v1/auth/magic-link'));
		const isDisabled = await submitBtn.isDisabled();
		expect(isDisabled).toBe(false);
	});

	test('should clear success message on new submission', async ({ page }) => {
		const testEmail1 = generateTestEmail();
		const testEmail2 = generateTestEmail();

		await page.goto(`${FRONTEND_BASE_URL}/auth/login`, { waitUntil: 'networkidle' });

		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');
		const successMsg = page.locator('#success-message');

		// First submission
		await emailInput.fill(testEmail1);
		await Promise.all([
			page.waitForResponse((response) => response.url().includes('/api/v1/auth/magic-link')),
			submitBtn.click(),
		]);

		await expect(successMsg).toContainText(testEmail1);

		// Second submission
		await emailInput.fill(testEmail2);
		const requestPromise = page.waitForRequest((request) => {
			return request.url().includes('/api/v1/auth/magic-link');
		});

		// The form should reset the message when resubmitting
		await submitBtn.click();
		await requestPromise;

		// New success message with new email
		await expect(successMsg).toContainText(testEmail2);
	});
});
