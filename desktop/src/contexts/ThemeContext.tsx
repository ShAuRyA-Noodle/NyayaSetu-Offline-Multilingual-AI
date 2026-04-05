import React, { createContext, useContext, useEffect, useState } from 'react';

interface ThemeContextType {
  darkMode: boolean;
  toggleDarkMode: () => void;
  cursorEnabled: boolean;
  toggleCursor: () => void;
  reducedMotion: boolean;
  toggleReducedMotion: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('darkMode');
    return saved ? JSON.parse(saved) : false;
  });

  const [cursorEnabled, setCursorEnabled] = useState<boolean>(() => {
    const saved = localStorage.getItem('cursorEnabled');
    return saved ? JSON.parse(saved) : true;
  });

  const [reducedMotion, setReducedMotion] = useState<boolean>(() => {
    const saved = localStorage.getItem('reducedMotion');
    return saved ? JSON.parse(saved) : false;
  });

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('darkMode', JSON.stringify(darkMode));
  }, [darkMode]);

  useEffect(() => {
    localStorage.setItem('cursorEnabled', JSON.stringify(cursorEnabled));
  }, [cursorEnabled]);

  useEffect(() => {
    localStorage.setItem('reducedMotion', JSON.stringify(reducedMotion));
  }, [reducedMotion]);

  const toggleDarkMode = () => setDarkMode(prev => !prev);
  const toggleCursor = () => setCursorEnabled(prev => !prev);
  const toggleReducedMotion = () => setReducedMotion(prev => !prev);

  return (
    <ThemeContext.Provider value={{
      darkMode, toggleDarkMode,
      cursorEnabled, toggleCursor,
      reducedMotion, toggleReducedMotion,
    }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export default ThemeContext;
