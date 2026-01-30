import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import DashboardLayout from '../components/layout/DashboardLayout';
import { useIsMobile } from '../components/layout/BottomNav';
import { MobileCard, MobileCardList } from '../components/MobileComponents';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
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
  CreditCard, 
  CheckCircle,
  XCircle,
  Clock,
  DollarSign,
  Loader2,
  Users,
  Minus,
  Plus,
  Sparkles,
  Shield,
  GraduationCap,
  FileText,
  Receipt
} from 'lucide-react';

const PaymentsModule = () => {
  const [searchParams] = useSearchParams();
  const [pricing, setPricing] = useState(null);
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [userCount, setUserCount] = useState(1);
  const [processingCheckout, setProcessingCheckout] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState(null);

  const fetchData = async () => {
    try {
      const [pricingData, historyData] = await Promise.all([
        api.getPricing(),
        api.getPaymentHistory()
      ]);
      setPricing(pricingData);
      setHistory(historyData);
    } catch (error) {
      console.error('Error fetching payment data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    // Check for session_id in URL (return from Stripe)
    const sessionId = searchParams.get('session_id');
    if (sessionId) {
      pollPaymentStatus(sessionId);
    }
  }, [searchParams]);

  const pollPaymentStatus = async (sessionId, attempts = 0) => {
    const maxAttempts = 5;
    const pollInterval = 2000;

    if (attempts >= maxAttempts) {
      setPaymentStatus({ status: 'timeout', message: 'Tiempo de espera agotado. Verifica tu email para confirmación.' });
      return;
    }

    try {
      const status = await api.getPaymentStatus(sessionId);
      
      if (status.payment_status === 'paid') {
        setPaymentStatus({ status: 'success', message: '¡Pago exitoso! Gracias por suscribirte a GENTURIX.' });
        fetchData();
        return;
      } else if (status.status === 'expired') {
        setPaymentStatus({ status: 'error', message: 'La sesión de pago expiró. Por favor intenta de nuevo.' });
        return;
      }

      setPaymentStatus({ status: 'processing', message: 'Procesando pago...' });
      setTimeout(() => pollPaymentStatus(sessionId, attempts + 1), pollInterval);
    } catch (error) {
      console.error('Error checking payment status:', error);
      setPaymentStatus({ status: 'error', message: 'Error verificando el pago.' });
    }
  };

  const handleCheckout = async () => {
    setProcessingCheckout(true);
    try {
      const result = await api.createCheckout({
        user_count: userCount,
        origin_url: window.location.origin
      });
      
      if (result.url) {
        window.location.href = result.url;
      }
    } catch (error) {
      console.error('Error creating checkout:', error);
      alert('Error al procesar el pago. Por favor intenta de nuevo.');
    } finally {
      setProcessingCheckout(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const calculateTotal = () => {
    if (!pricing) return 0;
    return userCount * pricing.price_per_user;
  };

  if (isLoading) {
    return (
      <DashboardLayout title="Pagos y Suscripciones">
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Pagos y Suscripciones">
      <div className="space-y-6">
        {/* Payment Status Alert */}
        {paymentStatus && (
          <div className={`p-4 rounded-lg border ${
            paymentStatus.status === 'success' ? 'bg-green-500/10 border-green-500/20 text-green-400' :
            paymentStatus.status === 'error' ? 'bg-red-500/10 border-red-500/20 text-red-400' :
            'bg-blue-500/10 border-blue-500/20 text-blue-400'
          }`}>
            <div className="flex items-center gap-3">
              {paymentStatus.status === 'success' ? (
                <CheckCircle className="w-5 h-5" />
              ) : paymentStatus.status === 'error' ? (
                <XCircle className="w-5 h-5" />
              ) : (
                <Loader2 className="w-5 h-5 animate-spin" />
              )}
              <span>{paymentStatus.message}</span>
            </div>
          </div>
        )}

        {/* GENTURIX Pricing Model */}
        <Card className="grid-card border-2 border-primary/20 overflow-hidden">
          <div className="bg-gradient-to-r from-primary/10 to-purple-500/10 p-6 border-b border-[#1E293B]">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center">
                <Shield className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h2 className="text-2xl font-bold font-['Outfit']">GENTURIX</h2>
                <p className="text-muted-foreground">Modelo de precios simple y accesible</p>
              </div>
            </div>
          </div>
          <CardContent className="p-6">
            <div className="grid gap-8 lg:grid-cols-2">
              {/* Pricing Info */}
              <div className="space-y-6">
                <div className="text-center p-6 rounded-xl bg-gradient-to-br from-primary/5 to-purple-500/5 border border-primary/20">
                  <div className="flex items-baseline justify-center gap-1">
                    <span className="text-6xl font-bold text-primary">$1</span>
                    <span className="text-2xl text-muted-foreground">/usuario</span>
                  </div>
                  <p className="text-muted-foreground mt-2">por mes</p>
                  <Badge className="mt-4 bg-primary/20 text-primary border-primary/30">
                    Sin planes corporativos - Modelo masivo
                  </Badge>
                </div>

                {/* Features */}
                <div className="space-y-3">
                  <h3 className="font-semibold">Incluido para cada usuario:</h3>
                  {pricing?.features?.map((feature, index) => (
                    <div key={index} className="flex items-center gap-3 text-sm">
                      <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Calculator */}
              <div className="space-y-6">
                <div className="p-6 rounded-xl bg-muted/30 border border-[#1E293B]">
                  <Label className="text-lg font-semibold mb-4 block">Calcular suscripción</Label>
                  
                  <div className="flex items-center justify-center gap-4 my-6">
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-12 w-12 rounded-full border-[#1E293B]"
                      onClick={() => setUserCount(Math.max(1, userCount - 1))}
                      disabled={userCount <= 1}
                      data-testid="decrease-users-btn"
                    >
                      <Minus className="w-5 h-5" />
                    </Button>
                    
                    <div className="text-center">
                      <Input
                        type="number"
                        min="1"
                        value={userCount}
                        onChange={(e) => setUserCount(Math.max(1, parseInt(e.target.value) || 1))}
                        className="w-24 h-16 text-center text-3xl font-bold bg-[#181B25] border-[#1E293B]"
                        data-testid="user-count-input"
                      />
                      <p className="text-sm text-muted-foreground mt-1">usuarios</p>
                    </div>
                    
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-12 w-12 rounded-full border-[#1E293B]"
                      onClick={() => setUserCount(userCount + 1)}
                      data-testid="increase-users-btn"
                    >
                      <Plus className="w-5 h-5" />
                    </Button>
                  </div>

                  <div className="border-t border-[#1E293B] pt-4 mt-4">
                    <div className="flex justify-between items-center text-sm text-muted-foreground mb-2">
                      <span>{userCount} usuario{userCount > 1 ? 's' : ''} × $1.00</span>
                      <span>{formatCurrency(calculateTotal())}/mes</span>
                    </div>
                    <div className="flex justify-between items-center text-xl font-bold">
                      <span>Total mensual:</span>
                      <span className="text-primary">{formatCurrency(calculateTotal())}</span>
                    </div>
                  </div>

                  <Button
                    className="w-full mt-6 h-12 text-lg"
                    onClick={handleCheckout}
                    disabled={processingCheckout}
                    data-testid="checkout-btn"
                  >
                    {processingCheckout ? (
                      <>
                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                        Procesando...
                      </>
                    ) : (
                      <>
                        <CreditCard className="w-5 h-5 mr-2" />
                        Suscribirse por {formatCurrency(calculateTotal())}/mes
                      </>
                    )}
                  </Button>
                </div>

                {/* Quick select */}
                <div className="flex flex-wrap gap-2">
                  {[1, 5, 10, 25, 50, 100].map((num) => (
                    <Button
                      key={num}
                      variant="outline"
                      size="sm"
                      className={`border-[#1E293B] ${userCount === num ? 'bg-primary/20 border-primary' : ''}`}
                      onClick={() => setUserCount(num)}
                      data-testid={`quick-select-${num}`}
                    >
                      {num} usuario{num > 1 ? 's' : ''}
                    </Button>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Premium Modules */}
        {pricing?.premium_modules && pricing.premium_modules.length > 0 && (
          <Card className="grid-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-yellow-400" />
                Módulos Premium (Próximamente)
              </CardTitle>
              <CardDescription>
                Funcionalidades adicionales que puedes agregar a tu suscripción base
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                {pricing.premium_modules.map((module, index) => (
                  <div 
                    key={index}
                    className="p-4 rounded-lg bg-muted/30 border border-[#1E293B] opacity-75"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{module.name}</span>
                      <Badge variant="outline">+${module.price}/usuario</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{module.description}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Payment History */}
        <Card className="grid-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-blue-400" />
              Historial de Pagos
            </CardTitle>
            <CardDescription>Registro de todas tus transacciones</CardDescription>
          </CardHeader>
          <CardContent>
            {history.length > 0 ? (
              <>
                {/* Desktop Table View - hidden on mobile */}
                <div className="hidden lg:block overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-[#1E293B]">
                        <TableHead>Fecha</TableHead>
                        <TableHead>Usuarios</TableHead>
                        <TableHead>Monto</TableHead>
                        <TableHead>Estado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {history.map((transaction) => (
                        <TableRow key={transaction.id} className="border-[#1E293B]" data-testid={`transaction-${transaction.id}`}>
                          <TableCell className="text-muted-foreground">
                            {formatDate(transaction.created_at)}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Users className="w-4 h-4 text-muted-foreground" />
                              {transaction.user_count || 1} usuario{(transaction.user_count || 1) > 1 ? 's' : ''}
                            </div>
                          </TableCell>
                          <TableCell className="font-mono">{formatCurrency(transaction.amount)}</TableCell>
                          <TableCell>
                            <Badge className={
                              transaction.payment_status === 'completed' ? 'badge-success' :
                              transaction.payment_status === 'pending' ? 'badge-warning' :
                              'badge-error'
                            }>
                              {transaction.payment_status === 'completed' ? 'Completado' :
                               transaction.payment_status === 'pending' ? 'Pendiente' : 'Fallido'}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>

                {/* Mobile Card View */}
                <div className="block lg:hidden">
                  <MobileCardList>
                    {history.map((transaction) => (
                      <MobileCard
                        key={transaction.id}
                        testId={`transaction-card-${transaction.id}`}
                        title={formatCurrency(transaction.amount)}
                        subtitle={formatDate(transaction.created_at)}
                        icon={Receipt}
                        status={
                          transaction.payment_status === 'completed' ? 'Completado' :
                          transaction.payment_status === 'pending' ? 'Pendiente' : 'Fallido'
                        }
                        statusColor={
                          transaction.payment_status === 'completed' ? 'green' :
                          transaction.payment_status === 'pending' ? 'yellow' : 'red'
                        }
                        details={[
                          { label: 'Usuarios', value: `${transaction.user_count || 1} usuario${(transaction.user_count || 1) > 1 ? 's' : ''}` },
                          { label: 'Monto', value: formatCurrency(transaction.amount) },
                        ]}
                      />
                    ))}
                  </MobileCardList>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <DollarSign className="w-12 h-12 mb-4" />
                <p>No hay transacciones registradas</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Payment Methods Info */}
        <Card className="grid-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-green-400" />
              Métodos de Pago Aceptados
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <div className="w-12 h-8 bg-blue-600 rounded flex items-center justify-center text-white font-bold text-xs">
                  VISA
                </div>
                <span className="text-sm text-muted-foreground">Visa</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-12 h-8 bg-red-600 rounded flex items-center justify-center text-white font-bold text-xs">
                  MC
                </div>
                <span className="text-sm text-muted-foreground">Mastercard</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-12 h-8 bg-purple-600 rounded flex items-center justify-center text-white font-bold text-xs">
                  AMEX
                </div>
                <span className="text-sm text-muted-foreground">American Express</span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-4">
              Todos los pagos son procesados de forma segura a través de Stripe. 
              El precio de GENTURIX es siempre <strong>$1 por usuario al mes</strong> - sin sorpresas, sin planes complicados.
            </p>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default PaymentsModule;
