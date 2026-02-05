import { expect, test } from '@playwright/test';

// Get API base URL from environment or use defaults
const API_BASE_URL = process.env.PUBLIC_BASE_URL || 'http://localhost:8000';
const FRONTEND_BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:4321';

test('Simple authentication test', async ({ page, context }) => {
	console.log('🔵 Starting simple auth test');

	// Step 1: Navigate to frontend
	// console.log('🟢 Navigating to frontend...');
	await page.goto(`${FRONTEND_BASE_URL}/`, { waitUntil: 'domcontentloaded' });
	// console.log('✅ Frontend loaded');

	const response = await page.request.post(`${API_BASE_URL}/api/v1/auth/magic-link`, {
		headers: { 'Content-Type': 'application/json' },
		data: { email: 'test@example.com', return_to: '/account' },
	});

	const data = await response.json();
	const token = data.debugToken ?? data.debug_token;
	expect(token).toBeDefined();

	const consumeResponse = await page.request.get(
		`${API_BASE_URL}/api/v1/auth/magic-link/consume?token=${token}&returnTo=/account`,
	);
	const setCookie = consumeResponse.headers()['set-cookie'];
	const sessionCookie = setCookie?.split(';')[0];
	const [cookieName, cookieValue] = sessionCookie ? sessionCookie.split('=') : [];
	if (cookieName && cookieValue) {
		await context.addCookies([
			{
				name: cookieName,
				value: cookieValue,
				url: FRONTEND_BASE_URL,
			},
		]);
	}

	await page.goto('/account', { waitUntil: 'load', timeout: 10000 });

	// Step 4: Check where we ended up
	// console.log('🟢 Checking current URL...');
	const currentUrl = page.url();
	// console.log('Current URL:', currentUrl);

	// Step 5: Check cookies
	// console.log('🟢 Checking cookies...');
	await context.cookies();
	// console.log('Cookies:', cookies);

	// Step 6: Try to access the account page
	// console.log('🟢 Trying to access account page...');
	if (currentUrl.includes('login')) {
		// console.log('❌ Still on login page, authentication failed');
		throw new Error('Authentication failed - still on login page');
	}

	// console.log('✅ Authentication successful');
});
