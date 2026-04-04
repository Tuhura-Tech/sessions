import { expect, type Page } from '@playwright/test';
import jwt from 'jsonwebtoken';

/**
 * Helper functions for Playwright tests
 */

/**
 * Backend auth configuration
 * Must match backend/app/lib/settings.py and backend/.env
 */
const AUTH_SECRET = process.env.PLAYWRIGHT_AUTH_SECRET || 'playwright-dev-secret';
const ADMIN_SESSION_ALGORITHM = 'HS256';
const ADMIN_SESSION_TTL_HOURS = 24;
const TEST_ADMIN_EMAIL = 'test@example.com';
const BASE_HOST = process.env.CI ? '127.0.0.1' : 'localhost';
export const ADMIN_API_BASE_URL = `http://${BASE_HOST}:8000/api/v1`;

const AUTH_SECRET_CANDIDATES = [
	process.env.PLAYWRIGHT_AUTH_SECRET,
	process.env.AUTH_SECRET,
	'playwright-dev-secret',
	'your-secret-key-change-me-in-production',
	'dev-secret-change-me',
].filter((secret): secret is string => Boolean(secret));

/**
 * Create a real admin session token using backend's JWT algorithm
 * This matches backend/app/domains/admin/guards.py create_admin_session()
 */
export function createAdminSessionToken(
	email: string = TEST_ADMIN_EMAIL,
	provider = 'debugToken',
	providerUserId = 'test123',
	authSecret: string = AUTH_SECRET,
): string {
	const now = Math.floor(Date.now() / 1000);
	const exp = now + ADMIN_SESSION_TTL_HOURS * 60 * 60;

	const payload = {
		email: email.trim().toLowerCase(),
		provider: provider,
		provider_user_id: providerUserId,
		iat: now,
		exp: exp,
	};

	return jwt.sign(payload, authSecret, { algorithm: ADMIN_SESSION_ALGORITHM });
}

export function getAdminSessionCookie(email: string = TEST_ADMIN_EMAIL): string {
	return `admin_session=${createAdminSessionToken(email)}`;
}

export function getAdminAuthHeaders(email: string = TEST_ADMIN_EMAIL): Record<string, string> {
	const token = createAdminSessionToken(email);
	return {
		Authorization: `Bearer ${token}`,
	};
}

async function resolveValidAdminToken(page: Page, email: string): Promise<string> {
	for (const secret of AUTH_SECRET_CANDIDATES) {
		const token = createAdminSessionToken(email, 'debugToken', 'test123', secret);
		const response = await page.request
			.get(`${ADMIN_API_BASE_URL}/admin/auth/me`, {
				headers: { Authorization: `Bearer ${token}` },
			})
			.catch(() => undefined);

		const body = response ? await response.json().catch(() => ({})) : {};
		if (response?.status() === 200 && (body as { hasSession?: boolean }).hasSession === true) {
			return token;
		}
	}

	return createAdminSessionToken(email);
}

export function unwrapListResponse<T>(data: unknown): T[] {
	if (Array.isArray(data)) return data as T[];
	return ((data as { items?: T[] })?.items || []) as T[];
}

/**
 * Wait for API requests to complete
 */
export async function waitForApiCalls(page: Page, timeout = 5000) {
	await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Authenticate with real backend session token
 * Creates a JWT token that matches backend's admin_session_cookie fixture
 * NO API MOCKING - all requests go to real backend
 *
 * Uses route interception to inject the cookie into API requests since
 * cross-port cookies (3002 -> 8000) don't work reliably in Playwright.
 */
export async function authenticateAsAdmin(page: Page, email: string = TEST_ADMIN_EMAIL) {
	// Resolve a token that matches the backend's current AUTH_SECRET.
	const token = await resolveValidAdminToken(page, email);
	const verifyResponse = await page.request.get(`${ADMIN_API_BASE_URL}/admin/auth/me`, {
		headers: { Authorization: `Bearer ${token}` },
	});
	const verifyBody = await verifyResponse.json().catch(() => ({}));
	if ((verifyBody as { hasSession?: boolean }).hasSession !== true) {
		throw new Error('Could not establish a valid admin token for E2E authentication');
	}

	// Inject token for axios request interceptor
	await page.addInitScript((tokenValue) => {
		(window as any).__adminToken = tokenValue;
		try {
			localStorage.setItem('adminToken', tokenValue);
		} catch {
			// Ignore storage issues
		}
	}, token);

	// Set a non-httpOnly cookie for same-site requests
	await page.context().addCookies([
		{
			name: 'admin_session',
			value: token,
			url: `http://${BASE_HOST}:3002`,
			httpOnly: false,
			sameSite: 'Lax',
			expires: Math.floor(Date.now() / 1000) + 86400,
		},
		{
			name: 'admin_session',
			value: token,
			url: `http://${BASE_HOST}:8000`,
			httpOnly: false,
			sameSite: 'Lax',
			expires: Math.floor(Date.now() / 1000) + 86400,
		},
	]);

	// Also set token on a concrete app origin immediately.
	await page.goto('/login');
	await page.evaluate((tokenValue) => {
		(window as any).__adminToken = tokenValue;
		try {
			localStorage.setItem('adminToken', tokenValue);
		} catch {
			// Ignore storage issues
		}
	}, token);

	// Ensure all API calls carry the admin token, independent of app startup timing.
	await page.route('**/api/v1/**', async (route) => {
		const headers = {
			...route.request().headers(),
			Authorization: `Bearer ${token}`,
		};
		await route.continue({ headers });
	});

	// No request interception needed; axios interceptor sends Authorization header.
}

export async function waitForAuthReady(page: Page, timeout = 10000) {
	const response = await page
		.waitForResponse(
			(response) => response.url().includes('/api/v1/admin/auth/me') && response.status() === 200,
			{ timeout },
		)
		.catch(() => undefined);

	await page.waitForLoadState('networkidle', { timeout }).catch(() => undefined);
	return Boolean(response);
}

/**
 * Navigate to page and wait for load
 */
export async function navigateTo(page: Page, url: string) {
	await page.goto(url);
	await page.waitForLoadState('domcontentloaded');
}

export async function ensureAuthenticated(page: Page) {
	await navigateTo(page, '/dashboard');
	await page.waitForLoadState('networkidle').catch(() => undefined);
	const diagnostics = await page
		.evaluate(async () => {
			const token =
				(window as typeof window & { __adminToken?: string }).__adminToken ||
				localStorage.getItem('adminToken');
			const response = await fetch('/api/v1/admin/auth/me', {
				credentials: 'include',
				headers: token ? { Authorization: `Bearer ${token}` } : undefined,
			}).catch(() => undefined);

			let body: unknown;
			if (response) {
				body = await response.json().catch(() => undefined);
			}

			return {
				hasToken: Boolean(token),
				status: response?.status,
				body,
			};
		})
		.catch(() => ({ hasToken: false, status: undefined, body: undefined }));

	if ((diagnostics.body as { hasSession?: boolean } | undefined)?.hasSession !== true) {
		throw new Error(
			`Admin authentication failed. Current URL: ${page.url()} | diagnostics=${JSON.stringify(diagnostics)}`,
		);
	}
}

export function trackPageErrors(page: Page) {
	const errors: string[] = [];
	page.on('pageerror', (error) => {
		errors.push(error.message);
	});
	page.on('console', (msg) => {
		if (msg.type() === 'error') {
			errors.push(msg.text());
		}
	});
	return errors;
}

/**
 * Fill form and submit
 */
export async function fillFormAndSubmit(
	page: Page,
	formData: Record<string, string>,
	submitButtonSelector = 'button[type="submit"]',
) {
	// Fill each field
	for (const [selector, value] of Object.entries(formData)) {
		const field = page.locator(selector);
		await field.fill(value);
	}

	// Submit form
	await page.locator(submitButtonSelector).click();

	// Wait for navigation or API response
	await page.waitForLoadState('networkidle');
}

/**
 * Check if element is visible and contains text
 */
export async function expectElementWithText(page: Page, selector: string, text: string) {
	const element = page.locator(selector);
	await element.isVisible();
	await expect(element).toContainText(text);
}

/**
 * Get table data as array of objects
 */
export async function getTableData(page: Page, tableSelector = 'table') {
	const rows = await page.locator(`${tableSelector} tbody tr`).all();
	const data = [];

	for (const row of rows) {
		const cells = await row.locator('td').allTextContents();
		data.push(cells);
	}

	return data;
}

/**
 * Click button by text
 */
export async function clickButtonByText(page: Page, text: string) {
	await page.locator(`button:has-text("${text}")`).click();
	await page.waitForLoadState('networkidle');
}

/**
 * Wait for notification/toast
 */
export async function waitForNotification(page: Page, text: string, timeout = 5000) {
	await page.locator(`text=${text}`).isVisible({ timeout });
}
