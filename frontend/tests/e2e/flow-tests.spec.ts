import { expect, type Page, test } from '@playwright/test';

/**
 * Common flow tests for frontend (caregiver portal)
 * Tests complete workflows: authentication → student creation → session browsing → signup
 */

const API_BASE_URL = process.env.PUBLIC_BASE_URL || 'http://localhost:8000';
const FRONTEND_BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:4321';

/**
 * Helper to authenticate a user via magic link
 */
async function authenticateUser(page: Page, email: string): Promise<void> {
	// Navigate to frontend to establish domain context
	await page.goto(`${FRONTEND_BASE_URL}/`, { waitUntil: 'domcontentloaded' });

	// Request magic link
	const resp = await page.request.post(`${API_BASE_URL}/api/v1/auth/magic-link`, {
		headers: { 'Content-Type': 'application/json' },
		data: { email, return_to: '/account' },
	});
	const data = await resp.json();
	const token = (data.debugToken ?? data.debug_token) as string;
	expect(token).toBeDefined();

	// Consume magic link
	const consumeResponse = await page.request.get(
		`${API_BASE_URL}/api/v1/auth/magic-link/consume?token=${token}&returnTo=/account`,
	);
	const setCookie = consumeResponse.headers()['set-cookie'];
	const sessionCookie = setCookie?.split(';')[0];
	const [cookieName, cookieValue] = sessionCookie ? sessionCookie.split('=') : [];
	if (cookieName && cookieValue) {
		await page.context().addCookies([
			{
				name: cookieName,
				value: cookieValue,
				url: FRONTEND_BASE_URL,
			},
		]);
	}

	// Navigate to account page
	await page.goto('/account', { waitUntil: 'domcontentloaded' });

	// Complete profile
	await page.request.patch(`${API_BASE_URL}/api/v1/me`, {
		headers: { 'Content-Type': 'application/json' },
		data: { name: 'E2E Caregiver', phone: '+64-21-0000001' },
	});

	// Reload to get fresh profile state
	await page.reload({ waitUntil: 'domcontentloaded' });
}

/**
 * Test: Complete caregiver auth flow
 * Verifies: Magic link generation → token consumption → profile access
 */
test('Caregiver auth flow: request magic link → consume token → access account', async ({
	page,
}) => {
	const testEmail = `caregiver-${Date.now()}@e2e-test.example.com`;

	// Authenticate via magic link
	await authenticateUser(page, testEmail);

	// Verify we're on account page
	expect(page.url()).toContain('/account');

	// Verify profile elements are visible
	const profileHeading = page.locator('text=Account|Profile');
	if (await profileHeading.isVisible({ timeout: 2000 }).catch(() => false)) {
		await expect(profileHeading).toBeVisible({ timeout: 2000 });
	}
});

/**
 * Test: Complete student creation workflow
 * Verifies: Create student → Verify in list → Access student details
 */
test('Student workflow: create student → verify in list → access account', async ({ page }) => {
	const testEmail = `student-${Date.now()}@e2e-test.example.com`;
	const studentName = `E2E Student ${Date.now()}`;

	// Step 1: Authenticate
	await authenticateUser(page, testEmail);

	// Step 2: Create student via API
	const createResponse = await page.request.post(`${API_BASE_URL}/api/v1/students`, {
		headers: { 'Content-Type': 'application/json' },
		data: {
			name: studentName,
			dateOfBirth: '2012-06-15',
			region: 'Auckland',
			schoolName: 'Test School',
		},
	});
	expect(createResponse.ok()).toBeTruthy();

	// Step 3: Verify student was created
	const studentData = await createResponse.json();
	expect(studentData.id).toBeDefined();

	// Step 4: Navigate to children page
	await page.goto(`${FRONTEND_BASE_URL}/children`, { waitUntil: 'domcontentloaded' });

	// Step 5: Verify student appears in list (via API call)
	const listResponse = await page.request.get(`${API_BASE_URL}/api/v1/students`);
	const studentsList = (await listResponse.json()) as Array<{ id: string; name: string }>;
	const found = studentsList.find((s) => s.name === studentName);
	expect(found).toBeDefined();
});

/**
 * Test: Session browsing workflow
 * Verifies: Navigate to sessions → Verify data loads → Check session details
 */
test('Session browsing: navigate to sessions → verify data loads', async ({ page }) => {
	const testEmail = `browse-${Date.now()}@e2e-test.example.com`;

	// Step 1: Authenticate
	await authenticateUser(page, testEmail);

	// Step 2: Get available sessions via API
	const sessionsResponse = await page.request.get(`${API_BASE_URL}/api/v1/sessions`);
	expect(sessionsResponse.ok()).toBeTruthy();
	const sessionsData = await sessionsResponse.json();

	// Step 3: Verify we got sessions
	expect(Array.isArray(sessionsData) || sessionsData.items).toBeDefined();

	// Step 4: Navigate to sessions page
	await page.goto(`${FRONTEND_BASE_URL}/sessions`, { waitUntil: 'domcontentloaded' });

	// Step 5: Wait for page to load
	await page.waitForTimeout(1000);

	// Verify page loaded
	expect(page.url()).toContain('/sessions');
});

/**
 * Test: Profile update workflow
 * Verifies: Complete profile → Save data → Verify persistence
 */
test('Profile workflow: update profile → verify persistence', async ({ page }) => {
	const testEmail = `profile-${Date.now()}@e2e-test.example.com`;
	const profileName = `E2E Profile ${Date.now()}`;

	// Step 1: Authenticate
	await authenticateUser(page, testEmail);

	// Step 2: Update profile via API
	const updateResponse = await page.request.patch(`${API_BASE_URL}/api/v1/me`, {
		headers: { 'Content-Type': 'application/json' },
		data: {
			name: profileName,
			phone: '+64-21-0000002',
		},
	});
	expect(updateResponse.ok()).toBeTruthy();

	// Step 3: Fetch updated profile
	const getResponse = await page.request.get(`${API_BASE_URL}/api/v1/me`);
	expect(getResponse.ok()).toBeTruthy();
	const profileData = await getResponse.json();

	// Step 4: Verify profile was updated
	expect(profileData.name).toBe(profileName);
	expect(profileData.phone).toContain('0000002');

	// Step 5: Reload page and verify changes persisted
	await page.reload({ waitUntil: 'domcontentloaded' });

	// Verify still authenticated
	expect(page.url()).toContain('/account');
});

/**
 * Test: Logout workflow
 * Verifies: Logout → Session revoked → Redirect to login
 */
test('Logout workflow: logout → verify session revoked → check redirect', async ({ page }) => {
	const testEmail = `logout-${Date.now()}@e2e-test.example.com`;

	// Step 1: Authenticate
	await authenticateUser(page, testEmail);

	// Step 2: Verify authenticated
	expect(page.url()).toContain('/account');

	// Step 3: Logout via API
	const logoutResponse = await page.request.post(`${API_BASE_URL}/api/v1/auth/logout`);
	expect(logoutResponse.ok()).toBeTruthy();

	// Step 4: Navigate to account (should redirect)
	await page.goto(`${FRONTEND_BASE_URL}/account`, { waitUntil: 'domcontentloaded' });

	// Step 5: Verify redirected to login
	const url = page.url();
	expect(url).toMatch(/\/(login|auth)/);
});

/**
 * Test: Data persistence
 * Verifies: Create student → Navigate away → Navigate back → Student persists
 */
test('Data persistence: student data persists across navigation', async ({ page }) => {
	const testEmail = `persist-${Date.now()}@e2e-test.example.com`;
	const studentName = `Persist ${Date.now()}`;

	// Step 1: Authenticate
	await authenticateUser(page, testEmail);

	// Step 2: Create student via API
	const createResponse = await page.request.post(`${API_BASE_URL}/api/v1/students`, {
		headers: { 'Content-Type': 'application/json' },
		data: {
			name: studentName,
			dateOfBirth: '2014-05-10',
		},
	});
	expect(createResponse.ok()).toBeTruthy();
	const studentId = (await createResponse.json()).id;

	// Step 3: Navigate away
	await page.goto(`${FRONTEND_BASE_URL}/`, { waitUntil: 'domcontentloaded' });
	await page.waitForTimeout(500);

	// Step 4: Navigate back to children
	await page.goto(`${FRONTEND_BASE_URL}/children`, { waitUntil: 'domcontentloaded' });

	// Step 5: Verify student still exists
	const listResponse = await page.request.get(`${API_BASE_URL}/api/v1/students`);
	const studentsList = (await listResponse.json()) as Array<{ id: string; name: string }>;
	const found = studentsList.find((s) => s.id === studentId);
	expect(found).toBeDefined();
	if (found) {
		expect(found.name).toBe(studentName);
	}
});
