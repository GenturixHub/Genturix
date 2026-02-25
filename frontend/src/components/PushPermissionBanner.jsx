/**
 * GENTURIX Push Permission Request Component
 * Shows a friendly banner to request push notification permission
 * 
 * Works for ALL roles - Guards, Residents, Admins, etc.
 * Uses usePushNotifications hook for proper subscription handling.
 * 
 * IMPORTANT: This component waits for sync to complete before rendering
 * to prevent false-positive "activate notifications" prompts.
 */
import React, { useState, useEffect } from 'react';
import { Bell, X, Check, AlertTriangle, Loader2 } from 'lucide-react';
import { Button } from './ui/button';
import { useAuth } from '../contexts/AuthContext';
import usePushNotifications from '../hooks/usePushNotifications';

const PushPermissionBanner = ({ onSubscribed }) => {
  const { user } = useAuth();
  const {
    isSupported,
    permission,
    isSubscribed,
    isLoading,
    error,
    subscribe,
    isSyncing,  // NEW: Wait for sync
    isSynced    // NEW: Only show after sync complete
  } = usePushNotifications();
  
  const [show, setShow] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  useEffect(() => {
    const checkPermission = () => {
      // CRITICAL: Don't show until sync is complete
      // This prevents false prompts after login
      if (!isSynced || isSyncing) {
        console.log('[Push] Waiting for sync to complete before showing banner');
        return;
      }

      // Don't show if not supported
      if (!isSupported) {
        console.log('[Push] Not supported in this browser');
        return;
      }

      // Don't show if already subscribed (verified with backend)
      if (isSubscribed) {
        console.log('[Push] Already subscribed (confirmed with backend)');
        return;
      }

      // Don't show if permission denied
      if (permission === 'denied') {
        console.log('[Push] Permission denied by user');
        return;
      }

      // Don't show if user dismissed recently (1 hour cooldown)
      const dismissedAt = localStorage.getItem('push_banner_dismissed_v2');
      if (dismissedAt) {
        const dismissedTime = new Date(dismissedAt).getTime();
        const hourAgo = Date.now() - (60 * 60 * 1000);
        if (dismissedTime > hourAgo) {
          return;
        }
      }

      // Show banner after a delay for ALL authenticated users
      console.log(`[Push] Showing banner for role: ${user?.roles?.join(', ')} (sync confirmed: no active subscription)`);
      setTimeout(() => setShow(true), 3000);
    };

    if (user) {
      checkPermission();
    }
  }, [isSupported, isSubscribed, permission, user, isSynced, isSyncing]);

  const handleEnable = async () => {
    try {
      const success = await subscribe();
      
      if (success) {
        console.log(`[Push] Subscription created for role: ${user?.roles?.join(', ')}`);
        setShowSuccess(true);
        onSubscribed?.();
        setTimeout(() => setShow(false), 2000);
      }
    } catch (err) {
      console.error('[Push] Error enabling push:', err);
    }
  };

  const handleDismiss = () => {
    localStorage.setItem('push_banner_dismissed_v2', new Date().toISOString());
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
