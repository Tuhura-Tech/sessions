import { ArrowLeft, Save } from 'lucide-react';
import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Layout from '../components/Layout';
import Sidebar from '../components/Sidebar';
import { adminApi } from '../services/api';
import type { AttendanceRoll, AttendanceUpsert, Session } from '../types';

const AttendanceRollPage: React.FC = () => {
	const { occurrenceId } = useParams<{ occurrenceId: string }>();
	const navigate = useNavigate();
	const [roll, setRoll] = useState<AttendanceRoll | null>(null);
	const [session, setSession] = useState<Session | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [isSaving, setIsSaving] = useState(false);
	const [changes, setChanges] = useState<Map<string, AttendanceUpsert>>(new Map());

	const loadRoll = useCallback(async (id: string) => {
		try {
			setIsLoading(true);
			const data = await adminApi.getAttendanceRoll(id);
			setRoll(data);

			// Load session data to get full session details
			if (data.session_id) {
				const sessionData = await adminApi.getSession(data.session_id);
				setSession(sessionData);
			}
		} catch (error) {
			console.error('Failed to load attendance roll:', error);
		} finally {
			setIsLoading(false);
		}
	}, []);

	useEffect(() => {
		if (occurrenceId) {
			loadRoll(occurrenceId);
		}
	}, [occurrenceId, loadRoll]);

	const handleStatusChange = (
		studentId: string,
		status: 'present' | 'absent_known' | 'absent_unknown',
	) => {
		const newChanges = new Map(changes);
		newChanges.set(studentId, { student_id: studentId, status });
		setChanges(newChanges);
	};

	const handleSaveAll = async () => {
		if (!occurrenceId || changes.size === 0) return;

		try {
			setIsSaving(true);

			for (const [, attendance] of changes) {
				await adminApi.markAttendance(occurrenceId, attendance);
			}

			setChanges(new Map());
			await loadRoll(occurrenceId);
			alert('Attendance saved successfully');
		} catch (error) {
			console.error('Failed to save attendance:', error);
			alert('Failed to save attendance');
		} finally {
			setIsSaving(false);
		}
	};

	const getStatusForStudent = (studentId: string, currentStatus: string | null) => {
		const change = changes.get(studentId);
		return change ? change.status : currentStatus || '';
	};

	if (isLoading) {
		return (
			<div className="flex min-h-screen">
				<Sidebar />
				<div className="flex flex-1 items-center justify-center">
					<div className="h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600" />
				</div>
			</div>
		);
	}

	if (!roll) {
		return (
			<div className="flex min-h-screen">
				<Sidebar />
				<div className="flex-1">
					<Layout title="Occurrence Not Found">
						<p className="text-gray-500">Occurrence not found</p>
					</Layout>
				</div>
			</div>
		);
	}

	if (!roll.occurrence_id) {
		return (
			<div className="flex min-h-screen">
				<Sidebar />
				<div className="flex-1">
					<Layout title="Occurrence Not Found">
						<p className="text-gray-500">Occurrence data is unavailable</p>
					</Layout>
				</div>
			</div>
		);
	}

	return (
		<div className="flex min-h-screen">
			<Sidebar />

			<div className="flex-1">
				<Layout>
					<button
						type="button"
						onClick={() => navigate(`/sessions/${roll.session_id}`)}
						className="mb-6 flex items-center text-gray-600 hover:text-gray-900"
					>
						<ArrowLeft className="mr-2 h-4 w-4" />
						Back to Session
					</button>

					<div className="overflow-hidden rounded-lg bg-white shadow">
						{/* Header */}
						<div className="border-b border-gray-200 px-6 py-4">
							<div className="flex items-start justify-between">
								<div>
									<h1 className="text-2xl font-bold text-gray-900">{session?.name}</h1>
									<p className="mt-1 text-sm text-gray-600">
										{new Date(roll.starts_at).toLocaleDateString('en-NZ', {
											day: '2-digit',
											month: '2-digit',
											year: 'numeric',
										})}{' '}
										• {session?.day_of_week} {session?.start_time} - {session?.end_time}
									</p>
									{session?.location && (
										<p className="text-sm text-gray-600">{session.location.name}</p>
									)}
									{roll.cancelled && (
										<span className="mt-2 inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
											Cancelled
										</span>
									)}
								</div>

								{changes.size > 0 && (
									<button
										type="button"
										onClick={handleSaveAll}
										disabled={isSaving}
										className="inline-flex items-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
									>
										<Save className="mr-2 h-4 w-4" />
										{isSaving
											? 'Saving...'
											: `Save ${changes.size} change${changes.size !== 1 ? 's' : ''}`}
									</button>
								)}
							</div>
						</div>

						{/* Attendance Table */}
						<div className="overflow-x-auto">
							<table className="min-w-full divide-y divide-gray-200">
								<thead className="bg-gray-50">
									<tr>
										<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
											Student
										</th>
										<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
											Guardian
										</th>
										<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
											Attendance
										</th>
										<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
											Status
										</th>
									</tr>
								</thead>
								<tbody className="divide-y divide-gray-200 bg-white">
									{roll.items.map((item) => {
										const currentStatus = getStatusForStudent(
											item.student_id,
											item.attendance?.status || null,
										);
										const hasChanges = changes.has(item.student_id);

										return (
											<tr key={item.signup_id} className={hasChanges ? 'bg-yellow-50' : ''}>
												<td className="px-6 py-4 whitespace-nowrap">
													<div className="text-sm font-medium text-gray-900">
														{item.student_name}
													</div>
												</td>
												<td className="px-6 py-4 whitespace-nowrap">
													<div className="text-sm text-gray-500">{item.caregiver_name}</div>
												</td>
												<td className="px-6 py-4 whitespace-nowrap">
													<div className="flex gap-2">
														<button
															type="button"
															onClick={() => handleStatusChange(item.student_id, 'present')}
															className={`rounded-md px-3 py-1 text-sm font-medium ${
																currentStatus === 'present'
																	? 'bg-green-600 text-white'
																	: 'bg-gray-200 text-gray-700 hover:bg-gray-300'
															}`}
														>
															Present
														</button>
														<button
															type="button"
															onClick={() => handleStatusChange(item.student_id, 'absent_unknown')}
															className={`rounded-md px-3 py-1 text-sm font-medium ${
																currentStatus === 'absent_unknown'
																	? 'bg-red-600 text-white'
																	: 'bg-gray-200 text-gray-700 hover:bg-gray-300'
															}`}
														>
															Absent (Unknown)
														</button>
														<button
															type="button"
															onClick={() => handleStatusChange(item.student_id, 'absent_known')}
															className={`rounded-md px-3 py-1 text-sm font-medium ${
																currentStatus === 'absent_known'
																	? 'bg-yellow-600 text-white'
																	: 'bg-gray-200 text-gray-700 hover:bg-gray-300'
															}`}
														>
															Absent (Known)
														</button>
													</div>
												</td>
												<td className="px-6 py-4 whitespace-nowrap">
													{item.attendance?.updated_at && (
														<span className="text-xs text-gray-500">
															Marked {new Date(item.attendance.updated_at).toLocaleString()}
														</span>
													)}
													{hasChanges && (
														<span className="ml-2 text-xs font-medium text-yellow-700">
															Unsaved
														</span>
													)}
												</td>
											</tr>
										);
									})}
								</tbody>
							</table>

							{roll.items.length === 0 && (
								<div className="py-12 text-center text-gray-500">
									No students enrolled in this session
								</div>
							)}
						</div>

						{/* Summary */}
						{roll.items.length > 0 && (
							<div className="border-t border-gray-200 bg-gray-50 px-6 py-4">
								<div className="text-sm text-gray-600">
									<span className="font-medium">Total:</span> {roll.items.length} students
									{' • '}
									<span className="font-medium text-green-700">
										Present:{' '}
										{
											roll.items.filter(
												(i) =>
													getStatusForStudent(i.signup_id, i.attendance?.status || null) ===
													'present',
											).length
										}
									</span>
									{' • '}
									<span className="font-medium text-red-700">
										Absent:{' '}
										{
											roll.items.filter(
												(i) =>
													getStatusForStudent(i.signup_id, i.attendance?.status || null) ===
													'absent',
											).length
										}
									</span>
									{' • '}
									<span className="font-medium text-yellow-700">
										Excused:{' '}
										{
											roll.items.filter(
												(i) =>
													getStatusForStudent(i.signup_id, i.attendance?.status || null) ===
													'excused',
											).length
										}
									</span>
								</div>
							</div>
						)}
					</div>
				</Layout>
			</div>
		</div>
	);
};

export default AttendanceRollPage;
