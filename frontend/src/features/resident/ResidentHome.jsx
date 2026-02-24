/**
 * GENTURIX - Resident Home
 * 
 * Main resident interface with emergency, visits, reservations, directory and profile.
 * Uses independent ResidentLayout for mobile-first experience.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Tabs, TabsContent } from '../../components/ui/tabs';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../../components/ui/dropdown-menu';
import api from '../../services/api';
import ProfileDirectory from '../../components/ProfileDirectory';
import EmbeddedProfile from '../../components/EmbeddedProfile';
import ResidentVisitsModule from '../../components/ResidentVisitsModule';
import PushPermissionBanner from '../../components/PushPermissionBanner';
import ResidentReservations from '../../components/ResidentReservations';
import PremiumPanicButton from '../../components/PremiumPanicButton';
import ResidentLayout from './ResidentLayout';
import { toast } from 'sonner';
import { 
  Heart, 
  Eye, 
  AlertTriangle,
  Loader2,
  Shield,
  Phone,
  CheckCircle,
  MapPin,
  Wifi,
  WifiOff,
  Bell,
  User,
  Check,
  CheckCheck,
  RefreshCw,
  UserCheck,
  LogOut,
  Calendar,
  Users
} from 'lucide-react';

// Import emergency styles
import '../../styles/emergency-buttons.css';

// ============================================
// EMERGENCY TYPES CONFIGURATION
// ============================================
const EMERGENCY_TYPES = {
  emergencia_general: {
    id: 'emergencia_general',
    label: 'Emergencia General',
    shortLabel: 'EMERGENCIA',
    subLabel: 'Presiona para alertar',
    icon: AlertTriangle,
    colors: {
      bg: 'bg-red-500/20',
      text: 'text-red-400',
      border: 'border-red-500/30',
      button: 'bg-gradient-to-br from-red-500 to-red-700',
      glow: 'shadow-red-500/50',
      icon: 'text-white',
    },
    priority: 1,
  },
  emergencia_medica: {
    id: 'emergencia_medica',
    label: 'Emergencia Médica',
    shortLabel: 'MÉDICA',
    icon: Heart,
    colors: {
      bg: 'bg-green-500/20',
      text: 'text-green-400',
      border: 'border-green-500/30',
      button: 'bg-gradient-to-br from-green-500 to-green-700',
      glow: 'shadow-green-500/50',
      icon: 'text-white',
    },
    priority: 2,
  },
  actividad_sospechosa: {
    id: 'actividad_sospechosa',
    label: 'Actividad Sospechosa',
    shortLabel: 'SEGURIDAD',
    icon: Eye,
    colors: {
      bg: 'bg-yellow-500/20',
      text: 'text-yellow-400',
      border: 'border-yellow-500/30',
      button: 'bg-gradient-to-br from-yellow-500 to-yellow-700',
      glow: 'shadow-yellow-500/50',
      icon: 'text-black',
    },
    priority: 2,
  },
};

// ============================================
// HERO EMERGENCY BUTTON
// ============================================
const HeroEmergencyButton = ({ config, onPress, disabled, isLoading }) => {
  const [ripples, setRipples] = useState([]);
  const IconComponent = config.icon;

  const handlePress = (e) => {
    if (disabled || isLoading) return;
    if (navigator.vibrate) navigator.vibrate([50, 30, 50]);
    
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const rippleId = Date.now();
    setRipples(prev => [...prev, { id: rippleId, x, y }]);
    setTimeout(() => setRipples(prev => prev.filter(r => r.id !== rippleId)), 600);
    
    onPress(config.id);
  };

  return (
    <button
      onClick={handlePress}
      disabled={disabled || isLoading}
      data-testid={`panic-btn-${config.id}`}
      className={`emergency-hero-circle ${isLoading ? 'is-loading' : ''}`}
      style={{
        width: 'min(70vw, 280px)',
        height: 'min(70vw, 280px)',
        background: 'radial-gradient(circle at 30% 30%, #ff4444 0%, #cc0000 50%, #990000 100%)',
        border: '4px solid rgba(255, 255, 255, 0.9)',
        boxShadow: '0 0 60px rgba(255, 0, 0, 0.5), 0 0 100px rgba(255, 0, 0, 0.3), inset 0 -8px 20px rgba(0,0,0,0.3)'
      }}
    >
      <div className="emergency-hero-shimmer" />
      {ripples.map(ripple => (
        <span key={ripple.id} className="emergency-hero-ripple" style={{ left: ripple.x, top: ripple.y }} />
      ))}
      <div className="emergency-hero-icon-wrapper" style={{ transform: 'scale(1.3)' }}>
        {isLoading ? <Loader2 className="animate-spin" /> : <IconComponent strokeWidth={2.5} />}
      </div>
      <div className="emergency-hero-text">
        <p className="emergency-hero-label" style={{ fontSize: 'clamp(1.2rem, 5vw, 1.5rem)' }}>{config.shortLabel}</p>
        <p className="emergency-hero-sublabel" style={{ fontSize: 'clamp(0.7rem, 3vw, 0.9rem)' }}>{config.subLabel}</p>
      </div>
    </button>
  );
};

// ============================================
// SECONDARY EMERGENCY BUTTON
// ============================================
const SecondaryEmergencyButton = ({ config, variant, onPress, disabled, isLoading }) => {
  const [ripples, setRipples] = useState([]);
  const IconComponent = config.icon;

  const handlePress = (e) => {
    if (disabled || isLoading) return;
    if (navigator.vibrate) navigator.vibrate(30);
    
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const rippleId = Date.now();
    setRipples(prev => [...prev, { id: rippleId, x, y }]);
    setTimeout(() => setRipples(prev => prev.filter(r => r.id !== rippleId)), 500);
    
    onPress(config.id);
  };

  return (
    <div className="flex flex-col items-center">
      <button
        onClick={handlePress}
        disabled={disabled || isLoading}
        data-testid={`panic-btn-${config.id}`}
        className={`emergency-secondary-circle emergency-secondary-circle--${variant} ${isLoading ? 'is-loading' : ''}`}
        style={{
          width: '100%',
          height: 'min(35vw, 130px)',
          aspectRatio: '1',
          margin: '0 auto',
          boxShadow: variant === 'medical' 
            ? '0 0 30px rgba(34, 197, 94, 0.4), 0 0 60px rgba(34, 197, 94, 0.2)'
            : '0 0 30px rgba(251, 191, 36, 0.4), 0 0 60px rgba(251, 191, 36, 0.2)'
        }}
      >
        {ripples.map(ripple => (
          <span key={ripple.id} className="emergency-secondary-ripple" style={{ left: ripple.x, top: ripple.y }} />
        ))}
        <div className="emergency-secondary-icon-wrapper" style={{ transform: 'scale(1.2)' }}>
          {isLoading ? <Loader2 className="animate-spin" /> : <IconComponent strokeWidth={2.5} />}
        </div>
      </button>
      <p className="text-center font-semibold mt-2" style={{ 
        fontSize: 'clamp(0.7rem, 3vw, 0.85rem)',
        color: variant === 'medical' ? '#22c55e' : '#fbbf24'
      }}>
        {config.id === 'emergencia_medica' ? 'MÉDICA' : 'SEGURIDAD'}
      </p>
    </div>
  );
};

// ============================================
// GPS STATUS COMPONENT
// ============================================
const GPSStatus = ({ location, isLoading, error }) => {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-2 px-4 rounded-full bg-[#1E293B]/50 mx-auto w-fit">
        <Loader2 className="w-4 h-4 animate-spin text-primary" />
        <span className="text-xs text-muted-foreground">Obteniendo ubicación...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center gap-2 py-2 px-4 rounded-full bg-red-500/10 border border-red-500/20 mx-auto w-fit">
        <WifiOff className="w-4 h-4 text-red-400" />
        <span className="text-xs text-red-400">{error}</span>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center gap-2 py-2 px-4 rounded-full bg-green-500/10 border border-green-500/20 mx-auto w-fit">
      <MapPin className="w-4 h-4 text-green-400" />
      <span className="text-xs text-green-400">GPS activo</span>
      {location?.accuracy && (
        <span className="text-[10px] text-muted-foreground">±{Math.round(location.accuracy)}m</span>
      )}
    </div>
  );
};

// ============================================
// SUCCESS SCREEN
// ============================================
const SuccessScreen = ({ alert, onDismiss }) => {
  const config = EMERGENCY_TYPES[alert.type];
  const IconComponent = config?.icon || AlertTriangle;

  return (
    <div className="fixed inset-0 z-50 bg-[#05050A] flex flex-col items-center justify-center p-6">
      <div className="w-24 h-24 rounded-full bg-green-500/20 flex items-center justify-center mb-6 animate-pulse">
        <CheckCircle className="w-12 h-12 text-green-400" />
      </div>
      <h1 className="text-2xl font-bold text-white mb-2 text-center">Alerta Enviada</h1>
      <p className="text-muted-foreground text-center mb-6">
        {alert.guards > 0 
          ? `${alert.guards} guardias han sido notificados`
          : 'La alerta ha sido registrada'
        }
      </p>
      <div className="bg-[#0F111A] border border-[#1E293B] rounded-2xl p-4 w-full max-w-sm mb-6">
        <div className="flex items-center gap-3 mb-3">
          <div className={`w-10 h-10 rounded-lg ${config?.colors.bg} flex items-center justify-center`}>
            <IconComponent className={`w-5 h-5 ${config?.colors.text}`} />
          </div>
          <div>
            <p className="font-semibold text-white">{config?.label}</p>
            <p className="text-xs text-muted-foreground">{alert.time}</p>
          </div>
        </div>
        {alert.location && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <MapPin className="w-3 h-3" />
            <span>Ubicación enviada</span>
          </div>
        )}
      </div>
      <Button onClick={onDismiss} variant="outline" className="min-h-[48px] px-8">
        Cerrar
      </Button>
    </div>
  );
};

// ============================================
// EMERGENCY TAB
// ============================================
const EmergencyTab = ({ location, locationLoading, locationError, onEmergency, sendingType }) => (
  <div 
    style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      padding: '12px 12px 16px',
      gap: '12px',
      boxSizing: 'border-box'
    }}
  >
    {/* GPS Status */}
    <div className="flex-shrink-0">
      <GPSStatus location={location} isLoading={locationLoading} error={locationError} />
    </div>
    
    {/* Main Emergency Button */}
    <div className="flex-1 flex items-center justify-center min-h-0">
      <div className="emergency-hero-pulse-wrapper">
        <HeroEmergencyButton
          config={EMERGENCY_TYPES.emergencia_general}
          onPress={onEmergency}
          disabled={!!sendingType}
          isLoading={sendingType === 'emergencia_general'}
        />
      </div>
    </div>
    
    {/* Secondary Buttons + Info */}
    <div className="flex-shrink-0 space-y-3">
      <div className="grid grid-cols-2 gap-4">
        <SecondaryEmergencyButton
          config={EMERGENCY_TYPES.emergencia_medica}
          variant="medical"
          onPress={onEmergency}
          disabled={!!sendingType}
          isLoading={sendingType === 'emergencia_medica'}
        />
        <SecondaryEmergencyButton
          config={EMERGENCY_TYPES.actividad_sospechosa}
          variant="suspicious"
          onPress={onEmergency}
          disabled={!!sendingType}
          isLoading={sendingType === 'actividad_sospechosa'}
        />
      </div>
      
      {/* Instruction Card */}
      <div 
        className="rounded-2xl px-4 py-2.5 text-center"
        style={{ background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.08)' }}
      >
        <p className="text-xs text-muted-foreground leading-relaxed">
          <strong className="text-white/80">Presiona el botón</strong> para alertar a seguridad.
          <br />Tu ubicación será enviada automáticamente.
        </p>
      </div>
    </div>
  </div>
);

// ============================================
// MAIN COMPONENT
// ============================================
const ResidentHome = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('emergency');
  
  // Location state
  const [location, setLocation] = useState(null);
  const [locationLoading, setLocationLoading] = useState(true);
  const [locationError, setLocationError] = useState(null);
  
  // Emergency state
  const [sendingType, setSendingType] = useState(null);
  const [sentAlert, setSentAlert] = useState(null);
  
  // Notifications state
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  // GPS Location tracking
  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationError('GPS no soportado');
      setLocationLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
        setLocationLoading(false);
      },
      (err) => {
        console.error('GPS Error:', err);
        setLocationError('No se pudo obtener ubicación');
        setLocationLoading(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        setLocation({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
      },
      () => {},
      { enableHighAccuracy: true, maximumAge: 5000 }
    );

    return () => navigator.geolocation.clearWatch(watchId);
  }, []);

  // PWA Shortcuts handler
  useEffect(() => {
    const action = searchParams.get('action');
    if (action === 'medical') {
      handleEmergency('emergencia_medica');
    } else if (action === 'emergency') {
      handleEmergency('emergencia_general');
    }
  }, [searchParams]);

  // Emergency handler
  const handleEmergency = useCallback(async (emergencyType) => {
    if (sendingType) return;
    if (navigator.vibrate) navigator.vibrate([100, 50, 100]);

    setSendingType(emergencyType);

    try {
      const result = await api.triggerPanic({
        panic_type: emergencyType,
        location: `Residencia de ${user.full_name}`,
        latitude: location?.latitude,
        longitude: location?.longitude,
        description: `Alerta ${EMERGENCY_TYPES[emergencyType].label} activada por ${user.full_name}`,
      });

      if (navigator.vibrate) navigator.vibrate([200, 100, 200, 100, 300]);

      setSentAlert({
        type: emergencyType,
        guards: result.notified_guards,
        location: location,
        time: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }),
      });

      setTimeout(() => setSentAlert(null), 20000);
    } catch (error) {
      console.error('[Panic] Error:', error);
      if (navigator.vibrate) navigator.vibrate(500);
      
      let errorMessage = 'Error al enviar alerta. Intenta de nuevo o llama al 911.';
      const status = error.status || error.response?.status;
      const detail = error.data?.detail || error.message;
      
      if (status === 401) {
        errorMessage = 'Sesión expirada. Por favor, inicia sesión nuevamente.';
      } else if (status === 403) {
        errorMessage = detail || 'No tienes permisos para enviar alertas.';
      } else if (detail) {
        errorMessage = detail;
      }
      
      toast.error('Error de Emergencia', { description: errorMessage, duration: 10000 });
    } finally {
      setSendingType(null);
    }
  }, [sendingType, location, user]);

  // Success Screen
  if (sentAlert) {
    return <SuccessScreen alert={sentAlert} onDismiss={() => setSentAlert(null)} />;
  }

  return (
    <ResidentLayout activeTab={activeTab} onTabChange={setActiveTab}>
      <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
        <TabsContent value="emergency" className="mt-0 flex-1 min-h-0">
          <EmergencyTab
            location={location}
            locationLoading={locationLoading}
            locationError={locationError}
            onEmergency={handleEmergency}
            sendingType={sendingType}
          />
        </TabsContent>

        <TabsContent value="visits" className="mt-0 px-3 py-4">
          <ResidentVisitsModule />
        </TabsContent>

        <TabsContent value="reservations" className="mt-0 px-3 py-4">
          <ResidentReservations />
        </TabsContent>
        
        <TabsContent value="directory" className="mt-0">
          <ProfileDirectory embedded={true} maxHeight="calc(100vh - 140px)" />
        </TabsContent>
        
        <TabsContent value="profile" className="mt-0 px-3 py-4">
          <EmbeddedProfile />
        </TabsContent>
      </Tabs>
      
      {/* Push Permission Banner */}
      <PushPermissionBanner onSubscribed={() => console.log('Push enabled!')} />
    </ResidentLayout>
  );
};

export default ResidentHome;
