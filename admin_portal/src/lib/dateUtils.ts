/**
 * Shared date formatting utilities using NZ locale
 */

const NZ_TIMEZONE = 'Pacific/Auckland';
const NZ_LOCALE = 'en-NZ';

/**
 * Format a date as a short string (e.g., "Mon, 3 Feb 2026")
 */
export function formatShortDate(date: Date | string): string {
	const d = typeof date === 'string' ? new Date(date) : date;
	return d.toLocaleDateString(NZ_LOCALE, {
		weekday: 'short',
		year: 'numeric',
		month: 'short',
		day: 'numeric',
		timeZone: NZ_TIMEZONE,
	});
}

/**
 * Format a date as a long string (e.g., "Monday, 3 February 2026")
 */
export function formatLongDate(date: Date | string): string {
	const d = typeof date === 'string' ? new Date(date) : date;
	return d.toLocaleDateString(NZ_LOCALE, {
		weekday: 'long',
		year: 'numeric',
		month: 'long',
		day: 'numeric',
		timeZone: NZ_TIMEZONE,
	});
}

/**
 * Format a time as a string (e.g., "3:30 PM")
 */
export function formatTime(date: Date | string): string {
	const d = typeof date === 'string' ? new Date(date) : date;
	return d.toLocaleTimeString(NZ_LOCALE, {
		hour: 'numeric',
		minute: '2-digit',
		hour12: true,
		timeZone: NZ_TIMEZONE,
	});
}

/**
 * Format a date and time as a string (e.g., "Mon, 3 Feb 2026 • 3:30 PM")
 */
export function formatDateTime(date: Date | string): string {
	return `${formatShortDate(date)} • ${formatTime(date)}`;
}

/**
 * Format a time range (e.g., "3:30 PM–5:00 PM")
 */
export function formatTimeRange(start: Date | string, end: Date | string): string {
	return `${formatTime(start)}–${formatTime(end)}`;
}

/**
 * Format a date and time range (e.g., "Mon, 3 Feb 2026 • 3:30 PM–5:00 PM")
 */
export function formatDateTimeRange(start: Date | string, end: Date | string): string {
	return `${formatShortDate(start)} • ${formatTimeRange(start, end)}`;
}

/**
 * Format a date for input fields (YYYY-MM-DD)
 */
export function formatDateForInput(date: Date | string): string {
	const d = typeof date === 'string' ? new Date(date) : date;
	return d.toISOString().split('T')[0];
}

/**
 * Format a time for input fields (HH:MM)
 */
export function formatTimeForInput(time: string): string {
	return time.split(':').slice(0, 2).join(':');
}

/**
 * Parse a date string to a Date object in NZ timezone
 */
export function parseDate(dateString: string): Date {
	return new Date(dateString);
}
