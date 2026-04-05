import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import apiService from '../services/api';

interface User {
  id: number;
  username: string;
  email: string;
  role: 'citizen' | 'officer' | 'admin';
  department?: string;
  designation?: string;
  location?: string;
  preferred_language?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  checkAuth: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  // Check authentication on mount
  useEffect(() => {
    const checkAuthentication = async () => {
      const storedToken = localStorage.getItem('token');
      const storedUser = localStorage.getItem('user');

      if (storedToken && storedUser) {
        try {
          await apiService.checkAuth();
          setToken(storedToken);
          setUser(JSON.parse(storedUser));
        } catch {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }

      setIsLoading(false);
    };

    checkAuthentication();
  }, []);

  // Token refresh: refresh when < 1 hour remaining
  useEffect(() => {
    if (!token) return;

    const refreshInterval = setInterval(async () => {
      try {
        const data = await apiService.refreshToken();
        setToken(data.access_token);
        localStorage.setItem('token', data.access_token);
      } catch {
        // Will be caught by 401 interceptor
      }
    }, 60 * 60 * 1000);

    return () => clearInterval(refreshInterval);
  }, [token]);

  // Inactivity timeout: 30 min auto-logout
  useEffect(() => {
    if (!token) return;

    let timeout: ReturnType<typeof setTimeout>;

    const resetTimer = () => {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        performLogout();
      }, 30 * 60 * 1000);
    };

    const events = ['mousedown', 'keypress', 'scroll', 'touchstart'];
    events.forEach((event) => window.addEventListener(event, resetTimer));
    resetTimer();

    return () => {
      clearTimeout(timeout);
      events.forEach((event) => window.removeEventListener(event, resetTimer));
    };
  }, [token]);

  const login = useCallback((newToken: string, newUser: User) => {
    setToken(newToken);
    setUser(newUser);
    localStorage.setItem('token', newToken);
    localStorage.setItem('user', JSON.stringify(newUser));

    // Use navigate for HashRouter compatibility (NOT window.location.href)
    const destination = newUser.role === 'officer' ? '/department' : '/dashboard';
    navigate(destination);
  }, [navigate]);

  const performLogout = useCallback(async () => {
    try {
      await apiService.logout();
    } catch {
      // Clear local state regardless
    } finally {
      setToken(null);
      setUser(null);
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      navigate('/login');
    }
  }, [navigate]);

  const logout = useCallback(async () => {
    await performLogout();
  }, [performLogout]);

  const checkAuth = useCallback(async (): Promise<boolean> => {
    if (!token) return false;
    try {
      await apiService.checkAuth();
      return true;
    } catch {
      return false;
    }
  }, [token]);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    logout,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Protected Route Component
export const ProtectedRoute: React.FC<{ children: ReactNode; allowedRoles?: string[] }> = ({
  children,
  allowedRoles,
}) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        navigate('/login');
      } else if (allowedRoles && user && !allowedRoles.includes(user.role)) {
        navigate('/dashboard');
      }
    }
  }, [isAuthenticated, isLoading, user, allowedRoles, navigate]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;
  if (allowedRoles && user && !allowedRoles.includes(user.role)) return null;

  return <>{children}</>;
};
