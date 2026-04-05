import { useState, useEffect } from 'react';
import { HashRouter } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Toaster } from 'react-hot-toast';
import AppRoutes from './routes';
import apiService from './services/api';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { AuthProvider } from './contexts/AuthContext';
import ErrorBoundary from './components/common/ErrorBoundary';
import CustomCursor from './components/ui/CustomCursor';
import AshokaChakra from './components/decorative/AshokaChakra';
import SmoothScrollProvider from './components/providers/SmoothScrollProvider';
import ScrollProgress from './components/ui/ScrollProgress';
import FloatingParticles from './components/decorative/FloatingParticles';

function CursorWrapper() {
  const { cursorEnabled } = useTheme();
  return <CustomCursor enabled={cursorEnabled} />;
}

function App() {
  const [isOnline, setIsOnline] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkConnection();
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  const checkConnection = async () => {
    try {
      await apiService.checkHealth();
      setIsOnline(true);
    } catch {
      setIsOnline(false);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ErrorBoundary>
    <HashRouter>
      <ThemeProvider>
        <SmoothScrollProvider>
        <AuthProvider>
            <CursorWrapper />

            {/* Global ambient particle layer */}
            <FloatingParticles count={30} />

            {/* Scroll progress indicator */}
            <ScrollProgress />

            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: '#FBF7F0',
                  color: '#3A220E',
                  border: '1px solid rgba(194, 123, 58, 0.2)',
                  borderRadius: '12px',
                  fontSize: '14px',
                  boxShadow: '0 4px 16px rgba(58, 34, 14, 0.08), 0 12px 32px rgba(58, 34, 14, 0.06)',
                },
              }}
            />
            <AnimatePresence mode="wait">
              {isLoading ? (
                <motion.div
                  key="splash"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{
                    opacity: 0,
                    scale: 1.05,
                    filter: 'blur(12px)',
                  }}
                  transition={{
                    duration: 0.6,
                    ease: [0.25, 1, 0.5, 1], // ease-out-quart
                  }}
                  className="flex items-center justify-center h-screen bg-kora dark:bg-night-bg bg-village relative overflow-hidden"
                >
                  <div className="absolute inset-0 grain-overlay" />

                  <div className="text-center relative z-10">
                    {/* Chakra draws in with spring physics */}
                    <motion.div
                      initial={{ scale: 0, rotate: -180, opacity: 0 }}
                      animate={{ scale: 1, rotate: 0, opacity: 1 }}
                      transition={{
                        type: 'spring',
                        stiffness: 160,
                        damping: 18,
                        delay: 0.1,
                      }}
                      className="mb-8"
                    >
                      <AshokaChakra
                        size={80}
                        className="mx-auto animate-spin shadow-mitti-lg opacity-80"
                      />
                    </motion.div>

                    {/* Title with staggered letter reveal */}
                    <motion.h1
                      initial={{ opacity: 0, y: 30 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        delay: 0.3,
                        duration: 0.6,
                        ease: [0.25, 1, 0.5, 1],
                      }}
                      className="text-4xl md:text-5xl font-display font-bold text-gradient-mitti mb-3"
                      style={{
                        letterSpacing: '-0.02em',
                      }}
                    >
                      NyayaSetu
                    </motion.h1>

                    {/* Devanagari — blur-clear reveal */}
                    <motion.p
                      initial={{ opacity: 0, filter: 'blur(8px)', y: 10 }}
                      animate={{ opacity: 1, filter: 'blur(0px)', y: 0 }}
                      transition={{
                        delay: 0.5,
                        duration: 0.5,
                        ease: [0.25, 1, 0.5, 1],
                      }}
                      className="font-devanagari text-xl text-mitti-500 dark:text-mitti-300 mb-2"
                    >
                      न्यायसेतु
                    </motion.p>

                    <motion.p
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 0.6, y: 0 }}
                      transition={{
                        delay: 0.65,
                        duration: 0.4,
                        ease: [0.25, 1, 0.5, 1],
                      }}
                      className="text-sm text-mitti-600/60 dark:text-mitti-400/60 font-medium tracking-widest uppercase mb-8"
                    >
                      Rural Governance Platform
                    </motion.p>

                    {/* Kolam divider — scale from center */}
                    <motion.div
                      initial={{ opacity: 0, scaleX: 0 }}
                      animate={{ opacity: 1, scaleX: 1 }}
                      transition={{
                        delay: 0.75,
                        duration: 0.5,
                        ease: [0.25, 1, 0.5, 1],
                      }}
                      className="w-48 mx-auto mb-8"
                    >
                      <div className="kolam-divider" />
                    </motion.div>

                    {/* Loading indicator */}
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        delay: 0.9,
                        duration: 0.4,
                        ease: [0.25, 1, 0.5, 1],
                      }}
                      className="flex items-center justify-center space-x-3 text-sm text-mitti-400 dark:text-mitti-500"
                    >
                      <div className="chakra-spinner chakra-spinner-sm" />
                      <span className="font-medium tracking-wide">
                        Connecting to services...
                      </span>
                    </motion.div>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="app"
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{
                    duration: 0.5,
                    ease: [0.25, 1, 0.5, 1],
                  }}
                  className="min-h-screen w-full flex flex-col"
                >
                  <AppRoutes isOnline={isOnline} />
                </motion.div>
              )}
            </AnimatePresence>
        </AuthProvider>
        </SmoothScrollProvider>
      </ThemeProvider>
    </HashRouter>
    </ErrorBoundary>
  );
}

export default App;
