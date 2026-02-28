/**
 * Admin Billing Page - GENTURIX
 * 
 * Complete redesign aligned with the real billing engine.
 * NO hardcoded prices, NO manual calculations.
 * All data comes from backend billing endpoints.
 */

import React, { useState, useEffect, useCallback } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import api from '../services/api';
import { 
  CreditCard, 
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Loader2,
  Users,
  Plus,
  Calendar,
  Receipt,
  FileText,
  ArrowUpCircle,
  DollarSign,
  AlertOctagon,
  RefreshCw,
  Upload,
  TrendingUp
} from 'lucide-react';

// ==================== BILLING STATUS CONFIG ====================
const BILLING_STATUS_CONFIG = {
  active: {
    label: 'Activo',
    color: 'bg-green-500/20 text-green-400 border-green-500/30',
    icon: CheckCircle,
    description: 'Tu cuenta está al día'
  },
  pending_payment: {
    label: 'Pago Pendiente',
    color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    icon: Clock,
    description: 'Tienes un pago pendiente'
  },
  past_due: {
    label: 'Vencido',
    color: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    icon: AlertTriangle,
    description: 'Tu pago está vencido'
  },
  suspended: {
    label: 'Suspendido',
    color: 'bg-red-500/20 text-red-400 border-red-500/30',
    icon: AlertOctagon,
    description: 'Cuenta suspendida por falta de pago'
  },
  upgrade_pending: {
    label: 'Upgrade Pendiente',
    color: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    icon: ArrowUpCircle,
    description: 'Solicitud de asientos en proceso'
  },
  trialing: {
    label: 'Período de Prueba',
    color: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    icon: Clock,
    description: 'En período de prueba'
  }
};

// ==================== HELPER FUNCTIONS ====================
const formatCurrency = (amount) => {
  if (amount === null || amount === undefined) return '-';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  });
};

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('es-ES', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// ==================== BILLING OVERVIEW CARD ====================
const BillingOverviewCard = ({ billingInfo, balance, seatStatus, isLoading }) => {
  if (isLoading) {
    return (
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardContent className="p-6 flex items-center justify-center h-48">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  const status = billingInfo?.billing_status || 'pending_payment';
  const statusConfig = BILLING_STATUS_CONFIG[status] || BILLING_STATUS_CONFIG.pending_payment;
  const StatusIcon = statusConfig.icon;

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]" data-testid="billing-overview-card">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-primary" />
            Estado de Facturación
          </CardTitle>
          <Badge className={statusConfig.color}>
            <StatusIcon className="w-3 h-3 mr-1" />
            {statusConfig.label}
          </Badge>
        </div>
        <CardDescription>{statusConfig.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Main Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Balance Due */}
          <div className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
            <p className="text-xs text-muted-foreground mb-1">Balance Pendiente</p>
            <p className={`text-2xl font-bold ${balance?.balance_due > 0 ? 'text-yellow-400' : 'text-green-400'}`}>
              {formatCurrency(balance?.balance_due || 0)}
            </p>
          </div>

          {/* Paid Seats */}
          <div className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
            <p className="text-xs text-muted-foreground mb-1">Asientos Pagados</p>
            <p className="text-2xl font-bold text-white">{seatStatus?.paid_seats || billingInfo?.paid_seats || '-'}</p>
          </div>

          {/* Active Users */}
          <div className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
            <p className="text-xs text-muted-foreground mb-1">Usuarios Activos</p>
            <p className="text-2xl font-bold text-cyan-400">{seatStatus?.active_residents || billingInfo?.active_users || '-'}</p>
          </div>

          {/* Available Seats */}
          <div className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
            <p className="text-xs text-muted-foreground mb-1">Asientos Disponibles</p>
            <p className={`text-2xl font-bold ${(seatStatus?.available_seats || 0) === 0 ? 'text-red-400' : 'text-green-400'}`}>
              {seatStatus?.available_seats ?? '-'}
            </p>
          </div>
        </div>

        {/* Secondary Info */}
        <div className="grid grid-cols-2 gap-4 pt-2 border-t border-[#1E293B]">
          <div>
            <p className="text-xs text-muted-foreground">Próximo Cobro</p>
            <p className="text-sm font-medium">{formatDate(balance?.next_billing_date || billingInfo?.next_billing_date)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Ciclo de Facturación</p>
            <p className="text-sm font-medium capitalize">{balance?.billing_cycle || billingInfo?.billing_cycle || 'mensual'}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Monto Próxima Factura</p>
            <p className="text-sm font-medium">{formatCurrency(balance?.invoice_amount || billingInfo?.next_invoice_amount)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Pagado Este Ciclo</p>
            <p className="text-sm font-medium text-green-400">{formatCurrency(balance?.total_paid_cycle || 0)}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// ==================== BILLING ACTIONS ====================
const BillingActions = ({ billingInfo, balance, onRequestUpgrade, onPaymentUpload, isLoading }) => {
  const status = billingInfo?.billing_status || 'pending_payment';
  const balanceDue = balance?.balance_due || 0;

  if (isLoading) {
    return null;
  }

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]" data-testid="billing-actions-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary" />
          Acciones
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Action based on status */}
        {status === 'active' && (
          <Button 
            className="w-full" 
            variant="outline"
            onClick={onRequestUpgrade}
            data-testid="request-upgrade-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Solicitar Más Asientos
          </Button>
        )}

        {(status === 'past_due' || status === 'pending_payment') && balanceDue > 0 && (
          <>
            <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
              <p className="text-sm text-yellow-400 font-medium">Balance pendiente: {formatCurrency(balanceDue)}</p>
              <p className="text-xs text-muted-foreground mt-1">Sube tu comprobante de pago para regularizar</p>
            </div>
            <Button 
              className="w-full" 
              onClick={onPaymentUpload}
              data-testid="upload-payment-btn"
            >
              <Upload className="w-4 h-4 mr-2" />
              Subir Comprobante de Pago
            </Button>
          </>
        )}

        {status === 'suspended' && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
            <div className="flex items-center gap-2 text-red-400 mb-2">
              <AlertOctagon className="w-5 h-5" />
              <span className="font-semibold">Cuenta Suspendida</span>
            </div>
            <p className="text-sm text-muted-foreground mb-3">
              Tu cuenta ha sido suspendida por falta de pago. Para reactivarla, regulariza tu balance pendiente.
            </p>
            <p className="text-lg font-bold text-red-400 mb-3">Balance: {formatCurrency(balanceDue)}</p>
            <Button 
              className="w-full" 
              variant="destructive"
              onClick={onPaymentUpload}
              data-testid="regularize-payment-btn"
            >
              <Upload className="w-4 h-4 mr-2" />
              Regularizar Pago
            </Button>
          </div>
        )}

        {status === 'upgrade_pending' && (
          <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
            <div className="flex items-center gap-2 text-blue-400 mb-2">
              <ArrowUpCircle className="w-5 h-5" />
              <span className="font-semibold">Solicitud en Proceso</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Tu solicitud de asientos adicionales está siendo revisada. Recibirás una notificación cuando sea aprobada.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// ==================== PAYMENT HISTORY TABLE ====================
const PaymentHistoryTable = ({ payments, isLoading }) => {
  if (isLoading) {
    return (
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardContent className="p-6 flex items-center justify-center h-32">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]" data-testid="payment-history-card">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Receipt className="w-5 h-5 text-primary" />
          Historial de Pagos
        </CardTitle>
        <CardDescription>Pagos registrados en el ciclo actual</CardDescription>
      </CardHeader>
      <CardContent>
        {payments && payments.length > 0 ? (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-[#1E293B]">
                  <TableHead>Fecha</TableHead>
                  <TableHead>Monto</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Referencia</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payments.map((payment, index) => (
                  <TableRow key={payment.id || index} className="border-[#1E293B]">
                    <TableCell className="text-sm">{formatDateTime(payment.payment_date)}</TableCell>
                    <TableCell className="font-medium text-green-400">{formatCurrency(payment.amount_paid)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={payment.is_partial_payment ? 'border-yellow-500/30 text-yellow-400' : 'border-green-500/30 text-green-400'}>
                        {payment.is_partial_payment ? 'Parcial' : 'Completo'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-xs">{payment.payment_reference || '-'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No hay pagos registrados en este ciclo</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// ==================== SEAT UPGRADE SECTION ====================
const SeatUpgradeSection = ({ pendingRequest, onRefresh, isLoading }) => {
  if (isLoading) {
    return null;
  }

  if (!pendingRequest) {
    return null;
  }

  const statusColors = {
    pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    approved: 'bg-green-500/20 text-green-400 border-green-500/30',
    rejected: 'bg-red-500/20 text-red-400 border-red-500/30',
    completed: 'bg-blue-500/20 text-blue-400 border-blue-500/30'
  };

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]" data-testid="seat-upgrade-section">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <ArrowUpCircle className="w-5 h-5 text-primary" />
          Solicitud de Asientos
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="p-4 rounded-lg bg-[#0A0A0F] border border-[#1E293B]">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm text-muted-foreground">Estado</span>
            <Badge className={statusColors[pendingRequest.status] || statusColors.pending}>
              {pendingRequest.status === 'pending' ? 'Pendiente' : 
               pendingRequest.status === 'approved' ? 'Aprobada' :
               pendingRequest.status === 'rejected' ? 'Rechazada' : 'Completada'}
            </Badge>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Asientos solicitados</span>
              <span className="font-medium">{pendingRequest.requested_seats}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Fecha solicitud</span>
              <span>{formatDateTime(pendingRequest.created_at)}</span>
            </div>
            {pendingRequest.admin_comments && (
              <div className="pt-2 border-t border-[#1E293B]">
                <p className="text-muted-foreground mb-1">Comentarios:</p>
                <p className="text-sm">{pendingRequest.admin_comments}</p>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// ==================== SEAT UPGRADE REQUEST DIALOG ====================
const SeatUpgradeDialog = ({ isOpen, onClose, currentSeats, onSubmit, isSubmitting }) => {
  const [requestedSeats, setRequestedSeats] = useState(currentSeats + 10);
  const [justification, setJustification] = useState('');

  const handleSubmit = () => {
    if (requestedSeats <= currentSeats) {
      toast.error('Debes solicitar más asientos que los actuales');
      return;
    }
    onSubmit({ requested_seats: requestedSeats, justification });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md">
        <DialogHeader>
          <DialogTitle>Solicitar Más Asientos</DialogTitle>
          <DialogDescription>
            Tu solicitud será revisada por el administrador de la plataforma.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div>
            <Label>Asientos Actuales</Label>
            <p className="text-2xl font-bold text-primary">{currentSeats}</p>
          </div>
          <div>
            <Label htmlFor="requested-seats">Asientos Solicitados</Label>
            <Input
              id="requested-seats"
              type="number"
              min={currentSeats + 1}
              value={requestedSeats}
              onChange={(e) => setRequestedSeats(parseInt(e.target.value) || currentSeats + 1)}
              className="bg-[#0A0A0F] border-[#1E293B]"
              data-testid="requested-seats-input"
            />
          </div>
          <div>
            <Label htmlFor="justification">Justificación (opcional)</Label>
            <Textarea
              id="justification"
              placeholder="Explica por qué necesitas más asientos..."
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              className="bg-[#0A0A0F] border-[#1E293B]"
              data-testid="justification-input"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancelar</Button>
          <Button onClick={handleSubmit} disabled={isSubmitting} data-testid="submit-upgrade-request">
            {isSubmitting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
            Enviar Solicitud
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// ==================== BILLING EVENTS PANEL ====================
const BillingEventsPanel = ({ condoId, isLoading: parentLoading }) => {
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    const fetchEvents = async () => {
      if (!condoId) return;
      setIsLoading(true);
      try {
        const data = await api.getBillingEvents(condoId);
        setEvents(data || []);
      } catch (error) {
        console.error('Error fetching billing events:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchEvents();
  }, [condoId]);

  const EVENT_TYPE_CONFIG = {
    condominium_created: { label: 'Condominio Creado', color: 'text-green-400', icon: CheckCircle },
    upgrade_requested: { label: 'Upgrade Solicitado', color: 'text-blue-400', icon: ArrowUpCircle },
    upgrade_approved: { label: 'Upgrade Aprobado', color: 'text-green-400', icon: CheckCircle },
    upgrade_rejected: { label: 'Upgrade Rechazado', color: 'text-red-400', icon: XCircle },
    seat_change: { label: 'Cambio de Asientos', color: 'text-purple-400', icon: Users },
    payment_confirmed: { label: 'Pago Confirmado', color: 'text-green-400', icon: DollarSign },
    billing_cycle_change: { label: 'Ciclo Cambiado', color: 'text-yellow-400', icon: Calendar },
  };

  const displayedEvents = showAll ? events : events.slice(0, 5);

  if (parentLoading || isLoading) {
    return (
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Historial de Eventos
          </CardTitle>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <FileText className="w-4 h-4" />
          Historial de Eventos
        </CardTitle>
        <CardDescription>Actividad reciente de facturación</CardDescription>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="text-muted-foreground text-sm text-center py-4">
            No hay eventos de facturación aún
          </p>
        ) : (
          <div className="space-y-3">
            {displayedEvents.map((event, idx) => {
              const config = EVENT_TYPE_CONFIG[event.event_type] || {
                label: event.event_type,
                color: 'text-gray-400',
                icon: FileText
              };
              const Icon = config.icon;
              
              return (
                <div 
                  key={event.id || idx} 
                  className="flex items-start gap-3 p-3 rounded-lg bg-[#1E293B]/30"
                  data-testid={`billing-event-${idx}`}
                >
                  <div className={`p-1.5 rounded-lg bg-[#1E293B] ${config.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`font-medium text-sm ${config.color}`}>
                      {config.label}
                    </p>
                    {event.data?.previous_seats && event.data?.new_seats && (
                      <p className="text-xs text-muted-foreground">
                        {event.data.previous_seats} → {event.data.new_seats} asientos
                      </p>
                    )}
                    {event.data?.new_amount && (
                      <p className="text-xs text-muted-foreground">
                        Nuevo monto: ${event.data.new_amount}
                      </p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1">
                      {event.created_at ? new Date(event.created_at).toLocaleString('es-CR') : 'Fecha desconocida'}
                    </p>
                  </div>
                </div>
              );
            })}
            
            {events.length > 5 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowAll(!showAll)}
                className="w-full text-muted-foreground"
              >
                {showAll ? 'Ver menos' : `Ver todos (${events.length})`}
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// ==================== MAIN COMPONENT ====================
const AdminBillingPage = () => {
  const [isLoading, setIsLoading] = useState(true);
  const [billingInfo, setBillingInfo] = useState(null);
  const [balance, setBalance] = useState(null);
  const [seatStatus, setSeatStatus] = useState(null);
  const [payments, setPayments] = useState([]);
  const [pendingRequest, setPendingRequest] = useState(null);
  const [showUpgradeDialog, setShowUpgradeDialog] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchBillingData = useCallback(async () => {
    setIsLoading(true);
    try {
      // Fetch all billing data in parallel
      const [infoRes, seatRes, paymentsRes, pendingRes] = await Promise.allSettled([
        api.getBillingInfo(),
        api.getSeatUsage(),
        api.getPaymentHistory(),
        api.getMyPendingUpgradeRequest()
      ]);

      if (infoRes.status === 'fulfilled') {
        setBillingInfo(infoRes.value);
        // Balance info is included in billing info for admin
        setBalance({
          balance_due: infoRes.value.balance_due || 0,
          invoice_amount: infoRes.value.next_invoice_amount || 0,
          total_paid_cycle: infoRes.value.total_paid_current_cycle || 0,
          next_billing_date: infoRes.value.next_billing_date,
          billing_cycle: infoRes.value.billing_cycle
        });
      }

      if (seatRes.status === 'fulfilled') {
        setSeatStatus(seatRes.value);
      }

      if (paymentsRes.status === 'fulfilled') {
        setPayments(paymentsRes.value?.payments || paymentsRes.value || []);
      }

      if (pendingRes.status === 'fulfilled' && pendingRes.value) {
        setPendingRequest(pendingRes.value);
      }
    } catch (error) {
      console.error('Error fetching billing data:', error);
      toast.error('Error al cargar datos de facturación');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBillingData();
  }, [fetchBillingData]);

  const handleRequestUpgrade = () => {
    setShowUpgradeDialog(true);
  };

  const handleSubmitUpgradeRequest = async (data) => {
    setIsSubmitting(true);
    try {
      await api.requestSeatUpgrade(data);
      toast.success('Solicitud enviada exitosamente');
      setShowUpgradeDialog(false);
      fetchBillingData();
    } catch (error) {
      console.error('Error submitting upgrade request:', error);
      toast.error(error.response?.data?.detail || 'Error al enviar solicitud');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePaymentUpload = () => {
    // TODO: Implement payment upload dialog
    toast.info('Funcionalidad de subir comprobante próximamente');
  };

  return (
    <DashboardLayout title="Facturación">
      <div className="space-y-6" data-testid="admin-billing-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold font-['Outfit']">Facturación y Pagos</h1>
            <p className="text-muted-foreground">Gestiona tu suscripción y pagos</p>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchBillingData}
            disabled={isLoading}
            data-testid="refresh-billing-btn"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>

        {/* Main Grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left Column - Overview & Actions */}
          <div className="lg:col-span-2 space-y-6">
            <BillingOverviewCard 
              billingInfo={billingInfo}
              balance={balance}
              seatStatus={seatStatus}
              isLoading={isLoading}
            />
            <PaymentHistoryTable 
              payments={payments}
              isLoading={isLoading}
            />
          </div>

          {/* Right Column - Actions & Upgrade */}
          <div className="space-y-6">
            <BillingActions 
              billingInfo={billingInfo}
              balance={balance}
              onRequestUpgrade={handleRequestUpgrade}
              onPaymentUpload={handlePaymentUpload}
              isLoading={isLoading}
            />
            <SeatUpgradeSection 
              pendingRequest={pendingRequest}
              onRefresh={fetchBillingData}
              isLoading={isLoading}
            />
          </div>
        </div>

        {/* Upgrade Dialog */}
        <SeatUpgradeDialog
          isOpen={showUpgradeDialog}
          onClose={() => setShowUpgradeDialog(false)}
          currentSeats={seatStatus?.seat_limit || billingInfo?.paid_seats || 10}
          onSubmit={handleSubmitUpgradeRequest}
          isSubmitting={isSubmitting}
        />
      </div>
    </DashboardLayout>
  );
};

export default AdminBillingPage;
