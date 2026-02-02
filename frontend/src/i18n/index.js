import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import es from './es.json';
import en from './en.json';

// Get saved language from localStorage or default to 'es'
const getSavedLanguage = () => {
  try {
    const saved = localStorage.getItem('userLanguage');
    if (saved && ['es', 'en'].includes(saved)) {
      return saved;
    }
  } catch (e) {
    console.warn('Could not access localStorage for language');
  }
  return 'es'; // Default to Spanish
};

i18n
  .use(initReactI18next)
  .init({
    resources: {
      es: { translation: es },
      en: { translation: en }
    },
    lng: getSavedLanguage(), // Use saved language - NO browser detector override
    fallbackLng: 'es', // Fallback to Spanish
    debug: false,
    
    interpolation: {
      escapeValue: false // React already escapes values
    },

    // React options
    react: {
      useSuspense: false, // Disable suspense to avoid loading issues
      bindI18n: 'languageChanged loaded', // Re-render on language change
      bindI18nStore: 'added removed' // Re-render on store changes
    }
  });

// Helper function to change language and persist it
export const changeLanguage = async (lang) => {
  try {
    localStorage.setItem('userLanguage', lang);
    await i18n.changeLanguage(lang);
    // Force document lang attribute update
    document.documentElement.lang = lang;
    return true;
  } catch (error) {
    console.error('Error changing language:', error);
    return false;
  }
};

// Helper to get current language
export const getCurrentLanguage = () => {
  return i18n.language || 'es';
};

// Available languages
export const availableLanguages = [
  { code: 'es', name: 'Español', flag: '🇪🇸' },
  { code: 'en', name: 'English', flag: '🇺🇸' }
];

export default i18n;
