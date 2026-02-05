/**
 * Error Handling Utilities
 *
 * Centralized error handling for consistent user-facing error messages
 * across the admin portal.
 */

import type { AxiosError } from 'axios';

export interface ApiError {
	status: number;
	message: string;
	detail?: string;
	field?: string;
}

/**
 * Extract user-friendly error message from API response
 */
export function extractErrorMessage(error: unknown): string {
	if (!error) return 'An unknown error occurred';

	// Axios error with response
	if (isAxiosError(error) && error.response) {
		const { status, data } = error.response;
		const responseData = data as Record<string, unknown>;

		// Handle specific HTTP status codes
		switch (status) {
			case 400:
				return (
					(responseData?.detail as string | undefined) ||
					(responseData?.message as string | undefined) ||
					'Invalid request. Please check your input.'
				);
			case 401:
				return 'You are not authorized. Please log in again.';
			case 403:
				return 'You do not have permission to perform this action.';
			case 404:
				return (
					(responseData?.detail as string | undefined) || 'The requested resource was not found.'
				);
			case 409:
				return (
					(responseData?.detail as string | undefined) ||
					'This action conflicts with existing data.'
				);
			case 422:
				// Validation error
				if (responseData?.detail && Array.isArray(responseData.detail)) {
					const errors = (responseData.detail as Array<{ msg?: string; loc?: string[] }>)
						.map((err) => {
							const field = err.loc?.slice(1).join('.') || 'field';
							return `${field}: ${err.msg}`;
						})
						.join('; ');
					return `Validation error: ${errors}`;
				}
				return (
					(responseData?.detail as string | undefined) ||
					(responseData?.message as string | undefined) ||
					'Invalid data submitted.'
				);
			case 429:
				return 'Too many requests. Please wait a moment and try again.';
			case 500:
			case 502:
			case 503:
				return 'Server error. Please try again later.';
			case 504:
				return 'Request timeout. The server took too long to respond.';
			default:
				return (
					(responseData?.detail as string | undefined) ||
					(responseData?.message as string | undefined) ||
					`Error: ${status}`
				);
		}
	}

	// Axios error without response (network error)
	if (isAxiosError(error)) {
		if (error.code === 'ERR_NETWORK') {
			return 'Network error. Please check your connection.';
		}
		if (error.code === 'ECONNABORTED') {
			return 'Request timeout. Please try again.';
		}
		return error.message || 'A network error occurred.';
	}

	// Generic Error object
	if (error instanceof Error) {
		return error.message;
	}

	// Fallback
	return String(error);
}

/**
 * Type guard for Axios errors
 */
function isAxiosError(error: unknown): error is AxiosError {
	return (
		typeof error === 'object' &&
		error !== null &&
		'isAxiosError' in error &&
		error.isAxiosError === true
	);
}

/**
 * Parse API error into structured format
 */
export function parseApiError(error: unknown): ApiError {
	if (isAxiosError(error) && error.response) {
		const responseData = error.response.data as Record<string, unknown>;
		return {
			status: error.response.status,
			message: extractErrorMessage(error),
			detail: responseData?.detail as string | undefined,
			field: responseData?.field as string | undefined,
		};
	}

	return {
		status: 0,
		message: extractErrorMessage(error),
	};
}

/**
 * Toast notification helper types
 */
export interface ToastNotification {
	type: 'success' | 'error' | 'warning' | 'info';
	message: string;
	duration?: number;
}

/**
 * Create error toast notification
 */
export function createErrorToast(error: unknown, fallbackMessage?: string): ToastNotification {
	return {
		type: 'error',
		message: extractErrorMessage(error) || fallbackMessage || 'An error occurred',
		duration: 5000,
	};
}

/**
 * Create success toast notification
 */
export function createSuccessToast(message: string, duration = 3000): ToastNotification {
	return {
		type: 'success',
		message,
		duration,
	};
}

/**
 * Retry helper with exponential backoff
 */
export async function retryWithBackoff<T>(
	fn: () => Promise<T>,
	options: {
		maxRetries?: number;
		initialDelay?: number;
		maxDelay?: number;
		backoffFactor?: number;
	} = {},
): Promise<T> {
	const { maxRetries = 3, initialDelay = 1000, maxDelay = 10000, backoffFactor = 2 } = options;

	let lastError: unknown;
	let delay = initialDelay;

	for (let attempt = 0; attempt <= maxRetries; attempt++) {
		try {
			return await fn();
		} catch (error) {
			lastError = error;

			// Don't retry on client errors (4xx) except 429
			if (isAxiosError(error) && error.response) {
				const status = error.response.status;
				if (status >= 400 && status < 500 && status !== 429) {
					throw error;
				}
			}

			// Last attempt or non-retryable error
			if (attempt === maxRetries) {
				break;
			}

			// Wait before retrying
			await new Promise((resolve) => setTimeout(resolve, delay));
			delay = Math.min(delay * backoffFactor, maxDelay);
		}
	}

	throw lastError;
}

/**
 * Request deduplication helper
 */
class RequestDeduplicator {
	private pending = new Map<string, Promise<unknown>>();

	/**
	 * Deduplicate requests by key
	 * If a request with the same key is already in flight, return the existing promise
	 */
	async deduplicate<T>(key: string, fn: () => Promise<T>): Promise<T> {
		// Check if request is already pending
		const existing = this.pending.get(key);
		if (existing) {
			return existing as Promise<T>;
		}

		// Start new request
		const promise = fn()
			.then((result) => {
				this.pending.delete(key);
				return result;
			})
			.catch((error) => {
				this.pending.delete(key);
				throw error;
			});

		this.pending.set(key, promise);
		return promise;
	}

	/**
	 * Clear specific key or all pending requests
	 */
	clear(key?: string): void {
		if (key) {
			this.pending.delete(key);
		} else {
			this.pending.clear();
		}
	}
}

/**
 * Global request deduplicator instance
 */
export const requestDeduplicator = new RequestDeduplicator();

/**
 * Validation helpers
 */
export const validators = {
	/**
	 * Validate email format
	 */
	email: (email: string): boolean => {
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		return emailRegex.test(email);
	},

	/**
	 * Validate phone number (NZ format)
	 */
	phoneNZ: (phone: string): boolean => {
		const cleanedPhone = phone.replace(/[\s()-]/g, '');
		return /^(0|\+?64)[2-9]\d{7,9}$/.test(cleanedPhone);
	},

	/**
	 * Validate URL format
	 */
	url: (url: string): boolean => {
		try {
			new URL(url);
			return true;
		} catch {
			return false;
		}
	},

	/**
	 * Validate required field
	 */
	required: (value: unknown): boolean => {
		if (value === null || value === undefined) return false;
		if (typeof value === 'string') return value.trim().length > 0;
		if (Array.isArray(value)) return value.length > 0;
		return true;
	},

	/**
	 * Validate age range
	 */
	ageRange: (lower: number, upper: number): boolean => {
		return lower >= 0 && upper >= lower && upper <= 100;
	},
};
