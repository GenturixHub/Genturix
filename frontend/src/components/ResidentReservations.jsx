/**
 * GENTURIX - Resident Reservations Component
 * 
 * Allows residents to:
 * - View available common areas
 * - Check availability
 * - Create reservations
 * - Cancel/edit reservations
 * - See status (pending/approved/rejected)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Textarea } from './ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { toast } from 'sonner';
import api from '../services/api';
import {
  Calendar,
  Clock,
  Users,
  Plus,
  CheckCircle,
  XCircle,
  Loader2,
  Waves,
  Dumbbell,
  UtensilsCrossed,
  Building2,
  Tent,
  MoreHorizontal,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Info
} from 'lucide-react';

// ============================================
// CONFIGURATION
// ============================================
const AREA_ICONS = {
  pool: Waves,
  gym: Dumbbell,
  bbq: UtensilsCrossed,
  salon: Building2,
  tennis: Tent,
  cinema: Building2,
  playground: Tent,
  other: MoreHorizontal
};

const AREA_LABELS = {
  pool: 'Piscina',
  gym: 'Gimnasio',
  bbq: 'Área BBQ',
  salon: 'Salón de Eventos',
  tennis: 'Cancha de Tenis',
  cinema: 'Cine',
  playground: 'Área Infantil',
  other: 'Otro'
};

const STATUS_CONFIG = {
  pending: { label: 'Pendiente', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', icon: Clock },
  approved: { label: 'Aprobada', color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: CheckCircle },
  rejected: { label: 'Rechazada', color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: XCircle },
  cancelled: { label: 'Cancelada', color: 'bg-gray-500/20 text-gray-400 border-gray-500/30', icon: XCircle }
};

const DAYS_OF_WEEK = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
const DAYS_SHORT = { 'Lunes': 'L', 'Martes': 'M', 'Miércoles': 'X', 'Jueves': 'J', 'Viernes': 'V', 'Sábado': 'S', 'Domingo': 'D' };

// ============================================
// AREA CARD FOR RESIDENT
// ============================================
const AreaCard = ({ area, onReserve }) => {
  const AreaIcon = AREA_ICONS[area.area_type] || MoreHorizontal;
  
  return (
    <Card className="bg-[#0F111A] border-[#1E293B] hover:border-primary/30 transition-all">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-primary/10 flex-shrink-0">
            <AreaIcon className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-white truncate">{area.name}</h3>
            <p className="text-xs text-muted-foreground">{AREA_LABELS[area.area_type] || 'Área'}</p>
            
            <div className="flex flex-wrap gap-1.5 mt-2">
              <Badge variant="outline" className="text-[10px] h-5">
                <Users className="w-3 h-3 mr-1" />
                {area.capacity} personas
              </Badge>
              <Badge variant="outline" className="text-[10px] h-5">
                <Clock className="w-3 h-3 mr-1" />
                {area.available_from}-{area.available_until}
              </Badge>
            </div>
            
            {area.requires_approval && (
              <Badge className="bg-yellow-500/20 text-yellow-400 text-[10px] mt-2">
                Requiere aprobación
              </Badge>
            )}
            
            {/* Allowed days */}
            <div className="flex gap-0.5 mt-2">
              {DAYS_OF_WEEK.map(day => {
                const isAllowed = (area.allowed_days || DAYS_OF_WEEK).includes(day);
                return (
                  <span
                    key={day}
                    className={`w-5 h-5 rounded text-[9px] flex items-center justify-center ${
                      isAllowed ? 'bg-primary/20 text-primary' : 'bg-gray-800 text-gray-600'
                    }`}
                    title={day}
                  >
                    {DAYS_SHORT[day]}
                  </span>
                );
              })}
            </div>
          </div>
        </div>
        
        <Button 
          size="sm" 
          onClick={() => onReserve(area)} 
          className="w-full mt-3"
          data-testid={`reserve-area-${area.id}`}
        >
          <Calendar className="w-3.5 h-3.5 mr-1.5" />
          Reservar
        </Button>
      </CardContent>
    </Card>
  );
};

// ============================================
// MY RESERVATION CARD
// ============================================
const MyReservationCard = ({ reservation, onCancel }) => {
  const statusConfig = STATUS_CONFIG[reservation.status] || STATUS_CONFIG.pending;
  const StatusIcon = statusConfig.icon;
  const AreaIcon = AREA_ICONS[reservation.area_type] || MoreHorizontal;
  const canCancel = reservation.status === 'pending';
  
  return (
    <Card className={`bg-[#0F111A] border-[#1E293B] ${canCancel ? '' : 'opacity-75'}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="p-2 rounded-lg bg-primary/10 flex-shrink-0">
              <AreaIcon className="w-4 h-4 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-white text-sm truncate">{reservation.area_name}</p>
              <div className="flex flex-wrap items-center gap-2 mt-1 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <CalendarDays className="w-3 h-3" />
                  {reservation.date}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {reservation.start_time}-{reservation.end_time}
                </span>
              </div>
              {reservation.purpose && (
                <p className="text-xs text-muted-foreground mt-1 truncate">{reservation.purpose}</p>
              )}
            </div>
          </div>
          <Badge className={`${statusConfig.color} flex-shrink-0 text-[10px]`}>
            <StatusIcon className="w-3 h-3 mr-1" />
            {statusConfig.label}
          </Badge>
        </div>
        
        {canCancel && (
          <Button
            size="sm"
            variant="outline"
            className="w-full mt-3 text-red-400 border-red-500/30 hover:bg-red-500/10"
            onClick={() => onCancel(reservation)}
            data-testid={`cancel-reservation-${reservation.id}`}
          >
            <XCircle className="w-3 h-3 mr-1" />
            Cancelar Reservación
          </Button>
        )}
      </CardContent>
    </Card>
  );
};

// ============================================
// RESERVATION FORM DIALOG
// ============================================
const ReservationFormDialog = ({ open, onClose, area, onSave }) => {
  const [form, setForm] = useState({
    date: '',
    start_time: '',
    end_time: '',
    guests_count: 1,
    purpose: ''
  });
  const [availability, setAvailability] = useState(null);
  const [loadingAvailability, setLoadingAvailability] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  // Reset form when area changes
  useEffect(() => {
    if (area) {
      const today = new Date().toISOString().split('T')[0];
      setForm({
        date: today,
        start_time: area.available_from || '08:00',
        end_time: '',
        guests_count: 1,
        purpose: ''
      });
      setAvailability(null);
    }
  }, [area, open]);
  
  // Load availability when date changes
  useEffect(() => {
    const loadAvailability = async () => {
      if (!area?.id || !form.date) return;
      
      setLoadingAvailability(true);
      try {
        const data = await api.getReservationAvailability(area.id, form.date);
        setAvailability(data);
      } catch (error) {
        console.error('Error loading availability:', error);
      } finally {
        setLoadingAvailability(false);
      }
    };
    
    loadAvailability();
  }, [area?.id, form.date]);
  
  // Calculate end time based on max hours
  useEffect(() => {
    if (form.start_time && area?.max_hours_per_reservation) {
      const [hours, mins] = form.start_time.split(':').map(Number);
      const endHours = hours + (area.max_hours_per_reservation || 2);
      const endTime = `${String(Math.min(endHours, 23)).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
      setForm(prev => ({ ...prev, end_time: endTime }));
    }
  }, [form.start_time, area?.max_hours_per_reservation]);
  
  const handleSave = async () => {
    if (!form.date) {
      toast.error('Selecciona una fecha');
      return;
    }
    if (!form.start_time) {
      toast.error('Selecciona hora de inicio');
      return;
    }
    
    setIsSaving(true);
    try {
      await onSave({
        area_id: area.id,
        date: form.date,
        start_time: form.start_time,
        end_time: form.end_time || form.start_time,
        guests_count: form.guests_count,
        purpose: form.purpose
      });
      onClose();
    } catch (error) {
      toast.error(error.message || 'Error al crear reservación');
    } finally {
      setIsSaving(false);
    }
  };
  
  if (!area) return null;
  
  const AreaIcon = AREA_ICONS[area.area_type] || MoreHorizontal;
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AreaIcon className="w-5 h-5 text-primary" />
            Reservar {area.name}
          </DialogTitle>
          <DialogDescription>
            {area.requires_approval ? 'Esta área requiere aprobación del administrador' : 'Tu reservación será confirmada automáticamente'}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-2">
          {/* Date Selection */}
          <div className="space-y-1.5">
            <Label className="text-xs">Fecha de Reservación</Label>
            <Input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              min={new Date().toISOString().split('T')[0]}
              className="bg-[#0A0A0F] border-[#1E293B] h-10"
              data-testid="reservation-date"
            />
          </div>
          
          {/* Availability Info */}
          {loadingAvailability ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground p-3 bg-[#0A0A0F] rounded-lg">
              <Loader2 className="w-3 h-3 animate-spin" />
              Verificando disponibilidad...
            </div>
          ) : availability && (
            <div className={`p-3 rounded-lg text-xs ${
              availability.is_available 
                ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                : 'bg-red-500/10 border border-red-500/30 text-red-400'
            }`}>
              <div className="flex items-center gap-2">
                {availability.is_available ? (
                  <>
                    <CheckCircle className="w-3.5 h-3.5" />
                    <span>{availability.slots_remaining} espacios disponibles</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>No hay disponibilidad para esta fecha</span>
                  </>
                )}
              </div>
              {availability.reserved_slots?.length > 0 && (
                <div className="mt-2 text-muted-foreground">
                  Horarios ocupados: {availability.reserved_slots.map(s => `${s.start_time}-${s.end_time}`).join(', ')}
                </div>
              )}
            </div>
          )}
          
          {/* Time Selection */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Hora Inicio</Label>
              <Input
                type="time"
                value={form.start_time}
                onChange={(e) => setForm({ ...form, start_time: e.target.value })}
                min={area.available_from}
                max={area.available_until}
                className="bg-[#0A0A0F] border-[#1E293B] h-10"
                data-testid="reservation-start-time"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Hora Fin</Label>
              <Input
                type="time"
                value={form.end_time}
                onChange={(e) => setForm({ ...form, end_time: e.target.value })}
                min={form.start_time}
                max={area.available_until}
                className="bg-[#0A0A0F] border-[#1E293B] h-10"
                data-testid="reservation-end-time"
              />
            </div>
          </div>
          
          {/* Guests */}
          <div className="space-y-1.5">
            <Label className="text-xs">Número de Invitados</Label>
            <Input
              type="number"
              value={form.guests_count}
              onChange={(e) => setForm({ ...form, guests_count: Math.min(parseInt(e.target.value) || 1, area.capacity) })}
              min={1}
              max={area.capacity}
              className="bg-[#0A0A0F] border-[#1E293B] h-10"
              data-testid="reservation-guests"
            />
            <p className="text-[10px] text-muted-foreground">Máximo: {area.capacity} personas</p>
          </div>
          
          {/* Purpose */}
          <div className="space-y-1.5">
            <Label className="text-xs">Motivo (opcional)</Label>
            <Textarea
              value={form.purpose}
              onChange={(e) => setForm({ ...form, purpose: e.target.value })}
              placeholder="Ej: Reunión familiar, cumpleaños..."
              className="bg-[#0A0A0F] border-[#1E293B] h-20 resize-none"
              data-testid="reservation-purpose"
            />
          </div>
        </div>
        
        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button variant="outline" onClick={onClose} className="w-full sm:w-auto">
            Cancelar
          </Button>
          <Button 
            onClick={handleSave} 
            disabled={isSaving || !availability?.is_available}
            className="w-full sm:w-auto"
            data-testid="submit-reservation"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creando...
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4 mr-2" />
                Crear Reservación
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// MAIN COMPONENT
// ============================================
const ResidentReservations = () => {
  const [activeTab, setActiveTab] = useState('areas');
  const [areas, setAreas] = useState([]);
  const [myReservations, setMyReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedArea, setSelectedArea] = useState(null);
  const [showReservationForm, setShowReservationForm] = useState(false);
  
  // Load data
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [areasData, reservationsData] = await Promise.all([
        api.getReservationAreas(),
        api.getReservations()
      ]);
      setAreas(areasData.filter(a => a.is_active !== false));
      setMyReservations(reservationsData);
    } catch (error) {
      console.error('Error loading reservations data:', error);
      // Silently fail if module is not enabled or no data
      // Only show error for unexpected failures
      if (!error.message?.includes('módulo') && !error.message?.includes('No encontrado') && error.status !== 404) {
        // Don't show toast for expected "no data" scenarios
        if (error.status >= 500) {
          toast.error('Error al cargar datos de reservaciones');
        }
      }
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => {
    loadData();
  }, [loadData]);
  
  const handleReserve = (area) => {
    setSelectedArea(area);
    setShowReservationForm(true);
  };
  
  const handleCreateReservation = async (reservationData) => {
    await api.createReservation(reservationData);
    toast.success('Reservación creada exitosamente');
    loadData();
  };
  
  const handleCancelReservation = async (reservation) => {
    try {
      await api.updateReservation(reservation.id, { status: 'cancelled' });
      toast.success('Reservación cancelada');
      loadData();
    } catch (error) {
      toast.error(error.message || 'Error al cancelar');
    }
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }
  
  const pendingReservations = myReservations.filter(r => r.status === 'pending');
  const approvedReservations = myReservations.filter(r => r.status === 'approved');
  const pastReservations = myReservations.filter(r => ['rejected', 'cancelled'].includes(r.status));
  
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-[#1E293B]">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Calendar className="w-5 h-5 text-primary" />
          Reservaciones
        </h2>
        <p className="text-xs text-muted-foreground mt-1">
          Reserva áreas comunes del condominio
        </p>
      </div>
      
      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="grid grid-cols-2 mx-4 mt-3 bg-[#0A0A0F]">
          <TabsTrigger value="areas" className="text-xs" data-testid="tab-areas">
            <Building2 className="w-3.5 h-3.5 mr-1.5" />
            Áreas
          </TabsTrigger>
          <TabsTrigger value="mine" className="text-xs" data-testid="tab-my-reservations">
            <CalendarDays className="w-3.5 h-3.5 mr-1.5" />
            Mis Reservas
            {pendingReservations.length > 0 && (
              <Badge className="ml-1.5 bg-yellow-500/20 text-yellow-400 h-4 px-1.5 text-[10px]">
                {pendingReservations.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>
        
        {/* Areas Tab */}
        <TabsContent value="areas" className="flex-1 mt-0">
          <ScrollArea className="h-[calc(100vh-280px)]">
            <div className="p-4 space-y-3">
              {areas.length > 0 ? (
                areas.map(area => (
                  <AreaCard 
                    key={area.id} 
                    area={area} 
                    onReserve={handleReserve}
                  />
                ))
              ) : (
                <div className="text-center py-12">
                  <Building2 className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-30" />
                  <p className="text-sm text-muted-foreground">
                    No hay áreas comunes disponibles
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    El administrador debe habilitar el módulo de reservaciones
                  </p>
                </div>
              )}
            </div>
          </ScrollArea>
        </TabsContent>
        
        {/* My Reservations Tab */}
        <TabsContent value="mine" className="flex-1 mt-0">
          <ScrollArea className="h-[calc(100vh-280px)]">
            <div className="p-4 space-y-4">
              {/* Pending */}
              {pendingReservations.length > 0 && (
                <div>
                  <h3 className="text-xs font-medium text-yellow-400 mb-2 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" />
                    Pendientes ({pendingReservations.length})
                  </h3>
                  <div className="space-y-2">
                    {pendingReservations.map(res => (
                      <MyReservationCard 
                        key={res.id} 
                        reservation={res}
                        onCancel={handleCancelReservation}
                      />
                    ))}
                  </div>
                </div>
              )}
              
              {/* Approved */}
              {approvedReservations.length > 0 && (
                <div>
                  <h3 className="text-xs font-medium text-green-400 mb-2 flex items-center gap-1.5">
                    <CheckCircle className="w-3.5 h-3.5" />
                    Aprobadas ({approvedReservations.length})
                  </h3>
                  <div className="space-y-2">
                    {approvedReservations.map(res => (
                      <MyReservationCard 
                        key={res.id} 
                        reservation={res}
                        onCancel={handleCancelReservation}
                      />
                    ))}
                  </div>
                </div>
              )}
              
              {/* Past/Cancelled */}
              {pastReservations.length > 0 && (
                <div>
                  <h3 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1.5">
                    <XCircle className="w-3.5 h-3.5" />
                    Pasadas/Canceladas ({pastReservations.length})
                  </h3>
                  <div className="space-y-2">
                    {pastReservations.slice(0, 5).map(res => (
                      <MyReservationCard 
                        key={res.id} 
                        reservation={res}
                        onCancel={() => {}}
                      />
                    ))}
                  </div>
                </div>
              )}
              
              {/* Empty State */}
              {myReservations.length === 0 && (
                <div className="text-center py-12">
                  <CalendarDays className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-30" />
                  <p className="text-sm text-muted-foreground">
                    No tienes reservaciones
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Ve a "Áreas" para hacer tu primera reservación
                  </p>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="mt-4"
                    onClick={() => setActiveTab('areas')}
                  >
                    <Plus className="w-3.5 h-3.5 mr-1.5" />
                    Ver Áreas Disponibles
                  </Button>
                </div>
              )}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
      
      {/* Reservation Form Dialog */}
      <ReservationFormDialog
        open={showReservationForm}
        onClose={() => {
          setShowReservationForm(false);
          setSelectedArea(null);
        }}
        area={selectedArea}
        onSave={handleCreateReservation}
      />
    </div>
  );
};

export default ResidentReservations;
