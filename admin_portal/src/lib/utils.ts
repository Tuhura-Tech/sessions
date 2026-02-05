/**
 * Utility functions for date and time formatting
 */

/**
 * Parse a date string safely, handling ISO 8601 dates
 */
export const parseDate = (dateString: string | Date): Date | null => {
	if (!dateString) return null;
	if (dateString instanceof Date) return dateString;

	// Try to parse ISO 8601 date string (YYYY-MM-DD or ISO timestamp)
	const date = new Date(dateString);
	// Check if the date is valid
	if (Number.isNaN(date.getTime())) {
		console.warn(`Invalid date string: ${dateString}`);
		return null;
	}
	return date;
};

export const formatDate = (date: string | Date): string => {
	const d = parseDate(date);
	if (!d) return 'Invalid date';
	return d.toLocaleDateString('en-NZ', {
		year: 'numeric',
		month: 'long',
		day: 'numeric',
	});
};

export const formatDateTime = (date: string | Date): string => {
	const d = parseDate(date);
	if (!d) return 'Invalid date';
	return d.toLocaleDateString('en-NZ', {
		year: 'numeric',
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit',
	});
};

/**
 * Calculate age from date of birth
 */
export const calculateAge = (dateOfBirth: string | Date | null): number | null => {
	if (!dateOfBirth) return null;

	const birthDate = parseDate(dateOfBirth);
	if (!birthDate) return null;

	const today = new Date();
	let age = today.getFullYear() - birthDate.getFullYear();
	const monthDiff = today.getMonth() - birthDate.getMonth();

	if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
		age--;
	}

	return age < 0 ? null : age;
};

export const formatTime = (timeString: string): string => {
	// Assuming time is in HH:MM format
	if (!timeString) return '-';
	return timeString;
};

export const formatAgeRange = (lower: number | null, upper: number | null): string => {
	if (!lower && !upper) return 'All ages';
	if (lower && !upper) return `${lower}+ years`;
	if (!lower && upper) return `Up to ${upper} years`;
	return `${lower}-${upper} years`;
};

export const getStatusColor = (status: string): string => {
	switch (status) {
		case 'confirmed':
			return 'bg-green-100 text-green-800';
		case 'waitlisted':
			return 'bg-yellow-100 text-yellow-800';
		case 'withdrawn':
			return 'bg-red-100 text-red-800';
		case 'pending':
			return 'bg-gray-100 text-gray-800';
		case 'present':
			return 'bg-green-100 text-green-800';
		case 'absent':
			return 'bg-red-100 text-red-800';
		case 'excused':
			return 'bg-yellow-100 text-yellow-800';
		default:
			return 'bg-gray-100 text-gray-800';
	}
};

export const getStatusLabel = (status: string): string => {
	return status.charAt(0).toUpperCase() + status.slice(1);
};
