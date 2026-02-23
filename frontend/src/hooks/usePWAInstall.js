/**
 * GENTURIX - PWA Install Hook
 * Captures beforeinstallprompt event and provides install functionality
 */

import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'genturix_install_choice';

export function usePWAInstall() {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [isInstallable, setIsInstallable] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [userChoice, setUserChoice] = useState(() => {
    return localStorage.getItem(STORAGE_KEY);
  });

  // Check if running as installed PWA
  useEffect(() => {
    const checkInstalled = () => {
      // Check display-mode media query
      const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
      // Check iOS standalone mode
      const isIOSStandalone = window.navigator.standalone === true;
      // Check if launched from home screen (Android)
      const isLaunchedFromHomeScreen = document.referrer.includes('android-app://');
      
      const installed = isStandalone || isIOSStandalone || isLaunchedFromHomeScreen;
      setIsInstalled(installed);
      
      if (installed) {
        console.log('[PWA] Running as installed app');
      }
    };

    checkInstalled();

    // Also listen for display-mode changes
    const mediaQuery = window.matchMedia('(display-mode: standalone)');
    const handleChange = (e) => {
      setIsInstalled(e.matches);
    };
    
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
    } else {
      mediaQuery.addListener(handleChange);
    }

    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', handleChange);
      } else {
        mediaQuery.removeListener(handleChange);
      }
    };
  }, []);

  // Capture beforeinstallprompt event
  useEffect(() => {
    const handleBeforeInstallPrompt = (e) => {
      // Prevent the mini-infobar from appearing on mobile
      e.preventDefault();
      // Stash the event so it can be triggered later
      setDeferredPrompt(e);
      setIsInstallable(true);
      console.log('[PWA] Install prompt captured and ready');
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    // Listen for successful installation
    window.addEventListener('appinstalled', () => {
      console.log('[PWA] App was installed successfully');
      setIsInstalled(true);
      setIsInstallable(false);
      setDeferredPrompt(null);
      localStorage.setItem(STORAGE_KEY, 'app');
      setUserChoice('app');
    });

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  // Trigger install prompt
  const promptInstall = useCallback(async () => {
    if (!deferredPrompt) {
      console.log('[PWA] No install prompt available');
      return { outcome: 'unavailable' };
    }

    try {
      // Show the install prompt
      deferredPrompt.prompt();
      
      // Wait for the user to respond to the prompt
      const { outcome } = await deferredPrompt.userChoice;
      console.log(`[PWA] User response to install prompt: ${outcome}`);
      
      if (outcome === 'accepted') {
        localStorage.setItem(STORAGE_KEY, 'app');
        setUserChoice('app');
      }
      
      // Clear the deferred prompt - it can only be used once
      setDeferredPrompt(null);
      setIsInstallable(false);
      
      return { outcome };
    } catch (error) {
      console.error('[PWA] Error showing install prompt:', error);
      return { outcome: 'error', error };
    }
  }, [deferredPrompt]);

  // User chooses to continue on web
  const chooseWeb = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, 'web');
    setUserChoice('web');
    console.log('[PWA] User chose to continue on web');
  }, []);

  // Reset choice (for testing/debugging)
  const resetChoice = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setUserChoice(null);
    console.log('[PWA] Install choice reset');
  }, []);

  // Determine if we should show the install gate
  const shouldShowInstallGate = !isInstalled && !userChoice && isInstallable;

  return {
    isInstallable,
    isInstalled,
    userChoice,
    shouldShowInstallGate,
    promptInstall,
    chooseWeb,
    resetChoice,
  };
}

export default usePWAInstall;
