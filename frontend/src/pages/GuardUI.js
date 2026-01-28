/**
 * GENTURIX - GuardUI (Tab-Based Layout)
 * 
 * REFACTORED: Clean tab-based UX replacing vertical bloat
 * 
 * Tabs:
 * - Alertas: Emergency alerts with compact cards
 * - Control de Acceso: Entry/Exit registration
 * - Bitácora: Logbook entries
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
import { ScrollArea } from '../components/ui/scroll-area';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
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
  ExternalLink,
  Phone,
  UserPlus,
  UserMinus,
  Users,
  ClipboardList,
  Eye,
  X
} from 'lucide-react';

// ============================================
// PANIC TYPE CONFIGURATION
// ============================================
const PANIC_TYPE_CONFIG = {
  emergencia_medica: { 
    icon: Heart, 
    color: 'bg-red-500', 
    borderColor: 'border-red-500/30',
    bgColor: 'bg-red-500/10',
    label: 'MÉDICA',
    textColor: 'text-red-400'
  },
  actividad_sospechosa: { 
    icon: Eye, 
    color: 'bg-amber-500', 
    borderColor: 'border-amber-500/30',
    bgColor: 'bg-amber-500/10',
    label: 'SOSPECHOSO',
    textColor: 'text-amber-400'
  },
  emergencia_general: { 
    icon: Siren, 
    color: 'bg-orange-500', 
    borderColor: 'border-orange-500/30',
    bgColor: 'bg-orange-500/10',
    label: 'GENERAL',
    textColor: 'text-orange-400'
  }
};

// ============================================
// COMPACT ALERT CARD
// ============================================
const AlertCard = ({ emergency, onViewDetails, onResolve, isResolving }) => {
  const config = PANIC_TYPE_CONFIG[emergency.panic_type] || PANIC_TYPE_CONFIG.emergencia_general;
  const IconComponent = config.icon;

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Ahora';
    if (diffMins < 60) return `${diffMins}m`;
    return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div 
      className={`p-3 rounded-xl ${config.bgColor} border ${config.borderColor}`}
      data-testid={`alert-card-${emergency.id}`}
    >
      <div className="flex items-center gap-3">
        {/* Icon */}
        <div className={`w-10 h-10 rounded-full ${config.color} flex items-center justify-center flex-shrink-0 ${emergency.status === 'active' ? 'animate-pulse' : ''}`}>
          <IconComponent className="w-5 h-5 text-white" />
        </div>
        
        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-white truncate">{emergency.user_name}</span>
            <Badge className={`${config.color} text-white text-[10px] px-1.5 py-0`}>
              {config.label}
            </Badge>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <MapPin className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{emergency.location}</span>
            <span>•</span>
            <span>{formatTime(emergency.created_at)}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-1 flex-shrink-0">
          <Button 
            size="icon" 
            variant="ghost" 
            className="h-8 w-8"
            onClick={() => onViewDetails(emergency)}
          >
            <Eye className="w-4 h-4" />
          </Button>
          {emergency.status === 'active' && (
            <Button 
              size="icon" 
              className="h-8 w-8 bg-green-600 hover:bg-green-700"
              onClick={() => onResolve(emergency.id)}
              disabled={isResolving}
            >
              {isResolving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================
// ALERT DETAIL MODAL
// ============================================
const AlertDetailModal = ({ emergency, isOpen, onClose, onResolve, isResolving }) => {
  if (!emergency) return null;
  
  const config = PANIC_TYPE_CONFIG[emergency.panic_type] || PANIC_TYPE_CONFIG.emergencia_general;
  const IconComponent = config.icon;

  const openInMaps = () => {
    if (emergency.latitude && emergency.longitude) {
      const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
      const url = isIOS 
        ? `maps://maps.apple.com/?q=${emergency.latitude},${emergency.longitude}`
        : `https://www.google.com/maps/search/?api=1&query=${emergency.latitude},${emergency.longitude}`;
      window.open(url, '_blank');
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-full ${config.color} flex items-center justify-center`}>
              <IconComponent className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="block">{emergency.user_name}</span>
              <Badge className={`${config.color} text-white text-xs`}>{config.label}</Badge>
            </div>
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          {/* Location */}
          <div className="space-y-2">
            <Label className="text-muted-foreground text-xs">Ubicación</Label>
            <div className="flex items-center gap-2 p-3 rounded-lg bg-[#181B25] border border-[#1E293B]">
              <MapPin className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm">{emergency.location}</span>
            </div>
          </div>

          {/* GPS */}
          {emergency.latitude && (
            <button
              onClick={openInMaps}
              className="w-full flex items-center justify-between p-3 rounded-lg bg-blue-500/10 border border-blue-500/30 text-blue-400 hover:bg-blue-500/20 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Navigation className="w-4 h-4" />
                <span className="font-mono text-xs">
                  {emergency.latitude.toFixed(6)}, {emergency.longitude.toFixed(6)}
                </span>
              </div>
              <ExternalLink className="w-4 h-4" />
            </button>
          )}

          {/* Description */}
          {emergency.description && (
            <div className="space-y-2">
              <Label className="text-muted-foreground text-xs">Descripción</Label>
              <p className="text-sm p-3 rounded-lg bg-[#181B25] border border-[#1E293B]">
                {emergency.description}
              </p>
            </div>
          )}

          {/* Timestamp */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="w-3 h-3" />
            {new Date(emergency.created_at).toLocaleString('es-ES')}
          </div>
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          {emergency.latitude && (
            <Button 
              variant="outline" 
              className="flex-1 border-blue-500/30 text-blue-400"
              onClick={openInMaps}
            >
              <Navigation className="w-4 h-4 mr-2" />
              Ver en Mapa
            </Button>
          )}
          {emergency.status === 'active' && (
            <Button 
              className="flex-1 bg-green-600 hover:bg-green-700"
              onClick={() => { onResolve(emergency.id); onClose(); }}
              disabled={isResolving}
            >
              {isResolving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle className="w-4 h-4 mr-2" />}
              Resolver
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// ACCESS CONTROL TAB
// ============================================
const AccessControlTab = ({ onRegister }) => {
  const [entryForm, setEntryForm] = useState({ guest_name: '', resident_name: '', notes: '' });
  const [accessLogs, setAccessLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchAccessLogs();
  }, []);

  const fetchAccessLogs = async () => {
    try {
      const logs = await api.getAccessLogs();
      setAccessLogs(logs);
    } catch (error) {
      console.error('Error fetching access logs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (type) => {
    if (!entryForm.guest_name.trim()) return;
    
    setIsSubmitting(true);
    try {
      await api.createAccessLog({
        person_name: entryForm.guest_name,
        access_type: type,
        location: 'Entrada Principal',
        notes: entryForm.resident_name ? `Visita para: ${entryForm.resident_name}. ${entryForm.notes}` : entryForm.notes
      });
      setEntryForm({ guest_name: '', resident_name: '', notes: '' });
      fetchAccessLogs();
      if (navigator.vibrate) navigator.vibrate(100);
    } catch (error) {
      console.error('Error registering access:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4 p-4">
      {/* Registration Form */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardContent className="p-4 space-y-3">
          <h3 className="font-semibold text-sm flex items-center gap-2">
            <Users className="w-4 h-4 text-primary" />
            Registrar Acceso
          </h3>
          
          <div className="space-y-3">
            <div>
              <Label className="text-xs text-muted-foreground">Nombre del Visitante *</Label>
              <Input
                placeholder="Nombre completo"
                value={entryForm.guest_name}
                onChange={(e) => setEntryForm({...entryForm, guest_name: e.target.value})}
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Residente (visita para)</Label>
              <Input
                placeholder="Nombre del residente"
                value={entryForm.resident_name}
                onChange={(e) => setEntryForm({...entryForm, resident_name: e.target.value})}
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Notas</Label>
              <Input
                placeholder="Observaciones adicionales"
                value={entryForm.notes}
                onChange={(e) => setEntryForm({...entryForm, notes: e.target.value})}
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-2">
            <Button 
              onClick={() => handleRegister('entry')}
              disabled={!entryForm.guest_name.trim() || isSubmitting}
              className="bg-green-600 hover:bg-green-700"
              data-testid="register-entry-btn"
            >
              <UserPlus className="w-4 h-4 mr-2" />
              Entrada
            </Button>
            <Button 
              onClick={() => handleRegister('exit')}
              disabled={!entryForm.guest_name.trim() || isSubmitting}
              className="bg-red-600 hover:bg-red-700"
              data-testid="register-exit-btn"
            >
              <UserMinus className="w-4 h-4 mr-2" />
              Salida
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recent Access Logs */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-muted-foreground">Registros Recientes</h3>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : accessLogs.length > 0 ? (
          <div className="space-y-2">
            {accessLogs.slice(0, 10).map((log) => (
              <div 
                key={log.id} 
                className={`p-3 rounded-lg border ${
                  log.access_type === 'entry' 
                    ? 'bg-green-500/10 border-green-500/30' 
                    : 'bg-red-500/10 border-red-500/30'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {log.access_type === 'entry' ? (
                      <UserPlus className="w-4 h-4 text-green-400" />
                    ) : (
                      <UserMinus className="w-4 h-4 text-red-400" />
                    )}
                    <span className="font-medium text-sm">{log.person_name}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(log.timestamp).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                {log.notes && (
                  <p className="text-xs text-muted-foreground mt-1 pl-6">{log.notes}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Users className="w-10 h-10 mx-auto mb-2 opacity-30" />
            <p className="text-sm">Sin registros de acceso</p>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================
// LOGBOOK TAB
// ============================================
const LogbookTab = () => {
  const { user } = useAuth();
  const [entries, setEntries] = useState([]);
  const [newEntry, setNewEntry] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    fetchLogbook();
  }, []);

  const fetchLogbook = async () => {
    try {
      // Use audit logs filtered by guard actions as logbook
      const logs = await api.getAuditLogs({ module: 'security' });
      setEntries(logs.slice(0, 20));
    } catch (error) {
      console.error('Error fetching logbook:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddEntry = async () => {
    if (!newEntry.trim()) return;
    
    setIsSubmitting(true);
    try {
      await api.createAccessLog({
        person_name: user.full_name,
        access_type: 'logbook',
        location: 'Bitácora',
        notes: newEntry
      });
      setNewEntry('');
      fetchLogbook();
    } catch (error) {
      console.error('Error adding logbook entry:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4 p-4">
      {/* New Entry */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardContent className="p-4 space-y-3">
          <h3 className="font-semibold text-sm flex items-center gap-2">
            <ClipboardList className="w-4 h-4 text-primary" />
            Nueva Entrada en Bitácora
          </h3>
          <Textarea
            placeholder="Describe la novedad o evento..."
            value={newEntry}
            onChange={(e) => setNewEntry(e.target.value)}
            className="bg-[#181B25] border-[#1E293B] min-h-[80px]"
          />
          <Button 
            onClick={handleAddEntry}
            disabled={!newEntry.trim() || isSubmitting}
            className="w-full"
            data-testid="add-logbook-entry-btn"
          >
            {isSubmitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
            Agregar Entrada
          </Button>
        </CardContent>
      </Card>

      {/* Entries List */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-muted-foreground">Entradas Recientes</h3>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : entries.length > 0 ? (
          <div className="space-y-2">
            {entries.map((entry) => (
              <div key={entry.id} className="p-3 rounded-lg bg-[#0F111A] border border-[#1E293B]">
                <div className="flex items-center justify-between mb-1">
                  <Badge variant="outline" className="text-xs">
                    {entry.event_type?.replace(/_/g, ' ') || 'evento'}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {new Date(entry.timestamp).toLocaleString('es-ES', {
                      day: '2-digit',
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {JSON.stringify(entry.details).replace(/[{}"]/g, '').substring(0, 100)}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <ClipboardList className="w-10 h-10 mx-auto mb-2 opacity-30" />
            <p className="text-sm">Sin entradas en la bitácora</p>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================
// MAIN GUARD UI COMPONENT
// ============================================
const GuardUI = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('alerts');
  const [activeEmergencies, setActiveEmergencies] = useState([]);
  const [resolvedEmergencies, setResolvedEmergencies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [resolvingId, setResolvingId] = useState(null);
  const [selectedEmergency, setSelectedEmergency] = useState(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  const fetchEmergencies = useCallback(async () => {
    try {
      const events = await api.getPanicEvents();
      setActiveEmergencies(events.filter(e => e.status === 'active'));
      setResolvedEmergencies(events.filter(e => e.status === 'resolved').slice(0, 10));
    } catch (error) {
      console.error('Error fetching emergencies:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchEmergencies();
    const interval = setInterval(fetchEmergencies, 5000);
    return () => clearInterval(interval);
  }, [fetchEmergencies]);

  useEffect(() => {
    if (activeEmergencies.length > 0 && navigator.vibrate) {
      navigator.vibrate([200, 100, 200]);
    }
  }, [activeEmergencies.length]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchEmergencies();
  };

  const handleResolve = async (eventId) => {
    setResolvingId(eventId);
    try {
      await api.resolvePanic(eventId);
      if (navigator.vibrate) navigator.vibrate(100);
      fetchEmergencies();
    } catch (error) {
      console.error('Error resolving:', error);
    } finally {
      setResolvingId(null);
    }
  };

  const handleViewDetails = (emergency) => {
    setSelectedEmergency(emergency);
    setDetailModalOpen(true);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center safe-area">
        <Loader2 className="w-10 h-10 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#05050A] flex flex-col safe-area">
      {/* Header */}
      <header className="sticky top-0 z-40 p-4 flex items-center justify-between border-b border-[#1E293B] bg-[#0F111A]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-green-400" />
          </div>
          <div>
            <h1 className="text-base font-bold font-['Outfit']">GENTURIX GUARD</h1>
            <p className="text-xs text-muted-foreground truncate max-w-[120px]">
              {user?.full_name}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="text-muted-foreground hover:text-white"
          >
            <RefreshCw className={`w-5 h-5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleLogout}
            className="text-muted-foreground hover:text-white"
            data-testid="guard-logout-btn"
          >
            <LogOut className="w-5 h-5" />
          </Button>
        </div>
      </header>

      {/* Alert Status Bar */}
      <div className={`p-2 ${
        activeEmergencies.length > 0 
          ? 'bg-red-500/10 border-b-2 border-red-500' 
          : 'bg-green-500/10 border-b border-green-500/20'
      }`}>
        <div className="flex items-center justify-center gap-2">
          {activeEmergencies.length > 0 ? (
            <>
              <Bell className="w-4 h-4 text-red-400 animate-pulse" />
              <span className="text-sm font-bold text-red-400">
                {activeEmergencies.length} ALERTA{activeEmergencies.length > 1 ? 'S' : ''} ACTIVA{activeEmergencies.length > 1 ? 'S' : ''}
              </span>
            </>
          ) : (
            <>
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span className="text-sm font-bold text-green-400">TODO EN ORDEN</span>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="grid grid-cols-3 bg-[#0F111A] border-b border-[#1E293B] rounded-none h-12">
          <TabsTrigger 
            value="alerts" 
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
            data-testid="tab-alerts"
          >
            <AlertTriangle className="w-4 h-4 mr-2" />
            Alertas
            {activeEmergencies.length > 0 && (
              <Badge className="ml-2 bg-red-500 text-white text-[10px] h-5 min-w-[20px]">
                {activeEmergencies.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger 
            value="access" 
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
            data-testid="tab-access"
          >
            <Users className="w-4 h-4 mr-2" />
            Acceso
          </TabsTrigger>
          <TabsTrigger 
            value="logbook" 
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
            data-testid="tab-logbook"
          >
            <ClipboardList className="w-4 h-4 mr-2" />
            Bitácora
          </TabsTrigger>
        </TabsList>

        {/* Alerts Tab */}
        <TabsContent value="alerts" className="flex-1 mt-0">
          <ScrollArea className="h-[calc(100vh-220px)]">
            <div className="p-4 space-y-4">
              {/* Active Emergencies */}
              {activeEmergencies.length > 0 && (
                <section className="space-y-2">
                  <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Emergencias Activas
                  </h2>
                  {activeEmergencies.map((emergency) => (
                    <AlertCard
                      key={emergency.id}
                      emergency={emergency}
                      onViewDetails={handleViewDetails}
                      onResolve={handleResolve}
                      isResolving={resolvingId === emergency.id}
                    />
                  ))}
                </section>
              )}

              {/* Resolved */}
              <section className="space-y-2">
                <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Resueltas Recientemente
                </h2>
                {resolvedEmergencies.length > 0 ? (
                  resolvedEmergencies.map((emergency) => (
                    <AlertCard
                      key={emergency.id}
                      emergency={emergency}
                      onViewDetails={handleViewDetails}
                      onResolve={handleResolve}
                      isResolving={false}
                    />
                  ))
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <CheckCircle className="w-10 h-10 mx-auto mb-2 opacity-30" />
                    <p className="text-sm">Sin eventos recientes</p>
                  </div>
                )}
              </section>
            </div>
          </ScrollArea>
        </TabsContent>

        {/* Access Control Tab */}
        <TabsContent value="access" className="flex-1 mt-0">
          <ScrollArea className="h-[calc(100vh-220px)]">
            <AccessControlTab />
          </ScrollArea>
        </TabsContent>

        {/* Logbook Tab */}
        <TabsContent value="logbook" className="flex-1 mt-0">
          <ScrollArea className="h-[calc(100vh-220px)]">
            <LogbookTab />
          </ScrollArea>
        </TabsContent>
      </Tabs>

      {/* Emergency Call Footer */}
      <footer className="p-3 bg-[#0F111A] border-t border-[#1E293B] safe-area-bottom">
        <a 
          href="tel:911" 
          className="flex items-center justify-center gap-2 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400"
        >
          <Phone className="w-5 h-5" />
          <span className="font-semibold">Llamar 911</span>
        </a>
      </footer>

      {/* Alert Detail Modal */}
      <AlertDetailModal
        emergency={selectedEmergency}
        isOpen={detailModalOpen}
        onClose={() => setDetailModalOpen(false)}
        onResolve={handleResolve}
        isResolving={resolvingId === selectedEmergency?.id}
      />
    </div>
  );
};

export default GuardUI;
