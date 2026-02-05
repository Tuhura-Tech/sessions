import { Calendar, Check, MapPin, X } from 'lucide-react';
import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { LoadingSpinner } from '../components/Alert';
import CalendarView from '../components/CalendarView';
import Layout from '../components/Layout';
import Sidebar from '../components/Sidebar';
import { adminApi } from '../services/api';
import type { Session } from '../types';

const Dashboard: React.FC = () => {
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [fullSessions, setFullSessions] = useState(0);
	const [notFullSessions, setNotFullSessions] = useState(0);

	const loadDashboardData = useCallback(async () => {
		try {
			setIsLoading(true);
			setError(null);
			// Load sessions and calculate full/not-full
			const sessions = await adminApi.getSessions(new Date().getFullYear());
			const full = sessions.filter((s: Session) => s.is_full).length;
			const notFull = sessions.length - full;
			setFullSessions(full);
			setNotFullSessions(notFull);
		} catch (err) {
			console.error('Failed to load dashboard data:', err);
			setError('Failed to load dashboard data. Please try again.');
		} finally {
			setIsLoading(false);
		}
	}, []);

	useEffect(() => {
		loadDashboardData();
	}, [loadDashboardData]);

	return (
		<div className="flex min-h-screen">
			<Sidebar />

			<div className="flex-1">
				<Layout title="Dashboard">
					{error && (
						<div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700">
							{error}
						</div>
					)}

					{isLoading ? (
						<LoadingSpinner />
					) : (
						<>
							{/* Stats */}
							<div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-2">
								<div className="rounded-lg bg-white p-6 shadow">
									<div className="flex items-center gap-4">
										<div className="rounded-full bg-green-100 p-3 text-green-600">
											<Check className="h-6 w-6" />
										</div>
										<div>
											<p className="text-sm text-gray-500">Full Sessions</p>
											<p className="text-2xl font-bold text-gray-900">{fullSessions}</p>
										</div>
									</div>
								</div>

								<div className="rounded-lg bg-white p-6 shadow">
									<div className="flex items-center gap-4">
										<div className="rounded-full bg-blue-100 p-3 text-blue-600">
											<X className="h-6 w-6" />
										</div>
										<div>
											<p className="text-sm text-gray-500">Available Sessions</p>
											<p className="text-2xl font-bold text-gray-900">{notFullSessions}</p>
										</div>
									</div>
								</div>
							</div>

							{/* Quick Actions */}
							<div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-3">
								<Link
									to="/sessions/new"
									className="group flex items-center gap-4 rounded-lg bg-white p-6 shadow transition-shadow hover:shadow-lg"
								>
									<div className="rounded-full bg-blue-50 p-3 text-blue-600 group-hover:bg-blue-100">
										<Calendar className="h-6 w-6" />
									</div>
									<div>
										<h3 className="font-semibold text-gray-900 group-hover:text-blue-600">
											New Session
										</h3>
										<p className="text-sm text-gray-500">Create a new session</p>
									</div>
								</Link>

								<Link
									to="/locations"
									className="group flex items-center gap-4 rounded-lg bg-white p-6 shadow transition-shadow hover:shadow-lg"
								>
									<div className="rounded-full bg-purple-50 p-3 text-purple-600 group-hover:bg-purple-100">
										<MapPin className="h-6 w-6" />
									</div>
									<div>
										<h3 className="font-semibold text-gray-900 group-hover:text-purple-600">
											Locations
										</h3>
										<p className="text-sm text-gray-500">Manage venues</p>
									</div>
								</Link>
							</div>

							{/* Calendar View */}
							<div className="mb-8">
								<CalendarView />
							</div>
						</>
					)}
				</Layout>
			</div>
		</div>
	);
};

export default Dashboard;
