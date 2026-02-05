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

test.describe('Session Detail - Signup Counts', () => {
	let pageErrors: string[] = [];

	test.beforeEach(async ({ page }) => {
		pageErrors = trackPageErrors(page);
		await authenticateAsAdmin(page);
		await ensureAuthenticated(page);
	});

	test.afterEach(async () => {
		expect(pageErrors).toEqual([]);
	});

	test('should display only confirmed signups in tab count', async ({ page }) => {
		const headers = getAdminAuthHeaders();

		// Get a session with signups
		const sessionsRes = await page.request.get(`${ADMIN_API_BASE_URL}/admin/sessions`, {
			headers,
		});
		const sessionsPayload = await sessionsRes.json();
		const sessions = unwrapListResponse<any>(sessionsPayload);

		const sessionWithSignups = sessions.find(
			(s: any) => s.confirmedCount > 0 || s.waitlistCount > 0 || s.pendingCount > 0,
		);

		if (!sessionWithSignups) {
			return;
		}

		// Get signups for this session
		const signupsRes = await page.request.get(
			`${ADMIN_API_BASE_URL}/admin/sessions/${sessionWithSignups.id}/signups`,
			{ headers },
		);
		const signupsPayload = await signupsRes.json();
		const signups = unwrapListResponse<any>(signupsPayload);

		// Count confirmed, waitlisted, and pending
		const confirmedCount = signups.filter((s: any) => s.status === 'confirmed').length;
		const totalSignups = signups.length;

		// Navigate to session detail
		await navigateTo(page, `/sessions/${sessionWithSignups.id}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Find the Signups tab
		const signupsTab = page.getByRole('button', { name: /Signups \(/i });
		await expect(signupsTab).toBeVisible();

		// Get the tab text
		const tabText = await signupsTab.textContent();
		const match = tabText?.match(/Signups \((\d+)\)/);

		expect(match).toBeTruthy();

		if (match) {
			const displayedCount = parseInt(match[1], 10);

			// The tab should show ONLY confirmed signups
			expect(displayedCount).toBe(confirmedCount);

			// Should NOT be the total signup count if there are waitlisted/pending
			if (totalSignups > confirmedCount) {
				expect(displayedCount).not.toBe(totalSignups);
			}
		}
	});

	test('should display capacity correctly in session detail', async ({ page }) => {
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

		// Navigate to session detail
		await navigateTo(page, `/sessions/${session.id}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Find capacity section
		const capacityText = page.locator('text=/Capacity/i').locator('..');
		await expect(capacityText).toBeVisible();

		// Should show "X / capacity" format
		const text = await capacityText.textContent();
		expect(text).toMatch(/\d+\s*\/\s*(\d+|Unlimited)/i);
	});

	test('should display location link in session detail', async ({ page }) => {
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

		await navigateTo(page, `/sessions/${sessionWithLocation.id}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		const locationLink = page.locator(`a[href="/locations/${sessionWithLocation.location.id}"]`);
		await expect(locationLink).toBeVisible();
		await expect(locationLink).toHaveText(sessionWithLocation.location.name);
	});

	test('should show correct signup statuses in table', async ({ page }) => {
		const headers = getAdminAuthHeaders();

		const sessionsRes = await page.request.get(`${ADMIN_API_BASE_URL}/admin/sessions`, {
			headers,
		});
		const sessionsPayload = await sessionsRes.json();
		const sessions = unwrapListResponse<any>(sessionsPayload);

		const sessionWithSignups = sessions.find((s: any) => s.confirmedCount > 0);

		if (!sessionWithSignups) {
			return;
		}

		await navigateTo(page, `/sessions/${sessionWithSignups.id}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Click Signups tab
		const signupsTab = page.getByRole('button', { name: /Signups/i });
		await signupsTab.click();

		// Wait for signups table
		await page.waitForSelector('table tbody tr', { timeout: 5000 });

		// Check for status badges
		const statusBadges = page.locator('table tbody tr td span.rounded-full');
		const count = await statusBadges.count();

		if (count > 0) {
			for (let i = 0; i < Math.min(count, 5); i++) {
				const badge = statusBadges.nth(i);
				const text = await badge.textContent();

				// Status should be one of: confirmed, waitlisted, pending, withdrawn
				expect(text?.toLowerCase()).toMatch(/confirmed|waitlisted|pending|withdrawn/);
			}
		}
	});

	test('should display student ages correctly', async ({ page }) => {
		const headers = getAdminAuthHeaders();

		const sessionsRes = await page.request.get(`${ADMIN_API_BASE_URL}/admin/sessions`, {
			headers,
		});
		const sessionsPayload = await sessionsRes.json();
		const sessions = unwrapListResponse<any>(sessionsPayload);

		const sessionWithSignups = sessions.find((s: any) => s.confirmedCount > 0);

		if (!sessionWithSignups) {
			return;
		}

		await navigateTo(page, `/sessions/${sessionWithSignups.id}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Click Signups tab
		const signupsTab = page.getByRole('button', { name: /Signups/i });
		await signupsTab.click();

		// Wait for table
		await page.waitForSelector('table tbody tr', { timeout: 5000 });

		// Age column should show valid ages or "—"
		const ageColumns = page.locator('table tbody tr td:nth-child(4)');
		const count = await ageColumns.count();

		if (count > 0) {
			for (let i = 0; i < Math.min(count, 5); i++) {
				const ageText = await ageColumns.nth(i).textContent();

				// Should be either a number or "—"
				expect(ageText).toMatch(/^\d+$|^—$/);

				// If it's a number, should be reasonable (0-120)
				if (ageText && /^\d+$/.test(ageText)) {
					const age = parseInt(ageText, 10);
					expect(age).toBeGreaterThanOrEqual(0);
					expect(age).toBeLessThan(120);
				}
			}
		}
	});

	test('should show guardian names correctly', async ({ page }) => {
		const headers = getAdminAuthHeaders();

		const sessionsRes = await page.request.get(`${ADMIN_API_BASE_URL}/admin/sessions`, {
			headers,
		});
		const sessionsPayload = await sessionsRes.json();
		const sessions = unwrapListResponse<any>(sessionsPayload);

		const sessionWithSignups = sessions.find((s: any) => s.confirmedCount > 0);

		if (!sessionWithSignups) {
			return;
		}

		// Get signups
		const signupsRes = await page.request.get(
			`${ADMIN_API_BASE_URL}/admin/sessions/${sessionWithSignups.id}/signups`,
			{ headers },
		);
		const signupsPayload = await signupsRes.json();
		const signups = unwrapListResponse<any>(signupsPayload);

		if (signups.length === 0) {
			return;
		}

		await navigateTo(page, `/sessions/${sessionWithSignups.id}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Click Signups tab
		const signupsTab = page.getByRole('button', { name: /Signups/i });
		await signupsTab.click();

		// Wait for table
		await page.waitForSelector('table tbody tr', { timeout: 5000 });

		// Guardian column
		const guardianColumns = page.locator('table tbody tr td:nth-child(5)');
		const count = await guardianColumns.count();

		if (count > 0) {
			const firstGuardianText = await guardianColumns.first().textContent();

			// Should have guardian name
			expect(firstGuardianText).toBeTruthy();
			expect(firstGuardianText?.trim().length).toBeGreaterThan(0);

			// Match with API data
			const firstSignup = signups[0];
			if (firstSignup.guardianName) {
				expect(firstGuardianText).toContain(firstSignup.guardianName);
			}
		}
	});
});
