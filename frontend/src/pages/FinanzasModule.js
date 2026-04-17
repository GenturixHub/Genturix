import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '../components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import api from '../services/api';
import {
  DollarSign, Plus, CreditCard, AlertTriangle, CheckCircle, TrendingUp,
  Loader2, Filter, Wallet, Receipt, ArrowDownCircle, FileDown, FileSpreadsheet,
  Users, Settings, Save, Ban, Check, Building2, UserPlus, Trash2, X,
} from 'lucide-react';

const ACCT_COLORS = { al_dia: 'text-green-400', atrasado: 'text-red-400', adelantado: 'text-blue-400' };
const ACCT_LABELS = { al_dia: 'Al dia', atrasado: 'Atrasado', adelantado: 'Adelantado' };
const ACCT_BG = { al_dia: 'bg-green-500/15 border-green-500/30', atrasado: 'bg-red-500/15 border-red-500/30', adelantado: 'bg-blue-500/15 border-blue-500/30' };
function fmt(n) { return new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'USD' }).format(n); }

// ── Summary Cards ──
const SummaryCards = ({ summary }) => {
  if (!summary) return null;
  const cards = [
    { label: 'Total Cobrado', value: fmt(summary.global_due), color: 'text-white', icon: Receipt },
    { label: 'Total Pagado', value: fmt(summary.global_paid), color: 'text-green-400', icon: CheckCircle },
    { label: 'Balance Global', value: fmt(summary.global_balance), color: summary.global_balance > 0 ? 'text-red-400' : 'text-green-400', icon: DollarSign },
    { label: 'Al dia', value: summary.al_dia, color: 'text-green-400', icon: CheckCircle },
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

// ── Catalog Dialog ──
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

// ── Charge Dialog ──
const ChargeDialog = ({ open, onClose, onCreated, catalog, units = [] }) => {
  const [unitId, setUnitId] = useState('');
  const [chargeTypeId, setChargeTypeId] = useState('');
  const [period, setPeriod] = useState(() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; });
  const [amount, setAmount] = useState('');
  const [sending, setSending] = useState(false);
  const selectedCatalog = catalog.find(c => c.id === chargeTypeId);
  useEffect(() => { if (selectedCatalog && !amount) setAmount(String(selectedCatalog.default_amount)); }, [selectedCatalog, amount]);
  const handleSubmit = async () => {
    if (!unitId || !chargeTypeId || !period || !amount) return;
    setSending(true);
    try {
      await api.createCharge({ unit_id: unitId, charge_type_id: chargeTypeId, period, amount_due: parseFloat(amount) });
      toast.success('Cargo creado'); setUnitId(''); setChargeTypeId(''); setAmount(''); onCreated?.(); onClose();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setSending(false); }
  };
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md" data-testid="charge-dialog">
        <DialogHeader><DialogTitle>Generar Cargo Individual</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <Select value={unitId} onValueChange={setUnitId}>
            <SelectTrigger data-testid="charge-unit" className="bg-[#181B25] border-[#1E293B]"><SelectValue placeholder="Seleccionar unidad" /></SelectTrigger>
            <SelectContent className="bg-[#0F111A] border-[#1E293B] max-h-60">
              {units.map(u => (
                <SelectItem key={u.number} value={u.number}>
                  {u.number} {u.residents?.length > 0 ? `- ${u.residents[0].full_name}` : ''}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
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
          <Button onClick={handleSubmit} disabled={sending || !unitId || !chargeTypeId || !amount} data-testid="submit-charge" className="w-full">
            {sending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Receipt className="w-4 h-4 mr-2" />} Generar Cargo
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ── Register Payment Dialog (admin) ──
const PaymentDialog = ({ open, onClose, onCreated, prefillUnit, units = [] }) => {
  const [unitId, setUnitId] = useState(prefillUnit || '');
  const [amount, setAmount] = useState('');
  const [method, setMethod] = useState('efectivo');
  const [sending, setSending] = useState(false);
  useEffect(() => { if (prefillUnit) setUnitId(prefillUnit); }, [prefillUnit]);
  const handleSubmit = async () => {
    if (!unitId || !amount) return;
    setSending(true);
    try {
      const result = await api.registerPayment({ unit_id: unitId, amount: parseFloat(amount), payment_method: method });
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
          <Select value={unitId} onValueChange={setUnitId}>
            <SelectTrigger data-testid="payment-unit" className="bg-[#181B25] border-[#1E293B]"><SelectValue placeholder="Seleccionar unidad" /></SelectTrigger>
            <SelectContent className="bg-[#0F111A] border-[#1E293B] max-h-60">
              {units.map(u => (
                <SelectItem key={u.number} value={u.number}>
                  {u.number} {u.residents?.length > 0 ? `- ${u.residents[0].full_name}` : ''} {u.finance?.current_balance > 0 ? `(${fmt(u.finance.current_balance)})` : ''}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
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
          <Button onClick={handleSubmit} disabled={sending || !unitId || !amount} data-testid="submit-payment" className="w-full">
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
    setSending(true); setResult(null);
    try {
      const data = { charge_type_id: chargeTypeId, period };
      if (dueDate) data.due_date = dueDate;
      const res = await api.generateBulkCharges(data);
      setResult(res);
      toast.success(`${res.created_count} cargos generados`);
      onCreated?.();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setSending(false); }
  };
  const handleClose = () => { setResult(null); setChargeTypeId(''); onClose(); };
  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-md" data-testid="bulk-charge-dialog">
        <DialogHeader><DialogTitle>Cargos Masivos</DialogTitle></DialogHeader>
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
              <Input data-testid="bulk-due-date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} placeholder="Fecha vencimiento (opcional)" className="bg-[#181B25] border-[#1E293B]" />
              <Button onClick={handleSubmit} disabled={sending || !chargeTypeId} data-testid="submit-bulk" className="w-full">
                {sending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <ArrowDownCircle className="w-4 h-4 mr-2" />} Generar
              </Button>
            </>
          ) : (
            <div className="space-y-3 text-center" data-testid="bulk-result">
              <CheckCircle className="w-10 h-10 text-green-400 mx-auto" />
              <p className="text-lg font-bold">{result.created_count} creados, {result.skipped_count} omitidos</p>
              <p className="text-xs text-muted-foreground">{result.charge_type} - {result.period} - {fmt(result.amount)}</p>
              <Button variant="outline" onClick={handleClose} className="w-full">Cerrar</Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ── Payment Settings Dialog ──
const PaymentSettingsDialog = ({ open, onClose }) => {
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    api.getPaymentSettings().then(s => { setSettings(s || {}); setLoading(false); }).catch(() => setLoading(false));
  }, [open]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.updatePaymentSettings(settings);
      toast.success('Datos de pago actualizados');
      onClose();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setSaving(false); }
  };

  const update = (key, val) => setSettings(prev => ({ ...prev, [key]: val }));

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-lg" data-testid="payment-settings-dialog">
        <DialogHeader><DialogTitle>Datos de Pago (SINPE / Transferencia)</DialogTitle></DialogHeader>
        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin" /></div>
        ) : (
          <div className="space-y-4">
            <div>
              <p className="text-xs text-muted-foreground mb-2 font-medium">SINPE Movil</p>
              <div className="grid grid-cols-2 gap-3">
                <Input value={settings.sinpe_number || ''} onChange={(e) => update('sinpe_number', e.target.value)} placeholder="Numero SINPE" className="bg-[#181B25] border-[#1E293B]" data-testid="sinpe-number" />
                <Input value={settings.sinpe_name || ''} onChange={(e) => update('sinpe_name', e.target.value)} placeholder="Nombre titular" className="bg-[#181B25] border-[#1E293B]" data-testid="sinpe-name" />
              </div>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-2 font-medium">Transferencia Bancaria</p>
              <div className="space-y-2">
                <Input value={settings.bank_name || ''} onChange={(e) => update('bank_name', e.target.value)} placeholder="Nombre del banco" className="bg-[#181B25] border-[#1E293B]" data-testid="bank-name" />
                <Input value={settings.bank_account || ''} onChange={(e) => update('bank_account', e.target.value)} placeholder="Numero de cuenta" className="bg-[#181B25] border-[#1E293B]" data-testid="bank-account" />
                <Input value={settings.bank_iban || ''} onChange={(e) => update('bank_iban', e.target.value)} placeholder="IBAN" className="bg-[#181B25] border-[#1E293B]" data-testid="bank-iban" />
              </div>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-2 font-medium">Instrucciones adicionales</p>
              <textarea value={settings.additional_instructions || ''} onChange={(e) => update('additional_instructions', e.target.value)} placeholder="Ej: Incluir numero de unidad como referencia" rows={2} className="w-full rounded-md bg-[#181B25] border border-[#1E293B] text-sm px-3 py-2 text-white placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none" data-testid="payment-instructions" />
            </div>
            <Button onClick={handleSave} disabled={saving} className="w-full" data-testid="save-payment-settings">
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Save className="w-4 h-4 mr-2" />} Guardar
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

// ── Payment Requests Panel (admin reviews resident payments) ──
const PaymentRequestsPanel = () => {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(null);

  const fetchRequests = useCallback(async () => {
    try {
      const data = await api.getPaymentRequests('pending');
      setRequests(data.items || []);
    } catch { setRequests([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchRequests(); }, [fetchRequests]);

  const handleReview = async (id, action) => {
    setProcessing(id);
    try {
      await api.reviewPaymentRequest(id, action);
      toast.success(action === 'approved' ? 'Pago aprobado y registrado' : 'Pago rechazado');
      fetchRequests();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setProcessing(null); }
  };

  if (loading) return null;
  if (requests.length === 0) return null;

  return (
    <Card className="bg-[#0F111A] border-[#1E293B] border-orange-500/30" data-testid="payment-requests-panel">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <CreditCard className="w-4 h-4 text-orange-400" />
          Comprobantes de Pago Pendientes ({requests.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {requests.map(pr => (
          <div key={pr.id} className="p-3 rounded-lg bg-[#181B25] border border-orange-500/20 flex items-center gap-3" data-testid={`pr-${pr.id}`}>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white">{pr.resident_name} - {pr.unit_id}</p>
              <p className="text-xs text-muted-foreground">{fmt(pr.amount)} via {pr.payment_method} {pr.reference ? `| Ref: ${pr.reference}` : ''}</p>
              {pr.notes && <p className="text-xs text-muted-foreground mt-0.5">{pr.notes}</p>}
            </div>
            <div className="flex gap-1 flex-shrink-0">
              <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-green-400 hover:text-green-300 hover:bg-green-500/10" onClick={() => handleReview(pr.id, 'approved')} disabled={processing === pr.id} data-testid={`approve-${pr.id}`}>
                {processing === pr.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              </Button>
              <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-red-400 hover:text-red-300 hover:bg-red-500/10" onClick={() => handleReview(pr.id, 'rejected')} disabled={processing === pr.id} data-testid={`reject-${pr.id}`}>
                <Ban className="w-4 h-4" />
              </Button>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};

// ── Units Management Panel ──
const UnitsPanel = ({ onRefresh }) => {
  const [units, setUnits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showAssign, setShowAssign] = useState(null); // unit to assign to
  const [newNumber, setNewNumber] = useState('');
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [users, setUsers] = useState([]);
  const [assignUserId, setAssignUserId] = useState('');
  const [assigning, setAssigning] = useState(false);

  const fetchUnits = useCallback(async () => {
    try {
      const data = await api.getUnits();
      setUnits(data.items || []);
    } catch { setUnits([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchUnits(); }, [fetchUnits]);

  const handleCreate = async () => {
    if (!newNumber.trim()) return;
    setCreating(true);
    try {
      await api.createUnit({ number: newNumber.trim() });
      toast.success(`Unidad ${newNumber.trim()} creada`);
      setNewNumber('');
      setShowCreate(false);
      fetchUnits();
      onRefresh?.();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setCreating(false); }
  };

  const handleDelete = async (unit) => {
    const hasFinance = unit.finance?.current_balance !== 0;
    const msg = hasFinance
      ? `La unidad ${unit.number} tiene registros financieros. Eliminar de todas formas?`
      : `Eliminar unidad ${unit.number}?`;
    if (!window.confirm(msg)) return;
    setDeleting(unit.id);
    try {
      await api.deleteUnit(unit.id, hasFinance);
      toast.success('Unidad eliminada');
      fetchUnits();
      onRefresh?.();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setDeleting(null); }
  };

  const openAssign = async (unit) => {
    setShowAssign(unit);
    setAssignUserId('');
    try {
      const resp = await api.get('/admin/users?page_size=200');
      const allUsers = Array.isArray(resp) ? resp : (resp.users || resp.items || []);
      const unitResidentIds = (unit.residents || []).map(r => r.id);
      setUsers(allUsers.filter(u => !unitResidentIds.includes(u.id)));
    } catch { setUsers([]); }
  };

  const handleAssign = async () => {
    if (!assignUserId || !showAssign) return;
    setAssigning(true);
    try {
      await api.assignUserToUnit(showAssign.id, assignUserId);
      toast.success('Usuario asignado a la unidad');
      setShowAssign(null);
      fetchUnits();
      onRefresh?.();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setAssigning(false); }
  };

  const handleUnassign = async (unit, userId) => {
    try {
      await api.unassignUserFromUnit(unit.id, userId);
      toast.success('Usuario desvinculado');
      fetchUnits();
      onRefresh?.();
    } catch (err) { toast.error(err.message || 'Error'); }
  };

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]" data-testid="units-panel">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Building2 className="w-4 h-4 text-primary" /> Unidades
          </CardTitle>
          <Button size="sm" onClick={() => setShowCreate(true)} data-testid="btn-create-unit">
            <Plus className="w-4 h-4 mr-1" /> Nueva Unidad
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex justify-center py-6"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
        ) : units.length === 0 ? (
          <div className="text-center py-6">
            <Building2 className="w-10 h-10 text-muted-foreground/30 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No hay unidades. Crea la primera.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {units.map(unit => (
              <div key={unit.id} data-testid={`unit-${unit.number}`} className="p-3 rounded-lg bg-[#181B25] border border-[#1E293B]/50">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-white">{unit.number}</span>
                    <Badge variant="outline" className={`text-[10px] h-5 ${
                      unit.finance?.status === 'al_dia' ? 'bg-green-500/15 border-green-500/30 text-green-400' :
                      unit.finance?.status === 'atrasado' ? 'bg-red-500/15 border-red-500/30 text-red-400' :
                      'bg-blue-500/15 border-blue-500/30 text-blue-400'
                    }`}>
                      {unit.finance?.current_balance > 0 ? fmt(unit.finance.current_balance) : 'Al dia'}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => openAssign(unit)} data-testid={`assign-${unit.number}`}>
                      <UserPlus className="w-3.5 h-3.5" />
                    </Button>
                    <Button size="sm" variant="ghost" className="h-7 w-7 p-0 text-red-400 hover:text-red-300" onClick={() => handleDelete(unit)} disabled={deleting === unit.id} data-testid={`delete-unit-${unit.number}`}>
                      {deleting === unit.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                    </Button>
                  </div>
                </div>
                {/* Residents */}
                {unit.residents?.length > 0 ? (
                  <div className="space-y-1">
                    {unit.residents.map(r => (
                      <div key={r.id} className="flex items-center justify-between px-2 py-1.5 rounded bg-[#0F111A]">
                        <div className="min-w-0">
                          <p className="text-xs text-white truncate">{r.full_name}</p>
                          <p className="text-[10px] text-muted-foreground truncate">{r.email}</p>
                        </div>
                        <button onClick={() => handleUnassign(unit, r.id)} className="p-1 text-muted-foreground hover:text-red-400 transition-colors flex-shrink-0" data-testid={`unassign-${r.id}`}>
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[10px] text-muted-foreground/50 px-2">Sin residentes asignados</p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Create Unit Dialog */}
        <Dialog open={showCreate} onOpenChange={(v) => !v && setShowCreate(false)}>
          <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-sm" data-testid="create-unit-dialog">
            <DialogHeader><DialogTitle>Nueva Unidad</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Input value={newNumber} onChange={(e) => setNewNumber(e.target.value)} placeholder="Numero (ej: A-101)" className="bg-[#181B25] border-[#1E293B]" data-testid="unit-number-input" maxLength={50} />
              <Button onClick={handleCreate} disabled={creating || !newNumber.trim()} className="w-full" data-testid="submit-create-unit">
                {creating ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />} Crear Unidad
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Assign User Dialog */}
        <Dialog open={!!showAssign} onOpenChange={(v) => !v && setShowAssign(null)}>
          <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-sm" data-testid="assign-user-dialog">
            <DialogHeader><DialogTitle>Asignar Usuario a {showAssign?.number}</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <Select value={assignUserId} onValueChange={setAssignUserId}>
                <SelectTrigger className="bg-[#181B25] border-[#1E293B]" data-testid="assign-user-select"><SelectValue placeholder="Seleccionar usuario" /></SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B] max-h-60">
                  {users.map(u => (
                    <SelectItem key={u.id} value={u.id}>{u.full_name} ({u.email})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button onClick={handleAssign} disabled={assigning || !assignUserId} className="w-full" data-testid="submit-assign-user">
                {assigning ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <UserPlus className="w-4 h-4 mr-2" />} Asignar
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
};

// ── Resident Accounts Tab ──
const ResidentAccountsTab = () => {
  const [residents, setResidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedResident, setSelectedResident] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [exportingId, setExportingId] = useState(null);

  const fetchResidents = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getResidentAccounts(search, statusFilter);
      setResidents(data.items || []);
    } catch { setResidents([]); }
    finally { setLoading(false); }
  }, [search, statusFilter]);

  useEffect(() => { fetchResidents(); }, [fetchResidents]);

  const openDetail = async (r) => {
    setSelectedResident(r);
    setDetailLoading(true);
    try {
      const d = await api.getResidentAccountDetail(r.id);
      setDetail(d);
    } catch (err) { toast.error(err.message || 'Error'); setDetail(null); }
    finally { setDetailLoading(false); }
  };

  const handleExport = async (userId, format, userName) => {
    setExportingId(`${userId}-${format}`);
    try {
      await api.exportResidentStatement(userId, format, userName);
      toast.success(format === 'pdf' ? 'PDF descargado' : 'CSV descargado');
    } catch (err) { toast.error(err.message || 'Error al exportar'); }
    finally { setExportingId(null); }
  };

  const STATUS_CFG = {
    al_dia: { label: 'Al dia', color: 'text-green-400', bg: 'bg-green-500/15 border-green-500/30' },
    atrasado: { label: 'Atrasado', color: 'text-red-400', bg: 'bg-red-500/15 border-red-500/30' },
    adelantado: { label: 'Adelantado', color: 'text-blue-400', bg: 'bg-blue-500/15 border-blue-500/30' },
  };
  const REC_STATUS = {
    paid: { label: 'Pagado', bg: 'bg-green-500/15 text-green-400 border-green-500/30' },
    pending: { label: 'Pendiente', bg: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30' },
    overdue: { label: 'Vencido', bg: 'bg-red-500/15 text-red-400 border-red-500/30' },
    partial: { label: 'Parcial', bg: 'bg-blue-500/15 text-blue-400 border-blue-500/30' },
  };
  const PAY_STATUS = {
    pending: { label: 'Pendiente', bg: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30' },
    approved: { label: 'Aprobado', bg: 'bg-green-500/15 text-green-400 border-green-500/30' },
    rejected: { label: 'Rechazado', bg: 'bg-red-500/15 text-red-400 border-red-500/30' },
  };

  return (
    <div className="space-y-4" data-testid="resident-accounts-tab">
      {/* Search & Filters */}
      <div className="flex flex-wrap gap-2 items-center">
        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar por nombre, email o unidad..." className="bg-[#181B25] border-[#1E293B] max-w-xs" data-testid="resident-search" />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="bg-[#181B25] border-[#1E293B] w-40" data-testid="status-filter"><SelectValue /></SelectTrigger>
          <SelectContent className="bg-[#0F111A] border-[#1E293B]">
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="atrasado">Atrasados</SelectItem>
            <SelectItem value="al_dia">Al dia</SelectItem>
            <SelectItem value="adelantado">Adelantados</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground ml-2">{residents.length} residentes</span>
      </div>

      {/* List */}
      {loading ? (
        <div className="flex justify-center py-10"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
      ) : residents.length === 0 ? (
        <div className="text-center py-10">
          <Users className="w-10 h-10 text-muted-foreground/30 mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">No se encontraron residentes</p>
        </div>
      ) : (
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-0">
            {/* Header */}
            <div className="hidden sm:grid sm:grid-cols-[1.5fr_1fr_100px_120px_120px] gap-3 px-4 py-2.5 text-xs text-muted-foreground font-medium border-b border-[#1E293B]/50">
              <span>Residente</span>
              <span>Unidad</span>
              <span>Estado</span>
              <span className="text-right">Balance</span>
              <span className="text-right">Accion</span>
            </div>
            <div className="divide-y divide-[#1E293B]/30">
              {residents.map((r) => {
                const sc = STATUS_CFG[r.status] || STATUS_CFG.al_dia;
                return (
                  <div key={r.id} data-testid={`resident-row-${r.id}`} className="px-4 py-3 sm:grid sm:grid-cols-[1.5fr_1fr_100px_120px_120px] sm:items-center gap-3 hover:bg-white/[0.02] transition-colors">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white truncate">{r.full_name}</p>
                      <p className="text-[10px] text-muted-foreground truncate">{r.email}</p>
                    </div>
                    <div className="mt-1 sm:mt-0">
                      <span className="text-sm text-white">{r.unit || <span className="text-muted-foreground/50 text-xs">Sin unidad</span>}</span>
                    </div>
                    <div className="mt-1 sm:mt-0">
                      <Badge variant="outline" className={`text-[10px] h-5 ${sc.bg}`}>{sc.label}</Badge>
                    </div>
                    <div className="mt-1 sm:mt-0 text-right">
                      <span className={`text-sm font-bold ${r.balance > 0 ? 'text-red-400' : r.balance < 0 ? 'text-blue-400' : 'text-green-400'}`}>
                        {r.balance !== 0 ? fmt(Math.abs(r.balance)) : '$0.00'}
                      </span>
                    </div>
                    <div className="mt-2 sm:mt-0 flex justify-end">
                      <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => openDetail(r)} data-testid={`detail-${r.id}`}>
                        Ver detalle
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Detail Dialog */}
      <Dialog open={!!selectedResident} onOpenChange={(v) => !v && setSelectedResident(null)}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="resident-detail-dialog">
          {detailLoading ? (
            <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 animate-spin" /></div>
          ) : detail ? (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-3">
                  <span>{detail.user.full_name}</span>
                  <Badge variant="outline" className={`text-xs ${(STATUS_CFG[detail.status] || {}).bg}`}>
                    {(STATUS_CFG[detail.status] || {}).label}
                  </Badge>
                </DialogTitle>
              </DialogHeader>
              {/* Summary */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                <div className="p-3 rounded-lg bg-[#181B25]">
                  <p className="text-[10px] text-muted-foreground">Unidad</p>
                  <p className="text-sm font-bold text-white">{detail.unit || 'Sin asignar'}</p>
                </div>
                <div className="p-3 rounded-lg bg-[#181B25]">
                  <p className="text-[10px] text-muted-foreground">Total Cobrado</p>
                  <p className="text-sm font-bold text-white">{fmt(detail.total_due)}</p>
                </div>
                <div className="p-3 rounded-lg bg-[#181B25]">
                  <p className="text-[10px] text-muted-foreground">Total Pagado</p>
                  <p className="text-sm font-bold text-green-400">{fmt(detail.total_paid)}</p>
                </div>
                <div className="p-3 rounded-lg bg-[#181B25]">
                  <p className="text-[10px] text-muted-foreground">Balance</p>
                  <p className={`text-sm font-bold ${detail.balance > 0 ? 'text-red-400' : detail.balance < 0 ? 'text-blue-400' : 'text-green-400'}`}>
                    {detail.balance !== 0 ? fmt(Math.abs(detail.balance)) : '$0.00'}
                  </p>
                </div>
              </div>
              {/* Export Buttons */}
              <div className="flex gap-2 mb-4">
                <Button size="sm" variant="outline" onClick={() => handleExport(detail.user.id, 'pdf', detail.user.full_name)} disabled={!!exportingId} data-testid="export-pdf-btn">
                  {exportingId === `${detail.user.id}-pdf` ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <FileDown className="w-3 h-3 mr-1" />} PDF
                </Button>
                <Button size="sm" variant="outline" onClick={() => handleExport(detail.user.id, 'csv', detail.user.full_name)} disabled={!!exportingId} data-testid="export-csv-btn">
                  {exportingId === `${detail.user.id}-csv` ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <FileSpreadsheet className="w-3 h-3 mr-1" />} CSV
                </Button>
              </div>
              {/* Charges */}
              <div className="mb-4">
                <h4 className="text-sm font-medium text-white mb-2 flex items-center gap-2"><Receipt className="w-4 h-4 text-primary" /> Cargos ({detail.charges.length})</h4>
                {detail.charges.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-3 text-center">Sin cargos registrados</p>
                ) : (
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {detail.charges.map((c) => {
                      const rs = REC_STATUS[c.status] || {};
                      return (
                        <div key={c.id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#181B25]" data-testid={`charge-${c.id}`}>
                          <div className="min-w-0 flex-1">
                            <p className="text-xs text-white">{c.type} <span className="text-muted-foreground">({c.period})</span></p>
                            <p className="text-[10px] text-muted-foreground">{c.date?.slice(0, 10)}</p>
                          </div>
                          <div className="text-right ml-3 flex items-center gap-2">
                            <div>
                              <p className="text-xs font-medium text-white">{fmt(c.amount_due)}</p>
                              <Badge variant="outline" className={`text-[9px] h-4 ${rs.bg || ''}`}>{rs.label || c.status}</Badge>
                            </div>
                            {c.id && (
                              <button
                                onClick={async () => {
                                  if (!window.confirm(`Eliminar cargo ${c.type} (${c.period}) por ${fmt(c.amount_due)}?`)) return;
                                  try {
                                    await api.deleteCharge(c.id);
                                    toast.success('Cargo eliminado');
                                    openDetail(selectedResident);
                                  } catch (err) { toast.error(err.message || 'Error'); }
                                }}
                                className="p-1 text-muted-foreground/50 hover:text-red-400 transition-colors"
                                data-testid={`delete-charge-${c.id}`}
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
              {/* Payments */}
              {detail.payments.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-white mb-2 flex items-center gap-2"><CreditCard className="w-4 h-4 text-green-400" /> Comprobantes ({detail.payments.length})</h4>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {detail.payments.map((p) => {
                      const ps = PAY_STATUS[p.status] || {};
                      return (
                        <div key={p.id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#181B25]" data-testid={`payment-${p.id}`}>
                          <div className="min-w-0 flex-1">
                            <p className="text-xs text-white">{p.method} {p.reference ? `| Ref: ${p.reference}` : ''}</p>
                            <p className="text-[10px] text-muted-foreground">{p.date?.slice(0, 10)}</p>
                          </div>
                          <div className="text-right ml-3">
                            <p className="text-xs font-medium text-green-400">{fmt(p.amount)}</p>
                            <Badge variant="outline" className={`text-[9px] h-4 ${ps.bg || ''}`}>{ps.label || p.status}</Badge>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-6">No se pudo cargar el detalle</p>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

// ── Main Page ──
export default function FinanzasModule() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('overview');
  const [overview, setOverview] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [units, setUnits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCatalog, setShowCatalog] = useState(false);
  const [showCharge, setShowCharge] = useState(false);
  const [showPayment, setShowPayment] = useState(false);
  const [showBulk, setShowBulk] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [exporting, setExporting] = useState(null);
  const [prefillUnit, setPrefillUnit] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, cat, unitData] = await Promise.all([
        api.getFinanzasOverview(),
        api.getChargeCatalog(),
        api.getUnits(),
      ]);
      setOverview(ov);
      setCatalog(cat || []);
      setUnits(unitData?.items || []);
    } catch { /* empty state */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleExport = async (f) => {
    setExporting(f);
    try {
      await api.downloadFinancialReport(f);
      toast.success(f === 'pdf' ? 'PDF descargado' : 'CSV descargado');
    } catch (err) { toast.error(err.message || 'Error al exportar'); }
    finally { setExporting(null); }
  };

  const openPaymentFor = (unitId) => {
    setPrefillUnit(unitId);
    setShowPayment(true);
  };

  return (
    <DashboardLayout title={t('finanzas.pageTitle', 'Finanzas')}>
      <div data-testid="finanzas-module" className="space-y-6">
        {/* Tab Navigation */}
        <div className="flex gap-1 p-1 bg-[#0F111A] rounded-lg border border-[#1E293B] w-fit" data-testid="finanzas-tabs">
          <button onClick={() => setActiveTab('overview')} className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'overview' ? 'bg-primary text-white' : 'text-muted-foreground hover:text-white hover:bg-white/5'}`} data-testid="tab-overview">
            <Wallet className="w-4 h-4 inline mr-1.5 -mt-0.5" />Resumen
          </button>
          <button onClick={() => setActiveTab('residents')} className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'residents' ? 'bg-primary text-white' : 'text-muted-foreground hover:text-white hover:bg-white/5'}`} data-testid="tab-residents">
            <Users className="w-4 h-4 inline mr-1.5 -mt-0.5" />Estados de Cuenta
          </button>
        </div>

        {activeTab === 'residents' ? (
          <ResidentAccountsTab />
        ) : (
        <>
        {loading ? (
          <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
        ) : (
          <>
            <SummaryCards summary={overview?.summary} />

            {/* Pending Payment Requests */}
            <PaymentRequestsPanel />

            {/* Units Management */}
            <UnitsPanel onRefresh={fetchData} />

            {/* Actions */}
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={() => setShowCatalog(true)} data-testid="btn-new-catalog">
                <Plus className="w-4 h-4 mr-1" /> Tipo de Cargo
              </Button>
              <Button size="sm" variant="outline" onClick={() => { setPrefillUnit(''); setShowCharge(true); }} data-testid="btn-new-charge" disabled={catalog.length === 0}>
                <Receipt className="w-4 h-4 mr-1" /> Generar Cargo
              </Button>
              <Button size="sm" variant="outline" onClick={() => setShowBulk(true)} data-testid="btn-bulk-charge" disabled={catalog.length === 0}>
                <ArrowDownCircle className="w-4 h-4 mr-1" /> Cargos Masivos
              </Button>
              <Button size="sm" onClick={() => { setPrefillUnit(''); setShowPayment(true); }} data-testid="btn-new-payment">
                <CreditCard className="w-4 h-4 mr-1" /> Registrar Pago
              </Button>
              <Button size="sm" variant="outline" onClick={() => setShowSettings(true)} data-testid="btn-payment-settings">
                <Settings className="w-4 h-4 mr-1" /> Datos de Pago
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

            {/* Accounts Table - Enhanced with resident info */}
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
                  <>
                    {/* Table Header */}
                    <div className="hidden sm:grid sm:grid-cols-[1fr_1.5fr_100px_120px_100px] gap-3 px-3 pb-2 text-xs text-muted-foreground font-medium border-b border-[#1E293B]/50 mb-2">
                      <span>Unidad</span>
                      <span>Residente</span>
                      <span>Estado</span>
                      <span className="text-right">Deuda</span>
                      <span className="text-right">Accion</span>
                    </div>
                    <div className="space-y-1.5">
                      {overview.accounts.map((a) => (
                        <div key={a.unit_id} data-testid={`account-${a.unit_id}`} className="p-3 rounded-lg bg-[#181B25] border border-[#1E293B]/50 sm:grid sm:grid-cols-[1fr_1.5fr_100px_120px_100px] sm:items-center gap-3">
                          {/* Unit */}
                          <div>
                            <span className="text-sm font-bold text-white">{a.unit_id}</span>
                          </div>
                          {/* Resident */}
                          <div className="mt-1 sm:mt-0">
                            {a.resident_name ? (
                              <div>
                                <p className="text-sm text-white truncate">{a.resident_name}</p>
                                <p className="text-[10px] text-muted-foreground truncate">{a.resident_email}</p>
                              </div>
                            ) : (
                              <span className="text-xs text-muted-foreground/50">Sin residente asignado</span>
                            )}
                          </div>
                          {/* Status */}
                          <div className="mt-1 sm:mt-0">
                            <Badge variant="outline" className={`text-[10px] h-5 ${ACCT_BG[a.status] || ''} ${ACCT_COLORS[a.status] || ''}`}>
                              {ACCT_LABELS[a.status] || a.status}
                            </Badge>
                          </div>
                          {/* Balance */}
                          <div className="mt-1 sm:mt-0 text-right">
                            <span className={`text-sm font-bold ${a.current_balance > 0 ? 'text-red-400' : a.current_balance < 0 ? 'text-blue-400' : 'text-green-400'}`}>
                              {a.current_balance > 0 ? fmt(a.current_balance) : a.current_balance < 0 ? `-${fmt(Math.abs(a.current_balance))}` : '$0.00'}
                            </span>
                          </div>
                          {/* Action */}
                          <div className="mt-2 sm:mt-0 flex justify-end">
                            <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => openPaymentFor(a.unit_id)} data-testid={`pay-${a.unit_id}`}>
                              <CreditCard className="w-3 h-3 mr-1" /> Pago
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </>
        )}
        </>
        )}

        <CatalogDialog open={showCatalog} onClose={() => setShowCatalog(false)} onCreated={fetchData} />
        <ChargeDialog open={showCharge} onClose={() => setShowCharge(false)} onCreated={fetchData} catalog={catalog} units={units} />
        <PaymentDialog open={showPayment} onClose={() => { setShowPayment(false); setPrefillUnit(''); }} onCreated={fetchData} prefillUnit={prefillUnit} units={units} />
        <BulkChargeDialog open={showBulk} onClose={() => setShowBulk(false)} onCreated={fetchData} catalog={catalog} />
        <PaymentSettingsDialog open={showSettings} onClose={() => setShowSettings(false)} />
      </div>
    </DashboardLayout>
  );
}
