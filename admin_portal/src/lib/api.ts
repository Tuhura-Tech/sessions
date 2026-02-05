import axios from 'axios';

// Always call the API directly (no nginx proxy). Prefer explicit env, fall back to dev/prod defaults.
const env = (import.meta as { env?: Record<string, string | undefined> }).env || {};
const fallbackBaseUrl = '';
export const API_BASE_URL =
	(env.VITE_API_BASE_URL as string | undefined) ||
	(env.API_BASE_URL as string | undefined) ||
	(env.PUBLIC_BASE_URL as string | undefined) ||
	fallbackBaseUrl;

const baseURL =
	API_BASE_URL?.endsWith('/api/v1')
		? API_BASE_URL
		: API_BASE_URL
			? `${API_BASE_URL}/api/v1`
			: '/api/v1';

const api = axios.create({
	baseURL,
	withCredentials: true, // Important for cookie-based auth
});

api.interceptors.request.use((config) => {
	try {
		const win = window as typeof window & { __adminToken?: string };
		const token = win?.__adminToken || localStorage.getItem('adminToken');
		if (token) {
			config.headers = config.headers || {};
			config.headers.Authorization = `Bearer ${token}`;
		}
	} catch {
		// Ignore if window/localStorage not available
	}
	return config;
});

api.interceptors.response.use(
	(response) => response,
	(error) => {
		if (error.response?.status === 401 || error.response?.status === 403) {
			// Redirect to login on unauthorized or forbidden
			window.location.href = '/login';
		}
		return Promise.reject(error);
	},
);

export default api;
