import { expect, type Page } from '@playwright/test';
import jwt from 'jsonwebtoken';

/**
 * Helper functions for Playwright tests
 */

/**
 * Backend auth configuration
 * Must match backend/app/lib/settings.py and backend/.env
 */
const AUTH_SECRET =
	process.env.ADMIN_AUTH_SECRET || process.env.AUTH_SECRET || 'dev-secret-change-me';
const ADMIN_SESSION_ALGORITHM = 'HS256';
const ADMIN_SESSION_TTL_HOURS = 24;
const TEST_ADMIN_EMAIL = 'test@example.com';
export const ADMIN_API_BASE_URL = 'http://localhost:8000/api/v1';

/**
 * Create a real admin session token using backend's JWT algorithm
 * This matches backend/app/domains/admin/guards.py create_admin_session()
 */
export function createAdminSessionToken(
	email: string = TEST_ADMIN_EMAIL,
	provider = 'debugToken',
	providerUserId = 'test123',
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

	return jwt.sign(payload, AUTH_SECRET, { algorithm: ADMIN_SESSION_ALGORITHM });
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
	// Create real JWT token
	const token = createAdminSessionToken(email);

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
			url: 'http://localhost:3002',
			httpOnly: false,
			sameSite: 'Lax',
			expires: Math.floor(Date.now() / 1000) + 86400,
		},
	]);

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
	const isAuthenticated = await waitForAuthReady(page);
	if (!isAuthenticated) {
		throw new Error(`Admin authentication failed. Current URL: ${page.url()}`);
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
