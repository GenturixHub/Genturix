/**
 * PushNotificationManager v4 - Simplified
 * 
 * Simple utility for checking push notification support.
 * Push registration is now handled in AuthContext on login.
 * 
 * This file is kept for backward compatibility with any imports.
 */

class PushNotificationManager {
  constructor() {
    this.isSupported = this.checkSupport();
  }

  checkSupport() {
    return (
      'serviceWorker' in navigator &&
      'PushManager' in window &&
      'Notification' in window
    );
  }

  /**
   * Check if push is supported
   */
  static isSupported() {
    return (
      'serviceWorker' in navigator &&
      'PushManager' in window &&
      'Notification' in window
    );
  }

  /**
   * Check current permission status
   */
  static getPermissionStatus() {
    if (!('Notification' in window)) return 'unsupported';
    return Notification.permission; // 'granted', 'denied', or 'default'
  }

  /**
   * Request notification permission
   */
  static async requestPermission() {
    if (!('Notification' in window)) return 'unsupported';
    return await Notification.requestPermission();
  }

  /**
   * Get current subscription (if any)
   */
  static async getSubscription() {
    try {
      const registration = await navigator.serviceWorker.ready;
      return await registration.pushManager.getSubscription();
    } catch (e) {
      console.error('[PushManager] Error getting subscription:', e);
      return null;
    }
  }

  /**
   * Unsubscribe from push
   */
  static async unsubscribe() {
    try {
      const subscription = await this.getSubscription();
      if (subscription) {
        await subscription.unsubscribe();
        return true;
      }
      return false;
    } catch (e) {
      console.error('[PushManager] Error unsubscribing:', e);
      return false;
    }
  }
}

// Singleton instance
const pushManager = new PushNotificationManager();

export default pushManager;
export { PushNotificationManager };
