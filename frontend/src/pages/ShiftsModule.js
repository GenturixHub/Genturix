/**
 * GENTURIX - Módulo de Turnos (Shifts)
 * 
 * ENFOQUE: OPERACIONES Y TIEMPO (no personas)
 * - Turnos activos, próximos y finalizados
 * - Asignación de guardias
 * - Vista en tiempo real
 * - Quién está activo AHORA
 * 
 * NO incluye: Datos personales, contratos, historial laboral
 * Eso va en el módulo de RRHH (RRHHModule)
 */

import React, { useState, useEffect, useCallback } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ScrollArea } from '../components/ui/scroll-area';
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
import api from '../services/api';
import { 
  Calendar,
  Clock,
  MapPin,
  Plus,
  Loader2,
  Play,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  User,
  Timer
} from 'lucide-react';
import { useIsMobile } from '../components/layout/BottomNav';

// ============================================
// SHIFT STATUS HELPERS
// ============================================
const getShiftStatus = (shift) => {
  const now = new Date();
  const start = new Date(shift.start_time);
  const end = new Date(shift.end_time);

  if (shift.status === 'completed') return 'completed';
  if (now >= start && now <= end) return 'active';
  if (now < start) return 'scheduled';
  return 'completed';
};

const STATUS_CONFIG = {
  active: {
    label: 'EN TURNO',
    color: 'bg-green-500',
    textColor: 'text-green-400',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
  },
  scheduled: {
    label: 'PRÓXIMO',
    color: 'bg-blue-500',
    textColor: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
  },
  completed: {
    label: 'FINALIZADO',
    color: 'bg-gray-500',
    textColor: 'text-gray-400',
    bgColor: 'bg-gray-500/10',
    borderColor: 'border-gray-500/30',
  },
};

// ============================================
// ACTIVE NOW CARD (Priority display)
// ============================================
const ActiveNowCard = ({ activeShifts }) => {
  if (activeShifts.length === 0) {
    return (
      <Card className="bg-yellow-500/10 border-yellow-500/30">
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-8 h-8 text-yellow-400" />
            <div>
              <p className="font-semibold text-yellow-400">Sin guardias activos</p>
              <p className="text-sm text-muted-foreground">No hay turnos en este momento</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-green-500/10 border-green-500/30">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-green-400">Guardias Activos Ahora</span>
          <Badge className="ml-auto bg-green-500 text-white">{activeShifts.length}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {activeShifts.map((shift) => (
          <div 
            key={shift.id}
            className="flex items-center justify-between p-3 rounded-lg bg-[#0F111A] border border-green-500/20"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                <User className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="font-medium text-white">{shift.guard_name}</p>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <MapPin className="w-3 h-3" />
                  {shift.location}
                </div>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-mono text-green-400">
                {new Date(shift.end_time).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
              </p>
              <p className="text-xs text-muted-foreground">Termina</p>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

// ============================================
// SHIFT CARD COMPONENT
// ============================================
const ShiftCard = ({ shift }) => {
  const status = getShiftStatus(shift);
  const config = STATUS_CONFIG[status];

  const formatTime = (dateStr) => {
    return new Date(dateStr).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' });
  };

  return (
    <div className={`p-4 rounded-xl ${config.bgColor} border ${config.borderColor}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-full ${config.bgColor} flex items-center justify-center`}>
            {status === 'active' ? (
              <Play className={`w-5 h-5 ${config.textColor}`} />
            ) : status === 'scheduled' ? (
              <Clock className={`w-5 h-5 ${config.textColor}`} />
            ) : (
              <CheckCircle className={`w-5 h-5 ${config.textColor}`} />
            )}
          </div>
          <div>
            <p className="font-semibold text-white">{shift.guard_name}</p>
            <Badge variant="outline" className={`${config.textColor} ${config.borderColor} text-xs`}>
              {config.label}
            </Badge>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">{formatDate(shift.start_time)}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="space-y-1">
          <p className="text-muted-foreground text-xs">Horario</p>
          <p className="font-mono text-white">
            {formatTime(shift.start_time)} - {formatTime(shift.end_time)}
          </p>
        </div>
        <div className="space-y-1">
          <p className="text-muted-foreground text-xs">Ubicación</p>
          <div className="flex items-center gap-1">
            <MapPin className="w-3 h-3 text-muted-foreground" />
            <p className="text-white truncate">{shift.location}</p>
          </div>
        </div>
      </div>

      {shift.notes && (
        <p className="mt-3 pt-3 border-t border-[#1E293B] text-xs text-muted-foreground">
          {shift.notes}
        </p>
      )}
    </div>
  );
};

// ============================================
// MAIN SHIFTS MODULE
// ============================================
const ShiftsModule = () => {
  const isMobile = useIsMobile();
  const [shifts, setShifts] = useState([]);
  const [guards, setGuards] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newShift, setNewShift] = useState({
    guard_id: '',
    start_time: '',
    end_time: '',
    location: '',
    notes: ''
  });

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      const [shiftsData, guardsData] = await Promise.all([
        api.getShifts(),
        api.getGuards()
      ]);
      setShifts(shiftsData);
      setGuards(guardsData.filter(g => g.is_active));
    } catch (error) {
      console.error('Error fetching shifts:', error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    // Refresh every 30 seconds for real-time updates
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    fetchData();
  };

  // Categorize shifts
  const categorizedShifts = {
    active: shifts.filter(s => getShiftStatus(s) === 'active'),
    scheduled: shifts.filter(s => getShiftStatus(s) === 'scheduled'),
    completed: shifts.filter(s => getShiftStatus(s) === 'completed').slice(0, 10),
  };

  // Filter shifts
  const displayShifts = filterStatus === 'all' 
    ? [...categorizedShifts.active, ...categorizedShifts.scheduled, ...categorizedShifts.completed]
    : categorizedShifts[filterStatus] || [];

  // Create shift
  const handleCreateShift = async () => {
    try {
      await api.createShift(newShift);
      setCreateDialogOpen(false);
      setNewShift({ guard_id: '', start_time: '', end_time: '', location: '', notes: '' });
      fetchData();
    } catch (error) {
      console.error('Error creating shift:', error);
      alert('Error al crear turno');
    }
  };

  if (isLoading) {
    return (
      <DashboardLayout title="Turnos">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Turnos">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white">Gestión de Turnos</h1>
            <p className="text-sm text-muted-foreground">Control operativo de guardias</p>
          </div>
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              size="icon"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="border-[#1E293B]"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            </Button>
            <Button onClick={() => setCreateDialogOpen(true)} className="flex-1 sm:flex-none">
              <Plus className="w-4 h-4 mr-2" />
              Nuevo Turno
            </Button>
          </div>
        </div>

        {/* Active Now - Priority Display */}
        <ActiveNowCard activeShifts={categorizedShifts.active} />

        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/30 text-center">
            <p className="text-2xl font-bold text-green-400">{categorizedShifts.active.length}</p>
            <p className="text-xs text-muted-foreground">Activos</p>
          </div>
          <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/30 text-center">
            <p className="text-2xl font-bold text-blue-400">{categorizedShifts.scheduled.length}</p>
            <p className="text-xs text-muted-foreground">Próximos</p>
          </div>
          <div className="p-3 rounded-xl bg-gray-500/10 border border-gray-500/30 text-center">
            <p className="text-2xl font-bold text-gray-400">{categorizedShifts.completed.length}</p>
            <p className="text-xs text-muted-foreground">Finalizados</p>
          </div>
        </div>

        {/* Filter */}
        <div className="flex gap-2">
          {['all', 'active', 'scheduled', 'completed'].map((status) => (
            <Button
              key={status}
              variant={filterStatus === status ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterStatus(status)}
              className={filterStatus !== status ? 'border-[#1E293B]' : ''}
            >
              {status === 'all' ? 'Todos' : 
               status === 'active' ? 'Activos' :
               status === 'scheduled' ? 'Próximos' : 'Finalizados'}
            </Button>
          ))}
        </div>

        {/* Shifts List */}
        <div className="space-y-3">
          {displayShifts.length > 0 ? (
            displayShifts.map((shift) => (
              <ShiftCard key={shift.id} shift={shift} />
            ))
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Calendar className="w-12 h-12 mx-auto mb-4 opacity-30" />
              <p>No hay turnos para mostrar</p>
            </div>
          )}
        </div>

        {/* Create Shift Dialog */}
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogContent className="bg-[#0F111A] border-[#1E293B]">
            <DialogHeader>
              <DialogTitle>Crear Nuevo Turno</DialogTitle>
              <DialogDescription>
                Asigna un turno a un guardia
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Guardia</Label>
                <Select 
                  value={newShift.guard_id} 
                  onValueChange={(v) => setNewShift({...newShift, guard_id: v})}
                >
                  <SelectTrigger className="bg-[#181B25] border-[#1E293B]">
                    <SelectValue placeholder="Seleccionar guardia..." />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                    {guards.map((guard) => (
                      <SelectItem key={guard.id} value={guard.id}>
                        {guard.user_name} ({guard.badge_number})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Inicio</Label>
                  <Input
                    type="datetime-local"
                    value={newShift.start_time}
                    onChange={(e) => setNewShift({...newShift, start_time: e.target.value})}
                    className="bg-[#181B25] border-[#1E293B]"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Fin</Label>
                  <Input
                    type="datetime-local"
                    value={newShift.end_time}
                    onChange={(e) => setNewShift({...newShift, end_time: e.target.value})}
                    className="bg-[#181B25] border-[#1E293B]"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Ubicación / Zona</Label>
                <Input
                  placeholder="Ej: Entrada Principal, Perímetro Norte..."
                  value={newShift.location}
                  onChange={(e) => setNewShift({...newShift, location: e.target.value})}
                  className="bg-[#181B25] border-[#1E293B]"
                />
              </div>
              <div className="space-y-2">
                <Label>Notas (opcional)</Label>
                <Input
                  placeholder="Instrucciones especiales..."
                  value={newShift.notes}
                  onChange={(e) => setNewShift({...newShift, notes: e.target.value})}
                  className="bg-[#181B25] border-[#1E293B]"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                Cancelar
              </Button>
              <Button 
                onClick={handleCreateShift}
                disabled={!newShift.guard_id || !newShift.start_time || !newShift.end_time || !newShift.location}
              >
                Crear Turno
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
};

export default ShiftsModule;
