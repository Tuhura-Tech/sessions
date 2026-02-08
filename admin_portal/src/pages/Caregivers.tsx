import { Mail, Phone, Search, Trash2, UserPlus, Users } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LoadingSpinner } from '../components/Alert';
import Layout from '../components/Layout';
import Modal from '../components/Modal';
import Sidebar from '../components/Sidebar';
import { adminApi } from '../services/api';
import type { Caregiver, CaregiverCreate } from '../types';

export default function Caregivers() {
	const navigate = useNavigate();
	const [caregivers, setCaregivers] = useState<Caregiver[]>([]);
	const [filteredCaregivers, setFilteredCaregivers] = useState<Caregiver[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [searchQuery, setSearchQuery] = useState('');
	const [showCreateModal, setShowCreateModal] = useState(false);
	const [creating, setCreating] = useState(false);
	const [deleteConfirm, setDeleteConfirm] = useState<{
		show: boolean;
		caregiverId: string | null;
		caregiverName: string;
	}>({
		show: false,
		caregiverId: null,
		caregiverName: '',
	});
	const [deleting, setDeleting] = useState(false);

	const [newCaregiver, setNewCaregiver] = useState<CaregiverCreate>({
		email: '',
		name: '',
		phone: '',
		subscribeNewsletter: false,
	});

	const loadCaregivers = useCallback(async () => {
		try {
			setLoading(true);
			setError(null);
			const data = await adminApi.listCaregivers();
			setCaregivers(data);
			setFilteredCaregivers(data);
		} catch (err) {
			console.error('Failed to load caregivers:', err);
			setError('Failed to load caregivers');
		} finally {
			setLoading(false);
		}
	}, []);

	const filterCaregivers = useCallback(() => {
		const query = searchQuery.trim().toLowerCase();
		if (!query) {
			setFilteredCaregivers(caregivers);
			return;
		}
		const filtered = caregivers.filter((caregiver) =>
			[caregiver.name, caregiver.email, caregiver.phone]
				.filter(Boolean)
				.join(' ')
				.toLowerCase()
				.includes(query),
		);
		setFilteredCaregivers(filtered);
	}, [caregivers, searchQuery]);

	useEffect(() => {
		loadCaregivers();
	}, [loadCaregivers]);

	useEffect(() => {
		filterCaregivers();
	}, [filterCaregivers]);

	const handleCreateCaregiver = async (e: React.FormEvent) => {
		e.preventDefault();
		try {
			setCreating(true);
			setError(null);
			await adminApi.createCaregiver(newCaregiver);
			setShowCreateModal(false);
			setNewCaregiver({
				email: '',
				name: '',
				phone: '',
				subscribeNewsletter: false,
			});
			await loadCaregivers();
		} catch (err) {
			console.error('Failed to create caregiver:', err);
			const error = err as { response?: { data?: { detail?: string } } };
			setError(error.response?.data?.detail || 'Failed to create caregiver');
		} finally {
			setCreating(false);
		}
	};

	const handleDeleteClick = (e: React.MouseEvent, caregiver: Caregiver) => {
		e.stopPropagation();
		setDeleteConfirm({
			show: true,
			caregiverId: caregiver.id,
			caregiverName: caregiver.name,
		});
	};

	const handleDeleteConfirm = async () => {
		if (!deleteConfirm.caregiverId) return;

		try {
			setDeleting(true);
			setError(null);
			await adminApi.deleteCaregiver(deleteConfirm.caregiverId);
			setDeleteConfirm({ show: false, caregiverId: null, caregiverName: '' });
			await loadCaregivers();
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
					<Layout title="Parents / Caregivers">
						<LoadingSpinner />
					</Layout>
				</div>
			</div>
		);
	}

	return (
		<div className="flex min-h-screen">
			<Sidebar />

			<div className="flex-1">
				<Layout title="Parents / Caregivers">
					<div className="mb-6 flex items-center justify-between">
						<div className="flex items-center gap-4">
							<div className="relative flex-1">
								<Search className="absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-gray-400" />
								<input
									type="text"
									placeholder="Search by name, email, or phone..."
									value={searchQuery}
									onChange={(e) => setSearchQuery(e.target.value)}
									className="w-full rounded-lg border border-gray-300 py-2 pr-4 pl-10 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
								/>
							</div>
						</div>
						<button
							type="button"
							onClick={() => setShowCreateModal(true)}
							className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
						>
							<UserPlus className="h-5 w-5" />
							Add Parent
						</button>
					</div>

					{error && <div className="mb-4 rounded-lg bg-red-50 p-4 text-red-800">{error}</div>}

					<div className="rounded-lg bg-white shadow">
						<div className="overflow-x-auto">
							<table className="w-full">
								<thead className="bg-gray-50">
									<tr>
										<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
											Name
										</th>
										<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
											Email
										</th>
										<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
											Phone
										</th>
										<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
											Children
										</th>
										<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
											Actions
										</th>
									</tr>
								</thead>
								<tbody className="divide-y divide-gray-200 bg-white">
									{filteredCaregivers.length === 0 ? (
										<tr>
											<td colSpan={5} className="px-6 py-12 text-center text-gray-500">
												{searchQuery
													? 'No caregivers found matching your search'
													: 'No caregivers yet'}
											</td>
										</tr>
									) : (
										filteredCaregivers.map((caregiver) => (
											<tr
												key={caregiver.id}
												className="cursor-pointer hover:bg-gray-50"
												onClick={() => navigate(`/caregivers/${caregiver.id}`)}
											>
												<td className="px-6 py-4 whitespace-nowrap">
													<div className="flex items-center">
														<Users className="mr-2 h-5 w-5 text-gray-400" />
														<div className="font-medium text-gray-900">{caregiver.name}</div>
													</div>
												</td>
												<td className="px-6 py-4 whitespace-nowrap">
													<div className="flex items-center text-gray-500">
														<Mail className="mr-2 h-4 w-4" />
														{caregiver.email}
													</div>
												</td>
												<td className="px-6 py-4 whitespace-nowrap text-gray-500">
													{caregiver.phone ? (
														<div className="flex items-center">
															<Phone className="mr-2 h-4 w-4" />
															{caregiver.phone}
														</div>
													) : (
														<span className="text-gray-400">—</span>
													)}
												</td>
												<td className="px-6 py-4 whitespace-nowrap text-gray-500">
													{caregiver.students?.length || 0}
												</td>
												<td className="px-6 py-4 whitespace-nowrap">
													<div className="flex items-center gap-3">
														<button
															type="button"
															onClick={(e) => {
																e.stopPropagation();
																navigate(`/caregivers/${caregiver.id}`);
															}}
															className="text-blue-600 hover:text-blue-900"
														>
															View Details
														</button>
														<button
															type="button"
															onClick={(e) => handleDeleteClick(e, caregiver)}
															className="text-red-600 hover:text-red-900"
															title="Delete caregiver"
														>
															<Trash2 className="h-4 w-4" />
														</button>
													</div>
												</td>
											</tr>
										))
									)}
								</tbody>
							</table>
						</div>
					</div>

					{/* Create Caregiver Modal */}
					<Modal
						isOpen={showCreateModal}
						onClose={() => setShowCreateModal(false)}
						title="Add New Parent / Caregiver"
					>
						<form onSubmit={handleCreateCaregiver} className="space-y-4">
							<div>
								<label htmlFor="new-name" className="block text-sm font-medium text-gray-700">
									Full Name *
								</label>
								<input
									id="new-name"
									type="text"
									required
									value={newCaregiver.name}
									onChange={(e) => setNewCaregiver({ ...newCaregiver, name: e.target.value })}
									className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
								/>
							</div>

							<div>
								<label htmlFor="new-email" className="block text-sm font-medium text-gray-700">
									Email *
								</label>
								<input
									id="new-email"
									type="email"
									required
									value={newCaregiver.email}
									onChange={(e) => setNewCaregiver({ ...newCaregiver, email: e.target.value })}
									className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
								/>
							</div>

							<div>
								<label htmlFor="new-phone" className="block text-sm font-medium text-gray-700">
									Phone Number
								</label>
								<input
									id="new-phone"
									onChange={(e) => setNewCaregiver({ ...newCaregiver, phone: e.target.value })}
									className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
								/>
							</div>

							<div className="flex items-center">
								<input
									type="checkbox"
									id="subscribeNewsletter"
									checked={newCaregiver.subscribeNewsletter}
									onChange={(e) =>
										setNewCaregiver({
											...newCaregiver,
											subscribeNewsletter: e.target.checked,
										})
									}
									className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
								/>
								<label htmlFor="subscribeNewsletter" className="ml-2 block text-sm text-gray-700">
									Subscribe to newsletter
								</label>
							</div>

							{error && (
								<div className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</div>
							)}

							<div className="flex justify-end gap-3 pt-4">
								<button
									type="button"
									onClick={() => setShowCreateModal(false)}
									className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50"
								>
									Cancel
								</button>
								<button
									type="submit"
									disabled={creating}
									className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
								>
									{creating ? 'Creating...' : 'Create Parent'}
								</button>
							</div>
						</form>
					</Modal>

					{/* Delete Confirmation Modal */}
					<Modal
						isOpen={deleteConfirm.show}
						onClose={() =>
							!deleting && setDeleteConfirm({ show: false, caregiverId: null, caregiverName: '' })
						}
						title="Delete Caregiver"
					>
						<div className="space-y-4">
							<p className="text-gray-700">
								Are you sure you want to delete{' '}
								<span className="font-semibold">{deleteConfirm.caregiverName}</span>? This action
								cannot be undone.
							</p>
							{error && (
								<div className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</div>
							)}
							<div className="flex justify-end gap-3 pt-4">
								<button
									type="button"
									onClick={() =>
										setDeleteConfirm({ show: false, caregiverId: null, caregiverName: '' })
									}
									disabled={deleting}
									className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
								>
									Cancel
								</button>
								<button
									type="button"
									onClick={handleDeleteConfirm}
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
