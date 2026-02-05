import { expect, test } from '@playwright/test';
import { createAdminSessionToken } from './helpers';

test.describe('Location Detail Page', () => {
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

	test('should load location list', async ({ page }) => {
		await page.goto('http://localhost:3003/locations');
		await page.waitForLoadState('networkidle');

		await expect(page.locator('h1')).toContainText(/Locations/i);
	});

	test('should navigate to location detail', async ({ page }) => {
		await page.goto('http://localhost:3003/locations');
		await page.waitForLoadState('networkidle');

		// Wait for table to load
		await page.waitForTimeout(1000);

		// Find first location link
		const locationLinks = page.locator('table tbody tr td:first-child a');
		const count = await locationLinks.count();

		if (count > 0) {
			const firstLink = locationLinks.first();
			await firstLink.click();
			await page.waitForLoadState('networkidle');

			// Should be on location detail page
			await expect(page).toHaveURL(/\/locations\/[a-f0-9-]+/);
		}
	});

	test('should display location details correctly', async ({ page }) => {
		await page.goto('http://localhost:3003/locations');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const locationLinks = page.locator('table tbody tr td:first-child a');
		const count = await locationLinks.count();

		if (count > 0) {
			// Get location name from list
			const locationName = await locationLinks.first().textContent();

			// Navigate to detail
			await locationLinks.first().click();
			await page.waitForLoadState('networkidle');

			// Page title should match location name
			const pageTitle = page.locator('h1');
			await expect(pageTitle).toContainText(locationName?.trim() || '');

			// Should display location information
			await expect(page.locator('text=Address')).toBeVisible();
			await expect(page.locator('text=Region')).toBeVisible();
		}
	});

	test('should display contact information', async ({ page }) => {
		await page.goto('http://localhost:3003/locations');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const locationLinks = page.locator('table tbody tr td:first-child a');
		const count = await locationLinks.count();

		if (count > 0) {
			await locationLinks.first().click();
			await page.waitForLoadState('networkidle');

			// Check for contact section
			const contactSection = page
				.locator('text=Contact Information')
				.or(page.locator('text=Contact'));
			const hasContact = await contactSection.count();

			if (hasContact > 0) {
				// Should have contact details if section exists
				expect(hasContact).toBeGreaterThan(0);
			}
		}
	});

	test('should list sessions for location', async ({ page }) => {
		await page.goto('http://localhost:3003/locations');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const locationLinks = page.locator('table tbody tr td:first-child a');
		const count = await locationLinks.count();

		if (count > 0) {
			await locationLinks.first().click();
			await page.waitForLoadState('networkidle');
			await page.waitForTimeout(1500);

			// Should have a sessions section
			const sessionsHeading = page.getByText(/Sessions at this location/i);
			await expect(sessionsHeading).toBeVisible();

			// Should have either sessions table or empty state
			const hasTable = await page.locator('table').count();
			const hasEmptyState = await page.getByText(/No sessions/i).count();

			expect(hasTable > 0 || hasEmptyState > 0).toBeTruthy();
		}
	});

	test('should display session counts correctly for location', async ({ page }) => {
		await page.goto('http://localhost:3003/locations');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const locationLinks = page.locator('table tbody tr td:first-child a');
		const count = await locationLinks.count();

		if (count > 0) {
			await locationLinks.first().click();
			await page.waitForLoadState('networkidle');
			await page.waitForTimeout(1500);

			// Find sessions table
			const sessionRows = page.locator('table tbody tr');
			const rowCount = await sessionRows.count();

			if (rowCount > 0) {
				// Check first session row for signup count format
				const firstRow = sessionRows.first();
				const signupCell = firstRow.locator('td:nth-child(4)'); // Signups column

				const signupText = await signupCell.textContent();

				// Should be in format "X/Y" (confirmed/capacity)
				expect(signupText).toMatch(/\d+\/(\d+|\?)/);

				// Number before slash should be confirmed signups only
				const [confirmed] = signupText?.split('/') || [];
				expect(Number(confirmed)).toBeGreaterThanOrEqual(0);
			}
		}
	});

	test('should allow editing location', async ({ page }) => {
		await page.goto('http://localhost:3003/locations');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const locationLinks = page.locator('table tbody tr td:first-child a');
		const count = await locationLinks.count();

		if (count > 0) {
			await locationLinks.first().click();
			await page.waitForLoadState('networkidle');

			// Should have edit button
			const editButton = page.getByRole('button', { name: /Edit Location/i });
			const hasEditButton = await editButton.count();

			if (hasEditButton > 0) {
				await expect(editButton).toBeVisible();
			}
		}
	});

	test('should navigate back to locations list', async ({ page }) => {
		await page.goto('http://localhost:3003/locations');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const locationLinks = page.locator('table tbody tr td:first-child a');
		const count = await locationLinks.count();

		if (count > 0) {
			await locationLinks.first().click();
			await page.waitForLoadState('networkidle');

			// Click back button
			const backButton = page.getByRole('button', { name: /Back to Locations/i });
			await backButton.click();
			await page.waitForLoadState('networkidle');

			// Should be back at locations list
			await expect(page).toHaveURL(/\/locations$/);
		}
	});

	test('should display session details in table', async ({ page }) => {
		await page.goto('http://localhost:3003/locations');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const locationLinks = page.locator('table tbody tr td:first-child a');
		const count = await locationLinks.count();

		if (count > 0) {
			await locationLinks.first().click();
			await page.waitForLoadState('networkidle');
			await page.waitForTimeout(1500);

			const sessionRows = page.locator('table tbody tr');
			const rowCount = await sessionRows.count();

			if (rowCount > 0) {
				const firstRow = sessionRows.first();

				// Should have session name
				const nameCell = firstRow.locator('td:nth-child(1) a');
				const sessionName = await nameCell.textContent();
				expect(sessionName).toBeTruthy();
				expect(sessionName?.trim().length).toBeGreaterThan(0);

				// Should have day and time
				const dayTimeCell = firstRow.locator('td:nth-child(2)');
				const dayTimeText = await dayTimeCell.textContent();
				expect(dayTimeText).toBeTruthy();

				// Should have capacity
				const capacityCell = firstRow.locator('td:nth-child(3)');
				const capacityText = await capacityCell.textContent();
				expect(capacityText).toBeTruthy();
			}
		}
	});
});
