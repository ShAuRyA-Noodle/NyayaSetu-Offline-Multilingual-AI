import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Home, Compass, ArrowLeft } from 'lucide-react';
import AshokaChakra from '../components/decorative/AshokaChakra';

/**
 * NotFound.tsx — friendly 404 with bilingual copy and a path back to safety.
 */
const NotFound: React.FC = () => {
  return (
    <div className="min-h-screen relative overflow-hidden bg-[#060B18] flex items-center justify-center p-5">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="aurora-orb w-[600px] h-[600px] bg-[#0D92F4]/10 top-[-10%] left-[-10%]" />
        <div className="aurora-orb w-[500px] h-[500px] bg-[#F95454]/10 bottom-[-15%] right-[-5%]" style={{ animationDelay: '-7s' }} />
        <div className="absolute inset-0 grain-overlay" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-lg text-center"
      >
        <div className="inline-block mb-5">
          <AshokaChakra size={56} />
        </div>

        <h1 className="text-7xl sm:text-8xl font-display font-bold text-gradient-gold mb-2 leading-none">
          404
        </h1>
        <p className="font-devanagari text-2xl text-slate-400/70 mb-4">पृष्ठ नहीं मिला</p>

        <p className="text-base text-kora-100 font-semibold mb-2">
          We couldn&apos;t find that page.
        </p>
        <p className="text-sm text-slate-400 max-w-md mx-auto mb-8 leading-relaxed">
          The link may be broken, or the page may have moved. Try heading home,
          browsing schemes, or signing in.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/"
            className="btn-mitti px-5 py-2.5 inline-flex items-center gap-2 text-sm"
          >
            <Home className="w-4 h-4" />
            Home
          </Link>
          <Link
            to="/public/schemes"
            className="px-5 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.03] text-sm font-medium text-kora-100 hover:bg-white/[0.06] transition-colors inline-flex items-center gap-2"
          >
            <Compass className="w-4 h-4" />
            Browse Schemes
          </Link>
          <button
            onClick={() => window.history.length > 1 ? window.history.back() : null}
            className="px-5 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-kora-100 transition-colors inline-flex items-center gap-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Go back
          </button>
        </div>
      </motion.div>
    </div>
  );
};

export default NotFound;
