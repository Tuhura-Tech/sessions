import { ArrowLeft, Edit, Mail, Phone, Trash2, Users } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { LoadingSpinner } from '../components/Alert';
import Layout from '../components/Layout';
import Modal from '../components/Modal';
import Sidebar from '../components/Sidebar';
import { formatDate } from '../lib/utils';
import { adminApi } from '../services/api';
import type { Caregiver, CaregiverUpdate, ChildDetails } from '../types';

export default function CaregiverDetail() {
	const { id } = useParams<{ id: string }>();
	const navigate = useNavigate();
	const [caregiver, setCaregiver] = useState<Caregiver | null>(null);
	const [students, setStudents] = useState<ChildDetails[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [showEditModal, setShowEditModal] = useState(false);
	const [updating, setUpdating] = useState(false);
	const [showDeleteModal, setShowDeleteModal] = useState(false);
	const [deleting, setDeleting] = useState(false);

	const [editData, setEditData] = useState<CaregiverUpdate>({});

	const loadCaregiver = useCallback(async () => {
		if (!id) return;
		try {
			setLoading(true);
			setError(null);
			const data = await adminApi.getCaregiver(id);
			setCaregiver(data);
			setEditData({
				name: data.name ?? '',
				email: data.email ?? '',
				phone: data.phone ?? '',
			});
		} catch (err) {
			console.error('Failed to load caregiver:', err);
			setError('Failed to load caregiver details');
		} finally {
			setLoading(false);
		}
	}, [id]);

	const loadStudents = useCallback(async () => {
		if (!id) return;
		try {
			const data = await adminApi.getCaregiverStudents(id);
			setStudents(data);
		} catch (err) {
			console.error('Failed to load students:', err);
		}
	}, [id]);

	useEffect(() => {
		if (id) {
			loadCaregiver();
			loadStudents();
		}
	}, [id, loadCaregiver, loadStudents]);

	const handleUpdate = async (e: React.FormEvent) => {
		e.preventDefault();
		if (!id) return;

		try {
			setUpdating(true);
			setError(null);
			await adminApi.updateCaregiver(id, editData);
			setShowEditModal(false);
			await loadCaregiver();
		} catch (err) {
			console.error('Failed to update caregiver:', err);
			const error = err as { response?: { data?: { detail?: string } } };
			setError(error.response?.data?.detail || 'Failed to update caregiver');
		} finally {
			setUpdating(false);
		}
	};

	const handleDelete = async () => {
		if (!id) return;

		try {
			setDeleting(true);
			setError(null);
			await adminApi.deleteCaregiver(id);
			navigate('/caregivers');
		} catch (err) {
			console.error('Failed to delete caregiver:', err);
			const error = err as { response?: { data?: { detail?: string } } };
			setError(error.response?.data?.detail || 'Failed to delete caregiver');
		} finally {
			setDeleting(false);
		}
	};

	if (loading) {
		return (
			<div className="flex min-h-screen">
				<Sidebar />
				<div className="flex-1">
					<Layout title="Caregiver Details">
						<LoadingSpinner />
					</Layout>
				</div>
			</div>
		);
	}

	if (error && !caregiver) {
		return (
			<div className="flex min-h-screen">
				<Sidebar />
				<div className="flex-1">
					<Layout title="Caregiver Details">
						<div className="rounded-lg bg-red-50 p-4 text-red-800">{error}</div>
					</Layout>
				</div>
			</div>
		);
	}

	if (!caregiver) {
		return (
			<div className="flex min-h-screen">
				<Sidebar />
				<div className="flex-1">
					<Layout title="Caregiver Details">
						<div className="text-gray-500">Caregiver not found</div>
					</Layout>
				</div>
			</div>
		);
	}

	return (
		<div className="flex min-h-screen">
			<Sidebar />

			<div className="flex-1">
				<Layout title={caregiver.name ?? 'Caregiver Details'}>
					<div className="space-y-6">
						{/* Header */}
						<div className="flex items-center justify-between">
							<button
								type="button"
								onClick={() => navigate('/caregivers')}
								className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
							>
								<ArrowLeft className="h-5 w-5" />
								Back to Parents
							</button>
							<div className="flex gap-3">
								<button
									type="button"
									onClick={() => setShowEditModal(true)}
									className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
								>
									<Edit className="h-4 w-4" />
									Edit
								</button>
								<button
									type="button"
									onClick={() => setShowDeleteModal(true)}
									className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700"
								>
									<Trash2 className="h-4 w-4" />
									Delete
								</button>
							</div>
						</div>

						{error && <div className="rounded-lg bg-red-50 p-4 text-red-800">{error}</div>}

						{/* Contact Information */}
						<div className="rounded-lg bg-white p-6 shadow">
							<h2 className="mb-4 text-xl font-semibold">Contact Information</h2>
							<div className="grid gap-4 md:grid-cols-2">
								<div className="flex items-start gap-3">
									<Mail className="mt-1 h-5 w-5 text-gray-400" />
									<div>
										<div className="text-sm text-gray-500">Email</div>
										<div className="font-medium">{caregiver.email}</div>
									</div>
								</div>

								{caregiver.phone && (
									<div className="flex items-start gap-3">
										<Phone className="mt-1 h-5 w-5 text-gray-400" />
										<div>
											<div className="text-sm text-gray-500">Phone</div>
											<div className="font-medium">{caregiver.phone}</div>
										</div>
									</div>
								)}
							</div>
						</div>

						{/* Preferences */}
						<div className="rounded-lg bg-white p-6 shadow">
							<h2 className="mb-4 text-xl font-semibold">Preferences</h2>
							<div className="text-sm text-gray-600">No preferences available.</div>
						</div>

						{/* Children */}
						<div className="rounded-lg bg-white p-6 shadow">
							<div className="mb-4 flex items-center justify-between">
								<h2 className="text-xl font-semibold">Children ({students.length})</h2>
							</div>

							{students.length === 0 ? (
								<div className="py-8 text-center text-gray-500">No children registered yet</div>
							) : (
								<div className="space-y-3">
									{students.map((student) => (
										<button
											key={student.id}
											type="button"
											onClick={() => navigate(`/students/${student.id}`)}
											className="flex w-full cursor-pointer items-center justify-between rounded-lg border border-gray-200 p-4 text-left hover:bg-gray-50"
										>
											<div className="flex items-center gap-3">
												<Users className="h-5 w-5 text-gray-400" />
												<div>
													<div className="font-medium">{student.name}</div>
													{student.date_of_birth && (
														<div className="text-sm text-gray-500">
															Born: {formatDate(student.date_of_birth)}
														</div>
													)}
												</div>
											</div>
											<button
												type="button"
												onClick={(e) => {
													e.stopPropagation();
													navigate(`/students/${student.id}`);
												}}
												className="text-blue-600 hover:text-blue-900"
											>
												View Details
											</button>
										</button>
									))}
								</div>
							)}
						</div>

						{/* Metadata - Not available from API */}
						{/* <div className="rounded-lg bg-gray-50 p-4 text-sm text-gray-600">
							<div className="flex justify-between">
								<span>Created: {new Date(caregiver.createdAt).toLocaleString()}</span>
								<span>Updated: {new Date(caregiver.updatedAt).toLocaleString()}</span>
							</div>
						</div> */}
					</div>

					{/* Edit Modal */}
					<Modal
						isOpen={showEditModal}
						onClose={() => setShowEditModal(false)}
						title="Edit Parent / Caregiver"
					>
						<form onSubmit={handleUpdate} className="space-y-4">
							<div>
								<label htmlFor="edit-name" className="block text-sm font-medium text-gray-700">
									Full Name *
								</label>
								<input
									id="edit-name"
									type="text"
									required
									value={editData.name || ''}
									onChange={(e) => setEditData({ ...editData, name: e.target.value })}
									className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
								/>
							</div>

							<div>
								<label htmlFor="edit-email" className="block text-sm font-medium text-gray-700">
									Email *
								</label>
								<input
									id="edit-email"
									type="email"
									required
									value={editData.email || ''}
									onChange={(e) => setEditData({ ...editData, email: e.target.value })}
									className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
								/>
							</div>

							<div>
								<label htmlFor="edit-phone" className="block text-sm font-medium text-gray-700">
									Phone Number
								</label>
								<input
									id="edit-phone"
									onChange={(e) => setEditData({ ...editData, phone: e.target.value })}
									className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
								/>
							</div>

							{error && (
								<div className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</div>
							)}

							<div className="flex justify-end gap-3 pt-4">
								<button
									type="button"
									onClick={() => setShowEditModal(false)}
									className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50"
								>
									Cancel
								</button>
								<button
									type="submit"
									disabled={updating}
									className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
								>
									{updating ? 'Updating...' : 'Update Parent'}
								</button>
							</div>
						</form>
					</Modal>

					{/* Delete Confirmation Modal */}
					<Modal
						isOpen={showDeleteModal}
						onClose={() => !deleting && setShowDeleteModal(false)}
						title="Delete Caregiver"
					>
						<div className="space-y-4">
							<p className="text-gray-700">
								Are you sure you want to delete{' '}
								<span className="font-semibold">{caregiver.name}</span>? This action cannot be
								undone and will also delete all associated children and their signups.
							</p>
							{error && (
								<div className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</div>
							)}
							<div className="flex justify-end gap-3 pt-4">
								<button
									type="button"
									onClick={() => setShowDeleteModal(false)}
									disabled={deleting}
									className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
								>
									Cancel
								</button>
								<button
									type="button"
									onClick={handleDelete}
									disabled={deleting}
									className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700 disabled:opacity-50"
								>
									{deleting ? 'Deleting...' : 'Delete'}
								</button>
							</div>
						</div>
					</Modal>
				</Layout>
			</div>
		</div>
	);
}
