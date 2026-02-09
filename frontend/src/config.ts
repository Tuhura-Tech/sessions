/**
 * Central configuration for API endpoints and deployment settings.
 *
 * Environment variables:
 * - INTERNAL_API_URL: Docker-internal networking URL (e.g., http://backend:8000)
 * - PUBLIC_BASE_URL: Public API URL for client-side requests
 *
 * The URL is injected into client-side code via global variable set by Layout.astro.
 */

/**
 * Default API URL - used as fallback when no environment variables are set.
 * Set this to your production API URL.
 */
export const DEFAULT_API_URL = 'http://localhost:8000';

/**
 * Get API base URL for server-side rendering.
 * Uses INTERNAL_API_URL for Docker networking, falls back to PUBLIC_BASE_URL,
 * then DEFAULT_API_URL.
 */
export function getServerApiBaseUrl(): string {
	const internalUrl = process.env.INTERNAL_API_URL;
	const publicUrl = process.env.PUBLIC_BASE_URL;
	return internalUrl || publicUrl || DEFAULT_API_URL;
}

export function getServerApiExternalBaseUrl(): string {
	return process.env.PUBLIC_BASE_URL || DEFAULT_API_URL;
}

/**
 * Get API base URL for client-side code.
 * Reads from global variable set by server, falls back to server-side logic.
 */
export function getClientApiBaseUrl(): string {
	// Client-side: read from global variable (injected by Layout.astro)
	if (typeof window !== 'undefined') {
		const apiBaseUrl = (globalThis as unknown as { __TUHURA_API_BASE_URL?: string })
			?.__TUHURA_API_BASE_URL;
		if (apiBaseUrl) {
			return apiBaseUrl;
		}
	}

	// Server-side (SSR): use runtime env vars
	if (typeof window === 'undefined') {
		return getServerApiBaseUrl();
	}

	// Fallback - should not reach here if Layout.astro properly sets global
	return DEFAULT_API_URL;
}

/**
 * Get API base URL - works on both server and client.
 * This is the main function to use throughout the application.
 */
export function getApiBaseUrl(): string {
	return getClientApiBaseUrl();
}
