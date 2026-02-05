import {
	BookOpen,
	Calendar,
	Grid,
	Home,
	LogOut,
	MapPin,
	UserCircle,
	Users,
	XCircle,
} from 'lucide-react';
import type React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Sidebar: React.FC = () => {
	const { logout } = useAuth();

	const navItems = [
		{ to: '/dashboard', icon: Home, label: 'Dashboard' },
		{ to: '/sessions', icon: Calendar, label: 'Sessions' },
		{ to: '/locations', icon: MapPin, label: 'Locations' },
		{ to: '/blocks', icon: Grid, label: 'Blocks' },
		{ to: '/caregivers', icon: UserCircle, label: 'Parents' },
		{ to: '/students', icon: BookOpen, label: 'Students' },
		{ to: '/staff', icon: Users, label: 'Staff' },
		{ to: '/staff/schedule', icon: Calendar, label: 'Staff Schedule' },
		{ to: '/exclusions', icon: XCircle, label: 'Exclusions' },
	];

	return (
		<div className="flex min-h-screen w-64 flex-col bg-gray-900 text-white">
			<div className="p-6">
				<h1 className="text-2xl font-bold">Admin Portal</h1>
			</div>

			<nav className="flex-1 px-4">
				{navItems.map((item) => (
					<NavLink
						key={item.to}
						to={item.to}
						className={({ isActive }) =>
							`mb-2 flex items-center gap-3 rounded-lg px-4 py-3 transition-colors ${
								isActive
									? 'bg-blue-600 text-white'
									: 'text-gray-300 hover:bg-gray-800 hover:text-white'
							}`
						}
					>
						<item.icon className="h-5 w-5" />
						<span>{item.label}</span>
					</NavLink>
				))}
			</nav>

			<div className="p-4">
				<button
					type="button"
					onClick={logout}
					className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-gray-300 transition-colors hover:bg-gray-800 hover:text-white"
				>
					<LogOut className="h-5 w-5" />
					<span>Logout</span>
				</button>
			</div>
		</div>
	);
};

export default Sidebar;
