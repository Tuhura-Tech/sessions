export type ApiLatLng = { lat: number; lng: number };

export type ApiSessionLocationDetails = {
	id: string;
	name: string;
	address: string;
	region: string;
	latlong: ApiLatLng;
};

// Matches backend SessionPublic.
export type ApiSession = {
	id: string;
	name: string;
	age: string;
	time: string;
	day_of_week?: number | null;
	term_summary?: string | null;
	blocks?: string[];
	public_instructions?: string | null;
	arrival_instructions?: string | null;
	what_to_bring?: string | null;
	prerequisites?: string | null;
	waitlist: boolean;
	locationDetails?: ApiSessionLocationDetails | null;
};

export type ApiSessionOccurrence = {
	starts_at: string;
	ends_at: string;
	cancelled?: boolean;
};

export type ApiBlockOccurrences = {
	block_id: string;
	block_name: string;
	block_type: string;
	occurrences: ApiSessionOccurrence[];
};

export type ApiBlock = {
	id: string;
	year: number;
	name: string;
	block_type: string;
	start_date: string;
	end_date: string;
};

export type ApiSessionDetail = ApiSession & {
	occurrences_by_block?: ApiBlockOccurrences[];
};

export type ApiSessionLocation = {
	name: string;
	sessions: ApiSession[];
};

export type ApiPublicSession = {
	id: string;
	name: string;
	age_lower: number;
	age_upper: number;
	day_of_week?: number | null;
	start_time: string;
	end_time: string;
	waitlist?: boolean;
	what_to_bring?: string | null;
	prerequisites?: string | null;
	location?: {
		name: string;
		address: string;
		region: string;
		lat: number;
		lng: number;
	} | null;
};

export type ApiCaregiverMe = {
	id: string;
	email: string;
	name?: string | null;
	phone?: string | null;
	email_verified: boolean;
};

export type ApiChild = {
	id: string;
	name: string;
	dateOfBirth?: string | null;
	mediaConsent?: boolean;
	medicalInfo?: string | null;
	otherInfo?: string | null;
};

export type ApiCaregiverSignup = {
	id: string;
	status: string;
	sessionId: string;
	sessionName: string;
	childId: string;
	childName: string;
};

export type UiSession = {
	id: string;
	name: string;
	address: string;
	latlong: [number, number];
	age: string;
	time: string;
	day_of_week?: number | null;
	term_summary?: string | null;
	blocks?: string[];
	location: string;
	waitlist?: boolean;
	signupLink?: string;
	venueName?: string | null;

	// Optional detail fields (used on session detail pages)
	public_instructions?: string | null;
	arrival_instructions?: string | null;
	what_to_bring?: string | null;
	prerequisites?: string | null;

	occurrences_by_block?: ApiBlockOccurrences[];
};

export type UiSessionLocation = {
	name: string;
	sessions: UiSession[];
};

import { getApiBaseUrl } from '@/config';

export async function fetchSessionLocations(): Promise<UiSessionLocation[]> {
	const baseUrl = getApiBaseUrl();
	const res = await fetch(`${baseUrl}/api/v1/sessions`);
	if (!res.ok) throw new Error(`Failed to fetch sessions: ${res.status}`);
	const payload = (await res.json()) as
		| { items?: ApiSessionLocation[] | ApiPublicSession[] }
		| ApiSessionLocation[]
		| ApiPublicSession[];
	const items = Array.isArray(payload) ? payload : (payload.items ?? []);

	if (items.length === 0) return [];

	const formatTime = (value?: string | null) =>
		value ? value.split(':').slice(0, 2).join(':') : '';

	if ('sessions' in (items[0] as ApiSessionLocation)) {
		const locations = items as ApiSessionLocation[];
		return locations.map((loc) => ({
			name: loc.name,
			sessions: loc.sessions.map((s) => {
				const details = s.locationDetails ?? null;
				return {
					id: s.id,
					name: s.name,
					address: details?.address ?? '',
					latlong: [details?.latlong.lat ?? 0, details?.latlong.lng ?? 0],
					age: s.age,
					time: s.time,
					day_of_week: s.day_of_week ?? null,
					term_summary: s.term_summary ?? null,
					blocks: s.blocks ?? [],
					location: details?.region ?? loc.name,
					waitlist: s.waitlist,
					signupLink: `/signup?session=${s.id}`,
					venueName: details?.name ?? null,
					public_instructions: s.public_instructions ?? null,
					arrival_instructions: s.arrival_instructions ?? null,
					what_to_bring: s.what_to_bring ?? null,
					prerequisites: s.prerequisites ?? null,
				};
			}),
		}));
	}

	const sessions = items as ApiPublicSession[];

	const grouped = new Map<string, UiSessionLocation>();
	for (const session of sessions) {
		const locationName = session.location?.name ?? 'Unknown location';
		const group = grouped.get(locationName) ?? {
			name: locationName,
			sessions: [],
		};

		group.sessions.push({
			id: session.id,
			name: session.name,
			address: session.location?.address ?? '',
			latlong: [session.location?.lat ?? 0, session.location?.lng ?? 0],
			age: `${session.age_lower}-${session.age_upper}`,
			time: `${formatTime(session.start_time)}-${formatTime(session.end_time)}`,
			day_of_week: session.day_of_week ?? null,
			term_summary: null,
			blocks: [],
			location: session.location?.region ?? locationName,
			waitlist: session.waitlist ?? false,
			signupLink: `/signup?session=${session.id}`,
			venueName: session.location?.name ?? null,
			public_instructions: null,
			arrival_instructions: null,
			what_to_bring: session.what_to_bring ?? null,
			prerequisites: session.prerequisites ?? null,
		});

		grouped.set(locationName, group);
	}

	return Array.from(grouped.values());
}

async function apiFetch(path: string, init?: RequestInit, cookies?: string): Promise<Response> {
	const baseUrl = getApiBaseUrl();
	const fullUrl = `${baseUrl}${path}`;
	return fetch(fullUrl, {
		...init,
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json',
			...(init?.headers || {}),
			...(cookies ? { cookie: cookies } : {}),
		},
	});
}

export async function fetchMe(cookies?: string): Promise<ApiCaregiverMe | null> {
	const res = await apiFetch('/api/v1/me', undefined, cookies);
	if (res.status === 401) return null;
	if (!res.ok) throw new Error(`Failed to fetch me: ${res.status}`);
	return (await res.json()) as ApiCaregiverMe;
}

export async function updateMe(input: {
	name: string;
	phone: string;
	newsletter?: boolean;
	referralSource?: string;
}): Promise<ApiCaregiverMe> {
	const payload: Record<string, unknown> = {
		name: input.name,
		phone: input.phone,
	};
	if (typeof input.newsletter === 'boolean') {
		payload.subscribe_newsletter = input.newsletter;
	}
	if (input.referralSource) {
		payload.referral_source = input.referralSource;
	}

	const res = await apiFetch('/api/v1/me', { method: 'PATCH', body: JSON.stringify(payload) });
	if (!res.ok) throw new Error(`Failed to update me: ${res.status}`);
	return (await res.json()) as ApiCaregiverMe;
}

export async function requestMagicLink(
	email: string,
	returnTo?: string,
): Promise<{ ok: boolean; debugToken?: string | null }> {
	const res = await apiFetch('/api/v1/auth/magic-link', {
		method: 'POST',
		body: JSON.stringify({ email, return_to: returnTo }),
	});
	if (!res.ok) throw new Error(`Failed to request magic link: ${res.status}`);
	return (await res.json()) as { ok: boolean; debugToken?: string | null };
}

export function redirectToAuth(returnTo?: string): void {
	const url = new URL('/auth/magic-url', window.location.origin);
	if (returnTo) {
		url.searchParams.set('returnTo', returnTo);
	}
	window.location.href = url.toString();
}

export async function logout(): Promise<{ ok: boolean }> {
	const res = await apiFetch('/api/v1/auth/logout', { method: 'POST' });
	if (!res.ok) throw new Error(`Failed to logout: ${res.status}`);
	return (await res.json()) as { ok: boolean };
}

export async function listChildren(cookies?: string): Promise<ApiChild[]> {
	const res = await apiFetch('/api/v1/students', undefined, cookies);
	if (!res.ok) throw new Error(`Failed to list children: ${res.status}`);
	const payload = (await res.json()) as Array<Record<string, unknown>>;
	return payload.map((child) => ({
		id: String(child.id),
		name: String(child.name),
		dateOfBirth:
			(child.dateOfBirth as string | null | undefined) ??
			(child.date_of_birth as string | null | undefined) ??
			null,
		mediaConsent:
			(child.mediaConsent as boolean | undefined) ??
			(child.media_consent as boolean | undefined) ??
			false,
		medicalInfo:
			(child.medicalInfo as string | null | undefined) ??
			(child.medical_info as string | null | undefined) ??
			null,
		otherInfo:
			(child.otherInfo as string | null | undefined) ??
			(child.other_info as string | null | undefined) ??
			null,
	}));
}

export async function createChild(input: {
	name: string;
	dateOfBirth: string;
	mediaConsent?: boolean;
	medicalInfo?: string;
	otherInfo?: string;
	region?: string;
	ethnicity?: string;
	gender?: string;
	schoolName?: string;
}): Promise<ApiChild> {
	const payload: Record<string, unknown> = {
		name: input.name,
		date_of_birth: input.dateOfBirth,
		media_consent: input.mediaConsent ?? false,
		medical_info: input.medicalInfo ?? null,
		other_info: input.otherInfo ?? null,
		region: input.region ?? null,
		ethnicity: input.ethnicity ?? null,
		school_name: input.schoolName ?? null,
		gender: input.gender ?? null,
	};
	const res = await apiFetch('/api/v1/students', { method: 'POST', body: JSON.stringify(payload) });
	if (!res.ok) throw new Error(`Failed to create child: ${res.status}`);
	return (await res.json()) as ApiChild;
}

export async function updateChild(
	childId: string,
	input: { name?: string | null; dateOfBirth?: string | null },
): Promise<ApiChild> {
	const payload: Record<string, unknown> = {};
	if (input.name !== undefined) payload.name = input.name;
	if (input.dateOfBirth !== undefined) payload.date_of_birth = input.dateOfBirth;

	const res = await apiFetch(`/api/v1/students/${childId}`, {
		method: 'PATCH',
		body: JSON.stringify(payload),
	});
	if (!res.ok) throw new Error(`Failed to update child: ${res.status}`);
	return (await res.json()) as ApiChild;
}

export async function listMySignups(cookies?: string): Promise<ApiCaregiverSignup[]> {
	const res = await apiFetch('/api/v1/signups/', undefined, cookies);
	if (!res.ok) throw new Error(`Failed to list signups: ${res.status}`);
	const payload = (await res.json()) as Array<Record<string, unknown>>;
	return payload.map((signup) => ({
		id: String(signup.id),
		status: String(signup.status),
		sessionId: String(signup.sessionId ?? signup.session_id),
		sessionName: String(signup.sessionName ?? signup.session_name),
		childId: String(signup.childId ?? signup.child_id ?? signup.studentId ?? signup.student_id),
		childName: String(
			signup.childName ?? signup.child_name ?? signup.studentName ?? signup.student_name,
		),
	}));
}

export async function createAuthenticatedSignup(
	sessionId: string,
	input: {
		childId: string;
		pickupDropoff?: string;
		pairingPreference?: string;
	},
): Promise<{ id: string; status: string }> {
	const payload: Record<string, unknown> = {
		studentId: input.childId,
	};
	if (input.pickupDropoff) {
		payload.pickupDropoff = input.pickupDropoff;
	}
	const res = await apiFetch(`/api/v1/signups/${sessionId}`, {
		method: 'POST',
		body: JSON.stringify(payload),
	});
	if (!res.ok) throw new Error(`Failed to create signup: ${res.status}`);
	return (await res.json()) as { id: string; status: string };
}

export async function withdrawSignup(signupId: string): Promise<{ ok: boolean }> {
	const res = await apiFetch(`/api/v1/signups/${signupId}`, {
		method: 'DELETE',
	});
	if (!res.ok) throw new Error(`Failed to withdraw signup: ${res.status}`);
	return { ok: true };
}

export async function fetchFlatSessions(): Promise<UiSession[]> {
	const locations = await fetchSessionLocations();
	return locations.flatMap((location) => location.sessions);
}

export async function fetchSessionById(id: string): Promise<UiSession | null> {
	const baseUrl = getApiBaseUrl();
	const res = await fetch(`${baseUrl}/api/v1/sessions/${id}`);
	if (res.status === 404) return null;
	if (!res.ok) throw new Error(`Failed to fetch session: ${res.status}`);

	const payload = (await res.json()) as ApiSessionDetail & {
		age_lower?: number;
		age_upper?: number;
		start_time?: string;
		end_time?: string;
		location?: { name: string; address: string; region: string; lat: number; lng: number } | null;
	};
	const formatTime = (value?: string | null) =>
		value ? value.split(':').slice(0, 2).join(':') : '';

	const details = payload.locationDetails ?? null;
	if (details) {
		return {
			id: payload.id,
			name: payload.name,
			address: details.address ?? '',
			latlong: [details.latlong.lat ?? 0, details.latlong.lng ?? 0],
			age: payload.age,
			time: payload.time,
			day_of_week: payload.day_of_week ?? null,
			term_summary: payload.term_summary ?? null,
			blocks: payload.blocks ?? [],
			location: details.region ?? '',
			waitlist: payload.waitlist,
			signupLink: `/signup?session=${payload.id}`,
			venueName: details.name ?? null,
			public_instructions: payload.public_instructions ?? null,
			arrival_instructions: payload.arrival_instructions ?? null,
			what_to_bring: payload.what_to_bring ?? null,
			prerequisites: payload.prerequisites ?? null,
			occurrences_by_block: payload.occurrences_by_block ?? [],
		};
	}

	return {
		id: payload.id,
		name: payload.name,
		address: payload.location?.address ?? '',
		latlong: [payload.location?.lat ?? 0, payload.location?.lng ?? 0],
		age:
			payload.age_lower !== undefined && payload.age_upper !== undefined
				? `${payload.age_lower}-${payload.age_upper}`
				: (payload.age ?? ''),
		time:
			payload.start_time && payload.end_time
				? `${formatTime(payload.start_time)}-${formatTime(payload.end_time)}`
				: (payload.time ?? ''),
		day_of_week: payload.day_of_week ?? null,
		term_summary: payload.term_summary ?? null,
		blocks: payload.blocks ?? [],
		location: payload.location?.region ?? '',
		waitlist: payload.waitlist ?? false,
		signupLink: `/signup?session=${payload.id}`,
		venueName: payload.location?.name ?? null,
		public_instructions: payload.public_instructions ?? null,
		arrival_instructions: payload.arrival_instructions ?? null,
		what_to_bring: payload.what_to_bring ?? null,
		prerequisites: payload.prerequisites ?? null,
		occurrences_by_block: payload.occurrences_by_block ?? [],
	};
}

export async function fetchBlocks(): Promise<ApiBlock[]> {
	const baseUrl = getApiBaseUrl();
	const res = await fetch(`${baseUrl}/api/v1/blocks`);
	if (!res.ok) throw new Error(`Failed to fetch blocks: ${res.status}`);
	const payload = (await res.json()) as { items?: ApiBlock[] } | ApiBlock[];
	return Array.isArray(payload) ? payload : (payload.items ?? []);
}
