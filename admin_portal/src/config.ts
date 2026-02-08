/**
 * Configuration for environment-specific settings
 */
/// <reference types="vite/client" />

export const config = {
	// API URL is set at build time via Dockerfile ARG: PUBLIC_BASE_URL
	// Vite converts it to: import.meta.env.VITE_PUBLIC_BASE_URL
	// This is embedded in the static files and cannot change at runtime
	apiUrl: import.meta.env.VITE_PUBLIC_BASE_URL || '',
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
