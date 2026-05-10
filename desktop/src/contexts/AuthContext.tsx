import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  ReactNode,
} from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
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

// ─── Constants ────────────────────────────────────────────────
const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const INACTIVITY_WARNING_MS = 28 * 60 * 1000; // show warning at 28min (2min before logout)
const REFRESH_BUFFER_MS = 5 * 60 * 1000; // refresh 5min before exp
const REFRESH_FALLBACK_MS = 50 * 60 * 1000; // if no exp claim, fall back to 50min

// ─── JWT decode (no external dep) ─────────────────────────────
function decodeJwtExpMs(jwt: string): number | null {
  try {
    const parts = jwt.split('.');
    if (parts.length !== 3) return null;
    // base64url -> base64
    const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = b64 + '=='.slice(0, (4 - (b64.length % 4)) % 4);
    const json = atob(padded);
    const payload = JSON.parse(json);
    if (typeof payload.exp === 'number') {
      return payload.exp * 1000;
    }
    return null;
  } catch {
    return null;
  }
}

// ─── Inactivity warning modal (inline so AnimatedModal change is independent) ──
const SessionWarningModal: React.FC<{
  open: boolean;
  onStay: () => void;
  onLogout: () => void;
}> = ({ open, onStay, onLogout }) => {
  if (!open) return null;
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="session-warning-title"
      className="fixed inset-0 z-[10000] flex items-center justify-center p-4"
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div className="relative w-full max-w-sm rounded-2xl bg-[#0A1224] border border-white/[0.08] p-6 shadow-2xl">
        <h3
          id="session-warning-title"
          className="text-lg font-semibold text-kora-100 mb-2"
        >
          Session expiring soon
        </h3>
        <p className="text-sm text-slate-400/80 mb-5">
          You will be signed out in 2 minutes due to inactivity.
        </p>
        <div className="flex gap-3">
          <button
            onClick={onLogout}
            className="flex-1 py-2.5 rounded-xl text-sm font-medium bg-white/[0.04] border border-white/[0.08] text-slate-300 hover:bg-white/[0.08] transition-colors"
          >
            Sign out
          </button>
          <button
            onClick={onStay}
            autoFocus
            className="flex-1 py-2.5 rounded-xl text-sm font-semibold bg-[#0D92F4] text-white hover:bg-[#0B7DD4] transition-colors"
          >
            Stay signed in
          </button>
        </div>
      </div>
    </div>
  );
};

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showWarning, setShowWarning] = useState(false);
  const navigate = useNavigate();

  // Refs that stay in sync without retriggering effects
  const logoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const warningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ─── Check authentication on mount ───
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

  // ─── Token refresh: schedule based on JWT exp claim ───
  useEffect(() => {
    if (!token) return;

    const scheduleRefresh = (currentToken: string) => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);

      const expMs = decodeJwtExpMs(currentToken);
      let delay: number;
      if (expMs) {
        delay = expMs - Date.now() - REFRESH_BUFFER_MS;
        if (delay < 0) delay = 0; // refresh immediately if already past buffer
      } else {
        delay = REFRESH_FALLBACK_MS;
      }

      refreshTimerRef.current = setTimeout(async () => {
        try {
          const data = await apiService.refreshToken();
          setToken(data.access_token);
          localStorage.setItem('token', data.access_token);
          // setToken triggers this effect to re-run and schedule the next refresh
        } catch {
          // 401 path will be handled by the response interceptor
        }
      }, delay);
    };

    scheduleRefresh(token);

    return () => {
      if (refreshTimerRef.current) {
        clearTimeout(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
    };
  }, [token]);

  // ─── Logout (declared before inactivity effect that uses it) ───
  const performLogout = useCallback(async () => {
    try {
      await apiService.logout();
    } catch {
      toast.error('Failed to log out cleanly on the server. Local session cleared.');
    } finally {
      setToken(null);
      setUser(null);
      setShowWarning(false);
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      navigate('/login');
    }
  }, [navigate]);

  // ─── Inactivity timeout: 30 min auto-logout + 2 min warning ───
  const showWarningRef = useRef(showWarning);
  useEffect(() => {
    showWarningRef.current = showWarning;
  }, [showWarning]);

  useEffect(() => {
    if (!token) return;

    const resetTimers = () => {
      if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
      setShowWarning(false);

      warningTimerRef.current = setTimeout(() => {
        setShowWarning(true);
      }, INACTIVITY_WARNING_MS);

      logoutTimerRef.current = setTimeout(() => {
        performLogout();
      }, INACTIVITY_TIMEOUT_MS);
    };

    const events: (keyof WindowEventMap)[] = [
      'mousedown',
      'mousemove',
      'keypress',
      'touchstart',
      'scroll',
      'wheel',
    ];
    const handler = () => {
      // Only reset on activity if the warning is NOT being shown.
      // The warning requires an explicit user choice.
      if (!showWarningRef.current) resetTimers();
    };
    events.forEach((event) => window.addEventListener(event, handler, { passive: true }));
    resetTimers();

    return () => {
      if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
      events.forEach((event) => window.removeEventListener(event, handler));
    };
  }, [token, performLogout]);

  const login = useCallback(
    (newToken: string, newUser: User) => {
      setToken(newToken);
      setUser(newUser);
      localStorage.setItem('token', newToken);
      localStorage.setItem('user', JSON.stringify(newUser));

      const destination = newUser.role === 'officer' ? '/department' : '/dashboard';
      navigate(destination);
    },
    [navigate]
  );

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

  // ─── Stay-signed-in handler ───
  const handleStaySignedIn = useCallback(() => {
    setShowWarning(false);
    // Reset by re-triggering the inactivity effect via a no-op activity event
    if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    warningTimerRef.current = setTimeout(() => {
      setShowWarning(true);
    }, INACTIVITY_WARNING_MS);
    logoutTimerRef.current = setTimeout(() => {
      performLogout();
    }, INACTIVITY_TIMEOUT_MS);
  }, [performLogout]);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    isLoading,
    login,
    logout,
    checkAuth,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
      <SessionWarningModal
        open={showWarning && !!token}
        onStay={handleStaySignedIn}
        onLogout={performLogout}
      />
    </AuthContext.Provider>
  );
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
