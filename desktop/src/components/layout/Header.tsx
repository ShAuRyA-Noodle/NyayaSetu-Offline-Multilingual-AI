import React, { useState, useEffect, useRef } from 'react';
import { WifiOff, Bell, Menu } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { useScrollContext } from '../providers/SmoothScrollProvider';
import apiService from '../../services/api';
import LanguageToggle from '../ui/LanguageToggle';

interface HeaderProps {
  isOnline: boolean;
  onMenuClick?: () => void;
}

const Header: React.FC<HeaderProps> = ({ isOnline, onMenuClick }) => {
  const { user } = useAuth();
  const { t } = useTranslation();
  const { scrollY } = useScrollContext();
  const [unreadCount, setUnreadCount] = useState(0);
  const [prevUnread, setPrevUnread] = useState(0);
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);
  const panelRef = useRef<HTMLDivElement>(null);
  const [bellShake, setBellShake] = useState(false);

  const scrolled = scrollY > 20;

  useEffect(() => {
    loadNotificationCount();
    const interval = setInterval(loadNotificationCount, 60000);
    return () => clearInterval(interval);
  }, []);

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

  const iconBtnClass =
    'p-2 rounded-xl transition-all duration-200 border border-transparent hover:border-white/[0.06] hover:bg-white/[0.04]';

  return (
    <header
      className={`sticky top-0 z-30 px-4 md:px-6 py-2.5 transition-all duration-300 ${
        scrolled
          ? 'glass-surface-strong border-b border-white/[0.04] shadow-lg shadow-black/10'
          : 'bg-transparent border-b border-transparent'
      }`}
    >
      <div className="flex items-center justify-between">
        {/* Left side */}
        <div className="flex items-center gap-3">
          <motion.button
            onClick={onMenuClick}
            className={`lg:hidden ${iconBtnClass}`}
            whileTap={{ scale: 0.92 }}
            aria-label="Toggle menu"
          >
            <Menu className="w-5 h-5 text-kora-300/70" />
          </motion.button>

          {/* Status dot */}
          <div className="flex items-center gap-2">
            {isOnline ? (
              <>
                <div className="relative">
                  <div className="w-2 h-2 bg-india-green-500 rounded-full" />
                  <div className="absolute inset-0 w-2 h-2 bg-india-green-500 rounded-full animate-ping opacity-30" />
                </div>
                <span className="text-[11px] font-medium text-kora-300/40 hidden sm:inline tracking-wide uppercase">
                  {t('common.online')}
                </span>
              </>
            ) : (
              <>
                <motion.div animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1, repeat: Infinity }}>
                  <WifiOff className="w-3.5 h-3.5 text-red-500/70" />
                </motion.div>
                <span className="text-[11px] font-medium text-red-500/60 hidden sm:inline tracking-wide uppercase">
                  {t('common.offline')}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-1.5 md:gap-2">
          <LanguageToggle />

          {/* Notifications */}
          <div className="relative" ref={panelRef}>
            <motion.button
              onClick={handleBellClick}
              className={`relative ${iconBtnClass}`}
              whileTap={{ scale: 0.92 }}
              animate={bellShake ? { rotate: [0, -12, 10, -8, 6, -4, 2, 0] } : {}}
              transition={bellShake ? { duration: 0.5 } : { duration: 0.15 }}
              aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
            >
              <Bell className="w-[18px] h-[18px] text-kora-300/60" strokeWidth={1.8} />
              <AnimatePresence>
                {unreadCount > 0 && (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0 }}
                    transition={{ type: 'spring', stiffness: 500, damping: 20 }}
                    className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-[#0D92F4] text-white text-[10px] rounded-full flex items-center justify-center font-bold shadow-lg shadow-[#0D92F4]/30 tabular-nums"
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
                  className="absolute right-0 mt-2 w-80 rounded-xl overflow-hidden glass-surface-strong z-50"
                  style={{ boxShadow: '0 16px 48px rgba(0,0,0,0.4)' }}
                >
                  <div className="flex items-center justify-between p-3 border-b border-white/[0.04]">
                    <h3 className="font-semibold text-kora-200 text-sm">{t('header.notifications')}</h3>
                    {unreadCount > 0 && (
                      <button onClick={handleMarkAllRead}
                        className="text-xs text-slate-400/60 hover:text-[#77CDFF] font-medium transition-colors">
                        {t('header.markAllRead')}
                      </button>
                    )}
                  </div>
                  <div className="max-h-72 overflow-y-auto" data-lenis-prevent>
                    {notifications.length === 0 ? (
                      <div className="p-8 text-center">
                        <Bell className="w-6 h-6 text-[#0D92F4]/20 mx-auto mb-2" />
                        <p className="text-xs text-slate-400/40">{t('header.noNotifications')}</p>
                      </div>
                    ) : (
                      notifications.map((n: any, i: number) => (
                        <motion.div key={n.id}
                          initial={{ opacity: 0, y: 8 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.03, duration: 0.25 }}
                          className="p-3 border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors"
                        >
                          <p className="text-xs font-medium text-kora-200">{n.subject}</p>
                          <p className="text-xs text-slate-400/50 mt-0.5 line-clamp-2">{n.message}</p>
                          <p className="text-[10px] text-slate-500/30 mt-1 tabular-nums">{new Date(n.created_at).toLocaleString()}</p>
                        </motion.div>
                      ))
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* User avatar */}
          <div className="hidden md:flex items-center gap-2.5 pl-3 ml-1 border-l border-white/[0.06]">
            <motion.div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold relative overflow-hidden"
              whileHover={{ scale: 1.08 }}
              transition={{ type: 'spring', stiffness: 400, damping: 15 }}
            >
              <div className="absolute inset-0 bg-gradient-to-br from-[#0D92F4] to-[#77CDFF]" />
              <span className="relative text-white">
                {user?.username?.charAt(0).toUpperCase() || 'U'}
              </span>
            </motion.div>
            <span className="text-sm font-medium text-kora-200/70">{user?.username}</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
