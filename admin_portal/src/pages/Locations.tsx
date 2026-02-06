import { Plus } from 'lucide-react';
import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import Sidebar from '../components/Sidebar';
import { adminApi } from '../services/api';
import type { SessionLocation } from '../types';

const Locations: React.FC = () => {
	const [locations, setLocations] = useState<SessionLocation[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [showForm, setShowForm] = useState(false);
	const [editingId, setEditingId] = useState<string | null>(null);
	const navigate = useNavigate();
	const [formData, setFormData] = useState({
		name: '',
		address: '',
		region: '',
		lat: 0,
		lng: 0,
		contactName: '',
		contactEmail: '',
		contactPhone: '',
		instructions: '',
		internalNotes: '',
	});

	const loadLocations = useCallback(async () => {
		try {
			setIsLoading(true);
			const data = await adminApi.getLocations();
			setLocations(data);
		} catch (error) {
			console.error('Failed to load locations:', error);
		} finally {
			setIsLoading(false);
		}
	}, []);

	useEffect(() => {
		loadLocations();
	}, [loadLocations]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();

		try {
			if (editingId) {
				await adminApi.updateLocation(editingId, formData);
			} else {
				await adminApi.createLocation(formData);
			}

			setShowForm(false);
			setEditingId(null);
			setFormData({
				name: '',
				address: '',
				region: '',
				lat: 0,
				lng: 0,
				contactName: '',
				contactEmail: '',
				contactPhone: '',
				instructions: '',
				internalNotes: '',
			});
			loadLocations();
		} catch (error) {
			console.error('Failed to save location:', error);
			alert('Failed to save location');
		}
	};

	const handleEdit = (location: SessionLocation) => {
		setFormData({
			name: location.name,
			address: location.address || '',
			region: location.region || '',
			lat: location.lat || 0,
			lng: location.lng || 0,
			contactName: location.contact_name || '',
			contactEmail: location.contact_email || '',
			contactPhone: location.contact_phone || '',
			instructions: location.instructions || '',
			internalNotes: location.internal_notes || '',
		});
		setEditingId(location.id);
		setShowForm(true);
	};

	const handleCancel = () => {
		setShowForm(false);
		setEditingId(null);
		setFormData({
			name: '',
			address: '',
			region: '',
			lat: 0,
			lng: 0,
			contactName: '',
			contactEmail: '',
			contactPhone: '',
			instructions: '',
			internalNotes: '',
		});
	};

	return (
		<div className="flex min-h-screen">
			<Sidebar />

			<div className="flex-1">
				<Layout
					title="Locations"
					actions={
						!showForm && (
							<button
								type="button"
								onClick={() => setShowForm(true)}
								className="inline-flex items-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
							>
								<Plus className="mr-2 h-4 w-4" />
								New Location
							</button>
						)
					}
				>
					{showForm && (
						<div className="mb-6 rounded-lg bg-white p-6 shadow">
							<h2 className="mb-4 text-lg font-semibold text-gray-900">
								{editingId ? 'Edit Location' : 'Create New Location'}
							</h2>

							<form onSubmit={handleSubmit} className="space-y-4">
								<div className="grid grid-cols-1 gap-4 md:grid-cols-2">
									<div>
										<label htmlFor="name-" className="block text-sm font-medium text-gray-700">Name *</label>
<input
						id="name-"
											type="text"
											required
											value={formData.name}
											onChange={(e) => setFormData({ ...formData, name: e.target.value })}
											className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
										/>
									</div>

									<div>
										<label htmlFor="region" className="block text-sm font-medium text-gray-700">Region</label>
<input
						id="region"
											type="text"
											value={formData.region}
											onChange={(e) => setFormData({ ...formData, region: e.target.value })}
											className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
										/>
									</div>

									<div className="md:col-span-2">
										<label htmlFor="address" className="block text-sm font-medium text-gray-700">Address</label>
<input
						id="address"
											type="text"
											value={formData.address}
											onChange={(e) => setFormData({ ...formData, address: e.target.value })}
											className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
										/>
									</div>

									<div>
										<label htmlFor="latitude-" className="block text-sm font-medium text-gray-700">Latitude *</label>
<input
						id="latitude-"
											type="number"
											step="0.000001"
											required
											value={formData.lat}
											onChange={(e) =>
												setFormData({
													...formData,
													lat: Number.parseFloat(e.target.value),
												})
											}
											className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
										/>
									</div>

									<div>
										<label htmlFor="longitude-" className="block text-sm font-medium text-gray-700">Longitude *</label>
<input
						id="longitude-"
											type="number"
											step="0.000001"
											required
											value={formData.lng}
											onChange={(e) =>
												setFormData({
													...formData,
													lng: Number.parseFloat(e.target.value),
												})
											}
											className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
										/>
									</div>

									<div>
										<label htmlFor="contact-name" className="block text-sm font-medium text-gray-700">Contact Name</label>
<input
						id="contact-name"
											type="text"
											value={formData.contactName}
											onChange={(e) =>
												setFormData({
													...formData,
													contactName: e.target.value,
												})
											}
											className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
										/>
									</div>

									<div>
										<label htmlFor="contact-email" className="block text-sm font-medium text-gray-700">Contact Email</label>
<input
						id="contact-email"
											type="email"
											value={formData.contactEmail}
											onChange={(e) =>
												setFormData({
													...formData,
													contactEmail: e.target.value,
												})
											}
											className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
										/>
									</div>

									<div>
										<label htmlFor="contact-phone" className="block text-sm font-medium text-gray-700">Contact Phone</label>
<input
						id="contact-phone"
											type="tel"
											value={formData.contactPhone}
											onChange={(e) =>
												setFormData({
													...formData,
													contactPhone: e.target.value,
												})
											}
											className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
										/>
									</div>

									<div className="md:col-span-2">									{/* biome-ignore lint/a11y/noLabelWithoutControl: label for textarea */}										<label className="block text-sm font-medium text-gray-700">Instructions</label>
										<textarea
											rows={3}
											value={formData.instructions}
											onChange={(e) =>
												setFormData({
													...formData,
													instructions: e.target.value,
												})
											}
											className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
										/>
									</div>

									<div className="md:col-span-2">									{/* biome-ignore lint/a11y/noLabelWithoutControl: label for textarea */}										<label className="block text-sm font-medium text-gray-700">
											Internal Notes
										</label>
										<textarea
											rows={3}
											value={formData.internalNotes}
											onChange={(e) =>
												setFormData({
													...formData,
													internalNotes: e.target.value,
												})
											}
											className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
										/>
									</div>
								</div>

								<div className="flex justify-end gap-4">
									<button
										type="button"
										onClick={handleCancel}
										className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
									>
										Cancel
									</button>
									<button
										type="submit"
										className="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
									>
										{editingId ? 'Update' : 'Create'} Location
									</button>
								</div>
							</form>
						</div>
					)}

					<div className="overflow-hidden rounded-lg bg-white shadow">
						{isLoading ? (
							<div className="flex h-64 items-center justify-center">
								<div className="h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600" />
							</div>
						) : (
							<div className="overflow-x-auto">
								<table className="min-w-full divide-y divide-gray-200">
									<thead className="bg-gray-50">
										<tr>
											<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
												Name
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
												Region
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
												Address
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
												Contact
											</th>
											<th className="px-6 py-3 text-right text-xs font-medium tracking-wider text-gray-500 uppercase">
												Actions
											</th>
										</tr>
									</thead>
									<tbody className="divide-y divide-gray-200 bg-white">
										{locations.map((location) => (
											<tr key={location.id} className="hover:bg-gray-50">
												<td className="px-6 py-4 text-sm font-medium whitespace-nowrap text-gray-900">
													{location.name}
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
													{location.region || '-'}
												</td>
												<td className="px-6 py-4 text-sm text-gray-500">
													{location.address || '-'}
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
													{location.contact_name || '-'}
													{location.contact_email && (
														<div className="text-xs text-gray-400">{location.contact_email}</div>
													)}
												</td>
												<td className="px-6 py-4 text-right text-sm font-medium whitespace-nowrap">
													<button
														type="button"
														onClick={() => navigate(`/locations/${location.id}`)}
														className="mr-4 text-blue-600 hover:text-blue-900"
													>
														View
													</button>
													<button
														type="button"
														onClick={() => handleEdit(location)}
														className="text-blue-600 hover:text-blue-900"
													>
														Edit
													</button>
												</td>
											</tr>
										))}
									</tbody>
								</table>
								{locations.length === 0 && (
									<div className="py-12 text-center text-gray-500">No locations yet</div>
								)}
							</div>
						)}
					</div>
				</Layout>
			</div>
		</div>
	);
};

export default Locations;
