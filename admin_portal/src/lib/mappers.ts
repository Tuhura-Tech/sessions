/**
 * Type mapping utilities to convert between snake_case (API) and camelCase (frontend)
 */

import type {
	AttendanceUpsert,
	ChildDetails,
	Session,
	SessionBlock,
	SessionCreate,
	SessionUpdate,
} from '../types';

/**
 * Convert form data (camelCase) to SessionCreate (snake_case)
 */
export function toSessionCreate(data: {
	name: string;
	year: number;
	locationId: string;
	ageLower: number;
	ageUpper: number;
	dayOfWeek: number;
	startTime: string;
	endTime: string;
	capacity: number;
	sessionType?: 'term' | 'special';
	description?: string | null;
	photoAlbumUrl?: string | null;
	internalNotes?: string | null;
	blocks: string[];
	archived?: boolean;
	waitlist?: boolean;
}): SessionCreate {
	return {
		name: data.name,
		year: data.year,
		location_id: data.locationId,
		age_lower: data.ageLower,
		age_upper: data.ageUpper,
		day_of_week: data.dayOfWeek,
		start_time: data.startTime,
		end_time: data.endTime,
		capacity: data.capacity,
		session_type: data.sessionType,
		description: data.description ?? undefined,
		photo_album_url: data.photoAlbumUrl ?? undefined,
		internal_notes: data.internalNotes ?? undefined,
		blocks: data.blocks,
		archived: data.archived,
		waitlist: data.waitlist,
	};
}

/**
 * Convert form data (camelCase) to SessionUpdate (snake_case)
 */
export function toSessionUpdate(data: {
	name?: string;
	year?: number;
	locationId?: string;
	ageLower?: number;
	ageUpper?: number;
	dayOfWeek?: number;
	startTime?: string;
	endTime?: string;
	capacity?: number;
	sessionType?: 'term' | 'special';
	description?: string | null;
	photoAlbumUrl?: string | null;
	internalNotes?: string | null;
	blocks?: string[];
	archived?: boolean;
	waitlist?: boolean;
}): SessionUpdate {
	return {
		name: data.name,
		year: data.year,
		location_id: data.locationId,
		age_lower: data.ageLower,
		age_upper: data.ageUpper,
		day_of_week: data.dayOfWeek,
		start_time: data.startTime,
		end_time: data.endTime,
		capacity: data.capacity,
		session_type: data.sessionType,
		description: data.description,
		photo_album_url: data.photoAlbumUrl,
		internal_notes: data.internalNotes,
		blocks: data.blocks,
		archived: data.archived,
		waitlist: data.waitlist,
	};
}

/**
 * Convert Session (snake_case) to form data (camelCase)
 */
export function fromSession(session: Session): {
	name: string;
	year: number;
	locationId: string;
	ageLower: number;
	ageUpper: number;
	dayOfWeek: number | null;
	startTime: string;
	endTime: string;
	capacity: number;
	sessionType?: string;
	description?: string | null;
	photoAlbumUrl?: string | null;
	internalNotes?: string | null;
	blocks: string[];
	archived: boolean;
	waitlist?: boolean;
} {
	return {
		name: session.name,
		year: session.year,
		locationId: session.session_location_id || '',
		ageLower: session.age_lower,
		ageUpper: session.age_upper,
		dayOfWeek: session.day_of_week,
		startTime: session.start_time,
		endTime: session.end_time,
		capacity: session.capacity,
		sessionType: session.session_type,
		description: session.description,
		photoAlbumUrl: session.photo_album_url,
		internalNotes: session.internal_notes,
		blocks: session.blocks || [],
		archived: session.archived,
		waitlist: session.waitlist,
	};
}

/**
 * Convert Attendance Upsert form data to API format
 */
export function toAttendanceUpsert(data: {
	studentId: string;
	status: string;
	reason?: string;
}): AttendanceUpsert {
	return {
		student_id: data.studentId,
		status: data.status as 'present' | 'absent_known' | 'absent_unknown',
		reason: data.reason,
	};
}

/**
 * Ensure Session has all required properties with defaults
 */
export function normalizeSession(session: Partial<Session>): Session {
	return {
		id: session.id || '',
		name: session.name || '',
		year: session.year || new Date().getFullYear(),
		age_lower: session.age_lower ?? 5,
		age_upper: session.age_upper ?? 18,
		day_of_week: session.day_of_week ?? null,
		start_time: session.start_time || '',
		end_time: session.end_time || '',
		capacity: session.capacity ?? 30,
		archived: session.archived ?? false,
		description: session.description,
		photo_album_url: session.photo_album_url,
		internal_notes: session.internal_notes,
		session_type: session.session_type,
		blocks: session.blocks,
		location: session.location,
		session_location_id: session.session_location_id,
		confirmed_count: session.confirmed_count,
		waitlist_count: session.waitlist_count,
		pending_count: session.pending_count,
		needs_devices_count: session.needs_devices_count,
		is_full: session.is_full,
		waitlist: session.waitlist,
	};
}

/**
 * Ensure SessionBlock has all required properties
 */
export function normalizeSessionBlock(block: Partial<SessionBlock>): SessionBlock {
	return {
		id: block.id || '',
		name: block.name || '',
		year: block.year || new Date().getFullYear(),
		block_type: block.block_type,
		start_date: block.start_date,
		end_date: block.end_date,
		timezone: block.timezone,
	};
}

/**
 * Ensure ChildDetails has all required properties
 */
export function normalizeChildDetails(child: Partial<ChildDetails>): ChildDetails {
	return {
		id: child.id || '',
		caregiver_id: child.caregiver_id || '',
		name: child.name || '',
		date_of_birth: child.date_of_birth || '',
		media_consent: child.media_consent ?? false,
		medical_info: child.medical_info,
		other_info: child.other_info,
		caregiver: child.caregiver,
	};
}
