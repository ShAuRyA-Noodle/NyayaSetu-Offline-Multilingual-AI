import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, BookOpen, Search, X, ArrowRight, FileText } from 'lucide-react';
import AshokaChakra from '../components/decorative/AshokaChakra';
import ThemedSpinner from '../components/ui/ThemedSpinner';
import apiService from '../services/api';

/**
 * PublicSchemes.tsx — anonymous, public-facing scheme browser.
 * No login required. Uses the unauth `listSchemes()` endpoint.
 *
 * Citizens who want detail or to file grievances are gently prompted at
 * the bottom to register / login, but no hard wall is imposed.
 */

interface SchemeItem {
  name: string;
  scheme_id?: string;
}

const cardColors = [
  'from-mitti-500 to-mitti-600',
  'from-neel-500 to-neel-600',
  'from-mitti-600 to-mitti-700',
  'from-mitti-400 to-mitti-500',
];

const PublicSchemes: React.FC = () => {
  const { t } = useTranslation();
  const [schemes, setSchemes] = useState<SchemeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await apiService.listSchemes();
        if (cancelled) return;
        const names: string[] = response?.schemes || [];
        const idMap: Record<string, string> = response?.scheme_ids || {};
        setSchemes(names.map((name) => ({ name, scheme_id: idMap[name] })));
      } catch {
        if (!cancelled) {
          setError('Could not load schemes right now. Please try again later.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = schemes.filter((s) => s.name.toLowerCase().includes(searchTerm.toLowerCase()));

  return (
    <div className="min-h-screen bg-[#060B18] text-slate-200">
      {/* Background mesh */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="aurora-orb w-[600px] h-[600px] bg-[#0D92F4]/10 top-[-10%] left-[-10%]" />
        <div className="aurora-orb w-[500px] h-[500px] bg-[#77CDFF]/8 bottom-[-15%] right-[-5%]" style={{ animationDelay: '-7s' }} />
        <div className="absolute inset-0 grain-overlay" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto px-5 py-10 sm:py-12">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
            <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-[#77CDFF] transition-colors">
              <ArrowLeft className="w-4 h-4" />
              Home
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 text-xs font-medium text-[#77CDFF] hover:text-white transition-colors px-3 py-1.5 rounded-lg border border-[#0D92F4]/20 bg-[#0D92F4]/[0.05] hover:bg-[#0D92F4]/[0.1]"
            >
              Sign in / Register <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <header className="mb-8 pb-6 border-b border-white/[0.06]">
            <div className="flex items-center gap-3 mb-3">
              <AshokaChakra size={36} />
              <BookOpen className="w-5 h-5 text-[#77CDFF]" />
            </div>
            <h1 className="text-3xl sm:text-4xl font-display font-bold text-gradient-gold mb-1">
              {t('schemes.title', 'Government Schemes')}
            </h1>
            <p className="font-devanagari text-base text-slate-400/70 mb-3">सरकारी योजनाएँ</p>
            <p className="text-sm text-slate-400/80 max-w-2xl">
              Browse welfare schemes available to citizens. No account required to read summaries.
            </p>
          </header>

          {/* Search */}
          <div className="village-card rounded-xl p-4 mb-6">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder={t('schemes.searchPlaceholder', 'Search schemes...')}
                className="w-full pl-11 pr-10 py-3 village-input rounded-lg text-sm text-kora-100"
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  aria-label="Clear search"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {loading && (
            <div className="text-center py-16">
              <ThemedSpinner size="lg" className="mx-auto" />
            </div>
          )}

          {!loading && error && (
            <div className="village-card rounded-xl p-8 text-center">
              <p className="text-sm text-slate-400">{error}</p>
            </div>
          )}

          {!loading && !error && (
            <>
              {filtered.length === 0 ? (
                <div className="village-card rounded-xl p-12 text-center">
                  <Search className="w-10 h-10 text-slate-500 mx-auto mb-3" />
                  <p className="text-sm text-slate-400">
                    {schemes.length === 0
                      ? t('schemes.noSchemes', 'No schemes available right now.')
                      : 'No schemes match your search.'}
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-5">
                  {filtered.map((scheme, idx) => (
                    <motion.div
                      key={scheme.name}
                      initial={{ opacity: 0, y: 16 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.35, delay: Math.min(idx * 0.04, 0.4) }}
                      className="village-card rounded-xl overflow-hidden hover:shadow-lg transition-all group"
                    >
                      <div className={`bg-gradient-to-r ${cardColors[idx % cardColors.length]} p-4 text-white`}>
                        <div className="flex items-center gap-2 mb-1">
                          <FileText className="w-4 h-4 opacity-70" />
                          <span className="text-[10px] uppercase tracking-wider opacity-80">Welfare Scheme</span>
                        </div>
                        <h3 className="text-lg font-bold font-display leading-tight">{scheme.name}</h3>
                      </div>
                      <div className="p-4">
                        {scheme.scheme_id ? (
                          <Link
                            to={`/schemes/${scheme.scheme_id}`}
                            className="w-full inline-flex items-center justify-center gap-2 py-2.5 bg-white/[0.04] border border-white/[0.06] rounded-lg text-sm font-medium text-kora-100 hover:bg-[#0D92F4]/[0.08] hover:border-[#0D92F4]/20 transition-all"
                          >
                            Read more
                            <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
                          </Link>
                        ) : (
                          <Link
                            to="/login"
                            className="w-full inline-flex items-center justify-center gap-2 py-2.5 bg-white/[0.04] border border-white/[0.06] rounded-lg text-sm font-medium text-kora-100 hover:bg-[#0D92F4]/[0.08] hover:border-[#0D92F4]/20 transition-all"
                          >
                            Sign in to view
                            <ArrowRight className="w-3.5 h-3.5" />
                          </Link>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* CTA — soft, never a wall */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mt-10 village-card rounded-2xl p-6 sm:p-8 text-center border border-[#0D92F4]/20 bg-[#0D92F4]/[0.04]"
          >
            <h2 className="text-lg font-semibold text-kora-100 mb-1">Need to file a grievance or apply?</h2>
            <p className="font-devanagari text-sm text-slate-400/70 mb-3">शिकायत दर्ज करनी है या आवेदन करना है?</p>
            <p className="text-sm text-slate-400/80 mb-5 max-w-md mx-auto">
              Create a free citizen account to track your applications, file grievances, and get
              personalised scheme recommendations.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Link to="/login" className="btn-mitti px-5 py-2.5 inline-flex items-center gap-2 text-sm">
                Sign in <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/login"
                className="px-5 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.03] text-sm font-medium text-kora-100 hover:bg-white/[0.06] transition-colors"
              >
                Create free account
              </Link>
            </div>
          </motion.div>

          <footer className="mt-12 pt-6 border-t border-white/[0.06] flex flex-wrap gap-4 text-xs text-slate-500">
            <Link to="/privacy" className="hover:text-[#77CDFF] transition-colors">Privacy</Link>
            <Link to="/terms" className="hover:text-[#77CDFF] transition-colors">Terms</Link>
            <Link to="/login" className="hover:text-[#77CDFF] transition-colors">Login</Link>
            <span className="ml-auto">NyayaSetu &middot; पायलट परिनियोजन</span>
          </footer>
        </motion.div>
      </div>
    </div>
  );
};

export default PublicSchemes;
