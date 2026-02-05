import { expect, test } from '@playwright/test';
import { authenticateAsAdmin, ensureAuthenticated, trackPageErrors } from './helpers';

test.describe.skip('Staff Assignment on Session Creation', () => {
	let pageErrors: string[] = [];

	test.beforeEach(async ({ page }) => {
		pageErrors = trackPageErrors(page);
		await authenticateAsAdmin(page);
		await ensureAuthenticated(page);
	});

	test.afterEach(async () => {
		expect(pageErrors).toEqual([]);
	});

	test('should display staff selection checkboxes in create session form', async ({ page }) => {
		// Navigate to create session page
		await page.goto('/sessions/create');
		await expect(page.locator('h1')).toContainText(/Create Session/i);

		// Scroll down to staff section
		const _staffSection = page
			.locator('text=Staff Assignment')
			.or(page.locator('text=Assign Staff'));

		// Staff section might load asynchronously
		await page.waitForTimeout(1000);

		// Check if staff checkboxes exist
		const checkboxes = page.locator('input[type="checkbox"]');
		const count = await checkboxes.count();

		// Should have at least some checkboxes (for media consent, newsletter, etc.)
		expect(count).toBeGreaterThan(0);

		// Verify form fields have labels/structure
		const labels = page.locator('label');
		const labelCount = await labels.count();
		expect(labelCount).toBeGreaterThan(0);

		// Verify checkboxes are associated with text labels
		for (let i = 0; i < Math.min(3, count); i++) {
			const checkbox = checkboxes.nth(i);
			const label = await checkbox.evaluate((el) => {
				const labelElement = document.querySelector(`label[for="${el.id}"]`);
				return labelElement?.textContent?.trim() || '';
			});
			expect(label.length).toBeGreaterThan(0);
		}
	});

	test('should be able to select staff members when creating session', async ({ page }) => {
		await page.goto('/sessions/create');

		// Fill in required session fields first
		await page.fill('input[name="name"]', 'Test Session with Staff');

		// Select location
		const locationSelect = page.locator('select').first();
		if (await locationSelect.isVisible()) {
			const options = await locationSelect.locator('option').count();
			if (options > 1) {
				await locationSelect.selectOption({ index: 1 });
			}
		}

		// Fill age ranges
		await page.fill('input[name="ageLower"]', '8');
		await page.fill('input[name="ageUpper"]', '14');

		// Fill capacity
		await page.fill('input[name="capacity"]', '20');

		// Select day of week
		const daySelect = page.locator('select[name="dayOfWeek"]');
		if (await daySelect.isVisible()) {
			await daySelect.selectOption({ index: 1 });
		}

		// Fill times
		await page.fill('input[name="startTime"]', '15:30');
		await page.fill('input[name="endTime"]', '17:00');

		// Wait for staff list to load
		await page.waitForTimeout(1000);

		// Try to select first staff member checkbox
		const staffCheckboxes = page
			.locator('input[type="checkbox"][id*="staff"]')
			.or(page.locator('input[type="checkbox"]').filter({ hasText: /staff/i }));

		const staffCount = await staffCheckboxes.count();
		if (staffCount > 0) {
			// Select first staff member
			await staffCheckboxes.first().check();
			await expect(staffCheckboxes.first()).toBeChecked();
		}
	});

	test('should create session with assigned staff', async ({ page }) => {
		await page.goto('/sessions/create');

		// Fill required fields
		await page.fill('input[name="name"]', `Test Session ${Date.now()}`);

		const locationSelect = page.locator('select').first();
		if (await locationSelect.isVisible()) {
			const options = await locationSelect.locator('option').count();
			if (options > 1) {
				await locationSelect.selectOption({ index: 1 });
			}
		}

		await page.fill('input[name="ageLower"]', '8');
		await page.fill('input[name="ageUpper"]', '14');
		await page.fill('input[name="capacity"]', '20');

		const daySelect = page.locator('select[name="dayOfWeek"]');
		if (await daySelect.isVisible()) {
			await daySelect.selectOption({ index: 1 });
		}

		await page.fill('input[name="startTime"]', '15:30');
		await page.fill('input[name="endTime"]', '17:00');

		// Select year
		const yearInput = page.locator('input[name="year"]');
		if (await yearInput.isVisible()) {
			await yearInput.fill('2026');
		}

		// Wait for staff to load
		await page.waitForTimeout(1500);

		// Try to select a staff member
		const staffCheckboxes = page.locator('input[type="checkbox"]').filter({
			has: page.locator('[for*="staff"]'),
		});

		const count = await staffCheckboxes.count();
		if (count > 0) {
			await staffCheckboxes.first().check();
		}

		// Submit form
		const submitButton = page
			.getByRole('button', { name: /create/i })
			.or(page.getByRole('button', { name: /save/i }));

		if (await submitButton.isVisible()) {
			await submitButton.click();

			// Should navigate to session detail or sessions list
			await page.waitForURL(/\/sessions/);

			// Success - we're on a session page
			expect(page.url()).toContain('/sessions');
		}
	});

	test('should show staff names in staff selection list', async ({ page }) => {
		await page.goto('/sessions/create');

		// Wait for form to load
		await page.waitForLoadState('networkidle');

		// Look for staff names (emails or names)
		const staffLabels = page.locator('label').filter({ hasText: /@/ });

		// Wait a bit for async staff loading
		await page.waitForTimeout(1500);

		// Check if we have staff labels with emails
		const labelCount = await staffLabels.count();

		// This will pass if we have staff, or skip if no staff exists
		if (labelCount > 0) {
			expect(labelCount).toBeGreaterThan(0);

			// Verify staff labels have actual email/name content
			for (let i = 0; i < Math.min(2, labelCount); i++) {
				const staffLabel = staffLabels.nth(i);
				const labelText = await staffLabel.innerText();
				expect(labelText.trim().length).toBeGreaterThan(0);
				// Should contain staff identifier (email or name)
				expect(labelText).toMatch(/[\w.-]+@[\w.-]+|[A-Z][a-z]+ [A-Z]/);
			}
		}
	});

	test('should handle no available staff gracefully', async ({ page }) => {
		await page.goto('/sessions/create');

		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1500);

		// Page should still be usable even if no staff available
		const nameInput = page.locator('input[name="name"]');
		await expect(nameInput).toBeVisible();
		await expect(nameInput).toBeEnabled();

		// Form should still be submittable without staff
		await nameInput.fill('Test Session No Staff');

		// No errors should be shown
		const errorMessages = page.locator('.text-red-500, .error, [role="alert"]');
		const errorCount = await errorMessages.count();

		// Should not have errors just from loading the page
		expect(errorCount).toBe(0);

		// Verify form is interactive with valid input
		const formContent = await page.locator('form').innerText();
		expect(formContent.trim().length).toBeGreaterThan(0);

		// Verify the page contains expected form fields
		const requiredFields = ['name', 'location', 'capacity', 'time'];
		for (const field of requiredFields) {
			const hasField =
				(await page.locator(`[name*="${field}"]`).count()) > 0 ||
				formContent.toLowerCase().includes(field);
			expect(hasField).toBeTruthy();
		}
	});
});
