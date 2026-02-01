/**
 * GENTURIX - Advanced Visitor Check-in for Guards
 * 
 * High-contrast, mobile-optimized UI for quick visitor validation:
 * - Fast search by name, ID, or vehicle plate
 * - Color-coded authorization status
 * - One-tap check-in/check-out
 * - Real-time visitors inside list
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Card, CardContent } from './ui/card';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { ScrollArea } from './ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { toast } from 'sonner';
import api from '../services/api';
import { 
  Search,
  UserPlus,
  UserMinus,
  Users,
  Car,
  Calendar,
  CalendarCheck,
  Clock,
  Loader2,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Shield,
  ChevronRight,
  RefreshCw,
  Home,
  Timer,
  Infinity as InfinityIcon,
  Repeat,
  Eye,
  Trash2,
  Bug
} from 'lucide-react';

// ============================================
// CONFIGURATION
// ============================================
const COLOR_CONFIG = {
  green: { 
    bg: 'bg-green-500', 
    light: 'bg-green-500/20', 
    border: 'border-green-500', 
    text: 'text-green-400',
    label: 'PERMANENTE'
  },
  blue: { 
    bg: 'bg-blue-500', 
    light: 'bg-blue-500/20', 
    border: 'border-blue-500', 
    text: 'text-blue-400',
    label: 'RECURRENTE'
  },
  yellow: { 
    bg: 'bg-yellow-500', 
    light: 'bg-yellow-500/20', 
    border: 'border-yellow-500', 
    text: 'text-yellow-400',
    label: 'TEMPORAL'
  },
  purple: { 
    bg: 'bg-purple-500', 
    light: 'bg-purple-500/20', 
    border: 'border-purple-500', 
    text: 'text-purple-400',
    label: 'EXTENDIDO'
  },
  gray: { 
    bg: 'bg-gray-500', 
    light: 'bg-gray-500/20', 
    border: 'border-gray-500', 
    text: 'text-gray-400',
    label: 'MANUAL'
  }
};

const TYPE_ICONS = {
  permanent: InfinityIcon,
  recurring: Repeat,
  temporary: Timer,
  extended: Calendar,
  manual: UserPlus
};

// ============================================
// AUTHORIZATION SEARCH CARD
// ============================================
const AuthorizationSearchCard = ({ auth, onCheckIn, isProcessing }) => {
  const colorConfig = COLOR_CONFIG[auth.color_code] || COLOR_CONFIG.yellow;
  const IconComponent = TYPE_ICONS[auth.authorization_type] || Timer;
  const isValid = auth.is_currently_valid;

  const formatInfo = () => {
    if (auth.authorization_type === 'recurring' && auth.allowed_days?.length) {
      return auth.allowed_days.join(', ');
    }
    if (auth.valid_from) {
      const from = new Date(auth.valid_from).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
      if (auth.valid_to && auth.valid_from !== auth.valid_to) {
        const to = new Date(auth.valid_to).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
        return `${from} - ${to}`;
      }
      return from;
    }
    return '';
  };

  return (
    <div 
      className={`p-4 rounded-xl border-2 transition-all ${
        isValid 
          ? `${colorConfig.light} ${colorConfig.border}` 
          : 'bg-gray-800/50 border-gray-700'
      } ${isProcessing ? 'opacity-50 pointer-events-none' : ''}`}
      data-testid={`auth-card-${auth.id}`}
    >
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <div className={`w-12 h-12 rounded-xl ${colorConfig.bg} flex items-center justify-center flex-shrink-0`}>
          <IconComponent className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-bold text-white text-lg truncate">{auth.visitor_name}</p>
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className={`${colorConfig.light} ${colorConfig.text} border ${colorConfig.border}`}>
              {colorConfig.label}
            </Badge>
            {isValid ? (
              <Badge className="bg-green-500/20 text-green-400 border border-green-500/30">
                <CheckCircle className="w-3 h-3 mr-1" />
                AUTORIZADO
              </Badge>
            ) : (
              <Badge className="bg-red-500/20 text-red-400 border border-red-500/30">
                <XCircle className="w-3 h-3 mr-1" />
                {auth.validity_status === 'expired' ? 'EXPIRADO' : 'NO VÁLIDO'}
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Details */}
      <div className="grid grid-cols-2 gap-2 text-sm mb-3">
        <div className="flex items-center gap-1 text-muted-foreground">
          <Home className="w-4 h-4" />
          <span className="truncate">{auth.created_by_name || 'Residente'}</span>
        </div>
        {auth.resident_apartment && (
          <div className="flex items-center gap-1 text-muted-foreground">
            <span className="text-primary font-semibold">{auth.resident_apartment}</span>
          </div>
        )}
        {auth.identification_number && (
          <div className="flex items-center gap-1 text-muted-foreground">
            <Shield className="w-4 h-4" />
            <span>{auth.identification_number}</span>
          </div>
        )}
        {auth.vehicle_plate && (
          <div className="flex items-center gap-1 text-muted-foreground">
            <Car className="w-4 h-4" />
            <span className="font-mono font-bold">{auth.vehicle_plate}</span>
          </div>
        )}
      </div>

      {/* Info line */}
      {formatInfo() && (
        <p className="text-xs text-muted-foreground mb-3">
          <Calendar className="w-3 h-3 inline mr-1" />
          {formatInfo()}
          {auth.allowed_hours_from && ` • ${auth.allowed_hours_from} - ${auth.allowed_hours_to}`}
        </p>
      )}

      {/* Validity Message */}
      {!isValid && auth.validity_message && (
        <div className="p-2 rounded-lg bg-red-500/10 border border-red-500/30 mb-3">
          <p className="text-xs text-red-400 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" />
            {auth.validity_message}
          </p>
        </div>
      )}

      {/* Check-in Button */}
      <Button 
        className={`w-full h-14 text-lg font-bold ${
          isValid 
            ? 'bg-green-600 hover:bg-green-700' 
            : 'bg-yellow-600 hover:bg-yellow-700'
        }`}
        onClick={() => onCheckIn(auth)}
        disabled={isProcessing}
        data-testid={`checkin-btn-${auth.id}`}
      >
        {isProcessing ? (
          <>
            <Loader2 className="w-6 h-6 mr-2 animate-spin" />
            PROCESANDO...
          </>
        ) : (
          <>
            <UserPlus className="w-6 h-6 mr-2" />
            {isValid ? 'REGISTRAR ENTRADA' : 'ENTRADA MANUAL'}
          </>
        )}
      </Button>
    </div>
  );
};

// ============================================
// VISITOR INSIDE CARD
// ============================================
const VisitorInsideCard = ({ entry, onCheckOut, isProcessing }) => {
  const colorConfig = COLOR_CONFIG[entry.color_code] || COLOR_CONFIG.gray;
  
  const formatDuration = () => {
    if (!entry.entry_at) return '';
    const entryTime = new Date(entry.entry_at);
    const now = new Date();
    const diffMinutes = Math.floor((now - entryTime) / (1000 * 60));
    
    if (diffMinutes < 60) return `${diffMinutes}min`;
    const hours = Math.floor(diffMinutes / 60);
    const mins = diffMinutes % 60;
    return `${hours}h ${mins}m`;
  };

  return (
    <div className={`p-3 rounded-xl border-2 ${colorConfig.light} ${colorConfig.border}`}>
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-lg ${colorConfig.bg} flex items-center justify-center flex-shrink-0`}>
          <Users className="w-5 h-5 text-white" />
        </div>
        
        <div className="flex-1 min-w-0">
          <p className="font-bold text-white truncate">{entry.visitor_name}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {entry.resident_name && <span>{entry.resident_name}</span>}
            {entry.destination && <span>• {entry.destination}</span>}
          </div>
          <div className="flex items-center gap-2 text-xs mt-1">
            <span className="text-green-400">
              <Clock className="w-3 h-3 inline mr-1" />
              Entrada: {new Date(entry.entry_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
            </span>
            <span className="text-muted-foreground">• {formatDuration()}</span>
          </div>
        </div>

        <Button 
          className="h-12 bg-orange-600 hover:bg-orange-700 font-bold"
          onClick={() => onCheckOut(entry)}
          disabled={isProcessing}
          data-testid={`checkout-btn-${entry.id}`}
        >
          {isProcessing ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <>
              <UserMinus className="w-5 h-5 mr-1" />
              SALIDA
            </>
          )}
        </Button>
      </div>
    </div>
  );
};

// ============================================
// MANUAL CHECK-IN DIALOG
// ============================================
const ManualCheckInDialog = ({ open, onClose, authorization, onSubmit }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    visitor_name: '',
    identification_number: '',
    vehicle_plate: '',
    destination: '',
    notes: ''
  });

  useEffect(() => {
    if (authorization) {
      setFormData({
        visitor_name: authorization.visitor_name || '',
        identification_number: authorization.identification_number || '',
        vehicle_plate: authorization.vehicle_plate || '',
        destination: authorization.resident_apartment || '',
        notes: ''
      });
    } else {
      setFormData({
        visitor_name: '',
        identification_number: '',
        vehicle_plate: '',
        destination: '',
        notes: ''
      });
    }
  }, [authorization, open]);

  const handleSubmit = async () => {
    if (!formData.visitor_name.trim() && !authorization) {
      toast.error('El nombre es requerido');
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        authorization_id: authorization?.id || null,
        visitor_name: formData.visitor_name.trim() || null,
        identification_number: formData.identification_number.trim() || null,
        vehicle_plate: formData.vehicle_plate.trim().toUpperCase() || null,
        destination: formData.destination.trim() || null,
        notes: formData.notes.trim() || null
      };

      await onSubmit(payload);
      onClose();
    } catch (error) {
      toast.error(error.message || 'Error al registrar entrada');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isAuthorized = authorization?.is_currently_valid;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0A0A0F] border-[#1E293B] max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className={`w-5 h-5 ${isAuthorized ? 'text-green-400' : 'text-yellow-400'}`} />
            {authorization ? 'Confirmar Entrada' : 'Entrada Manual'}
          </DialogTitle>
          <DialogDescription>
            {authorization 
              ? isAuthorized 
                ? 'Visitante autorizado - confirmar entrada'
                : 'Autorización no válida - registrar como entrada manual'
              : 'Registrar visitante sin autorización previa'
            }
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Authorization Status Banner */}
          {authorization && (
            <div className={`p-3 rounded-lg border ${
              isAuthorized 
                ? 'bg-green-500/10 border-green-500/30' 
                : 'bg-yellow-500/10 border-yellow-500/30'
            }`}>
              <div className="flex items-center gap-2">
                {isAuthorized ? (
                  <CheckCircle className="w-5 h-5 text-green-400" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-yellow-400" />
                )}
                <div>
                  <p className={`font-semibold ${isAuthorized ? 'text-green-400' : 'text-yellow-400'}`}>
                    {isAuthorized ? 'AUTORIZADO' : 'NO AUTORIZADO'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {authorization.validity_message || (isAuthorized ? 'Autorización válida' : 'Autorización no válida actualmente')}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Visitor Name */}
          <div>
            <Label className="text-sm text-muted-foreground">Nombre del Visitante *</Label>
            <Input
              placeholder="Nombre completo"
              value={formData.visitor_name}
              onChange={(e) => setFormData({...formData, visitor_name: e.target.value})}
              className="bg-[#0F111A] border-[#1E293B] mt-1 h-12 text-lg"
              disabled={!!authorization}
              data-testid="checkin-visitor-name"
            />
          </div>

          {/* ID and Vehicle */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-sm text-muted-foreground">Cédula / ID</Label>
              <Input
                placeholder="Documento"
                value={formData.identification_number}
                onChange={(e) => setFormData({...formData, identification_number: e.target.value})}
                className="bg-[#0F111A] border-[#1E293B] mt-1"
              />
            </div>
            <div>
              <Label className="text-sm text-muted-foreground">Placa Vehículo</Label>
              <Input
                placeholder="ABC-123"
                value={formData.vehicle_plate}
                onChange={(e) => setFormData({...formData, vehicle_plate: e.target.value.toUpperCase()})}
                className="bg-[#0F111A] border-[#1E293B] mt-1 font-mono"
              />
            </div>
          </div>

          {/* Destination */}
          <div>
            <Label className="text-sm text-muted-foreground">Casa / Apartamento</Label>
            <Input
              placeholder="Destino del visitante"
              value={formData.destination}
              onChange={(e) => setFormData({...formData, destination: e.target.value})}
              className="bg-[#0F111A] border-[#1E293B] mt-1"
            />
          </div>

          {/* Notes */}
          <div>
            <Label className="text-sm text-muted-foreground">Notas (opcional)</Label>
            <Textarea
              placeholder="Observaciones..."
              value={formData.notes}
              onChange={(e) => setFormData({...formData, notes: e.target.value})}
              className="bg-[#0F111A] border-[#1E293B] mt-1 min-h-[60px]"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancelar
          </Button>
          <Button 
            className={`${isAuthorized ? 'bg-green-600 hover:bg-green-700' : 'bg-yellow-600 hover:bg-yellow-700'} font-bold`}
            onClick={handleSubmit}
            disabled={(!formData.visitor_name.trim() && !authorization) || isSubmitting}
            data-testid="confirm-checkin-btn"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <UserPlus className="w-4 h-4 mr-2" />
            )}
            REGISTRAR ENTRADA
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// MAIN COMPONENT
// ============================================
const VisitorCheckInGuard = () => {
  const [search, setSearch] = useState('');
  const [authorizations, setAuthorizations] = useState([]);
  const [todayPreregistrations, setTodayPreregistrations] = useState([]); // Pending pre-registrations for today
  const [entriesToday, setEntriesToday] = useState([]); // Visitors who have already checked in today
  const [visitorsInside, setVisitorsInside] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [showCheckInDialog, setShowCheckInDialog] = useState(false);
  const [selectedAuth, setSelectedAuth] = useState(null);
  const [processingAuthId, setProcessingAuthId] = useState(null); // Track which auth is being processed
  const [processingCheckout, setProcessingCheckout] = useState(null);
  const [showEntriesToday, setShowEntriesToday] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false); // Track refresh state
  const [recentlyProcessed, setRecentlyProcessed] = useState(new Set()); // Track recently processed to prevent double-clicks

  const fetchData = useCallback(async (showToast = false) => {
    if (showToast) setIsRefreshing(true);
    try {
      const [inside, allAuths, todayEntries] = await Promise.all([
        api.getVisitorsInside(),
        api.getAuthorizationsForGuard(''), // Only returns pending authorizations by default
        api.getEntriesToday().catch(() => []) // Get today's entries
      ]);
      setVisitorsInside(inside);
      setEntriesToday(todayEntries);
      
      // Filter only currently valid authorizations for today's list
      const validToday = allAuths.filter(auth => auth.is_currently_valid);
      setTodayPreregistrations(validToday);
      
      if (showToast) {
        toast.success(`✓ Actualizado: ${validToday.length} pendientes, ${inside.length} adentro`);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      if (showToast) {
        toast.error('Error al actualizar datos');
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  // Cleanup legacy authorizations that weren't properly marked as used
  const handleCleanup = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const result = await api.cleanupAuthorizations();
      console.log('Cleanup result:', result);
      
      if (result.fixed_count > 0) {
        toast.success(`🧹 Se limpiaron ${result.fixed_count} autorizaciones duplicadas`);
        // Refresh data after cleanup
        await fetchData();
      } else {
        // Show more info if nothing was fixed
        const msg = result.total_all_pending > 0 
          ? `No hay duplicados. Hay ${result.total_all_pending} pendientes (pueden ser permanentes/recurrentes)`
          : '✓ No hay autorizaciones para limpiar';
        toast.info(msg);
      }
    } catch (error) {
      console.error('Cleanup error:', error);
      toast.error('Error al limpiar autorizaciones');
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchData]);

  // Diagnose authorization issues
  const handleDiagnose = useCallback(async () => {
    try {
      const result = await api.diagnoseAuthorizations();
      console.log('Diagnose result:', result);
      
      // Find authorizations that SHOULD be marked as used but aren't
      const problems = result.authorizations?.filter(a => a.SHOULD_BE_USED) || [];
      
      if (problems.length > 0) {
        const names = problems.map(p => p.visitor_name).join(', ');
        toast.error(`🔍 Encontrados ${problems.length} con problema: ${names}. Ver consola para detalles.`);
      } else {
        toast.success(`✓ ${result.total_pending} pendientes, todos correctos`);
      }
    } catch (error) {
      console.error('Diagnose error:', error);
      toast.error('Error al diagnosticar');
    }
  }, []);

  useEffect(() => {
    fetchData();
    // Poll every 15 seconds
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Search authorizations
  const handleSearch = useCallback(async (searchTerm) => {
    if (!searchTerm.trim()) {
      setAuthorizations([]);
      return;
    }

    setIsSearching(true);
    try {
      const results = await api.getAuthorizationsForGuard(searchTerm.trim());
      setAuthorizations(results);
    } catch (error) {
      console.error('Error searching authorizations:', error);
      toast.error('Error en la búsqueda');
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      handleSearch(search);
    }, 300);
    return () => clearTimeout(timer);
  }, [search, handleSearch]);

  const handleCheckInClick = (auth) => {
    setSelectedAuth(auth);
    setShowCheckInDialog(true);
  };

  const handleManualCheckIn = () => {
    setSelectedAuth(null);
    setShowCheckInDialog(true);
  };

  const handleCheckInSubmit = async (payload) => {
    const authId = payload.authorization_id;
    
    // GUARD 1: Check if this authorization was recently processed (prevents double-click race condition)
    if (authId && recentlyProcessed.has(authId)) {
      console.log('[Guard] Blocked: authorization recently processed', authId);
      toast.info('Esta autorización ya fue procesada');
      return;
    }
    
    // GUARD 2: Check if already processing
    if (processingAuthId) {
      console.log('[Guard] Blocked: already processing another authorization');
      return;
    }
    
    // Set processing state to disable the button
    setProcessingAuthId(authId);
    
    // IMMEDIATELY mark as recently processed to prevent any race conditions
    if (authId) {
      setRecentlyProcessed(prev => new Set([...prev, authId]));
    }
    
    // IMMEDIATELY remove from local lists (optimistic update)
    if (authId) {
      setAuthorizations(prev => prev.filter(a => a.id !== authId));
      setTodayPreregistrations(prev => prev.filter(a => a.id !== authId));
    }
    
    try {
      const result = await api.guardCheckIn(payload);
      
      if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
      
      toast.success(result.is_authorized ? '✅ Entrada autorizada registrada' : '⚠️ Entrada manual registrada');
      
      setSearch('');
      // fetchData will refresh from backend which should also exclude the used authorization
      fetchData();
    } catch (error) {
      // Handle 409 Conflict - authorization already used
      if (error.status === 409) {
        toast.error('🚫 ' + (error.message || 'Esta autorización ya fue utilizada'));
        // Keep removed from local list since it's already used
        console.log('[Guard] 409 Conflict - authorization already used:', authId);
      } else {
        toast.error(error.message || 'Error al registrar entrada');
        // On other errors, we might want to restore the item... but for safety, keep it removed
        // The next fetchData will restore it if it should be there
      }
      throw error;
    } finally {
      setProcessingAuthId(null);
      // Clear from recently processed after 5 seconds to allow retry if needed
      if (authId) {
        setTimeout(() => {
          setRecentlyProcessed(prev => {
            const newSet = new Set(prev);
            newSet.delete(authId);
            return newSet;
          });
        }, 5000);
      }
    }
  };

  const handleCheckOut = async (entry) => {
    setProcessingCheckout(entry.id);
    try {
      await api.guardCheckOut(entry.id);
      
      if (navigator.vibrate) navigator.vibrate(100);
      
      toast.success(`Salida registrada: ${entry.visitor_name}`);
      fetchData();
    } catch (error) {
      toast.error(error.message || 'Error al registrar salida');
    } finally {
      setProcessingCheckout(null);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Search Header */}
      <div className="p-3 bg-[#0A0A0F] border-b border-[#1E293B]">
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <Input
            placeholder="Buscar nombre, cédula o placa..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-11 h-12 text-lg bg-[#0F111A] border-[#1E293B]"
            data-testid="visitor-search-input"
          />
          {isSearching && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-primary animate-spin" />
          )}
        </div>
        
        <Button 
          variant="outline" 
          className="w-full border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/10"
          onClick={handleManualCheckIn}
          data-testid="manual-checkin-btn"
        >
          <UserPlus className="w-4 h-4 mr-2" />
          Entrada Manual (Sin Autorización)
        </Button>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {/* Search Results */}
          {search.trim() && (
            <div>
              <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2 flex items-center gap-2">
                <Search className="w-4 h-4" />
                Resultados ({authorizations.length})
              </h3>
              
              {authorizations.length > 0 ? (
                <div className="space-y-3">
                  {authorizations.map((auth) => (
                    <AuthorizationSearchCard 
                      key={auth.id}
                      auth={auth}
                      onCheckIn={handleCheckInClick}
                      isProcessing={processingAuthId === auth.id}
                    />
                  ))}
                </div>
              ) : !isSearching && (
                <div className="text-center py-8 text-muted-foreground bg-[#0F111A] rounded-xl border border-dashed border-[#1E293B]">
                  <Search className="w-10 h-10 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">No se encontraron autorizaciones</p>
                  <p className="text-xs mt-1">Puedes registrar una entrada manual</p>
                </div>
              )}
            </div>
          )}

          {/* Today's Active Authorizations - Always visible when not searching */}
          {!search.trim() && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-bold text-blue-400 uppercase tracking-wider flex items-center gap-2">
                  <CalendarCheck className="w-4 h-4" />
                  PRE-REGISTROS PENDIENTES ({todayPreregistrations.length})
                </h3>
                <div className="flex items-center gap-1">
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={handleDiagnose}
                    disabled={isRefreshing}
                    title="Diagnosticar problemas"
                    data-testid="diagnose-btn"
                  >
                    <Bug className="w-4 h-4 text-yellow-400" />
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={handleCleanup}
                    disabled={isRefreshing}
                    title="Limpiar autorizaciones duplicadas"
                    data-testid="cleanup-btn"
                  >
                    <Trash2 className={`w-4 h-4 text-orange-400 ${isRefreshing ? 'animate-pulse' : ''}`} />
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => fetchData(true)}
                    disabled={isRefreshing}
                    data-testid="refresh-preregistrations-btn"
                  >
                    <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                  </Button>
                </div>
              </div>
              
              {todayPreregistrations.length > 0 ? (
                <div className="space-y-2">
                  {todayPreregistrations.map((auth) => (
                    <AuthorizationSearchCard 
                      key={auth.id}
                      auth={auth}
                      onCheckIn={handleCheckInClick}
                      isProcessing={processingAuthId === auth.id}
                    />
                  ))}
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground bg-[#0F111A] rounded-xl border border-dashed border-[#1E293B]">
                  <CalendarCheck className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <p className="text-sm">No hay pre-registros pendientes</p>
                  <p className="text-xs mt-1">Los residentes pueden crear autorizaciones</p>
                </div>
              )}
            </div>
          )}

          {/* Entries Today - Collapsible Section */}
          {!search.trim() && entriesToday.length > 0 && (
            <div>
              <Button
                variant="ghost"
                className="w-full flex items-center justify-between mb-2 px-0 hover:bg-transparent"
                onClick={() => setShowEntriesToday(!showEntriesToday)}
              >
                <h3 className="text-xs font-bold text-purple-400 uppercase tracking-wider flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  INGRESADOS HOY ({entriesToday.length})
                </h3>
                <ChevronRight className={`w-4 h-4 text-purple-400 transition-transform ${showEntriesToday ? 'rotate-90' : ''}`} />
              </Button>
              
              {showEntriesToday && (
                <div className="space-y-2 animate-in slide-in-from-top-2 duration-200">
                  {entriesToday.slice(0, 10).map((entry) => (
                    <div 
                      key={entry.id}
                      className="p-3 rounded-lg bg-purple-500/5 border border-purple-500/20"
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-medium text-sm">{entry.visitor_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {entry.resident_name && `→ ${entry.resident_name}`}
                            {entry.resident_apartment && ` (${entry.resident_apartment})`}
                          </p>
                        </div>
                        <div className="text-right">
                          <Badge variant="outline" className="text-purple-400 border-purple-400/30 text-xs">
                            {new Date(entry.entry_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                          </Badge>
                          {entry.is_authorized && (
                            <CheckCircle className="w-3 h-3 text-green-400 mt-1 ml-auto" />
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                  {entriesToday.length > 10 && (
                    <p className="text-xs text-center text-muted-foreground py-2">
                      ... y {entriesToday.length - 10} más
                    </p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Visitors Inside */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-bold text-green-400 uppercase tracking-wider flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                DENTRO DEL CONDOMINIO ({visitorsInside.length})
              </h3>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => fetchData(true)}
                disabled={isRefreshing}
                data-testid="refresh-inside-btn"
              >
                <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              </Button>
            </div>
            
            {visitorsInside.length > 0 ? (
              <div className="space-y-2">
                {visitorsInside.map((entry) => (
                  <VisitorInsideCard 
                    key={entry.id}
                    entry={entry}
                    onCheckOut={handleCheckOut}
                    isProcessing={processingCheckout === entry.id}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground bg-[#0F111A] rounded-xl border border-dashed border-[#1E293B]">
                <Users className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No hay visitantes dentro</p>
              </div>
            )}
          </div>
        </div>
      </ScrollArea>

      {/* Check-in Dialog */}
      <ManualCheckInDialog
        open={showCheckInDialog}
        onClose={() => { setShowCheckInDialog(false); setSelectedAuth(null); }}
        authorization={selectedAuth}
        onSubmit={handleCheckInSubmit}
      />
    </div>
  );
};

export default VisitorCheckInGuard;
