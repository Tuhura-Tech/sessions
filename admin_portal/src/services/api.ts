import api from '../lib/api';
import type {
	AttendanceRecord,
	AttendanceRoll,
	AttendanceUpsert,
	Caregiver,
	CaregiverCreate,
	CaregiverUpdate,
	ChildDetails,
	ExclusionDate,
	Occurrence,
	Session,
	SessionBlock,
	SessionCreate,
	SessionLocation,
	SessionUpdate,
	Signup,
	Staff,
	StaffAvailability,
	StaffListItem,
	StaffPublic,
	StaffSessionSummary,
} from '../types';

const unwrapList = <T>(data: unknown): T[] => {
	if (Array.isArray(data)) return data;
	return ((data as { items?: T[] })?.items || []) as T[];
};

export const adminApi = {
	// Auth
	checkSession: async () => {
		const { data } = await api.get('/admin/auth/me');
		return data;
	},

	logout: async () => {
		await api.post('/admin/auth/logout');
	},

	// Sessions
	getSessions: async (year?: number, includeArchived = false): Promise<Session[]> => {
		const params = new URLSearchParams();
		if (year) params.append('year', year.toString());
		if (includeArchived) params.append('include_archived', 'true');
		const { data } = await api.get(`/admin/sessions?${params}`);
		return unwrapList<Session>(data);
	},

	getSession: async (id: string): Promise<Session> => {
		const { data } = await api.get(`/admin/sessions/${id}`);
		return data;
	},

	createSession: async (session: SessionCreate): Promise<Session> => {
		const { data } = await api.post('/admin/sessions', session);
		return data;
	},

	updateSession: async (id: string, session: SessionUpdate): Promise<Session> => {
		const { data } = await api.patch(`/admin/sessions/${id}`, session);
		return data;
	},

	deleteSession: async (id: string): Promise<void> => {
		await api.delete(`/admin/sessions/${id}`);
	},

	// Locations
	getLocations: async (): Promise<SessionLocation[]> => {
		const { data } = await api.get('/admin/locations');
		return unwrapList<SessionLocation>(data);
	},

	getLocation: async (id: string): Promise<SessionLocation> => {
		const { data } = await api.get(`/admin/locations/${id}`);
		return data;
	},

	getLocationSessions: async (
		id: string,
		year?: number,
		includeArchived: boolean = false,
	): Promise<Session[]> => {
		const params = new URLSearchParams();
		if (year !== undefined) params.append('year', String(year));
		if (includeArchived) params.append('include_archived', 'true');
		const query = params.toString();
		const { data } = await api.get(`/admin/locations/${id}/sessions${query ? `?${query}` : ''}`);
		return unwrapList<Session>(data);
	},

	createLocation: async (location: Partial<SessionLocation>): Promise<SessionLocation> => {
		const { data } = await api.post('/admin/locations', location);
		return data;
	},

	updateLocation: async (
		id: string,
		location: Partial<SessionLocation>,
	): Promise<SessionLocation> => {
		const { data } = await api.patch(`/admin/locations/${id}`, location);
		return data;
	},

	// Blocks
	getBlocks: async (year?: number): Promise<SessionBlock[]> => {
		const params = year ? `?year=${year}` : '';
		const { data } = await api.get(`/admin/blocks${params}`);
		return unwrapList<SessionBlock>(data);
	},

	createBlock: async (block: Partial<SessionBlock>): Promise<SessionBlock> => {
		const { data } = await api.post('/admin/blocks', block);
		return data;
	},

	updateBlock: async (id: string, block: Partial<SessionBlock>): Promise<SessionBlock> => {
		const { data } = await api.patch(`/admin/blocks/${id}`, block);
		return data;
	},

	// Exclusions
	getExclusions: async (year?: number): Promise<ExclusionDate[]> => {
		const params = year ? `?year=${year}` : '';
		const { data } = await api.get(`/admin/exclusions${params}`);
		return unwrapList<ExclusionDate>(data);
	},

	createExclusion: async (exclusion: {
		date: string;
		reason: string | null;
	}): Promise<ExclusionDate> => {
		const { data } = await api.post('/admin/exclusions', exclusion);
		return data;
	},

	updateExclusion: async (
		id: string,
		exclusion: { reason: string | null },
	): Promise<ExclusionDate> => {
		const { data } = await api.patch(`/admin/exclusions/${id}`, exclusion);
		return data;
	},

	deleteExclusion: async (id: string): Promise<void> => {
		await api.delete(`/admin/exclusions/${id}`);
	},

	// Signups
	getStudentSignups: async (studentId: string): Promise<Signup[]> => {
		const { data } = await api.get(`/admin/students/${studentId}/signups`);
		return unwrapList<Signup>(data);
	},

	getSessionSignups: async (sessionId: string, status?: string): Promise<Signup[]> => {
		const params = status ? `?status=${status}` : '';
		const { data } = await api.get(`/admin/sessions/${sessionId}/signups${params}`);
		return unwrapList<Signup>(data);
	},

	updateSignupStatus: async (
		signupId: string,
		status: string,
		options?: { reason?: string | null; notifyCaregiver?: boolean },
	): Promise<Signup> => {
		const { data } = await api.patch(`/admin/signups/${signupId}/status`, {
			status,
			reason: options?.reason ?? null,
			notify_caregiver: options?.notifyCaregiver ?? false,
		});
		return data;
	},

	createSignup: async (payload: {
		sessionId: string;
		studentId: string;
		status?: string;
		pickupDropoff?: string | null;
	}): Promise<Signup> => {
		const { data } = await api.post('/admin/signups', {
			session_id: payload.sessionId,
			student_id: payload.studentId,
			status: payload.status,
			pickup_dropoff: payload.pickupDropoff ?? null,
		});
		return data;
	},

	// Occurrences
	getSessionOccurrences: async (sessionId: string): Promise<Occurrence[]> => {
		const { data } = await api.get(`/admin/sessions/${sessionId}/occurrences`);
		return unwrapList<Occurrence>(data);
	},

	cancelOccurrence: async (occurrenceId: string, reason?: string): Promise<Occurrence> => {
		const { data } = await api.patch(`/admin/occurrences/${occurrenceId}/cancel`, {
			cancelled: true,
			cancellationReason: reason,
		});
		return data;
	},

	reinstateOccurrence: async (occurrenceId: string): Promise<Occurrence> => {
		const { data } = await api.patch(`/admin/occurrences/${occurrenceId}/cancel`, {
			cancelled: false,
		});
		return data;
	},

	// Attendance
	getAttendanceRoll: async (occurrenceId: string): Promise<AttendanceRoll> => {
		const { data } = await api.get(`/admin/occurrences/${occurrenceId}/roll`);
		return data;
	},

	markAttendance: async (
		occurrenceId: string,
		attendance: AttendanceUpsert,
	): Promise<AttendanceRecord> => {
		const { data } = await api.post(`/admin/occurrences/${occurrenceId}/attendance`, attendance);
		return data;
	},

	// Exports
	exportSignupsCSV: async (sessionId: string, status?: string): Promise<Blob> => {
		const params = status ? `?status=${status}` : '';
		const { data } = await api.get(`/admin/sessions/${sessionId}/export/signups.csv${params}`, {
			responseType: 'blob',
		});
		return data;
	},

	exportAttendanceCSV: async (sessionId: string): Promise<Blob> => {
		const { data } = await api.get(`/admin/sessions/${sessionId}/export/attendance.csv`, {
			responseType: 'blob',
		});
		return data;
	},

	// Staff
	getStaff: async (activeOnly = true): Promise<StaffListItem[]> => {
		const params = activeOnly ? '?active_only=true' : '?active_only=false';
		const { data } = await api.get(`/admin/staff/${params}`);
		return unwrapList<StaffListItem>(data);
	},

	getStaffMember: async (staffId: string): Promise<Staff> => {
		const { data } = await api.get(`/admin/staff/${staffId}`);
		return data;
	},

	createStaff: async (payload: { name: string; email: string; ssoId: string }): Promise<Staff> => {
		const { data } = await api.post('/admin/staff/', {
			name: payload.name,
			email: payload.email,
			sso_id: payload.ssoId,
		});
		return data;
	},

	updateStaff: async (
		staffId: string,
		payload: Partial<{ name: string; email: string; active: boolean }>,
	): Promise<Staff> => {
		const { data } = await api.patch(`/admin/staff/${staffId}`, payload);
		return data;
	},

	getStaffSessions: async (staffId: string): Promise<StaffSessionSummary[]> => {
		const { data } = await api.get(`/admin/staff/${staffId}/sessions`);
		return unwrapList<Record<string, unknown>>(data).map((item) => {
			const sessionType = (item.sessionType ?? item.session_type) as string | undefined;
			const dayOfWeek = (item.dayOfWeek ?? item.day_of_week) as number | null | undefined;
			const startTime = (item.startTime ?? item.start_time) as string | null | undefined;
			const endTime = (item.endTime ?? item.end_time) as string | null | undefined;
			const locationName = (item.locationName ?? item.location_name) as string | null | undefined;
			const location = (item.location ?? item.location_name ?? item.locationName) as
				| string
				| null
				| undefined;

			return {
				id: item.id as string,
				name: item.name as string,
				year: item.year as number,
				location,
				sessionType,
				dayOfWeek,
				startTime,
				endTime,
				locationName,
			};
		});
	},

	getStaffAvailability: async (year?: number, activeOnly = true): Promise<StaffAvailability[]> => {
		const params = new URLSearchParams();
		if (year !== undefined) params.append('year', year.toString());
		params.append('active_only', activeOnly.toString());
		const { data } = await api.get(`/admin/staff/availability?${params.toString()}`);
		return unwrapList<StaffAvailability>(data);
	},

	// Session Staff Assignments
	getSessionStaff: async (sessionId: string): Promise<StaffPublic[]> => {
		const { data } = await api.get(`/admin/sessions/${sessionId}/staff`);
		return unwrapList<StaffPublic>(data);
	},

	assignStaffToSession: async (sessionId: string, staffId: string): Promise<void> => {
		await api.post(`/admin/sessions/${sessionId}/staff`, { staff_id: staffId });
	},

	removeStaffFromSession: async (sessionId: string, staffId: string): Promise<void> => {
		await api.delete(`/admin/sessions/${sessionId}/staff/${staffId}`);
	},

	bulkAssignStaff: async (
		sessionId: string,
		staffIds: string[],
		replace = false,
	): Promise<void> => {
		await api.post(`/admin/sessions/${sessionId}/staff/bulk`, {
			staff_ids: staffIds,
			replace,
		});
	},

	// Children / Notes
	getChild: async (childId: string): Promise<ChildDetails> => {
		const { data } = await api.get(`/admin/students/${childId}`);
		return data;
	},

	// Children list
	listChildren: async (): Promise<ChildDetails[]> => {
		const { data } = await api.get('/admin/students');
		return unwrapList<ChildDetails>(data);
	},

	// Caregivers
	listCaregivers: async (limit?: number, offset?: number): Promise<Caregiver[]> => {
		const params = new URLSearchParams();
		if (limit !== undefined) params.append('limit', limit.toString());
		if (offset !== undefined) params.append('offset', offset.toString());
		const qs = params.toString();
		const url = qs ? `/admin/caregivers?${qs}` : '/admin/caregivers';
		const { data } = await api.get(url);
		return unwrapList<Caregiver>(data);
	},

	getCaregiver: async (id: string): Promise<Caregiver> => {
		const { data } = await api.get(`/admin/caregivers/${id}`);
		return data;
	},

	createCaregiver: async (caregiver: CaregiverCreate): Promise<Caregiver> => {
		const { data } = await api.post('/admin/caregivers', caregiver);
		return data;
	},

	updateCaregiver: async (id: string, caregiver: CaregiverUpdate): Promise<Caregiver> => {
		const { data } = await api.patch(`/admin/caregivers/${id}`, caregiver);
		return data;
	},

	getCaregiverStudents: async (id: string): Promise<ChildDetails[]> => {
		const { data } = await api.get(`/admin/caregivers/${id}/students`);
		return unwrapList<ChildDetails>(data);
	},

	sendCaregiverEmail: async (
		id: string,
		payload: { subject: string; message: string },
	): Promise<{ ok: boolean }> => {
		const { data } = await api.post(`/admin/caregivers/${id}/email`, payload);
		return data;
	},

	// Attendance History
	getAttendanceHistory: async (
		occurrenceId: string,
		childId?: string,
	): Promise<AttendanceRecord[]> => {
		const params = childId ? `?child_id=${childId}` : '';
		const { data } = await api.get(
			`/admin/occurrences/${occurrenceId}/attendance-history${params}`,
		);
		return unwrapList<AttendanceRecord>(data);
	},

	// Communications
	bulkEmailSession: async (
		sessionId: string,
		payload: { subject: string; message: string; actor?: string | null },
	): Promise<{ enqueued: number }> => {
		const { data } = await api.post(`/admin/sessions/${sessionId}/email`, payload);
		return data;
	},
};
