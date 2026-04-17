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
    <div className="flex min-h-screen bg-[#060B18] relative">
      {/* Ambient background mesh */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="aurora-orb w-[800px] h-[800px] bg-[#0D92F4]/[0.03] top-[-20%] left-[-10%]" style={{ animationDuration: '40s' }} />
        <div className="aurora-orb w-[600px] h-[600px] bg-[#77CDFF]/[0.02] bottom-[-10%] right-[-5%]" style={{ animationDelay: '-15s', animationDuration: '35s' }} />
        <div className="aurora-orb w-[500px] h-[500px] bg-[#F95454]/[0.02] top-[50%] left-[40%]" style={{ animationDelay: '-25s', animationDuration: '45s' }} />
      </div>

      {/* Grain */}
      <div className="fixed inset-0 grain-overlay pointer-events-none z-[1]" />

      {/* Mobile sidebar backdrop */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="fixed inset-0 z-30 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            style={{
              backgroundColor: 'rgba(6, 5, 4, 0.7)',
              backdropFilter: 'blur(8px)',
              WebkitBackdropFilter: 'blur(8px)',
            }}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-40 lg:sticky lg:top-0 lg:h-screen lg:z-auto
        transition-transform duration-300
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}
        style={{ transitionTimingFunction: 'cubic-bezier(0.25, 1, 0.5, 1)' }}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main content */}
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
