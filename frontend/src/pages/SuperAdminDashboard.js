/**
 * GENTURIX - Super Admin Dashboard
 * 
 * Platform-level administration for multi-tenant management
 * 
 * Sections:
 * 1. Overview - Platform stats and KPIs
 * 2. Condominiums - CRUD and configuration
 * 3. Modules - Per-condominium module toggling
 * 4. Users - Global user oversight
 * 5. Pricing - Plans and discounts
 * 6. Content - Course management (placeholder)
 */

import React, { useState, useEffect, useCallback } from 'react';
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import api from '../services/api';
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
  UserPlus,
  Copy
} from 'lucide-react';

// ============================================
// MODULE CONFIGURATION
// ============================================
const MODULES = [
  { id: 'security', name: 'Seguridad', description: 'Botón de pánico, alertas', icon: Shield, color: 'text-red-400' },
  { id: 'visits', name: 'Visitas', description: 'Control de visitantes', icon: Users, color: 'text-blue-400' },
  { id: 'hr', name: 'RRHH', description: 'Recursos humanos, turnos', icon: Building, color: 'text-purple-400' },
  { id: 'school', name: 'Escuela', description: 'Cursos y certificaciones', icon: GraduationCap, color: 'text-cyan-400' },
  { id: 'payments', name: 'Pagos', description: 'Facturación y cobros', icon: CreditCard, color: 'text-green-400' },
  { id: 'audit', name: 'Auditoría', description: 'Logs y trazabilidad', icon: Activity, color: 'text-orange-400' },
  { id: 'reservations', name: 'Reservaciones', description: 'Áreas comunes', icon: Calendar, color: 'text-pink-400', future: true },
  { id: 'cctv', name: 'CCTV', description: 'Integración cámaras', icon: Video, color: 'text-yellow-400', future: true },
];

const STATUS_CONFIG = {
  active: { label: 'Activo', color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: CheckCircle },
  demo: { label: 'Demo', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: Play },
  suspended: { label: 'Suspendido', color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: Pause },
};

// ============================================
// OVERVIEW TAB
// ============================================
const OverviewTab = ({ stats, isLoading, onRefresh, onNavigateTab }) => {
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
              <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center">
                <Users className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white">{stats?.users?.total || 0}</p>
                <p className="text-xs text-muted-foreground">Usuarios</p>
              </div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              {stats?.users?.active || 0} activos
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
                <p className="text-2xl font-bold text-white">${stats?.revenue?.mrr_usd || 0}</p>
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
              className="h-auto py-4 flex-col gap-2 border-[#1E293B] hover:bg-[#1E293B]"
              onClick={() => onNavigateTab('condominiums')}
              data-testid="quick-action-new-condo"
            >
              <Building2 className="w-5 h-5 text-blue-400" />
              <span className="text-xs">Nuevo Condominio</span>
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
              <Users className="w-5 h-5 text-purple-400" />
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
const CondominiumsTab = ({ condos, onRefresh, onEdit, onCreate }) => {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedCondo, setSelectedCondo] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateAdminDialog, setShowCreateAdminDialog] = useState(false);
  const [adminTargetCondo, setAdminTargetCondo] = useState(null);

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
        <Button onClick={() => setShowCreateDialog(true)} className="gap-2">
          <Plus className="w-4 h-4" />
          Nuevo Condominio
        </Button>
      </div>

      {/* Table */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
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
                          <p className="font-medium text-white">{condo.name}</p>
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
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </ScrollArea>
      </Card>

      {/* Create Dialog */}
      <CreateCondoDialog 
        open={showCreateDialog} 
        onClose={() => setShowCreateDialog(false)} 
        onSuccess={() => { setShowCreateDialog(false); onRefresh(); }}
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
    </div>
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
    is_demo: false
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!form.name || !form.contact_email) return;
    
    setIsSubmitting(true);
    try {
      await api.createCondominium(form);
      onSuccess();
      setForm({ name: '', address: '', contact_email: '', contact_phone: '', max_users: 100, is_demo: false });
    } catch (error) {
      alert('Error creating condominium');
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
          <div>
            <Label>Máximo de Usuarios</Label>
            <Input
              type="number"
              value={form.max_users}
              onChange={(e) => setForm({...form, max_users: parseInt(e.target.value) || 100})}
              className="bg-[#0A0A0F] border-[#1E293B] mt-1"
            />
          </div>
          <div className="flex items-center justify-between p-3 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
            <div>
              <p className="font-medium">Modo Demo</p>
              <p className="text-xs text-muted-foreground">Para ventas y pruebas</p>
            </div>
            <Switch
              checked={form.is_demo}
              onCheckedChange={(checked) => setForm({...form, is_demo: checked})}
            />
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

  const handleModuleToggle = async (moduleId, enabled) => {
    setIsSubmitting(true);
    try {
      await api.updateCondoModule(condo.id, moduleId, enabled);
      setModules(prev => ({
        ...prev,
        [moduleId]: { ...prev[moduleId], enabled }
      }));
    } catch (error) {
      alert('Error updating module');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSavePricing = async () => {
    setIsSubmitting(true);
    try {
      await api.updateCondoPricing(condo.id, pricing.discount_percent, pricing.plan);
      onSuccess();
    } catch (error) {
      alert('Error updating pricing');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResetDemo = async () => {
    if (!confirm('¿Resetear todos los datos de demo? Esta acción no se puede deshacer.')) return;
    
    setIsSubmitting(true);
    try {
      await api.resetDemoData(condo.id);
      alert('Datos de demo reseteados');
      onSuccess();
    } catch (error) {
      alert('Error resetting demo data');
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
              const isEnabled = modules[mod.id]?.enabled !== false;
              const ModIcon = mod.icon;
              
              return (
                <div 
                  key={mod.id}
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    mod.future 
                      ? 'bg-[#0A0A0F]/50 border-[#1E293B]/50 opacity-50' 
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
                  ) : (
                    <Switch
                      checked={isEnabled}
                      onCheckedChange={(checked) => handleModuleToggle(mod.id, checked)}
                      disabled={isSubmitting}
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
                <p className="text-xs mt-2">Cambia el estado a "Demo" desde la lista</p>
              </div>
            )}
          </TabsContent>
        </Tabs>
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
          <SelectTrigger className="w-48 bg-[#0A0A0F] border-[#1E293B]">
            <SelectValue placeholder="Condominio" />
          </SelectTrigger>
          <SelectContent className="bg-[#0F111A] border-[#1E293B]">
            <SelectItem value="all">Todos los condominios</SelectItem>
            {condos.map(c => (
              <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger className="w-36 bg-[#0A0A0F] border-[#1E293B]">
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
      <div className="flex gap-4 text-sm">
        <span className="text-muted-foreground">Total: <strong className="text-white">{filteredUsers.length}</strong></span>
        <span className="text-muted-foreground">Activos: <strong className="text-green-400">{filteredUsers.filter(u => u.is_active).length}</strong></span>
        <span className="text-muted-foreground">Bloqueados: <strong className="text-red-400">{filteredUsers.filter(u => !u.is_active).length}</strong></span>
      </div>

      {/* Table */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
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
              <Activity className="w-8 h-8 text-purple-400 mx-auto mb-2" />
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
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [condos, setCondos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [statsData, condosData] = await Promise.all([
        api.getPlatformStats(),
        api.getCondominiums()
      ]);
      setStats(statsData);
      setCondos(condosData);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setIsLoading(false);
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
    <div className="min-h-screen bg-[#05050A]">
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
              <Button variant="ghost" size="sm" onClick={fetchData} className="gap-2">
                <RefreshCw className="w-4 h-4" />
                <span className="hidden sm:inline">Actualizar</span>
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

          <TabsContent value="overview">
            <OverviewTab stats={stats} isLoading={isLoading} onRefresh={fetchData} onNavigateTab={setActiveTab} />
          </TabsContent>

          <TabsContent value="condominiums">
            <CondominiumsTab condos={condos} onRefresh={fetchData} />
          </TabsContent>

          <TabsContent value="users">
            <UsersTab condos={condos} />
          </TabsContent>

          <TabsContent value="content">
            <ContentTab />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default SuperAdminDashboard;
