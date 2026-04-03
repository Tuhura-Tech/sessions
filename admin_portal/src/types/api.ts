/**
 * API type mapping and adapters
 * Converts between the raw OpenAPI schema types and frontend-friendly interfaces
 */

import type { components } from './schema';

/**
 * Attendance tracking
 */
export type AttendanceStatus = 'present' | 'absent_known' | 'absent_unknown';
export interface AttendanceRecord {
	id: string;
	occurrence_id: string;
	student_id: string;
	status: AttendanceStatus;
	reason?: string | null;
	created_at: string;
	updated_at: string;
}

export interface AttendanceRollItem {
	signup_id: string;
	student_id: string;
	student_name: string;
	caregiver_name: string;
	attendance?: AttendanceRecord | null;
}

export interface AttendanceRoll {
	occurrence_id: string;
	session_id: string;
	starts_at: string;
	ends_at: string;
	cancelled: boolean;
	items: AttendanceRollItem[];
}

export interface AttendanceUpsert {
	student_id: string;
	status: AttendanceStatus;
	reason?: string;
}

/**
 * Block management
 */
export type BlockType = 'special' | 'term_1' | 'term_2' | 'term_3' | 'term_4';

export interface SessionBlock {
	id: string;
	name: string;
	year: number;
	block_type?: BlockType;
	start_date?: string;
	end_date?: string;
	timezone?: string;
}

export interface SessionBlockCreate {
	name: string;
	year: number;
	block_type: BlockType;
	start_date: string;
	end_date: string;
	timezone?: string;
}

export interface SessionBlockUpdate {
	name?: string;
	year?: number;
	block_type?: BlockType;
	start_date?: string;
	end_date?: string;
	timezone?: string;
}

/**
 * Location management
 */
export interface SessionLocation {
	id: string;
	name: string;
	address: string;
	region: string;
	lat: number;
	lng: number;
	instructions?: string | null;
	contact_name: string;
	contact_email: string;
	contact_phone?: string | null;
	internal_notes?: string | null;
}

export interface LocationCreate {
	name: string;
	address: string;
	region: string;
	lat: number;
	lng: number;
	instructions?: string;
	contact_name: string;
	contact_email: string;
	contact_phone?: string;
	internal_notes?: string;
}

export interface LocationUpdate {
	name?: string;
	address?: string;
	region?: string;
	lat?: number;
	lng?: number;
	instructions?: string | null;
	contact_name?: string;
	contact_email?: string;
	contact_phone?: string | null;
	internal_notes?: string | null;
}

/**
 * Exclusion dates (school holidays, etc)
 */
export interface ExclusionDate {
	id: string;
	year: number;
	date: string;
	reason: string | null;
}

export interface ExclusionDateCreate {
	year: number;
	date: string;
	reason?: string;
}

export interface ExclusionDateUpdate {
	year?: number;
	date?: string;
	reason?: string | null;
}

/**
 * Session management
 */
export interface Session {
	id: string;
	name: string;
	year: number;
	age_lower: number;
	age_upper: number;
	day_of_week: number | null;
	start_time: string;
	end_time: string;
	capacity: number;
	description?: string | null;
	photo_album_url?: string | null;
	internal_notes?: string | null;
	archived: boolean;
	session_type?: string;
	blocks?: string[];
	location?: SessionLocation;
	session_location_id?: string;
	confirmed_count?: number;
	waitlist_count?: number;
	pending_count?: number;
	needs_devices_count?: number;
	is_full?: boolean;
	waitlist?: boolean;
}

export interface SessionCreate {
	name: string;
	year: number;
	location_id: string;
	session_type?: string;
	age_lower: number;
	age_upper: number;
	day_of_week: number;
	start_time: string;
	end_time: string;
	capacity: number;
	description?: string | null;
	photo_album_url?: string | null;
	internal_notes?: string | null;
	archived?: boolean;
	blocks: string[];
	waitlist?: boolean;
}

export interface SessionUpdate {
	year?: number;
	session_type?: string;
	name?: string;
	age_lower?: number;
	age_upper?: number;
	start_time?: string;
	end_time?: string;
	day_of_week?: number | null;
	capacity?: number;
	description?: string | null;
	photo_album_url?: string | null;
	internal_notes?: string | null;
	archived?: boolean;
	location_id?: string;
	blocks?: string[];
	waitlist?: boolean;
}

export interface SessionDetail extends Session {
	occurrences?: Occurrence[];
	signups?: Signup[];
	occurrences_by_block?: Record<string, Occurrence[]>;
}

/**
 * Occurrence/Session timing
 */
export interface Occurrence {
	id: string;
	session_id: string;
	starts_at: string;
	ends_at: string;
	cancelled: boolean;
	cancellation_reason?: string | null;
	auto_generated?: boolean;
	block_id?: string | null;
	block_name?: string | null;
}

export interface OccurrenceCreate {
	session_id: string;
	starts_at: string;
	ends_at: string;
	block_id: string;
}

export interface OccurrenceUpdate {
	starts_at?: string;
	ends_at?: string;
	cancelled?: boolean;
	cancellation_reason?: string | null;
	block_id?: string | null;
}

/**
 * Signup management
 */
export type SignupStatus = 'pending' | 'confirmed' | 'waitlisted' | 'withdrawn';

export interface Signup {
	id: string;
	student_id: string;
	session_id: string;
	status: SignupStatus;
	student_name?: string;
	guardian_name?: string;
	email?: string;
	phone?: string | null;
	date_of_birth?: string | null;
	media_consent?: boolean;
	needs_devices?: boolean;
	created_at: string;
	withdrawn_at?: string | null;
	pickup_dropoff?: string | null;
	notes?: string | null;
	medical_information?: string | null;
	other_information?: string | null;
}

export interface SignupCreate {
	session_id: string;
	student_id: string;
	status?: SignupStatus;
	notes?: string;
}

export interface SignupUpdate {
	status?: SignupStatus;
	notes?: string;
	withdrawn_at?: string | null;
	pickup_dropoff?: string | null;
}

/**
 * Staff management
 */
export interface Staff {
	id: string;
	name: string;
	email: string;
	sso_id: string;
	active: boolean;
	last_login_at?: string | null;
	created_at: string;
	updated_at: string;
}

export interface StaffListItem extends Staff {
	active: boolean;
}

export interface StaffCreate {
	name: string;
	email: string;
	active?: boolean;
}

export interface StaffUpdate {
	name?: string;
	email?: string;
	active?: boolean;
}

export interface StaffAvailability {
	staff_id: string;
	name: string;
	email: string;
	active: boolean;
	assigned_session_count: number;
	session_ids: string[];
}

export interface StaffPublic {
	id: string;
	name: string;
	email: string;
	active: boolean;
	last_login_at?: string | null;
}

export interface StaffSessionSummary {
	id: string;
	name: string;
	year: number;
	location?: string | null;
	sessionType?: string;
	dayOfWeek?: number | null;
	startTime?: string | null;
	endTime?: string | null;
	locationName?: string | null;
}

/**
 * Caregiver management
 */
export interface Caregiver {
	id: string;
	email: string;
	name?: string | null;
	phone?: string | null;
	email_verified: boolean;
	profile_complete: boolean;
	referral_source?: string | null;
	students?: ChildDetails[];
}

export interface CaregiverCreate {
	email: string;
	name?: string;
	phone?: string;
	subscribeNewsletter?: boolean;
}

export interface CaregiverUpdate {
	name?: string;
	phone?: string;
	email?: string;
}

export interface CaregiverMe {
	id: string;
	email: string;
	name?: string | null;
	phone?: string | null;
}

export interface CaregiverMessage {
	id: string;
	caregiver_id: string;
	subject: string;
	body: string;
	created_at: string;
}

/**
 * Student/Child details
 */
export interface ChildDetails {
	id: string;
	caregiver_id: string;
	name: string;
	date_of_birth: string;
	media_consent: boolean;
	medical_info?: string | null;
	other_info?: string | null;
	caregiver?: Caregiver;
}

/**
 * Health check endpoints
 */
export interface HealthCheckResponse {
	timestamp: string;
	status: 'ok' | 'error';
	uptime: number;
}

/**
 * Raw OpenAPI component type aliases (for advanced usage)
 */
export type AdminSchemaBlock = components['schemas']['admin_schemas_block_Block'];
export type AdminSchemaLocation = components['schemas']['admin_schemas_location_Location'];
export type AdminSchemaOccurrence = components['schemas']['admin_schemas_occurrence_Occurrence'];
export type AdminSchemaStudent = components['schemas']['admin_schemas_student_Student'];
export type AdminSchemaStudentCreate = components['schemas']['admin_schemas_student_StudentCreate'];
export type AdminSchemaStudentUpdate = components['schemas']['admin_schemas_student_StudentUpdate'];
export type PublicSchemaBlock = components['schemas']['public_schemas_block_Block'];
export type PublicSchemaLocation = components['schemas']['public_schemas_session_Location'];
export type PublicSchemaOccurrence = components['schemas']['public_schemas_occurrence_Occurrence'];
