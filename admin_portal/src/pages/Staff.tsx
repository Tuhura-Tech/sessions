import { BadgeCheck, Ban, Calendar, Clock, MapPin, Plus, RefreshCcw, Users } from 'lucide-react';
import type React from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { FormCheckbox, FormInput } from '../components/FormComponents';
import Layout from '../components/Layout';
import Modal from '../components/Modal';
import Sidebar from '../components/Sidebar';
import { adminApi } from '../services/api';
import type { Staff, StaffAvailability, StaffListItem, StaffSessionSummary } from '../types';

const StaffPage: React.FC = () => {
	const [staff, setStaff] = useState<StaffListItem[]>([]);
	const [availability, setAvailability] = useState<StaffAvailability[]>([]);
	const [activeOnly, setActiveOnly] = useState(true);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const [selectedStaff, setSelectedStaff] = useState<Staff | null>(null);
	const [staffSessions, setStaffSessions] = useState<StaffSessionSummary[]>([]);
	const [isLoadingDetails, setIsLoadingDetails] = useState(false);

	const [showCreateModal, setShowCreateModal] = useState(false);
	const [showEditModal, setShowEditModal] = useState(false);

	const [createForm, setCreateForm] = useState({
		name: '',
		email: '',
		ssoId: '',
	});
	const [editForm, setEditForm] = useState<Partial<Staff>>({});

	const loadStaff = useCallback(async () => {
		try {
			setIsLoading(true);
			setError(null);
			const [staffData, availData] = await Promise.all([
				adminApi.getStaff(activeOnly),
				adminApi.getStaffAvailability(new Date().getFullYear(), activeOnly),
			]);
			setStaff(staffData);
			setAvailability(availData);
		} catch (err) {
			console.error(err);
			setError('Failed to load staff list');
		} finally {
			setIsLoading(false);
		}
	}, [activeOnly]);

	useEffect(() => {
		loadStaff();
	}, [loadStaff]);

	const loadStaffDetails = async (staffId: string) => {
		try {
			setIsLoadingDetails(true);
			const [details, sessions] = await Promise.all([
				adminApi.getStaffMember(staffId),
				adminApi.getStaffSessions(staffId),
			]);
			setSelectedStaff(details);
			setEditForm({
				name: details.name,
				email: details.email,
				active: details.active,
			});
			setStaffSessions(sessions);
		} catch (err) {
			console.error(err);
			alert('Failed to load staff details');
		} finally {
			setIsLoadingDetails(false);
		}
	};

	const handleCreate = async () => {
		if (!createForm.name || !createForm.email || !createForm.ssoId) {
			alert('Name, email, and SSO ID are required');
			return;
		}
		try {
			await adminApi.createStaff(createForm);
			setShowCreateModal(false);
			setCreateForm({ name: '', email: '', ssoId: '' });
			await loadStaff();
		} catch (err) {
			console.error(err);
			alert('Failed to create staff member');
		}
	};

	const handleUpdate = async () => {
		if (!selectedStaff) return;
		try {
			await adminApi.updateStaff(selectedStaff.id, {
				name: editForm.name,
				email: editForm.email,
				active: editForm.active,
			});
			setShowEditModal(false);
			await Promise.all([loadStaff(), loadStaffDetails(selectedStaff.id)]);
		} catch (err) {
			console.error(err);
			alert('Failed to update staff member');
		}
	};

	const activeCount = useMemo(() => staff.filter((s) => s.active).length, [staff]);

	const workloadSummary = useMemo(() => {
		const maxSessions = Math.max(...availability.map((a) => a.assigned_session_count), 0);
		const avgSessions =
			availability.length > 0
				? availability.reduce((sum, a) => sum + a.assigned_session_count, 0) / availability.length
				: 0;
		return { maxSessions, avgSessions: Math.round(avgSessions * 10) / 10 };
	}, [availability]);

	return (
		<div className="flex min-h-screen">
			<Sidebar />
			<div className="flex-1">
				<Layout
					title="Staff"
					actions={
						<div className="flex items-center gap-3">
							<label className="inline-flex items-center text-sm text-gray-700">
								<FormCheckbox
									checked={activeOnly}
									onChange={(e) => setActiveOnly(e.target.checked)}
								/>
								<span className="ml-2">Show active only</span>
							</label>
							<Link
								to="/staff/schedule"
								className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
							>
								<Calendar className="mr-2 h-4 w-4" />
								View Schedule
							</Link>
							<button
								type="button"
								onClick={() => setShowCreateModal(true)}
								className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
							>
								<Plus className="mr-2 h-4 w-4" />
								New Staff
							</button>
							<button
								type="button"
								onClick={loadStaff}
								className="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
							>
								<RefreshCcw className="mr-2 h-4 w-4" />
								Refresh
							</button>
						</div>
					}
				>
					{error && (
						<div className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-700">{error}</div>
					)}

					<div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
						<div className="rounded-lg bg-blue-50 p-4">
							<div className="text-sm font-medium text-blue-900">Total Active Staff</div>
							<div className="mt-1 text-3xl font-bold text-blue-600">{activeCount}</div>
						</div>
						<div className="rounded-lg bg-green-50 p-4">
							<div className="text-sm font-medium text-green-900">Average Sessions/Staff</div>
							<div className="mt-1 text-3xl font-bold text-green-600">
								{workloadSummary.avgSessions}
							</div>
						</div>
						<div className="rounded-lg bg-purple-50 p-4">
							<div className="text-sm font-medium text-purple-900">Max Sessions/Staff</div>
							<div className="mt-1 text-3xl font-bold text-purple-600">
								{workloadSummary.maxSessions}
							</div>
						</div>
					</div>

					<div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
						<div className="rounded-lg bg-white shadow lg:col-span-2">
							<div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
								<div>
									<h2 className="flex items-center gap-2 text-lg font-semibold text-gray-900">
										<Users className="h-5 w-5" /> Staff
									</h2>
									<p className="text-sm text-gray-500">
										{activeCount} active / {staff.length} shown
									</p>
								</div>
							</div>
							<div className="overflow-x-auto">
								<table className="min-w-full divide-y divide-gray-200">
									<thead className="bg-gray-50">
										<tr>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Name
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Email
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
										{isLoading ? (
											<tr>
												<td colSpan={4} className="px-6 py-6 text-center text-gray-500">
													Loading staff...
												</td>
											</tr>
										) : staff.length === 0 ? (
											<tr>
												<td colSpan={4} className="px-6 py-6 text-center text-gray-500">
													No staff found
												</td>
											</tr>
										) : (
											staff.map((s) => (
												<tr key={s.id} className="hover:bg-gray-50">
													<td className="px-6 py-4 text-sm font-medium whitespace-nowrap text-gray-900">
														{s.name}
													</td>
													<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-600">
														{s.email}
													</td>
													<td className="px-6 py-4 text-sm whitespace-nowrap">
														{s.active ? (
															<span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-1 text-xs font-semibold text-green-800">
																<BadgeCheck className="h-4 w-4" /> Active
															</span>
														) : (
															<span className="inline-flex items-center gap-1 rounded-full bg-gray-200 px-2 py-1 text-xs font-semibold text-gray-700">
																<Ban className="h-4 w-4" /> Inactive
															</span>
														)}
													</td>
													<td className="px-6 py-4 text-sm whitespace-nowrap">
														<button
															type="button"
															onClick={() => loadStaffDetails(s.id)}
															className="text-blue-600 hover:text-blue-800"
														>
															View
														</button>
													</td>
												</tr>
											))
										)}
									</tbody>
								</table>
							</div>
						</div>

						<div className="rounded-lg bg-white p-6 shadow">
							<h3 className="mb-3 text-lg font-semibold text-gray-900">Details</h3>
							{!selectedStaff && (
								<p className="text-sm text-gray-500">Select a staff member to view details.</p>
							)}
							{selectedStaff && (
								<div className="space-y-4">
									<div>
										<p className="text-sm text-gray-500">Name</p>
										<p className="text-base font-semibold text-gray-900">{selectedStaff.name}</p>
									</div>
									<div>
										<p className="text-sm text-gray-500">Email</p>
										<p className="text-base text-gray-800">{selectedStaff.email}</p>
									</div>
									<div className="flex items-center gap-2">
										{selectedStaff.active ? (
											<span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-1 text-xs font-semibold text-green-800">
												<BadgeCheck className="h-4 w-4" /> Active
											</span>
										) : (
											<span className="inline-flex items-center gap-1 rounded-full bg-gray-200 px-2 py-1 text-xs font-semibold text-gray-700">
												<Ban className="h-4 w-4" /> Inactive
											</span>
										)}
										{isLoadingDetails && <span className="text-xs text-gray-500">Refreshing…</span>}
									</div>

									<div className="flex gap-3">
										<button
											type="button"
											onClick={() => setShowEditModal(true)}
											className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
										>
											Edit
										</button>
										<button
											type="button"
											onClick={() => loadStaffDetails(selectedStaff.id)}
											className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
										>
											Refresh
										</button>
									</div>

									<div>
										<p className="mb-2 text-sm font-semibold text-gray-900">Assigned sessions</p>
										{staffSessions.length === 0 ? (
											<p className="text-sm text-gray-500">No assignments</p>
										) : (
											<ul className="space-y-3">
												{staffSessions.map((sess) => (
													<li
														key={sess.id}
														className="rounded-md border border-gray-200 bg-gray-50 p-3"
													>
														<div className="mb-2 font-medium text-gray-900">{sess.name}</div>
														<div className="space-y-1 text-sm text-gray-600">
															{sess.dayOfWeek !== null &&
															sess.dayOfWeek !== undefined &&
															sess.startTime &&
															sess.endTime ? (
																<div className="flex items-center gap-1">
																	<Calendar className="h-4 w-4" />
																	<span>
																		{
																			[
																				'Sunday',
																				'Monday',
																				'Tuesday',
																				'Wednesday',
																				'Thursday',
																				'Friday',
																				'Saturday',
																			][sess.dayOfWeek]
																		}
																	</span>
																</div>
															) : null}
															{sess.startTime && sess.endTime ? (
																<div className="flex items-center gap-1">
																	<Clock className="h-4 w-4" />
																	<span>
																		{sess.startTime} - {sess.endTime}
																	</span>
																</div>
															) : null}
															{sess.locationName ? (
																<div className="flex items-center gap-1">
																	<MapPin className="h-4 w-4" />
																	<span>{sess.locationName}</span>
																</div>
															) : null}
															<div className="text-xs text-gray-500">Year: {sess.year}</div>
														</div>
													</li>
												))}
											</ul>
										)}
									</div>
								</div>
							)}
						</div>
					</div>
				</Layout>
			</div>

			<Modal
				isOpen={showCreateModal}
				onClose={() => setShowCreateModal(false)}
				title="Create staff member"
			>
				<div className="space-y-4">
					<FormInput
						label="Full name"
						value={createForm.name}
						onChange={(e) => setCreateForm((p) => ({ ...p, name: e.target.value }))}
						required
					/>
					<FormInput
						label="Email"
						type="email"
						value={createForm.email}
						onChange={(e) => setCreateForm((p) => ({ ...p, email: e.target.value }))}
						required
					/>
					<FormInput
						label="SSO ID"
						value={createForm.ssoId}
						onChange={(e) => setCreateForm((p) => ({ ...p, ssoId: e.target.value }))}
						required
						placeholder="e.g. OIDC sub"
					/>
					<div className="flex justify-end gap-3 pt-2">
						<button
							type="button"
							onClick={() => setShowCreateModal(false)}
							className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
						>
							Cancel
						</button>
						<button
							type="button"
							onClick={handleCreate}
							className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
						>
							Create
						</button>
					</div>
				</div>
			</Modal>

			<Modal
				isOpen={showEditModal}
				onClose={() => setShowEditModal(false)}
				title="Edit staff member"
			>
				<div className="space-y-4">
					<FormInput
						label="Full name"
						value={editForm.name || ''}
						onChange={(e) => setEditForm((p) => ({ ...p, name: e.target.value }))}
					/>
					<FormInput
						label="Email"
						type="email"
						value={editForm.email || ''}
						onChange={(e) => setEditForm((p) => ({ ...p, email: e.target.value }))}
					/>
					<FormCheckbox
						label="Active"
						checked={editForm.active ?? true}
						onChange={(e) => setEditForm((p) => ({ ...p, active: e.target.checked }))}
					/>
					<div className="flex justify-end gap-3 pt-2">
						<button
							type="button"
							onClick={() => setShowEditModal(false)}
							className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
						>
							Cancel
						</button>
						<button
							type="button"
							onClick={handleUpdate}
							className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
						>
							Save
						</button>
					</div>
				</div>
			</Modal>
		</div>
	);
};

export default StaffPage;
