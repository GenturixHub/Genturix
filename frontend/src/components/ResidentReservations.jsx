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
import { useTranslation } from 'react-i18next';
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
  Info,
  FileText,
  ScrollText
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

// Days mapping for translation keys
const DAYS_MAP = {
  'Lunes': 'monday',
  'Martes': 'tuesday',
  'Miércoles': 'wednesday',
  'Jueves': 'thursday',
  'Viernes': 'friday',
  'Sábado': 'saturday',
  'Domingo': 'sunday'
};

const DAYS_OF_WEEK_KEYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];
const DAYS_OF_WEEK = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

// ============================================
// AREA CARD FOR RESIDENT
// ============================================
// Behavior colors for display
const BEHAVIOR_COLORS = {
  exclusive: 'bg-cyan-500/20 text-cyan-400',
  capacity: 'bg-blue-500/20 text-blue-400',
  slot_based: 'bg-teal-500/20 text-teal-400',
  free_access: 'bg-green-500/20 text-green-400'
};

// Status colors for display
const STATUS_COLORS = {
  pending: { color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', icon: Clock },
  approved: { color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: CheckCircle },
  rejected: { color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: XCircle },
  cancelled: { color: 'bg-gray-500/20 text-gray-400 border-gray-500/30', icon: XCircle }
};

const AreaCard = ({ area, onReserve }) => {
  const { t } = useTranslation();
  const AreaIcon = AREA_ICONS[area.area_type] || MoreHorizontal;
  const behavior = area.reservation_behavior || 'exclusive';
  const behaviorColor = BEHAVIOR_COLORS[behavior] || BEHAVIOR_COLORS.exclusive;
  const behaviorKey = behavior === 'slot_based' ? 'slotBased' : behavior === 'free_access' ? 'freeAccess' : behavior;
  const [showRules, setShowRules] = useState(false);
  
  // Don't render reserve button for FREE_ACCESS areas
  const isFreeAccess = behavior === 'free_access';
  
  // Check if area has rules
  const hasRules = area.rules && area.rules.trim().length > 0;
  
  return (
    <Card className="bg-[#0F111A] border-[#1E293B] hover:border-primary/30 transition-all">
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-primary/10 flex-shrink-0">
            <AreaIcon className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-white truncate">{area.name}</h3>
            <p className="text-xs text-muted-foreground">{t(`reservations.areaTypes.${area.area_type}`, area.area_type)}</p>
            
            <div className="flex flex-wrap gap-1.5 mt-2">
              <Badge variant="outline" className="text-[10px] h-5">
                <Users className="w-3 h-3 mr-1" />
                {behavior === 'capacity' && area.max_capacity_per_slot 
                  ? t('reservations.perHour', { count: area.max_capacity_per_slot })
                  : t('reservations.peopleCount', { count: area.capacity })
                }
              </Badge>
              <Badge variant="outline" className="text-[10px] h-5">
                <Clock className="w-3 h-3 mr-1" />
                {area.available_from}-{area.available_until}
              </Badge>
              {/* Show behavior badge */}
              <Badge className={`${behaviorColor} text-[10px] h-5`}>
                {t(`reservations.behaviorLabels.${behaviorKey}`)}
              </Badge>
            </div>
            
            {area.requires_approval && (
              <Badge className="bg-yellow-500/20 text-yellow-400 text-[10px] mt-2">
                {t('reservations.requiresApproval')}
              </Badge>
            )}
            
            {/* Allowed days */}
            <div className="flex gap-0.5 mt-2">
              {DAYS_OF_WEEK.map((day, idx) => {
                const isAllowed = (area.allowed_days || DAYS_OF_WEEK).includes(day);
                const dayKey = DAYS_OF_WEEK_KEYS[idx];
                return (
                  <span
                    key={day}
                    className={`w-5 h-5 rounded text-[9px] flex items-center justify-center ${
                      isAllowed ? 'bg-primary/20 text-primary' : 'bg-gray-800 text-gray-600'
                    }`}
                    title={t(`reservations.daysFull.${dayKey}`)}
                  >
                    {t(`reservations.daysShort.${dayKey}`)}
                  </span>
                );
              })}
            </div>
          </div>
        </div>
        
        {/* Rules Section */}
        {hasRules && (
          <div className="mt-3">
            <button
              onClick={() => setShowRules(!showRules)}
              className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors w-full"
              data-testid={`toggle-rules-${area.id}`}
            >
              <ScrollText className="w-3.5 h-3.5" />
              <span className="font-medium">{t('reservations.areaRules')}</span>
              <ChevronRight className={`w-3.5 h-3.5 ml-auto transition-transform ${showRules ? 'rotate-90' : ''}`} />
            </button>
            
            {showRules && (
              <div className="mt-2 p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-xs text-blue-200/90">
                <div className="max-h-24 overflow-y-auto custom-scrollbar">
                  <p className="whitespace-pre-wrap leading-relaxed">{area.rules}</p>
                </div>
              </div>
            )}
          </div>
        )}
        
        {isFreeAccess ? (
          <div className="mt-3 p-2 rounded bg-green-500/10 border border-green-500/20 text-center">
            <span className="text-xs text-green-400">{t('reservations.freeAccessNoReservation')}</span>
          </div>
        ) : (
          <Button 
            size="sm" 
            onClick={() => onReserve(area)} 
            className="w-full mt-3"
            data-testid={`reserve-area-${area.id}`}
          >
            <Calendar className="w-3.5 h-3.5 mr-1.5" />
            {t('reservations.reserve')}
          </Button>
        )}
      </CardContent>
    </Card>
  );
};

// ============================================
// MY RESERVATION CARD
// ============================================
const MyReservationCard = ({ reservation, onCancel }) => {
  const { t } = useTranslation();
  const statusColors = STATUS_COLORS[reservation.status] || STATUS_COLORS.pending;
  const StatusIcon = statusColors.icon;
  const AreaIcon = AREA_ICONS[reservation.area_type] || MoreHorizontal;
  
  // Check if cancellation is allowed based on business rules
  const canCancel = (() => {
    // Can only cancel pending or approved reservations
    if (!['pending', 'approved'].includes(reservation.status)) return false;
    
    // Check if reservation has started
    try {
      const now = new Date();
      const [year, month, day] = reservation.date.split('-').map(Number);
      const [startHour, startMin] = reservation.start_time.split(':').map(Number);
      const reservationStart = new Date(year, month - 1, day, startHour, startMin);
      
      // Cannot cancel if already started
      if (now >= reservationStart) return false;
    } catch (e) {
      // If date parsing fails, allow cancellation (fail-safe)
      return true;
    }
    
    return true;
  })();
  
  // Check if reservation is in progress or past
  const isPastOrInProgress = (() => {
    try {
      const now = new Date();
      const [year, month, day] = reservation.date.split('-').map(Number);
      const [startHour, startMin] = reservation.start_time.split(':').map(Number);
      const reservationStart = new Date(year, month - 1, day, startHour, startMin);
      return now >= reservationStart;
    } catch (e) {
      return false;
    }
  })();
  
  return (
    <Card className={`bg-[#0F111A] border-[#1E293B] ${!canCancel && reservation.status !== 'cancelled' && reservation.status !== 'rejected' ? 'opacity-85' : ''}`}>
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
                {reservation.guests_count > 1 && (
                  <span className="flex items-center gap-1">
                    <Users className="w-3 h-3" />
                    {reservation.guests_count}
                  </span>
                )}
              </div>
              {reservation.purpose && (
                <p className="text-xs text-muted-foreground mt-1 truncate">{reservation.purpose}</p>
              )}
              {/* Show if in progress */}
              {isPastOrInProgress && reservation.status === 'approved' && (
                <p className="text-xs text-yellow-400 mt-1">{t('reservations.inProgressOrFinished')}</p>
              )}
              {/* Show cancellation reason if cancelled by admin */}
              {reservation.status === 'cancelled' && reservation.cancellation_reason && (
                <p className="text-xs text-red-400 mt-1">{t('reservations.reason')}: {reservation.cancellation_reason}</p>
              )}
            </div>
          </div>
          <Badge className={`${statusColors.color} flex-shrink-0 text-[10px]`}>
            <StatusIcon className="w-3 h-3 mr-1" />
            {t(`reservations.statusLabels.${reservation.status}`)}
          </Badge>
        </div>
        
        {canCancel && (
          <Button
            size="sm"
            variant="outline"
            className="w-full mt-3 text-red-400 border-red-500/30 hover:bg-red-500/10 active:scale-[0.98] transition-transform"
            onClick={() => onCancel(reservation)}
            data-testid={`cancel-reservation-${reservation.id}`}
          >
            <XCircle className="w-3.5 h-3.5 mr-1.5" />
            {t('reservations.cancelReservation')}
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
  const { t } = useTranslation();
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
  const [selectedSlotIndex, setSelectedSlotIndex] = useState(null);
  
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
      setSelectedSlotIndex(null);
    }
  }, [area, open]);
  
  // Load availability when date changes - Use smart availability for behavior-based logic
  useEffect(() => {
    const loadAvailability = async () => {
      if (!area?.id || !form.date) return;
      
      setLoadingAvailability(true);
      setSelectedSlotIndex(null); // Reset slot selection when date changes
      try {
        // Use smart availability which handles different area behaviors
        const data = await api.getSmartAvailability(area.id, form.date);
        setAvailability(data);
      } catch (error) {
        console.error('Error loading availability:', error);
        // Fallback to legacy endpoint if smart availability fails
        try {
          const legacyData = await api.getReservationAvailability(area.id, form.date);
          setAvailability(legacyData);
        } catch (e) {
          console.error('Error loading legacy availability:', e);
        }
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
  
  // Handle time slot click - auto-fill start and end times (supports new smart availability)
  const handleSlotClick = (slot, slotIndex) => {
    // Support both old status field and new available field
    const isSlotAvailable = slot.available !== undefined ? slot.available : slot.status === 'available';
    if (!isSlotAvailable) return;
    
    const maxHours = area?.max_hours_per_reservation || area?.max_duration_hours || 2;
    const reservationMode = area?.reservation_mode || 'por_hora';
    const reservationBehavior = availability?.reservation_behavior || 'exclusive';
    const closingTime = area?.closing_time || area?.available_until || '22:00';
    
    // Support both old (start_time) and new (start) field names
    const slotStart = slot.start || slot.start_time || '';
    const slotEnd = slot.end || slot.end_time || '';
    const startTime = slotStart.slice(0, 5); // "09:00"
    const [startHour, startMin] = startTime.split(':').map(Number);
    
    let endTime;
    
    // For SLOT_BASED or BY_HOUR areas, use the slot's exact end time
    if (reservationBehavior === 'slot_based' || reservationMode === 'por_hora') {
      endTime = slotEnd.slice(0, 5);
    } else if (reservationMode === 'bloque') {
      // Block mode: Select consecutive available slots until occupied or closing
      let endHour = startHour + 1;
      const slots = availability?.time_slots || [];
      
      for (let i = slotIndex + 1; i < slots.length; i++) {
        const nextSlotAvailable = slots[i].available !== undefined ? slots[i].available : slots[i].status === 'available';
        if (nextSlotAvailable) {
          const nextSlotStart = slots[i].start || slots[i].start_time || '';
          const nextSlotHour = parseInt(nextSlotStart.slice(0, 2));
          if (nextSlotHour >= parseInt(closingTime.split(':')[0])) break;
          endHour = nextSlotHour + 1;
        } else {
          break;
        }
      }
      
      endTime = `${String(Math.min(endHour, parseInt(closingTime.split(':')[0]))).padStart(2, '0')}:${String(startMin).padStart(2, '0')}`;
    } else {
      // Per-hour/flexible mode: Use max_hours_per_reservation
      const endHour = Math.min(startHour + maxHours, parseInt(closingTime.split(':')[0]));
      endTime = `${String(endHour).padStart(2, '0')}:${String(startMin).padStart(2, '0')}`;
    }
    
    setForm(prev => ({
      ...prev,
      start_time: startTime,
      end_time: endTime
    }));
    
    setSelectedSlotIndex(slotIndex);
    
    // Show capacity info for CAPACITY type areas
    if (reservationBehavior === 'capacity' && slot.remaining_slots !== undefined) {
      toast.success(`Horario: ${startTime} - ${endTime} (${slot.remaining_slots} cupos disponibles)`, { duration: 2000 });
    } else {
      toast.success(`Horario seleccionado: ${startTime} - ${endTime}`, { duration: 2000 });
    }
  };
  
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
      const errorMessage = error?.message || (typeof error === 'string' ? error : 'Error al crear reservación');
      toast.error(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };
  
  if (!area) return null;
  
  const AreaIcon = AREA_ICONS[area.area_type] || MoreHorizontal;
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center gap-2">
            <AreaIcon className="w-5 h-5 text-primary" />
            Reservar {area.name}
          </DialogTitle>
          <DialogDescription>
            {area.requires_approval ? 'Esta área requiere aprobación del administrador' : 'Tu reservación será confirmada automáticamente'}
          </DialogDescription>
        </DialogHeader>
        
        <div className="flex-1 overflow-y-auto min-h-0 pr-2 -mr-2">
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
            {/* Show allowed days info */}
            {area.allowed_days && area.allowed_days.length < 7 && (
              <div className="flex items-start gap-2 text-xs text-blue-400 mt-1">
                <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
                <span>Disponible solo: {area.allowed_days.join(', ')}</span>
              </div>
            )}
          </div>
          
          {/* Availability Info */}
          {loadingAvailability ? (
            <div className="flex items-center gap-2 text-xs text-muted-foreground p-3 bg-[#0A0A0F] rounded-lg">
              <Loader2 className="w-3 h-3 animate-spin" />
              Verificando disponibilidad...
            </div>
          ) : availability && (
            <div className="space-y-3">
              {/* Main availability status */}
              <div className={`p-3 rounded-lg text-xs ${
                availability.is_available 
                  ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                  : 'bg-red-500/10 border border-red-500/30 text-red-400'
              }`}>
                <div className="flex items-center gap-2">
                  {availability.is_available ? (
                    <>
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>
                        {availability.reservation_behavior === 'capacity' 
                          ? `${availability.available_slots_count} horarios disponibles`
                          : `${availability.available_slots_count || availability.slots_remaining} espacios disponibles`
                        }
                      </span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-3.5 h-3.5" />
                      <span>{availability.message || 'No hay disponibilidad para esta fecha'}</span>
                    </>
                  )}
                </div>
                {/* Show user limit warning */}
                {availability.user_can_reserve === false && (
                  <div className="mt-1 text-[10px] opacity-80">
                    Has alcanzado el límite de {availability.max_reservations_per_user_per_day} reservación(es) por día
                  </div>
                )}
                {!availability.is_day_allowed && (
                  <div className="mt-1 text-[10px] opacity-80">
                    {availability.day_name && `${availability.day_name} no está habilitado para esta área`}
                  </div>
                )}
              </div>
              
              {/* Visual time slots - CLICKABLE with CAPACITY support */}
              {availability.is_day_allowed && availability.time_slots?.length > 0 && (
                <div className="bg-[#0A0A0F] rounded-lg p-3 border border-[#1E293B]">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground font-medium">Selecciona un horario</span>
                    </div>
                    <span className="text-[10px] text-primary animate-pulse">← Clic para seleccionar</span>
                  </div>
                  <div className="grid grid-cols-4 gap-1.5">
                    {availability.time_slots.map((slot, idx) => {
                      const isSelected = selectedSlotIndex === idx;
                      // Support both old (status) and new (available) formats
                      const isAvailable = slot.available !== undefined ? slot.available : slot.status === 'available';
                      const slotStatus = slot.status || (isAvailable ? 'available' : 'occupied');
                      const slotTime = (slot.start || slot.start_time || '').slice(0, 5);
                      
                      // Determine slot color based on status (including new 'limited' and 'full' states)
                      let slotClasses;
                      if (isSelected) {
                        slotClasses = 'bg-primary text-primary-foreground border-2 border-primary ring-2 ring-primary/30 scale-105';
                      } else if (slotStatus === 'limited') {
                        // Yellow for limited capacity
                        slotClasses = 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 hover:bg-yellow-500/30 cursor-pointer';
                      } else if (isAvailable) {
                        slotClasses = 'bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30 hover:scale-102 cursor-pointer';
                      } else {
                        slotClasses = 'bg-red-500/20 text-red-400 border border-red-500/30 cursor-not-allowed opacity-60';
                      }
                      
                      return (
                        <button 
                          key={idx}
                          type="button"
                          onClick={() => handleSlotClick(slot, idx)}
                          disabled={!isAvailable}
                          className={`px-2 py-2 rounded text-[11px] text-center transition-all font-medium ${slotClasses}`}
                          title={
                            isAvailable 
                              ? (slot.remaining_slots !== undefined 
                                  ? `${slotTime} - ${slot.remaining_slots}/${slot.total_capacity} cupos`
                                  : 'Clic para seleccionar este horario')
                              : (slotStatus === 'full' ? 'Sin cupos disponibles' : 'Horario ocupado')
                          }
                          data-testid={`time-slot-${idx}`}
                        >
                          <span>{slotTime}</span>
                          {/* Show remaining slots for CAPACITY type */}
                          {slot.remaining_slots !== undefined && slot.total_capacity > 1 && (
                            <span className="block text-[9px] opacity-75 mt-0.5">
                              {slot.remaining_slots}/{slot.total_capacity}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                  <div className="flex items-center justify-between mt-3 text-[10px] text-muted-foreground">
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-1">
                        <div className="w-2 h-2 rounded-sm bg-green-500/40" />
                        <span>Disponible</span>
                      </div>
                      {/* Show yellow legend for capacity areas */}
                      {availability.reservation_behavior === 'capacity' && (
                        <div className="flex items-center gap-1">
                          <div className="w-2 h-2 rounded-sm bg-yellow-500/40" />
                          <span>Pocos cupos</span>
                        </div>
                      )}
                      <div className="flex items-center gap-1">
                        <div className="w-2 h-2 rounded-sm bg-red-500/40" />
                        <span>{availability.reservation_behavior === 'capacity' ? 'Lleno' : 'Ocupado'}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <div className="w-2 h-2 rounded-sm bg-primary" />
                        <span>Seleccionado</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* Time Selection - READ ONLY when slot is selected to avoid human errors */}
          {selectedSlotIndex !== null ? (
            // Slot selected - show read-only summary
            <div className="p-3 rounded-lg bg-primary/10 border border-primary/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-primary" />
                  <span className="text-sm font-medium text-primary">Horario seleccionado</span>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => setSelectedSlotIndex(null)}
                  className="text-xs h-7 text-muted-foreground hover:text-white"
                >
                  Cambiar
                </Button>
              </div>
              <p className="text-lg font-bold text-white mt-1">
                {form.start_time} - {form.end_time}
              </p>
              {availability?.reservation_behavior === 'capacity' && (
                <p className="text-xs text-muted-foreground mt-1">
                  Cupos disponibles en este horario
                </p>
              )}
            </div>
          ) : (
            // No slot selected - show manual inputs (fallback)
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-xs text-yellow-400 mb-2">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Selecciona un horario arriba o ingresa manualmente:</span>
              </div>
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
            </div>
          )}
          
          {/* Guests - Only show for CAPACITY behavior or when area capacity > 1 */}
          {(availability?.reservation_behavior === 'capacity' || (!availability?.reservation_behavior && area.capacity > 1)) && (
            <div className="space-y-1.5">
              <Label className="text-xs">Número de Personas</Label>
              <div className="flex items-center gap-3">
                <Input
                  type="number"
                  value={form.guests_count}
                  onChange={(e) => setForm({ ...form, guests_count: Math.max(1, Math.min(parseInt(e.target.value) || 1, 
                    availability?.reservation_behavior === 'capacity' 
                      ? (availability?.max_capacity_per_slot || area.capacity)
                      : area.capacity
                  )) })}
                  min={1}
                  max={availability?.reservation_behavior === 'capacity' 
                    ? (availability?.max_capacity_per_slot || area.capacity)
                    : area.capacity}
                  className="bg-[#0A0A0F] border-[#1E293B] h-10 w-24"
                  data-testid="reservation-guests"
                />
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Users className="w-3.5 h-3.5" />
                  <span>
                    {availability?.reservation_behavior === 'capacity' 
                      ? `Máx: ${availability?.max_capacity_per_slot || area.capacity} por horario`
                      : `Máx: ${area.capacity} personas`}
                  </span>
                </div>
              </div>
            </div>
          )}
          
          {/* Purpose - Optional */}
          <div className="space-y-1.5">
            <Label className="text-xs">Motivo (opcional)</Label>
            <Textarea
              value={form.purpose}
              onChange={(e) => setForm({ ...form, purpose: e.target.value })}
              placeholder="Ej: Reunión familiar, cumpleaños..."
              className="bg-[#0A0A0F] border-[#1E293B] h-16 resize-none text-sm"
              data-testid="reservation-purpose"
            />
          </div>
          
          {/* Area Rules Section - ALWAYS visible and prominent */}
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30" data-testid="area-rules-panel">
            <div className="flex items-start gap-2">
              <ScrollText className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-xs font-semibold text-amber-400 mb-1.5">📌 Reglas y Condiciones</p>
                {area.rules && area.rules.trim().length > 0 ? (
                  <div className="max-h-28 overflow-y-auto custom-scrollbar">
                    <p className="text-xs text-amber-200/90 whitespace-pre-wrap leading-relaxed">{area.rules}</p>
                  </div>
                ) : (
                  <p className="text-xs text-amber-200/70">
                    • Horario: {area.available_from} - {area.available_until}<br/>
                    • Capacidad máxima: {area.capacity} personas<br/>
                    {area.requires_approval && '• Requiere aprobación del administrador'}
                  </p>
                )}
                {/* Show behavior-specific rules */}
                <div className="mt-2 pt-2 border-t border-amber-500/20">
                  <p className="text-[10px] text-amber-300/60">
                    {availability?.reservation_behavior === 'exclusive' && 'ℹ️ Reservación exclusiva: el área queda bloqueada para ti durante el horario seleccionado.'}
                    {availability?.reservation_behavior === 'capacity' && `ℹ️ Área compartida: hasta ${availability?.max_capacity_per_slot || area.capacity} personas pueden reservar el mismo horario.`}
                    {availability?.reservation_behavior === 'slot_based' && 'ℹ️ Por turnos: cada reservación corresponde a un slot fijo.'}
                  </p>
                </div>
              </div>
            </div>
          </div>
          </div>
        </div>
        
        <DialogFooter className="flex-col sm:flex-row gap-2 flex-shrink-0 pt-4 border-t border-[#1E293B]">
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
  
  // Cancel confirmation dialog state
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [reservationToCancel, setReservationToCancel] = useState(null);
  const [isCancelling, setIsCancelling] = useState(false);
  
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
    try {
      await api.createReservation(reservationData);
      toast.success('Reservación creada exitosamente');
      loadData();
    } catch (error) {
      const errorMessage = error?.message || (typeof error === 'string' ? error : 'Error al crear reservación');
      toast.error(errorMessage);
      throw error; // Re-throw to let the dialog know
    }
  };
  
  // Open cancel confirmation dialog
  const openCancelDialog = (reservation) => {
    setReservationToCancel(reservation);
    setShowCancelDialog(true);
  };
  
  // Confirm and execute cancellation using DELETE endpoint
  const confirmCancelReservation = async () => {
    if (!reservationToCancel) return;
    
    setIsCancelling(true);
    try {
      await api.cancelReservation(reservationToCancel.id);
      toast.success('Reservación cancelada. El espacio ha sido liberado.');
      setShowCancelDialog(false);
      setReservationToCancel(null);
      loadData();
    } catch (error) {
      const errorMessage = error?.message || (typeof error === 'string' ? error : 'Error al cancelar reservación');
      toast.error(errorMessage);
    } finally {
      setIsCancelling(false);
    }
  };
  
  // Close cancel dialog
  const closeCancelDialog = () => {
    if (!isCancelling) {
      setShowCancelDialog(false);
      setReservationToCancel(null);
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
    <div className="min-h-0 flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-[#1E293B] flex-shrink-0">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Calendar className="w-5 h-5 text-primary" />
          Reservaciones
        </h2>
        <p className="text-xs text-muted-foreground mt-1">
          Reserva áreas comunes del condominio
        </p>
      </div>
      
      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <TabsList className="grid grid-cols-2 mx-4 mt-3 bg-[#0A0A0F] flex-shrink-0">
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
        <TabsContent value="areas" className="flex-1 mt-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4 pb-24 space-y-3">
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
        <TabsContent value="mine" className="flex-1 mt-0 overflow-hidden">
          <ScrollArea className="h-full">
            <div className="p-4 pb-24 space-y-4">
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
                        onCancel={openCancelDialog}
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
                        onCancel={openCancelDialog}
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
                    Ve a &quot;Áreas&quot; para hacer tu primera reservación
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
      
      {/* Cancel Confirmation Dialog */}
      <Dialog open={showCancelDialog} onOpenChange={closeCancelDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-sm mx-4">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-400">
              <AlertCircle className="w-5 h-5" />
              Cancelar Reservación
            </DialogTitle>
            <DialogDescription className="text-muted-foreground">
              ¿Estás seguro que deseas cancelar esta reservación?
            </DialogDescription>
          </DialogHeader>
          
          {reservationToCancel && (
            <div className="p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B] space-y-2">
              <p className="text-sm font-medium text-white">{reservationToCancel.area_name}</p>
              <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <CalendarDays className="w-3 h-3" />
                  {reservationToCancel.date}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {reservationToCancel.start_time} - {reservationToCancel.end_time}
                </span>
              </div>
            </div>
          )}
          
          <p className="text-xs text-yellow-400 flex items-start gap-2">
            <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
            Al cancelar, el espacio quedará disponible para otros residentes.
          </p>
          
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button 
              variant="outline" 
              onClick={closeCancelDialog}
              disabled={isCancelling}
              className="w-full sm:w-auto"
            >
              No, mantener
            </Button>
            <Button 
              variant="destructive"
              onClick={confirmCancelReservation}
              disabled={isCancelling}
              className="w-full sm:w-auto"
              data-testid="confirm-cancel-reservation"
            >
              {isCancelling ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Cancelando...
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4 mr-2" />
                  Sí, cancelar
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ResidentReservations;
