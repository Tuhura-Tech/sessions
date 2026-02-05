import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Info, X, XCircle } from 'lucide-react';

export interface Toast {
	id: string;
	type: 'success' | 'error' | 'warning' | 'info';
	message: string;
	duration?: number;
}

interface ToastProps {
	toast: Toast;
	onDismiss: (id: string) => void;
}

function ToastItem({ toast, onDismiss }: ToastProps) {
	const [isExiting, setIsExiting] = useState(false);

	const handleDismiss = useCallback(() => {
		setIsExiting(true);
		setTimeout(() => onDismiss(toast.id), 300);
	}, [toast.id, onDismiss]);

	useEffect(() => {
		if (toast.duration && toast.duration > 0) {
			const timer = setTimeout(() => {
				handleDismiss();
			}, toast.duration);
			return () => clearTimeout(timer);
		}
	}, [toast.duration, handleDismiss]);

	const iconMap = {
		success: <CheckCircle className="w-5 h-5" />,
		error: <XCircle className="w-5 h-5" />,
		warning: <AlertCircle className="w-5 h-5" />,
		info: <Info className="w-5 h-5" />,
	};

	const colorMap = {
		success: 'bg-green-50 text-green-800 border-green-200',
		error: 'bg-red-50 text-red-800 border-red-200',
		warning: 'bg-yellow-50 text-yellow-800 border-yellow-200',
		info: 'bg-blue-50 text-blue-800 border-blue-200',
	};

	return (
		<div
			className={`
				flex items-start gap-3 p-4 rounded-lg border shadow-lg max-w-md
				transition-all duration-300 ease-in-out
				${colorMap[toast.type]}
				${
					isExiting
						? 'opacity-0 translate-x-full'
						: 'opacity-100 translate-x-0'
				}
			`}
		>
			<div className="flex-shrink-0 mt-0.5">{iconMap[toast.type]}</div>
			<div className="flex-1 text-sm">{toast.message}</div>
			<button
				type="button"
				onClick={handleDismiss}
				className="flex-shrink-0 text-current opacity-70 hover:opacity-100 transition-opacity"
				aria-label="Dismiss"
			>
				<X className="w-4 h-4" />
			</button>
		</div>
	);
}

interface ToastContainerProps {
	toasts: Toast[];
	onDismiss: (id: string) => void;
	position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center';
}

export function ToastContainer({
	toasts,
	onDismiss,
	position = 'top-right',
}: ToastContainerProps) {
	const positionClasses = {
		'top-right': 'top-4 right-4',
		'top-left': 'top-4 left-4',
		'bottom-right': 'bottom-4 right-4',
		'bottom-left': 'bottom-4 left-4',
		'top-center': 'top-4 left-1/2 -translate-x-1/2',
	};

	return (
		<div
			className={`fixed z-50 flex flex-col gap-3 pointer-events-none ${positionClasses[position]}`}
			aria-live="polite"
			aria-atomic="true"
		>
			{toasts.map((toast) => (
				<div key={toast.id} className="pointer-events-auto">
					<ToastItem toast={toast} onDismiss={onDismiss} />
				</div>
			))}
		</div>
	);
}

/**
 * Hook for managing toasts
 */
export function useToast() {
	const [toasts, setToasts] = useState<Toast[]>([]);

	const addToast = (toast: Omit<Toast, 'id'>) => {
		const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
		setToasts((prev) => [...prev, { ...toast, id }]);
		return id;
	};

	const removeToast = (id: string) => {
		setToasts((prev) => prev.filter((t) => t.id !== id));
	};

	const success = (message: string, duration = 3000) => {
		return addToast({ type: 'success', message, duration });
	};

	const error = (message: string, duration = 5000) => {
		return addToast({ type: 'error', message, duration });
	};

	const warning = (message: string, duration = 4000) => {
		return addToast({ type: 'warning', message, duration });
	};

	const info = (message: string, duration = 3000) => {
		return addToast({ type: 'info', message, duration });
	};

	return {
		toasts,
		addToast,
		removeToast,
		success,
		error,
		warning,
		info,
	};
}
