/**
 * GENTURIX - Módulo RRHH (Recursos Humanos)
 * 
 * ENFOQUE: PERSONAS (no operaciones)
 * - Lista de empleados
 * - Datos personales y de contacto
 * - Estado laboral (activo/inactivo)
 * - Historial y acciones administrativas
 * 
 * NO incluye: Turnos, horarios, asignaciones temporales
 * Eso va en el módulo de Turnos (ShiftsModule)
 */

import React, { useState, useEffect } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
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
  Users, 
  UserPlus,
  Phone,
  Mail,
  BadgeCheck,
  Loader2,
  Search,
  MoreVertical,
  UserX,
  UserCheck,
  Edit,
  Briefcase,
  Calendar,
  DollarSign,
  ChevronRight
} from 'lucide-react';
import { useIsMobile } from '../components/layout/BottomNav';

// ============================================
// EMPLOYEE CARD COMPONENT (Mobile-first)
// ============================================
const EmployeeCard = ({ employee, onEdit, onToggleStatus }) => {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B] hover:border-[#2D3B4F] transition-colors">
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className={`
          w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold
          ${employee.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}
        `}>
          {employee.user_name?.charAt(0).toUpperCase() || 'E'}
        </div>

        {/* Info */}
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

          <div className="space-y-1 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <BadgeCheck className="w-3.5 h-3.5" />
              <span className="font-mono">{employee.badge_number}</span>
            </div>
            <div className="flex items-center gap-2">
              <Phone className="w-3.5 h-3.5" />
              <span>{employee.phone}</span>
            </div>
            <div className="flex items-center gap-2">
              <Mail className="w-3.5 h-3.5" />
              <span className="truncate">{employee.email}</span>
            </div>
          </div>
        </div>

        {/* Actions Menu */}
        <div className="relative">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            <MoreVertical className="w-4 h-4" />
          </Button>

          {menuOpen && (
            <>
              <div 
                className="fixed inset-0 z-10" 
                onClick={() => setMenuOpen(false)} 
              />
              <div className="absolute right-0 top-8 z-20 w-48 py-1 rounded-lg bg-[#1E293B] border border-[#2D3B4F] shadow-xl">
                <button
                  onClick={() => { onEdit(employee); setMenuOpen(false); }}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-white/5 flex items-center gap-2"
                >
                  <Edit className="w-4 h-4" />
                  Editar datos
                </button>
                <button
                  onClick={() => { onToggleStatus(employee); setMenuOpen(false); }}
                  className={`w-full px-4 py-2 text-left text-sm hover:bg-white/5 flex items-center gap-2 ${
                    employee.is_active ? 'text-red-400' : 'text-green-400'
                  }`}
                >
                  {employee.is_active ? (
                    <>
                      <UserX className="w-4 h-4" />
                      Desactivar
                    </>
                  ) : (
                    <>
                      <UserCheck className="w-4 h-4" />
                      Activar
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Additional Info Row */}
      <div className="mt-4 pt-3 border-t border-[#1E293B] flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <Calendar className="w-3 h-3" />
          <span>Desde {new Date(employee.hire_date).toLocaleDateString('es-ES', { month: 'short', year: 'numeric' })}</span>
        </div>
        <div className="flex items-center gap-1">
          <DollarSign className="w-3 h-3" />
          <span>${employee.hourly_rate}/hr</span>
        </div>
        <div className="flex items-center gap-1">
          <Briefcase className="w-3 h-3" />
          <span>{employee.total_hours || 0}h trabajadas</span>
        </div>
      </div>
    </div>
  );
};

// ============================================
// STATS CARD COMPONENT
// ============================================
const StatsCard = ({ icon: Icon, label, value, color }) => (
  <div className="p-4 rounded-xl bg-[#0F111A] border border-[#1E293B]">
    <div className="flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg ${color} flex items-center justify-center`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  </div>
);

// ============================================
// MAIN RRHH MODULE
// ============================================
const RRHHModule = () => {
  const isMobile = useIsMobile();
  const [employees, setEmployees] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);

  // Fetch employees (guards)
  const fetchEmployees = async () => {
    try {
      const guards = await api.getGuards();
      setEmployees(guards);
    } catch (error) {
      console.error('Error fetching employees:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployees();
  }, []);

  // Filter employees
  const filteredEmployees = employees.filter(emp => {
    const matchesSearch = 
      emp.user_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.badge_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      emp.email?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = 
      filterStatus === 'all' ||
      (filterStatus === 'active' && emp.is_active) ||
      (filterStatus === 'inactive' && !emp.is_active);

    return matchesSearch && matchesStatus;
  });

  // Stats
  const stats = {
    total: employees.length,
    active: employees.filter(e => e.is_active).length,
    inactive: employees.filter(e => !e.is_active).length,
  };

  // Handle edit
  const handleEdit = (employee) => {
    setSelectedEmployee(employee);
    setEditDialogOpen(true);
  };

  // Handle toggle status
  const handleToggleStatus = async (employee) => {
    // TODO: API call to toggle status
    console.log('Toggle status for:', employee.id);
    // Refresh list
    fetchEmployees();
  };

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
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-white">Gestión de Personal</h1>
            <p className="text-sm text-muted-foreground">Administración de empleados y datos laborales</p>
          </div>
          <Button className="w-full sm:w-auto">
            <UserPlus className="w-4 h-4 mr-2" />
            Agregar Empleado
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          <StatsCard 
            icon={Users} 
            label="Total" 
            value={stats.total} 
            color="bg-blue-500/20 text-blue-400" 
          />
          <StatsCard 
            icon={UserCheck} 
            label="Activos" 
            value={stats.active} 
            color="bg-green-500/20 text-green-400" 
          />
          <StatsCard 
            icon={UserX} 
            label="Inactivos" 
            value={stats.inactive} 
            color="bg-red-500/20 text-red-400" 
          />
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por nombre, badge o email..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 bg-[#0F111A] border-[#1E293B]"
            />
          </div>
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-full sm:w-40 bg-[#0F111A] border-[#1E293B]">
              <SelectValue placeholder="Estado" />
            </SelectTrigger>
            <SelectContent className="bg-[#0F111A] border-[#1E293B]">
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="active">Activos</SelectItem>
              <SelectItem value="inactive">Inactivos</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Employee List */}
        <div className="space-y-3">
          {filteredEmployees.length > 0 ? (
            filteredEmployees.map((employee) => (
              <EmployeeCard
                key={employee.id}
                employee={employee}
                onEdit={handleEdit}
                onToggleStatus={handleToggleStatus}
              />
            ))
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <Users className="w-12 h-12 mx-auto mb-4 opacity-30" />
              <p>No se encontraron empleados</p>
            </div>
          )}
        </div>

        {/* Edit Dialog */}
        <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
          <DialogContent className="bg-[#0F111A] border-[#1E293B]">
            <DialogHeader>
              <DialogTitle>Editar Empleado</DialogTitle>
              <DialogDescription>
                Modifica los datos del empleado
              </DialogDescription>
            </DialogHeader>
            {selectedEmployee && (
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Nombre completo</Label>
                  <Input 
                    defaultValue={selectedEmployee.user_name} 
                    className="bg-[#181B25] border-[#1E293B]"
                    disabled
                  />
                  <p className="text-xs text-muted-foreground">El nombre se edita desde el perfil de usuario</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Teléfono</Label>
                    <Input 
                      defaultValue={selectedEmployee.phone} 
                      className="bg-[#181B25] border-[#1E293B]"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Tarifa/hora</Label>
                    <Input 
                      type="number"
                      defaultValue={selectedEmployee.hourly_rate} 
                      className="bg-[#181B25] border-[#1E293B]"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Contacto de emergencia</Label>
                  <Input 
                    defaultValue={selectedEmployee.emergency_contact} 
                    className="bg-[#181B25] border-[#1E293B]"
                  />
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                Cancelar
              </Button>
              <Button onClick={() => setEditDialogOpen(false)}>
                Guardar Cambios
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  );
};

export default RRHHModule;
