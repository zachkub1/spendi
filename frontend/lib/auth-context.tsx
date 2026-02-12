'use client';

/**
 * AuthContext provides authentication state and methods throughout the app.
 * Manages user session, token validation, and auth lifecycle.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import type { User } from '@shared/types/auth';
import { getToken, setToken as saveToken, clearToken, isTokenExpired } from './auth-storage';
import { apiClient } from './api-client';

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: React.ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const router = useRouter();

  /**
   * Fetch user info from backend using current token.
   */
  const fetchUser = useCallback(async (authToken: string) => {
    try {
      const userData = await apiClient.get<User>('/auth/me');
      setUser(userData);
      setToken(authToken);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      clearToken();
      setUser(null);
      setToken(null);
    }
  }, []);

  /**
   * Initialize auth state from localStorage on mount.
   */
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = getToken();

      if (!storedToken) {
        setLoading(false);
        return;
      }

      // Check if token is expired
      if (isTokenExpired(storedToken)) {
        clearToken();
        setLoading(false);
        return;
      }

      // Token exists and is valid, fetch user info
      await fetchUser(storedToken);
      setLoading(false);
    };

    initAuth();
  }, [fetchUser]);

  /**
   * Login with a new token.
   * Stores token and fetches user info.
   */
  const login = async (newToken: string) => {
    saveToken(newToken);
    await fetchUser(newToken);
  };

  /**
   * Logout: clear token and user state, redirect to login.
   */
  const logout = () => {
    clearToken();
    setUser(null);
    setToken(null);
    router.push('/login');
  };

  const value: AuthContextType = {
    user,
    token,
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to access auth context.
 * Must be used within AuthProvider.
 */
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
