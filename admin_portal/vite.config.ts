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
	define: {
		// Set API base URL for development
		'import.meta.env.API_BASE_URL': JSON.stringify(''),
	},
	build: {
		// Ensure assets are referenced with relative paths
		assetsDir: 'assets',
	},
});
