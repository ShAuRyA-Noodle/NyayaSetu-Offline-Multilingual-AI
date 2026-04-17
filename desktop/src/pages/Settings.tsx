import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import {
  Bell, HardDrive, Trash2, Download, Info, Check, X, RefreshCw, Lock, Shield, Monitor,
  Smartphone, Laptop, Eye, EyeOff, AlertCircle, Globe,
} from 'lucide-react';
import apiService from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import PageTransition from '../components/ui/PageTransition';
import ThemedSpinner from '../components/ui/ThemedSpinner';

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
    const data = { settings: { notifications, autoSync, language }, timestamp: new Date().toISOString(), version: '2.0.0' };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = `nyayasetu-settings-${Date.now()}.json`; a.click();
    URL.revokeObjectURL(url);
  };

  const getDeviceIcon = (d: string) => d === 'mobile' ? Smartphone : d === 'tablet' ? Monitor : Laptop;
  const formatDate = (d: string) => new Date(d).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

  // ─── Toggle ───
  const Toggle = ({ label, value, onChange, description }: any) => (
    <div className="flex items-center justify-between py-1">
      <div className="flex-1">
        <p className="text-sm font-medium text-kora-200">{label}</p>
        {description && <p className="text-xs text-slate-400/40 mt-0.5">{description}</p>}
      </div>
      <button onClick={() => onChange(!value)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 ${
          value ? 'bg-[#0D92F4]' : 'bg-white/[0.08]'
        }`}>
        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 shadow-sm ${
          value ? 'translate-x-6' : 'translate-x-1'
        }`} />
      </button>
    </div>
  );

  // ─── Password Input ───
  const PasswordInput = ({ label, value, onChange, show, onToggle, placeholder }: any) => (
    <div>
      <label className="block text-xs font-medium text-slate-400/50 mb-1.5 uppercase tracking-wider">{label}</label>
      <div className="relative group">
        <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400/40 group-focus-within:text-[#77CDFF] transition-colors" />
        <input type={show ? 'text' : 'password'} value={value} onChange={onChange} placeholder={placeholder} required
          className="w-full pl-10 pr-10 py-2.5 village-input text-sm" />
        <button type="button" onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500/30 hover:text-[#77CDFF] transition-colors">
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );

  // ─── Section Card ───
  const Section = ({ icon: Icon, title, children }: { icon: any; title: string; children: React.ReactNode }) => (
    <motion.div className="village-card p-5"
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
      <div className="flex items-center gap-3 mb-5">
        <div className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.06] flex items-center justify-center">
          <Icon className="w-4 h-4 text-slate-400/60" />
        </div>
        <h3 className="text-sm font-semibold text-kora-200 uppercase tracking-wider">{title}</h3>
      </div>
      <div className="space-y-4">{children}</div>
    </motion.div>
  );

  return (
    <PageTransition>
      <div className="p-4 md:p-6 lg:p-8 min-h-screen">
        <div className="max-w-2xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-2xl font-display font-bold text-kora-100 tracking-tight">{t('settings.title')}</h1>
            <p className="text-sm text-slate-400/40 mt-1">{t('settings.subtitle')}</p>
          </div>

          <AnimatePresence>
            {savedMessage && (
              <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                className="mb-6 p-3 rounded-xl bg-india-green-500/10 border border-india-green-500/20 flex items-center gap-2">
                <Check className="w-4 h-4 text-india-green-400" />
                <p className="text-sm text-india-green-400 font-medium">{savedMessage}</p>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="space-y-4">
            {/* Security */}
            <Section icon={Shield} title={t('settings.security')}>
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
                {passwordError && <div className="flex items-center gap-2 text-red-400 text-xs"><AlertCircle className="w-3.5 h-3.5" /><span>{passwordError}</span></div>}
                {passwordSuccess && <div className="flex items-center gap-2 text-india-green-400 text-xs"><Check className="w-3.5 h-3.5" /><span>{passwordSuccess}</span></div>}
                <button type="submit" disabled={passwordLoading || !passwordForm.current || !passwordForm.newPw || !passwordForm.confirm}
                  className="w-full py-2.5 rounded-xl text-sm font-semibold bg-white/[0.06] border border-white/[0.08] text-kora-200 hover:bg-white/[0.08] disabled:opacity-30 transition-all flex items-center justify-center gap-2">
                  {passwordLoading ? <ThemedSpinner size="sm" /> : <>{t('settings.updatePassword')}</>}
                </button>
              </form>
            </Section>

            {/* Sessions */}
            <Section icon={Monitor} title={t('settings.sessions')}>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-slate-400/40">{sessions.length} active session{sessions.length !== 1 ? 's' : ''}</p>
                <div className="flex gap-3">
                  <button onClick={loadSessions} className="text-xs text-slate-400/50 hover:text-[#77CDFF] font-medium transition-colors">{t('common.refresh')}</button>
                  {sessions.length > 1 && <button onClick={handleRevokeAll} className="text-xs text-red-400/60 hover:text-red-400 font-medium transition-colors">{t('settings.revokeAllSessions')}</button>}
                </div>
              </div>
              {sessionsLoading ? <div className="text-center py-4"><ThemedSpinner size="sm" /></div>
              : sessions.length === 0 ? <p className="text-slate-500/30 text-xs text-center py-4">No active sessions</p>
              : <div className="space-y-2">
                  {sessions.map((session, index) => {
                    const DeviceIcon = getDeviceIcon(session.device_type);
                    const isCurrent = index === 0;
                    return (
                      <div key={session.id} className={`p-3 rounded-xl border transition-colors ${
                        isCurrent ? 'bg-[#0D92F4]/[0.06] border-[#0D92F4]/15' : 'bg-white/[0.02] border-white/[0.04]'
                      }`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <DeviceIcon className="w-4 h-4 text-slate-400/50" />
                            <div>
                              <div className="flex items-center gap-2">
                                <p className="text-xs font-medium text-kora-200 capitalize">{session.device_type}</p>
                                {isCurrent && <span className="px-1.5 py-0.5 bg-[#0D92F4]/20 text-[#77CDFF] text-[10px] rounded-md font-semibold">{t('settings.currentSession')}</span>}
                              </div>
                              <p className="text-[10px] text-slate-500/30">{session.ip_address || 'Unknown IP'} · {formatDate(session.last_activity)}</p>
                            </div>
                          </div>
                          {!isCurrent && (
                            <button onClick={() => handleRevokeSession(session.id)} disabled={revokingId === session.id}
                              className="px-2.5 py-1 text-[11px] text-red-400/60 hover:text-red-400 hover:bg-red-500/[0.06] rounded-lg font-medium transition-colors disabled:opacity-30">
                              {revokingId === session.id ? '...' : t('settings.revokeSession')}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              }
            </Section>

            {/* Language */}
            <Section icon={Globe} title={t('settings.appearance')}>
              <div>
                <label className="block text-xs font-medium text-slate-400/50 mb-2 uppercase tracking-wider">{t('settings.interfaceLanguage')}</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { code: 'en', label: 'English' },
                    { code: 'hi', label: 'हिंदी' },
                  ].map((lang) => (
                    <button key={lang.code} onClick={() => handleLanguageChange(lang.code)}
                      className={`p-3 rounded-xl text-center transition-all duration-200 border ${
                        language === lang.code
                          ? 'border-[#0D92F4]/30 bg-[#0D92F4]/[0.08] text-kora-200'
                          : 'border-white/[0.04] text-slate-400/50 hover:border-white/[0.08]'
                      }`}>
                      <p className="font-bold text-base">{lang.label}</p>
                      {language === lang.code && <Check className="w-3.5 h-3.5 text-[#77CDFF] mx-auto mt-1.5" />}
                    </button>
                  ))}
                </div>
              </div>
            </Section>

            {/* Notifications */}
            <Section icon={Bell} title={t('settings.notifications')}>
              <Toggle label={t('settings.emailNotifications')} value={notifications} onChange={setNotifications} description={t('settings.emailNotifDesc')} />
            </Section>

            {/* Sync Status */}
            <Section icon={RefreshCw} title={t('settings.syncStatus')}>
              <Toggle label="Auto-sync" value={autoSync} onChange={setAutoSync} description="Sync on connection restore" />
              <div className={`p-3 rounded-xl border ${
                apiStatus === 'online' ? 'bg-india-green-500/[0.06] border-india-green-500/15'
                : apiStatus === 'checking' ? 'bg-haldi-500/[0.06] border-haldi-500/15'
                : 'bg-red-500/[0.06] border-red-500/15'
              }`}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    {apiStatus === 'online' ? <div className="w-2 h-2 bg-india-green-500 rounded-full" />
                    : apiStatus === 'checking' ? <RefreshCw className="w-3.5 h-3.5 text-haldi-400 animate-spin" />
                    : <X className="w-3.5 h-3.5 text-red-400" />}
                    <p className="text-xs font-medium text-kora-200">Backend API</p>
                  </div>
                  <button onClick={checkApiStatus} className="text-[11px] text-slate-400/40 font-medium hover:text-[#77CDFF] transition-colors">{t('common.refresh')}</button>
                </div>
                <p className="text-[10px] text-slate-500/30">{t('settings.lastSync')}: {lastSync.toLocaleTimeString()}</p>
              </div>
            </Section>

            {/* Data Management */}
            <Section icon={HardDrive} title={t('settings.dataManagement')}>
              <div className="grid grid-cols-2 gap-2">
                <button onClick={handleClearCache}
                  className="px-4 py-2.5 rounded-xl text-sm font-medium bg-red-500/[0.08] border border-red-500/15 text-red-400 hover:bg-red-500/15 transition-colors flex items-center justify-center gap-2">
                  <Trash2 className="w-3.5 h-3.5" />{t('settings.clearCache')}
                </button>
                <button onClick={handleExportData}
                  className="px-4 py-2.5 rounded-xl text-sm font-medium bg-white/[0.04] border border-white/[0.06] text-kora-200 hover:bg-white/[0.06] transition-colors flex items-center justify-center gap-2">
                  <Download className="w-3.5 h-3.5" />{t('settings.exportData')}
                </button>
              </div>
            </Section>

            {/* About */}
            <Section icon={Info} title={t('settings.about')}>
              <div className="grid grid-cols-2 gap-2">
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-[10px] text-slate-500/30 uppercase tracking-wider">{t('settings.version')}</p>
                  <p className="text-lg font-bold text-kora-100 mt-0.5">2.0.0</p>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-[10px] text-slate-500/30 uppercase tracking-wider">{t('admin.role')}</p>
                  <p className="text-lg font-bold text-[#77CDFF] capitalize mt-0.5">{user?.role || 'N/A'}</p>
                </div>
              </div>
            </Section>
          </div>

          {/* Save button */}
          <div className="mt-8 flex items-center justify-center pb-8">
            <motion.button onClick={handleSaveSettings}
              className="btn-mitti text-sm px-8 py-3 flex items-center gap-2"
              whileTap={{ scale: 0.97 }}>
              <Check className="w-4 h-4" />{t('common.save')}
            </motion.button>
          </div>
        </div>
      </div>
    </PageTransition>
  );
};

export default Settings;
