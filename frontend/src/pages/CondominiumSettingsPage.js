/**
 * GENTURIX - Condominium Settings Page
 * Admin configuration module - Mobile-first, collapsible sections
 * 
 * Sections:
 * 1. General - Name, timezone, working hours
 * 2. Reservations - Rules for common area bookings
 * 3. Visits - Visitor registration settings
 * 4. Security & Alerts - Panic, notifications
 * 5. System - Advanced settings (read-only info)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import DashboardLayout from '../components/layout/DashboardLayout';
import { useIsMobile } from '../components/layout/BottomNav';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '../components/ui/collapsible';
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
  Building2,
  Calendar,
  Users,
  Bell,
  Loader2,
  Save,
  Clock,
  Globe,
  CheckCircle,
  Shield,
  AlertTriangle,
  ChevronDown,
  Server,
  Mail,
  Volume2,
  VolumeX,
  UserPlus,
  KeyRound,
  RefreshCw
} from 'lucide-react';

// Timezone options
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

// Collapsible Section Component - Mobile optimized
const SettingsSection = ({ 
  icon: Icon, 
  title, 
  description, 
  children, 
  defaultOpen = false,
  badge = null,
  iconColor = 'text-primary'
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className="w-full">
      <Card className="bg-[#0F111A] border-[#1E293B] overflow-hidden">
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-[#1E293B]/30 transition-colors p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg bg-[#0A0A0F] ${iconColor}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div className="text-left">
                  <CardTitle className="text-base flex items-center gap-2">
                    {title}
                    {badge}
                  </CardTitle>
                  <CardDescription className="text-xs mt-0.5">
                    {description}
                  </CardDescription>
                </div>
              </div>
              <ChevronDown className={`w-5 h-5 text-muted-foreground transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="pt-0 pb-4 px-4 space-y-4 border-t border-[#1E293B]">
            {children}
          </CardContent>
        </CollapsibleContent>
      </Card>
    </Collapsible>
  );
};

// Toggle Setting Component - Consistent styling
const ToggleSetting = ({ label, description, checked, onChange, testId }) => (
  <div className="flex items-start justify-between gap-4 p-3 rounded-lg bg-[#0A0A0F]/50 border border-[#1E293B]/50">
    <div className="flex-1 min-w-0">
      <Label className="text-sm font-medium">{label}</Label>
      <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">{description}</p>
    </div>
    <Switch
      checked={checked}
      onCheckedChange={onChange}
      data-testid={testId}
      className="flex-shrink-0 mt-0.5"
    />
  </div>
);

const CondominiumSettingsPage = () => {
  const { t } = useTranslation();
  const isMobile = useIsMobile();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
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
      toast.error(t('settings.loadError', 'Error al cargar configuración'));
    } finally {
      setLoading(false);
    }
  }, [t]);
  
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
      toast.success(t('settings.settingsSaved'));
      setOriginalSettings(JSON.stringify(settings));
      setHasChanges(false);
    } catch (err) {
      console.error('Error saving settings:', err);
      toast.error(err.message || t('settings.saveError', 'Error al guardar'));
    } finally {
      setSaving(false);
    }
  };
  
  // Discard changes
  const handleDiscard = () => {
    if (originalSettings) {
      setSettings(JSON.parse(originalSettings));
      setHasChanges(false);
      toast.info(t('settings.changesDiscarded', 'Cambios descartados'));
    }
  };
  
  if (loading) {
    return (
      <DashboardLayout title={t('settings.title')}>
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center space-y-3">
            <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
            <p className="text-sm text-muted-foreground">{t('common.loading')}</p>
          </div>
        </div>
      </DashboardLayout>
    );
  }
  
  return (
    <DashboardLayout title={t('settings.title')}>
      <div className="space-y-4 pb-28 md:pb-6">
        {/* Header - Simplified for mobile */}
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary/10">
              <Settings className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold">{t('settings.title')}</h1>
              <p className="text-sm text-muted-foreground">{settings.condominium_name}</p>
            </div>
          </div>
          
          {/* Unsaved changes warning */}
          {hasChanges && (
            <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0" />
              <p className="text-sm text-yellow-400 flex-1">{t('settings.unsavedChanges', 'Tienes cambios sin guardar')}</p>
              {!isMobile && (
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" onClick={handleDiscard}>
                    {t('common.cancel')}
                  </Button>
                  <Button size="sm" onClick={handleSave} disabled={saving}>
                    {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4 mr-1" />}
                    {t('common.save')}
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* SECTION 1: General Settings */}
        <SettingsSection
          icon={Building2}
          title={t('settings.general')}
          description={t('settings.generalDescription', 'Nombre, zona horaria, horarios')}
          defaultOpen={true}
          iconColor="text-blue-400"
        >
          {/* Condominium Name - Read only for now */}
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">{t('settings.condominiumName')}</Label>
            <Input
              value={settings.condominium_name}
              disabled
              className="bg-[#0A0A0F] border-[#1E293B] text-muted-foreground"
            />
            <p className="text-[10px] text-muted-foreground">
              {t('settings.condominiumNameHint', 'Contacta soporte para cambiar el nombre')}
            </p>
          </div>
          
          {/* Timezone */}
          <div className="space-y-1.5">
            <Label className="text-xs flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5" />
              {t('settings.timezone')}
            </Label>
            <Select 
              value={settings.general.timezone} 
              onValueChange={(v) => updateSetting('general', 'timezone', v)}
            >
              <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] w-full" data-testid="timezone-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                {TIMEZONE_OPTIONS.map(tz => (
                  <SelectItem key={tz.value} value={tz.value}>{tz.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          {/* Working Hours - Vertical on mobile */}
          <div className="space-y-2">
            <Label className="text-xs flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              {t('settings.workingHours', 'Horario de Operación')}
            </Label>
            <div className={`grid gap-3 ${isMobile ? 'grid-cols-1' : 'grid-cols-2'}`}>
              <div className="space-y-1">
                <Label className="text-[10px] text-muted-foreground">{t('settings.startTime', 'Apertura')}</Label>
                <Input
                  type="time"
                  value={settings.general.working_hours.start}
                  onChange={(e) => updateWorkingHours('start', e.target.value)}
                  className="bg-[#0A0A0F] border-[#1E293B] w-full"
                  data-testid="working-hours-start"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[10px] text-muted-foreground">{t('settings.endTime', 'Cierre')}</Label>
                <Input
                  type="time"
                  value={settings.general.working_hours.end}
                  onChange={(e) => updateWorkingHours('end', e.target.value)}
                  className="bg-[#0A0A0F] border-[#1E293B] w-full"
                  data-testid="working-hours-end"
                />
              </div>
            </div>
          </div>
        </SettingsSection>
        
        {/* SECTION 2: Reservations Settings */}
        <SettingsSection
          icon={Calendar}
          title={t('settings.reservationsSettings')}
          description={t('settings.reservationsDescription', 'Reglas de reservas de áreas comunes')}
          iconColor="text-cyan-400"
          badge={
            settings.reservations.enabled 
              ? <Badge variant="outline" className="ml-2 text-[10px] bg-green-500/10 text-green-400 border-green-500/30">{t('common.active')}</Badge>
              : <Badge variant="outline" className="ml-2 text-[10px] bg-red-500/10 text-red-400 border-red-500/30">{t('common.inactive')}</Badge>
          }
        >
          <ToggleSetting
            label={t('settings.enableReservations')}
            description={t('settings.enableReservationsDesc', 'Permite a los residentes reservar áreas comunes')}
            checked={settings.reservations.enabled}
            onChange={(v) => updateSetting('reservations', 'enabled', v)}
            testId="reservations-enabled"
          />
          
          {settings.reservations.enabled && (
            <>
              {/* Max Reservations */}
              <div className="space-y-1.5">
                <Label className="text-xs">{t('settings.maxReservationsPerUser')}</Label>
                <Select 
                  value={String(settings.reservations.max_active_per_user)} 
                  onValueChange={(v) => updateSetting('reservations', 'max_active_per_user', parseInt(v))}
                >
                  <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] w-full" data-testid="max-reservations">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                    {[1, 2, 3, 5, 10, 20].map(n => (
                      <SelectItem key={n} value={String(n)}>{n} {t('reservations.reservationsCount', 'reservas')}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <ToggleSetting
                label={t('settings.allowSameDay', 'Reservas el mismo día')}
                description={t('settings.allowSameDayDesc', 'Permite reservar para hoy')}
                checked={settings.reservations.allow_same_day}
                onChange={(v) => updateSetting('reservations', 'allow_same_day', v)}
                testId="allow-same-day"
              />
              
              <ToggleSetting
                label={t('settings.requireApproval')}
                description={t('settings.requireApprovalDesc', 'Las reservas requieren aprobación del admin')}
                checked={settings.reservations.approval_required_by_default}
                onChange={(v) => updateSetting('reservations', 'approval_required_by_default', v)}
                testId="approval-required"
              />
              
              {/* Advance limits - Vertical on mobile */}
              <div className={`grid gap-3 ${isMobile ? 'grid-cols-1' : 'grid-cols-2'}`}>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('settings.minHoursAdvance', 'Horas mínimas anticipación')}</Label>
                  <Select 
                    value={String(settings.reservations.min_hours_advance)} 
                    onValueChange={(v) => updateSetting('reservations', 'min_hours_advance', parseInt(v))}
                  >
                    <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                      {[0, 1, 2, 4, 8, 12, 24, 48].map(n => (
                        <SelectItem key={n} value={String(n)}>{n}h</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label className="text-xs">{t('settings.maxDaysAdvance', 'Días máximos anticipación')}</Label>
                  <Select 
                    value={String(settings.reservations.max_days_advance)} 
                    onValueChange={(v) => updateSetting('reservations', 'max_days_advance', parseInt(v))}
                  >
                    <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                      {[7, 14, 30, 60, 90].map(n => (
                        <SelectItem key={n} value={String(n)}>{n} {t('time.days')}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </>
          )}
        </SettingsSection>
        
        {/* SECTION 3: Visits Settings */}
        <SettingsSection
          icon={Users}
          title={t('settings.visitsSettings')}
          description={t('settings.visitsDescription', 'Reglas de registro de visitantes')}
          iconColor="text-green-400"
        >
          <ToggleSetting
            label={t('settings.enableVisitorPreRegistration')}
            description={t('settings.preRegistrationDesc', 'Residentes pueden pre-autorizar visitas')}
            checked={settings.visits.allow_resident_preregistration}
            onChange={(v) => updateSetting('visits', 'allow_resident_preregistration', v)}
            testId="allow-preregistration"
          />
          
          <ToggleSetting
            label={t('settings.allowRecurrentVisits', 'Visitas recurrentes')}
            description={t('settings.recurrentVisitsDesc', 'Autorización de visitas que se repiten')}
            checked={settings.visits.allow_recurrent_visits}
            onChange={(v) => updateSetting('visits', 'allow_recurrent_visits', v)}
            testId="allow-recurrent"
          />
          
          <ToggleSetting
            label={t('settings.allowPermanentVisits', 'Visitas permanentes')}
            description={t('settings.permanentVisitsDesc', 'Visitantes con acceso permanente')}
            checked={settings.visits.allow_permanent_visits}
            onChange={(v) => updateSetting('visits', 'allow_permanent_visits', v)}
            testId="allow-permanent"
          />
          
          <ToggleSetting
            label={t('settings.requireIdPhoto', 'Requerir foto de ID')}
            description={t('settings.requireIdPhotoDesc', 'Guardias deben capturar ID')}
            checked={settings.visits.require_id_photo}
            onChange={(v) => updateSetting('visits', 'require_id_photo', v)}
            testId="require-id-photo"
          />
          
          <div className="space-y-1.5">
            <Label className="text-xs">{t('settings.maxVisitorsPerReservation', 'Pre-registros máximos por día')}</Label>
            <Select 
              value={String(settings.visits.max_preregistrations_per_day)} 
              onValueChange={(v) => updateSetting('visits', 'max_preregistrations_per_day', parseInt(v))}
            >
              <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] w-full" data-testid="max-preregistrations">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                {[5, 10, 15, 20, 30, 50].map(n => (
                  <SelectItem key={n} value={String(n)}>{n}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </SettingsSection>
        
        {/* SECTION 4: Security & Alerts */}
        <SettingsSection
          icon={Shield}
          title={t('settings.securityAlerts', 'Seguridad y Alertas')}
          description={t('settings.securityDescription', 'Pánico, sonidos, notificaciones')}
          iconColor="text-red-400"
        >
          <ToggleSetting
            label={
              <span className="flex items-center gap-2">
                {settings.notifications.panic_sound_enabled ? <Volume2 className="w-4 h-4 text-red-400" /> : <VolumeX className="w-4 h-4 text-muted-foreground" />}
                {t('settings.panicSound', 'Sonido de alerta de pánico')}
              </span>
            }
            description={t('settings.panicSoundDesc', 'Reproducir sonido cuando se active pánico')}
            checked={settings.notifications.panic_sound_enabled}
            onChange={(v) => updateSetting('notifications', 'panic_sound_enabled', v)}
            testId="panic-sound"
          />
          
          <ToggleSetting
            label={t('settings.enablePushNotifications')}
            description={t('settings.pushDesc', 'Enviar notificaciones push a dispositivos')}
            checked={settings.notifications.push_enabled}
            onChange={(v) => updateSetting('notifications', 'push_enabled', v)}
            testId="push-enabled"
          />
          
          <ToggleSetting
            label={t('settings.enableEmailNotifications')}
            description={t('settings.emailDesc', 'Enviar notificaciones por correo')}
            checked={settings.notifications.email_notifications_enabled}
            onChange={(v) => updateSetting('notifications', 'email_notifications_enabled', v)}
            testId="email-enabled"
          />
          
          {/* Info box */}
          <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <div className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-blue-300/80 leading-relaxed">
                {t('settings.securityNote', 'Las alertas de pánico críticas siempre se enviarán para garantizar la seguridad.')}
              </p>
            </div>
          </div>
        </SettingsSection>
        
        {/* SECTION 5: System / Advanced (Read-only) */}
        <SettingsSection
          icon={Server}
          title={t('settings.systemAdvanced', 'Sistema')}
          description={t('settings.systemDescription', 'Información técnica')}
          iconColor="text-purple-400"
        >
          <div className="space-y-3">
            {/* System Status */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0A0A0F]/50 border border-[#1E293B]/50">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm">{t('settings.emailService', 'Servicio de Email')}</span>
              </div>
              <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/30">
                {t('common.active')}
              </Badge>
            </div>
            
            <div className="flex items-center justify-between p-3 rounded-lg bg-[#0A0A0F]/50 border border-[#1E293B]/50">
              <div className="flex items-center gap-2">
                <Bell className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm">{t('settings.pushService', 'Push Notifications')}</span>
              </div>
              <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/30">
                {t('common.active')}
              </Badge>
            </div>
            
            {/* Condominium ID */}
            <div className="p-3 rounded-lg bg-[#0A0A0F]/50 border border-[#1E293B]/50">
              <Label className="text-[10px] text-muted-foreground">ID del Condominio</Label>
              <p className="text-xs font-mono text-muted-foreground mt-1 break-all">
                {settings.condominium_id || 'N/A'}
              </p>
            </div>
            
            {/* Last sync */}
            <Button variant="outline" size="sm" onClick={fetchSettings} className="w-full">
              <RefreshCw className="w-4 h-4 mr-2" />
              {t('common.refresh', 'Actualizar datos')}
            </Button>
          </div>
        </SettingsSection>
        
        {/* Mobile Sticky Save Button */}
        {isMobile && hasChanges && (
          <div className="fixed bottom-20 left-0 right-0 p-4 bg-[#05050A]/95 backdrop-blur-lg border-t border-[#1E293B] z-40">
            <div className="flex items-center gap-3">
              <Button 
                variant="outline" 
                onClick={handleDiscard}
                className="flex-1"
              >
                {t('common.cancel')}
              </Button>
              <Button 
                onClick={handleSave} 
                disabled={saving}
                className="flex-1 bg-primary"
                data-testid="mobile-save-settings"
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Save className="w-4 h-4 mr-2" />
                )}
                {t('common.save')}
              </Button>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
};

export default CondominiumSettingsPage;
