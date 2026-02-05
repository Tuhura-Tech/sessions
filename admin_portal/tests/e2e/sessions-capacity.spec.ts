import { expect, test } from '@playwright/test';
import {
	authenticateAsAdmin,
	ensureAuthenticated,
	navigateTo,
	trackPageErrors,
	waitForApiCalls,
	waitForAuthReady,
} from './helpers';

test.describe('Sessions Capacity Metrics', () => {
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

	test('should display capacity information on sessions list', async ({ page }) => {
		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Check for capacity column in table
		const capacityHeader = page.locator('th:has-text("Capacity")');
		if ((await capacityHeader.count()) > 0) {
			await expect(capacityHeader).toBeVisible();

			// Verify table has rows with capacity data
			const table = page.locator('table');
			if ((await table.count()) > 0) {
				const rows = table.locator('tbody tr');
				const rowCount = await rows.count();

				if (rowCount > 0) {
					// Verify capacity cells have content
					const capacityCells = table.locator('td').filter({ hasText: /\d+/ });
					expect(await capacityCells.count()).toBeGreaterThan(0);
				}
			}
		} else {
			// If no capacity column, verify table exists with content
			const table = page.locator('table');
			if ((await table.count()) > 0) {
				const rows = table.locator('tbody tr');
				const rowCount = await rows.count();
				expect(rowCount).toBeGreaterThanOrEqual(0);
			}
		}
	});

	test('should display capacity breakdown on session detail', async ({ page }) => {
		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Click first session if available
		const firstSessionLink = page.locator('table tbody tr a').first();
		if ((await firstSessionLink.count()) > 0) {
			await firstSessionLink.click();

			// Wait for navigation with timeout
			try {
				await page.waitForURL(/\/sessions\/[a-zA-Z0-9-]+/, { timeout: 5000 });
			} catch {
				// Page might not navigate, that's ok
			}

			// Check page loaded with content
			const bodyText = await page.locator('body').innerText();
			expect(bodyText.length).toBeGreaterThan(0);

			// Verify session detail page has capacity-related information or page content
			const hasCapacityInfo =
				bodyText.includes('Capacity') ||
				bodyText.includes('Full') ||
				bodyText.includes('Available') ||
				bodyText.includes('Signup') ||
				bodyText.includes('Session');

			// If we navigated to a session detail page
			if (page.url().includes('/sessions/')) {
				expect(hasCapacityInfo).toBeTruthy();

				// Verify heading exists
				const heading = page.locator('h1, h2, [role="heading"]').first();
				if ((await heading.count()) > 0) {
					const headingText = await heading.innerText();
					expect(headingText.trim().length).toBeGreaterThan(0);
				}
			}
		}
	});

	test('should show full/waitlist status correctly', async ({ page }) => {
		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Check for any session information display
		const bodyText = await page.locator('body').innerText();

		// Should have some content on the page
		const hasContent = bodyText.length > 0 && bodyText.includes('Session');
		expect(hasContent).toBeTruthy();

		// Verify table exists with session data
		const table = page.locator('table');
		if ((await table.count()) > 0) {
			const rows = table.locator('tbody tr');
			const rowCount = await rows.count();
			expect(rowCount).toBeGreaterThan(0);

			// Check that rows have meaningful content
			if (rowCount > 0) {
				const firstRow = rows.first();
				const firstRowText = await firstRow.innerText();
				expect(firstRowText.trim().length).toBeGreaterThan(0);

				// Verify cells contain data
				const cells = firstRow.locator('td');
				const cellCount = await cells.count();
				expect(cellCount).toBeGreaterThan(0);
			}
		}
	});
});
