import { expect, type Page, test } from '@playwright/test';
import {
	ADMIN_API_BASE_URL,
	authenticateAsAdmin,
	createAdminSessionToken,
	ensureAuthenticated,
	navigateTo,
	trackPageErrors,
	waitForApiCalls,
	waitForAuthReady,
} from './helpers';

async function getFirstOccurrenceId(page: Page): Promise<string | null> {
	const token = createAdminSessionToken();
	const sessionsResponse = await page.request.get(
		`${ADMIN_API_BASE_URL}/admin/sessions?year=${new Date().getFullYear()}`,
		{ headers: { cookie: `admin_session=${token}` } },
	);

	if (!sessionsResponse.ok()) return null;
	const sessionsData = await sessionsResponse.json();
	const sessions = Array.isArray(sessionsData) ? sessionsData : sessionsData?.items || [];
	if (!Array.isArray(sessions) || sessions.length === 0) return null;

	let targetSessionId = sessions[0].id;
	for (const sessionItem of sessions) {
		const signupsResponse = await page.request.get(
			`${ADMIN_API_BASE_URL}/admin/sessions/${sessionItem.id}/signups`,
			{ headers: { cookie: `admin_session=${token}` } },
		);

		if (signupsResponse.ok()) {
			const signupsData = await signupsResponse.json();
			const signups = Array.isArray(signupsData) ? signupsData : signupsData?.items || [];
			if (Array.isArray(signups) && signups.length > 0) {
				targetSessionId = sessionItem.id;
				break;
			}
		}
	}

	const occurrencesResponse = await page.request.get(
		`${ADMIN_API_BASE_URL}/admin/sessions/${targetSessionId}/occurrences`,
		{ headers: { cookie: `admin_session=${token}` } },
	);

	if (!occurrencesResponse.ok()) return null;
	const occurrencesData = await occurrencesResponse.json();
	const occurrences = Array.isArray(occurrencesData)
		? occurrencesData
		: occurrencesData?.items || [];
	if (!Array.isArray(occurrences) || occurrences.length === 0) return null;

	return occurrences[0].id || null;
}

test.describe('Attendance Tracking', () => {
	let pageErrors: string[] = [];

	test.beforeEach(async ({ page }) => {
		pageErrors = trackPageErrors(page);
		await authenticateAsAdmin(page);
		await ensureAuthenticated(page);
	});

	test.afterEach(async () => {
		expect(pageErrors).toEqual([]);
	});

	test('should display attendance roll page', async ({ page }) => {
		const occurrenceId = await getFirstOccurrenceId(page);
		if (!occurrenceId) {
			test.skip(true, 'No occurrences available for attendance roll');
		}

		await navigateTo(page, `/attendance/${occurrenceId}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		const spinner = page.locator('.animate-spin');
		if ((await spinner.count()) > 0) {
			await expect(spinner).toBeHidden();
		}

		// Check page title
		const title = page.locator('h1, h2');
		await expect(title.first()).toBeVisible();

		// Validate attendance roll has proper structure
		const table = page.locator('table');
		if ((await table.count()) > 0) {
			// Check for attendance table headers
			const headers = table.locator('thead th');
			const headerCount = await headers.count();
			expect(headerCount).toBeGreaterThan(0);

			const rows = table.locator('tbody tr');
			if ((await rows.count()) > 0) {
				// First row should have student name and status fields
				const firstRow = rows.first();
				const cells = firstRow.locator('td');
				const cellCount = await cells.count();
				expect(cellCount).toBeGreaterThan(0);

				// Student name should be in first cell
				const nameCell = cells.first();
				const nameText = await nameCell.innerText();
				expect(nameText.trim().length).toBeGreaterThan(0);
			}
		}
	});

	test('should have attendance marking options', async ({ page }) => {
		const occurrenceId = await getFirstOccurrenceId(page);
		if (!occurrenceId) {
			test.skip(true, 'No occurrences available for attendance roll');
		}

		await navigateTo(page, `/attendance/${occurrenceId}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		const spinner = page.locator('.animate-spin');
		if ((await spinner.count()) > 0) {
			await expect(spinner).toBeHidden();
		}

		const notFound = page.locator('text=Occurrence Not Found');
		if ((await notFound.count()) > 0) {
			test.skip(true, 'Occurrence data unavailable');
			return;
		}

		const rowCount = await page.locator('table tbody tr').count();
		if (rowCount === 0) {
			await expect(page.locator('text=No students enrolled in this session')).toBeVisible();
		} else {
			// Verify attendance status buttons exist
			await expect(page.locator('button:has-text("Present")').first()).toBeVisible();
			await expect(page.locator('button:has-text("Absent")').first()).toBeVisible();

			// Verify first row has student name
			const firstRow = page.locator('table tbody tr').first();
			const nameCell = firstRow.locator('td').first();
			const nameText = await nameCell.innerText();
			expect(nameText.trim().length).toBeGreaterThan(0);
		}
	});

	test('should allow selecting attendance status', async ({ page }) => {
		const occurrenceId = await getFirstOccurrenceId(page);
		if (!occurrenceId) {
			test.skip(true, 'No occurrences available for attendance roll');
		}

		await navigateTo(page, `/attendance/${occurrenceId}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		const spinner = page.locator('.animate-spin');
		if ((await spinner.count()) > 0) {
			await expect(spinner).toBeHidden();
		}

		// Find first radio/checkbox for attendance
		const radioButtons = page.locator('input[type="radio"], input[type="checkbox"]');

		if ((await radioButtons.count()) > 0) {
			await radioButtons.first().click();

			// Verify it's checked
			const isChecked = await radioButtons.first().isChecked();
			expect(isChecked).toBeTruthy();
		}
	});

	test('should have save/submit button', async ({ page }) => {
		const occurrenceId = await getFirstOccurrenceId(page);
		if (!occurrenceId) {
			test.skip(true, 'No occurrences available for attendance roll');
		}

		await navigateTo(page, `/attendance/${occurrenceId}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		const spinner = page.locator('.animate-spin');
		if ((await spinner.count()) > 0) {
			await expect(spinner).toBeHidden();
		}

		const notFound = page.locator('text=Occurrence Not Found');
		if ((await notFound.count()) > 0) {
			test.skip(true, 'Occurrence data unavailable');
			return;
		}

		// Look for save/submit button
		const saveButton = page.locator(
			'button:has-text("Save"), button:has-text("Submit"), button:has-text("Mark")',
		);

		// Save button appears only when changes are made
		const rowCount = await page.locator('table tbody tr').count();
		if (rowCount === 0) {
			// Skip test if no students - we can't test the save button
			test.skip(true, 'No students enrolled to test attendance marking');
		} else {
			const presentButton = page.locator('button:has-text("Present")').first();
			await presentButton.scrollIntoViewIfNeeded();
			await presentButton.click({ force: true });
			await expect(saveButton.first()).toBeVisible();
		}
	});

	test('should handle form submission', async ({ page }) => {
		const occurrenceId = await getFirstOccurrenceId(page);
		if (!occurrenceId) {
			test.skip(true, 'No occurrences available for attendance roll');
		}

		await navigateTo(page, `/attendance/${occurrenceId}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		const spinner = page.locator('.animate-spin');
		if ((await spinner.count()) > 0) {
			await expect(spinner).toBeHidden();
		}

		const rowCount = await page.locator('table tbody tr').count();
		if (rowCount === 0) {
			test.skip(true, 'No students enrolled to test attendance marking');
		}

		// Mark attendance for first student
		const presentButton = page.locator('button:has-text("Present")').first();
		await presentButton.scrollIntoViewIfNeeded();
		await presentButton.click({ force: true });

		// Verify save button appears after making changes
		const saveButton = page.locator('button:has-text("Save"), button:has-text("Submit")');
		await expect(saveButton.first()).toBeVisible();

		// Click save and wait for API call
		await saveButton.first().click();
		await page.waitForLoadState('networkidle');

		// Verify success (alert or success message)
		page.once('dialog', async (dialog) => {
			expect(dialog.message()).toContain('success');
			await dialog.accept();
		});
	});

	test('should mark attendance for multiple students', async ({ page }) => {
		const occurrenceId = await getFirstOccurrenceId(page);
		if (!occurrenceId) {
			test.skip(true, 'No occurrences available for attendance roll');
		}

		await navigateTo(page, `/attendance/${occurrenceId}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);
		const spinner = page.locator('.animate-spin');
		if ((await spinner.count()) > 0) {
			await expect(spinner).toBeHidden();
		}

		const rowCount = await page.locator('table tbody tr').count();
		if (rowCount < 2) {
			test.skip(true, 'Need at least 2 students to test multiple attendance marking');
		}

		// Mark attendance for first two students with different statuses
		const presentButtons = page.locator('button:has-text("Present")');
		const absentButtons = page.locator('button:has-text("Absent")');

		// Mark first student as present
		await presentButtons.first().scrollIntoViewIfNeeded();
		await presentButtons.first().click({ force: true });

		// Mark second student as absent
		await absentButtons.nth(1).scrollIntoViewIfNeeded();
		await absentButtons.nth(1).click({ force: true });

		// Verify save button appears
		const saveButton = page.locator('button:has-text("Save"), button:has-text("Submit")');
		await expect(saveButton.first()).toBeVisible();

		// Setup dialog handler before clicking save
		page.once('dialog', async (dialog) => {
			expect(dialog.message()).toContain('success');
			await dialog.accept();
		});

		// Click save and wait for API call
		await saveButton.first().click();
		await page.waitForTimeout(1000); // Wait for API call to complete
	});

	test('should export attendance data', async ({ page }) => {
		const occurrenceId = await getFirstOccurrenceId(page);
		if (!occurrenceId) {
			test.skip(true, 'No occurrences available for attendance roll');
		}

		await navigateTo(page, `/attendance/${occurrenceId}`);
		await waitForAuthReady(page);
		await waitForApiCalls(page);

		// Look for export button
		const exportButton = page.locator('button:has-text("Export"), a:has-text("Download")');

		if ((await exportButton.count()) > 0) {
			// Start waiting for download before click
			const downloadPromise = page.waitForEvent('download');

			await exportButton.first().click();

			// Wait for download to start
			const download = await downloadPromise.catch(() => null);

			// If download was triggered, it should be a valid file
			if (download) {
				expect(download.suggestedFilename()).toContain('csv');
			}
		}
	});
});
