import type React from 'react';
import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { adminApi } from '../services/api';

interface AuthContextType {
	isAuthenticated: boolean;
	isLoading: boolean;
	checkAuth: () => Promise<void>;
	logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
	const [isAuthenticated, setIsAuthenticated] = useState(false);
	const [isLoading, setIsLoading] = useState(true);

	const checkAuth = useCallback(async () => {
		try {
			const result = await adminApi.checkSession();
			setIsAuthenticated(result.hasSession === true);
		} catch (_error) {
			setIsAuthenticated(false);
		} finally {
			setIsLoading(false);
		}
	}, []);

	const logout = useCallback(async () => {
		try {
			await adminApi.logout();
			setIsAuthenticated(false);
			window.location.href = '/login';
		} catch (error) {
			console.error('Logout failed:', error);
		}
	}, []);

	useEffect(() => {
		checkAuth();
	}, [checkAuth]);

	return (
		<AuthContext.Provider value={{ isAuthenticated, isLoading, checkAuth, logout }}>
			{children}
		</AuthContext.Provider>
	);
};

export const useAuth = () => {
	const context = useContext(AuthContext);
	if (context === undefined) {
		throw new Error('useAuth must be used within an AuthProvider');
	}
	return context;
};
