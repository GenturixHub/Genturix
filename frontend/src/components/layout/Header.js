import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../ui/button';
import { 
  Bell, 
  Menu, 
  Search,
  AlertTriangle,
  User
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
import api from '../../services/api';

const Header = ({ onMenuClick, title }) => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [loadingNotifications, setLoadingNotifications] = useState(false);

  // Fetch real notifications/alerts for admins and guards
  useEffect(() => {
    const fetchNotifications = async () => {
      if (!user) return;
      const roles = user.roles || [];
      
      // Only fetch for roles that handle alerts
      if (roles.includes('Administrador') || roles.includes('Supervisor') || roles.includes('Guarda')) {
        setLoadingNotifications(true);
        try {
          const events = await api.get('/security/panic-events');
          const activeAlerts = Array.isArray(events) 
            ? events.filter(e => e.status === 'active').slice(0, 5)
            : [];
          setNotifications(activeAlerts.map(e => ({
            id: e.id,
            title: e.panic_type_label || 'Alerta de Pánico',
            message: `${e.user_name} - ${e.location || 'Sin ubicación'}`,
            type: 'alert'
          })));
        } catch (err) {
          console.error('Error fetching notifications:', err);
          setNotifications([]);
        } finally {
          setLoadingNotifications(false);
        }
      }
    };
    
    fetchNotifications();
    // Refresh every 30 seconds
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, [user]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

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

      {/* Notifications - Only for Admin/Guard roles with real data */}
      {(user?.roles?.includes('Administrador') || user?.roles?.includes('Supervisor') || user?.roles?.includes('Guarda')) && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="relative"
              data-testid="notifications-btn"
            >
              <Bell className="w-5 h-5" />
              {notifications.length > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-[10px] font-bold flex items-center justify-center animate-pulse">
                  {notifications.length}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80 bg-[#0F111A] border-[#1E293B]">
            <DropdownMenuLabel className="flex items-center justify-between">
              <span>Alertas Activas</span>
              <span className="text-xs text-muted-foreground">
                {notifications.length > 0 ? `${notifications.length} activas` : 'Sin alertas'}
              </span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-[#1E293B]" />
            {notifications.length === 0 ? (
              <div className="p-4 text-center text-sm text-muted-foreground">
                No hay alertas activas
              </div>
            ) : (
              notifications.map((notif) => (
                <DropdownMenuItem key={notif.id} className="flex items-start gap-3 py-3 cursor-pointer">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-red-500/20 text-red-400">
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{notif.title}</p>
                    <p className="text-xs text-muted-foreground truncate">{notif.message}</p>
                  </div>
                </DropdownMenuItem>
              ))
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
