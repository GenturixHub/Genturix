import React, { useState, useEffect, useCallback } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import api from '../services/api';
import { Plus, Loader2, Users, Calendar, Video, MapPin, FileDown, ClipboardList, CheckCircle, ThumbsUp, ThumbsDown, Minus, ChevronRight } from 'lucide-react';

const STATUS_CFG = {
  scheduled: { label: 'Programada', color: 'bg-blue-500/15 text-blue-400 border-blue-500/30' },
  in_progress: { label: 'En curso', color: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30' },
  completed: { label: 'Completada', color: 'bg-green-500/15 text-green-400 border-green-500/30' },
  cancelled: { label: 'Cancelada', color: 'bg-red-500/15 text-red-400 border-red-500/30' },
};
const MOD_CFG = { presencial: { label: 'Presencial', icon: MapPin }, virtual: { label: 'Virtual', icon: Video }, hibrida: { label: 'Hibrida', icon: Video } };

// ── Create Assembly Dialog ──
const CreateDialog = ({ open, onClose, onCreated }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [date, setDate] = useState('');
  const [modality, setModality] = useState('presencial');
  const [link, setLink] = useState('');
  const [agendaItems, setAgendaItems] = useState([{ title: '', is_votable: false }]);
  const [sending, setSending] = useState(false);

  const addAgendaRow = () => setAgendaItems(prev => [...prev, { title: '', is_votable: false }]);
  const updateAgenda = (i, key, val) => setAgendaItems(prev => prev.map((item, idx) => idx === i ? { ...item, [key]: val } : item));

  const handleSubmit = async () => {
    if (!title.trim() || !date) return;
    setSending(true);
    try {
      const items = agendaItems.filter(a => a.title.trim());
      await api.createAsamblea({ title: title.trim(), description: description.trim(), date, modality, meeting_link: link.trim() || null, agenda_items: items });
      toast.success('Asamblea creada');
      setTitle(''); setDescription(''); setDate(''); setAgendaItems([{ title: '', is_votable: false }]);
      onCreated?.(); onClose();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setSending(false); }
  };

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-lg max-h-[85vh] overflow-y-auto" data-testid="create-asamblea-dialog">
        <DialogHeader><DialogTitle>Nueva Asamblea</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <Input value={title} onChange={e => setTitle(e.target.value)} placeholder="Titulo de la asamblea" className="bg-[#181B25] border-[#1E293B]" data-testid="asamblea-title" maxLength={200} />
          <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Descripcion (opcional)" rows={2} className="w-full rounded-md bg-[#181B25] border border-[#1E293B] text-sm px-3 py-2 text-white placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none" data-testid="asamblea-desc" maxLength={5000} />
          <div className="grid grid-cols-2 gap-3">
            <Input type="datetime-local" value={date} onChange={e => setDate(e.target.value)} className="bg-[#181B25] border-[#1E293B]" data-testid="asamblea-date" />
            <Select value={modality} onValueChange={setModality}>
              <SelectTrigger className="bg-[#181B25] border-[#1E293B]" data-testid="asamblea-modality"><SelectValue /></SelectTrigger>
              <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                <SelectItem value="presencial">Presencial</SelectItem>
                <SelectItem value="virtual">Virtual</SelectItem>
                <SelectItem value="hibrida">Hibrida</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {(modality === 'virtual' || modality === 'hibrida') && (
            <Input value={link} onChange={e => setLink(e.target.value)} placeholder="Link de la reunion (Zoom, Meet, etc.)" className="bg-[#181B25] border-[#1E293B]" data-testid="asamblea-link" maxLength={500} />
          )}
          {/* Agenda */}
          <div>
            <p className="text-xs text-muted-foreground mb-2 font-medium">Agenda</p>
            {agendaItems.map((item, i) => (
              <div key={i} className="flex gap-2 mb-2 items-center">
                <Input value={item.title} onChange={e => updateAgenda(i, 'title', e.target.value)} placeholder={`Punto ${i + 1}`} className="bg-[#181B25] border-[#1E293B] flex-1" data-testid={`agenda-title-${i}`} maxLength={200} />
                <label className="flex items-center gap-1 text-[10px] text-muted-foreground whitespace-nowrap cursor-pointer">
                  <input type="checkbox" checked={item.is_votable} onChange={e => updateAgenda(i, 'is_votable', e.target.checked)} className="rounded" data-testid={`agenda-votable-${i}`} />
                  Votable
                </label>
              </div>
            ))}
            <Button size="sm" variant="ghost" onClick={addAgendaRow} className="text-xs h-7" data-testid="add-agenda-row"><Plus className="w-3 h-3 mr-1" />Agregar punto</Button>
          </div>
          <Button onClick={handleSubmit} disabled={sending || !title.trim() || !date} className="w-full" data-testid="submit-asamblea">
            {sending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Plus className="w-4 h-4 mr-2" />} Crear Asamblea
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ── Assembly Detail ──
const AssemblyDetail = ({ assemblyId, onBack }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [newAgenda, setNewAgenda] = useState('');
  const [newVotable, setNewVotable] = useState(false);
  const [addingAgenda, setAddingAgenda] = useState(false);

  const fetch = useCallback(async () => {
    try { const d = await api.getAsambleaDetail(assemblyId); setData(d); }
    catch { toast.error('Error al cargar'); }
    finally { setLoading(false); }
  }, [assemblyId]);
  useEffect(() => { fetch(); }, [fetch]);

  const handleStatusChange = async (newStatus) => {
    try { await api.updateAsambleaStatus(assemblyId, newStatus); toast.success('Estado actualizado'); fetch(); }
    catch (err) { toast.error(err.message || 'Error'); }
  };

  const handleAddAgenda = async () => {
    if (!newAgenda.trim()) return;
    setAddingAgenda(true);
    try { await api.addAgendaItem(assemblyId, { title: newAgenda.trim(), is_votable: newVotable }); setNewAgenda(''); setNewVotable(false); fetch(); }
    catch (err) { toast.error(err.message || 'Error'); }
    finally { setAddingAgenda(false); }
  };

  const handleGenerateActa = async () => {
    setGenerating(true);
    try { await api.generateActa(assemblyId, data?.title); toast.success('Acta generada y guardada en Documentos'); }
    catch (err) { toast.error(err.message || 'Error'); }
    finally { setGenerating(false); }
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>;
  if (!data) return <p className="text-sm text-muted-foreground text-center py-8">No se pudo cargar</p>;

  const sc = STATUS_CFG[data.status] || STATUS_CFG.scheduled;

  return (
    <div className="space-y-6" data-testid="asamblea-detail">
      <button onClick={onBack} className="text-sm text-muted-foreground hover:text-white transition-colors" data-testid="back-btn">&larr; Volver a asambleas</button>
      {/* Header */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-3 mb-3">
            <h2 className="text-lg font-bold text-white">{data.title}</h2>
            <Badge variant="outline" className={sc.color}>{sc.label}</Badge>
          </div>
          {data.description && <p className="text-sm text-muted-foreground mb-3">{data.description}</p>}
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{data.date}</span>
            <span className="flex items-center gap-1">{MOD_CFG[data.modality]?.label || data.modality}</span>
            <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" />{data.attendance_count} asistentes</span>
          </div>
          {data.meeting_link && <a href={data.meeting_link} target="_blank" rel="noreferrer" className="text-xs text-primary mt-2 block hover:underline">{data.meeting_link}</a>}
          {/* Status actions */}
          <div className="flex gap-2 mt-4">
            {data.status === 'scheduled' && <Button size="sm" onClick={() => handleStatusChange('in_progress')} data-testid="start-assembly">Iniciar Asamblea</Button>}
            {data.status === 'in_progress' && <Button size="sm" onClick={() => handleStatusChange('completed')} data-testid="complete-assembly">Finalizar</Button>}
            {data.status !== 'completed' && data.status !== 'cancelled' && (
              <Button size="sm" variant="outline" className="text-red-400" onClick={() => handleStatusChange('cancelled')} data-testid="cancel-assembly">Cancelar</Button>
            )}
            <Button size="sm" variant="outline" onClick={handleGenerateActa} disabled={generating} data-testid="generate-acta">
              {generating ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <FileDown className="w-3 h-3 mr-1" />} Generar Acta
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Agenda */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><ClipboardList className="w-4 h-4 text-primary" />Agenda ({data.agenda?.length || 0})</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {(data.agenda || []).map((item, idx) => (
            <div key={item.id} className="p-3 rounded-lg bg-[#181B25] border border-[#1E293B]/50" data-testid={`agenda-item-${item.id}`}>
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-white">{idx + 1}. {item.title}</p>
                {item.is_votable && <Badge variant="outline" className="text-[9px] bg-purple-500/15 text-purple-400 border-purple-500/30">Votable</Badge>}
              </div>
              {item.description && <p className="text-xs text-muted-foreground mt-1">{item.description}</p>}
              {item.vote_results && (
                <div className="flex gap-4 mt-2 text-xs">
                  <span className="text-green-400 flex items-center gap-1"><ThumbsUp className="w-3 h-3" />{item.vote_results.yes}</span>
                  <span className="text-red-400 flex items-center gap-1"><ThumbsDown className="w-3 h-3" />{item.vote_results.no}</span>
                  <span className="text-muted-foreground flex items-center gap-1"><Minus className="w-3 h-3" />{item.vote_results.abstain}</span>
                  <span className="text-muted-foreground">({item.vote_results.total} votos)</span>
                </div>
              )}
            </div>
          ))}
          {/* Add agenda item */}
          <div className="flex gap-2 items-center mt-2">
            <Input value={newAgenda} onChange={e => setNewAgenda(e.target.value)} placeholder="Nuevo punto de agenda..." className="bg-[#181B25] border-[#1E293B] flex-1" data-testid="new-agenda-input" maxLength={200} />
            <label className="flex items-center gap-1 text-[10px] text-muted-foreground whitespace-nowrap cursor-pointer">
              <input type="checkbox" checked={newVotable} onChange={e => setNewVotable(e.target.checked)} className="rounded" />Votable
            </label>
            <Button size="sm" onClick={handleAddAgenda} disabled={addingAgenda || !newAgenda.trim()} data-testid="add-agenda-btn">
              {addingAgenda ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Attendance */}
      <Card className="bg-[#0F111A] border-[#1E293B]">
        <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><Users className="w-4 h-4 text-primary" />Asistencia ({data.attendance_count})</CardTitle></CardHeader>
        <CardContent>
          {data.attendance?.length > 0 ? (
            <div className="space-y-1">
              {data.attendance.map(a => (
                <div key={a.id} className="flex items-center justify-between px-2 py-1.5 rounded bg-[#181B25] text-xs">
                  <span className="text-white">{a.user_name}</span>
                  <span className="text-muted-foreground">{a.unit || '-'}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground text-center py-3">Sin asistencia confirmada</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

// ── Main Page ──
export default function AsambleaModule() {
  const [assemblies, setAssemblies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedId, setSelectedId] = useState(null);

  const fetchAssemblies = useCallback(async () => {
    setLoading(true);
    try { const d = await api.getAsambleas(); setAssemblies(d.items || []); }
    catch { setAssemblies([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAssemblies(); }, [fetchAssemblies]);

  if (selectedId) return (
    <DashboardLayout title="Asamblea">
      <AssemblyDetail assemblyId={selectedId} onBack={() => { setSelectedId(null); fetchAssemblies(); }} />
    </DashboardLayout>
  );

  return (
    <DashboardLayout title="Asamblea Virtual">
      <div data-testid="asamblea-module" className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Asambleas</h2>
          <Button size="sm" onClick={() => setShowCreate(true)} data-testid="btn-new-asamblea"><Plus className="w-4 h-4 mr-1" />Nueva Asamblea</Button>
        </div>
        {loading ? (
          <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /></div>
        ) : assemblies.length === 0 ? (
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardContent className="p-8 text-center">
              <Calendar className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No hay asambleas programadas</p>
              <Button size="sm" className="mt-3" onClick={() => setShowCreate(true)}>Crear primera asamblea</Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {assemblies.map(a => {
              const sc = STATUS_CFG[a.status] || STATUS_CFG.scheduled;
              return (
                <Card key={a.id} className="bg-[#0F111A] border-[#1E293B] cursor-pointer hover:border-primary/30 transition-colors" onClick={() => setSelectedId(a.id)} data-testid={`assembly-${a.id}`}>
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-medium text-white truncate">{a.title}</h3>
                        <Badge variant="outline" className={`text-[10px] h-5 flex-shrink-0 ${sc.color}`}>{sc.label}</Badge>
                      </div>
                      <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                        <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{a.date}</span>
                        <span>{MOD_CFG[a.modality]?.label}</span>
                        <span className="flex items-center gap-1"><Users className="w-3 h-3" />{a.attendance_count}</span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
        <CreateDialog open={showCreate} onClose={() => setShowCreate(false)} onCreated={fetchAssemblies} />
      </div>
    </DashboardLayout>
  );
}
