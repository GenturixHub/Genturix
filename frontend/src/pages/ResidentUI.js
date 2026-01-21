/**
 * GENTURIX - ResidentUI (Emergency-First Design)
 * 
 * REFACTORED: Complete UX overhaul for panic button system
 * 
 * Design Principles:
 * - Emergency-first: One scared person, one touch available
 * - Psychological color coding:
 *   • Medical (RED) = Life threat, critical
 *   • Suspicious (AMBER) = Alert, observation needed
 *   • General (ORANGE) = Urgent, immediate response
 * - Minimum 64px touch targets
 * - Immediate feedback (visual + haptic)
 * - Zero distractions
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
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
  WifiOff
} from 'lucide-react';

// ============================================
// EMERGENCY TYPE CONFIGURATION
// Psychological color mapping for stress situations
// ============================================
const EMERGENCY_TYPES = {
  emergencia_medica: {
    id: 'emergencia_medica',
    label: 'EMERGENCIA MÉDICA',
    subLabel: 'Necesito ayuda médica',
    icon: Heart,
    // RED = Life threat, critical, blood, medical
    colors: {
      bg: 'bg-gradient-to-b from-red-600 to-red-700',
      bgActive: 'bg-red-700',
      border: 'border-red-500',
      glow: 'shadow-[0_0_60px_rgba(239,68,68,0.5)]',
      glowPulse: 'shadow-[0_0_80px_rgba(239,68,68,0.7)]',
      text: 'text-white',
      icon: 'text-white',
    },
    priority: 1, // Highest - life threatening
  },
  actividad_sospechosa: {
    id: 'actividad_sospechosa',
    label: 'ACTIVIDAD SOSPECHOSA',
    subLabel: 'Veo algo sospechoso',
    icon: Eye,
    // AMBER/YELLOW = Caution, observation, alert
    colors: {
      bg: 'bg-gradient-to-b from-amber-500 to-yellow-600',
      bgActive: 'bg-amber-600',
      border: 'border-amber-400',
      glow: 'shadow-[0_0_60px_rgba(245,158,11,0.5)]',
      glowPulse: 'shadow-[0_0_80px_rgba(245,158,11,0.7)]',
      text: 'text-black',
      icon: 'text-black',
    },
    priority: 2, // Medium - needs verification
  },
  emergencia_general: {
    id: 'emergencia_general',
    label: 'EMERGENCIA GENERAL',
    subLabel: 'Necesito ayuda urgente',
    icon: AlertTriangle,
    // ORANGE = Urgent, warning, immediate action
    colors: {
      bg: 'bg-gradient-to-b from-orange-500 to-orange-600',
      bgActive: 'bg-orange-600',
      border: 'border-orange-400',
      glow: 'shadow-[0_0_60px_rgba(249,115,22,0.5)]',
      glowPulse: 'shadow-[0_0_80px_rgba(249,115,22,0.7)]',
      text: 'text-white',
      icon: 'text-white',
    },
    priority: 3, // High - urgent response
  },
};

// ============================================
// EMERGENCY BUTTON COMPONENT
// Single-purpose, high-contrast, touch-optimized
// ============================================
const EmergencyButton = ({ config, onPress, disabled, isLoading }) => {
  const [isPressed, setIsPressed] = useState(false);
  const IconComponent = config.icon;

  const handlePress = () => {
    if (disabled || isLoading) return;
    
    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(50);
    }
    
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
      {/* Pulse animation overlay for urgency */}
      <div className={`
        absolute inset-0 ${config.colors.bg} opacity-0
        ${!disabled && !isLoading ? 'animate-pulse' : ''}
      `} />
      
      {/* Content */}
      <div className="relative z-10 flex flex-col items-center justify-center h-full p-4 gap-2">
        {isLoading ? (
          <Loader2 className={`w-12 h-12 ${config.colors.icon} animate-spin`} />
        ) : (
          <IconComponent className={`w-12 h-12 md:w-14 md:h-14 ${config.colors.icon}`} strokeWidth={2.5} />
        )}
        
        <div className="text-center">
          <p className={`text-lg md:text-xl font-bold tracking-wide ${config.colors.text}`}>
            {config.label}
          </p>
          <p className={`text-sm ${config.colors.text} opacity-80 mt-1`}>
            {config.subLabel}
          </p>
        </div>
      </div>
    </button>
  );
};

// ============================================
// GPS STATUS INDICATOR
// Clear visual feedback on location status
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
      <span className="text-xs text-green-400 font-medium">
        GPS Activo • ±{Math.round(location.accuracy || 10)}m
      </span>
    </div>
  );
};

// ============================================
// SUCCESS CONFIRMATION SCREEN
// Clear feedback after emergency sent
// ============================================
const SuccessScreen = ({ alert, onDismiss }) => {
  const config = EMERGENCY_TYPES[alert.type];
  const IconComponent = config.icon;

  return (
    <div className="fixed inset-0 z-50 bg-[#05050A] flex flex-col items-center justify-center p-6 safe-area">
      {/* Animated success indicator */}
      <div className="relative mb-8">
        <div className="w-32 h-32 rounded-full bg-green-500/20 flex items-center justify-center">
          <CheckCircle className="w-16 h-16 text-green-400" />
        </div>
        {/* Ripple effect */}
        <div className="absolute inset-0 w-32 h-32 rounded-full border-4 border-green-400/50 animate-ping" />
        <div className="absolute inset-0 w-32 h-32 rounded-full border-2 border-green-400/30 animate-pulse" />
      </div>

      {/* Confirmation message */}
      <div className="text-center space-y-4 max-w-sm">
        <h1 className="text-3xl font-bold text-green-400">
          ¡ALERTA ENVIADA!
        </h1>
        
        {/* Emergency type badge */}
        <div className={`
          inline-flex items-center gap-2 px-5 py-3 rounded-xl
          ${config.colors.bg} ${config.colors.border} border-2
        `}>
          <IconComponent className={`w-6 h-6 ${config.colors.icon}`} />
          <span className={`font-bold ${config.colors.text}`}>{config.label}</span>
        </div>

        {/* Guards notified count */}
        <div className="p-6 rounded-2xl bg-[#0F111A] border border-green-500/30 space-y-3">
          <div className="flex items-center justify-center gap-3">
            <span className="text-5xl font-bold text-green-400">{alert.guards}</span>
            <span className="text-xl text-white">guardas<br/>notificados</span>
          </div>
          
          <p className="text-muted-foreground">
            Mantente en un lugar seguro.<br/>
            <strong className="text-green-400">Ayuda en camino.</strong>
          </p>

          {alert.location && (
            <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground font-mono">
              <MapPin className="w-3 h-3" />
              {alert.location.latitude.toFixed(5)}, {alert.location.longitude.toFixed(5)}
            </div>
          )}
        </div>

        <p className="text-sm text-muted-foreground">{alert.time}</p>
      </div>

      {/* Dismiss button */}
      <button
        onClick={onDismiss}
        className="mt-8 w-full max-w-sm py-4 rounded-xl bg-[#1E293B] text-white font-medium hover:bg-[#2D3B4F] transition-colors"
      >
        Volver al inicio
      </button>
    </div>
  );
};

// ============================================
// MAIN RESIDENT UI COMPONENT
// Emergency-first interface for residents
// ============================================
const ResidentUI = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, logout } = useAuth();
  
  // Location state
  const [location, setLocation] = useState(null);
  const [locationLoading, setLocationLoading] = useState(true);
  const [locationError, setLocationError] = useState(null);
  
  // Emergency state
  const [sendingType, setSendingType] = useState(null);
  const [sentAlert, setSentAlert] = useState(null);

  // ============================================
  // GPS LOCATION TRACKING
  // ============================================
  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationError('GPS no soportado');
      setLocationLoading(false);
      return;
    }

    // Get initial position
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

    // Watch position updates
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

  // ============================================
  // PWA SHORTCUTS HANDLER
  // ============================================
  useEffect(() => {
    const action = searchParams.get('action');
    if (action === 'medical') {
      handleEmergency('emergencia_medica');
    } else if (action === 'emergency') {
      handleEmergency('emergencia_general');
    }
  }, [searchParams]);

  // ============================================
  // EMERGENCY HANDLER
  // ============================================
  const handleEmergency = useCallback(async (emergencyType) => {
    if (sendingType) return;

    // Strong haptic feedback for confirmation
    if (navigator.vibrate) {
      navigator.vibrate([100, 50, 100]);
    }

    setSendingType(emergencyType);

    try {
      const result = await api.triggerPanic({
        panic_type: emergencyType,
        location: `Residencia de ${user.full_name}`,
        latitude: location?.latitude,
        longitude: location?.longitude,
        description: `Alerta ${EMERGENCY_TYPES[emergencyType].label} activada por ${user.full_name}`,
      });

      // Success haptic pattern
      if (navigator.vibrate) {
        navigator.vibrate([200, 100, 200, 100, 300]);
      }

      setSentAlert({
        type: emergencyType,
        guards: result.notified_guards,
        location: location,
        time: new Date().toLocaleTimeString('es-ES', { 
          hour: '2-digit', 
          minute: '2-digit' 
        }),
      });

      // Auto-dismiss after 20 seconds
      setTimeout(() => setSentAlert(null), 20000);

    } catch (error) {
      console.error('Emergency send error:', error);
      
      // Error haptic
      if (navigator.vibrate) {
        navigator.vibrate(500);
      }
      
      alert('Error al enviar alerta. Intenta de nuevo o llama al 911.');
    } finally {
      setSendingType(null);
    }
  }, [sendingType, location, user]);

  // ============================================
  // LOGOUT HANDLER
  // ============================================
  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // ============================================
  // SUCCESS SCREEN
  // ============================================
  if (sentAlert) {
    return (
      <SuccessScreen 
        alert={sentAlert} 
        onDismiss={() => setSentAlert(null)} 
      />
    );
  }

  // ============================================
  // MAIN RENDER
  // ============================================
  return (
    <div className="min-h-screen bg-[#05050A] flex flex-col safe-area">
      {/* ========== HEADER ========== */}
      <header className="flex items-center justify-between p-4 border-b border-[#1E293B]/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white">GENTURIX</h1>
            <p className="text-xs text-muted-foreground truncate max-w-[140px]">
              {user?.full_name}
            </p>
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

      {/* ========== GPS STATUS ========== */}
      <div className="flex justify-center py-3 border-b border-[#1E293B]/30">
        <GPSStatus 
          location={location} 
          isLoading={locationLoading} 
          error={locationError} 
        />
      </div>

      {/* ========== EMERGENCY BUTTONS ========== */}
      <main className="flex-1 flex flex-col p-4 gap-4">
        {/* Instruction */}
        <p className="text-center text-sm text-muted-foreground mb-2">
          Presiona el botón de emergencia
        </p>

        {/* Emergency buttons - ordered by priority */}
        <div className="flex-1 flex flex-col justify-center gap-4 max-w-lg mx-auto w-full">
          {Object.values(EMERGENCY_TYPES)
            .sort((a, b) => a.priority - b.priority)
            .map((config) => (
              <EmergencyButton
                key={config.id}
                config={config}
                onPress={handleEmergency}
                disabled={!!sendingType}
                isLoading={sendingType === config.id}
              />
            ))}
        </div>
      </main>

      {/* ========== EMERGENCY CALL FOOTER ========== */}
      <footer className="p-4 border-t border-[#1E293B]/50">
        <a
          href="tel:911"
          className="flex items-center justify-center gap-3 py-4 rounded-xl 
            bg-[#1E293B] hover:bg-[#2D3B4F] 
            border border-[#3D4B5F]
            transition-colors"
        >
          <Phone className="w-5 h-5 text-red-400" />
          <span className="text-white font-semibold">Llamar al 911</span>
        </a>
      </footer>
    </div>
  );
};

export default ResidentUI;
