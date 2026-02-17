/**
 * GENTURIX - User Management Page
 * Condominium Admin can create and manage all user roles
 * P0 CRITICAL - Required for production release
 * 
 * Features:
 * - User creation and management
 * - Access requests (pending approvals from invitation links)
 * - Invitation links management
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/layout/DashboardLayout';
import { useIsMobile } from '../components/layout/BottomNav';
import { MobileCard, MobileCardList } from '../components/MobileComponents';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { ScrollArea } from '../components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Textarea } from '../components/ui/textarea';
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
import { toast } from 'sonner';
import { QRCodeSVG } from 'qrcode.react';
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
  RefreshCw,
  Mail,
  Link2,
  QrCode,
  Clock,
  Trash2,
  UserX,
  Building,
  Calendar,
  ExternalLink
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
    color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
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

  const emailSent = credentials.email_sent;
  const emailSuccess = credentials.email_status === 'success';
  const tenantIsDemo = credentials.tenant_environment === 'demo';

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-green-400">
            <CheckCircle className="w-5 h-5" />
            Usuario Creado Exitosamente
            {tenantIsDemo && (
              <Badge className="bg-blue-500/20 text-blue-400 border border-blue-500/30 ml-2">
                DEMO
              </Badge>
            )}
          </DialogTitle>
          <DialogDescription>
            {tenantIsDemo 
              ? "Modo DEMO: Las credenciales se muestran en pantalla. Los emails no se envían."
              : emailSent && emailSuccess 
                ? "Las credenciales han sido enviadas al email del usuario."
                : "Guarda estas credenciales de forma segura. La contraseña no se mostrará de nuevo."
            }
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* DEMO MODE Banner */}
          {tenantIsDemo && (
            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 text-blue-400" />
              <div className="text-sm text-blue-400">
                <strong>Tenant en Modo DEMO</strong><br/>
                Este condominio está configurado como DEMO. Las credenciales siempre se muestran y los emails nunca se envían.
              </div>
            </div>
          )}

          {/* Email Status Banner */}
          {emailSent && !tenantIsDemo && (
            <div className={`p-3 rounded-lg flex items-start gap-2 ${
              emailSuccess 
                ? 'bg-green-500/10 border border-green-500/20' 
                : 'bg-yellow-500/10 border border-yellow-500/20'
            }`}>
              <Mail className={`w-5 h-5 flex-shrink-0 mt-0.5 ${emailSuccess ? 'text-green-400' : 'text-yellow-400'}`} />
              <div className={`text-sm ${emailSuccess ? 'text-green-400' : 'text-yellow-400'}`}>
                {emailSuccess ? (
                  <>
                    <strong>Email enviado exitosamente.</strong><br/>
                    El usuario recibirá una contraseña temporal y deberá cambiarla en su primer inicio de sesión.
                  </>
                ) : (
                  <>
                    <strong>No se pudo enviar el email.</strong><br/>
                    {credentials.email_message || 'El usuario fue creado pero deberás entregarle las credenciales manualmente.'}
                  </>
                )}
              </div>
            </div>
          )}

          {/* Warning Banner - only show if NOT sent by email and NOT demo mode */}
          {!emailSent && !tenantIsDemo && (
            <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-yellow-400">
                <strong>Importante:</strong> Esta es la única vez que verás la contraseña. 
                Cópiala ahora y entrégala al usuario de forma segura.
              </div>
            </div>
          )}

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
            {!emailSent && (
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
            )}
            {emailSent && emailSuccess && (
              <div>
                <Label className="text-xs text-muted-foreground">Contraseña</Label>
                <p className="text-sm text-muted-foreground italic">
                  (Enviada por email - el usuario deberá cambiarla)
                </p>
              </div>
            )}
            <div>
              <Label className="text-xs text-muted-foreground">Rol</Label>
              <Badge className={ROLE_CONFIG[credentials.role]?.color || 'bg-gray-500/10'}>
                {credentials.role}
              </Badge>
            </div>
          </div>

          {/* Copy Button - only show if NOT sent by email or email failed */}
          {(!emailSent || !emailSuccess) && (
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
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="close-credentials-btn">
            {emailSent && emailSuccess ? 'Cerrar' : 'He guardado las credenciales'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// CREATE USER DIALOG WITH DYNAMIC ROLE FORMS
// ============================================
const CreateUserDialog = ({ open, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    email: '',
    password: '',
    full_name: '',
    role: '',
    phone: '',
    send_credentials_email: false, // New: send credentials by email
    // Role-specific fields
    apartment_number: '',
    tower_block: '',
    resident_type: 'owner',
    badge_number: '',
    main_location: 'Entrada Principal',
    initial_shift: '',
    department: 'Recursos Humanos',
    permission_level: 'HR',
    subscription_plan: 'basic',
    subscription_status: 'trial',
    supervised_area: '',
    guard_assignments: []
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

  // Reset form when role changes
  const handleRoleChange = (role) => {
    setForm(prev => ({ ...prev, role }));
    setError(null);
  };

  // Validate role-specific required fields
  const validateRoleFields = () => {
    switch (form.role) {
      case 'Residente':
        if (!form.apartment_number) {
          setError('Número de apartamento/casa es requerido');
          return false;
        }
        break;
      case 'Guarda':
        if (!form.badge_number) {
          setError('Número de placa es requerido');
          return false;
        }
        break;
      default:
        break;
    }
    return true;
  };

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

    if (!validateRoleFields()) {
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await api.createUserByAdmin(form);
      
      // Tenant environment determines if we show passwords
      // Demo tenants: Always show password (no emails sent)
      // Production tenants: Show only if email toggle disabled or email not requested
      const displayPassword = response.credentials?.show_password 
        ? response.credentials.password 
        : (form.send_credentials_email ? '(enviada por email)' : form.password);
      
      onSuccess({
        email: form.email,
        password: displayPassword,
        full_name: form.full_name,
        role: form.role,
        email_sent: form.send_credentials_email,
        email_status: response.email_status,
        email_message: response.email_message,
        tenant_environment: response.tenant_environment,  // "demo" or "production"
        demo_mode_notice: response.demo_mode_notice,  // Message for demo tenants
        show_password: response.credentials?.show_password
      });
      // Reset form
      setForm({
        email: '', password: '', full_name: '', role: '', phone: '',
        send_credentials_email: false,
        apartment_number: '', tower_block: '', resident_type: 'owner',
        badge_number: '', main_location: 'Entrada Principal', initial_shift: '',
        department: 'Recursos Humanos', permission_level: 'HR',
        subscription_plan: 'basic', subscription_status: 'trial',
        supervised_area: '', guard_assignments: []
      });
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

  // Role-specific form fields
  const renderRoleFields = () => {
    switch (form.role) {
      case 'Residente':
        return (
          <div className="space-y-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
            <p className="text-xs font-medium text-blue-400 flex items-center gap-2">
              <Home className="w-4 h-4" />
              Datos de Residente
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Apartamento / Casa *</Label>
                <Input
                  value={form.apartment_number}
                  onChange={(e) => setForm({ ...form, apartment_number: e.target.value })}
                  placeholder="Ej: A-101, Casa 5"
                  className="bg-[#0A0A0F] border-[#1E293B] h-9 text-sm"
                  data-testid="resident-apartment"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Torre / Bloque</Label>
                <Input
                  value={form.tower_block}
                  onChange={(e) => setForm({ ...form, tower_block: e.target.value })}
                  placeholder="Ej: Torre A, Bloque 2"
                  className="bg-[#0A0A0F] border-[#1E293B] h-9 text-sm"
                  data-testid="resident-tower"
                />
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Tipo de Residente</Label>
              <Select value={form.resident_type} onValueChange={(v) => setForm({ ...form, resident_type: v })}>
                <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="owner">Propietario</SelectItem>
                  <SelectItem value="tenant">Arrendatario</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        );

      case 'Guarda':
        return (
          <div className="space-y-3 p-3 rounded-lg bg-green-500/5 border border-green-500/20">
            <p className="text-xs font-medium text-green-400 flex items-center gap-2">
              <Shield className="w-4 h-4" />
              Datos de Guardia
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Número de Placa *</Label>
                <Input
                  value={form.badge_number}
                  onChange={(e) => setForm({ ...form, badge_number: e.target.value })}
                  placeholder="Ej: G-001"
                  className="bg-[#0A0A0F] border-[#1E293B] h-9 text-sm"
                  data-testid="guard-badge"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Ubicación Principal</Label>
                <Select value={form.main_location} onValueChange={(v) => setForm({ ...form, main_location: v })}>
                  <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] h-9 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                    <SelectItem value="Entrada Principal">Entrada Principal</SelectItem>
                    <SelectItem value="Entrada Vehicular">Entrada Vehicular</SelectItem>
                    <SelectItem value="Entrada Peatonal">Entrada Peatonal</SelectItem>
                    <SelectItem value="Rondín">Rondín</SelectItem>
                    <SelectItem value="Centro de Control">Centro de Control</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Turno Inicial</Label>
              <Select value={form.initial_shift} onValueChange={(v) => setForm({ ...form, initial_shift: v })}>
                <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] h-9 text-sm">
                  <SelectValue placeholder="Seleccionar turno" />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="none">Sin asignar</SelectItem>
                  <SelectItem value="morning">Matutino (6:00 - 14:00)</SelectItem>
                  <SelectItem value="afternoon">Vespertino (14:00 - 22:00)</SelectItem>
                  <SelectItem value="night">Nocturno (22:00 - 6:00)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        );

      case 'HR':
        return (
          <div className="space-y-3 p-3 rounded-lg bg-orange-500/5 border border-orange-500/20">
            <p className="text-xs font-medium text-orange-400 flex items-center gap-2">
              <Briefcase className="w-4 h-4" />
              Datos de Recursos Humanos
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Departamento</Label>
                <Input
                  value={form.department}
                  onChange={(e) => setForm({ ...form, department: e.target.value })}
                  placeholder="Recursos Humanos"
                  className="bg-[#0A0A0F] border-[#1E293B] h-9 text-sm"
                  data-testid="hr-department"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Nivel de Permisos</Label>
                <Select value={form.permission_level} onValueChange={(v) => setForm({ ...form, permission_level: v })}>
                  <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] h-9 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                    <SelectItem value="HR">Solo RRHH</SelectItem>
                    <SelectItem value="HR_SUPERVISOR">RRHH + Supervisor</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        );

      case 'Estudiante':
        return (
          <div className="space-y-3 p-3 rounded-lg bg-cyan-500/5 border border-cyan-500/20">
            <p className="text-xs font-medium text-cyan-400 flex items-center gap-2">
              <GraduationCap className="w-4 h-4" />
              Datos de Estudiante
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Plan de Suscripción</Label>
                <Select value={form.subscription_plan} onValueChange={(v) => setForm({ ...form, subscription_plan: v })}>
                  <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] h-9 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                    <SelectItem value="basic">Básico ($1/mes)</SelectItem>
                    <SelectItem value="pro">Pro ($3/mes)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Estado de Suscripción</Label>
                <Select value={form.subscription_status} onValueChange={(v) => setForm({ ...form, subscription_status: v })}>
                  <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] h-9 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                    <SelectItem value="trial">Prueba (14 días)</SelectItem>
                    <SelectItem value="active">Activo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        );

      case 'Supervisor':
        return (
          <div className="space-y-3 p-3 rounded-lg bg-cyan-500/5 border border-cyan-500/20">
            <p className="text-xs font-medium text-cyan-400 flex items-center gap-2">
              <UserCheck className="w-4 h-4" />
              Datos de Supervisor
            </p>
            <div className="space-y-1">
              <Label className="text-xs">Área Supervisada</Label>
              <Input
                value={form.supervised_area}
                onChange={(e) => setForm({ ...form, supervised_area: e.target.value })}
                placeholder="Ej: Seguridad Perimetral, Accesos"
                className="bg-[#0A0A0F] border-[#1E293B] h-9 text-sm"
                data-testid="supervisor-area"
              />
            </div>
          </div>
        );

      default:
        return null;
    }
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
                onValueChange={handleRoleChange}
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

          {/* Role-specific fields */}
          {form.role && renderRoleFields()}

          {/* Email Credentials Checkbox */}
          <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={form.send_credentials_email}
                onChange={(e) => setForm({ ...form, send_credentials_email: e.target.checked })}
                className="mt-1 rounded border-[#1E293B] bg-[#0A0A0F] text-primary focus:ring-primary"
                data-testid="send-email-checkbox"
              />
              <div className="flex-1">
                <span className="flex items-center gap-2 text-sm font-medium text-white">
                  <Mail className="w-4 h-4 text-primary" />
                  Enviar credenciales por email
                </span>
                <p className="text-xs text-muted-foreground mt-1">
                  {form.send_credentials_email 
                    ? "Se enviará un email con la contraseña temporal. El usuario deberá cambiarla en su primer inicio de sesión."
                    : "El usuario podrá iniciar sesión con la contraseña especificada arriba. Asegúrate de comunicarla de forma segura."
                  }
                </p>
              </div>
            </label>
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
// INVITATIONS MANAGEMENT COMPONENT
// ============================================
const InvitationsSection = ({ onInviteCreated }) => {
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showQRDialog, setShowQRDialog] = useState(false);
  const [selectedInvite, setSelectedInvite] = useState(null);
  
  // Form state
  const [form, setForm] = useState({
    expiration_days: 7,
    usage_limit_type: 'single',
    max_uses: 1,
    notes: ''
  });
  
  const fetchInvitations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getInvitations();
      setInvitations(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error fetching invitations:', err);
      toast.error('Error al cargar invitaciones');
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => {
    fetchInvitations();
  }, [fetchInvitations]);
  
  const handleCreate = async () => {
    setCreating(true);
    try {
      const result = await api.createInvitation({
        expiration_days: parseInt(form.expiration_days),
        usage_limit_type: form.usage_limit_type,
        max_uses: form.usage_limit_type === 'fixed' ? parseInt(form.max_uses) : 1,
        notes: form.notes || null
      });
      toast.success('Invitación creada exitosamente');
      setShowCreateDialog(false);
      setForm({ expiration_days: 7, usage_limit_type: 'single', max_uses: 1, notes: '' });
      fetchInvitations();
      if (onInviteCreated) onInviteCreated();
    } catch (err) {
      toast.error(err.message || 'Error al crear invitación');
    } finally {
      setCreating(false);
    }
  };
  
  const handleRevoke = async (invitationId) => {
    try {
      await api.revokeInvitation(invitationId);
      toast.success('Invitación revocada');
      fetchInvitations();
    } catch (err) {
      toast.error('Error al revocar invitación');
    }
  };
  
  const copyToClipboard = async (url) => {
    await navigator.clipboard.writeText(url);
    toast.success('Link copiado al portapapeles');
  };
  
  const baseUrl = window.location.origin;
  
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h3 className="text-lg font-semibold text-white">Links de Invitación</h3>
          <p className="text-sm text-muted-foreground">Genera links o códigos QR para que nuevos residentes soliciten acceso</p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)} data-testid="create-invite-btn">
          <Link2 className="w-4 h-4 mr-2" />
          Nueva Invitación
        </Button>
      </div>
      
      {/* Invitations List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : invitations.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-[#1E293B] rounded-lg">
          <Link2 className="w-12 h-12 mx-auto mb-3 text-muted-foreground opacity-50" />
          <p className="text-muted-foreground">No hay invitaciones activas</p>
          <p className="text-sm text-muted-foreground/70">Crea una invitación para compartir con residentes potenciales</p>
        </div>
      ) : (
        <div className="space-y-3">
          {invitations.map((inv) => {
            const inviteUrl = `${baseUrl}/join/${inv.token}`;
            const isExpired = inv.is_expired;
            const isRevoked = !inv.is_active;
            const usageFull = inv.usage_limit_type !== 'unlimited' && inv.current_uses >= inv.max_uses;
            
            return (
              <div 
                key={inv.id}
                className={`p-4 rounded-lg border ${
                  isRevoked || isExpired || usageFull
                    ? 'bg-[#0A0A0F]/50 border-[#1E293B]/50 opacity-60'
                    : 'bg-[#0A0A0F] border-[#1E293B]'
                }`}
                data-testid={`invite-row-${inv.id}`}
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <code className="text-xs text-primary bg-primary/10 px-2 py-1 rounded truncate max-w-[200px]">
                        {inv.token.substring(0, 16)}...
                      </code>
                      {isRevoked && <Badge variant="destructive" className="text-xs">Revocada</Badge>}
                      {isExpired && !isRevoked && <Badge variant="secondary" className="text-xs">Expirada</Badge>}
                      {usageFull && !isExpired && !isRevoked && <Badge variant="secondary" className="text-xs">Límite alcanzado</Badge>}
                      {!isRevoked && !isExpired && !usageFull && <Badge className="text-xs bg-green-500/10 text-green-400">Activa</Badge>}
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        Expira: {new Date(inv.expires_at).toLocaleDateString('es-MX')}
                      </span>
                      <span className="flex items-center gap-1">
                        <Users className="w-3 h-3" />
                        Usos: {inv.current_uses}/{inv.usage_limit_type === 'unlimited' ? '∞' : inv.max_uses}
                      </span>
                      {inv.notes && (
                        <span className="text-muted-foreground/70 truncate max-w-[150px]">
                          &ldquo;{inv.notes}&rdquo;
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {!isRevoked && !isExpired && !usageFull && (
                      <>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => copyToClipboard(inviteUrl)}
                          data-testid={`copy-invite-${inv.id}`}
                        >
                          <Copy className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => {
                            setSelectedInvite({ ...inv, url: inviteUrl });
                            setShowQRDialog(true);
                          }}
                          data-testid={`qr-invite-${inv.id}`}
                        >
                          <QrCode className="w-4 h-4" />
                        </Button>
                      </>
                    )}
                    {inv.is_active && (
                      <Button 
                        variant="ghost" 
                        size="sm"
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                        onClick={() => handleRevoke(inv.id)}
                        data-testid={`revoke-invite-${inv.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      
      {/* Create Invitation Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle>Nueva Invitación</DialogTitle>
            <DialogDescription>
              Crea un link de invitación para que nuevos residentes soliciten acceso
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Expiración</Label>
              <Select 
                value={String(form.expiration_days)} 
                onValueChange={(v) => setForm({...form, expiration_days: parseInt(v)})}
              >
                <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="7">7 días</SelectItem>
                  <SelectItem value="30">30 días</SelectItem>
                  <SelectItem value="90">90 días</SelectItem>
                  <SelectItem value="365">1 año</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Límite de Uso</Label>
              <Select 
                value={form.usage_limit_type} 
                onValueChange={(v) => setForm({...form, usage_limit_type: v})}
              >
                <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="single">Un solo uso</SelectItem>
                  <SelectItem value="unlimited">Ilimitado hasta expirar</SelectItem>
                  <SelectItem value="fixed">Número fijo de usos</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {form.usage_limit_type === 'fixed' && (
              <div className="space-y-2">
                <Label>Número máximo de usos</Label>
                <Input
                  type="number"
                  min="1"
                  max="1000"
                  value={form.max_uses}
                  onChange={(e) => setForm({...form, max_uses: parseInt(e.target.value) || 1})}
                  className="bg-[#0A0A0F] border-[#1E293B]"
                />
              </div>
            )}
            
            <div className="space-y-2">
              <Label>Notas (opcional)</Label>
              <Textarea
                value={form.notes}
                onChange={(e) => setForm({...form, notes: e.target.value})}
                placeholder="Ej: Para residentes Torre A"
                className="bg-[#0A0A0F] border-[#1E293B]"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancelar
            </Button>
            <Button onClick={handleCreate} disabled={creating}>
              {creating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Link2 className="w-4 h-4 mr-2" />}
              Crear Invitación
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* QR Code Dialog */}
      <Dialog open={showQRDialog} onOpenChange={setShowQRDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle>Código QR de Invitación</DialogTitle>
            <DialogDescription>
              Escanea este código para acceder al formulario de solicitud
            </DialogDescription>
          </DialogHeader>
          {selectedInvite && (
            <div className="flex flex-col items-center space-y-4">
              <div className="p-4 bg-white rounded-xl">
                <QRCodeSVG 
                  value={selectedInvite.url} 
                  size={200}
                  level="M"
                />
              </div>
              <div className="text-center">
                <p className="text-xs text-muted-foreground mb-2">O comparte este link:</p>
                <code className="text-xs text-primary bg-primary/10 px-3 py-2 rounded block max-w-full overflow-x-auto">
                  {selectedInvite.url}
                </code>
              </div>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  onClick={() => copyToClipboard(selectedInvite.url)}
                >
                  <Copy className="w-4 h-4 mr-2" />
                  Copiar Link
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => window.open(selectedInvite.url, '_blank')}
                >
                  <ExternalLink className="w-4 h-4 mr-2" />
                  Abrir
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ============================================
// ACCESS REQUESTS TAB COMPONENT
// ============================================
const AccessRequestsTab = () => {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(null);
  const [showActionDialog, setShowActionDialog] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [actionType, setActionType] = useState(null);
  const [actionMessage, setActionMessage] = useState('');
  const [sendEmail, setSendEmail] = useState(true);
  const [createdCredentials, setCreatedCredentials] = useState(null);
  const [showCredentialsDialog, setShowCredentialsDialog] = useState(false);
  
  const fetchRequests = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getAccessRequests('all');
      setRequests(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error fetching access requests:', err);
      toast.error('Error al cargar solicitudes');
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);
  
  const handleAction = async () => {
    if (!selectedRequest || !actionType) return;
    
    setProcessing(selectedRequest.id);
    try {
      const result = await api.processAccessRequest(
        selectedRequest.id,
        actionType,
        actionMessage,
        sendEmail
      );
      
      if (actionType === 'approve') {
        toast.success('Solicitud aprobada. Usuario creado exitosamente.');
        // If email wasn't sent, show credentials
        if (!sendEmail && result.credentials?.password) {
          setCreatedCredentials({
            email: result.credentials.email,
            password: result.credentials.password,
            name: selectedRequest.full_name
          });
          setShowCredentialsDialog(true);
        }
      } else {
        toast.success('Solicitud rechazada.');
      }
      
      setShowActionDialog(false);
      setSelectedRequest(null);
      setActionType(null);
      setActionMessage('');
      fetchRequests();
    } catch (err) {
      toast.error(err.message || 'Error al procesar solicitud');
    } finally {
      setProcessing(null);
    }
  };
  
  const pendingCount = requests.filter(r => r.status === 'pending_approval').length;
  
  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-4 h-4 text-yellow-400" />
            <span className="text-2xl font-bold text-yellow-400">{pendingCount}</span>
          </div>
          <p className="text-xs text-muted-foreground">Pendientes</p>
        </div>
        <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle className="w-4 h-4 text-green-400" />
            <span className="text-2xl font-bold text-green-400">
              {requests.filter(r => r.status === 'approved').length}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">Aprobadas</p>
        </div>
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
          <div className="flex items-center gap-2 mb-1">
            <XCircle className="w-4 h-4 text-red-400" />
            <span className="text-2xl font-bold text-red-400">
              {requests.filter(r => r.status === 'rejected').length}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">Rechazadas</p>
        </div>
      </div>
      
      {/* Requests List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : requests.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-[#1E293B] rounded-lg">
          <Users className="w-12 h-12 mx-auto mb-3 text-muted-foreground opacity-50" />
          <p className="text-muted-foreground">No hay solicitudes de acceso</p>
          <p className="text-sm text-muted-foreground/70">Las solicitudes aparecerán cuando los residentes usen un link de invitación</p>
        </div>
      ) : (
        <div className="space-y-3">
          {requests.map((req) => {
            const isPending = req.status === 'pending_approval';
            const isApproved = req.status === 'approved';
            const isRejected = req.status === 'rejected';
            
            return (
              <div 
                key={req.id}
                className={`p-4 rounded-lg border ${
                  isPending 
                    ? 'bg-[#0A0A0F] border-yellow-500/30' 
                    : 'bg-[#0A0A0F]/50 border-[#1E293B]'
                }`}
                data-testid={`request-row-${req.id}`}
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-white">{req.full_name}</span>
                      {isPending && (
                        <Badge className="text-xs bg-yellow-500/10 text-yellow-400 border-yellow-500/20">
                          <Clock className="w-3 h-3 mr-1" />
                          Pendiente
                        </Badge>
                      )}
                      {isApproved && (
                        <Badge className="text-xs bg-green-500/10 text-green-400 border-green-500/20">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Aprobada
                        </Badge>
                      )}
                      {isRejected && (
                        <Badge className="text-xs bg-red-500/10 text-red-400 border-red-500/20">
                          <XCircle className="w-3 h-3 mr-1" />
                          Rechazada
                        </Badge>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Mail className="w-3 h-3" />
                        {req.email}
                      </span>
                      <span className="flex items-center gap-1">
                        <Building className="w-3 h-3" />
                        {req.tower_block ? `${req.tower_block} - ` : ''}{req.apartment_number}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {new Date(req.created_at).toLocaleDateString('es-MX')}
                      </span>
                    </div>
                    {req.notes && (
                      <p className="mt-2 text-xs text-muted-foreground/70 italic">
                        &ldquo;{req.notes}&rdquo;
                      </p>
                    )}
                    {req.status_message && !isPending && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        <strong>Mensaje:</strong> {req.status_message}
                      </p>
                    )}
                  </div>
                  
                  {isPending && (
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        className="bg-green-600 hover:bg-green-700"
                        onClick={() => {
                          setSelectedRequest(req);
                          setActionType('approve');
                          setActionMessage('');
                          setShowActionDialog(true);
                        }}
                        disabled={processing === req.id}
                        data-testid={`approve-request-${req.id}`}
                      >
                        {processing === req.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>
                            <CheckCircle className="w-4 h-4 mr-1" />
                            Aprobar
                          </>
                        )}
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => {
                          setSelectedRequest(req);
                          setActionType('reject');
                          setActionMessage('');
                          setShowActionDialog(true);
                        }}
                        disabled={processing === req.id}
                        data-testid={`reject-request-${req.id}`}
                      >
                        <XCircle className="w-4 h-4 mr-1" />
                        Rechazar
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
      
      {/* Action Confirmation Dialog */}
      <Dialog open={showActionDialog} onOpenChange={setShowActionDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle>
              {actionType === 'approve' ? 'Aprobar Solicitud' : 'Rechazar Solicitud'}
            </DialogTitle>
            <DialogDescription>
              {actionType === 'approve' 
                ? `Se creará una cuenta para ${selectedRequest?.full_name} con rol de Residente.`
                : `Se rechazará la solicitud de ${selectedRequest?.full_name}.`}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Request Details */}
            <div className="p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-muted-foreground">Email:</span>
                  <p className="text-white">{selectedRequest?.email}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Unidad:</span>
                  <p className="text-white">
                    {selectedRequest?.tower_block ? `${selectedRequest.tower_block} - ` : ''}
                    {selectedRequest?.apartment_number}
                  </p>
                </div>
              </div>
            </div>
            
            {/* Message */}
            <div className="space-y-2">
              <Label>
                {actionType === 'approve' ? 'Mensaje de bienvenida (opcional)' : 'Motivo de rechazo (opcional)'}
              </Label>
              <Textarea
                value={actionMessage}
                onChange={(e) => setActionMessage(e.target.value)}
                placeholder={actionType === 'approve' 
                  ? '¡Bienvenido a la comunidad!'
                  : 'Ej: No se pudo verificar la información proporcionada.'
                }
                className="bg-[#0A0A0F] border-[#1E293B]"
              />
            </div>
            
            {/* Email notification */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="sendEmail"
                checked={sendEmail}
                onChange={(e) => setSendEmail(e.target.checked)}
                className="rounded border-[#1E293B]"
              />
              <Label htmlFor="sendEmail" className="text-sm cursor-pointer">
                Enviar notificación por email al solicitante
              </Label>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowActionDialog(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleAction}
              disabled={processing}
              className={actionType === 'approve' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}
            >
              {processing ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : actionType === 'approve' ? (
                <CheckCircle className="w-4 h-4 mr-2" />
              ) : (
                <XCircle className="w-4 h-4 mr-2" />
              )}
              {actionType === 'approve' ? 'Aprobar y Crear Usuario' : 'Rechazar Solicitud'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Credentials Dialog (when email not sent) */}
      <Dialog open={showCredentialsDialog} onOpenChange={setShowCredentialsDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-400">
              <CheckCircle className="w-5 h-5" />
              Usuario Creado
            </DialogTitle>
            <DialogDescription>
              Comparte estas credenciales con {createdCredentials?.name}
            </DialogDescription>
          </DialogHeader>
          {createdCredentials && (
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                <div className="space-y-3">
                  <div>
                    <span className="text-xs text-muted-foreground">Email</span>
                    <p className="text-white font-mono">{createdCredentials.email}</p>
                  </div>
                  <div>
                    <span className="text-xs text-muted-foreground">Contraseña Temporal</span>
                    <p className="text-green-400 font-mono text-lg">{createdCredentials.password}</p>
                  </div>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                <p className="text-xs text-yellow-400">
                  ⚠️ El usuario deberá cambiar su contraseña en el primer inicio de sesión.
                </p>
              </div>
              <Button
                className="w-full"
                onClick={async () => {
                  await navigator.clipboard.writeText(
                    `Email: ${createdCredentials.email}\nContraseña: ${createdCredentials.password}`
                  );
                  toast.success('Credenciales copiadas');
                }}
              >
                <Copy className="w-4 h-4 mr-2" />
                Copiar Credenciales
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
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
  const [statusFilter, setStatusFilter] = useState('all'); // NEW: Filter by status
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showCredentialsDialog, setShowCredentialsDialog] = useState(false);
  const [newUserCredentials, setNewUserCredentials] = useState(null);
  const [showDeactivateDialog, setShowDeactivateDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false); // NEW: Delete confirmation
  const [selectedUser, setSelectedUser] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('users');
  const [pendingRequestsCount, setPendingRequestsCount] = useState(0);
  const [statusReason, setStatusReason] = useState(''); // NEW: Reason for blocking
  const [newStatus, setNewStatus] = useState(''); // NEW: Status to set
  const [showResetPasswordDialog, setShowResetPasswordDialog] = useState(false); // NEW: Reset password dialog
  
  // NEW: Seat usage state
  const [seatUsage, setSeatUsage] = useState({
    seat_limit: 0,
    active_residents: 0,
    available_seats: 0,
    total_users: 0,
    users_by_role: {},
    users_by_status: {},
    can_add_resident: true,
    billing_status: 'active'
  });

  // NEW: Fetch seat usage
  const fetchSeatUsage = useCallback(async () => {
    try {
      const data = await api.getSeatUsage();
      setSeatUsage(data);
    } catch (err) {
      console.error('Error fetching seat usage:', err);
    }
  }, []);

  // Fetch pending requests count
  const fetchPendingCount = useCallback(async () => {
    try {
      const data = await api.getAccessRequestsCount();
      setPendingRequestsCount(data.pending || 0);
    } catch (err) {
      console.error('Error fetching pending count:', err);
    }
  }, []);

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
    fetchPendingCount();
    fetchSeatUsage();
  }, [fetchUsers, fetchPendingCount, fetchSeatUsage]);

  // Filter users by search and status
  const filteredUsers = users.filter(u => {
    const matchesSearch = searchQuery === '' || 
      u.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email?.toLowerCase().includes(searchQuery.toLowerCase());
    
    // Status filter
    const userStatus = u.status || (u.is_active !== false ? 'active' : 'blocked');
    const matchesStatus = statusFilter === 'all' || userStatus === statusFilter;
    
    return matchesSearch && matchesStatus;
  });

  // Handle user creation success
  const handleUserCreated = (credentials) => {
    setNewUserCredentials(credentials);
    setShowCredentialsDialog(true);
    fetchUsers();
  };

  // Handle user status change (block/unblock/suspend)
  const handleChangeUserStatus = async () => {
    if (!selectedUser || !newStatus) return;
    
    setActionLoading(true);
    try {
      await api.updateUserStatusV2(selectedUser.id, newStatus, statusReason || null);
      toast.success(
        newStatus === 'active' ? 'Usuario activado exitosamente' :
        newStatus === 'blocked' ? 'Usuario bloqueado exitosamente' :
        'Usuario suspendido exitosamente'
      );
      fetchUsers();
      fetchSeatUsage();
      setShowDeactivateDialog(false);
      setSelectedUser(null);
      setNewStatus('');
      setStatusReason('');
    } catch (err) {
      console.error('Error updating user status:', err);
      toast.error(err.message || 'Error al cambiar el estado del usuario');
    } finally {
      setActionLoading(false);
    }
  };

  // Handle user deletion
  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    
    setActionLoading(true);
    try {
      await api.deleteUser(selectedUser.id);
      toast.success('Usuario eliminado exitosamente');
      fetchUsers();
      fetchSeatUsage();
      setShowDeleteDialog(false);
      setSelectedUser(null);
    } catch (err) {
      console.error('Error deleting user:', err);
      toast.error(err.message || 'Error al eliminar el usuario');
    } finally {
      setActionLoading(false);
    }
  };

  // Open status change dialog
  const openStatusDialog = (user, status) => {
    setSelectedUser(user);
    setNewStatus(status);
    setStatusReason('');
    setShowDeactivateDialog(true);
  };

  // Open delete dialog
  const openDeleteDialog = (user) => {
    setSelectedUser(user);
    setShowDeleteDialog(true);
  };

  // Stats - now includes status breakdown
  const stats = {
    total: users.length,
    active: users.filter(u => (u.status || 'active') === 'active' && u.is_active !== false).length,
    blocked: users.filter(u => u.status === 'blocked' || u.is_active === false).length,
    suspended: users.filter(u => u.status === 'suspended').length,
    byRole: AVAILABLE_ROLES.reduce((acc, role) => {
      acc[role.value] = users.filter(u => u.roles?.includes(role.value)).length;
      return acc;
    }, {})
  };

  // Get status badge for user
  const getStatusBadge = (user) => {
    const status = user.status || (user.is_active !== false ? 'active' : 'blocked');
    const statusConfig = {
      active: { label: 'Activo', className: 'bg-green-500/10 text-green-400 border-green-500/20' },
      blocked: { label: 'Bloqueado', className: 'bg-red-500/10 text-red-400 border-red-500/20' },
      suspended: { label: 'Suspendido', className: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' }
    };
    return statusConfig[status] || statusConfig.active;
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
          {activeTab === 'users' && (
            <Button 
              onClick={() => setShowCreateDialog(true)}
              className="gap-2"
              data-testid="create-user-btn"
            >
              <UserPlus className="w-4 h-4" />
              Crear Usuario
            </Button>
          )}
        </div>

        {/* Tabs Navigation */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3 bg-[#0F111A] border border-[#1E293B]">
            <TabsTrigger value="users" className="data-[state=active]:bg-primary/20" data-testid="tab-users">
              <Users className="w-4 h-4 mr-2" />
              Usuarios
            </TabsTrigger>
            <TabsTrigger value="requests" className="data-[state=active]:bg-primary/20 relative" data-testid="tab-requests">
              <Clock className="w-4 h-4 mr-2" />
              Solicitudes
              {pendingRequestsCount > 0 && (
                <Badge className="ml-2 bg-yellow-500 text-black text-xs px-1.5 py-0 min-w-[20px]">
                  {pendingRequestsCount}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="invitations" className="data-[state=active]:bg-primary/20" data-testid="tab-invitations">
              <Link2 className="w-4 h-4 mr-2" />
              Invitaciones
            </TabsTrigger>
          </TabsList>

          {/* Users Tab Content */}
          <TabsContent value="users" className="mt-6">
            {/* Seat Usage Card - Only for Residents */}
            <Card className="bg-gradient-to-r from-[#0F111A] to-[#1a1f2e] border-[#1E293B] mb-6">
              <CardContent className="p-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-xl bg-primary/10">
                      <Home className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold">Plan de Residentes</h3>
                      <p className="text-sm text-muted-foreground">
                        {seatUsage.active_residents} de {seatUsage.seat_limit} asientos ocupados
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-primary">{seatUsage.seat_limit}</p>
                      <p className="text-xs text-muted-foreground">Contratados</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-green-400">{seatUsage.active_residents}</p>
                      <p className="text-xs text-muted-foreground">Activos</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-cyan-400">{seatUsage.available_seats}</p>
                      <p className="text-xs text-muted-foreground">Disponibles</p>
                    </div>
                  </div>
                </div>
                {/* Progress bar */}
                <div className="mt-4">
                  <div className="h-2 bg-[#1E293B] rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all ${
                        seatUsage.available_seats === 0 ? 'bg-red-500' :
                        seatUsage.available_seats <= 2 ? 'bg-yellow-500' : 'bg-primary'
                      }`}
                      style={{ width: `${Math.min(100, (seatUsage.active_residents / seatUsage.seat_limit) * 100)}%` }}
                    />
                  </div>
                  {seatUsage.available_seats === 0 && (
                    <p className="text-xs text-red-400 mt-2 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      Límite alcanzado. Aumenta tu plan o bloquea residentes para agregar más.
                    </p>
                  )}
                  {seatUsage.available_seats > 0 && seatUsage.available_seats <= 2 && (
                    <p className="text-xs text-yellow-400 mt-2 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      Pocos asientos disponibles.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
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
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full md:w-40 bg-[#0A0A0F] border-[#1E293B]">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="active">Activos</SelectItem>
                  <SelectItem value="blocked">Bloqueados</SelectItem>
                  <SelectItem value="suspended">Suspendidos</SelectItem>
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
              <>
                {/* Desktop Table View - hidden on mobile (≤1023px) */}
                <div className="hidden lg:block">
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
                          const statusBadge = getStatusBadge(u);
                          const userStatus = u.status || (u.is_active !== false ? 'active' : 'blocked');
                          const isResident = u.roles?.includes('Residente');
                          
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
                                <Badge className={statusBadge.className}>
                                  {statusBadge.label}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-muted-foreground text-sm">
                                {u.created_at ? new Date(u.created_at).toLocaleDateString('es-MX') : 'N/A'}
                              </TableCell>
                              <TableCell className="text-right">
                                <div className="flex items-center justify-end gap-1">
                                  {userStatus === 'active' ? (
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => openStatusDialog(u, 'blocked')}
                                      data-testid={`block-user-${u.id}`}
                                      title="Bloquear usuario"
                                    >
                                      <Lock className="w-4 h-4 text-yellow-400" />
                                    </Button>
                                  ) : (
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => openStatusDialog(u, 'active')}
                                      data-testid={`unblock-user-${u.id}`}
                                      title="Desbloquear usuario"
                                      disabled={isResident && !seatUsage.can_add_resident}
                                    >
                                      <Unlock className="w-4 h-4 text-green-400" />
                                    </Button>
                                  )}
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => openDeleteDialog(u)}
                                    data-testid={`delete-user-${u.id}`}
                                    title="Eliminar usuario"
                                  >
                                    <Trash2 className="w-4 h-4 text-red-400" />
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                </div>

                {/* Mobile Card View */}
                <div className="block lg:hidden">
                  <MobileCardList>
                    {filteredUsers.map((u) => {
                      const role = u.roles?.[0] || 'Sin rol';
                      const config = ROLE_CONFIG[role];
                      const Icon = config?.icon || Users;
                      const statusBadge = getStatusBadge(u);
                      const userStatus = u.status || (u.is_active !== false ? 'active' : 'blocked');
                      const isResident = u.roles?.includes('Residente');
                      
                      return (
                        <MobileCard
                          key={u.id}
                          testId={`user-card-${u.id}`}
                          title={u.full_name || 'Sin nombre'}
                          subtitle={u.email}
                          icon={Icon}
                          status={statusBadge.label}
                          statusColor={userStatus === 'active' ? 'green' : userStatus === 'blocked' ? 'red' : 'yellow'}
                          details={[
                            { label: 'Rol', value: role },
                            { label: 'Teléfono', value: u.phone || '-' },
                            { label: 'Creado', value: u.created_at ? new Date(u.created_at).toLocaleDateString('es-MX') : '-' },
                          ]}
                          actions={[
                            userStatus === 'active' ? {
                              label: 'Bloquear',
                              icon: Lock,
                              onClick: () => openStatusDialog(u, 'blocked'),
                              variant: 'default'
                            } : {
                              label: 'Desbloquear',
                              icon: Unlock,
                              onClick: () => openStatusDialog(u, 'active'),
                              variant: 'default',
                              disabled: isResident && !seatUsage.can_add_resident
                            },
                            {
                              label: 'Eliminar',
                              icon: Trash2,
                              onClick: () => openDeleteDialog(u),
                              variant: 'destructive'
                            }
                          ]}
                        />
                      );
                    })}
                  </MobileCardList>
                </div>
              </>
            )}
          </CardContent>
        </Card>
          </TabsContent>

          {/* Access Requests Tab */}
          <TabsContent value="requests" className="mt-6">
            <Card className="bg-[#0F111A] border-[#1E293B]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="w-5 h-5 text-yellow-400" />
                  Solicitudes de Acceso
                </CardTitle>
                <CardDescription>
                  Revisa y procesa solicitudes de residentes que quieren unirse al condominio
                </CardDescription>
              </CardHeader>
              <CardContent>
                <AccessRequestsTab />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Invitations Tab */}
          <TabsContent value="invitations" className="mt-6">
            <Card className="bg-[#0F111A] border-[#1E293B]">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Link2 className="w-5 h-5 text-primary" />
                  Invitaciones
                </CardTitle>
                <CardDescription>
                  Genera y administra links de invitación para nuevos residentes
                </CardDescription>
              </CardHeader>
              <CardContent>
                <InvitationsSection onInviteCreated={fetchPendingCount} />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
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
            <AlertDialogTitle className="flex items-center gap-2">
              {newStatus === 'blocked' && <Lock className="w-5 h-5 text-red-400" />}
              {newStatus === 'suspended' && <AlertTriangle className="w-5 h-5 text-yellow-400" />}
              {newStatus === 'active' && <Unlock className="w-5 h-5 text-green-400" />}
              {newStatus === 'blocked' ? 'Bloquear Usuario' : 
               newStatus === 'suspended' ? 'Suspender Usuario' : 'Activar Usuario'}
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-3 text-muted-foreground text-sm">
                <p>
                  {newStatus === 'blocked' 
                    ? `¿Estás seguro de bloquear a ${selectedUser?.full_name}? El usuario no podrá iniciar sesión y su sesión actual será cerrada inmediatamente.`
                    : newStatus === 'suspended'
                    ? `¿Estás seguro de suspender a ${selectedUser?.full_name}? El usuario no podrá acceder temporalmente.`
                    : `¿Estás seguro de activar a ${selectedUser?.full_name}? El usuario podrá iniciar sesión nuevamente.`}
                </p>
                {selectedUser?.roles?.includes('Residente') && newStatus === 'blocked' && (
                  <p className="text-cyan-400">
                    ✓ Esto liberará 1 asiento de tu plan de residentes.
                  </p>
                )}
                {selectedUser?.roles?.includes('Residente') && newStatus === 'active' && !seatUsage.can_add_resident && (
                  <p className="text-red-400">
                    ⚠️ No hay asientos disponibles. Aumenta tu plan o bloquea otros residentes primero.
                  </p>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          
          {newStatus === 'blocked' && (
            <div className="space-y-2 py-2">
              <Label className="text-sm text-muted-foreground">Motivo (opcional)</Label>
              <Textarea
                value={statusReason}
                onChange={(e) => setStatusReason(e.target.value)}
                placeholder="Ej: Incumplimiento de reglas del condominio"
                className="bg-[#0A0A0F] border-[#1E293B] resize-none h-20"
              />
            </div>
          )}
          
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => {
              setStatusReason('');
              setNewStatus('');
            }}>
              Cancelar
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleChangeUserStatus}
              className={
                newStatus === 'blocked' ? 'bg-red-600 hover:bg-red-700' : 
                newStatus === 'suspended' ? 'bg-yellow-600 hover:bg-yellow-700' :
                'bg-green-600 hover:bg-green-700'
              }
              disabled={actionLoading || (newStatus === 'active' && selectedUser?.roles?.includes('Residente') && !seatUsage.can_add_resident)}
            >
              {actionLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : newStatus === 'blocked' ? (
                'Bloquear'
              ) : newStatus === 'suspended' ? (
                'Suspender'
              ) : (
                'Activar'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete User Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="bg-[#0F111A] border-[#1E293B]">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-red-400">
              <Trash2 className="w-5 h-5" />
              Eliminar Usuario
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-3 text-muted-foreground text-sm">
                <p>
                  ¿Estás seguro de eliminar permanentemente a <strong className="text-foreground">{selectedUser?.full_name}</strong>?
                </p>
                <p className="text-red-400 font-medium">
                  Esta acción no se puede deshacer.
                </p>
                {selectedUser?.roles?.includes('Residente') && (
                  <p className="text-cyan-400">
                    ✓ Esto liberará 1 asiento de tu plan de residentes.
                  </p>
                )}
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteUser}
              className="bg-red-600 hover:bg-red-700"
              disabled={actionLoading}
            >
              {actionLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                'Eliminar Permanentemente'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </DashboardLayout>
  );
};

export default UserManagementPage;
