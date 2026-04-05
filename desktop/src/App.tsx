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
        <AuthProvider>
            <CursorWrapper />
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
                },
              }}
            />
            <AnimatePresence mode="wait">
              {isLoading ? (
                <motion.div
                  key="splash"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0, filter: 'blur(8px)' }}
                  transition={{ duration: 0.5 }}
                  className="flex items-center justify-center h-screen bg-kora dark:bg-night-bg bg-village relative overflow-hidden"
                >
                  <div className="absolute inset-0 grain-overlay" />

                  <div className="text-center relative z-10">
                    <motion.div
                      initial={{ scale: 0, rotate: -180 }}
                      animate={{ scale: 1, rotate: 0 }}
                      transition={{ type: 'spring', stiffness: 200, damping: 20, delay: 0.1 }}
                      className="mb-8"
                    >
                      <AshokaChakra size={80} className="mx-auto animate-[chakra-spin_4s_linear_infinite]" />
                    </motion.div>

                    <motion.h1
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 }}
                      className="text-4xl font-display font-bold text-gradient-mitti mb-2"
                    >
                      NyayaSetu
                    </motion.h1>

                    <motion.p
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.5 }}
                      className="font-devanagari text-xl text-mitti-500 dark:text-mitti-300 mb-2"
                    >
                      न्यायसेतु
                    </motion.p>

                    <motion.p
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.6 }}
                      className="text-sm text-mitti-600/60 dark:text-mitti-400/60 font-medium tracking-wide mb-8"
                    >
                      Rural Governance Platform
                    </motion.p>

                    <motion.div
                      initial={{ opacity: 0, scaleX: 0 }}
                      animate={{ opacity: 1, scaleX: 1 }}
                      transition={{ delay: 0.7 }}
                      className="w-48 mx-auto mb-8"
                    >
                      <div className="kolam-divider" />
                    </motion.div>

                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.9 }}
                      className="flex items-center justify-center space-x-3 text-sm text-mitti-400 dark:text-mitti-500"
                    >
                      <div className="chakra-spinner chakra-spinner-sm" />
                      <span className="font-medium">Connecting to services...</span>
                    </motion.div>
                  </div>
                </motion.div>
              ) : (
                <motion.div
                  key="app"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                  className="h-full"
                >
                  <AppRoutes isOnline={isOnline} />
                </motion.div>
              )}
            </AnimatePresence>
        </AuthProvider>
      </ThemeProvider>
    </HashRouter>
    </ErrorBoundary>
  );
}

export default App;
