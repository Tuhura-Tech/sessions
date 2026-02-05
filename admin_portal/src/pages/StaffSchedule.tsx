import { Calendar, ChevronLeft, ChevronRight, Clock, Filter, MapPin, Users } from 'lucide-react';
import type React from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { FormCheckbox } from '../components/FormComponents';
import Layout from '../components/Layout';
import Sidebar from '../components/Sidebar';
import { adminApi } from '../services/api';
import type { Staff, StaffAvailability, StaffSessionSummary } from '../types';

interface DaySchedule {
	dayOfWeek: number;
	dayName: string;
	sessions: StaffSessionSummary[];
}

interface StaffScheduleData {
	staff: Staff;
	sessions: StaffSessionSummary[];
	schedule: DaySchedule[];
}

const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

const StaffSchedulePage: React.FC = () => {
	const [availability, setAvailability] = useState<StaffAvailability[]>([]);
	const [scheduleData, setScheduleData] = useState<StaffScheduleData[]>([]);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const [activeOnly, setActiveOnly] = useState(true);
	const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear());
	const [viewMode, setViewMode] = useState<'weekly' | 'workload'>('weekly');
	const [selectedDay, setSelectedDay] = useState<number | null>(null);
	const [searchQuery, setSearchQuery] = useState('');

	const loadStaffSchedule = useCallback(async () => {
		try {
			setIsLoading(true);
			setError(null);

			// Load staff list and availability
			const [staff, avail] = await Promise.all([
				adminApi.getStaff(activeOnly),
				adminApi.getStaffAvailability(selectedYear, activeOnly),
			]);

			setAvailability(avail);

			// Load sessions for each staff member
			const schedules = await Promise.all(
				staff.map(async (s) => {
					const sessions = await adminApi.getStaffSessions(s.id);
					console.log(`Staff ${s.name} sessions:`, sessions);

					// Group sessions by day of week
					const schedule: DaySchedule[] = DAYS.map((dayName, dayOfWeek) => ({
						dayOfWeek,
						dayName,
						sessions: sessions.filter((sess) => {
							// Handle both null and number values for dayOfWeek
							if (sess.dayOfWeek === null || sess.dayOfWeek === undefined) {
								console.log(`Session ${sess.name} has null/undefined dayOfWeek`);
								return false;
							}
							const matches = Number(sess.dayOfWeek) === dayOfWeek;
							if (matches) {
								console.log(`Session ${sess.name} matches day ${dayOfWeek} (${dayName})`);
							}
							return matches;
						}),
					}));

					console.log(`Staff ${s.name} schedule:`, schedule);

					return {
						staff: s,
						sessions,
						schedule,
					};
				}),
			);

			setScheduleData(schedules);
		} catch (err) {
			console.error(err);
			setError('Failed to load staff schedules');
		} finally {
			setIsLoading(false);
		}
	}, [activeOnly, selectedYear]);

	useEffect(() => {
		loadStaffSchedule();
	}, [loadStaffSchedule]);

	const filteredSchedules = useMemo(() => {
		let filtered = scheduleData;

		// Filter by search query
		if (searchQuery) {
			const query = searchQuery.toLowerCase();
			filtered = filtered.filter(
				(s) =>
					s.staff.name.toLowerCase().includes(query) ||
					s.staff.email.toLowerCase().includes(query) ||
					s.sessions.some((sess) => sess.name.toLowerCase().includes(query)),
			);
		}

		// Filter by selected day
		if (selectedDay !== null) {
			filtered = filtered.filter((s) => s.schedule[selectedDay].sessions.length > 0);
		}

		return filtered;
	}, [scheduleData, searchQuery, selectedDay]);

	const workloadStats = useMemo(() => {
		const stats = availability.map((a) => {
			const schedule = scheduleData.find((s) => s.staff.id === a.staff_id);
			const daysCovered = schedule
				? schedule.schedule.filter((d) => d.sessions.length > 0).length
				: 0;

			return {
				...a,
				daysCovered,
			};
		});

		// Sort by session count descending
		return stats.sort((a, b) => b.assigned_session_count - a.assigned_session_count);
	}, [availability, scheduleData]);

	const changeYear = (delta: number) => {
		setSelectedYear((prev) => prev + delta);
	};

	return (
		<div className="flex min-h-screen">
			<Sidebar />
			<div className="flex-1">
				<Layout
					title="Staff Schedule"
					actions={
						<div className="flex items-center gap-3">
							<label className="inline-flex items-center text-sm text-gray-700">
								<FormCheckbox
									checked={activeOnly}
									onChange={(e) => setActiveOnly(e.target.checked)}
								/>
								<span className="ml-2">Active only</span>
							</label>

							<div className="flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-2">
								<button
									type="button"
									onClick={() => changeYear(-1)}
									className="text-gray-600 hover:text-gray-900"
								>
									<ChevronLeft className="h-4 w-4" />
								</button>
								<span className="text-sm font-medium text-gray-900">{selectedYear}</span>
								<button
									type="button"
									onClick={() => changeYear(1)}
									className="text-gray-600 hover:text-gray-900"
								>
									<ChevronRight className="h-4 w-4" />
								</button>
							</div>

							<div className="flex rounded-md border border-gray-300 bg-white">
								<button
									type="button"
									onClick={() => setViewMode('weekly')}
									className={`px-4 py-2 text-sm font-medium ${
										viewMode === 'weekly'
											? 'bg-blue-600 text-white'
											: 'text-gray-700 hover:bg-gray-50'
									}`}
								>
									<Calendar className="mr-2 inline h-4 w-4" />
									Weekly
								</button>
								<button
									type="button"
									onClick={() => setViewMode('workload')}
									className={`px-4 py-2 text-sm font-medium ${
										viewMode === 'workload'
											? 'bg-blue-600 text-white'
											: 'text-gray-700 hover:bg-gray-50'
									}`}
								>
									<Users className="mr-2 inline h-4 w-4" />
									Workload
								</button>
							</div>
						</div>
					}
				>
					{error && (
						<div className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-700">{error}</div>
					)}

					<div className="mb-4 flex items-center gap-4">
						<div className="flex-1">
							<input
								type="text"
								placeholder="Search staff or sessions..."
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.target.value)}
								className="w-full rounded-md border border-gray-300 px-4 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
							/>
						</div>

						<div className="flex items-center gap-2">
							<Filter className="h-4 w-4 text-gray-500" />
							<select
								value={selectedDay ?? ''}
								onChange={(e) => setSelectedDay(e.target.value ? Number(e.target.value) : null)}
								className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
							>
								<option value="">All days</option>
								{DAYS.map((day, idx) => (
									<option key={idx} value={idx}>
										{day}
									</option>
								))}
							</select>
						</div>
					</div>

					{isLoading ? (
						<div className="flex items-center justify-center py-12">
							<div className="text-gray-500">Loading schedules...</div>
						</div>
					) : viewMode === 'weekly' ? (
						<div className="space-y-6">
							{filteredSchedules.length === 0 ? (
								<div className="rounded-lg bg-white p-8 text-center shadow">
									<p className="text-gray-500">No staff schedules found</p>
								</div>
							) : (
								filteredSchedules.map((data) => (
									<div key={data.staff.id} className="rounded-lg bg-white shadow">
										<div className="border-b border-gray-200 px-6 py-4">
											<div className="flex items-center justify-between">
												<div>
													<h3 className="text-lg font-semibold text-gray-900">{data.staff.name}</h3>
													<p className="text-sm text-gray-500">{data.staff.email}</p>
												</div>
												<div className="text-right">
													<div className="text-2xl font-bold text-blue-600">
														{data.sessions.length}
													</div>
													<div className="text-xs text-gray-500">
														session{data.sessions.length !== 1 ? 's' : ''}
													</div>
												</div>
											</div>
										</div>

										<div className="grid grid-cols-7 gap-px bg-gray-200 p-px">
											{data.schedule.map((day) => (
												<div
													key={day.dayOfWeek}
													className={`bg-white p-3 ${
														selectedDay === day.dayOfWeek ? 'ring-2 ring-blue-500' : ''
													}`}
												>
													<div className="mb-2 text-xs font-semibold text-gray-600">
														{day.dayName.slice(0, 3)}
													</div>
													<div className="space-y-2">
														{day.sessions.length === 0 ? (
															<div className="text-xs text-gray-400">—</div>
														) : (
															day.sessions.map((session) => (
																<div key={session.id} className="rounded-md bg-blue-50 p-2 text-xs">
																	<div className="mb-1 font-medium text-blue-900">
																		{session.name}
																	</div>
																	{session.startTime && session.endTime && (
																		<div className="flex items-center gap-1 text-blue-700">
																			<Clock className="h-3 w-3" />
																			{session.startTime} - {session.endTime}
																		</div>
																	)}
																	{session.locationName && (
																		<div className="mt-1 flex items-center gap-1 text-blue-600">
																			<MapPin className="h-3 w-3" />
																			<span className="truncate">{session.locationName}</span>
																		</div>
																	)}
																</div>
															))
														)}
													</div>
												</div>
											))}
										</div>
									</div>
								))
							)}
						</div>
					) : (
						<div className="rounded-lg bg-white shadow">
							<div className="border-b border-gray-200 px-6 py-4">
								<h3 className="text-lg font-semibold text-gray-900">Staff Workload</h3>
								<p className="text-sm text-gray-500">
									Session assignments per staff member for {selectedYear}
								</p>
							</div>

							<div className="overflow-x-auto">
								<table className="min-w-full divide-y divide-gray-200">
									<thead className="bg-gray-50">
										<tr>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Staff
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Sessions
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Days/Week
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Workload
											</th>
										</tr>
									</thead>
									<tbody className="divide-y divide-gray-200 bg-white">
										{workloadStats.map((stat) => {
											const maxSessions = Math.max(
												...workloadStats.map((s) => s.assigned_session_count),
											);
											const workloadPercent =
												maxSessions > 0 ? (stat.assigned_session_count / maxSessions) * 100 : 0;

											return (
												<tr key={stat.staff_id} className="hover:bg-gray-50">
													<td className="px-6 py-4">
														<div className="text-sm font-medium text-gray-900">{stat.name}</div>
														<div className="text-xs text-gray-500">{stat.email}</div>
													</td>
													<td className="px-6 py-4">
														<div className="text-sm font-semibold text-gray-900">
															{stat.assigned_session_count}
														</div>
													</td>
													<td className="px-6 py-4">
														<div className="text-sm text-gray-600">{stat.daysCovered}</div>
													</td>
													<td className="px-6 py-4">
														<div className="flex items-center gap-2">
															<div className="h-2 flex-1 rounded-full bg-gray-200">
																<div
																	className={`h-2 rounded-full ${
																		workloadPercent > 80
																			? 'bg-red-500'
																			: workloadPercent > 50
																				? 'bg-yellow-500'
																				: 'bg-green-500'
																	}`}
																	style={{ width: `${workloadPercent}%` }}
																/>
															</div>
															<div className="text-xs text-gray-500">
																{Math.round(workloadPercent)}%
															</div>
														</div>
													</td>
												</tr>
											);
										})}
									</tbody>
								</table>
							</div>
						</div>
					)}
				</Layout>
			</div>
		</div>
	);
};

export default StaffSchedulePage;
