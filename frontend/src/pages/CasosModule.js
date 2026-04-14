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
  Inbox,
  AlertTriangle,
  Clock,
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
  Filter,
  Loader2,
  MessageSquare,
  Send,
  BarChart3,
  ArrowUpRight,
} from 'lucide-react';

const STATUS_CONFIG = {
  open: { label: 'Abierto', icon: Inbox, color: 'bg-blue-500/15 text-blue-400 border-blue-500/30' },
  review: { label: 'En revisión', icon: Clock, color: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30' },
  in_progress: { label: 'En progreso', icon: ArrowUpRight, color: 'bg-purple-500/15 text-purple-400 border-purple-500/30' },
  closed: { label: 'Cerrado', icon: CheckCircle, color: 'bg-green-500/15 text-green-400 border-green-500/30' },
  rejected: { label: 'Rechazado', icon: XCircle, color: 'bg-red-500/15 text-red-400 border-red-500/30' },
};

const PRIORITY_CONFIG = {
  low: { label: 'Baja', color: 'bg-gray-500/15 text-gray-400' },
  medium: { label: 'Media', color: 'bg-blue-500/15 text-blue-400' },
  high: { label: 'Alta', color: 'bg-amber-500/15 text-amber-400' },
  urgent: { label: 'Urgente', color: 'bg-red-500/15 text-red-400' },
};

const CATEGORY_LABELS = {
  mantenimiento: 'Mantenimiento',
  seguridad: 'Seguridad',
  ruido: 'Ruido',
  limpieza: 'Limpieza',
  infraestructura: 'Infraestructura',
  convivencia: 'Convivencia',
  otro: 'Otro',
};

// ── Stats Cards ──
const StatsCards = ({ stats }) => {
  if (!stats) return null;
  const cards = [
    { label: 'Total', value: stats.total, color: 'text-white' },
    { label: 'Abiertos', value: stats.open, color: 'text-blue-400' },
    { label: 'En progreso', value: stats.in_progress, color: 'text-purple-400' },
    { label: 'Cerrados', value: stats.closed, color: 'text-green-400' },
    { label: 'Urgentes', value: stats.urgent, color: 'text-red-400' },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3" data-testid="casos-stats">
      {cards.map((c) => (
        <Card key={c.label} className="bg-[#0F111A] border-[#1E293B]">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">{c.label}</p>
            <p className={`text-2xl font-bold ${c.color}`}>{c.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

// ── Case Detail Dialog ──
const CaseDetailDialog = ({ caso, open, onClose, onUpdated }) => {
  const [newComment, setNewComment] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [sending, setSending] = useState(false);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);

  useEffect(() => {
    if (caso && open) {
      setLoading(true);
      api.getCasoDetail(caso.id)
        .then((d) => setDetail(d))
        .catch(() => toast.error('Error al cargar detalle'))
        .finally(() => setLoading(false));
    }
  }, [caso, open]);

  const handleStatusChange = async (newStatus) => {
    setUpdatingStatus(true);
    try {
      await api.updateCaso(caso.id, { status: newStatus });
      toast.success('Estado actualizado');
      const d = await api.getCasoDetail(caso.id);
      setDetail(d);
      onUpdated?.();
    } catch (err) {
      toast.error(err.message || 'Error');
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) return;
    setSending(true);
    try {
      await api.addCasoComment(caso.id, { comment: newComment.trim(), is_internal: isInternal });
      setNewComment('');
      setIsInternal(false);
      const d = await api.getCasoDetail(caso.id);
      setDetail(d);
      onUpdated?.();
    } catch (err) {
      toast.error(err.message || 'Error');
    } finally {
      setSending(false);
    }
  };

  const statusCfg = STATUS_CONFIG[detail?.status] || STATUS_CONFIG.open;
  const priorityCfg = PRIORITY_CONFIG[detail?.priority] || PRIORITY_CONFIG.medium;

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="bg-[#0F111A] border-[#1E293B] max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="caso-detail-dialog">
        <DialogHeader>
          <DialogTitle className="text-base">{detail?.title || caso?.title}</DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : detail ? (
          <div className="space-y-4">
            {/* Meta */}
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" className={statusCfg.color}>{statusCfg.label}</Badge>
              <Badge variant="outline" className={priorityCfg.color}>{priorityCfg.label}</Badge>
              <Badge variant="outline" className="bg-[#181B25] text-muted-foreground border-[#1E293B]">
                {CATEGORY_LABELS[detail.category] || detail.category}
              </Badge>
            </div>

            {/* Description */}
            <div className="p-3 rounded-lg bg-[#181B25] border border-[#1E293B]/50">
              <p className="text-sm text-white whitespace-pre-wrap">{detail.description}</p>
              <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
                <span>Por: {detail.created_by_name}</span>
                <span>{new Date(detail.created_at).toLocaleString('es-ES')}</span>
              </div>
            </div>

            {/* Status Actions */}
            <div className="flex flex-wrap gap-2">
              <span className="text-xs text-muted-foreground self-center mr-1">Cambiar estado:</span>
              {Object.entries(STATUS_CONFIG).map(([key, cfg]) => (
                <Button
                  key={key}
                  variant="outline"
                  size="sm"
                  disabled={detail.status === key || updatingStatus}
                  onClick={() => handleStatusChange(key)}
                  className={`text-xs h-7 ${detail.status === key ? cfg.color : ''}`}
                  data-testid={`status-btn-${key}`}
                >
                  {cfg.label}
                </Button>
              ))}
            </div>

            {/* Comments */}
            <div>
              <h4 className="text-sm font-medium mb-2 flex items-center gap-1.5">
                <MessageSquare className="w-4 h-4" />
                Comentarios ({detail.comments?.length || 0})
              </h4>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {(detail.comments || []).map((c) => (
                  <div
                    key={c.id}
                    data-testid={`comment-${c.id}`}
                    className={`p-2.5 rounded-lg text-sm ${
                      c.is_internal
                        ? 'bg-amber-500/5 border border-amber-500/20'
                        : 'bg-[#181B25] border border-[#1E293B]/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium">
                        {c.author_name}
                        <span className="text-muted-foreground ml-1">({c.author_role})</span>
                      </span>
                      {c.is_internal && (
                        <Badge variant="outline" className="text-[9px] h-4 bg-amber-500/10 text-amber-400 border-amber-500/30">
                          Interno
                        </Badge>
                      )}
                    </div>
                    <p className="text-muted-foreground">{c.comment}</p>
                    <span className="text-[10px] text-muted-foreground mt-1 block">
                      {new Date(c.created_at).toLocaleString('es-ES')}
                    </span>
                  </div>
                ))}
                {(!detail.comments || detail.comments.length === 0) && (
                  <p className="text-xs text-muted-foreground text-center py-4">Sin comentarios</p>
                )}
              </div>
            </div>

            {/* Add Comment */}
            <div className="flex gap-2">
              <div className="flex-1">
                <Input
                  data-testid="comment-input"
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Agregar comentario..."
                  className="bg-[#181B25] border-[#1E293B]"
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleAddComment()}
                />
                <label className="flex items-center gap-1.5 mt-1 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isInternal}
                    onChange={(e) => setIsInternal(e.target.checked)}
                    className="rounded border-[#1E293B]"
                    data-testid="internal-comment-checkbox"
                  />
                  <span className="text-[10px] text-muted-foreground">Nota interna (solo admins)</span>
                </label>
              </div>
              <Button
                size="sm"
                disabled={!newComment.trim() || sending}
                onClick={handleAddComment}
                data-testid="send-comment-btn"
              >
                {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </Button>
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
};

// ── Main Page ──
export default function CasosModule() {
  const { t } = useTranslation();
  const [cases, setCases] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterPriority, setFilterPriority] = useState('all');
  const [selectedCaso, setSelectedCaso] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, page_size: 15 };
      if (filterStatus !== 'all') params.status = filterStatus;
      if (filterPriority !== 'all') params.priority = filterPriority;

      const [casosData, statsData] = await Promise.all([
        api.getCasos(params),
        api.getCasosStats(),
      ]);
      setCases(casosData.items || []);
      setTotalPages(casosData.total_pages || 1);
      setStats(statsData);
    } catch {
      setCases([]);
    } finally {
      setLoading(false);
    }
  }, [page, filterStatus, filterPriority]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <DashboardLayout title={t('casos.pageTitle', 'Casos / Incidencias')}>
      <div data-testid="casos-module" className="space-y-6">
        <StatsCards stats={stats} />

        {/* Filters */}
        <Card className="bg-[#0F111A] border-[#1E293B]">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <BarChart3 className="w-4 h-4 text-primary" />
                {t('casos.list', 'Lista de Casos')}
              </CardTitle>
              <div className="flex items-center gap-2">
                <Select value={filterStatus} onValueChange={(v) => { setFilterStatus(v); setPage(1); }}>
                  <SelectTrigger data-testid="filter-status" className="h-8 w-32 bg-[#181B25] border-[#1E293B] text-xs">
                    <Filter className="w-3 h-3 mr-1" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                    <SelectItem value="all">Todos</SelectItem>
                    <SelectItem value="open">Abierto</SelectItem>
                    <SelectItem value="review">En revisión</SelectItem>
                    <SelectItem value="in_progress">En progreso</SelectItem>
                    <SelectItem value="closed">Cerrado</SelectItem>
                    <SelectItem value="rejected">Rechazado</SelectItem>
                  </SelectContent>
                </Select>
                <Select value={filterPriority} onValueChange={(v) => { setFilterPriority(v); setPage(1); }}>
                  <SelectTrigger data-testid="filter-priority" className="h-8 w-28 bg-[#181B25] border-[#1E293B] text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                    <SelectItem value="all">Prioridad</SelectItem>
                    <SelectItem value="low">Baja</SelectItem>
                    <SelectItem value="medium">Media</SelectItem>
                    <SelectItem value="high">Alta</SelectItem>
                    <SelectItem value="urgent">Urgente</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
              </div>
            ) : cases.length === 0 ? (
              <div className="text-center py-8">
                <Inbox className="w-10 h-10 text-muted-foreground/30 mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">No hay casos registrados</p>
              </div>
            ) : (
              <div className="space-y-2">
                {cases.map((c) => {
                  const sCfg = STATUS_CONFIG[c.status] || STATUS_CONFIG.open;
                  const pCfg = PRIORITY_CONFIG[c.priority] || PRIORITY_CONFIG.medium;
                  const StatusIcon = sCfg.icon;
                  return (
                    <div
                      key={c.id}
                      data-testid={`caso-row-${c.id}`}
                      onClick={() => setSelectedCaso(c)}
                      className="p-3 rounded-lg bg-[#181B25] border border-[#1E293B]/50 hover:border-primary/30 cursor-pointer transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${sCfg.color}`}>
                          <StatusIcon className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <h4 className="text-sm font-medium text-white truncate">{c.title}</h4>
                            <div className="flex items-center gap-1.5 flex-shrink-0">
                              <Badge variant="outline" className={`text-[10px] h-5 ${pCfg.color}`}>{pCfg.label}</Badge>
                              <Badge variant="outline" className={`text-[10px] h-5 ${sCfg.color}`}>{sCfg.label}</Badge>
                            </div>
                          </div>
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{c.description}</p>
                          <div className="flex items-center gap-3 mt-1.5 text-[10px] text-muted-foreground">
                            <span>{c.created_by_name}</span>
                            <span>{CATEGORY_LABELS[c.category] || c.category}</span>
                            <span>
                              {new Date(c.created_at).toLocaleString('es-ES', {
                                day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
                              })}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-4">
                <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} data-testid="casos-prev-page">
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-xs text-muted-foreground">{page} / {totalPages}</span>
                <Button variant="ghost" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)} data-testid="casos-next-page">
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Detail Dialog */}
        {selectedCaso && (
          <CaseDetailDialog
            caso={selectedCaso}
            open={!!selectedCaso}
            onClose={() => setSelectedCaso(null)}
            onUpdated={fetchData}
          />
        )}
      </div>
    </DashboardLayout>
  );
}
