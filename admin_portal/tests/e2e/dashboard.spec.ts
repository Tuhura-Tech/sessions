import { expect, test } from '@playwright/test';
import {
	authenticateAsAdmin,
	ensureAuthenticated,
	navigateTo,
	trackPageErrors,
	waitForApiCalls,
	waitForAuthReady,
} from './helpers';

test.describe('Dashboard', () => {
	let pageErrors: string[] = [];

	test.beforeEach(async ({ page }) => {
		pageErrors = trackPageErrors(page);
		// Mock authenticated session for all tests
		await authenticateAsAdmin(page);
		await ensureAuthenticated(page);
	});

	test.afterEach(async () => {
		// Filter out calendar errors which are expected when dashboard loads
		const relevantErrors = pageErrors.filter(
			(error) => !error.includes('Failed to load calendar data'),
		);
		expect(relevantErrors).toEqual([]);
	});

	test('should display dashboard page', async ({ page }) => {
		await navigateTo(page, '/dashboard');
		await waitForAuthReady(page);

		// Wait for page to fully load
		await waitForApiCalls(page);

		// Check page title
		await expect(page.locator('header h1')).toContainText('Dashboard');
	});

	test('should display statistics', async ({ page }) => {
		await navigateTo(page, '/dashboard');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Verify page loaded
		const bodyText = await page.locator('body').innerText();
		expect(bodyText.trim().length).toBeGreaterThan(0);

		// Verify stat cards for Full and Available Sessions
		const fullSessionsLabel = page.locator('p:has-text("Full Sessions")');
		const availableSessionsLabel = page.locator('p:has-text("Available Sessions")');

		// Both stats should be visible
		await expect(fullSessionsLabel).toBeVisible();
		await expect(availableSessionsLabel).toBeVisible();

		// Verify that stat values are numbers (0 or greater)
		const fullSessionsValue = page
			.locator('p:has-text("Full Sessions")')
			.locator('..')
			.locator('p:nth-child(2)');
		const availableSessionsValue = page
			.locator('p:has-text("Available Sessions")')
			.locator('..')
			.locator('p:nth-child(2)');

		const fullText = await fullSessionsValue.innerText();
		const availableText = await availableSessionsValue.innerText();

		expect(fullText.match(/^\d+$/)).toBeTruthy(); // Should be numeric
		expect(availableText.match(/^\d+$/)).toBeTruthy(); // Should be numeric
	});

	test('should have navigation links to main sections', async ({ page }) => {
		await navigateTo(page, '/dashboard');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Check for sidebar navigation
		const sidebar = page.locator('nav');
		await expect(sidebar).toBeVisible();

		// Check for common navigation items
		await expect(page.locator('nav a:has-text("Sessions")')).toBeVisible();
		await expect(page.locator('nav a:has-text("Locations")')).toBeVisible();
		await expect(page.locator('nav a:has-text("Blocks")')).toBeVisible();
	});

	test('should have logout button', async ({ page }) => {
		await navigateTo(page, '/dashboard');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Find logout button (may be in menu or directly visible)
		const logoutButton = page.locator(
			'button:has-text("Logout"), button:has-text("Sign Out"), [aria-label*="logout" i]',
		);

		// At least one logout option should exist
		await expect(logoutButton.first()).toBeVisible();
	});

	test('should be responsive on mobile', async ({ page }) => {
		// Set mobile viewport
		await page.setViewportSize({ width: 375, height: 667 });

		await navigateTo(page, '/dashboard');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Page should still render
		await expect(page.locator('header h1')).toContainText('Dashboard');
	});
});
