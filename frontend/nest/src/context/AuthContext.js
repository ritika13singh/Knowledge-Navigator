import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

// Hardcoded backend port (must match backend/config.py BACKEND_PORT). Override with REACT_APP_API_URL if needed.
const DEFAULT_BACKEND_PORT = 8000;
const DEFAULT_API_BASE = `http://localhost:${DEFAULT_BACKEND_PORT}`;

// In development (npm start), use env or default to backend URL. In production build served from backend, use ''.
export function getApiBase() {
  const env = process.env.REACT_APP_API_URL;
  if (env) return env.replace(/\/$/, '');
  if (process.env.NODE_ENV === 'development') return DEFAULT_API_BASE;
  return '';
}
const apiBase = getApiBase();

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchUser = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/auth/me`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const loginUrl = `${apiBase}/api/auth/google`;

  const logout = useCallback(async () => {
    try {
      await fetch(`${apiBase}/api/auth/logout`, { method: 'POST', credentials: 'include' });
    } finally {
      setUser(null);
    }
  }, []);

  const value = {
    user,
    loading,
    error,
    loginUrl,
    logout,
    refetchUser: fetchUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
