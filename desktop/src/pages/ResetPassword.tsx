import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Lock, Eye, EyeOff, ArrowLeft, ArrowRight, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import AshokaChakra from '../components/decorative/AshokaChakra';
import ThemedSpinner from '../components/ui/ThemedSpinner';
import apiService from '../services/api';

/**
 * ResetPassword — completes password reset flow.
 * Token is read from `:token` URL param. On success, redirects to /login.
 * Mirrors the password-strength meter from Login.tsx register tab.
 */
const ResetPassword: React.FC = () => {
  const { t } = useTranslation();
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();

  const [password, setPassword] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const passwordStrength = useMemo(() => {
    if (!password) return { score: 0, label: '', color: '' };
    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
    if (/\d/.test(password)) score++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;
    if (score <= 1) return { score, label: 'Weak', color: 'bg-red-500' };
    if (score <= 2) return { score, label: 'Fair', color: 'bg-haldi-500' };
    if (score <= 3) return { score, label: 'Good', color: 'bg-mitti-500' };
    return { score, label: 'Strong', color: 'bg-india-green-500' };
  }, [password]);

  const tokenMissing = !token || token.length < 8;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (tokenMissing) {
      setError(t('resetPassword.invalidTokenMsg', 'Reset link is invalid or has expired.'));
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirmPwd) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await apiService.resetPassword(token!, password);
      toast.success(
        t('resetPassword.successMsg', 'Password reset successful. Please log in.')
      );
      navigate('/login', { replace: true });
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          t('resetPassword.invalidTokenMsg', 'Reset link is invalid or has expired.')
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-[#060B18] flex items-center justify-center p-5" data-lenis-prevent>
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="aurora-orb w-[600px] h-[600px] bg-[#0D92F4]/15 top-[-10%] left-[-10%]" />
        <div className="aurora-orb w-[500px] h-[500px] bg-[#F95454]/10 bottom-[-15%] right-[-5%]" style={{ animationDelay: '-7s' }} />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `linear-gradient(rgba(13,146,244,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(13,146,244,0.3) 1px, transparent 1px)`,
            backgroundSize: '60px 60px',
          }}
        />
        <div className="absolute inset-0 grain-overlay" />
      </div>

      <motion.div
        className="relative z-10 w-full max-w-md"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <div className="glass-surface-strong rounded-2xl border border-white/[0.04] p-7 sm:p-8">
          <div className="text-center mb-6">
            <div className="inline-block mb-3">
              <AshokaChakra size={44} />
            </div>
            <h1 className="text-2xl font-display font-bold text-gradient-gold">NyayaSetu</h1>
            <p className="font-devanagari text-sm text-slate-400/50 mt-1">न्यायसेतु</p>
          </div>

          <div className="mb-6 text-center">
            <h2 className="text-xl font-bold text-kora-100 mb-1">
              {t('resetPassword.title', 'Reset Password')}
            </h2>
            <p className="text-xs text-slate-400/70 leading-relaxed">
              {t('resetPassword.subtitle', 'Choose a strong new password for your account.')}
            </p>
          </div>

          {tokenMissing && (
            <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-red-400">
                {t('resetPassword.invalidTokenMsg', 'Reset link is invalid or has expired.')}
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400/60 mb-2 uppercase tracking-wider">
                {t('resetPassword.passwordLabel', 'New Password')}
              </label>
              <div className="relative group">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-400/50" />
                <input
                  type={showPwd ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 8 characters"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  className="w-full pl-11 pr-11 py-3 village-input text-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowPwd((v) => !v)}
                  aria-label={showPwd ? 'Hide password' : 'Show password'}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400/50 hover:text-slate-300 transition-colors"
                >
                  {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {password && (
                <div className="mt-2">
                  <div className="flex gap-1 mb-1">
                    {[1, 2, 3, 4, 5].map((level) => (
                      <div
                        key={level}
                        className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                          level <= passwordStrength.score ? passwordStrength.color : 'bg-white/[0.06]'
                        }`}
                      />
                    ))}
                  </div>
                  <p className="text-[11px] text-slate-400/60">{passwordStrength.label}</p>
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400/60 mb-2 uppercase tracking-wider">
                {t('resetPassword.confirmLabel', 'Confirm Password')}
              </label>
              <div className="relative group">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-400/50" />
                <input
                  type={showPwd ? 'text' : 'password'}
                  value={confirmPwd}
                  onChange={(e) => setConfirmPwd(e.target.value)}
                  placeholder="Repeat password"
                  required
                  autoComplete="new-password"
                  className={`w-full pl-11 pr-4 py-3 village-input text-sm ${
                    confirmPwd && confirmPwd !== password ? '!border-red-500/50' : ''
                  }`}
                />
              </div>
              {confirmPwd && confirmPwd !== password && (
                <p className="text-[11px] text-red-400 mt-1">Passwords do not match</p>
              )}
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            <motion.button
              type="submit"
              disabled={loading || tokenMissing || !password || password !== confirmPwd}
              whileTap={{ scale: 0.98 }}
              className="w-full btn-mitti flex items-center justify-center gap-2 mt-2 disabled:opacity-50"
            >
              {loading ? (
                <ThemedSpinner size="sm" />
              ) : (
                <>
                  {t('resetPassword.submitBtn', 'Reset Password')}
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </motion.button>
          </form>

          <div className="mt-6 pt-5 border-t border-white/[0.04] text-center">
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-[#77CDFF] transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              {t('forgotPassword.backToLogin', 'Back to login')}
            </Link>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default ResetPassword;
