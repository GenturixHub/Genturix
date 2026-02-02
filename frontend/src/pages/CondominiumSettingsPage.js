/**
 * GENTURIX - Condominium Settings Page
 * Admin can configure operational rules for the condominium
 * Settings affect: reservations, visits, notifications
 */

import React, { useState, useEffect, useCallback } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { useIsMobile } from '../components/layout/BottomNav';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import api from '../services/api';
import {
  Settings,
  Building,
  Calendar,
  Users,
  Bell,
  Loader2,
  Save,
  Clock,
  Globe,
  CheckCircle,
  Shield,
  AlertTriangle
} from 'lucide-react';

// Timezone options for Mexico (can be expanded)
const TIMEZONE_OPTIONS = [
  { value: 'America/Mexico_City', label: 'Ciudad de México (GMT-6)' },
  { value: 'America/Tijuana', label: 'Tijuana (GMT-8)' },
  { value: 'America/Cancun', label: 'Cancún (GMT-5)' },
  { value: 'America/Hermosillo', label: 'Hermosillo (GMT-7)' },
  { value: 'America/Bogota', label: 'Bogotá (GMT-5)' },
  { value: 'America/Lima', label: 'Lima (GMT-5)' },
  { value: 'America/Santiago', label: 'Santiago (GMT-3)' },
  { value: 'America/Buenos_Aires', label: 'Buenos Aires (GMT-3)' },
];

const CondominiumSettingsPage = () => {
  const isMobile = useIsMobile();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('general');
  const [hasChanges, setHasChanges] = useState(false);
  
  // Settings state
  const [settings, setSettings] = useState({
    condominium_id: '',
    condominium_name: '',
    general: {
      timezone: 'America/Mexico_City',
      working_hours: { start: '06:00', end: '22:00' },
      condominium_name_display: null
    },
    reservations: {
      enabled: true,
      max_active_per_user: 3,
      allow_same_day: true,
      approval_required_by_default: false,
      min_hours_advance: 1,
      max_days_advance: 30
    },
    visits: {
      allow_resident_preregistration: true,
      allow_recurrent_visits: true,
      allow_permanent_visits: false,
      require_id_photo: false,
      max_preregistrations_per_day: 10
    },
    notifications: {
      panic_sound_enabled: true,
      push_enabled: true,
      email_notifications_enabled: true
    }
  });
  
  // Original settings for comparison
  const [originalSettings, setOriginalSettings] = useState(null);
  
  // Load settings
  const fetchSettings = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getCondominiumSettings();
      setSettings(data);
      setOriginalSettings(JSON.stringify(data));
      setHasChanges(false);
    } catch (err) {
      console.error('Error fetching settings:', err);
      toast.error('Error al cargar configuración');
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);
  
  // Check for changes
  useEffect(() => {
    if (originalSettings) {
      setHasChanges(JSON.stringify(settings) !== originalSettings);
    }
  }, [settings, originalSettings]);
  
  // Update nested settings
  const updateSetting = (section, field, value) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value
      }
    }));
  };
  
  // Update working hours
  const updateWorkingHours = (field, value) => {
    setSettings(prev => ({
      ...prev,
      general: {
        ...prev.general,
        working_hours: {
          ...prev.general.working_hours,
          [field]: value
        }
      }
    }));
  };
  
  // Save settings
  const handleSave = async () => {
    setSaving(true);
    try {
      const updateData = {
        general: settings.general,
        reservations: settings.reservations,
        visits: settings.visits,
        notifications: settings.notifications
      };
      
      await api.updateCondominiumSettings(updateData);
      toast.success('Configuración guardada exitosamente');
      setOriginalSettings(JSON.stringify(settings));
      setHasChanges(false);
    } catch (err) {
      console.error('Error saving settings:', err);
      toast.error(err.message || 'Error al guardar configuración');
    } finally {
      setSaving(false);
    }
  };
  
  // Discard changes
  const handleDiscard = () => {
    if (originalSettings) {
      setSettings(JSON.parse(originalSettings));
      setHasChanges(false);
      toast.info('Cambios descartados');
    }
  };
  
  if (loading) {
    return (
      <DashboardLayout title="Configuración">
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }
  
  return (
    <DashboardLayout title="Configuración">
      <div className="space-y-6 pb-24 md:pb-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Settings className="w-6 h-6 text-primary" />
              Configuración del Condominio
            </h1>
            <p className="text-muted-foreground mt-1">
              {settings.condominium_name}
            </p>
          </div>
          
          {/* Save Button */}
          <div className="flex items-center gap-3">
            {hasChanges && (
              <Button variant="outline" onClick={handleDiscard} data-testid="discard-settings">
                Descartar
              </Button>
            )}
            <Button 
              onClick={handleSave} 
              disabled={saving || !hasChanges}
              className={hasChanges ? 'animate-pulse' : ''}
              data-testid="save-settings"
            >
              {saving ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              Guardar Configuración
            </Button>
          </div>
        </div>
        
        {/* Unsaved changes warning */}
        {hasChanges && (
          <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0" />
            <p className="text-sm text-yellow-400">Tienes cambios sin guardar</p>
          </div>
        )}
        
        {/* Settings Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className={`grid w-full ${isMobile ? 'grid-cols-2' : 'grid-cols-4'} bg-[#0F111A] border border-[#1E293B]`}>
            <TabsTrigger value="general" className="data-[state=active]:bg-primary/20" data-testid="tab-general">
              <Building className="w-4 h-4 mr-2" />
              {!isMobile && 'General'}
            </TabsTrigger>
            <TabsTrigger value="reservations" className="data-[state=active]:bg-primary/20" data-testid="tab-reservations">
              <Calendar className="w-4 h-4 mr-2" />
              {!isMobile && 'Reservas'}
            </TabsTrigger>
            <TabsTrigger value="visits" className="data-[state=active]:bg-primary/20" data-testid="tab-visits">
              <Users className="w-4 h-4 mr-2" />
              {!isMobile && 'Visitas'}
            </TabsTrigger>
            <TabsTrigger value="notifications" className="data-[state=active]:bg-primary/20" data-testid="tab-notifications">
              <Bell className="w-4 h-4 mr-2" />
              {!isMobile && 'Notificaciones'}
            </TabsTrigger>
          </TabsList>
          
          {/* General Settings */}
          <TabsContent value="general" className="mt-6">
            <Card className="bg-[#0F111A] border-[#1E293B]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building className="w-5 h-5 text-primary" />
                  Configuración General
                </CardTitle>
                <CardDescription>
                  Ajustes básicos del condominio
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Timezone */}
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Globe className="w-4 h-4" />
                    Zona Horaria
                  </Label>
                  <Select 
                    value={settings.general.timezone} 
                    onValueChange={(v) => updateSetting('general', 'timezone', v)}
                  >
                    <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]" data-testid="timezone-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                      {TIMEZONE_OPTIONS.map(tz => (
                        <SelectItem key={tz.value} value={tz.value}>{tz.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Esta zona horaria se usa para reservaciones y registros de tiempo
                  </p>
                </div>
                
                {/* Working Hours */}
                <div className="space-y-3">
                  <Label className="flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    Horario de Operación
                  </Label>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <Label className="text-xs text-muted-foreground">Hora de Inicio</Label>
                      <Input
                        type="time"
                        value={settings.general.working_hours.start}
                        onChange={(e) => updateWorkingHours('start', e.target.value)}
                        className="bg-[#0A0A0F] border-[#1E293B]"
                        data-testid="working-hours-start"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-muted-foreground">Hora de Cierre</Label>
                      <Input
                        type="time"
                        value={settings.general.working_hours.end}
                        onChange={(e) => updateWorkingHours('end', e.target.value)}
                        className="bg-[#0A0A0F] border-[#1E293B]"
                        data-testid="working-hours-end"
                      />
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Horario general de operaciones del condominio
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* Reservations Settings */}
          <TabsContent value="reservations" className="mt-6">
            <Card className="bg-[#0F111A] border-[#1E293B]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-blue-400" />
                  Configuración de Reservaciones
                </CardTitle>
                <CardDescription>
                  Reglas para el sistema de reservas de áreas comunes
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Enable Reservations */}
                <div className="flex items-center justify-between p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                  <div className="space-y-0.5">
                    <Label className="text-base">Reservaciones Habilitadas</Label>
                    <p className="text-sm text-muted-foreground">
                      Permite a los residentes reservar áreas comunes
                    </p>
                  </div>
                  <Switch
                    checked={settings.reservations.enabled}
                    onCheckedChange={(v) => updateSetting('reservations', 'enabled', v)}
                    data-testid="reservations-enabled"
                  />
                </div>
                
                {settings.reservations.enabled && (
                  <>
                    {/* Max Active Reservations */}
                    <div className="space-y-2">
                      <Label>Máximo de reservas activas por residente</Label>
                      <Select 
                        value={String(settings.reservations.max_active_per_user)} 
                        onValueChange={(v) => updateSetting('reservations', 'max_active_per_user', parseInt(v))}
                      >
                        <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]" data-testid="max-reservations">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                          {[1, 2, 3, 5, 10, 20].map(n => (
                            <SelectItem key={n} value={String(n)}>{n} reserva{n > 1 ? 's' : ''}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    {/* Allow Same Day */}
                    <div className="flex items-center justify-between p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                      <div className="space-y-0.5">
                        <Label>Permitir reservas el mismo día</Label>
                        <p className="text-sm text-muted-foreground">
                          Los residentes pueden reservar áreas para el día actual
                        </p>
                      </div>
                      <Switch
                        checked={settings.reservations.allow_same_day}
                        onCheckedChange={(v) => updateSetting('reservations', 'allow_same_day', v)}
                        data-testid="allow-same-day"
                      />
                    </div>
                    
                    {/* Approval Required */}
                    <div className="flex items-center justify-between p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                      <div className="space-y-0.5">
                        <Label>Requerir aprobación por defecto</Label>
                        <p className="text-sm text-muted-foreground">
                          Las nuevas reservas necesitan aprobación del admin
                        </p>
                      </div>
                      <Switch
                        checked={settings.reservations.approval_required_by_default}
                        onCheckedChange={(v) => updateSetting('reservations', 'approval_required_by_default', v)}
                        data-testid="approval-required"
                      />
                    </div>
                    
                    {/* Advance Booking Limits */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Horas mínimas de anticipación</Label>
                        <Select 
                          value={String(settings.reservations.min_hours_advance)} 
                          onValueChange={(v) => updateSetting('reservations', 'min_hours_advance', parseInt(v))}
                        >
                          <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                            {[0, 1, 2, 4, 8, 12, 24, 48].map(n => (
                              <SelectItem key={n} value={String(n)}>{n} hora{n !== 1 ? 's' : ''}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>Días máximos de anticipación</Label>
                        <Select 
                          value={String(settings.reservations.max_days_advance)} 
                          onValueChange={(v) => updateSetting('reservations', 'max_days_advance', parseInt(v))}
                        >
                          <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                            {[7, 14, 30, 60, 90, 180, 365].map(n => (
                              <SelectItem key={n} value={String(n)}>{n} días</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* Visits Settings */}
          <TabsContent value="visits" className="mt-6">
            <Card className="bg-[#0F111A] border-[#1E293B]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-green-400" />
                  Configuración de Visitas
                </CardTitle>
                <CardDescription>
                  Reglas para el registro de visitantes
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Allow Pre-registration */}
                <div className="flex items-center justify-between p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                  <div className="space-y-0.5">
                    <Label className="text-base">Pre-registro por residentes</Label>
                    <p className="text-sm text-muted-foreground">
                      Los residentes pueden pre-autorizar visitas
                    </p>
                  </div>
                  <Switch
                    checked={settings.visits.allow_resident_preregistration}
                    onCheckedChange={(v) => updateSetting('visits', 'allow_resident_preregistration', v)}
                    data-testid="allow-preregistration"
                  />
                </div>
                
                {/* Allow Recurrent Visits */}
                <div className="flex items-center justify-between p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                  <div className="space-y-0.5">
                    <Label className="text-base">Visitas recurrentes</Label>
                    <p className="text-sm text-muted-foreground">
                      Permitir autorización de visitas que se repiten
                    </p>
                  </div>
                  <Switch
                    checked={settings.visits.allow_recurrent_visits}
                    onCheckedChange={(v) => updateSetting('visits', 'allow_recurrent_visits', v)}
                    data-testid="allow-recurrent"
                  />
                </div>
                
                {/* Allow Permanent Visits */}
                <div className="flex items-center justify-between p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                  <div className="space-y-0.5">
                    <Label className="text-base">Visitas permanentes</Label>
                    <p className="text-sm text-muted-foreground">
                      Autorizar visitantes con acceso permanente
                    </p>
                  </div>
                  <Switch
                    checked={settings.visits.allow_permanent_visits}
                    onCheckedChange={(v) => updateSetting('visits', 'allow_permanent_visits', v)}
                    data-testid="allow-permanent"
                  />
                </div>
                
                {/* Require ID Photo */}
                <div className="flex items-center justify-between p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                  <div className="space-y-0.5">
                    <Label className="text-base">Requerir foto de identificación</Label>
                    <p className="text-sm text-muted-foreground">
                      Los guardias deben capturar foto de ID
                    </p>
                  </div>
                  <Switch
                    checked={settings.visits.require_id_photo}
                    onCheckedChange={(v) => updateSetting('visits', 'require_id_photo', v)}
                    data-testid="require-id-photo"
                  />
                </div>
                
                {/* Max Pre-registrations */}
                <div className="space-y-2">
                  <Label>Máximo de pre-registros por día por residente</Label>
                  <Select 
                    value={String(settings.visits.max_preregistrations_per_day)} 
                    onValueChange={(v) => updateSetting('visits', 'max_preregistrations_per_day', parseInt(v))}
                  >
                    <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]" data-testid="max-preregistrations">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                      {[5, 10, 15, 20, 30, 50].map(n => (
                        <SelectItem key={n} value={String(n)}>{n} pre-registros</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* Notifications Settings */}
          <TabsContent value="notifications" className="mt-6">
            <Card className="bg-[#0F111A] border-[#1E293B]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="w-5 h-5 text-yellow-400" />
                  Configuración de Notificaciones
                </CardTitle>
                <CardDescription>
                  Controla cómo se envían alertas y notificaciones
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Panic Sound */}
                <div className="flex items-center justify-between p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                  <div className="space-y-0.5">
                    <Label className="text-base flex items-center gap-2">
                      <Shield className="w-4 h-4 text-red-400" />
                      Sonido de alerta de pánico
                    </Label>
                    <p className="text-sm text-muted-foreground">
                      Reproducir sonido cuando se active el botón de pánico
                    </p>
                  </div>
                  <Switch
                    checked={settings.notifications.panic_sound_enabled}
                    onCheckedChange={(v) => updateSetting('notifications', 'panic_sound_enabled', v)}
                    data-testid="panic-sound"
                  />
                </div>
                
                {/* Push Notifications */}
                <div className="flex items-center justify-between p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                  <div className="space-y-0.5">
                    <Label className="text-base">Notificaciones Push</Label>
                    <p className="text-sm text-muted-foreground">
                      Enviar notificaciones push a dispositivos móviles
                    </p>
                  </div>
                  <Switch
                    checked={settings.notifications.push_enabled}
                    onCheckedChange={(v) => updateSetting('notifications', 'push_enabled', v)}
                    data-testid="push-enabled"
                  />
                </div>
                
                {/* Email Notifications */}
                <div className="flex items-center justify-between p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                  <div className="space-y-0.5">
                    <Label className="text-base">Notificaciones por Email</Label>
                    <p className="text-sm text-muted-foreground">
                      Enviar notificaciones por correo electrónico
                    </p>
                  </div>
                  <Switch
                    checked={settings.notifications.email_notifications_enabled}
                    onCheckedChange={(v) => updateSetting('notifications', 'email_notifications_enabled', v)}
                    data-testid="email-enabled"
                  />
                </div>
                
                {/* Info box */}
                <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                  <div className="flex items-start gap-3">
                    <CheckCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm text-blue-400 font-medium">Nota importante</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Las notificaciones de seguridad críticas (como alertas de pánico) siempre se enviarán 
                        independientemente de esta configuración para garantizar la seguridad de los residentes.
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
        
        {/* Mobile Save Button (fixed at bottom) */}
        {isMobile && hasChanges && (
          <div className="fixed bottom-16 left-0 right-0 p-4 bg-[#0A0A0F]/95 backdrop-blur-lg border-t border-[#1E293B]">
            <Button 
              onClick={handleSave} 
              disabled={saving}
              className="w-full"
              data-testid="mobile-save-settings"
            >
              {saving ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              Guardar Configuración
            </Button>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default CondominiumSettingsPage;
