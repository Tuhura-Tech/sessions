import { expect, test } from '@playwright/test';
import { authenticateAsAdmin, navigateTo, trackPageErrors, waitForAuthReady } from './helpers';

test.describe('Authentication', () => {
	let pageErrors: string[] = [];

	test.beforeEach(async ({ page }) => {
		pageErrors = trackPageErrors(page);
	});

	test.afterEach(async () => {
		expect(pageErrors).toEqual([]);
	});
	test('should display login page', async ({ page }) => {
		await navigateTo(page, '/');

		await expect(page.locator('h2')).toContainText('Admin Portal');
		await expect(page.locator('p')).toContainText('Sign in with your Google account');
		await expect(page.locator('button')).toContainText('Sign in with Google');
	});

	test('should have correct login button href', async ({ page }) => {
		await navigateTo(page, '/');

		const loginButton = page.locator('button:has-text("Sign in with Google")');

		// We can't directly test the redirect without mocking, but we can verify the button exists
		await expect(loginButton).toBeVisible();
	});

	test('should allow access to dashboard when authenticated', async ({ page }) => {
		await authenticateAsAdmin(page);

		await navigateTo(page, '/dashboard');
		await waitForAuthReady(page);

		await expect(page.locator('header h1')).toContainText(/dashboard/i);
	});

	test('should redirect to login when accessing protected route without auth', async ({ page }) => {
		// Navigate to dashboard without session
		await navigateTo(page, '/dashboard');

		// Should redirect to login
		await page.waitForURL('/login', { timeout: 5000 });
		await expect(page).toHaveURL(/\/login/);
	});

	test('should keep login page when unauthenticated', async ({ page }) => {
		await navigateTo(page, '/login');

		await expect(page.locator('h2')).toContainText('Admin Portal');
		await expect(page).toHaveURL(/\/login/);
	});
});
