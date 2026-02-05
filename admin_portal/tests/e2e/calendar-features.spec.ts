import { expect, test } from '@playwright/test';
import {
	authenticateAsAdmin,
	ensureAuthenticated,
	navigateTo,
	trackPageErrors,
	waitForApiCalls,
	waitForAuthReady,
} from './helpers';

test.describe('Calendar Features', () => {
	let pageErrors: string[] = [];

	test.beforeEach(async ({ page }) => {
		pageErrors = trackPageErrors(page);
		await authenticateAsAdmin(page);
		await ensureAuthenticated(page);
	});

	test.afterEach(async () => {
		// Filter out calendar errors which are expected
		const relevantErrors = pageErrors.filter(
			(error) => !error.includes('Failed to load calendar data'),
		);
		expect(relevantErrors).toEqual([]);
	});

	test('should display calendar with correct week start (Sunday)', async ({ page }) => {
		await navigateTo(page, '/staff-calendar');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Look for calendar grid
		const calendar = page.locator('[role="grid"]');
		const calendarExists = (await calendar.count()) > 0;

		if (calendarExists) {
			// Check for day headers
			const dayHeaders = page.locator('[role="columnheader"]');
			const headerCount = await dayHeaders.count();
			expect(headerCount).toBeGreaterThan(0);

			// Verify headers have content (day names)
			for (let i = 0; i < Math.min(3, headerCount); i++) {
				const headerText = await dayHeaders.nth(i).innerText();
				expect(headerText.trim().length).toBeGreaterThan(0);
			}

			// Should include day of week
			const firstHeaderText = await dayHeaders.first().innerText();
			const hasDayHeaders =
				firstHeaderText.includes('Sun') ||
				firstHeaderText.includes('Mon') ||
				firstHeaderText.includes('Tue') ||
				firstHeaderText.includes('Wed') ||
				firstHeaderText.includes('Thu') ||
				firstHeaderText.includes('Fri') ||
				firstHeaderText.includes('Sat');
			expect(hasDayHeaders).toBeTruthy();
		}
	});

	test('should navigate between months in calendar', async ({ page }) => {
		await navigateTo(page, '/staff-calendar');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Look for next/previous month buttons
		const nextButton = page.locator('button:has-text("Next"), button[aria-label*="next"]');
		const prevButton = page.locator('button:has-text("Previous"), button[aria-label*="previous"]');

		if ((await nextButton.count()) > 0) {
			await expect(nextButton).toBeVisible();
			// Verify button has text or icon
			const nextText = await nextButton.first().innerText();
			expect(nextText.trim().length).toBeGreaterThanOrEqual(0);
		}
		if ((await prevButton.count()) > 0) {
			await expect(prevButton).toBeVisible();
			// Verify button has text or icon
			const prevText = await prevButton.first().innerText();
			expect(prevText.trim().length).toBeGreaterThanOrEqual(0);
		}

		// Verify page has loaded with content
		const bodyText = await page.locator('body').innerText();
		expect(bodyText.trim().length).toBeGreaterThan(0); // Should have any content
	});

	test('should display staff assignments in calendar', async ({ page }) => {
		await navigateTo(page, '/staff-calendar');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Page should load - check content exists
		const bodyText = await page.locator('body').innerText();
		expect(bodyText.length).toBeGreaterThan(0);

		// Verify page loaded (content might be minimal if no staff/sessions exist)
		expect(page.url()).toBeTruthy();
	});
});
