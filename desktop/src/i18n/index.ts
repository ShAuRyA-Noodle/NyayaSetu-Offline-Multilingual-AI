import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './en.json';
import hi from './hi.json';

const SUPPORTED = ['en', 'hi'] as const;
type Supported = (typeof SUPPORTED)[number];

/** Detect browser language, fall back to 'en' if unsupported. */
function detectBrowserLanguage(): Supported {
  if (typeof navigator === 'undefined') return 'en';
  const candidates: string[] = [];
  if (navigator.languages && navigator.languages.length) {
    candidates.push(...navigator.languages);
  }
  if (navigator.language) candidates.push(navigator.language);

  for (const raw of candidates) {
    const base = raw.toLowerCase().split('-')[0];
    if (SUPPORTED.includes(base as Supported)) return base as Supported;
  }
  return 'en';
}

const stored = typeof localStorage !== 'undefined' ? localStorage.getItem('language') : null;
const initialLang: Supported = (
  stored && SUPPORTED.includes(stored as Supported) ? stored : detectBrowserLanguage()
) as Supported;

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      hi: { translation: hi },
    },
    lng: initialLang,
    fallbackLng: 'en',
    supportedLngs: SUPPORTED as unknown as string[],
    interpolation: { escapeValue: false },
  });

// Keep <html lang="..."> in sync with the active i18n language.
const syncHtmlLang = (lng: string) => {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = lng;
  }
};

// Set initial value
syncHtmlLang(initialLang);

// Update on every language change
i18n.on('languageChanged', (lng) => {
  syncHtmlLang(lng);
});

export default i18n;
