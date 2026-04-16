import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { toast } from 'sonner';
import api from '../services/api';
import {
  Plus,
  Inbox,
  Clock,
  CheckCircle,
  XCircle,
  ArrowUpRight,
  Loader2,
  MessageSquare,
  Send,
  Lock,
  Globe,
  Trash2,
  Camera,
  Image as ImageIcon,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const STATUS_CONFIG = {
  open: { label: 'Abierto', color: 'bg-blue-500/15 text-blue-400 border-blue-500/30' },
  review: { label: 'En revisión', color: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30' },
  in_progress: { label: 'En progreso', color: 'bg-purple-500/15 text-purple-400 border-purple-500/30' },
  closed: { label: 'Cerrado', color: 'bg-green-500/15 text-green-400 border-green-500/30' },
  rejected: { label: 'Rechazado', color: 'bg-red-500/15 text-red-400 border-red-500/30' },
};

const PRIORITY_CONFIG = {
  low: { label: 'Baja', color: 'bg-gray-500/15 text-gray-400' },
  medium: { label: 'Media', color: 'bg-blue-500/15 text-blue-400' },
  high: { label: 'Alta', color: 'bg-amber-500/15 text-amber-400' },
  urgent: { label: 'Urgente', color: 'bg-red-500/15 text-red-400' },
};

const CATEGORIES = [
  { value: 'mantenimiento', label: 'Mantenimiento' },
  { value: 'seguridad', label: 'Seguridad' },
  { value: 'ruido', label: 'Ruido' },
  { value: 'limpieza', label: 'Limpieza' },
  { value: 'infraestructura', label: 'Infraestructura' },
  { value: 'convivencia', label: 'Convivencia' },
  { value: 'otro', label: 'Otro' },
];

// ── Create Case Dialog ──
const CreateCaseDialog = ({ open, onClose, onCreated }) => {
  const { t } = useTranslation();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('mantenimiento');
  const [priority, setPriority] = useState('medium');
  const [visibility, setVisibility] = useState('private');
  const [sending, setSending] = useState(false);

  const handleSubmit = async () => {
    if (!title.trim() || !description.trim()) {
      toast.error(t('casos.fillRequired', 'Completa los campos requeridos'));
      return;
    }
    setSending(true);
    try {
      await api.createCaso({ title: title.trim(), description: description.trim(), category, priority, visibility });
      toast.success(t('casos.created', 'Caso creado exitosamente'));
      setTitle('');
      setDescription('');
      setCategory('mantenimiento');
      setPriority('medium');
      setVisibility('private');
      onCreated?.();
      onClose();
    } catch (err) {
      toast.error(err.message || 'Error al crear caso');
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-lg" data-testid="create-caso-dialog">
        <DialogHeader>
          <DialogTitle>{t('casos.newCase', 'Reportar Incidencia')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">{t('casos.title', 'Titulo')} *</label>
            <Input
              data-testid="caso-title-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ej: Fuga de agua en pasillo B"
              maxLength={200}
              className="bg-[#181B25] border-[#1E293B]"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">{t('casos.description', 'Descripcion')} *</label>
            <textarea
              data-testid="caso-description-input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe el problema con detalle..."
              maxLength={5000}
              rows={3}
              className="w-full rounded-md bg-[#181B25] border border-[#1E293B] text-sm px-3 py-2 text-white placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
            />
          </div>
          {/* Visibility */}
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Visibilidad del caso</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setVisibility('private')}
                data-testid="visibility-private"
                className={`p-3 rounded-lg border text-left transition-colors ${
                  visibility === 'private'
                    ? 'bg-primary/10 border-primary/40'
                    : 'bg-[#181B25] border-[#1E293B] hover:border-[#2E3B4B]'
                }`}
              >
                <div className="flex items-center gap-2 mb-0.5">
                  <Lock className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm font-medium text-white">Privado</span>
                </div>
                <p className="text-[10px] text-muted-foreground">Solo tu y el administrador</p>
              </button>
              <button
                type="button"
                onClick={() => setVisibility('community')}
                data-testid="visibility-community"
                className={`p-3 rounded-lg border text-left transition-colors ${
                  visibility === 'community'
                    ? 'bg-primary/10 border-primary/40'
                    : 'bg-[#181B25] border-[#1E293B] hover:border-[#2E3B4B]'
                }`}
              >
                <div className="flex items-center gap-2 mb-0.5">
                  <Globe className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-medium text-white">Comunitario</span>
                </div>
                <p className="text-[10px] text-muted-foreground">Visible para todos los residentes</p>
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">{t('casos.category', 'Categoria')}</label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger data-testid="caso-category-select" className="bg-[#181B25] border-[#1E293B]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">{t('casos.priority', 'Prioridad')}</label>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger data-testid="caso-priority-select" className="bg-[#181B25] border-[#1E293B]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="low">Baja</SelectItem>
                  <SelectItem value="medium">Media</SelectItem>
                  <SelectItem value="high">Alta</SelectItem>
                  <SelectItem value="urgent">Urgente</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <Button
            onClick={handleSubmit}
            disabled={sending || !title.trim() || !description.trim()}
            data-testid="submit-caso-btn"
            className="w-full"
          >
            {sending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Send className="w-4 h-4 mr-2" />}
            {t('casos.submit', 'Enviar Reporte')}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// ── Case Detail Dialog (Resident) ──
const CaseDetailDialog = ({ caso, open, onClose, onUpdated }) => {
  const { user } = useAuth();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (caso && open) {
      setLoading(true);
      api.getCasoDetail(caso.id)
        .then((d) => setDetail(d))
        .catch(() => toast.error('Error al cargar'))
        .finally(() => setLoading(false));
    }
  }, [caso, open]);

  const handleAddComment = async () => {
    if (!newComment.trim()) return;
    setSending(true);
    try {
      await api.addCasoComment(caso.id, { comment: newComment.trim(), is_internal: false });
      setNewComment('');
      const d = await api.getCasoDetail(caso.id);
      setDetail(d);
      onUpdated?.();
    } catch (err) {
      toast.error(err.message || 'Error');
    } finally {
      setSending(false);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { toast.error('Imagen excede 5 MB'); return; }
    setUploading(true);
    try {
      await api.uploadCasoAttachment(caso.id, file);
      toast.success('Imagen adjuntada');
      const d = await api.getCasoDetail(caso.id);
      setDetail(d);
      onUpdated?.();
    } catch (err) { toast.error(err.message || 'Error al subir'); }
    finally { setUploading(false); e.target.value = ''; }
  };

  const handleDelete = async () => {
    if (!window.confirm('Eliminar este caso? Esta accion no se puede deshacer.')) return;
    setDeleting(true);
    try {
      await api.deleteCaso(caso.id);
      toast.success('Caso eliminado');
      onUpdated?.();
      onClose();
    } catch (err) { toast.error(err.message || 'Error al eliminar'); }
    finally { setDeleting(false); }
  };

  const sCfg = STATUS_CONFIG[detail?.status] || STATUS_CONFIG.open;
  const pCfg = PRIORITY_CONFIG[detail?.priority] || PRIORITY_CONFIG.medium;
  const isOwner = detail && user && detail.created_by === user.id;
  const canDelete = isOwner && detail?.status !== 'closed';
  const canComment = detail?.status !== 'closed' && detail?.status !== 'rejected';
  const canAttach = canComment;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-lg max-h-[80vh] overflow-y-auto" data-testid="resident-caso-detail">
        <DialogHeader>
          <DialogTitle className="text-base pr-8">{detail?.title || caso?.title}</DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : detail ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className={sCfg.color}>{sCfg.label}</Badge>
              <Badge variant="outline" className={pCfg.color}>{pCfg.label}</Badge>
              {detail.visibility === 'community' ? (
                <Badge variant="outline" className="bg-blue-500/15 text-blue-400 border-blue-500/30"><Globe className="w-3 h-3 mr-1" />Comunitario</Badge>
              ) : (
                <Badge variant="outline" className="bg-gray-500/15 text-gray-400 border-gray-500/30"><Lock className="w-3 h-3 mr-1" />Privado</Badge>
              )}
            </div>
            {detail.visibility === 'community' && (
              <p className="text-[10px] text-muted-foreground">Reportado por: {detail.created_by_name}</p>
            )}
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">{detail.description}</p>
            <div className="text-[10px] text-muted-foreground">
              Creado: {new Date(detail.created_at).toLocaleString('es-ES')}
            </div>

            {/* Attachments */}
            {detail.attachments?.length > 0 && (
              <div>
                <h4 className="text-xs font-medium mb-2 flex items-center gap-1.5">
                  <ImageIcon className="w-3.5 h-3.5" /> Adjuntos ({detail.attachments.length})
                </h4>
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {detail.attachments.map((url, i) => (
                    <div key={i} className="w-20 h-20 rounded-lg bg-[#181B25] border border-[#1E293B] flex-shrink-0 overflow-hidden" data-testid={`attachment-${i}`}>
                      {url.startsWith('local://') ? (
                        <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                          <ImageIcon className="w-6 h-6" />
                        </div>
                      ) : (
                        <img src={url} alt={`Adjunto ${i+1}`} className="w-full h-full object-cover" onError={(e) => { e.target.style.display='none'; }} />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Upload attachment */}
            {canAttach && (
              <div>
                <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handleUpload} className="hidden" id="caso-attachment-input" data-testid="caso-attachment-input" />
                <label htmlFor="caso-attachment-input" className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium cursor-pointer transition-colors ${uploading ? 'opacity-50 pointer-events-none' : 'bg-[#181B25] border border-[#1E293B] text-muted-foreground hover:text-white hover:bg-white/5'}`}>
                  {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Camera className="w-3.5 h-3.5" />}
                  {uploading ? 'Subiendo...' : 'Adjuntar foto'}
                </label>
              </div>
            )}

            {/* Comments */}
            <div>
              <h4 className="text-xs font-medium mb-2 flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5" />
                Comentarios ({detail.comments?.length || 0})
              </h4>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {(detail.comments || []).map((c) => (
                  <div key={c.id} className="p-2 rounded-lg bg-[#181B25] border border-[#1E293B]/50 text-sm" data-testid={`comment-${c.id}`}>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-medium">{c.author_name}</span>
                      <span className="text-[9px] text-muted-foreground/50">{c.author_role}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{c.comment}</p>
                    <span className="text-[10px] text-muted-foreground">
                      {new Date(c.created_at).toLocaleString('es-ES')}
                    </span>
                  </div>
                ))}
                {(!detail.comments || detail.comments.length === 0) && (
                  <p className="text-xs text-muted-foreground text-center py-3">Sin comentarios</p>
                )}
              </div>
            </div>

            {canComment && (
              <div className="flex gap-2">
                <Input
                  data-testid="resident-comment-input"
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Agregar comentario..."
                  className="bg-[#181B25] border-[#1E293B]"
                  onKeyDown={(e) => e.key === 'Enter' && handleAddComment()}
                />
                <Button size="sm" disabled={!newComment.trim() || sending} onClick={handleAddComment} data-testid="resident-send-comment">
                  {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </Button>
              </div>
            )}

            {/* Delete button */}
            {canDelete && (
              <Button variant="outline" size="sm" className="w-full text-red-400 border-red-500/30 hover:bg-red-500/10 hover:text-red-300" onClick={handleDelete} disabled={deleting} data-testid="delete-caso-btn">
                {deleting ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Trash2 className="w-4 h-4 mr-1" />}
                Eliminar caso
              </Button>
            )}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
};

// ── Main Component ──
export default function CasosResident() {
  const { t } = useTranslation();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedCaso, setSelectedCaso] = useState(null);
  const [filterStatus, setFilterStatus] = useState('all');

  const fetchCases = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page_size: 50 };
      if (filterStatus !== 'all') params.status = filterStatus;
      const data = await api.getCasos(params);
      setCases(data.items || []);
    } catch {
      setCases([]);
    } finally {
      setLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  return (
    <div className="h-full overflow-y-auto" style={{ WebkitOverflowScrolling: 'touch', paddingBottom: '112px' }}>
      <div className="p-3 space-y-4" data-testid="casos-resident">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">
            {t('casos.myCases', 'Mis Casos')}
          </h2>
          <Button size="sm" onClick={() => setShowCreate(true)} data-testid="new-caso-btn">
            <Plus className="w-4 h-4 mr-1" />
            {t('casos.report', 'Reportar')}
          </Button>
        </div>

        {/* Filter */}
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger data-testid="resident-filter-status" className="h-8 w-36 bg-[#181B25] border-[#1E293B] text-xs">
            <SelectValue placeholder="Estado" />
          </SelectTrigger>
          <SelectContent className="bg-[#0F111A] border-[#1E293B]">
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="open">Abierto</SelectItem>
            <SelectItem value="in_progress">En progreso</SelectItem>
            <SelectItem value="closed">Cerrado</SelectItem>
          </SelectContent>
        </Select>

        {/* List */}
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : cases.length === 0 ? (
          <Card className="bg-[#0F111A] border-[#1E293B]">
            <CardContent className="p-6 text-center">
              <Inbox className="w-10 h-10 text-muted-foreground/30 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">
                {t('casos.noCases', 'No tienes casos reportados')}
              </p>
              <Button size="sm" className="mt-3" onClick={() => setShowCreate(true)} data-testid="empty-new-caso-btn">
                <Plus className="w-4 h-4 mr-1" />
                {t('casos.reportFirst', 'Reportar tu primer caso')}
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {cases.map((c) => {
              const sCfg = STATUS_CONFIG[c.status] || STATUS_CONFIG.open;
              const pCfg = PRIORITY_CONFIG[c.priority] || PRIORITY_CONFIG.medium;
              return (
                <Card
                  key={c.id}
                  className="bg-[#0F111A] border-[#1E293B] cursor-pointer hover:border-primary/30 transition-colors"
                  onClick={() => setSelectedCaso(c)}
                  data-testid={`resident-caso-${c.id}`}
                >
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <h4 className="text-sm font-medium text-white truncate">{c.title}</h4>
                      <Badge variant="outline" className={`text-[10px] h-5 flex-shrink-0 ${sCfg.color}`}>{sCfg.label}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-1">{c.description}</p>
                    <div className="flex items-center gap-2 mt-1.5">
                      <Badge variant="outline" className={`text-[9px] h-4 ${pCfg.color}`}>{pCfg.label}</Badge>
                      {c.visibility === 'community' ? (
                        <Badge variant="outline" className="text-[9px] h-4 bg-blue-500/15 text-blue-400 border-blue-500/30"><Globe className="w-2.5 h-2.5 mr-0.5" />Comunitario</Badge>
                      ) : (
                        <Badge variant="outline" className="text-[9px] h-4 bg-gray-500/15 text-gray-400 border-gray-500/30"><Lock className="w-2.5 h-2.5 mr-0.5" />Privado</Badge>
                      )}
                      {c.visibility === 'community' && c.created_by_name && (
                        <span className="text-[10px] text-muted-foreground/70">por {c.created_by_name}</span>
                      )}
                      <span className="text-[10px] text-muted-foreground">
                        {new Date(c.created_at).toLocaleString('es-ES', { day: '2-digit', month: 'short' })}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        <CreateCaseDialog open={showCreate} onClose={() => setShowCreate(false)} onCreated={fetchCases} />
        {selectedCaso && (
          <CaseDetailDialog caso={selectedCaso} open={!!selectedCaso} onClose={() => setSelectedCaso(null)} onUpdated={fetchCases} />
        )}
      </div>
    </div>
  );
}
