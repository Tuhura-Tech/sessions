import { execSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export default async function globalSetup() {
	const dirname = path.dirname(fileURLToPath(import.meta.url));
	const backendDir = path.resolve(dirname, '../../../backend');

	console.log('🔵 [Global Setup] Resetting database schema...');
	execSync('uv run python scripts/reset_test_db.py', {
		cwd: backendDir,
		stdio: 'inherit',
		env: {
			...process.env,
		},
	});

	console.log('🔵 [Global Setup] Running migrations...');
	execSync('uv run litestar database upgrade --no-prompt', {
		cwd: backendDir,
		stdio: 'inherit',
		env: {
			...process.env,
		},
	});

	console.log('🔵 [Global Setup] Seeding database...');
	execSync('uv run python scripts/seed.py', {
		cwd: backendDir,
		stdio: 'inherit',
		env: {
			...process.env,
		},
	});
}
