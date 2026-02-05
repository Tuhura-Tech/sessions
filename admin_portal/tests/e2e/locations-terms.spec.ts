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

test.describe('Locations Management', () => {
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

	test('should display locations page', async ({ page }) => {
		await navigateTo(page, '/locations');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		await expect(page.locator('header h1')).toContainText(/locations/i);
	});

	test('should have create location button', async ({ page }) => {
		await navigateTo(page, '/locations');
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		await expect(page.locator('header h1')).toContainText(/locations/i);

		// Look for create/add button
		const createButton = page.locator('button:has-text("New Location"), button:has-text("Create")');

		await expect(createButton.first()).toBeVisible();
	});

	test('should display locations list', async ({ page }) => {
		await navigateTo(page, '/locations');
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		await expect(page.locator('header h1')).toContainText(/locations/i);

		// Check for table structure
		const table = page.locator('table');
		await expect(table).toBeVisible();

		// Check for table headers (should have location name, address, etc)
		const headers = page.locator('table thead th');
		const headerCount = await headers.count();
		expect(headerCount).toBeGreaterThanOrEqual(2);

		// If there are rows, validate location content
		const rows = page.locator('table tbody tr');
		const rowCount = await rows.count();

		if (rowCount > 0) {
			// Check first location row has content
			const firstRow = rows.first();
			const rowText = await firstRow.innerText();
			expect(rowText.length).toBeGreaterThan(0);

			// Verify location name exists in row
			const locationName = firstRow.locator('td').first();
			const nameText = await locationName.innerText();
			expect(nameText.trim().length).toBeGreaterThan(0);
		}
	});

	test('should show sessions for location with correct values', async ({ page }) => {
		const headers = getAdminAuthHeaders();
		const locationsRes = await page.request.get(`${ADMIN_API_BASE_URL}/admin/locations`, {
			headers,
		});
		const locationsPayload = await locationsRes.json();
		const locations = unwrapListResponse<any>(locationsPayload);

		if (locations.length === 0) {
			return;
		}

		const location = locations[0];
		const sessionsRes = await page.request.get(
			`${ADMIN_API_BASE_URL}/admin/locations/${location.id}/sessions?include_archived=true`,
			{ headers },
		);
		const sessionsPayload = await sessionsRes.json();
		const sessions = unwrapListResponse<any>(sessionsPayload);

		await navigateTo(page, `/locations/${location.id}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		await expect(page.locator('header h1')).toContainText(location.name);

		if (sessions.length === 0) {
			await expect(page.locator('text=No sessions at this location')).toBeVisible();
			return;
		}

		const rows = page.locator('table tbody tr');
		await expect(rows).toHaveCount(sessions.length);

		const session = sessions[0];
		const row = rows.filter({ hasText: session.name }).first();
		await expect(row).toBeVisible();

		const confirmed = session.confirmed_count ?? session.confirmedCount ?? 0;
		const capacity = session.capacity ?? '?';
		await expect(row).toContainText(`${confirmed}/${capacity}`);
	});

	test('should allow editing location', async ({ page }) => {
		await navigateTo(page, '/locations');
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		await expect(page.locator('header h1')).toContainText(/locations/i);

		// Look for edit button/link
		const editButton = page.locator(
			'button:has-text("Edit"), a:has-text("Edit"), button[aria-label*="edit" i]',
		);

		if ((await editButton.count()) > 0) {
			await editButton.first().scrollIntoViewIfNeeded();
			await editButton.first().click({ force: true });

			// Should show edit form
			const form = page.locator('form');
			const count = await form.count();

			if (count > 0) {
				await expect(form.first()).toBeVisible();
			}
		}
	});
});

test.describe.skip('Terms Management', () => {
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

	test('should display terms page', async ({ page }) => {
		await navigateTo(page, '/terms');
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		await expect(page.locator('header h1')).toContainText(/school terms/i);
	});

	test('should display terms list', async ({ page }) => {
		await navigateTo(page, '/terms');
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		await expect(page.locator('header h1')).toContainText(/school terms/i);

		// Check for table
		const table = page.locator('table');

		await expect(table).toBeVisible();
	});

	test('should filter terms by year', async ({ page }) => {
		await navigateTo(page, '/terms');
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		await expect(page.locator('header h1')).toContainText(/school terms/i);

		// Look for year filter
		const yearFilter = page.locator(
			'select, button:has-text("Year"), input[placeholder*="Year" i]',
		);

		await expect(yearFilter.first()).toBeVisible();
	});

	test('should allow editing term', async ({ page }) => {
		await navigateTo(page, '/terms');
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		await expect(page.locator('header h1')).toContainText(/school terms/i);

		// Look for edit button
		const editButton = page.locator('button:has-text("Edit"), a:has-text("Edit")');

		if ((await editButton.count()) > 0) {
			await editButton.first().click();

			// Should show edit form
			const input = page.locator('input[type="date"], input[type="text"]');
			await expect(input.first()).toBeVisible();
		}
	});
});
