/**
 * GENTURIX Push Notification Toggle Component
 * Allows users to manually enable/disable push notifications
 * 
 * This is a persistent setting - not tied to login/logout
 */
import React, { useState, useEffect } from 'react';
import { Bell, BellOff, Loader2, AlertTriangle } from 'lucide-react';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { toast } from 'sonner';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const PushNotificationToggle = () => {
  const [isEnabled, setIsEnabled] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isToggling, setIsToggling] = useState(false);
  const [permission, setPermission] = useState('default');
  const [isSupported, setIsSupported] = useState(true);

  useEffect(() => {
    checkPushStatus();
  }, []);

  const checkPushStatus = async () => {
    try {
      // Check browser support
      if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        setIsSupported(false);
        setIsLoading(false);
        return;
      }

      // Get current permission
      const currentPermission = Notification.permission;
      setPermission(currentPermission);

      if (currentPermission !== 'granted') {
        setIsEnabled(false);
        setIsLoading(false);
        return;
      }

      // Check if subscription exists
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      
      const hasSubscription = !!subscription;
      const localEnabled = localStorage.getItem('genturix_push_enabled') === 'true';
      
      setIsEnabled(hasSubscription && localEnabled);
      setIsLoading(false);
    } catch (error) {
      console.error('[PushToggle] Error checking status:', error);
      setIsLoading(false);
    }
  };

  const handleEnable = async () => {
    setIsToggling(true);
    try {
      // Request permission if needed
      if (Notification.permission === 'default') {
        const result = await Notification.requestPermission();
        setPermission(result);
        if (result !== 'granted') {
          toast.error('Permiso de notificaciones denegado');
          setIsToggling(false);
          return;
        }
      }

      if (Notification.permission === 'denied') {
        toast.error('Las notificaciones están bloqueadas. Habilítalas en la configuración del navegador.');
        setIsToggling(false);
        return;
      }

      // Get VAPID key
      const vapidResponse = await fetch(`${API_URL}/api/push/vapid-public-key`);
      if (!vapidResponse.ok) throw new Error('Failed to get VAPID key');
      const { publicKey } = await vapidResponse.json();

      // Subscribe
      const registration = await navigator.serviceWorker.ready;
      
      // Check for existing subscription first
      let subscription = await registration.pushManager.getSubscription();
      
      if (!subscription) {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(publicKey)
        });
      }

      // Send to backend
      const accessToken = localStorage.getItem('genturix_access_token');
      const subscriptionJson = subscription.toJSON();
      
      const response = await fetch(`${API_URL}/api/push/subscribe`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          endpoint: subscriptionJson.endpoint,
          keys: {
            p256dh: subscriptionJson.keys.p256dh,
            auth: subscriptionJson.keys.auth,
          },
          expirationTime: subscriptionJson.expirationTime,
        }),
      });

      if (response.ok) {
        localStorage.setItem('genturix_push_enabled', 'true');
        setIsEnabled(true);
        toast.success('Notificaciones push activadas');
        console.log('[PushToggle] Push enabled successfully');
      } else {
        throw new Error('Failed to register with server');
      }
    } catch (error) {
      console.error('[PushToggle] Error enabling:', error);
      toast.error('Error al activar notificaciones');
    } finally {
      setIsToggling(false);
    }
  };

  const handleDisable = async () => {
    setIsToggling(true);
    try {
      const accessToken = localStorage.getItem('genturix_access_token');
      
      // Unsubscribe from backend
      await fetch(`${API_URL}/api/push/unsubscribe-all`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
      });

      // Unsubscribe locally
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      if (subscription) {
        await subscription.unsubscribe();
      }

      localStorage.setItem('genturix_push_enabled', 'false');
      setIsEnabled(false);
      toast.success('Notificaciones push desactivadas');
      console.log('[PushToggle] Push disabled successfully');
    } catch (error) {
      console.error('[PushToggle] Error disabling:', error);
      toast.error('Error al desactivar notificaciones');
    } finally {
      setIsToggling(false);
    }
  };

  const handleToggle = () => {
    if (isEnabled) {
      handleDisable();
    } else {
      handleEnable();
    }
  };

  // Helper function to convert VAPID key
  const urlBase64ToUint8Array = (base64String) => {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  };

  if (!isSupported) {
    return (
      <Card className="bg-[#0F172A] border-[#1E293B]">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <BellOff className="w-4 h-4 text-gray-500" />
            Notificaciones Push
          </CardTitle>
          <CardDescription>No disponible en este navegador</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card className="bg-[#0F172A] border-[#1E293B]">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            Notificaciones Push
          </CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="bg-[#0F172A] border-[#1E293B]" data-testid="push-toggle-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          {isEnabled ? (
            <Bell className="w-4 h-4 text-cyan-400" />
          ) : (
            <BellOff className="w-4 h-4 text-gray-500" />
          )}
          Notificaciones Push
        </CardTitle>
        <CardDescription>
          {permission === 'denied' 
            ? 'Bloqueadas por el navegador'
            : isEnabled 
              ? 'Recibirás alertas de visitas y reservaciones'
              : 'Activa para recibir alertas importantes'
          }
        </CardDescription>
      </CardHeader>
      <CardContent>
        {permission === 'denied' ? (
          <div className="flex items-center gap-2 text-yellow-500 text-sm">
            <AlertTriangle className="w-4 h-4" />
            <span>Habilita las notificaciones en la configuración del navegador</span>
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">
              {isEnabled ? 'Activadas' : 'Desactivadas'}
            </span>
            <div className="flex items-center gap-3">
              {isToggling && <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />}
              <Switch
                checked={isEnabled}
                onCheckedChange={handleToggle}
                disabled={isToggling}
                data-testid="push-toggle-switch"
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default PushNotificationToggle;
