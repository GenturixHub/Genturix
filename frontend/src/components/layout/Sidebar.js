import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useModules } from '../../contexts/ModulesContext';
import { 
  LayoutDashboard, 
  AlertTriangle, 
  GraduationCap,
  CreditCard,
  FileText,
  Settings,
  LogOut,
  ChevronLeft,
  Building2,
  Briefcase,
  Users
} from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import GenturixLogo from '../GenturixLogo';

/**
 * GENTURIX - Sidebar Navigation
 * 
 * ESTRUCTURA ACTUALIZADA:
 * - Turnos YA NO es un módulo separado
 * - RRHH es el módulo central que contiene Turnos como submódulo
 * - Gestión de Usuarios para Administradores
 * - Módulos se filtran según configuración del condominio
 */

const Sidebar = ({ collapsed, onToggle }) => {
  const navigate = useNavigate();
  const { user, logout, hasAnyRole } = useAuth();
  const { isModuleEnabled } = useModules();
  const activeRole = sessionStorage.getItem('activeRole') || user?.roles?.[0];

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleSwitchPanel = () => {
    sessionStorage.removeItem('activeRole');
    navigate('/select-panel');
  };

  // Navigation items - TURNOS REMOVIDO como módulo independiente
  // Each item can have a moduleId to check if enabled for the condominium
  const navItems = [
    {
      title: 'Dashboard',
      icon: LayoutDashboard,
      href: '/dashboard',
      roles: ['Administrador', 'Supervisor', 'Guarda', 'Residente', 'Estudiante'],
      // Dashboard is always available
    },
    {
      title: 'Usuarios',
      icon: Users,
      href: '/admin/users',
      roles: ['Administrador'],
      description: 'Crear y gestionar usuarios'
      // User management is always available for admins
    },
    {
      title: 'Seguridad',
      icon: AlertTriangle,
      href: '/security',
      roles: ['Administrador', 'Supervisor', 'Guarda'],
      description: 'Emergencias, accesos, monitoreo',
      moduleId: 'security'
    },
    // RRHH - Módulo central único (incluye Turnos)
    {
      title: 'Recursos Humanos',
      icon: Briefcase,
      href: '/rrhh',
      roles: ['Administrador', 'Supervisor', 'Guarda', 'HR'],
      description: 'Personal, turnos, ausencias',
      moduleId: 'hr'
    },
    {
      title: 'Genturix School',
      icon: GraduationCap,
      href: '/school',
      roles: ['Administrador', 'Estudiante', 'Guarda'],
      moduleId: 'school'
    },
    {
      title: 'Pagos',
      icon: CreditCard,
      href: '/payments',
      roles: ['Administrador', 'Residente', 'Estudiante'],
      moduleId: 'payments'
    },
    {
      title: 'Auditoría',
      icon: FileText,
      href: '/audit',
      roles: ['Administrador'],
      moduleId: 'audit'
    },
    {
      title: 'Configuración',
      icon: Settings,
      href: '/settings',
      roles: ['Administrador'],
      // Settings is always available for admins
    },
  ];

  // Filter by role AND by module availability
  const filteredNavItems = navItems.filter(item => {
    // First check role permission
    const hasRolePermission = item.roles.includes(activeRole) || hasAnyRole(...item.roles);
    if (!hasRolePermission) return false;
    
    // Then check if module is enabled (if moduleId is specified)
    if (item.moduleId) {
      return isModuleEnabled(item.moduleId);
    }
    
    return true;
  });

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
            <GenturixLogo size={32} className="flex-shrink-0" />
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
