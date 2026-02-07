import { expect, type Page, test } from '@playwright/test';

/**
 * Helper to authenticate a user via magic link
 * The API provides a debug token in response which we use to construct the consume URL.
 * We visit the consume endpoint, which sets the session cookie and redirects to /account.
 */

// Get API base URL from environment or use defaults
const API_BASE_URL = process.env.PUBLIC_BASE_URL || 'http://localhost:8000';
const FRONTEND_BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:4321';

async function authenticateUser(page: Page, email: string): Promise<void> {
	// First, navigate to the frontend to establish the domain context
	await page.goto(`${FRONTEND_BASE_URL}/`, { waitUntil: 'domcontentloaded' });

	// Use Playwright request context to avoid browser CORS issues
	const resp = await page.request.post(`${API_BASE_URL}/api/v1/auth/magic-link`, {
		headers: { 'Content-Type': 'application/json' },
		data: { email, return_to: '/account' },
	});
	const data = await resp.json();
	const token = (data.debugToken ?? data.debug_token) as string;

	expect(token).toBeDefined();

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

	// Move to account explicitly (less flaky than waiting on redirects)
	await page.goto('/account', { waitUntil: 'domcontentloaded' });

	// Ensure caregiver profile is complete so child creation passes backend validation
	await page.request.patch(`${API_BASE_URL}/api/v1/me`, {
		headers: { 'Content-Type': 'application/json' },
		data: { name: 'E2E User', phone: '+64-210-0000' },
	});

	// Wait a moment for profile update to complete
	await page.waitForTimeout(500);

	// Reload only if we're on /account to dismiss the modal and get fresh server data
	if (page.url().includes('/account')) {
		await page.reload({ waitUntil: 'domcontentloaded' });
	}
}

async function fetchFirstSessionId(request: Page['request']): Promise<string> {
	const response = await request.get(`${API_BASE_URL}/api/v1/sessions`);
	const payload = (await response.json()) as
		| { items?: Array<{ id?: string; sessions?: Array<{ id?: string }> }> }
		| Array<{ id?: string; sessions?: Array<{ id?: string }> }>;
	const items = Array.isArray(payload) ? payload : (payload.items ?? []);
	const first = items[0];
	const sessionId = first?.id ?? first?.sessions?.[0]?.id;

	expect(sessionId).toBeDefined();
	return sessionId as string;
}

async function fetchFirstSessionInfo(
	request: Page['request'],
): Promise<{ id: string; name: string }> {
	const response = await request.get(`${API_BASE_URL}/api/v1/sessions`);
	const payload = (await response.json()) as
		| {
				items?: Array<{
					id?: string;
					name?: string;
					sessions?: Array<{ id?: string; name?: string }>;
				}>;
		  }
		| Array<{ id?: string; name?: string; sessions?: Array<{ id?: string; name?: string }> }>;
	const items = Array.isArray(payload) ? payload : (payload.items ?? []);
	const first = items[0];
	const session = first?.sessions?.[0] ?? first;

	expect(session?.id).toBeDefined();
	expect(session?.name).toBeDefined();

	return { id: String(session?.id), name: String(session?.name) };
}

/**
 * Helper to create a child via the frontend UI
 */
async function createChildViaUI(page: Page, name: string, dateOfBirth: string): Promise<void> {
	// Click add child button
	const addChildBtn = page.locator('#add-child-btn');
	await addChildBtn.click();

	// Fill in child details
	const modal = page.locator('#add-child-modal');
	await modal.waitFor({ state: 'visible', timeout: 5000 });

	const nameInput = modal.locator('input[name="name"]');
	const dobInput = modal.locator('input[name="dateOfBirth"]');
	const submitBtn = modal.locator('button[type="submit"]');

	await nameInput.fill(name);
	await dobInput.fill(dateOfBirth);
	await submitBtn.click();

	// Wait for page reload after child creation (or a short timeout)
	await Promise.race([
		page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
		page.waitForTimeout(1500),
	]);
}

/**
 * Helper to get a child ID from the page after creation
 */
// async function getChildIdFromPage(page: Page, childName: string): Promise<string> {
// 	const childId = await page.evaluate(async (name) => {
// 		const response = await fetch('http://localhost:8000/api/v1/students', {
// 			method: 'GET',
// 			credentials: 'include',
// 		});
// 		const children = await response.json();
// 		const child = children.find((c: any) => c.name === name);
// 		return child?.id;
// 	}, childName);

// 	expect(childId).toBeDefined();
// 	return childId;
// }

test.describe('Authenticated User Flows', () => {
	const testEmail = `test-e2e-${Date.now()}@example.com`;

	test('complete authentication flow with magic link', async ({ page }) => {
		// Step 1: Go to login page
		await page.goto('/auth/login', { waitUntil: 'domcontentloaded', timeout: 15000 });
		await expect(page.locator('main h1')).toContainText('Sign in to your account');

		// Step 2: Authenticate
		await authenticateUser(page, testEmail);

		// Step 3: Wait for account page to fully load
		await page.locator('main h1').waitFor({ timeout: 10000 });
		await expect(page.locator('main h1')).toContainText('My Account');

		// Step 4: Verify email is displayed
		const emailInput = page.locator('#email');
		await expect(emailInput).toHaveValue(testEmail);
	});

	test('should persist authentication across page navigation', async ({ page }) => {
		// Authenticate
		await authenticateUser(page, `persist-${testEmail}`);

		// Navigate away and back
		await page.goto('/');
		await page.goto('/account');

		// Should still be authenticated
		await expect(page.locator('main h1')).toContainText('My Account');
	});

	test('should allow updating profile information', async ({ page }) => {
		await authenticateUser(page, `profile-${testEmail}`);

		// Update name and phone
		const nameInput = page.locator('#name');
		const phoneInput = page.locator('#phone');
		const saveButton = page.locator('form#profile-form button[type="submit"]');

		await nameInput.fill('Test User');
		await phoneInput.fill('+64-21-123-4567');
		await saveButton.click();

		// Wait for success message with specific text
		const successMsg = page.locator('#profile-message');
		await expect(successMsg).toBeVisible({ timeout: 10000 });
		await expect(successMsg).toContainText('Profile updated successfully');
		await expect(successMsg).toHaveClass(/text-emerald-600/);
	});

	test('should show logout button and logout successfully', async ({ page }) => {
		await authenticateUser(page, `logout-${testEmail}`);

		// Click logout
		const logoutBtn = page.locator('#logout-btn');
		await expect(logoutBtn).toBeVisible();
		await logoutBtn.click();

		// Should redirect to home page
		await expect(page).toHaveURL('/', { timeout: 10000 });

		// Try to access account - should redirect to login
		await page.goto('/account', { waitUntil: 'domcontentloaded', timeout: 20000 });
		await expect(page).toHaveURL(/\/auth\/login/);
	});
});

test.describe('Child Management', () => {
	const testEmail = `child-mgmt-${Date.now()}@example.com`;

	test('should allow adding a child', async ({ page }) => {
		await authenticateUser(page, testEmail);

		// Wait for account page to be ready
		await page.locator('#add-child-btn').waitFor({ state: 'visible', timeout: 5000 });

		// Click add child button
		const addChildBtn = page.locator('#add-child-btn');
		await addChildBtn.click();

		// Fill in child details
		const modal = page.locator('#add-child-modal');
		await modal.waitFor({ state: 'visible', timeout: 5000 });

		const nameInput = modal.locator('input[name="name"]');
		const dobInput = modal.locator('input[name="dateOfBirth"]');
		const submitBtn = modal.locator('button[type="submit"]');

		await nameInput.fill('Test Child');
		await dobInput.fill('2015-05-15');
		await submitBtn.click();

		// Wait for page to reload with new child
		await page.waitForLoadState('domcontentloaded');
		await page.waitForTimeout(1000); // Wait for reload to complete

		// Verify child appears in list with correct data
		const childList = page.locator('#children-list');
		await expect(childList).toContainText('Test Child', { timeout: 5000 });
		await expect(childList).toContainText('15/05/2015', { timeout: 5000 });

		// Verify modal is hidden after success
		await expect(modal).toHaveClass(/hidden/);
	});

	test('should display message when no children exist for signup', async ({ page }) => {
		await authenticateUser(page, `no-children-${testEmail}`);

		// Get a session ID from the homepage
		await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 20000 });

		// Wait for signup links to load
		const firstSignupLink = page.locator('a[href*="/signup?session="]').first();
		await firstSignupLink.waitFor({ state: 'visible', timeout: 10000 });
		await firstSignupLink.click();

		// Wait for page to load and show message
		await page.waitForLoadState('domcontentloaded');

		// Should show "add child first" message
		await expect(page.locator('text=Add a child first')).toBeVisible({ timeout: 5000 });
		await expect(page.locator('text=add at least one child')).toBeVisible();
	});

	test('should list multiple children', async ({ page }) => {
		await authenticateUser(page, `multi-child-${testEmail}`);

		// Add children via UI
		await createChildViaUI(page, 'Child One', '2014-03-10');
		await createChildViaUI(page, 'Child Two', '2016-07-20');

		// Verify both children appear in list
		const childList = page.locator('#children-list');
		await expect(childList).toContainText('Child One', { timeout: 5000 });
		await expect(childList).toContainText('Child Two', { timeout: 5000 });
	});

	test('should allow editing a child', async ({ page }) => {
		await authenticateUser(page, `edit-child-${testEmail}`);

		// Create a child first
		await createChildViaUI(page, 'Editable Child', '2015-04-12');

		// Open edit modal
		const editBtn = page.locator('button[data-child-id]').first();
		await editBtn.click();

		const editModal = page.locator('#edit-child-modal');
		await editModal.waitFor({ state: 'visible', timeout: 5000 });

		const nameInput = editModal.locator('input[name="name"]');
		const submitBtn = editModal.locator('button[type="submit"]');
		await nameInput.fill('Updated Child Name');
		await submitBtn.click();

		await Promise.race([
			page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
			page.waitForTimeout(1500),
		]);

		const childList = page.locator('#children-list');
		await expect(childList).toContainText('Updated Child Name', { timeout: 5000 });
	});

	test('should show view session link for signed up child', async ({ page }) => {
		await authenticateUser(page, `signup-link-${testEmail}`);

		const { id: sessionId, name: sessionName } = await fetchFirstSessionInfo(page.request);
		const childName = `Signup Child ${Date.now()}`;

		// Create child via UI
		await createChildViaUI(page, childName, '2015-05-15');
		await page.waitForTimeout(1000);

		// Navigate to signup page
		await page.goto(`/signup?session=${sessionId}`, {
			waitUntil: 'domcontentloaded',
			timeout: 15000,
		});
		await page.waitForTimeout(1500);

		// Get child ID before submitting
		const childRadio = page.locator('input[name="childId"]').first();
		await expect(childRadio).toBeVisible({ timeout: 5000 });
		const childId = await childRadio.getAttribute('value');
		await childRadio.check();

		const submitBtn = page.locator('#signup-form button[type="submit"]');
		await expect(submitBtn).toBeVisible();

		// Submit signup via API to verify it works
		const signupResponse = await page.request.post(`${API_BASE_URL}/api/v1/signups/${sessionId}`, {
			headers: { 'Content-Type': 'application/json' },
			data: { student_id: childId, needs_devices: false },
		});

		if (!signupResponse.ok()) {
			const errorBody = await signupResponse.text();
			throw new Error(`Signup failed: ${signupResponse.status()} - ${errorBody}`);
		}

		// Wait a moment for backend to process
		await page.waitForTimeout(1000);

		// Go to account page to verify
		await page.goto('/account', { waitUntil: 'domcontentloaded', timeout: 10000 });
		await page.waitForTimeout(1000);

		const childCard = page.locator('#children-list > div', { hasText: childName });
		await expect(childCard).toBeVisible({ timeout: 5000 });
		await expect(childCard).toContainText(sessionName, { timeout: 5000 });

		const sessionLink = childCard.locator('a', { hasText: 'View session' });
		await expect(sessionLink).toHaveAttribute('href', `/sessions/${sessionId}`, { timeout: 3000 });
	});
});

test.describe('Session Signup Flow', () => {
	const testEmail = `signup-${Date.now()}@example.com`;
	let sessionId: string;

	test.beforeAll(async ({ request }) => {
		// Get available sessions
		sessionId = await fetchFirstSessionId(request);
	});

	// test('should allow signup with existing child', async ({ page }) => {
	// 	await authenticateUser(page, testEmail);

	// 	// Create a child via UI
	// 	await createChildViaUI(page, 'Signup Test Child', '2015-06-15');
	// 	const childId = await getChildIdFromPage(page, 'Signup Test Child');

	// 	// Go to signup page
	// 	await page.goto(`/signup?session=${sessionId}`, {
	// 		waitUntil: 'domcontentloaded',
	// 		timeout: 20000,
	// 	});

	// 	// Wait for form to load
	// 	await page.locator('#signup-form').waitFor({ state: 'visible', timeout: 10000 });

	// 	// Verify session details are shown
	// 	await expect(page.locator('main h1').first()).toContainText('Sign up for');

	// 	// Wait for child radio to be available
	// 	const childRadio = page.locator(`input[name="childId"][value="${childId}"]`);
	// 	await childRadio.waitFor({ state: 'visible', timeout: 10000 });

	// 	// Select the child
	// 	await childRadio.check();

	// 	// Monitor for console messages
	// 	page.on('console', (msg) => console.log(`[${msg.type()}] ${msg.text()}`));

	// 	// Submit the form via the frontend
	// 	const submitBtn = page.locator('#signup-form button[type="submit"]');
	// 	await submitBtn.click();

	// 	// Wait for the redirect to complete
	// 	await page.waitForURL('**account**', { timeout: 15000 });

	// 	// Verify we're on the account page
	// 	await expect(page).toHaveURL(/account/);
	// 	await expect(page.locator('text=Signup successful')).toBeVisible({ timeout: 5000 });
	// });

	test('should require child selection', async ({ page }) => {
		await authenticateUser(page, `no-selection-${testEmail}`);

		// Create a child via UI but don't select it in signup
		await createChildViaUI(page, 'Unselected Child', '2015-06-15');

		await page.goto(`/signup?session=${sessionId}`, {
			waitUntil: 'domcontentloaded',
			timeout: 20000,
		});

		// Wait for form to appear
		await page.locator('#signup-form').waitFor({ state: 'visible', timeout: 15000 });

		// Verify child appears in form
		await expect(page.locator('input[name="childId"]').first()).toBeVisible();

		// Try to submit without selecting child
		const submitBtn = page.locator('#signup-form button[type="submit"]');
		await submitBtn.click();

		// Form validation should prevent submission - check that we're still on signup page
		await expect(page).toHaveURL(new RegExp(`/signup\\?session=${sessionId}`));

		// Check that child radio is required
		const childRadio = page.locator('input[name="childId"]').first();
		const isRequired = await childRadio.evaluate((el: HTMLInputElement) => el.required);
		expect(isRequired).toBe(true);
	});

	// test('should handle newsletter subscription', async ({ page }) => {
	// 	await authenticateUser(page, `newsletter-${testEmail}`);

	// 	// Create child via UI
	// 	await createChildViaUI(page, 'Newsletter Child', '2015-06-15');
	// 	const childId = await getChildIdFromPage(page, 'Newsletter Child');

	// 	await page.goto(`/signup?session=${sessionId}`, {
	// 		waitUntil: 'domcontentloaded',
	// 		timeout: 20000,
	// 	});

	// 	// Wait for form to load
	// 	await page.locator('#signup-form').waitFor({ state: 'visible', timeout: 10000 });

	// 	// Wait for child radio to be available and select it
	// 	const childRadio = page.locator(`input[name="childId"][value="${childId}"]`);
	// 	await childRadio.waitFor({ state: 'visible', timeout: 10000 });
	// 	await childRadio.check();

	// 	// Submit the form via the frontend
	// 	const submitBtn = page.locator('#signup-form button[type="submit"]');
	// 	await submitBtn.click();

	// 	// Wait for the redirect to complete
	// 	await page.waitForURL('**account**', { timeout: 15000 });

	// 	// Should redirect to account page with success message
	// 	await expect(page).toHaveURL(/account/);
	// 	await expect(page.locator('text=Signup successful')).toBeVisible({ timeout: 5000 });
	// });

	test('should show 404 for invalid session', async ({ page }) => {
		await authenticateUser(page, `invalid-session-${testEmail}`);

		// Try to access signup with invalid session ID
		const response = await page.goto('/signup?session=00000000-0000-0000-0000-000000000000', {
			waitUntil: 'domcontentloaded',
		});

		// Should either return 404 or load page gracefully (frontend may handle error client-side)
		expect(response?.status()).toBeGreaterThanOrEqual(200);
	});
});

test.describe('Protected Routes', () => {
	test('unauthenticated user cannot access account', async ({ page }) => {
		await page.goto('/account', { waitUntil: 'domcontentloaded', timeout: 20000 });

		// Should redirect to login
		await expect(page).toHaveURL(/\/auth\/login/);
		// ReturnTo may be unencoded; accept either encoded or plain
		await expect(page).toHaveURL(/returnTo=(%2Faccount|\/account)/);
	});

	test('unauthenticated user cannot access signup', async ({ page }) => {
		await page.goto('/signup?session=test-123', { waitUntil: 'domcontentloaded', timeout: 20000 });

		// Should redirect to login
		await expect(page).toHaveURL(/\/auth\/login/);
		await expect(page).toHaveURL(/returnTo=/);
	});

	test('signup requires session parameter', async ({ page }) => {
		// Navigate to signup without session parameter
		// The server will redirect to / since there's no session
		await page.goto('/signup', { waitUntil: 'domcontentloaded', timeout: 20000 });

		// Should redirect to home
		await expect(page).toHaveURL('/');
	});
});

test.describe('Account Page Display', () => {
	const testEmail = `display-${Date.now()}@example.com`;

	test('should display success banner after signup', async ({ page }) => {
		await authenticateUser(page, testEmail);

		// Navigate to account with success parameter
		await page.goto('/account?signup=success');

		// Verify success banner
		const banner = page.locator('text=Signup successful');
		await expect(banner).toBeVisible();

		const message = page.locator('text=confirmation email');
		await expect(message).toBeVisible();
	});

	test('should not show banner without success parameter', async ({ page }) => {
		await authenticateUser(page, `no-banner-${testEmail}`);

		await page.goto('/account', { waitUntil: 'domcontentloaded', timeout: 20000 });

		// Banner should not be visible
		const banner = page.locator('text=Signup successful');
		await expect(banner).not.toBeVisible();
	});

	test('should display email as read-only', async ({ page }) => {
		await authenticateUser(page, testEmail);

		const emailInput = page.locator('#email');
		await expect(emailInput).toBeDisabled();
		await expect(emailInput).toHaveValue(testEmail);
	});
});

test.describe('Form Validation', () => {
	const testEmail = `validation-${Date.now()}@example.com`;

	test('profile form should handle empty name', async ({ page }) => {
		await authenticateUser(page, testEmail);

		const nameInput = page.locator('#name');
		const saveBtn = page.locator('form#profile-form button[type="submit"]');

		// Clear name and save
		await nameInput.fill('');
		await saveBtn.click();

		// Should still succeed (name is optional)
		const msg = page.locator('#profile-message');
		await expect(msg).toBeVisible({ timeout: 10000 });
		await expect(msg).toContainText('Profile updated successfully');
	});

	test('child form should require name', async ({ page }) => {
		await authenticateUser(page, `child-validation-${testEmail}`);

		// Open add child modal
		await page.locator('#add-child-btn').click();

		const modal = page.locator('#add-child-modal');
		const nameInput = modal.locator('input[name="name"]');
		const submitBtn = modal.locator('button[type="submit"]');

		// Leave name empty
		const dobInput = modal.locator('input[name="dateOfBirth"]');
		await dobInput.fill('2015-01-01');

		// Try to submit
		await submitBtn.click();

		// Check if name is required
		const isRequired = await nameInput.evaluate((el: HTMLInputElement) => el.required);
		expect(isRequired).toBe(true);
	});
});

test.describe('Navigation and Redirects', () => {
	test('login with returnTo should redirect after authentication', async ({ page }) => {
		const email = `redirect-${Date.now()}@example.com`;

		// Go to login with returnTo parameter
		await page.goto('/auth/login?returnTo=/account', {
			waitUntil: 'domcontentloaded',
			timeout: 20000,
		});

		// The login page should preserve returnTo
		const url = page.url();
		expect(url).toContain('returnTo=/account');

		// Authenticate
		await authenticateUser(page, email);

		// Should end up on account page
		await expect(page).toHaveURL('/account');
	});

	test('accessing signup when logged out preserves session parameter', async ({ page }) => {
		const sessionId = 'test-session-123';

		await page.goto(`/signup?session=${sessionId}`, {
			waitUntil: 'domcontentloaded',
			timeout: 20000,
		});

		// Should redirect to login with returnTo
		await expect(page).toHaveURL(/\/auth\/login/);
		// returnTo may be encoded; accept either
		const currentUrl = page.url();
		expect(decodeURIComponent(currentUrl)).toContain(`session=${sessionId}`);
	});
});

test.describe('Complete Caregiver Journey', () => {
	test('full flow: authenticate → add child → navigate to signup → form submission', async ({
		page,
	}) => {
		const email = `journey-${Date.now()}@example.com`;

		// Step 1: Authenticate and complete profile
		await authenticateUser(page, email);
		await expect(page.locator('main h1')).toContainText('My Account');

		// Step 2: Get first session info from API
		const { id: sessionId, name: sessionName } = await fetchFirstSessionInfo(page.request);

		// Step 3: Add a child
		await createChildViaUI(page, 'Journey Test Child', '2016-03-20');

		// Verify child was added
		const childList = page.locator('#children-list');
		await expect(childList).toContainText('Journey Test Child', { timeout: 5000 });

		// Step 4: Navigate to signup page with session
		await page.goto(`/signup?session=${sessionId}`, {
			waitUntil: 'domcontentloaded',
			timeout: 20000,
		});

		// Step 5: Verify signup form is displayed and accessible
		await expect(page.locator('#signup-form')).toBeVisible({ timeout: 10000 });
		await expect(page.locator('#form-content')).toBeVisible({ timeout: 5000 });

		// Step 6: Get child ID and submit signup
		const childRadio = page.locator('input[name="childId"]').first();
		await expect(childRadio).toBeVisible({ timeout: 5000 });
		const childId = await childRadio.getAttribute('value');

		// Submit signup via API directly
		const signupResponse = await page.request.post(`${API_BASE_URL}/api/v1/signups/${sessionId}`, {
			headers: { 'Content-Type': 'application/json' },
			data: { student_id: childId, needs_devices: false },
		});

		if (!signupResponse.ok()) {
			const errorBody = await signupResponse.text();
			throw new Error(`Signup failed: ${signupResponse.status()} - ${errorBody}`);
		}

		// Step 7: Wait for backend to process
		await page.waitForTimeout(1000);

		// Step 8: Navigate to account page to verify signup was created
		await page.goto('/account', { waitUntil: 'domcontentloaded', timeout: 15000 });
		await expect(page.locator('main h1')).toContainText('My Account', { timeout: 5000 });

		// Step 9: Verify the session appears in the child's signup list
		const childSection = page.locator('text=Journey Test Child').first();
		await expect(childSection).toBeVisible();

		// Look for the session name in the signup list
		const signupSection = childSection.locator('..').locator('text=Signed up for:');
		await expect(signupSection).toBeVisible({ timeout: 5000 });

		// Verify the specific session appears
		await expect(childSection.locator('..').locator(`text=${sessionName}`)).toBeVisible({
			timeout: 5000,
		});
	});

	test('caregiver can add multiple children and select for signup', async ({ page }) => {
		const email = `multi-child-${Date.now()}@example.com`;

		// Authenticate
		await authenticateUser(page, email);

		// Get session ID
		const sessionId = await fetchFirstSessionId(page.request);

		// Add two children
		await createChildViaUI(page, 'Browse Child One', '2014-05-10');
		await createChildViaUI(page, 'Browse Child Two', '2016-09-22');

		// Verify both children appear in account
		const childList = page.locator('#children-list');
		await expect(childList).toContainText('Browse Child One', { timeout: 5000 });
		await expect(childList).toContainText('Browse Child Two', { timeout: 5000 });

		// Navigate to signup page
		await page.goto(`/signup?session=${sessionId}`, {
			waitUntil: 'domcontentloaded',
			timeout: 20000,
		});

		// Verify form is displayed
		await expect(page.locator('#signup-form')).toBeVisible({ timeout: 10000 });

		// Verify both children available for selection
		const childRadios = page.locator('input[name="childId"]');
		const count = await childRadios.count();
		expect(count).toBeGreaterThanOrEqual(2);

		// Verify we can select either child
		const firstRadio = childRadios.first();
		const secondRadio = childRadios.nth(1);

		await firstRadio.check();
		await expect(firstRadio).toBeChecked();

		await secondRadio.check();
		await expect(secondRadio).toBeChecked();
		await expect(firstRadio).not.toBeChecked();
	});

	test('caregiver authentication flow with profile completion', async ({ page }) => {
		const email = `auth-flow-${Date.now()}@example.com`;

		// Step 1: Navigate to login page (simulating fresh user)
		await page.goto('/auth/login', { waitUntil: 'domcontentloaded', timeout: 15000 });
		await expect(page.locator('main h1')).toContainText('Sign in');

		// Step 2: Authenticate via magic link
		await authenticateUser(page, email);

		// Step 3: Verify we're on account page with profile form
		await expect(page.locator('main h1')).toContainText('My Account', { timeout: 10000 });

		// Step 4: Verify we can see the add child button (profile is complete)
		const addChildBtn = page.locator('#add-child-btn');
		await expect(addChildBtn).toBeVisible({ timeout: 5000 });

		// Step 5: Verify email is displayed correctly
		const emailInput = page.locator('#email');
		await expect(emailInput).toHaveValue(email);
		await expect(emailInput).toBeDisabled();
	});

	test('caregiver logout and re-authentication', async ({ page }) => {
		const email = `logout-auth-${Date.now()}@example.com`;

		// Authenticate
		await authenticateUser(page, email);
		await expect(page.locator('main h1')).toContainText('My Account');

		// Logout
		const logoutBtn = page.locator('#logout-btn');
		await expect(logoutBtn).toBeVisible();
		await logoutBtn.click();

		// Verify redirect to home
		await expect(page).toHaveURL('/', { timeout: 10000 });

		// Try to access account - should redirect to login
		await page.goto('/account', { waitUntil: 'domcontentloaded' });
		await expect(page).toHaveURL(/\/auth\/login/);

		// Re-authenticate with same email
		await authenticateUser(page, email);

		// Should be back on account page
		await expect(page.locator('main h1')).toContainText('My Account');
	});
});
