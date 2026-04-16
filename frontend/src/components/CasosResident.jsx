import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Convert storage path to secure proxy URL
const toProxyUrl = (path) => {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('blob:')) return path;
  const token = localStorage.getItem('genturix_access_token');
  return `${API_URL}/api/casos/image-proxy?path=${encodeURIComponent(path)}&token=${encodeURIComponent(token || '')}`;
};
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

// ── Image Lightbox Modal ──
const ImageLightbox = ({ src, onClose }) => {
  if (!src) return null;
  return (
    <div className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center p-4" onClick={onClose} data-testid="image-lightbox">
      <button onClick={onClose} className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 flex items-center justify-center text-white hover:bg-white/20 transition-colors z-10">
        <XCircle className="w-6 h-6" />
      </button>
      <img src={toProxyUrl(src)} alt="Ampliada" className="max-w-full max-h-[85vh] rounded-lg object-contain" onClick={e => e.stopPropagation()} />
    </div>
  );
};

// ── Image Grid (reusable) ──
const ImageGrid = ({ images, onImageClick }) => {
  if (!images || images.length === 0) return null;
  return (
    <div className="flex gap-2 flex-wrap mt-2">
      {images.map((url, i) => (
        <button
          key={i}
          onClick={() => onImageClick?.(url)}
          className="w-16 h-16 rounded-xl overflow-hidden bg-[#181B25] border border-white/5 flex-shrink-0 hover:border-cyan-500/30 transition-colors"
          data-testid={`img-thumb-${i}`}
        >
          <img src={toProxyUrl(url)} alt="" className="w-full h-full object-cover" onError={e => { e.target.style.display='none'; }} />
        </button>
      ))}
    </div>
  );
};

// ── Multi-File Picker with Preview ──
const ImagePicker = ({ files, setFiles, maxFiles = 5 }) => {
  const handleAdd = (e) => {
    const newFiles = Array.from(e.target.files || []);
    const valid = newFiles.filter(f => {
      if (f.size > 5 * 1024 * 1024) { toast.error(`${f.name} excede 5 MB`); return false; }
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(f.type)) { toast.error(`${f.name}: formato no permitido`); return false; }
      return true;
    });
    setFiles(prev => [...prev, ...valid].slice(0, maxFiles));
    e.target.value = '';
  };
  const handleRemove = (idx) => setFiles(prev => prev.filter((_, i) => i !== idx));

  return (
    <div>
      {files.length > 0 && (
        <div className="flex gap-2 flex-wrap mb-2">
          {files.map((f, i) => (
            <div key={i} className="relative w-16 h-16 rounded-xl overflow-hidden bg-[#181B25] border border-white/5 group">
              <img src={URL.createObjectURL(f)} alt="" className="w-full h-full object-cover" />
              <button
                onClick={() => handleRemove(i)}
                className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity"
                data-testid={`remove-img-${i}`}
              >
                <XCircle className="w-5 h-5 text-white" />
              </button>
            </div>
          ))}
        </div>
      )}
      {files.length < maxFiles && (
        <label className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium cursor-pointer bg-white/[0.03] border border-white/[0.08] text-slate-400 hover:text-white hover:bg-white/[0.06] transition-colors">
          <Camera className="w-3.5 h-3.5" />
          {files.length === 0 ? 'Adjuntar fotos' : `Agregar (${files.length}/${maxFiles})`}
          <input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={handleAdd} className="hidden" data-testid="image-picker-input" />
        </label>
      )}
    </div>
  );
};

// ── Create Case Dialog ──
const CreateCaseDialog = ({ open, onClose, onCreated }) => {
  const { t } = useTranslation();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('mantenimiento');
  const [priority, setPriority] = useState('medium');
  const [visibility, setVisibility] = useState('private');
  const [images, setImages] = useState([]);
  const [sending, setSending] = useState(false);

  const handleSubmit = async () => {
    if (!title.trim() || !description.trim()) {
      toast.error(t('casos.fillRequired', 'Completa los campos requeridos'));
      return;
    }
    setSending(true);
    try {
      // 1. Create the case
      const caso = await api.createCaso({ title: title.trim(), description: description.trim(), category, priority, visibility });
      // 2. Upload images one by one
      if (images.length > 0 && caso?.id) {
        for (const file of images) {
          try { await api.uploadCasoAttachment(caso.id, file); }
          catch (err) { console.error('Image upload failed:', err); }
        }
      }
      toast.success(images.length > 0 ? `Caso creado con ${images.length} imagen(es)` : 'Caso creado');
      setTitle(''); setDescription(''); setCategory('mantenimiento'); setPriority('medium'); setVisibility('private'); setImages([]);
      onCreated?.(); onClose();
    } catch (err) { toast.error(err.message || 'Error al crear caso'); }
    finally { setSending(false); }
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
          {/* Images */}
          <div>
            <label className="text-xs text-muted-foreground mb-1.5 block">Fotos (opcional)</label>
            <ImagePicker files={images} setFiles={setImages} maxFiles={5} />
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
  const [commentImages, setCommentImages] = useState([]);
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [lightboxSrc, setLightboxSrc] = useState(null);

  const refreshDetail = useCallback(async () => {
    if (!caso) return;
    try {
      const d = await api.getCasoDetail(caso.id);
      setDetail(d);
    } catch {}
  }, [caso]);

  useEffect(() => {
    if (caso && open) {
      setLoading(true);
      refreshDetail().finally(() => setLoading(false));
    }
  }, [caso, open, refreshDetail]);

  const handleAddComment = async () => {
    if (!newComment.trim() && commentImages.length === 0) return;
    setSending(true);
    try {
      // 1. Create the comment
      const commentText = newComment.trim() || (commentImages.length > 0 ? '[Imagen]' : '');
      const result = await api.addCasoComment(caso.id, { comment: commentText, is_internal: false });
      // 2. Upload comment images
      if (commentImages.length > 0 && result?.id) {
        for (const file of commentImages) {
          try { await api.uploadCommentImage(caso.id, result.id, file); }
          catch (err) { console.error('Comment image upload failed:', err); }
        }
      }
      setNewComment('');
      setCommentImages([]);
      await refreshDetail();
      onUpdated?.();
    } catch (err) { toast.error(err.message || 'Error'); }
    finally { setSending(false); }
  };

  const handleUploadToCase = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { toast.error('Imagen excede 5 MB'); return; }
    setUploading(true);
    try {
      await api.uploadCasoAttachment(caso.id, file);
      toast.success('Imagen adjuntada');
      await refreshDetail();
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
          <div className="flex items-center justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
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

            {/* Case Attachments */}
            {detail.attachments?.length > 0 && (
              <div>
                <h4 className="text-xs font-medium mb-1.5 flex items-center gap-1.5"><ImageIcon className="w-3.5 h-3.5" /> Adjuntos ({detail.attachments.length})</h4>
                <ImageGrid images={detail.attachments} onImageClick={setLightboxSrc} />
              </div>
            )}

            {/* Upload to case */}
            {canAttach && (
              <div>
                <input type="file" accept="image/jpeg,image/png,image/webp" onChange={handleUploadToCase} className="hidden" id="caso-upload-input" data-testid="caso-attachment-input" />
                <label htmlFor="caso-upload-input" className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium cursor-pointer transition-colors ${uploading ? 'opacity-50 pointer-events-none' : 'bg-white/[0.03] border border-white/[0.08] text-slate-400 hover:text-white hover:bg-white/[0.06]'}`}>
                  {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Camera className="w-3.5 h-3.5" />}
                  {uploading ? 'Subiendo...' : 'Adjuntar foto al caso'}
                </label>
              </div>
            )}

            {/* Comments */}
            <div>
              <h4 className="text-xs font-medium mb-2 flex items-center gap-1.5"><MessageSquare className="w-3.5 h-3.5" /> Comentarios ({detail.comments?.length || 0})</h4>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {(detail.comments || []).map((c) => (
                  <div key={c.id} className="p-2.5 rounded-xl bg-[#181B25] border border-white/[0.05]" data-testid={`comment-${c.id}`}>
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="text-xs font-medium text-white">{c.author_name}</span>
                      <span className="text-[9px] text-slate-600">{c.author_role}</span>
                      <span className="text-[9px] text-slate-600 ml-auto">{new Date(c.created_at).toLocaleString('es-ES', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <p className="text-xs text-slate-400">{c.comment}</p>
                    {/* Comment images */}
                    {c.images?.length > 0 && (
                      <ImageGrid images={c.images} onImageClick={setLightboxSrc} />
                    )}
                  </div>
                ))}
                {(!detail.comments || detail.comments.length === 0) && (
                  <p className="text-xs text-slate-600 text-center py-3">Sin comentarios</p>
                )}
              </div>
            </div>

            {/* Add comment */}
            {canComment && (
              <div className="space-y-2">
                <div className="flex gap-2">
                  <Input
                    data-testid="resident-comment-input"
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    placeholder="Comentario..."
                    className="bg-[#181B25] border-[#1E293B]"
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleAddComment()}
                  />
                  <Button size="sm" disabled={(!newComment.trim() && commentImages.length === 0) || sending} onClick={handleAddComment} data-testid="resident-send-comment">
                    {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  </Button>
                </div>
                <ImagePicker files={commentImages} setFiles={setCommentImages} maxFiles={3} />
              </div>
            )}

            {/* Delete */}
            {canDelete && (
              <Button variant="outline" size="sm" className="w-full text-red-400 border-red-500/30 hover:bg-red-500/10" onClick={handleDelete} disabled={deleting} data-testid="delete-caso-btn">
                {deleting ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Trash2 className="w-4 h-4 mr-1" />} Eliminar caso
              </Button>
            )}
          </div>
        ) : null}
      </DialogContent>
      {lightboxSrc && <ImageLightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />}
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
