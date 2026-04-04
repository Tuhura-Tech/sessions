import { defineConfig, devices } from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
	testDir: './tests/e2e',
	/* Run tests in files in parallel */
	fullyParallel: true,
	/* Fail the build on CI if you accidentally left test.only in the source code. */
	forbidOnly: !!process.env.CI,
	/* Retry on CI only */
	retries: process.env.CI ? 2 : 0,
	/* Opt out of parallel tests on CI. */
	workers: process.env.CI ? 1 : undefined,
	/* Reporter to use. See https://playwright.dev/docs/test-reporters */
	reporter: [['list'], ['html', { open: 'never' }]],
	/* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
	use: {
		/* Base URL to use in actions like `await page.goto('/')`. */
		baseURL:
			process.env.PLAYWRIGHT_BASE_URL ||
			(process.env.CI ? 'http://127.0.0.1:3002' : 'http://localhost:3002'),
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
	/* In CI, the backend is started by the workflow - only Playwright starts the frontend */
	webServer: process.env.CI
		? {
				command: 'pnpm dev --host 127.0.0.1',
				url: 'http://127.0.0.1:3002',
				reuseExistingServer: false,
				timeout: 120 * 1000,
				env: Object.entries(process.env).reduce(
					(acc, [k, v]) => {
						if (v !== undefined) {
							acc[k] = v;
						}
						return acc;
					},
					{} as Record<string, string>,
				),
			}
		: [
				{
					command:
						'docker compose -f ../docker-compose.yml up -d postgres && uv run litestar database upgrade --no-prompt && uv run litestar run --host 0.0.0.0 --port 8000',
					cwd: '../backend',
					url: 'http://localhost:8000/api/v1/health',
					reuseExistingServer: true,
					timeout: 120 * 1000,
					env: {
						...Object.entries(process.env).reduce(
							(acc, [k, v]) => {
								if (v !== undefined) {
									acc[k] = v;
								}
								return acc;
							},
							{} as Record<string, string>,
						),
						AUTH_SECRET: process.env.PLAYWRIGHT_AUTH_SECRET || 'playwright-dev-secret',
						DATABASE_URL:
							process.env.DATABASE_URL ||
							'postgresql+psycopg://sessions:sessions@localhost:5433/sessions',
						CORS_ORIGINS:
							'http://localhost:3002,http://127.0.0.1:3002,http://localhost:8000,http://127.0.0.1:8000',
						SAQ_USE_SERVER_LIFESPAN: 'false',
					},
				},
				{
					command: 'pnpm dev',
					url: 'http://localhost:3002',
					reuseExistingServer: true,
					timeout: 120 * 1000,
					env: Object.entries(process.env).reduce(
						(acc, [k, v]) => {
							if (v !== undefined) {
								acc[k] = v;
							}
							return acc;
						},
						{} as Record<string, string>,
					),
				},
			],
});
