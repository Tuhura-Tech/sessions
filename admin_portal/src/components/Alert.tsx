import { AlertCircle, CheckCircle, InfoIcon, X } from 'lucide-react';
import type React from 'react';

interface AlertProps {
	type: 'error' | 'success' | 'info' | 'warning';
	title?: string;
	message: string;
	onClose?: () => void;
	dismissible?: boolean;
}

export const Alert: React.FC<AlertProps> = ({
	type,
	title,
	message,
	onClose,
	dismissible = true,
}) => {
	const styles = {
		error: 'bg-red-50 border-red-200 text-red-700',
		success: 'bg-green-50 border-green-200 text-green-700',
		info: 'bg-blue-50 border-blue-200 text-blue-700',
		warning: 'bg-yellow-50 border-yellow-200 text-yellow-700',
	};

	const icons = {
		error: <AlertCircle className="h-5 w-5" />,
		success: <CheckCircle className="h-5 w-5" />,
		info: <InfoIcon className="h-5 w-5" />,
		warning: <AlertCircle className="h-5 w-5" />,
	};

	return (
		<div className={`flex items-start gap-3 rounded-lg border px-4 py-3 ${styles[type]}`}>
			<div className="shrink-0">{icons[type]}</div>
			<div className="flex-1">
				{title && <h3 className="font-semibold">{title}</h3>}
				<p className={title ? 'mt-1 text-sm' : ''}>{message}</p>
			</div>
			{dismissible && onClose && (
				<button type="button" onClick={onClose} className="shrink-0 opacity-75 hover:opacity-100">
					<X className="h-5 w-5" />
				</button>
			)}
		</div>
	);
};

export const ErrorMessage: React.FC<{ error: string }> = ({ error }) => (
	<Alert type="error" message={error} dismissible={false} />
);

export const SuccessMessage: React.FC<{
	message: string;
	onClose?: () => void;
}> = ({ message, onClose }) => <Alert type="success" message={message} onClose={onClose} />;

export const LoadingSpinner: React.FC<{ text?: string }> = ({ text = 'Loading...' }) => (
	<div className="flex flex-col items-center justify-center py-12">
		<div className="h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600" />
		<p className="mt-4 text-gray-600">{text}</p>
	</div>
);

export const EmptyState: React.FC<{
	message: string;
	action?: React.ReactNode;
}> = ({ message, action }) => (
	<div className="py-12 text-center">
		<p className="mb-4 text-gray-500">{message}</p>
		{action}
	</div>
);
