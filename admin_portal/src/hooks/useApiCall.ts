import { useCallback, useState } from 'react';
import { useToast } from '../components/Toast';
import { extractErrorMessage } from '../lib/errorHandling';

/**
 * Hook for handling API calls with loading, error states, and toast notifications
 */
export function useApiCall<T = void>() {
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const toast = useToast();

	const execute = useCallback(
		async (
			apiCall: () => Promise<T>,
			options?: {
				successMessage?: string;
				errorMessage?: string;
				showSuccessToast?: boolean;
				showErrorToast?: boolean;
			},
		): Promise<T | null> => {
			const {
				successMessage,
				errorMessage,
				showSuccessToast = true,
				showErrorToast = true,
			} = options || {};

			setIsLoading(true);
			setError(null);

			try {
				const result = await apiCall();

				if (successMessage && showSuccessToast) {
					toast.success(successMessage);
				}

				return result;
			} catch (err) {
				const message = extractErrorMessage(err);
				setError(errorMessage || message);

				if (showErrorToast) {
					toast.error(errorMessage || message);
				}

				return null;
			} finally {
				setIsLoading(false);
			}
		},
		[toast],
	);

	const reset = useCallback(() => {
		setIsLoading(false);
		setError(null);
	}, []);

	return {
		isLoading,
		error,
		execute,
		reset,
		toast,
	};
}

/**
 * Hook for handling form submissions with validation
 */
export function useFormSubmit<T = void>() {
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [errors, setErrors] = useState<Record<string, string>>({});
	const toast = useToast();

	const submit = useCallback(
		async (
			submitFn: () => Promise<T>,
			options?: {
				successMessage?: string;
				onSuccess?: (result: T) => void;
				onError?: (error: unknown) => void;
			},
		): Promise<boolean> => {
			setIsSubmitting(true);
			setErrors({});

			try {
				const result = await submitFn();

				if (options?.successMessage) {
					toast.success(options.successMessage);
				}

				if (options?.onSuccess) {
					options.onSuccess(result);
				}

				return true;
			} catch (err) {
				const message = extractErrorMessage(err);
				toast.error(message);

				setErrors({ _form: message });

				if (options?.onError) {
					options.onError(err);
				}

				return false;
			} finally {
				setIsSubmitting(false);
			}
		},
		[toast],
	);

	const setFieldError = useCallback((field: string, message: string) => {
		setErrors((prev) => ({ ...prev, [field]: message }));
	}, []);

	const clearErrors = useCallback(() => {
		setErrors({});
	}, []);

	return {
		isSubmitting,
		errors,
		submit,
		setFieldError,
		clearErrors,
		toast,
	};
}
