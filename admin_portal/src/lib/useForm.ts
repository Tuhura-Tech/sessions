import type React from 'react';
import { useCallback, useState } from 'react';

export interface FormErrors {
	[key: string]: string | undefined;
}

export interface UseFormReturn<T> {
	values: T;
	errors: FormErrors;
	touched: { [key: string]: boolean };
	setValues: React.Dispatch<React.SetStateAction<T>>;
	setErrors: (errors: FormErrors | ((prev: FormErrors) => FormErrors)) => void;
	setTouched: (touched: { [key: string]: boolean }) => void;
	handleChange: (
		e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
	) => void;
	handleBlur: (
		e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
	) => void;
	resetForm: () => void;
	getFieldProps: (name: keyof T) => {
		name: string;
		value: T[keyof T] | '';
		onChange: (
			e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
		) => void;
		onBlur: (
			e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
		) => void;
	};
	getFieldError: (name: keyof T) => string | undefined;
	hasError: (name: keyof T) => boolean;
	isFieldTouched: (name: keyof T) => boolean;
}

export function useForm<T extends Record<string, unknown>>(
	initialValues: T,
	validate?: (values: T) => FormErrors,
): UseFormReturn<T> {
	const [values, setValues] = useState<T>(initialValues);
	const [errors, setErrors] = useState<FormErrors>({});
	const [touched, setTouched] = useState<{ [key: string]: boolean }>({});

	const validateField = useCallback(
		(fieldValues: T) => {
			if (validate) {
				const newErrors = validate(fieldValues);
				setErrors(newErrors);
				return newErrors;
			}
			return {};
		},
		[validate],
	);

	const handleChange = useCallback(
		(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
			const { name, value, type } = e.target;
			const newValue = type === 'checkbox' ? (e.target as HTMLInputElement).checked : value;

			setValues((prev) => {
				const updated = { ...prev, [name]: newValue };
				validateField(updated);
				return updated;
			});
		},
		[validateField],
	);

	const handleBlur = useCallback(
		(e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
			const { name } = e.target;
			setTouched((prev) => ({ ...prev, [name]: true }));
		},
		[],
	);

	const resetForm = useCallback(() => {
		setValues(initialValues);
		setErrors({});
		setTouched({});
	}, [initialValues]);

	const getFieldProps = useCallback(
		(name: keyof T) => ({
			name: String(name),
			value: (values[name] ?? '') as T[keyof T] | '',
			onChange: handleChange,
			onBlur: handleBlur,
		}),
		[values, handleChange, handleBlur],
	);

	const getFieldError = useCallback((name: keyof T) => errors[String(name)], [errors]);

	const hasError = useCallback((name: keyof T) => Boolean(errors[String(name)]), [errors]);

	const isFieldTouched = useCallback((name: keyof T) => touched[String(name)] ?? false, [touched]);

	return {
		values,
		errors,
		touched,
		setValues,
		setErrors,
		setTouched,
		handleChange,
		handleBlur,
		resetForm,
		getFieldProps,
		getFieldError,
		hasError,
		isFieldTouched,
	};
}
