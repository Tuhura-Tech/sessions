import { ArrowLeft, Download, Edit, Mail, Trash2, UserPlus, Users, X } from 'lucide-react';
import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import Layout from '../components/Layout';
import Modal from '../components/Modal';
import Sidebar from '../components/Sidebar';
import { downloadBlob } from '../lib/export';
import { calculateAge, getStatusColor } from '../lib/utils';
import { adminApi } from '../services/api';
import type { ChildDetails, Occurrence, Session, Signup, Staff, StaffPublic } from '../types';

function dayOfWeekAsString(dayIndex: number | null): string {
	if (dayIndex === null || dayIndex === undefined) return 'Not set';
	const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
	return days[dayIndex] || 'Unknown';
}

const SessionDetail: React.FC = () => {
	const { id } = useParams<{ id: string }>();
	const navigate = useNavigate();
	const [session, setSession] = useState<Session | null>(null);
	const [signups, setSignups] = useState<Signup[]>([]);
	const [occurrences, setOccurrences] = useState<Occurrence[]>([]);
	const [assignedStaff, setAssignedStaff] = useState<StaffPublic[]>([]);
	const [availableStaff, setAvailableStaff] = useState<Staff[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [activeTab, setActiveTab] = useState<'signups' | 'occurrences' | 'staff' | 'comms'>(
		'signups',
	);
	const [statusFilter, setStatusFilter] = useState<string>('');
	const [blockFilter, setBlockFilter] = useState<string>('');
	const [showStaffModal, setShowStaffModal] = useState(false);
	const [showAddStudentModal, setShowAddStudentModal] = useState(false);
	const [allStudents, setAllStudents] = useState<ChildDetails[]>([]);
	const [studentSearchQuery, setStudentSearchQuery] = useState('');
	const [selectedStudent, setSelectedStudent] = useState<string | null>(null);
	const [addingStudent, setAddingStudent] = useState(false);

	const [bulkSubject, setBulkSubject] = useState('');
	const [bulkMessage, setBulkMessage] = useState('');
	const [commsStatus, setCommsStatus] = useState<string | null>(null);

	const loadSessionData = useCallback(async (sessionId: string) => {
		try {
			setIsLoading(true);
			const [sessionData, signupsData, occurrencesData, staffData, allStaff, students] =
				await Promise.all([
					adminApi.getSession(sessionId),
					adminApi.getSessionSignups(sessionId),
					adminApi.getSessionOccurrences(sessionId),
					adminApi.getSessionStaff(sessionId),
					adminApi.getStaff(true),
					adminApi.listChildren(),
				]);
			setSession(sessionData);
			setSignups(signupsData);
			setOccurrences(occurrencesData);
			setAssignedStaff(staffData);
			setAvailableStaff(allStaff);
			setAllStudents(students);
		} catch (error) {
			console.error('Failed to load session data:', error);
		} finally {
			setIsLoading(false);
		}
	}, []);

	useEffect(() => {
		if (id) {
			setBlockFilter('');
			loadSessionData(id);
		}
	}, [id, loadSessionData]);

	const filteredOccurrences = occurrences
		.filter((occurrence) => !blockFilter || occurrence.block_name === blockFilter)
		.slice()
		.sort((a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime());

	const handleStatusChange = async (signupId: string, newStatus: string) => {
		try {
			await adminApi.updateSignupStatus(signupId, newStatus);
			if (id) {
				const updatedSignups = await adminApi.getSessionSignups(id);
				setSignups(updatedSignups);
			}
		} catch (error) {
			console.error('Failed to update signup status:', error);
			alert('Failed to update signup status');
		}
	};

	const handleExportSignups = async () => {
		if (!id || !session) return;
		try {
			const blob = await adminApi.exportSignupsCSV(id, statusFilter || undefined);
			downloadBlob(blob, `signups-${session.name}.csv`);
		} catch (error) {
			console.error('Failed to export signups:', error);
			alert('Failed to export signups');
		}
	};

	const handleCancelOccurrence = async (occurrenceId: string) => {
		const reason = prompt('Enter cancellation reason (optional):');
		if (reason === null) return;

		try {
			await adminApi.cancelOccurrence(occurrenceId, reason || undefined);
			if (id) {
				const updated = await adminApi.getSessionOccurrences(id);
				setOccurrences(updated);
				alert('Occurrence cancelled');
			}
		} catch (error) {
			console.error('Failed to cancel occurrence:', error);
			alert('Failed to cancel occurrence');
		}
	};

	const handleReinstateOccurrence = async (occurrenceId: string) => {
		try {
			await adminApi.reinstateOccurrence(occurrenceId);
			if (id) {
				const updated = await adminApi.getSessionOccurrences(id);
				setOccurrences(updated);
				alert('Occurrence reinstated');
			}
		} catch (error) {
			console.error('Failed to reinstate occurrence:', error);
			alert('Failed to reinstate occurrence');
		}
	};

	const handleBulkEmail = async () => {
		if (!id) return;
		if (!bulkSubject.trim() || !bulkMessage.trim()) {
			alert('Subject and message are required');
			return;
		}
		try {
			setCommsStatus('Sending bulk email...');
			const res = await adminApi.bulkEmailSession(id, {
				subject: bulkSubject,
				message: bulkMessage,
			});
			setCommsStatus(`Enqueued ${res.enqueued} emails`);
			setBulkSubject('');
			setBulkMessage('');
		} catch (error) {
			console.error('Failed to send bulk email:', error);
			setCommsStatus('Failed to send bulk email');
		}
	};

	const handleAddStudent = async () => {
		if (!id || !selectedStudent) return;

		try {
			setAddingStudent(true);
			await adminApi.createSignup({
				sessionId: id,
				studentId: selectedStudent,
				status: 'confirmed',
			});

			// Reload signups
			const updatedSignups = await adminApi.getSessionSignups(id);
			setSignups(updatedSignups);

			// Reset and close modal
			setSelectedStudent(null);
			setStudentSearchQuery('');
			setShowAddStudentModal(false);
			alert('Student added successfully');
		} catch (error) {
			console.error('Failed to add student:', error);
			alert('Failed to add student to session');
		} finally {
			setAddingStudent(false);
		}
	};

	const handleDeleteSession = async () => {
		if (!id) return;
		if (!confirm('Are you sure you want to delete this session? This cannot be undone.')) return;

		try {
			await adminApi.deleteSession(id);
			alert('Session deleted successfully');
			navigate('/sessions');
		} catch (error) {
			console.error('Failed to delete session:', error);
			alert('Failed to delete session');
		}
	};

	const handleAssignStaff = async (staffId: string) => {
		if (!id) return;
		try {
			await adminApi.assignStaffToSession(id, staffId);
			const updatedStaff = await adminApi.getSessionStaff(id);
			setAssignedStaff(updatedStaff);
			setShowStaffModal(false);
		} catch (error) {
			console.error('Failed to assign staff:', error);
			alert('Failed to assign staff');
		}
	};

	const handleRemoveStaff = async (staffId: string) => {
		if (!id) return;
		if (!confirm('Remove this staff member from the session?')) return;
		try {
			await adminApi.removeStaffFromSession(id, staffId);
			const updatedStaff = await adminApi.getSessionStaff(id);
			setAssignedStaff(updatedStaff);
		} catch (error) {
			console.error('Failed to remove staff:', error);
			alert('Failed to remove staff');
		}
	};

	const filteredSignups = statusFilter ? signups.filter((s) => s.status === statusFilter) : signups;

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

	if (!session) {
		return (
			<div className="flex min-h-screen">
				<Sidebar />
				<div className="flex-1">
					<Layout>
						<div className="py-12 text-center">
							<p className="text-gray-500">Session not found</p>
							<button
								type="button"
								onClick={() => navigate('/sessions')}
								className="mt-4 inline-block text-blue-600 hover:text-blue-700"
							>
								Back to Sessions
							</button>
						</div>
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
					{/* Header */}
					<div className="mb-6">
						<button
							type="button"
							onClick={() => navigate('/sessions')}
							className="mb-4 flex items-center text-gray-600 hover:text-gray-900"
						>
							<ArrowLeft className="mr-2 h-4 w-4" />
							Back to Sessions
						</button>

						<div className="flex items-start justify-between">
							<div>
								<h1 className="text-3xl font-bold text-gray-900">{session.name}</h1>
								{session.internal_notes && (
									<p className="mt-2 text-gray-600">{session.internal_notes}</p>
								)}
							</div>
							<div className="flex gap-2">
								<button
									type="button"
									onClick={() => navigate(`/sessions/${id}/edit`)}
									className="inline-flex items-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
								>
									<Edit className="mr-2 h-4 w-4" />
									Edit
								</button>
								<button
									type="button"
									onClick={handleDeleteSession}
									className="inline-flex items-center rounded-md border border-transparent bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-700"
								>
									<Trash2 className="mr-2 h-4 w-4" />
									Delete
								</button>
							</div>
						</div>
					</div>

					{/* Session Info */}
					<div className="mb-6 rounded-lg bg-white p-6 shadow">
						<div className="grid grid-cols-1 gap-6 md:grid-cols-3">
							<div className="flex items-start">
								<div className="mt-0.5 mr-3 text-gray-400">📅</div>
								<div>
									<p className="text-sm font-medium text-gray-500">Schedule</p>
									<p className="mt-1 text-sm text-gray-900">
										{dayOfWeekAsString(session.day_of_week)} {session.start_time} -{' '}
										{session.end_time}
									</p>
								</div>
							</div>

							<div className="flex items-start">
								<div className="mt-0.5 mr-3 text-gray-400">📍</div>
								<div>
									<p className="text-sm font-medium text-gray-500">Location</p>
									{session.location ? (
										<Link
											to={`/locations/${session.location.id}`}
											className="mt-1 text-sm text-blue-600 hover:text-blue-800"
										>
											{session.location.name}
										</Link>
									) : (
										<p className="mt-1 text-sm text-gray-900">No location set</p>
									)}
								</div>
							</div>

							<div className="flex items-start">
								<div className="mt-0.5 mr-3 text-gray-400">👥</div>
								<div>
									<p className="text-sm font-medium text-gray-500">Capacity</p>
									<p className="mt-1 text-sm text-gray-900">
										{signups.filter((s) => s.status === 'confirmed').length} /{' '}
										{session.capacity || 'Unlimited'}
									</p>
								</div>
							</div>
						</div>
					</div>

					{/* Tabs */}
					<div className="mb-6 border-b border-gray-200">
						<nav className="-mb-px flex space-x-8">
							<button
								type="button"
								onClick={() => setActiveTab('signups')}
								className={`border-b-2 px-1 py-4 text-sm font-medium ${
									activeTab === 'signups'
										? 'border-blue-500 text-blue-600'
										: 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
								}`}
							>
								Signups ({signups.filter((s) => s.status === 'confirmed').length})
							</button>
							<button
								type="button"
								onClick={() => setActiveTab('occurrences')}
								className={`border-b-2 px-1 py-4 text-sm font-medium ${
									activeTab === 'occurrences'
										? 'border-blue-500 text-blue-600'
										: 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
								}`}
							>
								Occurrences ({occurrences.length})
							</button>
							<button
								type="button"
								onClick={() => setActiveTab('staff')}
								className={`border-b-2 px-1 py-4 text-sm font-medium ${
									activeTab === 'staff'
										? 'border-blue-500 text-blue-600'
										: 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
								}`}
							>
								Staff ({assignedStaff.length})
							</button>
							<button
								type="button"
								onClick={() => setActiveTab('comms')}
								className={`border-b-2 px-1 py-4 text-sm font-medium ${
									activeTab === 'comms'
										? 'border-blue-500 text-blue-600'
										: 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
								}`}
							>
								Communications
							</button>
						</nav>
					</div>

					{/* Signups Tab */}
					{activeTab === 'signups' && (
						<div className="rounded-lg bg-white shadow">
							<div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
								<div className="flex items-center gap-4">
									<h2 className="text-lg font-semibold text-gray-900">Signups</h2>
									<select
										value={statusFilter}
										onChange={(e) => setStatusFilter(e.target.value)}
										className="rounded-md border-gray-300 px-3 py-1 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
									>
										<option value="">All statuses</option>
										<option value="confirmed">Confirmed</option>
										<option value="waitlisted">Waitlisted</option>
										<option value="pending">Pending</option>
										<option value="withdrawn">Withdrawn</option>
									</select>
								</div>
								<div className="flex gap-2">
									<button
										type="button"
										onClick={() => setShowAddStudentModal(true)}
										className="inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
									>
										<UserPlus className="mr-2 h-4 w-4" />
										Add Student
									</button>
									<button
										type="button"
										onClick={handleExportSignups}
										className="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
									>
										<Download className="mr-2 h-4 w-4" />
										Export CSV
									</button>
								</div>
							</div>

							<div className="overflow-x-auto">
								<table className="min-w-full divide-y divide-gray-200">
									<thead className="bg-gray-50">
										<tr>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Student
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Age
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Guardian
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Email
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Media Consent
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Status
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Actions
											</th>
										</tr>
									</thead>
									<tbody className="divide-y divide-gray-200 bg-white">
										{filteredSignups.map((signup) => (
											<tr key={signup.id}>
												<td className="px-6 py-4 text-sm font-medium whitespace-nowrap text-gray-900">
													<button
														type="button"
														onClick={() => navigate(`/students/${signup.student_id}`)}
														className="text-blue-600 hover:text-blue-800"
													>
														{signup.student_name}
													</button>
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
													{calculateAge(signup.date_of_birth ?? null) ?? '—'}
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
													{signup.guardian_name || '—'}
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
													{signup.email || '—'}
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
													{signup.media_consent === null || signup.media_consent === undefined
														? '—'
														: signup.media_consent
															? 'Yes'
															: 'No'}
												</td>
												<td className="px-6 py-4 whitespace-nowrap">
													<span
														className={`inline-flex rounded-full px-2 py-1 text-xs leading-5 font-semibold ${getStatusColor(
															signup.status,
														)}`}
													>
														{signup.status}
													</span>
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap">
													<select
														value={signup.status}
														onChange={(e) => handleStatusChange(signup.id, e.target.value)}
														className="rounded-md border-gray-300 px-2 py-1 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
													>
														<option value="confirmed">Confirmed</option>
														<option value="waitlisted">Waitlisted</option>
														<option value="pending">Pending</option>
														<option value="withdrawn">Withdrawn</option>
													</select>
												</td>
											</tr>
										))}
									</tbody>
								</table>
								{filteredSignups.length === 0 && (
									<div className="py-12 text-center text-gray-500">No signups matching filter</div>
								)}
							</div>
						</div>
					)}

					{/* Occurrences Tab */}
					{activeTab === 'occurrences' && (
						<div className="rounded-lg bg-white shadow">
							<div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
								<div>
									<h2 className="text-lg font-semibold text-gray-900">Occurrences</h2>
									<p className="text-sm text-gray-500">
										Showing {filteredOccurrences.length} of {occurrences.length} occurrence(s)
									</p>
								</div>
								<div>
									<label className="flex items-center gap-2">
										<span className="text-sm text-gray-700">Filter by term:</span>
										<select
											value={blockFilter}
											onChange={(e) => setBlockFilter(e.target.value)}
											className="rounded-md border border-gray-300 py-1 pr-8 pl-3 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
										>
											<option value="">All terms</option>
											{Array.from(new Set(occurrences.map((o) => o.block_name).filter(Boolean)))
												.sort()
												.map((blockName) => (
													<option key={blockName} value={blockName || ''}>
														{blockName}
													</option>
												))}
										</select>
									</label>
								</div>
							</div>
							{filteredOccurrences.length > 0 ? (
								<div className="overflow-x-auto">
									<table className="min-w-full divide-y divide-gray-200">
										<thead className="bg-gray-50">
											<tr>
												<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
													Date
												</th>
												<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
													Term/Block
												</th>
												<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
													Status
												</th>
												<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
													Actions
												</th>
											</tr>
										</thead>
										<tbody className="divide-y divide-gray-200 bg-white">
											{filteredOccurrences.map((occurrence) => (
												<tr key={occurrence.id}>
													<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-900">
														{new Date(occurrence.starts_at).toLocaleDateString('en-NZ', {
															day: '2-digit',
															month: '2-digit',
															year: 'numeric',
														})}
													</td>
													<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-900">
														{occurrence.block_name || '—'}
													</td>
													<td className="px-6 py-4 whitespace-nowrap">
														{occurrence.cancelled ? (
															<span className="inline-flex rounded-full bg-red-100 px-2 py-1 text-xs leading-5 font-semibold text-red-800">
																Cancelled
															</span>
														) : (
															<span className="inline-flex rounded-full bg-green-100 px-2 py-1 text-xs leading-5 font-semibold text-green-800">
																Active
															</span>
														)}
													</td>
													<td className="px-6 py-4 text-sm whitespace-nowrap">
														<button
															type="button"
															onClick={() => navigate(`/attendance/${occurrence.id}`)}
															className="mr-4 text-blue-600 hover:text-blue-900"
														>
															Attendance
														</button>
														{occurrence.cancelled ? (
															<button
																type="button"
																onClick={() => handleReinstateOccurrence(occurrence.id)}
																className="text-green-600 hover:text-green-900"
															>
																Reinstate
															</button>
														) : (
															<button
																type="button"
																onClick={() => handleCancelOccurrence(occurrence.id)}
																className="text-red-600 hover:text-red-900"
															>
																Cancel
															</button>
														)}
													</td>
												</tr>
											))}
										</tbody>
									</table>
								</div>
							) : (
								<div className="py-12 text-center text-gray-500">
									{blockFilter
										? `No occurrences found for "${blockFilter}".`
										: 'No occurrences available.'}
								</div>
							)}
						</div>
					)}

					{/* Staff Tab */}
					{activeTab === 'staff' && (
						<div className="rounded-lg bg-white shadow">
							<div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
								<div>
									<h2 className="text-lg font-semibold text-gray-900">Assigned Staff</h2>
									<p className="text-sm text-gray-500">
										{assignedStaff.length} staff member{assignedStaff.length !== 1 ? 's' : ''}{' '}
										assigned
									</p>
								</div>
								<button
									type="button"
									onClick={() => setShowStaffModal(true)}
									className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
								>
									<UserPlus className="mr-2 h-4 w-4" />
									Assign Staff
								</button>
							</div>

							<div className="p-6">
								{assignedStaff.length === 0 ? (
									<div className="py-12 text-center text-gray-500">
										<Users className="mx-auto mb-3 h-12 w-12 text-gray-300" />
										<p>No staff assigned to this session yet.</p>
										<button
											type="button"
											onClick={() => setShowStaffModal(true)}
											className="mt-3 text-sm text-blue-600 hover:text-blue-800"
										>
											Assign your first staff member
										</button>
									</div>
								) : (
									<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
										{assignedStaff.map((staff) => (
											<div
												key={staff.id}
												className="rounded-lg border border-gray-200 bg-gray-50 p-4"
											>
												<div className="flex items-start justify-between">
													<div className="flex-1">
														<h3 className="font-medium text-gray-900">{staff.name}</h3>
														<p className="mt-1 text-sm text-gray-600">{staff.email}</p>
														{staff.last_login_at && (
															<p className="mt-2 text-xs text-gray-500">
																Last login: {new Date(staff.last_login_at).toLocaleDateString()}
															</p>
														)}
													</div>
													<button
														type="button"
														onClick={() => handleRemoveStaff(staff.id)}
														className="ml-2 text-gray-400 hover:text-red-600"
														title="Remove staff"
													>
														<X className="h-5 w-5" />
													</button>
												</div>
											</div>
										))}
									</div>
								)}
							</div>
						</div>
					)}

					{/* Communications Tab */}
					{activeTab === 'comms' && (
						<div className="rounded-lg bg-white shadow">
							<div className="border-b border-gray-200 px-6 py-4">
								<h2 className="text-lg font-semibold text-gray-900">Communications</h2>
								{commsStatus && <p className="mt-1 text-sm text-gray-500">{commsStatus}</p>}
							</div>
							<div className="grid grid-cols-1 gap-6 p-6 md:grid-cols-2">
								<div className="rounded-lg border border-gray-200 p-4">
									<div className="mb-3 flex items-center gap-2">
										<Mail className="h-4 w-4 text-gray-600" />
										<h3 className="text-base font-semibold text-gray-900">Bulk email</h3>
									</div>
									<div className="space-y-3">
										<input
											type="text"
											value={bulkSubject}
											onChange={(e) => setBulkSubject(e.target.value)}
											placeholder="Subject"
											className="w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500"
										/>
										<textarea
											rows={6}
											value={bulkMessage}
											onChange={(e) => setBulkMessage(e.target.value)}
											placeholder="Message to caregivers"
											className="w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500"
										/>
										<button
											type="button"
											onClick={handleBulkEmail}
											className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
										>
											Send bulk email
										</button>
									</div>
								</div>
							</div>
						</div>
					)}
				</Layout>
			</div>

			{/* Assign Staff Modal */}
			<Modal
				isOpen={showStaffModal}
				onClose={() => setShowStaffModal(false)}
				title="Assign Staff to Session"
			>
				<div className="space-y-4">
					<p className="text-sm text-gray-600">
						Select staff members to assign to this session. Already assigned staff are excluded.
					</p>

					<div className="max-h-96 space-y-2 overflow-y-auto">
						{availableStaff
							.filter((staff) => !assignedStaff.some((assigned) => assigned.id === staff.id))
							.map((staff) => (
								<button
									key={staff.id}
									type="button"
									onClick={() => handleAssignStaff(staff.id)}
									className="w-full rounded-lg border border-gray-300 bg-white p-4 text-left transition-colors hover:border-blue-500 hover:bg-blue-50"
								>
									<div className="font-medium text-gray-900">{staff.name}</div>
									<div className="text-sm text-gray-600">{staff.email}</div>
									{!staff.active && <div className="mt-1 text-xs text-gray-500">(Inactive)</div>}
								</button>
							))}
						{availableStaff.filter(
							(staff) => !assignedStaff.some((assigned) => assigned.id === staff.id),
						).length === 0 && (
							<div className="py-8 text-center text-gray-500">
								All staff members are already assigned to this session.
							</div>
						)}
					</div>

					<div className="flex justify-end pt-4">
						<button
							type="button"
							onClick={() => setShowStaffModal(false)}
							className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
						>
							Close
						</button>
					</div>
				</div>
			</Modal>

			{/* Add Student Modal */}
			<Modal
				isOpen={showAddStudentModal}
				onClose={() => {
					setShowAddStudentModal(false);
					setSelectedStudent(null);
					setStudentSearchQuery('');
				}}
				title="Add Student to Session"
			>
				<div className="space-y-4">
					<p className="text-sm text-gray-600">
						Search and select a student to add to this session.
					</p>

					<input
						type="text"
						value={studentSearchQuery}
						onChange={(e) => setStudentSearchQuery(e.target.value)}
						placeholder="Search by student or guardian name..."
						className="w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500"
					/>

					<div className="max-h-96 space-y-2 overflow-y-auto">
						{allStudents
							.filter((student) => {
								// Filter out already signed up students
								const alreadySignedUp = signups.some(
									(signup) => signup.student_id === student.id && signup.status !== 'withdrawn',
								);
								if (alreadySignedUp) return false;

								// Apply search filter
								if (!studentSearchQuery.trim()) return true;
								const query = studentSearchQuery.toLowerCase();
								return (
									student.name?.toLowerCase().includes(query) ||
									student.caregiver?.name?.toLowerCase().includes(query) ||
									student.caregiver?.email?.toLowerCase().includes(query)
								);
							})
							.map((student) => (
								<button
									key={student.id}
									type="button"
									onClick={() => setSelectedStudent(student.id)}
									className={`w-full rounded-lg border p-4 text-left transition-colors ${
										selectedStudent === student.id
											? 'border-blue-500 bg-blue-50'
											: 'border-gray-300 bg-white hover:border-blue-500 hover:bg-blue-50'
									}`}
								>
									<div className="font-medium text-gray-900">{student.name}</div>
									<div className="text-sm text-gray-600">
										Guardian: {student.caregiver?.name || 'Unknown'}
									</div>
									{student.date_of_birth && (
										<div className="text-sm text-gray-600">
											Age: {calculateAge(student.date_of_birth) ?? '—'}
										</div>
									)}
									{student.caregiver?.email && (
										<div className="text-xs text-gray-500">{student.caregiver.email}</div>
									)}
								</button>
							))}
						{allStudents.filter((student) => {
							const alreadySignedUp = signups.some(
								(signup) => signup.student_id === student.id && signup.status !== 'withdrawn',
							);
							if (alreadySignedUp) return false;
							if (!studentSearchQuery.trim()) return true;
							const query = studentSearchQuery.toLowerCase();
							return (
								student.name?.toLowerCase().includes(query) ||
								student.caregiver?.name?.toLowerCase().includes(query) ||
								student.caregiver?.email?.toLowerCase().includes(query)
							);
						}).length === 0 && (
							<div className="py-8 text-center text-gray-500">
								{studentSearchQuery.trim()
									? 'No students found matching your search.'
									: 'All students are already signed up for this session.'}
							</div>
						)}
					</div>

					<div className="flex justify-end gap-2 pt-4">
						<button
							type="button"
							onClick={() => {
								setShowAddStudentModal(false);
								setSelectedStudent(null);
								setStudentSearchQuery('');
							}}
							className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
						>
							Cancel
						</button>
						<button
							type="button"
							onClick={handleAddStudent}
							disabled={!selectedStudent || addingStudent}
							className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
						>
							{addingStudent ? 'Adding...' : 'Add Student'}
						</button>
					</div>
				</div>
			</Modal>
		</div>
	);
};

export default SessionDetail;
