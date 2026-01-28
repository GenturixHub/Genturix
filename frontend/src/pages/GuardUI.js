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
 * 2. VISITAS - Pre-registered visitors
 * 3. REGISTRO - Manual entry for walk-ins
 * 4. HISTORIAL - Read-only past records
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
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
import api from '../services/api';
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
  User,
  Home,
  FileText,
  ChevronRight,
  ExternalLink
} from 'lucide-react';

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
// TAB 1: ALERTS
// ============================================
const AlertsTab = ({ alerts, onResolve, resolvingId, onRefresh, isRefreshing }) => {
  const activeAlerts = alerts.filter(a => a.status === 'active');
  const recentResolved = alerts.filter(a => a.status === 'resolved').slice(0, 5);

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
                  onResolve={onResolve}
                  isResolving={resolvingId === alert.id}
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
                <AlertCard key={alert.id} alert={alert} resolved />
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
    </div>
  );
};

const AlertCard = ({ alert, onResolve, isResolving, resolved }) => {
  const config = PANIC_CONFIG[alert.panic_type] || PANIC_CONFIG.emergencia_general;
  const IconComponent = config.icon;
  const hasLocation = alert.latitude && alert.longitude;

  return (
    <div 
      className={`p-3 rounded-xl border-2 ${resolved ? 'bg-[#0F111A] border-[#1E293B] opacity-60' : `${config.bgLight} ${config.border}`}`}
      data-testid={`alert-${alert.id}`}
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
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 mt-3">
        {hasLocation && (
          <Button 
            size="sm" 
            variant="outline" 
            className="flex-1 h-10 border-blue-500/30 text-blue-400 hover:bg-blue-500/10"
            onClick={() => openMaps(alert.latitude, alert.longitude)}
          >
            <Navigation className="w-4 h-4 mr-1" />
            MAPA
          </Button>
        )}
        
        {!resolved && onResolve && (
          <Button 
            size="sm"
            className={`flex-1 h-10 bg-green-600 hover:bg-green-700 font-bold ${!hasLocation && 'w-full'}`}
            onClick={() => onResolve(alert.id)}
            disabled={isResolving}
          >
            {isResolving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <CheckCircle className="w-4 h-4 mr-1" />
                ATENDIDA
              </>
            )}
          </Button>
        )}

        {resolved && (
          <div className="flex-1 flex items-center justify-center h-10 rounded-md bg-green-500/10 border border-green-500/30">
            <CheckCircle className="w-4 h-4 text-green-400 mr-1" />
            <span className="text-xs font-medium text-green-400">ATENDIDA</span>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================
// TAB 2: VISITS (Pre-registered)
// ============================================
const VisitsTab = ({ onRefresh }) => {
  const [visitors, setVisitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [processingId, setProcessingId] = useState(null);

  const fetchVisitors = useCallback(async () => {
    try {
      const data = await api.getPendingVisitors();
      setVisitors(data);
    } catch (error) {
      console.error('Error fetching visitors:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVisitors();
    const interval = setInterval(fetchVisitors, 15000);
    return () => clearInterval(interval);
  }, [fetchVisitors]);

  const handleEntry = async (id) => {
    setProcessingId(id);
    try {
      await api.registerVisitorEntry(id, '');
      if (navigator.vibrate) navigator.vibrate(100);
      fetchVisitors();
    } catch (error) {
      alert('Error al registrar entrada');
    } finally {
      setProcessingId(null);
    }
  };

  const handleExit = async (id) => {
    setProcessingId(id);
    try {
      await api.registerVisitorExit(id, '');
      if (navigator.vibrate) navigator.vibrate(100);
      fetchVisitors();
    } catch (error) {
      alert('Error al registrar salida');
    } finally {
      setProcessingId(null);
    }
  };

  const filteredVisitors = search
    ? visitors.filter(v => 
        v.full_name?.toLowerCase().includes(search.toLowerCase()) ||
        v.vehicle_plate?.toLowerCase().includes(search.toLowerCase()) ||
        v.national_id?.toLowerCase().includes(search.toLowerCase()) ||
        v.created_by_name?.toLowerCase().includes(search.toLowerCase())
      )
    : visitors;

  const pending = filteredVisitors.filter(v => v.status === 'pending');
  const inside = filteredVisitors.filter(v => v.status === 'entry_registered');

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="h-full flex flex-col">
      {/* Search Bar */}
      <div className="p-3 border-b border-[#1E293B]">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre, placa, cédula..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10 h-11 bg-[#0A0A0F] border-[#1E293B] text-base"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3 space-y-4">
        {/* Inside - Need Exit */}
        {inside.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <h3 className="text-xs font-bold text-green-400 uppercase tracking-wider">
                DENTRO ({inside.length}) — Registrar Salida
              </h3>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {inside.map((visitor) => (
                <VisitorCard 
                  key={visitor.id} 
                  visitor={visitor} 
                  status="inside"
                  onAction={() => handleExit(visitor.id)}
                  isProcessing={processingId === visitor.id}
                />
              ))}
            </div>
          </div>
        )}

        {/* Pending - Need Entry */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-yellow-500" />
            <h3 className="text-xs font-bold text-yellow-400 uppercase tracking-wider">
              ESPERADOS ({pending.length}) — Registrar Entrada
            </h3>
          </div>
          {pending.length > 0 ? (
            <div className="grid gap-2 sm:grid-cols-2">
              {pending.map((visitor) => (
                <VisitorCard 
                  key={visitor.id} 
                  visitor={visitor} 
                  status="pending"
                  onAction={() => handleEntry(visitor.id)}
                  isProcessing={processingId === visitor.id}
                />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-32 text-muted-foreground bg-[#0A0A0F] rounded-xl border border-dashed border-[#1E293B]">
              <Users className="w-10 h-10 mb-2 opacity-30" />
              <p className="text-sm">Sin visitas esperadas</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

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
const ManualEntryTab = () => {
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
    if (!form.full_name.trim()) return;

    setIsSubmitting(true);
    try {
      await api.createAccessLog({
        person_name: form.full_name,
        access_type: 'entry',
        location: form.destination || 'Entrada Principal',
        notes: [
          form.national_id && `Cédula: ${form.national_id}`,
          form.vehicle_plate && `Placa: ${form.vehicle_plate}`,
          form.reason && `Motivo: ${form.reason}`
        ].filter(Boolean).join(' | ')
      });

      if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
      
      setLastEntry({
        name: form.full_name,
        time: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
      });

      setForm({ full_name: '', national_id: '', vehicle_plate: '', destination: '', reason: '' });
    } catch (error) {
      console.error('Error:', error);
      alert('Error al registrar entrada');
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
// TAB 4: HISTORY (Read-only)
// ============================================
const HistoryTab = () => {
  const [filter, setFilter] = useState('today');
  const [alertHistory, setAlertHistory] = useState([]);
  const [visitHistory, setVisitHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const [alerts, visitors] = await Promise.all([
          api.getPanicEvents(),
          api.getAllVisitors('exit_registered')
        ]);

        // Filter by date range
        const now = new Date();
        const filterDate = filter === 'today' 
          ? new Date(now.setHours(0, 0, 0, 0))
          : new Date(now.setDate(now.getDate() - 7));

        setAlertHistory(
          alerts
            .filter(a => a.status === 'resolved' && new Date(a.created_at) >= filterDate)
            .slice(0, 20)
        );

        setVisitHistory(
          visitors
            .filter(v => new Date(v.created_at) >= filterDate)
            .slice(0, 20)
        );
      } catch (error) {
        console.error('Error fetching history:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [filter]);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="h-full flex flex-col">
      {/* Filter */}
      <div className="p-3 border-b border-[#1E293B] flex items-center gap-3">
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
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3 space-y-4">
        {/* Alerts History */}
        <div>
          <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Alertas Atendidas ({alertHistory.length})
          </h3>
          {alertHistory.length > 0 ? (
            <div className="space-y-2">
              {alertHistory.map((alert) => {
                const config = PANIC_CONFIG[alert.panic_type] || PANIC_CONFIG.emergencia_general;
                return (
                  <div key={alert.id} className="p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B] flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg ${config.bg} flex items-center justify-center`}>
                      <config.icon className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{alert.user_name}</p>
                      <p className="text-xs text-muted-foreground">{alert.location}</p>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      <p>{formatTime(alert.created_at)}</p>
                      <p>{new Date(alert.created_at).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">Sin alertas en este período</p>
          )}
        </div>

        {/* Visits History */}
        <div>
          <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-2">
            <Users className="w-4 h-4" />
            Visitas Completadas ({visitHistory.length})
          </h3>
          {visitHistory.length > 0 ? (
            <div className="space-y-2">
              {visitHistory.map((visit) => (
                <div key={visit.id} className="p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B] flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
                    <User className="w-4 h-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{visit.full_name}</p>
                    <p className="text-xs text-muted-foreground">Para: {visit.created_by_name}</p>
                  </div>
                  <div className="text-right text-xs">
                    <p className="text-green-400">↓ {formatTime(visit.entry_at)}</p>
                    <p className="text-orange-400">↑ {formatTime(visit.exit_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">Sin visitas en este período</p>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================
// MAIN COMPONENT
// ============================================
const GuardUI = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('alerts');
  const [alerts, setAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [resolvingId, setResolvingId] = useState(null);

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

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, [fetchAlerts]);

  // Vibrate on new active alerts
  useEffect(() => {
    const activeCount = alerts.filter(a => a.status === 'active').length;
    if (activeCount > 0 && navigator.vibrate) {
      navigator.vibrate([200, 100, 200]);
    }
  }, [alerts]);

  const handleResolve = async (alertId) => {
    setResolvingId(alertId);
    try {
      await api.resolvePanic(alertId);
      if (navigator.vibrate) navigator.vibrate(100);
      fetchAlerts();
    } catch (error) {
      console.error('Error resolving alert:', error);
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
    <div className="h-screen bg-[#05050A] flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 p-3 flex items-center justify-between border-b border-[#1E293B] bg-[#0A0A0F]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-wide">GENTURIX SECURITY</h1>
            <p className="text-xs text-muted-foreground truncate max-w-[140px]">{user?.full_name}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-9 w-9" onClick={handleLogout}>
            <LogOut className="w-5 h-5" />
          </Button>
        </div>
      </header>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
        <TabsList className="flex-shrink-0 grid grid-cols-4 bg-[#0A0A0F] border-b border-[#1E293B] rounded-none h-14 p-0">
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
            value="visits" 
            className="h-full rounded-none data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary flex flex-col gap-0.5"
            data-testid="tab-visits"
          >
            <Users className="w-5 h-5" />
            <span className="text-[10px]">Visitas</span>
          </TabsTrigger>
          
          <TabsTrigger 
            value="manual" 
            className="h-full rounded-none data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary flex flex-col gap-0.5"
            data-testid="tab-manual"
          >
            <UserPlus className="w-5 h-5" />
            <span className="text-[10px]">Registro</span>
          </TabsTrigger>
          
          <TabsTrigger 
            value="history" 
            className="h-full rounded-none data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary flex flex-col gap-0.5"
            data-testid="tab-history"
          >
            <History className="w-5 h-5" />
            <span className="text-[10px]">Historial</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab Content */}
        <div className="flex-1 min-h-0 overflow-hidden">
          <TabsContent value="alerts" className="h-full m-0 data-[state=inactive]:hidden">
            <AlertsTab 
              alerts={alerts}
              onResolve={handleResolve}
              resolvingId={resolvingId}
              onRefresh={handleRefresh}
              isRefreshing={isRefreshing}
            />
          </TabsContent>

          <TabsContent value="visits" className="h-full m-0 data-[state=inactive]:hidden">
            <VisitsTab />
          </TabsContent>

          <TabsContent value="manual" className="h-full m-0 data-[state=inactive]:hidden">
            <ManualEntryTab />
          </TabsContent>

          <TabsContent value="history" className="h-full m-0 data-[state=inactive]:hidden">
            <HistoryTab />
          </TabsContent>
        </div>
      </Tabs>

      {/* Emergency Footer */}
      <footer className="flex-shrink-0 p-2 bg-[#0A0A0F] border-t border-[#1E293B]">
        <a 
          href="tel:911" 
          className="flex items-center justify-center gap-2 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 active:bg-red-500/20"
        >
          <Phone className="w-5 h-5" />
          <span className="font-bold">LLAMAR 911</span>
        </a>
      </footer>
    </div>
  );
};

export default GuardUI;
