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
import api from '../services/api';
import ProfileDirectory from '../components/ProfileDirectory';
import EmbeddedProfile from '../components/EmbeddedProfile';
import VisitorAuthorizationsResident from '../components/VisitorAuthorizationsResident';
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
  User
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
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold flex items-center gap-2">
          <History className="w-5 h-5 text-primary" />
          Mis Alertas
        </h2>
        <span className="text-xs text-muted-foreground">{alerts.length} alertas</span>
      </div>

      {alerts.length === 0 ? (
        <div className="text-center py-12">
          <Bell className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
          <p className="text-muted-foreground">No has enviado alertas</p>
          <p className="text-xs text-muted-foreground mt-1">Las alertas que envíes aparecerán aquí</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => {
            const statusConfig = getStatusConfig(alert.status);
            const typeConfig = getTypeConfig(alert.panic_type);
            const IconComponent = typeConfig.icon;

            return (
              <div 
                key={alert.id} 
                className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]"
                data-testid={`alert-history-${alert.id}`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-lg ${typeConfig.colors.bg} flex items-center justify-center flex-shrink-0`}>
                    <IconComponent className={`w-5 h-5 ${typeConfig.colors.text}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-semibold text-sm truncate">{alert.panic_type_label || typeConfig.label}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs border ${statusConfig.color}`}>
                        {statusConfig.label}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mb-2">{alert.location}</p>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">
                        {new Date(alert.created_at).toLocaleDateString('es-ES', { 
                          day: '2-digit', 
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>
                      {alert.resolved_by_name && (
                        <span className="text-green-400">
                          Atendido por: {alert.resolved_by_name}
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
      fetchVisitors();
    } catch (error) {
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
    <div className="p-4 space-y-4">
      {/* Add Visitor Button */}
      <Button 
        className="w-full" 
        onClick={() => setShowForm(true)}
        data-testid="add-visitor-btn"
      >
        <UserPlus className="w-4 h-4 mr-2" />
        Pre-registrar Visitante
      </Button>

      {/* Visitors List */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-muted-foreground">Mis Visitantes</h3>
        
        {visitors.length > 0 ? (
          visitors.map((visitor) => {
            const status = STATUS_CONFIG[visitor.status] || STATUS_CONFIG.pending;
            
            return (
              <Card key={visitor.id} className="bg-[#0F111A] border-[#1E293B]">
                <CardContent className="p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-white text-sm truncate">{visitor.full_name}</span>
                        <Badge className={status.color}>{status.label}</Badge>
                      </div>
                      
                      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
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

                    {visitor.status === 'pending' && (
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8 text-red-400 hover:bg-red-500/10"
                        onClick={() => handleCancel(visitor.id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Users className="w-12 h-12 mx-auto mb-4 opacity-30" />
            <p className="text-sm">No tienes visitantes registrados</p>
            <p className="text-xs mt-1">Pre-registra visitantes para agilizar su entrada</p>
          </div>
        )}
      </div>

      {/* Add Visitor Dialog */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-primary" />
              Pre-registrar Visitante
            </DialogTitle>
            <DialogDescription>
              El guarda recibirá esta información para verificar al visitante
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-xs text-muted-foreground">Nombre Completo *</Label>
              <Input
                placeholder="Nombre del visitante"
                value={formData.full_name}
                onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                className="bg-[#181B25] border-[#1E293B] mt-1"
                data-testid="visitor-name-input"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-muted-foreground">Cédula / ID</Label>
                <Input
                  placeholder="Número de ID"
                  value={formData.national_id}
                  onChange={(e) => setFormData({...formData, national_id: e.target.value})}
                  className="bg-[#181B25] border-[#1E293B] mt-1"
                />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Placa Vehículo</Label>
                <Input
                  placeholder="ABC-123"
                  value={formData.vehicle_plate}
                  onChange={(e) => setFormData({...formData, vehicle_plate: e.target.value.toUpperCase()})}
                  className="bg-[#181B25] border-[#1E293B] mt-1"
                />
              </div>
            </div>

            <div>
              <Label className="text-xs text-muted-foreground">Tipo de Visita</Label>
              <Select 
                value={formData.visit_type} 
                onValueChange={(v) => setFormData({...formData, visit_type: v})}
              >
                <SelectTrigger className="bg-[#181B25] border-[#1E293B] mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  {VISIT_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs text-muted-foreground">Fecha Esperada *</Label>
                <Input
                  type="date"
                  value={formData.expected_date}
                  onChange={(e) => setFormData({...formData, expected_date: e.target.value})}
                  className="bg-[#181B25] border-[#1E293B] mt-1"
                />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Hora Aproximada</Label>
                <Input
                  type="time"
                  value={formData.expected_time}
                  onChange={(e) => setFormData({...formData, expected_time: e.target.value})}
                  className="bg-[#181B25] border-[#1E293B] mt-1"
                />
              </div>
            </div>

            <div>
              <Label className="text-xs text-muted-foreground">Notas</Label>
              <Input
                placeholder="Información adicional para el guarda"
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowForm(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={handleSubmit} 
              disabled={!formData.full_name.trim() || isSubmitting}
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
    <div className={`min-h-screen bg-[#05050A] flex flex-col safe-area ${isMobile ? 'pb-20' : ''}`}>
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
        {/* Desktop Tabs - hidden on mobile */}
        {!isMobile && (
          <TabsList className="grid grid-cols-5 bg-[#0F111A] border-b border-[#1E293B] rounded-none h-12">
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
              value="history" 
              className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-yellow-500 rounded-none flex flex-col items-center gap-0.5 text-[10px]"
              data-testid="tab-history"
            >
              <History className="w-4 h-4 text-yellow-400" />
              Mis Alertas
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

        <TabsContent value="emergency" className="flex-1 flex flex-col mt-0">
          <EmergencyTab
            location={location}
            locationLoading={locationLoading}
            locationError={locationError}
            onEmergency={handleEmergency}
            sendingType={sendingType}
          />
        </TabsContent>

        <TabsContent value="authorizations" className="flex-1 mt-0">
          <VisitorAuthorizationsResident />
        </TabsContent>

        <TabsContent value="history" className="flex-1 mt-0">
          <ScrollArea className={isMobile ? "h-[calc(100vh-160px)]" : "h-[calc(100vh-180px)]"}>
            <AlertHistoryTab />
          </ScrollArea>
        </TabsContent>
        
        <TabsContent value="directory" className="flex-1 mt-0">
          <ProfileDirectory embedded={true} maxHeight={isMobile ? "calc(100vh - 160px)" : "calc(100vh - 180px)"} />
        </TabsContent>
        
        <TabsContent value="profile" className="flex-1 mt-0">
          <EmbeddedProfile />
        </TabsContent>
      </Tabs>

      {/* Emergency Call Footer - Hidden on mobile (use bottom nav) */}
      {!isMobile && (
        <footer className="p-4 border-t border-[#1E293B]/50">
          <a
            href="tel:911"
            className="flex items-center justify-center gap-3 py-4 rounded-xl bg-[#1E293B] hover:bg-[#2D3B4F] border border-[#3D4B5F] transition-colors"
          >
            <Phone className="w-5 h-5 text-red-400" />
            <span className="text-white font-semibold">Llamar al 911</span>
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
    </div>
  );
};

export default ResidentUI;
