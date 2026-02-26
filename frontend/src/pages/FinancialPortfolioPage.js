/**
 * GENTURIX Financial Portfolio Management - Gestión de Cartera
 * 
 * Vista completa para SuperAdmin de todos los condominios con deuda:
 * - pending_payment: Pago inicial pendiente
 * - past_due: Pago vencido
 * - upgrade_pending: Upgrade pendiente de pago
 * - suspended: Cuenta suspendida por falta de pago
 * 
 * v2.0: Uses backend pagination and filtering (no N+1 queries)
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import {
  Building2,
  DollarSign,
  AlertTriangle,
  Clock,
  CalendarX,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Filter,
  Search,
  Eye,
  CheckCircle,
  Ban,
  ChevronLeft,
  ChevronRight,
  Loader2,
  RefreshCw,
  Users,
  CreditCard,
  TrendingUp,
  AlertCircle,
  History,
  FileText
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
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
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import { ScrollArea } from '../components/ui/scroll-area';
import { toast } from 'sonner';

// Billing status configuration
const BILLING_STATUS_CONFIG = {
  pending_payment: {
    label: 'Pago Pendiente',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/30',
    icon: Clock,
    priority: 2
  },
  upgrade_pending: {
    label: 'Upgrade Pendiente',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
    icon: TrendingUp,
    priority: 3
  },
  past_due: {
    label: 'Vencido',
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    icon: AlertCircle,
    priority: 1
  },
  suspended: {
    label: 'Suspendido',
    color: 'text-gray-400',
    bgColor: 'bg-gray-500/10',
    borderColor: 'border-gray-500/30',
    icon: Ban,
    priority: 4
  }
};

const DEBT_STATUSES = 'pending_payment,upgrade_pending,past_due,suspended';
const PAGE_SIZE = 15;

const FinancialPortfolioPage = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  // Data state
  const [condos, setCondos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Pagination state (now from backend)
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: PAGE_SIZE,
    total_count: 0,
    total_pages: 0,
    has_next: false,
    has_prev: false
  });
  
  // Totals from backend
  const [totals, setTotals] = useState({
    total_condominiums: 0,
    total_paid_seats: 0,
    total_active_users: 0,
    total_monthly_revenue: 0
  });
  
  // Filter and sort state
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [providerFilter, setProviderFilter] = useState('all');
  const [sortField, setSortField] = useState('next_invoice_amount');
  const [sortDirection, setSortDirection] = useState('desc');
  
  // Debounce search
  const [debouncedSearch, setDebouncedSearch] = useState('');
  
  // Dialog states
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);
  const [showHistoryDialog, setShowHistoryDialog] = useState(false);
  const [showSuspendDialog, setShowSuspendDialog] = useState(false);
  const [selectedCondo, setSelectedCondo] = useState(null);
  const [paymentHistory, setPaymentHistory] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Partial payment state
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentReference, setPaymentReference] = useState('');
  const [billingBalance, setBillingBalance] = useState(null);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Fetch condos with BACKEND pagination
  const fetchCondos = useCallback(async (page = 1) => {
    setIsLoading(true);
    setError(null);
    try {
      // Build billing_status filter
      let billingStatusParam = DEBT_STATUSES; // Default: all debt statuses
      if (statusFilter !== 'all') {
        billingStatusParam = statusFilter;
      }
      
      const response = await api.getSuperAdminBillingOverview({
        page,
        page_size: PAGE_SIZE,
        billing_status: billingStatusParam,
        billing_provider: providerFilter !== 'all' ? providerFilter : undefined,
        search: debouncedSearch || undefined,
        sort_by: sortField,
        sort_order: sortDirection
      });
      
      setCondos(response.condominiums || []);
      setPagination(response.pagination || {
        page: 1,
        page_size: PAGE_SIZE,
        total_count: 0,
        total_pages: 0,
        has_next: false,
        has_prev: false
      });
      setTotals(response.totals || {
        total_condominiums: 0,
        total_paid_seats: 0,
        total_active_users: 0,
        total_monthly_revenue: 0
      });
    } catch (err) {
      console.error('Error fetching condos:', err);
      setError('Error al cargar los condominios');
      toast.error('Error al cargar los datos de cartera');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, providerFilter, debouncedSearch, sortField, sortDirection]);

  // Fetch on mount and when filters change
  useEffect(() => {
    fetchCondos(1); // Reset to page 1 when filters change
  }, [fetchCondos]);

  // Count by status (from fetched data for summary cards)
  const statusCounts = condos.reduce((acc, c) => {
    const status = c.billing_status || 'pending_payment';
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {});

  // Handlers
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const handlePageChange = (newPage) => {
    fetchCondos(newPage);
  };

  const handleConfirmPayment = async (condo) => {
    setSelectedCondo(condo);
    setPaymentAmount('');
    setPaymentReference('');
    setBillingBalance(null);
    setShowPaymentDialog(true);
    
    // Load billing balance for partial payment support
    try {
      const balance = await api.getBillingBalance(condo.condominium_id);
      setBillingBalance(balance);
      // Pre-fill with balance due or invoice amount
      setPaymentAmount(String(balance.balance_due > 0 ? balance.balance_due : balance.invoice_amount));
    } catch (err) {
      console.error('Error loading balance:', err);
      // Fallback to invoice amount
      setPaymentAmount(String(condo.next_invoice_amount || 0));
    }
  };

  const handleViewHistory = async (condo) => {
    setSelectedCondo(condo);
    setShowHistoryDialog(true);
    try {
      const history = await api.getCondominiumPaymentHistory(condo.condominium_id);
      setPaymentHistory(history.payments || []);
    } catch (err) {
      console.error('Error fetching history:', err);
      setPaymentHistory([]);
    }
  };

  const handleSuspend = (condo) => {
    setSelectedCondo(condo);
    setShowSuspendDialog(true);
  };

  const confirmPayment = async () => {
    if (!selectedCondo) return;
    setIsProcessing(true);
    try {
      await api.confirmCondominiumPayment(selectedCondo.condominium_id, {
        amount_paid: selectedCondo.next_invoice_amount,
        payment_method: selectedCondo.billing_provider || 'manual',
        notes: 'Pago confirmado desde gestión de cartera'
      });
      toast.success(`Pago confirmado para ${selectedCondo.condominium_name}`);
      setShowPaymentDialog(false);
      fetchCondos(pagination.page); // Refresh current page
    } catch (err) {
      console.error('Error confirming payment:', err);
      toast.error('Error al confirmar el pago');
    } finally {
      setIsProcessing(false);
    }
  };

  const confirmSuspend = async () => {
    if (!selectedCondo) return;
    setIsProcessing(true);
    try {
      await api.updateCondoStatus(selectedCondo.condominium_id, 'suspended');
      toast.success(`Condominio ${selectedCondo.condominium_name} suspendido`);
      setShowSuspendDialog(false);
      fetchCondos(pagination.page);
    } catch (err) {
      console.error('Error suspending condo:', err);
      toast.error('Error al suspender el condominio');
    } finally {
      setIsProcessing(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getDaysOverdue = (dateStr) => {
    if (!dateStr) return 0;
    const dueDate = new Date(dateStr);
    const today = new Date();
    const diff = Math.floor((today - dueDate) / (1000 * 60 * 60 * 24));
    return diff > 0 ? diff : 0;
  };

  // Render sort indicator
  const SortIndicator = ({ field }) => {
    if (sortField !== field) return <ArrowUpDown className="w-3 h-3 opacity-50" />;
    return sortDirection === 'asc' 
      ? <ArrowUp className="w-3 h-3" /> 
      : <ArrowDown className="w-3 h-3" />;
  };

  if (isLoading && condos.length === 0) {
    return (
      <div className="min-h-screen bg-[#05050A] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Cargando cartera...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#05050A] p-4 lg:p-6" data-testid="financial-portfolio-page">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/super-admin')}
            className="text-muted-foreground hover:text-white"
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Volver
          </Button>
        </div>
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <DollarSign className="w-7 h-7 text-yellow-400" />
              Gestión de Cartera
            </h1>
            <p className="text-muted-foreground text-sm mt-1">
              Condominios con pagos pendientes, vencidos o suspendidos
              <span className="ml-2 text-xs text-primary">
                (Paginación backend v2.0)
              </span>
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => fetchCondos(pagination.page)}
            disabled={isLoading}
            className="border-[#1E293B] gap-2"
            data-testid="refresh-btn"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-500/20 rounded-lg">
                <DollarSign className="w-5 h-5 text-yellow-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">${totals.total_monthly_revenue.toLocaleString()}</p>
                <p className="text-xs text-muted-foreground">Total Pendiente</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/20 rounded-lg">
                <Building2 className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totals.total_condominiums}</p>
                <p className="text-xs text-muted-foreground">Condominios</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {Object.entries(BILLING_STATUS_CONFIG).map(([status, config]) => {
          const count = statusCounts[status] || 0;
          if (count === 0 && statusFilter !== 'all' && statusFilter !== status) return null;
          const StatusIcon = config.icon;
          return (
            <Card key={status} className={`bg-[#0F111A] border-[#1E293B] ${config.borderColor}`}>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className={`p-2 ${config.bgColor} rounded-lg`}>
                    <StatusIcon className={`w-5 h-5 ${config.color}`} />
                  </div>
                  <div>
                    <p className="text-xl font-bold">{count}</p>
                    <p className="text-xs text-muted-foreground">{config.label}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Filters */}
      <Card className="bg-[#0F111A] border-[#1E293B] mb-4">
        <CardContent className="p-4">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por nombre o email..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-[#0A0A0F] border-[#1E293B]"
                data-testid="search-input"
              />
            </div>
            
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full lg:w-48 bg-[#0A0A0F] border-[#1E293B]" data-testid="status-filter">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                <SelectItem value="all">Todos los estados</SelectItem>
                <SelectItem value="pending_payment">Pago Pendiente</SelectItem>
                <SelectItem value="past_due">Vencido</SelectItem>
                <SelectItem value="upgrade_pending">Upgrade Pendiente</SelectItem>
                <SelectItem value="suspended">Suspendido</SelectItem>
              </SelectContent>
            </Select>

            <Select value={providerFilter} onValueChange={setProviderFilter}>
              <SelectTrigger className="w-full lg:w-48 bg-[#0A0A0F] border-[#1E293B]" data-testid="provider-filter">
                <CreditCard className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Proveedor" />
              </SelectTrigger>
              <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                <SelectItem value="all">Todos los proveedores</SelectItem>
                <SelectItem value="sinpe">SINPE</SelectItem>
                <SelectItem value="stripe">Stripe</SelectItem>
                <SelectItem value="manual">Manual</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <ScrollArea className="h-[calc(100vh-450px)] min-h-[400px]">
          <Table>
            <TableHeader>
              <TableRow className="border-[#1E293B] hover:bg-transparent">
                <TableHead 
                  className="text-muted-foreground cursor-pointer hover:text-white"
                  onClick={() => handleSort('condominium_name')}
                >
                  <span className="flex items-center gap-2">
                    Condominio <SortIndicator field="condominium_name" />
                  </span>
                </TableHead>
                <TableHead 
                  className="text-muted-foreground cursor-pointer hover:text-white"
                  onClick={() => handleSort('billing_status')}
                >
                  <span className="flex items-center gap-2">
                    Estado <SortIndicator field="billing_status" />
                  </span>
                </TableHead>
                <TableHead 
                  className="text-muted-foreground cursor-pointer hover:text-white"
                  onClick={() => handleSort('paid_seats')}
                >
                  <span className="flex items-center gap-2">
                    Asientos <SortIndicator field="paid_seats" />
                  </span>
                </TableHead>
                <TableHead 
                  className="text-muted-foreground cursor-pointer hover:text-white"
                  onClick={() => handleSort('next_invoice_amount')}
                >
                  <span className="flex items-center gap-2">
                    Monto <SortIndicator field="next_invoice_amount" />
                  </span>
                </TableHead>
                <TableHead 
                  className="text-muted-foreground cursor-pointer hover:text-white"
                  onClick={() => handleSort('next_billing_date')}
                >
                  <span className="flex items-center gap-2">
                    Vencimiento <SortIndicator field="next_billing_date" />
                  </span>
                </TableHead>
                <TableHead className="text-muted-foreground">Proveedor</TableHead>
                <TableHead className="text-muted-foreground text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {condos.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <div className="flex flex-col items-center gap-2">
                      <CheckCircle className="w-8 h-8 text-green-400" />
                      <p className="text-muted-foreground">
                        {pagination.total_count === 0 
                          ? 'No hay condominios con pagos pendientes' 
                          : 'No se encontraron resultados con los filtros aplicados'}
                      </p>
                    </div>
                  </TableCell>
                </TableRow>
              ) : (
                condos.map((condo) => {
                  const statusConfig = BILLING_STATUS_CONFIG[condo.billing_status] || BILLING_STATUS_CONFIG.pending_payment;
                  const StatusIcon = statusConfig.icon;
                  const daysOverdue = getDaysOverdue(condo.next_billing_date);
                  
                  return (
                    <TableRow 
                      key={condo.condominium_id} 
                      className="border-[#1E293B] hover:bg-[#1E293B]/30"
                      data-testid={`condo-row-${condo.condominium_id}`}
                    >
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                            <Building2 className="w-5 h-5 text-primary" />
                          </div>
                          <div>
                            <p className="font-medium text-white">{condo.condominium_name}</p>
                            <p className="text-xs text-muted-foreground">{condo.admin_email}</p>
                          </div>
                        </div>
                      </TableCell>
                      
                      <TableCell>
                        <Badge className={`${statusConfig.bgColor} ${statusConfig.color} ${statusConfig.borderColor} gap-1`}>
                          <StatusIcon className="w-3 h-3" />
                          {statusConfig.label}
                        </Badge>
                        {daysOverdue > 0 && condo.billing_status === 'past_due' && (
                          <p className="text-xs text-red-400 mt-1">
                            {daysOverdue} días vencido
                          </p>
                        )}
                      </TableCell>
                      
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Users className="w-3 h-3 text-muted-foreground" />
                          <span>{condo.current_users || 0} / {condo.paid_seats || 0}</span>
                        </div>
                      </TableCell>
                      
                      <TableCell>
                        <span className="text-lg font-bold text-yellow-400">
                          ${(condo.next_invoice_amount || 0).toLocaleString()}
                        </span>
                        <span className="text-xs text-muted-foreground ml-1">
                          /{condo.billing_cycle === 'yearly' ? 'año' : 'mes'}
                        </span>
                      </TableCell>
                      
                      <TableCell>
                        <span className={daysOverdue > 0 ? 'text-red-400' : ''}>
                          {formatDate(condo.next_billing_date)}
                        </span>
                      </TableCell>
                      
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {condo.billing_provider === 'sinpe' ? 'SINPE' :
                           condo.billing_provider === 'stripe' ? 'Stripe' :
                           condo.billing_provider === 'manual' ? 'Manual' :
                           condo.billing_provider || 'N/A'}
                        </Badge>
                      </TableCell>
                      
                      <TableCell>
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleViewHistory(condo)}
                            className="h-8 px-2"
                            title="Ver historial"
                            data-testid={`history-btn-${condo.condominium_id}`}
                          >
                            <History className="w-4 h-4" />
                          </Button>
                          
                          {['pending_payment', 'past_due', 'upgrade_pending'].includes(condo.billing_status) && (
                            <Button
                              size="sm"
                              onClick={() => handleConfirmPayment(condo)}
                              className="h-8 bg-green-600 hover:bg-green-700 gap-1"
                              data-testid={`confirm-payment-btn-${condo.condominium_id}`}
                            >
                              <CheckCircle className="w-3 h-3" />
                              Confirmar
                            </Button>
                          )}
                          
                          {condo.billing_status === 'past_due' && daysOverdue > 30 && (
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleSuspend(condo)}
                              className="h-8 gap-1"
                              data-testid={`suspend-btn-${condo.condominium_id}`}
                            >
                              <Ban className="w-3 h-3" />
                              Suspender
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </ScrollArea>

        {/* Backend Pagination */}
        {pagination.total_pages > 1 && (
          <div className="flex items-center justify-between p-4 border-t border-[#1E293B]">
            <p className="text-sm text-muted-foreground">
              Mostrando {((pagination.page - 1) * pagination.page_size) + 1} - {Math.min(pagination.page * pagination.page_size, pagination.total_count)} de {pagination.total_count}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(pagination.page - 1)}
                disabled={!pagination.has_prev || isLoading}
                className="border-[#1E293B]"
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-sm px-3">
                Página {pagination.page} de {pagination.total_pages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(pagination.page + 1)}
                disabled={!pagination.has_next || isLoading}
                className="border-[#1E293B]"
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Payment Confirmation Dialog */}
      <Dialog open={showPaymentDialog} onOpenChange={setShowPaymentDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-400" />
              Confirmar Pago
            </DialogTitle>
            <DialogDescription>
              Confirmar recepción de pago para {selectedCondo?.condominium_name}
            </DialogDescription>
          </DialogHeader>
          
          {selectedCondo && (
            <div className="space-y-4 py-4">
              <div className="p-4 bg-[#1E293B]/30 rounded-lg space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Condominio:</span>
                  <span className="font-medium">{selectedCondo.condominium_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Monto:</span>
                  <span className="text-xl font-bold text-green-400">
                    ${selectedCondo.next_invoice_amount?.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Asientos:</span>
                  <span>{selectedCondo.paid_seats}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Proveedor:</span>
                  <span>{selectedCondo.billing_provider}</span>
                </div>
              </div>
              
              <div className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <p className="text-sm text-yellow-200">
                  Al confirmar, el estado del condominio cambiará a "Activo" y se actualizará la fecha de próximo cobro.
                </p>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPaymentDialog(false)}>
              Cancelar
            </Button>
            <Button 
              onClick={confirmPayment} 
              disabled={isProcessing}
              className="bg-green-600 hover:bg-green-700"
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Confirmar Pago
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Payment History Dialog */}
      <Dialog open={showHistoryDialog} onOpenChange={setShowHistoryDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <History className="w-5 h-5 text-primary" />
              Historial de Pagos
            </DialogTitle>
            <DialogDescription>
              {selectedCondo?.condominium_name}
            </DialogDescription>
          </DialogHeader>
          
          <ScrollArea className="max-h-[400px]">
            {paymentHistory.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No hay historial de pagos</p>
              </div>
            ) : (
              <div className="space-y-3">
                {paymentHistory.map((payment, idx) => (
                  <div key={idx} className="p-3 bg-[#1E293B]/30 rounded-lg">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium">${payment.amount_paid?.toLocaleString()}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatDate(payment.created_at)}
                        </p>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {payment.payment_method}
                      </Badge>
                    </div>
                    {payment.notes && (
                      <p className="text-xs text-muted-foreground mt-2">{payment.notes}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowHistoryDialog(false)}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Suspend Dialog */}
      <Dialog open={showSuspendDialog} onOpenChange={setShowSuspendDialog}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-400">
              <Ban className="w-5 h-5" />
              Suspender Condominio
            </DialogTitle>
            <DialogDescription>
              Esta acción suspenderá el acceso al condominio {selectedCondo?.condominium_name}
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p className="text-sm text-red-200">
                <strong>Advertencia:</strong> Al suspender este condominio:
              </p>
              <ul className="text-sm text-red-200/80 list-disc ml-4 mt-2 space-y-1">
                <li>Los usuarios no podrán acceder a la plataforma</li>
                <li>Las notificaciones push se desactivarán</li>
                <li>El condominio aparecerá como "Suspendido"</li>
              </ul>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSuspendDialog(false)}>
              Cancelar
            </Button>
            <Button 
              variant="destructive"
              onClick={confirmSuspend} 
              disabled={isProcessing}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <Ban className="w-4 h-4 mr-2" />
                  Suspender
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default FinancialPortfolioPage;
