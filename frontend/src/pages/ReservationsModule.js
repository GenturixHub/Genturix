/**
 * GENTURIX - Reservations & Common Areas Module
 * Production-ready, mobile-first implementation
 * 
 * Features:
 * - Common Areas Management (Admin)
 * - Reservations (Resident)
 * - Approval Flow (Admin)
 * - Guard View (Today's reservations)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import { Textarea } from '../components/ui/textarea';
import { Switch } from '../components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import api from '../services/api';
import {
  Calendar,
  Clock,
  Users,
  MapPin,
  Plus,
  Edit,
  Trash2,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Waves,
  Dumbbell,
  UtensilsCrossed,
  Tent,
  Building2,
  MoreHorizontal,
  ChevronLeft,
  ChevronRight,
  CalendarDays,
  List,
  Settings,
  Eye
} from 'lucide-react';

// ============================================
// CONFIGURATION
// ============================================
const AREA_ICONS = {
  pool: Waves,
  gym: Dumbbell,
  bbq: UtensilsCrossed,
  event_room: Building2,
  sports: Tent,
  other: MoreHorizontal
};

const AREA_LABELS = {
  pool: 'Piscina',
  gym: 'Gimnasio',
  bbq: 'Área BBQ',
  event_room: 'Salón de Eventos',
  sports: 'Cancha Deportiva',
  other: 'Otro'
};

const STATUS_CONFIG = {
  pending: { label: 'Pendiente', color: 'bg-yellow-500/20 text-yellow-400', icon: Clock },
  approved: { label: 'Aprobada', color: 'bg-green-500/20 text-green-400', icon: CheckCircle },
  rejected: { label: 'Rechazada', color: 'bg-red-500/20 text-red-400', icon: XCircle },
  cancelled: { label: 'Cancelada', color: 'bg-gray-500/20 text-gray-400', icon: XCircle }
};

const DAYS_OF_WEEK = [
  { key: 'Lunes', short: 'L' },
  { key: 'Martes', short: 'M' },
  { key: 'Miércoles', short: 'X' },
  { key: 'Jueves', short: 'J' },
  { key: 'Viernes', short: 'V' },
  { key: 'Sábado', short: 'S' },
  { key: 'Domingo', short: 'D' }
];

// Helper to detect mobile
const useIsMobile = () => {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  return isMobile;
};

// ============================================
// AREA CARD COMPONENT
// ============================================
const AreaCard = ({ area, isAdmin, onEdit, onDelete, onReserve }) => {
  const AreaIcon = AREA_ICONS[area.area_type] || MoreHorizontal;
  const isMobile = useIsMobile();
  
  return (
    <Card className="bg-[#0F111A] border-[#1E293B] hover:border-primary/30 transition-all">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="p-2 rounded-lg bg-primary/10 flex-shrink-0">
              <AreaIcon className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-white truncate">{area.name}</h3>
              <p className="text-xs text-muted-foreground">{AREA_LABELS[area.area_type] || 'Área'}</p>
              
              <div className="flex flex-wrap gap-2 mt-2">
                <Badge variant="outline" className="text-[10px]">
                  <Users className="w-3 h-3 mr-1" />
                  {area.capacity} personas
                </Badge>
                <Badge variant="outline" className="text-[10px]">
                  <Clock className="w-3 h-3 mr-1" />
                  {area.available_from}-{area.available_until}
                </Badge>
                {area.requires_approval && (
                  <Badge className="bg-yellow-500/20 text-yellow-400 text-[10px]">
                    Requiere aprobación
                  </Badge>
                )}
              </div>
              
              {area.description && (
                <p className="text-xs text-muted-foreground mt-2 line-clamp-2">{area.description}</p>
              )}
              
              {/* Allowed days */}
              <div className="flex gap-1 mt-2">
                {DAYS_OF_WEEK.map(day => {
                  const isAllowed = (area.allowed_days || DAYS_OF_WEEK.map(d => d.key)).includes(day.key);
                  return (
                    <span
                      key={day.key}
                      className={`w-5 h-5 rounded text-[10px] flex items-center justify-center ${
                        isAllowed ? 'bg-primary/20 text-primary' : 'bg-gray-800 text-gray-600'
                      }`}
                      title={day.key}
                    >
                      {day.short}
                    </span>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
        
        <div className={`flex gap-2 mt-3 ${isMobile ? 'flex-col' : ''}`}>
          {isAdmin ? (
            <>
              <Button size="sm" variant="outline" onClick={() => onEdit(area)} className="flex-1">
                <Edit className="w-3 h-3 mr-1" />
                Editar
              </Button>
              <Button size="sm" variant="outline" onClick={() => onDelete(area)} className="text-red-400 hover:bg-red-500/10 flex-1">
                <Trash2 className="w-3 h-3 mr-1" />
                Eliminar
              </Button>
            </>
          ) : (
            <Button size="sm" onClick={() => onReserve(area)} className="w-full">
              <Calendar className="w-3 h-3 mr-1" />
              Reservar
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

// ============================================
// RESERVATION CARD COMPONENT
// ============================================
const ReservationCard = ({ reservation, isAdmin, onApprove, onReject, onCancel }) => {
  const statusConfig = STATUS_CONFIG[reservation.status] || STATUS_CONFIG.pending;
  const StatusIcon = statusConfig.icon;
  const AreaIcon = AREA_ICONS[reservation.area_type] || MoreHorizontal;
  
  // Determine if cancellation is allowed
  const canCancel = (() => {
    // Can only cancel pending or approved reservations
    if (!['pending', 'approved'].includes(reservation.status)) return false;
    
    // For non-admin, also check if reservation has started
    if (!isAdmin) {
      try {
        const now = new Date();
        const [year, month, day] = reservation.date.split('-').map(Number);
        const [startHour, startMin] = reservation.start_time.split(':').map(Number);
        const reservationStart = new Date(year, month - 1, day, startHour, startMin);
        if (now >= reservationStart) return false;
      } catch (e) {
        return true;
      }
    }
    
    return true;
  })();
  
  // Admin can cancel any non-completed/non-cancelled reservation
  const adminCanCancel = isAdmin && ['pending', 'approved'].includes(reservation.status);
  
  return (
    <Card className="bg-[#0F111A] border-[#1E293B]">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            {isAdmin && reservation.resident_name && (
              <Avatar className="w-10 h-10 flex-shrink-0">
                <AvatarImage src={reservation.resident_photo} />
                <AvatarFallback>{reservation.resident_name?.charAt(0)}</AvatarFallback>
              </Avatar>
            )}
            {!isAdmin && (
              <div className="p-2 rounded-lg bg-primary/10 flex-shrink-0">
                <AreaIcon className="w-5 h-5 text-primary" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              {isAdmin && <p className="font-medium text-white truncate">{reservation.resident_name}</p>}
              <p className={`${isAdmin ? 'text-sm text-muted-foreground' : 'font-medium text-white'} truncate`}>
                {reservation.area_name}
              </p>
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
                <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                  {reservation.purpose}
                </p>
              )}
              {/* Show cancellation reason if available */}
              {reservation.status === 'cancelled' && reservation.cancellation_reason && (
                <p className="text-xs text-red-400 mt-1">
                  Motivo: {reservation.cancellation_reason}
                </p>
              )}
            </div>
          </div>
          <Badge className={`${statusConfig.color} flex-shrink-0`}>
            <StatusIcon className="w-3 h-3 mr-1" />
            {statusConfig.label}
          </Badge>
        </div>
        
        {/* Admin Actions - Pending: Approve/Reject + Cancel */}
        {isAdmin && reservation.status === 'pending' && (
          <div className="flex flex-col gap-2 mt-3">
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                className="flex-1 border-red-500/50 text-red-400 hover:bg-red-500/10"
                onClick={() => onReject(reservation)}
                data-testid={`reject-reservation-${reservation.id}`}
              >
                <XCircle className="w-3 h-3 mr-1" />
                Rechazar
              </Button>
              <Button
                size="sm"
                className="flex-1 bg-green-600 hover:bg-green-700"
                onClick={() => onApprove(reservation)}
                data-testid={`approve-reservation-${reservation.id}`}
              >
                <CheckCircle className="w-3 h-3 mr-1" />
                Aprobar
              </Button>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="w-full text-orange-400 border-orange-500/30 hover:bg-orange-500/10"
              onClick={() => onCancel(reservation)}
              data-testid={`admin-cancel-reservation-${reservation.id}`}
            >
              <Trash2 className="w-3 h-3 mr-1" />
              Cancelar Reservación
            </Button>
          </div>
        )}
        
        {/* Admin Actions - Approved: Just Cancel */}
        {isAdmin && reservation.status === 'approved' && (
          <Button
            size="sm"
            variant="outline"
            className="w-full mt-3 text-orange-400 border-orange-500/30 hover:bg-orange-500/10"
            onClick={() => onCancel(reservation)}
            data-testid={`admin-cancel-reservation-${reservation.id}`}
          >
            <Trash2 className="w-3 h-3 mr-1" />
            Cancelar Reservación
          </Button>
        )}
        
        {/* Non-admin Cancel */}
        {!isAdmin && canCancel && (
          <Button
            size="sm"
            variant="outline"
            className="w-full mt-3 text-red-400 hover:bg-red-500/10"
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
// AREA FORM DIALOG
// ============================================
const AreaFormDialog = ({ open, onClose, area, onSave }) => {
  const [form, setForm] = useState({
    name: '',
    area_type: 'other',
    capacity: 10,
    description: '',
    rules: '',
    available_from: '06:00',
    available_until: '22:00',
    requires_approval: false,
    max_hours_per_reservation: 2,
    max_reservations_per_day: 10,
    allowed_days: DAYS_OF_WEEK.map(d => d.key),
    // NEW: Reservation behavior fields
    reservation_behavior: 'exclusive',
    max_capacity_per_slot: null,
    slot_duration_minutes: 60,
    max_reservations_per_user_per_day: null
  });
  const [isSaving, setIsSaving] = useState(false);
  
  // Behavior descriptions for admin
  const BEHAVIOR_OPTIONS = [
    { 
      value: 'exclusive', 
      label: 'Exclusivo', 
      description: 'Un residente bloquea todo el espacio (Salón, Rancho)',
      icon: '🔒'
    },
    { 
      value: 'capacity', 
      label: 'Por Capacidad', 
      description: 'Múltiples reservas hasta llenar capacidad (Gimnasio, Piscina)',
      icon: '👥'
    },
    { 
      value: 'slot_based', 
      label: 'Por Turnos', 
      description: 'Slots fijos, 1 reserva por slot (Canchas, BBQ)',
      icon: '⏰'
    },
    { 
      value: 'free_access', 
      label: 'Acceso Libre', 
      description: 'No requiere reservación (Áreas abiertas)',
      icon: '🚪'
    }
  ];
  
  useEffect(() => {
    if (area) {
      setForm({
        name: area.name || '',
        area_type: area.area_type || 'other',
        capacity: area.capacity || 10,
        description: area.description || '',
        rules: area.rules || '',
        available_from: area.available_from || '06:00',
        available_until: area.available_until || '22:00',
        requires_approval: area.requires_approval || false,
        max_hours_per_reservation: area.max_hours_per_reservation || area.max_duration_hours || 2,
        max_reservations_per_day: area.max_reservations_per_day || 10,
        allowed_days: area.allowed_days || DAYS_OF_WEEK.map(d => d.key),
        // NEW fields
        reservation_behavior: area.reservation_behavior || 'exclusive',
        max_capacity_per_slot: area.max_capacity_per_slot || null,
        slot_duration_minutes: area.slot_duration_minutes || 60,
        max_reservations_per_user_per_day: area.max_reservations_per_user_per_day || null
      });
    } else {
      setForm({
        name: '',
        area_type: 'other',
        capacity: 10,
        description: '',
        rules: '',
        available_from: '06:00',
        available_until: '22:00',
        requires_approval: false,
        max_hours_per_reservation: 2,
        max_reservations_per_day: 10,
        allowed_days: DAYS_OF_WEEK.map(d => d.key),
        reservation_behavior: 'exclusive',
        max_capacity_per_slot: null,
        slot_duration_minutes: 60,
        max_reservations_per_user_per_day: null
      });
    }
  }, [area, open]);
  
  const toggleDay = (day) => {
    setForm(prev => ({
      ...prev,
      allowed_days: prev.allowed_days.includes(day)
        ? prev.allowed_days.filter(d => d !== day)
        : [...prev.allowed_days, day]
    }));
  };
  
  const handleSave = async () => {
    if (!form.name.trim()) {
      toast.error('El nombre es requerido');
      return;
    }
    if (form.allowed_days.length === 0) {
      toast.error('Debe seleccionar al menos un día');
      return;
    }
    
    setIsSaving(true);
    try {
      await onSave(form, area?.id);
      onClose();
    } catch (error) {
      const errorMessage = error?.message || (typeof error === 'string' ? error : 'Error al guardar');
      toast.error(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{area ? 'Editar Área' : 'Nueva Área'}</DialogTitle>
          <DialogDescription>Configure los detalles del área común</DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Nombre *</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Ej: Piscina Principal"
                className="bg-[#0A0A0F] border-[#1E293B] h-9"
                data-testid="area-form-name"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Tipo</Label>
              <Select value={form.area_type} onValueChange={(v) => setForm({ ...form, area_type: v })}>
                <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] h-9" data-testid="area-form-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(AREA_LABELS).map(([key, label]) => (
                    <SelectItem key={key} value={key}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          
          {/* Capacity & Hours */}
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Capacidad</Label>
              <Input
                type="number"
                value={form.capacity}
                onChange={(e) => setForm({ ...form, capacity: parseInt(e.target.value) || 1 })}
                min={1}
                className="bg-[#0A0A0F] border-[#1E293B] h-9"
                data-testid="area-form-capacity"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Desde</Label>
              <Input
                type="time"
                value={form.available_from}
                onChange={(e) => setForm({ ...form, available_from: e.target.value })}
                className="bg-[#0A0A0F] border-[#1E293B] h-9"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Hasta</Label>
              <Input
                type="time"
                value={form.available_until}
                onChange={(e) => setForm({ ...form, available_until: e.target.value })}
                className="bg-[#0A0A0F] border-[#1E293B] h-9"
              />
            </div>
          </div>
          
          {/* NEW: Reservation Behavior Selection */}
          <div className="space-y-2">
            <Label className="text-xs font-semibold">Tipo de Reservación</Label>
            <div className="grid grid-cols-2 gap-2">
              {BEHAVIOR_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setForm({ ...form, reservation_behavior: opt.value })}
                  className={`p-2.5 rounded-lg border text-left transition-all ${
                    form.reservation_behavior === opt.value
                      ? 'bg-primary/20 border-primary text-white'
                      : 'bg-[#0A0A0F] border-[#1E293B] text-gray-400 hover:border-primary/50'
                  }`}
                  data-testid={`behavior-${opt.value}`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{opt.icon}</span>
                    <span className="text-xs font-medium">{opt.label}</span>
                  </div>
                  <p className="text-[10px] text-muted-foreground mt-1 leading-tight">{opt.description}</p>
                </button>
              ))}
            </div>
          </div>
          
          {/* Conditional fields based on behavior */}
          {form.reservation_behavior === 'capacity' && (
            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30 space-y-3">
              <p className="text-xs text-blue-400 font-medium">⚙️ Configuración de Capacidad por Horario</p>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs">Cupos por horario</Label>
                  <Input
                    type="number"
                    value={form.max_capacity_per_slot || form.capacity}
                    onChange={(e) => setForm({ ...form, max_capacity_per_slot: parseInt(e.target.value) || null })}
                    min={1}
                    placeholder={form.capacity}
                    className="bg-[#0A0A0F] border-[#1E293B] h-9"
                    data-testid="area-form-capacity-per-slot"
                  />
                  <p className="text-[10px] text-muted-foreground">Máximo de personas por franja horaria</p>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Duración slot (min)</Label>
                  <Select 
                    value={String(form.slot_duration_minutes || 60)} 
                    onValueChange={(v) => setForm({ ...form, slot_duration_minutes: parseInt(v) })}
                  >
                    <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="30">30 minutos</SelectItem>
                      <SelectItem value="60">1 hora</SelectItem>
                      <SelectItem value="90">1.5 horas</SelectItem>
                      <SelectItem value="120">2 horas</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          )}
          
          {form.reservation_behavior === 'slot_based' && (
            <div className="p-3 rounded-lg bg-teal-500/10 border border-teal-500/30 space-y-3">
              <p className="text-xs text-teal-400 font-medium">⚙️ Configuración de Turnos</p>
              <div className="space-y-1">
                <Label className="text-xs">Duración de cada turno</Label>
                <Select 
                  value={String(form.slot_duration_minutes || 60)} 
                  onValueChange={(v) => setForm({ ...form, slot_duration_minutes: parseInt(v) })}
                >
                  <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="30">30 minutos</SelectItem>
                    <SelectItem value="60">1 hora</SelectItem>
                    <SelectItem value="90">1.5 horas</SelectItem>
                    <SelectItem value="120">2 horas</SelectItem>
                    <SelectItem value="180">3 horas</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-[10px] text-muted-foreground">Los residentes reservan turnos completos de esta duración</p>
              </div>
            </div>
          )}
          
          {form.reservation_behavior === 'free_access' && (
            <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/30">
              <p className="text-xs text-green-400">
                ℹ️ Esta área no requerirá reservaciones. Los residentes podrán acceder libremente durante el horario de operación.
              </p>
            </div>
          )}
          
          {/* Limits */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Max horas por reserva</Label>
              <Input
                type="number"
                value={form.max_hours_per_reservation}
                onChange={(e) => setForm({ ...form, max_hours_per_reservation: parseInt(e.target.value) || 1 })}
                min={1}
                max={24}
                className="bg-[#0A0A0F] border-[#1E293B] h-9"
                disabled={form.reservation_behavior === 'slot_based' || form.reservation_behavior === 'free_access'}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Max reservas por día</Label>
              <Input
                type="number"
                value={form.max_reservations_per_day}
                onChange={(e) => setForm({ ...form, max_reservations_per_day: parseInt(e.target.value) || 1 })}
                min={1}
                max={100}
                className="bg-[#0A0A0F] border-[#1E293B] h-9"
                disabled={form.reservation_behavior === 'free_access'}
              />
            </div>
          </div>
          
          {/* Limit per user per day */}
          {form.reservation_behavior !== 'free_access' && (
            <div className="space-y-1">
              <Label className="text-xs">Límite por usuario por día (opcional)</Label>
              <Input
                type="number"
                value={form.max_reservations_per_user_per_day || ''}
                onChange={(e) => setForm({ ...form, max_reservations_per_user_per_day: e.target.value ? parseInt(e.target.value) : null })}
                min={1}
                max={10}
                placeholder="Sin límite"
                className="bg-[#0A0A0F] border-[#1E293B] h-9"
              />
              <p className="text-[10px] text-muted-foreground">Máximo de reservas que un usuario puede hacer por día en esta área</p>
            </div>
          )}
          
          {/* Allowed Days */}
          <div className="space-y-2">
            <Label className="text-xs">Días disponibles</Label>
            <div className="flex gap-2">
              {DAYS_OF_WEEK.map(day => (
                <button
                  key={day.key}
                  type="button"
                  onClick={() => toggleDay(day.key)}
                  className={`w-9 h-9 rounded-lg text-xs font-medium transition-all ${
                    form.allowed_days.includes(day.key)
                      ? 'bg-primary text-white'
                      : 'bg-[#1E293B] text-gray-400 hover:bg-[#2E3A4B]'
                  }`}
                >
                  {day.short}
                </button>
              ))}
            </div>
          </div>
          
          {/* Description */}
          <div className="space-y-1">
            <Label className="text-xs">Descripción</Label>
            <Textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Descripción del área..."
              className="bg-[#0A0A0F] border-[#1E293B] min-h-[60px]"
            />
          </div>
          
          {/* Rules */}
          <div className="space-y-1">
            <Label className="text-xs">Reglas (opcional)</Label>
            <Textarea
              value={form.rules}
              onChange={(e) => setForm({ ...form, rules: e.target.value })}
              placeholder="Reglas de uso del área..."
              className="bg-[#0A0A0F] border-[#1E293B] min-h-[60px]"
            />
          </div>
          
          {/* Requires Approval */}
          <div className="flex items-center gap-3 p-3 rounded-lg bg-[#0A0A0F]">
            <Switch
              checked={form.requires_approval}
              onCheckedChange={(checked) => setForm({ ...form, requires_approval: checked })}
              data-testid="area-form-approval"
            />
            <div>
              <Label className="text-sm">Requiere aprobación</Label>
              <p className="text-xs text-muted-foreground">
                El administrador debe aprobar cada reservación
              </p>
            </div>
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={handleSave} disabled={isSaving} data-testid="area-form-save">
            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : (area ? 'Guardar' : 'Crear')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
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
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingAvailability, setIsLoadingAvailability] = useState(false);
  
  // Reset form when area changes
  useEffect(() => {
    if (area && open) {
      const today = new Date().toISOString().split('T')[0];
      setForm({
        date: today,
        start_time: area.available_from || '08:00',
        end_time: '',
        guests_count: 1,
        purpose: ''
      });
      loadAvailability(area.id, today);
    }
  }, [area, open]);
  
  const loadAvailability = async (areaId, date) => {
    setIsLoadingAvailability(true);
    try {
      const data = await api.getAreaAvailability(areaId, date);
      setAvailability(data);
    } catch (error) {
      console.error('Error loading availability:', error);
    } finally {
      setIsLoadingAvailability(false);
    }
  };
  
  const handleDateChange = (date) => {
    setForm({ ...form, date });
    if (area) {
      loadAvailability(area.id, date);
    }
  };
  
  const handleSave = async () => {
    if (!form.date || !form.start_time || !form.end_time) {
      toast.error('Completa todos los campos requeridos');
      return;
    }
    
    if (form.start_time >= form.end_time) {
      toast.error('La hora de fin debe ser posterior a la de inicio');
      return;
    }
    
    setIsSaving(true);
    try {
      await onSave({
        area_id: area.id,
        ...form
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
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        <DialogHeader>
          <DialogTitle>Reservar: {area.name}</DialogTitle>
          <DialogDescription>
            {AREA_LABELS[area.area_type]} - Capacidad: {area.capacity} personas
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          {/* Date */}
          <div className="space-y-1">
            <Label className="text-xs">Fecha *</Label>
            <Input
              type="date"
              value={form.date}
              onChange={(e) => handleDateChange(e.target.value)}
              min={new Date().toISOString().split('T')[0]}
              className="bg-[#0A0A0F] border-[#1E293B]"
              data-testid="reservation-date"
            />
          </div>
          
          {/* Availability info */}
          {availability && (
            <div className={`p-3 rounded-lg text-sm ${
              availability.is_day_allowed
                ? 'bg-green-500/10 border border-green-500/20 text-green-400'
                : 'bg-red-500/10 border border-red-500/20 text-red-400'
            }`}>
              {availability.is_day_allowed ? (
                <>
                  <CheckCircle className="w-4 h-4 inline mr-2" />
                  Disponible: {availability.slots_remaining} reservaciones restantes
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4 inline mr-2" />
                  Esta área no está disponible este día
                </>
              )}
            </div>
          )}
          
          {/* Occupied slots */}
          {availability?.occupied_slots?.length > 0 && (
            <div className="p-3 rounded-lg bg-[#0A0A0F]">
              <p className="text-xs text-muted-foreground mb-2">Horarios ocupados:</p>
              <div className="flex flex-wrap gap-2">
                {availability.occupied_slots.map((slot, i) => (
                  <Badge key={i} variant="outline" className="text-xs">
                    {slot.start_time}-{slot.end_time}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          
          {/* Time */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Hora inicio *</Label>
              <Input
                type="time"
                value={form.start_time}
                onChange={(e) => setForm({ ...form, start_time: e.target.value })}
                min={area.available_from}
                max={area.available_until}
                className="bg-[#0A0A0F] border-[#1E293B]"
                data-testid="reservation-start"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Hora fin *</Label>
              <Input
                type="time"
                value={form.end_time}
                onChange={(e) => setForm({ ...form, end_time: e.target.value })}
                min={form.start_time || area.available_from}
                max={area.available_until}
                className="bg-[#0A0A0F] border-[#1E293B]"
                data-testid="reservation-end"
              />
            </div>
          </div>
          
          <p className="text-xs text-muted-foreground">
            Horario disponible: {area.available_from} - {area.available_until}
          </p>
          
          {/* Guests */}
          <div className="space-y-1">
            <Label className="text-xs">Número de personas</Label>
            <Input
              type="number"
              value={form.guests_count}
              onChange={(e) => setForm({ ...form, guests_count: parseInt(e.target.value) || 1 })}
              min={1}
              max={area.capacity}
              className="bg-[#0A0A0F] border-[#1E293B]"
            />
          </div>
          
          {/* Purpose */}
          <div className="space-y-1">
            <Label className="text-xs">Propósito (opcional)</Label>
            <Input
              value={form.purpose}
              onChange={(e) => setForm({ ...form, purpose: e.target.value })}
              placeholder="Ej: Reunión familiar"
              className="bg-[#0A0A0F] border-[#1E293B]"
            />
          </div>
          
          {/* Approval warning */}
          {area.requires_approval && (
            <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-sm">
              <AlertCircle className="w-4 h-4 inline mr-2" />
              Esta área requiere aprobación del administrador
            </div>
          )}
          
          {/* Rules */}
          {area.rules && (
            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-sm">
              <p className="font-medium mb-1">Reglas del área:</p>
              <p className="text-muted-foreground text-xs">{area.rules}</p>
            </div>
          )}
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button 
            onClick={handleSave} 
            disabled={isSaving || !availability?.is_day_allowed}
            data-testid="reservation-submit"
          >
            {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Reservar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// MAIN COMPONENT
// ============================================
const ReservationsModule = () => {
  const { user } = useAuth();
  const isMobile = useIsMobile();
  const isAdmin = user?.roles?.some(r => ['Administrador', 'SuperAdmin'].includes(r));
  const isGuard = user?.roles?.includes('Guarda');
  
  const [activeTab, setActiveTab] = useState('areas');
  const [areas, setAreas] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Dialogs
  const [showAreaDialog, setShowAreaDialog] = useState(false);
  const [editingArea, setEditingArea] = useState(null);
  const [showReservationDialog, setShowReservationDialog] = useState(false);
  const [selectedArea, setSelectedArea] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [areaToDelete, setAreaToDelete] = useState(null);
  
  // Cancel reservation dialog state (for admin)
  const [showCancelReservationDialog, setShowCancelReservationDialog] = useState(false);
  const [reservationToCancel, setReservationToCancel] = useState(null);
  const [cancelReason, setCancelReason] = useState('');
  const [isCancelling, setIsCancelling] = useState(false);
  
  // Fetch data
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [areasData, reservationsData] = await Promise.all([
        api.getReservationAreas(),
        api.getReservations()
      ]);
      setAreas(areasData);
      setReservations(reservationsData);
      setError(null);
    } catch (err) {
      setError(err.message || 'Error al cargar datos');
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  useEffect(() => {
    fetchData();
  }, [fetchData]);
  
  // Handlers
  const handleSaveArea = async (formData, areaId) => {
    try {
      if (areaId) {
        await api.updateReservationArea(areaId, formData);
        toast.success('Área actualizada');
      } else {
        await api.createReservationArea(formData);
        toast.success('Área creada');
      }
      fetchData();
    } catch (error) {
      const errorMessage = error?.message || (typeof error === 'string' ? error : 'Error al guardar área');
      toast.error(errorMessage);
      throw error; // Re-throw to let the dialog know
    }
  };
  
  const handleDeleteArea = async () => {
    if (!areaToDelete) return;
    try {
      await api.deleteReservationArea(areaToDelete.id);
      toast.success('Área eliminada');
      setShowDeleteDialog(false);
      setAreaToDelete(null);
      fetchData();
    } catch (err) {
      toast.error(err.message || 'Error al eliminar');
    }
  };
  
  const handleCreateReservation = async (formData) => {
    try {
      await api.createReservation(formData);
      toast.success('Reservación creada');
      fetchData();
    } catch (error) {
      const errorMessage = error?.message || (typeof error === 'string' ? error : 'Error al crear reservación');
      toast.error(errorMessage);
      throw error; // Re-throw to let the dialog know
    }
  };
  
  const handleUpdateReservation = async (reservationId, status, notes = null) => {
    try {
      await api.updateReservationStatus(reservationId, { status, admin_notes: notes });
      toast.success(`Reservación ${status === 'approved' ? 'aprobada' : status === 'rejected' ? 'rechazada' : 'cancelada'}`);
      fetchData();
    } catch (error) {
      const errorMessage = error?.message || (typeof error === 'string' ? error : 'Error al actualizar reservación');
      toast.error(errorMessage);
    }
  };
  
  // Open cancel reservation dialog (for admin)
  const openCancelReservationDialog = (reservation) => {
    setReservationToCancel(reservation);
    setCancelReason('');
    setShowCancelReservationDialog(true);
  };
  
  // Confirm and execute admin cancellation using DELETE endpoint
  const confirmCancelReservation = async () => {
    if (!reservationToCancel) return;
    
    setIsCancelling(true);
    try {
      await api.cancelReservation(reservationToCancel.id, cancelReason || null);
      toast.success('Reservación cancelada. El espacio ha sido liberado.');
      setShowCancelReservationDialog(false);
      setReservationToCancel(null);
      setCancelReason('');
      fetchData();
    } catch (error) {
      const errorMessage = error?.message || (typeof error === 'string' ? error : 'Error al cancelar reservación');
      toast.error(errorMessage);
    } finally {
      setIsCancelling(false);
    }
  };
  
  // Close cancel dialog
  const closeCancelReservationDialog = () => {
    if (!isCancelling) {
      setShowCancelReservationDialog(false);
      setReservationToCancel(null);
      setCancelReason('');
    }
  };
  
  const openEditArea = (area) => {
    setEditingArea(area);
    setShowAreaDialog(true);
  };
  
  const openDeleteArea = (area) => {
    setAreaToDelete(area);
    setShowDeleteDialog(true);
  };
  
  const openReservation = (area) => {
    setSelectedArea(area);
    setShowReservationDialog(true);
  };
  
  // Filter reservations
  const myReservations = reservations.filter(r => r.resident_id === user?.id);
  const pendingReservations = reservations.filter(r => r.status === 'pending');
  const approvedReservations = reservations.filter(r => r.status === 'approved');
  
  if (isLoading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }
  
  if (error) {
    return (
      <DashboardLayout>
        <Card className="bg-red-500/10 border-red-500/30">
          <CardContent className="p-6 text-center">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <p className="text-red-400">{error}</p>
            <Button onClick={fetchData} className="mt-4">Reintentar</Button>
          </CardContent>
        </Card>
      </DashboardLayout>
    );
  }
  
  return (
    <DashboardLayout>
      <div className="space-y-4" data-testid="reservations-module">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold">Reservaciones</h1>
            <p className="text-sm text-muted-foreground">
              {isAdmin ? 'Gestión de áreas y reservaciones' : 'Reserva áreas comunes'}
            </p>
          </div>
          {isAdmin && (
            <Button onClick={() => { setEditingArea(null); setShowAreaDialog(true); }} data-testid="new-area-btn">
              <Plus className="w-4 h-4 mr-2" />
              Nueva Área
            </Button>
          )}
        </div>
        
        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className={`bg-[#0F111A] ${isMobile ? 'grid w-full' : ''}`} style={isMobile && isAdmin ? { gridTemplateColumns: 'repeat(4, 1fr)' } : isMobile ? { gridTemplateColumns: 'repeat(3, 1fr)' } : {}}>
            <TabsTrigger value="areas" className="gap-1">
              <MapPin className="w-3 h-3" />
              {!isMobile && 'Áreas'}
            </TabsTrigger>
            <TabsTrigger value="reservations" className="gap-1">
              <Calendar className="w-3 h-3" />
              {!isMobile && 'Mis Reservas'}
              {myReservations.length > 0 && (
                <Badge className="ml-1 bg-primary/20 text-primary text-[10px]">
                  {myReservations.length}
                </Badge>
              )}
            </TabsTrigger>
            {isAdmin && (
              <TabsTrigger value="pending" className="gap-1">
                <Clock className="w-3 h-3" />
                {!isMobile && 'Pendientes'}
                {pendingReservations.length > 0 && (
                  <Badge className="ml-1 bg-yellow-500/20 text-yellow-400 text-[10px]">
                    {pendingReservations.length}
                  </Badge>
                )}
              </TabsTrigger>
            )}
            {isAdmin && (
              <TabsTrigger value="all" className="gap-1">
                <List className="w-3 h-3" />
                {!isMobile && 'Todas'}
                {approvedReservations.length > 0 && (
                  <Badge className="ml-1 bg-green-500/20 text-green-400 text-[10px]">
                    {approvedReservations.length}
                  </Badge>
                )}
              </TabsTrigger>
            )}
          </TabsList>
          
          {/* Areas Tab */}
          <TabsContent value="areas" className="mt-4">
            {areas.length === 0 ? (
              <Card className="bg-[#0F111A] border-[#1E293B]">
                <CardContent className="p-8 text-center">
                  <MapPin className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-30" />
                  <p className="text-muted-foreground mb-4">No hay áreas configuradas</p>
                  {isAdmin && (
                    <Button onClick={() => { setEditingArea(null); setShowAreaDialog(true); }}>
                      <Plus className="w-4 h-4 mr-2" />
                      Crear primera área
                    </Button>
                  )}
                </CardContent>
              </Card>
            ) : (
              <div className={`grid gap-4 ${isMobile ? 'grid-cols-1' : 'grid-cols-2 lg:grid-cols-3'}`}>
                {areas.map(area => (
                  <AreaCard
                    key={area.id}
                    area={area}
                    isAdmin={isAdmin}
                    onEdit={openEditArea}
                    onDelete={openDeleteArea}
                    onReserve={openReservation}
                  />
                ))}
              </div>
            )}
          </TabsContent>
          
          {/* My Reservations Tab */}
          <TabsContent value="reservations" className="mt-4">
            {myReservations.length === 0 ? (
              <Card className="bg-[#0F111A] border-[#1E293B]">
                <CardContent className="p-8 text-center">
                  <Calendar className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-30" />
                  <p className="text-muted-foreground mb-4">No tienes reservaciones</p>
                  {areas.length > 0 && (
                    <Button onClick={() => setActiveTab('areas')}>
                      Ver áreas disponibles
                    </Button>
                  )}
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {myReservations.map(res => (
                  <ReservationCard
                    key={res.id}
                    reservation={res}
                    isAdmin={false}
                    onCancel={openCancelReservationDialog}
                  />
                ))}
              </div>
            )}
          </TabsContent>
          
          {/* Pending Tab (Admin) */}
          {isAdmin && (
            <TabsContent value="pending" className="mt-4">
              {pendingReservations.length === 0 ? (
                <Card className="bg-[#0F111A] border-[#1E293B]">
                  <CardContent className="p-8 text-center">
                    <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
                    <p className="text-muted-foreground">No hay reservaciones pendientes</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-3">
                  {pendingReservations.map(res => (
                    <ReservationCard
                      key={res.id}
                      reservation={res}
                      isAdmin={true}
                      onApprove={(r) => handleUpdateReservation(r.id, 'approved')}
                      onReject={(r) => handleUpdateReservation(r.id, 'rejected')}
                      onCancel={openCancelReservationDialog}
                    />
                  ))}
                </div>
              )}
            </TabsContent>
          )}
          
          {/* All Reservations Tab (Admin) - Shows approved reservations for cancellation */}
          {isAdmin && (
            <TabsContent value="all" className="mt-4">
              {approvedReservations.length === 0 ? (
                <Card className="bg-[#0F111A] border-[#1E293B]">
                  <CardContent className="p-8 text-center">
                    <Calendar className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-30" />
                    <p className="text-muted-foreground">No hay reservaciones aprobadas activas</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-3">
                  <p className="text-xs text-muted-foreground mb-2">
                    Reservaciones aprobadas que pueden ser canceladas:
                  </p>
                  {approvedReservations.map(res => (
                    <ReservationCard
                      key={res.id}
                      reservation={res}
                      isAdmin={true}
                      onApprove={() => {}}
                      onReject={() => {}}
                      onCancel={openCancelReservationDialog}
                    />
                  ))}
                </div>
              )}
            </TabsContent>
          )}
        </Tabs>
      </div>
      
      {/* Dialogs */}
      <AreaFormDialog
        open={showAreaDialog}
        onClose={() => { setShowAreaDialog(false); setEditingArea(null); }}
        area={editingArea}
        onSave={handleSaveArea}
      />
      
      <ReservationFormDialog
        open={showReservationDialog}
        onClose={() => { setShowReservationDialog(false); setSelectedArea(null); }}
        area={selectedArea}
        onSave={handleCreateReservation}
      />
      
      {/* Delete Confirmation */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle>¿Eliminar área?</DialogTitle>
            <DialogDescription>
              ¿Estás seguro de eliminar &quot;{areaToDelete?.name}&quot;? Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancelar
            </Button>
            <Button variant="destructive" onClick={handleDeleteArea} data-testid="confirm-delete-area">
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Cancel Reservation Confirmation (Admin) */}
      <Dialog open={showCancelReservationDialog} onOpenChange={closeCancelReservationDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-orange-400">
              <AlertCircle className="w-5 h-5" />
              Cancelar Reservación
            </DialogTitle>
            <DialogDescription>
              Esta acción liberará el espacio para que otros residentes puedan reservarlo.
            </DialogDescription>
          </DialogHeader>
          
          {reservationToCancel && (
            <div className="p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B] space-y-2">
              <div className="flex items-center gap-2">
                <Avatar className="w-8 h-8">
                  <AvatarImage src={reservationToCancel.resident_photo} />
                  <AvatarFallback>{reservationToCancel.resident_name?.charAt(0)}</AvatarFallback>
                </Avatar>
                <div>
                  <p className="text-sm font-medium text-white">{reservationToCancel.resident_name}</p>
                  <p className="text-xs text-muted-foreground">{reservationToCancel.area_name}</p>
                </div>
              </div>
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
          
          {/* Cancellation reason (optional for admin) */}
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Motivo de cancelación (opcional)</Label>
            <Textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Ej: Mantenimiento del área, conflicto de horarios..."
              className="bg-[#0A0A0F] border-[#1E293B] min-h-[80px] resize-none"
              data-testid="cancel-reason-input"
            />
            <p className="text-[10px] text-muted-foreground">
              El residente recibirá una notificación con este motivo.
            </p>
          </div>
          
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button 
              variant="outline" 
              onClick={closeCancelReservationDialog}
              disabled={isCancelling}
              className="w-full sm:w-auto"
            >
              No, mantener
            </Button>
            <Button 
              variant="destructive"
              onClick={confirmCancelReservation}
              disabled={isCancelling}
              className="w-full sm:w-auto bg-orange-600 hover:bg-orange-700"
              data-testid="confirm-cancel-reservation"
            >
              {isCancelling ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Cancelando...
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4 mr-2" />
                  Cancelar Reservación
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
};

export default ReservationsModule;
