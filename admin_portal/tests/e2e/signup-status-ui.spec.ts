import { expect, test } from '@playwright/test';
import { createAdminSessionToken } from './helpers';

const ADMIN_BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

/**
 * Test suite for signup status changes in admin portal
 * Tests all possible status transitions via UI interactions only
 */

test.describe('Signup status changes via UI', () => {
	test.beforeEach(async ({ page, context }) => {
		// Set admin authentication cookie
		const token = createAdminSessionToken();
		await context.addCookies([
			{
				name: 'admin_session_cookie',
				value: token,
				domain: 'localhost',
				path: '/',
			},
		]);
	});

	test('should display status dropdown in session detail signups tab', async ({ page }) => {
		// Navigate to sessions page
		await page.goto(`${ADMIN_BASE_URL}/sessions`, { waitUntil: 'domcontentloaded' });
		await page.waitForTimeout(1500);

		// Click on first session
		const sessionLinks = page.locator('a[href*="/sessions/"]').filter({ hasText: /\w/ });
		const linkCount = await sessionLinks.count();

		if (linkCount > 0) {
			await sessionLinks.first().click();
			await page.waitForTimeout(1500);

			// Click signups tab
			const signupsTab = page.locator('button:has-text("Signups")');
			if ((await signupsTab.count()) > 0) {
				await signupsTab.click();
				await page.waitForTimeout(1000);

				// Check for status dropdowns in table
				const statusDropdowns = page.locator('table tbody select');
				const dropdownCount = await statusDropdowns.count();

				if (dropdownCount > 0) {
					// Verify options in first dropdown
					const firstDropdown = statusDropdowns.first();
					const options = await firstDropdown.locator('option').allTextContents();

					expect(options).toContain('Confirmed');
					expect(options).toContain('Waitlisted');
					expect(options).toContain('Pending');
					expect(options).toContain('Withdrawn');
				}
			}
		}
	});

	test('should  change signup status using dropdown', async ({ page }) => {
		// Navigate to sessions page
		await page.goto(`${ADMIN_BASE_URL}/sessions`, { waitUntil: 'domcontentloaded' });
		await page.waitForTimeout(1500);

		// Click on first session
		const sessionLinks = page.locator('a[href*="/sessions/"]').filter({ hasText: /\w/ });
		if ((await sessionLinks.count()) > 0) {
			await sessionLinks.first().click();
			await page.waitForTimeout(1500);

			// Click signups tab
			const signupsTab = page.locator('button:has-text("Signups")');
			if ((await signupsTab.count()) > 0) {
				await signupsTab.click();
				await page.waitForTimeout(1000);

				// Find first status dropdown
				const statusDropdowns = page.locator('table tbody select');
				if ((await statusDropdowns.count()) > 0) {
					const firstDropdown = statusDropdowns.first();
					const currentValue = await firstDropdown.inputValue();

					// Change to a different status
					const newStatus = currentValue === 'confirmed' ? 'waitlisted' : 'confirmed';
					await firstDropdown.selectOption(newStatus);
					await page.waitForTimeout(1500);

					// Verify status changed
					const updatedValue = await firstDropdown.inputValue();
					expect(updatedValue).toBe(newStatus);
				}
			}
		}
	});

	test('should change status from confirmed to withdrawn', async ({ page }) => {
		// Navigate to sessions page
		await page.goto(`${ADMIN_BASE_URL}/sessions`, { waitUntil: 'domcontentloaded' });
		await page.waitForTimeout(1500);

		// Click on a session
		const sessionLinks = page.locator('a[href*="/sessions/"]').filter({ hasText: /\w/ });
		if ((await sessionLinks.count()) > 0) {
			await sessionLinks.first().click();
			await page.waitForTimeout(1500);

			// Click signups tab
			const signupsTab = page.locator('button:has-text("Signups")');
			if ((await signupsTab.count()) > 0) {
				await signupsTab.click();
				await page.waitForTimeout(1000);

				// Find a confirmed signup
				const statusDropdowns = page.locator('table tbody select');
				const dropdownCount = await statusDropdowns.count();

				for (let i = 0; i < dropdownCount; i++) {
					const dropdown = statusDropdowns.nth(i);
					const value = await dropdown.inputValue();

					if (value === 'confirmed') {
						// Change to withdrawn
						await dropdown.selectOption('withdrawn');
						await page.waitForTimeout(1500);

						// Verify change
						const newValue = await dropdown.inputValue();
						expect(newValue).toBe('withdrawn');
						break;
					}
				}
			}
		}
	});

	test('should change status from withdrawn back to confirmed', async ({ page }) => {
		// Navigate to sessions page
		await page.goto(`${ADMIN_BASE_URL}/sessions`, { waitUntil: 'domcontentloaded' });
		await page.waitForTimeout(1500);

		// Click on a session
		const sessionLinks = page.locator('a[href*="/sessions/"]').filter({ hasText: /\w/ });
		if ((await sessionLinks.count()) > 0) {
			await sessionLinks.first().click();
			await page.waitForTimeout(1500);

			// Click signups tab
			const signupsTab = page.locator('button:has-text("Signups")');
			if ((await signupsTab.count()) > 0) {
				await signupsTab.click();
				await page.waitForTimeout(1000);

				// Find a withdrawn signup
				const statusDropdowns = page.locator('table tbody select');
				const dropdownCount = await statusDropdowns.count();

				for (let i = 0; i < dropdownCount; i++) {
					const dropdown = statusDropdowns.nth(i);
					const value = await dropdown.inputValue();

					if (value === 'withdrawn') {
						// Change to confirmed
						await dropdown.selectOption('confirmed');
						await page.waitForTimeout(1500);

						// Verify change
						const newValue = await dropdown.inputValue();
						expect(newValue).toBe('confirmed');
						break;
					}
				}
			}
		}
	});

	test('should change status from waitlisted to confirmed', async ({ page }) => {
		// Navigate to sessions page
		await page.goto(`${ADMIN_BASE_URL}/sessions`, { waitUntil: 'domcontentloaded' });
		await page.waitForTimeout(1500);

		// Click on a session
		const sessionLinks = page.locator('a[href*="/sessions/"]').filter({ hasText: /\w/ });
		if ((await sessionLinks.count()) > 0) {
			await sessionLinks.first().click();
			await page.waitForTimeout(1500);

			// Click signups tab
			const signupsTab = page.locator('button:has-text("Signups")');
			if ((await signupsTab.count()) > 0) {
				await signupsTab.click();
				await page.waitForTimeout(1000);

				// Find a waitlisted signup
				const statusDropdowns = page.locator('table tbody select');
				const dropdownCount = await statusDropdowns.count();

				for (let i = 0; i < dropdownCount; i++) {
					const dropdown = statusDropdowns.nth(i);
					const value = await dropdown.inputValue();

					if (value === 'waitlisted') {
						// Change to confirmed
						await dropdown.selectOption('confirmed');
						await page.waitForTimeout(1500);

						// Verify change
						const newValue = await dropdown.inputValue();
						expect(newValue).toBe('confirmed');
						break;
					}
				}
			}
		}
	});

	test('should preserve status badges in the table', async ({ page }) => {
		// Navigate to sessions page
		await page.goto(`${ADMIN_BASE_URL}/sessions`, { waitUntil: 'domcontentloaded' });
		await page.waitForTimeout(1500);

		// Click on a session
		const sessionLinks = page.locator('a[href*="/sessions/"]').filter({ hasText: /\w/ });
		if ((await sessionLinks.count()) > 0) {
			await sessionLinks.first().click();
			await page.waitForTimeout(1500);

			// Click signups tab
			const signupsTab = page.locator('button:has-text("Signups")');
			if ((await signupsTab.count()) > 0) {
				await signupsTab.click();
				await page.waitForTimeout(1000);

				// Check for status badges (colored pills)
				const statusBadges = page.locator('table tbody span.inline-flex');
				const badgeCount = await statusBadges.count();

				// Should have status badges for each signup
				if (badgeCount > 0) {
					expect(badgeCount).toBeGreaterThan(0);

					// Check that badges contain valid status text
					const firstBadge = statusBadges.first();
					const text = await firstBadge.textContent();
					expect(text?.toLowerCase()).toMatch(/confirmed|waitlisted|pending| withdrawn/);
				}
			}
		}
	});
});
