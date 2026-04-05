import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
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

interface AppRoutesProps {
  isOnline: boolean;
}

const AnimatedRoutes: React.FC<{ isOnline: boolean }> = ({ isOnline }) => {
  const location = useLocation();

  return (
    <Layout isOnline={isOnline}>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/admin" element={<AdminDashboard />} />
          <Route path="/schemes" element={<Schemes />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/grievances" element={<Grievances />} />
          <Route path="/notices" element={<NoticeDrafter />} />
          <Route path="/nyayavaani" element={<NyayaVaani />} />
          <Route path="/department" element={<DepartmentDashboard />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </AnimatePresence>
    </Layout>
  );
};

const AppRoutes: React.FC<AppRoutesProps> = ({ isOnline }) => {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AnimatedRoutes isOnline={isOnline} />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
};

export default AppRoutes;
