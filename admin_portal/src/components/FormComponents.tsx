import React from 'react';

interface FormInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
	label?: string;
	required?: boolean;
	error?: string;
}

export const FormInput = React.forwardRef<HTMLInputElement, FormInputProps>(
	({ label, required, error, className, id, ...props }, ref) => {
		const inputId = id || `input-${label?.replace(/\s+/g, '-').toLowerCase()}`;
		return (
			<div className="flex flex-col gap-1">
				{label && (
					<label htmlFor={inputId} className="block text-sm font-medium text-gray-700">
						{label}
						{required && <span className="text-red-500"> *</span>}
					</label>
				)}
				<input
					ref={ref}
					id={inputId}
					className={`rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500 ${
						error ? 'border-red-500' : ''
					} ${className || ''}`}
					{...props}
				/>
				{error && <span className="text-sm text-red-600">{error}</span>}
			</div>
		);
	},
);

FormInput.displayName = 'FormInput';

interface FormSelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
	label?: string;
	required?: boolean;
	error?: string;
	options?: { value: string; label: string }[];
}

export const FormSelect = React.forwardRef<HTMLSelectElement, FormSelectProps>(
	({ label, required, error, options, className, id, children, ...props }, ref) => {
		const selectId = id || `select-${label?.replace(/\s+/g, '-').toLowerCase()}`;
		return (
			<div className="flex flex-col gap-1">
				{label && (
					<label htmlFor={selectId} className="block text-sm font-medium text-gray-700">
						{label}
						{required && <span className="text-red-500"> *</span>}
					</label>
				)}
				<select
					ref={ref}
					id={selectId}
					className={`rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500 ${
						error ? 'border-red-500' : ''
					} ${className || ''}`}
					{...props}
				>
					{options?.map((opt) => (
						<option key={opt.value} value={opt.value}>
							{opt.label}
						</option>
					))}
					{children}
				</select>
				{error && <span className="text-sm text-red-600">{error}</span>}
			</div>
		);
	},
);

FormSelect.displayName = 'FormSelect';

interface FormTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
	label?: string;
	required?: boolean;
	error?: string;
}

export const FormTextarea = React.forwardRef<HTMLTextAreaElement, FormTextareaProps>(
	({ label, required, error, className, id, ...props }, ref) => {
		const textareaId = id || `textarea-${label?.replace(/\s+/g, '-').toLowerCase()}`;
		return (
			<div className="flex flex-col gap-1">
				{label && (
					<label htmlFor={textareaId} className="block text-sm font-medium text-gray-700">
						{label}
						{required && <span className="text-red-500"> *</span>}
					</label>
				)}
				<textarea
					ref={ref}
					id={textareaId}
					className={`rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-blue-500 ${
						error ? 'border-red-500' : ''
					} ${className || ''}`}
					{...props}
				/>
				{error && <span className="text-sm text-red-600">{error}</span>}
			</div>
		);
	},
);

FormTextarea.displayName = 'FormTextarea';

interface FormCheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
	label?: string;
}

export const FormCheckbox = React.forwardRef<HTMLInputElement, FormCheckboxProps>(
	({ label, className, ...props }, ref) => (
		<label className="flex cursor-pointer items-center gap-2">
			<input
				type="checkbox"
				ref={ref}
				className={`h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 ${className || ''}`}
				{...props}
			/>
			{label && <span className="text-sm text-gray-900">{label}</span>}
		</label>
	),
);

FormCheckbox.displayName = 'FormCheckbox';
