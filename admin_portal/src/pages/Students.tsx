import { Users } from 'lucide-react';
import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import Sidebar from '../components/Sidebar';
import { formatDate } from '../lib/utils';
import { adminApi } from '../services/api';
import type { ChildDetails } from '../types';

const Students: React.FC = () => {
	const [children, setChildren] = useState<ChildDetails[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [searchTerm, setSearchTerm] = useState('');
	const navigate = useNavigate();

	const loadChildren = useCallback(async () => {
		try {
			setIsLoading(true);
			const data = await adminApi.listChildren();
			setChildren(data);
		} catch (error) {
			console.error('Failed to load children:', error);
		} finally {
			setIsLoading(false);
		}
	}, []);

	useEffect(() => {
		loadChildren();
	}, [loadChildren]);

	const filteredChildren = children.filter((child) =>
		child.name.toLowerCase().includes(searchTerm.toLowerCase()),
	);

	return (
		<div className="flex min-h-screen">
			<Sidebar />
			<div className="flex-1">
				<Layout title="Student Management">
					<div className="mb-6 rounded-lg bg-white p-4 shadow">
						<input
							type="text"
							placeholder="Search students by name..."
							value={searchTerm}
							onChange={(e) => setSearchTerm(e.target.value)}
							className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-blue-500 focus:ring-blue-500"
						/>
					</div>

					<div className="overflow-hidden rounded-lg bg-white shadow">
						{isLoading ? (
							<div className="flex h-64 items-center justify-center">
								<div className="h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600" />
							</div>
						) : filteredChildren.length === 0 ? (
							<div className="flex flex-col items-center justify-center py-12 text-gray-500">
								<Users className="mb-4 h-12 w-12 opacity-50" />
								<p>{searchTerm ? 'No students matching your search.' : 'No students found.'}</p>
							</div>
						) : (
							<div className="overflow-x-auto">
								<table className="min-w-full divide-y divide-gray-200">
									<thead className="bg-gray-50">
										<tr>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Name
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Date of Birth
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Media Consent
											</th>
											<th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
												Actions
											</th>
										</tr>
									</thead>
									<tbody className="divide-y divide-gray-200 bg-white">
										{filteredChildren.map((child) => (
											<tr key={child.id} className="hover:bg-gray-50">
												<td className="px-6 py-4 text-sm font-medium whitespace-nowrap text-gray-900">
													{child.name}
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-600">
													{child.date_of_birth ? formatDate(child.date_of_birth) : '—'}
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-600">
													{child.media_consent ? (
														<span className="inline-flex items-center rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800">
															Yes
														</span>
													) : (
														<span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-800">
															No
														</span>
													)}
												</td>
												<td className="px-6 py-4 text-sm whitespace-nowrap">
													<button
														type="button"
														onClick={() => navigate(`/students/${child.id}`)}
														className="font-medium text-blue-600 hover:text-blue-900"
													>
														View Details
													</button>
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						)}
					</div>
				</Layout>
			</div>
		</div>
	);
};

export default Students;
