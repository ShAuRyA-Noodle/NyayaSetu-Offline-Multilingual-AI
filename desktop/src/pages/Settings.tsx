import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import {
  Bell, HardDrive,
  Trash2, Download, Info, Check, X, RefreshCw, Lock, Shield, Monitor,
  Smartphone, Laptop, Eye, EyeOff, AlertCircle, Globe,
} from 'lucide-react';
import apiService from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import PageTransition from '../components/ui/PageTransition';
import ThemedSpinner from '../components/ui/ThemedSpinner';
import AshokaChakra from '../components/decorative/AshokaChakra';
import TricolorDivider from '../components/decorative/TricolorDivider';

interface Session {
  id: number;
  ip_address: string | null;
  user_agent: string | null;
  device_type: string;
  created_at: string;
  last_activity: string;
  expires_at: string;
}

const Settings: React.FC = () => {
  const { darkMode, toggleDarkMode } = useTheme();
  const { user } = useAuth();
  const { t, i18n } = useTranslation();
  const [notifications, setNotifications] = useState(true);
  const [autoSync, setAutoSync] = useState(true);
  const [language, setLanguage] = useState(i18n.language || 'en');
  const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [lastSync, setLastSync] = useState(new Date());
  const [savedMessage, setSavedMessage] = useState('');

  const [passwordForm, setPasswordForm] = useState({ current: '', newPw: '', confirm: '' });
  const [showPasswords, setShowPasswords] = useState({ current: false, new: false, confirm: false });
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState('');

  const [sessions, setSessions] = useState<Session[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [revokingId, setRevokingId] = useState<number | null>(null);

  useEffect(() => {
    setNotifications(localStorage.getItem('notifications') !== 'false');
    setAutoSync(localStorage.getItem('autoSync') !== 'false');
    checkApiStatus();
    loadSessions();
    const interval = setInterval(checkApiStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkApiStatus = async () => {
    setApiStatus('checking');
    try { await apiService.checkHealth(); setApiStatus('online'); setLastSync(new Date()); }
    catch { setApiStatus('offline'); }
  };

  const loadSessions = async () => {
    setSessionsLoading(true);
    try { const data = await apiService.listSessions(); setSessions(data.sessions || []); }
    catch { setSessions([]); } finally { setSessionsLoading(false); }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(''); setPasswordSuccess('');
    if (passwordForm.newPw !== passwordForm.confirm) { setPasswordError('Passwords do not match'); return; }
    if (passwordForm.newPw.length < 8) { setPasswordError('Min 8 characters required'); return; }
    setPasswordLoading(true);
    try {
      await apiService.changePassword(passwordForm.current, passwordForm.newPw);
      setPasswordSuccess(t('settings.passwordChanged'));
      setPasswordForm({ current: '', newPw: '', confirm: '' });
    } catch (err: any) {
      setPasswordError(err.response?.data?.detail || 'Failed');
    } finally { setPasswordLoading(false); }
  };

  const handleRevokeSession = async (sessionId: number) => {
    setRevokingId(sessionId);
    try { await apiService.revokeSession(sessionId); setSessions(sessions.filter(s => s.id !== sessionId)); }
    catch { /* ignore */ } finally { setRevokingId(null); }
  };

  const handleRevokeAll = async () => {
    if (!confirm('This will log you out of all other devices. Continue?')) return;
    try { await apiService.logoutAll(); await loadSessions(); } catch { /* ignore */ }
  };

  const handleLanguageChange = (lang: string) => {
    setLanguage(lang);
    i18n.changeLanguage(lang);
    localStorage.setItem('language', lang);
  };

  const handleSaveSettings = () => {
    localStorage.setItem('darkMode', darkMode.toString());
    localStorage.setItem('notifications', notifications.toString());
    localStorage.setItem('autoSync', autoSync.toString());
    localStorage.setItem('language', language);
    setSavedMessage(t('common.success'));
    setTimeout(() => setSavedMessage(''), 3000);
  };

  const handleClearCache = () => {
    if (confirm('Clear all cached data?')) { localStorage.clear(); sessionStorage.clear(); window.location.reload(); }
  };

  const handleExportData = () => {
    const data = { settings: { darkMode, notifications, autoSync, language }, timestamp: new Date().toISOString(), version: '2.0.0' };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `nyayasetu-settings-${Date.now()}.json`; a.click();
    URL.revokeObjectURL(url);
  };

  const getDeviceIcon = (d: string) => d === 'mobile' ? Smartphone : d === 'tablet' ? Monitor : Laptop;
  const formatDate = (d: string) => new Date(d).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

  const SettingCard = ({ icon: Icon, title, children, color }: { icon: any; title: string; children: React.ReactNode; color: string }) => (
    <motion.div className="village-card p-5 md:p-6" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <div className="flex items-center space-x-3 mb-4">
        <div className={`p-2.5 rounded-xl ${color} shadow-sm`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <h3 className="text-lg font-semibold text-mitti-900 dark:text-kora-100">{title}</h3>
      </div>
      <div className="space-y-4">{children}</div>
    </motion.div>
  );

  const Toggle = ({ label, value, onChange, description }: any) => (
    <div className="flex items-center justify-between">
      <div className="flex-1">
        <p className="font-medium text-mitti-900 dark:text-kora-100">{label}</p>
        {description && <p className="text-sm text-mitti-500 dark:text-mitti-400 mt-0.5">{description}</p>}
      </div>
      <button onClick={() => onChange(!value)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${value ? 'bg-mitti-500' : 'bg-gray-300 dark:bg-gray-600'}`}>
        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm ${value ? 'translate-x-6' : 'translate-x-1'}`} />
      </button>
    </div>
  );

  const PasswordInput = ({ label, value, onChange, show, onToggle, placeholder }: any) => (
    <div>
      <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-1">{label}</label>
      <div className="relative">
        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-mitti-400 w-4 h-4" />
        <input type={show ? 'text' : 'password'} value={value} onChange={onChange} placeholder={placeholder} required
          className="w-full pl-10 pr-10 py-2.5 village-input text-sm" />
        <button type="button" onClick={onToggle} className="absolute right-3 top-1/2 -translate-y-1/2 text-mitti-400 hover:text-mitti-500 transition-colors">
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );

  return (
    <PageTransition>
      <div className="p-4 md:p-6 min-h-screen">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="inline-block mb-3">
              <AshokaChakra size={48} />
            </div>
            <h1 className="text-3xl md:text-4xl font-bold font-display text-mitti-900 dark:text-kora-100 mb-2">{t('settings.title')}</h1>
            <p className="text-mitti-600 dark:text-mitti-400">{t('settings.subtitle')}</p>
            <TricolorDivider className="mt-3" width="w-20" />
          </div>

          {savedMessage && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
              className="mb-6 glass-green p-4 flex items-center space-x-3">
              <Check className="w-5 h-5 text-india-green-600" />
              <p className="text-india-green-800 dark:text-india-green-300 font-medium">{savedMessage}</p>
            </motion.div>
          )}

          <div className="space-y-6">
            {/* Security */}
            <SettingCard icon={Shield} title={t('settings.security')} color="bg-red-500">
              <form onSubmit={handleChangePassword} className="space-y-3">
                <PasswordInput label={t('settings.currentPassword')} value={passwordForm.current}
                  onChange={(e: any) => setPasswordForm({ ...passwordForm, current: e.target.value })}
                  show={showPasswords.current} onToggle={() => setShowPasswords({ ...showPasswords, current: !showPasswords.current })}
                  placeholder={t('settings.currentPassword')} />
                <PasswordInput label={t('settings.newPassword')} value={passwordForm.newPw}
                  onChange={(e: any) => setPasswordForm({ ...passwordForm, newPw: e.target.value })}
                  show={showPasswords.new} onToggle={() => setShowPasswords({ ...showPasswords, new: !showPasswords.new })}
                  placeholder="Min 8 characters" />
                <PasswordInput label={t('settings.confirmNewPassword')} value={passwordForm.confirm}
                  onChange={(e: any) => setPasswordForm({ ...passwordForm, confirm: e.target.value })}
                  show={showPasswords.confirm} onToggle={() => setShowPasswords({ ...showPasswords, confirm: !showPasswords.confirm })}
                  placeholder={t('settings.confirmNewPassword')} />
                {passwordError && <div className="flex items-center space-x-2 text-red-500 text-sm"><AlertCircle className="w-4 h-4" /><span>{passwordError}</span></div>}
                {passwordSuccess && <div className="flex items-center space-x-2 text-india-green-600 text-sm"><Check className="w-4 h-4" /><span>{passwordSuccess}</span></div>}
                <motion.button type="submit" disabled={passwordLoading || !passwordForm.current || !passwordForm.newPw || !passwordForm.confirm}
                  className="w-full py-2.5 bg-red-500 hover:bg-red-600 text-white rounded-xl font-medium transition-colors disabled:opacity-50 flex items-center justify-center"
                  whileTap={{ scale: 0.98 }}>
                  {passwordLoading ? <ThemedSpinner size="sm" /> : <><Lock className="w-4 h-4 mr-2" />{t('settings.updatePassword')}</>}
                </motion.button>
              </form>
            </SettingCard>

            {/* Sessions */}
            <SettingCard icon={Monitor} title={t('settings.sessions')} color="bg-terracotta-500">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm text-mitti-500">{sessions.length} session{sessions.length !== 1 ? 's' : ''}</p>
                <div className="flex space-x-2">
                  <button onClick={loadSessions} className="text-sm text-mitti-600 hover:text-mitti-700 font-medium">{t('common.refresh')}</button>
                  {sessions.length > 1 && <button onClick={handleRevokeAll} className="text-sm text-red-500 hover:text-red-600 font-medium">{t('settings.revokeAllSessions')}</button>}
                </div>
              </div>
              {sessionsLoading ? <div className="text-center py-4"><ThemedSpinner size="sm" /></div>
              : sessions.length === 0 ? <p className="text-mitti-500 text-sm text-center py-4">No active sessions</p>
              : <div className="space-y-2">
                  {sessions.map((session, index) => {
                    const DeviceIcon = getDeviceIcon(session.device_type);
                    const isCurrent = index === 0;
                    return (
                      <div key={session.id} className={`p-3 rounded-xl border ${isCurrent ? 'bg-mitti-500/10 border-mitti-500/20' : 'village-card-subtle'}`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <DeviceIcon className="w-5 h-5 text-mitti-500" />
                            <div>
                              <div className="flex items-center space-x-2">
                                <p className="text-sm font-medium text-mitti-900 dark:text-kora-100 capitalize">{session.device_type}</p>
                                {isCurrent && <span className="px-2 py-0.5 bg-mitti-500 text-white text-xs rounded-full">{t('settings.currentSession')}</span>}
                              </div>
                              <p className="text-xs text-mitti-500">{session.ip_address || 'Unknown IP'} - {formatDate(session.last_activity)}</p>
                            </div>
                          </div>
                          {!isCurrent && (
                            <button onClick={() => handleRevokeSession(session.id)} disabled={revokingId === session.id}
                              className="px-3 py-1.5 text-xs text-red-500 hover:bg-red-500/10 rounded-lg font-medium transition-colors disabled:opacity-50">
                              {revokingId === session.id ? '...' : t('settings.revokeSession')}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              }
            </SettingCard>

            {/* Appearance & Language */}
            <SettingCard icon={Globe} title={t('settings.appearance')} color="bg-mitti-500">
              <Toggle label={t('settings.darkModeLabel')} value={darkMode} onChange={toggleDarkMode} description={t('settings.darkModeDesc')} />
              <div>
                <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">{t('settings.interfaceLanguage')}</label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { code: 'en', label: t('common.english'), sub: 'English' },
                    { code: 'hi', label: t('common.hindi'), sub: 'हिंदी' },
                  ].map((lang) => (
                    <motion.button key={lang.code} onClick={() => handleLanguageChange(lang.code)}
                      className={`p-4 rounded-xl border-2 transition-all text-center ${
                        language === lang.code
                          ? 'border-mitti-500 bg-mitti-500/10 shadow-mitti'
                          : 'border-mitti-200/20 dark:border-night-border/10 hover:border-mitti-300 village-card-subtle'
                      }`}
                      whileTap={{ scale: 0.97 }}>
                      <p className="font-bold text-mitti-900 dark:text-kora-100 text-lg">{lang.sub}</p>
                      <p className="text-xs text-mitti-500 dark:text-mitti-400 mt-0.5">{lang.label}</p>
                      {language === lang.code && <Check className="w-4 h-4 text-mitti-500 mx-auto mt-2" />}
                    </motion.button>
                  ))}
                </div>
              </div>
            </SettingCard>

            {/* Notifications */}
            <SettingCard icon={Bell} title={t('settings.notifications')} color="bg-haldi-500">
              <Toggle label={t('settings.emailNotifications')} value={notifications} onChange={setNotifications} description={t('settings.emailNotifDesc')} />
            </SettingCard>

            {/* Sync */}
            <SettingCard icon={RefreshCw} title={t('settings.syncStatus')} color="bg-india-green-500">
              <Toggle label="Auto-sync" value={autoSync} onChange={setAutoSync} description="Sync on connection restore" />
              <div className={`p-4 rounded-xl border ${
                apiStatus === 'online' ? 'bg-india-green-500/10 border-india-green-500/20'
                : apiStatus === 'checking' ? 'bg-haldi-500/10 border-haldi-500/20'
                : 'bg-red-500/10 border-red-500/20'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    {apiStatus === 'online' ? <Check className="w-4 h-4 text-india-green-600" />
                    : apiStatus === 'checking' ? <RefreshCw className="w-4 h-4 text-haldi-600 animate-spin" />
                    : <X className="w-4 h-4 text-red-500" />}
                    <p className="font-medium text-mitti-900 dark:text-kora-100 text-sm">Backend API</p>
                  </div>
                  <button onClick={checkApiStatus} className="text-xs text-mitti-600 font-medium">{t('common.refresh')}</button>
                </div>
                <p className="text-xs text-mitti-500">{t('settings.lastSync')}: {lastSync.toLocaleTimeString()}</p>
              </div>
            </SettingCard>

            {/* Data */}
            <SettingCard icon={HardDrive} title={t('settings.dataManagement')} color="bg-terracotta-400">
              <div className="grid grid-cols-2 gap-3">
                <motion.button onClick={handleClearCache}
                  className="px-4 py-3 bg-red-500 text-white rounded-xl font-medium flex items-center justify-center space-x-2 text-sm hover:bg-red-600 transition-colors"
                  whileTap={{ scale: 0.97 }}>
                  <Trash2 className="w-4 h-4" /><span>{t('settings.clearCache')}</span>
                </motion.button>
                <motion.button onClick={handleExportData}
                  className="btn-mitti text-sm py-3 flex items-center justify-center space-x-2"
                  whileTap={{ scale: 0.97 }}>
                  <Download className="w-4 h-4" /><span>{t('settings.exportData')}</span>
                </motion.button>
              </div>
            </SettingCard>

            {/* About */}
            <SettingCard icon={Info} title={t('settings.about')} color="bg-mitti-500">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 village-card-subtle rounded-xl">
                  <p className="text-xs text-mitti-500">{t('settings.version')}</p>
                  <p className="text-lg font-bold text-mitti-900 dark:text-kora-100">2.0.0</p>
                </div>
                <div className="p-3 village-card-subtle rounded-xl">
                  <p className="text-xs text-mitti-500">{t('admin.role')}</p>
                  <p className="text-lg font-bold text-mitti-600 dark:text-mitti-400 capitalize">{user?.role || 'N/A'}</p>
                </div>
              </div>
              <div className="p-3 glass-saffron rounded-xl">
                <p className="text-sm text-mitti-800 dark:text-mitti-200">
                  <strong>{t('common.appName')}</strong> - Bridging rural citizens and government services through AI-powered governance assistance.
                </p>
              </div>
            </SettingCard>
          </div>

          <div className="mt-8 flex items-center justify-center pb-6">
            <motion.button onClick={handleSaveSettings}
              className="btn-mitti text-base md:text-lg px-6 md:px-8 py-3 md:py-4 flex items-center space-x-2"
              whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
              <Check className="w-6 h-6" /><span>{t('common.save')}</span>
            </motion.button>
          </div>
        </div>
      </div>
    </PageTransition>
  );
};

export default Settings;
