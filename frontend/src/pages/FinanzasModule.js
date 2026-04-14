import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
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
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import api from '../services/api';
import {
  DollarSign,
  Plus,
  CreditCard,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Filter,
  Wallet,
  Receipt,
  ArrowDownCircle,
  FileDown,
  FileSpreadsheet,
} from 'lucide-react';

const STATUS_COLORS = {
  paid: 'bg-green-500/15 text-green-400 border-green-500/30',
  pending: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  overdue: 'bg-red-500/15 text-red-400 border-red-500/30',
  partial: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
};
const STATUS_LABELS = { paid: 'Pagado', pending: 'Pendiente', overdue: 'Vencido', partial: 'Parcial' };
const ACCT_COLORS = {
  al_dia: 'text-green-400',
  atrasado: 'text-red-400',
  adelantado: 'text-blue-400',
};
const ACCT_LABELS = { al_dia: 'Al día', atrasado: 'Atrasado', adelantado: 'Adelantado' };

function fmt(n) { return new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'USD' }).format(n); }

// ── Summary Cards ──
const SummaryCards = ({ summary }) => {
  if (!summary) return null;
  const cards = [
    { label: 'Total Cobrado', value: fmt(summary.global_due), color: 'text-white', icon: Receipt },
    { label: 'Total Pagado', value: fmt(summary.global_paid), color: 'text-green-400', icon: CheckCircle },
    { label: 'Balance Global', value: fmt(summary.global_balance), color: summary.global_balance > 0 ? 'text-red-400' : 'text-green-400', icon: DollarSign },
    { label: 'Al día', value: summary.al_dia, color: 'text-green-400', icon: CheckCircle },
    { label: 'Atrasados', value: summary.atrasado, color: 'text-red-400', icon: AlertTriangle },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3" data-testid="finanzas-summary">
      {cards.map((c) => {
        const Icon = c.icon;
        return (
          <Card key={c.label} className="bg-[#0F111A] border-[#1E293B]">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-1">
                <Icon className="w-4 h-4 text-muted-foreground" />
                <p className="text-xs text-muted-foreground">{c.label}</p>
              </div>
              <p className={`text-xl font-bold ${c.color}`}>{c.value}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};

// ── Create Charge Catalog Dialog ──
const CatalogDialog = ({ open, onClose, onCreated }) => {
  const [name, setName] = useState('');
  const [type, setType] = useState('fixed');
  const [amount, setAmount] = useState('');
  const [sending, setSending] = useState(false);
  const handleSubmit = async () => {
    if (!name.trim() || !amount) return;
    setSending(true);
    try {
      await api.createChargeCatalog({ name: name.trim(), type, default_amount: parseFloat(amount) });
      toast.success('Tipo de cargo creado');
      setName(''); setAmount(''); onCreated?.(); onClose();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setSending(false); }
  };
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md" data-testid="catalog-dialog">
        <DialogHeader><DialogTitle>Nuevo Tipo de Cargo</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <Input data-testid="catalog-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej: Cuota mensual" className="bg-[#181B25] border-[#1E293B]" />
          <div className="grid grid-cols-2 gap-3">
            <Select value={type} onValueChange={setType}>
              <SelectTrigger className="bg-[#181B25] border-[#1E293B]"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                <SelectItem value="fixed">Fijo</SelectItem>
                <SelectItem value="variable">Variable</SelectItem>
              </SelectContent>
            </Select>
            <Input data-testid="catalog-amount" type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Monto" className="bg-[#181B25] border-[#1E293B]" />
          </div>
          <Button onClick={handleSubmit} disabled={sending || !name.trim() || !amount} data-testid="submit-catalog" className="w-full">
            {sending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />} Crear Cargo
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ── Create Charge Dialog ──
const ChargeDialog = ({ open, onClose, onCreated, catalog }) => {
  const [unitId, setUnitId] = useState('');
  const [chargeTypeId, setChargeTypeId] = useState('');
  const [period, setPeriod] = useState(() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; });
  const [amount, setAmount] = useState('');
  const [sending, setSending] = useState(false);

  const selectedCatalog = catalog.find(c => c.id === chargeTypeId);
  useEffect(() => { if (selectedCatalog && !amount) setAmount(String(selectedCatalog.default_amount)); }, [selectedCatalog, amount]);

  const handleSubmit = async () => {
    if (!unitId.trim() || !chargeTypeId || !period || !amount) return;
    setSending(true);
    try {
      await api.createCharge({ unit_id: unitId.trim(), charge_type_id: chargeTypeId, period, amount_due: parseFloat(amount) });
      toast.success('Cargo creado'); setUnitId(''); setChargeTypeId(''); setAmount(''); onCreated?.(); onClose();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setSending(false); }
  };
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md" data-testid="charge-dialog">
        <DialogHeader><DialogTitle>Generar Cargo</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <Input data-testid="charge-unit" value={unitId} onChange={(e) => setUnitId(e.target.value)} placeholder="Unidad (ej: A-101)" className="bg-[#181B25] border-[#1E293B]" />
          <Select value={chargeTypeId} onValueChange={(v) => { setChargeTypeId(v); setAmount(''); }}>
            <SelectTrigger data-testid="charge-type-select" className="bg-[#181B25] border-[#1E293B]"><SelectValue placeholder="Tipo de cargo" /></SelectTrigger>
            <SelectContent className="bg-[#0F111A] border-[#1E293B]">
              {catalog.map(c => <SelectItem key={c.id} value={c.id}>{c.name} ({fmt(c.default_amount)})</SelectItem>)}
            </SelectContent>
          </Select>
          <div className="grid grid-cols-2 gap-3">
            <Input data-testid="charge-period" type="month" value={period} onChange={(e) => setPeriod(e.target.value)} className="bg-[#181B25] border-[#1E293B]" />
            <Input data-testid="charge-amount" type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Monto" className="bg-[#181B25] border-[#1E293B]" />
          </div>
          <Button onClick={handleSubmit} disabled={sending || !unitId.trim() || !chargeTypeId || !amount} data-testid="submit-charge" className="w-full">
            {sending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Receipt className="w-4 h-4 mr-2" />} Generar Cargo
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ── Payment Dialog ──
const PaymentDialog = ({ open, onClose, onCreated }) => {
  const [unitId, setUnitId] = useState('');
  const [amount, setAmount] = useState('');
  const [method, setMethod] = useState('efectivo');
  const [sending, setSending] = useState(false);
  const handleSubmit = async () => {
    if (!unitId.trim() || !amount) return;
    setSending(true);
    try {
      const result = await api.registerPayment({ unit_id: unitId.trim(), amount: parseFloat(amount), payment_method: method });
      toast.success(`Pago registrado. Nuevo balance: ${fmt(result.new_balance)}`);
      setUnitId(''); setAmount(''); onCreated?.(); onClose();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setSending(false); }
  };
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md" data-testid="payment-dialog">
        <DialogHeader><DialogTitle>Registrar Pago</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <Input data-testid="payment-unit" value={unitId} onChange={(e) => setUnitId(e.target.value)} placeholder="Unidad (ej: A-101)" className="bg-[#181B25] border-[#1E293B]" />
          <Input data-testid="payment-amount" type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="Monto a pagar" className="bg-[#181B25] border-[#1E293B]" />
          <Select value={method} onValueChange={setMethod}>
            <SelectTrigger data-testid="payment-method" className="bg-[#181B25] border-[#1E293B]"><SelectValue /></SelectTrigger>
            <SelectContent className="bg-[#0F111A] border-[#1E293B]">
              <SelectItem value="efectivo">Efectivo</SelectItem>
              <SelectItem value="transferencia">Transferencia</SelectItem>
              <SelectItem value="tarjeta">Tarjeta</SelectItem>
              <SelectItem value="sinpe">SINPE</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={handleSubmit} disabled={sending || !unitId.trim() || !amount} data-testid="submit-payment" className="w-full">
            {sending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <CreditCard className="w-4 h-4 mr-2" />} Registrar Pago
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ── Bulk Charge Dialog ──
const BulkChargeDialog = ({ open, onClose, onCreated, catalog }) => {
  const [chargeTypeId, setChargeTypeId] = useState('');
  const [period, setPeriod] = useState(() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; });
  const [dueDate, setDueDate] = useState('');
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async () => {
    if (!chargeTypeId || !period) return;
    setSending(true);
    setResult(null);
    try {
      const data = { charge_type_id: chargeTypeId, period };
      if (dueDate) data.due_date = dueDate;
      const res = await api.generateBulkCharges(data);
      setResult(res);
      toast.success(`${res.created_count} cargos generados, ${res.skipped_count} omitidos`);
      onCreated?.();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setSending(false); }
  };

  const handleClose = () => { setResult(null); setChargeTypeId(''); onClose(); };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md" data-testid="bulk-charge-dialog">
        <DialogHeader><DialogTitle>Generación Masiva de Cargos</DialogTitle></DialogHeader>
        <div className="space-y-3">
          {!result ? (
            <>
              <Select value={chargeTypeId} onValueChange={setChargeTypeId}>
                <SelectTrigger data-testid="bulk-charge-type" className="bg-[#181B25] border-[#1E293B]"><SelectValue placeholder="Tipo de cargo" /></SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  {catalog.map(c => <SelectItem key={c.id} value={c.id}>{c.name} ({fmt(c.default_amount)})</SelectItem>)}
                </SelectContent>
              </Select>
              <Input data-testid="bulk-period" type="month" value={period} onChange={(e) => setPeriod(e.target.value)} className="bg-[#181B25] border-[#1E293B]" />
              <Input data-testid="bulk-due-date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} placeholder="Fecha de vencimiento (opcional)" className="bg-[#181B25] border-[#1E293B]" />
              <p className="text-xs text-muted-foreground">Se generará un cargo para TODAS las unidades registradas. Las unidades que ya tengan este cargo para el período seleccionado serán omitidas.</p>
              <Button onClick={handleSubmit} disabled={sending || !chargeTypeId || !period} data-testid="submit-bulk" className="w-full">
                {sending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ArrowDownCircle className="w-4 h-4 mr-2" />} Generar Cargos Masivos
              </Button>
            </>
          ) : (
            <div className="space-y-3" data-testid="bulk-result">
              <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20 text-center">
                <CheckCircle className="w-8 h-8 text-green-400 mx-auto mb-2" />
                <p className="text-lg font-bold text-white">Cargos Generados</p>
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-3 rounded-lg bg-[#181B25]">
                  <p className="text-xl font-bold text-white">{result.total_units}</p>
                  <p className="text-[10px] text-muted-foreground">Total Unidades</p>
                </div>
                <div className="p-3 rounded-lg bg-[#181B25]">
                  <p className="text-xl font-bold text-green-400">{result.created_count}</p>
                  <p className="text-[10px] text-muted-foreground">Creados</p>
                </div>
                <div className="p-3 rounded-lg bg-[#181B25]">
                  <p className="text-xl font-bold text-yellow-400">{result.skipped_count}</p>
                  <p className="text-[10px] text-muted-foreground">Omitidos</p>
                </div>
              </div>
              <div className="text-xs text-muted-foreground text-center">
                <p>{result.charge_type} - {result.period} - {fmt(result.amount)} c/u</p>
              </div>
              <Button variant="outline" onClick={handleClose} className="w-full" data-testid="bulk-close">Cerrar</Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ── Main Page ──
export default function FinanzasModule() {
  const { t } = useTranslation();
  const [overview, setOverview] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCatalog, setShowCatalog] = useState(false);
  const [showCharge, setShowCharge] = useState(false);
  const [showPayment, setShowPayment] = useState(false);
  const [showBulk, setShowBulk] = useState(false);
  const [exporting, setExporting] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, cat] = await Promise.all([api.getFinanzasOverview(), api.getChargeCatalog()]);
      setOverview(ov);
      setCatalog(cat || []);
    } catch { /* empty state */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleExport = async (fmt) => {
    setExporting(fmt);
    try {
      await api.downloadFinancialReport(fmt);
      toast.success(fmt === 'pdf' ? 'PDF descargado' : 'CSV descargado');
    } catch (err) {
      toast.error(err.message || 'Error al exportar');
    } finally {
      setExporting(null);
    }
  };

  return (
    <DashboardLayout title={t('finanzas.pageTitle', 'Finanzas')}>
      <div data-testid="finanzas-module" className="space-y-6">
        {loading ? (
          <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
        ) : (
          <>
            <SummaryCards summary={overview?.summary} />

            {/* Actions */}
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={() => setShowCatalog(true)} data-testid="btn-new-catalog">
                <Plus className="w-4 h-4 mr-1" /> Tipo de Cargo
              </Button>
              <Button size="sm" variant="outline" onClick={() => setShowCharge(true)} data-testid="btn-new-charge" disabled={catalog.length === 0}>
                <Receipt className="w-4 h-4 mr-1" /> Generar Cargo
              </Button>
              <Button size="sm" variant="outline" onClick={() => setShowBulk(true)} data-testid="btn-bulk-charge" disabled={catalog.length === 0}>
                <ArrowDownCircle className="w-4 h-4 mr-1" /> Cargos Masivos
              </Button>
              <Button size="sm" onClick={() => setShowPayment(true)} data-testid="btn-new-payment">
                <CreditCard className="w-4 h-4 mr-1" /> Registrar Pago
              </Button>
              <div className="ml-auto flex gap-2">
                <Button size="sm" variant="outline" onClick={() => handleExport('pdf')} disabled={!!exporting} data-testid="btn-export-pdf">
                  {exporting === 'pdf' ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <FileDown className="w-4 h-4 mr-1" />} PDF
                </Button>
                <Button size="sm" variant="outline" onClick={() => handleExport('csv')} disabled={!!exporting} data-testid="btn-export-csv">
                  {exporting === 'csv' ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <FileSpreadsheet className="w-4 h-4 mr-1" />} CSV
                </Button>
              </div>
            </div>

            {/* Catalog */}
            {catalog.length > 0 && (
              <Card className="bg-[#0F111A] border-[#1E293B]">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2"><Receipt className="w-4 h-4 text-primary" /> Tipos de Cargo</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {catalog.map(c => (
                      <Badge key={c.id} variant="outline" className="bg-[#181B25] border-[#1E293B] text-sm py-1 px-3" data-testid={`catalog-${c.id}`}>
                        {c.name}: {fmt(c.default_amount)} <span className="text-muted-foreground ml-1">({c.type})</span>
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Accounts Table */}
            <Card className="bg-[#0F111A] border-[#1E293B]">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base"><Wallet className="w-4 h-4 text-primary" /> Cuentas por Unidad</CardTitle>
              </CardHeader>
              <CardContent>
                {(!overview?.accounts || overview.accounts.length === 0) ? (
                  <div className="text-center py-8">
                    <Wallet className="w-10 h-10 text-muted-foreground/30 mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground">No hay cuentas registradas. Genera un cargo para crear la primera.</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {overview.accounts.map((a) => (
                      <div key={a.unit_id} data-testid={`account-${a.unit_id}`} className="p-3 rounded-lg bg-[#181B25] border border-[#1E293B]/50 flex items-center justify-between">
                        <div>
                          <span className="text-sm font-medium text-white">{a.unit_id}</span>
                          <Badge variant="outline" className={`ml-2 text-[10px] h-5 ${ACCT_COLORS[a.status] ? `${a.status === 'al_dia' ? 'bg-green-500/15 border-green-500/30' : a.status === 'atrasado' ? 'bg-red-500/15 border-red-500/30' : 'bg-blue-500/15 border-blue-500/30'} ${ACCT_COLORS[a.status]}` : ''}`}>
                            {ACCT_LABELS[a.status] || a.status}
                          </Badge>
                        </div>
                        <span className={`text-sm font-bold ${a.current_balance > 0 ? 'text-red-400' : a.current_balance < 0 ? 'text-blue-400' : 'text-green-400'}`}>
                          {a.current_balance > 0 ? `Debe: ${fmt(a.current_balance)}` : a.current_balance < 0 ? `A favor: ${fmt(Math.abs(a.current_balance))}` : 'Al día'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </>
        )}

        <CatalogDialog open={showCatalog} onClose={() => setShowCatalog(false)} onCreated={fetchData} />
        <ChargeDialog open={showCharge} onClose={() => setShowCharge(false)} onCreated={fetchData} catalog={catalog} />
        <PaymentDialog open={showPayment} onClose={() => setShowPayment(false)} onCreated={fetchData} />
        <BulkChargeDialog open={showBulk} onClose={() => setShowBulk(false)} onCreated={fetchData} catalog={catalog} />
      </div>
    </DashboardLayout>
  );
}
