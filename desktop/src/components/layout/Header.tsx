import React, { useState, useEffect, useRef } from 'react';
import { WifiOff, Moon, Sun, Bell, Menu } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
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
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadNotificationCount();
    const interval = setInterval(loadNotificationCount, 60000);
    return () => clearInterval(interval);
  }, []);

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
    <header className="village-panel border-b border-mitti-200/20 dark:border-night-border/40 px-4 md:px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <button onClick={onMenuClick} className="lg:hidden p-2 rounded-xl hover:bg-mitti-100/50 dark:hover:bg-night-card/50 transition-colors">
            <Menu className="w-5 h-5 text-mitti-500 dark:text-mitti-400" />
          </button>
          <div className="flex items-center space-x-2">
            {isOnline ? (
              <>
                <div className="w-2 h-2 bg-mitti-500 rounded-full animate-pulse-soft" />
                <span className="text-xs font-medium text-mitti-500 dark:text-mitti-400 hidden sm:inline">{t('common.online')}</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-500" />
                <span className="text-xs font-medium text-red-500 hidden sm:inline">{t('common.offline')}</span>
              </>
            )}
          </div>
        </div>

        <div className="flex items-center space-x-2 md:space-x-3">
          <LanguageToggle />

          <div className="relative" ref={panelRef}>
            <motion.button
              onClick={handleBellClick}
              className="relative p-2 rounded-xl bg-kora-200/50 dark:bg-night-card/60 hover:bg-mitti-100/60 dark:hover:bg-night-card/80 transition-colors border border-mitti-200/20 dark:border-night-border/40"
              whileTap={{ scale: 0.95 }}
            >
              <Bell className="w-5 h-5 text-mitti-500 dark:text-mitti-400" strokeWidth={1.8} />
              {unreadCount > 0 && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute -top-1 -right-1 w-5 h-5 bg-mitti-500 text-white text-xs rounded-full flex items-center justify-center font-bold shadow-mitti"
                >
                  {unreadCount > 9 ? '9+' : unreadCount}
                </motion.span>
              )}
            </motion.button>

            <AnimatePresence>
              {showNotifications && (
                <motion.div
                  initial={{ opacity: 0, y: -10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.95 }}
                  transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                  className="absolute right-0 mt-2 w-80 village-card z-50 max-h-96 overflow-hidden"
                >
                  <div className="flex items-center justify-between p-3 border-b border-mitti-200/20 dark:border-night-border/40">
                    <h3 className="font-semibold text-mitti-900 dark:text-kora-200 text-sm">{t('header.notifications')}</h3>
                    {unreadCount > 0 && (
                      <button onClick={handleMarkAllRead} className="text-xs text-mitti-500 hover:text-mitti-600 font-medium">
                        {t('header.markAllRead')}
                      </button>
                    )}
                  </div>
                  <div className="max-h-72 overflow-y-auto">
                    {notifications.length === 0 ? (
                      <p className="p-4 text-center text-sm text-mitti-400 dark:text-night-muted">{t('header.noNotifications')}</p>
                    ) : (
                      notifications.map((n: any) => (
                        <div key={n.id} className="p-3 border-b border-mitti-100/20 dark:border-night-border/20 hover:bg-mitti-50/50 dark:hover:bg-night-card/50 transition-colors">
                          <p className="text-xs font-medium text-mitti-900 dark:text-kora-200">{n.subject}</p>
                          <p className="text-xs text-mitti-500 dark:text-night-muted mt-0.5">{n.message}</p>
                          <p className="text-xs text-mitti-400 mt-1">{new Date(n.created_at).toLocaleString()}</p>
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <motion.button
            onClick={toggleDarkMode}
            className="p-2 rounded-xl bg-kora-200/50 dark:bg-night-card/60 hover:bg-mitti-100/60 dark:hover:bg-night-card/80 transition-colors border border-mitti-200/20 dark:border-night-border/40"
            whileTap={{ scale: 0.95 }}
          >
            {darkMode ? <Sun className="w-5 h-5 text-haldi-400" /> : <Moon className="w-5 h-5 text-mitti-500" />}
          </motion.button>

          <div className="hidden md:flex items-center space-x-2 pl-3 border-l border-mitti-200/20 dark:border-night-border/40">
            <div className="w-8 h-8 bg-gradient-to-br from-mitti-500 to-haldi-500 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-mitti">
              {user?.username?.charAt(0).toUpperCase() || 'U'}
            </div>
            <span className="text-sm font-medium text-mitti-700 dark:text-kora-200">{user?.username}</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
