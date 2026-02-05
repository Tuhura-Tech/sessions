import { AlertCircle } from 'lucide-react';
import React, { type ReactNode } from 'react';

interface ErrorBoundaryProps {
	children: ReactNode;
}

interface ErrorBoundaryState {
	hasError: boolean;
	error: Error | null;
	errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
	constructor(props: ErrorBoundaryProps) {
		super(props);
		this.state = {
			hasError: false,
			error: null,
			errorInfo: null,
		};
	}

	static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
		return { hasError: true, error };
	}

	componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
		console.error('Error boundary caught an error:', error, errorInfo);
		this.setState({
			error,
			errorInfo,
		});
	}

	render() {
		if (this.state.hasError) {
			return (
				<div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
					<div className="w-full max-w-md rounded-lg bg-white p-8 shadow-lg">
						<div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
							<AlertCircle className="h-6 w-6 text-red-600" />
						</div>

						<h1 className="mt-4 text-center text-xl font-semibold text-gray-900">
							Something went wrong
						</h1>

						<p className="mt-2 text-center text-sm text-gray-600">
							An unexpected error occurred. Please try refreshing the page or contact support if the
							problem persists.
						</p>

						{this.state.error && (
							<div className="mt-4 max-h-32 overflow-auto rounded bg-gray-100 p-4 font-mono text-xs text-gray-700">
								<p className="mb-1 font-semibold">Error:</p>
								<p>{this.state.error.toString()}</p>
								{this.state.errorInfo && (
									<>
										<p className="mt-2 mb-1 font-semibold">Stack trace:</p>
										<pre className="text-xs whitespace-pre-wrap">
											{this.state.errorInfo.componentStack}
										</pre>
									</>
								)}
							</div>
						)}

						<button
							type="button"
							onClick={() => window.location.reload()}
							className="mt-4 w-full rounded bg-blue-600 px-4 py-2 font-medium text-white transition-colors hover:bg-blue-700"
						>
							Refresh Page
						</button>

						<button
							type="button"
							onClick={() => window.history.back()}
							className="mt-2 w-full rounded bg-gray-200 px-4 py-2 font-medium text-gray-900 transition-colors hover:bg-gray-300"
						>
							Go Back
						</button>
					</div>
				</div>
			);
		}

		return this.props.children;
	}
}
