import axios from 'axios';

// API Base URL Configuration
//
// Build-time: PUBLIC_BASE_URL is set via Dockerfile ARG at container build time
// - Vite automatically converts environment variable to: import.meta.env.VITE_PUBLIC_BASE_URL
// - This is embedded in the built static files and cannot change at runtime
//
// Runtime behavior:
// - Development: VITE_PUBLIC_BASE_URL is empty, Vite proxy handles /api/v1 requests
// - Production: VITE_PUBLIC_BASE_URL is the actual API URL (e.g., https://api.example.com)
//
// To deploy with a specific API URL:
//   docker build --build-arg PUBLIC_BASE_URL=https://api.yourdomain.com -t admin-portal .

export const API_BASE_URL =
	import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_PUBLIC_BASE_URL || '';

// Build the API base URL
const baseURL = API_BASE_URL?.endsWith('/api/v1')
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
