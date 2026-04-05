import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import {
  LayoutDashboard, FileText, MessageSquare, AlertCircle, Mic,
  Settings, LogOut, Building2, ScrollText, Shield, X,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import AshokaChakra from '../decorative/AshokaChakra';

interface SidebarProps {
  onClose?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ onClose }) => {
  const location = useLocation();
  const { logout, user } = useAuth();
  const { t } = useTranslation();

  const allMenuItems = [
    { path: '/dashboard', icon: LayoutDashboard, labelKey: 'sidebar.dashboard', roles: ['citizen'] },
    { path: '/department', icon: Building2, labelKey: 'sidebar.department', roles: ['officer'] },
    { path: '/admin', icon: Shield, labelKey: 'sidebar.adminDashboard', roles: ['admin'] },
    { path: '/schemes', icon: FileText, labelKey: 'sidebar.schemes', roles: ['citizen', 'officer', 'admin'] },
    { path: '/chat', icon: MessageSquare, labelKey: 'sidebar.askQuestion', roles: ['citizen', 'officer', 'admin'] },
    { path: '/grievances', icon: AlertCircle, labelKey: 'sidebar.grievances', roles: ['citizen', 'officer', 'admin'] },
    { path: '/notices', icon: ScrollText, labelKey: 'sidebar.noticeBoard', roles: ['citizen', 'officer', 'admin'] },
    { path: '/nyayavaani', icon: Mic, labelKey: 'sidebar.nyayavaani', roles: ['citizen', 'officer', 'admin'] },
    { path: '/settings', icon: Settings, labelKey: 'sidebar.settings', roles: ['citizen', 'officer', 'admin'] },
  ];

  const role = user?.role || 'citizen';
  const menuItems = allMenuItems.filter(item => item.roles.includes(role));

  return (
    <div className="w-64 village-panel flex flex-col h-screen">
      {/* Logo */}
      <div className="p-5 border-b border-mitti-200/20 dark:border-night-border/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <AshokaChakra size={36} spinning />
            </div>
            <div>
              <h1 className="text-xl font-display font-bold text-gradient-mitti">
                {t('common.appName')}
              </h1>
              <p className="text-[10px] font-devanagari text-mitti-400 dark:text-mitti-500 tracking-wide">
                {t('sidebar.governancePlatform')}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="lg:hidden p-1 rounded-lg hover:bg-mitti-100/50 dark:hover:bg-night-card transition-colors">
            <X className="w-5 h-5 text-mitti-400" />
          </button>
        </div>
      </div>

      {/* Menu Items */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <Link key={item.path} to={item.path} onClick={onClose} className="relative block">
              <motion.div
                className={`flex items-center space-x-3 px-4 py-2.5 rounded-xl transition-colors text-sm relative z-10 ${
                  isActive
                    ? 'text-white font-semibold'
                    : 'text-mitti-700 dark:text-mitti-300 hover:bg-mitti-100/50 dark:hover:bg-night-card/50'
                }`}
                whileHover={{ x: isActive ? 0 : 4 }}
                transition={{ duration: 0.2 }}
              >
                {isActive && (
                  <motion.div
                    layoutId="sidebar-active"
                    className="absolute inset-0 bg-mitti-500 rounded-xl shadow-mitti"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                  />
                )}
                <Icon className="w-5 h-5 relative z-10" strokeWidth={1.8} />
                <span className="relative z-10">{t(item.labelKey)}</span>
              </motion.div>
            </Link>
          );
        })}
      </nav>

      {/* Kolam divider */}
      <div className="mx-4">
        <div className="kolam-divider" />
      </div>

      {/* User Profile & Logout */}
      <div className="p-4">
        <div className="flex items-center mb-3">
          <div className="w-10 h-10 bg-gradient-to-br from-mitti-500 to-haldi-500 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-mitti">
            {user?.username?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="ml-3 min-w-0">
            <p className="font-semibold text-mitti-900 dark:text-kora-200 text-sm truncate">{user?.username}</p>
            <p className="text-xs text-mitti-500 dark:text-mitti-400 capitalize font-medium">{user?.role}</p>
          </div>
        </div>
        <motion.button
          onClick={logout}
          className="w-full flex items-center px-4 py-2 text-red-500 hover:bg-red-500/10 rounded-xl transition-all text-sm font-medium"
          whileHover={{ x: 4 }}
          whileTap={{ scale: 0.98 }}
        >
          <LogOut className="w-4 h-4 mr-3" />
          {t('common.logout')}
        </motion.button>
      </div>
    </div>
  );
};

export default Sidebar;
