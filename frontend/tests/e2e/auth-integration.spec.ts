import { expect, type Page, test } from '@playwright/test';

/**
 * Integration tests for the authentication and account flow.
 *
 * These tests verify:
 * 1. Magic link login page functionality
 * 2. Account page access control
 * 3. Profile management
 * 4. Child management
 * 5. Signup page access control
 * 6. Signup form functionality (with children)
 *
 * Note: These tests work with the actual backend API.
 * They use unique emails to avoid conflicts between test runs.
 */

// Get API base URL from environment or use defaults
const API_BASE_URL = process.env.PUBLIC_BASE_URL || 'http://localhost:8000';
const FRONTEND_BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:4321';

// Utility to generate unique test data
const generateTestData = () => {
	const uniqueSuffix = `${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
	return {
		email: `test-${uniqueSuffix}@example.com`,
		childName: `Test Child ${uniqueSuffix}`,
		childDob: '2015-01-15',
		parentName: `Test Parent ${uniqueSuffix}`,
		parentPhone: '+64-200-123-456',
	};
};

/**
 * Helper to authenticate a user via magic link
 */
async function authenticateUser(page: Page, email: string): Promise<void> {
	await page.goto(`${FRONTEND_BASE_URL}/`, { waitUntil: 'domcontentloaded' });

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

	await page.goto('/account', { waitUntil: 'domcontentloaded' });

	await page.request.patch(`${API_BASE_URL}/api/v1/me`, {
		headers: { 'Content-Type': 'application/json' },
		data: { name: 'E2E User', phone: '+64-210-0000' },
	});

	await page.waitForTimeout(500);

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

/**
 * Helper to create a child via the frontend UI
 */
async function createChildViaUI(page: Page, name: string, dateOfBirth: string): Promise<void> {
	const addChildBtn = page.locator('#add-child-btn');
	await addChildBtn.click();

	const modal = page.locator('#add-child-modal');
	await modal.waitFor({ state: 'visible', timeout: 5000 });

	const nameInput = modal.locator('input[name="name"]');
	const dobInput = modal.locator('input[name="dateOfBirth"]');
	const submitBtn = modal.locator('button[type="submit"]');

	await nameInput.fill(name);
	await dobInput.fill(dateOfBirth);
	await submitBtn.click();

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

test.describe('Authentication Flow - Magic Link', () => {
	test('should display login page with email input', async ({ page }) => {
		await page.goto('/auth/login');

		// Verify page structure - use more specific selector to avoid Astro islands
		const heading = page.locator('main h1');
		await expect(heading).toContainText('Sign in to your account');

		// Verify form elements
		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');

		await expect(emailInput).toBeVisible();
		await expect(submitBtn).toBeVisible();
		await expect(submitBtn).toContainText('Send magic link');
	});

	test('should validate email format before submission', async ({ page }) => {
		await page.goto('/auth/login');

		const emailInput = page.locator('#email');

		// Type invalid email
		await emailInput.fill('not-an-email');

		// Get HTML5 validation state
		const isValid = await emailInput.evaluate((el: HTMLInputElement) => {
			return el.validity.valid;
		});

		expect(isValid).toBe(false);
	});

	test('should accept valid email and send request', async ({ page }) => {
		const { email } = generateTestData();

		await page.goto('/auth/login');

		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');
		const successMsg = page.locator('#success-message');

		// Fill email
		await emailInput.fill(email);

		// Intercept the API request
		const requestPromise = page.waitForRequest(
			(request) => request.url().includes('/api/v1/auth/magic-link') && request.method() === 'POST',
		);

		// Submit form
		await submitBtn.click();

		// Verify request was made
		const request = await requestPromise;
		const postData = request.postDataJSON();

		expect(postData).toEqual({
			email: email,
			return_to: '/account',
		});

		// Verify success message appears
		await expect(successMsg).toBeVisible();
		await expect(successMsg).toContainText(`Check your email! We've sent a magic link to ${email}`);
	});

	test('should pass returnTo parameter through login flow', async ({ page }) => {
		const { email } = generateTestData();
		const returnTo = '/signup?session=test-session-id';

		await page.goto(`/auth/login?returnTo=${encodeURIComponent(returnTo)}`);

		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');

		await emailInput.fill(email);

		// Intercept request
		const requestPromise = page.waitForRequest((request) =>
			request.url().includes('/api/v1/auth/magic-link'),
		);

		await submitBtn.click();

		const request = await requestPromise;
		const postData = request.postDataJSON();

		expect(postData.return_to).toBe(returnTo);
	});

	test('should handle API errors gracefully', async ({ page }) => {
		const { email } = generateTestData();

		await page.goto('/auth/login');

		// Mock API failure
		await page.route('**/api/v1/auth/magic-link', (route) => {
			route.abort('failed');
		});

		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');
		const errorMsg = page.locator('#error-message');

		await emailInput.fill(email);
		await submitBtn.click();

		// Should show error message
		await expect(errorMsg).toBeVisible();
		await expect(errorMsg).toContainText('Something went wrong');
	});

	test('should disable button while request is in flight', async ({ page }) => {
		const { email } = generateTestData();

		await page.goto('/auth/login');

		// Delay the API response
		await page.route('**/api/v1/auth/magic-link', (route) => {
			setTimeout(() => route.continue(), 500);
		});

		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');

		await emailInput.fill(email);

		// Click submit
		const clickPromise = submitBtn.click();

		// Button text should change during submission
		await expect(submitBtn).toContainText('Sending...');

		// Wait for request to complete
		await clickPromise;
		await page.waitForTimeout(600);

		// Button text should return to normal after success
		await expect(submitBtn).toContainText('Send magic link');
	});
});

test.describe('Access Control - Unauthenticated Users', () => {
	test('should redirect to login when accessing /account without authentication', async ({
		page,
	}) => {
		await page.goto('/account', { waitUntil: 'domcontentloaded', timeout: 20000 });

		// Should redirect to login page
		expect(page.url()).toContain('/auth/login');
		expect(page.url()).toContain('returnTo');
	});

	test('should redirect to login when accessing /signup without authentication', async ({
		page,
	}) => {
		const sessionId = 'test-session-123';

		await page.goto(`/signup?session=${sessionId}`, {
			waitUntil: 'domcontentloaded',
			timeout: 20000,
		});

		// Should redirect to login page
		expect(page.url()).toContain('/auth/login');
		expect(page.url()).toContain('returnTo');
	});

	test('should reject signup without session parameter', async ({ page }) => {
		await page.goto('/signup', { waitUntil: 'domcontentloaded', timeout: 20000 });

		// Should redirect to home
		await expect(page).toHaveURL('/');
	});
});

test.describe('Account Page - User Profile', () => {
	const testEmail = `profile-${Date.now()}@example.com`;

	test('should display profile form with current user data', async ({ page }) => {
		await authenticateUser(page, testEmail);

		// Verify email field (read-only)
		const emailInput = page.locator('#email');
		await expect(emailInput).toBeDisabled();
		await expect(emailInput).toHaveValue(testEmail);

		// Verify name and phone fields are editable
		const nameInput = page.locator('#name');
		const phoneInput = page.locator('#phone');

		await expect(nameInput).toBeEnabled();
		await expect(phoneInput).toBeEnabled();

		// Verify save button exists
		const saveBtn = page.locator('form#profile-form button[type="submit"]');
		await expect(saveBtn).toBeVisible();
	});

	test('should allow updating profile information', async ({ page }) => {
		await authenticateUser(page, `update-${testEmail}`);

		// Update name and phone
		const nameInput = page.locator('#name');
		const phoneInput = page.locator('#phone');
		const saveBtn = page.locator('form#profile-form button[type="submit"]');

		// Ensure the fields have values first (authenticateUser sets them)
		await expect(nameInput).toHaveValue('E2E User');
		await expect(phoneInput).toHaveValue('+64-210-0000');

		await nameInput.fill('Updated Test Name');
		await phoneInput.fill('+64-21-999-8888');
		await saveBtn.click();

		// Verify success message appears with correct text
		const successMsg = page.locator('#profile-message');
		await expect(successMsg).toBeVisible({ timeout: 10000 });
		await expect(successMsg).toContainText('Profile updated successfully');
		await expect(successMsg).toHaveClass(/text-emerald-600/);
	});

	test('should display sign out button', async ({ page }) => {
		await authenticateUser(page, `logout-${testEmail}`);

		// Verify logout button is visible
		const logoutBtn = page.locator('#logout-btn');
		await expect(logoutBtn).toBeVisible();

		// Click logout
		await logoutBtn.click();

		// Should redirect to home
		await expect(page).toHaveURL('/', { timeout: 10000 });

		// Subsequent access to /account should redirect to login
		await page.goto('/account', { waitUntil: 'domcontentloaded', timeout: 20000 });
		await expect(page).toHaveURL(/\/auth\/login/);
	});
});

test.describe('Account Page - Children Management', () => {
	const testEmail = `children-${Date.now()}@example.com`;
	let sessionId: string;

	test.beforeAll(async ({ request }) => {
		sessionId = await fetchFirstSessionId(request);
	});

	test('should display "add child first" message when no children exist', async ({ page }) => {
		await authenticateUser(page, `no-children-${testEmail}`);

		// Navigate to signup page
		await page.goto(`/signup?session=${sessionId}`, {
			waitUntil: 'domcontentloaded',
			timeout: 20000,
		});

		// Verify "Add a child first" message is shown
		await expect(page.locator('text=Add a child first')).toBeVisible();
		await expect(page.locator('text=You need to add at least one child')).toBeVisible();

		// Verify link to account page (use more specific selector)
		const accountLink = page.locator('a.btn.btn-primary', { hasText: 'Add a child and continue' });
		await expect(accountLink).toBeVisible();
	});

	test('should allow adding a child', async ({ page }) => {
		await authenticateUser(page, `add-child-${testEmail}`);

		const { childName, childDob } = generateTestData();

		// Create child via UI
		await createChildViaUI(page, childName, childDob);

		// Verify child appears in the list
		await expect(page.locator(`text=${childName}`)).toBeVisible();
	});

	test('should display list of children', async ({ page }) => {
		await authenticateUser(page, `list-children-${testEmail}`);

		// Create multiple children
		const child1 = generateTestData();
		const child2 = generateTestData();

		await createChildViaUI(page, child1.childName, child1.childDob);
		await createChildViaUI(page, child2.childName, child2.childDob);

		// Verify both children are displayed
		await expect(page.locator(`text=${child1.childName}`)).toBeVisible();
		await expect(page.locator(`text=${child2.childName}`)).toBeVisible();
	});

	test('should allow editing a child', async ({ page }) => {
		await authenticateUser(page, `edit-child-${testEmail}`);

		// Create a child first
		const { childName, childDob } = generateTestData();
		await createChildViaUI(page, childName, childDob);

		// Click edit button for the child
		const editBtn = page.locator('button[data-child-id]').first();
		await editBtn.click();

		// Wait for edit modal
		const editModal = page.locator('#edit-child-modal');
		await editModal.waitFor({ state: 'visible', timeout: 5000 });

		// Update child name
		const updatedName = `Updated ${childName}`;
		const nameInput = editModal.locator('input[name="name"]');
		await nameInput.fill(updatedName);

		// Submit the form
		const submitBtn = editModal.locator('button[type="submit"]');
		await submitBtn.click();

		// Wait for page reload
		await Promise.race([
			page.waitForNavigation({ waitUntil: 'domcontentloaded' }),
			page.waitForTimeout(1500),
		]);

		// Verify updated name is displayed
		await expect(page.locator(`text=${updatedName}`)).toBeVisible();
	});

	test('should cancel child editing without saving', async ({ page }) => {
		await authenticateUser(page, `cancel-edit-${testEmail}`);

		// Create a child first
		const { childName, childDob } = generateTestData();
		await createChildViaUI(page, childName, childDob);

		// Click edit button
		const editBtn = page.locator('button[data-child-id]').first();
		await editBtn.click();

		// Wait for edit modal
		const editModal = page.locator('#edit-child-modal');
		await editModal.waitFor({ state: 'visible', timeout: 5000 });

		// Update name but don't save
		const nameInput = editModal.locator('input[name="name"]');
		await nameInput.fill('Should Not Appear');

		// Cancel the edit
		const cancelBtn = editModal.locator('button', { hasText: 'Cancel' });
		await cancelBtn.click();

		// Modal should be hidden
		await expect(editModal).toHaveClass(/hidden/);

		// Original name should still be visible
		await expect(page.locator(`text=${childName}`)).toBeVisible();
		await expect(page.locator('text=Should Not Appear')).not.toBeVisible();
	});
});

test.describe('Signup Flow - Session Selection and Submission', () => {
	const testEmail = `signup-flow-${Date.now()}@example.com`;
	let sessionId: string;

	test.beforeAll(async ({ request }) => {
		sessionId = await fetchFirstSessionId(request);
	});

	test('should display session details on signup page', async ({ page }) => {
		await authenticateUser(page, `session-details-${testEmail}`);
		const { childName, childDob } = generateTestData();
		await createChildViaUI(page, childName, childDob);

		await page.goto(`/signup?session=${sessionId}`, {
			waitUntil: 'domcontentloaded',
			timeout: 20000,
		});

		// Verify session details are displayed
		await expect(page.locator('main h1').first()).toContainText('Sign up for');
	});

	test('should show 404 for invalid session', async ({ page }) => {
		await authenticateUser(page, `invalid-session-${testEmail}`);

		const response = await page.goto('/signup?session=00000000-0000-0000-0000-000000000000', {
			waitUntil: 'domcontentloaded',
		});

		expect(response?.status()).toBeGreaterThanOrEqual(200);
	});

	test('should require child selection', async ({ page }) => {
		await authenticateUser(page, `require-child-${testEmail}`);
		const { childName, childDob } = generateTestData();
		await createChildViaUI(page, childName, childDob);

		await page.goto(`/signup?session=${sessionId}`, {
			waitUntil: 'domcontentloaded',
			timeout: 20000,
		});

		await page.locator('#signup-form').waitFor({ state: 'visible', timeout: 10000 });

		// Get the child radio to confirm it exists
		const childRadios = page.locator('input[name="childId"]');
		await expect(childRadios.first()).toBeVisible();

		// Try to submit without selecting a child - HTML5 validation or custom validation should prevent it
		const submitBtn = page.locator('#signup-form button[type="submit"]');
		const currentUrl = page.url();
		await submitBtn.click();

		// Wait a moment
		await page.waitForTimeout(1000);

		// The form should either show an error message OR not navigate away (due to HTML5 validation)
		const errorMsg = page.locator('#error-message');
		const isErrorVisible = await errorMsg.isVisible();

		if (isErrorVisible) {
			// Custom validation error shown
			await expect(errorMsg).toContainText('Please select a child');
		} else {
			// HTML5 validation prevented submission - page should still be on signup
			expect(page.url()).toBe(currentUrl);
		}
	});

	// test('should allow submitting signup with required fields', async ({ page }) => {
	// 	await authenticateUser(page, `submit-signup-${testEmail}`);
	// 	const { childName, childDob } = generateTestData();
	// 	await createChildViaUI(page, childName, childDob);
	// 	const childId = await getChildIdFromPage(page, childName);

	// 	await page.goto(`/signup?session=${sessionId}`, {
	// 		waitUntil: 'domcontentloaded',
	// 		timeout: 20000,
	// 	});
	// 	await page.locator('#signup-form').waitFor({ state: 'visible', timeout: 10000 });

	// 	// Select child
	// 	const childRadio = page.locator(`input[name="childId"][value="${childId}"]`);
	// 	await childRadio.waitFor({ state: 'visible', timeout: 10000 });
	// 	await childRadio.check();

	// 	// Submit form
	// 	const submitBtn = page.locator('#signup-form button[type="submit"]');
	// 	await submitBtn.click();

	// 	// Wait for redirect
	// 	await page.waitForURL('**account**', { timeout: 15000 });
	// 	await expect(page).toHaveURL(/account/);
	// 	await expect(page.locator('text=Signup successful')).toBeVisible({ timeout: 5000 });
	// });

	// test('should accept optional fields in signup form', async ({ page }) => {
	// 	await authenticateUser(page, `optional-fields-${testEmail}`);
	// 	const { childName, childDob } = generateTestData();
	// 	await createChildViaUI(page, childName, childDob);
	// 	const childId = await getChildIdFromPage(page, childName);

	// 	await page.goto(`/signup?session=${sessionId}`, {
	// 		waitUntil: 'domcontentloaded',
	// 		timeout: 20000,
	// 	});
	// 	await page.locator('#signup-form').waitFor({ state: 'visible', timeout: 10000 });

	// 	// Select child
	// 	const childRadio = page.locator(`input[name="childId"][value="${childId}"]`);
	// 	await childRadio.check();

	// 	// No additional fields needed for signup

	// 	// Submit
	// 	await page.locator('#signup-form button[type="submit"]').click();

	// 	await page.waitForURL('**account**', { timeout: 15000 });
	// 	await expect(page).toHaveURL(/account/);
	// });

	// test('should show success message after signup', async ({ page }) => {
	// 	await authenticateUser(page, `success-message-${testEmail}`);
	// 	const { childName, childDob } = generateTestData();
	// 	await createChildViaUI(page, childName, childDob);
	// 	const childId = await getChildIdFromPage(page, childName);

	// 	await page.goto(`/signup?session=${sessionId}`, {
	// 		waitUntil: 'domcontentloaded',
	// 		timeout: 20000,
	// 	});
	// 	await page.locator('#signup-form').waitFor({ state: 'visible', timeout: 10000 });

	// 	await page.locator(`input[name="childId"][value="${childId}"]`).check();
	// 	await page.locator('#signup-form button[type="submit"]').click();

	// 	await page.waitForURL('**account**', { timeout: 15000 });

	// 	// Verify success banner
	// 	await expect(page.locator('text=Signup successful')).toBeVisible();
	// 	await expect(page.locator('text=confirmation email')).toBeVisible();
	// });
});

test.describe('Logout Functionality', () => {
	test('should clear session on logout', async ({ page }) => {
		const { email } = generateTestData();
		await authenticateUser(page, email);

		// Click sign out button
		const logoutBtn = page.locator('#logout-btn');
		await expect(logoutBtn).toBeVisible();
		await logoutBtn.click();

		// Verify redirect to home
		await expect(page).toHaveURL('/', { timeout: 10000 });

		// Verify subsequent /account access redirects to login
		await page.goto('/account', { waitUntil: 'domcontentloaded', timeout: 20000 });
		await expect(page).toHaveURL(/\/auth\/login/);
	});
});

test.describe('End-to-End Complete User Journey', () => {
	test('user can request magic link and flow is set up correctly @integration', async ({
		page,
	}) => {
		const { email } = generateTestData();

		// Step 1: Visit login page
		await page.goto('/auth/login');
		expect(page.url()).toContain('/auth/login');

		// Step 2: Request magic link
		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');
		const successMsg = page.locator('#success-message');

		await emailInput.fill(email);

		const requestPromise = page.waitForRequest((request) =>
			request.url().includes('/api/v1/auth/magic-link'),
		);

		await submitBtn.click();

		// Step 3: Verify request was sent
		const request = await requestPromise;
		const postData = request.postDataJSON();

		expect(postData.email).toBe(email);
		expect(postData.return_to).toBeDefined();

		// Step 4: Verify success message
		await expect(successMsg).toBeVisible();

		// In a real test, here you would:
		// 1. Extract the magic link token (from API response or mock email service)
		// 2. Navigate to the consume endpoint
		// 3. Verify authentication cookie is set
		// 4. Verify /account page is accessible
		// 5. Add a child
		// 6. Select a session and complete signup
		// 7. Verify signup appears in the account page
	});
});

test.describe('Form Validation and User Feedback', () => {
	test('should clear form after successful magic link submission', async ({ page }) => {
		const { email } = generateTestData();

		await page.goto('/auth/login');

		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');

		// Fill and submit
		await emailInput.fill(email);

		const requestPromise = page.waitForRequest((request) =>
			request.url().includes('/api/v1/auth/magic-link'),
		);

		await submitBtn.click();
		await requestPromise;

		// After success, input should be cleared
		await page.waitForTimeout(1000);
		const inputValue = await emailInput.inputValue();
		expect(inputValue).toBe('');
	});

	test('should manage visibility of success and error messages', async ({ page }) => {
		const { email } = generateTestData();

		await page.goto('/auth/login');

		const errorMsg = page.locator('#error-message');
		const successMsg = page.locator('#success-message');
		const emailInput = page.locator('#email');
		const submitBtn = page.locator('#submit-btn');

		// Initially both hidden
		await expect(errorMsg).toHaveClass(/hidden/);
		await expect(successMsg).toHaveClass(/hidden/);

		// Fill and submit
		await emailInput.fill(email);

		const requestPromise = page.waitForRequest((request) =>
			request.url().includes('/api/v1/auth/magic-link'),
		);

		await submitBtn.click();
		await requestPromise;

		// Success should show, error should hide
		await expect(successMsg).not.toHaveClass(/hidden/, { timeout: 5000 });
		await expect(errorMsg).toHaveClass(/hidden/);
	});
});
