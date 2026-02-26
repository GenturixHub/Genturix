/**
 * GENTURIX Push Permission Request Component v3.1
 * Shows a friendly banner to request push notification permission
 * 
 * Works for ALL roles - Guards, Residents, Admins, etc.
 * Uses usePushNotifications hook for proper subscription handling.
 * 
 * v3.0: NON-BLOCKING - Banner shows immediately based on local state.
 * v3.1: FIX - Added localStorage persistence to prevent banner from showing
 *       when user is already subscribed but SW is still initializing.
 */
import React, { useState, useEffect } from 'react';
import { Bell, X, Check, AlertTriangle } from 'lucide-react';
import { Button } from './ui/button';
import { useAuth } from '../contexts/AuthContext';
import usePushNotifications from '../hooks/usePushNotifications';

// LocalStorage key to track successful push subscription
const PUSH_SUBSCRIBED_KEY = 'push_subscription_active';
const PUSH_DISMISSED_KEY = 'push_banner_dismissed_v2';

const PushPermissionBanner = ({ onSubscribed }) => {
  const { user } = useAuth();
  const {
    isSupported,
    permission,
    isSubscribed,
    isLoading,
    error,
    subscribe,
    isInitialized  // v3.0: Fast local check, not backend sync
  } = usePushNotifications();
  
  const [show, setShow] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  // v3.1: Sync localStorage with hook state when subscription state changes
  useEffect(() => {
    if (isInitialized && isSubscribed) {
      // User is subscribed, mark in localStorage
      localStorage.setItem(PUSH_SUBSCRIBED_KEY, 'true');
    }
  }, [isInitialized, isSubscribed]);

  useEffect(() => {
    const checkPermission = () => {
      // v3.1: FAST CHECK - Check localStorage first before waiting for SW
      // This prevents banner flash when user is subscribed but SW is still loading
      const storedSubscriptionState = localStorage.getItem(PUSH_SUBSCRIBED_KEY);
      if (storedSubscriptionState === 'true') {
        console.log('[Push] Already subscribed (localStorage cache hit)');
        return; // Don't show banner - user was previously subscribed
      }

      // v3.0: Wait for fast local SW check
      if (!isInitialized) {
        console.log('[Push] Waiting for local SW check...');
        return;
      }

      // Don't show if not supported
      if (!isSupported) {
        console.log('[Push] Not supported in this browser');
        return;
      }

      // Don't show if already subscribed (based on local SW state)
      if (isSubscribed) {
        console.log('[Push] Already subscribed (local SW check)');
        // Also update localStorage for future fast checks
        localStorage.setItem(PUSH_SUBSCRIBED_KEY, 'true');
        return;
      }

      // Don't show if permission is denied
      if (permission === 'denied') {
        console.log('[Push] Permission denied by user');
        return;
      }

      // Don't show if permission is granted but not subscribed
      // This means user previously subscribed and then unsubscribed
      // They should use settings to re-enable, not the banner
      if (permission === 'granted') {
        console.log('[Push] Permission granted but not subscribed - user likely unsubscribed');
        // Clear the localStorage cache since user is not actually subscribed
        localStorage.removeItem(PUSH_SUBSCRIBED_KEY);
        // Don't show banner for users who explicitly unsubscribed
        // They can re-enable from settings
        return;
      }

      // Don't show if user dismissed recently (1 hour cooldown)
      const dismissedAt = localStorage.getItem(PUSH_DISMISSED_KEY);
      if (dismissedAt) {
        const dismissedTime = new Date(dismissedAt).getTime();
        const hourAgo = Date.now() - (60 * 60 * 1000);
        if (dismissedTime > hourAgo) {
          console.log('[Push] Banner dismissed recently, cooldown active');
          return;
        }
      }

      // Show banner after a short delay for ALL authenticated users
      // Only show if permission is 'default' (never asked before)
      console.log(`[Push] Showing banner for role: ${user?.roles?.join(', ')}, permission: ${permission}`);
      setTimeout(() => setShow(true), 2000);
    };

    if (user) {
      checkPermission();
    }
  }, [isSupported, isSubscribed, permission, user, isInitialized]);

  const handleEnable = async () => {
    try {
      const success = await subscribe();
      
      if (success) {
        console.log(`[Push] Subscription created for role: ${user?.roles?.join(', ')}`);
        // v3.1: Mark as subscribed in localStorage for future fast checks
        localStorage.setItem(PUSH_SUBSCRIBED_KEY, 'true');
        setShowSuccess(true);
        onSubscribed?.();
        setTimeout(() => setShow(false), 2000);
      }
    } catch (err) {
      console.error('[Push] Error enabling push:', err);
    }
  };

  const handleDismiss = () => {
    localStorage.setItem(PUSH_DISMISSED_KEY, new Date().toISOString());
    setDismissed(true);
    setTimeout(() => setShow(false), 300);
  };

  if (!show) return null;

  if (showSuccess) {
    return (
      <div 
        className={`
          fixed bottom-20 left-4 right-4 z-50 
          sm:left-auto sm:right-4 sm:max-w-md
          bg-gradient-to-r from-green-600 to-green-700
          rounded-xl shadow-2xl border border-green-500/30
          p-4 flex items-center gap-3
          animate-in slide-in-from-bottom-4 duration-300
        `}
        data-testid="push-success-banner"
      >
        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
          <Check className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-white font-semibold text-sm">
            ¡Notificaciones activadas!
          </p>
          <p className="text-white/80 text-xs mt-0.5">
            Recibirás alertas de visitas y reservaciones
          </p>
        </div>
      </div>
    );
  }

  return (
    <div 
      className={`
        fixed bottom-20 left-4 right-4 z-50 
        sm:left-auto sm:right-4 sm:max-w-md
        bg-gradient-to-r from-cyan-600 to-cyan-700
        rounded-xl shadow-2xl border border-cyan-500/30
        p-4 flex items-center gap-3
        animate-in slide-in-from-bottom-4 duration-300
        ${dismissed ? 'opacity-0 translate-y-4' : ''}
        transition-all
      `}
      data-testid="push-permission-banner"
    >
      {/* Icon */}
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
        <Bell className="w-5 h-5 text-white" />
      </div>
      
      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-white font-semibold text-sm">
          Activa las notificaciones
        </p>
        <p className="text-white/80 text-xs mt-0.5">
          Recibe alertas de visitas y reservaciones
        </p>
        {error && (
          <p className="text-red-200 text-xs mt-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            {error}
          </p>
        )}
      </div>
      
      {/* Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <Button
          size="sm"
          variant="secondary"
          className="bg-white/20 hover:bg-white/30 text-white border-0 text-xs px-3"
          onClick={handleEnable}
          disabled={isLoading}
          data-testid="enable-push-btn"
        >
          {isLoading ? 'Activando...' : 'Activar'}
        </Button>
        <button
          onClick={handleDismiss}
          className="p-1 rounded-full hover:bg-white/20 transition-colors"
          aria-label="Cerrar"
          data-testid="dismiss-push-btn"
        >
          <X className="w-4 h-4 text-white/80" />
        </button>
      </div>
    </div>
  );
};

export default PushPermissionBanner;
