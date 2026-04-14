import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import api from '../services/api';
import {
  DollarSign,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  Loader2,
  Receipt,
  Wallet,
} from 'lucide-react';

const STATUS_COLORS = {
  paid: 'bg-green-500/15 text-green-400 border-green-500/30',
  pending: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  overdue: 'bg-red-500/15 text-red-400 border-red-500/30',
  partial: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
};
const STATUS_LABELS = { paid: 'Pagado', pending: 'Pendiente', overdue: 'Vencido', partial: 'Parcial' };

function fmt(n) { return new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'USD' }).format(n); }

export default function FinanzasResident() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const unitId = user?.apartment || user?.id || '';

  const fetchData = useCallback(async () => {
    if (!unitId) return;
    setLoading(true);
    try {
      const result = await api.getUnitAccount(unitId);
      setData(result);
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

  const account = data?.account || { current_balance: 0, status: 'al_dia' };
  const breakdown = data?.breakdown || {};
  const records = data?.records || [];
  const balance = account.current_balance || 0;

  const statusConfig = {
    al_dia: { label: 'Al Día', icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/20' },
    atrasado: { label: 'Atrasado', icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' },
    adelantado: { label: 'Adelantado', icon: TrendingUp, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/20' },
  };
  const sc = statusConfig[account.status] || statusConfig.al_dia;
  const StatusIcon = sc.icon;

  return (
    <div className="h-full overflow-y-auto" style={{ WebkitOverflowScrolling: 'touch', paddingBottom: '112px' }}>
      <div className="p-3 space-y-4" data-testid="finanzas-resident">
        <h2 className="text-base font-semibold">{t('finanzas.myFinances', 'Mi Estado Financiero')}</h2>

        {/* Balance Card */}
        <Card className={`border ${sc.bg}`} data-testid="balance-card">
          <CardContent className="p-5 text-center">
            <StatusIcon className={`w-10 h-10 mx-auto mb-2 ${sc.color}`} />
            <p className={`text-3xl font-bold ${sc.color}`}>
              {balance > 0 ? fmt(balance) : balance < 0 ? fmt(Math.abs(balance)) : '$0.00'}
            </p>
            <p className={`text-sm mt-1 ${sc.color}`}>
              {balance > 0 ? 'Saldo pendiente' : balance < 0 ? 'Saldo a favor' : 'Sin saldo pendiente'}
            </p>
            <Badge variant="outline" className={`mt-2 ${sc.bg} ${sc.color}`}>
              {sc.label}
            </Badge>
          </CardContent>
        </Card>

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
                  <div className="text-right">
                    <span className={`text-sm font-medium ${vals.pending > 0 ? 'text-red-400' : vals.pending < 0 ? 'text-blue-400' : 'text-green-400'}`}>
                      {vals.pending > 0 ? `Debe: ${fmt(vals.pending)}` : vals.pending < 0 ? `A favor: ${fmt(Math.abs(vals.pending))}` : 'Al día'}
                    </span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Recent Records */}
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
    </div>
  );
}
