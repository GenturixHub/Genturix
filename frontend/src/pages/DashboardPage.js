import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useModules } from '../contexts/ModulesContext';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
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
import { useIsMobile } from '../components/layout/BottomNav';
import api from '../services/api';
import { 
  Users, 
  Shield, 
  AlertTriangle, 
  GraduationCap,
  CreditCard,
  Activity,
  TrendingUp,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  ChevronRight,
  UserPlus,
  Wallet,
  AlertCircle,
  ArrowUpRight,
  LogOut,
  Calendar
} from 'lucide-react';

const StatCard = ({ title, value, icon: Icon, trend, color = 'primary', onClick }) => {
  const colorClasses = {
    primary: 'bg-primary/10 text-primary',
    success: 'bg-green-500/10 text-green-400',
    warning: 'bg-yellow-500/10 text-yellow-400',
    error: 'bg-red-500/10 text-red-400',
    info: 'bg-blue-500/10 text-blue-400',
  };

  return (
    <Card 
      className={`grid-card ${onClick ? 'cursor-pointer hover:border-primary' : ''}`}
      onClick={onClick}
    >
      <CardContent className="p-4 md:p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 md:block">
            <div className={`w-10 h-10 md:w-12 md:h-12 rounded-lg ${colorClasses[color]} flex items-center justify-center md:mb-3`}>
              <Icon className="w-5 h-5 md:w-6 md:h-6" />
            </div>
            <div>
              <p className="text-xs md:text-sm text-muted-foreground">{title}</p>
              <p className="text-xl md:text-3xl font-bold font-['Outfit']">{value}</p>
            </div>
          </div>
          {trend && (
            <div className="flex items-center gap-1 text-xs text-green-400">
              <TrendingUp className="w-3 h-3" />
              <span>{trend}</span>
            </div>
          )}
          {onClick && (
            <ChevronRight className="w-5 h-5 text-muted-foreground md:hidden" />
          )}
        </div>
      </CardContent>
    </Card>
  );
};

const ActivityItem = ({ activity }) => {
  const getIcon = (type) => {
    switch (type) {
      case 'login_success':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'login_failure':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'panic_button':
      case 'panic_alert':
        return <AlertTriangle className="w-4 h-4 text-red-400" />;
      case 'visitor_checkin':
        return <UserPlus className="w-4 h-4 text-green-400" />;
      case 'visitor_checkout':
        return <LogOut className="w-4 h-4 text-orange-400" />;
      case 'reservation_created':
        return <Calendar className="w-4 h-4 text-cyan-400" />;
      case 'user_created':
        return <UserPlus className="w-4 h-4 text-blue-400" />;
      default:
        return <Activity className="w-4 h-4 text-blue-400" />;
    }
  };

  const getModuleColor = (module) => {
    switch (module) {
      case 'security': return 'text-red-400';
      case 'reservations': return 'text-purple-400';
      case 'auth': return 'text-green-400';
      case 'visitor': return 'text-blue-400';
      default: return 'text-muted-foreground';
    }
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Ahora';
    if (diffMins < 60) return `${diffMins}m`;
    if (diffMins < 1440) return `${Math.floor(diffMins/60)}h`;
    return date.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
  };

  const getEventLabel = (type) => {
    const labels = {
      'login_success': 'Inicio de sesión',
      'login_failure': 'Intento fallido',
      'logout': 'Cerró sesión',
      'panic_alert': 'Alerta de pánico',
      'visitor_checkin': 'Check-in visitante',
      'visitor_checkout': 'Check-out visitante',
      'reservation_created': 'Nueva reservación',
      'user_created': 'Usuario creado'
    };
    return labels[type] || type?.replace(/_/g, ' ');
  };

  return (
    <div className="flex items-center gap-3 py-3 border-b border-[#1E293B] last:border-0">
      <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
        {getIcon(activity.event_type)}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm truncate">
          {activity.description || getEventLabel(activity.event_type)}
        </p>
        <p className={`text-xs ${getModuleColor(activity.module)}`}>
          {activity.user_name || activity.module}
        </p>
      </div>
      <span className="text-xs text-muted-foreground whitespace-nowrap">
        {formatTime(activity.timestamp)}
      </span>
    </div>
  );
};

// ============================================
// CREATE USER DIALOG
// ============================================
const CreateUserDialog = ({ open, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    email: '',
    password: '',
    full_name: '',
    role: '',
    phone: '',
    // Role-specific fields
    badge_number: '',        // Guarda
    apartment_number: '',    // Residente
    tower_block: '',         // Residente
    resident_type: 'owner',  // Residente
    department: '',          // HR
    supervised_area: ''      // Supervisor
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const ROLES = [
    { value: 'Residente', label: 'Residente', description: 'Acceso a pánico y visitas' },
    { value: 'Guarda', label: 'Guarda', description: 'Panel de seguridad y alertas' },
    { value: 'HR', label: 'Recursos Humanos', description: 'Gestión de personal y reclutamiento' },
    { value: 'Supervisor', label: 'Supervisor', description: 'Supervisión de turnos y empleados' },
    { value: 'Estudiante', label: 'Estudiante', description: 'Acceso a Genturix School' }
  ];

  // Reset role-specific fields when role changes
  const handleRoleChange = (newRole) => {
    setForm({ 
      ...form, 
      role: newRole, 
      badge_number: '',
      apartment_number: '',
      tower_block: '',
      resident_type: 'owner',
      department: '',
      supervised_area: ''
    });
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.email || !form.password || !form.full_name || !form.role) {
      setError('Por favor complete todos los campos obligatorios');
      return;
    }
    
    // Validation for Guard role
    if (form.role === 'Guarda' && !form.badge_number) {
      setError('El número de placa es requerido para usuarios con rol Guarda');
      return;
    }
    
    // Validation for Resident role
    if (form.role === 'Residente' && !form.apartment_number) {
      setError('El número de apartamento/casa es requerido para usuarios con rol Residente');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      // Build payload with role-specific fields
      const payload = {
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        role: form.role,
        phone: form.phone || null
      };
      
      // Add role-specific fields
      if (form.role === 'Guarda') {
        payload.badge_number = form.badge_number;
      } else if (form.role === 'Residente') {
        payload.apartment_number = form.apartment_number;
        payload.tower_block = form.tower_block || null;
        payload.resident_type = form.resident_type || 'owner';
      } else if (form.role === 'HR') {
        payload.department = form.department || 'Recursos Humanos';
      } else if (form.role === 'Supervisor') {
        payload.supervised_area = form.supervised_area || 'General';
      }
      
      const result = await api.createUserByAdmin(payload);
      setSuccess(`Usuario ${form.full_name} creado exitosamente`);
      setTimeout(() => {
        setForm({ 
          email: '', password: '', full_name: '', role: '', phone: '', 
          badge_number: '', apartment_number: '', tower_block: '', resident_type: 'owner',
          department: '', supervised_area: ''
        });
        setSuccess(null);
        onSuccess?.();
        onClose();
      }, 2000);
    } catch (err) {
      // Show the specific backend error message
      const errorMsg = err.data?.detail || err.message || 'Error al crear usuario';
      setError(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const generatePassword = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$';
    let password = '';
    for (let i = 0; i < 12; i++) {
      password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setForm({ ...form, password });
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-primary" />
            Crear Nuevo Usuario
          </DialogTitle>
          <DialogDescription>
            Crea un usuario para tu condominio. Se asignará automáticamente a tu organización.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}
          
          {success && (
            <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              {success}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="full_name">Nombre Completo *</Label>
            <Input
              id="full_name"
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              placeholder="Juan Pérez"
              className="bg-[#0A0A0F] border-[#1E293B]"
              required
              data-testid="create-user-name"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email *</Label>
            <Input
              id="email"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="usuario@ejemplo.com"
              className="bg-[#0A0A0F] border-[#1E293B]"
              required
              data-testid="create-user-email"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Contraseña *</Label>
            <div className="flex gap-2">
              <Input
                id="password"
                type="text"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                placeholder="Mínimo 8 caracteres"
                className="bg-[#0A0A0F] border-[#1E293B] flex-1"
                required
                minLength={8}
                data-testid="create-user-password"
              />
              <Button type="button" variant="outline" size="sm" onClick={generatePassword}>
                Generar
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="role">Rol *</Label>
            <Select value={form.role} onValueChange={handleRoleChange}>
              <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]" data-testid="create-user-role">
                <SelectValue placeholder="Selecciona un rol" />
              </SelectTrigger>
              <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                {ROLES.map((role) => (
                  <SelectItem key={role.value} value={role.value}>
                    <div className="flex flex-col">
                      <span>{role.label}</span>
                      <span className="text-xs text-muted-foreground">{role.description}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Badge Number field - only for Guarda role */}
          {form.role === 'Guarda' && (
            <div className="space-y-2">
              <Label htmlFor="badge_number">Número de Placa *</Label>
              <Input
                id="badge_number"
                value={form.badge_number}
                onChange={(e) => setForm({ ...form, badge_number: e.target.value })}
                placeholder="Ej: G-001"
                className="bg-[#0A0A0F] border-[#1E293B]"
                required
                data-testid="create-user-badge"
              />
              <p className="text-xs text-muted-foreground">
                Identificador único del guardia para registros y reportes
              </p>
            </div>
          )}

          {/* Residente-specific fields */}
          {form.role === 'Residente' && (
            <>
              <div className="space-y-2">
                <Label htmlFor="apartment_number">Número de Apartamento/Casa *</Label>
                <Input
                  id="apartment_number"
                  value={form.apartment_number}
                  onChange={(e) => setForm({ ...form, apartment_number: e.target.value })}
                  placeholder="Ej: A-101, Casa 15"
                  className="bg-[#0A0A0F] border-[#1E293B]"
                  required
                  data-testid="create-user-apartment"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="tower_block">Torre/Bloque</Label>
                  <Input
                    id="tower_block"
                    value={form.tower_block}
                    onChange={(e) => setForm({ ...form, tower_block: e.target.value })}
                    placeholder="Ej: Torre A"
                    className="bg-[#0A0A0F] border-[#1E293B]"
                    data-testid="create-user-tower"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="resident_type">Tipo</Label>
                  <Select value={form.resident_type} onValueChange={(v) => setForm({ ...form, resident_type: v })}>
                    <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]" data-testid="create-user-resident-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                      <SelectItem value="owner">Propietario</SelectItem>
                      <SelectItem value="tenant">Inquilino</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </>
          )}

          {/* HR-specific fields */}
          {form.role === 'HR' && (
            <div className="space-y-2">
              <Label htmlFor="department">Departamento</Label>
              <Input
                id="department"
                value={form.department}
                onChange={(e) => setForm({ ...form, department: e.target.value })}
                placeholder="Recursos Humanos"
                className="bg-[#0A0A0F] border-[#1E293B]"
                data-testid="create-user-department"
              />
            </div>
          )}

          {/* Supervisor-specific fields */}
          {form.role === 'Supervisor' && (
            <div className="space-y-2">
              <Label htmlFor="supervised_area">Área Supervisada</Label>
              <Input
                id="supervised_area"
                value={form.supervised_area}
                onChange={(e) => setForm({ ...form, supervised_area: e.target.value })}
                placeholder="Ej: Seguridad, Mantenimiento"
                className="bg-[#0A0A0F] border-[#1E293B]"
                data-testid="create-user-area"
              />
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="phone">Teléfono (opcional)</Label>
            <Input
              id="phone"
              type="tel"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              placeholder="+1234567890"
              className="bg-[#0A0A0F] border-[#1E293B]"
              data-testid="create-user-phone"
            />
          </div>

          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isSubmitting} data-testid="create-user-submit">
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Creando...
                </>
              ) : (
                <>
                  <UserPlus className="w-4 h-4 mr-2" />
                  Crear Usuario
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

const DashboardPage = () => {
  const navigate = useNavigate();
  const { user, hasRole } = useAuth();
  const { isModuleEnabled } = useModules();
  const isMobile = useIsMobile();
  const [stats, setStats] = useState(null);
  const [activities, setActivities] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateUser, setShowCreateUser] = useState(false);
  // SaaS Billing State
  const [billingInfo, setBillingInfo] = useState(null);
  const [showUpgradeDialog, setShowUpgradeDialog] = useState(false);
  const [additionalSeats, setAdditionalSeats] = useState(10);
  const [isUpgrading, setIsUpgrading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsData, activityData, billingData] = await Promise.all([
          api.getDashboardStats(),
          api.getRecentActivity(),
          api.getBillingInfo().catch(() => null) // Don't fail if billing not available
        ]);
        setStats(statsData);
        setActivities(activityData);
        setBillingInfo(billingData);
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, []);

  // Handle seat upgrade
  const handleUpgradeSeats = async () => {
    if (additionalSeats < 1) return;
    
    setIsUpgrading(true);
    try {
      const result = await api.upgradeSeats(additionalSeats);
      if (result.url) {
        window.location.href = result.url;
      }
    } catch (error) {
      console.error('Error creating upgrade checkout:', error);
      alert(error.message || 'Error al procesar la actualización');
    } finally {
      setIsUpgrading(false);
    }
  };

  // Check if can create users based on billing
  const canCreateUsers = billingInfo?.can_create_users !== false;
  const isAtSeatLimit = billingInfo && billingInfo.remaining_seats <= 0;
  const billingStatusWarning = billingInfo?.billing_status && !['active', 'trialing'].includes(billingInfo.billing_status);

  if (isLoading) {
    return (
      <DashboardLayout title="Dashboard">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Dashboard">
      <div className="space-y-4 md:space-y-6">
        {/* Welcome - Mobile compact */}
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-xl md:text-2xl font-bold font-['Outfit']">
              {isMobile ? `Hola, ${user?.full_name?.split(' ')[0]}` : `Bienvenido, ${user?.full_name}`}
            </h2>
            <p className="text-sm text-muted-foreground">
              Panel de control GENTURIX
            </p>
          </div>
        </div>

        {/* Billing Warning Banner */}
        {hasRole('Administrador') && (isAtSeatLimit || billingStatusWarning) && (
          <Card className={`border-2 ${isAtSeatLimit ? 'border-yellow-500/50 bg-yellow-500/5' : 'border-red-500/50 bg-red-500/5'}`}>
            <CardContent className="py-3 px-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <AlertCircle className={`w-5 h-5 ${isAtSeatLimit ? 'text-yellow-400' : 'text-red-400'}`} />
                  <div>
                    <p className={`font-medium ${isAtSeatLimit ? 'text-yellow-400' : 'text-red-400'}`}>
                      {isAtSeatLimit 
                        ? `Límite de usuarios alcanzado (${billingInfo?.active_users}/${billingInfo?.paid_seats})` 
                        : `Suscripción ${billingInfo?.billing_status}`}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {isAtSeatLimit 
                        ? 'No puedes crear más usuarios. Actualiza tu plan para agregar más.' 
                        : 'Por favor actualiza tu método de pago para continuar creando usuarios.'}
                    </p>
                  </div>
                </div>
                <Button
                  size="sm"
                  className="bg-primary hover:bg-primary/90"
                  onClick={() => setShowUpgradeDialog(true)}
                >
                  Actualizar Plan
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats Grid - 2 columns on mobile, 4 on desktop */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          <StatCard
            title="Usuarios"
            value={stats?.total_users || 0}
            icon={Users}
            color="primary"
            onClick={() => navigate('/hr')}
          />
          <StatCard
            title="Guardas"
            value={stats?.active_guards || 0}
            icon={Shield}
            color="success"
            onClick={() => navigate('/hr')}
          />
          <StatCard
            title="Alertas"
            value={stats?.active_alerts || 0}
            icon={AlertTriangle}
            color={stats?.active_alerts > 0 ? 'error' : 'success'}
            onClick={() => navigate('/security')}
          />
          <StatCard
            title="Cursos"
            value={stats?.total_courses || 0}
            icon={GraduationCap}
            color="info"
            onClick={() => navigate('/school')}
          />
        </div>

        {/* Main Content - Stack on mobile */}
        <div className="grid gap-4 md:gap-6 md:grid-cols-3">
          {/* Recent Activity */}
          <Card className="grid-card md:col-span-2">
            <CardHeader className="pb-2 md:pb-4">
              <CardTitle className="text-base md:text-lg flex items-center gap-2">
                <Activity className="w-4 h-4 md:w-5 md:h-5 text-primary" />
                Actividad Reciente
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 md:p-6 md:pt-0">
              <ScrollArea className={isMobile ? 'h-[250px]' : 'h-[350px]'}>
                <div className="px-4 md:px-0">
                  {activities.length > 0 ? (
                    activities.slice(0, isMobile ? 8 : 15).map((activity, index) => (
                      <ActivityItem key={activity.id || index} activity={activity} />
                    ))
                  ) : (
                    <p className="text-center text-muted-foreground py-8">
                      Sin actividad reciente
                    </p>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card className="grid-card">
            <CardHeader className="pb-2 md:pb-4">
              <CardTitle className="text-base md:text-lg">Accesos Rápidos</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 md:space-y-3">
              {hasRole('Administrador') && (
                <>
                  <div className="relative group">
                    <Button
                      className={`w-full justify-between h-12 ${canCreateUsers ? 'bg-primary hover:bg-primary/90' : 'bg-gray-600 cursor-not-allowed opacity-60'}`}
                      onClick={() => canCreateUsers ? setShowCreateUser(true) : setShowUpgradeDialog(true)}
                      data-testid="create-user-btn"
                    >
                      <span className="flex items-center gap-3">
                        <UserPlus className="w-4 h-4" />
                        Crear Usuario
                        {!canCreateUsers && <AlertCircle className="w-4 h-4 text-yellow-400" />}
                      </span>
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                    {!canCreateUsers && (
                      <div className="absolute bottom-full left-0 right-0 mb-2 p-2 bg-gray-800 rounded text-xs text-center opacity-0 group-hover:opacity-100 transition-opacity z-50">
                        Límite de usuarios alcanzado. Actualiza tu plan.
                      </div>
                    )}
                  </div>
                  
                  {/* Billing & Plan Button */}
                  <Button
                    variant="outline"
                    className="w-full justify-between h-12 border-[#1E293B] hover:bg-muted"
                    onClick={() => setShowUpgradeDialog(true)}
                    data-testid="billing-btn"
                  >
                    <span className="flex items-center gap-3">
                      <Wallet className="w-4 h-4 text-emerald-400" />
                      Plan y Facturación
                      {billingInfo && (
                        <span className="text-xs text-muted-foreground">
                          ({billingInfo.active_users}/{billingInfo.paid_seats})
                        </span>
                      )}
                    </span>
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                  
                  {isModuleEnabled('security') && (
                    <Button
                      variant="outline"
                      className="w-full justify-between h-12 border-[#1E293B] hover:bg-muted"
                      onClick={() => navigate('/security')}
                    >
                      <span className="flex items-center gap-3">
                        <Shield className="w-4 h-4 text-primary" />
                        Seguridad
                      </span>
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  )}
                  {isModuleEnabled('hr') && (
                    <Button
                      variant="outline"
                      className="w-full justify-between h-12 border-[#1E293B] hover:bg-muted"
                      onClick={() => navigate('/hr')}
                    >
                      <span className="flex items-center gap-3">
                        <Users className="w-4 h-4 text-blue-400" />
                        Recursos Humanos
                      </span>
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  )}
                  {isModuleEnabled('audit') && (
                    <Button
                      variant="outline"
                      className="w-full justify-between h-12 border-[#1E293B] hover:bg-muted"
                      onClick={() => navigate('/audit')}
                    >
                      <span className="flex items-center gap-3">
                        <Activity className="w-4 h-4 text-yellow-400" />
                        Auditoría
                      </span>
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  )}
                </>
              )}
              
              {isModuleEnabled('school') && (
                <Button
                  variant="outline"
                  className="w-full justify-between h-12 border-[#1E293B] hover:bg-muted"
                  onClick={() => navigate('/school')}
                >
                  <span className="flex items-center gap-3">
                    <GraduationCap className="w-4 h-4 text-green-400" />
                    Genturix School
                  </span>
                  <ChevronRight className="w-4 h-4" />
                </Button>
              )}
              
              {isModuleEnabled('payments') && (
                <Button
                  variant="outline"
                  className="w-full justify-between h-12 border-[#1E293B] hover:bg-muted"
                  onClick={() => navigate('/payments')}
                >
                  <span className="flex items-center gap-3">
                    <CreditCard className="w-4 h-4 text-cyan-400" />
                    Pagos
                  </span>
                  <ChevronRight className="w-4 h-4" />
                </Button>
              )}
            </CardContent>
          </Card>
        </div>

        {/* System Status - Compact on mobile */}
        <Card className="grid-card">
          <CardHeader className="pb-2 md:pb-4">
            <CardTitle className="text-base md:text-lg flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              Estado del Sistema
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
              {[
                { name: 'API', status: 'online' },
                { name: 'Base de Datos', status: 'online' },
                { name: 'Auth', status: 'online' },
                { name: 'Pagos', status: 'online' }
              ].map((service) => (
                <div key={service.name} className="flex items-center gap-2 p-2 md:p-3 rounded-lg bg-muted/30">
                  <div className="w-2 h-2 rounded-full bg-green-400" />
                  <div>
                    <p className="text-xs md:text-sm font-medium">{service.name}</p>
                    <p className="text-[10px] md:text-xs text-muted-foreground">Operativo</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Create User Dialog */}
      <CreateUserDialog
        open={showCreateUser}
        onClose={() => setShowCreateUser(false)}
        onSuccess={() => {
          // Refresh stats and billing after creating user
          Promise.all([
            api.getDashboardStats().then(setStats),
            api.getBillingInfo().then(setBillingInfo)
          ]).catch(console.error);
        }}
      />
      
      {/* Billing & Upgrade Dialog */}
      <Dialog open={showUpgradeDialog} onOpenChange={setShowUpgradeDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Wallet className="w-5 h-5 text-emerald-400" />
              Plan y Facturación
            </DialogTitle>
          </DialogHeader>
          
          {billingInfo ? (
            <div className="space-y-4">
              {/* Current Plan Info */}
              <div className="p-4 rounded-lg bg-[#1E293B]/30 border border-[#1E293B]">
                <div className="flex justify-between items-center mb-3">
                  <span className="text-sm text-muted-foreground">Estado</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    billingInfo.billing_status === 'active' ? 'bg-emerald-500/20 text-emerald-400' :
                    billingInfo.billing_status === 'trialing' ? 'bg-blue-500/20 text-blue-400' :
                    billingInfo.billing_status === 'past_due' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    {billingInfo.billing_status === 'active' ? 'Activo' :
                     billingInfo.billing_status === 'trialing' ? 'Periodo de Prueba' :
                     billingInfo.billing_status === 'past_due' ? 'Pago Pendiente' :
                     'Cancelado'}
                  </span>
                </div>
                
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div>
                    <p className="text-2xl font-bold text-primary">{billingInfo.paid_seats}</p>
                    <p className="text-xs text-muted-foreground">Asientos Pagados</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-emerald-400">{billingInfo.active_users}</p>
                    <p className="text-xs text-muted-foreground">Usuarios Activos</p>
                  </div>
                  <div>
                    <p className={`text-2xl font-bold ${billingInfo.remaining_seats > 0 ? 'text-blue-400' : 'text-yellow-400'}`}>
                      {billingInfo.remaining_seats}
                    </p>
                    <p className="text-xs text-muted-foreground">Disponibles</p>
                  </div>
                </div>
                
                <div className="mt-3 pt-3 border-t border-[#1E293B]">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Costo Mensual</span>
                    <span className="text-lg font-bold">${billingInfo.monthly_cost?.toFixed(2)} USD</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    ${billingInfo.price_per_seat?.toFixed(2)} USD por usuario/mes
                  </p>
                </div>
              </div>
              
              {/* Seat Usage Progress Bar */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Uso de Asientos</span>
                  <span className={billingInfo.remaining_seats <= 2 ? 'text-yellow-400' : ''}>
                    {Math.round((billingInfo.active_users / billingInfo.paid_seats) * 100)}%
                  </span>
                </div>
                <div className="h-2 bg-[#1E293B] rounded-full overflow-hidden">
                  <div 
                    className={`h-full transition-all ${
                      billingInfo.remaining_seats <= 0 ? 'bg-red-500' :
                      billingInfo.remaining_seats <= 2 ? 'bg-yellow-500' :
                      'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, (billingInfo.active_users / billingInfo.paid_seats) * 100)}%` }}
                  />
                </div>
              </div>
              
              {/* Upgrade Section */}
              <div className="p-4 rounded-lg bg-primary/10 border border-primary/30">
                <h4 className="font-medium mb-3 flex items-center gap-2">
                  <ArrowUpRight className="w-4 h-4 text-primary" />
                  Agregar más asientos
                </h4>
                
                <div className="flex items-center gap-3 mb-3">
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-[#1E293B]"
                    onClick={() => setAdditionalSeats(Math.max(1, additionalSeats - 10))}
                    disabled={additionalSeats <= 1}
                  >
                    -10
                  </Button>
                  <div className="flex-1">
                    <Input
                      type="number"
                      value={additionalSeats}
                      onChange={(e) => setAdditionalSeats(Math.max(1, parseInt(e.target.value) || 1))}
                      className="bg-[#0A0A0F] border-[#1E293B] text-center"
                      min={1}
                      max={1000}
                    />
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-[#1E293B]"
                    onClick={() => setAdditionalSeats(additionalSeats + 10)}
                  >
                    +10
                  </Button>
                </div>
                
                <div className="flex justify-between items-center mb-3 text-sm">
                  <span className="text-muted-foreground">Nuevo total de asientos:</span>
                  <span className="font-bold">{billingInfo.paid_seats + additionalSeats}</span>
                </div>
                
                <div className="flex justify-between items-center mb-4 text-sm">
                  <span className="text-muted-foreground">Costo adicional:</span>
                  <span className="font-bold text-primary">
                    +${(additionalSeats * (billingInfo.price_per_seat || 1)).toFixed(2)} USD/mes
                  </span>
                </div>
                
                <Button
                  className="w-full bg-primary hover:bg-primary/90"
                  onClick={handleUpgradeSeats}
                  disabled={isUpgrading || additionalSeats < 1}
                >
                  {isUpgrading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Procesando...
                    </>
                  ) : (
                    <>
                      <CreditCard className="w-4 h-4 mr-2" />
                      Actualizar Plan
                    </>
                  )}
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-primary" />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  );
};

export default DashboardPage;
