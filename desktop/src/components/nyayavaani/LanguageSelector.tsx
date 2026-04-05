import React from 'react';
import { motion } from 'framer-motion';

interface Language {
  code: string;
  englishName: string;
  nativeName: string;
}

const LANGUAGES: Language[] = [
  { code: 'hi', englishName: 'Hindi', nativeName: 'हिन्दी' },
  { code: 'bn', englishName: 'Bengali', nativeName: 'বাংলা' },
  { code: 'ta', englishName: 'Tamil', nativeName: 'தமிழ்' },
  { code: 'te', englishName: 'Telugu', nativeName: 'తెలుగు' },
  { code: 'mr', englishName: 'Marathi', nativeName: 'मराठी' },
  { code: 'gu', englishName: 'Gujarati', nativeName: 'ગુજરાતી' },
  { code: 'kn', englishName: 'Kannada', nativeName: 'ಕನ್ನಡ' },
  { code: 'ml', englishName: 'Malayalam', nativeName: 'മലയാളം' },
  { code: 'pa', englishName: 'Punjabi', nativeName: 'ਪੰਜਾਬੀ' },
  { code: 'or', englishName: 'Odia', nativeName: 'ଓଡ଼ିଆ' },
  { code: 'as', englishName: 'Assamese', nativeName: 'অসমীয়া' },
  { code: 'en', englishName: 'English', nativeName: 'English' },
];

interface LanguageSelectorProps {
  selected: string;
  onSelect: (code: string) => void;
  mode?: 'grid' | 'dropdown';
  exclude?: string;
  className?: string;
}

const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  selected,
  onSelect,
  mode = 'grid',
  exclude,
  className = '',
}) => {
  const filtered = LANGUAGES.filter((l) => l.code !== exclude);

  if (mode === 'dropdown') {
    return (
      <select
        value={selected}
        onChange={(e) => onSelect(e.target.value)}
        className={`px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm ${className}`}
      >
        {filtered.map((l) => (
          <option key={l.code} value={l.code}>
            {l.nativeName} ({l.englishName})
          </option>
        ))}
      </select>
    );
  }

  return (
    <div className={`grid grid-cols-3 sm:grid-cols-4 gap-2 ${className}`}>
      {filtered.map((l) => (
        <motion.button
          key={l.code}
          onClick={() => onSelect(l.code)}
          className={`px-3 py-2 rounded-xl text-center transition-all border ${
            selected === l.code
              ? 'bg-gradient-to-r from-saffron-500 to-orange-500 text-white border-transparent shadow-saffron'
              : 'bg-white/50 dark:bg-white/5 border-gray-200 dark:border-gray-700 hover:border-saffron-300 dark:hover:border-saffron-500'
          }`}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <span className={`text-sm font-medium block ${selected === l.code ? 'text-white' : 'text-gray-800 dark:text-gray-200'}`}>
            {l.nativeName}
          </span>
          <span className={`text-[10px] block ${selected === l.code ? 'text-white/80' : 'text-gray-400'}`}>
            {l.englishName}
          </span>
        </motion.button>
      ))}
    </div>
  );
};

export { LANGUAGES };
export default LanguageSelector;
