/**
 * GENTURIX — Home Dashboard (Resident)
 * Engagement-driven dashboard: Finance summary, Smart alerts, Quick actions, Recent activity, FAB.
 */
import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import {
  ClipboardList, Wallet, FolderOpen, Landmark,
  CheckCircle, AlertTriangle, Loader2, ChevronRight,
  Globe, Lock, Plus, Users, Calendar, DollarSign,
  BellRing, CreditCard, Gavel, Clock,
} from 'lucide-react';

const GLASS = 'rgba(255,255,255,0.03)';
const BORDER = 'rgba(255,255,255,0.08)';

const fmt = (n) => new Intl.NumberFormat('es-CR', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n || 0);

export default function HomeDashboard({ onNavigate }) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [cases, setCases] = useState([]);
  const [finance, setFinance] = useState(null);
  const [assemblies, setAssemblies] = useState([]);
  const [showFab, setShowFab] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const apartment = user?.apartment || user?.role_data?.apartment_number;

        const promises = [
          api.getCasos(1, 5).catch(() => ({ items: [] })),
          api.get('/asamblea').catch(() => []),
        ];

        if (apartment) {
          promises.push(api.getUnitAccount(apartment).catch(() => null));
        }

        const results = await Promise.all(promises);
        setCases(results[0]?.items || []);

        const asmData = results[1];
        setAssemblies(Array.isArray(asmData) ? asmData : asmData?.items || []);

        if (apartment && results[2]) {
          setFinance(results[2]);
        }
      } catch { /* graceful degradation */ }
      finally { setLoading(false); }
    };
    load();
  }, [user]);

  // Computed values
  const openCases = useMemo(() => cases.filter(c => c.status === 'open').length, [cases]);
  const balance = finance?.account?.current_balance ?? null;
  const accountStatus = finance?.account?.status || null;
  const activeAssemblies = useMemo(() => assemblies.filter(a => a.status === 'scheduled' || a.status === 'in_progress'), [assemblies]);

  // Smart alerts
  const alerts = useMemo(() => {
    const list = [];
    if (balance !== null && balance > 0) {
      list.push({ id: 'finance', icon: DollarSign, text: `Saldo pendiente: ${fmt(balance)}`, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20', tab: 'finanzas' });
    }
    if (openCases > 0) {
      list.push({ id: 'cases', icon: ClipboardList, text: `${openCases} caso${openCases > 1 ? 's' : ''} abierto${openCases > 1 ? 's' : ''}`, color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/20', tab: 'casos' });
    }
    if (activeAssemblies.length > 0) {
      list.push({ id: 'assembly', icon: Gavel, text: `Asamblea: ${activeAssemblies[0].title}`, color: 'text-violet-400', bg: 'bg-violet-500/10 border-violet-500/20', tab: 'asamblea' });
    }
    return list;
  }, [balance, openCases, activeAssemblies]);

  const quickActions = [
    { id: 'casos', label: 'Casos', icon: ClipboardList, color: 'from-orange-500/20 to-orange-600/5', iconColor: 'text-orange-400', border: 'border-orange-500/20' },
    { id: 'finanzas', label: 'Finanzas', icon: Wallet, color: 'from-emerald-500/20 to-emerald-600/5', iconColor: 'text-emerald-400', border: 'border-emerald-500/20' },
    { id: 'documentos', label: 'Documentos', icon: FolderOpen, color: 'from-cyan-500/20 to-cyan-600/5', iconColor: 'text-cyan-400', border: 'border-cyan-500/20' },
    { id: 'asamblea', label: 'Asamblea', icon: Landmark, color: 'from-violet-500/20 to-violet-600/5', iconColor: 'text-violet-400', border: 'border-violet-500/20' },
  ];

  const STATUS_COLORS = {
    open: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
    in_progress: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
    closed: 'bg-slate-500/15 text-slate-400 border-slate-500/30',
  };
  const STATUS_LABELS = { open: 'Abierto', in_progress: 'En proceso', closed: 'Cerrado' };

  if (loading) {
    return (
      <div className="space-y-4 py-2" data-testid="home-dashboard">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-24 rounded-2xl animate-pulse" style={{ background: GLASS, border: `1px solid ${BORDER}` }} />
        ))}
      </div>
    );
  }

  const hasAlerts = alerts.length > 0;

  return (
    <div className="space-y-5 relative" data-testid="home-dashboard">

      {/* ══ 1. Financial Summary Card ══ */}
      {balance !== null && (
        <button
          onClick={() => onNavigate('finanzas')}
          className="w-full text-left rounded-3xl p-5 transition-all active:scale-[0.98]"
          style={{
            background: balance > 0
              ? 'linear-gradient(135deg, rgba(239,68,68,0.12) 0%, rgba(17,20,29,1) 60%)'
              : 'linear-gradient(135deg, rgba(34,197,94,0.12) 0%, rgba(17,20,29,1) 60%)',
            border: `1px solid ${balance > 0 ? 'rgba(239,68,68,0.15)' : 'rgba(34,197,94,0.15)'}`,
          }}
          data-testid="finance-card"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${balance > 0 ? 'bg-red-500/15' : 'bg-green-500/15'}`}>
                <CreditCard className={`w-6 h-6 ${balance > 0 ? 'text-red-400' : 'text-green-400'}`} strokeWidth={1.5} />
              </div>
              <div>
                <p className="text-[11px] text-slate-500 uppercase tracking-wider mb-0.5">Estado de Cuenta</p>
                <p className="text-xl font-bold text-white tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>
                  {fmt(balance)}
                </p>
              </div>
            </div>
            <div className="text-right flex flex-col items-end gap-2">
              <Badge className={`text-[10px] h-5 ${balance > 0 ? 'bg-red-500/15 text-red-400 border-red-500/30' : 'bg-green-500/15 text-green-400 border-green-500/30'}`}>
                {balance > 0 ? 'Atrasado' : 'Al dia'}
              </Badge>
              {balance > 0 && (
                <span className="text-[10px] text-cyan-400 font-medium flex items-center gap-0.5">
                  Pagar ahora <ChevronRight className="w-3 h-3" />
                </span>
              )}
            </div>
          </div>
        </button>
      )}

      {/* ══ 2. Smart Alerts ══ */}
      {hasAlerts ? (
        <div
          className="rounded-3xl p-4 space-y-2"
          style={{ background: GLASS, border: `1px solid ${BORDER}` }}
          data-testid="smart-alerts"
        >
          <div className="flex items-center gap-2 mb-1">
            <BellRing className="w-4 h-4 text-yellow-400" strokeWidth={1.5} />
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-[0.2em]">Atenci&oacute;n</p>
          </div>
          {alerts.map((alert) => {
            const Icon = alert.icon;
            return (
              <button
                key={alert.id}
                onClick={() => onNavigate(alert.tab)}
                className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all active:scale-[0.98] ${alert.bg}`}
                data-testid={`alert-${alert.id}`}
              >
                <Icon className={`w-4 h-4 flex-shrink-0 ${alert.color}`} strokeWidth={1.5} />
                <span className="text-sm text-white flex-1 text-left truncate">{alert.text}</span>
                <ChevronRight className="w-4 h-4 text-slate-600 flex-shrink-0" />
              </button>
            );
          })}
        </div>
      ) : (
        <div
          className="rounded-3xl p-5"
          style={{
            background: 'linear-gradient(135deg, rgba(6,182,212,0.12) 0%, rgba(17,20,29,1) 60%)',
            border: '1px solid rgba(6,182,212,0.15)',
          }}
          data-testid="status-card"
        >
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center bg-cyan-500/15">
              <CheckCircle className="w-7 h-7 text-cyan-400" strokeWidth={1.5} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>Todo en orden</h2>
              <p className="text-sm text-slate-400">No hay incidencias activas</p>
            </div>
          </div>
        </div>
      )}

      {/* ══ 3. Quick Actions Grid ══ */}
      <div>
        <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-[0.2em] mb-3 px-1">Acceso rapido</p>
        <div className="grid grid-cols-2 gap-3">
          {quickActions.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.id}
                onClick={() => onNavigate(action.id)}
                data-testid={`quick-${action.id}`}
                className={`p-4 rounded-2xl border bg-gradient-to-br ${action.color} ${action.border} text-left transition-all active:scale-[0.97] hover:brightness-110`}
              >
                <Icon className={`w-6 h-6 ${action.iconColor} mb-3`} strokeWidth={1.5} />
                <span className="text-sm font-semibold text-white">{action.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ══ 4. Recent Activity ══ */}
      <div>
        <div className="flex items-center justify-between mb-3 px-1">
          <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-[0.2em]">Actividad reciente</p>
          <button onClick={() => onNavigate('casos')} className="text-[11px] text-cyan-400 font-medium flex items-center gap-0.5 hover:text-cyan-300">
            Ver todos <ChevronRight className="w-3 h-3" />
          </button>
        </div>
        {cases.length === 0 ? (
          <div className="text-center py-8 rounded-2xl" style={{ background: GLASS, border: `1px solid ${BORDER}` }}>
            <ClipboardList className="w-8 h-8 text-slate-700 mx-auto mb-2" />
            <p className="text-sm text-slate-500">Sin actividad reciente</p>
          </div>
        ) : (
          <div className="space-y-2">
            {cases.slice(0, 4).map((c) => {
              const sc = STATUS_COLORS[c.status] || STATUS_COLORS.open;
              return (
                <button
                  key={c.id}
                  onClick={() => onNavigate('casos')}
                  className="w-full p-3.5 rounded-2xl text-left transition-all active:scale-[0.98]"
                  style={{ background: GLASS, border: `1px solid ${BORDER}` }}
                  data-testid={`recent-${c.id}`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <p className="text-sm font-medium text-white truncate">{c.title}</p>
                    <Badge variant="outline" className={`text-[9px] h-5 flex-shrink-0 ${sc}`}>
                      {STATUS_LABELS[c.status] || c.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-slate-500">
                    {c.visibility === 'community' ? (
                      <span className="flex items-center gap-0.5"><Globe className="w-2.5 h-2.5" />Comunitario</span>
                    ) : (
                      <span className="flex items-center gap-0.5"><Lock className="w-2.5 h-2.5" />Privado</span>
                    )}
                    <span>{new Date(c.created_at).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })}</span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ══ 5. FAB (Floating Action Button) ══ */}
      <button
        onClick={() => setShowFab(true)}
        className="fixed bottom-24 right-5 w-14 h-14 rounded-full bg-cyan-500 text-white shadow-lg shadow-cyan-500/25 flex items-center justify-center z-50 transition-all active:scale-90 hover:bg-cyan-400"
        data-testid="fab-button"
      >
        <Plus className="w-6 h-6" strokeWidth={2} />
      </button>

      {/* FAB Actions Sheet */}
      <Dialog open={showFab} onOpenChange={setShowFab}>
        <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-sm" data-testid="fab-menu">
          <DialogHeader><DialogTitle className="text-base">Crear nuevo</DialogTitle></DialogHeader>
          <div className="space-y-2">
            {[
              { id: 'casos', label: 'Crear caso', desc: 'Reportar un incidente', icon: ClipboardList, color: 'text-orange-400', bg: 'bg-orange-500/10' },
              { id: 'visits', label: 'Nueva visita', desc: 'Autorizar un visitante', icon: Users, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
              { id: 'reservations', label: 'Reservar area', desc: 'Agendar area comun', icon: Calendar, color: 'text-violet-400', bg: 'bg-violet-500/10' },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  onClick={() => { setShowFab(false); onNavigate(item.id); }}
                  className="w-full flex items-center gap-4 p-4 rounded-xl transition-all active:scale-[0.98] hover:bg-white/[0.04]"
                  style={{ border: `1px solid ${BORDER}` }}
                  data-testid={`fab-${item.id}`}
                >
                  <div className={`w-10 h-10 rounded-xl ${item.bg} flex items-center justify-center`}>
                    <Icon className={`w-5 h-5 ${item.color}`} strokeWidth={1.5} />
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-semibold text-white">{item.label}</p>
                    <p className="text-[11px] text-slate-500">{item.desc}</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-600 ml-auto" />
                </button>
              );
            })}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
