import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from './Sidebar';
import Header from './Header';

interface LayoutProps {
  children: React.ReactNode;
  isOnline: boolean;
}

const Layout: React.FC<LayoutProps> = ({ children, isOnline }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-kora dark:bg-night-bg bg-village bg-khadi-texture relative">
      {/* Grain texture overlay */}
      <div className="absolute inset-0 grain-overlay pointer-events-none z-[1]" />

      {/* Mobile sidebar backdrop with smooth fade */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.25, 1, 0.5, 1] }}
            className="fixed inset-0 z-30 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            style={{
              backgroundColor: 'rgba(15, 13, 10, 0.5)',
              backdropFilter: 'blur(4px)',
              WebkitBackdropFilter: 'blur(4px)',
            }}
          />
        )}
      </AnimatePresence>

      {/* Sidebar — smooth slide with spring physics */}
      <div className={`
        fixed inset-y-0 left-0 z-40 lg:sticky lg:top-0 lg:h-screen lg:z-auto
        transition-transform duration-300
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}
        style={{
          transitionTimingFunction: 'cubic-bezier(0.25, 1, 0.5, 1)',
        }}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0 relative z-[2] w-full lg:w-[calc(100%-16rem)]">
        <Header isOnline={isOnline} onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
