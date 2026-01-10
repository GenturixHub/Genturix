import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { Button } from '../ui/button';
import { 
  Bell, 
  Menu, 
  Search,
  AlertTriangle
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

const Header = ({ onMenuClick, title }) => {
  const { user } = useAuth();
  const [notifications] = React.useState([
    { id: 1, title: 'Alerta de seguridad', message: 'Nuevo evento de pánico registrado', type: 'alert' },
    { id: 2, title: 'Turno asignado', message: 'Se te ha asignado un nuevo turno', type: 'info' },
  ]);

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

      {/* Notifications */}
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
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-[10px] font-bold flex items-center justify-center">
                {notifications.length}
              </span>
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-80 bg-[#0F111A] border-[#1E293B]">
          <DropdownMenuLabel className="flex items-center justify-between">
            <span>Notificaciones</span>
            <span className="text-xs text-muted-foreground">{notifications.length} nuevas</span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator className="bg-[#1E293B]" />
          {notifications.map((notif) => (
            <DropdownMenuItem key={notif.id} className="flex items-start gap-3 py-3 cursor-pointer">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                notif.type === 'alert' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'
              }`}>
                <AlertTriangle className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{notif.title}</p>
                <p className="text-xs text-muted-foreground truncate">{notif.message}</p>
              </div>
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator className="bg-[#1E293B]" />
          <DropdownMenuItem className="text-center text-primary cursor-pointer">
            Ver todas las notificaciones
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

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
          <DropdownMenuItem className="cursor-pointer">Mi Perfil</DropdownMenuItem>
          <DropdownMenuItem className="cursor-pointer">Configuración</DropdownMenuItem>
          <DropdownMenuSeparator className="bg-[#1E293B]" />
          <DropdownMenuItem className="cursor-pointer text-red-400">
            Cerrar Sesión
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
};

export default Header;
