import React from 'react';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';

const LanguageToggle: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { i18n } = useTranslation();
  const isHindi = i18n.language === 'hi';

  const toggle = () => {
    const newLang = isHindi ? 'en' : 'hi';
    i18n.changeLanguage(newLang);
    localStorage.setItem('language', newLang);
  };

  return (
    <button
      onClick={toggle}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
        bg-kora-200/50 dark:bg-night-card/60
        border border-mitti-200/20 dark:border-night-border/40
        text-mitti-600 dark:text-mitti-400
        hover:bg-mitti-100/60 dark:hover:bg-night-card/80
        transition-all duration-300 ${className}`}
      title={isHindi ? 'Switch to English' : 'हिंदी में बदलें'}
    >
      <Globe className="w-4 h-4" strokeWidth={1.8} />
      <span className="font-semibold">{isHindi ? 'EN' : 'हि'}</span>
    </button>
  );
};

export default LanguageToggle;
