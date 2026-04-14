import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/layout/DashboardLayout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';
import api from '../services/api';
import {
  Bell,
  Send,
  CheckCheck,
  Clock,
  ChevronLeft,
  ChevronRight,
  Megaphone,
  Filter,
  Loader2,
  AlertTriangle,
  Info,
  Radio,
  Settings2,
} from 'lucide-react';

const PRIORITY_COLORS = {
  low: 'text-gray-400 bg-gray-500/10',
  normal: 'text-blue-400 bg-blue-500/10',
  high: 'text-amber-400 bg-amber-500/10',
  urgent: 'text-red-400 bg-red-500/10',
};

const TYPE_ICONS = {
  broadcast: Megaphone,
  system: Settings2,
  alert: AlertTriangle,
  info: Info,
};

// ── Broadcast Form ──
const BroadcastForm = ({ onSent }) => {
  const { t } = useTranslation();
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [priority, setPriority] = useState('normal');
  const [notificationType, setNotificationType] = useState('broadcast');
  const [targetRoles, setTargetRoles] = useState([]);
  const [sending, setSending] = useState(false);

  const roles = [
    { value: 'Residente', label: t('roles.resident', 'Residente') },
    { value: 'Guarda', label: t('roles.guard', 'Guarda') },
    { value: 'Supervisor', label: t('roles.supervisor', 'Supervisor') },
    { value: 'Administrador', label: t('roles.admin', 'Administrador') },
  ];

  const toggleRole = (role) => {
    setTargetRoles((prev) =>
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !message.trim()) {
      toast.error(t('notifications.fillRequired', 'Completa los campos requeridos'));
      return;
    }
    setSending(true);
    try {
      await api.createBroadcastV2({
        title: title.trim(),
        message: message.trim(),
        notification_type: notificationType,
        priority,
        target_roles: targetRoles.length > 0 ? targetRoles : null,
      });
      toast.success(t('notifications.broadcastSent', 'Notificación enviada'));
      setTitle('');
      setMessage('');
      setPriority('normal');
      setNotificationType('broadcast');
      setTargetRoles([]);
      onSent?.();
    } catch (err) {
      toast.error(err.message || 'Error al enviar');
    } finally {
      setSending(false);
    }
  };

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-base">
          <Send className="w-4 h-4 text-primary" />
          {t('notifications.newBroadcast', 'Nueva Notificación')}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">
              {t('notifications.title', 'Título')} *
            </label>
            <Input
              data-testid="broadcast-title-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t('notifications.titlePlaceholder', 'Ej: Mantenimiento programado')}
              maxLength={200}
              className="bg-[#181B25] border-[#1E293B]"
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1 block">
              {t('notifications.message', 'Mensaje')} *
            </label>
            <textarea
              data-testid="broadcast-message-input"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder={t('notifications.messagePlaceholder', 'Escribe el mensaje de la notificación...')}
              maxLength={2000}
              rows={3}
              className="w-full rounded-md bg-[#181B25] border border-[#1E293B] text-sm px-3 py-2 text-white placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
            />
            <span className="text-[10px] text-muted-foreground">{message.length}/2000</span>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">
                {t('notifications.type', 'Tipo')}
              </label>
              <Select value={notificationType} onValueChange={setNotificationType}>
                <SelectTrigger data-testid="broadcast-type-select" className="bg-[#181B25] border-[#1E293B]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="broadcast">Broadcast</SelectItem>
                  <SelectItem value="alert">Alerta</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                  <SelectItem value="system">Sistema</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">
                {t('notifications.priority', 'Prioridad')}
              </label>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger data-testid="broadcast-priority-select" className="bg-[#181B25] border-[#1E293B]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                  <SelectItem value="low">Baja</SelectItem>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="high">Alta</SelectItem>
                  <SelectItem value="urgent">Urgente</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1 block">
              {t('notifications.targetRoles', 'Destinatarios')}
            </label>
            <div className="flex flex-wrap gap-2">
              {roles.map((r) => (
                <button
                  type="button"
                  key={r.value}
                  data-testid={`role-chip-${r.value}`}
                  onClick={() => toggleRole(r.value)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    targetRoles.includes(r.value)
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-[#181B25] text-muted-foreground border border-[#1E293B] hover:border-primary/50'
                  }`}
                >
                  {r.label}
                </button>
              ))}
            </div>
            <span className="text-[10px] text-muted-foreground mt-1 block">
              {targetRoles.length === 0
                ? t('notifications.allRoles', 'Se enviará a todos los roles')
                : `${targetRoles.length} rol(es) seleccionado(s)`}
            </span>
          </div>

          <Button
            type="submit"
            disabled={sending || !title.trim() || !message.trim()}
            data-testid="send-broadcast-btn"
            className="w-full"
          >
            {sending ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Send className="w-4 h-4 mr-2" />
            )}
            {t('notifications.send', 'Enviar Notificación')}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};

// ── Broadcast History ──
const BroadcastHistory = ({ refreshKey }) => {
  const { t } = useTranslation();
  const [broadcasts, setBroadcasts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchBroadcasts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getBroadcastHistoryV2(page);
      setBroadcasts(data.items || []);
      setTotalPages(data.total_pages || 1);
    } catch {
      setBroadcasts([]);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchBroadcasts();
  }, [fetchBroadcasts, refreshKey]);

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]">
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2 text-base">
          <Clock className="w-4 h-4 text-muted-foreground" />
          {t('notifications.broadcastHistory', 'Historial de Broadcasts')}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : broadcasts.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            {t('notifications.noHistory', 'No hay broadcasts enviados')}
          </p>
        ) : (
          <div className="space-y-3">
            {broadcasts.map((b) => (
              <div
                key={b.id}
                data-testid={`broadcast-item-${b.id}`}
                className="p-3 rounded-lg bg-[#181B25] border border-[#1E293B]/50"
              >
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-sm font-medium text-white">{b.title}</h4>
                  <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                    {new Date(b.created_at).toLocaleString('es-ES', {
                      day: '2-digit',
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{b.message}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-[10px] text-muted-foreground">
                    Por: {b.created_by_name}
                  </span>
                  {b.target_roles && b.target_roles.length > 0 && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                      {b.target_roles.join(', ')}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-4">
            <Button
              variant="ghost"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              data-testid="broadcast-prev-page"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="text-xs text-muted-foreground">
              {page} / {totalPages}
            </span>
            <Button
              variant="ghost"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              data-testid="broadcast-next-page"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// ── Notification List (for all users) ──
const NotificationList = ({ refreshKey }) => {
  const { t } = useTranslation();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filter, setFilter] = useState('all');

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getNotificationsV2(page, filter === 'unread');
      setNotifications(data.items || []);
      setTotalPages(data.total_pages || 1);
    } catch {
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, [page, filter]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications, refreshKey]);

  const handleMarkRead = async (id) => {
    try {
      await api.markNotificationV2Read(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
    } catch {
      toast.error('Error');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      const result = await api.markAllNotificationsV2Read();
      toast.success(`${result.count || 0} marcadas como leídas`);
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    } catch {
      toast.error('Error');
    }
  };

  return (
    <Card className="bg-[#0F111A] border-[#1E293B]">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <Bell className="w-4 h-4 text-primary" />
            {t('notifications.list', 'Notificaciones')}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Select value={filter} onValueChange={(v) => { setFilter(v); setPage(1); }}>
              <SelectTrigger data-testid="notif-filter-select" className="h-8 w-32 bg-[#181B25] border-[#1E293B] text-xs">
                <Filter className="w-3 h-3 mr-1" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#0F111A] border-[#1E293B]">
                <SelectItem value="all">{t('notifications.all', 'Todas')}</SelectItem>
                <SelectItem value="unread">{t('notifications.unread', 'Sin leer')}</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs text-primary"
              onClick={handleMarkAllRead}
              data-testid="mark-all-read-v2-btn"
            >
              <CheckCheck className="w-3 h-3 mr-1" />
              {t('notifications.markAllRead', 'Marcar todas')}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : notifications.length === 0 ? (
          <div className="text-center py-8">
            <Bell className="w-10 h-10 text-muted-foreground/30 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              {filter === 'unread'
                ? t('notifications.allRead', 'Todas las notificaciones están leídas')
                : t('notifications.empty', 'No hay notificaciones')}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {notifications.map((n) => {
              const TypeIcon = TYPE_ICONS[n.notification_type] || Bell;
              const priorityClass = PRIORITY_COLORS[n.priority] || PRIORITY_COLORS.normal;
              return (
                <div
                  key={n.id}
                  data-testid={`notification-v2-item-${n.id}`}
                  className={`p-3 rounded-lg border transition-colors ${
                    n.read
                      ? 'bg-[#181B25]/50 border-[#1E293B]/30'
                      : 'bg-[#181B25] border-primary/20'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${priorityClass}`}>
                      <TypeIcon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <h4 className={`text-sm ${n.read ? 'text-muted-foreground' : 'font-medium text-white'}`}>
                          {n.title}
                        </h4>
                        {!n.read && (
                          <button
                            onClick={() => handleMarkRead(n.id)}
                            className="text-[10px] text-primary hover:underline whitespace-nowrap"
                            data-testid={`mark-read-${n.id}`}
                          >
                            Marcar leída
                          </button>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                        {n.message}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className="text-[10px] text-muted-foreground">
                          {new Date(n.created_at).toLocaleString('es-ES', {
                            day: '2-digit',
                            month: 'short',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded ${priorityClass}`}>
                          {n.priority}
                        </span>
                        {n.created_by_name && (
                          <span className="text-[10px] text-muted-foreground">
                            {n.created_by_name}
                          </span>
                        )}
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
            <Button
              variant="ghost"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              data-testid="notif-prev-page"
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <span className="text-xs text-muted-foreground">
              {page} / {totalPages}
            </span>
            <Button
              variant="ghost"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              data-testid="notif-next-page"
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// ── Main Page ──
export default function NotificationsPage() {
  const { t } = useTranslation();
  const { hasRole } = useAuth();
  const isAdmin = hasRole?.('Administrador') || hasRole?.('SuperAdmin');
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <DashboardLayout title={t('notifications.pageTitle', 'Notificaciones')}>
      <div data-testid="notifications-page" className="space-y-6">
        {isAdmin && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <BroadcastForm onSent={() => setRefreshKey((k) => k + 1)} />
            <BroadcastHistory refreshKey={refreshKey} />
          </div>
        )}
        <NotificationList refreshKey={refreshKey} />
      </div>
    </DashboardLayout>
  );
}
