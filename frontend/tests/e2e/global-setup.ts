import { execSync, spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const sleep = promisify(setTimeout);

// Store backend process for cleanup
let backendProcess: ReturnType<typeof spawn> | null = null;

export default async function globalSetup() {
	const dirname = path.dirname(fileURLToPath(import.meta.url));
	const backendDir = path.resolve(dirname, '../../../backend');

	console.log('🔵 [Global Setup] Seeding database...');
	execSync('uv run python scripts/seed.py', {
		cwd: backendDir,
		stdio: 'inherit',
		env: {
			...process.env,
			LITESTAR_APP: process.env.LITESTAR_APP || 'app.server.asgi:create_app',
		},
	});

	console.log('🔵 [Global Setup] Starting backend server...');
	backendProcess = spawn('uv', ['run', 'python', 'main.py'], {
		cwd: backendDir,
		stdio: 'pipe',
		env: {
			...process.env,
			LITESTAR_APP: process.env.LITESTAR_APP || 'app.server.asgi:create_app',
		},
	});

	let backendReady = false;
	let attempts = 0;
	const maxAttempts = 30; // 30 seconds timeout

	// Wait for backend to start
	while (!backendReady && attempts < maxAttempts) {
		try {
			const response = await fetch('http://localhost:8000/api/v1/health', {
				method: 'GET',
				headers: { 'Content-Type': 'application/json' },
			});
			if (response.ok) {
				backendReady = true;
				console.log('✅ [Global Setup] Backend server ready');
				break;
			}
		} catch {
			// Backend not ready yet
		}

		await sleep(1000);
		attempts++;
	}

	if (!backendReady) {
		console.error('❌ [Global Setup] Backend failed to start after 30 seconds');
		if (backendProcess) {
			backendProcess.kill();
		}
		throw new Error('Backend server failed to start');
	}

	// Register cleanup
	process.on('exit', () => {
		if (backendProcess) {
			console.log('🔵 [Global Setup] Stopping backend server...');
			backendProcess.kill();
		}
	});
}
