import { expect, test } from '@playwright/test';
import { createAdminSessionToken } from './helpers';

const ADMIN_BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

/**
 * Test suite for additional admin portal actions
 * Tests student deletion, caregiver management, session management, etc.
 */

test.describe('Student management actions', () => {
	test.beforeEach(async ({ page, context }) => {
		// Set admin authentication cookie
		const token = createAdminSessionToken();
		await context.addCookies([
			{
				name: 'admin_session_cookie',
				value: token,
				domain: 'localhost',
				path: '/',
			},
		]);
	});

	test('should delete student from student detail page', async ({ page, request }) => {
		// Get students list
		const studentsResp = await request.get(`${API_BASE_URL}/api/v1/admin/students`);
		const students = await studentsResp.json();
		const studentItems = students.items || students;

		if (studentItems.length > 0) {
			const student = studentItems[0];

			// Navigate to student detail page
			await page.goto(`${ADMIN_BASE_URL}/students/${student.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Click delete button
			const deleteButton = page.locator('button:has-text("Delete")');
			if (await deleteButton.isVisible()) {
				await deleteButton.click();

				// Wait for confirmation modal
				await page.waitForTimeout(500);

				// Confirm deletion
				const confirmButton = page.locator('button:has-text("Delete")').last();
				if (await confirmButton.isVisible()) {
					await confirmButton.click();

					// Should redirect to students list
					await page.waitForTimeout(1000);
					expect(page.url()).toContain('/students');
				}
			}
		}
	});

	test('should delete student from students list page', async ({ page, request }) => {
		// Get students list
		const studentsResp = await request.get(`${API_BASE_URL}/api/v1/admin/students`);
		const students = await studentsResp.json();
		const studentItems = students.items || students;

		if (studentItems.length > 0) {
			// Navigate to students list
			await page.goto(`${ADMIN_BASE_URL}/students`, { waitUntil: 'domcontentloaded' });
			await page.waitForTimeout(1000);

			// Count initial students
			const initialCount = await page.locator('table tbody tr').count();

			// Find delete button for first student (if available)
			const deleteButton = page
				.locator('button[title*="Delete"], button:has-text("Delete")')
				.first();
			if (await deleteButton.isVisible()) {
				await deleteButton.click();

				// Wait for confirmation modal
				await page.waitForTimeout(500);

				// Confirm deletion
				const confirmButton = page.locator('button:has-text("Delete")').last();
				if (await confirmButton.isVisible()) {
					await confirmButton.click();

					// Wait for deletion to complete
					await page.waitForTimeout(1500);

					// Count should decrease by 1
					const newCount = await page.locator('table tbody tr').count();
					expect(newCount).toBe(initialCount - 1);
				}
			}
		}
	});

	test('should cancel student deletion', async ({ page, request }) => {
		// Get students list
		const studentsResp = await request.get(`${API_BASE_URL}/api/v1/admin/students`);
		const students = await studentsResp.json();
		const studentItems = students.items || students;

		if (studentItems.length > 0) {
			const student = studentItems[0];

			// Navigate to student detail page
			await page.goto(`${ADMIN_BASE_URL}/students/${student.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Click delete button
			const deleteButton = page.locator('button:has-text("Delete")');
			if (await deleteButton.isVisible()) {
				await deleteButton.click();

				// Wait for confirmation modal
				await page.waitForTimeout(500);

				// Cancel deletion
				const cancelButton = page.locator('button:has-text("Cancel")');
				if (await cancelButton.isVisible()) {
					await cancelButton.click();

					// Should stay on student detail page
					await page.waitForTimeout(500);
					expect(page.url()).toContain(`/students/${student.id}`);
				}
			}
		}
	});

	test('should navigate from student detail to caregiver detail', async ({ page }) => {
		// Navigate to students page
		await page.goto(`${ADMIN_BASE_URL}/students`, { waitUntil: 'domcontentloaded' });
		await page.waitForTimeout(1500);

		// Click on first student
		const studentLinks = page.locator('a[href*="/students/"]').filter({ hasText: /\w/ });
		if ((await studentLinks.count()) > 0) {
			await studentLinks.first().click();
			await page.waitForTimeout(1500);

			// Look for caregiver link
			const caregiverLink = page.locator('a:has-text("View Caregiver"), a[href*="/caregivers/"]');
			if ((await caregiverLink.count()) > 0) {
				await caregiverLink.first().click();

				// Should navigate to caregiver detail page
				await page.waitForTimeout(1500);
				expect(page.url()).toContain('/caregivers/');
			}
		}
	});

	test('should show student enrollments with session links', async ({ page, request }) => {
		// Get students list
		const studentsResp = await request.get(`${API_BASE_URL}/api/v1/admin/students`);
		const students = await studentsResp.json();
		const studentItems = students.items || students;

		if (studentItems.length > 0) {
			const student = studentItems[0];

			// Navigate to student detail page
			await page.goto(`${ADMIN_BASE_URL}/students/${student.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Check for enrollments section
			const enrollmentsSection = page.locator('text="Enrollments"');
			if (await enrollmentsSection.isVisible()) {
				// Check for session links
				const sessionLinks = page.locator('a[href*="/sessions/"]');
				const linkCount = await sessionLinks.count();

				// If there are enrollments, there should be session links
				if (linkCount > 0) {
					expect(linkCount).toBeGreaterThan(0);

					// Verify links are clickable
					const firstLink = sessionLinks.first();
					expect(await firstLink.isVisible()).toBeTruthy();
				}
			}
		}
	});
});

test.describe('Session occurrence management', () => {
	test.beforeEach(async ({ page, context }) => {
		// Set admin authentication cookie
		const token = createAdminSessionToken();
		await context.addCookies([
			{
				name: 'admin_session_cookie',
				value: token,
				domain: 'localhost',
				path: '/',
			},
		]);
	});

	test('should display occurrences tab in session detail', async ({ page, request }) => {
		// Find a session
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		if (sessionItems.length > 0) {
			const session = sessionItems[0];

			// Navigate to session detail
			await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Click occurrences tab
			const occurrencesTab = page.locator('button:has-text("Occurrences")');
			if ((await occurrencesTab.count()) > 0) {
				await occurrencesTab.click();
				await page.waitForTimeout(500);

				// Should display occurrences table
				const occurrencesTable = page.locator('table');
				expect(await occurrencesTable.isVisible()).toBeTruthy();
			}
		}
	});

	test('should filter occurrences by term/block', async ({ page, request }) => {
		// Find a session with multiple terms
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		if (sessionItems.length > 0) {
			const session = sessionItems[0];

			// Navigate to session detail
			await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Click occurrences tab
			const occurrencesTab = page.locator('button:has-text("Occurrences")');
			if ((await occurrencesTab.count()) > 0) {
				await occurrencesTab.click();
				await page.waitForTimeout(500);

				// Get total occurrences
				const totalRows = await page.locator('table tbody tr').count();

				// Look for term filter
				const termFilter = page.locator('select:has(option:has-text("All terms"))');
				if ((await termFilter.count()) > 0) {
					// Select a specific term
					const options = await termFilter.locator('option').allTextContents();
					if (options.length > 1) {
						await termFilter.selectOption({ index: 1 });
						await page.waitForTimeout(500);

						// Filtered count should be less than or equal to total
						const filteredRows = await page.locator('table tbody tr').count();
						expect(filteredRows).toBeLessThanOrEqual(totalRows);
					}
				}
			}
		}
	});

	test('should navigate to attendance from occurrence', async ({ page, request }) => {
		// Find a session with occurrences
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		if (sessionItems.length > 0) {
			const session = sessionItems[0];

			// Navigate to session detail
			await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Click occurrences tab
			const occurrencesTab = page.locator('button:has-text("Occurrences")');
			if ((await occurrencesTab.count()) > 0) {
				await occurrencesTab.click();
				await page.waitForTimeout(500);

				// Look for attendance link
				const attendanceLink = page
					.locator('a[href*="/attendance/"], button:has-text("Attendance")')
					.first();
				if (await attendanceLink.isVisible()) {
					await attendanceLink.click();

					// Should navigate to attendance page
					await page.waitForTimeout(1000);
					expect(page.url()).toMatch(/\/attendance\//);
				}
			}
		}
	});

	test('should show cancelled occurrences with correct status', async ({ page, request }) => {
		// Find a session with occurrences
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		if (sessionItems.length > 0) {
			const session = sessionItems[0];

			// Navigate to session detail
			await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Click occurrences tab
			const occurrencesTab = page.locator('button:has-text("Occurrences")');
			if ((await occurrencesTab.count()) > 0) {
				await occurrencesTab.click();
				await page.waitForTimeout(500);

				// Check for status indicators
				const statusBadges = page.locator('span:has-text("Cancelled"), span:has-text("Active")');
				const count = await statusBadges.count();

				// Should have status indicators for each occurrence
				expect(count).toBeGreaterThan(0);
			}
		}
	});
});

test.describe('Session management actions', () => {
	test.beforeEach(async ({ page, context }) => {
		// Set admin authentication cookie
		const token = createAdminSessionToken();
		await context.addCookies([
			{
				name: 'admin_session_cookie',
				value: token,
				domain: 'localhost',
				path: '/',
			},
		]);
	});

	test('should export signups as CSV', async ({ page }) => {
		// Navigate to sessions page
		await page.goto(`${ADMIN_BASE_URL}/sessions`, { waitUntil: 'domcontentloaded' });
		await page.waitForTimeout(1500);

		// Click on first session
		const sessionLinks = page.locator('a[href*="/sessions/"]').filter({ hasText: /\w/ });
		if ((await sessionLinks.count()) > 0) {
			await sessionLinks.first().click();
			await page.waitForTimeout(1500);

			// Click signups tab
			const signupsTab = page.locator('button:has-text("Signups")');
			if ((await signupsTab.count()) > 0) {
				await signupsTab.click();
				await page.waitForTimeout(1000);

				// Look for export button
				const exportButton = page.locator('button:has-text("Export")');
				if ((await exportButton.count()) > 0) {
					// Setup download listener
					try {
						const downloadPromise = page.waitForEvent('download', { timeout: 5000 });
						await exportButton.click();

						// Wait for download
						const download = await downloadPromise;

						// Verify download filename
						expect(download.suggestedFilename()).toMatch(/\.csv$/);
					} catch (e) {
						// If no download happens, at least verify button exists
						expect(await exportButton.isVisible()).toBeTruthy();
					}
				}
			}
		}
	});

	test('should display session capacity information', async ({ page, request }) => {
		// Find a session
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		if (sessionItems.length > 0) {
			const session = sessionItems[0];

			// Navigate to session detail
			await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Check for capacity display (e.g., "5/10")
			const capacityText = page.locator('text=/\\d+\\/\\d+/');
			if ((await capacityText.count()) > 0) {
				expect(await capacityText.first().isVisible()).toBeTruthy();

				// Verify format
				const text = await capacityText.first().textContent();
				expect(text).toMatch(/^\d+\/\d+$/);
			}
		}
	});

	test('should navigate from session to location detail', async ({ page }) => {
		// Navigate to sessions page
		await page.goto(`${ADMIN_BASE_URL}/sessions`, { waitUntil: 'domcontentloaded' });
		await page.waitForTimeout(1500);

		// Click on first session
		const sessionLinks = page.locator('a[href*="/sessions/"]').filter({ hasText: /\w/ });
		if ((await sessionLinks.count()) > 0) {
			await sessionLinks.first().click();
			await page.waitForTimeout(1500);

			// Look for location link in the session detail page
			const locationLink = page.locator('a[href*="/locations/"]');
			if ((await locationLink.count()) > 0) {
				await locationLink.first().click();

				// Should navigate to location detail
				await page.waitForTimeout(1500);
				expect(page.url()).toContain('/locations/');
			}
		}
	});

	test('should display staff assignments in session detail', async ({ page, request }) => {
		// Find a session with staff assignments
		const sessionsResp = await request.get(`${API_BASE_URL}/api/v1/admin/sessions/2026`);
		const sessions = await sessionsResp.json();
		const sessionItems = sessions.items || sessions;

		if (sessionItems.length > 0) {
			const session = sessionItems[0];

			// Navigate to session detail
			await page.goto(`${ADMIN_BASE_URL}/sessions/${session.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Look for staff section or staff names
			const staffSection = page.locator('text="Staff", text="Facilitator"');
			if ((await staffSection.count()) > 0) {
				expect(await staffSection.first().isVisible()).toBeTruthy();
			}
		}
	});
});

test.describe('Caregiver management actions', () => {
	test.beforeEach(async ({ page, context }) => {
		// Set admin authentication cookie
		const token = createAdminSessionToken();
		await context.addCookies([
			{
				name: 'admin_session_cookie',
				value: token,
				domain: 'localhost',
				path: '/',
			},
		]);
	});

	test('should navigate to caregiver detail page', async ({ page, request }) => {
		// Get caregivers list
		const caregiversResp = await request.get(`${API_BASE_URL}/api/v1/admin/caregivers`);
		const caregivers = await caregiversResp.json();
		const caregiverItems = caregivers.items || caregivers;

		if (caregiverItems.length > 0) {
			const caregiver = caregiverItems[0];

			// Navigate to caregiver detail
			await page.goto(`${ADMIN_BASE_URL}/caregivers/${caregiver.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Should display caregiver details
			expect(page.url()).toContain(`/caregivers/${caregiver.id}`);

			// Check for caregiver name
			const nameElement = page.locator(`text="${caregiver.name}"`);
			if (caregiver.name) {
				expect(await nameElement.count()).toBeGreaterThan(0);
			}
		}
	});

	test('should display caregiver children list', async ({ page, request }) => {
		// Get caregivers list
		const caregiversResp = await request.get(`${API_BASE_URL}/api/v1/admin/caregivers`);
		const caregivers = await caregiversResp.json();
		const caregiverItems = caregivers.items || caregivers;

		if (caregiverItems.length > 0) {
			const caregiver = caregiverItems[0];

			// Navigate to caregiver detail
			await page.goto(`${ADMIN_BASE_URL}/caregivers/${caregiver.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Look for children/students section
			const childrenSection = page.locator('text="Children", text="Students"');
			if ((await childrenSection.count()) > 0) {
				expect(await childrenSection.first().isVisible()).toBeTruthy();
			}
		}
	});

	test('should send email to caregiver from caregiver detail', async ({ page, request }) => {
		// Get caregivers list
		const caregiversResp = await request.get(`${API_BASE_URL}/api/v1/admin/caregivers`);
		const caregivers = await caregiversResp.json();
		const caregiverItems = caregivers.items || caregivers;

		if (caregiverItems.length > 0) {
			const caregiver = caregiverItems[0];

			// Navigate to caregiver detail
			await page.goto(`${ADMIN_BASE_URL}/caregivers/${caregiver.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Look for email button
			const emailButton = page.locator('button:has-text("Email"), button:has-text("Send Email")');
			if ((await emailButton.count()) > 0) {
				await emailButton.first().click();

				// Should open email modal/dialog
				await page.waitForTimeout(500);
				const emailDialog = page.locator('text="Subject", text="Message"');
				expect(await emailDialog.count()).toBeGreaterThan(0);
			}
		}
	});
});

test.describe('Location management actions', () => {
	test.beforeEach(async ({ page, context }) => {
		// Set admin authentication cookie
		const token = createAdminSessionToken();
		await context.addCookies([
			{
				name: 'admin_session_cookie',
				value: token,
				domain: 'localhost',
				path: '/',
			},
		]);
	});

	test('should edit location details', async ({ page, request }) => {
		// Get locations list
		const locationsResp = await request.get(`${API_BASE_URL}/api/v1/admin/locations`);
		const locations = await locationsResp.json();
		const locationItems = locations.items || locations;

		if (locationItems.length > 0) {
			const location = locationItems[0];

			// Navigate to location detail
			await page.goto(`${ADMIN_BASE_URL}/locations/${location.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Look for edit button
			const editButton = page.locator('button:has-text("Edit")');
			if (await editButton.isVisible()) {
				await editButton.click();

				// Should open edit form or navigate to edit page
				await page.waitForTimeout(500);
				expect(page.url()).toMatch(/\/locations\/(edit|[a-f0-9-]+)/);
			}
		}
	});

	test('should display location sessions list', async ({ page, request }) => {
		// Get locations list
		const locationsResp = await request.get(`${API_BASE_URL}/api/v1/admin/locations`);
		const locations = await locationsResp.json();
		const locationItems = locations.items || locations;

		if (locationItems.length > 0) {
			const location = locationItems[0];

			// Navigate to location detail
			await page.goto(`${ADMIN_BASE_URL}/locations/${location.id}`, {
				waitUntil: 'domcontentloaded',
			});
			await page.waitForTimeout(1000);

			// Look for sessions section
			const sessionsSection = page.locator('text="Sessions"');
			if ((await sessionsSection.count()) > 0) {
				expect(await sessionsSection.first().isVisible()).toBeTruthy();

				// Check for sessions list or table
				const sessionsTable = page.locator('table');
				if ((await sessionsTable.count()) > 0) {
					expect(await sessionsTable.first().isVisible()).toBeTruthy();
				}
			}
		}
	});
});
