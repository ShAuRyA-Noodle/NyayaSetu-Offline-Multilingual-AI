import React, { Suspense } from 'react';
import { Routes, Route, Navigate, useLocation, Link } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { ProtectedRoute } from './contexts/AuthContext';
import Layout from './components/layout/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Schemes from './pages/Schemes';
import Chat from './pages/Chat';
import Grievances from './pages/Grievances';
import NoticeDrafter from './pages/NoticeDrafter';
import Settings from './pages/Settings';
import DepartmentDashboard from './pages/DepartmentDashboard';
import AdminDashboard from './pages/AdminDashboard';
import NyayaVaani from './pages/NyayaVaani';
import ThemedSpinner from './components/ui/ThemedSpinner';

// TODO: The following pages are being added by another agent. Until they exist
// in `desktop/src/pages/`, build will fail at the lazy-import resolution step.
// Expected files:
//   - desktop/src/pages/ForgotPassword.tsx
//   - desktop/src/pages/ResetPassword.tsx
//   - desktop/src/pages/Privacy.tsx
//   - desktop/src/pages/Terms.tsx
//   - desktop/src/pages/PublicSchemes.tsx
//   - desktop/src/pages/NotFound.tsx (optional — fallback inline)
const ForgotPassword = React.lazy(() => import('./pages/ForgotPassword'));
const ResetPassword = React.lazy(() => import('./pages/ResetPassword'));
const Privacy = React.lazy(() => import('./pages/Privacy'));
const Terms = React.lazy(() => import('./pages/Terms'));
const PublicSchemes = React.lazy(() => import('./pages/PublicSchemes'));

interface AppRoutesProps {
  isOnline: boolean;
}

const SuspenseFallback: React.FC = () => (
  <div className="min-h-screen flex items-center justify-center bg-[#060B18]">
    <ThemedSpinner size="md" />
  </div>
);

// Inline 404 — does NOT render the protected layout/sidebar
const NotFound: React.FC = () => (
  <div className="min-h-screen flex items-center justify-center bg-[#060B18] text-kora-100 px-6">
    <div className="text-center max-w-md">
      <p className="text-xs uppercase tracking-[0.3em] text-mitti-500/60 mb-4">
        404
      </p>
      <h1 className="text-3xl md:text-4xl font-display font-bold mb-3">
        Page not found
      </h1>
      <p className="text-sm text-slate-400/60 mb-8">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        to="/dashboard"
        className="inline-flex items-center px-5 py-2.5 rounded-xl bg-[#0D92F4]/20 border border-[#0D92F4]/30 text-[#77CDFF] hover:bg-[#0D92F4]/30 transition-colors text-sm font-medium"
      >
        Go to dashboard
      </Link>
    </div>
  </div>
);

const AnimatedRoutes: React.FC<{ isOnline: boolean }> = ({ isOnline }) => {
  const location = useLocation();

  return (
    <Layout isOnline={isOnline}>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          <Route
            path="/dashboard"
            element={
              <ProtectedRoute allowedRoles={['citizen', 'officer', 'admin']}>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/schemes"
            element={
              <ProtectedRoute allowedRoles={['citizen', 'officer', 'admin']}>
                <Schemes />
              </ProtectedRoute>
            }
          />
          <Route
            path="/chat"
            element={
              <ProtectedRoute allowedRoles={['citizen', 'officer', 'admin']}>
                <Chat />
              </ProtectedRoute>
            }
          />
          <Route
            path="/grievances"
            element={
              <ProtectedRoute allowedRoles={['citizen', 'officer', 'admin']}>
                <Grievances />
              </ProtectedRoute>
            }
          />
          <Route
            path="/notices"
            element={
              <ProtectedRoute allowedRoles={['officer', 'admin']}>
                <NoticeDrafter />
              </ProtectedRoute>
            }
          />
          <Route
            path="/nyayavaani"
            element={
              <ProtectedRoute allowedRoles={['citizen', 'officer', 'admin']}>
                <NyayaVaani />
              </ProtectedRoute>
            }
          />
          <Route
            path="/department"
            element={
              <ProtectedRoute allowedRoles={['officer', 'admin']}>
                <DepartmentDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute allowedRoles={['citizen', 'officer', 'admin']}>
                <Settings />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AnimatePresence>
    </Layout>
  );
};

const AppRoutes: React.FC<AppRoutesProps> = ({ isOnline }) => {
  return (
    <Suspense fallback={<SuspenseFallback />}>
      <Routes>
        {/* Public auth routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password/:token" element={<ResetPassword />} />

        {/* Public legal / informational routes */}
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/public/schemes" element={<PublicSchemes />} />

        {/* 404 catch-all (no protected layout) — must come before the protected wildcard */}
        <Route path="/404" element={<NotFound />} />

        {/* Protected app shell */}
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <AnimatedRoutes isOnline={isOnline} />
            </ProtectedRoute>
          }
        />
      </Routes>
    </Suspense>
  );
};

export default AppRoutes;
