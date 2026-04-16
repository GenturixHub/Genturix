/**
 * GENTURIX — Resident Layout (Premium SaaS Redesign)
 * 
 * Dark jewel theme with glassmorphism, neon accents.
 * Bottom nav: Emergency (red glow), Home, Cases, Profile
 * Sidebar drawer for secondary modules.
 * Notification bell in header (no Alerts tab).
 */
import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  Shield, LogOut, Users, Calendar, User, AlertTriangle, Bell,
  RefreshCw, CheckCheck, UserCheck, Check, ClipboardList, FolderOpen,
  Wallet, Menu, Home, ChevronRight, Landmark, Siren,
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import {
  Sheet, SheetContent, SheetHeader, SheetTitle,
} from '../../components/ui/sheet';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from '../../components/ui/dropdown-menu';
import api from '../../services/api';
import { toast } from 'sonner';

// ── Design tokens ──
const BG = '#06080D';
const SURFACE = '#11141D';
const GLASS = 'rgba(255,255,255,0.03)';
const BORDER = 'rgba(255,255,255,0.08)';
const ACCENT = '#06B6D4';

const ResidentLayout = ({ children, activeTab, onTabChange, title = 'GENTURIX' }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Notifications
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchNotifications = useCallback(async () => {
    try {
      const [notifs, countData] = await Promise.all([
        api.getVisitorNotifications(),
        api.get('/resident/visitor-notifications/unread-count'),
      ]);
      setNotifications(Array.isArray(notifs) ? notifs.slice(0, 20) : []);
      setUnreadCount(countData?.count || 0);
    } catch {}
  }, []);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  const handleMarkAllRead = async (e) => {
    e?.stopPropagation();
    if (unreadCount === 0) return;
    try {
      await api.markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      setUnreadCount(0);
    } catch {}
  };

  const handleDropdownOpenChange = (open) => {
    setIsNotificationsOpen(open);
    if (open && unreadCount > 0) {
      setTimeout(async () => {
        try {
          await api.markAllNotificationsRead();
          setNotifications(prev => prev.map(n => ({ ...n, read: true })));
          setUnreadCount(0);
        } catch {}
      }, 3000);
    }
  };

  const handleRefresh = async (e) => {
    e?.stopPropagation();
    setIsRefreshing(true);
    await fetchNotifications();
    setIsRefreshing(false);
  };

  // Drawer items
  const DRAWER_ITEMS = useMemo(() => [
    { id: 'visits', label: 'Visitas', icon: Users, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
    { id: 'reservations', label: 'Reservas', icon: Calendar, color: 'text-violet-400', bg: 'bg-violet-500/10' },
    { id: 'directory', label: 'Directorio', icon: UserCheck, color: 'text-purple-400', bg: 'bg-purple-500/10' },
    { id: 'documentos', label: 'Documentos', icon: FolderOpen, color: 'text-teal-400', bg: 'bg-teal-500/10' },
    { id: 'finanzas', label: 'Finanzas', icon: Wallet, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { id: 'asamblea', label: 'Asamblea', icon: Landmark, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  ], []);

  // Bottom nav: Emergency, Home, Cases, Profile
  const handleBottomNav = useCallback((tabId) => {
    if (tabId === 'home') {
      onTabChange('visits');
      return;
    }
    onTabChange(tabId);
  }, [onTabChange]);

  const handleDrawerClick = useCallback((id) => {
    setIsDrawerOpen(false);
    onTabChange(id);
  }, [onTabChange]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Active bottom tab mapping
  const activeBottomTab = useMemo(() => {
    if (activeTab === 'emergency') return 'emergency';
    if (activeTab === 'casos') return 'casos';
    if (activeTab === 'profile') return 'profile';
    return 'home';
  }, [activeTab]);

  return (
    <div
      className="flex flex-col w-full"
      style={{ height: '100dvh', maxHeight: '100dvh', overflow: 'hidden', background: BG, fontFamily: "'Manrope', sans-serif" }}
    >
      {/* ═══ HEADER ═══ */}
      <header
        className="z-40 flex-shrink-0 backdrop-blur-2xl"
        style={{
          height: '60px', minHeight: '60px',
          background: 'rgba(6,8,13,0.75)',
          borderBottom: `1px solid ${BORDER}`,
        }}
      >
        <div className="flex items-center justify-between h-full px-4">
          {/* Left: Hamburger + Title */}
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <button
              onClick={() => setIsDrawerOpen(true)}
              className="w-10 h-10 rounded-2xl flex items-center justify-center text-slate-400 hover:text-white transition-all active:scale-95"
              style={{ background: GLASS, border: `1px solid ${BORDER}` }}
              data-testid="drawer-toggle"
            >
              <Menu className="w-5 h-5" strokeWidth={1.5} />
            </button>
            <div className="min-w-0 flex-1">
              <h1 className="text-sm font-bold tracking-tight text-white" style={{ fontFamily: "'Outfit', sans-serif" }}>
                {title}
              </h1>
              <p className="text-[11px] text-slate-500 truncate">{user?.full_name}</p>
            </div>
          </div>

          {/* Right: Bell + Logout */}
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <DropdownMenu open={isNotificationsOpen} onOpenChange={handleDropdownOpenChange}>
              <DropdownMenuTrigger asChild>
                <button
                  className="relative w-10 h-10 rounded-2xl flex items-center justify-center text-slate-400 hover:text-white transition-all active:scale-95"
                  style={{ background: GLASS, border: `1px solid ${BORDER}` }}
                  data-testid="resident-notifications-btn"
                >
                  <Bell className="w-5 h-5" strokeWidth={1.5} />
                  {unreadCount > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-[9px] font-bold flex items-center justify-center animate-pulse" data-testid="resident-notification-badge">
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                  )}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-[calc(100vw-2rem)] max-w-sm border-white/10" style={{ background: SURFACE }}>
                <DropdownMenuLabel className="flex items-center justify-between px-3 py-2">
                  <span className="text-sm text-white">Notificaciones</span>
                  <div className="flex items-center gap-1.5">
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={handleRefresh} disabled={isRefreshing}>
                      <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                    </Button>
                    {unreadCount > 0 && (
                      <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-cyan-400" onClick={handleMarkAllRead}>
                        <CheckCheck className="w-3.5 h-3.5" />
                      </Button>
                    )}
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-white/5" />
                {notifications.length === 0 ? (
                  <div className="p-6 text-center text-sm text-slate-500">
                    <Bell className="w-8 h-8 mx-auto mb-2 opacity-20" />
                    Sin notificaciones
                  </div>
                ) : (
                  <div className="max-h-[50vh] overflow-y-auto">
                    {notifications.map((n) => (
                      <DropdownMenuItem key={n.id} className={`py-3 px-3 min-h-[52px] cursor-pointer ${!n.read ? 'bg-cyan-500/5' : ''}`}>
                        <div className="flex-1 min-w-0">
                          <p className={`text-xs line-clamp-2 ${n.read ? 'text-slate-500' : 'text-white'}`}>{n.message}</p>
                          <p className="text-[10px] text-slate-600 mt-1">
                            {new Date(n.created_at).toLocaleString('es-MX', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' })}
                          </p>
                        </div>
                      </DropdownMenuItem>
                    ))}
                  </div>
                )}
              </DropdownMenuContent>
            </DropdownMenu>

            <button
              onClick={handleLogout}
              className="w-10 h-10 rounded-2xl flex items-center justify-center text-slate-500 hover:text-white transition-all active:scale-95"
              style={{ background: GLASS, border: `1px solid ${BORDER}` }}
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4" strokeWidth={1.5} />
            </button>
          </div>
        </div>
      </header>

      {/* ═══ CONTENT ═══ */}
      <main className="flex-1 min-h-0 flex flex-col" style={{ overflow: 'hidden' }}>
        {children}
      </main>

      {/* ═══ BOTTOM NAV ═══ */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 backdrop-blur-2xl"
        style={{
          height: '80px',
          background: 'rgba(6,8,13,0.85)',
          borderTop: `1px solid ${BORDER}`,
          paddingBottom: 'env(safe-area-inset-bottom, 0px)',
        }}
        data-testid="mobile-bottom-nav"
      >
        <div className="flex items-center justify-around h-full px-4">
          {/* Emergency */}
          <button
            onClick={() => handleBottomNav('emergency')}
            data-testid="mobile-nav-emergency"
            className="relative flex flex-col items-center justify-center -mt-5 active:scale-95 transition-transform"
          >
            <div
              className={`w-16 h-16 rounded-full flex items-center justify-center transition-all ${
                activeBottomTab === 'emergency' ? 'ring-2 ring-red-400/30 scale-105' : ''
              }`}
              style={{
                background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
                boxShadow: '0 0 28px rgba(239,68,68,0.45), 0 0 8px rgba(239,68,68,0.2)',
              }}
            >
              <Siren className="w-7 h-7 text-white" strokeWidth={2} />
            </div>
            <span className="text-[10px] font-medium text-red-400 mt-1">SOS</span>
          </button>

          {/* Home */}
          <button
            onClick={() => handleBottomNav('home')}
            data-testid="mobile-nav-home"
            className={`flex flex-col items-center justify-center py-2 min-h-[60px] transition-all active:scale-95 ${
              activeBottomTab === 'home' ? 'text-cyan-400' : 'text-slate-500'
            }`}
          >
            <div className={`w-11 h-11 rounded-2xl flex items-center justify-center mb-0.5 transition-all ${
              activeBottomTab === 'home' ? 'bg-cyan-500/15' : ''
            }`}>
              <Home className="w-[22px] h-[22px]" strokeWidth={1.5} />
            </div>
            <span className="text-[10px] font-medium">Inicio</span>
          </button>

          {/* Cases */}
          <button
            onClick={() => handleBottomNav('casos')}
            data-testid="mobile-nav-casos"
            className={`flex flex-col items-center justify-center py-2 min-h-[60px] transition-all active:scale-95 ${
              activeBottomTab === 'casos' ? 'text-cyan-400' : 'text-slate-500'
            }`}
          >
            <div className={`w-11 h-11 rounded-2xl flex items-center justify-center mb-0.5 transition-all ${
              activeBottomTab === 'casos' ? 'bg-cyan-500/15' : ''
            }`}>
              <ClipboardList className="w-[22px] h-[22px]" strokeWidth={1.5} />
            </div>
            <span className="text-[10px] font-medium">Casos</span>
          </button>

          {/* Profile */}
          <button
            onClick={() => handleBottomNav('profile')}
            data-testid="mobile-nav-profile"
            className={`flex flex-col items-center justify-center py-2 min-h-[60px] transition-all active:scale-95 ${
              activeBottomTab === 'profile' ? 'text-cyan-400' : 'text-slate-500'
            }`}
          >
            <div className={`w-11 h-11 rounded-2xl flex items-center justify-center mb-0.5 transition-all ${
              activeBottomTab === 'profile' ? 'bg-cyan-500/15' : ''
            }`}>
              <User className="w-[22px] h-[22px]" strokeWidth={1.5} />
            </div>
            <span className="text-[10px] font-medium">Perfil</span>
          </button>
        </div>
      </nav>

      {/* ═══ SIDEBAR DRAWER ═══ */}
      <Sheet open={isDrawerOpen} onOpenChange={setIsDrawerOpen}>
        <SheetContent
          side="left"
          className="w-[280px] p-0 border-r"
          style={{ background: SURFACE, borderColor: BORDER }}
          data-testid="module-drawer"
        >
          <SheetHeader className="px-5 pt-6 pb-4" style={{ borderBottom: `1px solid ${BORDER}` }}>
            <SheetTitle className="text-left text-base font-bold tracking-tight text-white" style={{ fontFamily: "'Outfit', sans-serif" }}>
              Modulos
            </SheetTitle>
          </SheetHeader>
          <nav className="p-3 space-y-1" data-testid="drawer-nav">
            {DRAWER_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleDrawerClick(item.id)}
                  data-testid={`drawer-item-${item.id}`}
                  className={`w-full flex items-center gap-3 px-3 py-3.5 rounded-2xl transition-all min-h-[52px] active:scale-[0.98] ${
                    isActive ? 'bg-white/[0.06]' : 'hover:bg-white/[0.03]'
                  }`}
                  style={isActive ? { border: `1px solid ${BORDER}` } : { border: '1px solid transparent' }}
                >
                  <div className={`w-10 h-10 rounded-xl ${item.bg} flex items-center justify-center flex-shrink-0`}>
                    <Icon className={`w-5 h-5 ${item.color}`} strokeWidth={1.5} />
                  </div>
                  <span className={`text-sm font-medium ${isActive ? 'text-white' : 'text-slate-400'}`}>
                    {item.label}
                  </span>
                  <ChevronRight className={`w-4 h-4 ml-auto ${isActive ? 'text-cyan-400' : 'text-slate-700'}`} />
                </button>
              );
            })}
          </nav>
          {/* Footer */}
          <div className="absolute bottom-0 left-0 right-0 p-5" style={{ borderTop: `1px solid ${BORDER}` }}>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold" style={{ background: 'linear-gradient(135deg, #6366F1, #06B6D4)', color: 'white' }}>
                {user?.full_name?.charAt(0)?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{user?.full_name}</p>
                <p className="text-[11px] text-slate-500 truncate">{user?.apartment || ''}</p>
              </div>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
};

export default ResidentLayout;
