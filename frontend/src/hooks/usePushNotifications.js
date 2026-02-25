import { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

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
  const [isSupported, setIsSupported] = useState(false);
  const [permission, setPermission] = useState('default');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [registration, setRegistration] = useState(null);

  // Check browser support
  useEffect(() => {
    const supported = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
    setIsSupported(supported);
    
    if (supported) {
      setPermission(Notification.permission);
    }
  }, []);

  // Register service worker and check existing subscription
  useEffect(() => {
    if (!isSupported) return;

    const initServiceWorker = async () => {
      try {
        console.log('[PUSH-DEBUG] Registering service worker...');
        const reg = await navigator.serviceWorker.register('/service-worker.js');
        setRegistration(reg);
        console.log('[PUSH-DEBUG] Service worker registered');
        
        // Wait for service worker to be ready
        await navigator.serviceWorker.ready;
        console.log('[PUSH-DEBUG] Service worker ready');
        
        // Check if already subscribed
        const existingSubscription = await reg.pushManager.getSubscription();
        setIsSubscribed(!!existingSubscription);
        console.log('[PUSH-DEBUG] Existing subscription:', !!existingSubscription);
        
      } catch (err) {
        console.error('[PUSH-DEBUG] Service Worker registration failed:', err);
        setError('Error al registrar Service Worker');
      }
    };

    initServiceWorker();
  }, [isSupported]);

  // Subscribe to push notifications
  const subscribe = useCallback(async () => {
    console.log('[PUSH-DEBUG] ========== SUBSCRIBE START ==========');
    console.log('[PUSH-DEBUG] registration:', !!registration);
    console.log('[PUSH-DEBUG] isSupported:', isSupported);
    
    if (!registration || !isSupported) {
      setError('Push notifications not supported');
      console.log('[PUSH-DEBUG] ABORT: Not supported or no registration');
      return false;
    }

    setIsLoading(true);
    setError(null);

    try {
      // STEP 1: Request notification permission
      console.log('[PUSH-DEBUG] Step 1: Requesting notification permission...');
      const permissionResult = await withTimeout(
        Notification.requestPermission(),
        10000,
        'Timeout: No se recibió respuesta del permiso de notificaciones'
      );
      setPermission(permissionResult);
      console.log('[PUSH-DEBUG] Step 1 COMPLETE: Permission =', permissionResult);

      if (permissionResult !== 'granted') {
        setError('Permiso de notificaciones denegado');
        console.log('[PUSH-DEBUG] ABORT: Permission denied');
        return false;
      }

      // STEP 2: Get VAPID public key from server
      console.log('[PUSH-DEBUG] Step 2: Fetching VAPID public key...');
      const vapidResponse = await withTimeout(
        api.getVapidPublicKey(),
        8000,
        'Timeout: No se pudo obtener la clave VAPID del servidor'
      );
      const vapid_public_key = vapidResponse?.publicKey;
      console.log('[PUSH-DEBUG] Step 2 COMPLETE: VAPID key received =', !!vapid_public_key);
      
      if (!vapid_public_key) {
        throw new Error('VAPID key not configured on server');
      }

      // STEP 3: Subscribe to push manager
      console.log('[PUSH-DEBUG] Step 3: Subscribing to PushManager...');
      console.log('[PUSH-DEBUG] Step 3: applicationServerKey length =', urlBase64ToUint8Array(vapid_public_key).length);
      
      const subscription = await withTimeout(
        registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(vapid_public_key)
        }),
        15000,  // 15 second timeout for subscribe
        'Timeout: La suscripción push tardó demasiado. Intenta de nuevo.'
      );
      console.log('[PUSH-DEBUG] Step 3 COMPLETE: Subscription created');

      // STEP 4: Send subscription to server
      const subscriptionJson = subscription.toJSON();
      console.log('[PUSH-DEBUG] Step 4: Sending subscription to server...');
      console.log('[PUSH-DEBUG] Step 4: Subscription data:', {
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
      
      console.log('[PUSH-DEBUG] Step 4 COMPLETE: Server response =', result);
      console.log('[PUSH-DEBUG] ========== SUBSCRIBE SUCCESS ==========');

      setIsSubscribed(true);
      return true;

    } catch (err) {
      console.error('[PUSH-DEBUG] ========== SUBSCRIBE FAILED ==========');
      console.error('[PUSH-DEBUG] Error:', err.message);
      console.error('[PUSH-DEBUG] Full error:', err);
      setError(err.message || 'Error al suscribirse a notificaciones');
      return false;
    } finally {
      // ALWAYS reset loading state
      console.log('[PUSH-DEBUG] Finally: Setting isLoading = false');
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
        // Unsubscribe locally
        await subscription.unsubscribe();
        console.log('[PUSH-DEBUG] Unsubscribed locally from push manager');
        
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
          console.log('[PUSH-DEBUG] Unsubscription confirmed on server');
        } catch (serverError) {
          console.warn('[PUSH-DEBUG] Failed to notify server of unsubscription:', serverError.message);
          // Don't throw - local unsubscribe succeeded
        }
      }

      setIsSubscribed(false);
      return true;

    } catch (err) {
      console.error('[PUSH-DEBUG] Unsubscription failed:', err);
      setError(err.message || 'Error al desuscribirse');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [registration]);

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
    isSupported,
    permission,
    isSubscribed,
    isLoading,
    error,
    subscribe,
    unsubscribe,
    testNotification
  };
}

export default usePushNotifications;
