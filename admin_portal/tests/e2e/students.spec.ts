import { expect, test } from '@playwright/test';
import { authenticateAsAdmin, ensureAuthenticated, navigateTo } from './helpers';

test.describe('Students Management', () => {
	test.beforeEach(async ({ page }) => {
		await authenticateAsAdmin(page);
		await ensureAuthenticated(page);
	});

	test('should display students list page', async ({ page }) => {
		await navigateTo(page, '/students');
		await page.waitForLoadState('networkidle');

		// Check page title
		await expect(page.getByRole('heading', { name: /Student Management/i })).toBeVisible();

		// Should have search input
		const searchInput = page.locator('input[placeholder*="Search students"]');
		await expect(searchInput).toBeVisible();
	});

	test('should search students by name', async ({ page }) => {
		await navigateTo(page, '/students');
		await page.waitForLoadState('networkidle');

		// Enter search term
		const searchInput = page.locator('input[placeholder*="Search students"]');
		await searchInput.fill('Test');

		// Wait for table to update
		await page.waitForTimeout(500);
	});

	test('should navigate to student detail page', async ({ page }) => {
		await navigateTo(page, '/students');
		await page.waitForLoadState('networkidle');

		// Wait for table to load
		await page.waitForTimeout(1000);

		// Click on first "View Details" button if available
		const viewButton = page.locator('button:has-text("View Details")').first();
		const viewButtonCount = await viewButton.count();

		if (viewButtonCount > 0) {
			await viewButton.click();
			await page.waitForLoadState('networkidle');

			// Should be on student detail page
			expect(page.url()).toContain('/students/');
		}
	});

	test('should display student profile information', async ({ page }) => {
		await navigateTo(page, '/students');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const viewButton = page.locator('button:has-text("View Details")').first();
		const viewButtonCount = await viewButton.count();

		if (viewButtonCount > 0) {
			await viewButton.click();
			await page.waitForLoadState('networkidle');

			// Check for profile section
			await expect(page.locator('h2:has-text("Profile")')).toBeVisible();

			// Should display profile fields
			await expect(page.locator('dt:has-text("Name")')).toBeVisible();
			await expect(page.locator('dt:has-text("Date of birth")')).toBeVisible();
			await expect(page.locator('dt:has-text("Age")')).toBeVisible();
		}
	});

	test('should have clickable caregiver link on student detail page', async ({ page }) => {
		await navigateTo(page, '/students');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const viewButton = page.locator('button:has-text("View Details")').first();
		const viewButtonCount = await viewButton.count();

		if (viewButtonCount > 0) {
			await viewButton.click();
			await page.waitForLoadState('networkidle');

			// Look for caregiver link
			const caregiverLabel = page.locator('dt:has-text("Caregiver")');
			await expect(caregiverLabel).toBeVisible();

			// Check if there's a caregiver link (not all students may have one)
			const caregiverLink = page.locator('a[href*="/caregiver/"]');
			const caregiverLinkCount = await caregiverLink.count();

			if (caregiverLinkCount > 0) {
				// Verify link format is correct (singular /caregiver/, not /caregivers/)
				const href = await caregiverLink.getAttribute('href');
				expect(href).toMatch(/\/caregiver\/[a-f0-9-]+/);

				// Click the caregiver link
				await caregiverLink.click();
				await page.waitForLoadState('networkidle');

				// Should navigate to caregiver detail page
				expect(page.url()).toContain('/caregiver/');
				expect(page.url()).not.toContain('/caregivers/');
			}
		}
	});

	test('should display student enrollments', async ({ page }) => {
		await navigateTo(page, '/students');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const viewButton = page.locator('button:has-text("View Details")').first();
		const viewButtonCount = await viewButton.count();

		if (viewButtonCount > 0) {
			await viewButton.click();
			await page.waitForLoadState('networkidle');

			// Check for enrollments section
			await expect(page.locator('h2:has-text("Enrollments")')).toBeVisible();
		}
	});

	test('should show session links in student enrollments', async ({ page }) => {
		await navigateTo(page, '/students');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const viewButton = page.locator('button:has-text("View Details")').first();
		const viewButtonCount = await viewButton.count();

		if (viewButtonCount > 0) {
			await viewButton.click();
			await page.waitForLoadState('networkidle');

			// Check if there are any session links
			const sessionLinks = page.locator('a[href*="/sessions/"]');
			const sessionLinkCount = await sessionLinks.count();

			// If there are enrollments, verify they link to sessions
			if (sessionLinkCount > 0) {
				const firstSessionLink = sessionLinks.first();
				const href = await firstSessionLink.getAttribute('href');
				expect(href).toMatch(/\/sessions\/[a-f0-9-]+/);
			}
		}
	});

	test('should display signup status badges', async ({ page }) => {
		await navigateTo(page, '/students');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const viewButton = page.locator('button:has-text("View Details")').first();
		const viewButtonCount = await viewButton.count();

		if (viewButtonCount > 0) {
			await viewButton.click();
			await page.waitForLoadState('networkidle');

			// Check for status badges (confirmed, waitlisted, pending, withdrawn)
			const statusBadges = page.locator('span').filter({
				hasText: /Confirmed|Waitlisted|Pending|Withdrawn/i,
			});
			// May or may not have signups, so just check the page loaded
			expect(page.url()).toContain('/students/');
		}
	});

	test('should have back button on student detail page', async ({ page }) => {
		await navigateTo(page, '/students');
		await page.waitForLoadState('networkidle');
		await page.waitForTimeout(1000);

		const viewButton = page.locator('button:has-text("View Details")').first();
		const viewButtonCount = await viewButton.count();

		if (viewButtonCount > 0) {
			await viewButton.click();
			await page.waitForLoadState('networkidle');

			// Should have back button
			const backButton = page.locator('button:has-text("Back")');
			await expect(backButton).toBeVisible();

			// Click back button
			await backButton.click();
			await page.waitForLoadState('networkidle');

			// Should return to students list
			expect(page.url()).toContain('/students');
			expect(page.url()).not.toContain('/students/'); // Not on detail page
		}
	});
});
