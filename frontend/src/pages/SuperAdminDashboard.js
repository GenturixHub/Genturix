/**
 * GENTURIX - Super Admin Dashboard
 * 
 * Platform-level administration for multi-tenant management
 * 
 * Sections:
 * 1. Overview - Platform stats, KPIs, and System Config
 * 2. Condominiums - CRUD and configuration
 * 3. Modules - Per-condominium module toggling
 * 4. Users - Global user oversight
 * 5. Pricing - Plans and discounts
 * 6. Content - Course management (placeholder)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { ScrollArea } from '../components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import api from '../services/api';
import { useIsMobile } from '../components/layout/BottomNav';
import { MobileCard, MobileCardList } from '../components/MobileComponents';
import { 
  Shield, 
  Building2,
  Users,
  DollarSign,
  Activity,
  Settings,
  Plus,
  Edit,
  Trash2,
  Lock,
  Unlock,
  RefreshCw,
  Search,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff,
  LogOut,
  Loader2,
  Zap,
  BookOpen,
  BarChart3,
  Archive,
  Play,
  Pause,
  Crown,
  Building,
  GraduationCap,
  CreditCard,
  Bell,
  Calendar,
  Video,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  UserPlus,
  Copy,
  AlertOctagon,
  ShieldAlert,
  LayoutDashboard,
  User,
  TrendingUp
} from 'lucide-react';
import { cn } from '../lib/utils';
import { Mail, MailX } from 'lucide-react';

// Super Admin Mobile Navigation
const SuperAdminMobileNav = ({ activeTab, onTabChange }) => {
  const navigate = useNavigate();
  
  const items = [
    { id: 'overview', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'condominiums', label: 'Condos', icon: Building2 },
    { id: 'content', label: 'Contenido', icon: BookOpen },
    { id: 'users', label: 'Usuarios', icon: Users },
    { id: 'profile', label: 'Perfil', icon: User, href: '/profile' },
  ];

  const handleNavClick = (item) => {
    if (item.href) {
      navigate(item.href);
    } else {
      onTabChange(item.id);
    }
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-[#0A0A0F]/95 backdrop-blur-lg border-t border-[#1E293B] safe-area-bottom" data-testid="superadmin-mobile-nav">
      <div className="flex items-center justify-around px-2 py-1">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => handleNavClick(item)}
              data-testid={`superadmin-nav-${item.id}`}
              className={cn(
                'flex flex-col items-center justify-center gap-1 py-2 px-3 min-w-[60px]',
                'transition-all duration-200 active:scale-95',
                isActive ? 'text-yellow-400' : 'text-muted-foreground hover:text-white'
              )}
            >
              <div className={cn(
                'w-10 h-10 rounded-xl flex items-center justify-center',
                isActive ? 'bg-yellow-500/20' : 'bg-transparent'
              )}>
                <Icon className={cn('w-5 h-5', isActive ? 'text-yellow-400' : '')} />
              </div>
              <span className="text-[10px] font-medium">{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};

// ============================================
// MODULE CONFIGURATION
// ============================================
const MODULES = [
  { id: 'security', name: 'Seguridad', description: 'Botón de pánico, alertas', icon: Shield, color: 'text-red-400' },
  { id: 'visits', name: 'Visitas', description: 'Control de visitantes', icon: Users, color: 'text-blue-400' },
  { id: 'hr', name: 'RRHH', description: 'Recursos humanos, turnos', icon: Building, color: 'text-cyan-400' },
  { id: 'school', name: 'Escuela', description: 'Cursos y certificaciones', icon: GraduationCap, color: 'text-cyan-400' },
  { id: 'payments', name: 'Pagos', description: 'Facturación y cobros', icon: CreditCard, color: 'text-green-400' },
  { id: 'audit', name: 'Auditoría', description: 'Logs y trazabilidad', icon: Activity, color: 'text-orange-400' },
  { id: 'reservations', name: 'Reservaciones', description: 'Áreas comunes', icon: Calendar, color: 'text-pink-400', future: true },
  { id: 'cctv', name: 'CCTV', description: 'Integración cámaras', icon: Video, color: 'text-yellow-400', future: true },
];

const STATUS_CONFIG = {
  active: { label: 'Activo', color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: CheckCircle },
  demo: { label: 'Demo', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', icon: Play },
  suspended: { label: 'Suspendido', color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: Pause },
};

// ============================================
// SYSTEM RESET BUTTON (Danger Zone)
// ============================================
const SystemResetButton = ({ onSuccess }) => {
  const [isResetting, setIsResetting] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [confirmText, setConfirmText] = useState('');

  const handleReset = async () => {
    if (confirmText !== 'BORRAR TODO') {
      toast.error('Debes escribir "BORRAR TODO" para confirmar');
      return;
    }

    setIsResetting(true);
    try {
      const result = await api.resetAllData();
      toast.success(result.message);
      setShowConfirm(false);
      setConfirmText('');
      if (onSuccess) onSuccess();
    } catch (error) {
      toast.error(`Error: ${error.message || 'No se pudo limpiar el sistema'}`);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <>
      <Button
        variant="outline"
        className="w-full border-red-500/50 text-red-400 hover:bg-red-500/10 hover:border-red-500"
        onClick={() => setShowConfirm(true)}
        data-testid="reset-all-btn"
      >
        <Trash2 className="w-4 h-4 mr-2" />
        Limpiar Sistema Completo
      </Button>

      <AlertDialog open={showConfirm} onOpenChange={setShowConfirm}>
        <AlertDialogContent className="bg-[#0F111A] border-[#1E293B]">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-red-400">
              <AlertTriangle className="w-5 h-5" />
              ⚠️ ACCIÓN IRREVERSIBLE
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-3">
              <p>Esta acción eliminará <strong>TODOS</strong> los datos del sistema:</p>
              <ul className="list-disc pl-6 space-y-1 text-sm">
                <li>Todos los condominios</li>
                <li>Todos los usuarios (excepto tu cuenta SuperAdmin)</li>
                <li>Todos los guardias y turnos</li>
                <li>Todas las reservaciones y áreas</li>
                <li>Todas las autorizaciones de visitantes</li>
                <li>Todos los registros de acceso y auditoría</li>
              </ul>
              <p className="text-red-400 font-semibold mt-4">
                Para confirmar, escribe &quot;BORRAR TODO&quot; en el campo de abajo:
              </p>
              <Input
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder="Escribe BORRAR TODO"
                className="bg-[#0A0A0F] border-red-500/50 text-center font-mono"
              />
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="bg-[#1E293B] border-[#2D3B4F]">
              Cancelar
            </AlertDialogCancel>
            <Button
              variant="destructive"
              onClick={handleReset}
              disabled={isResetting || confirmText !== 'BORRAR TODO'}
              className="bg-red-600 hover:bg-red-700"
            >
              {isResetting ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Trash2 className="w-4 h-4 mr-2" />
              )}
              Borrar Todo
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

// ============================================
// SYSTEM CONFIG SECTION (Email Toggle)
// ============================================
const SystemConfigSection = ({ onRefreshStats }) => {
  const [emailConfig, setEmailConfig] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isToggling, setIsToggling] = useState(false);

  useEffect(() => {
    fetchEmailConfig();
  }, []);

  const fetchEmailConfig = async () => {
    try {
      const data = await api.getEmailStatus();
      setEmailConfig(data);
    } catch (error) {
      console.error('Error fetching email config:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggle = async (newValue) => {
    setIsToggling(true);
    try {
      const result = await api.setEmailStatus(newValue);
      setEmailConfig({
        ...emailConfig,
        email_enabled: result.email_enabled,
        status_text: result.status_text,
        updated_at: result.updated_at,
        updated_by: result.updated_by
      });
      toast.success(result.message);
    } catch (error) {
      toast.error(error.message || 'Error al cambiar configuración');
    } finally {
      setIsToggling(false);
    }
  };

  if (isLoading) {
    return (
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardContent className="p-4 flex items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  const isEnabled = emailConfig?.email_enabled;

  return (
    <Card className={`bg-[#0F111A] border-2 ${isEnabled ? 'border-green-500/30' : 'border-yellow-500/30'}`}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Settings className="w-5 h-5 text-blue-400" />
          Configuración del Sistema
        </CardTitle>
        <CardDescription>
          Controla las funcionalidades del sistema para pruebas y producción
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Email Toggle */}
        <div className={`p-4 rounded-lg border ${
          isEnabled 
            ? 'bg-green-500/5 border-green-500/30' 
            : 'bg-yellow-500/5 border-yellow-500/30'
        }`}>
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              {isEnabled ? (
                <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                  <Mail className="w-5 h-5 text-green-400" />
                </div>
              ) : (
                <div className="w-10 h-10 rounded-lg bg-yellow-500/20 flex items-center justify-center">
                  <MailX className="w-5 h-5 text-yellow-400" />
                </div>
              )}
              <div>
                <p className="font-semibold text-white">Envío de Emails</p>
                <p className={`text-sm ${isEnabled ? 'text-green-400' : 'text-yellow-400'}`}>
                  {emailConfig?.status_text || (isEnabled ? 'Habilitado' : 'Deshabilitado')}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <Switch
                checked={isEnabled}
                onCheckedChange={handleToggle}
                disabled={isToggling}
                data-testid="email-toggle-switch"
              />
              {isToggling && <Loader2 className="w-4 h-4 animate-spin" />}
            </div>
          </div>
          
          {/* Status Details */}
          <div className="mt-3 pt-3 border-t border-[#1E293B] text-xs text-muted-foreground">
            {isEnabled ? (
              <div className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-green-400 font-medium">Modo Producción</p>
                  <p>• Credenciales enviadas por email</p>
                  <p>• Cambio de contraseña obligatorio en primer login</p>
                  <p>• Contraseña NO visible en la interfaz</p>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-yellow-400 font-medium">Modo Pruebas</p>
                  <p>• Emails NO se envían</p>
                  <p>• Sin cambio de contraseña obligatorio</p>
                  <p>• Contraseña visible en la interfaz después de crear usuario</p>
                </div>
              </div>
            )}
          </div>

          {/* Last Updated */}
          {emailConfig?.updated_by && (
            <p className="mt-2 text-xs text-muted-foreground">
              Último cambio: {emailConfig.updated_by} • {new Date(emailConfig.updated_at).toLocaleString('es-ES')}
            </p>
          )}
        </div>

        {/* Danger Zone - System Reset */}
        <div className="p-4 rounded-lg border-2 border-red-500/30 bg-red-500/5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <p className="font-semibold text-red-400">Zona de Peligro</p>
              <p className="text-xs text-muted-foreground">Acciones irreversibles</p>
            </div>
          </div>
          <SystemResetButton onSuccess={onRefreshStats} />
        </div>
      </CardContent>
    </Card>
  );
};

// ============================================
// BILLING SUMMARY SECTION (Executive View)
// ============================================
const BillingSummarySection = ({ billingOverview }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const INITIAL_DISPLAY_COUNT = 3;
  
  const condominiums = billingOverview?.condominiums || [];
  const totals = billingOverview?.totals || {};
  const hasMoreItems = condominiums.length > INITIAL_DISPLAY_COUNT;
  const displayedCondos = isExpanded ? condominiums : condominiums.slice(0, INITIAL_DISPLAY_COUNT);
  
  // Calculate overall seat usage percentage
  const overallUsagePercent = totals.total_paid_seats > 0 
    ? Math.round((totals.total_active_users / totals.total_paid_seats) * 100) 
    : 0;

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-emerald-400" />
              Facturación SaaS por Condominio
            </CardTitle>
            <CardDescription className="mt-1">
              Resumen ejecutivo de asientos y suscripciones
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Executive Summary - Always visible at top */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* Total Condominiums */}
          <div className="p-3 rounded-lg bg-gradient-to-br from-blue-500/10 to-blue-500/5 border border-blue-500/20">
            <div className="flex items-center gap-2 mb-1">
              <Building2 className="w-4 h-4 text-blue-400" />
              <span className="text-xs text-blue-400 font-medium">Condominios</span>
            </div>
            <p className="text-2xl font-bold text-white">{totals.total_condominiums || 0}</p>
          </div>
          
          {/* Total Users / Seats */}
          <div className="p-3 rounded-lg bg-gradient-to-br from-cyan-500/10 to-cyan-500/5 border border-cyan-500/20">
            <div className="flex items-center gap-2 mb-1">
              <Users className="w-4 h-4 text-cyan-400" />
              <span className="text-xs text-cyan-400 font-medium">Usuarios</span>
            </div>
            <p className="text-2xl font-bold text-white">
              {totals.total_active_users || 0}
              <span className="text-sm font-normal text-muted-foreground">/{totals.total_paid_seats || 0}</span>
            </p>
          </div>
          
          {/* MRR */}
          <div className="p-3 rounded-lg bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 border border-emerald-500/20">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="w-4 h-4 text-emerald-400" />
              <span className="text-xs text-emerald-400 font-medium">MRR</span>
            </div>
            <p className="text-2xl font-bold text-white">
              ${totals.total_monthly_revenue?.toFixed(0) || 0}
              <span className="text-xs font-normal text-muted-foreground ml-1">USD</span>
            </p>
          </div>
          
          {/* Capacity Usage */}
          <div className="p-3 rounded-lg bg-gradient-to-br from-amber-500/10 to-amber-500/5 border border-amber-500/20">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-amber-400" />
              <span className="text-xs text-amber-400 font-medium">Capacidad</span>
            </div>
            <div className="flex items-center gap-2">
              <p className="text-2xl font-bold text-white">{overallUsagePercent}%</p>
              <div className="flex-1 h-2 bg-[#1E293B] rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-500 ${
                    overallUsagePercent >= 90 ? 'bg-red-500' :
                    overallUsagePercent >= 70 ? 'bg-amber-500' :
                    'bg-emerald-500'
                  }`}
                  style={{ width: `${overallUsagePercent}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Condominiums List - Collapsible with Scroll */}
        <div className="pt-2">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-muted-foreground">
              Detalle por Condominio
            </h4>
            {hasMoreItems && (
              <span className="text-xs text-muted-foreground">
                Mostrando {displayedCondos.length} de {condominiums.length}
              </span>
            )}
          </div>
          
          {/* Scrollable List Container - Production Safe */}
          <div 
            className="space-y-2 transition-all duration-300 ease-in-out"
            style={{ 
              maxHeight: isExpanded ? 'min(60vh, 600px)' : `${INITIAL_DISPLAY_COUNT * 80}px`,
              overflowY: isExpanded && condominiums.length > 6 ? 'auto' : 'hidden',
              overscrollBehavior: 'contain',
              scrollbarWidth: 'thin',
              scrollbarColor: '#3B82F6 #1E293B'
            }}
          >
            {displayedCondos.map((condo, index) => (
              <div 
                key={condo.condominium_id}
                className="p-3 rounded-lg bg-[#1E293B]/30 border border-[#1E293B] hover:bg-[#1E293B]/50 transition-colors"
                style={{
                  animation: isExpanded && index >= INITIAL_DISPLAY_COUNT 
                    ? `fadeIn 0.3s ease-out ${(index - INITIAL_DISPLAY_COUNT) * 0.1}s forwards` 
                    : 'none',
                  opacity: isExpanded && index >= INITIAL_DISPLAY_COUNT ? 0 : 1
                }}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{condo.condominium_name}</p>
                    <p className="text-xs text-muted-foreground">
                      ${condo.monthly_revenue?.toFixed(2)} USD/mes
                    </p>
                  </div>
                  <Badge 
                    variant="outline" 
                    className={`ml-2 shrink-0 ${
                      condo.billing_status === 'active' ? 'text-green-400 border-green-400/30 bg-green-400/5' :
                      condo.billing_status === 'trialing' ? 'text-blue-400 border-blue-400/30 bg-blue-400/5' :
                      condo.billing_status === 'past_due' ? 'text-yellow-400 border-yellow-400/30 bg-yellow-400/5' :
                      'text-red-400 border-red-400/30 bg-red-400/5'
                    }`}
                  >
                    {condo.billing_status === 'active' ? 'Activo' :
                     condo.billing_status === 'trialing' ? 'Prueba' :
                     condo.billing_status === 'past_due' ? 'Pendiente' :
                     'Cancelado'}
                  </Badge>
                </div>
                
                <div className="flex items-center gap-3 text-sm">
                  <div className="flex items-center gap-1 shrink-0">
                    <Users className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="text-xs">{condo.active_users}/{condo.paid_seats}</span>
                  </div>
                  <div className="flex-1">
                    <div className="h-1.5 bg-[#0A0A0F] rounded-full overflow-hidden">
                      <div 
                        className={`h-full transition-all duration-500 ${
                          condo.remaining_seats <= 0 ? 'bg-red-500' :
                          condo.remaining_seats <= 2 ? 'bg-yellow-500' :
                          'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.min(100, (condo.active_users / condo.paid_seats) * 100)}%` }}
                      />
                    </div>
                  </div>
                  <span className={`text-xs shrink-0 ${condo.remaining_seats <= 0 ? 'text-red-400' : 'text-muted-foreground'}`}>
                    {condo.remaining_seats} disp.
                  </span>
                </div>
              </div>
            ))}
          </div>
          
          {/* Expand/Collapse Button */}
          {hasMoreItems && (
            <Button
              variant="ghost"
              size="sm"
              className="w-full mt-3 text-muted-foreground hover:text-white hover:bg-[#1E293B]/50 transition-colors"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="w-4 h-4 mr-2" />
                  Ver menos
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4 mr-2" />
                  Ver más ({condominiums.length - INITIAL_DISPLAY_COUNT} restantes)
                </>
              )}
            </Button>
          )}
        </div>
      </CardContent>
      
      {/* CSS Animation for fadeIn */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </Card>
  );
};

// ============================================
// OVERVIEW TAB
// ============================================
const OverviewTab = ({ stats, billingOverview, isLoading, onRefresh, onNavigateTab, navigate }) => {
  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>;
  }

  return (
    <div className="p-6 space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center">
                <Building2 className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats?.condominiums?.total || 0}</p>
                <p className="text-xs text-muted-foreground">Condominios</p>
              </div>
            </div>
            <div className="flex gap-2 mt-3 text-xs">
              <Badge variant="outline" className="text-green-400 border-green-400/30">{stats?.condominiums?.active || 0} activos</Badge>
              <Badge variant="outline" className="text-blue-400 border-blue-400/30">{stats?.condominiums?.demo || 0} demo</Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-cyan-500/20 flex items-center justify-center">
                <Users className="w-6 h-6 text-cyan-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{billingOverview?.totals?.total_active_users || stats?.users?.total || 0}</p>
                <p className="text-xs text-muted-foreground">Usuarios Activos</p>
              </div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              de {billingOverview?.totals?.total_paid_seats || 0} asientos pagados
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">${billingOverview?.totals?.total_monthly_revenue?.toFixed(2) || stats?.revenue?.mrr_usd || 0}</p>
                <p className="text-xs text-muted-foreground">MRR (USD)</p>
              </div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              ${stats?.revenue?.price_per_user || 1}/usuario/mes
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-red-500/20 flex items-center justify-center">
                <AlertTriangle className="w-6 h-6 text-red-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats?.alerts?.active || 0}</p>
                <p className="text-xs text-muted-foreground">Alertas Activas</p>
              </div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              {stats?.alerts?.total || 0} totales
            </div>
          </CardContent>
        </Card>
      </div>

      {/* SaaS Billing Overview */}
      {billingOverview && billingOverview.condominiums?.length > 0 && (
        <BillingSummarySection billingOverview={billingOverview} />
      )}

      {/* Quick Actions */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            Acciones Rápidas
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Button 
              variant="outline" 
              className="h-auto py-4 flex-col gap-2 border-primary/50 hover:bg-primary/10 bg-primary/5"
              onClick={() => navigate('/super-admin/onboarding')}
              data-testid="quick-action-new-condo"
            >
              <Plus className="w-5 h-5 text-primary" />
              <span className="text-xs font-medium">Nuevo Condominio</span>
            </Button>
            <Button 
              variant="outline" 
              className="h-auto py-4 flex-col gap-2 border-[#1E293B] hover:bg-[#1E293B]"
              onClick={() => onNavigateTab('condominiums')}
              data-testid="quick-action-create-demo"
            >
              <Play className="w-5 h-5 text-green-400" />
              <span className="text-xs">Crear Demo</span>
            </Button>
            <Button 
              variant="outline" 
              className="h-auto py-4 flex-col gap-2 border-[#1E293B] hover:bg-[#1E293B]"
              onClick={() => onNavigateTab('users')}
              data-testid="quick-action-view-users"
            >
              <Users className="w-5 h-5 text-cyan-400" />
              <span className="text-xs">Ver Usuarios</span>
            </Button>
            <Button 
              variant="outline" 
              className="h-auto py-4 flex-col gap-2 border-[#1E293B] hover:bg-[#1E293B]"
              onClick={() => onNavigateTab('content')}
              data-testid="quick-action-view-audit"
            >
              <Activity className="w-5 h-5 text-orange-400" />
              <span className="text-xs">Ver Contenido</span>
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* System Configuration */}
      <SystemConfigSection onRefreshStats={onRefresh} />

      {/* Platform Info */}
      <div className="text-center text-xs text-muted-foreground">
        <p>GENTURIX Platform • Multi-tenant Security System</p>
        <p className="mt-1">Modelo de Precios: <strong className="text-green-400">$1 USD / usuario / mes</strong></p>
      </div>
    </div>
  );
};

// ============================================
// CONDOMINIUMS TAB
// ============================================
const CondominiumsTab = ({ condos, onRefresh, onEdit, onCreate, isSuperAdmin, navigate }) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDemoWizard, setShowDemoWizard] = useState(false);
  const [selectedCondo, setSelectedCondo] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateAdminDialog, setShowCreateAdminDialog] = useState(false);
  const [adminTargetCondo, setAdminTargetCondo] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteTargetCondo, setDeleteTargetCondo] = useState(null);

  const filteredCondos = condos.filter(c => {
    const matchesSearch = c.name?.toLowerCase().includes(search.toLowerCase()) ||
                         c.contact_email?.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || c.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const handleStatusChange = async (condoId, newStatus) => {
    setIsLoading(true);
    try {
      await api.updateCondoStatus(condoId, newStatus);
      onRefresh();
    } catch (error) {
      alert('Error updating status');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateAdmin = (condo) => {
    setAdminTargetCondo(condo);
    setShowCreateAdminDialog(true);
  };

  const handleDeleteCondo = (condo) => {
    setDeleteTargetCondo(condo);
    setShowDeleteDialog(true);
  };

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row gap-3 justify-between">
        <div className="flex gap-2 flex-1">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Buscar condominios..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10 bg-[#0A0A0F] border-[#1E293B]"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-32 bg-[#0A0A0F] border-[#1E293B]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#0F111A] border-[#1E293B]">
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="active">Activos</SelectItem>
              <SelectItem value="demo">Demo</SelectItem>
              <SelectItem value="suspended">Suspendidos</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex gap-2 w-full sm:w-auto">
          <Button 
            variant="outline" 
            onClick={() => setShowDemoWizard(true)} 
            className="gap-2 flex-1 sm:flex-none border-yellow-500/30 text-yellow-400 hover:bg-yellow-500/10" 
            data-testid="condos-quick-create-btn"
          >
            <Zap className="w-4 h-4" />
            Demo Rápido
          </Button>
          <Button 
            onClick={() => navigate('/super-admin/onboarding')} 
            className="gap-2 flex-1 sm:flex-none" 
            data-testid="condos-new-condo-btn"
          >
            <Plus className="w-4 h-4" />
            Nuevo Condominio
          </Button>
        </div>
      </div>

      {/* Desktop Table View - hidden on mobile */}
      <Card className="bg-[#0F111A] border-[#1E293B] hidden lg:block">
        <ScrollArea className="h-[500px]">
          <Table>
            <TableHeader>
              <TableRow className="border-[#1E293B] hover:bg-transparent">
                <TableHead className="text-muted-foreground">Condominio</TableHead>
                <TableHead className="text-muted-foreground">Estado</TableHead>
                <TableHead className="text-muted-foreground">Usuarios</TableHead>
                <TableHead className="text-muted-foreground">MRR</TableHead>
                <TableHead className="text-muted-foreground text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCondos.map((condo) => {
                const statusConfig = STATUS_CONFIG[condo.status] || STATUS_CONFIG.active;
                const StatusIcon = statusConfig.icon;
                const userCount = condo.current_users || 0;
                const mrr = userCount * (condo.price_per_user || 1) * (1 - (condo.discount_percent || 0) / 100);

                return (
                  <TableRow key={condo.id} className="border-[#1E293B]">
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                          <Building2 className="w-5 h-5 text-primary" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-white">{condo.name}</p>
                            {/* Environment Badge */}
                            {(condo.environment === 'demo' || condo.is_demo) && (
                              <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30 text-[10px] px-1.5">DEMO</Badge>
                            )}
                            {condo.environment === 'production' && !condo.is_demo && (
                              <Badge className="bg-green-500/20 text-green-400 border-green-500/30 text-[10px] px-1.5">PROD</Badge>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground">{condo.contact_email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={statusConfig.color}>
                        <StatusIcon className="w-3 h-3 mr-1" />
                        {statusConfig.label}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono">{userCount} / {condo.max_users || 100}</span>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-green-400">${mrr.toFixed(2)}</span>
                      {condo.discount_percent > 0 && (
                        <Badge className="ml-2 bg-yellow-500/20 text-yellow-400 text-[10px]">
                          -{condo.discount_percent}%
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button 
                          size="icon" 
                          variant="ghost" 
                          className="h-8 w-8" 
                          onClick={() => handleCreateAdmin(condo)}
                          title="Crear Administrador"
                          data-testid={`create-admin-${condo.id}`}
                        >
                          <UserPlus className="w-4 h-4 text-blue-400" />
                        </Button>
                        <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => setSelectedCondo(condo)}>
                          <Settings className="w-4 h-4" />
                        </Button>
                        <Select 
                          value={condo.status || 'active'} 
                          onValueChange={(status) => handleStatusChange(condo.id, status)}
                        >
                          <SelectTrigger className="w-8 h-8 p-0 border-0 bg-transparent">
                            <ChevronRight className="w-4 h-4" />
                          </SelectTrigger>
                          <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                            <SelectItem value="active">Activar</SelectItem>
                            <SelectItem value="demo">Modo Demo</SelectItem>
                            <SelectItem value="suspended">Suspender</SelectItem>
                          </SelectContent>
                        </Select>
                        {/* Delete Button - Super Admin Only */}
                        {isSuperAdmin && (
                          <Button 
                            size="icon" 
                            variant="ghost" 
                            className="h-8 w-8 hover:bg-red-500/20" 
                            onClick={() => handleDeleteCondo(condo)}
                            title="Eliminar Permanentemente"
                            data-testid={`delete-condo-${condo.id}`}
                          >
                            <Trash2 className="w-4 h-4 text-red-400" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </ScrollArea>
      </Card>

      {/* Mobile Card View */}
      <div className="block lg:hidden space-y-3">
        {filteredCondos.map((condo) => {
          const statusConfig = STATUS_CONFIG[condo.status] || STATUS_CONFIG.active;
          const userCount = condo.current_users || 0;
          const mrr = userCount * (condo.price_per_user || 1) * (1 - (condo.discount_percent || 0) / 100);

          return (
            <MobileCard
              key={condo.id}
              testId={`condo-card-${condo.id}`}
              title={
                <div className="flex items-center gap-2">
                  <span>{condo.name}</span>
                  {(condo.environment === 'demo' || condo.is_demo) && (
                    <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30 text-[10px] px-1.5">DEMO</Badge>
                  )}
                  {condo.environment === 'production' && !condo.is_demo && (
                    <Badge className="bg-green-500/20 text-green-400 border-green-500/30 text-[10px] px-1.5">PROD</Badge>
                  )}
                </div>
              }
              subtitle={condo.contact_email}
              icon={Building2}
              status={statusConfig.label}
              statusColor={condo.status === 'active' ? 'green' : condo.status === 'demo' ? 'yellow' : 'red'}
              details={[
                { label: 'Usuarios', value: `${userCount} / ${condo.max_users || 100}` },
                { label: 'MRR', value: `$${mrr.toFixed(2)}${condo.discount_percent > 0 ? ` (-${condo.discount_percent}%)` : ''}` },
              ]}
              actions={[
                {
                  label: 'Crear Admin',
                  icon: UserPlus,
                  onClick: () => handleCreateAdmin(condo),
                },
                {
                  label: 'Configurar',
                  icon: Settings,
                  onClick: () => setSelectedCondo(condo),
                },
                ...(isSuperAdmin ? [{
                  label: 'Eliminar',
                  icon: Trash2,
                  onClick: () => handleDeleteCondo(condo),
                  variant: 'destructive'
                }] : [])
              ]}
            />
          );
        })}
      </div>

      {/* Create Dialog */}
      <CreateCondoDialog 
        open={showCreateDialog} 
        onClose={() => setShowCreateDialog(false)} 
        onSuccess={() => { setShowCreateDialog(false); onRefresh(); }}
      />

      {/* Demo Wizard Dialog */}
      <DemoWizardDialog 
        open={showDemoWizard} 
        onClose={() => setShowDemoWizard(false)} 
        onSuccess={() => { setShowDemoWizard(false); onRefresh(); }}
      />

      {/* Edit Dialog */}
      {selectedCondo && (
        <EditCondoDialog
          condo={selectedCondo}
          open={!!selectedCondo}
          onClose={() => setSelectedCondo(null)}
          onSuccess={() => { setSelectedCondo(null); onRefresh(); }}
        />
      )}

      {/* Create Admin Dialog */}
      {adminTargetCondo && (
        <CreateAdminDialog
          condo={adminTargetCondo}
          open={showCreateAdminDialog}
          onClose={() => { setShowCreateAdminDialog(false); setAdminTargetCondo(null); }}
          onSuccess={() => { setShowCreateAdminDialog(false); setAdminTargetCondo(null); onRefresh(); }}
        />
      )}

      {/* Delete Condo Dialog - Super Admin Only */}
      {deleteTargetCondo && (
        <DeleteCondoDialog
          condo={deleteTargetCondo}
          open={showDeleteDialog}
          onClose={() => { setShowDeleteDialog(false); setDeleteTargetCondo(null); }}
          onSuccess={() => { setShowDeleteDialog(false); setDeleteTargetCondo(null); onRefresh(); }}
        />
      )}
    </div>
  );
};

// ============================================
// DEMO WIZARD DIALOG - Creates demo with test data
// ============================================
const DemoWizardDialog = ({ open, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    name: '',
    admin_email: '',
    admin_name: 'Admin Demo',
    include_guards: true,
    include_residents: true,
    include_areas: true
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async () => {
    if (!form.name || !form.admin_email) return;
    
    setIsSubmitting(true);
    try {
      const response = await api.createDemoWithTestData(form);
      setResult(response);
      toast.success(`Demo "${form.name}" creado con ${response.credentials?.length || 0} usuarios`);
    } catch (error) {
      toast.error(error.message || 'Error al crear demo');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setForm({
      name: '',
      admin_email: '',
      admin_name: 'Admin Demo',
      include_guards: true,
      include_residents: true,
      include_areas: true
    });
    setResult(null);
    onClose();
    if (result) onSuccess();
  };

  const copyCredentials = () => {
    if (!result?.credentials) return;
    const text = result.credentials.map(c => 
      `${c.role}: ${c.email} / ${c.password}${c.apartment ? ` (${c.apartment})` : ''}`
    ).join('\n');
    navigator.clipboard.writeText(text);
    toast.success('Credenciales copiadas al portapapeles');
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            Demo Rápido con Datos
          </DialogTitle>
          <DialogDescription>
            Crea un condominio demo con usuarios y áreas de prueba pre-cargados
          </DialogDescription>
        </DialogHeader>

        {!result ? (
          <>
            <div className="space-y-4 py-4">
              <div>
                <Label>Nombre del Condominio *</Label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({...form, name: e.target.value})}
                  placeholder="Demo Residencial XYZ"
                  className="bg-[#0A0A0F] border-[#1E293B] mt-1"
                  data-testid="demo-wizard-name"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Email Admin *</Label>
                  <Input
                    type="email"
                    value={form.admin_email}
                    onChange={(e) => setForm({...form, admin_email: e.target.value})}
                    placeholder="admin@cliente.com"
                    className="bg-[#0A0A0F] border-[#1E293B] mt-1"
                    data-testid="demo-wizard-email"
                  />
                </div>
                <div>
                  <Label>Nombre Admin</Label>
                  <Input
                    value={form.admin_name}
                    onChange={(e) => setForm({...form, admin_name: e.target.value})}
                    placeholder="Admin Demo"
                    className="bg-[#0A0A0F] border-[#1E293B] mt-1"
                  />
                </div>
              </div>

              {/* Data Options */}
              <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 space-y-3">
                <p className="text-sm font-medium text-yellow-400 flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  Datos de Prueba Incluidos
                </p>
                
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-2 text-sm cursor-pointer">
                      <Shield className="w-4 h-4 text-blue-400" />
                      Guardias de prueba (2)
                    </Label>
                    <Switch
                      checked={form.include_guards}
                      onCheckedChange={(v) => setForm({...form, include_guards: v})}
                      data-testid="demo-wizard-guards-switch"
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-2 text-sm cursor-pointer">
                      <Users className="w-4 h-4 text-green-400" />
                      Residentes de prueba (3)
                    </Label>
                    <Switch
                      checked={form.include_residents}
                      onCheckedChange={(v) => setForm({...form, include_residents: v})}
                      data-testid="demo-wizard-residents-switch"
                    />
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-2 text-sm cursor-pointer">
                      <Calendar className="w-4 h-4 text-pink-400" />
                      Áreas comunes (Gym, Piscina)
                    </Label>
                    <Switch
                      checked={form.include_areas}
                      onCheckedChange={(v) => setForm({...form, include_areas: v})}
                      data-testid="demo-wizard-areas-switch"
                    />
                  </div>
                </div>
              </div>

              {/* Info Box */}
              <div className="bg-[#0A0A0F] border border-[#1E293B] rounded-lg p-3 text-xs text-muted-foreground space-y-1">
                <p>• Límite fijo de <strong className="text-yellow-400">10 residentes</strong></p>
                <p>• Sin integración con Stripe (facturación deshabilitada)</p>
                <p>• Credenciales visibles solo una vez después de crear</p>
                <p>• Ideal para demostraciones a clientes</p>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>Cancelar</Button>
              <Button 
                onClick={handleSubmit} 
                disabled={!form.name || !form.admin_email || isSubmitting}
                className="bg-yellow-500 hover:bg-yellow-600 text-black"
                data-testid="demo-wizard-submit"
              >
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Zap className="w-4 h-4 mr-2" />}
                Crear Demo
              </Button>
            </DialogFooter>
          </>
        ) : (
          /* Result View - Show Credentials */
          <div className="space-y-4 py-4">
            <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4 text-center">
              <CheckCircle className="w-10 h-10 text-green-400 mx-auto mb-2" />
              <p className="text-green-400 font-semibold">Demo creado exitosamente</p>
              <p className="text-sm text-muted-foreground">{result.condominium?.name}</p>
            </div>

            {/* Credentials Table */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-yellow-400 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  Credenciales (guárdalas ahora)
                </Label>
                <Button size="sm" variant="outline" onClick={copyCredentials} className="gap-1">
                  <Copy className="w-3 h-3" />
                  Copiar
                </Button>
              </div>
              
              <div className="bg-[#0A0A0F] border border-[#1E293B] rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow className="border-[#1E293B]">
                      <TableHead className="text-xs">Rol</TableHead>
                      <TableHead className="text-xs">Email</TableHead>
                      <TableHead className="text-xs">Contraseña</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {result.credentials?.map((cred, idx) => (
                      <TableRow key={idx} className="border-[#1E293B]">
                        <TableCell className="py-2">
                          <Badge variant="outline" className={
                            cred.role === 'Administrador' ? 'border-purple-500/30 text-purple-400' :
                            cred.role === 'Guardia' ? 'border-blue-500/30 text-blue-400' :
                            'border-green-500/30 text-green-400'
                          }>
                            {cred.role}
                          </Badge>
                        </TableCell>
                        <TableCell className="py-2 text-xs font-mono">{cred.email}</TableCell>
                        <TableCell className="py-2 text-xs font-mono text-yellow-400">{cred.password}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>

            {/* Areas Created */}
            {result.areas_created?.length > 0 && (
              <div className="bg-pink-500/10 border border-pink-500/20 rounded-lg p-3">
                <p className="text-sm font-medium text-pink-400 mb-2">Áreas Creadas</p>
                <div className="flex gap-2 flex-wrap">
                  {result.areas_created.map((area, idx) => (
                    <Badge key={idx} variant="outline" className="border-pink-500/30 text-pink-300">
                      {area.name} ({area.capacity} cap.)
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <DialogFooter>
              <Button onClick={handleClose} className="w-full">
                <CheckCircle className="w-4 h-4 mr-2" />
                Cerrar
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// CREATE CONDO DIALOG
// ============================================
const CreateCondoDialog = ({ open, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    name: '',
    address: '',
    contact_email: '',
    contact_phone: '',
    max_users: 100,
    paid_seats: 10,
    environment: 'production'  // "demo" or "production"
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.name || !form.contact_email) return;
    
    setIsSubmitting(true);
    try {
      // Use different endpoint based on environment selection
      if (form.environment === 'demo') {
        // Demo endpoint - simplified payload (no billing fields)
        await api.createDemoCondominium({
          name: form.name,
          address: form.address || 'Demo Address',
          contact_email: form.contact_email,
          contact_phone: form.contact_phone || ''
        });
      } else {
        // Production endpoint - full payload with billing
        await api.createCondominium({
          name: form.name,
          address: form.address,
          contact_email: form.contact_email,
          contact_phone: form.contact_phone,
          max_users: form.max_users,
          paid_seats: form.paid_seats
        });
      }
      toast.success(`Condominio ${form.environment === 'demo' ? 'DEMO' : 'de PRODUCCIÓN'} creado exitosamente`);
      onSuccess();
      setForm({ name: '', address: '', contact_email: '', contact_phone: '', max_users: 100, paid_seats: 10, environment: 'production' });
    } catch (error) {
      toast.error(error.message || 'Error al crear condominio');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Building2 className="w-5 h-5 text-primary" />
            Nuevo Condominio
          </DialogTitle>
          <DialogDescription>
            Crear un nuevo tenant en la plataforma GENTURIX
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <Label>Nombre *</Label>
            <Input
              value={form.name}
              onChange={(e) => setForm({...form, name: e.target.value})}
              placeholder="Residencial Las Palmas"
              className="bg-[#0A0A0F] border-[#1E293B] mt-1"
            />
          </div>
          <div>
            <Label>Dirección</Label>
            <Input
              value={form.address}
              onChange={(e) => setForm({...form, address: e.target.value})}
              placeholder="Av. Principal 123"
              className="bg-[#0A0A0F] border-[#1E293B] mt-1"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Email Contacto *</Label>
              <Input
                type="email"
                value={form.contact_email}
                onChange={(e) => setForm({...form, contact_email: e.target.value})}
                placeholder="admin@condo.com"
                className="bg-[#0A0A0F] border-[#1E293B] mt-1"
              />
            </div>
            <div>
              <Label>Teléfono</Label>
              <Input
                value={form.contact_phone}
                onChange={(e) => setForm({...form, contact_phone: e.target.value})}
                placeholder="+52 555 123 4567"
                className="bg-[#0A0A0F] border-[#1E293B] mt-1"
              />
            </div>
          </div>
          
          {/* Seat Limit - only shown for production */}
          {form.environment === 'production' && (
            <div>
              <Label>Asientos Iniciales (Paid Seats)</Label>
              <Input
                type="number"
                value={form.paid_seats}
                onChange={(e) => setForm({...form, paid_seats: parseInt(e.target.value) || 10, max_users: parseInt(e.target.value) || 100})}
                className="bg-[#0A0A0F] border-[#1E293B] mt-1"
                min={1}
              />
              <p className="text-xs text-muted-foreground mt-1">Número de usuarios facturables</p>
            </div>
          )}
          
          {/* Environment Selector */}
          <div className="space-y-2">
            <Label>Tipo de Tenant</Label>
            <Select 
              value={form.environment} 
              onValueChange={(v) => setForm({...form, environment: v, paid_seats: v === 'demo' ? 10 : form.paid_seats})}
            >
              <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B]">
                <SelectValue placeholder="Seleccionar tipo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="production">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-green-500/20 text-green-400 border-green-500/30 text-[10px]">PRODUCCIÓN</Badge>
                    <span>Stripe activo, facturación real</span>
                  </div>
                </SelectItem>
                <SelectItem value="demo">
                  <div className="flex items-center gap-2">
                    <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30 text-[10px]">DEMO</Badge>
                    <span>Sin cargos, solo pruebas</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            
            {/* Demo Environment Info */}
            {form.environment === 'demo' && (
              <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">DEMO</Badge>
                  <span className="text-yellow-400 text-sm font-medium">Modo Demostración</span>
                </div>
                <ul className="text-xs text-yellow-200/70 space-y-1">
                  <li>• Límite fijo de <strong>10 residentes</strong></li>
                  <li>• Sin integración con Stripe</li>
                  <li>• No genera cargos</li>
                  <li>• Credenciales visibles en pantalla (no email)</li>
                </ul>
              </div>
            )}
            
            {/* Production Environment Info */}
            {form.environment === 'production' && (
              <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 space-y-2">
                <div className="flex items-center gap-2">
                  <Badge className="bg-green-500/20 text-green-400 border-green-500/30">PRODUCCIÓN</Badge>
                  <span className="text-green-400 text-sm font-medium">Modo Producción</span>
                </div>
                <ul className="text-xs text-green-200/70 space-y-1">
                  <li>• Facturación activa vía Stripe</li>
                  <li>• Compra de asientos disponible</li>
                  <li>• Emails de credenciales vía Resend</li>
                  <li>• Cambio de contraseña obligatorio</li>
                </ul>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={handleSubmit} disabled={!form.name || !form.contact_email || isSubmitting}>
            {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />}
            Crear
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// EDIT CONDO DIALOG (Modules & Pricing)
// ============================================
const EditCondoDialog = ({ condo, open, onClose, onSuccess }) => {
  const [activeTab, setActiveTab] = useState('modules');
  const [modules, setModules] = useState(condo.modules || {});
  const [pricing, setPricing] = useState({
    discount_percent: condo.discount_percent || 0,
    free_modules: condo.free_modules || [],
    plan: condo.plan || 'basic'
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [togglingModule, setTogglingModule] = useState(null); // Track which module is being toggled

  const handleModuleToggle = async (moduleId, enabled) => {
    setTogglingModule(moduleId);
    console.log(`[module-toggle] Toggling module '${moduleId}' to enabled=${enabled} for condo '${condo.id}'`);
    
    try {
      const response = await api.updateCondoModule(condo.id, moduleId, enabled);
      console.log(`[module-toggle] API Response:`, response);
      
      // Update local state - always use object format now
      setModules(prev => ({
        ...prev,
        [moduleId]: { enabled }
      }));
      const moduleName = MODULES.find(m => m.id === moduleId)?.name || moduleId;
      toast.success(`Módulo "${moduleName}" ${enabled ? 'activado' : 'desactivado'}`);
    } catch (error) {
      console.error(`[module-toggle] ERROR:`, error);
      const errorMsg = error.message || 'Error desconocido';
      toast.error(`Error al actualizar módulo: ${errorMsg}`);
    } finally {
      setTogglingModule(null);
    }
  };

  const handleSavePricing = async () => {
    setIsSubmitting(true);
    try {
      await api.updateCondoPricing(condo.id, pricing.discount_percent, pricing.plan);
      toast.success('Precios actualizados correctamente');
      onSuccess();
    } catch (error) {
      toast.error(`Error al actualizar precios: ${error.message || 'Error desconocido'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetDemo = async () => {
    if (!confirm('¿Resetear todos los datos de demo? Esta acción no se puede deshacer.')) return;
    
    setIsSubmitting(true);
    try {
      await api.resetDemoData(condo.id);
      toast.success('Datos de demo reseteados correctamente');
      onSuccess();
    } catch (error) {
      toast.error(`Error al resetear datos: ${error.message || 'Error desconocido'}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-primary" />
            {condo.name}
          </DialogTitle>
          <DialogDescription>
            Configuración de módulos y precios
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid grid-cols-3 bg-[#0A0A0F]">
            <TabsTrigger value="modules">Módulos</TabsTrigger>
            <TabsTrigger value="pricing">Precios</TabsTrigger>
            <TabsTrigger value="demo">Demo</TabsTrigger>
          </TabsList>

          <TabsContent value="modules" className="space-y-3 mt-4">
            {MODULES.map((mod) => {
              // Handle both legacy boolean format and new object format
              const moduleValue = modules[mod.id];
              const isEnabled = typeof moduleValue === 'boolean' 
                ? moduleValue 
                : moduleValue?.enabled !== false;
              const ModIcon = mod.icon;
              const isToggling = togglingModule === mod.id;
              
              return (
                <div 
                  key={mod.id}
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    mod.future 
                      ? 'bg-[#0A0A0F]/50 border-[#1E293B]/50 opacity-50' 
                      : isToggling
                        ? 'bg-primary/5 border-primary/30'
                        : 'bg-[#0A0A0F] border-[#1E293B]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <ModIcon className={`w-5 h-5 ${mod.color}`} />
                    <div>
                      <p className="font-medium text-sm">{mod.name}</p>
                      <p className="text-xs text-muted-foreground">{mod.description}</p>
                    </div>
                  </div>
                  {mod.future ? (
                    <Badge variant="outline" className="text-xs">Próximamente</Badge>
                  ) : isToggling ? (
                    <Loader2 className="w-5 h-5 animate-spin text-primary" />
                  ) : (
                    <Switch
                      checked={isEnabled}
                      onCheckedChange={(checked) => handleModuleToggle(mod.id, checked)}
                      disabled={togglingModule !== null}
                      data-testid={`module-toggle-${mod.id}`}
                    />
                  )}
                </div>
              );
            })}
          </TabsContent>

          <TabsContent value="pricing" className="space-y-4 mt-4">
            <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/30">
              <p className="text-sm text-green-400 font-medium">Precio Base: $1 USD / usuario / mes</p>
              <p className="text-xs text-muted-foreground mt-1">Este es el precio base de la plataforma</p>
            </div>

            <div>
              <Label>Descuento (%)</Label>
              <Input
                type="number"
                min={0}
                max={100}
                value={pricing.discount_percent}
                onChange={(e) => setPricing({...pricing, discount_percent: parseInt(e.target.value) || 0})}
                className="bg-[#0A0A0F] border-[#1E293B] mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Precio final: ${(1 * (1 - pricing.discount_percent / 100)).toFixed(2)} / usuario / mes
              </p>
            </div>

            <div>
              <Label>Plan</Label>
              <Select value={pricing.plan} onValueChange={(v) => setPricing({...pricing, plan: v})}>
                <SelectTrigger className="bg-[#0A0A0F] border-[#1E293B] mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="basic">Básico</SelectItem>
                  <SelectItem value="pro">Profesional</SelectItem>
                  <SelectItem value="enterprise">Enterprise</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button onClick={handleSavePricing} disabled={isSubmitting} className="w-full">
              {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Guardar Cambios
            </Button>
          </TabsContent>

          <TabsContent value="demo" className="space-y-4 mt-4">
            {condo.is_demo ? (
              <>
                <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
                  <p className="text-sm text-blue-400 font-medium flex items-center gap-2">
                    <Play className="w-4 h-4" />
                    Modo Demo Activo
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Este condominio está en modo demo para ventas y pruebas
                  </p>
                </div>

                <Button 
                  variant="destructive" 
                  onClick={handleResetDemo}
                  disabled={isSubmitting}
                  className="w-full"
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Resetear Datos de Demo
                </Button>

                <p className="text-xs text-muted-foreground text-center">
                  Esto eliminará: alertas, visitas, logs de acceso
                </p>
              </>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Archive className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Este condominio no está en modo demo</p>
                <p className="text-xs mt-2">Cambia el estado a &quot;Demo&quot; desde la lista</p>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// CREATE ADMIN DIALOG (Super Admin → Condo Admin)
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

const CreateAdminDialog = ({ condo, open, onClose, onSuccess }) => {
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    phone: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [showPassword, setShowPassword] = useState(false);
  const [useAutoPassword, setUseAutoPassword] = useState(true);
  const [createdCredentials, setCreatedCredentials] = useState(null);
  const [copied, setCopied] = useState(false);

  // Auto-generate password on mount
  useEffect(() => {
    if (open && useAutoPassword) {
      setForm(prev => ({ ...prev, password: generateSecurePassword() }));
    }
    // Reset state when dialog opens
    if (open) {
      setCreatedCredentials(null);
      setError(null);
    }
  }, [open, useAutoPassword]);

  const regeneratePassword = () => {
    setForm({ ...form, password: generateSecurePassword() });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!form.email || !form.password || !form.full_name) {
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
      await api.createCondoAdmin(condo.id, {
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        phone: form.phone,
        role: 'Administrador'
      });
      
      // Show credentials
      setCreatedCredentials({
        full_name: form.full_name,
        email: form.email,
        password: form.password,
        condo_name: condo.name
      });
      
    } catch (err) {
      setError(err.message || 'Error al crear administrador');
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyCredentials = async () => {
    const text = `Condominio: ${createdCredentials.condo_name}\nEmail: ${createdCredentials.email}\nContraseña: ${createdCredentials.password}`;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    setForm({ full_name: '', email: '', password: '', phone: '' });
    setCreatedCredentials(null);
    setError(null);
    if (createdCredentials) {
      onSuccess();
    } else {
      onClose();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        {!createdCredentials ? (
          // Form View
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-blue-400" />
                Crear Administrador
              </DialogTitle>
              <DialogDescription>
                Crear administrador para <strong className="text-white">{condo.name}</strong>
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
                  <XCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <Label>Nombre Completo *</Label>
                <Input
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  placeholder="Carlos Administrador"
                  className="bg-[#0A0A0F] border-[#1E293B]"
                  required
                  data-testid="admin-name"
                />
              </div>

              <div className="space-y-2">
                <Label>Email *</Label>
                <Input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="admin@condominio.com"
                  className="bg-[#0A0A0F] border-[#1E293B]"
                  required
                  data-testid="admin-email"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>Contraseña *</Label>
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
                      type={showPassword ? "text" : "password"}
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      placeholder="Mínimo 8 caracteres"
                      className="bg-[#0A0A0F] border-[#1E293B] pr-10 font-mono"
                      required
                      minLength={8}
                      disabled={useAutoPassword}
                      data-testid="admin-password"
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
              </div>

              <div className="space-y-2">
                <Label>Teléfono</Label>
                <Input
                  type="tel"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  placeholder="+52 555 123 4567"
                  className="bg-[#0A0A0F] border-[#1E293B]"
                  data-testid="admin-phone"
                />
              </div>

              <DialogFooter className="gap-2">
                <Button type="button" variant="outline" onClick={handleClose}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={isSubmitting} data-testid="create-admin-submit">
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Creando...
                    </>
                  ) : (
                    <>
                      <UserPlus className="w-4 h-4 mr-2" />
                      Crear Administrador
                    </>
                  )}
                </Button>
              </DialogFooter>
            </form>
          </>
        ) : (
          // Credentials View
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-green-400">
                <CheckCircle className="w-5 h-5" />
                Administrador Creado
              </DialogTitle>
              <DialogDescription>
                Guarda estas credenciales. La contraseña no se mostrará de nuevo.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              {/* Warning Banner */}
              <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-400">
                  <strong>Importante:</strong> Esta es la única vez que verás la contraseña. 
                  Cópiala y entrégala al administrador de forma segura.
                </div>
              </div>

              {/* Credentials */}
              <div className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B] space-y-3">
                <div>
                  <Label className="text-xs text-muted-foreground">Condominio</Label>
                  <p className="font-medium text-primary">{createdCredentials.condo_name}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Nombre</Label>
                  <p className="font-medium">{createdCredentials.full_name}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Email</Label>
                  <p className="font-mono text-primary">{createdCredentials.email}</p>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Contraseña</Label>
                  <code className="block p-2 rounded bg-[#1E293B] font-mono text-green-400">
                    {createdCredentials.password}
                  </code>
                </div>
              </div>

              {/* Copy Button */}
              <Button className="w-full" onClick={copyCredentials} data-testid="copy-admin-credentials">
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
              <Button variant="outline" onClick={handleClose} className="w-full">
                He guardado las credenciales
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// DELETE CONDO DIALOG (Permanent Deletion)
// ============================================
const DeleteCondoDialog = ({ condo, open, onClose, onSuccess }) => {
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState(null);
  const [deletionStats, setDeletionStats] = useState(null);

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (open) {
      setPassword('');
      setError(null);
      setDeletionStats(null);
    }
  }, [open]);

  const handleDelete = async () => {
    if (!password) {
      setError('Ingresa tu contraseña para confirmar');
      return;
    }

    setIsDeleting(true);
    setError(null);

    try {
      const result = await api.permanentlyDeleteCondominium(condo.id, password);
      setDeletionStats(result.deletion_stats);
    } catch (err) {
      setError(err.message || 'Error al eliminar condominio');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleClose = () => {
    if (deletionStats) {
      onSuccess();
    } else {
      onClose();
    }
    setPassword('');
    setError(null);
    setDeletionStats(null);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        {!deletionStats ? (
          // Confirmation View
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-red-400">
                <AlertOctagon className="w-5 h-5" />
                Eliminar Condominio Permanentemente
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {/* Critical Warning */}
              <div className="p-4 rounded-lg bg-red-500/10 border-2 border-red-500/30">
                <div className="flex items-start gap-3">
                  <ShieldAlert className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-bold text-red-400 mb-2">
                      Esta acción es IRREVERSIBLE
                    </p>
                    <p className="text-sm text-red-300/80">
                      Todos los datos relacionados con este condominio serán eliminados permanentemente:
                    </p>
                    <ul className="text-xs text-red-300/70 mt-2 space-y-1 list-disc list-inside">
                      <li>Todos los usuarios del condominio</li>
                      <li>Eventos de pánico e historial</li>
                      <li>Datos de RRHH (guardias, turnos, ausencias)</li>
                      <li>Registro de visitantes</li>
                      <li>Logs de auditoría</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Condo Info */}
              <div className="p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                <p className="text-xs text-muted-foreground mb-1">Condominio a eliminar:</p>
                <p className="font-bold text-white flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-primary" />
                  {condo?.name}
                </p>
                <p className="text-xs text-muted-foreground mt-1">{condo?.contact_email}</p>
              </div>

              {/* Password Input */}
              <div className="space-y-2">
                <Label className="text-sm">
                  Ingresa tu contraseña de Super Admin para confirmar:
                </Label>
                <div className="relative">
                  <Input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Tu contraseña"
                    className="bg-[#0A0A0F] border-[#1E293B] pr-10"
                    data-testid="delete-condo-password"
                    autoComplete="current-password"
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
              </div>

              {/* Error */}
              {error && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-2">
                  <XCircle className="w-4 h-4 flex-shrink-0" />
                  {error}
                </div>
              )}
            </div>

            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={handleClose} className="flex-1">
                Cancelar
              </Button>
              <Button 
                variant="destructive" 
                onClick={handleDelete} 
                disabled={!password || isDeleting}
                className="flex-1 gap-2"
                data-testid="confirm-delete-condo"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Eliminando...
                  </>
                ) : (
                  <>
                    <Trash2 className="w-4 h-4" />
                    Eliminar Permanentemente
                  </>
                )}
              </Button>
            </DialogFooter>
          </>
        ) : (
          // Success View
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-green-400">
                <CheckCircle className="w-5 h-5" />
                Condominio Eliminado
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <p className="text-sm text-muted-foreground">
                El condominio <strong className="text-white">{deletionStats.condominium}</strong> y todos sus datos asociados han sido eliminados permanentemente.
              </p>

              {/* Deletion Stats */}
              <div className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
                <p className="text-xs text-muted-foreground mb-3">Resumen de eliminación:</p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Usuarios:</span>
                    <span className="font-mono">{deletionStats.users_deleted}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Alertas pánico:</span>
                    <span className="font-mono">{deletionStats.panic_events_deleted}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Historial guardia:</span>
                    <span className="font-mono">{deletionStats.guard_history_deleted}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Guardias:</span>
                    <span className="font-mono">{deletionStats.guards_deleted}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Visitantes:</span>
                    <span className="font-mono">{deletionStats.visitors_deleted}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Turnos:</span>
                    <span className="font-mono">{deletionStats.shifts_deleted}</span>
                  </div>
                </div>
              </div>
            </div>

            <DialogFooter>
              <Button onClick={handleClose} className="w-full">
                Entendido
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

// ============================================
// USERS TAB
// ============================================
const UsersTab = ({ condos }) => {
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [condoFilter, setCondoFilter] = useState('all');
  const [roleFilter, setRoleFilter] = useState('all');
  const [processingId, setProcessingId] = useState(null);

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await api.getAllUsersGlobal(
        condoFilter !== 'all' ? condoFilter : '',
        roleFilter !== 'all' ? roleFilter : ''
      );
      setUsers(data);
    } catch (error) {
      console.error('Error fetching users:', error);
    } finally {
      setIsLoading(false);
    }
  }, [condoFilter, roleFilter]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleLockToggle = async (userId, isCurrentlyActive) => {
    setProcessingId(userId);
    try {
      if (isCurrentlyActive) {
        await api.lockUser(userId);
      } else {
        await api.unlockUser(userId);
      }
      fetchUsers();
    } catch (error) {
      alert('Error updating user');
    } finally {
      setProcessingId(null);
    }
  };

  const filteredUsers = users.filter(u => 
    u.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    u.email?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-4 space-y-4">
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Buscar usuarios..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10 bg-[#0A0A0F] border-[#1E293B]"
          />
        </div>
        <Select value={condoFilter} onValueChange={setCondoFilter}>
          <SelectTrigger className="w-full sm:w-48 bg-[#0A0A0F] border-[#1E293B]">
            <SelectValue placeholder="Condominio" />
          </SelectTrigger>
          <SelectContent 
            className="bg-[#0F111A] border-[#1E293B] max-h-[60vh] overflow-y-auto"
            style={{ overscrollBehavior: 'contain' }}
          >
            <SelectItem value="all">Todos los condominios</SelectItem>
            {condos.map(c => (
              <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger className="w-full sm:w-36 bg-[#0A0A0F] border-[#1E293B]">
            <SelectValue placeholder="Rol" />
          </SelectTrigger>
          <SelectContent className="bg-[#0F111A] border-[#1E293B]">
            <SelectItem value="all">Todos los roles</SelectItem>
            <SelectItem value="SuperAdmin">SuperAdmin</SelectItem>
            <SelectItem value="Administrador">Administrador</SelectItem>
            <SelectItem value="Supervisor">Supervisor</SelectItem>
            <SelectItem value="Guarda">Guarda</SelectItem>
            <SelectItem value="Residente">Residente</SelectItem>
            <SelectItem value="Estudiante">Estudiante</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Stats */}
      <div className="flex flex-wrap gap-4 text-sm">
        <span className="text-muted-foreground">Total: <strong className="text-white">{filteredUsers.length}</strong></span>
        <span className="text-muted-foreground">Activos: <strong className="text-green-400">{filteredUsers.filter(u => u.is_active).length}</strong></span>
        <span className="text-muted-foreground">Bloqueados: <strong className="text-red-400">{filteredUsers.filter(u => !u.is_active).length}</strong></span>
      </div>

      {/* Desktop Table View - hidden on mobile */}
      <Card className="bg-[#0F111A] border-[#1E293B] hidden lg:block">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : (
          <ScrollArea className="h-[500px]">
            <Table>
              <TableHeader>
                <TableRow className="border-[#1E293B] hover:bg-transparent">
                  <TableHead className="text-muted-foreground">Usuario</TableHead>
                  <TableHead className="text-muted-foreground">Condominio</TableHead>
                  <TableHead className="text-muted-foreground">Rol</TableHead>
                  <TableHead className="text-muted-foreground">Estado</TableHead>
                  <TableHead className="text-muted-foreground text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.map((user) => (
                  <TableRow key={user.id} className="border-[#1E293B]">
                    <TableCell>
                      <div>
                        <p className="font-medium text-white">{user.full_name}</p>
                        <p className="text-xs text-muted-foreground">{user.email}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm">{user.condominium_name || 'Sin asignar'}</span>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {user.roles?.map((role) => (
                          <Badge key={role} variant="outline" className="text-xs">
                            {role}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      {user.is_active ? (
                        <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Activo
                        </Badge>
                      ) : (
                        <Badge className="bg-red-500/20 text-red-400 border-red-500/30">
                          <Lock className="w-3 h-3 mr-1" />
                          Bloqueado
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant={user.is_active ? "destructive" : "default"}
                        onClick={() => handleLockToggle(user.id, user.is_active)}
                        disabled={processingId === user.id || user.roles?.includes('SuperAdmin')}
                        className="gap-1"
                      >
                        {processingId === user.id ? (
                          <Loader2 className="w-3 h-3 animate-spin" />
                        ) : user.is_active ? (
                          <><Lock className="w-3 h-3" /> Bloquear</>
                        ) : (
                          <><Unlock className="w-3 h-3" /> Desbloquear</>
                        )}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ScrollArea>
        )}
      </Card>

      {/* Mobile Card View */}
      <div className="block lg:hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : (
          <MobileCardList>
            {filteredUsers.map((user) => (
              <MobileCard
                key={user.id}
                testId={`user-card-global-${user.id}`}
                title={user.full_name || 'Sin nombre'}
                subtitle={user.email}
                icon={User}
                status={user.is_active ? 'Activo' : 'Bloqueado'}
                statusColor={user.is_active ? 'green' : 'red'}
                details={[
                  { label: 'Condominio', value: user.condominium_name || 'Sin asignar' },
                  { label: 'Rol', value: user.roles?.join(', ') || 'Sin rol' },
                ]}
                actions={user.roles?.includes('SuperAdmin') ? [] : [
                  {
                    label: user.is_active ? 'Bloquear' : 'Desbloquear',
                    icon: user.is_active ? Lock : Unlock,
                    onClick: () => handleLockToggle(user.id, user.is_active),
                    variant: user.is_active ? 'destructive' : 'default'
                  }
                ]}
              />
            ))}
          </MobileCardList>
        )}
      </div>
    </div>
  );
};

// ============================================
// CONTENT TAB (Placeholder for School Content Management)
// ============================================
const ContentTab = () => {
  return (
    <div className="p-6">
      <div className="max-w-2xl mx-auto text-center py-12">
        <div className="w-20 h-20 rounded-2xl bg-cyan-500/20 flex items-center justify-center mx-auto mb-6">
          <BookOpen className="w-10 h-10 text-cyan-400" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Gestión de Contenido</h2>
        <p className="text-muted-foreground mb-8">
          Administra cursos, certificaciones y material educativo para Genturix School
        </p>

        <div className="grid sm:grid-cols-3 gap-4 mb-8">
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardContent className="p-4 text-center">
              <GraduationCap className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
              <p className="font-medium">Cursos</p>
              <p className="text-2xl font-bold text-white mt-1">0</p>
            </CardContent>
          </Card>
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardContent className="p-4 text-center">
              <Activity className="w-8 h-8 text-cyan-400 mx-auto mb-2" />
              <p className="font-medium">Certificaciones</p>
              <p className="text-2xl font-bold text-white mt-1">0</p>
            </CardContent>
          </Card>
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardContent className="p-4 text-center">
              <Video className="w-8 h-8 text-orange-400 mx-auto mb-2" />
              <p className="font-medium">Videos</p>
              <p className="text-2xl font-bold text-white mt-1">0</p>
            </CardContent>
          </Card>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button disabled className="gap-2">
            <Plus className="w-4 h-4" />
            Crear Curso
          </Button>
          <Button variant="outline" disabled className="gap-2 border-[#1E293B]">
            <Video className="w-4 h-4" />
            Subir Video
          </Button>
        </div>

        <p className="text-sm text-muted-foreground mt-8">
          🚧 Esta funcionalidad estará disponible próximamente
        </p>
      </div>
    </div>
  );
};

// ============================================
// MAIN COMPONENT
// ============================================
const SuperAdminDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const isMobile = useIsMobile();
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [condos, setCondos] = useState([]);
  const [billingOverview, setBillingOverview] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchData = useCallback(async (showToast = false) => {
    if (showToast) setIsRefreshing(true);
    try {
      const [statsData, condosData, billingData] = await Promise.all([
        api.getPlatformStats(),
        api.getCondominiums(),
        api.getAllCondominiumsBilling().catch(() => null)
      ]);
      setStats(statsData);
      setCondos(condosData);
      setBillingOverview(billingData);
      if (showToast) {
        toast.success('Datos actualizados correctamente');
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      if (showToast) {
        toast.error('Error al actualizar datos');
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Check if user has SuperAdmin role
  const isSuperAdmin = user?.roles?.includes('SuperAdmin') || user?.roles?.includes('Administrador');
  
  // Only true SuperAdmin can delete condos (not regular Administrador)
  const canDeleteCondos = user?.roles?.includes('SuperAdmin');

  if (!isSuperAdmin) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center p-4">
        <Card className="bg-[#0F111A] border-[#1E293B] max-w-md">
          <CardContent className="p-6 text-center">
            <Lock className="w-16 h-16 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">Acceso Restringido</h2>
            <p className="text-muted-foreground mb-4">
              No tienes permisos para acceder al panel de Super Admin
            </p>
            <Button onClick={() => navigate('/admin/dashboard')}>
              Ir al Dashboard
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className={`min-h-screen bg-[#05050A] ${isMobile ? 'pb-20' : ''}`}>
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-[#1E293B] bg-[#0A0A0F]/95 backdrop-blur">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-yellow-500 to-orange-600 flex items-center justify-center">
                <Crown className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-base font-bold tracking-wide">GENTURIX</h1>
                <p className="text-xs text-yellow-400">Super Admin</p>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => fetchData(true)} 
                disabled={isRefreshing}
                className="gap-2"
                data-testid="refresh-btn"
              >
                <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                <span className="hidden sm:inline">{isRefreshing ? 'Actualizando...' : 'Actualizar'}</span>
              </Button>
              <div className="hidden sm:block text-right">
                <p className="text-sm font-medium">{user?.full_name}</p>
                <p className="text-xs text-muted-foreground">{user?.email}</p>
              </div>
              <Button variant="ghost" size="icon" onClick={handleLogout}>
                <LogOut className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          {/* Desktop Tabs - hidden on mobile */}
          {!isMobile && (
            <TabsList className="bg-[#0F111A] border border-[#1E293B] p-1 mb-6">
              <TabsTrigger value="overview" className="gap-2 data-[state=active]:bg-primary/20">
                <BarChart3 className="w-4 h-4" />
                <span className="hidden sm:inline">Resumen</span>
              </TabsTrigger>
              <TabsTrigger value="condominiums" className="gap-2 data-[state=active]:bg-primary/20">
                <Building2 className="w-4 h-4" />
                <span className="hidden sm:inline">Condominios</span>
              </TabsTrigger>
              <TabsTrigger value="users" className="gap-2 data-[state=active]:bg-primary/20">
                <Users className="w-4 h-4" />
                <span className="hidden sm:inline">Usuarios</span>
              </TabsTrigger>
              <TabsTrigger value="content" className="gap-2 data-[state=active]:bg-primary/20">
                <BookOpen className="w-4 h-4" />
                <span className="hidden sm:inline">Contenido</span>
              </TabsTrigger>
            </TabsList>
          )}

          <TabsContent value="overview">
            <OverviewTab stats={stats} billingOverview={billingOverview} isLoading={isLoading} onRefresh={fetchData} onNavigateTab={setActiveTab} navigate={navigate} />
          </TabsContent>

          <TabsContent value="condominiums">
            <CondominiumsTab condos={condos} onRefresh={fetchData} isSuperAdmin={canDeleteCondos} navigate={navigate} />
          </TabsContent>

          <TabsContent value="users">
            <UsersTab condos={condos} />
          </TabsContent>

          <TabsContent value="content">
            <ContentTab />
          </TabsContent>
        </Tabs>
      </main>

      {/* Mobile Bottom Navigation */}
      {isMobile && (
        <SuperAdminMobileNav 
          activeTab={activeTab} 
          onTabChange={setActiveTab} 
        />
      )}
    </div>
  );
};

export default SuperAdminDashboard;
