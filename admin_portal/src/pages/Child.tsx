import { ArrowLeft, Trash2 } from 'lucide-react';
import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import Layout from '../components/Layout';
import Modal from '../components/Modal';
import Sidebar from '../components/Sidebar';
import { calculateAge, formatDate } from '../lib/utils';
import { adminApi } from '../services/api';
import type { ChildDetails, Signup } from '../types';

const ChildPage: React.FC = () => {
	const { id } = useParams<{ id: string }>();
	const navigate = useNavigate();

	const [child, setChild] = useState<ChildDetails | null>(null);
	const [signups, setSignups] = useState<(Signup & { sessionName?: string; sessionId?: string })[]>(
		[],
	);
	const [isLoading, setIsLoading] = useState(true);
	const [showDeleteModal, setShowDeleteModal] = useState(false);
	const [deleting, setDeleting] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const loadChild = useCallback(async (childId: string) => {
		try {
			setIsLoading(true);
			const [childData, allSignups, allSessions] = await Promise.all([
				adminApi.getChild(childId),
				adminApi.getStudentSignups(childId).catch(() => []),
				adminApi.getSessions(new Date().getFullYear()).catch(() => []),
			]);
			setChild(childData);

			// Enrich signups with session names
			const enrichedSignups = allSignups.map((signup) => {
				const session = allSessions.find((s) => s.id === signup.session_id);
				return {
					...signup,
					sessionName: session?.name || 'Unknown Session',
					sessionId: signup.session_id,
				};
			});
			setSignups(enrichedSignups);
		} catch (err) {
			console.error(err);
			alert('Failed to load child details');
		} finally {
			setIsLoading(false);
		}
	}, []);

	useEffect(() => {
		if (id) {
			loadChild(id);
		}
	}, [id, loadChild]);

	const handleDeleteChild = async () => {
		if (!id) return;

		try {
			setDeleting(true);
			setError(null);
			await adminApi.deleteStudent(id);
			navigate('/students');
		} catch (err) {
			console.error('Failed to delete child:', err);
			const error = err as { response?: { data?: { detail?: string } } };
			setError(error.response?.data?.detail || 'Failed to delete child');
		} finally {
			setDeleting(false);
		}
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

	if (!child) {
		return (
			<div className="flex min-h-screen">
				<Sidebar />
				<div className="flex-1">
					<Layout>
						<div className="py-12 text-center">
							<p className="text-gray-500">Child not found</p>
							<button
								type="button"
								onClick={() => navigate(-1)}
								className="mt-4 inline-block text-blue-600 hover:text-blue-700"
							>
								Go back
							</button>
						</div>
					</Layout>
				</div>
			</div>
		);
	}

	const caregiverId = child.caregiver?.id ?? child.caregiver_id;
	const hasCaregiverId = Boolean(caregiverId && caregiverId !== 'undefined');

	return (
		<div className="flex min-h-screen">
			<Sidebar />
			<div className="flex-1">
				<Layout
					title={child.name}
					actions={
						<button
							type="button"
							onClick={() => setShowDeleteModal(true)}
							className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700"
						>
							<Trash2 className="h-4 w-4" />
							Delete Child
						</button>
					}
				>
					<button
						type="button"
						onClick={() => navigate(-1)}
						className="mb-4 flex items-center text-gray-600 hover:text-gray-900"
					>
						<ArrowLeft className="mr-2 h-4 w-4" /> Back
					</button>

					<div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
						<div className="rounded-lg bg-white p-6 shadow lg:col-span-1">
							<h2 className="mb-4 text-lg font-semibold text-gray-900">Profile</h2>
							<dl className="space-y-3 text-sm text-gray-800">
								<div>
									<dt className="font-medium text-gray-600">Name</dt>
									<dd>{child.name}</dd>
								</div>
								<div>
									<dt className="font-medium text-gray-600">Date of birth</dt>
									<dd>{formatDate(child.date_of_birth)}</dd>
								</div>
								<div>
									<dt className="font-medium text-gray-600">Age</dt>
									<dd>{calculateAge(child.date_of_birth)} years</dd>
								</div>
								<div>
									<dt className="font-medium text-gray-600">Media consent</dt>
									<dd>{child.media_consent ? 'Yes' : 'No'}</dd>
								</div>
								<div>
									<dt className="font-medium text-gray-600">Medical info</dt>
									<dd>{child.medical_info || 'None'}</dd>
								</div>
								<div>
									<dt className="font-medium text-gray-600">Other info</dt>
									<dd>{child.other_info || 'None'}</dd>
								</div>
								<div className="border-t pt-3">
									<dt className="font-medium text-gray-600">Caregiver</dt>
									<dd className="mt-1">
										{hasCaregiverId ? (
											<Link
												to={`/caregivers/${caregiverId}`}
												className="text-blue-600 hover:text-blue-900 hover:underline"
											>
												{child.caregiver?.name || 'View Caregiver'}
											</Link>
										) : (
											<span className="text-gray-500">No caregiver assigned</span>
										)}
									</dd>
								</div>
							</dl>
						</div>
					</div>

					{/* Signups Section */}
					<div className="mt-6 rounded-lg bg-white shadow">
						<div className="border-b border-gray-200 px-6 py-4">
							<h2 className="text-lg font-semibold text-gray-900">Enrollments</h2>
						</div>
						<div className="p-6">
							{signups.length === 0 ? (
								<div className="text-center text-gray-500">No enrollments yet</div>
							) : (
								<div className="overflow-x-auto">
									<table className="min-w-full divide-y divide-gray-200">
										<thead className="bg-gray-50">
											<tr>
												<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
													Session
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
											{signups.map((signup) => (
												<tr key={signup.id} className="hover:bg-gray-50">
													<td className="px-6 py-4 whitespace-nowrap">
														<Link
															to={`/sessions/${signup.session_id}`}
															className="text-sm font-medium text-blue-600 hover:text-blue-900"
														>
															{signup.sessionName}
														</Link>
													</td>
													<td className="px-6 py-4 whitespace-nowrap">
														<span
															className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${
																signup.status === 'confirmed'
																	? 'bg-green-100 text-green-800'
																	: signup.status === 'waitlisted'
																		? 'bg-yellow-100 text-yellow-800'
																		: signup.status === 'pending'
																			? 'bg-blue-100 text-blue-800'
																			: 'bg-gray-100 text-gray-800'
															}`}
														>
															{signup.status.charAt(0).toUpperCase() + signup.status.slice(1)}
														</span>
													</td>
													<td className="px-6 py-4 text-right text-sm font-medium whitespace-nowrap">
														<Link
															to={`/sessions/${signup.session_id}`}
															className="text-blue-600 hover:text-blue-900"
														>
															View Session
														</Link>
													</td>
												</tr>
											))}
										</tbody>
									</table>
								</div>
							)}
						</div>
					</div>

					{/* Delete Confirmation Modal */}
					<Modal
						isOpen={showDeleteModal}
						onClose={() => !deleting && setShowDeleteModal(false)}
						title="Delete Child"
					>
						<div className="space-y-4">
							<p className="text-gray-700">
								Are you sure you want to delete <span className="font-semibold">{child.name}</span>?
								This action cannot be undone and will remove all associated signups and records.
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
									onClick={handleDeleteChild}
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
};

export default ChildPage;
