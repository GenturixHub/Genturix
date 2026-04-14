import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { toast } from 'sonner';
import api from '../services/api';
import { Settings2, Loader2 } from 'lucide-react';

const ToggleRow = ({ label, description, checked, onChange, testId }) => (
  <div className="flex items-center justify-between py-3 border-b border-[#1E293B]/50 last:border-b-0">
    <div>
      <p className="text-sm text-white">{label}</p>
      {description && <p className="text-xs text-muted-foreground">{description}</p>}
    </div>
    <button
      data-testid={testId}
      onClick={() => onChange(!checked)}
      className={`relative w-10 h-5 rounded-full transition-colors ${
        checked ? 'bg-primary' : 'bg-[#1E293B]'
      }`}
    >
      <span
        className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
          checked ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  </div>
);

export default function NotificationPreferences() {
  const { t } = useTranslation();
  const [prefs, setPrefs] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.getNotificationPreferencesV2();
        setPrefs(data);
      } catch {
        setPrefs({
          broadcasts_enabled: true,
          alerts_enabled: true,
          system_enabled: true,
          email_notifications: false,
        });
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleToggle = async (field, value) => {
    setPrefs((prev) => ({ ...prev, [field]: value }));
    setSaving(true);
    try {
      const updated = await api.updateNotificationPreferencesV2({ [field]: value });
      setPrefs(updated);
    } catch {
      toast.error('Error al guardar preferencias');
      setPrefs((prev) => ({ ...prev, [field]: !value }));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]" data-testid="notification-preferences">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-base">
          <Settings2 className="w-4 h-4 text-primary" />
          {t('notifications.preferences', 'Preferencias de Notificaciones')}
          {saving && <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ToggleRow
          label={t('notifications.prefBroadcasts', 'Broadcasts')}
          description={t('notifications.prefBroadcastsDesc', 'Recibir anuncios del administrador')}
          checked={prefs?.broadcasts_enabled ?? true}
          onChange={(v) => handleToggle('broadcasts_enabled', v)}
          testId="pref-toggle-broadcasts"
        />
        <ToggleRow
          label={t('notifications.prefAlerts', 'Alertas')}
          description={t('notifications.prefAlertsDesc', 'Alertas de seguridad y emergencias')}
          checked={prefs?.alerts_enabled ?? true}
          onChange={(v) => handleToggle('alerts_enabled', v)}
          testId="pref-toggle-alerts"
        />
        <ToggleRow
          label={t('notifications.prefSystem', 'Sistema')}
          description={t('notifications.prefSystemDesc', 'Notificaciones del sistema')}
          checked={prefs?.system_enabled ?? true}
          onChange={(v) => handleToggle('system_enabled', v)}
          testId="pref-toggle-system"
        />
        <ToggleRow
          label={t('notifications.prefEmail', 'Email')}
          description={t('notifications.prefEmailDesc', 'Recibir notificaciones por correo')}
          checked={prefs?.email_notifications ?? false}
          onChange={(v) => handleToggle('email_notifications', v)}
          testId="pref-toggle-email"
        />
      </CardContent>
    </Card>
  );
}
