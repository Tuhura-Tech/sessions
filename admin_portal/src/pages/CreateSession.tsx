import { ArrowLeft } from 'lucide-react';
import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import Sidebar from '../components/Sidebar';
import { toSessionCreate } from '../lib/mappers';
import { adminApi } from '../services/api';
import type { SessionBlock, SessionLocation } from '../types';

const CreateSession: React.FC = () => {
	const navigate = useNavigate();
	const [locations, setLocations] = useState<SessionLocation[]>([]);
	const [blocks, setBlocks] = useState<SessionBlock[]>([]);
	const [isSubmitting, setIsSubmitting] = useState(false);

	const [formData, setFormData] = useState({
		name: '',
		year: new Date().getFullYear(),
		locationId: '',
		ageLower: '',
		ageUpper: '',
		dayOfWeek: '',
		startTime: '',
		endTime: '',
		capacity: '16',
		waitlist: false,
		description: '',
		photoAlbumUrl: '',
		internalNotes: '',
		sessionType: 'term' as 'term' | 'special',
		blocks: [] as string[],
	});

	const loadFormData = useCallback(async () => {
		try {
			const [locationsData, blocksData] = await Promise.all([
				adminApi.getLocations(),
				adminApi.getBlocks(),
			]);
			setLocations(locationsData);
			setBlocks(blocksData);
		} catch (error) {
			console.error('Failed to load form data:', error);
		}
	}, []);

	useEffect(() => {
		loadFormData();
	}, [loadFormData]);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();

		try {
			setIsSubmitting(true);
			const sessionCreate = toSessionCreate({
				name: formData.name,
				year: formData.year,
				locationId: formData.locationId,
				ageLower: Number.parseInt(String(formData.ageLower), 10),
				ageUpper: Number.parseInt(String(formData.ageUpper), 10),
				dayOfWeek: Number.parseInt(String(formData.dayOfWeek), 10),
				startTime: formData.startTime,
				endTime: formData.endTime,
				capacity: Number.parseInt(String(formData.capacity), 10),
				sessionType: formData.sessionType,
				description: formData.description || null,
				photoAlbumUrl: formData.photoAlbumUrl || null,
				internalNotes: formData.internalNotes || null,
				blocks: formData.blocks,
			});

			const created = await adminApi.createSession(sessionCreate);
			navigate(`/sessions/${created.id}`);
		} catch (error) {
			console.error('Failed to create session:', error);
			alert('Failed to create session');
		} finally {
			setIsSubmitting(false);
		}
	};

	const daysOfWeek = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

	return (
		<div className="flex min-h-screen">
			<Sidebar />

			<div className="flex-1">
				<Layout>
					<button
						type="button"
						onClick={() => navigate('/sessions')}
						className="mb-6 flex items-center text-gray-600 hover:text-gray-900"
					>
						<ArrowLeft className="mr-2 h-4 w-4" />
						Back to Sessions
					</button>

					<div className="rounded-lg bg-white p-6 shadow">
						<h1 className="mb-6 text-2xl font-bold text-gray-900">Create New Session</h1>

						<form onSubmit={handleSubmit} className="space-y-6">
							<div className="grid grid-cols-1 gap-6 md:grid-cols-2">
								<div className="md:col-span-2">
									<label
										htmlFor="session-name-"
										className="block text-sm font-medium text-gray-700"
									>
										Session Name *
									</label>
									<input
										id="session-name-"
										type="text"
										required
										value={formData.name}
										onChange={(e) => setFormData({ ...formData, name: e.target.value })}
										className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
									/>
								</div>

								<div>
									<label htmlFor="year-" className="block text-sm font-medium text-gray-700">
										Year *
									</label>
									<input
										id="year-"
										type="number"
										required
										value={formData.year}
										onChange={(e) =>
											setFormData({
												...formData,
												year: Number.parseInt(e.target.value, 10),
											})
										}
										className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
									/>
								</div>

								<div>
									<label
										htmlFor="session-type-"
										className="block text-sm font-medium text-gray-700"
									>
										Session Type *
									</label>
									<select
										id="session-type-"
										required
										value={formData.sessionType}
										onChange={(e) =>
											setFormData({
												...formData,
												sessionType: e.target.value as 'term' | 'special',
											})
										}
										className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
									>
										<option value="term">Term (Recurring)</option>
										<option value="special">Special (One-off)</option>
									</select>
								</div>

								<div>
									<label htmlFor="location" className="block text-sm font-medium text-gray-700">
										Location
									</label>
									<select
										id="location"
										value={formData.locationId}
										onChange={(e) =>
											setFormData({
												...formData,
												locationId: e.target.value,
											})
										}
										className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
									>
										<option value="">Select a location</option>
										{locations.map((loc) => (
											<option key={loc.id} value={loc.id}>
												{loc.name}
											</option>
										))}
									</select>
								</div>

								<div>
									<label htmlFor="day-of-week" className="block text-sm font-medium text-gray-700">
										Day of Week
									</label>
									<select
										id="day-of-week"
										value={formData.dayOfWeek}
										onChange={(e) => setFormData({ ...formData, dayOfWeek: e.target.value })}
										className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
									>
										<option value="">Select a day</option>
										{daysOfWeek.map((day, index) => (
											<option key={day} value={index}>
												{day}
											</option>
										))}
									</select>
								</div>

								<div>
									<label htmlFor="start-time" className="block text-sm font-medium text-gray-700">
										Start Time
									</label>
									<input
										id="start-time"
										type="time"
										value={formData.startTime}
										onChange={(e) => setFormData({ ...formData, startTime: e.target.value })}
										className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
									/>
								</div>

								<div>
									<label htmlFor="end-time" className="block text-sm font-medium text-gray-700">
										End Time
									</label>
									<input
										id="end-time"
										type="time"
										value={formData.endTime}
										onChange={(e) => setFormData({ ...formData, endTime: e.target.value })}
										className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
									/>
								</div>

								<div>
									<label htmlFor="age-lower" className="block text-sm font-medium text-gray-700">
										Age Lower
									</label>
									<select
										id="age-lower"
										value={formData.ageLower}
										onChange={(e) => setFormData({ ...formData, ageLower: e.target.value })}
										className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
									>
										<option value="">No minimum</option>
										{Array.from({ length: 21 }, (_, i) => i + 5).map((age) => (
											<option key={age} value={age}>
												{age}
											</option>
										))}
									</select>
								</div>

								<div>
									<label htmlFor="age-upper" className="block text-sm font-medium text-gray-700">
										Age Upper
									</label>
									<select
										id="age-upper"
										value={formData.ageUpper}
										onChange={(e) => setFormData({ ...formData, ageUpper: e.target.value })}
										className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
									>
										<option value="">No maximum</option>
										{Array.from({ length: 21 }, (_, i) => i + 5).map((age) => (
											<option key={age} value={age}>
												{age}
											</option>
										))}
									</select>
								</div>

								<div>
									<label htmlFor="capacity" className="block text-sm font-medium text-gray-700">
										Capacity
									</label>
									<select
										id="capacity"
										value={formData.capacity}
										onChange={(e) => setFormData({ ...formData, capacity: e.target.value })}
										className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
									>
										<option value="">Select capacity</option>
										{Array.from({ length: 46 }, (_, i) => i + 5).map((cap) => (
											<option key={cap} value={cap}>
												{cap}
											</option>
										))}
									</select>
								</div>

								<div className="flex items-center">
									<input
										type="checkbox"
										checked={formData.waitlist}
										onChange={(e) => setFormData({ ...formData, waitlist: e.target.checked })}
										className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
									/>
									{/* biome-ignore lint/a11y/noLabelWithoutControl: label is adjacent to checkbox */}
									<label className="ml-2 block text-sm text-gray-900">Enable waitlist</label>
								</div>

								<div className="md:col-span-2">
									{/* biome-ignore lint/a11y/noLabelWithoutControl: label headers a section */}
									<label className="block text-sm font-medium text-gray-700">
										Associated Blocks (for term sessions)
									</label>
									<div className="mt-2 space-y-2">
										{blocks.map((block) => (
											<label key={block.id} className="flex items-center">
												<input
													type="checkbox"
													checked={formData.blocks.includes(block.id)}
													onChange={(e) => {
														if (e.target.checked) {
															setFormData({
																...formData,
																blocks: [...formData.blocks, block.id],
															});
														} else {
															setFormData({
																...formData,
																blocks: formData.blocks.filter((id) => id !== block.id),
															});
														}
													}}
													className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
												/>
												<span className="ml-2 text-sm text-gray-900">
													{block.name} ({block.block_type}) - {block.year}
												</span>
											</label>
										))}
									</div>
								</div>

								<div className="md:col-span-2">
									<label
										htmlFor="description"
										className="block text-sm font-medium text-gray-700"
									>
										Description
									</label>
									<textarea
										id="description"
										rows={3}
										value={formData.description}
										onChange={(e) => setFormData({ ...formData, description: e.target.value })}
										className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
									/>
								</div>

							</div>

							<div className="flex justify-end gap-4">
								<button
									type="button"
									onClick={() => navigate('/sessions')}
									className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
								>
									Cancel
								</button>
								<button
									type="submit"
									disabled={isSubmitting}
									className="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
								>
									{isSubmitting ? 'Creating...' : 'Create Session'}
								</button>
							</div>
						</form>
					</div>
				</Layout>
			</div>
		</div>
	);
};

export default CreateSession;
