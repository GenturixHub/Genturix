import React, { useState, useEffect } from 'react';
import { Bell, BellOff, X, Check, AlertTriangle } from 'lucide-react';
import { Button } from '../components/ui/button';
import usePushNotifications from '../hooks/usePushNotifications';

export function PushNotificationBanner({ onClose }) {
  const {
    isSupported,
    permission,
    isSubscribed,
    isLoading,
    error,
    subscribe
  } = usePushNotifications();

  const [dismissed, setDismissed] = useState(false);
  // Initialize dismissed state from localStorage
  const [dismissed, setDismissed] = useState(() => {
    return localStorage.getItem('push_banner_dismissed') === 'true';
  });
  const [showSuccess, setShowSuccess] = useState(false);

  // Don't show if not supported, already subscribed, permission denied, or dismissed
  if (!isSupported || isSubscribed || permission === 'denied' || dismissed) {
    return null;
  }

  const handleSubscribe = async () => {
    const success = await subscribe();
    if (success) {
      setShowSuccess(true);
      setTimeout(() => {
        onClose?.();
      }, 2000);
    }
  };

  const handleDismiss = () => {
    localStorage.setItem('push_banner_dismissed', 'true');
    setDismissed(true);
    onClose?.();
  };

  if (showSuccess) {
    return (
      <div 
        className="bg-green-500/10 border border-green-500/30 rounded-lg p-4 mb-4 animate-in slide-in-from-top duration-300"
        data-testid="push-success-banner"
      >
        <div className="flex items-center gap-3">
          <Check className="h-5 w-5 text-green-400" />
          <span className="text-green-100 font-medium">
            ¡Notificaciones activadas correctamente!
          </span>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="bg-gradient-to-r from-amber-500/10 to-orange-500/10 border border-amber-500/30 rounded-lg p-4 mb-4 animate-in slide-in-from-top duration-300"
      data-testid="push-notification-banner"
    >
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-start gap-3 flex-1">
          <div className="p-2 bg-amber-500/20 rounded-full">
            <Bell className="h-5 w-5 text-amber-400 animate-pulse" />
          </div>
          <div className="flex-1">
            <h4 className="text-white font-semibold text-sm mb-1">
              Activa las Notificaciones Push
            </h4>
            <p className="text-gray-400 text-xs leading-relaxed">
              Recibe alertas de pánico en tiempo real, incluso cuando la app esté cerrada.
              Esencial para responder rápidamente a emergencias.
            </p>
            {error && (
              <p className="text-red-400 text-xs mt-1 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                {error}
              </p>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Button
            onClick={handleSubscribe}
            disabled={isLoading}
            className="flex-1 sm:flex-none bg-amber-500 hover:bg-amber-600 text-black font-medium text-sm px-4 py-2"
            data-testid="enable-push-btn"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                Activando...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Bell className="h-4 w-4" />
                Activar
              </span>
            )}
          </Button>
          <Button
            onClick={handleDismiss}
            variant="ghost"
            size="icon"
            className="text-gray-400 hover:text-white hover:bg-white/10"
            data-testid="dismiss-push-btn"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// Toggle component for settings/profile
export function PushNotificationToggle() {
  const {
    isSupported,
    permission,
    isSubscribed,
    isLoading,
    error,
    subscribe,
    unsubscribe
  } = usePushNotifications();

  if (!isSupported) {
    return (
      <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
        <div className="flex items-center gap-3">
          <BellOff className="h-5 w-5 text-gray-500" />
          <div>
            <p className="text-sm text-gray-400">Notificaciones Push</p>
            <p className="text-xs text-gray-500">No soportado en este navegador</p>
          </div>
        </div>
      </div>
    );
  }

  if (permission === 'denied') {
    return (
      <div className="flex items-center justify-between p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
        <div className="flex items-center gap-3">
          <BellOff className="h-5 w-5 text-red-400" />
          <div>
            <p className="text-sm text-red-300">Notificaciones Bloqueadas</p>
            <p className="text-xs text-red-400/70">Habilítalas desde la configuración del navegador</p>
          </div>
        </div>
      </div>
    );
  }

  const handleToggle = async () => {
    if (isSubscribed) {
      await unsubscribe();
    } else {
      await subscribe();
    }
  };

  return (
    <div 
      className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg"
      data-testid="push-notification-toggle"
    >
      <div className="flex items-center gap-3">
        {isSubscribed ? (
          <Bell className="h-5 w-5 text-green-400" />
        ) : (
          <BellOff className="h-5 w-5 text-gray-400" />
        )}
        <div>
          <p className="text-sm text-white">Notificaciones Push</p>
          <p className="text-xs text-gray-400">
            {isSubscribed ? 'Recibirás alertas de pánico' : 'Activa para recibir alertas'}
          </p>
          {error && <p className="text-xs text-red-400 mt-1">{error}</p>}
        </div>
      </div>
      <Button
        onClick={handleToggle}
        disabled={isLoading}
        variant={isSubscribed ? "destructive" : "default"}
        size="sm"
        className={isSubscribed ? '' : 'bg-primary hover:bg-primary/90'}
        data-testid="toggle-push-btn"
      >
        {isLoading ? (
          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : isSubscribed ? (
          'Desactivar'
        ) : (
          'Activar'
        )}
      </Button>
    </div>
  );
}

export default PushNotificationBanner;
