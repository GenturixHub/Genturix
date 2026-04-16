import React, { useState, useEffect, useCallback } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import api from '../services/api';
import { Calendar, Users, Video, MapPin, Loader2, ThumbsUp, ThumbsDown, Minus, CheckCircle, ClipboardList, ChevronLeft } from 'lucide-react';

const STATUS_CFG = {
  scheduled: { label: 'Programada', color: 'bg-blue-500/15 text-blue-400 border-blue-500/30' },
  in_progress: { label: 'En curso', color: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30' },
  completed: { label: 'Completada', color: 'bg-green-500/15 text-green-400 border-green-500/30' },
  cancelled: { label: 'Cancelada', color: 'bg-red-500/15 text-red-400 border-red-500/30' },
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
      await api.castVote(assemblyId, { agenda_item_id: agendaItemId, vote });
      toast.success('Voto registrado');
      fetchDetail();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setVotingId(null); }
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>;
  if (!data) return null;

  const sc = STATUS_CFG[data.status] || STATUS_CFG.scheduled;

  return (
    <div className="space-y-4" data-testid="asamblea-detail-resident">
      <button onClick={onBack} className="text-xs text-muted-foreground hover:text-white flex items-center gap-1" data-testid="back-btn">
        <ChevronLeft className="w-3.5 h-3.5" />Volver
      </button>

      {/* Header */}
      <Card className={`border ${sc.color.split(' ')[0].replace('text', 'border')}/20`}>
        <CardContent className="p-4">
          <div className="flex items-start justify-between mb-2">
            <h3 className="text-base font-bold text-white">{data.title}</h3>
            <Badge variant="outline" className={sc.color}>{sc.label}</Badge>
          </div>
          {data.description && <p className="text-xs text-muted-foreground mb-3">{data.description}</p>}
          <div className="flex flex-wrap gap-3 text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{data.date}</span>
            <span>{data.modality === 'presencial' ? 'Presencial' : data.modality === 'virtual' ? 'Virtual' : 'Hibrida'}</span>
            <span className="flex items-center gap-1"><Users className="w-3 h-3" />{data.attendance_count} asistentes</span>
          </div>
          {data.meeting_link && (
            <a href={data.meeting_link} target="_blank" rel="noreferrer" className="text-xs text-primary mt-2 block hover:underline">Unirse a la reunion</a>
          )}
          {/* Confirm attendance */}
          {data.status !== 'completed' && data.status !== 'cancelled' && (
            <Button
              size="sm"
              onClick={handleConfirmAttendance}
              disabled={confirming || data.my_attendance}
              className="w-full mt-3"
              variant={data.my_attendance ? 'outline' : 'default'}
              data-testid="confirm-attendance-btn"
            >
              {confirming ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <CheckCircle className="w-4 h-4 mr-1" />}
              {data.my_attendance ? 'Asistencia confirmada' : 'Confirmar asistencia'}
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Agenda + Voting */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2"><ClipboardList className="w-4 h-4 text-primary" />Agenda</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {(data.agenda || []).map((item, idx) => (
            <div key={item.id} className="p-3 rounded-lg bg-[#181B25] border border-[#1E293B]/50" data-testid={`agenda-${item.id}`}>
              <p className="text-sm font-medium text-white mb-1">{idx + 1}. {item.title}</p>
              {item.description && <p className="text-xs text-muted-foreground mb-2">{item.description}</p>}
              {item.is_votable && (
                <div className="space-y-2">
                  {/* Vote results */}
                  {item.vote_results && (
                    <div className="flex gap-3 text-xs">
                      <span className="text-green-400 flex items-center gap-1"><ThumbsUp className="w-3 h-3" />{item.vote_results.yes}</span>
                      <span className="text-red-400 flex items-center gap-1"><ThumbsDown className="w-3 h-3" />{item.vote_results.no}</span>
                      <span className="text-muted-foreground flex items-center gap-1"><Minus className="w-3 h-3" />{item.vote_results.abstain}</span>
                    </div>
                  )}
                  {/* Vote buttons */}
                  {data.status !== 'completed' && data.status !== 'cancelled' && (
                    <div className="flex gap-2">
                      {[{ key: 'yes', label: 'A favor', icon: ThumbsUp, color: 'text-green-400 border-green-500/30 hover:bg-green-500/10' },
                        { key: 'no', label: 'En contra', icon: ThumbsDown, color: 'text-red-400 border-red-500/30 hover:bg-red-500/10' },
                        { key: 'abstain', label: 'Abstencion', icon: Minus, color: 'text-muted-foreground border-[#1E293B] hover:bg-white/5' },
                      ].map(opt => {
                        const Icon = opt.icon;
                        const isMyVote = item.my_vote === opt.key;
                        return (
                          <Button
                            key={opt.key}
                            size="sm"
                            variant="outline"
                            className={`h-7 text-[10px] ${isMyVote ? 'bg-primary/20 border-primary text-primary' : opt.color}`}
                            onClick={() => handleVote(item.id, opt.key)}
                            disabled={!!votingId}
                            data-testid={`vote-${item.id}-${opt.key}`}
                          >
                            {votingId === `${item.id}-${opt.key}` ? <Loader2 className="w-3 h-3 animate-spin mr-0.5" /> : <Icon className="w-3 h-3 mr-0.5" />}
                            {opt.label}
                          </Button>
                        );
                      })}
                    </div>
                  )}
                  {item.my_vote && <p className="text-[10px] text-muted-foreground">Tu voto: {item.my_vote === 'yes' ? 'A favor' : item.my_vote === 'no' ? 'En contra' : 'Abstencion'}</p>}
                </div>
              )}
            </div>
          ))}
          {(!data.agenda || data.agenda.length === 0) && (
            <p className="text-xs text-muted-foreground text-center py-4">Sin puntos de agenda</p>
          )}
        </CardContent>
      </Card>
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
          <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
        ) : assemblies.length === 0 ? (
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardContent className="p-6 text-center">
              <Calendar className="w-10 h-10 text-muted-foreground/30 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No hay asambleas programadas</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {assemblies.map(a => {
              const sc = STATUS_CFG[a.status] || STATUS_CFG.scheduled;
              return (
                <Card key={a.id} className="bg-[#0F111A] border-[#1E293B] cursor-pointer hover:border-primary/30 transition-colors" onClick={() => setSelectedId(a.id)} data-testid={`assembly-card-${a.id}`}>
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <h4 className="text-sm font-medium text-white truncate">{a.title}</h4>
                      <Badge variant="outline" className={`text-[10px] h-5 flex-shrink-0 ${sc.color}`}>{sc.label}</Badge>
                    </div>
                    <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                      <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{a.date}</span>
                      <span>{a.modality === 'presencial' ? 'Presencial' : a.modality === 'virtual' ? 'Virtual' : 'Hibrida'}</span>
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
