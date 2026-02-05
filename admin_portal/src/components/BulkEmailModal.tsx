import { Send } from 'lucide-react';
import type React from 'react';
import { useState } from 'react';
import Modal from './Modal';

interface BulkEmailModalProps {
	isOpen: boolean;
	onClose: () => void;
	onSend: (content: string, status?: string) => Promise<void>;
}

const BulkEmailModal: React.FC<BulkEmailModalProps> = ({ isOpen, onClose, onSend }) => {
	const [content, setContent] = useState('');
	const [selectedStatus, setSelectedStatus] = useState<string>('confirmed');
	const [isSending, setIsSending] = useState(false);

	const handleSend = async () => {
		if (!content.trim()) {
			alert('Please enter email content');
			return;
		}

		try {
			setIsSending(true);
			await onSend(content, selectedStatus);
			setContent('');
			setSelectedStatus('confirmed');
			onClose();
		} finally {
			setIsSending(false);
		}
	};

	return (
		<Modal isOpen={isOpen} title="Send Bulk Email" onClose={onClose}>
			<div className="space-y-4">
				<div>
					<label htmlFor="status" className="mb-2 block text-sm font-medium text-gray-700">
						Recipient Status
					</label>
					<select
						id="status"
						value={selectedStatus}
						onChange={(e) => setSelectedStatus(e.target.value)}
						className="w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500"
					>
						<option value="confirmed">Confirmed</option>
						<option value="waitlisted">Waitlisted</option>
						<option value="all">All</option>
					</select>
				</div>

				<div>
					<label htmlFor="content" className="mb-2 block text-sm font-medium text-gray-700">
						Email Content
					</label>
					<textarea
						id="content"
						value={content}
						onChange={(e) => setContent(e.target.value)}
						rows={8}
						placeholder="Type your email message here..."
						className="w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500"
					/>
				</div>

				<div className="flex justify-end gap-3">
					<button
						type="button"
						onClick={onClose}
						disabled={isSending}
						className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
					>
						Cancel
					</button>
					<button
						type="button"
						onClick={handleSend}
						disabled={isSending || !content.trim()}
						className="inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
					>
						<Send className="mr-2 h-4 w-4" />
						{isSending ? 'Sending...' : 'Send Email'}
					</button>
				</div>
			</div>
		</Modal>
	);
};

export default BulkEmailModal;
