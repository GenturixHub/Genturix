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
        // Register or get existing service worker
        const reg = await navigator.serviceWorker.register('/service-worker.js');
        setRegistration(reg);
        
        // Wait for service worker to be ready
        await navigator.serviceWorker.ready;
        
        // Check if already subscribed
        const existingSubscription = await reg.pushManager.getSubscription();
        setIsSubscribed(!!existingSubscription);
        
      } catch (err) {
        console.error('Service Worker registration failed:', err);
        setError('Error al registrar Service Worker');
      }
    };

    initServiceWorker();
  }, [isSupported]);

  // Subscribe to push notifications
  const subscribe = useCallback(async () => {
    if (!registration || !isSupported) {
      setError('Push notifications not supported');
      return false;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Request notification permission
      const permissionResult = await Notification.requestPermission();
      setPermission(permissionResult);

      if (permissionResult !== 'granted') {
        setError('Permiso de notificaciones denegado');
        setIsLoading(false);
        return false;
      }

      // Get VAPID public key from server
      const vapidResponse = await api.getVapidPublicKey();
      const vapid_public_key = vapidResponse?.publicKey;
      
      if (!vapid_public_key) {
        throw new Error('VAPID key not configured on server');
      }

      // Subscribe to push
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapid_public_key)
      });

      // Send subscription to server
      const subscriptionJson = subscription.toJSON();
      
      console.log('[PUSH] Sending subscription to server...', {
        endpoint: subscriptionJson.endpoint?.substring(0, 50) + '...',
        hasP256dh: !!subscriptionJson.keys?.p256dh,
        hasAuth: !!subscriptionJson.keys?.auth
      });
      
      try {
        const result = await api.subscribeToPush({
          endpoint: subscriptionJson.endpoint,
          keys: {
            p256dh: subscriptionJson.keys.p256dh,
            auth: subscriptionJson.keys.auth
          },
          expirationTime: subscriptionJson.expirationTime
        });
        
        console.log('[PUSH] Subscription saved successfully:', result);
      } catch (subscribeError) {
        console.error('[PUSH] Failed to save subscription to server:', {
          error: subscribeError.message,
          status: subscribeError.status,
          data: subscribeError.data
        });
        throw subscribeError;
      }

      setIsSubscribed(true);
      setIsLoading(false);
      return true;

    } catch (err) {
      console.error('Push subscription failed:', err);
      setError(err.message || 'Error al suscribirse a notificaciones');
      setIsLoading(false);
      return false;
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
        
        // Notify server
        const subscriptionJson = subscription.toJSON();
        await api.unsubscribeFromPush({
          endpoint: subscriptionJson.endpoint,
          keys: {
            p256dh: subscriptionJson.keys.p256dh,
            auth: subscriptionJson.keys.auth
          }
        });
      }

      setIsSubscribed(false);
      setIsLoading(false);
      return true;

    } catch (err) {
      console.error('Push unsubscription failed:', err);
      setError(err.message || 'Error al desuscribirse');
      setIsLoading(false);
      return false;
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
