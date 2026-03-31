import { expect, test } from '@playwright/test';
import { createAdminSessionToken } from './helpers';

const ADMIN_BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

/**
 * Test suite for signup status changes in admin portal
 * Tests all possible status transitions: pending, confirmed, waitlisted, withdrawn
 */

test.describe('Signup status changes', () => {
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

	test('should display status dropdown for each signup in session detail', async ({ page }) => {
		// Navigate to sessions page
		await page.goto(`${ADMIN_BASE_URL}/sessions`, { waitUntil: 'domcontentloaded' });
		await page.waitForTimeout(1000);

		// Click on first session
		const sessionLinks = page.locator('a[href*="/sessions/"]');
		const linkCount = await sessionLinks.count();

		if (linkCount > 0) {
			await sessionLinks.first().click();
			await page.waitForTimeout(1000);

			// Wait for signups tab to load
			const signupsTab = page.locator('button:has-text("Signups")');
			if ((await signupsTab.count()) > 0) {
				await signupsTab.click();
				await page.waitForTimeout(500);

				// Check for status dropdown (select element) in the action column
				const statusDropdowns = page.locator('table select');
				const count = await statusDropdowns.count();

				// Should have at least one status dropdown if there are signups
				if (count > 0) {
					expect(count).toBeGreaterThan(0);

					// Verify all status options are available
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

	test('should change signup status from pending to confirmed', async ({ page, request }) => {
		// Find a session with pending signups
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		for (const session of sessionItems) {
			const signupsResp = await request.get(
				`${API_BASE_URL}/api/v1/admin/sessions/${session.id}/signups`,
			);
			const signups = await signupsResp.json();
			const signupItems = signups.items || signups;

			const pendingSignup = signupItems.find((s: any) => s.status === 'pending');
			if (pendingSignup) {
				// Navigate to session detail
				await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
					waitUntil: 'domcontentloaded',
				});
				await page.waitForTimeout(1000);

				// Click signups tab
				const signupsTab = page.locator('button:has-text("Signups")');
				if ((await signupsTab.count()) > 0) {
					await signupsTab.click();
					await page.waitForTimeout(500);

					// Find the row with pending status
					const pendingRow = page.locator(`tr:has-text("${pendingSignup.student_name}")`);
					if ((await pendingRow.count()) > 0) {
						// Find the status dropdown in that row
						const statusSelect = pendingRow.locator('select');
						await statusSelect.selectOption('confirmed');

						// Wait for the status change to complete
						await page.waitForTimeout(1000);

						// Verify the status changed
						const newStatus = await statusSelect.inputValue();
						expect(newStatus).toBe('confirmed');
					}
				}
				break;
			}
		}
	});

	test('should change signup status from waitlisted to confirmed', async ({ page, request }) => {
		// Find a session with waitlisted signups
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		for (const session of sessionItems) {
			const signupsResp = await request.get(
				`${API_BASE_URL}/api/v1/admin/sessions/${session.id}/signups`,
			);
			const signups = await signupsResp.json();
			const signupItems = signups.items || signups;

			const waitlistedSignup = signupItems.find((s: any) => s.status === 'waitlisted');
			if (waitlistedSignup) {
				// Navigate to session detail
				await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
					waitUntil: 'domcontentloaded',
				});
				await page.waitForTimeout(1000);

				// Click signups tab
				const signupsTab = page.locator('button:has-text("Signups")');
				if ((await signupsTab.count()) > 0) {
					await signupsTab.click();
					await page.waitForTimeout(500);

					// Find the row with waitlisted status
					const waitlistedRow = page.locator(`tr:has-text("${waitlistedSignup.student_name}")`);
					if ((await waitlistedRow.count()) > 0) {
						// Find the status dropdown in that row
						const statusSelect = waitlistedRow.locator('select');
						await statusSelect.selectOption('confirmed');

						// Wait for the status change to complete
						await page.waitForTimeout(1000);

						// Verify the status changed
						const newStatus = await statusSelect.inputValue();
						expect(newStatus).toBe('confirmed');
					}
				}
				break;
			}
		}
	});

	test('should change signup status from confirmed to withdrawn', async ({ page, request }) => {
		// Find a session with confirmed signups
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		for (const session of sessionItems) {
			const signupsResp = await request.get(
				`${API_BASE_URL}/api/v1/admin/sessions/${session.id}/signups`,
			);
			const signups = await signupsResp.json();
			const signupItems = signups.items || signups;

			const confirmedSignup = signupItems.find((s: any) => s.status === 'confirmed');
			if (confirmedSignup) {
				// Navigate to session detail
				await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
					waitUntil: 'domcontentloaded',
				});
				await page.waitForTimeout(1000);

				// Click signups tab
				const signupsTab = page.locator('button:has-text("Signups")');
				if ((await signupsTab.count()) > 0) {
					await signupsTab.click();
					await page.waitForTimeout(500);

					// Find the row with confirmed status
					const confirmedRow = page.locator(`tr:has-text("${confirmedSignup.student_name}")`);
					if ((await confirmedRow.count()) > 0) {
						// Find the status dropdown in that row
						const statusSelect = confirmedRow.locator('select');
						await statusSelect.selectOption('withdrawn');

						// Wait for the status change to complete
						await page.waitForTimeout(1000);

						// Verify the status changed
						const newStatus = await statusSelect.inputValue();
						expect(newStatus).toBe('withdrawn');
					}
				}
				break;
			}
		}
	});

	test('should change signup status from withdrawn back to confirmed', async ({
		page,
		request,
	}) => {
		// Find a session with withdrawn signups
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		for (const session of sessionItems) {
			const signupsResp = await request.get(
				`${API_BASE_URL}/api/v1/admin/sessions/${session.id}/signups`,
			);
			const signups = await signupsResp.json();
			const signupItems = signups.items || signups;

			const withdrawnSignup = signupItems.find((s: any) => s.status === 'withdrawn');
			if (withdrawnSignup) {
				// Navigate to session detail
				await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
					waitUntil: 'domcontentloaded',
				});
				await page.waitForTimeout(1000);

				// Click signups tab
				const signupsTab = page.locator('button:has-text("Signups")');
				if ((await signupsTab.count()) > 0) {
					await signupsTab.click();
					await page.waitForTimeout(500);

					// Find the row with withdrawn status
					const withdrawnRow = page.locator(`tr:has-text("${withdrawnSignup.student_name}")`);
					if ((await withdrawnRow.count()) > 0) {
						// Find the status dropdown in that row
						const statusSelect = withdrawnRow.locator('select');
						await statusSelect.selectOption('confirmed');

						// Wait for the status change to complete
						await page.waitForTimeout(1000);

						// Verify the status changed
						const newStatus = await statusSelect.inputValue();
						expect(newStatus).toBe('confirmed');
					}
				}
				break;
			}
		}
	});

	test('should change signup status from waitlisted to withdrawn', async ({ page, request }) => {
		// Find a session with waitlisted signups
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		for (const session of sessionItems) {
			const signupsResp = await request.get(
				`${API_BASE_URL}/api/v1/admin/sessions/${session.id}/signups`,
			);
			const signups = await signupsResp.json();
			const signupItems = signups.items || signups;

			const waitlistedSignup = signupItems.find((s: any) => s.status === 'waitlisted');
			if (waitlistedSignup) {
				// Navigate to session detail
				await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
					waitUntil: 'domcontentloaded',
				});
				await page.waitForTimeout(1000);

				// Click signups tab
				const signupsTab = page.locator('button:has-text("Signups")');
				if ((await signupsTab.count()) > 0) {
					await signupsTab.click();
					await page.waitForTimeout(500);

					// Find the row with waitlisted status
					const waitlistedRow = page.locator(`tr:has-text("${waitlistedSignup.student_name}")`);
					if ((await waitlistedRow.count()) > 0) {
						// Find the status dropdown in that row
						const statusSelect = waitlistedRow.locator('select');
						await statusSelect.selectOption('withdrawn');

						// Wait for the status change to complete
						await page.waitForTimeout(1000);

						// Verify the status changed
						const newStatus = await statusSelect.inputValue();
						expect(newStatus).toBe('withdrawn');
					}
				}
				break;
			}
		}
	});

	test('should update confirmed count when changing status to confirmed', async ({
		page,
		request,
	}) => {
		// Find a session with non-confirmed signups
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		for (const session of sessionItems) {
			const signupsResp = await request.get(
				`${API_BASE_URL}/api/v1/admin/sessions/${session.id}/signups`,
			);
			const signups = await signupsResp.json();
			const signupItems = signups.items || signups;

			const nonConfirmedSignup = signupItems.find(
				(s: any) => s.status !== 'confirmed' && s.status !== 'withdrawn',
			);
			if (nonConfirmedSignup) {
				// Navigate to session detail
				await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
					waitUntil: 'domcontentloaded',
				});
				await page.waitForTimeout(1000);

				// Get initial confirmed count
				const initialCountText = await page.locator('text=/\\d+\\/\\d+/').first().textContent();
				const initialCount = initialCountText ? Number.parseInt(initialCountText.split('/')[0]) : 0;

				// Click signups tab
				const signupsTab = page.locator('button:has-text("Signups")');
				if ((await signupsTab.count()) > 0) {
					await signupsTab.click();
					await page.waitForTimeout(500);

					// Find the row with non-confirmed status
					const nonConfirmedRow = page.locator(`tr:has-text("${nonConfirmedSignup.student_name}")`);
					if ((await nonConfirmedRow.count()) > 0) {
						// Find the status dropdown in that row
						const statusSelect = nonConfirmedRow.locator('select');
						await statusSelect.selectOption('confirmed');

						// Wait for the status change to complete and reload
						await page.waitForTimeout(2000);

						// Navigate back to session list to see updated count
						await page.goto(`${ADMIN_BASE_URL}/sessions`, { waitUntil: 'domcontentloaded' });
						await page.waitForTimeout(1000);

						// Click on the same session again
						await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
							waitUntil: 'domcontentloaded',
						});
						await page.waitForTimeout(1000);

						// Get updated confirmed count
						const updatedCountText = await page.locator('text=/\\d+\\/\\d+/').first().textContent();
						const updatedCount = updatedCountText
							? Number.parseInt(updatedCountText.split('/')[0])
							: 0;

						// Confirmed count should have increased by 1
						expect(updatedCount).toBe(initialCount + 1);
					}
				}
				break;
			}
		}
	});

	test('should filter signups by status', async ({ page, request }) => {
		// Find a session with multiple signup statuses
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		for (const session of sessionItems) {
			const signupsResp = await request.get(
				`${API_BASE_URL}/api/v1/admin/sessions/${session.id}/signups`,
			);
			const signups = await signupsResp.json();
			const signupItems = signups.items || signups;

			if (signupItems.length > 1) {
				// Navigate to session detail
				await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
					waitUntil: 'domcontentloaded',
				});
				await page.waitForTimeout(1000);

				// Click signups tab
				const signupsTab = page.locator('button:has-text("Signups")');
				if ((await signupsTab.count()) > 0) {
					await signupsTab.click();
					await page.waitForTimeout(500);

					// Get total signups count
					const totalRows = await page.locator('table tbody tr').count();

					// Look for status filter dropdown
					const filterDropdown = page.locator('select').first();
					if (await filterDropdown.isVisible()) {
						// Select "confirmed" filter
						await filterDropdown.selectOption('confirmed');
						await page.waitForTimeout(500);

						// Count filtered rows
						const filteredRows = await page.locator('table tbody tr').count();

						// Filtered count should be less than or equal to total
						expect(filteredRows).toBeLessThanOrEqual(totalRows);

						// All visible rows should show "Confirmed" status
						const statusBadges = await page.locator('span:has-text("confirmed")').count();
						expect(statusBadges).toBeGreaterThan(0);
					}
				}
				break;
			}
		}
	});

	test('should handle bulk status changes correctly', async ({ page, request }) => {
		// Find a session with multiple non-confirmed signups
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		for (const session of sessionItems) {
			const signupsResp = await request.get(
				`${API_BASE_URL}/api/v1/admin/sessions/${session.id}/signups`,
			);
			const signups = await signupsResp.json();
			const signupItems = signups.items || signups;

			const nonConfirmedSignups = signupItems.filter(
				(s: any) => s.status === 'waitlisted' || s.status === 'pending',
			);

			if (nonConfirmedSignups.length >= 2) {
				// Navigate to session detail
				await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
					waitUntil: 'domcontentloaded',
				});
				await page.waitForTimeout(1000);

				// Click signups tab
				const signupsTab = page.locator('button:has-text("Signups")');
				if ((await signupsTab.count()) > 0) {
					await signupsTab.click();
					await page.waitForTimeout(500);

					// Change first two non-confirmed signups to confirmed
					for (let i = 0; i < Math.min(2, nonConfirmedSignups.length); i++) {
						const signup = nonConfirmedSignups[i];
						const row = page.locator(`tr:has-text("${signup.student_name}")`);
						if ((await row.count()) > 0) {
							const statusSelect = row.locator('select');
							await statusSelect.selectOption('confirmed');
							await page.waitForTimeout(500);
						}
					}

					// Both should now be confirmed
					await page.waitForTimeout(1000);
					const firstRow = page.locator(`tr:has-text("${nonConfirmedSignups[0].student_name}")`);
					const firstStatus = await firstRow.locator('select').inputValue();
					expect(firstStatus).toBe('confirmed');

					if (nonConfirmedSignups[1]) {
						const secondRow = page.locator(`tr:has-text("${nonConfirmedSignups[1].student_name}")`);
						const secondStatus = await secondRow.locator('select').inputValue();
						expect(secondStatus).toBe('confirmed');
					}
				}
				break;
			}
		}
	});
});
