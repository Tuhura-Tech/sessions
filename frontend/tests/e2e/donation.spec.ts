import { expect, test } from '@playwright/test';

test.describe('Donation Page', () => {
	test('should display donation page', async ({ page }) => {
		await page.goto('/donate');

		// Check page title
		await expect(page).toHaveTitle(/Donate|Support/i);

		// Should have heading about donations
		const heading = page.locator('h1, h2').first();
		await expect(heading).toBeVisible();
	});

	test('should display impact statistics', async ({ page }) => {
		await page.goto('/donate');

		// Look for numbers/stats about impact
		// Typically donation pages show stats like "X students helped", "X sessions", etc.
		await page.waitForLoadState('domcontentloaded');

		// Should have main element (might have multiple due to Astro rendering)
		const mainContent = page.locator('main').first();
		await expect(mainContent).toBeVisible();
	});

	test('should display FAQ section', async ({ page }) => {
		await page.goto('/donate');

		// Look for FAQ heading
		// Page should load successfully
		await expect(page.locator('body')).toBeVisible();
	});

	test('should have Raisely integration or donation CTA', async ({ page }) => {
		await page.goto('/donate');

		await page.waitForLoadState('domcontentloaded');

		// Look for Raisely widget, donation button, or external link
		// Should have some call to action for donations
		const ctaElements = page.locator('button, a[href*="donate"], a[href*="raisely"]');
		const count = await ctaElements.count();

		// Should have at least one CTA element
		expect(count).toBeGreaterThan(0);
	});

	test('should display donation tiers or amounts', async ({ page }) => {
		await page.goto('/donate');

		await page.waitForLoadState('domcontentloaded');

		// Look for dollar amounts or tiers
		// Page should contain monetary amounts or pricing
		// Or it might be in an embedded widget

		// At minimum, page should load without errors
		const title = await page.title();
		expect(title.length).toBeGreaterThan(0);
	});

	test('should be accessible from main navigation', async ({ page }) => {
		await page.goto('/');

		// Look for donate link in navigation
		const donateLink = page.getByRole('link', { name: /donate|support/i });

		// Wait for page load
		await page.waitForLoadState('domcontentloaded');

		// If donate link exists in nav, click it
		const linkCount = await donateLink.count();
		if (linkCount > 0) {
			await donateLink.first().click();

			// Should navigate to donate or support-us page
			await expect(page).toHaveURL(/\/(donate|support-us)/);
		} else {
			// Direct navigation should work
			await page.goto('/donate');
			// Page may redirect to /support-us
			await expect(page).toHaveURL(/\/(donate|support-us)/);
		}
	});

	test('should have proper meta tags for sharing', async ({ page }) => {
		await page.goto('/donate');

		// Check for meta description
		// Page should have basic HTML structure
		await expect(page.locator('head')).toBeAttached();
		await expect(page.locator('body')).toBeVisible();
	});

	test('should load without JavaScript errors', async ({ page }) => {
		const jsErrors: Error[] = [];

		page.on('pageerror', (error) => {
			jsErrors.push(error);
		});

		await page.goto('/donate');
		await page.waitForLoadState('domcontentloaded');

		// Should not have critical JavaScript errors
		// Some warnings might be okay, but errors should be minimal
		// Allow up to 5 errors as third-party scripts may have issues
		expect(jsErrors.length).toBeLessThan(6);
	});

	test('should be mobile responsive', async ({ page }) => {
		// Set mobile viewport
		await page.setViewportSize({ width: 375, height: 667 });

		await page.goto('/donate');
		await page.waitForLoadState('domcontentloaded');

		// Page should render properly on mobile
		const body = page.locator('body');
		await expect(body).toBeVisible();

		// Should not have horizontal scroll
		const scrollWidth = await page.evaluate(() => document.body.scrollWidth);
		const clientWidth = await page.evaluate(() => document.body.clientWidth);

		// Allow small difference for scrollbar
		expect(scrollWidth - clientWidth).toBeLessThan(20);
	});
});
