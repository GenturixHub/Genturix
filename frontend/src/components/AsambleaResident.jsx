import React, { useState, useEffect, useCallback } from 'react';
import { Button } from './ui/button';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import api from '../services/api';
import {
  Calendar, Users, Loader2, ThumbsUp, ThumbsDown, Minus,
  CheckCircle, ChevronLeft, ExternalLink, Vote, Clock, Lock,
} from 'lucide-react';

const STATUS_CFG = {
  scheduled: { label: 'Programada', color: 'bg-blue-500/15 text-blue-400 border-blue-500/30', dotColor: 'bg-blue-400' },
  in_progress: { label: 'En curso', color: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30', dotColor: 'bg-emerald-400 animate-pulse' },
  completed: { label: 'Finalizada', color: 'bg-gray-500/15 text-gray-400 border-gray-500/30', dotColor: 'bg-gray-400' },
  cancelled: { label: 'Cancelada', color: 'bg-red-500/15 text-red-400 border-red-500/30', dotColor: 'bg-red-400' },
};

const MODALITY = { presencial: 'Presencial', virtual: 'Virtual', hibrida: 'Hibrida' };

function formatDate(d) {
  if (!d) return '';
  try {
    const date = new Date(d);
    return date.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch { return d; }
}

// ── Vote Buttons ──
const VoteButtons = ({ item, assemblyStatus, onVote, votingId }) => {
  const closed = assemblyStatus === 'completed' || assemblyStatus === 'cancelled';
  const hasVoted = !!item.my_vote;
  const r = item.vote_results || { yes: 0, no: 0, abstain: 0, total: 0 };
  const total = r.yes + r.no + r.abstain;

  const options = [
    { key: 'yes', label: 'A favor', icon: ThumbsUp, activeColor: 'bg-emerald-500 text-white border-emerald-500', inactiveColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20' },
    { key: 'no', label: 'En contra', icon: ThumbsDown, activeColor: 'bg-red-500 text-white border-red-500', inactiveColor: 'bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/20' },
    { key: 'abstain', label: 'Abstencion', icon: Minus, activeColor: 'bg-gray-500 text-white border-gray-500', inactiveColor: 'bg-white/5 text-muted-foreground border-[#1E293B] hover:bg-white/10' },
  ];

  return (
    <div className="space-y-3" data-testid={`vote-section-${item.id}`}>
      {/* Results bar */}
      {total > 0 && (
        <div className="space-y-1.5">
          <div className="flex h-2 rounded-full overflow-hidden bg-[#181B25]">
            {r.yes > 0 && <div className="bg-emerald-500 transition-all" style={{ width: `${(r.yes / total) * 100}%` }} />}
            {r.no > 0 && <div className="bg-red-500 transition-all" style={{ width: `${(r.no / total) * 100}%` }} />}
            {r.abstain > 0 && <div className="bg-gray-500 transition-all" style={{ width: `${(r.abstain / total) * 100}%` }} />}
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span className="text-emerald-400">{r.yes} a favor</span>
            <span className="text-red-400">{r.no} en contra</span>
            <span>{r.abstain} abstencion</span>
          </div>
        </div>
      )}

      {/* Vote buttons */}
      {closed ? (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Lock className="w-3.5 h-3.5" /> Votacion cerrada
          {item.my_vote && <span className="ml-1">— Tu voto: {item.my_vote === 'yes' ? 'A favor' : item.my_vote === 'no' ? 'En contra' : 'Abstencion'}</span>}
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-2">
          {options.map(opt => {
            const Icon = opt.icon;
            const isActive = item.my_vote === opt.key;
            const isLoading = votingId === `${item.id}-${opt.key}`;
            return (
              <button
                key={opt.key}
                onClick={() => onVote(item.id, opt.key)}
                disabled={!!votingId}
                data-testid={`vote-${item.id}-${opt.key}`}
                className={`flex flex-col items-center gap-1 py-3 px-2 rounded-xl border text-center transition-all duration-150 active:scale-95 min-h-[56px] ${isActive ? opt.activeColor : opt.inactiveColor}`}
              >
                {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Icon className="w-5 h-5" />}
                <span className="text-[10px] font-medium leading-none">{opt.label}</span>
              </button>
            );
          })}
        </div>
      )}
      {hasVoted && !closed && (
        <p className="text-[10px] text-muted-foreground text-center">
          Tu voto: <strong>{item.my_vote === 'yes' ? 'A favor' : item.my_vote === 'no' ? 'En contra' : 'Abstencion'}</strong> — puedes cambiarlo
        </p>
      )}
    </div>
  );
};

// ── Detail View ──
const AssemblyDetailView = ({ assemblyId, onBack }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [votingId, setVotingId] = useState(null);

  const fetchDetail = useCallback(async () => {
    try { const d = await api.getAsambleaDetail(assemblyId); setData(d); }
    catch { toast.error('Error al cargar'); }
    finally { setLoading(false); }
  }, [assemblyId]);
  useEffect(() => { fetchDetail(); }, [fetchDetail]);

  const handleConfirmAttendance = async () => {
    setConfirming(true);
    try {
      const res = await api.confirmAttendance(assemblyId);
      toast.success(res.status === 'already_confirmed' ? 'Ya confirmaste asistencia' : 'Asistencia confirmada');
      fetchDetail();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setConfirming(false); }
  };

  const handleVote = async (agendaItemId, vote) => {
    setVotingId(`${agendaItemId}-${vote}`);
    try {
      const res = await api.castVote(assemblyId, { agenda_item_id: agendaItemId, vote });
      toast.success(res.status === 'vote_updated' ? 'Voto actualizado' : 'Voto registrado');
      fetchDetail();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setVotingId(null); }
  };

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>;
  if (!data) return null;

  const sc = STATUS_CFG[data.status] || STATUS_CFG.scheduled;
  const isOpen = data.status === 'scheduled' || data.status === 'in_progress';
  const votableItems = (data.agenda || []).filter(i => i.is_votable);
  const nonVotableItems = (data.agenda || []).filter(i => !i.is_votable);

  return (
    <div className="space-y-4" data-testid="asamblea-detail-resident">
      <button onClick={onBack} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-white transition-colors py-1" data-testid="back-btn">
        <ChevronLeft className="w-4 h-4" />Asambleas
      </button>

      {/* ── Header Card ── */}
      <Card className="bg-gradient-to-br from-[#0F111A] to-[#131620] border-[#1E293B] overflow-hidden">
        <CardContent className="p-5">
          <div className="flex items-start justify-between mb-3">
            <h2 className="text-lg font-bold text-white leading-tight pr-3">{data.title}</h2>
            <Badge variant="outline" className={`flex-shrink-0 ${sc.color}`}>
              <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${sc.dotColor}`} />
              {sc.label}
            </Badge>
          </div>
          {data.description && <p className="text-sm text-muted-foreground mb-4">{data.description}</p>}
          <div className="space-y-2 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-primary flex-shrink-0" />
              <span>{formatDate(data.date)}</span>
            </div>
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-primary flex-shrink-0" />
              <span>{data.attendance_count} asistente{data.attendance_count !== 1 ? 's' : ''} confirmados</span>
            </div>
          </div>
          {data.meeting_link && (
            <a href={data.meeting_link} target="_blank" rel="noreferrer"
              className="mt-3 inline-flex items-center gap-1.5 text-sm text-primary hover:underline">
              <ExternalLink className="w-3.5 h-3.5" />Unirse a la reunion
            </a>
          )}
        </CardContent>
      </Card>

      {/* ── Attendance ── */}
      {isOpen && (
        <Button
          onClick={handleConfirmAttendance}
          disabled={confirming || data.my_attendance}
          variant={data.my_attendance ? 'outline' : 'default'}
          className={`w-full h-14 text-base font-medium rounded-xl transition-all ${data.my_attendance ? 'border-emerald-500/30 text-emerald-400' : ''}`}
          data-testid="confirm-attendance-btn"
        >
          {confirming ? (
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
          ) : data.my_attendance ? (
            <CheckCircle className="w-5 h-5 mr-2 text-emerald-400" />
          ) : (
            <Users className="w-5 h-5 mr-2" />
          )}
          {data.my_attendance ? 'Asistencia confirmada' : 'Confirmar mi asistencia'}
        </Button>
      )}

      {/* ── Voting Section ── */}
      {votableItems.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 px-1">
            <Vote className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold text-white">Votaciones</h3>
            {!isOpen && <Badge variant="outline" className="text-[9px] bg-gray-500/15 text-gray-400 border-gray-500/30 ml-auto"><Lock className="w-2.5 h-2.5 mr-0.5" />Cerrada</Badge>}
          </div>
          {votableItems.map((item, idx) => (
            <Card key={item.id} className="bg-[#0F111A] border-[#1E293B]" data-testid={`votable-item-${item.id}`}>
              <CardContent className="p-4 space-y-3">
                <div>
                  <p className="text-sm font-medium text-white">{item.title}</p>
                  {item.description && <p className="text-xs text-muted-foreground mt-1">{item.description}</p>}
                </div>
                <VoteButtons item={item} assemblyStatus={data.status} onVote={handleVote} votingId={votingId} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* ── Agenda (non-votable) ── */}
      {nonVotableItems.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-1">
            <Clock className="w-4 h-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-white">Otros puntos</h3>
          </div>
          {nonVotableItems.map((item, idx) => (
            <div key={item.id} className="p-3 rounded-xl bg-[#0F111A] border border-[#1E293B]/50" data-testid={`agenda-${item.id}`}>
              <p className="text-sm text-white">{item.title}</p>
              {item.description && <p className="text-xs text-muted-foreground mt-1">{item.description}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ── Main Component ──
export default function AsambleaResident() {
  const [assemblies, setAssemblies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState(null);

  const fetchAssemblies = useCallback(async () => {
    setLoading(true);
    try { const d = await api.getAsambleas(); setAssemblies(d.items || []); }
    catch { setAssemblies([]); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { fetchAssemblies(); }, [fetchAssemblies]);

  if (selectedId) return (
    <div className="h-full overflow-y-auto" style={{ WebkitOverflowScrolling: 'touch', paddingBottom: '112px' }}>
      <div className="p-3">
        <AssemblyDetailView assemblyId={selectedId} onBack={() => { setSelectedId(null); fetchAssemblies(); }} />
      </div>
    </div>
  );

  return (
    <div className="h-full overflow-y-auto" style={{ WebkitOverflowScrolling: 'touch', paddingBottom: '112px' }}>
      <div className="p-3 space-y-4" data-testid="asamblea-resident">
        <h2 className="text-base font-semibold">Asambleas</h2>
        {loading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
        ) : assemblies.length === 0 ? (
          <div className="text-center py-16">
            <Calendar className="w-12 h-12 text-muted-foreground/20 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">No hay asambleas programadas</p>
          </div>
        ) : (
          <div className="space-y-3">
            {assemblies.map(a => {
              const sc = STATUS_CFG[a.status] || STATUS_CFG.scheduled;
              return (
                <Card key={a.id} className="bg-[#0F111A] border-[#1E293B] cursor-pointer hover:border-primary/30 active:scale-[0.98] transition-all" onClick={() => setSelectedId(a.id)} data-testid={`assembly-card-${a.id}`}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h3 className="text-sm font-medium text-white">{a.title}</h3>
                      <Badge variant="outline" className={`text-[10px] h-5 flex-shrink-0 ${sc.color}`}>
                        <span className={`w-1.5 h-1.5 rounded-full mr-1 ${sc.dotColor}`} />
                        {sc.label}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-4 text-[11px] text-muted-foreground">
                      <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{formatDate(a.date).split(',').slice(0, 2).join(',')}</span>
                      <span>{MODALITY[a.modality]}</span>
                      <span className="flex items-center gap-1"><Users className="w-3 h-3" />{a.attendance_count}</span>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
