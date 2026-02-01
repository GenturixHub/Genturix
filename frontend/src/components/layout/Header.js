import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../ui/button';
import { 
  Bell, 
  Menu, 
  Search,
  AlertTriangle,
  User,
  Check,
  CheckCheck,
  RefreshCw
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { Input } from '../ui/input';
import { toast } from 'sonner';
import api from '../../services/api';

const Header = ({ onMenuClick, title }) => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loadingNotifications, setLoadingNotifications] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Fetch notifications and unread count
  const fetchNotifications = useCallback(async () => {
    if (!user) return;
    const roles = user.roles || [];
    
    // Only fetch for roles that handle notifications
    if (roles.includes('Administrador') || roles.includes('Supervisor') || roles.includes('Guarda') || roles.includes('SuperAdmin')) {
      try {
        const [notifData, countData] = await Promise.all([
          api.getNotifications(false),  // Get all notifications
          api.getUnreadNotificationCount()  // Get unread count
        ]);
        
        setNotifications(Array.isArray(notifData) ? notifData.slice(0, 10) : []);
        setUnreadCount(countData?.count || 0);
      } catch (err) {
        console.error('Error fetching notifications:', err);
        // Fallback to empty
        setNotifications([]);
        setUnreadCount(0);
      }
    }
  }, [user]);

  // Initial fetch and polling
  useEffect(() => {
    fetchNotifications();
    // Refresh every 30 seconds
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  // Mark single notification as read
  const handleMarkRead = async (notificationId, e) => {
    e?.stopPropagation();
    try {
      await api.markNotificationAsRead(notificationId);
      setNotifications(prev => prev.map(n => 
        n.id === notificationId ? {...n, read: true} : n
      ));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('Error marking notification read:', error);
    }
  };

  // Mark all as read when opening dropdown
  const handleDropdownOpenChange = async (open) => {
    setIsDropdownOpen(open);
    
    // When opening the dropdown, mark visible unread notifications as read
    if (open && unreadCount > 0) {
      // Small delay to let user see notifications first
      setTimeout(async () => {
        try {
          await api.markAllNotificationsAsRead();
          setNotifications(prev => prev.map(n => ({...n, read: true})));
          setUnreadCount(0);
        } catch (error) {
          console.error('Error marking all as read:', error);
        }
      }, 2000); // Mark as read after 2 seconds of viewing
    }
  };

  // Manual refresh
  const handleRefresh = async (e) => {
    e?.stopPropagation();
    setIsRefreshing(true);
    await fetchNotifications();
    setIsRefreshing(false);
    toast.success('Notificaciones actualizadas');
  };

  // Manual mark all as read
  const handleMarkAllRead = async (e) => {
    e?.stopPropagation();
    if (unreadCount === 0) return;
    
    try {
      const result = await api.markAllNotificationsAsRead();
      setNotifications(prev => prev.map(n => ({...n, read: true})));
      setUnreadCount(0);
      toast.success(`${result.count || 'Todas las'} notificaciones marcadas como leídas`);
    } catch (error) {
      toast.error('Error al marcar notificaciones');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Check if user has notification-enabled role
  const hasNotifications = user?.roles?.some(r => 
    ['Administrador', 'Supervisor', 'Guarda', 'SuperAdmin'].includes(r)
  );

  return (
    <header className="sticky top-0 z-30 h-16 bg-[#0F111A] border-b border-[#1E293B] px-4 flex items-center gap-4">
      {/* Mobile Menu Button */}
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={onMenuClick}
        data-testid="mobile-menu-btn"
      >
        <Menu className="w-5 h-5" />
      </Button>

      {/* Page Title */}
      <h1 className="text-lg font-semibold font-['Outfit'] hidden sm:block">
        {title}
      </h1>

      {/* Search */}
      <div className="flex-1 max-w-md ml-auto lg:ml-0">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Buscar..."
            className="pl-10 bg-[#181B25] border-[#1E293B] focus:border-primary w-full"
            data-testid="header-search"
          />
        </div>
      </div>

      {/* Notifications - Dynamic badge based on unread count */}
      {hasNotifications && (
        <DropdownMenu open={isDropdownOpen} onOpenChange={handleDropdownOpenChange}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="relative"
              data-testid="notifications-btn"
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span 
                  className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-[10px] font-bold flex items-center justify-center animate-pulse"
                  data-testid="notification-badge"
                >
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80 bg-[#0F111A] border-[#1E293B]">
            <DropdownMenuLabel className="flex items-center justify-between">
              <span>Notificaciones</span>
              <div className="flex items-center gap-2">
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-6 px-2"
                  onClick={handleRefresh}
                  disabled={isRefreshing}
                >
                  <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
                </Button>
                {unreadCount > 0 && (
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-6 px-2 text-primary"
                    onClick={handleMarkAllRead}
                    title="Marcar todas como leídas"
                  >
                    <CheckCheck className="w-3 h-3" />
                  </Button>
                )}
                <span className="text-xs text-muted-foreground">
                  {unreadCount > 0 ? `${unreadCount} sin leer` : 'Al día'}
                </span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-[#1E293B]" />
            {notifications.length === 0 ? (
              <div className="p-4 text-center text-sm text-muted-foreground">
                No hay notificaciones
              </div>
            ) : (
              <div className="max-h-80 overflow-y-auto">
                {notifications.map((notif) => (
                  <DropdownMenuItem 
                    key={notif.id} 
                    className={`flex items-start gap-3 py-3 cursor-pointer ${!notif.read ? 'bg-primary/5' : ''}`}
                    onClick={() => navigate('/security')}
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                      notif.read ? 'bg-gray-500/20 text-gray-400' : 'bg-red-500/20 text-red-400'
                    }`}>
                      <AlertTriangle className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm ${notif.read ? 'text-muted-foreground' : 'font-medium'}`}>
                        {notif.panic_type_label || 'Alerta'}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">
                        {notif.resident_name} - {notif.location || 'Sin ubicación'}
                      </p>
                      <p className="text-[10px] text-muted-foreground mt-1">
                        {new Date(notif.created_at).toLocaleString('es-ES', { 
                          day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
                        })}
                      </p>
                    </div>
                    {!notif.read && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 flex-shrink-0"
                        onClick={(e) => handleMarkRead(notif.id, e)}
                        title="Marcar como leída"
                      >
                        <Check className="w-3 h-3" />
                      </Button>
                    )}
                  </DropdownMenuItem>
                ))}
              </div>
            )}
            {notifications.length > 0 && (
              <>
                <DropdownMenuSeparator className="bg-[#1E293B]" />
                <DropdownMenuItem 
                  className="text-center text-primary cursor-pointer"
                  onClick={() => navigate('/security')}
                >
                  Ver todas las alertas
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      )}

      {/* User Menu */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="flex items-center gap-2"
            data-testid="user-menu-btn"
          >
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <span className="text-sm font-semibold text-primary">
                {user?.full_name?.charAt(0).toUpperCase()}
              </span>
            </div>
            <span className="hidden md:block text-sm">{user?.full_name}</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56 bg-[#0F111A] border-[#1E293B]">
          <DropdownMenuLabel>
            <div>
              <p className="font-medium">{user?.full_name}</p>
              <p className="text-xs text-muted-foreground">{user?.email}</p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator className="bg-[#1E293B]" />
          <DropdownMenuItem className="cursor-pointer" onClick={() => navigate('/profile')}>
            <User className="w-4 h-4 mr-2" />
            Mi Perfil
          </DropdownMenuItem>
          <DropdownMenuSeparator className="bg-[#1E293B]" />
          <DropdownMenuItem className="cursor-pointer text-red-400" onClick={handleLogout}>
            Cerrar Sesión
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
};

export default Header;
