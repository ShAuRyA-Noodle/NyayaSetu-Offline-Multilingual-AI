import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, ArrowRight, CheckCircle } from 'lucide-react';
import AshokaChakra from '../components/decorative/AshokaChakra';
import ThemedSpinner from '../components/ui/ThemedSpinner';
import apiService from '../services/api';

/**
 * ForgotPassword — citizen-facing password recovery initiation.
 *
 * Always shows the same success message (no enumeration of accounts).
 * Mirrors the visual language of Login.tsx (deep navy, glass surfaces,
 * Ashoka chakra, bilingual subtitle).
 */
const ForgotPassword: React.FC = () => {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || loading) return;
    setLoading(true);
    try {
      await apiService.forgotPassword(email.trim());
    } catch {
      // Intentionally swallow — never leak whether the email exists
    } finally {
      setLoading(false);
      setSubmitted(true);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-[#060B18] flex items-center justify-center p-5" data-lenis-prevent>
      {/* Animated background mesh */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="aurora-orb w-[600px] h-[600px] bg-[#0D92F4]/15 top-[-10%] left-[-10%]" style={{ animationDelay: '0s' }} />
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
          {/* Branding */}
          <div className="text-center mb-6">
            <div className="inline-block mb-3">
              <AshokaChakra size={44} />
            </div>
            <h1 className="text-2xl font-display font-bold text-gradient-gold">NyayaSetu</h1>
            <p className="font-devanagari text-sm text-slate-400/50 mt-1">न्यायसेतु</p>
          </div>

          {!submitted ? (
            <>
              <div className="mb-6 text-center">
                <h2 className="text-xl font-bold text-kora-100 mb-1">
                  {t('forgotPassword.title', 'Forgot Password?')}
                </h2>
                <p className="text-xs text-slate-400/70 leading-relaxed">
                  {t(
                    'forgotPassword.subtitle',
                    "Enter your email — we'll send a reset link if an account exists."
                  )}
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400/60 mb-2 uppercase tracking-wider">
                    {t('forgotPassword.emailLabel', 'Email Address')}
                  </label>
                  <div className="relative group">
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-400/50" />
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="email@example.com"
                      required
                      autoComplete="email"
                      className="w-full pl-11 pr-4 py-3 village-input text-sm"
                    />
                  </div>
                </div>

                <motion.button
                  type="submit"
                  disabled={loading || !email.trim()}
                  whileTap={{ scale: 0.98 }}
                  className="w-full btn-mitti flex items-center justify-center gap-2 mt-2 disabled:opacity-50"
                >
                  {loading ? (
                    <ThemedSpinner size="sm" />
                  ) : (
                    <>
                      {t('forgotPassword.submitBtn', 'Send Reset Link')}
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </motion.button>
              </form>
            </>
          ) : (
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4 }}
              className="text-center py-4"
              role="status"
              aria-live="polite"
            >
              <div className="w-14 h-14 mx-auto rounded-full bg-india-green-500/10 border border-india-green-500/30 flex items-center justify-center mb-4">
                <CheckCircle className="w-7 h-7 text-india-green-400" />
              </div>
              <h2 className="text-lg font-semibold text-kora-100 mb-2">
                {t('common.success', 'Check your email')}
              </h2>
              <p className="text-sm text-slate-400/80 leading-relaxed">
                {t(
                  'forgotPassword.successMsg',
                  "If an account exists, you'll receive a reset link shortly."
                )}
              </p>
            </motion.div>
          )}

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

export default ForgotPassword;
