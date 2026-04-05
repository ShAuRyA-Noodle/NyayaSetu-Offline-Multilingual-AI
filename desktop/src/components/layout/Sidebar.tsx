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

// Stagger animation for menu items
const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.03,
      delayChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: -12 },
  visible: {
    opacity: 1,
    x: 0,
    transition: {
      duration: 0.35,
      ease: [0.25, 1, 0.5, 1] as const,
    },
  },
};

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
      {/* Logo — with warm glow in dark mode */}
      <div className="p-5 border-b border-mitti-200/20 dark:border-night-border/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <motion.div
              className="relative"
              whileHover={{ scale: 1.08 }}
              transition={{ type: 'spring', stiffness: 400, damping: 15 }}
            >
              <AshokaChakra size={36} spinning />
              {/* Glow ring behind chakra */}
              <div className="absolute inset-0 rounded-full opacity-0 dark:opacity-30"
                   style={{ boxShadow: '0 0 12px rgba(194, 123, 58, 0.4)' }} />
            </motion.div>
            <div>
              <h1 className="text-xl font-display font-bold text-gradient-mitti">
                {t('common.appName')}
              </h1>
              <p className="text-[10px] font-devanagari text-mitti-400 dark:text-mitti-500 tracking-wide">
                {t('sidebar.governancePlatform')}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden p-1.5 rounded-lg hover:bg-mitti-100/50 dark:hover:bg-night-card transition-colors"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5 text-mitti-400" />
          </button>
        </div>
      </div>

      {/* Menu Items — staggered entrance */}
      <motion.nav
        className="flex-1 p-3 space-y-1 overflow-y-auto"
        data-lenis-prevent
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;

          return (
            <motion.div key={item.path} variants={itemVariants}>
              <Link to={item.path} onClick={onClose} className="relative block group">
                <motion.div
                  className={`flex items-center space-x-3 px-4 py-2.5 rounded-xl text-sm relative z-10 ${
                    isActive
                      ? 'text-white font-semibold'
                      : 'text-mitti-700 dark:text-mitti-300'
                  }`}
                  whileHover={{ x: isActive ? 0 : 4 }}
                  transition={{ duration: 0.15, ease: [0.25, 1, 0.5, 1] }}
                >
                  {/* Active background indicator — shared spring animation */}
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-active"
                      className="absolute inset-0 rounded-xl"
                      style={{
                        background: 'linear-gradient(135deg, #C27B3A, #A66228)',
                        boxShadow: '0 4px 16px rgba(194, 123, 58, 0.25), 0 0 20px rgba(194, 123, 58, 0.1)',
                      }}
                      transition={{ type: 'spring', stiffness: 350, damping: 28 }}
                    />
                  )}

                  {/* Hover background for non-active items */}
                  {!isActive && (
                    <div className="absolute inset-0 rounded-xl bg-mitti-100/0 dark:bg-night-card/0 group-hover:bg-mitti-100/50 dark:group-hover:bg-night-card/50 transition-colors duration-200" />
                  )}

                  {/* Icon with hover scale effect */}
                  <motion.div
                    className="relative z-10"
                    whileHover={{ scale: 1.12 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 15 }}
                  >
                    <Icon className="w-5 h-5" strokeWidth={1.8} />
                  </motion.div>

                  {/* Label with line-reveal effect on hover */}
                  <span className="relative z-10 line-reveal">{t(item.labelKey)}</span>
                </motion.div>
              </Link>
            </motion.div>
          );
        })}
      </motion.nav>

      {/* Kolam divider — animated entrance */}
      <motion.div
        className="mx-4"
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ delay: 0.4, duration: 0.5, ease: [0.25, 1, 0.5, 1] }}
      >
        <div className="kolam-divider" />
      </motion.div>

      {/* User Profile & Logout */}
      <motion.div
        className="p-4"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35, duration: 0.4, ease: [0.25, 1, 0.5, 1] }}
      >
        <div className="flex items-center mb-3 group">
          {/* Avatar with gradient ring animation on hover */}
          <motion.div
            className="relative"
            whileHover={{ scale: 1.08 }}
            transition={{ type: 'spring', stiffness: 300, damping: 15 }}
          >
            <div className="w-10 h-10 bg-gradient-to-br from-mitti-500 to-haldi-500 rounded-full flex items-center justify-center text-white font-bold text-sm shadow-mitti">
              {user?.username?.charAt(0).toUpperCase() || 'U'}
            </div>
            {/* Glow ring on hover */}
            <div
              className="absolute -inset-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300"
              style={{
                background: 'conic-gradient(from 0deg, #C27B3A, #F59E0B, #D49A5E, #C27B3A)',
                mask: 'radial-gradient(farthest-side, transparent calc(100% - 2px), #000 calc(100% - 2px))',
                WebkitMask: 'radial-gradient(farthest-side, transparent calc(100% - 2px), #000 calc(100% - 2px))',
                zIndex: -1,
              }}
            />
          </motion.div>
          <div className="ml-3 min-w-0">
            <p className="font-semibold text-mitti-900 dark:text-kora-200 text-sm truncate">{user?.username}</p>
            <p className="text-xs text-mitti-500 dark:text-mitti-400 capitalize font-medium">{user?.role}</p>
          </div>
        </div>
        <motion.button
          onClick={logout}
          className="w-full flex items-center px-4 py-2 text-red-500 hover:bg-red-500/10 rounded-xl text-sm font-medium"
          whileHover={{ x: 4 }}
          whileTap={{ scale: 0.97 }}
          transition={{ duration: 0.15, ease: [0.25, 1, 0.5, 1] }}
          aria-label="Logout"
        >
          <LogOut className="w-4 h-4 mr-3" />
          {t('common.logout')}
        </motion.button>
      </motion.div>
    </div>
  );
};

export default Sidebar;
