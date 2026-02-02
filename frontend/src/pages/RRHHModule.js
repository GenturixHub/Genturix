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
import { Switch } from '../components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { toast } from 'sonner';
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
import ProfileDirectory from '../components/ProfileDirectory';

// Helper function to get employee name (handles both user_name and name fields)
const getEmployeeName = (emp) => emp?.user_name || emp?.name || emp?.full_name || 'Sin nombre';
import EmbeddedProfile from '../components/EmbeddedProfile';
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
  TrendingUp,
  XCircle,
  User,
  Trash2
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
    roles: ['Administrador', 'Supervisor', 'Guarda', 'HR'],
  },
  control_horario: {
    id: 'control_horario',
    label: 'Control Horario',
    shortLabel: 'Horario',
    icon: Clock,
    description: 'Entrada/salida, ajustes, reportes',
    roles: ['Administrador', 'Supervisor', 'Guarda', 'HR'],
  },
  turnos: {
    id: 'turnos',
    label: 'Planificación de Turnos',
    shortLabel: 'Turnos',
    icon: CalendarDays,
    description: 'Creación, asignación, calendario',
    roles: ['Administrador', 'Supervisor', 'HR'],
  },
  reclutamiento: {
    id: 'reclutamiento',
    label: 'Reclutamiento',
    shortLabel: 'Reclutar',
    icon: UserPlus,
    description: 'Candidatos, pipeline, contratación',
    roles: ['Administrador', 'HR'],
  },
  onboarding: {
    id: 'onboarding',
    label: 'Onboarding / Offboarding',
    shortLabel: 'Onboard',
    icon: ClipboardList,
    description: 'Accesos, equipos, desactivación',
    roles: ['Administrador', 'HR'],
  },
  evaluacion: {
    id: 'evaluacion',
    label: 'Evaluación de Desempeño',
    shortLabel: 'Evaluación',
    icon: TrendingUp,
    description: 'Evaluaciones, feedback, historial',
    roles: ['Administrador', 'Supervisor', 'HR'],
  },
  personas: {
    id: 'personas',
    label: 'Directorio de Personas',
    shortLabel: 'Personas',
    icon: Users,
    description: 'Ver usuarios del condominio',
    roles: ['Administrador', 'Supervisor', 'Guarda', 'HR'],
  },
  mi_perfil: {
    id: 'mi_perfil',
    label: 'Mi Perfil',
    shortLabel: 'Perfil',
    icon: User,
    description: 'Ver y editar mi información',
    roles: ['Administrador', 'Supervisor', 'Guarda', 'HR'],
  },
};

// ============================================
// EMPLOYEE CARD COMPONENT
// ============================================
const EmployeeCard = ({ employee, onEdit }) => (
  <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B] hover:border-[#2D3B4F] transition-colors">
    <div className="flex items-start gap-4">
      <Avatar className={`w-12 h-12 border-2 ${employee.is_active ? 'border-green-500/50' : 'border-red-500/50'}`}>
        <AvatarImage src={employee.profile_photo} />
        <AvatarFallback className={`${employee.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'} text-lg font-bold`}>
          {employee.user_name?.charAt(0).toUpperCase() || employee.name?.charAt(0).toUpperCase() || 'E'}
        </AvatarFallback>
      </Avatar>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="font-semibold text-white truncate">{getEmployeeName(employee)}</h3>
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
      <Button variant="ghost" size="icon" onClick={() => onEdit(employee)} data-testid="edit-employee-btn">
        <Edit className="w-4 h-4" />
      </Button>
    </div>
  </div>
);

// ============================================
// EDIT EMPLOYEE DIALOG (PRIORITY 1 FIX)
// ============================================
const EditEmployeeDialog = ({ employee, open, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    badge_number: '',
    phone: '',
    emergency_contact: '',
    hourly_rate: 0,
    is_active: true
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Load employee data when dialog opens
  useEffect(() => {
    if (employee && open) {
      setForm({
        badge_number: employee.badge_number || '',
        phone: employee.phone || '',
        emergency_contact: employee.emergency_contact || '',
        hourly_rate: employee.hourly_rate || 0,
        is_active: employee.is_active !== false
      });
      setError(null);
    }
  }, [employee, open]);

  const handleSubmit = async () => {
    if (!employee) return;
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      await api.updateGuard(employee.id, {
        badge_number: form.badge_number,
        phone: form.phone,
        emergency_contact: form.emergency_contact,
        hourly_rate: parseFloat(form.hourly_rate) || 0,
        is_active: form.is_active
      });
      onSuccess();
    } catch (err) {
      setError(err.message || 'Error al actualizar empleado');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!employee) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Edit className="w-5 h-5 text-primary" />
            Editar Empleado
          </DialogTitle>
          <DialogDescription>
            {getEmployeeName(employee)} - {employee.email}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              {error}
            </div>
          )}

          <div>
            <Label>Número de Identificación</Label>
            <Input
              value={form.badge_number}
              onChange={(e) => setForm({...form, badge_number: e.target.value})}
              placeholder="GRD-001"
              className="bg-[#0A0A0F] border-[#1E293B] mt-1"
            />
          </div>

          <div>
            <Label>Teléfono</Label>
            <Input
              value={form.phone}
              onChange={(e) => setForm({...form, phone: e.target.value})}
              placeholder="+52 555 123 4567"
              className="bg-[#0A0A0F] border-[#1E293B] mt-1"
            />
          </div>

          <div>
            <Label>Contacto de Emergencia</Label>
            <Input
              value={form.emergency_contact}
              onChange={(e) => setForm({...form, emergency_contact: e.target.value})}
              placeholder="Nombre y teléfono"
              className="bg-[#0A0A0F] border-[#1E293B] mt-1"
            />
          </div>

          <div>
            <Label>Tarifa por Hora (USD)</Label>
            <Input
              type="number"
              step="0.01"
              value={form.hourly_rate}
              onChange={(e) => setForm({...form, hourly_rate: e.target.value})}
              className="bg-[#0A0A0F] border-[#1E293B] mt-1"
            />
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
            <div>
              <p className="font-medium">Estado Activo</p>
              <p className="text-xs text-muted-foreground">El empleado puede trabajar</p>
            </div>
            <Switch
              checked={form.is_active}
              onCheckedChange={(checked) => setForm({...form, is_active: checked})}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CheckCircle className="w-4 h-4 mr-2" />}
            Guardar Cambios
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// COMING SOON BADGE COMPONENT
// ============================================
const ComingSoonBadge = () => (
  <Badge className="bg-yellow-500/10 text-yellow-400 border-yellow-500/30 text-[10px]">
    Próximamente
  </Badge>
);

// ============================================
// SHIFT CARD COMPONENT
// ============================================
const ShiftCard = ({ shift, onDelete }) => {
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
        <div className="flex items-center gap-2">
          <Badge className={`${config.color} text-white`}>{config.label}</Badge>
          {onDelete && status !== 'active' && (
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => onDelete(shift)}
              className="h-6 w-6 p-0 text-red-400 hover:text-red-300 hover:bg-red-500/10"
              title="Eliminar turno"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
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
// SUBMÓDULO: SOLICITUDES DE AUSENCIA (FUNCTIONAL)
// ============================================
const AusenciasSubmodule = ({ employees, onRefresh }) => {
  const [absences, setAbsences] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newAbsence, setNewAbsence] = useState({
    reason: '',
    type: 'vacaciones',
    start_date: '',
    end_date: '',
    notes: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const { hasRole } = useAuth();

  const fetchAbsences = useCallback(async () => {
    try {
      const data = await api.getAbsences();
      setAbsences(data);
    } catch (err) {
      console.error('Error fetching absences:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAbsences();
  }, [fetchAbsences]);

  const handleCreateAbsence = async () => {
    if (!newAbsence.reason || !newAbsence.start_date || !newAbsence.end_date) {
      setError('Completa todos los campos requeridos');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      await api.createAbsence(newAbsence);
      setShowCreateDialog(false);
      setNewAbsence({ reason: '', type: 'vacaciones', start_date: '', end_date: '', notes: '' });
      fetchAbsences();
    } catch (err) {
      setError(err.message || 'Error al crear solicitud');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApprove = async (absenceId) => {
    try {
      await api.approveAbsence(absenceId);
      fetchAbsences();
    } catch (err) {
      alert(err.message || 'Error al aprobar solicitud');
    }
  };

  const handleReject = async (absenceId) => {
    try {
      await api.rejectAbsence(absenceId);
      fetchAbsences();
    } catch (err) {
      alert(err.message || 'Error al rechazar solicitud');
    }
  };

  const typeLabels = {
    vacaciones: { label: 'Vacaciones', color: 'bg-blue-500/10 text-blue-400' },
    permiso_medico: { label: 'Permiso Médico', color: 'bg-cyan-500/10 text-cyan-400' },
    personal: { label: 'Personal', color: 'bg-yellow-500/10 text-yellow-400' },
    otro: { label: 'Otro', color: 'bg-gray-500/10 text-gray-400' }
  };

  const statusLabels = {
    pending: { label: 'Pendiente', color: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30' },
    approved: { label: 'Aprobada', color: 'bg-green-500/10 text-green-400 border-green-500/30' },
    rejected: { label: 'Rechazada', color: 'bg-red-500/10 text-red-400 border-red-500/30' }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Solicitudes de Ausencia</h3>
        <Button size="sm" onClick={() => setShowCreateDialog(true)} data-testid="new-absence-btn">
          <Plus className="w-4 h-4 mr-2" />
          Nueva Solicitud
        </Button>
      </div>

      {absences.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <CalendarOff className="w-12 h-12 mx-auto mb-2 opacity-30" />
          <p>No hay solicitudes de ausencia</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {absences.map(absence => (
            <div key={absence.id} className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className="font-semibold text-white">{absence.employee_name}</p>
                  <Badge className={typeLabels[absence.type]?.color || 'bg-gray-500/10'}>
                    {typeLabels[absence.type]?.label || absence.type}
                  </Badge>
                </div>
                <Badge variant="outline" className={statusLabels[absence.status]?.color}>
                  {statusLabels[absence.status]?.label}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-2">{absence.reason}</p>
              <p className="text-xs text-muted-foreground">
                {absence.start_date} → {absence.end_date}
              </p>
              
              {/* Admin actions */}
              {absence.status === 'pending' && (hasRole('Administrador') || hasRole('Supervisor') || hasRole('HR')) && (
                <div className="flex gap-2 mt-3 pt-3 border-t border-[#1E293B]">
                  <Button size="sm" variant="outline" className="flex-1 text-green-400 border-green-500/30" onClick={() => handleApprove(absence.id)}>
                    <CheckCircle className="w-4 h-4 mr-1" /> Aprobar
                  </Button>
                  <Button size="sm" variant="outline" className="flex-1 text-red-400 border-red-500/30" onClick={() => handleReject(absence.id)}>
                    <XCircle className="w-4 h-4 mr-1" /> Rechazar
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Absence Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle>Nueva Solicitud de Ausencia</DialogTitle>
            <DialogDescription>Solicita vacaciones o permisos</DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">{error}</div>
            )}
            
            <div>
              <Label>Tipo de Ausencia</Label>
              <Select value={newAbsence.type} onValueChange={(v) => setNewAbsence({...newAbsence, type: v})}>
                <SelectTrigger className="bg-[#181B25] border-[#1E293B] mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="vacaciones">Vacaciones</SelectItem>
                  <SelectItem value="permiso_medico">Permiso Médico</SelectItem>
                  <SelectItem value="personal">Personal</SelectItem>
                  <SelectItem value="otro">Otro</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>Motivo *</Label>
              <Input
                value={newAbsence.reason}
                onChange={(e) => setNewAbsence({...newAbsence, reason: e.target.value})}
                placeholder="Describe el motivo..."
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Fecha Inicio *</Label>
                <Input
                  type="date"
                  value={newAbsence.start_date}
                  onChange={(e) => setNewAbsence({...newAbsence, start_date: e.target.value})}
                  className="bg-[#181B25] border-[#1E293B] mt-1"
                />
              </div>
              <div>
                <Label>Fecha Fin *</Label>
                <Input
                  type="date"
                  value={newAbsence.end_date}
                  onChange={(e) => setNewAbsence({...newAbsence, end_date: e.target.value})}
                  className="bg-[#181B25] border-[#1E293B] mt-1"
                />
              </div>
            </div>
            
            <div>
              <Label>Notas Adicionales</Label>
              <Input
                value={newAbsence.notes}
                onChange={(e) => setNewAbsence({...newAbsence, notes: e.target.value})}
                placeholder="Opcional..."
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancelar</Button>
            <Button onClick={handleCreateAbsence} disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Enviar Solicitud
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============================================
// SUBMÓDULO: CONTROL HORARIO (FUNCTIONAL)
// ============================================
const ControlHorarioSubmodule = ({ employees, currentUser, hasRole }) => {
  const [clockStatus, setClockStatus] = useState(null);
  const [clockHistory, setClockHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isClocking, setIsClocking] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [statusData, historyData] = await Promise.all([
        api.getClockStatus(),
        api.getClockHistory()
      ]);
      setClockStatus(statusData);
      setClockHistory(historyData);
    } catch (err) {
      console.error('Error fetching clock data:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleClock = async (type) => {
    setIsClocking(true);
    setError(null);
    setSuccess(null);
    
    try {
      const result = await api.clockInOut(type);
      setSuccess(result.message);
      fetchData();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.message || 'Error al registrar fichaje');
    } finally {
      setIsClocking(false);
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  const isClockedIn = clockStatus?.is_clocked_in || false;

  return (
    <div className="space-y-6">
      {/* Error/Success Messages */}
      {error && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">{error}</div>
      )}
      {success && (
        <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/30 text-green-400">{success}</div>
      )}

      {/* Clock In/Out for Guards */}
      {(hasRole('Guarda') || hasRole('Supervisor')) && (
        <Card className={`${isClockedIn ? 'bg-green-500/10 border-green-500/30' : 'bg-[#0F111A] border-[#1E293B]'}`}>
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold text-white">
                  {isClockedIn ? '✓ Fichado - En Turno' : 'Sin Fichar'}
                </h3>
                {clockStatus?.last_time && (
                  <p className="text-sm text-muted-foreground">
                    Última acción: {clockStatus.last_action === 'IN' ? 'Entrada' : 'Salida'} a las {new Date(clockStatus.last_time).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                )}
              </div>
              <Button 
                size="lg" 
                className={isClockedIn ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}
                onClick={() => handleClock(isClockedIn ? 'OUT' : 'IN')}
                disabled={isClocking}
                data-testid="clock-btn"
              >
                {isClocking ? (
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                ) : isClockedIn ? (
                  <LogOutIcon className="w-5 h-5 mr-2" />
                ) : (
                  <LogIn className="w-5 h-5 mr-2" />
                )}
                {isClockedIn ? 'Fichar Salida' : 'Fichar Entrada'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Today's Logs */}
      {clockStatus?.today_logs && clockStatus.today_logs.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold">Registros de Hoy</h3>
          <div className="grid gap-2">
            {clockStatus.today_logs.map((log, idx) => (
              <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-[#0F111A] border border-[#1E293B]">
                <div className="flex items-center gap-3">
                  {log.type === 'IN' ? (
                    <LogIn className="w-4 h-4 text-green-400" />
                  ) : (
                    <LogOutIcon className="w-4 h-4 text-red-400" />
                  )}
                  <span className={log.type === 'IN' ? 'text-green-400' : 'text-red-400'}>
                    {log.type === 'IN' ? 'Entrada' : 'Salida'}
                  </span>
                </div>
                <span className="text-muted-foreground">
                  {new Date(log.timestamp).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Admin/Supervisor/HR: All Employees Today */}
      {(hasRole('Administrador') || hasRole('Supervisor') || hasRole('HR')) && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Historial Reciente</h3>
          {clockHistory.length === 0 ? (
            <p className="text-muted-foreground text-center py-4">No hay registros</p>
          ) : (
            <div className="grid gap-2">
              {clockHistory.slice(0, 10).map(log => (
                <div key={log.id} className="flex items-center justify-between p-3 rounded-lg bg-[#0F111A] border border-[#1E293B]">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-sm font-bold">
                      {log.employee_name?.charAt(0)}
                    </div>
                    <div>
                      <span className="text-white">{log.employee_name}</span>
                      <Badge className={log.type === 'IN' ? 'ml-2 bg-green-500/10 text-green-400' : 'ml-2 bg-red-500/10 text-red-400'}>
                        {log.type === 'IN' ? 'Entrada' : 'Salida'}
                      </Badge>
                    </div>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {new Date(log.timestamp).toLocaleString('es-ES', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ============================================
// SUBMÓDULO: PLANIFICACIÓN DE TURNOS
// ============================================
const TurnosSubmodule = ({ employees, shifts, onCreateShift, onDeleteShift, isLoading, onEditEmployee }) => {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [shiftToDelete, setShiftToDelete] = useState(null);
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

  const handleDeleteClick = (shift) => {
    setShiftToDelete(shift);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (shiftToDelete && onDeleteShift) {
      await onDeleteShift(shiftToDelete.id);
    }
    setDeleteDialogOpen(false);
    setShiftToDelete(null);
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

      {/* Employees Section */}
      {employees.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold">Empleados</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {employees.map(emp => (
              <EmployeeCard key={emp.id} employee={emp} onEdit={onEditEmployee} />
            ))}
          </div>
        </div>
      )}

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
            <ShiftCard key={shift.id} shift={shift} onDelete={handleDeleteClick} />
          ))
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Calendar className="w-12 h-12 mx-auto mb-2 opacity-30" />
            <p>No hay turnos programados</p>
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-sm">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-400">
              <Trash2 className="w-5 h-5" />
              Eliminar Turno
            </DialogTitle>
            <DialogDescription>
              ¿Estás seguro de eliminar el turno de {shiftToDelete?.guard_name}?
              Esta acción no se puede deshacer.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex-col sm:flex-row gap-2 mt-4">
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancelar
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDeleteConfirm}
              className="bg-red-600 hover:bg-red-700"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
              {employees.filter(e => e.is_active).length === 0 ? (
                <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-sm">
                  <p className="font-medium">No hay empleados disponibles</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Primero debes contratar guardias desde el módulo de Reclutamiento
                  </p>
                </div>
              ) : (
                <Select value={newShift.guard_id} onValueChange={(v) => setNewShift({...newShift, guard_id: v})}>
                  <SelectTrigger className="bg-[#181B25] border-[#1E293B]">
                    <SelectValue placeholder="Seleccionar..." />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                    {employees.filter(e => e.is_active).map(emp => (
                      <SelectItem key={emp.id} value={emp.id}>{getEmployeeName(emp)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
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
// SUBMÓDULO: RECLUTAMIENTO (FUNCTIONAL)
// ============================================
const ReclutamientoSubmodule = ({ onRefresh }) => {
  const [candidates, setCandidates] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showHireDialog, setShowHireDialog] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  
  const [newCandidate, setNewCandidate] = useState({
    full_name: '',
    email: '',
    phone: '',
    position: 'Guarda',
    experience_years: 0,
    notes: ''
  });
  
  const [hireData, setHireData] = useState({
    badge_number: '',
    hourly_rate: 12.0,
    password: ''
  });

  const fetchCandidates = useCallback(async () => {
    try {
      const data = await api.getCandidates();
      setCandidates(data);
    } catch (err) {
      console.error('Error fetching candidates:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCandidates();
  }, [fetchCandidates]);

  const handleCreateCandidate = async () => {
    if (!newCandidate.full_name || !newCandidate.email || !newCandidate.phone) {
      setError('Completa todos los campos requeridos');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      await api.createCandidate(newCandidate);
      setShowCreateDialog(false);
      setNewCandidate({ full_name: '', email: '', phone: '', position: 'Guarda', experience_years: 0, notes: '' });
      setSuccess('Candidato registrado exitosamente');
      fetchCandidates();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.message || 'Error al crear candidato');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateStatus = async (candidateId, newStatus) => {
    try {
      await api.updateCandidate(candidateId, { status: newStatus });
      fetchCandidates();
    } catch (err) {
      alert(err.message || 'Error al actualizar estado');
    }
  };

  const handleHire = async () => {
    if (!hireData.badge_number || !hireData.password) {
      setError('Completa todos los campos de contratación');
      return;
    }
    
    if (hireData.password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      const result = await api.hireCandidate(selectedCandidate.id, hireData);
      setShowHireDialog(false);
      setSelectedCandidate(null);
      setHireData({ badge_number: '', hourly_rate: 12.0, password: '' });
      setSuccess(`${result.message}. Email: ${result.email}`);
      fetchCandidates();
      if (onRefresh) onRefresh();
      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      setError(err.message || 'Error al contratar candidato');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReject = async (candidateId) => {
    if (!window.confirm('¿Estás seguro de rechazar este candidato?')) return;
    
    try {
      await api.rejectCandidate(candidateId);
      fetchCandidates();
    } catch (err) {
      alert(err.message || 'Error al rechazar candidato');
    }
  };

  const openHireDialog = (candidate) => {
    setSelectedCandidate(candidate);
    setShowHireDialog(true);
    setError(null);
  };

  const statusLabels = {
    applied: { label: 'Aplicó', color: 'bg-blue-500/10 text-blue-400 border-blue-500/30' },
    interview: { label: 'Entrevista', color: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30' },
    hired: { label: 'Contratado', color: 'bg-green-500/10 text-green-400 border-green-500/30' },
    rejected: { label: 'Rechazado', color: 'bg-red-500/10 text-red-400 border-red-500/30' }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>;
  }

  return (
    <div className="space-y-4">
      {/* Success/Error Messages */}
      {success && (
        <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/30 text-green-400">{success}</div>
      )}
      {error && !showCreateDialog && !showHireDialog && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">{error}</div>
      )}

      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Pipeline de Reclutamiento</h3>
        <Button size="sm" onClick={() => setShowCreateDialog(true)} data-testid="new-candidate-btn">
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Candidato
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30 text-center">
          <p className="text-2xl font-bold text-blue-400">{candidates.filter(c => c.status === 'applied').length}</p>
          <p className="text-xs text-muted-foreground">Aplicaron</p>
        </div>
        <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/30 text-center">
          <p className="text-2xl font-bold text-yellow-400">{candidates.filter(c => c.status === 'interview').length}</p>
          <p className="text-xs text-muted-foreground">Entrevista</p>
        </div>
        <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/30 text-center">
          <p className="text-2xl font-bold text-green-400">{candidates.filter(c => c.status === 'hired').length}</p>
          <p className="text-xs text-muted-foreground">Contratados</p>
        </div>
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-center">
          <p className="text-2xl font-bold text-red-400">{candidates.filter(c => c.status === 'rejected').length}</p>
          <p className="text-xs text-muted-foreground">Rechazados</p>
        </div>
      </div>

      {/* Candidates List */}
      {candidates.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Briefcase className="w-12 h-12 mx-auto mb-2 opacity-30" />
          <p>No hay candidatos registrados</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {candidates.map(candidate => (
            <div key={candidate.id} className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className="font-semibold text-white">{candidate.full_name}</p>
                  <p className="text-sm text-muted-foreground">{candidate.email}</p>
                </div>
                <Badge variant="outline" className={statusLabels[candidate.status]?.color}>
                  {statusLabels[candidate.status]?.label}
                </Badge>
              </div>
              
              <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                <span>{candidate.position}</span>
                <span>•</span>
                <span>{candidate.experience_years} años exp.</span>
                <span>•</span>
                <span>{candidate.phone}</span>
              </div>
              
              {/* Actions */}
              {candidate.status !== 'hired' && candidate.status !== 'rejected' && (
                <div className="flex gap-2 pt-3 border-t border-[#1E293B]">
                  {candidate.status === 'applied' && (
                    <Button size="sm" variant="outline" className="text-yellow-400 border-yellow-500/30" 
                      onClick={() => handleUpdateStatus(candidate.id, 'interview')}>
                      Marcar Entrevista
                    </Button>
                  )}
                  <Button size="sm" variant="outline" className="text-green-400 border-green-500/30"
                    onClick={() => openHireDialog(candidate)}>
                    <UserCheck className="w-4 h-4 mr-1" /> Contratar
                  </Button>
                  <Button size="sm" variant="outline" className="text-red-400 border-red-500/30"
                    onClick={() => handleReject(candidate.id)}>
                    <UserX className="w-4 h-4 mr-1" /> Rechazar
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Candidate Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle>Nuevo Candidato</DialogTitle>
            <DialogDescription>Registra un nuevo candidato para el proceso de selección</DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {error && showCreateDialog && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">{error}</div>
            )}
            
            <div>
              <Label>Nombre Completo *</Label>
              <Input
                value={newCandidate.full_name}
                onChange={(e) => setNewCandidate({...newCandidate, full_name: e.target.value})}
                placeholder="Juan Pérez"
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
            
            <div>
              <Label>Email *</Label>
              <Input
                type="email"
                value={newCandidate.email}
                onChange={(e) => setNewCandidate({...newCandidate, email: e.target.value})}
                placeholder="candidato@email.com"
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
            
            <div>
              <Label>Teléfono *</Label>
              <Input
                value={newCandidate.phone}
                onChange={(e) => setNewCandidate({...newCandidate, phone: e.target.value})}
                placeholder="+52 555 123 4567"
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Posición</Label>
                <Select value={newCandidate.position} onValueChange={(v) => setNewCandidate({...newCandidate, position: v})}>
                  <SelectTrigger className="bg-[#181B25] border-[#1E293B] mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                    <SelectItem value="Guarda">Guardia</SelectItem>
                    <SelectItem value="Supervisor">Supervisor</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Años de Experiencia</Label>
                <Input
                  type="number"
                  min="0"
                  value={newCandidate.experience_years}
                  onChange={(e) => setNewCandidate({...newCandidate, experience_years: parseInt(e.target.value) || 0})}
                  className="bg-[#181B25] border-[#1E293B] mt-1"
                />
              </div>
            </div>
            
            <div>
              <Label>Notas</Label>
              <Input
                value={newCandidate.notes}
                onChange={(e) => setNewCandidate({...newCandidate, notes: e.target.value})}
                placeholder="Información adicional..."
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>Cancelar</Button>
            <Button onClick={handleCreateCandidate} disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Registrar Candidato
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Hire Candidate Dialog */}
      <Dialog open={showHireDialog} onOpenChange={setShowHireDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle>Contratar Candidato</DialogTitle>
            <DialogDescription>
              {selectedCandidate && `Creando cuenta para ${selectedCandidate.full_name}`}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {error && showHireDialog && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">{error}</div>
            )}
            
            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/30">
              <p className="text-sm text-blue-400">
                Se creará automáticamente una cuenta de usuario con el email: <strong>{selectedCandidate?.email}</strong>
              </p>
            </div>
            
            <div>
              <Label>Número de Identificación *</Label>
              <Input
                value={hireData.badge_number}
                onChange={(e) => setHireData({...hireData, badge_number: e.target.value})}
                placeholder="GRD-003"
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
            
            <div>
              <Label>Tarifa por Hora (USD)</Label>
              <Input
                type="number"
                step="0.01"
                value={hireData.hourly_rate}
                onChange={(e) => setHireData({...hireData, hourly_rate: parseFloat(e.target.value) || 0})}
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
            
            <div>
              <Label>Contraseña Inicial * (mín. 8 caracteres)</Label>
              <Input
                type="password"
                value={hireData.password}
                onChange={(e) => setHireData({...hireData, password: e.target.value})}
                placeholder="••••••••"
                className="bg-[#181B25] border-[#1E293B] mt-1"
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowHireDialog(false)}>Cancelar</Button>
            <Button onClick={handleHire} disabled={isSubmitting} className="bg-green-600 hover:bg-green-700">
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <UserCheck className="w-4 h-4 mr-2" />}
              Confirmar Contratación
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
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
            <span className="text-white">{getEmployeeName(emp)}</span>
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

// Star Rating Component
const StarRating = ({ value, onChange, readonly = false, size = 'md' }) => {
  const sizes = { sm: 'w-4 h-4', md: 'w-5 h-5', lg: 'w-6 h-6' };
  const iconSize = sizes[size] || sizes.md;
  
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map(star => (
        <button
          key={star}
          type="button"
          disabled={readonly}
          onClick={() => !readonly && onChange?.(star)}
          className={`transition-all duration-150 ${readonly ? 'cursor-default' : 'cursor-pointer hover:scale-110'}`}
        >
          <Star 
            className={`${iconSize} ${star <= value ? 'text-yellow-400 fill-yellow-400' : 'text-gray-600'}`}
          />
        </button>
      ))}
    </div>
  );
};

// Create Evaluation Dialog
const CreateEvaluationDialog = ({ open, onClose, employees, onSuccess }) => {
  const [selectedEmployee, setSelectedEmployee] = useState('');
  const [categories, setCategories] = useState({
    discipline: 3,
    punctuality: 3,
    performance: 3,
    communication: 3
  });
  const [comments, setComments] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const categoryLabels = {
    discipline: 'Disciplina',
    punctuality: 'Puntualidad',
    performance: 'Desempeño',
    communication: 'Comunicación'
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedEmployee) return;
    
    setIsSubmitting(true);
    try {
      await api.createEvaluation({
        employee_id: selectedEmployee,
        categories,
        comments: comments.trim() || null
      });
      onSuccess?.();
      onClose();
      // Reset form
      setSelectedEmployee('');
      setCategories({ discipline: 3, punctuality: 3, performance: 3, communication: 3 });
      setComments('');
    } catch (error) {
      console.error('Error creating evaluation:', error);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const avgScore = Object.values(categories).reduce((a, b) => a + b, 0) / 4;
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary" />
            Nueva Evaluación de Desempeño
          </DialogTitle>
          <DialogDescription>
            Evalúa el desempeño de un empleado en diferentes categorías
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label>Empleado a evaluar</Label>
            <Select value={selectedEmployee} onValueChange={setSelectedEmployee}>
              <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] mt-1">
                <SelectValue placeholder="Selecciona un empleado" />
              </SelectTrigger>
              <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                {employees.map(emp => (
                  <SelectItem key={emp.id} value={emp.id}>
                    {getEmployeeName(emp)} - {emp.position || 'Guarda'}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="space-y-3">
            <Label>Calificaciones por Categoría</Label>
            {Object.entries(categoryLabels).map(([key, label]) => (
              <div key={key} className="flex items-center justify-between p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                <span className="text-sm text-muted-foreground">{label}</span>
                <StarRating 
                  value={categories[key]} 
                  onChange={(val) => setCategories(prev => ({ ...prev, [key]: val }))}
                />
              </div>
            ))}
          </div>
          
          <div className="flex items-center justify-between p-3 rounded-lg bg-primary/10 border border-primary/20">
            <span className="text-sm font-medium">Promedio General</span>
            <div className="flex items-center gap-2">
              <StarRating value={Math.round(avgScore)} readonly size="sm" />
              <span className="text-lg font-bold text-primary">{avgScore.toFixed(1)}</span>
            </div>
          </div>
          
          <div>
            <Label>Comentarios (opcional)</Label>
            <textarea
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder="Observaciones sobre el desempeño del empleado..."
              className="w-full mt-1 p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B] text-white text-sm min-h-[80px] resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
            />
          </div>
          
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={!selectedEmployee || isSubmitting}>
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Guardar Evaluación
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

// Evaluation Detail Dialog
const EvaluationDetailDialog = ({ open, onClose, evaluation }) => {
  if (!evaluation) return null;
  
  const categoryLabels = {
    discipline: 'Disciplina',
    punctuality: 'Puntualidad',
    performance: 'Desempeño',
    communication: 'Comunicación'
  };
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        <DialogHeader>
          <DialogTitle>Detalle de Evaluación</DialogTitle>
          <DialogDescription>
            Evaluación de {evaluation.employee_name}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 rounded-lg bg-primary/10 border border-primary/20">
            <div>
              <p className="text-sm text-muted-foreground">Puntuación General</p>
              <p className="text-2xl font-bold text-white">{evaluation.score?.toFixed(1) || 'N/A'}</p>
            </div>
            <StarRating value={Math.round(evaluation.score || 0)} readonly size="lg" />
          </div>
          
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Categorías</p>
            {evaluation.categories && Object.entries(evaluation.categories).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between p-2 rounded-lg bg-[#0A0A0F]">
                <span className="text-sm">{categoryLabels[key] || key}</span>
                <StarRating value={value} readonly size="sm" />
              </div>
            ))}
          </div>
          
          {evaluation.comments && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Comentarios</p>
              <p className="text-sm p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                {evaluation.comments}
              </p>
            </div>
          )}
          
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-muted-foreground">Evaluador</p>
              <p className="font-medium">{evaluation.evaluator_name}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Fecha</p>
              <p className="font-medium">
                {evaluation.created_at ? new Date(evaluation.created_at).toLocaleDateString('es-MX') : 'N/A'}
              </p>
            </div>
          </div>
        </div>
        
        <DialogFooter>
          <Button onClick={onClose}>Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// Employee Evaluation Card (Mobile)
const EmployeeEvaluationCard = ({ employee, evaluations, onViewHistory, onNewEvaluation, canCreate }) => {
  const lastEvaluation = evaluations.find(e => e.employee_id === employee.id);
  const employeeEvaluations = evaluations.filter(e => e.employee_id === employee.id);
  const avgScore = employeeEvaluations.length > 0 
    ? employeeEvaluations.reduce((acc, e) => acc + (e.score || 0), 0) / employeeEvaluations.length 
    : 0;
  
  // Check if employee is evaluable
  const isEvaluable = employee._is_evaluable !== false && employee.user_id;
  
  return (
    <div 
      className={`p-4 rounded-xl border ${
        isEvaluable 
          ? 'bg-[#0F111A] border-[#1E293B]' 
          : 'bg-red-500/5 border-red-500/20'
      }`} 
      data-testid={`eval-card-${employee.id}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
            isEvaluable ? 'bg-primary/20' : 'bg-red-500/20'
          }`}>
            <User className={`w-5 h-5 ${isEvaluable ? 'text-primary' : 'text-red-400'}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="font-semibold text-white">{getEmployeeName(employee)}</p>
              {!isEvaluable && (
                <Badge variant="destructive" className="text-[10px]">No evaluable</Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground">{employee.position || 'Guarda'}</p>
          </div>
        </div>
        <div className="text-right">
          <StarRating value={Math.round(avgScore)} readonly size="sm" />
          <p className="text-xs text-muted-foreground mt-1">
            {employeeEvaluations.length} evaluación{employeeEvaluations.length !== 1 ? 'es' : ''}
          </p>
        </div>
      </div>
      
      {!isEvaluable && (
        <div className="mb-3 p-2 rounded bg-red-500/10 text-xs text-red-400">
          Este empleado no puede ser evaluado: {employee._validation_status === 'invalid_user' ? 'usuario no válido' : 'sin usuario asignado'}
        </div>
      )}
      
      <div className="flex items-center justify-between pt-3 border-t border-[#1E293B]">
        <span className="text-xs text-muted-foreground">
          Última: {lastEvaluation?.created_at 
            ? new Date(lastEvaluation.created_at).toLocaleDateString('es-MX') 
            : 'Sin evaluaciones'}
        </span>
        <div className="flex gap-2">
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-8 text-xs"
            onClick={() => onViewHistory(employee)}
          >
            Ver historial
          </Button>
          {canCreate && isEvaluable && (
            <Button 
              size="sm" 
              className="h-8 text-xs"
              onClick={() => onNewEvaluation(employee)}
            >
              <Plus className="w-3 h-3 mr-1" />
              Evaluar
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

// Employee History Dialog
const EmployeeHistoryDialog = ({ open, onClose, employee, evaluations, onViewDetail }) => {
  if (!employee) return null;
  
  const employeeEvals = evaluations.filter(e => e.employee_id === employee.id);
  const avgScore = employeeEvals.length > 0 
    ? employeeEvals.reduce((acc, e) => acc + (e.score || 0), 0) / employeeEvals.length 
    : 0;
  
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-lg">
        <DialogHeader>
          <DialogTitle>Historial de Evaluaciones</DialogTitle>
          <DialogDescription>
            Evaluaciones de {getEmployeeName(employee)}
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 rounded-lg bg-primary/10 border border-primary/20">
            <div>
              <p className="text-sm text-muted-foreground">Promedio General</p>
              <p className="text-2xl font-bold text-white">{avgScore.toFixed(1)}</p>
            </div>
            <div className="text-right">
              <StarRating value={Math.round(avgScore)} readonly />
              <p className="text-xs text-muted-foreground mt-1">{employeeEvals.length} evaluaciones</p>
            </div>
          </div>
          
          <ScrollArea className="h-[300px]">
            {employeeEvals.length > 0 ? (
              <div className="space-y-2">
                {employeeEvals.map(evaluation => (
                  <div 
                    key={evaluation.id} 
                    className="p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B] cursor-pointer hover:border-primary/50 transition-colors"
                    onClick={() => onViewDetail(evaluation)}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium">
                          {new Date(evaluation.created_at).toLocaleDateString('es-MX', { 
                            year: 'numeric', month: 'long', day: 'numeric' 
                          })}
                        </p>
                        <p className="text-xs text-muted-foreground">Por: {evaluation.evaluator_name}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StarRating value={Math.round(evaluation.score || 0)} readonly size="sm" />
                        <span className="text-lg font-bold text-primary">{evaluation.score?.toFixed(1)}</span>
                      </div>
                    </div>
                    {evaluation.comments && (
                      <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                        &quot;{evaluation.comments}&quot;
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <Star className="w-12 h-12 mb-3 opacity-30" />
                <p>No hay evaluaciones registradas</p>
              </div>
            )}
          </ScrollArea>
        </div>
        
        <DialogFooter>
          <Button onClick={onClose}>Cerrar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// Main Evaluation Submodule
const EvaluacionSubmodule = ({ employees: propEmployees, canCreate = true }) => {
  const isMobile = useIsMobile();
  const [evaluations, setEvaluations] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [showHistoryDialog, setShowHistoryDialog] = useState(false);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [selectedEvaluation, setSelectedEvaluation] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  
  const fetchData = useCallback(async () => {
    try {
      const [evaluationsData, employeesData] = await Promise.all([
        api.getEvaluations(),
        api.getEvaluableEmployees().catch(() => propEmployees || [])
      ]);
      setEvaluations(evaluationsData);
      // Use evaluable employees if available, fallback to prop employees
      setEmployees(employeesData.length > 0 ? employeesData : propEmployees);
    } catch (error) {
      console.error('Error fetching evaluations:', error);
      setEmployees(propEmployees || []);
    } finally {
      setIsLoading(false);
    }
  }, [propEmployees]);
  
  useEffect(() => {
    fetchData();
  }, [fetchData]);
  
  const handleViewHistory = (employee) => {
    setSelectedEmployee(employee);
    setShowHistoryDialog(true);
  };
  
  const handleNewEvaluation = (employee) => {
    if (employee) {
      setSelectedEmployee(employee);
    }
    setShowCreateDialog(true);
  };
  
  const handleViewDetail = (evaluation) => {
    setSelectedEvaluation(evaluation);
    setShowDetailDialog(true);
  };
  
  const filteredEmployees = employees.filter(emp => 
    getEmployeeName(emp).toLowerCase().includes(searchTerm.toLowerCase()) ||
    emp.position?.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  // Stats
  const totalEvaluations = evaluations.length;
  const avgOverall = totalEvaluations > 0 
    ? evaluations.reduce((acc, e) => acc + (e.score || 0), 0) / totalEvaluations 
    : 0;
  const evaluatedEmployees = new Set(evaluations.map(e => e.employee_id)).size;
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row gap-3 justify-between">
        <h3 className="text-lg font-semibold">Evaluaciones de Desempeño</h3>
        {canCreate && (
          <Button size="sm" onClick={() => setShowCreateDialog(true)} className="w-full sm:w-auto">
            <Plus className="w-4 h-4 mr-2" />
            Nueva Evaluación
          </Button>
        )}
      </div>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <FileText className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totalEvaluations}</p>
                <p className="text-xs text-muted-foreground">Evaluaciones</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-yellow-500/20 flex items-center justify-center">
                <Star className="w-5 h-5 text-yellow-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{avgOverall.toFixed(1)}</p>
                <p className="text-xs text-muted-foreground">Promedio</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                <UserCheck className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{evaluatedEmployees}</p>
                <p className="text-xs text-muted-foreground">Evaluados</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                <Users className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{employees.length}</p>
                <p className="text-xs text-muted-foreground">Empleados</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          placeholder="Buscar empleado..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10 bg-[#0A0A0F] border-[#1E293B]"
        />
      </div>
      
      {/* Employee List - Cards on mobile, Grid on desktop */}
      <div className={isMobile ? "space-y-3" : "grid gap-3 md:grid-cols-2 lg:grid-cols-3"}>
        {filteredEmployees.length > 0 ? (
          filteredEmployees.map(emp => (
            <EmployeeEvaluationCard
              key={emp.id}
              employee={emp}
              evaluations={evaluations}
              onViewHistory={handleViewHistory}
              onNewEvaluation={handleNewEvaluation}
              canCreate={canCreate}
            />
          ))
        ) : (
          <div className="col-span-full flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Users className="w-12 h-12 mb-3 opacity-30" />
            <p>No se encontraron empleados</p>
          </div>
        )}
      </div>
      
      {/* Dialogs */}
      <CreateEvaluationDialog
        open={showCreateDialog}
        onClose={() => { setShowCreateDialog(false); setSelectedEmployee(null); }}
        employees={employees}
        onSuccess={fetchData}
      />
      
      <EmployeeHistoryDialog
        open={showHistoryDialog}
        onClose={() => { setShowHistoryDialog(false); setSelectedEmployee(null); }}
        employee={selectedEmployee}
        evaluations={evaluations}
        onViewDetail={handleViewDetail}
      />
      
      <EvaluationDetailDialog
        open={showDetailDialog}
        onClose={() => { setShowDetailDialog(false); setSelectedEvaluation(null); }}
        evaluation={selectedEvaluation}
      />
    </div>
  );
};

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
  const [editingEmployee, setEditingEmployee] = useState(null);
  const [showEditSuccess, setShowEditSuccess] = useState(false);

  // Fetch data
  const fetchData = useCallback(async () => {
    try {
      const [employeesData, shiftsData] = await Promise.all([
        api.getGuards(),
        api.getShifts()
      ]);
      setEmployees(employeesData);
      // Filter out cancelled shifts - they should not appear in the UI
      const activeShifts = shiftsData.filter(s => s.status !== 'cancelled');
      setShifts(activeShifts);
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
      toast.success('Turno creado exitosamente');
      fetchData();
    } catch (error) {
      console.error('Error creating shift:', error);
      // Show specific error message from backend
      const errorMsg = error.message || 'Error al crear turno';
      toast.error(errorMsg);
    }
  };

  // Delete shift handler
  const handleDeleteShift = async (shiftId) => {
    try {
      await api.deleteShift(shiftId);
      toast.success('Turno eliminado');
      fetchData();
    } catch (error) {
      console.error('Error deleting shift:', error);
      toast.error(error.message || 'Error al eliminar turno');
    }
  };

  // Edit employee handler
  const handleEditEmployee = (employee) => {
    setEditingEmployee(employee);
  };

  // Edit success handler
  const handleEditSuccess = () => {
    setEditingEmployee(null);
    setShowEditSuccess(true);
    fetchData();
    setTimeout(() => setShowEditSuccess(false), 3000);
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
        {/* Success Toast */}
        {showEditSuccess && (
          <div className="fixed top-4 right-4 z-50 p-4 rounded-lg bg-green-500/20 border border-green-500/30 text-green-400 flex items-center gap-2 animate-in slide-in-from-top-2">
            <CheckCircle className="w-5 h-5" />
            Empleado actualizado correctamente
          </div>
        )}

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
              <Calendar className="w-4 h-4 text-cyan-400" />
              <span className="text-xs text-muted-foreground">Turnos Hoy</span>
            </div>
            <p className="text-2xl font-bold text-white">{shifts.length}</p>
          </div>
          <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
            <div className="flex items-center gap-2 mb-1">
              <CalendarOff className="w-4 h-4 text-yellow-400" />
              <span className="text-xs text-muted-foreground">Ausencias</span>
            </div>
            <p className="text-2xl font-bold text-white">--</p>
          </div>
        </div>

        {/* Submodule Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          {/* Mobile-friendly horizontal scroll container */}
          <div 
            className="w-full overflow-x-auto overflow-y-hidden scrollbar-hide mobile-scroll-tabs pb-2" 
            style={{ WebkitOverflowScrolling: 'touch' }}
          >
            <TabsList className="inline-flex w-max bg-[#0F111A] border border-[#1E293B] p-1">
              {availableSubmodules.map(submodule => {
                const Icon = submodule.icon;
                return (
                  <TabsTrigger 
                    key={submodule.id} 
                    value={submodule.id}
                    className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary whitespace-nowrap flex-shrink-0"
                    data-testid={`rrhh-tab-${submodule.id}`}
                  >
                    <Icon className="w-4 h-4 mr-2" />
                    {isMobile ? submodule.shortLabel : submodule.label}
                  </TabsTrigger>
                );
              })}
            </TabsList>
          </div>

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
                onDeleteShift={handleDeleteShift}
                isLoading={isLoading}
                onEditEmployee={handleEditEmployee}
              />
            </TabsContent>

            <TabsContent value="reclutamiento">
              <ReclutamientoSubmodule onRefresh={fetchData} />
            </TabsContent>

            <TabsContent value="onboarding">
              <OnboardingSubmodule employees={employees} />
            </TabsContent>

            <TabsContent value="evaluacion">
              <EvaluacionSubmodule 
                employees={employees} 
                canCreate={hasAnyRole('Administrador', 'Supervisor', 'HR')}
              />
            </TabsContent>

            <TabsContent value="personas">
              <ProfileDirectory embedded={false} maxHeight="calc(100vh - 300px)" />
            </TabsContent>

            <TabsContent value="mi_perfil">
              <EmbeddedProfile />
            </TabsContent>
          </div>
        </Tabs>

        {/* Edit Employee Dialog */}
        <EditEmployeeDialog
          employee={editingEmployee}
          open={!!editingEmployee}
          onClose={() => setEditingEmployee(null)}
          onSuccess={handleEditSuccess}
        />
      </div>
    </DashboardLayout>
  );
};

export default RRHHModule;
