import { Plus, Search } from 'lucide-react';
import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import Sidebar from '../components/Sidebar';
import { adminApi } from '../services/api';
import type { Session } from '../types';

function dayOfWeekAsString(dayIndex: number | null): string {
	if (dayIndex === null || dayIndex === undefined) return '';
	return (
		['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][dayIndex] || ''
	);
}

const Sessions: React.FC = () => {
	const [sessions, setSessions] = useState<Session[]>([]);
	const [filteredSessions, setFilteredSessions] = useState<Session[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [searchTerm, setSearchTerm] = useState('');
	const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
	const [showArchived, setShowArchived] = useState(false);

	const loadSessions = useCallback(async () => {
		try {
			setIsLoading(true);
			const data = await adminApi.getSessions(selectedYear, showArchived);
			setSessions(data);
			setFilteredSessions(data);
		} catch (error) {
			console.error('Failed to load sessions:', error);
		} finally {
			setIsLoading(false);
		}
	}, [selectedYear, showArchived]);

	useEffect(() => {
		loadSessions();
	}, [loadSessions]);

	useEffect(() => {
		const filtered = sessions.filter((session) =>
			session.name.toLowerCase().includes(searchTerm.toLowerCase()),
		);
		setFilteredSessions(filtered);
	}, [searchTerm, sessions]);

	const years = [2024, 2025, 2026];

	return (
		<div className="flex min-h-screen">
			<Sidebar />

			<div className="flex-1">
				<Layout
					title="Sessions"
					actions={
						<Link
							to="/sessions/new"
							className="inline-flex items-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
						>
							<Plus className="mr-2 h-4 w-4" />
							New Session
						</Link>
					}
				>
					{/* Filters */}
					<div className="mb-6 rounded-lg bg-white p-4 shadow">
						<div className="grid grid-cols-1 gap-4 md:grid-cols-4">
							<div className="relative">
								<Search className="absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 transform text-gray-400" />
								<input
									type="text"
									placeholder="Search sessions..."
									value={searchTerm}
									onChange={(e) => setSearchTerm(e.target.value)}
									className="w-full rounded-md border-gray-300 pl-10 shadow-sm focus:border-blue-500 focus:ring-blue-500"
								/>
							</div>

							<select
								value={selectedYear}
								onChange={(e) => setSelectedYear(Number(e.target.value))}
								className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
							>
								{years.map((year) => (
									<option key={year} value={year}>
										{year}
									</option>
								))}
							</select>

							<label className="flex items-center">
								<input
									type="checkbox"
									checked={showArchived}
									onChange={(e) => setShowArchived(e.target.checked)}
									className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
								/>
								<span className="ml-2 text-sm text-gray-700">Show archived</span>
							</label>
						</div>
					</div>

					{/* Sessions List */}
					<div className="overflow-hidden rounded-lg bg-white shadow">
						{isLoading ? (
							<div className="flex h-64 items-center justify-center">
								<div className="h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600" />
							</div>
						) : filteredSessions.length === 0 ? (
							<div className="py-12 text-center text-gray-500">No sessions found</div>
						) : (
							<div className="overflow-x-auto">
								<table className="min-w-full divide-y divide-gray-200">
									<thead className="bg-gray-50">
										<tr>
											<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
												Name
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
												Location
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
												Schedule
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
												Capacity
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
												Signups
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
												Status
											</th>
											<th className="px-6 py-3 text-right text-xs font-medium tracking-wider text-gray-500 uppercase">
												Actions
											</th>
										</tr>
									</thead>
									<tbody className="divide-y divide-gray-200 bg-white">
										{filteredSessions.map((session) => (
											<tr key={session.id} className="hover:bg-gray-50">
												<td className="px-6 py-4 whitespace-nowrap">
													<Link
														to={`/sessions/${session.id}`}
														className="text-sm font-medium text-blue-600 hover:text-blue-900"
													>
														{session.name}
													</Link>
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
													{session.location ? (
														<Link
															to={`/locations/${session.location.id}`}
															className="text-blue-600 hover:text-blue-900"
														>
															{session.location.name}
														</Link>
													) : (
														<span className="text-gray-400">No location</span>
													)}
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
													{dayOfWeekAsString(session.day_of_week)} {session.start_time}-
													{session.end_time}
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
													{session.capacity || 'N/A'}
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
													<div className="flex items-center gap-2">
														<span>
															{session.confirmed_count || 0}/{session.capacity || '?'}
														</span>
														{session.pending_count ? (
															<span className="inline-flex rounded-full bg-amber-100 px-2 py-1 text-xs leading-4 font-semibold text-amber-800">
																+{session.pending_count} pending
															</span>
														) : null}
													</div>
												</td>
												<td className="px-6 py-4 whitespace-nowrap">
													<span
														className={`inline-flex rounded-full px-2 py-1 text-xs leading-5 font-semibold ${
															session.archived
																? 'bg-gray-100 text-gray-800'
																: session.waitlist
																	? 'bg-yellow-100 text-yellow-800'
																	: 'bg-green-100 text-green-800'
														}`}
													>
														{session.archived
															? 'Archived'
															: session.waitlist
																? 'Waitlist'
																: 'Active'}
													</span>
												</td>
												<td className="px-6 py-4 text-right text-sm font-medium whitespace-nowrap">
													<Link
														to={`/sessions/${session.id}/edit`}
														className="mr-4 text-blue-600 hover:text-blue-900"
													>
														Edit
													</Link>
													<Link
														to={`/sessions/${session.id}`}
														className="text-gray-600 hover:text-gray-900"
													>
														View
													</Link>
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						)}
					</div>
				</Layout>
			</div>
		</div>
	);
};

export default Sessions;
