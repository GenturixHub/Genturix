import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useIsMobile } from './BottomNav';
import { useAuth } from '../../contexts/AuthContext';
import Sidebar from './Sidebar';
import Header from './Header';
import { 
  LayoutDashboard, 
  Users, 
  Briefcase, 
  Calendar, 
  User,
  Menu,
  CalendarOff,
  Clock,
  Settings,
  LogOut,
  MoreHorizontal,
  X
} from 'lucide-react';
import { Button } from '../ui/button';
import { cn } from '../../lib/utils';

// HR-specific Mobile Navigation - Native App Style
const HRMobileNav = ({ activeRoute }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  
  const items = [
    { id: 'dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard, href: '/rrhh' },
    { id: 'shifts', labelKey: 'rrhh.shiftPlanning', icon: Clock, href: '/rrhh?tab=turnos' },
    { id: 'absences', labelKey: 'rrhh.absences', icon: CalendarOff, href: '/rrhh?tab=ausencias' },
    { id: 'people', labelKey: 'rrhh.people', icon: Users, href: '/rrhh?tab=directory' },
    { id: 'profile', labelKey: 'nav.profile', icon: User, href: '/rrhh?tab=profile' },
  ];

  return (
    <nav 
      className="fixed bottom-0 left-0 right-0 z-50 bg-[#0A0A0F] border-t border-[#1E293B]/60" 
      data-testid="hr-mobile-nav"
      style={{ 
        height: '72px',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)'
      }}
    >
      <div className="flex items-center justify-around h-full px-2">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = activeRoute === item.href || 
            (item.id === 'dashboard' && activeRoute === '/rrhh');
          
          return (
            <button
              key={item.id}
              onClick={() => navigate(item.href)}
              data-testid={`hr-nav-${item.id}`}
              className={cn(
                'flex flex-col items-center justify-center flex-1 py-2 min-h-[60px]',
                'transition-all duration-150 active:scale-95 active:opacity-80',
                isActive ? 'text-primary' : 'text-muted-foreground'
              )}
            >
              <div className={cn(
                'w-11 h-11 rounded-2xl flex items-center justify-center mb-0.5',
                isActive ? 'bg-primary/15' : 'bg-transparent'
              )}>
                <Icon className={cn('w-[22px] h-[22px]', isActive ? 'text-primary' : '')} />
              </div>
              <span className="text-[10px] font-medium">{t(item.labelKey)}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};

// Admin-specific Mobile Navigation
const AdminMobileNav = ({ activeRoute }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [showMoreMenu, setShowMoreMenu] = useState(false);
  
  const items = [
    { id: 'dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard, href: '/dashboard' },
    { id: 'users', labelKey: 'nav.users', icon: Users, href: '/admin/users' },
    { id: 'rrhh', labelKey: 'nav.rrhhShort', icon: Briefcase, href: '/rrhh' },
    { id: 'reservations', labelKey: 'nav.reservationsShort', icon: Calendar, href: '/reservations' },
    { id: 'more', labelKey: 'nav.more', icon: MoreHorizontal, isMenu: true },
  ];

  const handleLogout = () => {
    setShowMoreMenu(false);
    logout();
    navigate('/login');
  };

  return (
    <>
      {/* More Menu Overlay */}
      {showMoreMenu && (
        <div className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm" onClick={() => setShowMoreMenu(false)}>
          <div 
            className="absolute bottom-24 right-4 w-56 bg-[#0F111A] border border-[#1E293B] rounded-xl shadow-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-1">
              <button
                onClick={() => { setShowMoreMenu(false); navigate('/profile'); }}
                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-white hover:bg-white/10 rounded-lg transition-colors"
                data-testid="mobile-nav-profile"
              >
                <User className="w-5 h-5 text-primary" />
                <span>{t('nav.profile', 'Mi Perfil')}</span>
              </button>
              <button
                onClick={() => { setShowMoreMenu(false); navigate('/admin/settings'); }}
                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-white hover:bg-white/10 rounded-lg transition-colors"
                data-testid="mobile-nav-settings"
              >
                <Settings className="w-5 h-5 text-muted-foreground" />
                <span>{t('nav.settings', 'Configuración')}</span>
              </button>
              <div className="border-t border-[#1E293B] my-1" />
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-4 py-3 text-sm text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                data-testid="mobile-nav-logout"
              >
                <LogOut className="w-5 h-5" />
                <span>{t('nav.logout', 'Cerrar Sesión')}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      <nav 
        className="fixed bottom-0 left-0 right-0 z-50 bg-[#0A0A0F] border-t border-[#1E293B]/60" 
        data-testid="admin-mobile-nav"
        style={{ 
          height: '72px',
          paddingBottom: 'env(safe-area-inset-bottom, 0px)'
        }}
      >
        <div className="flex items-center justify-around h-full px-2">
          {items.map((item) => {
            const Icon = item.icon;
            const isActive = item.isMenu 
              ? showMoreMenu
              : (activeRoute?.startsWith(item.href) || (item.id === 'dashboard' && activeRoute === '/admin/dashboard'));
            
            return (
              <button
                key={item.id}
                onClick={() => item.isMenu ? setShowMoreMenu(!showMoreMenu) : navigate(item.href)}
                data-testid={`admin-nav-${item.id}`}
                className={cn(
                  'flex flex-col items-center justify-center flex-1 py-2 min-h-[60px]',
                  'transition-all duration-150 active:scale-95 active:opacity-80',
                  isActive ? 'text-primary' : 'text-muted-foreground'
                )}
              >
                <div className={cn(
                  'w-11 h-11 rounded-2xl flex items-center justify-center mb-0.5',
                  isActive ? 'bg-primary/15' : 'bg-transparent'
                )}>
                  <Icon className={cn('w-[22px] h-[22px]', isActive ? 'text-primary' : '')} />
                </div>
                <span className="text-[10px] font-medium">{t(item.labelKey, item.id === 'more' ? 'Más' : '')}</span>
              </button>
            );
          })}
        </div>
      </nav>
    </>
  );
};

const DashboardLayout = ({ children, title = 'Dashboard', variant = 'admin' }) => {
  const isMobile = useIsMobile();
  const location = useLocation();
  const { user, hasRole } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Determine which nav to show based on role
  const isHRUser = hasRole?.('HR') && !hasRole?.('Administrador') && !hasRole?.('SuperAdmin');

  // Mobile layout - Native App Style
  if (isMobile) {
    return (
      <div 
        className="min-h-screen bg-[#05050A] flex flex-col w-full"
        style={{ 
          minHeight: '100dvh',
          WebkitOverflowScrolling: 'touch'
        }}
      >
        {/* Mobile Header - Sticky, compact, full-width */}
        <header 
          className="sticky top-0 z-40 bg-[#0A0A0F]/95 backdrop-blur-lg border-b border-[#1E293B]/60 flex-shrink-0 safe-area-top"
          style={{ height: '52px' }}
        >
          <div className="flex items-center justify-between h-full px-4">
            <h1 className="text-lg font-bold font-['Outfit'] text-white truncate">{title}</h1>
          </div>
        </header>
        
        {/* Content - Full width, native scrolling */}
        <main 
          className="flex-1 overflow-y-auto overflow-x-hidden w-full"
          style={{ 
            paddingBottom: 'calc(72px + env(safe-area-inset-bottom, 0px))',
            WebkitOverflowScrolling: 'touch'
          }}
        >
          <div className="px-3 py-4 w-full">
            {children}
          </div>
        </main>
        
        {/* Bottom Navigation - Fixed, app-style */}
        {isHRUser || variant === 'hr' ? (
          <HRMobileNav activeRoute={location.pathname + location.search} />
        ) : (
          <AdminMobileNav activeRoute={location.pathname} />
        )}
      </div>
    );
  }

  // Desktop layout - unchanged
  return (
    <div className="min-h-screen bg-[#05050A]">
      <Sidebar 
        collapsed={sidebarCollapsed} 
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} 
      />

      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      <div className={`transition-all duration-300 ${sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'}`}>
        <Header 
          onMenuClick={() => setMobileMenuOpen(!mobileMenuOpen)} 
          title={title}
        />
        
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
