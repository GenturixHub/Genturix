/**
 * GENTURIX - GuardUI (Operational Security Panel)
 * 
 * Optimized for real-world guard/casetilla usage:
 * - Tab-based navigation (no excessive scrolling)
 * - Large touch targets (usable with gloves/stress)
 * - High contrast emergency color coding
 * - Fast visual scanning
 * - Mobile-first, desktop optimized
 * 
 * TABS:
 * 1. ALERTAS - Active panic alerts
 * 2. CHECK-IN - Advanced visitor authorization & check-in
 * 3. VISITAS - Pre-registered visitors (legacy)
 * 4. MI TURNO - Shift management
 * 5. HISTORIAL - Read-only past records
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
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
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '../components/ui/accordion';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import api from '../services/api';
import AlertSoundManager from '../utils/AlertSoundManager';
import pushManager from '../utils/PushNotificationManager';
import PushNotificationBanner from '../components/PushNotificationBanner';
import PushPermissionBanner from '../components/PushPermissionBanner';
import VisitorCheckInGuard from '../components/VisitorCheckInGuard';
import GuardHistoryVisual from '../components/GuardHistoryVisual';
import { 
  Shield, 
  LogOut,
  AlertTriangle,
  MapPin,
  Clock,
  CheckCircle,
  Navigation,
  Loader2,
  RefreshCw,
  Heart,
  Search,
  Siren,
  Bell,
  Phone,
  UserPlus,
  UserMinus,
  Users,
  History,
  Eye,
  Car,
  Calendar,
  CalendarOff,
  CalendarPlus,
  CalendarDays,
  User,
  Home,
  FileText,
  ChevronRight,
  ExternalLink,
  Briefcase,
  CalendarClock,
  CalendarX,
  PlayCircle,
  StopCircle,
  Users as UsersIcon,
  ScanLine
} from 'lucide-react';
import { ScrollArea } from '../components/ui/scroll-area';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import EmbeddedProfile from '../components/EmbeddedProfile';
import ProfileDirectory from '../components/ProfileDirectory';
import MobileBottomNav, { useIsMobile } from '../components/layout/BottomNav';

// ============================================
// CONFIGURATION
// ============================================
const PANIC_CONFIG = {
  emergencia_medica: { 
    icon: Heart, 
    bg: 'bg-red-600',
    bgLight: 'bg-red-500/15',
    border: 'border-red-500/40',
    text: 'text-red-400',
    label: 'MÉDICA',
    priority: 1
  },
  actividad_sospechosa: { 
    icon: Eye, 
    bg: 'bg-amber-500',
    bgLight: 'bg-amber-500/15',
    border: 'border-amber-500/40',
    text: 'text-amber-400',
    label: 'SOSPECHOSO',
    priority: 2
  },
  emergencia_general: { 
    icon: Siren, 
    bg: 'bg-orange-500',
    bgLight: 'bg-orange-500/15',
    border: 'border-orange-500/40',
    text: 'text-orange-400',
    label: 'GENERAL',
    priority: 3
  }
};

const VISIT_TYPES = {
  familiar: 'Familiar',
  friend: 'Amigo',
  delivery: 'Delivery',
  service: 'Servicio',
  other: 'Otro'
};

// ============================================
// UTILITY FUNCTIONS
// ============================================
const formatTime = (timestamp) => {
  if (!timestamp) return '--:--';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
};

const formatRelativeTime = (timestamp) => {
  if (!timestamp) return '';
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return 'Ahora';
  if (diffMins < 60) return `${diffMins}m`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h`;
  return date.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
};

const openMaps = (lat, lng) => {
  if (!lat || !lng) return;
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
  const url = isIOS 
    ? `maps://maps.apple.com/?q=${lat},${lng}`
    : `https://www.google.com/maps/search/?api=1&query=${lat},${lng}`;
  window.open(url, '_blank');
};

// ============================================
// ============================================
// TAB 1: ALERTS (with Interactive Modal)
// ============================================
const AlertsTab = ({ alerts, onResolve, resolvingId, onRefresh, isRefreshing, highlightedAlertId }) => {
  const [selectedAlert, setSelectedAlert] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [isResolving, setIsResolving] = useState(false);

  const activeAlerts = alerts.filter(a => a.status === 'active');
  const recentResolved = alerts.filter(a => a.status === 'resolved').slice(0, 5);

  // Auto-open highlighted alert from push notification
  useEffect(() => {
    if (highlightedAlertId) {
      const alertToOpen = alerts.find(a => a.id === highlightedAlertId);
      if (alertToOpen && alertToOpen.status === 'active') {
        handleOpenAlert(alertToOpen);
      }
    }
  }, [highlightedAlertId, alerts]);

  const handleOpenAlert = (alert) => {
    // CRITICAL: Stop panic sound immediately when opening an alert
    AlertSoundManager.stop();
    setSelectedAlert(alert);
    setResolutionNotes('');
    setShowModal(true);
  };

  const handleResolve = async () => {
    if (!selectedAlert) return;
    // CRITICAL: Stop sound when resolving alert
    AlertSoundManager.stop();
    setIsResolving(true);
    try {
      await onResolve(selectedAlert.id, resolutionNotes);
      toast.success('Alerta resuelta correctamente');
      setShowModal(false);
      setSelectedAlert(null);
      setResolutionNotes('');
    } catch (err) {
      toast.error(err.message || 'Error al resolver alerta');
    } finally {
      setIsResolving(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Active Alerts Counter */}
      <div className={`p-3 ${activeAlerts.length > 0 ? 'bg-red-500/20 border-b-2 border-red-500' : 'bg-green-500/10 border-b border-green-500/30'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {activeAlerts.length > 0 ? (
              <>
                <Bell className="w-5 h-5 text-red-400 animate-pulse" />
                <span className="font-bold text-red-400">{activeAlerts.length} ALERTA{activeAlerts.length > 1 ? 'S' : ''} ACTIVA{activeAlerts.length > 1 ? 'S' : ''}</span>
              </>
            ) : (
              <>
                <CheckCircle className="w-5 h-5 text-green-400" />
                <span className="font-bold text-green-400">SIN ALERTAS ACTIVAS</span>
              </>
            )}
          </div>
          <Button size="sm" variant="ghost" onClick={onRefresh} disabled={isRefreshing}>
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Alerts Grid */}
      <div className="flex-1 overflow-auto p-3">
        {activeAlerts.length > 0 && (
          <div className="mb-4">
            <h3 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2">🚨 REQUIEREN ATENCIÓN</h3>
            <div className="grid gap-2 sm:grid-cols-2">
              {activeAlerts.map((alert) => (
                <AlertCard 
                  key={alert.id} 
                  alert={alert} 
                  onClick={() => handleOpenAlert(alert)}
                  isResolving={resolvingId === alert.id}
                  isHighlighted={alert.id === highlightedAlertId}
                />
              ))}
            </div>
          </div>
        )}

        {recentResolved.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Atendidas recientemente</h3>
            <div className="grid gap-2 sm:grid-cols-2">
              {recentResolved.map((alert) => (
                <AlertCard key={alert.id} alert={alert} onClick={() => handleOpenAlert(alert)} resolved />
              ))}
            </div>
          </div>
        )}

        {alerts.length === 0 && (
          <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
            <Shield className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-lg font-medium">Todo en orden</p>
            <p className="text-sm">No hay alertas registradas</p>
          </div>
        )}
      </div>

      {/* Panic Alert Detail Modal */}
      <PanicAlertModal 
        alert={selectedAlert}
        open={showModal}
        onClose={() => { setShowModal(false); setSelectedAlert(null); }}
        onResolve={handleResolve}
        resolutionNotes={resolutionNotes}
        setResolutionNotes={setResolutionNotes}
        isResolving={isResolving}
      />
    </div>
  );
};

// ============================================
// PANIC ALERT DETAIL MODAL
// ============================================
const PanicAlertModal = ({ alert, open, onClose, onResolve, resolutionNotes, setResolutionNotes, isResolving }) => {
  if (!alert) return null;

  const config = PANIC_CONFIG[alert.panic_type] || PANIC_CONFIG.emergencia_general;
  const IconComponent = config.icon;
  const hasLocation = alert.latitude && alert.longitude;
  const isResolved = alert.status === 'resolved';

  const formatDateTime = (timestamp) => {
    if (!timestamp) return 'No disponible';
    const date = new Date(timestamp);
    return date.toLocaleString('es-ES', {
      weekday: 'short',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0A0A0F] border-[#1E293B] max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-xl ${config.bg} flex items-center justify-center`}>
              <IconComponent className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className={`text-lg ${config.text}`}>{config.label}</span>
              <Badge 
                variant="outline" 
                className={isResolved 
                  ? 'ml-2 border-green-500/30 text-green-400' 
                  : 'ml-2 border-red-500/30 text-red-400 animate-pulse'
                }
              >
                {isResolved ? 'RESUELTA' : 'ACTIVA'}
              </Badge>
            </div>
          </DialogTitle>
          <DialogDescription>
            Detalles completos de la alerta de emergencia
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Resident Information */}
          <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
            <h4 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-3">
              <User className="w-4 h-4 inline mr-2" />
              Información del Residente
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-muted-foreground">Nombre Completo</Label>
                <p className="text-white font-semibold">{alert.user_name || 'No disponible'}</p>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Apartamento / Casa</Label>
                <p className="text-white font-semibold">{alert.location || alert.apartment || 'No especificado'}</p>
              </div>
              {alert.phone && (
                <div>
                  <Label className="text-xs text-muted-foreground">Teléfono</Label>
                  <a href={`tel:${alert.phone}`} className="text-blue-400 hover:underline flex items-center gap-1">
                    <Phone className="w-3 h-3" />
                    {alert.phone}
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Alert Details */}
          <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
            <h4 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-3">
              <AlertTriangle className="w-4 h-4 inline mr-2" />
              Detalles de la Alerta
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-muted-foreground">Tipo de Emergencia</Label>
                <Badge className={`${config.bg} text-white`}>{alert.panic_type_label || config.label}</Badge>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Fecha y Hora</Label>
                <p className="text-white text-sm">{formatDateTime(alert.created_at)}</p>
              </div>
              {isResolved && alert.resolved_at && (
                <>
                  <div>
                    <Label className="text-xs text-muted-foreground">Resuelta</Label>
                    <p className="text-green-400 text-sm">{formatDateTime(alert.resolved_at)}</p>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Atendida por</Label>
                    <p className="text-white text-sm">{alert.resolved_by_name || 'No registrado'}</p>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Resident Notes - IMPORTANT */}
          {(alert.notes || alert.description) && (
            <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30">
              <h4 className="text-sm font-bold text-yellow-400 uppercase tracking-wider mb-2">
                <FileText className="w-4 h-4 inline mr-2" />
                Notas del Residente
              </h4>
              <p className="text-white whitespace-pre-wrap">{alert.notes || alert.description}</p>
            </div>
          )}

          {/* Map Section */}
          {hasLocation && (
            <div className="rounded-xl overflow-hidden border border-[#1E293B]">
              <h4 className="text-sm font-bold text-muted-foreground uppercase tracking-wider p-3 bg-[#0F111A]">
                <MapPin className="w-4 h-4 inline mr-2" />
                Ubicación en Mapa
              </h4>
              
              {/* Embedded Map using OpenStreetMap - Reduced height on mobile */}
              <div className="relative w-full overflow-hidden">
                <iframe
                  title="Ubicación de la alerta"
                  className="w-full h-[150px] sm:h-[180px]"
                  style={{ border: 0, maxWidth: '100%' }}
                  loading="lazy"
                  src={`https://www.openstreetmap.org/export/embed.html?bbox=${alert.longitude - 0.002},${alert.latitude - 0.002},${alert.longitude + 0.002},${alert.latitude + 0.002}&layer=mapnik&marker=${alert.latitude},${alert.longitude}`}
                />
              </div>
              
              {/* Map Actions - Stack on mobile */}
              <div className="p-3 bg-[#0F111A] flex flex-col sm:flex-row gap-2">
                <Button 
                  variant="outline" 
                  size="sm"
                  className="border-blue-500/30 text-blue-400 hover:bg-blue-500/10 w-full sm:w-auto"
                  onClick={() => openMaps(alert.latitude, alert.longitude)}
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Abrir en Maps
                </Button>
                <div className="text-xs text-muted-foreground flex items-center justify-center sm:justify-start">
                  <MapPin className="w-3 h-3 mr-1 flex-shrink-0" />
                  <span className="truncate">{alert.latitude.toFixed(4)}, {alert.longitude.toFixed(4)}</span>
                </div>
              </div>
            </div>
          )}

          {/* Resolution Section (only if not resolved) */}
          {!isResolved && (
            <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
              <h4 className="text-sm font-bold text-muted-foreground uppercase tracking-wider mb-3">
                <CheckCircle className="w-4 h-4 inline mr-2" />
                Resolución
              </h4>
              <div className="space-y-3">
                <div>
                  <Label className="text-xs text-muted-foreground">Notas de resolución (opcional)</Label>
                  <Textarea
                    placeholder="Describe las acciones tomadas..."
                    value={resolutionNotes}
                    onChange={(e) => setResolutionNotes(e.target.value)}
                    className="bg-[#0A0A0F] border-[#1E293B] mt-1 min-h-[80px]"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {hasLocation && (
            <Button 
              variant="outline"
              className="w-full sm:w-auto border-blue-500/30 text-blue-400"
              onClick={() => openMaps(alert.latitude, alert.longitude)}
            >
              <Navigation className="w-4 h-4 mr-2" />
              IR A UBICACIÓN
            </Button>
          )}
          
          {!isResolved && (
            <Button 
              className="w-full sm:w-auto bg-green-600 hover:bg-green-700 font-bold"
              onClick={onResolve}
              disabled={isResolving}
            >
              {isResolving ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <CheckCircle className="w-4 h-4 mr-2" />
              )}
              MARCAR COMO ATENDIDA
            </Button>
          )}
          
          <Button variant="outline" onClick={onClose}>
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

const AlertCard = ({ alert, onClick, isResolving, resolved, isHighlighted }) => {
  const config = PANIC_CONFIG[alert.panic_type] || PANIC_CONFIG.emergencia_general;
  const IconComponent = config.icon;
  const hasLocation = alert.latitude && alert.longitude;

  return (
    <div 
      className={`p-3 rounded-xl border-2 cursor-pointer transition-all hover:scale-[1.02] ${
        isHighlighted 
          ? 'ring-4 ring-yellow-400 ring-opacity-75 animate-pulse' 
          : ''
      } ${resolved ? 'bg-[#0F111A] border-[#1E293B] opacity-60' : `${config.bgLight} ${config.border}`}`}
      data-testid={`alert-${alert.id}`}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`w-12 h-12 rounded-xl ${config.bg} flex items-center justify-center flex-shrink-0 ${!resolved && 'animate-pulse'}`}>
          <IconComponent className="w-6 h-6 text-white" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge className={`${config.bg} text-white font-bold text-xs`}>{config.label}</Badge>
            <span className="text-xs text-muted-foreground">{formatRelativeTime(alert.created_at)}</span>
          </div>
          
          <p className="font-semibold text-white text-sm truncate">{alert.user_name || 'Residente'}</p>
          
          <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
            <MapPin className="w-3 h-3" />
            <span className="truncate">{alert.location || 'Ubicación no especificada'}</span>
          </div>
          
          {(alert.notes || alert.description) && (
            <p className="text-xs text-yellow-400 mt-1 truncate">📝 {alert.notes || alert.description}</p>
          )}
        </div>
        
        <ChevronRight className="w-5 h-5 text-muted-foreground flex-shrink-0" />
      </div>

      {/* Quick Status Indicators */}
      <div className="flex gap-2 mt-3 justify-end">
        {hasLocation && (
          <Badge variant="outline" className="text-xs border-blue-500/30 text-blue-400">
            <MapPin className="w-3 h-3 mr-1" />
            GPS
          </Badge>
        )}
        {resolved && (
          <Badge variant="outline" className="text-xs border-green-500/30 text-green-400">
            <CheckCircle className="w-3 h-3 mr-1" />
            Atendida
          </Badge>
        )}
      </div>
    </div>
  );
};

// ============================================
// TAB 2: VISITS (Pre-registered)
// ============================================
const VisitsTab = ({ onRefresh }) => {
  const [data, setData] = useState({ pending: [], inside: [], exits: [] });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeSection, setActiveSection] = useState('inside'); // inside, pending, exits

  const fetchData = useCallback(async () => {
    try {
      const result = await api.getVisitsSummary();
      setData(result);
    } catch (error) {
      console.error('Error fetching visits summary:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Filter all sections by search
  const filterBySearch = (items) => {
    if (!search) return items;
    const searchLower = search.toLowerCase();
    return items.filter(item => 
      (item.visitor_name || item.full_name || '').toLowerCase().includes(searchLower) ||
      (item.identification_number || item.national_id || '').toLowerCase().includes(searchLower) ||
      (item.vehicle_plate || '').toLowerCase().includes(searchLower) ||
      (item.created_by_name || item.resident_name || '').toLowerCase().includes(searchLower) ||
      (item.company || '').toLowerCase().includes(searchLower)
    );
  };

  const filteredInside = filterBySearch(data.inside || []);
  const filteredPending = filterBySearch(data.pending || []);
  const filteredExits = filterBySearch(data.exits || []);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header with Search */}
      <div className="p-3 border-b border-[#1E293B]">
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Buscar visitante, placa, empresa..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10 h-11 bg-[#0A0A0F] border-[#1E293B] text-base"
            data-testid="visits-search"
          />
        </div>
        
        {/* Section Tabs */}
        <div className="flex gap-2">
          <button
            onClick={() => setActiveSection('inside')}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
              activeSection === 'inside' 
                ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                : 'bg-[#0F111A] text-muted-foreground border border-[#1E293B]'
            }`}
            data-testid="visits-tab-inside"
          >
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            Dentro ({data.inside?.length || 0})
          </button>
          <button
            onClick={() => setActiveSection('pending')}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
              activeSection === 'pending' 
                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' 
                : 'bg-[#0F111A] text-muted-foreground border border-[#1E293B]'
            }`}
            data-testid="visits-tab-pending"
          >
            <CalendarDays className="w-4 h-4" />
            Pendientes ({data.pending?.length || 0})
          </button>
          <button
            onClick={() => setActiveSection('exits')}
            className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
              activeSection === 'exits' 
                ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' 
                : 'bg-[#0F111A] text-muted-foreground border border-[#1E293B]'
            }`}
            data-testid="visits-tab-exits"
          >
            <UserMinus className="w-4 h-4" />
            Salidas ({data.exits?.length || 0})
          </button>
        </div>
        
        <p className="text-[10px] text-muted-foreground mt-2 text-center">
          👁️ Vista de solo lectura. Para registrar entradas/salidas usa <span className="text-primary font-medium">Check-In</span>
        </p>
      </div>

      {/* Content based on active section */}
      <div className="flex-1 overflow-auto p-3 space-y-3">
        {/* INSIDE Section */}
        {activeSection === 'inside' && (
          filteredInside.length > 0 ? (
            <div className="grid gap-2 sm:grid-cols-2">
              {filteredInside.map((entry) => (
                <VisitCard key={entry.id} item={entry} type="inside" />
              ))}
            </div>
          ) : (
            <EmptyState icon={Users} message="No hay visitantes dentro" subMessage="Aparecerán aquí cuando entren" />
          )
        )}

        {/* PENDING Section - Grouped by Resident */}
        {activeSection === 'pending' && (
          filteredPending.length > 0 ? (
            (() => {
              // Group authorizations by resident
              const groupedByResident = filteredPending.reduce((acc, auth) => {
                const residentKey = auth.created_by || 'unknown';
                if (!acc[residentKey]) {
                  acc[residentKey] = {
                    resident_name: auth.created_by_name || 'Residente',
                    resident_apartment: auth.resident_apartment || '',
                    authorizations: []
                  };
                }
                acc[residentKey].authorizations.push(auth);
                return acc;
              }, {});
              
              const residentKeys = Object.keys(groupedByResident);
              
              return (
                <Accordion type="multiple" defaultValue={residentKeys} className="space-y-2">
                  {residentKeys.map((residentKey) => {
                    const group = groupedByResident[residentKey];
                    return (
                      <AccordionItem 
                        key={residentKey} 
                        value={residentKey}
                        className="border border-[#1E293B] rounded-xl bg-[#0F111A]/50 overflow-hidden"
                        data-testid={`pending-resident-${residentKey}`}
                      >
                        <AccordionTrigger className="px-4 py-3 hover:no-underline hover:bg-[#1E293B]/30">
                          <div className="flex items-center gap-3 w-full">
                            <div className="w-10 h-10 rounded-lg bg-blue-500/20 border border-blue-500/30 flex items-center justify-center flex-shrink-0">
                              <Home className="w-5 h-5 text-blue-400" />
                            </div>
                            <div className="flex-1 text-left">
                              <p className="font-semibold text-white text-sm">{group.resident_name}</p>
                              {group.resident_apartment && (
                                <p className="text-xs text-muted-foreground">{group.resident_apartment}</p>
                              )}
                            </div>
                            <Badge className="bg-blue-500/20 text-blue-400 border border-blue-500/30 mr-2">
                              {group.authorizations.length} visitante{group.authorizations.length !== 1 ? 's' : ''}
                            </Badge>
                          </div>
                        </AccordionTrigger>
                        <AccordionContent className="px-3 pb-3">
                          <div className="grid gap-2 pt-1">
                            {group.authorizations.map((auth) => (
                              <VisitCard key={auth.id} item={auth} type="pending" />
                            ))}
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    );
                  })}
                </Accordion>
              );
            })()
          ) : (
            <EmptyState icon={CalendarDays} message="No hay pre-registros pendientes" subMessage="Los residentes pueden crear autorizaciones" />
          )
        )}

        {/* EXITS Section */}
        {activeSection === 'exits' && (
          filteredExits.length > 0 ? (
            <div className="grid gap-2 sm:grid-cols-2">
              {filteredExits.map((entry) => (
                <VisitCard key={entry.id} item={entry} type="exit" />
              ))}
            </div>
          ) : (
            <EmptyState icon={UserMinus} message="No hay salidas registradas hoy" subMessage="Aparecerán aquí al registrar salidas" />
          )
        )}
      </div>
    </div>
  );
};

// Empty state component
const EmptyState = ({ icon: Icon, message, subMessage }) => (
  <div className="flex flex-col items-center justify-center h-48 text-muted-foreground bg-[#0A0A0F] rounded-xl border border-dashed border-[#1E293B]">
    <Icon className="w-12 h-12 mb-3 opacity-30" />
    <p className="text-sm font-medium">{message}</p>
    <p className="text-xs mt-1">{subMessage}</p>
  </div>
);

// READ-ONLY visit card for Visitas tab
const VisitCard = ({ item, type }) => {
  const getTypeConfig = () => {
    switch (type) {
      case 'inside':
        return { 
          bgColor: 'bg-green-500/10', 
          borderColor: 'border-green-500/30',
          badge: { bg: 'bg-green-600', text: 'DENTRO' },
          icon: Users
        };
      case 'pending':
        return { 
          bgColor: 'bg-blue-500/10', 
          borderColor: 'border-blue-500/30',
          badge: { bg: 'bg-blue-600', text: 'PENDIENTE' },
          icon: CalendarDays
        };
      case 'exit':
        return { 
          bgColor: 'bg-gray-500/10', 
          borderColor: 'border-gray-500/30',
          badge: { bg: 'bg-gray-600', text: 'SALIÓ' },
          icon: UserMinus
        };
      default:
        return { bgColor: 'bg-[#0F111A]', borderColor: 'border-[#1E293B]', badge: { bg: 'bg-gray-600', text: '?' }, icon: Users };
    }
  };

  const config = getTypeConfig();
  const Icon = config.icon;
  
  // Get visitor type badge if exists
  const visitorType = item.visitor_type;
  const visitorTypeLabels = {
    visitor: null,
    delivery: { label: 'Delivery', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
    maintenance: { label: 'Manten.', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
    technical: { label: 'Técnico', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
    cleaning: { label: 'Limpieza', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
    other: { label: 'Otro', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30' }
  };
  const typeLabel = visitorTypeLabels[visitorType];
  
  // Get authorization type badge
  const authType = item.authorization_type;
  const authTypeLabels = {
    permanent: { label: 'Permanente', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
    recurring: { label: 'Recurrente', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
    temporary: { label: 'Temporal', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
    extended: { label: 'Extendido', color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
    manual: { label: 'Manual', color: 'bg-gray-500/20 text-gray-400 border-gray-500/30' }
  };
  const authLabel = authTypeLabels[authType];

  const visitorName = item.visitor_name || item.full_name || 'Visitante';
  const residentName = item.resident_name || item.created_by_name || '';

  return (
    <div className={`p-3 rounded-xl border-2 ${config.bgColor} ${config.borderColor}`} data-testid={`visit-card-${item.id}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <div className={`w-8 h-8 rounded-lg ${config.badge.bg} flex items-center justify-center flex-shrink-0`}>
            <Icon className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-bold text-white truncate">{visitorName}</p>
            {residentName && (
              <p className="text-[10px] text-muted-foreground truncate flex items-center gap-1">
                <Home className="w-3 h-3" /> {residentName}
              </p>
            )}
          </div>
        </div>
        <Badge className={`${config.badge.bg} text-[10px] flex-shrink-0`}>
          {config.badge.text}
        </Badge>
      </div>

      {/* Badges row */}
      <div className="flex flex-wrap gap-1 mb-2">
        {typeLabel && (
          <Badge className={`${typeLabel.color} text-[9px] border`}>
            {typeLabel.label}
          </Badge>
        )}
        {authLabel && (
          <Badge className={`${authLabel.color} text-[9px] border`}>
            {authLabel.label}
          </Badge>
        )}
      </div>

      {/* Details */}
      <div className="grid grid-cols-2 gap-1 text-[11px] text-muted-foreground">
        {(item.identification_number || item.national_id) && (
          <div className="flex items-center gap-1">
            <User className="w-3 h-3" />
            <span>{item.identification_number || item.national_id}</span>
          </div>
        )}
        {item.vehicle_plate && (
          <div className="flex items-center gap-1">
            <Car className="w-3 h-3" />
            <span className="font-mono">{item.vehicle_plate}</span>
          </div>
        )}
        {item.company && (
          <div className="flex items-center gap-1 col-span-2">
            <span className="font-medium">{item.company}</span>
          </div>
        )}
        {item.destination && (
          <div className="flex items-center gap-1">
            <Home className="w-3 h-3" />
            <span className="truncate">{item.destination}</span>
          </div>
        )}
      </div>

      {/* Timestamps */}
      <div className="mt-2 pt-2 border-t border-[#1E293B]/50 text-[10px] text-muted-foreground">
        {type === 'inside' && item.entry_at && (
          <div className="flex items-center gap-1 text-green-400">
            <Clock className="w-3 h-3" />
            Entrada: {new Date(item.entry_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
          </div>
        )}
        {type === 'exit' && (
          <>
            {item.entry_at && (
              <div className="flex items-center gap-1">
                <UserPlus className="w-3 h-3" />
                Entrada: {new Date(item.entry_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
              </div>
            )}
            {item.exit_at && (
              <div className="flex items-center gap-1 text-orange-400">
                <UserMinus className="w-3 h-3" />
                Salida: {new Date(item.exit_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                {item.duration_minutes && <span className="ml-1">({item.duration_minutes} min)</span>}
              </div>
            )}
          </>
        )}
        {type === 'pending' && item.created_at && (
          <div className="flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            Creado: {new Date(item.created_at).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })}
          </div>
        )}
      </div>
    </div>
  );
};

// Keep the old VisitorCard for backwards compatibility (used elsewhere)
const VisitorCard = ({ visitor, status, onAction, isProcessing }) => {
  const isInside = status === 'inside';
  
  return (
    <div className={`p-3 rounded-xl border-2 ${isInside ? 'bg-green-500/10 border-green-500/30' : 'bg-yellow-500/10 border-yellow-500/30'}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <p className="font-bold text-white truncate">{visitor.full_name}</p>
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Home className="w-3 h-3" />
            <span className="truncate">{visitor.created_by_name || 'Residente'}</span>
          </div>
        </div>
        <Badge className={isInside ? 'bg-green-600' : 'bg-yellow-600'}>
          {isInside ? 'DENTRO' : 'ESPERADO'}
        </Badge>
      </div>

      {/* Details Grid */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs mb-3">
        {visitor.national_id && (
          <div className="flex items-center gap-1 text-muted-foreground">
            <User className="w-3 h-3" />
            <span>{visitor.national_id}</span>
          </div>
        )}
        {visitor.vehicle_plate && (
          <div className="flex items-center gap-1 text-muted-foreground">
            <Car className="w-3 h-3" />
            <span className="font-mono">{visitor.vehicle_plate}</span>
          </div>
        )}
        <div className="flex items-center gap-1 text-muted-foreground">
          <Calendar className="w-3 h-3" />
          <span>{new Date(visitor.expected_date).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })}</span>
        </div>
        {visitor.expected_time && (
          <div className="flex items-center gap-1 text-muted-foreground">
            <Clock className="w-3 h-3" />
            <span>{visitor.expected_time}</span>
          </div>
        )}
      </div>

      {/* Entry time if inside */}
      {isInside && visitor.entry_at && (
        <div className="text-xs text-green-400 mb-2">
          ✓ Entrada: {formatTime(visitor.entry_at)}
        </div>
      )}

      {/* Action Button */}
      <Button 
        className={`w-full h-12 font-bold text-base ${isInside ? 'bg-orange-600 hover:bg-orange-700' : 'bg-green-600 hover:bg-green-700'}`}
        onClick={onAction}
        disabled={isProcessing}
      >
        {isProcessing ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : isInside ? (
          <>
            <UserMinus className="w-5 h-5 mr-2" />
            REGISTRAR SALIDA
          </>
        ) : (
          <>
            <UserPlus className="w-5 h-5 mr-2" />
            REGISTRAR ENTRADA
          </>
        )}
      </Button>
    </div>
  );
};

// ============================================
// TAB 3: MANUAL ENTRY (Walk-ins)
// ============================================
const ManualEntryTab = ({ onRefresh }) => {
  const [form, setForm] = useState({
    full_name: '',
    national_id: '',
    vehicle_plate: '',
    destination: '',
    reason: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastEntry, setLastEntry] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.full_name.trim()) {
      toast.error('El nombre del visitante es requerido');
      return;
    }

    setIsSubmitting(true);
    try {
      // Use the correct endpoint: /guard/checkin
      // This creates a proper visitor_entries record that:
      // - Marks visitor as "inside"
      // - Appears in history
      // - Allows checkout later
      const result = await api.guardCheckIn({
        visitor_name: form.full_name.trim(),
        identification_number: form.national_id?.trim() || null,
        vehicle_plate: form.vehicle_plate?.trim().toUpperCase() || null,
        destination: form.destination?.trim() || 'Entrada Principal',
        notes: form.reason?.trim() || null
        // authorization_id is NOT sent for manual entries
      });

      if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
      
      toast.success(`✓ ${form.full_name} registrado como ADENTRO`);
      
      setLastEntry({
        name: form.full_name,
        time: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
      });

      setForm({ full_name: '', national_id: '', vehicle_plate: '', destination: '', reason: '' });
      
      // Refresh parent component to update visitors inside count
      if (onRefresh) onRefresh();
      
    } catch (error) {
      console.error('Error registering manual entry:', error);
      const errorMessage = error?.message || 'Error al registrar entrada';
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Success Banner */}
      {lastEntry && (
        <div className="p-3 bg-green-500/20 border-b border-green-500/30 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <span className="text-green-400 font-medium">
              {lastEntry.name} registrado a las {lastEntry.time}
            </span>
          </div>
          <Button size="sm" variant="ghost" onClick={() => setLastEntry(null)}>
            ✕
          </Button>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="flex-1 overflow-auto p-4">
        <div className="max-w-lg mx-auto space-y-4">
          <div className="text-center mb-6">
            <div className="w-16 h-16 rounded-2xl bg-primary/20 flex items-center justify-center mx-auto mb-3">
              <UserPlus className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-lg font-bold">Registro Manual</h2>
            <p className="text-sm text-muted-foreground">Visitante sin pre-registro</p>
          </div>

          {/* Name - Required */}
          <div>
            <Label className="text-sm font-medium">Nombre Completo *</Label>
            <Input
              value={form.full_name}
              onChange={(e) => setForm({...form, full_name: e.target.value})}
              placeholder="Nombre del visitante"
              className="h-12 text-base bg-[#0A0A0F] border-[#1E293B] mt-1"
              required
              autoComplete="off"
            />
          </div>

          {/* ID and Plate - Row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-sm font-medium">Cédula / ID</Label>
              <Input
                value={form.national_id}
                onChange={(e) => setForm({...form, national_id: e.target.value})}
                placeholder="Documento"
                className="h-12 text-base bg-[#0A0A0F] border-[#1E293B] mt-1"
              />
            </div>
            <div>
              <Label className="text-sm font-medium">Placa Vehículo</Label>
              <Input
                value={form.vehicle_plate}
                onChange={(e) => setForm({...form, vehicle_plate: e.target.value.toUpperCase()})}
                placeholder="ABC-123"
                className="h-12 text-base bg-[#0A0A0F] border-[#1E293B] mt-1 font-mono"
              />
            </div>
          </div>

          {/* Destination */}
          <div>
            <Label className="text-sm font-medium">Casa / Apartamento</Label>
            <Input
              value={form.destination}
              onChange={(e) => setForm({...form, destination: e.target.value})}
              placeholder="Destino del visitante"
              className="h-12 text-base bg-[#0A0A0F] border-[#1E293B] mt-1"
            />
          </div>

          {/* Reason */}
          <div>
            <Label className="text-sm font-medium">Motivo (opcional)</Label>
            <Input
              value={form.reason}
              onChange={(e) => setForm({...form, reason: e.target.value})}
              placeholder="Motivo de la visita"
              className="h-12 text-base bg-[#0A0A0F] border-[#1E293B] mt-1"
            />
          </div>

          {/* Submit */}
          <Button 
            type="submit" 
            className="w-full h-14 text-lg font-bold bg-green-600 hover:bg-green-700 mt-6"
            disabled={!form.full_name.trim() || isSubmitting}
          >
            {isSubmitting ? (
              <Loader2 className="w-6 h-6 animate-spin" />
            ) : (
              <>
                <UserPlus className="w-6 h-6 mr-2" />
                REGISTRAR ENTRADA
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
};

// ============================================
// TAB 4: MY SHIFT (HR Integration)
// ============================================
const MyShiftTab = ({ clockStatus, onClockInOut, isClocking, onClockSuccess }) => {
  const [shiftData, setShiftData] = useState(null);
  const [absences, setAbsences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [clockError, setClockError] = useState(null);

  const fetchShiftData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [shiftInfo, absenceData] = await Promise.all([
        api.getGuardMyShift(),
        api.getGuardMyAbsences()
      ]);
      setShiftData(shiftInfo);
      setAbsences(absenceData);
    } catch (err) {
      console.error('Error fetching shift data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchShiftData();
  }, []);

  // Refresh shift data after clock action
  useEffect(() => {
    if (clockStatus) {
      fetchShiftData();
    }
  }, [clockStatus?.is_clocked_in]);

  const handleClockAction = async () => {
    setClockError(null);
    try {
      const result = await onClockInOut();
      
      if (result && !result.success) {
        // Display the error message from the result
        setClockError(result.error || 'Error al registrar fichaje');
        return;
      }
      
      // Success - refresh data
      fetchShiftData();
      if (onClockSuccess) onClockSuccess();
    } catch (err) {
      // Fallback catch - should not happen but prevents crash
      setClockError(err.message || 'Error inesperado al registrar fichaje');
    }
  };

  const formatShiftTime = (isoString) => {
    if (!isoString) return '--:--';
    const date = new Date(isoString);
    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  };

  const formatShiftDate = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' });
  };

  const getStatusBadge = (status) => {
    const configs = {
      scheduled: { label: 'Programado', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
      in_progress: { label: 'En Curso', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
      completed: { label: 'Completado', color: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
      pending: { label: 'Pendiente', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
      approved: { label: 'Aprobada', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
      rejected: { label: 'Rechazada', color: 'bg-red-500/20 text-red-400 border-red-500/30' }
    };
    return configs[status] || { label: status, color: 'bg-gray-500/20 text-gray-400' };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center">
        <p className="text-red-400">{error}</p>
        <Button onClick={fetchShiftData} variant="outline" className="mt-4">
          Reintentar
        </Button>
      </div>
    );
  }

  const { current_shift, next_shift, has_guard_record, can_clock_in, clock_in_message } = shiftData || {};
  const isClockedIn = clockStatus?.is_clocked_in || false;
  
  // Determine if clock in is allowed
  const canClockIn = has_guard_record && (current_shift || can_clock_in);
  const canClockOut = isClockedIn;
  
  // Determine button state and message
  const getClockButtonState = () => {
    if (!has_guard_record) {
      return { disabled: true, message: 'No tienes registro como empleado. Contacta a tu supervisor.' };
    }
    
    if (isClockedIn) {
      return { disabled: false, message: null }; // Can always clock out if clocked in
    }
    
    if (!current_shift && !can_clock_in) {
      if (next_shift) {
        const nextStart = new Date(next_shift.start_time);
        const now = new Date();
        const diffMinutes = Math.round((nextStart - now) / (1000 * 60));
        if (diffMinutes <= 15 && diffMinutes > 0) {
          return { disabled: false, message: `Tu turno comienza en ${diffMinutes} minutos.` };
        }
        return { disabled: true, message: `Próximo turno en ${diffMinutes > 60 ? Math.round(diffMinutes/60) + ' horas' : diffMinutes + ' minutos'}. Puedes fichar 15 min antes.` };
      }
      return { disabled: true, message: 'No tienes un turno asignado para hoy.' };
    }
    
    return { disabled: false, message: null };
  };

  const buttonState = getClockButtonState();

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        {/* Clock In/Out Section */}
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold flex items-center gap-2">
                <Clock className="w-5 h-5 text-primary" />
                Control de Asistencia
              </h3>
              {clockStatus?.last_time && (
                <span className="text-xs text-muted-foreground">
                  Último: {formatShiftTime(clockStatus.last_time)}
                </span>
              )}
            </div>

            <Button
              onClick={handleClockAction}
              disabled={isClocking || (isClockedIn ? false : buttonState.disabled)}
              className={`w-full h-16 text-lg font-bold gap-3 ${
                isClockedIn 
                  ? 'bg-orange-600 hover:bg-orange-700' 
                  : buttonState.disabled
                    ? 'bg-gray-600 hover:bg-gray-600 cursor-not-allowed opacity-50'
                    : 'bg-green-600 hover:bg-green-700'
              }`}
              data-testid="clock-btn"
            >
              {isClocking ? (
                <Loader2 className="w-6 h-6 animate-spin" />
              ) : isClockedIn ? (
                <>
                  <StopCircle className="w-6 h-6" />
                  REGISTRAR SALIDA
                </>
              ) : (
                <>
                  <PlayCircle className="w-6 h-6" />
                  REGISTRAR ENTRADA
                </>
              )}
            </Button>

            {/* Status/Error Messages */}
            {clockError && (
              <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/30">
                <p className="text-sm text-red-400 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                  {clockError}
                </p>
              </div>
            )}

            {buttonState.message && !clockError && (
              <p className="text-xs text-yellow-400 mt-3 text-center">
                {buttonState.message}
              </p>
            )}

            {/* Success indicator when clocked in */}
            {isClockedIn && current_shift && (
              <div className="mt-3 p-2 rounded-lg bg-green-500/10 border border-green-500/30">
                <p className="text-xs text-green-400 text-center">
                  ✓ Entrada registrada - Turno en curso
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Current Shift */}
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <h3 className="font-bold flex items-center gap-2 mb-4">
              <Briefcase className="w-5 h-5 text-primary" />
              Turno Actual
            </h3>

            {current_shift ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Estado</span>
                  <Badge className={getStatusBadge(current_shift.status).color}>
                    {getStatusBadge(current_shift.status).label}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Fecha</span>
                  <span className="text-sm font-medium">{formatShiftDate(current_shift.start_time)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Horario</span>
                  <span className="text-sm font-medium">
                    {formatShiftTime(current_shift.start_time)} - {formatShiftTime(current_shift.end_time)}
                  </span>
                </div>
                {current_shift.location && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Ubicación</span>
                    <span className="text-sm font-medium">{current_shift.location}</span>
                  </div>
                )}
                {current_shift.clock_in_time && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Fichaste</span>
                    <span className="text-sm font-medium text-green-400">{formatShiftTime(current_shift.clock_in_time)}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-6">
                <CalendarX className="w-10 h-10 text-muted-foreground/30 mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">No hay turno activo</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Next Shift */}
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <h3 className="font-bold flex items-center gap-2 mb-4">
              <CalendarClock className="w-5 h-5 text-blue-400" />
              Próximo Turno
            </h3>

            {next_shift ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Fecha</span>
                  <span className="text-sm font-medium">{formatShiftDate(next_shift.start_time)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Horario</span>
                  <span className="text-sm font-medium">
                    {formatShiftTime(next_shift.start_time)} - {formatShiftTime(next_shift.end_time)}
                  </span>
                </div>
                {next_shift.location && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Ubicación</span>
                    <span className="text-sm font-medium">{next_shift.location}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-muted-foreground">No hay turnos programados</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Absences */}
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <h3 className="font-bold flex items-center gap-2 mb-4">
              <Calendar className="w-5 h-5 text-yellow-400" />
              Mis Ausencias
            </h3>

            {absences.length > 0 ? (
              <div className="space-y-2">
                {absences.slice(0, 5).map((absence) => (
                  <div 
                    key={absence.id} 
                    className="p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B]"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{absence.absence_type}</span>
                      <Badge className={getStatusBadge(absence.status).color}>
                        {getStatusBadge(absence.status).label}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{absence.start_date} - {absence.end_date}</span>
                      {absence.reason && (
                        <span className="truncate max-w-[120px]">{absence.reason}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-sm text-muted-foreground">No tienes solicitudes de ausencia</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  );
};

// ============================================
// TAB 5: ABSENCES (Request & View)
// ============================================
const AbsencesTab = () => {
  const [absences, setAbsences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    type: 'vacaciones',
    start_date: '',
    end_date: '',
    reason: '',
    notes: ''
  });
  const [formError, setFormError] = useState(null);

  const fetchAbsences = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getGuardMyAbsences();
      setAbsences(data);
    } catch (error) {
      console.error('Error fetching absences:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAbsences();
  }, [fetchAbsences]);

  const validateForm = () => {
    if (!formData.start_date) {
      setFormError('La fecha de inicio es requerida');
      return false;
    }
    if (!formData.end_date) {
      setFormError('La fecha de fin es requerida');
      return false;
    }
    if (new Date(formData.end_date) < new Date(formData.start_date)) {
      setFormError('La fecha de fin debe ser igual o posterior a la fecha de inicio');
      return false;
    }
    if (!formData.reason.trim()) {
      setFormError('El motivo es requerido');
      return false;
    }
    setFormError(null);
    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;
    
    setIsSubmitting(true);
    try {
      await api.createAbsence({
        type: formData.type,
        start_date: formData.start_date,
        end_date: formData.end_date,
        reason: formData.reason,
        notes: formData.notes || ''
      });
      
      toast.success('Solicitud de ausencia enviada correctamente');
      setShowCreateDialog(false);
      setFormData({
        type: 'vacaciones',
        start_date: '',
        end_date: '',
        reason: '',
        notes: ''
      });
      fetchAbsences();
    } catch (error) {
      toast.error(error.message || 'Error al enviar solicitud');
    } finally {
      setIsSubmitting(false);
    }
  };

  const typeLabels = {
    vacaciones: { label: 'Vacaciones', icon: '🏖️', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
    permiso_medico: { label: 'Permiso Médico', icon: '🏥', color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
    personal: { label: 'Personal', icon: '👤', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
    otro: { label: 'Otro', icon: '📋', color: 'bg-gray-500/20 text-gray-400 border-gray-500/30' }
  };

  const statusLabels = {
    pending: { label: 'Pendiente', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
    approved: { label: 'Aprobada', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
    rejected: { label: 'Rechazada', color: 'bg-red-500/20 text-red-400 border-red-500/30' }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-3 bg-[#0A0A0F] border-b border-[#1E293B]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CalendarOff className="w-5 h-5 text-cyan-400" />
            <span className="font-semibold text-white">Mis Ausencias</span>
          </div>
          <Button 
            size="sm" 
            className="bg-cyan-600 hover:bg-cyan-700"
            onClick={() => setShowCreateDialog(true)}
            data-testid="new-absence-request-btn"
          >
            <CalendarPlus className="w-4 h-4 mr-1" />
            Solicitar
          </Button>
        </div>
      </div>

      {/* Absences List */}
      <ScrollArea className="flex-1 p-3">
        {absences.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
            <CalendarOff className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-lg font-medium">Sin solicitudes</p>
            <p className="text-sm text-center">No tienes solicitudes de ausencia registradas</p>
            <Button 
              className="mt-4 bg-cyan-600 hover:bg-cyan-700"
              onClick={() => setShowCreateDialog(true)}
            >
              <CalendarPlus className="w-4 h-4 mr-2" />
              Nueva Solicitud
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {absences.map((absence) => {
              const typeConfig = typeLabels[absence.type] || typeLabels.otro;
              const statusConfig = statusLabels[absence.status] || statusLabels.pending;
              
              return (
                <div 
                  key={absence.id} 
                  className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]"
                  data-testid={`absence-${absence.id}`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{typeConfig.icon}</span>
                      <Badge variant="outline" className={typeConfig.color}>
                        {typeConfig.label}
                      </Badge>
                    </div>
                    <Badge variant="outline" className={statusConfig.color}>
                      {statusConfig.label}
                    </Badge>
                  </div>
                  
                  <p className="text-white font-medium mb-2">{absence.reason}</p>
                  
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      <span>{formatDate(absence.start_date)}</span>
                    </div>
                    <span>→</span>
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      <span>{formatDate(absence.end_date)}</span>
                    </div>
                  </div>
                  
                  {absence.notes && (
                    <p className="text-xs text-muted-foreground mt-2 pt-2 border-t border-[#1E293B]">
                      📝 {absence.notes}
                    </p>
                  )}
                  
                  {absence.status === 'rejected' && absence.admin_notes && (
                    <div className="mt-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20">
                      <p className="text-xs text-red-400">
                        <strong>Motivo de rechazo:</strong> {absence.admin_notes}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </ScrollArea>

      {/* Create Absence Request Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="bg-[#0A0A0F] border-[#1E293B] max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CalendarPlus className="w-5 h-5 text-cyan-400" />
              Nueva Solicitud de Ausencia
            </DialogTitle>
            <DialogDescription>
              Completa el formulario para solicitar una ausencia
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {formError && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {formError}
              </div>
            )}

            {/* Absence Type */}
            <div>
              <Label className="text-sm text-muted-foreground">Tipo de Ausencia *</Label>
              <Select 
                value={formData.type} 
                onValueChange={(v) => setFormData({...formData, type: v})}
              >
                <SelectTrigger className="bg-[#0F111A] border-[#1E293B] mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="vacaciones">🏖️ Vacaciones</SelectItem>
                  <SelectItem value="permiso_medico">🏥 Permiso Médico</SelectItem>
                  <SelectItem value="personal">👤 Personal</SelectItem>
                  <SelectItem value="otro">📋 Otro</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Date Range */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-sm text-muted-foreground">Fecha Inicio *</Label>
                <Input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({...formData, start_date: e.target.value})}
                  className="bg-[#0F111A] border-[#1E293B] mt-1"
                  min={new Date().toISOString().split('T')[0]}
                />
              </div>
              <div>
                <Label className="text-sm text-muted-foreground">Fecha Fin *</Label>
                <Input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => setFormData({...formData, end_date: e.target.value})}
                  className="bg-[#0F111A] border-[#1E293B] mt-1"
                  min={formData.start_date || new Date().toISOString().split('T')[0]}
                />
              </div>
            </div>

            {/* Reason */}
            <div>
              <Label className="text-sm text-muted-foreground">Motivo *</Label>
              <Input
                value={formData.reason}
                onChange={(e) => setFormData({...formData, reason: e.target.value})}
                placeholder="Ej: Cita médica, vacaciones familiares..."
                className="bg-[#0F111A] border-[#1E293B] mt-1"
              />
            </div>

            {/* Additional Notes */}
            <div>
              <Label className="text-sm text-muted-foreground">Notas adicionales (opcional)</Label>
              <Textarea
                value={formData.notes}
                onChange={(e) => setFormData({...formData, notes: e.target.value})}
                placeholder="Información adicional..."
                className="bg-[#0F111A] border-[#1E293B] mt-1 min-h-[80px]"
              />
            </div>
          </div>

          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setShowCreateDialog(false)}
              disabled={isSubmitting}
            >
              Cancelar
            </Button>
            <Button 
              className="bg-cyan-600 hover:bg-cyan-700"
              onClick={handleSubmit}
              disabled={isSubmitting}
              data-testid="submit-absence-btn"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <CalendarPlus className="w-4 h-4 mr-2" />
              )}
              Enviar Solicitud
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============================================
// TAB 6: HISTORY (Read-only)
// ============================================
const HistoryTab = () => {
  const [filter, setFilter] = useState('today');
  const [guardHistory, setGuardHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        // Use proper guard history endpoint - already scoped by condominium_id
        const history = await api.getGuardHistory();
        
        // Filter by date range
        const now = new Date();
        const filterDate = filter === 'today' 
          ? new Date(now.getFullYear(), now.getMonth(), now.getDate())
          : new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

        const filteredHistory = history.filter(h => new Date(h.timestamp) >= filterDate);
        setGuardHistory(filteredHistory);
      } catch (error) {
        console.error('Error fetching guard history:', error);
        setGuardHistory([]);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [filter]);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>;
  }

  // Categorize history by type
  const alertHistory = guardHistory.filter(h => h.type === 'alert_resolved');
  const visitEntryHistory = guardHistory.filter(h => h.type === 'visit_entry');
  const visitExitHistory = guardHistory.filter(h => h.type === 'visit_exit');
  const clockHistory = guardHistory.filter(h => h.type === 'clock_in' || h.type === 'clock_out');
  const shiftHistory = guardHistory.filter(h => h.type === 'shift_completed');

  return (
    <ScrollArea className="h-full">
      <div className="p-3 space-y-4">
        {/* Filter */}
        <div className="flex items-center gap-3 pb-3 border-b border-[#1E293B]">
          <History className="w-5 h-5 text-muted-foreground" />
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-40 bg-[#0A0A0F] border-[#1E293B]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#0F111A] border-[#1E293B]">
              <SelectItem value="today">Hoy</SelectItem>
              <SelectItem value="week">Últimos 7 días</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-xs text-muted-foreground ml-auto">
            {guardHistory.length} eventos
          </span>
        </div>

        {/* Visitor Entries (Check-ins) */}
        {visitEntryHistory.length > 0 && (
          <div>
            <h3 className="text-xs font-bold text-green-400 uppercase tracking-wider mb-2 flex items-center gap-2">
              <UserPlus className="w-4 h-4" />
              Entradas Registradas ({visitEntryHistory.length})
            </h3>
            <div className="space-y-2">
              {visitEntryHistory.map((entry) => (
                <div key={entry.id} className="p-3 rounded-lg bg-[#0A0A0F] border border-green-500/30 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center">
                    <UserPlus className="w-4 h-4 text-green-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{entry.visitor_name}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{entry.destination || 'Sin destino'}</span>
                      {entry.vehicle_plate && <span className="font-mono">🚗 {entry.vehicle_plate}</span>}
                    </div>
                  </div>
                  <div className="text-right text-xs">
                    <p className="text-green-400">{formatTime(entry.timestamp)}</p>
                    <Badge variant="outline" className={entry.is_authorized ? 'border-green-500/30 text-green-400' : 'border-yellow-500/30 text-yellow-400'}>
                      {entry.is_authorized ? '✓ Auth' : 'Manual'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Visitor Exits (Check-outs) */}
        {visitExitHistory.length > 0 && (
          <div>
            <h3 className="text-xs font-bold text-orange-400 uppercase tracking-wider mb-2 flex items-center gap-2">
              <UserMinus className="w-4 h-4" />
              Salidas Registradas ({visitExitHistory.length})
            </h3>
            <div className="space-y-2">
              {visitExitHistory.map((exit) => (
                <div key={exit.id} className="p-3 rounded-lg bg-[#0A0A0F] border border-orange-500/30 flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-orange-500/20 flex items-center justify-center">
                    <UserMinus className="w-4 h-4 text-orange-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{exit.visitor_name}</p>
                    <p className="text-xs text-muted-foreground">{exit.destination || 'Sin destino'}</p>
                  </div>
                  <div className="text-right text-xs text-orange-400">
                    <p>{formatTime(exit.timestamp)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Clock Events */}
        {clockHistory.length > 0 && (
          <div>
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Fichajes ({clockHistory.length})
            </h3>
            <div className="space-y-2">
              {clockHistory.map((event) => (
                <div key={event.id} className="p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B] flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    event.type === 'clock_in' ? 'bg-green-500/20' : 'bg-orange-500/20'
                  }`}>
                    {event.type === 'clock_in' ? (
                      <PlayCircle className="w-4 h-4 text-green-400" />
                    ) : (
                      <StopCircle className="w-4 h-4 text-orange-400" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">
                      {event.type === 'clock_in' ? 'Entrada' : 'Salida'}
                    </p>
                    <p className="text-xs text-muted-foreground">{event.date}</p>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <p>{formatTime(event.timestamp)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Completed Shifts */}
        {shiftHistory.length > 0 && (
          <div>
            <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-2">
              <Briefcase className="w-4 h-4" />
              Turnos Completados ({shiftHistory.length})
            </h3>
            <div className="space-y-2">
              {shiftHistory.map((shift) => (
                <div key={shift.id} className="p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B] flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                    <CheckCircle className="w-4 h-4 text-blue-400" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{shift.location || 'Turno'}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatTime(shift.shift_start)} - {formatTime(shift.shift_end)}
                    </p>
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <p>{new Date(shift.timestamp).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Alerts History */}
        {alertHistory.length > 0 && (
          <div>
            <h3 className="text-xs font-bold text-red-400 uppercase tracking-wider mb-2 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              Alertas Atendidas ({alertHistory.length})
            </h3>
            <div className="space-y-2">
              {alertHistory.map((alert) => {
                const config = PANIC_CONFIG[alert.alert_type] || PANIC_CONFIG.emergencia_general;
                return (
                  <div key={alert.id} className="p-3 rounded-lg bg-[#0A0A0F] border border-red-500/30 flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg ${config.bg} flex items-center justify-center`}>
                      <config.icon className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{alert.user_name || 'Residente'}</p>
                      <p className="text-xs text-muted-foreground">{alert.location || 'Sin ubicación'}</p>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      <p>{formatTime(alert.timestamp)}</p>
                      <Badge variant="outline" className="border-green-500/30 text-green-400 text-[10px]">
                        Resuelta
                      </Badge>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {guardHistory.length === 0 && (
          <div className="text-center py-12">
            <History className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
            <p className="text-muted-foreground">No hay actividad registrada</p>
            <p className="text-xs text-muted-foreground mt-2">Los check-ins, alertas y fichajes aparecerán aquí</p>
          </div>
        )}
      </div>
    </ScrollArea>
  );
};

// ============================================
// MAIN COMPONENT
// ============================================

// Mobile Bottom Nav Configuration for Guard
const GUARD_MOBILE_NAV = [
  { id: 'alerts', label: 'Alertas', icon: AlertTriangle },
  { id: 'checkin', label: 'Check-In', icon: ScanLine },
  { id: 'visits', label: 'Visitas', icon: Users },
  { id: 'panic', label: 'Pánico', icon: Siren, bgColor: 'bg-red-600', glowColor: 'shadow-red-500/50' },
  { id: 'profile', label: 'Perfil', icon: User },
];

const GuardUI = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, logout } = useAuth();
  const isMobile = useIsMobile();
  const [activeTab, setActiveTab] = useState('alerts');
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [resolvingId, setResolvingId] = useState(null);
  const [showPushBanner, setShowPushBanner] = useState(true);
  
  // Clock In/Out state
  const [clockStatus, setClockStatus] = useState(null);
  const [isClocking, setIsClocking] = useState(false);
  
  // Mobile panic modal state
  const [showPanicModal, setShowPanicModal] = useState(false);
  
  // Highlighted alert from push notification
  const [highlightedAlertId, setHighlightedAlertId] = useState(null);

  // Handle URL parameters (alert from push notification, tab from redirect)
  useEffect(() => {
    const alertId = searchParams.get('alert');
    const tabParam = searchParams.get('tab');
    
    if (alertId) {
      // Stop sound when navigating to alerts via URL param
      AlertSoundManager.stop();
      setActiveTab('alerts');
      setHighlightedAlertId(alertId);
      // Clear highlight after animation
      setTimeout(() => setHighlightedAlertId(null), 5000);
      // Clean URL
      navigate('/guard', { replace: true });
    }
    
    // Handle tab parameter (e.g., from profile redirect)
    if (tabParam) {
      const validTabs = ['alerts', 'checkin', 'history', 'profile'];
      if (validTabs.includes(tabParam)) {
        // Stop sound if navigating to alerts
        if (tabParam === 'alerts') {
          AlertSoundManager.stop();
        }
        setActiveTab(tabParam);
      }
      // Clean URL
      navigate('/guard', { replace: true });
    }
  }, [searchParams, navigate]);

  // Listen for messages from service worker (push notification clicks)
  useEffect(() => {
    const handleServiceWorkerMessage = (event) => {
      if (event.data?.type === 'PANIC_ALERT_CLICK') {
        // Stop sound immediately when clicking push notification
        AlertSoundManager.stop();
        const data = event.data.data;
        setActiveTab('alerts');
        if (data.event_id) {
          setHighlightedAlertId(data.event_id);
          setTimeout(() => setHighlightedAlertId(null), 5000);
        }
      }
    };

    navigator.serviceWorker?.addEventListener('message', handleServiceWorkerMessage);
    return () => {
      navigator.serviceWorker?.removeEventListener('message', handleServiceWorkerMessage);
    };
  }, []);

  // Auto-subscribe to push notifications for guards
  useEffect(() => {
    const subscribeGuardToPush = async () => {
      try {
        const { PushNotificationManager } = await import('../utils/PushNotificationManager');
        
        if (!PushNotificationManager.isSupported()) {
          console.log('[Guard] Push notifications not supported');
          return;
        }
        
        // Request permission
        const permission = await pushManager.requestPermission();
        if (permission !== 'granted') {
          console.log('[Guard] Push permission not granted:', permission);
          return;
        }
        
        // Get VAPID key
        const vapidResponse = await api.getVapidPublicKey();
        if (!vapidResponse?.publicKey) {
          console.log('[Guard] No VAPID key from server');
          return;
        }
        
        // Subscribe
        const subscriptionData = await pushManager.subscribe(vapidResponse.publicKey);
        await api.subscribeToPush(subscriptionData);
        console.log('[Guard] Successfully subscribed to push notifications');
        
      } catch (error) {
        console.error('[Guard] Error subscribing to push:', error);
      }
    };
    
    // Delay to not interfere with initial load
    const timer = setTimeout(subscribeGuardToPush, 2000);
    return () => clearTimeout(timer);
  }, []);

  // Handler for tab changes - stops panic sound when navigating to alerts tab
  const handleTabChange = useCallback((newTab) => {
    // Stop panic sound when navigating to alerts tab
    if (newTab === 'alerts') {
      AlertSoundManager.stop();
    }
    setActiveTab(newTab);
  }, []);

  // Handle mobile nav tab changes
  const handleMobileTabChange = (tabId) => {
    if (tabId === 'panic') {
      setShowPanicModal(true);
    } else {
      // Use the handler that stops sound
      handleTabChange(tabId);
    }
  };

  const fetchAlerts = useCallback(async () => {
    try {
      const events = await api.getPanicEvents();
      setAlerts(events);
    } catch (error) {
      console.error('Error fetching alerts:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  const fetchClockStatus = useCallback(async () => {
    try {
      const status = await api.getClockStatus();
      setClockStatus(status);
    } catch (error) {
      console.error('Error fetching clock status:', error);
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    fetchClockStatus();
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, [fetchAlerts, fetchClockStatus]);

  // Stop panic sound on component unmount (cleanup)
  useEffect(() => {
    return () => {
      AlertSoundManager.stop();
    };
  }, []);

  // Stop sound when guard views alerts tab (mounting)
  useEffect(() => {
    if (activeTab === 'alerts') {
      AlertSoundManager.stop();
    }
  }, [activeTab]);

  // Vibrate on new active alerts
  useEffect(() => {
    const activeCount = alerts.filter(a => a.status === 'active').length;
    if (activeCount > 0 && navigator.vibrate) {
      navigator.vibrate([200, 100, 200]);
    }
  }, [alerts]);

  const handleClockInOut = async () => {
    setIsClocking(true);
    try {
      const type = clockStatus?.is_clocked_in ? 'OUT' : 'IN';
      await api.clockInOut(type);
      if (navigator.vibrate) navigator.vibrate(100);
      fetchClockStatus();
      return { success: true };
    } catch (error) {
      // Handle specific HTTP status codes
      if (error.status === 401) {
        // Force logout on unauthorized
        sessionStorage.clear();
        window.location.href = '/login';
        return { success: false, error: 'Sesión expirada' };
      }
      
      // Return error for UI display - DO NOT re-throw
      return { 
        success: false, 
        error: error.message || 'Error al registrar fichaje',
        status: error.status 
      };
    } finally {
      setIsClocking(false);
    }
  };

  const handleResolve = async (alertId, notes = '') => {
    setResolvingId(alertId);
    try {
      await api.resolvePanic(alertId, notes);
      if (navigator.vibrate) navigator.vibrate(100);
      fetchAlerts();
    } catch (error) {
      console.error('Error resolving alert:', error);
      throw error; // Re-throw to let the modal handle it
    } finally {
      setResolvingId(null);
    }
  };

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchAlerts();
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const activeAlertCount = alerts.filter(a => a.status === 'active').length;
  const isClockedIn = clockStatus?.is_clocked_in || false;

  // Update mobile nav items with alert count
  const mobileNavItems = GUARD_MOBILE_NAV.map(item => {
    if (item.id === 'alerts' && activeAlertCount > 0) {
      return { ...item, badge: activeAlertCount };
    }
    return item;
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 text-primary mx-auto mb-4 animate-pulse" />
          <p className="text-muted-foreground">Cargando panel...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`h-screen bg-[#05050A] flex flex-col overflow-hidden ${isMobile ? 'pb-20' : ''}`}>
      {/* Header with Clock Status */}
      <header className="flex-shrink-0 p-2 flex items-center justify-between border-b border-[#1E293B] bg-[#0A0A0F]">
        <div className="flex items-center gap-2">
          {/* Clickable Avatar - opens embedded profile tab (no separate page) */}
          <div 
            className="cursor-pointer group"
            onClick={() => setActiveTab('profile')}
            data-testid="guard-profile-avatar"
          >
            <Avatar className={`w-9 h-9 border-2 ${isClockedIn ? 'border-green-500' : 'border-gray-500'} transition-transform group-hover:scale-110`}>
              <AvatarImage src={user?.profile_photo} />
              <AvatarFallback className={`${isClockedIn ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'} text-sm font-bold`}>
                {user?.full_name?.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
          </div>
          <div 
            className="cursor-pointer hover:opacity-80"
            onClick={() => setActiveTab('profile')}
          >
            <h1 className="text-xs font-bold tracking-wide">GENTURIX</h1>
            <p className="text-[10px] text-muted-foreground truncate max-w-[100px]">{user?.full_name}</p>
          </div>
        </div>
        
        {/* Clock In/Out Button - always visible */}
        <div className="flex items-center gap-2">
          <Button 
            size="sm"
            variant={isClockedIn ? "destructive" : "default"}
            className={`h-10 px-4 text-sm font-bold ${isClockedIn ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}`}
            onClick={handleClockInOut}
            disabled={isClocking}
            data-testid="clock-btn-header"
          >
            {isClocking ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Clock className="w-4 h-4 mr-1" />
                {isClockedIn ? 'SALIDA' : 'ENTRADA'}
              </>
            )}
          </Button>
          
          {/* Profile quick access - uses embedded profile tab (no separate page) */}
          {!isMobile && (
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-8 w-8" 
              onClick={() => setActiveTab('profile')}
              data-testid="guard-profile-btn"
              title="Mi Perfil"
            >
              <User className="w-4 h-4" />
            </Button>
          )}
          
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleLogout} data-testid="guard-logout-btn">
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </header>

      {/* Clock Status Banner */}
      {clockStatus && (
        <div className={`px-3 py-1.5 ${isClockedIn ? 'bg-green-500/10' : 'bg-amber-500/10'} border-b border-[#1E293B]`}>
          <div className="flex items-center justify-between text-xs">
            <span className={isClockedIn ? 'text-green-400' : 'text-amber-400'}>
              {isClockedIn ? '✓ En turno' : '○ Sin fichar'}
            </span>
            {clockStatus.last_time && (
              <span className="text-muted-foreground">
                Último: {new Date(clockStatus.last_time).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Push Notification Permission Banner */}
      {showPushBanner && (
        <div className="px-3 pt-3">
          <PushNotificationBanner onClose={() => setShowPushBanner(false)} />
        </div>
      )}

      {/* Tabs - Hidden on mobile, visible on desktop */}
      <Tabs value={activeTab} onValueChange={handleTabChange} className="flex-1 flex flex-col min-h-0">
        {/* Desktop Tabs - hidden on mobile */}
        {!isMobile && (
          <TabsList className="flex-shrink-0 grid grid-cols-8 bg-[#0A0A0F] border-b border-[#1E293B] rounded-none h-14 p-0">
            <TabsTrigger 
              value="alerts" 
              className="h-full rounded-none data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-red-500 flex flex-col gap-0.5"
              data-testid="tab-alerts"
            >
              <div className="relative">
                <AlertTriangle className="w-5 h-5" />
                {activeAlertCount > 0 && (
                  <span className="absolute -top-1 -right-2 w-4 h-4 rounded-full bg-red-500 text-[10px] font-bold flex items-center justify-center animate-pulse">
                    {activeAlertCount}
                  </span>
                )}
              </div>
              <span className="text-[10px]">Alertas</span>
            </TabsTrigger>
            
            <TabsTrigger 
              value="checkin" 
              className="h-full rounded-none data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-green-500 flex flex-col gap-0.5"
              data-testid="tab-checkin"
            >
              <ScanLine className="w-5 h-5" />
              <span className="text-[10px]">Check-In</span>
            </TabsTrigger>
            
            <TabsTrigger 
              value="myshift" 
              className="h-full rounded-none data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-blue-500 flex flex-col gap-0.5"
              data-testid="tab-myshift"
            >
              <Briefcase className="w-5 h-5" />
              <span className="text-[10px]">Mi Turno</span>
            </TabsTrigger>
            
            <TabsTrigger 
              value="absences" 
              className="h-full rounded-none data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-cyan-500 flex flex-col gap-0.5"
              data-testid="tab-absences"
            >
              <CalendarOff className="w-5 h-5" />
              <span className="text-[10px]">Ausencias</span>
            </TabsTrigger>
            
            <TabsTrigger 
              value="visits" 
              className="h-full rounded-none data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary flex flex-col gap-0.5"
              data-testid="tab-visits"
            >
              <Users className="w-5 h-5" />
              <span className="text-[10px]">Visitas</span>
            </TabsTrigger>
            
            <TabsTrigger 
              value="history" 
              className="h-full rounded-none data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary flex flex-col gap-0.5"
              data-testid="tab-history"
            >
              <History className="w-5 h-5" />
              <span className="text-[10px]">Historial</span>
            </TabsTrigger>
            
            <TabsTrigger 
              value="directory" 
              className="h-full rounded-none data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-cyan-500 flex flex-col gap-0.5"
              data-testid="tab-directory"
            >
              <UsersIcon className="w-5 h-5" />
              <span className="text-[10px]">Personas</span>
            </TabsTrigger>
            
            <TabsTrigger 
              value="profile" 
              className="h-full rounded-none data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-amber-500 flex flex-col gap-0.5"
              data-testid="tab-profile"
            >
              <User className="w-5 h-5" />
              <span className="text-[10px]">Perfil</span>
            </TabsTrigger>
          </TabsList>
        )}

        {/* Tab Content */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <TabsContent value="alerts" className="h-full m-0 data-[state=inactive]:hidden">
            <AlertsTab 
              alerts={alerts}
              onResolve={handleResolve}
              resolvingId={resolvingId}
              onRefresh={handleRefresh}
              isRefreshing={isRefreshing}
              highlightedAlertId={highlightedAlertId}
            />
          </TabsContent>

          <TabsContent value="checkin" className="h-full m-0 data-[state=inactive]:hidden">
            <VisitorCheckInGuard />
          </TabsContent>

          <TabsContent value="visits" className="h-full m-0 data-[state=inactive]:hidden">
            <VisitsTab />
          </TabsContent>

          <TabsContent value="myshift" className="h-full m-0 data-[state=inactive]:hidden">
            <MyShiftTab 
              clockStatus={clockStatus}
              onClockInOut={handleClockInOut}
              isClocking={isClocking}
            />
          </TabsContent>

          <TabsContent value="absences" className="h-full m-0 data-[state=inactive]:hidden">
            <AbsencesTab />
          </TabsContent>

          <TabsContent value="history" className="h-full m-0 data-[state=inactive]:hidden">
            <GuardHistoryVisual />
          </TabsContent>
          
          <TabsContent value="directory" className="h-full m-0 data-[state=inactive]:hidden">
            <ProfileDirectory embedded={true} maxHeight="100%" />
          </TabsContent>
          
          <TabsContent value="profile" className="h-full m-0 data-[state=inactive]:hidden">
            <EmbeddedProfile onBack={() => handleTabChange('alerts')} />
          </TabsContent>
        </div>
      </Tabs>

      {/* Mobile Panic Modal */}
      <Dialog open={showPanicModal} onOpenChange={setShowPanicModal}>
        <DialogContent className="bg-[#0A0A0F] border-[#1E293B] max-w-md p-0">
          <DialogHeader className="p-4 border-b border-[#1E293B]">
            <DialogTitle className="flex items-center gap-2 text-red-400">
              <Siren className="w-6 h-6" />
              Panel de Pánico
            </DialogTitle>
            <DialogDescription>
              Activar alerta de emergencia
            </DialogDescription>
          </DialogHeader>
          <div className="p-4 space-y-4">
            <p className="text-sm text-muted-foreground text-center">
              Solo para uso de guardias en situaciones de emergencia real.
            </p>
            <div className="grid gap-3">
              <Button 
                className="h-16 bg-red-600 hover:bg-red-700 text-lg font-bold"
                onClick={() => {
                  setShowPanicModal(false);
                  // Here you would trigger the actual panic
                }}
              >
                <Heart className="w-6 h-6 mr-2" />
                EMERGENCIA MÉDICA
              </Button>
              <Button 
                className="h-16 bg-amber-500 hover:bg-amber-600 text-lg font-bold text-black"
                onClick={() => setShowPanicModal(false)}
              >
                <Eye className="w-6 h-6 mr-2" />
                ACTIVIDAD SOSPECHOSA
              </Button>
              <Button 
                className="h-16 bg-orange-500 hover:bg-orange-600 text-lg font-bold"
                onClick={() => setShowPanicModal(false)}
              >
                <AlertTriangle className="w-6 h-6 mr-2" />
                EMERGENCIA GENERAL
              </Button>
            </div>
          </div>
          <DialogFooter className="p-4 border-t border-[#1E293B]">
            <Button variant="outline" className="w-full" onClick={() => setShowPanicModal(false)}>
              Cancelar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Emergency Footer - Hidden on mobile (use bottom nav instead) */}
      {!isMobile && (
        <footer className="flex-shrink-0 p-2 bg-[#0A0A0F] border-t border-[#1E293B]">
          <a 
            href="tel:911" 
            className="flex items-center justify-center gap-2 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 active:bg-red-500/20"
          >
            <Phone className="w-5 h-5" />
            <span className="font-bold">LLAMAR 911</span>
          </a>
        </footer>
      )}

      {/* Mobile Bottom Navigation */}
      {isMobile && (
        <MobileBottomNav 
          items={mobileNavItems}
          activeTab={activeTab}
          onTabChange={handleMobileTabChange}
          centerIndex={2}
        />
      )}
      
      {/* Push Permission Banner */}
      <PushPermissionBanner onSubscribed={() => console.log('Guard push enabled!')} />
    </div>
  );
};

export default GuardUI;
