import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import type { ReactNode } from 'react';
import { authStorage } from '../services/authStorage';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

interface User {
  id: string;
  email: string;
  name?: string;
  [key: string]: unknown;
}

interface Session {
  access_token: string;
  refresh_token: string;
  expires_at?: number;
  expires_in?: number;
}

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  rememberMe: boolean;
  signup: (email: string, password: string, name?: string) => Promise<{ success: boolean; email_confirmation_required?: boolean; message?: string }>;
  login: (email: string, password: string, shouldRememberMe?: boolean) => Promise<{ user: User; session: Session }>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  updateRememberMe: (value: boolean) => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState<string | null>(authStorage.getTokens().accessToken);
  const [rememberMe, setRememberMe] = useState(authStorage.getRememberMe());

  const isRefreshing = useRef(false);
  const stopAutoRefreshRef = useRef<(() => void) | null>(null);

  // Refresh token function
  const refreshToken = useCallback(async (): Promise<boolean> => {
    if (isRefreshing.current) return false;

    const { refreshToken: storedRefreshToken } = authStorage.getTokens();
    if (!storedRefreshToken) {
      console.log('[Auth] No refresh token available');
      return false;
    }

    isRefreshing.current = true;

    try {
      console.log('[Auth] Refreshing token...');
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: storedRefreshToken }),
      });

      if (response.ok) {
        const data = await response.json();
        authStorage.updateTokens(data.session);
        setToken(data.session.access_token);
        console.log('[Auth] Token refreshed successfully');
        return true;
      } else {
        console.log('[Auth] Token refresh failed, logging out');
        await logout();
        return false;
      }
    } catch (error) {
      console.error('[Auth] Token refresh error:', error);
      return false;
    } finally {
      isRefreshing.current = false;
    }
  }, []);

  // Verify token and load user data
  const verifyToken = useCallback(async (): Promise<void> => {
    const { accessToken } = authStorage.getTokens();

    if (!accessToken) {
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/verify`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
        setToken(accessToken);
        authStorage.setUser(data.user);
      } else if (response.status === 401) {
        console.log('[Auth] Token invalid, attempting refresh...');
        const refreshed = await refreshToken();
        if (refreshed) {
          await verifyToken();
          return;
        }
        await logout();
      } else {
        await logout();
      }
    } catch (error) {
      console.error('[Auth] Token verification failed:', error);
      await logout();
    } finally {
      setLoading(false);
    }
  }, [refreshToken]);

  // Logout function
  const logout = useCallback(async (): Promise<void> => {
    const { accessToken } = authStorage.getTokens();

    try {
      if (accessToken) {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      if (stopAutoRefreshRef.current) {
        stopAutoRefreshRef.current();
        stopAutoRefreshRef.current = null;
      }

      authStorage.clear();
      setToken(null);
      setUser(null);
    }
  }, []);

  // Load user on mount
  useEffect(() => {
    const initAuth = async () => {
      const { accessToken, refreshToken: storedRefreshToken } = authStorage.getTokens();

      if (accessToken) {
        if (authStorage.isTokenExpired()) {
          console.log('[Auth] Token expired, attempting refresh...');
          if (storedRefreshToken) {
            const refreshed = await refreshToken();
            if (!refreshed) {
              setLoading(false);
              return;
            }
          } else {
            authStorage.clear();
            setLoading(false);
            return;
          }
        }

        await verifyToken();
      } else {
        setLoading(false);
      }
    };

    initAuth();

    return () => {
      if (stopAutoRefreshRef.current) {
        stopAutoRefreshRef.current();
      }
    };
  }, [refreshToken, verifyToken]);

  // Start auto-refresh when we have a valid token
  useEffect(() => {
    if (token && user) {
      if (stopAutoRefreshRef.current) {
        stopAutoRefreshRef.current();
      }

      // Wrap refreshToken to ignore return value
      const wrappedRefresh = async () => { await refreshToken(); };
      stopAutoRefreshRef.current = authStorage.startAutoRefresh(wrappedRefresh, 30000);
    }

    return () => {
      if (stopAutoRefreshRef.current) {
        stopAutoRefreshRef.current();
      }
    };
  }, [token, user, refreshToken]);

  // Sign up new user
  const signup = async (email: string, password: string, name?: string) => {
    const response = await fetch(`${API_BASE_URL}/auth/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password, name }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Signup failed');
    }

    if (data.email_confirmation_required) {
      return data;
    }

    if (data.session) {
      authStorage.setSession(data.session, rememberMe, data.user);
      setToken(data.session.access_token);
      setUser(data.user);
    }

    return data;
  };

  // Login existing user
  const login = async (email: string, password: string, shouldRememberMe = rememberMe) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Login failed');
    }

    authStorage.setSession(data.session, shouldRememberMe, data.user);
    setRememberMe(shouldRememberMe);
    setToken(data.session.access_token);
    setUser(data.user);

    return data;
  };

  // Update remember me preference
  const updateRememberMe = (value: boolean) => {
    setRememberMe(value);
    authStorage.setRememberMe(value);
  };

  const value: AuthContextValue = {
    user,
    token,
    loading,
    rememberMe,
    signup,
    login,
    logout,
    refreshToken,
    updateRememberMe,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
