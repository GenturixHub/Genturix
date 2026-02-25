/**
 * GENTURIX - ResidentUI (Emergency-First Design with Visitor Pre-Registration)
 * 
 * FLOW: Resident creates visitor → Guard executes entry/exit → Admin audits
 * 
 * Tabs:
 * - Emergencia: Panic buttons (NOT modified)
 * - Autorizaciones: Advanced visitor authorization system
 * - Historial: Alert history
 * - Directorio: Condominium directory
 * - Perfil: User profile
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent } from '../components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import api from '../services/api';
// Push initialization is handled in AuthContext - no push logic needed here
import ProfileDirectory from '../components/ProfileDirectory';
import EmbeddedProfile from '../components/EmbeddedProfile';
import ResidentVisitsModule from '../components/ResidentVisitsModule';
import PushPermissionBanner from '../components/PushPermissionBanner';
import ResidentReservations from '../components/ResidentReservations';
import MobileBottomNav, { useIsMobile } from '../components/layout/BottomNav';
import { 
  Heart, 
  Eye, 
  AlertTriangle,
  Loader2,
  LogOut,
  Shield,
  Phone,
  CheckCircle,
  MapPin,
  Wifi,
  WifiOff,
  Users,
  UserPlus,
  Car,
  Calendar as CalendarIcon,
  Clock,
  X,
  Trash2,
  History,
  Bell,
  User,
  Check,
  CheckCheck,
  RefreshCw,
  UserCheck
} from 'lucide-react';
import { toast } from 'sonner';

// ============================================
// EMERGENCY TYPE CONFIGURATION
// ============================================
const EMERGENCY_TYPES = {
  emergencia_medica: {
    id: 'emergencia_medica',
    label: 'EMERGENCIA MÉDICA',
    shortLabel: 'MÉDICA',
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
    shortLabel: 'SEGURIDAD',
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
    shortLabel: 'EMERGENCIA',
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

const VISIT_TYPES = [
  { value: 'familiar', label: 'Familiar' },
  { value: 'friend', label: 'Amigo' },
  { value: 'delivery', label: 'Delivery / Paquetería' },
  { value: 'service', label: 'Servicio Técnico' },
  { value: 'other', label: 'Otro' },
];

const STATUS_CONFIG = {
  pending: { label: 'Pendiente', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  approved: { label: 'Aprobado', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  entry_registered: { label: 'Dentro', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  exit_registered: { label: 'Salió', color: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
  cancelled: { label: 'Cancelado', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
  expired: { label: 'Expirado', color: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
};

// ============================================
// HERO EMERGENCY BUTTON - Circular Premium Design
// ============================================
const HeroEmergencyButton = ({ config, onPress, disabled, isLoading, enlarged = false }) => {
  const [ripples, setRipples] = useState([]);
  const IconComponent = config.icon;

  const handlePress = (e) => {
    if (disabled || isLoading) return;
    
    // Strong haptic feedback for hero button
    if (navigator.vibrate) navigator.vibrate([50, 30, 50]);
    
    // Create ripple at center for circular button
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const rippleId = Date.now();
    setRipples(prev => [...prev, { id: rippleId, x, y }]);
    setTimeout(() => setRipples(prev => prev.filter(r => r.id !== rippleId)), 600);
    
    onPress(config.id);
  };

  // Enlarged styles with viewport-relative sizing
  const enlargedStyles = enlarged ? {
    width: 'min(70vw, 280px)',
    height: 'min(70vw, 280px)',
    background: 'radial-gradient(circle at 30% 30%, #ff4444 0%, #cc0000 50%, #990000 100%)',
    border: '4px solid rgba(255, 255, 255, 0.9)',
    boxShadow: '0 0 60px rgba(255, 0, 0, 0.5), 0 0 100px rgba(255, 0, 0, 0.3), inset 0 -8px 20px rgba(0,0,0,0.3)'
  } : {};

  return (
    <button
      onClick={handlePress}
      disabled={disabled || isLoading}
      data-testid={`panic-btn-${config.id}`}
      className={`emergency-hero-circle ${isLoading ? 'is-loading' : ''} ${enlarged ? 'emergency-hero-enlarged' : ''}`}
      style={enlargedStyles}
    >
      {/* Shimmer effect overlay */}
      <div className="emergency-hero-shimmer" />
      
      {/* Ripples */}
      {ripples.map(ripple => (
        <span
          key={ripple.id}
          className="emergency-hero-ripple"
          style={{ left: ripple.x, top: ripple.y }}
        />
      ))}
      
      {/* Icon */}
      <div className="emergency-hero-icon-wrapper" style={enlarged ? { transform: 'scale(1.3)' } : {}}>
        {isLoading ? (
          <Loader2 />
        ) : (
          <IconComponent strokeWidth={2.5} />
        )}
      </div>
      
      {/* Text */}
      <div className="emergency-hero-text">
        <p className="emergency-hero-label" style={enlarged ? { fontSize: 'clamp(1.2rem, 5vw, 1.5rem)' } : {}}>{config.shortLabel || 'EMERGENCIA'}</p>
        <p className="emergency-hero-sublabel" style={enlarged ? { fontSize: 'clamp(0.7rem, 3vw, 0.9rem)' } : {}}>{config.subLabel}</p>
      </div>
    </button>
  );
};

// ============================================
// SECONDARY EMERGENCY BUTTON - Circular Design
// ============================================
const SecondaryEmergencyButton = ({ config, variant, onPress, disabled, isLoading, enlarged = false }) => {
  const [ripples, setRipples] = useState([]);
  const IconComponent = config.icon;

  const handlePress = (e) => {
    if (disabled || isLoading) return;
    
    // Light haptic
    if (navigator.vibrate) navigator.vibrate(30);
    
    // Create ripple
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const rippleId = Date.now();
    setRipples(prev => [...prev, { id: rippleId, x, y }]);
    setTimeout(() => setRipples(prev => prev.filter(r => r.id !== rippleId)), 500);
    
    onPress(config.id);
  };

  // Uniform sizing for grid layout
  const enlargedStyles = enlarged ? {
    width: '100%',
    height: 'min(35vw, 130px)',
    aspectRatio: '1',
    margin: '0 auto',
    boxShadow: variant === 'medical' 
      ? '0 0 30px rgba(34, 197, 94, 0.4), 0 0 60px rgba(34, 197, 94, 0.2)'
      : '0 0 30px rgba(251, 191, 36, 0.4), 0 0 60px rgba(251, 191, 36, 0.2)'
  } : {};

  return (
    <div className="flex flex-col items-center">
      <button
        onClick={handlePress}
        disabled={disabled || isLoading}
        data-testid={`panic-btn-${config.id}`}
        className={`emergency-secondary-circle emergency-secondary-circle--${variant} ${isLoading ? 'is-loading' : ''}`}
        style={enlargedStyles}
      >
        {/* Ripples */}
        {ripples.map(ripple => (
          <span
            key={ripple.id}
            className="emergency-secondary-ripple"
            style={{ left: ripple.x, top: ripple.y }}
          />
        ))}
        
        {/* Icon */}
        <div className="emergency-secondary-icon-wrapper" style={enlarged ? { transform: 'scale(1.2)' } : {}}>
          {isLoading ? (
            <Loader2 />
          ) : (
            <IconComponent strokeWidth={2.5} />
          )}
        </div>
      </button>
      {/* Label outside button for better layout */}
      <p 
        className="text-center font-semibold mt-2"
        style={{ 
          fontSize: 'clamp(0.7rem, 3vw, 0.85rem)',
          color: variant === 'medical' ? '#22c55e' : '#fbbf24'
        }}
      >
        {config.id === 'emergencia_medica' ? 'MÉDICA' : 'SEGURIDAD'}
      </p>
    </div>
  );
};

// ============================================
// GPS STATUS INDICATOR - Premium Compact
// ============================================
const GPSStatus = ({ location, isLoading, error }) => {
  if (isLoading) {
    return (
      <div className="emergency-gps-status emergency-gps-status--loading">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        <span>Obteniendo ubicación...</span>
      </div>
    );
  }
  if (error || !location) {
    return (
      <div className="emergency-gps-status emergency-gps-status--error">
        <WifiOff className="w-3.5 h-3.5" />
        <span>GPS no disponible</span>
      </div>
    );
  }
  return (
    <div className="emergency-gps-status emergency-gps-status--active">
      <span className="emergency-gps-dot" />
      <span>GPS Activo • ±{Math.round(location.accuracy || 10)}m</span>
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
        </div>
      </div>
      <button onClick={onDismiss} className="mt-8 w-full max-w-sm py-4 rounded-xl bg-[#1E293B] text-white font-medium hover:bg-[#2D3B4F] transition-colors">
        Volver al inicio
      </button>
    </div>
  );
};

// ============================================
// EMERGENCY TAB - Optimized Mobile Layout
// ============================================
const EmergencyTab = ({ location, locationLoading, locationError, onEmergency, sendingType }) => (
  <div 
    className="emergency-container"
    style={{
      minHeight: 'calc(100vh - 180px)',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      padding: '12px 16px 24px',
      gap: '16px'
    }}
  >
    {/* TOP SECTION: GPS Status */}
    <div className="flex-shrink-0">
      <GPSStatus location={location} isLoading={locationLoading} error={locationError} />
    </div>
    
    {/* CENTER SECTION: Main Emergency Button */}
    <div 
      className="flex-1 flex items-center justify-center"
      style={{ minHeight: '40vh' }}
    >
      <div className="emergency-hero-pulse-wrapper">
        <HeroEmergencyButton
          config={EMERGENCY_TYPES.emergencia_general}
          onPress={onEmergency}
          disabled={!!sendingType}
          isLoading={sendingType === 'emergencia_general'}
          enlarged={true}
        />
      </div>
    </div>
    
    {/* BOTTOM SECTION: Secondary Buttons + Info */}
    <div className="flex-shrink-0 space-y-4">
      {/* Secondary Buttons - Grid 2 columns */}
      <div 
        className="grid grid-cols-2 gap-4"
        data-testid="emergency-secondary-container"
      >
        <SecondaryEmergencyButton
          config={EMERGENCY_TYPES.emergencia_medica}
          variant="medical"
          onPress={onEmergency}
          disabled={!!sendingType}
          isLoading={sendingType === 'emergencia_medica'}
          enlarged={true}
        />
        <SecondaryEmergencyButton
          config={EMERGENCY_TYPES.actividad_sospechosa}
          variant="suspicious"
          onPress={onEmergency}
          disabled={!!sendingType}
          isLoading={sendingType === 'actividad_sospechosa'}
          enlarged={true}
        />
      </div>
      
      {/* Instruction Card */}
      <div 
        className="rounded-2xl px-4 py-3 text-center"
        style={{
          background: 'rgba(255, 255, 255, 0.05)',
          border: '1px solid rgba(255, 255, 255, 0.08)'
        }}
      >
        <p className="text-xs text-muted-foreground leading-relaxed">
          <strong className="text-white/80">Presiona el botón</strong> para alertar a seguridad.
          <br />
          Tu ubicación será enviada automáticamente.
        </p>
      </div>
    </div>
  </div>
);

// ============================================
// ALERT HISTORY TAB (My Alerts)
// ============================================
const AlertHistoryTab = () => {
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const data = await api.getResidentAlerts();
        setAlerts(data);
      } catch (error) {
        console.error('Error fetching alerts:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAlerts();
  }, []);

  const getStatusConfig = (status) => {
    switch (status) {
      case 'active':
        return { label: 'Enviada', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' };
      case 'resolved':
        return { label: 'Atendida', color: 'bg-green-500/20 text-green-400 border-green-500/30' };
      default:
        return { label: status, color: 'bg-gray-500/20 text-gray-400 border-gray-500/30' };
    }
  };

  const getTypeConfig = (type) => {
    return EMERGENCY_TYPES[type] || {
      label: type,
      icon: AlertTriangle,
      colors: { bg: 'bg-gray-600', text: 'text-white' }
    };
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-3 sm:p-4 space-y-3 sm:space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base sm:text-lg font-bold flex items-center gap-2">
          <History className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
          Mis Alertas
        </h2>
        <span className="text-xs text-muted-foreground">{alerts.length} alertas</span>
      </div>

      {alerts.length === 0 ? (
        <div className="text-center py-10 sm:py-12">
          <Bell className="w-10 h-10 sm:w-12 sm:h-12 text-muted-foreground/30 mx-auto mb-3 sm:mb-4" />
          <p className="text-sm text-muted-foreground">No has enviado alertas</p>
          <p className="text-xs text-muted-foreground mt-1">Las alertas que envíes aparecerán aquí</p>
        </div>
      ) : (
        <div className="space-y-2 sm:space-y-3">
          {alerts.map((alert) => {
            const statusConfig = getStatusConfig(alert.status);
            const typeConfig = getTypeConfig(alert.panic_type);
            const IconComponent = typeConfig.icon;

            return (
              <div 
                key={alert.id} 
                className="p-3 sm:p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]"
                data-testid={`alert-history-${alert.id}`}
              >
                <div className="flex items-start gap-2.5 sm:gap-3">
                  <div className={`w-9 h-9 sm:w-10 sm:h-10 rounded-lg ${typeConfig.colors.bg} flex items-center justify-center flex-shrink-0`}>
                    <IconComponent className={`w-4 h-4 sm:w-5 sm:h-5 ${typeConfig.colors.text}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-semibold text-sm truncate">{alert.panic_type_label || typeConfig.label}</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] sm:text-xs border whitespace-nowrap ${statusConfig.color}`}>
                        {statusConfig.label}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-1.5 sm:mb-2 truncate">{alert.location}</p>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                      <span className="text-muted-foreground">
                        {new Date(alert.created_at).toLocaleDateString('es-ES', { 
                          day: '2-digit', 
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>
                      {alert.resolved_by_name && (
                        <span className="text-green-400 truncate">
                          Por: {alert.resolved_by_name}
                        </span>
                      )}
                    </div>
                    {alert.notified_guards > 0 && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {alert.notified_guards} guardias notificados
                      </p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// ============================================
// VISITORS TAB (Pre-Registration)
// ============================================
const VisitorsTab = ({ user }) => {
  const [visitors, setVisitors] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    full_name: '',
    national_id: '',
    vehicle_plate: '',
    visit_type: 'friend',
    expected_date: new Date().toISOString().split('T')[0],
    expected_time: '',
    notes: ''
  });

  useEffect(() => {
    fetchVisitors();
  }, []);

  const fetchVisitors = async () => {
    try {
      const data = await api.getMyVisitors();
      setVisitors(data);
    } catch (error) {
      console.error('Error fetching visitors:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!formData.full_name.trim()) return;
    
    setIsSubmitting(true);
    try {
      await api.preRegisterVisitor(formData);
      setFormData({
        full_name: '',
        national_id: '',
        vehicle_plate: '',
        visit_type: 'friend',
        expected_date: new Date().toISOString().split('T')[0],
        expected_time: '',
        notes: ''
      });
      setShowForm(false);
      fetchVisitors();
      if (navigator.vibrate) navigator.vibrate(100);
    } catch (error) {
      console.error('Error pre-registering visitor:', error);
      alert('Error al registrar visitante');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async (visitorId) => {
    try {
      await api.cancelVisitor(visitorId);
      toast.success('Autorización eliminada');
      fetchVisitors();
    } catch (error) {
      const errorMessage = error?.message || 'Error al eliminar';
      toast.error(errorMessage);
      console.error('Error cancelling visitor:', error);
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="p-3 sm:p-4 space-y-3 sm:space-y-4">
      {/* Add Visitor Button - Touch-friendly */}
      <Button 
        className="w-full min-h-[44px] text-sm" 
        onClick={() => setShowForm(true)}
        data-testid="add-visitor-btn"
      >
        <UserPlus className="w-4 h-4 mr-2" />
        Pre-registrar Visitante
      </Button>

      {/* Visitors List */}
      <div className="space-y-2">
        <h3 className="text-xs sm:text-sm font-semibold text-muted-foreground">Mis Visitantes</h3>
        
        {visitors.length > 0 ? (
          visitors.map((visitor) => {
            const status = STATUS_CONFIG[visitor.status] || STATUS_CONFIG.pending;
            
            return (
              <Card key={visitor.id} className="bg-[#0F111A] border-[#1E293B]">
                <CardContent className="p-2.5 sm:p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-semibold text-white text-sm truncate max-w-[150px] sm:max-w-none">{visitor.full_name}</span>
                        <Badge className={`${status.color} text-[10px] px-1.5 py-0`}>{status.label}</Badge>
                      </div>
                      
                      <div className="flex flex-wrap gap-x-2 gap-y-1 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <CalendarIcon className="w-3 h-3" />
                          {formatDate(visitor.expected_date)}
                        </span>
                        {visitor.vehicle_plate && (
                          <span className="flex items-center gap-1">
                            <Car className="w-3 h-3" />
                            {visitor.vehicle_plate}
                          </span>
                        )}
                        <span className="capitalize">
                          {VISIT_TYPES.find(t => t.value === visitor.visit_type)?.label || visitor.visit_type}
                        </span>
                      </div>

                      {visitor.entry_at && (
                        <div className="text-xs text-green-400 mt-1">
                          Entrada: {new Date(visitor.entry_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                          {visitor.entry_by_name && ` por ${visitor.entry_by_name}`}
                        </div>
                      )}
                      {visitor.exit_at && (
                        <div className="text-xs text-orange-400">
                          Salida: {new Date(visitor.exit_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      )}
                    </div>

                    {/* Delete button - Touch-friendly 44px */}
                    {(visitor.status === 'pending' || visitor.status === 'exited' || visitor.status === 'exit_registered' || visitor.status === 'cancelled') && (
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-10 w-10 min-h-[40px] min-w-[40px] text-red-400 hover:bg-red-500/10 flex-shrink-0"
                        onClick={() => handleCancel(visitor.id)}
                        data-testid={`delete-visitor-${visitor.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                    
                    {/* Info when inside - cannot delete */}
                    {(visitor.status === 'inside' || visitor.status === 'entry_registered') && (
                      <div 
                        className="h-8 px-2 flex items-center rounded text-[10px] text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 flex-shrink-0"
                        title="No puedes eliminar mientras la persona está dentro del condominio"
                      >
                        <Shield className="w-3 h-3 mr-1" />
                        Dentro
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })
        ) : (
          <div className="text-center py-6 sm:py-8 text-muted-foreground">
            <Users className="w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 sm:mb-4 opacity-30" />
            <p className="text-sm">No tienes visitantes registrados</p>
            <p className="text-xs mt-1">Pre-registra visitantes para agilizar su entrada</p>
          </div>
        )}
      </div>

      {/* Add Visitor Dialog - Mobile optimized */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B] w-[calc(100vw-2rem)] max-w-md mx-auto max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base">
              <UserPlus className="w-5 h-5 text-primary" />
              Pre-registrar Visitante
            </DialogTitle>
            <DialogDescription className="text-xs sm:text-sm">
              El guarda recibirá esta información para verificar al visitante
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-3 sm:space-y-4 py-3 sm:py-4">
            <div>
              <Label className="text-xs text-muted-foreground">Nombre Completo *</Label>
              <Input
                placeholder="Nombre del visitante"
                value={formData.full_name}
                onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                className="bg-[#181B25] border-[#1E293B] mt-1 h-11 text-base"
                data-testid="visitor-name-input"
              />
            </div>

            <div className="grid grid-cols-2 gap-2 sm:gap-3">
              <div>
                <Label className="text-xs text-muted-foreground">Cédula / ID</Label>
                <Input
                  placeholder="Número de ID"
                  value={formData.national_id}
                  onChange={(e) => setFormData({...formData, national_id: e.target.value})}
                  className="bg-[#181B25] border-[#1E293B] mt-1 h-11 text-base"
                />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Placa Vehículo</Label>
                <Input
                  placeholder="ABC-123"
                  value={formData.vehicle_plate}
                  onChange={(e) => setFormData({...formData, vehicle_plate: e.target.value.toUpperCase()})}
                  className="bg-[#181B25] border-[#1E293B] mt-1 h-11 text-base"
                />
              </div>
            </div>

            <div>
              <Label className="text-xs text-muted-foreground">Tipo de Visita</Label>
              <Select 
                value={formData.visit_type} 
                onValueChange={(v) => setFormData({...formData, visit_type: v})}
              >
                <SelectTrigger className="bg-[#181B25] border-[#1E293B] mt-1 h-11">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  {VISIT_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value} className="py-2.5">{type.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:gap-3">
              <div>
                <Label className="text-xs text-muted-foreground">Fecha Esperada *</Label>
                <Input
                  type="date"
                  value={formData.expected_date}
                  onChange={(e) => setFormData({...formData, expected_date: e.target.value})}
                  className="bg-[#181B25] border-[#1E293B] mt-1 h-11"
                />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Hora Aproximada</Label>
                <Input
                  type="time"
                  value={formData.expected_time}
                  onChange={(e) => setFormData({...formData, expected_time: e.target.value})}
                  className="bg-[#181B25] border-[#1E293B] mt-1 h-11"
                />
              </div>
            </div>

            <div>
              <Label className="text-xs text-muted-foreground">Notas</Label>
              <Input
                placeholder="Información adicional para el guarda"
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                className="bg-[#181B25] border-[#1E293B] mt-1 h-11 text-base"
              />
            </div>
          </div>

          <DialogFooter className="flex-col sm:flex-row gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setShowForm(false)} className="w-full sm:w-auto min-h-[44px]">
              Cancelar
            </Button>
            <Button 
              onClick={handleSubmit} 
              disabled={!formData.full_name.trim() || isSubmitting}
              className="w-full sm:w-auto min-h-[44px]"
              data-testid="submit-visitor-btn"
            >
              {isSubmitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <UserPlus className="w-4 h-4 mr-2" />}
              Registrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============================================
// MAIN RESIDENT UI COMPONENT
// ============================================

// Mobile Bottom Nav Configuration for Resident
// Spec: PANIC (center) | Authorizations | Alerts | People | Profile
const RESIDENT_MOBILE_NAV = [
  { id: 'emergency', label: 'Pánico', icon: AlertTriangle, bgColor: 'bg-red-600', glowColor: 'shadow-red-500/50' },
  { id: 'authorizations', label: 'Visitas', icon: Shield },
  { id: 'reservations', label: 'Reservas', icon: CalendarIcon },
  { id: 'directory', label: 'Personas', icon: Users },
  { id: 'profile', label: 'Perfil', icon: User },
];

const ResidentUI = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, logout } = useAuth();
  const isMobile = useIsMobile();
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
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isRefreshingNotifications, setIsRefreshingNotifications] = useState(false);

  // Fetch notifications
  const fetchNotifications = useCallback(async () => {
    try {
      const [notifData, countData] = await Promise.all([
        api.getVisitorNotifications(false),
        api.getResidentUnreadNotificationCount()
      ]);
      
      setNotifications(Array.isArray(notifData) ? notifData.slice(0, 20) : []);
      setUnreadCount(countData?.count || 0);
    } catch (err) {
      console.error('Error fetching notifications:', err);
      setNotifications([]);
      setUnreadCount(0);
    }
  }, []);

  // Initial fetch and polling for notifications
  useEffect(() => {
    fetchNotifications();
    // Refresh every 30 seconds
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // Mark single notification as read
  const handleMarkNotificationRead = async (notificationId, e) => {
    e?.stopPropagation();
    try {
      await api.markNotificationRead(notificationId);
      setNotifications(prev => prev.map(n => 
        n.id === notificationId ? {...n, read: true} : n
      ));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Error marking notification read:', error);
    }
  };

  // Mark all as read when dropdown is open for a while
  const handleNotificationsDropdownOpenChange = async (open) => {
    setIsNotificationsOpen(open);
    
    if (open && unreadCount > 0) {
      // Mark as read after 2 seconds of viewing
      setTimeout(async () => {
        try {
          const result = await api.markAllNotificationsRead();
          setNotifications(prev => prev.map(n => ({...n, read: true})));
          setUnreadCount(0);
        } catch (error) {
          console.error('Error marking all as read:', error);
        }
      }, 2000);
    }
  };

  // Manual refresh notifications
  const handleRefreshNotifications = async (e) => {
    e?.stopPropagation();
    setIsRefreshingNotifications(true);
    await fetchNotifications();
    setIsRefreshingNotifications(false);
    toast.success('Notificaciones actualizadas');
  };

  // Manual mark all as read
  const handleMarkAllRead = async (e) => {
    e?.stopPropagation();
    if (unreadCount === 0) return;
    
    try {
      const result = await api.markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({...n, read: true})));
      setUnreadCount(0);
      toast.success('Notificaciones marcadas como leídas');
    } catch (error) {
      toast.error('Error al marcar notificaciones');
    }
  };

  // Push notifications are handled by PushPermissionBanner component
  // which shows a banner for ALL roles to subscribe to push notifications
  
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
      console.log('[Panic] Sending alert:', emergencyType, 'GPS:', location);
      
      const result = await api.triggerPanic({
        panic_type: emergencyType,
        location: `Residencia de ${user.full_name}`,
        latitude: location?.latitude,
        longitude: location?.longitude,
        description: `Alerta ${EMERGENCY_TYPES[emergencyType].label} activada por ${user.full_name}`,
      });

      console.log('[Panic] Alert sent successfully:', result);
      if (navigator.vibrate) navigator.vibrate([200, 100, 200, 100, 300]);

      setSentAlert({
        type: emergencyType,
        guards: result.notified_guards,
        location: location,
        time: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }),
      });

      setTimeout(() => setSentAlert(null), 20000);
    } catch (error) {
      console.error('[Panic] Error details:', error);
      if (navigator.vibrate) navigator.vibrate(500);
      
      // Mensaje específico según el error
      let errorMessage = 'Error al enviar alerta. Intenta de nuevo o llama al 911.';
      const status = error.status || error.response?.status;
      const detail = error.data?.detail || error.message;
      
      console.log('[Panic] Error status:', status, 'detail:', detail);
      
      if (status === 401) {
        errorMessage = 'Sesión expirada. Por favor, inicia sesión nuevamente.';
      } else if (status === 403) {
        errorMessage = detail || 'No tienes permisos para enviar alertas. Contacta al administrador.';
      } else if (status === 422) {
        errorMessage = 'Datos incompletos. Verifica tu ubicación GPS.';
      } else if (detail) {
        errorMessage = detail;
      }
      
      toast.error('Error de Emergencia', {
        description: errorMessage,
        duration: 10000,
      });
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
    <div className={`min-h-screen bg-[#05050A] flex flex-col safe-area overflow-x-hidden ${isMobile ? 'pb-20' : ''}`}>
      {/* Header - Mobile First: Compact, touch-friendly */}
      <header className="flex items-center justify-between px-3 py-2.5 sm:px-4 sm:py-3 border-b border-[#1E293B]/50 flex-shrink-0">
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-primary/20 flex items-center justify-center flex-shrink-0">
            <Shield className="w-4 h-4 sm:w-5 sm:h-5 text-primary" />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-sm font-bold text-white">GENTURIX</h1>
            <p className="text-xs text-muted-foreground truncate">{user?.full_name}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {/* Notifications Bell - Touch-friendly 44px min */}
          <DropdownMenu open={isNotificationsOpen} onOpenChange={handleNotificationsDropdownOpenChange}>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="relative h-11 w-11 min-h-[44px] min-w-[44px]"
                data-testid="resident-notifications-btn"
              >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span 
                    className="absolute top-1.5 right-1.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-[10px] font-bold flex items-center justify-center animate-pulse"
                    data-testid="resident-notification-badge"
                  >
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[calc(100vw-2rem)] max-w-sm bg-[#0F111A] border-[#1E293B]">
              <DropdownMenuLabel className="flex items-center justify-between px-3 py-2">
                <span className="text-sm">Notificaciones</span>
                <div className="flex items-center gap-1.5">
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-8 w-8 p-0"
                    onClick={handleRefreshNotifications}
                    disabled={isRefreshingNotifications}
                  >
                    <RefreshCw className={`w-4 h-4 ${isRefreshingNotifications ? 'animate-spin' : ''}`} />
                  </Button>
                  {unreadCount > 0 && (
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-8 w-8 p-0 text-primary"
                      onClick={handleMarkAllRead}
                      title="Marcar todas como leídas"
                    >
                      <CheckCheck className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-[#1E293B]" />
              {notifications.length === 0 ? (
                <div className="p-6 text-center text-sm text-muted-foreground">
                  <Bell className="w-10 h-10 mx-auto mb-3 opacity-30" />
                  No tienes notificaciones
                </div>
              ) : (
                <div className="max-h-[60vh] overflow-y-auto overscroll-contain">
                  {notifications.map((notif) => (
                    <DropdownMenuItem 
                      key={notif.id} 
                      className={`flex items-start gap-3 py-3 px-3 min-h-[60px] cursor-pointer ${!notif.read ? 'bg-primary/5' : ''}`}
                    >
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${
                        notif.type === 'visitor_arrival' 
                          ? 'bg-green-500/20 text-green-400' 
                          : 'bg-orange-500/20 text-orange-400'
                      }`}>
                        {notif.type === 'visitor_arrival' ? (
                          <UserCheck className="w-4 h-4" />
                        ) : (
                          <LogOut className="w-4 h-4" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm leading-tight ${notif.read ? 'text-muted-foreground' : 'font-medium'}`}>
                          {notif.type === 'visitor_arrival' ? 'Visitante ingresó' : 'Visitante salió'}
                        </p>
                        <p className="text-xs text-muted-foreground truncate mt-0.5">
                          {notif.visitor_name || 'Visitante'}
                        </p>
                        <p className="text-[10px] text-muted-foreground mt-1">
                          {new Date(notif.created_at).toLocaleString('es-ES', { 
                            day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                          })}
                        </p>
                      </div>
                      {!notif.read && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0 flex-shrink-0"
                          onClick={(e) => handleMarkNotificationRead(notif.id, e)}
                          title="Marcar como leída"
                        >
                          <Check className="w-4 h-4" />
                        </Button>
                      )}
                    </DropdownMenuItem>
                  ))}
                </div>
              )}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Logout Button - Touch-friendly */}
          <button
            onClick={handleLogout}
            className="p-2.5 min-h-[44px] min-w-[44px] rounded-lg text-muted-foreground hover:text-white hover:bg-white/5 transition-colors flex items-center justify-center"
            data-testid="logout-btn"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Desktop Tabs - hidden on mobile */}
        {!isMobile && (
          <TabsList className="grid grid-cols-5 bg-[#0F111A] border-b border-[#1E293B] rounded-none h-12 flex-shrink-0">
            <TabsTrigger 
              value="emergency" 
              className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-red-500 rounded-none flex flex-col items-center gap-0.5 text-[10px]"
              data-testid="tab-emergency"
            >
              <AlertTriangle className="w-4 h-4 text-red-400" />
              Emergencia
            </TabsTrigger>
            <TabsTrigger 
              value="authorizations" 
              className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none flex flex-col items-center gap-0.5 text-[10px]"
              data-testid="tab-authorizations"
            >
              <Shield className="w-4 h-4 text-primary" />
              Visitas
            </TabsTrigger>
            <TabsTrigger 
              value="reservations" 
              className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-green-500 rounded-none flex flex-col items-center gap-0.5 text-[10px]"
              data-testid="tab-reservations"
            >
              <CalendarIcon className="w-4 h-4 text-green-400" />
              Reservas
            </TabsTrigger>
            <TabsTrigger 
              value="directory" 
              className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-cyan-500 rounded-none flex flex-col items-center gap-0.5 text-[10px]"
              data-testid="tab-directory"
            >
              <Users className="w-4 h-4 text-cyan-400" />
              Personas
            </TabsTrigger>
            <TabsTrigger 
              value="profile" 
              className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-amber-500 rounded-none flex flex-col items-center gap-0.5 text-[10px]"
              data-testid="tab-profile"
            >
              <User className="w-4 h-4 text-amber-400" />
              Perfil
            </TabsTrigger>
          </TabsList>
        )}

        <TabsContent value="emergency" className="flex-1 flex flex-col mt-0 overflow-hidden">
          <EmergencyTab
            location={location}
            locationLoading={locationLoading}
            locationError={locationError}
            onEmergency={handleEmergency}
            sendingType={sendingType}
          />
        </TabsContent>

        <TabsContent value="authorizations" className="flex-1 mt-0 overflow-y-auto overflow-x-hidden">
          <ResidentVisitsModule 
            notifications={notifications}
            onRefreshNotifications={fetchNotifications}
          />
        </TabsContent>

        <TabsContent value="reservations" className="flex-1 mt-0 overflow-y-auto overflow-x-hidden">
          <ResidentReservations />
        </TabsContent>
        
        <TabsContent value="directory" className="flex-1 mt-0 overflow-hidden">
          <ProfileDirectory embedded={true} maxHeight={isMobile ? "calc(100vh - 140px)" : "calc(100vh - 180px)"} />
        </TabsContent>
        
        <TabsContent value="profile" className="flex-1 mt-0 overflow-y-auto overflow-x-hidden">
          <EmbeddedProfile onBack={() => setActiveTab('panic')} />
        </TabsContent>
      </Tabs>

      {/* Emergency Call Footer - Hidden on mobile (use bottom nav) */}
      {!isMobile && (
        <footer className="p-3 sm:p-4 border-t border-[#1E293B]/50 flex-shrink-0">
          <a
            href="tel:911"
            className="flex items-center justify-center gap-3 py-3.5 sm:py-4 rounded-xl bg-[#1E293B] hover:bg-[#2D3B4F] border border-[#3D4B5F] transition-colors min-h-[48px]"
          >
            <Phone className="w-5 h-5 text-red-400" />
            <span className="text-white font-semibold text-sm sm:text-base">Llamar al 911</span>
          </a>
        </footer>
      )}

      {/* Mobile Bottom Navigation */}
      {isMobile && (
        <MobileBottomNav 
          items={RESIDENT_MOBILE_NAV}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          centerIndex={0}
        />
      )}
      
      {/* Push Permission Banner */}
      <PushPermissionBanner onSubscribed={() => console.log('Push notifications enabled!')} />
    </div>
  );
};

export default ResidentUI;
