import React, { useState, useMemo, useEffect, useCallback, Suspense } from 'react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { User, Lock, Mail, Phone, MapPin, LogIn, UserPlus, Eye, EyeOff, Shield, KeyRound } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import apiService from '../services/api';
import AshokaChakra from '../components/decorative/AshokaChakra';
import WarliIllustration from '../components/decorative/WarliIllustration';
import RangoliPattern from '../components/decorative/RangoliPattern';
import GlobeParticles from '../components/decorative/GlobeParticles';
import ThemedSpinner from '../components/ui/ThemedSpinner';
import TextReveal from '../components/ui/TextReveal';

const LoginScene = React.lazy(() => import('../components/three/LoginScene'));

const Login: React.FC = () => {
  const { login } = useAuth();
  const { t } = useTranslation();
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [use3D, setUse3D] = useState(false);

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
      if (!officerCode) { setError(t('login.codeInvalid')); setLoading(false); return; }
      if (!codeValidation?.valid) { setError(t('login.codeInvalid')); setLoading(false); return; }
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

  const inputClass = "w-full pl-10 pr-4 py-3 village-input";
  const inputClassRight = "w-full pl-10 pr-12 py-3 village-input";

  return (
    <div className="min-h-screen relative overflow-x-hidden overflow-y-auto bg-kora dark:bg-night-bg" data-lenis-prevent>
      {/* Background: Either 3D scene or globe particles */}
      {use3D ? (
        <Suspense fallback={null}>
          <LoginScene />
        </Suspense>
      ) : (
        <>
          {/* Village gradient background */}
          <div className="absolute inset-0 bg-gradient-village dark:bg-gradient-night" />
          {/* Globe particle effect */}
          <GlobeParticles className="z-[1]" />
          {/* Subtle kolam pattern */}
          <div className="absolute inset-0 z-[2]">
            <RangoliPattern opacity={0.03} />
          </div>
          {/* Grain */}
          <div className="absolute inset-0 z-[3] grain-overlay" />
        </>
      )}

      {/* 3D toggle */}
      <button
        onClick={() => setUse3D(!use3D)}
        className="absolute top-4 right-4 z-20 px-3 py-1.5 text-xs font-medium rounded-lg bg-kora-100/80 dark:bg-night-card/80 border border-mitti-200/30 dark:border-night-border text-mitti-500 dark:text-mitti-400 hover:bg-mitti-100/60 transition-colors backdrop-blur-sm"
      >
        {use3D ? 'Village' : '3D'} View
      </button>

      {/* Content — Two column on desktop */}
      <div className="relative z-10 min-h-screen flex items-center justify-center p-4 lg:p-8">
        <div className="w-full max-w-5xl flex flex-col lg:flex-row items-center gap-8 lg:gap-16">

          {/* Left Hero (hidden on mobile) */}
          <motion.div
            className="hidden lg:flex flex-col flex-1 max-w-lg"
            initial={{ opacity: 0, x: -40 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, ease: [0.25, 0.1, 0.25, 1] }}
          >
            <div className="mb-6">
              <AshokaChakra size={48} spinning />
            </div>

            <h1 className="font-display text-hero-sm xl:text-hero text-mitti-900 dark:text-kora-100 mb-3">
              NyayaSetu
            </h1>

            <p className="font-devanagari text-3xl text-mitti-500 dark:text-mitti-300 mb-4">
              न्यायसेतु
            </p>

            <TextReveal
              as="p"
              className="text-lg text-mitti-600/80 dark:text-mitti-400/80 font-light leading-relaxed mb-8"
              splitBy="word"
              delay={0.3}
              stagger={0.04}
            >
              Bridging the gap between rural citizens and governance with AI-powered intelligence
            </TextReveal>

            <div className="kolam-divider w-32 mb-8" />

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.15 }}
              transition={{ delay: 0.8 }}
            >
              <WarliIllustration variant="panchayat" size={280} />
            </motion.div>
          </motion.div>

          {/* Right Form */}
          <motion.div
            className="w-full max-w-md lg:flex-shrink-0"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
          >
            {/* Mobile logo */}
            <motion.div
              className="text-center mb-6 lg:hidden"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              <div className="inline-block mb-3">
                <AshokaChakra size={48} spinning />
              </div>
              <h1 className="text-2xl font-display font-bold text-gradient-mitti">
                {t('common.appName')}
              </h1>
              <p className="font-devanagari text-lg text-mitti-500 dark:text-mitti-300 mt-1">न्यायसेतु</p>
              <div className="kolam-divider w-24 mx-auto mt-3" />
            </motion.div>

            {/* Form Card */}
            <div className="village-card border border-mitti-200/40 dark:border-night-border/60 shadow-elevated grain-overlay p-5 sm:p-7 md:p-8">
              {/* Tabs */}
              <div className="flex mb-6 village-card-subtle p-1 rounded-xl relative z-10">
                <button
                  onClick={() => { setIsLogin(true); setError(''); }}
                  className={`flex-1 py-2.5 rounded-lg font-semibold text-sm transition-all ${
                    isLogin
                      ? 'bg-mitti-500 text-white shadow-mitti'
                      : 'text-mitti-600 dark:text-mitti-400 hover:text-mitti-800'
                  }`}
                >{t('login.loginTab')}</button>
                <button
                  onClick={() => { setIsLogin(false); setError(''); }}
                  className={`flex-1 py-2.5 rounded-lg font-semibold text-sm transition-all ${
                    !isLogin
                      ? 'bg-mitti-500 text-white shadow-mitti'
                      : 'text-mitti-600 dark:text-mitti-400 hover:text-mitti-800'
                  }`}
                >{t('login.registerTab')}</button>
              </div>

              <div style={{
                display: 'grid',
                gridTemplateRows: error ? '1fr' : '0fr',
                transition: 'grid-template-rows 0.22s cubic-bezier(0.25, 1, 0.5, 1)',
              }}>
                <div className="overflow-hidden">
                  <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl relative z-10"
                    style={{ opacity: error ? 1 : 0, transition: 'opacity 0.15s ease' }}>
                    <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                  </div>
                </div>
              </div>

              <div className="relative z-10">
                {isLogin ? (
                  <form onSubmit={handleLogin} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">{t('login.username')}</label>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 -translate-y-1/2 text-mitti-400 w-5 h-5" />
                        <input type="text" value={loginData.username} onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                          className={inputClass} placeholder={t('login.username')} required />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">{t('login.password')}</label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-mitti-400 w-5 h-5" />
                        <input type={showPassword ? 'text' : 'password'} value={loginData.password} onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                          className={inputClassRight} placeholder={t('login.password')} required />
                        <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-mitti-400 hover:text-mitti-600 transition-colors">
                          {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                        </button>
                      </div>
                    </div>
                    <motion.button
                      type="submit" disabled={loading}
                      className="w-full btn-mitti flex items-center justify-center disabled:opacity-50"
                      whileHover={{ scale: loading ? 1 : 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      {loading ? <ThemedSpinner size="sm" /> : <><LogIn className="w-5 h-5 mr-2" />{t('login.loginButton')}</>}
                    </motion.button>
                  </form>
                ) : (
                  <form onSubmit={handleRegister} className="space-y-4">
                    {/* Role Selector */}
                    <div>
                      <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">{t('login.iAmA')}</label>
                      <div className="grid grid-cols-2 gap-3">
                        <motion.button type="button" onClick={() => { setSelectedRole('citizen'); setOfficerCode(''); setCodeValidation(null); }}
                          className={`flex items-center justify-center space-x-2 py-3 rounded-xl border-2 font-semibold transition-all ${
                            selectedRole === 'citizen'
                              ? 'border-mitti-500 bg-mitti-500/10 text-mitti-700 dark:text-mitti-400'
                              : 'border-mitti-200/30 dark:border-night-border text-mitti-500 dark:text-mitti-400 hover:border-mitti-300'
                          }`}
                          whileTap={{ scale: 0.97 }}>
                          <User className="w-5 h-5" /><span>{t('login.citizen')}</span>
                        </motion.button>
                        <motion.button type="button" onClick={() => setSelectedRole('officer')}
                          className={`flex items-center justify-center space-x-2 py-3 rounded-xl border-2 font-semibold transition-all ${
                            selectedRole === 'officer'
                              ? 'border-neel-500 bg-neel-500/10 text-neel-600 dark:text-neel-400'
                              : 'border-mitti-200/30 dark:border-night-border text-mitti-500 dark:text-mitti-400 hover:border-neel-300'
                          }`}
                          whileTap={{ scale: 0.97 }}>
                          <Shield className="w-5 h-5" /><span>{t('login.officer')}</span>
                        </motion.button>
                      </div>
                    </div>

                    {/* Officer Code */}
                    <div style={{
                      display: 'grid',
                      gridTemplateRows: selectedRole === 'officer' ? '1fr' : '0fr',
                      transition: 'grid-template-rows 0.25s cubic-bezier(0.25, 1, 0.5, 1)',
                    }}>
                      <div className="overflow-hidden">
                      <div style={{ opacity: selectedRole === 'officer' ? 1 : 0, transition: 'opacity 0.2s ease' }}>
                        <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">{t('login.officerCode')} *</label>
                        <div className="relative">
                          <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 text-neel-400 w-5 h-5" />
                          <input type="text" value={officerCode} onChange={(e) => setOfficerCode(e.target.value.toUpperCase())}
                            className={`${inputClass} font-mono tracking-widest ${
                              codeValidation?.valid ? '!border-india-green-500 !ring-india-green-500/50' : codeValidation?.valid === false ? '!border-red-500' : ''
                            }`}
                            placeholder={t('login.enterCode')} maxLength={8} />
                          {validatingCode && <div className="absolute right-3 top-1/2 -translate-y-1/2"><ThemedSpinner size="sm" /></div>}
                        </div>
                        {codeValidation && (
                          <div className={`mt-2 p-2.5 rounded-xl text-sm ${
                            codeValidation.valid
                              ? 'bg-india-green-500/10 border border-india-green-500/20 text-india-green-700 dark:text-india-green-400'
                              : 'bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400'
                          }`}>
                            {codeValidation.valid
                              ? <span>Department: <strong>{codeValidation.department}</strong>{codeValidation.designation && ` | ${codeValidation.designation}`}</span>
                              : <span>{codeValidation.message || t('login.codeInvalid')}</span>}
                          </div>
                        )}
                      </div>
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">{t('login.username')} *</label>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 -translate-y-1/2 text-mitti-400 w-5 h-5" />
                        <input type="text" value={registerData.username} onChange={(e) => setRegisterData({ ...registerData, username: e.target.value })}
                          className={inputClass} placeholder={t('login.username')} required minLength={3} />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">{t('login.email')} *</label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-mitti-400 w-5 h-5" />
                        <input type="email" value={registerData.email} onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                          className={inputClass} placeholder="email@example.com" required />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">{t('login.password')} *</label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-mitti-400 w-5 h-5" />
                        <input type={showPassword ? 'text' : 'password'} value={registerData.password} onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                          className={inputClassRight} placeholder="Min 8 chars" required minLength={8} />
                        <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-mitti-400 hover:text-mitti-600 transition-colors">
                          {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                        </button>
                      </div>
                      {registerData.password && (
                        <div className="mt-2">
                          <div className="flex gap-1 mb-1">
                            {[1, 2, 3, 4, 5].map((level) => (
                              <div key={level} className={`h-1.5 flex-1 rounded-full transition-colors ${level <= passwordStrength.score ? passwordStrength.color : 'bg-mitti-200 dark:bg-night-border'}`} />
                            ))}
                          </div>
                          <p className="text-xs text-mitti-500">{passwordStrength.label}</p>
                        </div>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">{t('login.location')}</label>
                        <div className="relative">
                          <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 text-mitti-400 w-4 h-4" />
                          <input type="text" value={registerData.location} onChange={(e) => setRegisterData({ ...registerData, location: e.target.value })}
                            className={inputClass} placeholder="City, State" />
                        </div>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-mitti-700 dark:text-mitti-300 mb-2">Phone</label>
                        <div className="relative">
                          <Phone className="absolute left-3 top-1/2 -translate-y-1/2 text-mitti-400 w-4 h-4" />
                          <input type="tel" value={registerData.phone} onChange={(e) => setRegisterData({ ...registerData, phone: e.target.value })}
                            className={inputClass} placeholder="+91-XXXXX" />
                        </div>
                      </div>
                    </div>
                    <motion.button
                      type="submit" disabled={loading || (selectedRole === 'officer' && !codeValidation?.valid)}
                      className={`w-full flex items-center justify-center disabled:opacity-50 ${selectedRole === 'officer' ? 'btn-neel' : 'btn-mitti'}`}
                      whileHover={{ scale: loading ? 1 : 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      {loading ? <ThemedSpinner size="sm" /> : <><UserPlus className="w-5 h-5 mr-2" />{t('login.createAccount')}</>}
                    </motion.button>
                  </form>
                )}
              </div>

            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Login;
