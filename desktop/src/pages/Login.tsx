import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { User, Lock, Mail, Phone, MapPin, Eye, EyeOff, Shield, KeyRound, ArrowRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import apiService from '../services/api';
import AshokaChakra from '../components/decorative/AshokaChakra';
import ThemedSpinner from '../components/ui/ThemedSpinner';

// Defined OUTSIDE component to avoid remount on every keystroke
const InputField = ({ icon: Icon, ...props }: any) => (
  <div className="relative group">
    <Icon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-400/50 dark:text-slate-400 transition-colors group-focus-within:text-slate-400 dark:group-focus-within:text-slate-400" />
    <input {...props} className="w-full pl-11 pr-4 py-3 village-input text-sm" />
  </div>
);

const Login: React.FC = () => {
  const { login } = useAuth();
  const { t } = useTranslation();
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [loginData, setLoginData] = useState({ username: '', password: '' });
  const [registerData, setRegisterData] = useState({
    username: '', email: '', password: '', phone: '', location: '', preferred_language: 'en',
  });

  const [selectedRole, setSelectedRole] = useState<'citizen' | 'officer'>('citizen');
  const [officerCode, setOfficerCode] = useState('');
  const [codeValidation, setCodeValidation] = useState<{ valid?: boolean; department?: string; designation?: string; message?: string } | null>(null);
  const [validatingCode, setValidatingCode] = useState(false);

  const validateCode = useCallback(async (code: string) => {
    if (code.length < 4) { setCodeValidation(null); return; }
    setValidatingCode(true);
    try {
      const result = await apiService.validateOfficerCode(code);
      setCodeValidation(result);
    } catch {
      setCodeValidation({ valid: false, message: 'Failed to validate code' });
    } finally { setValidatingCode(false); }
  }, []);

  useEffect(() => {
    if (selectedRole !== 'officer' || !officerCode) { setCodeValidation(null); return; }
    const timer = setTimeout(() => validateCode(officerCode), 500);
    return () => clearTimeout(timer);
  }, [officerCode, selectedRole, validateCode]);

  const passwordStrength = useMemo(() => {
    const pw = isLogin ? '' : registerData.password;
    if (!pw) return { score: 0, label: '', color: '' };
    let score = 0;
    if (pw.length >= 8) score++;
    if (pw.length >= 12) score++;
    if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score++;
    if (/\d/.test(pw)) score++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(pw)) score++;
    if (score <= 1) return { score, label: 'Weak', color: 'bg-red-500' };
    if (score <= 2) return { score, label: 'Fair', color: 'bg-haldi-500' };
    if (score <= 3) return { score, label: 'Good', color: 'bg-mitti-500' };
    return { score, label: 'Strong', color: 'bg-india-green-500' };
  }, [isLogin, registerData.password]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await apiService.login(loginData.username, loginData.password);
      login(data.access_token, data.user);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || t('login.loginError'));
    } finally { setLoading(false); }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    if (selectedRole === 'officer') {
      if (!officerCode || !codeValidation?.valid) { setError(t('login.codeInvalid')); setLoading(false); return; }
    }
    try {
      await apiService.register({
        ...registerData,
        role: selectedRole,
        officer_code: selectedRole === 'officer' ? officerCode : undefined,
      });
      const data = await apiService.login(registerData.username, registerData.password);
      login(data.access_token, data.user);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || t('login.registerError'));
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-[#060B18] flex" data-lenis-prevent>

      {/* ─── Animated background mesh ─── */}
      <div className="absolute inset-0 overflow-hidden">
        {/* Ambient orbs */}
        <div className="aurora-orb w-[600px] h-[600px] bg-[#0D92F4]/15 top-[-10%] left-[-10%]" style={{ animationDelay: '0s' }} />
        <div className="aurora-orb w-[500px] h-[500px] bg-[#F95454]/10 bottom-[-15%] right-[-5%]" style={{ animationDelay: '-7s' }} />
        <div className="aurora-orb w-[400px] h-[400px] bg-[#77CDFF]/8 top-[40%] left-[60%]" style={{ animationDelay: '-14s' }} />
        {/* Grid pattern */}
        <div className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `linear-gradient(rgba(13,146,244,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(13,146,244,0.3) 1px, transparent 1px)`,
            backgroundSize: '60px 60px',
          }}
        />
        {/* Grain */}
        <div className="absolute inset-0 grain-overlay" />
      </div>

      {/* ─── Left Hero ─── */}
      <div className="hidden lg:flex flex-1 relative items-center justify-center p-12">
        <motion.div
          className="relative z-10 max-w-lg"
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: [0.25, 0.1, 0.25, 1] }}
        >
          {/* Ashoka Chakra */}
          <motion.div
            className="mb-8"
            initial={{ opacity: 0, rotate: -180 }}
            animate={{ opacity: 1, rotate: 0 }}
            transition={{ duration: 1.2, ease: [0.25, 0.1, 0.25, 1] }}
          >
            <AshokaChakra size={56} spinning />
          </motion.div>

          {/* Title */}
          <motion.h1
            className="text-6xl xl:text-7xl font-display font-bold tracking-tight mb-2"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2 }}
          >
            <span className="text-gradient-gold">Nyaya</span>
            <span className="text-kora-100">Setu</span>
          </motion.h1>

          {/* Devanagari */}
          <motion.p
            className="font-devanagari text-2xl text-slate-400/60 mb-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            न्यायसेतु
          </motion.p>

          {/* Divider */}
          <motion.div
            className="w-16 h-[2px] bg-gradient-to-r from-mitti-500 to-transparent mb-6"
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            style={{ transformOrigin: 'left' }}
          />

          {/* Subtitle */}
          <motion.p
            className="text-lg text-kora-300/50 font-light leading-relaxed max-w-sm"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
          >
            AI-powered citizen governance platform bridging rural India with intelligent public services
          </motion.p>

          {/* Feature pills */}
          <motion.div
            className="flex flex-wrap gap-2 mt-8"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.8 }}
          >
            {['12 Languages', 'Voice Interface', 'AI-Powered', 'Offline Ready'].map((tag, i) => (
              <span key={tag} className="px-3 py-1.5 text-xs font-medium rounded-full border border-[#0D92F4]/15 text-[#77CDFF]/50 bg-[#0D92F4]/5"
                style={{ animationDelay: `${0.9 + i * 0.1}s` }}>
                {tag}
              </span>
            ))}
          </motion.div>
        </motion.div>
      </div>

      {/* ─── Right Form Panel ─── */}
      <div className="w-full lg:w-[480px] xl:w-[520px] flex-shrink-0 relative z-10 flex items-center justify-center px-5 py-8 sm:p-6 lg:p-10">

        {/* Glass panel background */}
        <div className="absolute inset-0 glass-surface-strong border-l border-white/[0.04]" />

        <motion.div
          className="relative z-10 w-full max-w-sm"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
        >
          {/* Mobile branding */}
          <div className="text-center mb-8 lg:hidden">
            <div className="inline-block mb-3">
              <AshokaChakra size={44} spinning />
            </div>
            <h1 className="text-2xl font-display font-bold text-gradient-gold">NyayaSetu</h1>
            <p className="font-devanagari text-base text-slate-400/50 mt-1">न्यायसेतु</p>
          </div>

          {/* Welcome text */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-kora-100 mb-1">
              {isLogin ? t('login.loginTab') : t('login.registerTab')}
            </h2>
            <p className="text-sm text-slate-400/60">
              {isLogin ? 'Welcome back to NyayaSetu' : 'Create your account to get started'}
            </p>
          </div>

          {/* Tab switcher */}
          <div className="flex mb-6 rounded-xl p-1 bg-white/[0.04] border border-white/[0.06]">
            {[{ key: true, label: t('login.loginTab') }, { key: false, label: t('login.registerTab') }].map((tab) => (
              <button key={String(tab.key)}
                onClick={() => { setIsLogin(tab.key); setError(''); }}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-all duration-200 ${
                  isLogin === tab.key
                    ? 'bg-[#0D92F4] text-white shadow-lg shadow-[#0D92F4]/20'
                    : 'text-slate-400/60 hover:text-slate-400/80'
                }`}
              >{tab.label}</button>
            ))}
          </div>

          {/* Error */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-4 overflow-hidden"
              >
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ─── Login Form ─── */}
          {isLogin ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400/60 mb-2 uppercase tracking-wider">{t('login.username')}</label>
                <InputField icon={User} type="text" value={loginData.username}
                  onChange={(e: any) => setLoginData({ ...loginData, username: e.target.value })}
                  placeholder={t('login.username')} required />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400/60 mb-2 uppercase tracking-wider">{t('login.password')}</label>
                <div className="relative group">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-400/50 dark:text-slate-400 transition-colors group-focus-within:text-slate-400 dark:group-focus-within:text-slate-400" />
                  <input type={showPassword ? 'text' : 'password'} value={loginData.password}
                    onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                    className="w-full pl-11 pr-11 py-3 village-input text-sm" placeholder={t('login.password')} required />
                  <button type="button" onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400/50 hover:text-slate-400 transition-colors">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <motion.button type="submit" disabled={loading}
                className="w-full btn-mitti flex items-center justify-center gap-2 mt-6 disabled:opacity-50"
                whileTap={{ scale: 0.98 }}>
                {loading ? <ThemedSpinner size="sm" /> : <>
                  {t('login.loginButton')}
                  <ArrowRight className="w-4 h-4" />
                </>}
              </motion.button>
            </form>
          ) : (
            /* ─── Register Form ─── */
            <form onSubmit={handleRegister} className="space-y-3.5">
              {/* Role selector */}
              <div>
                <label className="block text-xs font-medium text-slate-400/60 mb-2 uppercase tracking-wider">{t('login.iAmA')}</label>
                <div className="grid grid-cols-2 gap-2">
                  <button type="button" onClick={() => { setSelectedRole('citizen'); setOfficerCode(''); setCodeValidation(null); }}
                    className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 border ${
                      selectedRole === 'citizen'
                        ? 'border-[#0D92F4]/30 bg-[#0D92F4]/10 text-[#77CDFF]'
                        : 'border-white/[0.06] text-slate-400/50 hover:border-white/[0.1]'
                    }`}>
                    <User className="w-4 h-4" />{t('login.citizen')}
                  </button>
                  <button type="button" onClick={() => setSelectedRole('officer')}
                    className={`flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 border ${
                      selectedRole === 'officer'
                        ? 'border-neel-500/50 bg-[#77CDFF]/8 text-neel-400'
                        : 'border-white/[0.06] text-slate-400/50 hover:border-white/[0.1]'
                    }`}>
                    <Shield className="w-4 h-4" />{t('login.officer')}
                  </button>
                </div>
              </div>

              {/* Officer code */}
              <AnimatePresence>
                {selectedRole === 'officer' && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    <label className="block text-xs font-medium text-slate-400/60 mb-2 uppercase tracking-wider">{t('login.officerCode')} *</label>
                    <div className="relative">
                      <KeyRound className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-neel-400/70" />
                      <input type="text" value={officerCode} onChange={(e) => setOfficerCode(e.target.value.toUpperCase())}
                        className={`w-full pl-11 pr-4 py-3 village-input text-sm font-mono tracking-widest ${
                          codeValidation?.valid ? '!border-india-green-500/50' : codeValidation?.valid === false ? '!border-red-500/50' : ''
                        }`}
                        placeholder={t('login.enterCode')} maxLength={8} />
                      {validatingCode && <div className="absolute right-3 top-1/2 -translate-y-1/2"><ThemedSpinner size="sm" /></div>}
                    </div>
                    {codeValidation && (
                      <div className={`mt-2 p-2.5 rounded-lg text-xs ${
                        codeValidation.valid
                          ? 'bg-india-green-500/10 border border-india-green-500/20 text-india-green-400'
                          : 'bg-red-500/10 border border-red-500/20 text-red-400'
                      }`}>
                        {codeValidation.valid
                          ? <span>Dept: <strong>{codeValidation.department}</strong>{codeValidation.designation && ` · ${codeValidation.designation}`}</span>
                          : <span>{codeValidation.message || t('login.codeInvalid')}</span>}
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>

              <div>
                <label className="block text-xs font-medium text-slate-400/60 mb-2 uppercase tracking-wider">{t('login.username')} *</label>
                <InputField icon={User} type="text" value={registerData.username}
                  onChange={(e: any) => setRegisterData({ ...registerData, username: e.target.value })}
                  placeholder={t('login.username')} required minLength={3} />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400/60 mb-2 uppercase tracking-wider">{t('login.email')} *</label>
                <InputField icon={Mail} type="email" value={registerData.email}
                  onChange={(e: any) => setRegisterData({ ...registerData, email: e.target.value })}
                  placeholder="email@example.com" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400/60 mb-2 uppercase tracking-wider">{t('login.password')} *</label>
                <div className="relative group">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-400/50 dark:text-slate-400 transition-colors group-focus-within:text-slate-400 dark:group-focus-within:text-slate-400" />
                  <input type={showPassword ? 'text' : 'password'} value={registerData.password}
                    onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                    className="w-full pl-11 pr-11 py-3 village-input text-sm" placeholder="Min 8 characters" required minLength={8} />
                  <button type="button" onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400/50 hover:text-slate-400 transition-colors">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {registerData.password && (
                  <div className="mt-2">
                    <div className="flex gap-1 mb-1">
                      {[1, 2, 3, 4, 5].map((level) => (
                        <div key={level} className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                          level <= passwordStrength.score ? passwordStrength.color : 'bg-white/[0.06]'
                        }`} />
                      ))}
                    </div>
                    <p className="text-[11px] text-slate-400/50">{passwordStrength.label}</p>
                  </div>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-slate-400/60 mb-2 uppercase tracking-wider">{t('login.location')}</label>
                  <InputField icon={MapPin} type="text" value={registerData.location}
                    onChange={(e: any) => setRegisterData({ ...registerData, location: e.target.value })}
                    placeholder="City, State" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400/60 mb-2 uppercase tracking-wider">Phone</label>
                  <InputField icon={Phone} type="tel" value={registerData.phone}
                    onChange={(e: any) => setRegisterData({ ...registerData, phone: e.target.value })}
                    placeholder="+91-XXXXX" />
                </div>
              </div>
              <motion.button type="submit"
                disabled={loading || (selectedRole === 'officer' && !codeValidation?.valid)}
                className={`w-full flex items-center justify-center gap-2 mt-4 disabled:opacity-50 ${selectedRole === 'officer' ? 'btn-neel' : 'btn-mitti'}`}
                whileTap={{ scale: 0.98 }}>
                {loading ? <ThemedSpinner size="sm" /> : <>
                  {t('login.createAccount')}
                  <ArrowRight className="w-4 h-4" />
                </>}
              </motion.button>
            </form>
          )}

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-[11px] text-slate-500/30">
              NyayaSetu v2.0 · AI-Powered Governance
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Login;
