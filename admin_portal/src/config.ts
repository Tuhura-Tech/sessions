/**
 * Configuration for environment-specific settings
 */
/// <reference types="vite/client" />

export const config = {
	// Always call the API directly (no nginx proxy)
	// Prefer explicit environment variable, fall back to dev mode
	apiUrl:
		(import.meta.env.PUBLIC_BASE_URL as string | undefined) ||
		(import.meta.env.DEV ? '' : '/api/v1'),
	appName: 'Admin Portal',
	appVersion: '1.0.0',
};

// Feature flags
export const features = {
	attendance: true,
	exports: true,
	bulkEmail: true,
	waitlistPromotion: true,
	sessionBlocks: true,
	childNotes: true,
};
