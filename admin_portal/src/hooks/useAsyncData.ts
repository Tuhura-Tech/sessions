import { useCallback, useEffect, useState } from 'react';

export interface AsyncDataState<T> {
	data: T | null;
	loading: boolean;
	error: string | null;
}

export interface UseAsyncDataReturn<T> extends AsyncDataState<T> {
	refetch: () => Promise<void>;
	setData: (data: T | null) => void;
}

/**
 * Custom hook to standardize async data fetching patterns
 *
 * @param fetchFn - Async function that fetches data
 * @param dependencies - Array of dependencies that trigger refetch
 * @returns Object with data, loading, error, and refetch function
 *
 * @example
 * const { data, loading, error, refetch } = useAsyncData(
 *   () => adminApi.getSession(id),
 *   [id]
 * );
 */
export function useAsyncData<T>(
	fetchFn: () => Promise<T>,
	dependencies: React.DependencyList = [],
): UseAsyncDataReturn<T> {
	const [state, setState] = useState<AsyncDataState<T>>({
		data: null,
		loading: true,
		error: null,
	});

	const fetchData = useCallback(async () => {
		setState((prev) => ({ ...prev, loading: true, error: null }));
		try {
			const result = await fetchFn();
			setState({ data: result, loading: false, error: null });
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'An error occurred';
			setState({ data: null, loading: false, error: errorMessage });
			console.error('useAsyncData error:', err);
		}
	}, [fetchFn]);

	useEffect(() => {
		fetchData();
	}, dependencies);

	const setData = useCallback((data: T | null) => {
		setState((prev) => ({ ...prev, data }));
	}, []);

	return {
		...state,
		refetch: fetchData,
		setData,
	};
}
