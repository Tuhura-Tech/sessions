import { AlertCircle } from 'lucide-react';
import type React from 'react';

interface FormFieldProps {
	label: string;
	name: string;
	value: string | number | boolean;
	onChange: (
		e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>,
	) => void;
	onBlur: (e: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void;
	error?: string;
	touched?: boolean;
	required?: boolean;
	disabled?: boolean;
	placeholder?: string;
	type?: 'text' | 'email' | 'number' | 'tel' | 'date' | 'time';
	min?: number;
	max?: number;
	step?: number;
	className?: string;
}

export function FormField({
	label,
	name,
	value,
	onChange,
	onBlur,
	error,
	touched,
	required = false,
	disabled = false,
	placeholder,
	type = 'text',
	min,
	max,
	step,
	className = '',
}: FormFieldProps) {
	const showError = touched && error;

	return (
		<div className="mb-4">
			<label htmlFor={name} className="mb-1 block text-sm font-medium text-gray-700">
				{label}
				{required && <span className="ml-1 text-red-500">*</span>}
			</label>

			<input
				id={name}
				name={name}
				type={type}
				value={typeof value === 'boolean' ? String(value) : (value ?? '')}
				onChange={onChange}
				onBlur={onBlur}
				disabled={disabled}
				placeholder={placeholder}
				min={min}
				max={max}
				step={step}
				aria-invalid={showError ? 'true' : 'false'}
				aria-describedby={showError ? `${name}-error` : undefined}
				className={`w-full rounded-md border px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500 focus:outline-none disabled:bg-gray-100 disabled:text-gray-500 ${
					showError ? 'border-red-500 bg-red-50' : 'border-gray-300 bg-white'
				} transition-colors ${className}`}
			/>

			{showError && (
				<div
					id={`${name}-error`}
					className="mt-1 flex items-center text-sm text-red-600"
					role="alert"
				>
					<AlertCircle className="mr-1 h-4 w-4 flex-shrink-0" />
					{error}
				</div>
			)}
		</div>
	);
}

interface FormSelectProps {
	label: string;
	name: string;
	value: string | number;
	onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
	onBlur: (e: React.FocusEvent<HTMLSelectElement>) => void;
	options: { value: string | number; label: string }[];
	error?: string;
	touched?: boolean;
	required?: boolean;
	disabled?: boolean;
	placeholder?: string;
	className?: string;
}

export function FormSelect({
	label,
	name,
	value,
	onChange,
	onBlur,
	options,
	error,
	touched,
	required = false,
	disabled = false,
	placeholder,
	className = '',
}: FormSelectProps) {
	const showError = touched && error;

	return (
		<div className="mb-4">
			<label htmlFor={name} className="mb-1 block text-sm font-medium text-gray-700">
				{label}
				{required && <span className="ml-1 text-red-500">*</span>}
			</label>

			<select
				id={name}
				name={name}
				value={value ?? ''}
				onChange={onChange}
				onBlur={onBlur}
				disabled={disabled}
				aria-invalid={showError ? 'true' : 'false'}
				aria-describedby={showError ? `${name}-error` : undefined}
				className={`w-full rounded-md border px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500 focus:outline-none disabled:bg-gray-100 disabled:text-gray-500 ${
					showError ? 'border-red-500 bg-red-50' : 'border-gray-300 bg-white'
				} transition-colors ${className}`}
			>
				{placeholder && <option value="">{placeholder}</option>}
				{options.map((option) => (
					<option key={option.value} value={option.value}>
						{option.label}
					</option>
				))}
			</select>

			{showError && (
				<div
					id={`${name}-error`}
					className="mt-1 flex items-center text-sm text-red-600"
					role="alert"
				>
					<AlertCircle className="mr-1 h-4 w-4 flex-shrink-0" />
					{error}
				</div>
			)}
		</div>
	);
}

interface FormTextAreaProps {
	label: string;
	name: string;
	value: string;
	onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
	onBlur: (e: React.FocusEvent<HTMLTextAreaElement>) => void;
	error?: string;
	touched?: boolean;
	required?: boolean;
	disabled?: boolean;
	placeholder?: string;
	rows?: number;
	className?: string;
}

export function FormTextArea({
	label,
	name,
	value,
	onChange,
	onBlur,
	error,
	touched,
	required = false,
	disabled = false,
	placeholder,
	rows = 4,
	className = '',
}: FormTextAreaProps) {
	const showError = touched && error;

	return (
		<div className="mb-4">
			<label htmlFor={name} className="mb-1 block text-sm font-medium text-gray-700">
				{label}
				{required && <span className="ml-1 text-red-500">*</span>}
			</label>

			<textarea
				id={name}
				name={name}
				value={value ?? ''}
				onChange={onChange}
				onBlur={onBlur}
				disabled={disabled}
				placeholder={placeholder}
				rows={rows}
				aria-invalid={showError ? 'true' : 'false'}
				aria-describedby={showError ? `${name}-error` : undefined}
				className={`resize-vertical w-full rounded-md border px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500 focus:outline-none disabled:bg-gray-100 disabled:text-gray-500 ${
					showError ? 'border-red-500 bg-red-50' : 'border-gray-300 bg-white'
				} transition-colors ${className}`}
			/>

			{showError && (
				<div
					id={`${name}-error`}
					className="mt-1 flex items-center text-sm text-red-600"
					role="alert"
				>
					<AlertCircle className="mr-1 h-4 w-4 flex-shrink-0" />
					{error}
				</div>
			)}
		</div>
	);
}
