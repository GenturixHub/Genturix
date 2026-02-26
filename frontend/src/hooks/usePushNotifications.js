/**
 * GENTURIX Push Notifications Hook v3.0 (Non-Blocking)
 * 
 * ARQUITECTURA: Backend como fuente de verdad + UI no bloqueante
 * 
 * Este hook sincroniza el estado entre:
 * - Service Worker local (pushManager.getSubscription())
 * - Base de datos del backend (GET /api/push/status)
 * 
 * CASOS MANEJADOS:
 * - Caso A: SW ✅ + DB ❌ → Re-registrar automáticamente
 * - Caso B: SW ❌ + DB ✅ → Limpiar DB (DELETE unsubscribe-all)
 * - Caso C: SW ✅ + DB ✅ → Sincronizado, isSubscribed = true
 * - Caso D: SW ❌ + DB ❌ → Sincronizado, isSubscribed = false
 * 
 * v3.0 CHANGES:
 * - UI renders IMMEDIATELY based on local SW state
 * - Backend sync runs in BACKGROUND (fire-and-forget)
 * - No blocking of component mounting or module navigation
 * - Banner shows based on local state, corrects if sync finds discrepancy
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import api from '../services/api';

// LocalStorage key for fast subscription state caching
const PUSH_SUBSCRIBED_KEY = 'push_subscription_active';

// Convert base64 to Uint8Array for applicationServerKey
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

// Helper: Promise with timeout
function withTimeout(promise, ms, errorMessage) {
  return Promise.race([
    promise,
    new Promise((_, reject) => 
      setTimeout(() => reject(new Error(errorMessage)), ms)
    )
  ]);
}

export function usePushNotifications() {
  // Core state
  const [isSupported, setIsSupported] = useState(false);
  const [permission, setPermission] = useState('default');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [registration, setRegistration] = useState(null);
  
  // v3.0: Track if initial local check is done (fast, non-blocking)
  const [isInitialized, setIsInitialized] = useState(false);
  
  // Prevent duplicate sync operations
  const syncInProgressRef = useRef(false);
  const mountedRef = useRef(true);

  // Check browser support
  useEffect(() => {
    const supported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
    setIsSupported(supported);
    
    if (supported) {
      setPermission(Notification.permission);
    }
    
    return () => {
      mountedRef.current = false;
    };
  }, []);

  /**
   * BACKGROUND SYNC FUNCTION (v3.0 - Fire and Forget)
   * Resolves inconsistencies between SW local state and backend DB
   * Does NOT block UI rendering
   */
  const syncSubscriptionStateBackground = useCallback(async (reg) => {
    // Prevent concurrent syncs
    if (syncInProgressRef.current) {
      console.log('[PUSH-SYNC] Sync already in progress, skipping');
      return;
    }
    
    syncInProgressRef.current = true;
    console.log('[PUSH-SYNC] ========== BACKGROUND SYNC START ==========');
    
    try {
      // STEP 1: Get SW local subscription state (already checked, but re-verify)
      const swSubscription = await reg.pushManager.getSubscription();
      const hasSW = !!swSubscription;
      console.log('[PUSH-SYNC] SW Local:', hasSW);
      
      // STEP 2: Get DB subscription state from backend
      let hasDB = false;
      let dbSubscriptionCount = 0;
      
      try {
        const statusResponse = await withTimeout(
          api.getPushStatus(),
          8000,
          'Timeout checking push status'
        );
        hasDB = statusResponse?.is_subscribed || false;
        dbSubscriptionCount = statusResponse?.subscription_count || 0;
        console.log('[PUSH-SYNC] DB Backend:', hasDB, `(${dbSubscriptionCount} subscriptions)`);
      } catch (statusError) {
        // If user not authenticated or network error, assume DB has no subscription
        console.log('[PUSH-SYNC] DB check failed (likely not authenticated):', statusError.message);
        hasDB = false;
      }
      
      // STEP 3: Resolve state based on matrix
      console.log('[PUSH-SYNC] State Matrix: SW=' + hasSW + ', DB=' + hasDB);
      
      // CASE A: SW ✅ + DB ❌ → Re-register subscription to backend
      if (hasSW && !hasDB) {
        console.log('[PUSH-SYNC] CASE A: SW has subscription, DB missing → Re-registering...');
        
        try {
          const subscriptionJson = swSubscription.toJSON();
          await withTimeout(
            api.subscribeToPush({
              endpoint: subscriptionJson.endpoint,
              keys: {
                p256dh: subscriptionJson.keys.p256dh,
                auth: subscriptionJson.keys.auth
              },
              expirationTime: subscriptionJson.expirationTime
            }),
            10000,
            'Timeout re-registering subscription'
          );
          
          console.log('[PUSH-SYNC] CASE A: Re-registration SUCCESS');
          // State already correct (isSubscribed = true from local check)
        } catch (reRegError) {
          console.warn('[PUSH-SYNC] CASE A: Re-registration failed:', reRegError.message);
          // Keep local state - user is subscribed locally
        }
      }
      
      // CASE B: SW ❌ + DB ✅ → Clean up DB (orphaned subscription)
      else if (!hasSW && hasDB) {
        console.log('[PUSH-SYNC] CASE B: SW missing, DB has subscription → Cleaning DB...');
        
        try {
          // Use unsubscribe-all to clean orphaned subscriptions for this user
          await withTimeout(
            api.delete('/push/unsubscribe-all'),
            8000,
            'Timeout cleaning orphaned subscriptions'
          );
          console.log('[PUSH-SYNC] CASE B: DB cleanup SUCCESS');
        } catch (cleanupError) {
          console.warn('[PUSH-SYNC] CASE B: DB cleanup failed:', cleanupError.message);
        }
        
        // Update state - user is NOT subscribed (SW is source of truth for local device)
        if (mountedRef.current) {
          setIsSubscribed(false);
        }
      }
      
      // CASE C: SW ✅ + DB ✅ → Perfectly synced
      else if (hasSW && hasDB) {
        console.log('[PUSH-SYNC] CASE C: Both SW and DB have subscription → Synced');
        // State already correct
      }
      
      // CASE D: SW ❌ + DB ❌ → Both empty, user needs to subscribe
      else {
        console.log('[PUSH-SYNC] CASE D: Neither SW nor DB have subscription → Not subscribed');
        // State already correct
      }
      
      console.log('[PUSH-SYNC] ========== BACKGROUND SYNC COMPLETE ==========');
      
    } catch (syncError) {
      console.error('[PUSH-SYNC] ========== BACKGROUND SYNC ERROR ==========');
      console.error('[PUSH-SYNC] Error:', syncError.message);
      // Don't update state on error - keep local SW state as truth
    } finally {
      syncInProgressRef.current = false;
    }
  }, []);

  /**
   * v3.0: NON-BLOCKING INITIALIZATION
   * 1. Register SW
   * 2. Immediately check local subscription (fast)
   * 3. Set isInitialized = true (UI can render)
   * 4. Fire background sync (doesn't block)
   */
  useEffect(() => {
    if (!isSupported) {
      setIsInitialized(true); // Mark as initialized even if not supported
      return;
    }

    const initServiceWorker = async () => {
      try {
        console.log('[PUSH-SYNC] v3.0: Non-blocking initialization starting...');
        const reg = await navigator.serviceWorker.register('/service-worker.js');
        
        if (!mountedRef.current) return;
        setRegistration(reg);
        console.log('[PUSH-SYNC] Service worker registered');
        
        // Wait for service worker to be ready
        await navigator.serviceWorker.ready;
        console.log('[PUSH-SYNC] Service worker ready');
        
        // v3.0: FAST LOCAL CHECK - No network call, instant
        const existingSubscription = await reg.pushManager.getSubscription();
        const hasLocalSubscription = !!existingSubscription;
        
        console.log('[PUSH-SYNC] v3.0: Local subscription check:', hasLocalSubscription);
        
        if (mountedRef.current) {
          setIsSubscribed(hasLocalSubscription);
          setIsInitialized(true); // UI CAN NOW RENDER
          
          // v3.1: Sync localStorage for instant banner hiding on next page load
          if (hasLocalSubscription) {
            localStorage.setItem(PUSH_SUBSCRIBED_KEY, 'true');
          }
        }
        
        // v3.0: BACKGROUND SYNC - Fire and forget, doesn't block UI
        // Small delay to let UI render first
        setTimeout(() => {
          if (mountedRef.current) {
            syncSubscriptionStateBackground(reg);
          }
        }, 100);
        
      } catch (err) {
        console.error('[PUSH-SYNC] Service Worker registration failed:', err);
        if (mountedRef.current) {
          setError('Error al registrar Service Worker');
          setIsInitialized(true); // Still mark as initialized so UI renders
        }
      }
    };

    initServiceWorker();
  }, [isSupported, syncSubscriptionStateBackground]);

  // Subscribe to push notifications
  const subscribe = useCallback(async () => {
    console.log('[PUSH-SYNC] ========== SUBSCRIBE START ==========');
    console.log('[PUSH-SYNC] registration:', !!registration);
    console.log('[PUSH-SYNC] isSupported:', isSupported);
    
    if (!registration || !isSupported) {
      setError('Push notifications not supported');
      console.log('[PUSH-SYNC] ABORT: Not supported or no registration');
      return false;
    }

    setIsLoading(true);
    setError(null);

    try {
      // STEP 1: Request notification permission
      console.log('[PUSH-SYNC] Step 1: Requesting notification permission...');
      const permissionResult = await withTimeout(
        Notification.requestPermission(),
        10000,
        'Timeout: No se recibió respuesta del permiso de notificaciones'
      );
      setPermission(permissionResult);
      console.log('[PUSH-SYNC] Step 1 COMPLETE: Permission =', permissionResult);

      if (permissionResult !== 'granted') {
        setError('Permiso de notificaciones denegado');
        console.log('[PUSH-SYNC] ABORT: Permission denied');
        return false;
      }

      // STEP 2: Get VAPID public key from server
      console.log('[PUSH-SYNC] Step 2: Fetching VAPID public key...');
      const vapidResponse = await withTimeout(
        api.getVapidPublicKey(),
        8000,
        'Timeout: No se pudo obtener la clave VAPID del servidor'
      );
      const vapid_public_key = vapidResponse?.publicKey;
      console.log('[PUSH-SYNC] Step 2 COMPLETE: VAPID key received =', !!vapid_public_key);
      
      if (!vapid_public_key) {
        throw new Error('VAPID key not configured on server');
      }

      // STEP 3: Subscribe to push manager
      console.log('[PUSH-SYNC] Step 3: Subscribing to PushManager...');
      
      // First, check if already subscribed locally
      let subscription = await registration.pushManager.getSubscription();
      
      if (!subscription) {
        // Create new subscription
        subscription = await withTimeout(
          registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(vapid_public_key)
          }),
          15000,
          'Timeout: La suscripción push tardó demasiado. Intenta de nuevo.'
        );
        console.log('[PUSH-SYNC] Step 3 COMPLETE: New subscription created');
      } else {
        console.log('[PUSH-SYNC] Step 3 COMPLETE: Using existing local subscription');
      }

      // STEP 4: Send subscription to server
      const subscriptionJson = subscription.toJSON();
      console.log('[PUSH-SYNC] Step 4: Sending subscription to server...');
      console.log('[PUSH-SYNC] Step 4: Subscription data:', {
        endpoint: subscriptionJson.endpoint?.substring(0, 50) + '...',
        hasP256dh: !!subscriptionJson.keys?.p256dh,
        hasAuth: !!subscriptionJson.keys?.auth
      });
      
      const result = await withTimeout(
        api.subscribeToPush({
          endpoint: subscriptionJson.endpoint,
          keys: {
            p256dh: subscriptionJson.keys.p256dh,
            auth: subscriptionJson.keys.auth
          },
          expirationTime: subscriptionJson.expirationTime
        }),
        10000,
        'Timeout: No se pudo guardar la suscripción en el servidor'
      );
      
      console.log('[PUSH-SYNC] Step 4 COMPLETE: Server response =', result);
      console.log('[PUSH-SYNC] ========== SUBSCRIBE SUCCESS ==========');

      setIsSubscribed(true);
      // v3.1: Update localStorage for instant banner hiding
      localStorage.setItem(PUSH_SUBSCRIBED_KEY, 'true');
      return true;

    } catch (err) {
      console.error('[PUSH-SYNC] ========== SUBSCRIBE FAILED ==========');
      console.error('[PUSH-SYNC] Error:', err.message);
      console.error('[PUSH-SYNC] Full error:', err);
      setError(err.message || 'Error al suscribirse a notificaciones');
      return false;
    } finally {
      console.log('[PUSH-SYNC] Finally: Setting isLoading = false');
      setIsLoading(false);
    }
  }, [registration, isSupported]);

  // Unsubscribe from push notifications
  const unsubscribe = useCallback(async () => {
    if (!registration) return false;

    setIsLoading(true);
    setError(null);

    try {
      const subscription = await registration.pushManager.getSubscription();
      
      if (subscription) {
        // Unsubscribe locally first
        await subscription.unsubscribe();
        console.log('[PUSH-SYNC] Unsubscribed locally from push manager');
        
        // Notify server
        const subscriptionJson = subscription.toJSON();
        try {
          await api.unsubscribeFromPush({
            endpoint: subscriptionJson.endpoint,
            keys: {
              p256dh: subscriptionJson.keys.p256dh,
              auth: subscriptionJson.keys.auth
            }
          });
          console.log('[PUSH-SYNC] Unsubscription confirmed on server');
        } catch (serverError) {
          console.warn('[PUSH-SYNC] Failed to notify server of unsubscription:', serverError.message);
          // Don't throw - local unsubscribe succeeded
        }
      } else {
        // No local subscription, but try to clean server anyway
        try {
          await api.delete('/push/unsubscribe-all');
          console.log('[PUSH-SYNC] Cleaned up any orphaned server subscriptions');
        } catch (cleanupError) {
          console.warn('[PUSH-SYNC] Server cleanup failed:', cleanupError.message);
        }
      }

      setIsSubscribed(false);
      // v3.1: Clear localStorage when unsubscribing
      localStorage.removeItem(PUSH_SUBSCRIBED_KEY);
      return true;

    } catch (err) {
      console.error('[PUSH-SYNC] Unsubscription failed:', err);
      setError(err.message || 'Error al desuscribirse');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [registration]);

  // Manual refresh sync (for use after login/logout)
  const refreshSync = useCallback(async () => {
    if (registration && !syncInProgressRef.current) {
      console.log('[PUSH-SYNC] Manual refresh triggered');
      syncSubscriptionStateBackground(registration);
    }
  }, [registration, syncSubscriptionStateBackground]);

  // Test notification (for debugging)
  const testNotification = useCallback(() => {
    if (permission !== 'granted') {
      setError('Permiso de notificaciones no otorgado');
      return;
    }

    new Notification('GENTURIX - Prueba', {
      body: 'Las notificaciones están funcionando correctamente',
      icon: '/logo192.png',
      tag: 'test-notification'
    });
  }, [permission]);

  return {
    // Core state
    isSupported,
    permission,
    isSubscribed,
    isLoading,
    error,
    
    // v3.0: isInitialized replaces isSynced/isSyncing for non-blocking behavior
    // isInitialized becomes true as soon as local SW check completes (fast)
    // Background sync continues but doesn't block UI
    isInitialized,
    
    // Legacy compatibility - but these are now instant (based on local check)
    isSyncing: !isInitialized,
    isSynced: isInitialized,
    
    // Actions
    subscribe,
    unsubscribe,
    refreshSync,
    testNotification
  };
}

export default usePushNotifications;
