import { useState, useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Toaster } from 'react-hot-toast';
import AppRoutes from './routes';
import apiService from './services/api';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import ErrorBoundary from './components/common/ErrorBoundary';
import CustomCursor from './components/ui/CustomCursor';
import SmoothScrollProvider from './components/providers/SmoothScrollProvider';
import ScrollProgress from './components/ui/ScrollProgress';

function CursorWrapper() {
  const { cursorEnabled } = useTheme();
  return <CustomCursor enabled={cursorEnabled} />;
}

/* ─────────────────────────────────────────────
   SPLASH SCREEN — cinematic loading experience
   ───────────────────────────────────────────── */
function SplashScreen() {
  return (
    <motion.div
      key="splash"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 1.05 }}
      transition={{ duration: 0.5, ease: [0.25, 1, 0.5, 1] }}
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-[#060B18] overflow-hidden"
    >
      {/* Ambient glow orbs */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="aurora-orb w-[500px] h-[500px] bg-[#0D92F4]/15 top-[10%] left-[20%]" />
        <div className="aurora-orb w-[400px] h-[400px] bg-[#77CDFF]/8 bottom-[10%] right-[15%]" style={{ animationDelay: '-10s' }} />
        <div className="absolute inset-0 grain-overlay" />
      </div>

      <div className="text-center relative z-10">
        {/* Animated logo mark */}
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 200, damping: 20, delay: 0.1 }}
          className="mb-10 relative inline-block"
        >
          {/* Glow ring behind the logo */}
          <motion.div
            className="absolute inset-0 rounded-full"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.4, 0.2] }}
            transition={{ duration: 2, delay: 0.5, repeat: Infinity, repeatType: 'reverse' }}
            style={{
              background: 'radial-gradient(circle, rgba(13,146,244,0.2) 0%, transparent 70%)',
              transform: 'scale(2.5)',
            }}
          />
          {/* Logo — stylized N in a circle */}
          <div className="w-16 h-16 rounded-full border border-[#0D92F4]/20 flex items-center justify-center relative">
            <span className="text-2xl font-display font-bold text-gradient-gold">N</span>
            {/* Spinning ring */}
            <motion.div
              className="absolute inset-[-3px] rounded-full border border-transparent"
              style={{
                borderTopColor: 'rgba(194, 123, 58, 0.4)',
                borderRightColor: 'rgba(194, 123, 58, 0.1)',
              }}
              animate={{ rotate: 360 }}
              transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
            />
          </div>
        </motion.div>

        {/* Title */}
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6, ease: [0.25, 1, 0.5, 1] }}
          className="text-3xl md:text-4xl font-display font-bold tracking-tight mb-2"
        >
          <span className="text-gradient-gold">Nyaya</span>
          <span className="text-kora-100">Setu</span>
        </motion.h1>

        {/* Devanagari */}
        <motion.p
          initial={{ opacity: 0, filter: 'blur(6px)' }}
          animate={{ opacity: 0.5, filter: 'blur(0px)' }}
          transition={{ delay: 0.5, duration: 0.4 }}
          className="font-devanagari text-base text-mitti-500/50 mb-8"
        >
          न्यायसेतु
        </motion.p>

        {/* Progress line */}
        <motion.div
          className="w-32 mx-auto mb-8 h-[1px] bg-white/5 rounded-full overflow-hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
        >
          <motion.div
            className="h-full rounded-full"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(13,146,244,0.6), transparent)' }}
            initial={{ x: '-100%' }}
            animate={{ x: '100%' }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          />
        </motion.div>

        {/* Status text */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.35 }}
          transition={{ delay: 0.7, duration: 0.4 }}
          className="text-xs text-mitti-500 font-medium tracking-widest uppercase"
        >
          Initializing
        </motion.p>
      </div>
    </motion.div>
  );
}

/* ─────────────────────────────────────────────
   APP ROOT
   ───────────────────────────────────────────── */
function App() {
  const [isOnline, setIsOnline] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkConnection();
    const interval = setInterval(() => {
      if (!document.hidden) checkConnection();
    }, 30000);
    const onVisible = () => { if (!document.hidden) checkConnection(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, []);

  const checkConnection = async (retries = 2) => {
    try {
      await apiService.checkHealth();
      setIsOnline(true);
    } catch {
      if (retries > 0) {
        await new Promise(r => setTimeout(r, 1500));
        return checkConnection(retries - 1);
      }
      setIsOnline(false);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ErrorBoundary>
    <BrowserRouter>
      <ThemeProvider>
        <SmoothScrollProvider>
        <AuthProvider>
            <CursorWrapper />
            <ScrollProgress />

            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: 'rgba(8, 16, 32, 0.9)',
                  backdropFilter: 'blur(20px)',
                  color: '#E2E8F0',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: '12px',
                  fontSize: '13px',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
                },
              }}
            />

            <AnimatePresence mode="wait">
              {isLoading ? (
                <SplashScreen />
              ) : (
                <motion.div
                  key="app"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.4, ease: [0.25, 1, 0.5, 1] }}
                  className="min-h-screen w-full flex flex-col"
                >
                  <AppRoutes isOnline={isOnline} />
                </motion.div>
              )}
            </AnimatePresence>
        </AuthProvider>
        </SmoothScrollProvider>
      </ThemeProvider>
    </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
