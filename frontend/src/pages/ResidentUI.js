/**
 * GENTURIX - ResidentUI (Emergency-First Design with Notifications)
 * 
 * UPDATED: Added "Avisos" tab for guest entry/exit notifications
 * 
 * Design Principles:
 * - Emergency-first: One scared person, one touch available
 * - Psychological color coding for panic buttons
 * - Notifications for guest access events
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Badge } from '../components/ui/badge';
import api from '../services/api';
import { 
  Heart, 
  Eye, 
  AlertTriangle,
  Navigation,
  Loader2,
  LogOut,
  Shield,
  Phone,
  CheckCircle,
  MapPin,
  Wifi,
  WifiOff,
  Bell,
  UserPlus,
  UserMinus,
  Clock
} from 'lucide-react';

// ============================================
// EMERGENCY TYPE CONFIGURATION
// ============================================
const EMERGENCY_TYPES = {
  emergencia_medica: {
    id: 'emergencia_medica',
    label: 'EMERGENCIA MÉDICA',
    subLabel: 'Necesito ayuda médica',
    icon: Heart,
    colors: {
      bg: 'bg-gradient-to-b from-red-600 to-red-700',
      bgActive: 'bg-red-700',
      border: 'border-red-500',
      glow: 'shadow-[0_0_60px_rgba(239,68,68,0.5)]',
      glowPulse: 'shadow-[0_0_80px_rgba(239,68,68,0.7)]',
      text: 'text-white',
      icon: 'text-white',
    },
    priority: 1,
  },
  actividad_sospechosa: {
    id: 'actividad_sospechosa',
    label: 'ACTIVIDAD SOSPECHOSA',
    subLabel: 'Veo algo sospechoso',
    icon: Eye,
    colors: {
      bg: 'bg-gradient-to-b from-amber-500 to-yellow-600',
      bgActive: 'bg-amber-600',
      border: 'border-amber-400',
      glow: 'shadow-[0_0_60px_rgba(245,158,11,0.5)]',
      glowPulse: 'shadow-[0_0_80px_rgba(245,158,11,0.7)]',
      text: 'text-black',
      icon: 'text-black',
    },
    priority: 2,
  },
  emergencia_general: {
    id: 'emergencia_general',
    label: 'EMERGENCIA GENERAL',
    subLabel: 'Necesito ayuda urgente',
    icon: AlertTriangle,
    colors: {
      bg: 'bg-gradient-to-b from-orange-500 to-orange-600',
      bgActive: 'bg-orange-600',
      border: 'border-orange-400',
      glow: 'shadow-[0_0_60px_rgba(249,115,22,0.5)]',
      glowPulse: 'shadow-[0_0_80px_rgba(249,115,22,0.7)]',
      text: 'text-white',
      icon: 'text-white',
    },
    priority: 3,
  },
};

// ============================================
// EMERGENCY BUTTON COMPONENT
// ============================================
const EmergencyButton = ({ config, onPress, disabled, isLoading }) => {
  const [isPressed, setIsPressed] = useState(false);
  const IconComponent = config.icon;

  const handlePress = () => {
    if (disabled || isLoading) return;
    if (navigator.vibrate) navigator.vibrate(50);
    setIsPressed(true);
    onPress(config.id);
    setTimeout(() => setIsPressed(false), 200);
  };

  return (
    <button
      onClick={handlePress}
      disabled={disabled || isLoading}
      data-testid={`panic-btn-${config.id}`}
      className={`
        relative w-full rounded-2xl overflow-hidden
        min-h-[120px] md:min-h-[140px]
        ${config.colors.bg}
        ${config.colors.glow}
        ${isPressed ? config.colors.glowPulse : ''}
        border-2 ${config.colors.border}
        transition-all duration-150 ease-out
        transform ${isPressed ? 'scale-[0.98]' : 'scale-100'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer active:scale-[0.97]'}
        focus:outline-none focus:ring-4 focus:ring-white/30
      `}
      style={{ WebkitTapHighlightColor: 'transparent' }}
    >
      <div className={`absolute inset-0 ${config.colors.bg} opacity-0 ${!disabled && !isLoading ? 'animate-pulse' : ''}`} />
      <div className="relative z-10 flex flex-col items-center justify-center h-full p-4 gap-2">
        {isLoading ? (
          <Loader2 className={`w-12 h-12 ${config.colors.icon} animate-spin`} />
        ) : (
          <IconComponent className={`w-12 h-12 md:w-14 md:h-14 ${config.colors.icon}`} strokeWidth={2.5} />
        )}
        <div className="text-center">
          <p className={`text-lg md:text-xl font-bold tracking-wide ${config.colors.text}`}>{config.label}</p>
          <p className={`text-sm ${config.colors.text} opacity-80 mt-1`}>{config.subLabel}</p>
        </div>
      </div>
    </button>
  );
};

// ============================================
// GPS STATUS INDICATOR
// ============================================
const GPSStatus = ({ location, isLoading, error }) => {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-2 px-4 rounded-full bg-blue-500/20 border border-blue-500/30">
        <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
        <span className="text-xs text-blue-400 font-medium">Obteniendo ubicación...</span>
      </div>
    );
  }
  if (error || !location) {
    return (
      <div className="flex items-center justify-center gap-2 py-2 px-4 rounded-full bg-yellow-500/20 border border-yellow-500/30">
        <WifiOff className="w-4 h-4 text-yellow-400" />
        <span className="text-xs text-yellow-400 font-medium">GPS no disponible</span>
      </div>
    );
  }
  return (
    <div className="flex items-center justify-center gap-2 py-2 px-4 rounded-full bg-green-500/20 border border-green-500/30">
      <div className="relative">
        <Wifi className="w-4 h-4 text-green-400" />
        <div className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-green-400 rounded-full animate-pulse" />
      </div>
      <span className="text-xs text-green-400 font-medium">GPS Activo • ±{Math.round(location.accuracy || 10)}m</span>
    </div>
  );
};

// ============================================
// SUCCESS CONFIRMATION SCREEN
// ============================================
const SuccessScreen = ({ alert, onDismiss }) => {
  const config = EMERGENCY_TYPES[alert.type];
  const IconComponent = config.icon;

  return (
    <div className="fixed inset-0 z-50 bg-[#05050A] flex flex-col items-center justify-center p-6 safe-area">
      <div className="relative mb-8">
        <div className="w-32 h-32 rounded-full bg-green-500/20 flex items-center justify-center">
          <CheckCircle className="w-16 h-16 text-green-400" />
        </div>
        <div className="absolute inset-0 w-32 h-32 rounded-full border-4 border-green-400/50 animate-ping" />
        <div className="absolute inset-0 w-32 h-32 rounded-full border-2 border-green-400/30 animate-pulse" />
      </div>
      <div className="text-center space-y-4 max-w-sm">
        <h1 className="text-3xl font-bold text-green-400">¡ALERTA ENVIADA!</h1>
        <div className={`inline-flex items-center gap-2 px-5 py-3 rounded-xl ${config.colors.bg} ${config.colors.border} border-2`}>
          <IconComponent className={`w-6 h-6 ${config.colors.icon}`} />
          <span className={`font-bold ${config.colors.text}`}>{config.label}</span>
        </div>
        <div className="p-6 rounded-2xl bg-[#0F111A] border border-green-500/30 space-y-3">
          <div className="flex items-center justify-center gap-3">
            <span className="text-5xl font-bold text-green-400">{alert.guards}</span>
            <span className="text-xl text-white">guardas<br/>notificados</span>
          </div>
          <p className="text-muted-foreground">Mantente en un lugar seguro.<br/><strong className="text-green-400">Ayuda en camino.</strong></p>
          {alert.location && (
            <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground font-mono">
              <MapPin className="w-3 h-3" />
              {alert.location.latitude.toFixed(5)}, {alert.location.longitude.toFixed(5)}
            </div>
          )}
        </div>
        <p className="text-sm text-muted-foreground">{alert.time}</p>
      </div>
      <button onClick={onDismiss} className="mt-8 w-full max-w-sm py-4 rounded-xl bg-[#1E293B] text-white font-medium hover:bg-[#2D3B4F] transition-colors">
        Volver al inicio
      </button>
    </div>
  );
};

// ============================================
// EMERGENCY TAB (Panic Buttons)
// ============================================
const EmergencyTab = ({ location, locationLoading, locationError, onEmergency, sendingType }) => (
  <div className="flex-1 flex flex-col p-4 gap-4">
    <div className="flex justify-center py-2">
      <GPSStatus location={location} isLoading={locationLoading} error={locationError} />
    </div>
    <p className="text-center text-sm text-muted-foreground">Presiona el botón de emergencia</p>
    <div className="flex-1 flex flex-col justify-center gap-4 max-w-lg mx-auto w-full">
      {Object.values(EMERGENCY_TYPES)
        .sort((a, b) => a.priority - b.priority)
        .map((config) => (
          <EmergencyButton
            key={config.id}
            config={config}
            onPress={onEmergency}
            disabled={!!sendingType}
            isLoading={sendingType === config.id}
          />
        ))}
    </div>
  </div>
);

// ============================================
// NOTIFICATIONS TAB (Avisos)
// ============================================
const NotificationsTab = ({ user }) => {
  const [notifications, setNotifications] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchNotifications();
    // Poll for new notifications every 30 seconds
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchNotifications = async () => {
    try {
      // Get access logs that mention this resident
      const accessLogs = await api.getAccessLogs();
      // Filter logs that are visits for this resident
      const residentNotifications = accessLogs.filter(log => 
        log.notes?.toLowerCase().includes(user?.full_name?.toLowerCase()) ||
        log.notes?.toLowerCase().includes('visita')
      ).slice(0, 20);
      
      setNotifications(residentNotifications);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    
    if (diffMins < 1) return 'Ahora';
    if (diffMins < 60) return `Hace ${diffMins}m`;
    if (diffHours < 24) return `Hace ${diffHours}h`;
    return date.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <h2 className="text-sm font-semibold text-muted-foreground mb-4">Avisos de Visitantes</h2>
      
      {notifications.length > 0 ? (
        notifications.map((notif) => (
          <div 
            key={notif.id}
            className={`p-4 rounded-xl border ${
              notif.access_type === 'entry' 
                ? 'bg-green-500/10 border-green-500/30' 
                : 'bg-orange-500/10 border-orange-500/30'
            }`}
            data-testid={`notification-${notif.id}`}
          >
            <div className="flex items-start gap-3">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                notif.access_type === 'entry' ? 'bg-green-500/20' : 'bg-orange-500/20'
              }`}>
                {notif.access_type === 'entry' ? (
                  <UserPlus className="w-5 h-5 text-green-400" />
                ) : (
                  <UserMinus className="w-5 h-5 text-orange-400" />
                )}
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <Badge className={notif.access_type === 'entry' ? 'bg-green-500/20 text-green-400' : 'bg-orange-500/20 text-orange-400'}>
                    {notif.access_type === 'entry' ? 'Entrada' : 'Salida'}
                  </Badge>
                  <span className="text-xs text-muted-foreground">{formatTime(notif.timestamp)}</span>
                </div>
                
                <p className="font-semibold text-white text-sm">{notif.person_name}</p>
                
                {notif.notes && (
                  <p className="text-xs text-muted-foreground mt-1">{notif.notes}</p>
                )}
                
                <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                  <MapPin className="w-3 h-3" />
                  <span>{notif.location}</span>
                </div>
              </div>
            </div>
          </div>
        ))
      ) : (
        <div className="text-center py-12 text-muted-foreground">
          <Bell className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-sm">No hay avisos de visitantes</p>
          <p className="text-xs mt-1">Aquí verás cuando alguien te visite</p>
        </div>
      )}
    </div>
  );
};

// ============================================
// MAIN RESIDENT UI COMPONENT
// ============================================
const ResidentUI = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('emergency');
  
  // Location state
  const [location, setLocation] = useState(null);
  const [locationLoading, setLocationLoading] = useState(true);
  const [locationError, setLocationError] = useState(null);
  
  // Emergency state
  const [sendingType, setSendingType] = useState(null);
  const [sentAlert, setSentAlert] = useState(null);

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
      console.error('Emergency send error:', error);
      if (navigator.vibrate) navigator.vibrate(500);
      alert('Error al enviar alerta. Intenta de nuevo o llama al 911.');
    } finally {
      setSendingType(null);
    }
  }, [sendingType, location, user]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Success Screen
  if (sentAlert) {
    return <SuccessScreen alert={sentAlert} onDismiss={() => setSentAlert(null)} />;
  }

  return (
    <div className="min-h-screen bg-[#05050A] flex flex-col safe-area">
      {/* Header */}
      <header className="flex items-center justify-between p-4 border-b border-[#1E293B]/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white">GENTURIX</h1>
            <p className="text-xs text-muted-foreground truncate max-w-[140px]">{user?.full_name}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="p-2 rounded-lg text-muted-foreground hover:text-white hover:bg-white/5 transition-colors"
          data-testid="logout-btn"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </header>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="grid grid-cols-2 bg-[#0F111A] border-b border-[#1E293B] rounded-none h-12">
          <TabsTrigger 
            value="emergency" 
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-red-500 rounded-none"
            data-testid="tab-emergency"
          >
            <AlertTriangle className="w-4 h-4 mr-2 text-red-400" />
            Emergencia
          </TabsTrigger>
          <TabsTrigger 
            value="notifications" 
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
            data-testid="tab-avisos"
          >
            <Bell className="w-4 h-4 mr-2" />
            Avisos
          </TabsTrigger>
        </TabsList>

        <TabsContent value="emergency" className="flex-1 flex flex-col mt-0">
          <EmergencyTab
            location={location}
            locationLoading={locationLoading}
            locationError={locationError}
            onEmergency={handleEmergency}
            sendingType={sendingType}
          />
        </TabsContent>

        <TabsContent value="notifications" className="flex-1 mt-0">
          <ScrollArea className="h-[calc(100vh-180px)]">
            <NotificationsTab user={user} />
          </ScrollArea>
        </TabsContent>
      </Tabs>

      {/* Emergency Call Footer */}
      <footer className="p-4 border-t border-[#1E293B]/50">
        <a
          href="tel:911"
          className="flex items-center justify-center gap-3 py-4 rounded-xl bg-[#1E293B] hover:bg-[#2D3B4F] border border-[#3D4B5F] transition-colors"
        >
          <Phone className="w-5 h-5 text-red-400" />
          <span className="text-white font-semibold">Llamar al 911</span>
        </a>
      </footer>
    </div>
  );
};

export default ResidentUI;
