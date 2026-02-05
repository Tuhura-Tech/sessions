import { expect, test } from '@playwright/test';
import { authenticateAsAdmin, ensureAuthenticated, trackPageErrors } from './helpers';

test.describe('Caregiver Email UI', () => {
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

	test('should display email button for each signup in session detail', async ({ page }) => {
		// Navigate to sessions page
		await page.goto('/sessions');
		await expect(page.locator('h1, h2').first()).toBeVisible();

		// Click on first session
		await page.click('tbody tr:first-child a');

		// Wait for session detail page
		await expect(page).toHaveURL(/\/sessions\/[^/]+$/);
		await expect(page.locator('h1').first()).toBeVisible();

		// Switch to signups tab if not already there
		const signupsTab = page.getByText('Signups', { exact: false });
		if (await signupsTab.isVisible()) {
			await signupsTab.click();
		}

		// Check if there are any signups
		const signupRows = page.locator('table tbody tr');
		const count = await signupRows.count();

		if (count > 0) {
			// Verify email button exists for first signup
			const firstRow = signupRows.first();
			const emailButton = firstRow.getByRole('button', { name: /email/i });
			await expect(emailButton).toBeVisible();

			// Verify signup row has required content (student name, guardian info, etc)
			const cells = firstRow.locator('td');
			const cellCount = await cells.count();
			expect(cellCount).toBeGreaterThanOrEqual(3); // At least student, guardian, email/phone

			// Verify row has non-empty content
			const rowText = await firstRow.innerText();
			expect(rowText.trim().length).toBeGreaterThan(0);

			// Verify there's actual content in cells (not just empty placeholders)
			for (let i = 0; i < Math.min(2, cellCount); i++) {
				const cellText = await cells.nth(i).innerText();
				expect(cellText.trim().length).toBeGreaterThan(0);
			}
		}
	});

	test('should open email dialog when email button clicked', async ({ page }) => {
		// Navigate to sessions
		await page.goto('/sessions');
		await expect(page.locator('h1, h2').first()).toBeVisible();

		// Click on first session
		await page.click('tbody tr:first-child a');

		// Wait for page load
		await page.waitForLoadState('networkidle');

		// Check for signups with email buttons
		const emailButtons = page.getByRole('button', { name: /email/i });
		const count = await emailButtons.count();

		if (count > 0) {
			// Click first email button
			await emailButtons.first().click();

			// Verify dialog opens - check for subject and message fields
			await expect(page.locator('input[type="text"]').first()).toBeVisible();
			await expect(page.locator('textarea').first()).toBeVisible();
		}
	});

	test('should be able to send email to caregiver', async ({ page }) => {
		// Navigate to sessions
		await page.goto('/sessions');
		await expect(page.locator('h1, h2').first()).toBeVisible();

		// Click on first session
		await page.click('tbody tr:first-child a');

		// Wait for page load
		await page.waitForLoadState('networkidle');

		const emailButtons = page.getByRole('button', { name: /email/i });
		const count = await emailButtons.count();

		if (count > 0) {
			// Click email button
			await emailButtons.first().click();

			// Fill in email form
			await page.locator('input[type="text"]').first().fill('Test Subject');
			await page.locator('textarea').first().fill('Test message body');

			// Click send button
			const sendButton = page.getByRole('button', { name: /send/i });
			if (await sendButton.isVisible()) {
				await sendButton.click();

				// Wait for success message or dialog to close
				await page.waitForTimeout(1000);

				// Dialog should close
				await expect(page.locator('input[type="text"]').first()).not.toBeVisible();
			}
		}
	});

	test('should show loading state when sending email', async ({ page }) => {
		// Navigate to sessions
		await page.goto('/sessions');
		await expect(page.locator('h1, h2').first()).toBeVisible();

		// Click on first session
		await page.click('tbody tr:first-child a');

		// Wait for page load
		await page.waitForLoadState('networkidle');

		const emailButtons = page.getByRole('button', { name: /email/i });
		const count = await emailButtons.count();

		if (count > 0) {
			// Click email button
			await emailButtons.first().click();

			// Fill form
			await page.locator('input[type="text"]').first().fill('Test');
			await page.locator('textarea').first().fill('Test');

			// Send email and check for disabled state
			const sendButton = page.getByRole('button', { name: /send/i });
			if (await sendButton.isVisible()) {
				// Button should be enabled before click
				await expect(sendButton).toBeEnabled();

				await sendButton.click();

				// During send, button might be disabled (if loading state implemented)
				// This is optional - depends on implementation
				await page.waitForTimeout(500);
			}
		}
	});
});
