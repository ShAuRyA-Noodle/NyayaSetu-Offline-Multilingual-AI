import React, { useState, useEffect, useRef } from 'react';
import { WifiOff, Moon, Sun, Bell, Menu } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import { useScrollContext } from '../providers/SmoothScrollProvider';
import apiService from '../../services/api';
import LanguageToggle from '../ui/LanguageToggle';

interface HeaderProps {
  isOnline: boolean;
  onMenuClick?: () => void;
}

const Header: React.FC<HeaderProps> = ({ isOnline, onMenuClick }) => {
  const { darkMode, toggleDarkMode } = useTheme();
  const { user } = useAuth();
  const { t } = useTranslation();
  const { scrollY } = useScrollContext();
  const [unreadCount, setUnreadCount] = useState(0);
  const [prevUnread, setPrevUnread] = useState(0);
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const panelRef = useRef<HTMLDivElement>(null);
  const [bellShake, setBellShake] = useState(false);

  // Simple scroll state — no per-frame blur computation
  const scrolled = scrollY > 20;

  useEffect(() => {
    loadNotificationCount();
    const interval = setInterval(loadNotificationCount, 60000);
    return () => clearInterval(interval);
  }, []);

  // Bell shake animation on new notification
  useEffect(() => {
    if (unreadCount > prevUnread && prevUnread >= 0) {
      setBellShake(true);
      const timer = setTimeout(() => setBellShake(false), 600);
      return () => clearTimeout(timer);
    }
    setPrevUnread(unreadCount);
  }, [unreadCount, prevUnread]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const loadNotificationCount = async () => {
    try {
      const data = await apiService.getNotificationCount();
      setUnreadCount(data.unread_count || 0);
    } catch { /* ignore */ }
  };

  const handleBellClick = async () => {
    setShowNotifications(!showNotifications);
    if (!showNotifications) {
      try {
        const data = await apiService.getNotifications();
        setNotifications(data.notifications || []);
      } catch { /* ignore */ }
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiService.markAllNotificationsRead();
      setUnreadCount(0);
      setNotifications([]);
    } catch { /* ignore */ }
  };

  return (
    <header
      className={`village-panel border-b border-mitti-200/20 dark:border-night-border/40 px-4 md:px-6 py-3 sticky top-0 z-30 transition-shadow duration-300 ${scrolled ? 'header-scrolled' : ''}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <motion.button
            onClick={onMenuClick}
            className="lg:hidden p-2 rounded-xl hover:bg-mitti-100/50 dark:hover:bg-night-card/50"
            whileTap={{ scale: 0.92 }}
            aria-label="Toggle menu"
          >
            <Menu className="w-5 h-5 text-mitti-500 dark:text-mitti-400" />
          </motion.button>

          {/* Connection status — breathing dot or flash */}
          <div className="flex items-center space-x-2">
            {isOnline ? (
              <>
                <motion.div
                  className="w-2 h-2 bg-mitti-500 rounded-full"
                  animate={{ scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] }}
                  transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
                />
                <span className="text-xs font-medium text-mitti-500 dark:text-mitti-400 hidden sm:inline">
                  {t('common.online')}
                </span>
              </>
            ) : (
              <>
                <motion.div
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                >
                  <WifiOff className="w-4 h-4 text-red-500" />
                </motion.div>
                <span className="text-xs font-medium text-red-500 hidden sm:inline">
                  {t('common.offline')}
                </span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2 md:space-x-3">
          <LanguageToggle />

          {/* Notification bell — shakes on new count */}
          <div className="relative" ref={panelRef}>
            <motion.button
              onClick={handleBellClick}
              className="relative p-2 rounded-xl bg-kora-200/50 dark:bg-night-card/60 hover:bg-kora-200/80 dark:hover:bg-night-card/80 border border-mitti-200/20 dark:border-night-border/40 transition-colors"
              whileTap={{ scale: 0.92 }}
              animate={bellShake ? {
                rotate: [0, -12, 10, -8, 6, -4, 2, 0],
              } : {}}
              transition={bellShake ? {
                duration: 0.5,
                ease: [0.25, 1, 0.5, 1],
              } : {
                duration: 0.15,
              }}
              aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
            >
              <Bell className="w-5 h-5 text-mitti-500 dark:text-mitti-400" strokeWidth={1.8} />
              <AnimatePresence>
                {unreadCount > 0 && (
                  <motion.span
                    initial={{ scale: 0, y: 5 }}
                    animate={{ scale: 1, y: 0 }}
                    exit={{ scale: 0 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 20 }}
                    className="absolute -top-1 -right-1 w-5 h-5 bg-mitti-500 text-white text-xs rounded-full flex items-center justify-center font-bold shadow-mitti tabular-nums"
                  >
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </motion.span>
                )}
              </AnimatePresence>
            </motion.button>

            {/* Notification panel */}
            <AnimatePresence>
              {showNotifications && (
                <motion.div
                  initial={{ opacity: 0, y: -8, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.96 }}
                  transition={{ type: 'spring', damping: 22, stiffness: 300 }}
                  className="absolute right-0 mt-2 w-80 village-card z-50 max-h-96 overflow-hidden"
                  style={{ boxShadow: 'var(--shadow-overlay)' }}
                >
                  <div className="flex items-center justify-between p-3 border-b border-mitti-200/20 dark:border-night-border/40">
                    <h3 className="font-semibold text-mitti-900 dark:text-kora-200 text-sm">{t('header.notifications')}</h3>
                    {unreadCount > 0 && (
                      <button
                        onClick={handleMarkAllRead}
                        className="text-xs text-mitti-500 hover:text-mitti-600 font-medium transition-colors"
                      >
                        {t('header.markAllRead')}
                      </button>
                    )}
                  </div>
                  <div className="max-h-72 overflow-y-auto" data-lenis-prevent>
                    {notifications.length === 0 ? (
                      <div className="p-6 text-center">
                        <Bell className="w-8 h-8 text-mitti-300 dark:text-night-muted mx-auto mb-2 opacity-50" />
                        <p className="text-sm text-mitti-400 dark:text-night-muted">
                          {t('header.noNotifications')}
                        </p>
                      </div>
                    ) : (
                      notifications.map((n: any, i: number) => (
                        <motion.div
                          key={n.id}
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.03, duration: 0.25, ease: [0.25, 1, 0.5, 1] }}
                          className="p-3 border-b border-mitti-100/20 dark:border-night-border/20 hover:bg-mitti-50/50 dark:hover:bg-night-card/50 transition-colors"
                        >
                          <p className="text-xs font-medium text-mitti-900 dark:text-kora-200">{n.subject}</p>
                          <p className="text-xs text-mitti-500 dark:text-night-muted mt-0.5 line-clamp-2">{n.message}</p>
                          <p className="text-xs text-mitti-400 mt-1 tabular-nums">{new Date(n.created_at).toLocaleString()}</p>
                        </motion.div>
                      ))
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Dark mode toggle — sun/moon morph with rotation */}
          <motion.button
            onClick={toggleDarkMode}
            className="p-2 rounded-xl bg-kora-200/50 dark:bg-night-card/60 hover:bg-kora-200/80 dark:hover:bg-night-card/80 border border-mitti-200/20 dark:border-night-border/40 transition-colors"
            whileTap={{ scale: 0.92 }}
            aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            <AnimatePresence mode="wait" initial={false}>
              {darkMode ? (
                <motion.div
                  key="sun"
                  initial={{ rotate: -90, scale: 0, opacity: 0 }}
                  animate={{ rotate: 0, scale: 1, opacity: 1 }}
                  exit={{ rotate: 90, scale: 0, opacity: 0 }}
                  transition={{ duration: 0.25, ease: [0.25, 1, 0.5, 1] }}
                >
                  <Sun className="w-5 h-5 text-haldi-400" />
                </motion.div>
              ) : (
                <motion.div
                  key="moon"
                  initial={{ rotate: 90, scale: 0, opacity: 0 }}
                  animate={{ rotate: 0, scale: 1, opacity: 1 }}
                  exit={{ rotate: -90, scale: 0, opacity: 0 }}
                  transition={{ duration: 0.25, ease: [0.25, 1, 0.5, 1] }}
                >
                  <Moon className="w-5 h-5 text-mitti-500" />
                </motion.div>
              )}
            </AnimatePresence>
          </motion.button>

          {/* User avatar */}
          <div className="hidden md:flex items-center space-x-2 pl-3 border-l border-mitti-200/20 dark:border-night-border/40">
            <motion.div
              className="w-8 h-8 bg-gradient-to-br from-mitti-500 to-haldi-500 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-mitti"
              whileHover={{ scale: 1.1 }}
              transition={{ type: 'spring', stiffness: 400, damping: 15 }}
            >
              {user?.username?.charAt(0).toUpperCase() || 'U'}
            </motion.div>
            <span className="text-sm font-medium text-mitti-700 dark:text-kora-200">{user?.username}</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
