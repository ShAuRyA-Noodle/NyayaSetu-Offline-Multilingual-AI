import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import {
  LayoutDashboard, FileText, MessageSquare, AlertCircle, Mic,
  Settings, LogOut, Building2, ScrollText, Shield, X,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

interface SidebarProps {
  onClose?: () => void;
}

const containerVariants = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.04, delayChildren: 0.15 } },
};

const itemVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.3, ease: [0.25, 1, 0.5, 1] as const } },
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
    <div className="w-64 h-screen flex flex-col glass-surface-strong border-r border-white/[0.04]">
      {/* ─── Logo ─── */}
      <div className="p-5 border-b border-white/[0.04]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Logo mark */}
            <motion.div
              className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#0D92F4] to-[#77CDFF] flex items-center justify-center shadow-lg shadow-[#0D92F4]/20"
              whileHover={{ scale: 1.08, rotate: 2 }}
              transition={{ type: 'spring', stiffness: 400, damping: 15 }}
            >
              <span className="text-white font-display font-bold text-sm">N</span>
            </motion.div>
            <div>
              <h1 className="text-base font-display font-bold text-kora-100 tracking-tight">
                NyayaSetu
              </h1>
              <p className="text-[10px] text-slate-400/40 font-medium tracking-wider uppercase">
                Governance
              </p>
            </div>
          </div>
          <button onClick={onClose}
            className="lg:hidden p-1.5 rounded-lg hover:bg-white/[0.04] transition-colors"
            aria-label="Close sidebar">
            <X className="w-4 h-4 text-slate-400/50" />
          </button>
        </div>
      </div>

      {/* ─── Navigation ─── */}
      <motion.nav
        className="flex-1 p-3 space-y-0.5 overflow-y-auto"
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
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] relative z-10 transition-colors duration-200 ${
                    isActive
                      ? 'text-white font-semibold'
                      : 'text-kora-300/50 hover:text-kora-300/80'
                  }`}
                  whileHover={{ x: isActive ? 0 : 3 }}
                  transition={{ duration: 0.15 }}
                >
                  {/* Active indicator */}
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-active"
                      className="absolute inset-0 rounded-xl"
                      style={{
                        background: 'linear-gradient(135deg, rgba(13, 146, 244, 0.15), rgba(13, 146, 244, 0.08))',
                        border: '1px solid rgba(13, 146, 244, 0.15)',
                      }}
                      transition={{ type: 'spring', stiffness: 350, damping: 28 }}
                    />
                  )}

                  {/* Hover bg */}
                  {!isActive && (
                    <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-white/[0.03]" />
                  )}

                  {/* Active accent line */}
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-accent-line"
                      className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 rounded-r-full bg-[#0D92F4]"
                      transition={{ type: 'spring', stiffness: 350, damping: 28 }}
                    />
                  )}

                  <Icon className={`relative z-10 w-[18px] h-[18px] flex-shrink-0 ${isActive ? 'text-[#77CDFF]' : ''}`} strokeWidth={1.8} />
                  <span className="relative z-10">{t(item.labelKey)}</span>
                </motion.div>
              </Link>
            </motion.div>
          );
        })}
      </motion.nav>

      {/* ─── Divider ─── */}
      <div className="mx-4">
        <div className="h-[1px] bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />
      </div>

      {/* ─── User & Logout ─── */}
      <motion.div className="p-4"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, duration: 0.4 }}>
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold relative overflow-hidden flex-shrink-0">
            <div className="absolute inset-0 bg-gradient-to-br from-[#0D92F4] to-[#77CDFF]" />
            <span className="relative text-white">{user?.username?.charAt(0).toUpperCase() || 'U'}</span>
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-kora-200 text-sm truncate">{user?.username}</p>
            <p className="text-[11px] text-slate-400/40 capitalize font-medium">{user?.role}</p>
          </div>
        </div>
        <motion.button
          onClick={logout}
          className="w-full flex items-center gap-2.5 px-3 py-2 text-red-400/60 hover:text-red-400 hover:bg-red-500/[0.06] rounded-xl text-[13px] font-medium transition-colors"
          whileHover={{ x: 3 }}
          whileTap={{ scale: 0.97 }}
          aria-label="Logout"
        >
          <LogOut className="w-4 h-4" />
          {t('common.logout')}
        </motion.button>
      </motion.div>
    </div>
  );
};

export default Sidebar;
