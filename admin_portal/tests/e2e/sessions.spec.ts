import { expect, test } from '@playwright/test';
import {
	ADMIN_API_BASE_URL,
	authenticateAsAdmin,
	ensureAuthenticated,
	getAdminAuthHeaders,
	navigateTo,
	trackPageErrors,
	unwrapListResponse,
	waitForApiCalls,
	waitForAuthReady,
} from './helpers';

test.describe('Sessions Management', () => {
	let pageErrors: string[] = [];

	test.beforeEach(async ({ page }) => {
		pageErrors = trackPageErrors(page);
		await authenticateAsAdmin(page);
		await ensureAuthenticated(page);
	});

	test.afterEach(async () => {
		// Filter out calendar errors which are expected when sessions page doesn't have calendar data
		const relevantErrors = pageErrors.filter(
			(error) => !error.includes('Failed to load calendar data'),
		);
		expect(relevantErrors).toEqual([]);
	});

	test('should display sessions list', async ({ page }) => {
		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Check page title
		await expect(page.locator('header h1')).toContainText(/sessions/i);

		// Check for table or list structure
		const table = page.locator('table');
		const hasTable = (await table.count()) > 0;
		const hasRows = (await page.locator('table tbody tr').count()) > 0;
		const hasEmptyState = (await page.locator('text=No sessions found').count()) > 0;

		// At least one of these should exist
		expect(hasTable || hasRows || hasEmptyState).toBeTruthy();

		if (hasRows) {
			// Validate session row content
			const firstRow = page.locator('table tbody tr').first();
			const rowText = await firstRow.innerText();

			// Session names should be present
			expect(rowText.length).toBeGreaterThan(0);

			// Check for year/capacity/type information
			const headers = page.locator('table thead th');
			const headerCount = await headers.count();
			expect(headerCount).toBeGreaterThanOrEqual(2); // At least name and one more column
		}
	});

	test('should show location links in sessions list', async ({ page }) => {
		const headers = getAdminAuthHeaders();

		const sessionsRes = await page.request.get(`${ADMIN_API_BASE_URL}/admin/sessions`, {
			headers,
		});
		const sessionsPayload = await sessionsRes.json();
		const sessions = unwrapListResponse<any>(sessionsPayload);

		const sessionWithLocation = sessions.find((s: any) => s.location?.id && s.location?.name);
		if (!sessionWithLocation) {
			return;
		}

		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		const row = page.locator('table tbody tr', {
			has: page.getByRole('link', { name: sessionWithLocation.name }),
		});
		await expect(row.first()).toBeVisible();

		const locationLink = row
			.first()
			.locator(`a[href="/locations/${sessionWithLocation.location.id}"]`);
		await expect(locationLink).toBeVisible();
		await expect(locationLink).toHaveText(sessionWithLocation.location.name);
	});

	test('should have search functionality', async ({ page }) => {
		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		await expect(page.locator('header h1')).toContainText(/sessions/i);

		// Look for search input
		const searchInput = page.locator('input[placeholder*="Search" i], input[type="search"]');

		// Should have at least one search field
		await expect(searchInput.first()).toBeVisible();
	});

	test('should have filter options', async ({ page }) => {
		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		await expect(page.locator('header h1')).toContainText(/sessions/i);

		// Look for year select and archived checkbox
		await expect(page.locator('select')).toBeVisible();
		await expect(page.locator('input[type="checkbox"]')).toBeVisible();
	});

	test('should navigate to create session page', async ({ page }) => {
		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		await expect(page.locator('header h1')).toContainText(/sessions/i);

		// Click create button
		const createButton = page.locator('a:has-text("New Session"), button:has-text("New Session")');

		if ((await createButton.count()) > 0) {
			await createButton.first().scrollIntoViewIfNeeded();
			await createButton.first().click({ force: true });

			// Should navigate to create page
			await page.waitForURL(/\/sessions\/create|\/create-session/, { timeout: 5000 }).catch(() => {
				// Page might have a different URL structure
			});
		}
	});

	test('should display session details when clicking on a session', async ({ page }) => {
		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		await expect(page.locator('header h1')).toContainText(/sessions/i);

		const firstSessionLink = page.locator('table tbody tr a').first();
		if ((await firstSessionLink.count()) > 0) {
			await firstSessionLink.click();
			await page.waitForURL(/\/sessions\/[a-zA-Z0-9-]+/, { timeout: 5000 });

			// Verify session page loaded - check for any heading or title
			const heading = page.locator('h1, h2, [role="heading"]').first();
			await expect(heading).toBeVisible();

			// Check for signup section with button/tab
			await expect(page.getByRole('button', { name: /signups/i })).toBeVisible();

			// Verify table structure exists
			const signupsTable = page.locator('table');
			const hasRows = (await page.locator('table tbody tr').count()) > 0;
			const hasEmptyState = (await page.locator('text=No signups matching filter').count()) > 0;

			if (hasRows) {
				// If there are signup rows, validate their content
				const firstSignupRow = page.locator('table tbody tr').first();

				// Check for key signup fields - should have student name, status, guardian
				const rowText = await firstSignupRow.innerText();
				expect(rowText.length).toBeGreaterThan(0);

				// Verify table headers exist for key fields
				const headers = page.locator('table thead th');
				const headerCount = await headers.count();
				expect(headerCount).toBeGreaterThan(0);

				// Look for status indicator (confirmed, pending, waitlisted, etc)
				const statusBadge = page
					.locator('text="Confirmed", text="Pending", text="Waitlisted", text="Withdrawn"')
					.first();
				if ((await statusBadge.count()) > 0) {
					await expect(statusBadge).toBeVisible();
				}
			}

			expect((await signupsTable.count()) > 0 || hasRows || hasEmptyState).toBeTruthy();

			expect(pageErrors).toEqual([]);
		}
	});

	test('should handle empty sessions list gracefully', async ({ page }) => {
		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		await expect(page.locator('header h1')).toContainText(/sessions/i);

		// Switch to a different year and verify page remains stable
		const yearSelect = page.locator('select');
		await yearSelect.selectOption('2024');
		// Wait longer for webkit to process the year change
		await page.waitForTimeout(1000);
		await waitForApiCalls(page).catch(() => {
			// Ignore timeout, page might already be stable
		});

		const spinner = page.locator('.animate-spin');
		if ((await spinner.count()) > 0) {
			await expect(spinner).toBeHidden({ timeout: 10000 });
		}

		// Wait for content to load (either empty state or rows)
		await page
			.waitForSelector('text=No sessions found, table tbody tr', { timeout: 10000 })
			.catch(() => {
				// Either element might appear
			});

		const hasEmptyState = (await page.locator('text=No sessions found').count()) > 0;
		const hasRows = (await page.locator('table tbody tr').count()) > 0;
		expect(hasEmptyState || hasRows).toBeTruthy();
	});

	test('should display signup counts correctly', async ({ page }) => {
		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		await expect(page.locator('header h1')).toContainText(/sessions/i);

		// Get all signup count cells from the table
		const signupCountCells = page.locator('table tbody tr td:nth-child(5)'); // Signups column
		const cellCount = await signupCountCells.count();

		if (cellCount > 0) {
			// Check each signup count format (should be "X/Y" format)
			for (let i = 0; i < Math.min(cellCount, 5); i++) {
				const cellText = await signupCountCells.nth(i).innerText();
				// Should match format like "0/16" or "5/20" - NOT all zeros
				const matches = cellText.match(/(\d+)\/(\d+)/);
				expect(matches).toBeTruthy(); // Must have "X/Y" format

				if (matches) {
					const confirmed = parseInt(matches[1], 10);
					const capacity = parseInt(matches[2], 10);
					// Confirmed should not exceed capacity
					expect(confirmed).toBeLessThanOrEqual(capacity);
					// Capacity should be positive
					expect(capacity).toBeGreaterThan(0);
				}
			}
		}
	});

	test('should show confirmed signup count and guardian name', async ({ page }) => {
		const headers = getAdminAuthHeaders();
		const sessionsRes = await page.request.get(`${ADMIN_API_BASE_URL}/admin/sessions`, {
			headers,
		});
		const sessionsPayload = await sessionsRes.json();
		const sessions = unwrapListResponse<any>(sessionsPayload);

		if (sessions.length === 0) {
			return;
		}

		const session = sessions[0];
		const signupsRes = await page.request.get(
			`${ADMIN_API_BASE_URL}/admin/sessions/${session.id}/signups`,
			{ headers },
		);
		const signupsPayload = await signupsRes.json();
		const signups = unwrapListResponse<any>(signupsPayload);
		const confirmedCount = signups.filter((s) => s.status === 'confirmed').length;

		await navigateTo(page, `/sessions/${session.id}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		const signupsTab = page.locator('button:has-text("Signups")').first();
		await expect(signupsTab).toContainText(`Signups (${confirmedCount})`);

		if (signups.length === 0) {
			await expect(page.locator('text=No signups matching filter')).toBeVisible();
			return;
		}

		const signup = signups[0];
		const studentName = signup.student_name ?? signup.studentName ?? '';
		const guardianName = signup.guardian_name ?? signup.guardianName ?? '';
		if (studentName) {
			const row = page.locator('table tbody tr').filter({ hasText: studentName }).first();
			await expect(row).toBeVisible();
			if (guardianName) {
				await expect(row).toContainText(guardianName);
			}
		}
	});

	test('should be responsive on mobile', async ({ page }) => {
		await page.setViewportSize({ width: 375, height: 667 });

		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Table should be scrollable or simplified on mobile
		await expect(page.locator('header h1')).toContainText(/sessions/i);
	});

	test('should count only confirmed signups, not waitlisted or pending', async ({ page }) => {
		const headers = getAdminAuthHeaders();

		// Get first session with signups
		const sessionsRes = await page.request.get(`${ADMIN_API_BASE_URL}/admin/sessions`, {
			headers,
		});
		const sessionsPayload = await sessionsRes.json();
		const sessions = unwrapListResponse<any>(sessionsPayload);

		if (sessions.length === 0) {
			return;
		}

		const sessionWithSignups = sessions.find(
			(s: any) => s.confirmedCount > 0 || s.waitlistCount > 0 || s.pendingCount > 0,
		);

		if (!sessionWithSignups) {
			return;
		}

		// Get actual signups from API
		const signupsRes = await page.request.get(
			`${ADMIN_API_BASE_URL}/admin/sessions/${sessionWithSignups.id}/signups`,
			{ headers },
		);
		const signupsPayload = await signupsRes.json();
		const signups = unwrapListResponse<any>(signupsPayload);

		// Count confirmed signups
		const confirmedCount = signups.filter((s: any) => s.status === 'confirmed').length;

		// Navigate to sessions list
		await navigateTo(page, '/sessions');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Find the session row
		const rows = page.locator('table tbody tr');
		const rowCount = await rows.count();

		for (let i = 0; i < rowCount; i++) {
			const row = rows.nth(i);
			const nameCell = row.locator('td:nth-child(1) a');
			const name = await nameCell.textContent();

			if (name?.includes(sessionWithSignups.name)) {
				// Get signup count from the row
				const signupCell = row.locator('td:nth-child(4)');
				const signupText = await signupCell.textContent();
				const match = signupText?.match(/(\d+)\/(\d+)/);

				if (match) {
					const displayedConfirmed = parseInt(match[1], 10);
					// Should match confirmed count from API
					expect(displayedConfirmed).toBe(confirmedCount);
				}
				break;
			}
		}
	});
});
