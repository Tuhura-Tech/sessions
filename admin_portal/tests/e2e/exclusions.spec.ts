import { test, expect } from '@playwright/test';
import { createAdminSessionToken } from './helpers';

test.describe('Exclusions Page', () => {
	test.beforeEach(async ({ context }) => {
		const token = createAdminSessionToken();
		await context.addCookies([
			{
				name: 'admin_session_cookie',
				value: token,
				domain: 'localhost',
				path: '/',
				httpOnly: true,
				sameSite: 'Lax',
				expires: Date.now() / 1000 + 86400,
			},
		]);
	});

	test('should load exclusions page', async ({ page }) => {
		await page.goto('http://localhost:3003/exclusions');
		await page.waitForLoadState('networkidle');

		// Check page title
		await expect(page.locator('h1')).toContainText(/Exclusion Dates/i);
	});

	test('should display year filter', async ({ page }) => {
		await page.goto('http://localhost:3003/exclusions');
		await page.waitForLoadState('networkidle');

		// Check for year filter select
		const yearFilter = page.locator('select').first();
		await expect(yearFilter).toBeVisible();

		// Should have multiple year options
		const options = await yearFilter.locator('option').count();
		expect(options).toBeGreaterThan(0);
	});

	test('should show add exclusion button', async ({ page }) => {
		await page.goto('http://localhost:3003/exclusions');
		await page.waitForLoadState('networkidle');

		// Check for Add Exclusion button
		const addButton = page.getByRole('button', { name: /Add Exclusion/i });
		await expect(addButton).toBeVisible();
	});

	test('should open modal when clicking add exclusion', async ({ page }) => {
		await page.goto('http://localhost:3003/exclusions');
		await page.waitForLoadState('networkidle');

		// Click Add Exclusion button
		const addButton = page.getByRole('button', { name: /Add Exclusion/i });
		await addButton.click();

		// Modal should appear
		await expect(page.getByText(/Add Exclusion Date/i)).toBeVisible();

		// Should have date input
		await expect(page.locator('input[type="date"]')).toBeVisible();

		// Should have reason textarea
		await expect(page.locator('textarea')).toBeVisible();
	});

	test('should display exclusions grouped by month', async ({ page }) => {
		await page.goto('http://localhost:3003/exclusions');
		await page.waitForLoadState('networkidle');

		// Wait for data to load
		await page.waitForTimeout(1000);

		// Check if either we have exclusions or an empty state
		const hasExclusions = await page.locator('.bg-white.shadow').count();
		const hasEmptyState = await page.getByText(/No exclusion dates/i).count();

		expect(hasExclusions > 0 || hasEmptyState > 0).toBeTruthy();
	});

	test('should allow filtering by year', async ({ page }) => {
		await page.goto('http://localhost:3003/exclusions');
		await page.waitForLoadState('networkidle');

		const yearFilter = page.locator('select').first();
		const initialYear = await yearFilter.inputValue();

		// Change year
		await yearFilter.selectOption({ index: 1 });
		await page.waitForLoadState('networkidle');

		const newYear = await yearFilter.inputValue();
		expect(newYear).not.toBe(initialYear);
	});

	test('should display edit and delete buttons for existing exclusions', async ({ page }) => {
		await page.goto('http://localhost:3003/exclusions');
		await page.waitForLoadState('networkidle');

		// Wait for potential data
		await page.waitForTimeout(1000);

		// If there are exclusions, check for action buttons
		const exclusionItems = page.locator('.flex.items-start.justify-between');
		const count = await exclusionItems.count();

		if (count > 0) {
			// First exclusion should have edit and delete buttons
			const firstItem = exclusionItems.first();
			await expect(firstItem.getByTitle(/Edit exclusion/i)).toBeVisible();
			await expect(firstItem.getByTitle(/Delete exclusion/i)).toBeVisible();
		}
	});

	test('should show formatted dates', async ({ page }) => {
		await page.goto('http://localhost:3003/exclusions');
		await page.waitForLoadState('networkidle');

		// Wait for data
		await page.waitForTimeout(1000);

		// Check if dates are formatted (should contain day name and full month)
		const dateTexts = page.locator('.text-sm.font-medium.text-gray-900');
		const count = await dateTexts.count();

		if (count > 0) {
			const firstDate = await dateTexts.first().textContent();
			// Should contain day name (e.g., "Monday") and full month (e.g., "January")
			expect(firstDate).toMatch(/\w+,.*\d{1,2}.*\w+.*\d{4}/);
		}
	});

	test('should navigate using sidebar', async ({ page }) => {
		await page.goto('http://localhost:3003/exclusions');
		await page.waitForLoadState('networkidle');

		// Click on Sessions in sidebar
		await page
			.getByRole('link', { name: /Sessions/i })
			.first()
			.click();
		await page.waitForLoadState('networkidle');

		// Should navigate to sessions page
		await expect(page).toHaveURL(/\/sessions/);
	});
});
