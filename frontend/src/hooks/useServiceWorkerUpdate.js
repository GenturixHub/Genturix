/**
 * GENTURIX - Service Worker Update Hook
 * 
 * Handles detection and triggering of Service Worker updates.
 * Works in both web browser and installed PWA.
 * Does NOT interfere with push notifications or existing SW functionality.
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export const useServiceWorkerUpdate = () => {
  const [showUpdate, setShowUpdate] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [registration, setRegistration] = useState(null);
  const refreshingRef = useRef(false);

  useEffect(() => {
    if (!('serviceWorker' in navigator)) {
      console.log('[SW-Update] Service Workers not supported');
      return;
    }

    // Listen for controller change (new SW activated)
    const handleControllerChange = () => {
      if (refreshingRef.current) return;
      refreshingRef.current = true;
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
          console.log('[SW-Update] Registration found, scope:', reg.scope);
          
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
                console.log('[SW-Update] New worker state:', newWorker.state);
                // When the new worker is installed and waiting
                if (newWorker.state === 'installed') {
                  // Check if there's an existing controller (not first install)
                  if (navigator.serviceWorker.controller) {
                    console.log('[SW-Update] New worker installed and waiting - showing modal');
                    setShowUpdate(true);
                  } else {
                    // First time install - no update needed
                    console.log('[SW-Update] First install, no update modal needed');
                  }
                }
              });
            }
          });

          // Check for updates immediately on load
          reg.update().catch(err => {
            console.log('[SW-Update] Initial update check failed:', err.message);
          });
          
          // Periodically check for updates (every 60 seconds)
          const checkForUpdates = () => {
            if (document.visibilityState === 'visible') {
              reg.update().catch(err => {
                console.log('[SW-Update] Update check failed:', err.message);
              });
            }
          };
          
          const updateInterval = setInterval(checkForUpdates, 60000);

          // Also check on visibility change (when user returns to tab/app)
          const handleVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
              // Small delay to avoid immediate check on app resume
              setTimeout(checkForUpdates, 1000);
            }
          };
          document.addEventListener('visibilitychange', handleVisibilityChange);

          // Check on online event (for PWA that was offline)
          const handleOnline = () => {
            console.log('[SW-Update] Back online, checking for updates...');
            checkForUpdates();
          };
          window.addEventListener('online', handleOnline);

          return () => {
            clearInterval(updateInterval);
            document.removeEventListener('visibilitychange', handleVisibilityChange);
            window.removeEventListener('online', handleOnline);
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

  // Trigger update - with fallback reload
  const triggerUpdate = useCallback(() => {
    const waitingWorker = registration?.waiting;
    
    if (!waitingWorker) {
      console.log('[SW-Update] No waiting worker to activate');
      // Fallback: force reload anyway
      window.location.reload();
      return;
    }

    setIsUpdating(true);
    console.log('[SW-Update] Triggering SKIP_WAITING...');
    
    // Send message to waiting SW to skip waiting
    waitingWorker.postMessage({ type: 'SKIP_WAITING' });
    
    // Fallback: if controllerchange doesn't fire within 3 seconds, force reload
    // This handles edge cases where the event might not fire
    setTimeout(() => {
      if (!refreshingRef.current) {
        console.log('[SW-Update] Fallback reload after timeout');
        refreshingRef.current = true;
        window.location.reload();
      }
    }, 3000);
    
  }, [registration]);

  // Dismiss modal (user chose not to update now)
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
