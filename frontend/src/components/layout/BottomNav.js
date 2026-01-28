import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { 
  Shield, 
  LayoutDashboard, 
  AlertTriangle, 
  Users, 
  GraduationCap,
  CreditCard,
  FileText,
  LogOut,
  Home,
  Settings,
  Clock,
  Briefcase
} from 'lucide-react';

/**
 * GENTURIX - Bottom Navigation (Mobile)
 * 
 * Role-based navigation with clear separation:
 * - RRHH = People management (Admin/Supervisor)
 * - Turnos = Operations (Admin/Supervisor/Guard)
 */

// Hook to detect mobile
export const useIsMobile = () => {
  const [isMobile, setIsMobile] = React.useState(window.innerWidth < 768);

  React.useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return isMobile;
};

const BottomNav = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const activeRole = sessionStorage.getItem('activeRole') || user?.roles?.[0];

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Different nav items based on role
  const getNavItems = () => {
    // Resident - Emergency focused
    if (activeRole === 'Residente') {
      return [
        { icon: Home, label: 'Inicio', href: '/resident' },
        { icon: CreditCard, label: 'Pagos', href: '/payments' },
        { icon: Settings, label: 'Perfil', href: '/profile' },
      ];
    }
    
    // Guard - Operations focused
    if (activeRole === 'Guarda') {
      return [
        { icon: AlertTriangle, label: 'Alertas', href: '/guard' },
        { icon: Clock, label: 'Turnos', href: '/turnos' },
        { icon: GraduationCap, label: 'Cursos', href: '/student' },
      ];
    }
    
    // Student - Learning focused
    if (activeRole === 'Estudiante') {
      return [
        { icon: GraduationCap, label: 'Cursos', href: '/student' },
        { icon: CreditCard, label: 'Pagos', href: '/payments' },
        { icon: Settings, label: 'Perfil', href: '/profile' },
      ];
    }

    // Admin/Supervisor - Full access with separation
    return [
      { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard' },
      { icon: AlertTriangle, label: 'Seguridad', href: '/security' },
      { icon: Clock, label: 'Turnos', href: '/turnos' },
      { icon: Briefcase, label: 'RRHH', href: '/rrhh' },
    ];
  };

  const navItems = getNavItems();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-[#0F111A] border-t border-[#1E293B] safe-area-bottom">
      <div className="flex items-center justify-around h-16 px-2">
        {navItems.map((item) => {
          const IconComponent = item.icon;
          return (
            <NavLink
              key={item.href}
              to={item.href}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center flex-1 h-full transition-colors ${
                  isActive 
                    ? 'text-primary' 
                    : 'text-muted-foreground hover:text-foreground'
                }`
              }
              data-testid={`nav-mobile-${item.label.toLowerCase()}`}
            >
              <IconComponent className="w-5 h-5 mb-1" />
              <span className="text-[10px] font-medium">{item.label}</span>
            </NavLink>
          );
        })}
        <button
          onClick={handleLogout}
          className="flex flex-col items-center justify-center flex-1 h-full text-muted-foreground hover:text-red-400 transition-colors"
          data-testid="nav-mobile-logout"
        >
          <LogOut className="w-5 h-5 mb-1" />
          <span className="text-[10px] font-medium">Salir</span>
        </button>
      </div>
    </nav>
  );
};

export default BottomNav;
