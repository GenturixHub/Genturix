/**
 * GENTURIX - Módulo RRHH (Recursos Humanos)
 * 
 * MÓDULO CENTRAL para toda la gestión de personal.
 * Turnos NO es un módulo separado - es un submódulo de RRHH.
 * 
 * SUBMÓDULOS:
 * - Solicitudes de Ausencia (vacaciones, permisos, aprobaciones)
 * - Control Horario (entrada/salida, ajustes, reportes)
 * - Planificación de Turnos (creación, asignación, calendario)
 * - Reclutamiento (candidatos, pipeline, conversión)
 * - Onboarding / Offboarding (accesos, equipos, desactivación)
 * - Evaluación de Desempeño (evaluaciones, feedback, historial)
 * 
 * ACCESO POR ROL:
 * - Guarda/Empleado: Ver sus turnos, fichar, solicitar ausencias
 * - Supervisor: Planificar turnos, aprobar ausencias, ver desempeño
 * - Admin: Acceso completo a RRHH
 */

import React, { useState, useEffect, useCallback } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
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
import { useAuth } from '../contexts/AuthContext';
import { useIsMobile } from '../components/layout/BottomNav';
import api from '../services/api';
import { 
  Users, 
  UserPlus,
  Clock,
  Calendar,
  CalendarDays,
  FileText,
  UserCheck,
  UserX,
  Briefcase,
  GraduationCap,
  Star,
  Plus,
  Loader2,
  Search,
  MoreVertical,
  Edit,
  MapPin,
  Play,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  LogIn,
  LogOut as LogOutIcon,
  CalendarOff,
  ClipboardList,
  TrendingUp
} from 'lucide-react';

// ============================================
// RRHH SUBMODULE CONFIGURATION
// ============================================
const RRHH_SUBMODULES = {
  ausencias: {
    id: 'ausencias',
    label: 'Solicitudes de Ausencia',
    shortLabel: 'Ausencias',
    icon: CalendarOff,
    description: 'Vacaciones, permisos, aprobaciones',
    roles: ['Administrador', 'Supervisor', 'Guarda'],
  },
  control_horario: {
    id: 'control_horario',
    label: 'Control Horario',
    shortLabel: 'Horario',
    icon: Clock,
    description: 'Entrada/salida, ajustes, reportes',
    roles: ['Administrador', 'Supervisor', 'Guarda'],
  },
  turnos: {
    id: 'turnos',
    label: 'Planificación de Turnos',
    shortLabel: 'Turnos',
    icon: CalendarDays,
    description: 'Creación, asignación, calendario',
    roles: ['Administrador', 'Supervisor'],
  },
  reclutamiento: {
    id: 'reclutamiento',
    label: 'Reclutamiento',
    shortLabel: 'Reclutar',
    icon: UserPlus,
    description: 'Candidatos, pipeline, contratación',
    roles: ['Administrador'],
  },
  onboarding: {
    id: 'onboarding',
    label: 'Onboarding / Offboarding',
    shortLabel: 'Onboard',
    icon: ClipboardList,
    description: 'Accesos, equipos, desactivación',
    roles: ['Administrador'],
  },
  evaluacion: {
    id: 'evaluacion',
    label: 'Evaluación de Desempeño',
    shortLabel: 'Evaluación',
    icon: TrendingUp,
    description: 'Evaluaciones, feedback, historial',
    roles: ['Administrador', 'Supervisor'],
  },
};

// ============================================
// EMPLOYEE CARD COMPONENT
// ============================================
const EmployeeCard = ({ employee, onEdit }) => (
  <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B] hover:border-[#2D3B4F] transition-colors">
    <div className="flex items-start gap-4">
      <div className={`
        w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold
        ${employee.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}
      `}>
        {employee.user_name?.charAt(0).toUpperCase() || 'E'}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="font-semibold text-white truncate">{employee.user_name}</h3>
          <Badge 
            variant="outline" 
            className={employee.is_active ? 'border-green-500/30 text-green-400' : 'border-red-500/30 text-red-400'}
          >
            {employee.is_active ? 'Activo' : 'Inactivo'}
          </Badge>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
          <span className="font-mono">{employee.badge_number}</span>
          <span>{employee.phone}</span>
        </div>
      </div>
      <Button variant="ghost" size="icon" onClick={() => onEdit(employee)}>
        <Edit className="w-4 h-4" />
      </Button>
    </div>
  </div>
);

// ============================================
// SHIFT CARD COMPONENT
// ============================================
const ShiftCard = ({ shift }) => {
  const getStatus = () => {
    const now = new Date();
    const start = new Date(shift.start_time);
    const end = new Date(shift.end_time);
    if (now >= start && now <= end) return 'active';
    if (now < start) return 'scheduled';
    return 'completed';
  };

  const status = getStatus();
  const statusConfig = {
    active: { label: 'EN TURNO', color: 'bg-green-500', textColor: 'text-green-400', bgColor: 'bg-green-500/10' },
    scheduled: { label: 'PRÓXIMO', color: 'bg-blue-500', textColor: 'text-blue-400', bgColor: 'bg-blue-500/10' },
    completed: { label: 'FINALIZADO', color: 'bg-gray-500', textColor: 'text-gray-400', bgColor: 'bg-gray-500/10' },
  };
  const config = statusConfig[status];

  return (
    <div className={`p-4 rounded-xl ${config.bgColor} border border-[#1E293B]`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {status === 'active' && <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />}
          <span className="font-semibold text-white">{shift.guard_name}</span>
        </div>
        <Badge className={`${config.color} text-white`}>{config.label}</Badge>
      </div>
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {new Date(shift.start_time).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })} - 
          {new Date(shift.end_time).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
        </div>
        <div className="flex items-center gap-1">
          <MapPin className="w-3 h-3" />
          {shift.location}
        </div>
      </div>
    </div>
  );
};

// ============================================
// ABSENCE REQUEST CARD
// ============================================
const AbsenceCard = ({ absence }) => {
  const statusColors = {
    pending: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    approved: 'bg-green-500/10 text-green-400 border-green-500/30',
    rejected: 'bg-red-500/10 text-red-400 border-red-500/30',
  };

  return (
    <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-white">{absence.employee_name}</span>
        <Badge className={statusColors[absence.status]}>
          {absence.status === 'pending' ? 'Pendiente' : absence.status === 'approved' ? 'Aprobada' : 'Rechazada'}
        </Badge>
      </div>
      <p className="text-sm text-muted-foreground mb-2">{absence.type}: {absence.reason}</p>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Calendar className="w-3 h-3" />
        {absence.start_date} - {absence.end_date}
      </div>
    </div>
  );
};

// ============================================
// SUBMÓDULO: SOLICITUDES DE AUSENCIA
// ============================================
const AusenciasSubmodule = ({ employees }) => {
  // Demo data - en producción vendría de la API
  const [absences] = useState([
    { id: '1', employee_name: 'Juan Pérez', type: 'Vacaciones', reason: 'Viaje familiar', start_date: '2026-02-01', end_date: '2026-02-15', status: 'pending' },
    { id: '2', employee_name: 'María García', type: 'Permiso médico', reason: 'Cita médica', start_date: '2026-01-25', end_date: '2026-01-25', status: 'approved' },
  ]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Solicitudes de Ausencia</h3>
        <Button size="sm">
          <Plus className="w-4 h-4 mr-2" />
          Nueva Solicitud
        </Button>
      </div>
      
      <div className="grid gap-3 sm:grid-cols-2">
        {absences.map(absence => (
          <AbsenceCard key={absence.id} absence={absence} />
        ))}
      </div>

      {absences.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          <CalendarOff className="w-12 h-12 mx-auto mb-2 opacity-30" />
          <p>No hay solicitudes pendientes</p>
        </div>
      )}
    </div>
  );
};

// ============================================
// SUBMÓDULO: CONTROL HORARIO
// ============================================
const ControlHorarioSubmodule = ({ employees, currentUser, hasRole }) => {
  const [isClockedIn, setIsClockedIn] = useState(false);
  const [clockTime, setClockTime] = useState(null);

  const handleClock = () => {
    setIsClockedIn(!isClockedIn);
    setClockTime(new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }));
  };

  return (
    <div className="space-y-6">
      {/* Clock In/Out for Guards */}
      {hasRole('Guarda') && (
        <Card className={`${isClockedIn ? 'bg-green-500/10 border-green-500/30' : 'bg-[#0F111A] border-[#1E293B]'}`}>
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold text-white">
                  {isClockedIn ? '✓ Fichado' : 'Sin fichar'}
                </h3>
                {clockTime && (
                  <p className="text-sm text-muted-foreground">
                    {isClockedIn ? 'Entrada' : 'Salida'}: {clockTime}
                  </p>
                )}
              </div>
              <Button 
                size="lg" 
                className={isClockedIn ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}
                onClick={handleClock}
              >
                {isClockedIn ? (
                  <><LogOutIcon className="w-5 h-5 mr-2" /> Fichar Salida</>
                ) : (
                  <><LogIn className="w-5 h-5 mr-2" /> Fichar Entrada</>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Admin/Supervisor View */}
      {(hasRole('Administrador') || hasRole('Supervisor')) && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Registro de Hoy</h3>
          <div className="grid gap-3">
            {employees.slice(0, 5).map(emp => (
              <div key={emp.id} className="flex items-center justify-between p-3 rounded-lg bg-[#0F111A] border border-[#1E293B]">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-sm font-bold">
                    {emp.user_name?.charAt(0)}
                  </div>
                  <span className="text-white">{emp.user_name}</span>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-green-400">08:00</span>
                  <span className="text-muted-foreground">-</span>
                  <span className="text-red-400">--:--</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================
// SUBMÓDULO: PLANIFICACIÓN DE TURNOS
// ============================================
const TurnosSubmodule = ({ employees, shifts, onCreateShift, isLoading }) => {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newShift, setNewShift] = useState({
    guard_id: '',
    start_time: '',
    end_time: '',
    location: '',
    notes: ''
  });

  const activeShifts = shifts.filter(s => {
    const now = new Date();
    const start = new Date(s.start_time);
    const end = new Date(s.end_time);
    return now >= start && now <= end;
  });

  const handleCreate = async () => {
    await onCreateShift(newShift);
    setCreateDialogOpen(false);
    setNewShift({ guard_id: '', start_time: '', end_time: '', location: '', notes: '' });
  };

  return (
    <div className="space-y-6">
      {/* Active Now Banner */}
      <Card className={activeShifts.length > 0 ? 'bg-green-500/10 border-green-500/30' : 'bg-yellow-500/10 border-yellow-500/30'}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {activeShifts.length > 0 ? (
                <CheckCircle className="w-6 h-6 text-green-400" />
              ) : (
                <AlertCircle className="w-6 h-6 text-yellow-400" />
              )}
              <div>
                <p className={`font-semibold ${activeShifts.length > 0 ? 'text-green-400' : 'text-yellow-400'}`}>
                  {activeShifts.length > 0 ? `${activeShifts.length} guardia(s) en turno` : 'Sin guardias activos'}
                </p>
                <p className="text-sm text-muted-foreground">
                  {activeShifts.length > 0 ? activeShifts.map(s => s.guard_name).join(', ') : 'No hay turnos en este momento'}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Planificación de Turnos</h3>
        <Button onClick={() => setCreateDialogOpen(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Turno
        </Button>
      </div>

      {/* Shifts List */}
      <div className="grid gap-3">
        {shifts.length > 0 ? (
          shifts.map(shift => (
            <ShiftCard key={shift.id} shift={shift} />
          ))
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Calendar className="w-12 h-12 mx-auto mb-2 opacity-30" />
            <p>No hay turnos programados</p>
          </div>
        )}
      </div>

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle>Crear Nuevo Turno</DialogTitle>
            <DialogDescription>Asigna un turno a un empleado</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Empleado</Label>
              <Select value={newShift.guard_id} onValueChange={(v) => setNewShift({...newShift, guard_id: v})}>
                <SelectTrigger className="bg-[#181B25] border-[#1E293B]">
                  <SelectValue placeholder="Seleccionar..." />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  {employees.filter(e => e.is_active).map(emp => (
                    <SelectItem key={emp.id} value={emp.id}>{emp.user_name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Inicio</Label>
                <Input type="datetime-local" value={newShift.start_time} onChange={(e) => setNewShift({...newShift, start_time: e.target.value})} className="bg-[#181B25] border-[#1E293B]" />
              </div>
              <div className="space-y-2">
                <Label>Fin</Label>
                <Input type="datetime-local" value={newShift.end_time} onChange={(e) => setNewShift({...newShift, end_time: e.target.value})} className="bg-[#181B25] border-[#1E293B]" />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Ubicación</Label>
              <Input placeholder="Ej: Entrada Principal" value={newShift.location} onChange={(e) => setNewShift({...newShift, location: e.target.value})} className="bg-[#181B25] border-[#1E293B]" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>Cancelar</Button>
            <Button onClick={handleCreate} disabled={!newShift.guard_id || !newShift.start_time || !newShift.end_time || !newShift.location}>
              Crear Turno
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============================================
// SUBMÓDULO: RECLUTAMIENTO
// ============================================
const ReclutamientoSubmodule = () => {
  const [candidates] = useState([
    { id: '1', name: 'Carlos López', position: 'Guardia', status: 'interview', applied: '2026-01-15' },
    { id: '2', name: 'Ana Martínez', position: 'Supervisor', status: 'applied', applied: '2026-01-18' },
  ]);

  const statusLabels = {
    applied: { label: 'Aplicó', color: 'bg-blue-500/10 text-blue-400' },
    interview: { label: 'Entrevista', color: 'bg-yellow-500/10 text-yellow-400' },
    hired: { label: 'Contratado', color: 'bg-green-500/10 text-green-400' },
    rejected: { label: 'Rechazado', color: 'bg-red-500/10 text-red-400' },
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Pipeline de Reclutamiento</h3>
        <Button size="sm">
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Candidato
        </Button>
      </div>

      <div className="grid gap-3">
        {candidates.map(candidate => (
          <div key={candidate.id} className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-white">{candidate.name}</span>
              <Badge className={statusLabels[candidate.status].color}>
                {statusLabels[candidate.status].label}
              </Badge>
            </div>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>{candidate.position}</span>
              <span>•</span>
              <span>Aplicó: {candidate.applied}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================
// SUBMÓDULO: ONBOARDING/OFFBOARDING
// ============================================
const OnboardingSubmodule = ({ employees }) => (
  <div className="space-y-4">
    <h3 className="text-lg font-semibold">Onboarding / Offboarding</h3>
    
    <div className="grid gap-4 sm:grid-cols-2">
      <Card className="bg-green-500/10 border-green-500/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-base text-green-400">Onboarding Activos</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-3xl font-bold text-white">2</p>
          <p className="text-sm text-muted-foreground">empleados en proceso</p>
        </CardContent>
      </Card>
      
      <Card className="bg-red-500/10 border-red-500/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-base text-red-400">Offboarding Pendientes</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-3xl font-bold text-white">0</p>
          <p className="text-sm text-muted-foreground">por procesar</p>
        </CardContent>
      </Card>
    </div>

    <div className="space-y-3">
      <h4 className="font-medium text-muted-foreground">Empleados Recientes</h4>
      {employees.slice(0, 3).map(emp => (
        <div key={emp.id} className="flex items-center justify-between p-3 rounded-lg bg-[#0F111A] border border-[#1E293B]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
              <UserCheck className="w-4 h-4 text-green-400" />
            </div>
            <span className="text-white">{emp.user_name}</span>
          </div>
          <Badge variant="outline" className="text-green-400 border-green-500/30">Completado</Badge>
        </div>
      ))}
    </div>
  </div>
);

// ============================================
// SUBMÓDULO: EVALUACIÓN DE DESEMPEÑO
// ============================================
const EvaluacionSubmodule = ({ employees }) => (
  <div className="space-y-4">
    <div className="flex items-center justify-between">
      <h3 className="text-lg font-semibold">Evaluaciones de Desempeño</h3>
      <Button size="sm">
        <Plus className="w-4 h-4 mr-2" />
        Nueva Evaluación
      </Button>
    </div>

    <div className="grid gap-3">
      {employees.slice(0, 4).map(emp => (
        <div key={emp.id} className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
          <div className="flex items-center justify-between mb-2">
            <span className="font-semibold text-white">{emp.user_name}</span>
            <div className="flex items-center gap-1">
              {[1,2,3,4,5].map(star => (
                <Star key={star} className={`w-4 h-4 ${star <= 4 ? 'text-yellow-400 fill-yellow-400' : 'text-gray-600'}`} />
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Última evaluación: Dic 2025</span>
            <Button variant="ghost" size="sm" className="h-6 text-xs">Ver historial</Button>
          </div>
        </div>
      ))}
    </div>
  </div>
);

// ============================================
// MAIN RRHH MODULE
// ============================================
const RRHHModule = () => {
  const { user, hasRole, hasAnyRole } = useAuth();
  const isMobile = useIsMobile();
  const [employees, setEmployees] = useState([]);
  const [shifts, setShifts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('turnos');

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      const [employeesData, shiftsData] = await Promise.all([
        api.getGuards(),
        api.getShifts()
      ]);
      setEmployees(employeesData);
      setShifts(shiftsData);
    } catch (error) {
      console.error('Error fetching RRHH data:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Create shift handler
  const handleCreateShift = async (shiftData) => {
    try {
      await api.createShift(shiftData);
      fetchData();
    } catch (error) {
      console.error('Error creating shift:', error);
      alert('Error al crear turno');
    }
  };

  // Filter available submodules based on role
  const availableSubmodules = Object.values(RRHH_SUBMODULES).filter(
    submodule => submodule.roles.some(role => hasRole(role))
  );

  if (isLoading) {
    return (
      <DashboardLayout title="Recursos Humanos">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Recursos Humanos">
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-xl font-bold text-white">Recursos Humanos</h1>
          <p className="text-sm text-muted-foreground">Gestión integral de personal y operaciones</p>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
            <div className="flex items-center gap-2 mb-1">
              <Users className="w-4 h-4 text-blue-400" />
              <span className="text-xs text-muted-foreground">Empleados</span>
            </div>
            <p className="text-2xl font-bold text-white">{employees.length}</p>
          </div>
          <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
            <div className="flex items-center gap-2 mb-1">
              <UserCheck className="w-4 h-4 text-green-400" />
              <span className="text-xs text-muted-foreground">Activos</span>
            </div>
            <p className="text-2xl font-bold text-white">{employees.filter(e => e.is_active).length}</p>
          </div>
          <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
            <div className="flex items-center gap-2 mb-1">
              <Calendar className="w-4 h-4 text-purple-400" />
              <span className="text-xs text-muted-foreground">Turnos Hoy</span>
            </div>
            <p className="text-2xl font-bold text-white">{shifts.length}</p>
          </div>
          <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
            <div className="flex items-center gap-2 mb-1">
              <CalendarOff className="w-4 h-4 text-yellow-400" />
              <span className="text-xs text-muted-foreground">Ausencias</span>
            </div>
            <p className="text-2xl font-bold text-white">2</p>
          </div>
        </div>

        {/* Submodule Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <ScrollArea className="w-full">
            <TabsList className="inline-flex w-max bg-[#0F111A] border border-[#1E293B] p-1">
              {availableSubmodules.map(submodule => {
                const Icon = submodule.icon;
                return (
                  <TabsTrigger 
                    key={submodule.id} 
                    value={submodule.id}
                    className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary whitespace-nowrap"
                  >
                    <Icon className="w-4 h-4 mr-2" />
                    {isMobile ? submodule.shortLabel : submodule.label}
                  </TabsTrigger>
                );
              })}
            </TabsList>
          </ScrollArea>

          {/* Submodule Content */}
          <div className="mt-6">
            <TabsContent value="ausencias">
              <AusenciasSubmodule employees={employees} />
            </TabsContent>

            <TabsContent value="control_horario">
              <ControlHorarioSubmodule employees={employees} currentUser={user} hasRole={hasRole} />
            </TabsContent>

            <TabsContent value="turnos">
              <TurnosSubmodule 
                employees={employees} 
                shifts={shifts} 
                onCreateShift={handleCreateShift}
                isLoading={isLoading}
              />
            </TabsContent>

            <TabsContent value="reclutamiento">
              <ReclutamientoSubmodule />
            </TabsContent>

            <TabsContent value="onboarding">
              <OnboardingSubmodule employees={employees} />
            </TabsContent>

            <TabsContent value="evaluacion">
              <EvaluacionSubmodule employees={employees} />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </DashboardLayout>
  );
};

export default RRHHModule;
