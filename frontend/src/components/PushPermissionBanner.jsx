/**
 * GENTURIX Push Permission Request Component
 * Shows a friendly banner to request push notification permission
 * 
 * Note: For Guards, push is auto-registered on login via AuthContext.
 * This banner is for other roles (Residents) who want notifications.
 */
import React, { useState, useEffect } from 'react';
import { Bell, X } from 'lucide-react';
import { Button } from './ui/button';
import { PushNotificationManager } from '../utils/PushNotificationManager';

const PushPermissionBanner = ({ onSubscribed }) => {
  const [show, setShow] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const checkPermission = () => {
      // Don't show if not supported
      if (!PushNotificationManager.isSupported()) {
        return;
      }

      // Don't show if already granted or denied
      const permission = PushNotificationManager.getPermissionStatus();
      if (permission === 'granted' || permission === 'denied') {
        return;
      }

      // Don't show if user dismissed recently (1 hour cooldown)
      const dismissedAt = localStorage.getItem('push_banner_dismissed');
      if (dismissedAt) {
        const dismissedTime = new Date(dismissedAt).getTime();
        const hourAgo = Date.now() - (60 * 60 * 1000);
        if (dismissedTime > hourAgo) {
          return;
        }
      }

      // Show banner after a delay
      setTimeout(() => setShow(true), 3000);
    };

    checkPermission();
  }, []);

  const handleEnable = async () => {
    setIsLoading(true);
    try {
      const permission = await PushNotificationManager.requestPermission();
      
      if (permission === 'granted') {
        // Push registration will happen on next login for Guards
        // For other roles, they can subscribe manually
        onSubscribed?.();
        setShow(false);
      } else if (permission === 'denied') {
        setShow(false);
      }
    } catch (error) {
      console.error('Error enabling push:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDismiss = () => {
    localStorage.setItem('push_banner_dismissed', new Date().toISOString());
    setDismissed(true);
    setTimeout(() => setShow(false), 300);
  };

  if (!show) return null;

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
      </div>
      
      {/* Actions */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <Button
          size="sm"
          variant="secondary"
          className="bg-white/20 hover:bg-white/30 text-white border-0 text-xs px-3"
          onClick={handleEnable}
          disabled={isLoading}
        >
          {isLoading ? 'Activando...' : 'Activar'}
        </Button>
        <button
          onClick={handleDismiss}
          className="p-1 rounded-full hover:bg-white/20 transition-colors"
          aria-label="Cerrar"
        >
          <X className="w-4 h-4 text-white/80" />
        </button>
      </div>
    </div>
  );
};

export default PushPermissionBanner;
