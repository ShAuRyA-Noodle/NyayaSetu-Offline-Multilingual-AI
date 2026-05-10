import React, { useState, useEffect } from 'react';
import { Info, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';

interface AIDisclaimerBannerProps {
  /** Storage key — distinct keys allow different views to dismiss separately. */
  storageKey?: string;
  className?: string;
}

/**
 * Dismissible banner shown above AI-generated content.
 * Dismissal persists in sessionStorage (re-shows each new tab/session).
 *
 * Currently mounted in: Schemes.tsx (AI summary view), NoticeDrafter.tsx
 * (generated draft preview).
 *
 * TODO(Chat.tsx agent): when revisiting Chat.tsx, please mount
 *   <AIDisclaimerBanner storageKey="ai-disclaimer-chat" />
 * at the top of the AI answer area (above the very first assistant message),
 * so RAG answers carry the same advisory.
 */
const AIDisclaimerBanner: React.FC<AIDisclaimerBannerProps> = ({
  storageKey = 'ai-disclaimer-dismissed',
  className = '',
}) => {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      const dismissed = sessionStorage.getItem(storageKey) === '1';
      setVisible(!dismissed);
    } catch {
      setVisible(true);
    }
  }, [storageKey]);

  const dismiss = () => {
    try {
      sessionStorage.setItem(storageKey, '1');
    } catch {
      /* ignore storage errors */
    }
    setVisible(false);
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ opacity: 0, y: -8, height: 0 }}
          animate={{ opacity: 1, y: 0, height: 'auto' }}
          exit={{ opacity: 0, y: -8, height: 0 }}
          transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
          className={`overflow-hidden ${className}`}
          role="status"
          aria-live="polite"
        >
          <div className="flex items-start gap-3 rounded-xl border border-[#0D92F4]/20 bg-[#0D92F4]/[0.06] px-4 py-3 mb-4">
            <div className="mt-0.5 flex-shrink-0 w-7 h-7 rounded-full bg-[#0D92F4]/15 flex items-center justify-center">
              <Info className="w-3.5 h-3.5 text-[#77CDFF]" />
            </div>
            <p className="flex-1 text-xs text-slate-300 leading-relaxed pt-0.5">
              {t(
                'aiDisclaimer.message',
                'AI-generated answer. Verify with official sources before acting.'
              )}
            </p>
            <button
              type="button"
              onClick={dismiss}
              aria-label={t('aiDisclaimer.dismiss', 'Dismiss')}
              className="flex-shrink-0 p-1 rounded-md text-slate-500 hover:text-slate-300 hover:bg-white/[0.06] transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default AIDisclaimerBanner;
