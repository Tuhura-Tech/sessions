import type React from 'react';
import type { ReactNode } from 'react';

interface ModalProps {
	isOpen: boolean;
	title: string;
	description?: string;
	children?: ReactNode;
	onClose: () => void;
	onConfirm?: () => void | Promise<void>;
	confirmText?: string;
	cancelText?: string;
	isDangerous?: boolean;
	isLoading?: boolean;
}

const Modal: React.FC<ModalProps> = ({
	isOpen,
	title,
	description,
	children,
	onClose,
	onConfirm,
	confirmText = 'Confirm',
	cancelText = 'Cancel',
	isDangerous = false,
	isLoading = false,
}) => {
	if (!isOpen) return null;

	return (
		<div className="bg-opacity-50 fixed inset-0 z-50 flex items-center justify-center bg-black p-4">
			<div className="w-full max-w-md rounded-lg bg-white shadow-xl">
				{/* Header */}
				<div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
					<h2 className="text-lg font-semibold text-gray-900">{title}</h2>
					<button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600">
						<span className="sr-only">Close</span>×
					</button>
				</div>

				{/* Content */}
				<div className="px-6 py-4">
					{description && <p className="mb-4 text-sm text-gray-600">{description}</p>}
					{children}
				</div>

				{/* Footer */}
				{onConfirm && (
					<div className="flex justify-end gap-3 border-t border-gray-200 px-6 py-4">
						<button
							type="button"
							onClick={onClose}
							disabled={isLoading}
							className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
						>
							{cancelText}
						</button>
						<button
							type="button"
							onClick={onConfirm}
							disabled={isLoading}
							className={`rounded-md border border-transparent px-4 py-2 text-sm font-medium text-white ${
								isDangerous ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
							} disabled:opacity-50`}
						>
							{isLoading ? 'Loading...' : confirmText}
						</button>
					</div>
				)}
			</div>
		</div>
	);
};

export default Modal;
