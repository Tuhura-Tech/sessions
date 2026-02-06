import { Edit2, Plus } from 'lucide-react';
import type React from 'react';
import { useCallback, useEffect, useState } from 'react';
import { ErrorMessage, LoadingSpinner, SuccessMessage } from '../components/Alert';
import { FormInput, FormSelect } from '../components/FormComponents';
import Layout from '../components/Layout';
import Modal from '../components/Modal';
import Sidebar from '../components/Sidebar';
import { formatDate } from '../lib/utils';
import { adminApi } from '../services/api';
import type { SessionBlock } from '../types';

type Block = SessionBlock;

const Blocks: React.FC = () => {
	const [blocks, setBlocks] = useState<Block[]>([]);
	const [filteredBlocks, setFilteredBlocks] = useState<Block[]>([]);
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [success, setSuccess] = useState<string | null>(null);
	const [selectedYear] = useState<number>(new Date().getFullYear());
	const [showModal, setShowModal] = useState(false);
	const [editingBlock, setEditingBlock] = useState<Block | null>(null);

	const [formData, setFormData] = useState({
		year: new Date().getFullYear(),
		block_type: 'term_1' as Block['block_type'],
		name: '',
		start_date: '',
		end_date: '',
		timezone: 'Pacific/Auckland',
	});

	const loadBlocks = useCallback(async () => {
		try {
			setIsLoading(true);
			setError(null);
			const data = await adminApi.getBlocks(selectedYear);
			setBlocks(data);
		} catch (err) {
			setError('Failed to load blocks');
			console.error(err);
		} finally {
			setIsLoading(false);
		}
	}, [selectedYear]);

	useEffect(() => {
		loadBlocks();
	}, [loadBlocks]);

	useEffect(() => {
		const filtered = blocks.filter((block) => block.year === selectedYear);
		setFilteredBlocks(filtered);
	}, [blocks, selectedYear]);

	const handleCreate = () => {
		setEditingBlock(null);
		setFormData({
			year: selectedYear,
			block_type: 'term_1',
			name: '',
			start_date: '',
			end_date: '',
			timezone: 'Pacific/Auckland',
		});
		setShowModal(true);
	};

	const handleEdit = (block: Block) => {
		setEditingBlock(block);
		setFormData({
			year: block.year,
			block_type: block.block_type,
			name: block.name,
			start_date: block.start_date ?? '',
			end_date: block.end_date ?? '',
			timezone: block.timezone || 'Pacific/Auckland',
		});
		setShowModal(true);
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError(null);
		setSuccess(null);

		try {
			if (editingBlock) {
				await adminApi.updateBlock(editingBlock.id, formData);
				setSuccess('Block updated successfully');
			} else {
				await adminApi.createBlock(formData);
				setSuccess('Block created successfully');
			}

			setShowModal(false);
			loadBlocks();
		} catch (err) {
			const error = err as { response?: { data?: { detail?: string } } };
			setError(error.response?.data?.detail || 'Failed to save block');
		}
	};

	const blockTypeLabels = {
		term_1: 'Term 1',
		term_2: 'Term 2',
		term_3: 'Term 3',
		term_4: 'Term 4',
		special: 'Special',
	};

	const years = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - 1 + i);

	if (isLoading) {
		return (
			<div className="flex min-h-screen">
				<Sidebar />
				<div className="flex flex-1 items-center justify-center">
					<LoadingSpinner />
				</div>
			</div>
		);
	}

	return (
		<div className="flex min-h-screen">
			<Sidebar />

			<div className="flex-1">
				<Layout
					title="Session Blocks"
					actions={
						<button
							type="button"
							onClick={handleCreate}
							className="inline-flex items-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
						>
							<Plus className="mr-2 h-4 w-4" />
							Create Block
						</button>
					}
				>
					{error && <ErrorMessage error={error} />}
					{success && <SuccessMessage message={success} onClose={() => setSuccess(null)} />}

					{/* Year Filter */}
					<div className="mb-6">
					<label htmlFor="filter-year" className="mb-2 block text-sm font-medium text-gray-700">Filter by Year</label>
					<select
						id="filter-year"
							className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
						>
							{years.map((year) => (
								<option key={year} value={year}>
									{year}
								</option>
							))}
						</select>
					</div>

					{/* Blocks Table */}
					<div className="overflow-hidden rounded-lg bg-white shadow">
						<table className="min-w-full divide-y divide-gray-200">
							<thead className="bg-gray-50">
								<tr>
									<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
										Type
									</th>
									<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
										Name
									</th>
									<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
										Start Date
									</th>
									<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
										End Date
									</th>
									<th className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase">
										Actions
									</th>
								</tr>
							</thead>
							<tbody className="divide-y divide-gray-200 bg-white">
								{filteredBlocks.map((block) => (
									<tr key={block.id}>
										<td className="px-6 py-4 text-sm font-medium whitespace-nowrap text-gray-900">
											{block.block_type ? blockTypeLabels[block.block_type] : '—'}
										</td>
										<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
											{block.name}
										</td>
										<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
											{block.start_date ? formatDate(block.start_date) : '—'}
										</td>
										<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
											{block.end_date ? formatDate(block.end_date) : '—'}
										</td>
										<td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
											<button
												type="button"
												onClick={() => handleEdit(block)}
												className="mr-4 text-blue-600 hover:text-blue-900"
											>
												<Edit2 className="h-4 w-4" />
											</button>
										</td>
									</tr>
								))}
							</tbody>
						</table>

						{filteredBlocks.length === 0 && (
							<div className="py-12 text-center text-gray-500">
								No blocks found for {selectedYear}. Create one to get started.
							</div>
						)}
					</div>
				</Layout>
			</div>

			{/* Create/Edit Modal */}
			{showModal && (
				<Modal
					isOpen={showModal}
					onClose={() => setShowModal(false)}
					title={editingBlock ? 'Edit Block' : 'Create Block'}
				>
					<form onSubmit={handleSubmit} className="space-y-4">
						<FormSelect
							label="Year"
							value={formData.year}
							onChange={(e) => setFormData({ ...formData, year: Number(e.target.value) })}
							required
						>
							{years.map((year) => (
								<option key={year} value={year}>
									{year}
								</option>
							))}
						</FormSelect>

						<FormSelect
							label="Block Type"
							value={formData.block_type}
							onChange={(e) =>
								setFormData({
									...formData,
									block_type: e.target.value as Block['block_type'],
								})
							}
							required
						>
							<option value="term_1">Term 1</option>
							<option value="term_2">Term 2</option>
							<option value="term_3">Term 3</option>
							<option value="term_4">Term 4</option>
							<option value="special">Special</option>
						</FormSelect>

						<FormInput
							label="Name"
							type="text"
							value={formData.name}
							onChange={(e) => setFormData({ ...formData, name: e.target.value })}
							required
							placeholder="e.g., Term 1 2024"
						/>

						<FormInput
							label="Start Date"
							type="date"
							value={formData.start_date}
							onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
							required
						/>

						<FormInput
							label="End Date"
							type="date"
							value={formData.end_date}
							onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
							required
						/>

						<div className="mt-6 flex justify-end gap-3">
							<button
								type="button"
								onClick={() => setShowModal(false)}
								className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
							>
								Cancel
							</button>
							<button
								type="submit"
								className="rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700"
							>
								{editingBlock ? 'Update' : 'Create'}
							</button>
						</div>
					</form>
				</Modal>
			)}
		</div>
	);
};

export default Blocks;
