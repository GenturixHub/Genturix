/**
 * GENTURIX - User Management Page
 * Condominium Admin can create and manage all user roles
 * P0 CRITICAL - Required for production release
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/alert-dialog';
import api from '../services/api';
import { 
  Users, 
  UserPlus, 
  Search,
  Filter,
  CheckCircle,
  XCircle,
  Loader2,
  Copy,
  Eye,
  EyeOff,
  AlertTriangle,
  Shield,
  Home,
  GraduationCap,
  Briefcase,
  UserCheck,
  MoreVertical,
  Lock,
  Unlock,
  RefreshCw
} from 'lucide-react';

// ============================================
// ROLE CONFIGURATION
// ============================================
const ROLE_CONFIG = {
  'Residente': { 
    icon: Home, 
    color: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    description: 'Acceso a botón de pánico y registro de visitas'
  },
  'Guarda': { 
    icon: Shield, 
    color: 'bg-green-500/10 text-green-400 border-green-500/20',
    description: 'Panel de seguridad, alertas y control de acceso'
  },
  'HR': { 
    icon: Briefcase, 
    color: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
    description: 'Gestión de personal, turnos y reclutamiento'
  },
  'Supervisor': { 
    icon: UserCheck, 
    color: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    description: 'Supervisión de guardias y monitoreo'
  },
  'Estudiante': { 
    icon: GraduationCap, 
    color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
    description: 'Acceso a Genturix School y cursos'
  },
};

const AVAILABLE_ROLES = [
  { value: 'Residente', label: 'Residente' },
  { value: 'Guarda', label: 'Guarda' },
  { value: 'HR', label: 'Recursos Humanos' },
  { value: 'Supervisor', label: 'Supervisor' },
  { value: 'Estudiante', label: 'Estudiante' },
];

// ============================================
// PASSWORD GENERATOR
// ============================================
const generateSecurePassword = () => {
  const upper = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
  const lower = 'abcdefghjkmnpqrstuvwxyz';
  const numbers = '23456789';
  const special = '!@#$%&*';
  
  let password = '';
  password += upper[Math.floor(Math.random() * upper.length)];
  password += lower[Math.floor(Math.random() * lower.length)];
  password += numbers[Math.floor(Math.random() * numbers.length)];
  password += special[Math.floor(Math.random() * special.length)];
  
  const allChars = upper + lower + numbers + special;
  for (let i = 0; i < 8; i++) {
    password += allChars[Math.floor(Math.random() * allChars.length)];
  }
  
  return password.split('').sort(() => Math.random() - 0.5).join('');
};

// ============================================
// CREDENTIALS SUCCESS DIALOG
// ============================================
const CredentialsDialog = ({ open, onClose, credentials }) => {
  const [copied, setCopied] = useState(false);
  const [showPassword, setShowPassword] = useState(true);

  const copyToClipboard = async () => {
    const text = `Email: ${credentials.email}\nContraseña: ${credentials.password}`;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!credentials) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-green-400">
            <CheckCircle className="w-5 h-5" />
            Usuario Creado Exitosamente
          </DialogTitle>
          <DialogDescription>
            Guarda estas credenciales de forma segura. La contraseña no se mostrará de nuevo.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Warning Banner */}
          <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-400">
              <strong>Importante:</strong> Esta es la única vez que verás la contraseña. 
              Cópiala ahora y entrégala al usuario de forma segura.
            </div>
          </div>

          {/* User Info */}
          <div className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B] space-y-3">
            <div>
              <Label className="text-xs text-muted-foreground">Nombre</Label>
              <p className="font-medium">{credentials.full_name}</p>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Email</Label>
              <p className="font-mono text-primary">{credentials.email}</p>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Contraseña</Label>
              <div className="flex items-center gap-2">
                <code className="flex-1 p-2 rounded bg-[#1E293B] font-mono text-green-400">
                  {showPassword ? credentials.password : '••••••••••••'}
                </code>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </Button>
              </div>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Rol</Label>
              <Badge className={ROLE_CONFIG[credentials.role]?.color || 'bg-gray-500/10'}>
                {credentials.role}
              </Badge>
            </div>
          </div>

          {/* Copy Button */}
          <Button
            className="w-full"
            onClick={copyToClipboard}
            data-testid="copy-credentials-btn"
          >
            {copied ? (
              <>
                <CheckCircle className="w-4 h-4 mr-2" />
                ¡Copiado!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 mr-2" />
                Copiar Credenciales
              </>
            )}
          </Button>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="close-credentials-btn">
            He guardado las credenciales
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
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
    is_active: true
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [useAutoPassword, setUseAutoPassword] = useState(true);

  // Auto-generate password on mount
  useEffect(() => {
    if (open && useAutoPassword) {
      setForm(prev => ({ ...prev, password: generateSecurePassword() }));
    }
  }, [open, useAutoPassword]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!form.email || !form.password || !form.full_name || !form.role) {
      setError('Por favor complete todos los campos obligatorios');
      return;
    }

    if (form.password.length < 8) {
      setError('La contraseña debe tener al menos 8 caracteres');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await api.createUserByAdmin(form);
      onSuccess({
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        role: form.role
      });
      setForm({ email: '', password: '', full_name: '', role: '', phone: '', is_active: true });
      onClose();
    } catch (err) {
      setError(err.message || 'Error al crear usuario');
    } finally {
      setIsSubmitting(false);
    }
  };

  const regeneratePassword = () => {
    setForm({ ...form, password: generateSecurePassword() });
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="w-5 h-5 text-primary" />
            Crear Nuevo Usuario
          </DialogTitle>
          <DialogDescription>
            El usuario se asignará automáticamente a tu condominio y podrá iniciar sesión inmediatamente.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
              <XCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 space-y-2">
              <Label htmlFor="full_name">Nombre Completo *</Label>
              <Input
                id="full_name"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="Juan Pérez García"
                className="bg-[#0A0A0F] border-[#1E293B]"
                required
                data-testid="create-user-name"
              />
            </div>

            <div className="col-span-2 space-y-2">
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

            <div className="col-span-2 space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Contraseña *</Label>
                <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useAutoPassword}
                    onChange={(e) => {
                      setUseAutoPassword(e.target.checked);
                      if (e.target.checked) {
                        setForm({ ...form, password: generateSecurePassword() });
                      }
                    }}
                    className="rounded border-[#1E293B]"
                  />
                  Auto-generar
                </label>
              </div>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    placeholder="Mínimo 8 caracteres"
                    className="bg-[#0A0A0F] border-[#1E293B] pr-10 font-mono"
                    required
                    minLength={8}
                    disabled={useAutoPassword}
                    data-testid="create-user-password"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute right-0 top-0 h-full"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </Button>
                </div>
                {useAutoPassword && (
                  <Button 
                    type="button" 
                    variant="outline" 
                    size="icon"
                    onClick={regeneratePassword}
                    title="Regenerar contraseña"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </Button>
                )}
              </div>
              {useAutoPassword && (
                <p className="text-xs text-muted-foreground">
                  Contraseña segura generada automáticamente
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="role">Rol *</Label>
              <Select 
                value={form.role} 
                onValueChange={(value) => setForm({ ...form, role: value })}
              >
                <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]" data-testid="create-user-role">
                  <SelectValue placeholder="Seleccionar rol" />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  {AVAILABLE_ROLES.map((role) => {
                    const config = ROLE_CONFIG[role.value];
                    const Icon = config?.icon || Users;
                    return (
                      <SelectItem key={role.value} value={role.value}>
                        <div className="flex items-center gap-2">
                          <Icon className="w-4 h-4" />
                          <span>{role.label}</span>
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
              {form.role && ROLE_CONFIG[form.role] && (
                <p className="text-xs text-muted-foreground">
                  {ROLE_CONFIG[form.role].description}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Teléfono</Label>
              <Input
                id="phone"
                type="tel"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="+52 555 123 4567"
                className="bg-[#0A0A0F] border-[#1E293B]"
                data-testid="create-user-phone"
              />
            </div>
          </div>

          {/* Info Banner */}
          <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm">
            <strong>Nota:</strong> El usuario podrá iniciar sesión inmediatamente con estas credenciales.
            Asegúrate de comunicarlas de forma segura.
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

// ============================================
// MAIN PAGE COMPONENT
// ============================================
const UserManagementPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showCredentialsDialog, setShowCredentialsDialog] = useState(false);
  const [newUserCredentials, setNewUserCredentials] = useState(null);
  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Fetch users
  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await api.getUsersByAdmin(roleFilter === 'all' ? '' : roleFilter);
      setUsers(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error fetching users:', err);
      setUsers([]);
    } finally {
      setIsLoading(false);
    }
  }, [roleFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Filter users by search
  const filteredUsers = users.filter(u => {
    const matchesSearch = searchQuery === '' || 
      u.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  // Handle user creation success
  const handleUserCreated = (credentials) => {
    setNewUserCredentials(credentials);
    setShowCredentialsDialog(true);
    fetchUsers();
  };

  // Handle user status toggle
  const handleToggleUserStatus = async () => {
    if (!selectedUser) return;
    
    setActionLoading(true);
    try {
      await api.patch(`/admin/users/${selectedUser.id}/status`, {
        is_active: !selectedUser.is_active
      });
      fetchUsers();
      setShowDeactivateDialog(false);
      setSelectedUser(null);
    } catch (err) {
      console.error('Error updating user status:', err);
    } finally {
      setActionLoading(false);
    }
  };

  // Stats
  const stats = {
    total: users.length,
    active: users.filter(u => u.is_active !== false).length,
    byRole: AVAILABLE_ROLES.reduce((acc, role) => {
      acc[role.value] = users.filter(u => u.roles?.includes(role.value)).length;
      return acc;
    }, {})
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <Users className="w-6 h-6 text-primary" />
              Gestión de Usuarios
            </h1>
            <p className="text-muted-foreground mt-1">
              Crea y administra usuarios de tu condominio
            </p>
          </div>
          <Button 
            onClick={() => setShowCreateDialog(true)}
            className="gap-2"
            data-testid="create-user-btn"
          >
            <UserPlus className="w-4 h-4" />
            Crear Usuario
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-primary" />
                <span className="text-2xl font-bold">{stats.total}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">Total Usuarios</p>
            </CardContent>
          </Card>
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-400" />
                <span className="text-2xl font-bold">{stats.active}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">Activos</p>
            </CardContent>
          </Card>
          {AVAILABLE_ROLES.slice(0, 4).map(role => {
            const config = ROLE_CONFIG[role.value];
            const Icon = config?.icon || Users;
            return (
              <Card key={role.value} className="bg-[#0F111A] border-[#1E293B]">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2">
                    <Icon className="w-5 h-5 text-muted-foreground" />
                    <span className="text-2xl font-bold">{stats.byRole[role.value] || 0}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{role.label}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Filters */}
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Buscar por nombre o email..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 bg-[#0A0A0F] border-[#1E293B]"
                  data-testid="search-users"
                />
              </div>
              <Select value={roleFilter} onValueChange={setRoleFilter}>
                <SelectTrigger className="w-full md:w-48 bg-[#0A0A0F] border-[#1E293B]">
                  <Filter className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="Filtrar por rol" />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="all">Todos los roles</SelectItem>
                  {AVAILABLE_ROLES.map(role => (
                    <SelectItem key={role.value} value={role.value}>{role.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Users Table */}
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardHeader>
            <CardTitle>Usuarios ({filteredUsers.length})</CardTitle>
            <CardDescription>
              Lista de usuarios de tu condominio
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-primary" />
              </div>
            ) : filteredUsers.length === 0 ? (
              <div className="text-center py-12">
                <Users className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium">No hay usuarios</h3>
                <p className="text-muted-foreground mb-4">
                  {searchQuery || roleFilter !== 'all' 
                    ? 'No se encontraron usuarios con estos filtros'
                    : 'Comienza creando el primer usuario de tu condominio'}
                </p>
                <Button onClick={() => setShowCreateDialog(true)}>
                  <UserPlus className="w-4 h-4 mr-2" />
                  Crear Usuario
                </Button>
              </div>
            ) : (
              <ScrollArea className="h-[500px]">
                <Table>
                  <TableHeader>
                    <TableRow className="border-[#1E293B]">
                      <TableHead>Usuario</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Rol</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Creado</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredUsers.map((u) => {
                      const role = u.roles?.[0] || 'Sin rol';
                      const config = ROLE_CONFIG[role];
                      const Icon = config?.icon || Users;
                      
                      return (
                        <TableRow key={u.id} className="border-[#1E293B]" data-testid={`user-row-${u.id}`}>
                          <TableCell>
                            <div className="flex items-center gap-3">
                              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${config?.color || 'bg-gray-500/10'}`}>
                                <Icon className="w-5 h-5" />
                              </div>
                              <div>
                                <p className="font-medium">{u.full_name || 'Sin nombre'}</p>
                                <p className="text-xs text-muted-foreground">{u.phone || 'Sin teléfono'}</p>
                              </div>
                            </div>
                          </TableCell>
                          <TableCell>
                            <code className="text-sm text-primary">{u.email}</code>
                          </TableCell>
                          <TableCell>
                            <Badge className={config?.color || 'bg-gray-500/10'}>
                              {role}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <Badge 
                              className={u.is_active !== false 
                                ? 'bg-green-500/10 text-green-400 border-green-500/20' 
                                : 'bg-red-500/10 text-red-400 border-red-500/20'}
                            >
                              {u.is_active !== false ? 'Activo' : 'Inactivo'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground text-sm">
                            {u.created_at ? new Date(u.created_at).toLocaleDateString('es-MX') : 'N/A'}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedUser(u);
                                setShowDeactivateDialog(true);
                              }}
                              data-testid={`toggle-status-${u.id}`}
                            >
                              {u.is_active !== false ? (
                                <Lock className="w-4 h-4 text-yellow-400" />
                              ) : (
                                <Unlock className="w-4 h-4 text-green-400" />
                              )}
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Create User Dialog */}
      <CreateUserDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSuccess={handleUserCreated}
      />

      {/* Credentials Success Dialog */}
      <CredentialsDialog
        open={showCredentialsDialog}
        onClose={() => {
          setShowCredentialsDialog(false);
          setNewUserCredentials(null);
        }}
        credentials={newUserCredentials}
      />

      {/* Deactivate/Activate User Dialog */}
      <AlertDialog open={showDeactivateDialog} onOpenChange={setShowDeactivateDialog}>
        <AlertDialogContent className="bg-[#0F111A] border-[#1E293B]">
          <AlertDialogHeader>
            <AlertDialogTitle>
              {selectedUser?.is_active !== false ? 'Desactivar Usuario' : 'Activar Usuario'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {selectedUser?.is_active !== false 
                ? `¿Estás seguro de desactivar a ${selectedUser?.full_name}? El usuario no podrá iniciar sesión hasta que lo reactives.`
                : `¿Estás seguro de activar a ${selectedUser?.full_name}? El usuario podrá iniciar sesión nuevamente.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleToggleUserStatus}
              className={selectedUser?.is_active !== false ? 'bg-red-600 hover:bg-red-700' : 'bg-green-600 hover:bg-green-700'}
              disabled={actionLoading}
            >
              {actionLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : selectedUser?.is_active !== false ? (
                'Desactivar'
              ) : (
                'Activar'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </DashboardLayout>
  );
};

export default UserManagementPage;
