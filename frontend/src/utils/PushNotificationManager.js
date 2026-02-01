/**
 * GENTURIX Push Notification Manager
 * Handles push subscription and permission flow
 */

class PushNotificationManager {
  constructor() {
    this.registration = null;
    this.subscription = null;
  }

  /**
   * Check if push notifications are supported
   */
  static isSupported() {
    return 'serviceWorker' in navigator && 
           'PushManager' in window && 
           'Notification' in window;
  }

  /**
   * Get current notification permission
   */
  static getPermission() {
    if (!('Notification' in window)) {
      return 'unsupported';
    }
    return Notification.permission;
  }

  /**
   * Request notification permission from user
   */
  async requestPermission() {
    if (!PushNotificationManager.isSupported()) {
      console.log('[Push] Not supported in this browser');
      return 'unsupported';
    }

    try {
      const permission = await Notification.requestPermission();
      console.log('[Push] Permission result:', permission);
      return permission;
    } catch (error) {
      console.error('[Push] Error requesting permission:', error);
      return 'error';
    }
  }

  /**
   * Get service worker registration
   */
  async getRegistration() {
    if (this.registration) {
      return this.registration;
    }

    try {
      this.registration = await navigator.serviceWorker.ready;
      console.log('[Push] Service worker ready:', this.registration.scope);
      return this.registration;
    } catch (error) {
      console.error('[Push] Error getting registration:', error);
      throw error;
    }
  }

  /**
   * Convert VAPID key from base64 to Uint8Array
   */
  urlBase64ToUint8Array(base64String) {
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

  /**
   * Subscribe to push notifications
   * @param {string} vapidPublicKey - VAPID public key from server
   */
  async subscribe(vapidPublicKey) {
    if (!PushNotificationManager.isSupported()) {
      throw new Error('Push notifications not supported');
    }

    // Check permission
    if (Notification.permission !== 'granted') {
      const permission = await this.requestPermission();
      if (permission !== 'granted') {
        throw new Error('Notification permission denied');
      }
    }

    // Get registration
    const registration = await this.getRegistration();

    // Check for existing subscription
    let subscription = await registration.pushManager.getSubscription();

    if (subscription) {
      console.log('[Push] Existing subscription found');
      this.subscription = subscription;
      return this.formatSubscription(subscription);
    }

    // Create new subscription
    try {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(vapidPublicKey)
      });

      console.log('[Push] New subscription created');
      this.subscription = subscription;
      return this.formatSubscription(subscription);
    } catch (error) {
      console.error('[Push] Error subscribing:', error);
      throw error;
    }
  }

  /**
   * Unsubscribe from push notifications
   */
  async unsubscribe() {
    if (!this.subscription) {
      const registration = await this.getRegistration();
      this.subscription = await registration.pushManager.getSubscription();
    }

    if (this.subscription) {
      await this.subscription.unsubscribe();
      this.subscription = null;
      console.log('[Push] Unsubscribed');
      return true;
    }

    return false;
  }

  /**
   * Format subscription for sending to server
   */
  formatSubscription(subscription) {
    const key = subscription.getKey('p256dh');
    const auth = subscription.getKey('auth');

    return {
      endpoint: subscription.endpoint,
      keys: {
        p256dh: key ? btoa(String.fromCharCode.apply(null, new Uint8Array(key))) : '',
        auth: auth ? btoa(String.fromCharCode.apply(null, new Uint8Array(auth))) : ''
      }
    };
  }

  /**
   * Check if currently subscribed
   */
  async isSubscribed() {
    try {
      const registration = await this.getRegistration();
      const subscription = await registration.pushManager.getSubscription();
      return !!subscription;
    } catch {
      return false;
    }
  }

  /**
   * Send a test notification (for debugging)
   */
  async sendTestNotification(title = 'Test', body = 'This is a test notification') {
    if (Notification.permission !== 'granted') {
      console.warn('[Push] Cannot send test - permission not granted');
      return false;
    }

    const registration = await this.getRegistration();
    await registration.showNotification(title, {
      body,
      icon: '/logo192.png',
      badge: '/logo192.png',
      vibrate: [100, 50, 100],
      tag: 'test-notification'
    });

    return true;
  }
}

// Singleton instance
const pushManager = new PushNotificationManager();

export default pushManager;
export { PushNotificationManager };
