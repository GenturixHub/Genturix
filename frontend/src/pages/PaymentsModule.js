import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
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
  ExternalLink,
  Star,
  Zap,
  Crown
} from 'lucide-react';

const PaymentsModule = () => {
  const [searchParams] = useSearchParams();
  const [packages, setPackages] = useState({});
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [processingPackage, setProcessingPackage] = useState(null);
  const [paymentStatus, setPaymentStatus] = useState(null);

  const fetchData = async () => {
    try {
      const [packagesData, historyData] = await Promise.all([
        api.getPackages(),
        api.getPaymentHistory()
      ]);
      setPackages(packagesData);
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
        setPaymentStatus({ status: 'success', message: '¡Pago exitoso! Gracias por tu compra.' });
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

  const handleCheckout = async (packageId) => {
    setProcessingPackage(packageId);
    try {
      const result = await api.createCheckout({
        package_id: packageId,
        origin_url: window.location.origin
      });
      
      if (result.url) {
        window.location.href = result.url;
      }
    } catch (error) {
      console.error('Error creating checkout:', error);
      alert('Error al procesar el pago. Por favor intenta de nuevo.');
    } finally {
      setProcessingPackage(null);
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

  const getPackageIcon = (packageId) => {
    switch (packageId) {
      case 'basic':
        return <Star className="w-8 h-8" />;
      case 'professional':
        return <Zap className="w-8 h-8" />;
      case 'enterprise':
        return <Crown className="w-8 h-8" />;
      default:
        return <Star className="w-8 h-8" />;
    }
  };

  const getPackageColors = (packageId) => {
    switch (packageId) {
      case 'basic':
        return 'from-blue-500/20 to-cyan-500/20 border-blue-500/20';
      case 'professional':
        return 'from-purple-500/20 to-pink-500/20 border-purple-500/20';
      case 'enterprise':
        return 'from-yellow-500/20 to-orange-500/20 border-yellow-500/20';
      default:
        return 'from-gray-500/20 to-slate-500/20 border-gray-500/20';
    }
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

        {/* Packages */}
        <div>
          <h2 className="text-xl font-bold font-['Outfit'] mb-4">Planes Disponibles</h2>
          <div className="grid gap-6 md:grid-cols-3">
            {Object.entries(packages).map(([packageId, pkg]) => (
              <Card 
                key={packageId}
                className={`grid-card bg-gradient-to-br ${getPackageColors(packageId)}`}
                data-testid={`package-card-${packageId}`}
              >
                <CardHeader className="text-center">
                  <div className="w-16 h-16 mx-auto rounded-full bg-white/10 flex items-center justify-center mb-4">
                    {getPackageIcon(packageId)}
                  </div>
                  <CardTitle className="text-xl">{pkg.name}</CardTitle>
                  <div className="mt-4">
                    <span className="text-4xl font-bold">{formatCurrency(pkg.price)}</span>
                    <span className="text-muted-foreground">/mes</span>
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3 mb-6">
                    {pkg.features.map((feature, index) => (
                      <li key={index} className="flex items-center gap-2 text-sm">
                        <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className="w-full"
                    onClick={() => handleCheckout(packageId)}
                    disabled={processingPackage === packageId}
                    data-testid={`checkout-btn-${packageId}`}
                  >
                    {processingPackage === packageId ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Procesando...
                      </>
                    ) : (
                      <>
                        <CreditCard className="w-4 h-4 mr-2" />
                        Suscribirse
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

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
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-[#1E293B]">
                      <TableHead>Fecha</TableHead>
                      <TableHead>Plan</TableHead>
                      <TableHead>Monto</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>ID Sesión</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history.map((transaction) => (
                      <TableRow key={transaction.id} className="border-[#1E293B]" data-testid={`transaction-${transaction.id}`}>
                        <TableCell className="text-muted-foreground">
                          {formatDate(transaction.created_at)}
                        </TableCell>
                        <TableCell className="font-medium">{transaction.package_name}</TableCell>
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
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {transaction.session_id?.slice(0, 20)}...
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
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
            </p>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
};

export default PaymentsModule;
