import { expect, test } from '@playwright/test';
import {
	authenticateAsAdmin,
	ensureAuthenticated,
	navigateTo,
	trackPageErrors,
	waitForApiCalls,
	waitForAuthReady,
} from './helpers';

test.describe('Blocks Form Options', () => {
	let pageErrors: string[] = [];

	test.beforeEach(async ({ page }) => {
		pageErrors = trackPageErrors(page);
		await authenticateAsAdmin(page);
		await ensureAuthenticated(page);
	});

	test.afterEach(async () => {
		expect(pageErrors).toEqual([]);
	});

	test('should show year and block type options in create block modal', async ({ page }) => {
		await navigateTo(page, '/blocks');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		await page.getByRole('button', { name: /Create Block/i }).click();
		await expect(page.getByRole('heading', { name: /Create Block/i })).toBeVisible();

		const yearSelect = page.locator('select#select-year');
		await expect(yearSelect).toBeVisible();
		await expect(yearSelect.locator('option')).toHaveCount(5);

		const blockTypeSelect = page.locator('select#select-block-type');
		await expect(blockTypeSelect).toBeVisible();
		await expect(blockTypeSelect.locator('option')).toHaveCount(5);
		await expect(blockTypeSelect).toContainText('Special');
	});
});
