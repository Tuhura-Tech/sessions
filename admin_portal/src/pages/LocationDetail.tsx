import { ArrowLeft, Mail, MapPin, Phone } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import Layout from '../components/Layout';
import Sidebar from '../components/Sidebar';
import { adminApi } from '../services/api';
import type { Session, SessionLocation } from '../types';

function dayOfWeekAsString(dayIndex: number | null): string {
	if (dayIndex === null || dayIndex === undefined) return '';
	return (
		['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][dayIndex] || ''
	);
}

export default function LocationDetail() {
	const { id } = useParams<{ id: string }>();
	const navigate = useNavigate();
	const [location, setLocation] = useState<SessionLocation | null>(null);
	const [sessions, setSessions] = useState<Session[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		const fetchData = async () => {
			try {
				if (!id) {
					setError('Location ID not provided');
					return;
				}
				const [locationData, sessionsData] = await Promise.all([
					adminApi.getLocation(id),
					adminApi.getLocationSessions(id, undefined, true),
				]);
				setLocation(locationData);
				setSessions(sessionsData);
			} catch (err) {
				setError('Failed to load location');
				console.error(err);
			} finally {
				setLoading(false);
			}
		};

		fetchData();
	}, [id]);

	if (loading) {
		return (
			<div className="flex min-h-screen">
				<Sidebar />
				<div className="flex-1">
					<Layout title="Location Details">
						<div className="flex h-screen items-center justify-center">
							<div className="text-center">
								<div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-blue-500" />
								<p className="text-gray-600">Loading location...</p>
							</div>
						</div>
					</Layout>
				</div>
			</div>
		);
	}

	if (error || !location) {
		return (
			<div className="flex min-h-screen">
				<Sidebar />
				<div className="flex-1">
					<Layout title="Location Details">
						<div className="rounded-lg bg-red-50 p-4 text-red-800">
							{error || 'Location not found'}
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
				<Layout title={location.name}>
					<div className="space-y-6">
						{/* Header */}
						<div className="flex items-center justify-between">
							<button
								type="button"
								onClick={() => navigate('/locations')}
								className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
							>
								<ArrowLeft className="h-5 w-5" />
								Back to Locations
							</button>
						</div>

						{/* Details Section */}
						<div className="grid grid-cols-1 gap-6 md:grid-cols-2">
							{/* Address & Location Info */}
							<div className="rounded-lg bg-white p-6 shadow-md">
								<h2 className="mb-4 text-xl font-bold text-gray-900">Location Info</h2>
								<div className="space-y-3">
									{location.address && (
										<div className="flex gap-3">
											<MapPin className="mt-1 h-5 w-5 shrink-0 text-gray-500" />
											<div>
												<p className="text-sm font-medium text-gray-500">Address</p>
												<p className="text-gray-900">{location.address}</p>
											</div>
										</div>
									)}
									{location.lat && location.lng && (
										<div className="flex gap-3 border-t pt-3">
											<MapPin className="mt-1 h-5 w-5 shrink-0 text-gray-500" />
											<div>
												<p className="text-sm font-medium text-gray-500">Coordinates</p>
												<p className="text-gray-900">
													{location.lat.toFixed(6)}, {location.lng.toFixed(6)}
												</p>
											</div>
										</div>
									)}
								</div>
							</div>

							{/* Contact Info */}
							<div className="rounded-lg bg-white p-6 shadow-md">
								<h2 className="mb-4 text-xl font-bold text-gray-900">Contact Info</h2>
								<div className="space-y-3">
									{location.contact_name && (
										<div>
											<p className="text-sm font-medium text-gray-500">Contact Name</p>
											<p className="text-gray-900">{location.contact_name}</p>
										</div>
									)}
									{location.contact_phone && (
										<div className="flex gap-3 border-t pt-2">
											<Phone className="mt-1 h-5 w-5 shrink-0 text-gray-500" />
											<div>
												<p className="text-sm font-medium text-gray-500">Phone</p>
												<a
													href={`tel:${location.contact_phone}`}
													className="text-blue-600 hover:underline"
												>
													{location.contact_phone}
												</a>
											</div>
										</div>
									)}
									{location.contact_email && (
										<div className="flex gap-3 border-t pt-2">
											<Mail className="mt-1 h-5 w-5 shrink-0 text-gray-500" />
											<div>
												<p className="text-sm font-medium text-gray-500">Email</p>
												<a
													href={`mailto:${location.contact_email}`}
													className="text-blue-600 hover:underline"
												>
													{location.contact_email}
												</a>
											</div>
										</div>
									)}
								</div>
							</div>
						</div>

						{/* Sessions at this location */}
						<div className="rounded-lg bg-white shadow">
							<div className="border-b border-gray-200 px-6 py-4">
								<h2 className="text-lg font-semibold text-gray-900">Sessions</h2>
							</div>
							<div className="p-6">
								{sessions.length === 0 ? (
									<div className="text-center text-gray-500">No sessions at this location</div>
								) : (
									<div className="overflow-x-auto">
										<table className="min-w-full divide-y divide-gray-200">
											<thead className="bg-gray-50">
												<tr>
													<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
														Name
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
													<th className="px-6 py-3 text-right text-xs font-medium tracking-wider text-gray-500 uppercase">
														Actions
													</th>
												</tr>
											</thead>
											<tbody className="divide-y divide-gray-200 bg-white">
												{sessions.map((session) => (
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
															{dayOfWeekAsString(session.day_of_week)} {session.start_time}-
															{session.end_time}
														</td>
														<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
															{session.capacity || 'N/A'}
														</td>
														<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
															{session.confirmed_count || 0}/{session.capacity || '?'}
														</td>
														<td className="px-6 py-4 text-right text-sm font-medium whitespace-nowrap">
															<Link
																to={`/sessions/${session.id}`}
																className="text-blue-600 hover:text-blue-900"
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
						</div>
					</div>
				</Layout>
			</div>
		</div>
	);
}
