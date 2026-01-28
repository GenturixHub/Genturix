import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { 
  Shield, 
  LayoutDashboard, 
  AlertTriangle, 
  Users, 
  Calendar,
  GraduationCap,
  CreditCard,
  FileText,
  Settings,
  LogOut,
  ChevronLeft,
  Building2,
  Clock,
  Briefcase
} from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';

/**
 * GENTURIX - Sidebar Navigation
 * 
 * Updated navigation structure:
 * - RRHH (Recursos Humanos) = Personas, datos laborales
 * - Turnos = Operaciones, asignaciones de tiempo
 */

const Sidebar = ({ collapsed, onToggle }) => {
  const navigate = useNavigate();
  const { user, logout, hasAnyRole } = useAuth();
  const activeRole = sessionStorage.getItem('activeRole') || user?.roles?.[0];

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleSwitchPanel = () => {
    sessionStorage.removeItem('activeRole');
    navigate('/select-panel');
  };

  // Navigation items with clear separation of concerns
  const navItems = [
    {
      title: 'Dashboard',
      icon: LayoutDashboard,
      href: '/dashboard',
      roles: ['Administrador', 'Supervisor', 'Guarda', 'Residente', 'Estudiante'],
    },
    {
      title: 'Seguridad',
      icon: AlertTriangle,
      href: '/security',
      roles: ['Administrador', 'Supervisor', 'Guarda'],
      description: 'Emergencias, accesos, monitoreo'
    },
    // HR Module - PEOPLE FOCUSED
    {
      title: 'Recursos Humanos',
      icon: Briefcase,
      href: '/rrhh',
      roles: ['Administrador', 'Supervisor'],
      description: 'Gestión de personal'
    },
    // Shifts Module - OPERATIONS FOCUSED
    {
      title: 'Turnos',
      icon: Clock,
      href: '/turnos',
      roles: ['Administrador', 'Supervisor', 'Guarda'],
      description: 'Horarios y asignaciones'
    },
    {
      title: 'Genturix School',
      icon: GraduationCap,
      href: '/school',
      roles: ['Administrador', 'Estudiante', 'Guarda'],
    },
    {
      title: 'Pagos',
      icon: CreditCard,
      href: '/payments',
      roles: ['Administrador', 'Residente', 'Estudiante'],
    },
    {
      title: 'Auditoría',
      icon: FileText,
      href: '/audit',
      roles: ['Administrador'],
    },
    {
      title: 'Configuración',
      icon: Settings,
      href: '/settings',
      roles: ['Administrador'],
    },
  ];

  const filteredNavItems = navItems.filter(item => 
    item.roles.includes(activeRole) || hasAnyRole(...item.roles)
  );

  return (
    <aside 
      className={`fixed left-0 top-0 z-40 h-screen bg-[#0F111A] border-r border-[#1E293B] transition-all duration-300 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
      data-testid="sidebar"
    >
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="flex items-center h-16 px-4 border-b border-[#1E293B]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center flex-shrink-0">
              <Shield className="w-5 h-5 text-white" />
            </div>
            {!collapsed && (
              <span className="text-lg font-bold font-['Outfit']">GENTURIX</span>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            className={`ml-auto ${collapsed ? 'rotate-180' : ''}`}
            onClick={onToggle}
            data-testid="sidebar-toggle"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
        </div>

        {/* User Info */}
        {!collapsed && (
          <div className="p-4 border-b border-[#1E293B]">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                <span className="text-sm font-semibold text-primary">
                  {user?.full_name?.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user?.full_name}</p>
                <p className="text-xs text-muted-foreground truncate">{activeRole}</p>
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <ScrollArea className="flex-1 py-4">
          <nav className="space-y-1 px-2">
            {filteredNavItems.map((item) => {
              const IconComponent = item.icon;
              return (
                <NavLink
                  key={item.href}
                  to={item.href}
                  className={({ isActive }) =>
                    `sidebar-item ${isActive ? 'active' : ''} ${collapsed ? 'justify-center px-2' : ''}`
                  }
                  data-testid={`nav-${item.href.replace('/', '')}`}
                  title={collapsed ? item.title : undefined}
                >
                  <IconComponent className="w-5 h-5 flex-shrink-0" />
                  {!collapsed && (
                    <div className="flex-1 min-w-0">
                      <span className="block">{item.title}</span>
                      {item.description && (
                        <span className="text-[10px] text-muted-foreground block truncate">
                          {item.description}
                        </span>
                      )}
                    </div>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </ScrollArea>

        {/* Footer Actions */}
        <div className="p-2 border-t border-[#1E293B]">
          {user?.roles?.length > 1 && (
            <Button
              variant="ghost"
              className={`w-full mb-2 ${collapsed ? 'px-2' : 'justify-start'}`}
              onClick={handleSwitchPanel}
              data-testid="switch-panel-btn"
            >
              <Building2 className="w-5 h-5 flex-shrink-0" />
              {!collapsed && <span className="ml-3">Cambiar Panel</span>}
            </Button>
          )}
          <Button
            variant="ghost"
            className={`w-full text-red-400 hover:text-red-300 hover:bg-red-500/10 ${collapsed ? 'px-2' : 'justify-start'}`}
            onClick={handleLogout}
            data-testid="sidebar-logout-btn"
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            {!collapsed && <span className="ml-3">Cerrar Sesión</span>}
          </Button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
