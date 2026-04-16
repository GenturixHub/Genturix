/**
 * GENTURIX - Resident Layout (Refactored)
 * 
 * Mobile-first layout with:
 * - Clean 4-item bottom nav (Emergency, Home, Notifications, Profile)
 * - Slide-out drawer for all modules (Visits, Reservations, Directory, Cases, Docs, Finances)
 * - Hamburger menu in header
 */

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  Shield, LogOut, Users, Calendar, User, AlertTriangle, Bell,
  RefreshCw, CheckCheck, UserCheck, Check, ClipboardList, FolderOpen,
  Wallet, Menu, X, Home, ChevronRight, Landmark,
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import {
  Sheet, SheetContent, SheetHeader, SheetTitle,
} from '../../components/ui/sheet';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
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

  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Notifications state
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

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

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

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

  const handleMarkAllRead = async (e) => {
    e?.stopPropagation();
    if (unreadCount === 0) return;
    try {
      await api.markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({...n, read: true})));
      setUnreadCount(0);
      toast.success(t('notifications.allMarkedRead', 'Notificaciones marcadas como leidas'));
    } catch (error) {
      toast.error('Error al marcar notificaciones');
    }
  };

  const handleRefresh = async (e) => {
    e?.stopPropagation();
    setIsRefreshing(true);
    await fetchNotifications();
    setIsRefreshing(false);
  };

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

  // Bottom nav: 4 items only
  const BOTTOM_NAV_ITEMS = useMemo(() => [
    { 
      id: 'emergency', 
      label: t('resident.emergency', 'Emergencia'), 
      icon: AlertTriangle,
      bgColor: 'bg-red-600',
      glowColor: 'shadow-red-500/40'
    },
    { id: 'home', label: t('resident.home', 'Inicio'), icon: Home },
    { id: 'notifications', label: t('resident.notifications', 'Alertas'), icon: Bell },
    { id: 'profile', label: t('resident.profile', 'Perfil'), icon: User },
  ], [t]);

  // Drawer menu items (modules)
  const DRAWER_ITEMS = useMemo(() => [
    { id: 'visits', label: t('resident.visits', 'Visitas'), icon: Users, color: 'text-blue-400', bg: 'bg-blue-500/10' },
    { id: 'reservations', label: t('resident.reservations', 'Reservas'), icon: Calendar, color: 'text-green-400', bg: 'bg-green-500/10' },
    { id: 'directory', label: t('resident.directory', 'Directorio'), icon: UserCheck, color: 'text-purple-400', bg: 'bg-purple-500/10' },
    { id: 'casos', label: t('casos.tab', 'Casos'), icon: ClipboardList, color: 'text-orange-400', bg: 'bg-orange-500/10' },
    { id: 'documentos', label: t('documentos.tab', 'Documentos'), icon: FolderOpen, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
    { id: 'finanzas', label: t('finanzas.tab', 'Finanzas'), icon: Wallet, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { id: 'asamblea', label: t('asamblea.tab', 'Asamblea'), icon: Landmark, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  ], [t]);

  const handleBottomNavChange = useCallback((tabId) => {
    if (tabId === 'notifications') {
      // Open notifications dropdown instead of tab
      setIsNotificationsOpen(true);
      return;
    }
    if (tabId === 'home') {
      onTabChange('visits');
      return;
    }
    onTabChange(tabId);
  }, [onTabChange]);

  const handleDrawerItemClick = useCallback((itemId) => {
    setIsDrawerOpen(false);
    onTabChange(itemId);
  }, [onTabChange]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Determine which bottom nav item is "active"
  const activeBottomTab = useMemo(() => {
    if (activeTab === 'emergency') return 'emergency';
    if (activeTab === 'profile') return 'profile';
    if (activeTab === 'visits') return 'home';
    // For drawer modules, highlight "home" as the closest
    return 'home';
  }, [activeTab]);

  return (
    <div 
      className="bg-[#05050A] flex flex-col w-full"
      style={{ height: '100dvh', maxHeight: '100dvh', overflow: 'hidden' }}
    >
      {/* Header */}
      <header 
        className="z-40 bg-[#0A0A0F]/95 backdrop-blur-lg border-b border-[#1E293B]/60 flex-shrink-0"
        style={{ height: '56px', minHeight: '56px' }}
      >
        <div className="flex items-center justify-between h-full px-3">
          {/* Hamburger + Logo */}
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <button
              onClick={() => setIsDrawerOpen(true)}
              className="w-10 h-10 min-h-[44px] min-w-[44px] rounded-xl bg-white/5 border border-[#1E293B]/60 text-muted-foreground hover:text-white hover:bg-white/10 transition-all duration-150 active:scale-95 flex items-center justify-center"
              data-testid="drawer-toggle"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="min-w-0 flex-1">
              <h1 className="text-sm font-bold text-white">{title}</h1>
              <p className="text-xs text-muted-foreground truncate">{user?.full_name}</p>
            </div>
          </div>
          
          {/* Notifications Bell + Logout */}
          <div className="flex items-center gap-1 flex-shrink-0">
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
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0" onClick={handleRefresh} disabled={isRefreshing}>
                      <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                    </Button>
                    {unreadCount > 0 && (
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-primary" onClick={handleMarkAllRead}>
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
                          notif.type === 'visitor_arrival' ? 'bg-green-500/20 text-green-400' : 'bg-orange-500/20 text-orange-400'
                        }`}>
                          {notif.type === 'visitor_arrival' ? <UserCheck className="w-4 h-4" /> : <LogOut className="w-4 h-4" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm line-clamp-2 ${notif.read ? 'text-muted-foreground' : 'text-white'}`}>{notif.message}</p>
                          <p className="text-[10px] text-muted-foreground mt-1">
                            {new Date(notif.created_at).toLocaleString('es-MX', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' })}
                          </p>
                        </div>
                        {!notif.read && (
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0 flex-shrink-0" onClick={(e) => handleMarkRead(notif.id, e)}>
                            <Check className="w-3.5 h-3.5" />
                          </Button>
                        )}
                      </DropdownMenuItem>
                    ))}
                  </div>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
            
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

      {/* Content */}
      <main className="flex-1 min-h-0 flex flex-col" style={{ overflow: 'hidden' }}>
        {children}
      </main>

      {/* Bottom Navigation — 4 clean items */}
      <MobileBottomNav 
        items={BOTTOM_NAV_ITEMS}
        activeTab={activeBottomTab}
        onTabChange={handleBottomNavChange}
        centerIndex={0}
      />

      {/* Drawer Menu — Modules */}
      <Sheet open={isDrawerOpen} onOpenChange={setIsDrawerOpen}>
        <SheetContent side="left" className="w-[280px] bg-[#0A0A0F] border-r border-[#1E293B] p-0" data-testid="module-drawer">
          <SheetHeader className="px-4 pt-5 pb-3 border-b border-[#1E293B]/60">
            <SheetTitle className="text-left text-base font-bold text-white">
              {t('drawer.modules', 'Modulos')}
            </SheetTitle>
          </SheetHeader>
          <nav className="p-3 space-y-1.5" data-testid="drawer-nav">
            {DRAWER_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleDrawerItemClick(item.id)}
                  disabled={item.disabled}
                  data-testid={`drawer-item-${item.id}`}
                  className={`w-full flex items-center gap-3 px-3 py-3.5 rounded-xl transition-all duration-150 min-h-[52px]
                    ${item.disabled 
                      ? 'opacity-30 cursor-not-allowed' 
                      : isActive 
                        ? 'bg-primary/10 border border-primary/20' 
                        : 'hover:bg-white/5 active:scale-[0.98]'
                    }`}
                >
                  <div className={`w-10 h-10 rounded-lg ${item.bg} flex items-center justify-center flex-shrink-0`}>
                    <Icon className={`w-5 h-5 ${item.color}`} />
                  </div>
                  <span className={`text-sm font-medium flex-1 text-left ${isActive ? 'text-white' : item.disabled ? 'text-muted-foreground/40' : 'text-white/80'}`}>
                    {item.label}
                  </span>
                  {item.disabled ? (
                    <span className="text-[9px] text-muted-foreground/40 bg-white/5 px-1.5 py-0.5 rounded">Pronto</span>
                  ) : (
                    <ChevronRight className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-primary' : 'text-muted-foreground/30'}`} />
                  )}
                </button>
              );
            })}
          </nav>
          {/* Drawer footer */}
          <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-[#1E293B]/60">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-primary/20 flex items-center justify-center text-primary text-sm font-bold">
                {user?.full_name?.charAt(0)?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{user?.full_name}</p>
                <p className="text-[10px] text-muted-foreground truncate">{user?.apartment || ''}</p>
              </div>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default ResidentLayout;
