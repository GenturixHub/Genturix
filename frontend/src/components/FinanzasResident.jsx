import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from './ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from './ui/select';
import { toast } from 'sonner';
import api from '../services/api';
import {
  DollarSign, CheckCircle, AlertTriangle, TrendingUp, Loader2,
  Receipt, Wallet, CreditCard, Smartphone, Building2, Copy, Check,
} from 'lucide-react';

const STATUS_COLORS = {
  paid: 'bg-green-500/15 text-green-400 border-green-500/30',
  pending: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  overdue: 'bg-red-500/15 text-red-400 border-red-500/30',
  partial: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
};
const STATUS_LABELS = { paid: 'Pagado', pending: 'Pendiente', overdue: 'Vencido', partial: 'Parcial' };

function fmt(n) { return new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'USD' }).format(n); }

// ── Pay Now Dialog ──
const PayDialog = ({ open, onClose, balance, unitId }) => {
  const [step, setStep] = useState('method'); // method | instructions | confirm
  const [method, setMethod] = useState('');
  const [settings, setSettings] = useState({});
  const [amount, setAmount] = useState('');
  const [reference, setReference] = useState('');
  const [notes, setNotes] = useState('');
  const [sending, setSending] = useState(false);
  const [loadingSettings, setLoadingSettings] = useState(false);
  const [copied, setCopied] = useState('');

  useEffect(() => {
    if (open) {
      setStep('method');
      setMethod('');
      setAmount(balance > 0 ? String(balance) : '');
      setReference('');
      setNotes('');
    }
  }, [open, balance]);

  const selectMethod = async (m) => {
    setMethod(m);
    setLoadingSettings(true);
    try {
      const s = await api.getPaymentSettings();
      setSettings(s || {});
    } catch { setSettings({}); }
    finally { setLoadingSettings(false); }
    setStep('instructions');
  };

  const handleCopy = (text, label) => {
    navigator.clipboard.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(''), 2000);
  };

  const handleSubmit = async () => {
    if (!amount || parseFloat(amount) <= 0) { toast.error('Ingresa un monto valido'); return; }
    setSending(true);
    try {
      await api.createPaymentRequest({
        amount: parseFloat(amount),
        payment_method: method,
        reference: reference.trim(),
        notes: notes.trim(),
      });
      toast.success('Comprobante enviado. El administrador lo revisara.');
      onClose();
    } catch (err) { toast.error(err.message || 'Error al enviar'); }
    finally { setSending(false); }
  };

  const CopyBtn = ({ text, label }) => (
    <button onClick={() => handleCopy(text, label)} className="ml-2 p-1 rounded hover:bg-white/10 transition-colors">
      {copied === label ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5 text-muted-foreground" />}
    </button>
  );

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md" data-testid="pay-dialog">
        <DialogHeader>
          <DialogTitle>{step === 'method' ? 'Metodo de Pago' : step === 'instructions' ? 'Instrucciones de Pago' : 'Confirmar Pago'}</DialogTitle>
        </DialogHeader>

        {step === 'method' && (
          <div className="space-y-3">
            <button onClick={() => selectMethod('sinpe')} className="w-full p-4 rounded-lg bg-[#181B25] border border-[#1E293B] hover:border-primary/50 transition-colors text-left flex items-center gap-3" data-testid="method-sinpe">
              <div className="w-10 h-10 rounded-lg bg-blue-500/15 flex items-center justify-center">
                <Smartphone className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">SINPE Movil</p>
                <p className="text-xs text-muted-foreground">Pago rapido desde tu celular</p>
              </div>
            </button>
            <button onClick={() => selectMethod('transferencia')} className="w-full p-4 rounded-lg bg-[#181B25] border border-[#1E293B] hover:border-primary/50 transition-colors text-left flex items-center gap-3" data-testid="method-transfer">
              <div className="w-10 h-10 rounded-lg bg-green-500/15 flex items-center justify-center">
                <Building2 className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">Transferencia Bancaria</p>
                <p className="text-xs text-muted-foreground">Desde tu cuenta bancaria</p>
              </div>
            </button>
          </div>
        )}

        {step === 'instructions' && (
          <div className="space-y-4">
            {loadingSettings ? (
              <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin" /></div>
            ) : (
              <>
                {method === 'sinpe' && (
                  <div className="space-y-3">
                    {settings.sinpe_number ? (
                      <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20">
                        <p className="text-xs text-blue-400 font-medium mb-2">SINPE Movil</p>
                        <div className="flex items-center justify-between">
                          <p className="text-lg font-bold text-white">{settings.sinpe_number}</p>
                          <CopyBtn text={settings.sinpe_number} label="sinpe" />
                        </div>
                        {settings.sinpe_name && <p className="text-sm text-muted-foreground mt-1">A nombre de: {settings.sinpe_name}</p>}
                      </div>
                    ) : (
                      <div className="p-4 rounded-lg bg-[#181B25] text-center">
                        <p className="text-sm text-muted-foreground">El administrador no ha configurado los datos de SINPE. Contactalo directamente.</p>
                      </div>
                    )}
                  </div>
                )}
                {method === 'transferencia' && (
                  <div className="space-y-3">
                    {settings.bank_account || settings.bank_iban ? (
                      <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20 space-y-2">
                        <p className="text-xs text-green-400 font-medium">Transferencia Bancaria</p>
                        {settings.bank_name && (
                          <div><span className="text-xs text-muted-foreground">Banco:</span> <span className="text-sm text-white ml-1">{settings.bank_name}</span></div>
                        )}
                        {settings.bank_account && (
                          <div className="flex items-center"><span className="text-xs text-muted-foreground">Cuenta:</span> <span className="text-sm text-white ml-1">{settings.bank_account}</span> <CopyBtn text={settings.bank_account} label="account" /></div>
                        )}
                        {settings.bank_iban && (
                          <div className="flex items-center"><span className="text-xs text-muted-foreground">IBAN:</span> <span className="text-sm text-white ml-1">{settings.bank_iban}</span> <CopyBtn text={settings.bank_iban} label="iban" /></div>
                        )}
                      </div>
                    ) : (
                      <div className="p-4 rounded-lg bg-[#181B25] text-center">
                        <p className="text-sm text-muted-foreground">El administrador no ha configurado los datos bancarios. Contactalo directamente.</p>
                      </div>
                    )}
                  </div>
                )}
                {settings.additional_instructions && (
                  <div className="p-3 rounded-lg bg-[#181B25] border border-[#1E293B]">
                    <p className="text-xs text-muted-foreground">{settings.additional_instructions}</p>
                  </div>
                )}

                {/* Amount and reference */}
                <div className="space-y-3 pt-2 border-t border-[#1E293B]">
                  <p className="text-xs text-muted-foreground font-medium">Una vez realizado el pago, reportalo aqui:</p>
                  <Input type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Monto pagado" className="bg-[#181B25] border-[#1E293B]" data-testid="pay-amount" />
                  <Input value={reference} onChange={(e) => setReference(e.target.value)} placeholder="Numero de referencia (opcional)" className="bg-[#181B25] border-[#1E293B]" data-testid="pay-reference" maxLength={200} />
                  <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Notas adicionales (opcional)" rows={2} className="w-full rounded-md bg-[#181B25] border border-[#1E293B] text-sm px-3 py-2 text-white placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none" data-testid="pay-notes" maxLength={500} />
                  <Button onClick={handleSubmit} disabled={sending || !amount || parseFloat(amount) <= 0} className="w-full" data-testid="submit-payment-request">
                    {sending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CreditCard className="w-4 h-4 mr-2" />}
                    Reportar Pago
                  </Button>
                </div>
              </>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

// ── Main Component ──
export default function FinanzasResident() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showPay, setShowPay] = useState(false);
  const [myRequests, setMyRequests] = useState([]);

  const unitId = user?.role_data?.apartment_number || user?.apartment || '';

  const fetchData = useCallback(async () => {
    if (!unitId) { setLoading(false); return; }
    setLoading(true);
    try {
      const [result, reqData] = await Promise.all([
        api.getUnitAccount(unitId),
        api.getPaymentRequests().catch(() => ({ items: [] })),
      ]);
      setData(result);
      setMyRequests(reqData.items || []);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [unitId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!unitId) {
    return (
      <div className="h-full overflow-y-auto" style={{ WebkitOverflowScrolling: 'touch', paddingBottom: '112px' }}>
        <div className="p-3 text-center py-12" data-testid="finanzas-resident">
          <Wallet className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">No tienes una unidad asignada.</p>
          <p className="text-xs text-muted-foreground mt-1">Contacta a tu administrador.</p>
        </div>
      </div>
    );
  }

  const account = data?.account || { current_balance: 0, status: 'al_dia' };
  const breakdown = data?.breakdown || {};
  const records = data?.records || [];
  const balance = account.current_balance || 0;

  const statusConfig = {
    al_dia: { label: 'Al Dia', icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20' },
    atrasado: { label: 'Atrasado', icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' },
    adelantado: { label: 'Adelantado', icon: TrendingUp, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
  };
  const sc = statusConfig[account.status] || statusConfig.al_dia;
  const StatusIcon = sc.icon;

  const pendingRequests = myRequests.filter(r => r.status === 'pending');

  return (
    <div className="h-full overflow-y-auto" style={{ WebkitOverflowScrolling: 'touch', paddingBottom: '112px' }}>
      <div className="p-3 space-y-4" data-testid="finanzas-resident">
        <h2 className="text-base font-semibold">{t('finanzas.myFinances', 'Mi Estado Financiero')}</h2>

        {/* Unit & Balance Card */}
        <Card className={`border ${sc.bg}`} data-testid="balance-card">
          <CardContent className="p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-xs text-muted-foreground">Tu unidad</p>
                <p className="text-lg font-bold text-white">{unitId}</p>
              </div>
              <Badge variant="outline" className={`${sc.bg} ${sc.color}`}>
                {sc.label}
              </Badge>
            </div>
            <div className="text-center py-3">
              <StatusIcon className={`w-10 h-10 mx-auto mb-2 ${sc.color}`} />
              <p className={`text-3xl font-bold ${sc.color}`}>
                {balance > 0 ? fmt(balance) : balance < 0 ? fmt(Math.abs(balance)) : '$0.00'}
              </p>
              <p className={`text-sm mt-1 ${sc.color}`}>
                {balance > 0 ? 'Saldo pendiente' : balance < 0 ? 'Saldo a favor' : 'Sin saldo pendiente'}
              </p>
            </div>
            {balance > 0 && (
              <Button onClick={() => setShowPay(true)} className="w-full mt-3" data-testid="pay-now-btn">
                <CreditCard className="w-4 h-4 mr-2" /> Pagar ahora
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Pending payment requests */}
        {pendingRequests.length > 0 && (
          <Card className="bg-orange-500/5 border-orange-500/20">
            <CardContent className="p-3">
              <p className="text-xs text-orange-400 font-medium mb-2">Pagos pendientes de revision ({pendingRequests.length})</p>
              {pendingRequests.map(pr => (
                <div key={pr.id} className="flex items-center justify-between py-1.5">
                  <span className="text-sm text-white">{fmt(pr.amount)} via {pr.payment_method}</span>
                  <Badge variant="outline" className="text-[9px] bg-orange-500/15 text-orange-400 border-orange-500/30">En revision</Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Breakdown */}
        {Object.keys(breakdown).length > 0 && (
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Receipt className="w-4 h-4 text-primary" />
                {t('finanzas.breakdown', 'Desglose')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {Object.entries(breakdown).map(([name, vals]) => (
                <div key={name} className="flex items-center justify-between p-2 rounded-lg bg-[#181B25]" data-testid={`breakdown-${name}`}>
                  <span className="text-sm text-white">{name}</span>
                  <span className={`text-sm font-medium ${vals.pending > 0 ? 'text-red-400' : vals.pending < 0 ? 'text-blue-400' : 'text-green-400'}`}>
                    {vals.pending > 0 ? `Debe: ${fmt(vals.pending)}` : vals.pending < 0 ? `A favor: ${fmt(Math.abs(vals.pending))}` : 'Al dia'}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* History */}
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Wallet className="w-4 h-4 text-primary" />
              {t('finanzas.history', 'Historial')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {records.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-6">No hay movimientos registrados</p>
            ) : (
              <div className="space-y-2">
                {records.slice(0, 20).map((r) => (
                  <div key={r.id} className="flex items-center justify-between p-2 rounded-lg bg-[#181B25]" data-testid={`record-${r.id}`}>
                    <div>
                      <p className="text-sm text-white">{r.charge_type_name}</p>
                      <p className="text-[10px] text-muted-foreground">{r.period}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium">{fmt(r.amount_due)}</p>
                      <Badge variant="outline" className={`text-[9px] h-4 ${STATUS_COLORS[r.status] || ''}`}>
                        {STATUS_LABELS[r.status] || r.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <PayDialog open={showPay} onClose={() => { setShowPay(false); fetchData(); }} balance={balance} unitId={unitId} />
    </div>
  );
}
