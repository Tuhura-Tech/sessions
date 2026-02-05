import type React from 'react';

interface LayoutProps {
	children: React.ReactNode;
	title?: string;
	actions?: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children, title, actions }) => {
	return (
		<div className="min-h-screen bg-gray-100">
			{title && (
				<header className="bg-white shadow">
					<div className="max-w-screen-1xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
						<div className="flex items-center justify-between">
							<h1 className="text-3xl font-bold text-gray-900">{title}</h1>
							{actions && <div>{actions}</div>}
						</div>
					</div>
				</header>
			)}
			<main className="max-w-screen-1xl mx-auto px-4 py-8 sm:px-6 lg:px-8">{children}</main>
		</div>
	);
};

export default Layout;
