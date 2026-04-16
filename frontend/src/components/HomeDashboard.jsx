/**
 * GENTURIX — Home Dashboard (Resident)
 * Premium SaaS design with status card, quick actions, and recent activity.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import api from '../services/api';
import {
  ClipboardList, Wallet, FolderOpen, Landmark,
  CheckCircle, AlertTriangle, Loader2, ChevronRight,
  Globe, Lock,
} from 'lucide-react';

const SURFACE = '#11141D';
const GLASS = 'rgba(255,255,255,0.03)';
const BORDER = 'rgba(255,255,255,0.08)';

export default function HomeDashboard({ onNavigate }) {
  const [loading, setLoading] = useState(true);
  const [cases, setCases] = useState([]);
  const [balance, setBalance] = useState(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [casosRes] = await Promise.all([
          api.getCasos(1, 5).catch(() => ({ items: [] })),
        ]);
        setCases(casosRes.items || []);
      } catch {}
      finally { setLoading(false); }
    };
    load();
  }, []);

  const hasPending = cases.some(c => c.status === 'open');

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
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-5 h-5 animate-spin text-slate-500" />
      </div>
    );
  }

  return (
    <div className="space-y-5" data-testid="home-dashboard">
      {/* Status Card */}
      <div
        className="relative overflow-hidden rounded-3xl p-5"
        style={{
          background: hasPending
            ? 'linear-gradient(135deg, rgba(234,179,8,0.12) 0%, rgba(17,20,29,1) 60%)'
            : 'linear-gradient(135deg, rgba(6,182,212,0.12) 0%, rgba(17,20,29,1) 60%)',
          border: `1px solid ${hasPending ? 'rgba(234,179,8,0.15)' : 'rgba(6,182,212,0.15)'}`,
        }}
        data-testid="status-card"
      >
        <div className="flex items-center gap-4">
          <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${hasPending ? 'bg-yellow-500/15' : 'bg-cyan-500/15'}`}>
            {hasPending ? (
              <AlertTriangle className="w-7 h-7 text-yellow-400" strokeWidth={1.5} />
            ) : (
              <CheckCircle className="w-7 h-7 text-cyan-400" strokeWidth={1.5} />
            )}
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>
              {hasPending ? 'Temas pendientes' : 'Todo en orden'}
            </h2>
            <p className="text-sm text-slate-400">
              {hasPending
                ? `${cases.filter(c => c.status === 'open').length} caso${cases.filter(c => c.status === 'open').length > 1 ? 's' : ''} abierto${cases.filter(c => c.status === 'open').length > 1 ? 's' : ''}`
                : 'No hay incidencias activas'
              }
            </p>
          </div>
        </div>
      </div>

      {/* Quick Actions Grid */}
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

      {/* Recent Cases */}
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
    </div>
  );
}
