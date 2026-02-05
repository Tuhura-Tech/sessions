import type React from 'react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../lib/api';

const Login: React.FC = () => {
	const navigate = useNavigate();
	const { isAuthenticated } = useAuth();

	useEffect(() => {
		if (isAuthenticated) {
			navigate('/dashboard');
		}
	}, [isAuthenticated, navigate]);

	const handleGoogleLogin = () => {
		const returnTo = encodeURIComponent(`${window.location.origin}/dashboard`);
		window.location.href = `${API_BASE_URL}/api/v1/admin/auth/google/start?returnTo=${returnTo}`;
	};

	return (
		<div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
			<div className="w-full max-w-md space-y-8">
				<div>
					<h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">Admin Portal</h2>
					<p className="mt-2 text-center text-sm text-gray-600">Sign in with your Google account</p>
				</div>
				<div className="mt-8">
					<button
						type="button"
						onClick={handleGoogleLogin}
						className="group relative flex w-full justify-center rounded-md border border-transparent bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:outline-none"
					>
						Sign in with Google
					</button>
				</div>
			</div>
		</div>
	);
};

export default Login;
