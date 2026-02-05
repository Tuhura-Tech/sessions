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

test.describe('Pagination and Validation', () => {
	let pageErrors: string[] = [];

	test.beforeEach(async ({ page }) => {
		pageErrors = trackPageErrors(page);
		await authenticateAsAdmin(page);
		await ensureAuthenticated(page);
	});

	test.afterEach(async () => {
		// Filter out expected errors
		const relevantErrors = pageErrors.filter(
			(error) => !error.includes('Failed to load calendar data'),
		);
		expect(relevantErrors).toEqual([]);
	});

	test.describe('Sessions Pagination', () => {
		test('should support pagination via API', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Test default pagination (should return up to 100 items)
			const defaultRes = await page.request.get(`${ADMIN_API_BASE_URL}/admin/sessions`, {
				headers,
			});
			expect(defaultRes.ok()).toBeTruthy();
			const defaultData = await defaultRes.json();
			expect(defaultData).toHaveProperty('items');
			expect(defaultData).toHaveProperty('total');
			expect(Array.isArray(defaultData.items)).toBeTruthy();

			// Test with limit parameter
			const limitRes = await page.request.get(`${ADMIN_API_BASE_URL}/admin/sessions?limit=5`, {
				headers,
			});
			expect(limitRes.ok()).toBeTruthy();
			const limitData = await limitRes.json();
			expect(limitData.items.length).toBeLessThanOrEqual(5);

			// Test with offset parameter
			if (limitData.total > 5) {
				const offsetRes = await page.request.get(
					`${ADMIN_API_BASE_URL}/admin/sessions?limit=5&offset=5`,
					{ headers },
				);
				expect(offsetRes.ok()).toBeTruthy();
				const offsetData = await offsetRes.json();
				expect(offsetData.items.length).toBeGreaterThan(0);
				// Items should be different from first page
				if (limitData.items.length > 0 && offsetData.items.length > 0) {
					expect(limitData.items[0].id).not.toBe(offsetData.items[0].id);
				}
			}

			// Test limit=0 edge case
			const zeroLimitRes = await page.request.get(
				`${ADMIN_API_BASE_URL}/admin/sessions?limit=0`,
				{ headers },
			);
			expect(zeroLimitRes.ok()).toBeTruthy();
			const zeroLimitData = await zeroLimitRes.json();
			expect(zeroLimitData.items).toHaveLength(0);
		});

		test('should support pagination for students endpoint', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Test students pagination
			const studentsRes = await page.request.get(
				`${ADMIN_API_BASE_URL}/admin/students?limit=10&offset=0`,
				{ headers },
			);
			expect(studentsRes.ok()).toBeTruthy();
			const studentsData = await studentsRes.json();
			expect(studentsData).toHaveProperty('items');
			expect(studentsData).toHaveProperty('total');
			expect(studentsData.items.length).toBeLessThanOrEqual(10);
		});

		test('should support pagination for locations endpoint', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Test locations pagination
			const locationsRes = await page.request.get(
				`${ADMIN_API_BASE_URL}/admin/locations?limit=10&offset=0`,
				{ headers },
			);
			expect(locationsRes.ok()).toBeTruthy();
			const locationsData = await locationsRes.json();
			expect(locationsData).toHaveProperty('items');
			expect(locationsData).toHaveProperty('total');
			expect(locationsData.items.length).toBeLessThanOrEqual(10);
		});

		test('should support pagination for caregivers endpoint', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Test caregivers pagination
			const caregiversRes = await page.request.get(
				`${ADMIN_API_BASE_URL}/admin/caregivers?limit=10&offset=0`,
				{ headers },
			);
			expect(caregiversRes.ok()).toBeTruthy();
			const caregiversData = await caregiversRes.json();
			expect(caregiversData).toHaveProperty('items');
			expect(caregiversData).toHaveProperty('total');
			expect(caregiversData.items.length).toBeLessThanOrEqual(10);
		});

		test('should support pagination for blocks endpoint', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Test blocks pagination
			const blocksRes = await page.request.get(
				`${ADMIN_API_BASE_URL}/admin/blocks?limit=10&offset=0`,
				{ headers },
			);
			expect(blocksRes.ok()).toBeTruthy();
			const blocksData = await blocksRes.json();
			expect(blocksData).toHaveProperty('items');
			expect(blocksData).toHaveProperty('total');
			expect(blocksData.items.length).toBeLessThanOrEqual(10);
		});
	});

	test.describe('Form Validation', () => {
		test('should validate session creation form', async ({ page }) => {
			await navigateTo(page, '/sessions/create');
			await waitForAuthReady(page);
			await waitForApiCalls(page);

			// Try to submit empty form (should show validation errors)
			const submitButton = page.getByRole('button', { name: /create session|save|submit/i });
			if (await submitButton.isVisible()) {
				await submitButton.click();

				// Wait for validation messages
				await page.waitForTimeout(500);

				// Should have validation errors for required fields
				const errors = page.locator('[role="alert"], .error, .text-red-500, .text-red-600');
				const errorCount = await errors.count();
				
				// Expect at least some validation errors for required fields
				// (name, location, capacity, etc.)
				expect(errorCount).toBeGreaterThan(0);
			}
		});

		test('should validate location creation form', async ({ page }) => {
			await navigateTo(page, '/locations');
			await waitForAuthReady(page);
			await waitForApiCalls(page);

			// Look for "Add Location" or "Create" button
			const createButton = page.getByRole('button', { name: /add location|new location|create/i });
			const hasCreateButton = await createButton.count() > 0;

			if (hasCreateButton) {
				await createButton.first().click();
				await page.waitForTimeout(300);

				// Try to submit with empty required fields
				const submitButton = page.getByRole('button', { name: /save|create|submit/i });
				if (await submitButton.isVisible()) {
					await submitButton.click();
					await page.waitForTimeout(500);

					// Should show validation for required fields (name, address, contact_name, contact_email)
					const errors = page.locator('[role="alert"], .error, .text-red-500, .text-red-600');
					const errorCount = await errors.count();
					expect(errorCount).toBeGreaterThan(0);
				}
			}
		});

		test('should validate student data', async ({ page }) => {
			await navigateTo(page, '/students');
			await waitForAuthReady(page);
			await waitForApiCalls(page);

			// Page should load successfully
			await expect(page.locator('header h1, h1, h2')).toBeVisible();

			// Check if student data displays properly
			const table = page.locator('table');
			if (await table.count() > 0) {
				const rows = page.locator('table tbody tr');
				const rowCount = await rows.count();
				
				if (rowCount > 0) {
					// First row should have valid data
					const firstRow = rows.first();
					const rowText = await firstRow.innerText();
					expect(rowText.length).toBeGreaterThan(0);
					
					// Should have student name
					expect(rowText).not.toBe('undefined');
					expect(rowText).not.toBe('null');
				}
			}
		});

		test('should validate required fields in session form', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Try to create session with missing required fields
			const invalidSession = {
				name: '', // Empty name - should fail
				year: 2026,
			};

			const response = await page.request.post(`${ADMIN_API_BASE_URL}/admin/sessions`, {
				headers,
				data: invalidSession,
			});

			// Should return validation error (422 or 400)
			expect([400, 422]).toContain(response.status());
		});

		test('should validate required fields in location form', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Try to create location with missing required fields
			const invalidLocation = {
				name: 'Test Location',
				// Missing address, region, lat, lng, contact_name, contact_email
			};

			const response = await page.request.post(`${ADMIN_API_BASE_URL}/admin/locations`, {
				headers,
				data: invalidLocation,
			});

			// Should return validation error
			expect([400, 422]).toContain(response.status());
		});
	});

	test.describe('Error Handling', () => {
		test('should handle 404 errors gracefully', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Request non-existent session
			const nonExistentId = '00000000-0000-0000-0000-000000000000';
			const response = await page.request.get(
				`${ADMIN_API_BASE_URL}/admin/sessions/${nonExistentId}`,
				{ headers },
			);

			expect(response.status()).toBe(404);
		});

		test('should handle invalid pagination parameters', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Test negative limit (should handle gracefully or return error)
			const negativeLimitRes = await page.request.get(
				`${ADMIN_API_BASE_URL}/admin/sessions?limit=-1`,
				{ headers },
			);
			// Should either handle gracefully (200) or return validation error (400/422)
			expect([200, 400, 422]).toContain(negativeLimitRes.status());

			// Test negative offset
			const negativeOffsetRes = await page.request.get(
				`${ADMIN_API_BASE_URL}/admin/sessions?offset=-1`,
				{ headers },
			);
			expect([200, 400, 422]).toContain(negativeOffsetRes.status());
		});

		test('should validate session capacity is positive', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Get a location first
			const locationsRes = await page.request.get(`${ADMIN_API_BASE_URL}/admin/locations`, {
				headers,
			});
			const locationsData = await locationsRes.json();
			const locations = unwrapListResponse<any>(locationsData);

			if (locations.length === 0) {
				return; // Skip if no locations
			}

			// Try to create session with zero or negative capacity
			const invalidSession = {
				name: 'Test Invalid Capacity',
				locationId: locations[0].id,
				year: 2026,
				sessionType: 'term',
				ageLower: 8,
				ageUpper: 12,
				dayOfWeek: 1,
				startTime: '14:00:00',
				endTime: '16:00:00',
				capacity: 0, // Invalid capacity
			};

			const response = await page.request.post(`${ADMIN_API_BASE_URL}/admin/sessions`, {
				headers,
				data: invalidSession,
			});

			// Should return validation error
			expect([400, 422]).toContain(response.status());
		});

		test('should validate email format in location contact', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Try to create location with invalid email
			const invalidLocation = {
				name: 'Test Location',
				address: '123 Test St',
				region: 'Test Region',
				lat: -36.8485,
				lng: 174.7633,
				contactName: 'Test Contact',
				contactEmail: 'not-an-email', // Invalid email
			};

			const response = await page.request.post(`${ADMIN_API_BASE_URL}/admin/locations`, {
				headers,
				data: invalidLocation,
			});

			// Should return validation error
			expect([400, 422]).toContain(response.status());
		});
	});

	test.describe('Data Integrity', () => {
		test('should maintain data consistency with pagination', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Get all sessions with pagination
			const page1Res = await page.request.get(
				`${ADMIN_API_BASE_URL}/admin/sessions?limit=10&offset=0`,
				{ headers },
			);
			const page1Data = await page1Res.json();

			if (page1Data.total > 10) {
				const page2Res = await page.request.get(
					`${ADMIN_API_BASE_URL}/admin/sessions?limit=10&offset=10`,
					{ headers },
				);
				const page2Data = await page2Res.json();

				// Total should be consistent across pages
				expect(page1Data.total).toBe(page2Data.total);

				// Items should not overlap
				const page1Ids = page1Data.items.map((item: any) => item.id);
				const page2Ids = page2Data.items.map((item: any) => item.id);
				const intersection = page1Ids.filter((id: string) => page2Ids.includes(id));
				expect(intersection).toHaveLength(0);
			}
		});

		test('should return consistent total count', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Make multiple requests
			const res1 = await page.request.get(`${ADMIN_API_BASE_URL}/admin/students`, { headers });
			const data1 = await res1.json();

			const res2 = await page.request.get(`${ADMIN_API_BASE_URL}/admin/students?limit=5`, {
				headers,
			});
			const data2 = await res2.json();

			// Total count should be the same regardless of limit/offset
			expect(data1.total).toBe(data2.total);
		});

		test('should validate session occurrences load correctly', async ({ page }) => {
			const headers = getAdminAuthHeaders();

			// Get sessions
			const sessionsRes = await page.request.get(`${ADMIN_API_BASE_URL}/admin/sessions`, {
				headers,
			});
			const sessionsData = await sessionsRes.json();
			const sessions = unwrapListResponse<any>(sessionsData);

			if (sessions.length === 0) {
				return; // Skip if no sessions
			}

			// Get occurrences for first session
			const sessionId = sessions[0].id;
			const occurrencesRes = await page.request.get(
				`${ADMIN_API_BASE_URL}/admin/sessions/${sessionId}/occurrences`,
				{ headers },
			);

			expect(occurrencesRes.ok()).toBeTruthy();
			const occurrencesData = await occurrencesRes.json();
			expect(occurrencesData).toHaveProperty('items');
			expect(Array.isArray(occurrencesData.items)).toBeTruthy();

			// Each occurrence should have required fields
			if (occurrencesData.items.length > 0) {
				const firstOccurrence = occurrencesData.items[0];
				expect(firstOccurrence).toHaveProperty('id');
				expect(firstOccurrence).toHaveProperty('date');
				expect(firstOccurrence).toHaveProperty('sessionId');
			}
		});
	});

	test.describe('UI State Management', () => {
		test('should display loading states correctly', async ({ page }) => {
			await navigateTo(page, '/sessions');

			// Page should eventually show content (not stuck in loading)
			await page.waitForTimeout(5000); // Wait max 5 seconds
			
			// Should have either content or an empty state
			const hasTable = (await page.locator('table').count()) > 0;
			const hasEmptyState = (await page.locator('text=No sessions').count()) > 0;
			expect(hasTable || hasEmptyState).toBeTruthy();
		});

		test('should handle navigation between pages', async ({ page }) => {
			// Navigate through different pages
			await navigateTo(page, '/sessions');
			await waitForAuthReady(page);
			await waitForApiCalls(page);
			await expect(page.locator('header h1, h1')).toBeVisible();

			await navigateTo(page, '/locations');
			await waitForAuthReady(page);
			await waitForApiCalls(page);
			await expect(page.locator('header h1, h1')).toBeVisible();

			await navigateTo(page, '/students');
			await waitForAuthReady(page);
			await waitForApiCalls(page);
			await expect(page.locator('header h1, h1')).toBeVisible();

			// No console errors should occur during navigation
			const criticalErrors = pageErrors.filter(
				(error) =>
					!error.includes('calendar') &&
					!error.includes('Failed to load') &&
					error.includes('Error'),
			);
			expect(criticalErrors).toHaveLength(0);
		});
	});
});
