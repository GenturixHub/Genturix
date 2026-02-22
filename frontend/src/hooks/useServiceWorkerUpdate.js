/**
 * GENTURIX - Service Worker Update Hook
 * 
 * Handles detection and triggering of Service Worker updates.
 * Does NOT interfere with push notifications or existing SW functionality.
 */

import { useState, useEffect, useCallback } from 'react';

export const useServiceWorkerUpdate = () => {
  const [showUpdate, setShowUpdate] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [registration, setRegistration] = useState(null);

  useEffect(() => {
    if (!('serviceWorker' in navigator)) {
      console.log('[SW-Update] Service Workers not supported');
      return;
    }

    let refreshing = false;

    // Listen for controller change (new SW activated)
    const handleControllerChange = () => {
      if (refreshing) return;
      refreshing = true;
      console.log('[SW-Update] Controller changed, reloading page...');
      window.location.reload();
    };

    navigator.serviceWorker.addEventListener('controllerchange', handleControllerChange);

    // Check for existing registration
    const checkRegistration = async () => {
      try {
        const reg = await navigator.serviceWorker.getRegistration();
        
        if (reg) {
          setRegistration(reg);
          
          // If there's already a waiting worker (from previous visit)
          if (reg.waiting) {
            console.log('[SW-Update] Found waiting worker on load');
            setShowUpdate(true);
          }

          // Listen for new updates
          reg.addEventListener('updatefound', () => {
            const newWorker = reg.installing;
            console.log('[SW-Update] Update found, new worker installing...');

            if (newWorker) {
              newWorker.addEventListener('statechange', () => {
                // When the new worker is installed and waiting
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  console.log('[SW-Update] New worker installed and waiting');
                  setShowUpdate(true);
                }
              });
            }
          });

          // Periodically check for updates (every 60 seconds)
          const checkForUpdates = () => {
            reg.update().catch(err => {
              console.log('[SW-Update] Update check failed:', err.message);
            });
          };
          
          // Check for updates periodically
          const updateInterval = setInterval(checkForUpdates, 60000);

          // Also check on visibility change (when user returns to tab)
          const handleVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
              checkForUpdates();
            }
          };
          document.addEventListener('visibilitychange', handleVisibilityChange);

          return () => {
            clearInterval(updateInterval);
            document.removeEventListener('visibilitychange', handleVisibilityChange);
          };
        }
      } catch (err) {
        console.error('[SW-Update] Error checking registration:', err);
      }
    };

    // Wait for SW to be ready before checking
    navigator.serviceWorker.ready.then(() => {
      checkRegistration();
    });

    return () => {
      navigator.serviceWorker.removeEventListener('controllerchange', handleControllerChange);
    };
  }, []);

  // Trigger update
  const triggerUpdate = useCallback(() => {
    if (!registration?.waiting) {
      console.log('[SW-Update] No waiting worker to activate');
      return;
    }

    setIsUpdating(true);
    console.log('[SW-Update] Triggering SKIP_WAITING...');
    
    // Send message to waiting SW to skip waiting
    registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    
    // The controllerchange listener will handle the reload
  }, [registration]);

  // Dismiss banner (user chose not to update now)
  const dismissUpdate = useCallback(() => {
    setShowUpdate(false);
  }, []);

  return {
    showUpdate,
    isUpdating,
    triggerUpdate,
    dismissUpdate
  };
};

export default useServiceWorkerUpdate;
