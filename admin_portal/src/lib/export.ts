/**
 * Data export utilities for CSV and other formats
 */

export const exportToCSV = (data: Record<string, unknown>[], filename: string) => {
	if (data.length === 0) {
		alert('No data to export');
		return;
	}

	// Get headers from first object
	const headers = Object.keys(data[0]);

	// Create CSV content
	let csv = `${headers.join(',')}\n`;
	data.forEach((row) => {
		const values = headers.map((header) => {
			const value = row[header];
			// Escape quotes and wrap in quotes if contains comma or newline
			if (typeof value === 'string' && (value.includes(',') || value.includes('\n'))) {
				return `"${value.replace(/"/g, '""')}"`;
			}
			return value || '';
		});
		csv += `${values.join(',')}\n`;
	});

	// Create blob and download
	const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
	const link = document.createElement('a');
	const url = URL.createObjectURL(blob);

	link.setAttribute('href', url);
	link.setAttribute('download', filename);
	link.style.visibility = 'hidden';

	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
};

export const exportToJSON = (data: Record<string, unknown>[], filename: string) => {
	const json = JSON.stringify(data, null, 2);
	const blob = new Blob([json], { type: 'application/json;charset=utf-8;' });
	const link = document.createElement('a');
	const url = URL.createObjectURL(blob);

	link.setAttribute('href', url);
	link.setAttribute('download', filename);
	link.style.visibility = 'hidden';

	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
};

export const downloadBlob = (blob: Blob, filename: string) => {
	const url = URL.createObjectURL(blob);
	const link = document.createElement('a');

	link.setAttribute('href', url);
	link.setAttribute('download', filename);
	link.style.visibility = 'hidden';

	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);

	URL.revokeObjectURL(url);
};
