import node from '@astrojs/node';
import sitemap from '@astrojs/sitemap';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'astro/config';

// Allowed origins for CORS
const ALLOWED_ORIGINS = [
	'https://sessions.tuhuratech.org.nz',
	'https://admin.tuhuratech.org.nz',
	'https://www.tuhuratech.org.nz',
];

// Allow localhost in development
if (process.env.NODE_ENV === 'development') {
	ALLOWED_ORIGINS.push('http://localhost:3000', 'http://localhost:5173', 'http://localhost:5174');
}

// https://astro.build/config
export default defineConfig({
	output: 'server',
	adapter: node({ mode: 'standalone' }),
	site: 'https://sessions.tuhuratech.org.nz',
	integrations: [sitemap()],

	image: {
		service: {
			entrypoint: 'astro/assets/services/sharp',
		},
	},

	vite: {
		plugins: [tailwindcss()],
		optimizeDeps: { include: ['leaflet'] },
		cors: {
			origin: ALLOWED_ORIGINS,
			methods: ['GET', 'HEAD', 'PUT', 'PATCH', 'POST', 'DELETE'],
			credentials: true,
			preflightContinue: true,
			optionsSuccessStatus: 204,
		},
	},
	security: {
		checkOrigin: true,
	},
});
