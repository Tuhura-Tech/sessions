import { expect, test } from '@playwright/test';
import {
	ADMIN_API_BASE_URL,
	authenticateAsAdmin,
	createAdminSessionToken,
	ensureAuthenticated,
	navigateTo,
	trackPageErrors,
	waitForApiCalls,
} from './helpers';

test.describe('API Integration', () => {
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

	test('should return an authenticated session', async ({ page }) => {
		const token = createAdminSessionToken();
		const response = await page.request.get(`${ADMIN_API_BASE_URL}/admin/auth/me`, {
			headers: {
				cookie: `admin_session=${token}`,
			},
		});

		expect(response.ok()).toBeTruthy();
		const data = await response.json();
		expect(data.hasSession).toBe(true);
		expect(data.email).toBeDefined();
		expect(typeof data.email).toBe('string');
	});

	test('should load sessions list', async ({ page }) => {
		await navigateTo(page, '/sessions');
		await waitForApiCalls(page);

		await expect(page.locator('header h1')).toContainText(/sessions/i);
		const hasRows = (await page.locator('table tbody tr').count()) > 0;
		const hasEmptyState = (await page.locator('text=No sessions found').count()) > 0;
		expect(hasRows || hasEmptyState).toBeTruthy();

		if (hasRows) {
			// Validate session row structure
			const firstRow = page.locator('table tbody tr').first();
			const cells = firstRow.locator('td');
			const cellCount = await cells.count();
			// Should have at least session name and one other field
			expect(cellCount).toBeGreaterThanOrEqual(2);

			// First cell should have session name or link
			const sessionNameCell = cells.first();
			const nameText = await sessionNameCell.innerText();
			expect(nameText.trim().length).toBeGreaterThan(0);
		}
	});

	test('should load locations list', async ({ page }) => {
		await navigateTo(page, '/locations');
		await waitForApiCalls(page);

		await expect(page.locator('header h1')).toContainText(/locations/i);
		const hasRows = (await page.locator('table tbody tr').count()) > 0;
		const hasEmptyState = (await page.locator('text=No locations yet').count()) > 0;
		expect(hasRows || hasEmptyState).toBeTruthy();

		if (hasRows) {
			// Validate location row structure with name and address info
			const firstRow = page.locator('table tbody tr').first();
			const cells = firstRow.locator('td');
			const cellCount = await cells.count();
			expect(cellCount).toBeGreaterThanOrEqual(2); // Name and at least one more column

			// Location should have name
			const locationNameCell = cells.first();
			const nameText = await locationNameCell.innerText();
			expect(nameText.trim().length).toBeGreaterThan(0);
		}
	});

	test('should load blocks list', async ({ page }) => {
		await navigateTo(page, '/blocks');
		await waitForApiCalls(page);

		// Check for page heading - might be in different locations
		const heading1 = page.locator('h1').filter({ hasText: 'blocks' });
		const heading2 = page.locator('h2').filter({ hasText: 'blocks' });
		const headingExists =
			(await heading1.count()) > 0 ||
			(await heading2.count()) > 0 ||
			(await page.locator('body').innerText()).toLowerCase().includes('block');
		expect(headingExists).toBeTruthy();

		const hasRows = (await page.locator('table tbody tr').count()) > 0;
		const hasEmptyState = (await page.locator('text=/No blocks found/i').count()) > 0;
		expect(hasRows || hasEmptyState).toBeTruthy();

		if (hasRows) {
			// Validate block row structure with name, year, dates
			const firstRow = page.locator('table tbody tr').first();
			const cells = firstRow.locator('td');
			const cellCount = await cells.count();
			expect(cellCount).toBeGreaterThanOrEqual(3); // Name, year, dates

			// Block should have name
			const blockNameCell = cells.first();
			const nameText = await blockNameCell.innerText();
			expect(nameText.trim().length).toBeGreaterThan(0);
		}
	});

	test('should load students list with valid date format', async ({ page }) => {
		await navigateTo(page, '/students');
		await waitForApiCalls(page);

		const hasRows = (await page.locator('table tbody tr').count()) > 0;
		const hasEmptyState = (await page.locator('text=/No students found/i').count()) > 0;
		expect(hasRows || hasEmptyState).toBeTruthy();

		if (hasRows) {
			// Validate student row structure
			const firstRow = page.locator('table tbody tr').first();
			const cells = firstRow.locator('td');
			const cellCount = await cells.count();
			expect(cellCount).toBeGreaterThanOrEqual(2); // Name and at least one more column

			// Student should have name
			const studentNameCell = cells.first();
			const nameText = await studentNameCell.innerText();
			expect(nameText.trim().length).toBeGreaterThan(0);

			// Click first student to view details
			const studentLink = firstRow.locator('a').first();
			if ((await studentLink.count()) > 0) {
				await studentLink.click();
				await page.waitForURL(/\/students\/[a-zA-Z0-9-]+/, { timeout: 5000 });

				// Check for date of birth field with proper format
				const dobLabel = page.locator('dt:has-text("Date of birth")');
				const dobValue = dobLabel.locator('..').locator('dd');

				if ((await dobLabel.count()) > 0) {
					const dobText = await dobValue.innerText();
					// Should be formatted date, not raw timestamp or undefined
					// Common formats: "MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD", or "Month Day, Year"
					expect(dobText.trim().length).toBeGreaterThan(0);
					expect(dobText).not.toMatch(/\d{13}|undefined|null/); // Not a timestamp or null

					// Check that it looks like a date (contains numbers and separators or month names)
					const hasDatePattern =
						/\d{1,2}[-\/\.]\d{1,2}[-\/\.]\d{2,4}|[A-Za-z]+ \d{1,2}, \d{4}/.test(dobText);
					expect(hasDatePattern).toBeTruthy();
				}

				// Check for age field (should be a number)
				const ageLabel = page.locator('dt:has-text("Age")');
				const ageValue = ageLabel.locator('..').locator('dd');

				if ((await ageLabel.count()) > 0) {
					const ageText = await ageValue.innerText();
					// Age should be a number followed by "years"
					const ageMatches = ageText.match(/(\d+)\s*years?/i);
					expect(ageMatches).toBeTruthy(); // Should match "X years" format
					if (ageMatches) {
						const age = parseInt(ageMatches[1], 10);
						expect(age).toBeGreaterThanOrEqual(0);
						expect(age).toBeLessThan(150); // Reasonable age limit
					}
				}

				// Check for caregiver link
				const caregiverLabel = page.locator('dt:has-text("Caregiver")');
				if ((await caregiverLabel.count()) > 0) {
					const caregiverSection = caregiverLabel.locator('..');
					const caregiverLink = caregiverSection.locator('a');
					const noAssignment = caregiverSection.locator('span:has-text("No caregiver assigned")');

					// Should have either a link or the "no assignment" message
					const hasCaregiverLink = (await caregiverLink.count()) > 0;
					const hasNoAssignment = (await noAssignment.count()) > 0;
					expect(hasCaregiverLink || hasNoAssignment).toBeTruthy();
				}
			}
		}
	});
});
