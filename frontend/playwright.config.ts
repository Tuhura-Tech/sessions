import { defineConfig, devices } from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
	testDir: './tests/e2e',
	globalSetup: './tests/e2e/global-setup.ts',
	/* Run tests in files in parallel */
	fullyParallel: true,
	/* Fail the build on CI if you accidentally left test.only in the source code. */
	forbidOnly: !!process.env.CI,
	/* Retry on CI only */
	retries: process.env.CI ? 2 : 0,
	/* Opt out of parallel tests on CI. */
	...(process.env.CI ? { workers: 1 } : {}),
	/* Reporter to use. See https://playwright.dev/docs/test-reporters */
	reporter: [['list'], ['html', { open: 'never' }]],
	/* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
	use: {
		/* Base URL to use in actions like `await page.goto('/')`. */
		baseURL:
			process.env.PLAYWRIGHT_BASE_URL ||
			(process.env.CI ? 'http://127.0.0.1:4321' : 'http://localhost:4321'),
		/* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
		trace: 'on-first-retry',
		screenshot: 'only-on-failure',
		video: 'retain-on-failure',
	},

	/* Configure projects for major browsers */
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] },
		},

		{
			name: 'firefox',
			use: { ...devices['Desktop Firefox'] },
		},

		{
			name: 'webkit',
			use: { ...devices['Desktop Safari'] },
			workers: 1, // Reduce parallelization to prevent flakiness
		},

		/* Test against mobile viewports. */
		{
			name: 'Mobile Chrome',
			use: { ...devices['Pixel 5'] },
		},
		{
			name: 'Mobile Safari',
			use: { ...devices['iPhone 12'] },
			workers: 1, // Reduce parallelization to prevent flakiness
		},
	],

	/* Run your local dev server before starting the tests */
	webServer: [
		{
			command: 'cd ../backend && uv run litestar run --host 0.0.0.0 --port 8000',
			url: process.env.CI
				? 'http://127.0.0.1:8000/api/v1/health'
				: 'http://localhost:8000/api/v1/health',
			reuseExistingServer: !process.env.CI,
			timeout: 120 * 1000,
			env: {
				...process.env,
				DATABASE_URL:
					process.env.DATABASE_URL ||
					(process.env.CI
						? 'postgresql+asyncpg://postgres:postgres@localhost:5432/test_db'
						: 'postgresql+asyncpg://sessions:sessions@localhost:5433/sessions'),
			},
		},
		{
			command: 'pnpm dev',
			url: process.env.CI ? 'http://127.0.0.1:4321' : 'http://localhost:4321',
			reuseExistingServer: !process.env.CI,
			timeout: 120 * 1000,
			env: {
				...process.env,
				PUBLIC_BASE_URL:
					process.env.PUBLIC_BASE_URL ||
					(process.env.CI ? 'http://127.0.0.1:8000' : 'http://localhost:8000'),
			},
		},
	],
});
