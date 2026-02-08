import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [react(), tailwindcss()],
	server: {
		port: 3002,
		proxy: {
			'/api/v1': 'http://localhost:8000',
		},
	},
	// Vite automatically reads VITE_* prefixed environment variables
	// VITE_PUBLIC_BASE_URL is set at build time via Docker build argument
	// In development, it's empty and Vite proxy handles /api/v1 requests
	build: {
		// Ensure assets are referenced with relative paths
		assetsDir: 'assets',
	},
});
