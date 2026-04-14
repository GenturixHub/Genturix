/**
 * GENTURIX - Resident Layout (i18n)
 * 
 * Independent mobile-first layout for Resident role.
 * Completely decoupled from DashboardLayout.
 * Designed as native app experience.
 * Full i18n support.
 */

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Shield, LogOut, Users, Calendar, User, AlertTriangle, Bell, RefreshCw, CheckCheck, UserCheck, Check, ClipboardList, FolderOpen, Wallet } from 'lucide-react';
import { Button } from '../../components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../../components/ui/dropdown-menu';
import MobileBottomNav from '../../components/layout/BottomNav.js';
import api from '../../services/api';
import { toast } from 'sonner';

const ResidentLayout = ({ 
  children, 
  activeTab, 
  onTabChange, 
  title = 'GENTURIX'
}) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  // Notifications state
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Fetch notifications
  const fetchNotifications = useCallback(async () => {
    try {
      const [notifs, countData] = await Promise.all([
        api.getVisitorNotifications(),
        api.get('/resident/visitor-notifications/unread-count')
      ]);
      setNotifications(Array.isArray(notifs) ? notifs.slice(0, 20) : []);
      setUnreadCount(countData?.count || 0);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    }
  }, []);

  // Initial fetch and polling
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // Mark notification as read
  const handleMarkRead = async (notificationId, e) => {
    e?.stopPropagation();
    try {
      await api.markNotificationRead(notificationId);
      setNotifications(prev => prev.map(n => n.id === notificationId ? {...n, read: true} : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Error marking notification read:', error);
    }
  };

  // Mark all as read
  const handleMarkAllRead = async (e) => {
    e?.stopPropagation();
    if (unreadCount === 0) return;
    try {
      await api.markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({...n, read: true})));
      setUnreadCount(0);
      toast.success(t('notifications.allMarkedRead', 'Notificaciones marcadas como leídas'));
    } catch (error) {
      toast.error('Error al marcar notificaciones');
    }
  };

  // Refresh notifications
  const handleRefresh = async (e) => {
    e?.stopPropagation();
    setIsRefreshing(true);
    await fetchNotifications();
    setIsRefreshing(false);
    toast.success(t('notifications.refreshed', 'Notificaciones actualizadas'));
  };

  // Auto mark as read when dropdown opens
  const handleDropdownOpenChange = async (open) => {
    setIsNotificationsOpen(open);
    if (open && unreadCount > 0) {
      setTimeout(async () => {
        try {
          await api.markAllNotificationsRead();
          setNotifications(prev => prev.map(n => ({...n, read: true})));
          setUnreadCount(0);
        } catch (error) {
          console.error('Error marking all as read:', error);
        }
      }, 3000);
    }
  };

  // Navigation items with translations
  const RESIDENT_NAV_ITEMS = useMemo(() => [
    { 
      id: 'emergency', 
      label: t('resident.emergency'), 
      icon: AlertTriangle,
      bgColor: 'bg-red-600',
      glowColor: 'shadow-red-500/40'
    },
    { id: 'visits', label: t('resident.visits'), icon: Users },
    { id: 'casos', label: t('casos.tab', 'Casos'), icon: ClipboardList },
    { id: 'finanzas', label: t('finanzas.tab', 'Finanzas'), icon: Wallet },
    { id: 'profile', label: t('resident.profile'), icon: User },
  ], [t]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div 
      className="bg-[#05050A] flex flex-col w-full"
      style={{ 
        height: '100dvh',
        maxHeight: '100dvh',
        overflow: 'hidden'
      }}
    >
      {/* Header - Compact, fixed height */}
      <header 
        className="z-40 bg-[#0A0A0F]/95 backdrop-blur-lg border-b border-[#1E293B]/60 flex-shrink-0"
        style={{ height: '56px', minHeight: '56px' }}
      >
        <div className="flex items-center justify-between h-full px-3">
          {/* Logo & User */}
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center flex-shrink-0">
              <Shield className="w-4 h-4 text-primary" />
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="text-sm font-bold text-white">{title}</h1>
              <p className="text-xs text-muted-foreground truncate">{user?.full_name}</p>
            </div>
          </div>
          
          {/* Notifications Bell + Logout */}
          <div className="flex items-center gap-1 flex-shrink-0">
            {/* Notifications Dropdown */}
            <DropdownMenu open={isNotificationsOpen} onOpenChange={handleDropdownOpenChange}>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="relative h-11 w-11 min-h-[44px] min-w-[44px] rounded-xl"
                  data-testid="resident-notifications-btn"
                >
                  <Bell className="w-5 h-5" />
                  {unreadCount > 0 && (
                    <span 
                      className="absolute top-1.5 right-1.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-[10px] font-bold flex items-center justify-center animate-pulse"
                      data-testid="resident-notification-badge"
                    >
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                  )}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-[calc(100vw-2rem)] max-w-sm bg-[#0F111A] border-[#1E293B]">
                <DropdownMenuLabel className="flex items-center justify-between px-3 py-2">
                  <span className="text-sm">{t('notifications.title', 'Notificaciones')}</span>
                  <div className="flex items-center gap-1.5">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-8 w-8 p-0"
                      onClick={handleRefresh}
                      disabled={isRefreshing}
                    >
                      <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                    </Button>
                    {unreadCount > 0 && (
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-8 w-8 p-0 text-primary"
                        onClick={handleMarkAllRead}
                        title={t('notifications.markAllRead', 'Marcar todas como leídas')}
                      >
                        <CheckCheck className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-[#1E293B]" />
                {notifications.length === 0 ? (
                  <div className="p-6 text-center text-sm text-muted-foreground">
                    <Bell className="w-10 h-10 mx-auto mb-3 opacity-30" />
                    {t('notifications.empty', 'No tienes notificaciones')}
                  </div>
                ) : (
                  <div className="max-h-[60vh] overflow-y-auto overscroll-contain">
                    {notifications.map((notif) => (
                      <DropdownMenuItem 
                        key={notif.id} 
                        className={`flex items-start gap-3 py-3 px-3 min-h-[60px] cursor-pointer ${!notif.read ? 'bg-primary/5' : ''}`}
                      >
                        <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${
                          notif.type === 'visitor_arrival' 
                            ? 'bg-green-500/20 text-green-400' 
                            : 'bg-orange-500/20 text-orange-400'
                        }`}>
                          {notif.type === 'visitor_arrival' ? (
                            <UserCheck className="w-4 h-4" />
                          ) : (
                            <LogOut className="w-4 h-4" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm line-clamp-2 ${notif.read ? 'text-muted-foreground' : 'text-white'}`}>
                            {notif.message}
                          </p>
                          <p className="text-[10px] text-muted-foreground mt-1">
                            {new Date(notif.created_at).toLocaleString('es-MX', { 
                              hour: '2-digit', 
                              minute: '2-digit',
                              day: '2-digit',
                              month: 'short'
                            })}
                          </p>
                        </div>
                        {!notif.read && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0 flex-shrink-0"
                            onClick={(e) => handleMarkRead(notif.id, e)}
                          >
                            <Check className="w-3.5 h-3.5" />
                          </Button>
                        )}
                      </DropdownMenuItem>
                    ))}
                  </div>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
            
            {/* Logout */}
            <button
              onClick={handleLogout}
              className="p-2.5 min-h-[44px] min-w-[44px] rounded-xl text-muted-foreground hover:text-white hover:bg-white/5 transition-colors flex items-center justify-center"
              data-testid="logout-btn"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Content - Full height container for carousel */}
      <main 
        className="flex-1 min-h-0 flex flex-col"
        style={{ overflow: 'hidden' }}
      >
        {children}
      </main>

      {/* Bottom Navigation - Fixed, app-style */}
      <MobileBottomNav 
        items={RESIDENT_NAV_ITEMS}
        activeTab={activeTab}
        onTabChange={onTabChange}
        centerIndex={0}
      />
    </div>
  );
};

export default ResidentLayout;
